use serde::Serialize;
use serde_json;
use sqlx::postgres::{PgPool, PgPoolOptions};
use std::env;

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
        .max_connections(5)
        .connect(&database_url)
        .await?;

    Ok(pool)
}

pub async fn save_analysis(
    pool: &PgPool,
    analysis: &SeoAnalysis,
) -> Result<(), Box<dyn std::error::Error>> {
    // Use raw SQL queries without prepared statements
    let analysis_id: i32 = sqlx::query_scalar(
        r#"
        INSERT INTO sites (url, language, title, canonical_url, content_text)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        "#,
    )
    .bind(&analysis.url)
    .bind(&analysis.language)
    .bind(&analysis.title)
    .bind(&analysis.canonical_url)
    .bind(&analysis.content_text)
    .fetch_one(pool)
    .await?;

    // Batch insert using JSON
    sqlx::query(
        r#"
        INSERT INTO meta_tags (analysis_id, name, content)
        SELECT $1, (elem->>'name')::text, (elem->>'content')::text
        FROM jsonb_array_elements($2::jsonb) AS elem
        "#,
    )
    .bind(analysis_id)
    .bind(serde_json::to_value(&analysis.meta_tags)?)
    .execute(pool)
    .await?;

    Ok(())
}
