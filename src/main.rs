mod db;
mod meta_tags;
mod proxy;

use std::collections::HashSet;
use std::fs;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use meta_tags::META_SELECTORS;
use reqwest;
use scraper::{Html, Selector};
use tokio::sync::{Mutex, Semaphore};
use tokio_stream::wrappers::UnboundedReceiverStream;
use url::Url;

use crate::db::{create_db_pool, save_analysis, MetaTag, SeoAnalysis};
use crate::proxy::ProxyManager;
use futures::stream::StreamExt;

const MAX_PAGES: usize = 100000;
const CONCURRENCY: usize = 1000;
const DB_CONCURRENCY: usize = 20;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let sites_file = fs::read_to_string("data/sites.txt")?;
    let seeds: Vec<String> = sites_file
        .lines()
        .map(|line| line.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();

    let proxy_manager = ProxyManager::new("data/proxies.txt")?;
    let pool = create_db_pool().await?;
    let visited = Arc::new(Mutex::new(HashSet::new()));
    let pages_count = Arc::new(AtomicUsize::new(0));
    let db_semaphore = Arc::new(Semaphore::new(DB_CONCURRENCY));

    let (tx, rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    let tx = Arc::new(tx);

    {
        let mut visited_lock = visited.lock().await;
        for seed in seeds {
            if visited_lock.insert(seed.clone()) {
                tx.send(seed).expect("failed to enqueue seed URL");
            }
        }
    }

    println!(
        "Starting concurrent crawl with a page limit of {} pages...",
        MAX_PAGES
    );

    let rx_stream = UnboundedReceiverStream::new(rx);

    rx_stream
        .for_each_concurrent(CONCURRENCY, |url: String| {
            let pool = pool.clone();
            let proxy_manager = proxy_manager.clone();
            let visited = Arc::clone(&visited);
            let pages_count = Arc::clone(&pages_count);
            let tx = Arc::clone(&tx);
            let db_semaphore = Arc::clone(&db_semaphore);

            async move {
                let current_count = pages_count.fetch_add(1, Ordering::Relaxed) + 1;

                if current_count > MAX_PAGES {
                    return;
                }
                print_progress(current_count, MAX_PAGES, &url);

                match process_page(&url, &pool, &proxy_manager, &db_semaphore).await {
                    Ok((child_links, _analysis)) => {
                        for link in child_links {
                            let mut visited_lock = visited.lock().await;
                            if visited_lock.insert(link.clone()) {
                                drop(visited_lock);
                                if tx.send(link).is_err() {
                                    break;
                                }
                            }
                        }
                    }
                    Err(e) => {
                        eprintln!("Error processing {}: {:?}", url, e);
                    }
                }
            }
        })
        .await;

    let total_processed = pages_count.load(Ordering::Relaxed);
    println!("\nProcessed {} pages total", total_processed);

    Ok(())
}

async fn process_page(
    url: &str,
    pool: &sqlx::PgPool,
    proxy_manager: &ProxyManager,
    db_semaphore: &Semaphore,
) -> Result<(Vec<String>, SeoAnalysis), Box<dyn std::error::Error>> {
    let mut client_builder = reqwest::Client::builder().timeout(std::time::Duration::from_secs(30));

    if let Some((proxy, username, password)) = proxy_manager.get_next_proxy() {
        client_builder =
            client_builder.proxy(reqwest::Proxy::all(&proxy)?.basic_auth(&username, &password));
    }

    let client = client_builder.build()?;
    let response = client.get(url).send().await?;
    let text = match response.text().await {
        Ok(text) => text,
        Err(e) => {
            println!("Error decoding response for {}: {:?}", url, e);
            return Err(Box::new(e));
        }
    };
    let document = Html::parse_document(&text);

    let analysis = analyze_document(&document, url);
    let links = extract_links(&document, url);

    let _permit = db_semaphore.acquire().await.unwrap();
    match save_analysis(pool, &analysis).await {
        Ok(_) => (),
        Err(e) => {
            println!("Database error for {}: {:?}", url, e);
        }
    }

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
