use anyhow::{bail, Result};
use glob::glob;
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::time::{Instant, SystemTime};
use tantivy::schema::{Schema, STORED, TEXT};
use tantivy::{doc, Index};
use tokio::fs::File;
use tokio::io::{AsyncBufReadExt, BufReader};
use tracing::info;

const COMMIT_THRESHOLD: usize = 1000;

#[derive(Debug, Deserialize)]
struct JsonlEntry {
    url: String,
    title: Option<String>,
    content_text: Option<String>,
    meta_content: Option<String>,
}

#[derive(Debug, Serialize)]
struct ModerationRequest {
    input: String,
}

#[derive(Debug, Deserialize, Clone)]
struct ModerationResponse {
    results: Vec<ModerationResult>,
}

#[derive(Debug, Deserialize, Clone)]
struct ModerationResult {
    flagged: bool,
    categories: ModerationCategories,
}

#[derive(Debug, Deserialize, Clone)]
struct ModerationCategories {
    sexual: bool,
    hate: bool,
    harassment: bool,
    #[serde(rename = "self-harm")]
    self_harm: bool,
    #[serde(rename = "sexual/minors")]
    sexual_minors: bool,
    violence: bool,
}

async fn check_content_moderation(content: &str) -> Result<ModerationResult> {
    let api_key =
        std::env::var("OPENAI_API_KEY").map_err(|_| anyhow::anyhow!("OPENAI_API_KEY not set"))?;

    let client = reqwest::Client::new();
    let response = client
        .post("https://api.openai.com/v1/moderations")
        .header("Authorization", format!("Bearer {}", api_key))
        .json(&ModerationRequest {
            input: content.to_string(),
        })
        .send()
        .await?
        .json::<ModerationResponse>()
        .await?;

    response
        .results
        .first()
        .cloned()
        .ok_or_else(|| anyhow::anyhow!("No moderation results"))
}

async fn create_search_index() -> Result<Index> {
    let timestamp = SystemTime::now()
        .duration_since(SystemTime::UNIX_EPOCH)?
        .as_secs();

    let index_path = PathBuf::from("pulse_indexes").join(format!("index_{}", timestamp));

    std::fs::create_dir_all(&index_path)?;
    info!("Creating index at: {}", index_path.display());

    let mut schema_builder = Schema::builder();

    schema_builder.add_text_field("url", TEXT | STORED);
    schema_builder.add_text_field("title", TEXT | STORED);
    schema_builder.add_text_field("content", TEXT);
    schema_builder.add_text_field("meta_tags", TEXT | STORED);
    schema_builder.add_bool_field("nsfw", STORED);
    schema_builder.add_bool_field("harassment", STORED);
    schema_builder.add_bool_field("hate", STORED);
    schema_builder.add_bool_field("violence", STORED);
    schema_builder.add_bool_field("self_harm", STORED);

    let schema = schema_builder.build();
    let index = Index::create_in_dir(&index_path, schema)?;
    Ok(index)
}

async fn check_files_exist(pattern: &str) -> Result<usize> {
    let mut count = 0;
    for entry in glob(pattern)? {
        match entry {
            Ok(_) => count += 1,
            Err(e) => tracing::warn!("Error matching pattern: {}", e),
        }
    }

    if count == 0 {
        bail!("No files found matching pattern: {}", pattern);
    }

    info!("Found {} files to process", count);
    Ok(count)
}

