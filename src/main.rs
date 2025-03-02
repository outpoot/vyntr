mod db;
mod meta_tags;

use std::collections::HashSet;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use reqwest;
use scraper::{Html, Selector};
use tokio::sync::Mutex;
use url::Url;

use crate::db::{create_db_pool, save_analysis, MetaTag, SeoAnalysis};
use crate::meta_tags::META_SELECTORS;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let initial_url = "https://nytimes.com";

    let pool = create_db_pool().await?;
    let visited = Arc::new(Mutex::new(HashSet::new()));

    let (main_links, main_analysis) = process_page(initial_url, &pool).await?;

    let document = Html::parse_document(&reqwest::get(initial_url).await?.text().await?);
    let a_selector = Selector::parse("a").unwrap();
    let a_tags_count = document.select(&a_selector).count();
    println!(
        "Total <a> tags on root page {}: {}",
        initial_url, a_tags_count
    );

    save_analysis(&pool, &main_analysis).await?;
    println!("Main page processed: {}", initial_url);

    let max_pages = 700;

    let limit = max_pages - 1;
    let total_links = main_links.len().min(limit);

    println!("Processing {} child pages concurrently...", total_links);

    use futures::stream::{self, StreamExt};

    let progress = Arc::new(AtomicUsize::new(0));

    stream::iter(main_links)
        .filter_map(|url| {
            let visited = visited.clone();
            async move {
                let mut visited_lock = visited.lock().await;
                if visited_lock.insert(url.clone()) {
                    Some(url)
                } else {
                    None
                }
            }
        })
        .take(limit)
        .for_each_concurrent(500, |url| {
            let pool = pool.clone();
            let progress = progress.clone();
            async move {
                let current = progress.fetch_add(1, Ordering::Relaxed) + 1;
                print_progress(current, total_links, &url);
                if let Err(e) = process_page(&url, &pool).await {
                    // eprintln!("Error processing {}: {}", url, e);
                }
            }
        })
        .await;

    let processed = progress.load(Ordering::Relaxed) + 1;
    println!("\nProcessed {} pages total", processed);

    Ok(())
}
async fn process_page(
    url: &str,
    pool: &sqlx::PgPool,
) -> Result<(Vec<String>, SeoAnalysis), Box<dyn std::error::Error>> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(3))
        .build()?;

    let response = client.get(url).send().await?;

    let response = match response.text().await {
        Ok(text) => text,
        Err(e) => {
            println!("Error decoding response for {}: {:?}", url, e);
            return Err(Box::new(e));
        }
    };
    let document = Html::parse_document(&response);

    let analysis = analyze_document(&document, url);
    let links = extract_links(&document, url);

    save_analysis(pool, &analysis).await?;
    Ok((links, analysis))
}

fn analyze_document(document: &Html, url: &str) -> SeoAnalysis {
    let mut analysis = SeoAnalysis {
        url: url.to_string(),
        language: String::new(),
        title: String::new(),
        meta_tags: Vec::new(),
        canonical_url: None,
        content_text: String::new(),
    };

    // ====== LANGUAGE EXTRACTION ======
    if let Ok(html_selector) = Selector::parse("html") {
        if let Some(html_element) = document.select(&html_selector).next() {
            if let Some(lang) = html_element.value().attr("lang") {
                analysis.language = lang.to_string();
            }
        }
    }

    // ====== TITLE EXTRACTION ======
    if let Ok(selector) = Selector::parse("title") {
        if let Some(title) = document.select(&selector).next() {
            analysis.title = title.text().collect();
        }
    }

    // ====== META TAGS EXTRACTION ======
    for selector in META_SELECTORS {
        if let Ok(sel) = Selector::parse(&format!("meta[{}='{}']", selector.attr, selector.value)) {
            for element in document.select(&sel) {
                if let Some(content) = element.value().attr("content") {
                    analysis.meta_tags.push(MetaTag {
                        name: selector.value.to_string(),
                        content: content.to_string(),
                    });
                }
            }
        }
    }

    // ====== CANONICAL URL EXTRACTION ======
    if let Ok(selector) = Selector::parse("link[rel='canonical']") {
        if let Some(link) = document.select(&selector).next() {
            analysis.canonical_url = link.value().attr("href").map(|s| s.to_string());
        }
    }

    // ====== CONTENT TEXT EXTRACTION ======
    let content_selector = Selector::parse("h1, h2, h3, h4, h5, h6, p, li").unwrap();
    for element in document.select(&content_selector) {
        let text = element.text().collect::<String>();
        analysis.content_text.push_str(&text);
        analysis.content_text.push('\n');
    }

    analysis
}

fn extract_links(document: &Html, base_url: &str) -> Vec<String> {
    let mut links = Vec::new();
    let base_url = match Url::parse(base_url) {
        Ok(u) => u,
        Err(_) => return links,
    };

    if let Ok(selector) = Selector::parse("a[href]") {
        for element in document.select(&selector) {
            if let Some(href) = element.value().attr("href") {
                if let Ok(mut parsed_url) = base_url.join(href) {
                    parsed_url.set_fragment(None);
                    if parsed_url.scheme() == "http" || parsed_url.scheme() == "https" {
                        links.push(parsed_url.to_string());
                    }
                }
            }
        }
    }

    links
}

fn print_progress(current: usize, total: usize, url: &str) {
    println!("[{}/{}] Processing {}", current, total, url);
}
