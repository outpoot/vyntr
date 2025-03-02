use serde::Serialize;
use std::env;
use tokio_postgres::{Client, NoTls};

#[derive(Debug, Serialize)]
pub struct SeoAnalysis {
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

pub async fn create_db_client() -> Result<Client, Box<dyn std::error::Error>> {
    dotenvy::dotenv().ok();

    let database_url = env::var("DATABASE_URL").expect("DATABASE_URL must be set in .env");

    let (client, connection) = tokio_postgres::connect(&database_url, NoTls).await?;

    tokio::spawn(async move {
        if let Err(e) = connection.await {
            eprintln!("Connection error: {}", e);
        }
    });

    Ok(client)
}

pub async fn save_analysis(
    client: &Client,
    analysis: &SeoAnalysis,
) -> Result<(), Box<dyn std::error::Error>> {
    let row = client
        .query_one(
            "INSERT INTO sites (language, title, canonical_url, content_text) 
            VALUES ($1, $2, $3, $4) RETURNING id",
            &[
                &analysis.language,
                &analysis.title,
                &analysis.canonical_url,
                &analysis.content_text,
            ],
        )
        .await?;

    let analysis_id: i32 = row.get(0);

    let stmt = client
        .prepare("INSERT INTO meta_tags (analysis_id, name, content) VALUES ($1, $2, $3)")
        .await?;

    for meta in &analysis.meta_tags {
        client
            .execute(&stmt, &[&analysis_id, &meta.name, &meta.content])
            .await?;
    }

    Ok(())
}
