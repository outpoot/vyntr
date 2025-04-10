use anyhow::Result;
use axum::{extract::Query, http::StatusCode, routing::get, Json, Router};
use serde::{Deserialize, Serialize};
use std::{path::PathBuf, sync::Arc};
use tantivy::{
    collector::TopDocs,
    query::QueryParser,
    schema::{OwnedValue, Schema, Value},
    Index, IndexReader, TantivyDocument,
};
use tower_http::cors::CorsLayer;
use tracing::info;

const MAX_RESULTS: usize = 10;

#[derive(Debug, Deserialize)]
struct SearchParams {
    q: String,
}

#[derive(Debug, Serialize)]
struct SearchResult {
    score: f32,
    title: String,
    url: String,
    preview: String,
    language: String,
    meta_description: String,
    nsfw: bool,
}

#[derive(Debug, Serialize)]
struct SearchResponse {
    results: Vec<SearchResult>,
    query: String,
    total: usize,
}

struct SearchState {
    reader: IndexReader,
    query_parser: QueryParser,
    schema: Arc<Schema>,
}

fn get_latest_index() -> Result<PathBuf> {
    let index_dir = PathBuf::from("pulse_indexes");

    let latest = std::fs::read_dir(&index_dir)?
        .filter_map(Result::ok)
        .filter(|entry| entry.file_type().map(|ft| ft.is_dir()).unwrap_or(false))
        .max_by_key(|entry| entry.path());

    latest
        .map(|e| e.path())
        .ok_or_else(|| anyhow::anyhow!("No index found in {}", index_dir.display()))
}

async fn search_handler(
    state: axum::extract::State<Arc<SearchState>>,
    Query(params): Query<SearchParams>,
) -> Result<Json<SearchResponse>, (StatusCode, String)> {
    let searcher = state.reader.searcher();

    let query = state
        .query_parser
        .parse_query(&params.q)
        .map_err(|e| (StatusCode::BAD_REQUEST, e.to_string()))?;

    let top_docs = searcher
        .search(&query, &TopDocs::with_limit(MAX_RESULTS))
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, e.to_string()))?;

    let title_field = state.schema.get_field("title").unwrap();
    let url_field = state.schema.get_field("url").unwrap();
    let preview_field = state.schema.get_field("preview").unwrap();
    let language_field = state.schema.get_field("language").unwrap();
    let meta_field = state.schema.get_field("meta_tags").unwrap();
    let nsfw_field = state.schema.get_field("nsfw").unwrap();

    let results: Vec<SearchResult> = top_docs
        .iter()
        .filter_map(|(score, doc_address)| {
            searcher
                .doc(*doc_address)
                .ok()
                .map(|retrieved_doc: TantivyDocument| {
                    let doc = retrieved_doc.to_owned();
                    SearchResult {
                        score: *score,
                        title: doc
                            .get_first(title_field)
                            .and_then(|v| match v {
                                OwnedValue::Str(s) => Some(s.clone()),
                                _ => None,
                            })
                            .unwrap_or_default(),
                        url: doc
                            .get_first(url_field)
                            .and_then(|v| match v {
                                OwnedValue::Str(s) => Some(s.clone()),
                                _ => None,
                            })
                            .unwrap_or_default(),
                        preview: doc
                            .get_first(preview_field)
                            .and_then(|v| match v {
                                OwnedValue::Str(s) => Some(s.clone()),
                                _ => None,
                            })
                            .unwrap_or_default(),
                        language: doc
                            .get_first(language_field)
                            .and_then(|v| match v {
                                OwnedValue::Str(s) => Some(s.clone()),
                                _ => None,
                            })
                            .unwrap_or_else(|| "en".to_string()),
                        meta_description: doc
                            .get_first(meta_field)
                            .and_then(|v| match v {
                                OwnedValue::Str(s) => Some(s.clone()),
                                _ => None,
                            })
                            .unwrap_or_default(),
                        nsfw: doc
                            .get_first(nsfw_field)
                            .and_then(|v| v.as_bool())
                            .unwrap_or_default(),
                    }
                })
        })
        .collect();

    let total_results = results.len();

    Ok(Json(SearchResponse {
        results,
        query: params.q,
        total: total_results,
    }))
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt().with_env_filter("info").init();

    let index_path = get_latest_index()?;
    info!("Using index at: {}", index_path.display());

    let index = Index::open_in_dir(&index_path)?;
    let schema = Arc::new(index.schema());

    let reader = index.reader()?;
    let title_field = schema.get_field("title").unwrap();
    let content_field = schema.get_field("content").unwrap();
    let meta_field = schema.get_field("meta_tags").unwrap();

    let query_parser = QueryParser::for_index(&index, vec![title_field, content_field, meta_field]);

    let state = Arc::new(SearchState {
        reader,
        query_parser,
        schema: schema.clone(),
    });

    let app = Router::new()
        .route("/search", get(search_handler))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = "0.0.0.0:3000";
    info!("Starting server at http://{}", addr);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}
