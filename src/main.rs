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
use rand::rngs::StdRng;
use rand::seq::SliceRandom;
use rand::SeedableRng;
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
const CONCURRENCY: usize = 100_000;
const DB_CONCURRENCY: usize = 20;
const BATCH_SIZE: usize = 2_000;
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

    // Channel setup
    let (discovered_tx, mut discovered_rx) = tokio::sync::mpsc::unbounded_channel();
    let (processing_tx, processing_rx) = tokio::sync::mpsc::unbounded_channel();
    let discovered_tx = Arc::new(discovered_tx);
    let processing_tx = Arc::new(processing_tx);

    // Batch processing task
    let batch_task = tokio::spawn({
        let processing_tx = processing_tx.clone();
        async move {
            let mut buffer = Vec::with_capacity(BATCH_SIZE);
            let mut rng = StdRng::from_os_rng();
            let mut interval = tokio::time::interval(std::time::Duration::from_secs(1));

            loop {
                tokio::select! {
                    // Receive new URLs
                    Some(link) = discovered_rx.recv() => {
                        buffer.push(link);

                        if buffer.len() >= BATCH_SIZE {
                            buffer.shuffle(&mut rng);
                            for link in buffer.drain(..) {
                                if processing_tx.send(link).is_err() {
                                    return;
                                }
                            }
                        }
                    },
                    // Flush periodically
                    _ = interval.tick() => {
                        if !buffer.is_empty() {
                            buffer.shuffle(&mut rng);
                            for link in buffer.drain(..) {
                                let _ = processing_tx.send(link);
                            }
                        }
                    }
                }
            }
        }
    });

    // Seed initialization
    {
        let mut visited_lock = visited.lock().await;
        for seed in seeds {
            if visited_lock.insert(seed.clone()) {
                discovered_tx
                    .send(seed)
                    .expect("Failed to enqueue seed URL");
            }
        }
    }

    println!("Starting crawl with limit of {} pages...", MAX_PAGES);

    let start_time = Instant::now();
    let rate_limiter = Arc::new(
        RateLimiter::builder()
            .max(MAX_REQUESTS_PER_SECOND)
            .initial(MAX_REQUESTS_PER_SECOND)
            .refill(MAX_REQUESTS_PER_SECOND)
            .interval(std::time::Duration::from_secs(1))
            .build(),
    );

    let pause_flag = Arc::new(AtomicBool::new(false));

    UnboundedReceiverStream::new(processing_rx)
        .for_each_concurrent(CONCURRENCY, |url| {
            let pool = pool.clone();
            let proxy_manager = proxy_manager.clone();
            let visited = visited.clone();
            let pages_count = pages_count.clone();
            let discovered_tx = discovered_tx.clone();
            let pending_analyses = pending_analyses.clone();
            let rate_limiter = rate_limiter.clone();
            let pause_flag = pause_flag.clone();

            {
                let db_semaphore = db_semaphore.clone();
                async move {
                    let current_count = pages_count.fetch_add(1, Ordering::Relaxed) + 1;
                    if current_count > MAX_PAGES {
                        return;
                    }

                    println!("[{}/{}] URL: {}", current_count, MAX_PAGES, url);

                    match process_page(&url, &proxy_manager, &rate_limiter).await {
                        Ok((child_links, analysis)) => {
                            // Store analysis
                            let mut analyses = pending_analyses.lock().await;
                            analyses.push(analysis);

                            // Batch save logic
                            if analyses.len() >= BATCH_SIZE {
                                let analyses_to_save: Vec<SeoAnalysis> =
                                    analyses.drain(..BATCH_SIZE).collect();
                                let _permit = db_semaphore.acquire().await;
                                if let Err(e) = save_analyses_batch(&pool, &analyses_to_save).await
                                {
                                    eprintln!("Batch save error: {:?}", e);
                                }
                            }

                            // Add new links to discovery queue
                            if !pause_flag.load(Ordering::SeqCst) {
                                for link in child_links {
                                    let mut visited_lock = visited.lock().await;
                                    if visited_lock.insert(link.clone()) {
                                        let _ = discovered_tx.send(link);
                                    }
                                }
                            }
                        }
                        Err(e) => {
                            eprintln!("Error processing {}: {:?}", url, e);
                        }
                    }

                    // Periodic pause and save
                    if current_count % 3000 == 0 {
                        println!("======== Pausing for batch save ========");
                        pause_flag.store(true, Ordering::SeqCst);

                        let mut analyses = pending_analyses.lock().await;
                        if !analyses.is_empty() {
                            let analyses_to_save: Vec<SeoAnalysis> = analyses.drain(..).collect();
                            let _permit = db_semaphore.acquire().await;
                            if let Err(e) = save_analyses_batch(&pool, &analyses_to_save).await {
                                eprintln!("Final batch save error: {:?}", e);
                            }
                        }

                        pause_flag.store(false, Ordering::SeqCst);
                    }
                }
            }
        })
        .await;

    batch_task.await?;

    // Final save
    let final_analyses = pending_analyses.lock().await.drain(..).collect::<Vec<_>>();
    if !final_analyses.is_empty() {
        save_analyses_batch(&pool, &final_analyses).await?;
    }

    // Statistics
    let total_processed = pages_count.load(Ordering::Relaxed);
    let elapsed = start_time.elapsed();
    println!(
        "\nProcessed {} pages in {:.2} seconds ({:.2}/sec)",
        total_processed,
        elapsed.as_secs_f64(),
        total_processed as f64 / elapsed.as_secs_f64()
    );

    Ok(())
}

async fn process_page(
    url: &str,
    proxy_manager: &ProxyManager,
    rate_limiter: &RateLimiter,
) -> Result<(Vec<String>, SeoAnalysis), Box<dyn std::error::Error>> {
    rate_limiter.acquire_one().await;

    let proxy = proxy_manager.get_next_proxy().ok_or("No proxy available")?;
    let fp = RequestFingerprint::new(&proxy.ip, url);

    let client = reqwest::Client::builder()
        .user_agent(&fp.user_agent)
        .referer(fp.referrer.is_some())
        .proxy(reqwest::Proxy::all(&proxy.addr)?.basic_auth(&proxy.username, &proxy.password))
        .timeout(std::time::Duration::from_secs(30))
        .build()?;

    let response = client.get(url).send().await?;
    let text = response.text().await?;
    let document = Html::parse_document(&text);

    Ok((
        extract_links(&document, url),
        analyze_document(&document, url),
    ))
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

fn is_ignored_file_type(url: &str) -> bool {
    let extensions = [
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".pdf", ".doc", ".docx", ".xls",
        ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".tar", ".gz", ".mp3", ".mp4", ".avi", ".mov",
    ];

    let url_lower = url.to_lowercase();
    extensions.iter().any(|&ext| url_lower.ends_with(ext))
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
                    if (parsed_url.scheme() == "http" || parsed_url.scheme() == "https")
                        && !is_ignored_file_type(&parsed_url.path())
                    {
                        links.push(parsed_url.to_string());
                    }
                }
            }
        }
    }

    links
}
