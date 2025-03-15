use reqwest::Client;
use std::fs;
use std::net::IpAddr;
use std::str::FromStr;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

#[derive(Clone)]
#[allow(dead_code)]
pub struct Proxy {
    pub addr: String,
    pub ip: IpAddr,
    pub username: String,
    pub password: String,
    pub client: Client,
}

#[derive(Clone)]
pub struct ProxyManager {
    pub proxies: Arc<Vec<Proxy>>,
    current: Arc<AtomicUsize>,
}

lazy_static::lazy_static! {
    pub static ref TUNNEL_CLIENT: Client = Client::builder()
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .unwrap();
}

impl ProxyManager {
    pub fn new(proxy_file: &str) -> std::io::Result<Self> {
        println!("Reading proxy file: {}", proxy_file); // debug added
        let content = fs::read_to_string(proxy_file)?;
        let lines: Vec<&str> = content.lines().collect();
        println!("Proxy file has {} lines", lines.len()); // debug added

        let mut proxies = Vec::new();

        for (i, line) in lines.into_iter().enumerate() {
            if i % 100 == 0 {
                // Increased frequency of progress updates
                println!("Processed {} proxy lines", i); // debug progress
            }
            let parts: Vec<&str> = line.split(':').collect();
            if parts.len() == 4 {
                println!(
                    "Initializing proxy {}: {}:{}@{}:{}",
                    i, parts[2], parts[3], parts[0], parts[1]
                );

                let ip = match IpAddr::from_str(parts[0]) {
                    Ok(ip) => ip,
                    Err(e) => {
                        println!("Warning: Invalid IP {} at line {}: {}", parts[0], i, e);
                        IpAddr::from_str("0.0.0.0").unwrap()
                    }
                };

                let proxy_url = format!("http://{}:{}", parts[0], parts[1]);
                println!("Building client for proxy {}: {}", i, proxy_url);

                match Client::builder()
                    .proxy(
                        reqwest::Proxy::all(&proxy_url)
                            .unwrap()
                            .basic_auth(parts[2], parts[3]),
                    )
                    .timeout(std::time::Duration::from_secs(30))
                    .build()
                {
                    Ok(client) => {
                        println!("Successfully built client for proxy {}", i);
                        proxies.push(Proxy {
                            addr: proxy_url,
                            ip,
                            username: parts[2].to_string(),
                            password: parts[3].to_string(),
                            client,
                        });
                    }
                    Err(e) => {
                        println!("Failed to build client for proxy {}: {}", i, e);
                    }
                }
            } else {
                println!("Warning: Invalid proxy format at line {}: {}", i, line);
            }
        }
        println!("Successfully loaded {} proxies", proxies.len());
        Ok(ProxyManager {
            proxies: Arc::new(proxies),
            current: Arc::new(AtomicUsize::new(0)),
        })
    }

    pub fn get_next_proxy(&self) -> Option<Proxy> {
        if self.proxies.is_empty() {
            return None;
        }

        let current = self.current.fetch_add(1, Ordering::Relaxed) % self.proxies.len();
        Some(self.proxies[current].clone())
    }
}
