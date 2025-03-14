mod crawler;
mod db;
mod fingerprint;
mod html_parser;
mod logger;
mod metrics;
mod network;
mod proxy;
mod utils;

use std::collections::HashSet;
use std::env;
use std::fs;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};

use fingerprint::RequestFingerprint;
use futures::StreamExt;
use rand::rngs::StdRng;
use rand::seq::SliceRandom;
use rand::SeedableRng;
use tokio::sync::{Mutex, Semaphore};
use tokio_stream::wrappers::UnboundedReceiverStream;

use crate::crawler::{DomainQueues, extract_domain};
use crate::metrics::Metrics;
use crate::utils::{normalize_url, print_request_status};
use crate::logger::AsyncLogger;
use crate::proxy::ProxyManager;
use crate::db::{create_db_pool, save_analyses_batch, SeoAnalysis};
use crate::network::try_tunnel_request;

const MAX_PAGES: usize = 200_000_000;
const CONCURRENCY: usize = 5_000;
const DB_CONCURRENCY: usize = 20;
const BATCH_SIZE: usize = 2_000;
const MAX_TUNNEL_RETRIES: usize = 2;
const LOG_BUFFER_SIZE: usize = 10000;
const INACTIVITY_TIMEOUT: Duration = Duration::from_secs(60);

lazy_static::lazy_static! {
    static ref PROXY_TUNNEL_URL: String = env::var("PROXY_TUNNEL_URL")
        .expect("PROXY_TUNNEL_URL must be set in environment");
}

#[macro_export]
#[cfg(debug_assertions)]
macro_rules! debug_only {
    ($($stmt:stmt)*) => {
        $($stmt)*
    };
}

