use std::fs;
use std::net::IpAddr;
use std::str::FromStr;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

#[derive(Clone)]
pub struct Proxy {
    pub addr: String,
    pub ip: IpAddr,
    pub username: String,
    pub password: String,
}

#[derive(Clone)]
pub struct ProxyManager {
    proxies: Arc<Vec<Proxy>>,
    current: Arc<AtomicUsize>,
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

                proxies.push(Proxy {
                    addr: format!("http://{}:{}", parts[0], parts[1]),
                    ip,
                    username: parts[2].to_string(),
                    password: parts[3].to_string(),
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
