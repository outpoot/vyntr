mod db;
mod fingerprint;
mod meta_tags;
mod proxy;

use std::collections::HashSet;
use std::fs;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Instant;

use leaky_bucket::RateLimiter;
use meta_tags::META_SELECTORS;
use reqwest;
use scraper::{Html, Selector};
use tokio::sync::{Mutex, Semaphore};
use tokio_stream::wrappers::UnboundedReceiverStream;
use url::Url;

use crate::db::{create_db_pool, save_analyses_batch, MetaTag, SeoAnalysis};
use crate::fingerprint::RequestFingerprint;
use crate::proxy::ProxyManager;
use futures::stream::StreamExt;

const MAX_PAGES: usize = 1_000_000;
const CONCURRENCY: usize = 100000;
const DB_CONCURRENCY: usize = 20;
const BATCH_SIZE: usize = 5000;
const MAX_REQUESTS_PER_SECOND: usize = 1000;

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
    let pending_analyses = Arc::new(Mutex::new(Vec::new()));

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

    let start_time = Instant::now();

    let rate_limiter = Arc::new(
        RateLimiter::builder()
            .max(MAX_REQUESTS_PER_SECOND)
            .initial(MAX_REQUESTS_PER_SECOND)
            .refill(MAX_REQUESTS_PER_SECOND)
            .interval(std::time::Duration::from_secs(1))
            .build(),
    );

    let pause_flag: Arc<AtomicBool> = Arc::new(AtomicBool::new(false));

    let rx_stream = UnboundedReceiverStream::new(rx);

    rx_stream
        .for_each_concurrent(CONCURRENCY, |url: String| {
            let pool = pool.clone();
            let proxy_manager = proxy_manager.clone();
            let visited = Arc::clone(&visited);
            let pages_count = Arc::clone(&pages_count);
            let tx = Arc::clone(&tx);
            let db_semaphore = Arc::clone(&db_semaphore);
            let pending_analyses = Arc::clone(&pending_analyses);
            let rate_limiter = Arc::clone(&rate_limiter);
            let pause_flag = Arc::clone(&pause_flag);

            async move {
                let current_count = pages_count.fetch_add(1, Ordering::Relaxed) + 1;

                if current_count > MAX_PAGES {
                    return;
                }

                let result = process_page(&url, &proxy_manager, &rate_limiter).await;

                let should_pause = current_count % 3000 == 0;

                if should_pause {
                    println!("=============== Pausing for batch save ===============");
                    pause_flag.store(true, Ordering::SeqCst);

                    let mut analyses = pending_analyses.lock().await;
                    if !analyses.is_empty() {
                        let analyses_to_save: Vec<SeoAnalysis> = analyses.drain(..).collect();
                        let _permit = db_semaphore.acquire().await;
                        if let Err(e) = save_analyses_batch(&pool, &analyses_to_save).await {
                            eprintln!("Batch save error: {:?}", e);
                        }
                    }

                    pause_flag.store(false, Ordering::SeqCst);
                }

                match result {
                    Ok((child_links, analysis)) => {
                        let mut analyses = pending_analyses.lock().await;
                        analyses.push(analysis);

                        if analyses.len() >= BATCH_SIZE {
                            let analyses_to_save: Vec<SeoAnalysis> =
                                analyses.drain(..BATCH_SIZE).collect();
                            let _permit = db_semaphore.acquire().await;
                            if let Err(e) = save_analyses_batch(&pool, &analyses_to_save).await {
                                eprintln!("Batch save error: {:?}", e);
                            }
                        }

                        if !pause_flag.load(Ordering::SeqCst) {
                            for link in child_links {
                                let mut visited_lock = visited.lock().await;
                                if visited_lock.insert(link.clone()) {
                                    let _ = tx.send(link);
                                }
                            }
                        }
                    }
                    Err(e) => eprintln!(
                        "[{}/{}] Error processing {}: {:?}",
                        current_count, MAX_PAGES, url, e
                    ),
                }
            }
        })
        .await;

    let final_analyses = {
        let mut analyses = pending_analyses.lock().await;
        analyses.drain(..).collect::<Vec<_>>()
    };

    if !final_analyses.is_empty() {
        if let Err(e) = save_analyses_batch(&pool, &final_analyses).await {
            eprintln!("Error saving final batch: {:?}", e);
        }
    }

    let total_processed = pages_count.load(Ordering::Relaxed);
    let elapsed = start_time.elapsed();
    let requests_per_second = total_processed as f64 / elapsed.as_secs_f64();

    println!("\nProcessed {} pages total", total_processed);
    println!("Time elapsed: {:.2} seconds", elapsed.as_secs_f64());
    println!(
        "Average request rate: {:.2} requests/second",
        requests_per_second
    );

    Ok(())
}

async fn process_page(
    url: &str,
    proxy_manager: &ProxyManager,
    rate_limiter: &RateLimiter,
) -> Result<(Vec<String>, SeoAnalysis), Box<dyn std::error::Error>> {
    rate_limiter.acquire_one().await;

    let proxy = match proxy_manager.get_next_proxy() {
        Some(proxy) => proxy,
        _ => return Err("No proxy available".into()),
    };

    let fingerprint = RequestFingerprint::new(&proxy.ip, url);

    let mut client_builder = reqwest::Client::builder()
        .user_agent(&fingerprint.user_agent)
        .timeout(std::time::Duration::from_secs(30));

    if fingerprint.http_version == "HTTP/3" {
        client_builder = client_builder.tls_sni(true);
    } else if fingerprint.http_version == "HTTP/2" {
        client_builder = client_builder.http2_prior_knowledge();
    }

    if let Some(ref referrer) = fingerprint.referrer {
        let mut headers = reqwest::header::HeaderMap::new();
        headers.insert(reqwest::header::REFERER, referrer.parse()?);
        client_builder = client_builder.default_headers(headers);
    }

    client_builder = client_builder
        .proxy(reqwest::Proxy::all(&proxy.addr)?.basic_auth(&proxy.username, &proxy.password));

    let client = client_builder.build()?;
    let response = client.get(url).send().await?;
    let text = match response.text().await {
        Ok(text) => text,
        Err(e) => {
            return Err(Box::new(e));
        }
    };
    let document = Html::parse_document(&text);

    let analysis = analyze_document(&document, url);
    let links = extract_links(&document, url);

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
        let text = element
            .text()
            .collect::<String>()
            .split_whitespace()
            .collect::<Vec<&str>>()
            .join(" ");
        if !text.is_empty() {
            if !analysis.content_text.is_empty() {
                analysis.content_text.push(' ');
            }
            analysis.content_text.push_str(&text);
        }
        // println!("Content: {}", analysis.content_text);
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
