use serde::Serialize;
use std::env;
use tokio_postgres::{Client, NoTls, Statement};

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

pub struct DbStatements {
    pub insert_site: Statement,
    pub insert_meta: Statement,
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

pub async fn prepare_statements(
    client: &Client,
) -> Result<DbStatements, Box<dyn std::error::Error>> {
    let insert_site = client
        .prepare(
            "INSERT INTO sites (url, language, title, canonical_url, content_text)
             VALUES ($1, $2, $3, $4, $5)
             RETURNING id;",
        )
        .await?;

    let insert_meta = client
        .prepare(
            "INSERT INTO meta_tags (analysis_id, name, content)
             VALUES ($1, $2, $3);",
        )
        .await?;

    Ok(DbStatements {
        insert_site,
        insert_meta,
    })
}

pub async fn save_analysis(
    client: &Client,
    statements: &DbStatements,
    analysis: &SeoAnalysis,
) -> Result<(), Box<dyn std::error::Error>> {
    let row = client
        .query_one(
            &statements.insert_site,
            &[
                &analysis.url,
                &analysis.language,
                &analysis.title,
                &analysis.canonical_url.as_deref(),
                &analysis.content_text,
            ],
        )
        .await?;
    let analysis_id: i32 = row.get(0);

    for meta in &analysis.meta_tags {
        client
            .execute(
                &statements.insert_meta,
                &[&analysis_id, &meta.name, &meta.content],
            )
            .await?;
    }

    println!("Saved analysis for {}", analysis.url);
    Ok(())
}
