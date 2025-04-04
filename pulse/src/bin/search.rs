use anyhow::Result;
use std::{env, path::PathBuf, io::{self, Write}};
use tantivy::{collector::TopDocs, query::QueryParser, Index};
use tracing::info;

const MAX_RESULTS: usize = 10;

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

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .init();

    let index_path = get_latest_index()?;
    info!("Using index at: {}", index_path.display());

    let index = Index::open_in_dir(&index_path)?;
    let reader = index.reader()?;
    let searcher = reader.searcher();

    let schema = index.schema();
    let title_field = schema.get_field("title").unwrap();
    let url_field = schema.get_field("url").unwrap();
    let content_field = schema.get_field("content").unwrap();
    let meta_field = schema.get_field("meta_tags").unwrap();

    let query_parser = QueryParser::for_index(&index, vec![title_field, content_field, meta_field]);

    loop {
        print!("\nEnter search query (or 'quit' to exit): ");
        io::stdout().flush()?;

        let mut query_str = String::new();
        io::stdin().read_line(&mut query_str)?;
        let query_str = query_str.trim();

        if query_str.eq_ignore_ascii_case("quit") {
            break;
        }

        if query_str.is_empty() {
            continue;
        }

        let query = query_parser.parse_query(query_str)?;
        let top_docs = searcher.search(&query, &TopDocs::with_limit(MAX_RESULTS))?;
        
        println!("\nSearch results for: {}", query_str);
        println!("{}", "─".repeat(50));

        for (score, doc_address) in top_docs {
            let retrieved_doc = searcher.doc(doc_address)?;
            let empty_value = tantivy::schema::Value::Str("".to_string());
            println!(
                "Score: {:.2}\nTitle: {}\nURL: {}\n{}",
                score,
                retrieved_doc.get_first(title_field).map(|v| v.as_text().unwrap_or_default()).unwrap_or_default(),
                retrieved_doc.get_first(url_field).unwrap_or_else(|| &empty_value).as_text().unwrap_or_default(),
                "─".repeat(50)
            );
        }
    }

    Ok(())
}
