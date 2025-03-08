use serde::Serialize;
use sqlx::postgres::{PgPool, PgPoolOptions};
use sqlx::Row;
use std::env;
use std::time::Duration;

#[derive(Debug, Serialize)]
pub struct SeoAnalysis {
    pub url: String,
    pub language: String,
    pub title: String,
    pub meta_tags: Vec<MetaTag>,
    pub canonical_url: Option<String>,
    pub content_text: String,
}

#[derive(Debug, Serialize)]
pub struct MetaTag {
    pub name: String,
    pub content: String,
}

pub async fn create_db_pool() -> Result<PgPool, Box<dyn std::error::Error>> {
    dotenvy::dotenv().ok();
    let database_url = env::var("DATABASE_URL")?;
    let pool = PgPoolOptions::new()
        .max_connections(20)
        .acquire_timeout(Duration::from_secs(30))
        .idle_timeout(Duration::from_secs(600))
        .connect(&database_url)
        .await?;

    Ok(pool)
}

fn sanitize_text(text: &str) -> String {
    text.chars()
        .filter(|c| !c.is_control() && *c != '\0')
        .collect()
}

fn sanitize_analysis(analysis: &SeoAnalysis) -> SeoAnalysis {
    SeoAnalysis {
        url: sanitize_text(&analysis.url),
        language: sanitize_text(&analysis.language),
        title: sanitize_text(&analysis.title),
        meta_tags: analysis
            .meta_tags
            .iter()
            .map(|tag| MetaTag {
                name: sanitize_text(&tag.name),
                content: sanitize_text(&tag.content),
            })
            .collect(),
        canonical_url: analysis
            .canonical_url
            .as_ref()
            .map(|url| sanitize_text(url)),
        content_text: sanitize_text(&analysis.content_text),
    }
}

pub async fn save_analyses_batch(
    pool: &PgPool,
    analyses: &[SeoAnalysis],
) -> Result<(), Box<dyn std::error::Error>> {
    println!("Attempting to save batch of {} analyses", analyses.len());

    let sanitized: Vec<SeoAnalysis> = analyses.iter().map(sanitize_analysis).collect();

    let mut tx = pool.begin().await?;

    let rows = sqlx::query(
        r#"
        INSERT INTO sites (url, language, title, canonical_url, content_text)
        SELECT 
            s.url, s.language, s.title, s.canonical_url, s.content_text
        FROM jsonb_to_recordset($1::jsonb) AS s(
            url text,
            language text,
            title text,
            canonical_url text,
            content_text text
        )
        RETURNING id
        "#,
    )
    .bind(serde_json::to_value(&sanitized)?)
    .fetch_all(&mut *tx)
    .await?;

    let site_ids: Vec<i32> = rows.iter().map(|row| row.get("id")).collect();

    let mut all_meta_tags = Vec::new();
    for (idx, analysis) in sanitized.iter().enumerate() {
        for meta_tag in &analysis.meta_tags {
            all_meta_tags.push(serde_json::json!({
                "analysis_id": site_ids[idx],
                "name": meta_tag.name,
                "content": meta_tag.content
            }));
        }
    }

    if !all_meta_tags.is_empty() {
        sqlx::query(
            r#"
            INSERT INTO meta_tags (analysis_id, name, content)
            SELECT 
                (elem->>'analysis_id')::integer,
                (elem->>'name')::text,
                (elem->>'content')::text
            FROM jsonb_array_elements($1::jsonb) AS elem
            "#,
        )
        .bind(serde_json::to_value(all_meta_tags)?)
        .execute(&mut *tx)
        .await?;
    }

    tx.commit().await?;

    Ok(())
}