#[macro_export]
#[cfg(not(debug_assertions))]
macro_rules! debug_only {
    ($($stmt:stmt)*) => {
        // ... skidibvi
    };
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let logger = AsyncLogger::new(LOG_BUFFER_SIZE)?;

    tokio::spawn({
        let logger = logger.clone();
        async move {
            let mut interval = tokio::time::interval(Duration::from_secs(5));
            loop {
                interval.tick().await;
                let _ = logger.lock().await.flush();
            }
        }
    });

    let metrics = Arc::new(Metrics::default());
    let start_time = Instant::now();
    tokio::spawn({
        let logger = logger.clone();
        let metrics = metrics.clone();
        async move {
            let mut interval = tokio::time::interval(Duration::from_secs(5));
            loop {
                interval.tick().await;
                let elapsed = start_time.elapsed().as_secs_f64();
                let t_p_rate = if metrics.proxy.load(Ordering::Relaxed) > 0 {
                    metrics.tunnel.load(Ordering::Relaxed) as f64
                        / metrics.proxy.load(Ordering::Relaxed) as f64
                } else {
                    0.0
                };

                let metrics_str = format!(
                    "[Metrics] Total: {}, Success: {}, Tunnel: {}, Proxy: {}, T-P Rate: {:.2}, Failed: {}, Left: {}, Rate: {:.2} req/sec",
                    metrics.total.load(Ordering::Relaxed),
                    metrics.success.load(Ordering::Relaxed),
                    metrics.tunnel.load(Ordering::Relaxed),
                    metrics.proxy.load(Ordering::Relaxed),
                    t_p_rate,
                    metrics.failed.load(Ordering::Relaxed),
                    metrics.total_left.load(Ordering::Relaxed),
                    metrics.total.load(Ordering::Relaxed) as f64 / elapsed
                );
                let mut log = logger.lock().await;
                let _ = log.add_entry(metrics_str);
                let _ = log.flush();
            }
        }
    });

    // inactivity checker task
    tokio::spawn({
        let metrics = metrics.clone();

        debug_only! { let logger = logger.clone() }
        async move {
            let mut interval = tokio::time::interval(Duration::from_secs(5));
            loop {
                interval.tick().await;
                let last_activity = *metrics.last_activity.lock().await;
                let idle_time = last_activity.elapsed();

                if idle_time >= INACTIVITY_TIMEOUT {
                    debug_only! {
                        let mut log = logger.lock().await
                        let _ = log.add_entry(format!(
                           "No activity for {}s, shutting down...",
                           idle_time.as_secs()
                       ))
                        let _ = log.flush()
                        std::process::exit(0)
                    }
                }
            }
        }
    });

    let base_dir = std::env::current_dir()?;

    let sites_file = fs::read_to_string(base_dir.join("data/sites.txt").to_str().unwrap())?;
    let seeds: Vec<String> = sites_file
        .lines()
        .map(|line| line.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();

    let proxy_manager = ProxyManager::new(base_dir.join("data/proxies.txt").to_str().unwrap())?;
    let pool = create_db_pool().await?;
    let visited = Arc::new(Mutex::new(HashSet::new()));
    let pages_count = Arc::new(AtomicUsize::new(0));
    let db_semaphore = Arc::new(Semaphore::new(DB_CONCURRENCY));
    let pending_analyses = Arc::new(Mutex::new(Vec::new()));

    let (discovered_tx, mut discovered_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    let (processing_tx, processing_rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    let discovered_tx = Arc::new(discovered_tx);
    let processing_tx = Arc::new(processing_tx);

    let batch_task = tokio::spawn({
        let processing_tx = processing_tx.clone();
        async move {
            let mut domain_queues = DomainQueues::new();
            let mut rng = StdRng::from_os_rng();
            let mut interval = tokio::time::interval(Duration::from_secs(1));
            const MAX_PER_DOMAIN: usize = 5;

            loop {
                tokio::select! {
                    Some(link) = discovered_rx.recv() => {
                        let normalized_url = match normalize_url(&link) {
                            Ok(url) => url,
                            Err(_) => continue,
                        };
                        let domain = match extract_domain(&normalized_url) {
                            Ok(d) => d,
                            Err(_) => continue,
                        };
                        domain_queues.add(domain, normalized_url);

                        if domain_queues.total >= BATCH_SIZE {
                            let batch = domain_queues.collect_batch(MAX_PER_DOMAIN);
                            let mut shuffled = batch;
                            shuffled.shuffle(&mut rng);
                            for url in shuffled {
                                if processing_tx.send(url).is_err() {
                                    return;
                                }
                            }
                        }
                    },
                    _ = interval.tick() => {
                        if domain_queues.total > 0 {
                            let batch = domain_queues.collect_batch(MAX_PER_DOMAIN);
                            let mut shuffled = batch;
                            shuffled.shuffle(&mut rng);
                            for url in shuffled {
                                let _ = processing_tx.send(url);
                            }
                        }
                    }
                }
            }
        }
    });

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

    UnboundedReceiverStream::new(processing_rx)
        .for_each_concurrent(CONCURRENCY, |url| {
            let pool = pool.clone();
            let proxy_manager = proxy_manager.clone();
            let visited = visited.clone();
            let pages_count = pages_count.clone();
            let discovered_tx = discovered_tx.clone();
            let pending_analyses = pending_analyses.clone();
            let logger = logger.clone();
            let metrics = metrics.clone();

            {
                let db_semaphore = db_semaphore.clone();
                async move {
                    let current_count = pages_count.fetch_add(1, Ordering::Relaxed) + 1;
                    if current_count > MAX_PAGES {
                        return;
                    }

                    match process_page(&url, &proxy_manager, &metrics).await {
                        Ok((child_links, analysis)) => {
                            // decrease total_left since we processed one
                            metrics.total_left.fetch_sub(1, Ordering::Relaxed);
                            
                            debug_only! { println!("[DEBUG] Extracted {} links from {}", child_links.len(), url) }

                            let mut analyses = pending_analyses.lock().await;
                            analyses.push(analysis);

                            if analyses.len() >= BATCH_SIZE {
                                let analyses_to_save: Vec<SeoAnalysis> =
                                    analyses.drain(..BATCH_SIZE).collect();
                                let pool_clone = pool.clone();
                                let _permit = db_semaphore.acquire().await;
                                tokio::spawn(async move {
                                    if let Err(e) =
                                        save_analyses_batch(&pool_clone, &analyses_to_save).await
                                    {
                                        eprintln!("Batch save error: {:?}", e);
                                    }
                                });
                            }

                            for link in child_links {
                                let mut visited_lock = visited.lock().await;
                                if visited_lock.insert(link.clone()) {
                                    // increase total_left for each new URL discovered
                                    metrics.total_left.fetch_add(1, Ordering::Relaxed);
                                    let _ = discovered_tx.send(link);
                                }
                            }
                        }
                        Err(e) => {
                            debug_only! { eprintln!("Error processing {}: {:?}", url, e) }
                        }
                    }

                    if current_count % BATCH_SIZE == 0 {
                        let mut logger = logger.lock().await;
                        let _ = logger.add_entry(format!(
                            "======== Batch {} complete ========",
                            current_count
                        ));
                        let _ = logger.flush();
                    }
                }
            }
        })
        .await;

    batch_task.await?;

    let final_analyses = pending_analyses.lock().await.drain(..).collect::<Vec<_>>();
    if !final_analyses.is_empty() {
        save_analyses_batch(&pool, &final_analyses).await?;
    }

    logger.lock().await.flush()?;

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
    metrics: &Arc<Metrics>,
) -> Result<(Vec<String>, SeoAnalysis), Box<dyn std::error::Error>> {
    *metrics.last_activity.lock().await = Instant::now();

    let base_url = normalize_url(url)?;

    let mut tunnel_retries = 0;
    let text = loop {
        match try_tunnel_request(url, metrics).await {
            Ok(text) => {
                *metrics.last_activity.lock().await = Instant::now();
                break text;
            }
            Err(_) => {
                tunnel_retries += 1;
                if tunnel_retries < MAX_TUNNEL_RETRIES {
                    print_request_status(
                        url,
                        "TUNNEL",
                        "RETRY",
                        Some(&format!(
                            "attempt {}/{}",
                            tunnel_retries, MAX_TUNNEL_RETRIES
                        )),
                    );
                    continue;
                }

                metrics.proxy.fetch_add(1, Ordering::Relaxed);

                let proxy = proxy_manager.get_next_proxy().ok_or("No proxy available")?;
                let fp = RequestFingerprint::new(&proxy.ip, url);

                match proxy
                    .client
                    .get(&base_url)
                    .header("User-Agent", &fp.user_agent)
                    .header("Referer", fp.referrer.as_deref().unwrap_or(&base_url))
                    .send()
                    .await
                {
                    Ok(response) => {
                        let status = response.status();
                        let text = response.text().await?;
                        if status == 403 || text.contains("403 Forbidden") {
                            metrics.failed.fetch_add(1, Ordering::Relaxed);
                            print_request_status(url, "PROXY", "FAILED", Some("403 Forbidden"));
                            return Err("403 Forbidden".into());
                        }
                        print_request_status(url, "PROXY", "SUCCESS", None);
                        break text;
                    }
                    Err(e) => {
                        metrics.failed.fetch_add(1, Ordering::Relaxed);
                        print_request_status(url, "PROXY", "FAILED", Some(&e.to_string()));
                        return Err(e.into());
                    }
                }
            }
        }
    };

    let parsed = html_parser::parse_html(text.as_bytes(), &base_url)?;

    let analysis = SeoAnalysis {
        url: base_url,
        language: parsed.language,
        title: parsed.title,
        meta_tags: parsed.meta_tags,
        canonical_url: parsed.canonical_url,
        content_text: parsed.content_text,
    };

    metrics.success.fetch_add(1, Ordering::Relaxed);
    Ok((parsed.links, analysis))
}
