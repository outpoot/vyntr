use anyhow::Result;
use dotenv::dotenv;
use sqlx::{postgres::PgPoolOptions, FromRow};
use std::{env, time::Instant};
use tantivy::{doc, Index};
use tantivy::schema::{Schema, STORED, TEXT};
use tracing::info;
use std::{path::PathBuf, time::SystemTime};
use std::thread;
use std::time::Duration;

mod models;

const CHUNK_SIZE: i32 = 5000;
const MIN_DISK_SPACE: u64 = 10 * 1024 * 1024 * 1024; // 10GB minimum
const MAX_RETRIES: u32 = 3;
const COMMIT_THRESHOLD: usize = 1000;

#[derive(Debug, FromRow)]
struct SiteIndexed {
    id: i32,
    url: String,
    title: Option<String>,
    content_text: Option<String>,
    meta_content: Option<String>,
}

fn check_disk_space(path: &PathBuf) -> Result<()> {
    let available = fs2::available_space(path)?;
    if available < MIN_DISK_SPACE {
        anyhow::bail!("Not enough disk space. Need at least 10GB, found {}GB", available / 1024 / 1024 / 1024);
    }
    Ok(())
}
 
async fn create_search_index() -> Result<Index> {
    let timestamp = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)?
        .as_secs();
    
    // Use user's home directory instead
    let home = env::var("USERPROFILE").unwrap_or_else(|_| ".".to_string());
    let index_path = PathBuf::from(home)
        .join("pulse_indexes")
        .join(format!("index_{}", timestamp));
    
    check_disk_space(&index_path)?;
    std::fs::create_dir_all(&index_path)?;
    info!("Creating index at: {}", index_path.display());
    
    let mut schema_builder = Schema::builder();
    
    schema_builder.add_text_field("url", TEXT);
    schema_builder.add_text_field("title", TEXT | STORED);
    schema_builder.add_text_field("content", TEXT);
    schema_builder.add_text_field("meta_tags", TEXT);
    
    let schema = schema_builder.build();
    let index = Index::create_in_dir(&index_path, schema)?;
    Ok(index)
}

async fn index_documents(pool: &sqlx::PgPool, index: &Index) -> Result<()> {
    let start_time = Instant::now();
    let schema = index.schema();
    let mut total_processed = 0;
    let mut last_id = 0;
    let mut retry_count = 0;

    loop {
        let mut index_writer = match index.writer_with_num_threads(4, 4 * 1024 * 1024 * 1024) {
            Ok(writer) => writer,
            Err(e) => {
                if retry_count >= MAX_RETRIES {
                    anyhow::bail!("Failed to create index writer after {} retries: {}", MAX_RETRIES, e);
                }
                retry_count += 1;
                info!("Failed to create index writer, retrying in 5s: {}", e);
                thread::sleep(Duration::from_secs(5));
                continue;
            }
        };

        let sites = sqlx::query_as::<_, SiteIndexed>(
            "SELECT id, url, title, content_text, meta_content 
             FROM sites_indexed 
             WHERE id > $1 
             ORDER BY id 
             LIMIT $2"
        )
        .bind(last_id)
        .bind(CHUNK_SIZE)
        .fetch_all(pool)
        .await;

        let sites = match sites {
            Ok(s) => s,
            Err(e) => {
                info!("Query failed, retrying in 5s: {}", e);
                thread::sleep(Duration::from_secs(5));
                continue;
            }
        };

        let chunk_size = sites.len();
        if chunk_size == 0 {
            break;
        }

        for site in sites {
            last_id = site.id;
            index_writer.add_document(doc!(
                schema.get_field("url").unwrap() => site.url,
                schema.get_field("title").unwrap() => site.title.unwrap_or_default(),
                schema.get_field("content").unwrap() => site.content_text.unwrap_or_default(),
                schema.get_field("meta_tags").unwrap() => site.meta_content.unwrap_or_default(),
            ))?;

            total_processed += 1;
            if total_processed % COMMIT_THRESHOLD == 0 {
                match index_writer.commit() {
                    Ok(_) => {
                        info!(total_processed, "Commit successful");
                        let elapsed = start_time.elapsed().as_secs();
                        let rate = total_processed as f64 / elapsed as f64;
                        info!(
                            last_id,
                            total_processed,
                            rate = rate,
                            "Processing at {:.2} sites/second",
                            rate
                        );
                    },
                    Err(e) => {
                        info!("Commit failed, will retry on next iteration: {}", e);
                        break;
                    }
                }
            }
        }
    }

    info!(total_processed, "Indexing completed");
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenv().ok();
    
    // Initialize logging
    tracing_subscriber::fmt()
        .with_env_filter("info")
        .init();

    info!("Starting search indexer");
    
    let database_url = env::var("DATABASE_URL")
        .expect("DATABASE_URL must be set in .env file");

    let pool = PgPoolOptions::new()
        .max_connections(5)
        .acquire_timeout(Duration::from_secs(30))
        .connect(&database_url)
        .await?;
    
    info!("Database connection established");

    let index = create_search_index().await?;
    info!("Search index created");
    
    index_documents(&pool, &index).await?;

    info!("Search indexing completed successfully");
    info!("You can use the latest index in the 'indexes' directory for search operations");
    Ok(())
}
