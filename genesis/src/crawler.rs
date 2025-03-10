use std::collections::{HashMap, VecDeque};
use url::Url;

pub struct DomainQueues {
    queues: HashMap<String, VecDeque<String>>,
    order: Vec<String>,
    pub total: usize,
}

impl DomainQueues {
    pub fn new() -> Self {
        Self {
            queues: HashMap::new(),
            order: Vec::new(),
            total: 0,
        }
    }

    pub fn add(&mut self, domain: String, url: String) {
        let queue = self.queues.entry(domain.clone()).or_insert_with(|| {
            self.order.push(domain);
            VecDeque::new()
        });
        queue.push_back(url);
        self.total += 1;
    }

    pub fn collect_batch(&mut self, max_per_domain: usize) -> Vec<String> {
        let mut batch = Vec::new();

        for domain in &self.order {
            if let Some(queue) = self.queues.get_mut(domain) {
                let take = std::cmp::min(queue.len(), max_per_domain);
                for _ in 0..take {
                    if let Some(url) = queue.pop_front() {
                        batch.push(url);
                        self.total -= 1;
                    }
                }
            }
        }

        if !self.order.is_empty() {
            self.order.rotate_left(1);
        }

        batch
    }
}

pub fn extract_domain(url: &str) -> Result<String, Box<dyn std::error::Error>> {
    let parsed = Url::parse(url)?;
    let domain = parsed.host_str().ok_or("URL has no host")?.to_string();
    Ok(domain)
}
