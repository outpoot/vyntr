use std::fs;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

#[derive(Clone)]
pub struct ProxyManager {
    proxies: Arc<Vec<String>>,
    current: Arc<AtomicUsize>,
}

impl ProxyManager {
    pub fn new(proxy_file: &str) -> std::io::Result<Self> {
        let content = fs::read_to_string(proxy_file)?;
        let proxies: Vec<String> = content.lines().map(|s| s.to_string()).collect();
        
        Ok(ProxyManager {
            proxies: Arc::new(proxies),
            current: Arc::new(AtomicUsize::new(0)),
        })
    }

    pub fn get_next_proxy(&self) -> Option<(String, String, String)> {
        if self.proxies.is_empty() {
            return None;
        }

        let current = self.current.fetch_add(1, Ordering::Relaxed) % self.proxies.len();
        let proxy = &self.proxies[current];
        
        let parts: Vec<&str> = proxy.split(':').collect();
        if parts.len() == 4 {
            Some((
                format!("http://{}:{}", parts[0], parts[1]),
                parts[2].to_string(),
                parts[3].to_string(),
            ))
        } else {
            None
        }
    }
}
