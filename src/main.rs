mod db;
mod meta_tags;

use std::collections::HashSet;
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

    save_analysis(&pool, &main_analysis).await?;
    println!("Main page processed: {}", initial_url);

    let max_pages = 700;
    let mut processed = 1;
    let mut progress = 0;
    let total_links = main_links.len().min(max_pages - 1);

    println!("Processing {} child pages...", total_links);

    for url in main_links.iter() {
        if processed >= max_pages {
            break;
        }

        let mut visited_lock = visited.lock().await;
        if visited_lock.insert(url.clone()) {
            drop(visited_lock);

            progress += 1;
            print_progress(progress, total_links, url);

            match process_page(url, &pool).await {
                Ok(_) => processed += 1,
                Err(e) => eprintln!("Error processing {}: {}", url, e),
            }
        }
    }

    println!("\nProcessed {} pages total", processed);
    Ok(())
}

async fn process_page(
    url: &str,
    pool: &sqlx::PgPool,
) -> Result<(Vec<String>, SeoAnalysis), Box<dyn std::error::Error>> {
    let response = reqwest::get(url).await?.text().await?;
    let document = Html::parse_document(&response);

    let a_selector = Selector::parse("a").unwrap();
    let a_tags_count = document.select(&a_selector).count();
    println!("Total <a> tags on {}: {}", url, a_tags_count);

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
