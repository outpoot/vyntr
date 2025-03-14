use aws_sdk_s3::{
    config::{retry, timeout, Region},
    primitives::ByteStream,
    Client,
};
use serde::{Deserialize, Serialize};
use std::env;
use uuid::Uuid;

#[derive(Debug, Serialize, Deserialize)]
pub struct SeoAnalysis {
    pub url: String,
    pub language: String,
    pub title: String,
    pub meta_tags: Vec<MetaTag>,
    pub canonical_url: Option<String>,
    pub content_text: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct MetaTag {
    pub name: String,
    pub content: String,
}

pub async fn create_db_pool() -> Result<Client, Box<dyn std::error::Error>> {
    dotenvy::dotenv().ok();

    let bucket = env::var("S3_BUCKET")?;
    let region_env = env::var("S3_REGION").unwrap_or_else(|_| "us-east-1".to_string());

    println!("[S3] Using region: {}", region_env);
    println!("[S3] Using bucket: {}", bucket);

    let shared_config = aws_config::from_env()
        .region(Region::new(region_env))
        .load()
        .await;

    let s3_config = aws_sdk_s3::config::Builder::from(&shared_config)
        .force_path_style(true)
        .retry_config(
            retry::RetryConfig::standard()
                .with_max_attempts(3)
                .with_initial_backoff(std::time::Duration::from_secs(1)),
        )
        .timeout_config(
            timeout::TimeoutConfig::builder()
                .connect_timeout(std::time::Duration::from_secs(10))
                .read_timeout(std::time::Duration::from_secs(30))
                .build(),
        )
        .build();

    Ok(Client::from_conf(s3_config))
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
    client: &Client,
    analyses: &[SeoAnalysis],
) -> Result<(), Box<dyn std::error::Error>> {
    let bucket = env::var("S3_BUCKET")?;
    println!("[S3] Using bucket: {}", bucket);

    for (chunk_idx, chunk) in analyses.chunks(10_000).enumerate() {
        let mut jsonl = Vec::new();
        for analysis in chunk {
            let sanitized = sanitize_analysis(analysis);
            let json = serde_json::to_string(&sanitized)?;
            jsonl.push(json);
        }

        let body = jsonl.join("\n");
        if body.is_empty() {
            continue;
        }

        let partition = if let Some(first) = chunk.first() {
            format!("{:02x}", md5::compute(&first.url).0[0])
        } else {
            continue;
        };

        let key = format!(
            "analyses/partition={}/batch_{}.jsonl",
            partition,
            Uuid::new_v4()
        );

        println!(
            "[S3] Uploading chunk {} to {}/{}",
            chunk_idx + 1,
            bucket,
            key
        );

        client
            .put_object()
            .bucket(&bucket)
            .key(&key)
            .content_type("application/jsonlines")
            .content_length(body.len() as i64)
            .body(ByteStream::from(body.into_bytes()))
            .send()
            .await?;

        println!("[S3] Successfully uploaded chunk {}", chunk_idx + 1);
    }

    Ok(())
}