async fn index_documents(analyses_pattern: &str, index: &Index) -> Result<()> {
    let start_time = Instant::now();
    let schema = index.schema();
    let mut total_processed = 0;

    let mut index_writer = index.writer_with_num_threads(4, 4 * 1024 * 1024 * 1024)?;

    info!("Starting to process files...");
    let mut file_count = 0;

    for entry in glob(analyses_pattern)? {
        match entry {
            Ok(path) => {
                file_count += 1;
                info!("Processing file [{}]: {}", file_count, path.display());
                let file_start_time = Instant::now();
                let mut line_count = 0;

                let file = File::open(&path).await?;
                let reader = BufReader::new(file);
                let mut lines = reader.lines();

                while let Some(line) = lines.next_line().await? {
                    line_count += 1;
                    match serde_json::from_str::<JsonlEntry>(&line) {
                        Ok(entry_data) => {
                            let content = entry_data.content_text.as_deref().unwrap_or_default();
                            let title = entry_data.title.as_deref().unwrap_or_default();

                            let combined_content = format!(
                                "{}\n{}\n{}",
                                title,
                                content,
                                entry_data.meta_content.as_deref().unwrap_or_default()
                            );

                            let result = check_content_moderation(&combined_content)
                                .await
                                .unwrap_or_else(|e| {
                                    tracing::warn!("Moderation check failed: {}", e);
                                    ModerationResult {
                                        flagged: false,
                                        categories: ModerationCategories {
                                            sexual: false,
                                            hate: false,
                                            harassment: false,
                                            self_harm: false,
                                            sexual_minors: false,
                                            violence: false,
                                        },
                                    }
                                });

                            index_writer.add_document(doc!(
                                schema.get_field("url").unwrap() => entry_data.url,
                                schema.get_field("title").unwrap() => entry_data.title.unwrap_or_default(),
                                schema.get_field("content").unwrap() => content,
                                schema.get_field("meta_tags").unwrap() => entry_data.meta_content.unwrap_or_default(),
                                schema.get_field("nsfw").unwrap() => result.flagged || result.categories.sexual || result.categories.sexual_minors,
                                schema.get_field("harassment").unwrap() => result.categories.harassment,
                                schema.get_field("hate").unwrap() => result.categories.hate,
                                schema.get_field("violence").unwrap() => result.categories.violence,
                                schema.get_field("self_harm").unwrap() => result.categories.self_harm
                            ))?;

                            total_processed += 1;

                            if total_processed % COMMIT_THRESHOLD == 0 {
                                if let Ok(_) = index_writer.commit() {
                                    let elapsed = start_time.elapsed().as_secs_f64();
                                    let rate = total_processed as f64 / elapsed;
                                    info!(
                                        total_processed,
                                        rate = rate,
                                        "Processing at {:.2} docs/second",
                                        rate
                                    );
                                }
                            }
                        }
                        Err(e) => {
                            tracing::warn!(
                                "Failed to parse JSON line {} in file {}: {}",
                                line_count,
                                path.display(),
                                e
                            );
                        }
                    }
                }

                info!(
                    "Finished file {} ({} lines) in {:.2}s",
                    path.display(),
                    line_count,
                    file_start_time.elapsed().as_secs_f64()
                );
            }
            Err(e) => tracing::error!("Error matching glob pattern: {}", e),
        }
    }

    info!("Performing final commit...");
    index_writer.commit()?;

    let total_duration = start_time.elapsed();
    info!(
        total_processed,
        total_files = file_count,
        duration = format!("{:?}", total_duration),
        "Indexing completed"
    );
    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt().with_env_filter("info").init();
    info!("Starting search indexer from JSONL files");

    let analyses_pattern = "analyses/partition=*/*.jsonl";
    info!("Looking for files matching: {}", analyses_pattern);

    // Check for files before creating index
    check_files_exist(analyses_pattern).await?;

    let index = create_search_index().await?;
    info!("Search index created");

    index_documents(analyses_pattern, &index).await?;

    info!("Search indexing completed successfully");
    info!("You can use the latest index in the 'pulse_indexes' directory for search operations");
    Ok(())
}

// THE CONTENT BELOW CONTAINS NSFW KEYWORDS
// DISCRETION ADVISED
// ====================================================
// ====================================================
// ====================================================
// ====================================================
// ====================================================
// ====================================================
// ====================================================
// ====================================================
// ====================================================
// ====================================================
// ====================================================
