use std::fs;
use std::net::IpAddr;
use std::str::FromStr;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use reqwest::Client;

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
        let content = fs::read_to_string(proxy_file)?;
        let mut proxies = Vec::new();

        for line in content.lines() {
            let parts: Vec<&str> = line.split(':').collect();
            if parts.len() == 4 {
                let ip = match IpAddr::from_str(parts[0]) {
                    Ok(ip) => ip,
                    Err(_) => {
                        IpAddr::from_str("0.0.0.0").unwrap()
                    }
                };

                let proxy_url = format!("http://{}:{}", parts[0], parts[1]);
                let client = Client::builder()
                    .proxy(
                        reqwest::Proxy::all(&proxy_url)
                            .unwrap()
                            .basic_auth(parts[2], parts[3])
                    )
                    .timeout(std::time::Duration::from_secs(30))
                    .build()
                    .expect("Failed to build client");

                proxies.push(Proxy {
                    addr: proxy_url,
                    ip,
                    username: parts[2].to_string(),
                    password: parts[3].to_string(),
                    client,
                });
            }
        }

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
