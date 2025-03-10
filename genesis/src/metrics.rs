use std::sync::atomic::AtomicUsize;
use std::sync::Arc;
use std::time::Instant;
use tokio::sync::Mutex;

pub struct Metrics {
    pub total: AtomicUsize,
    pub tunnel: AtomicUsize,
    pub proxy: AtomicUsize,
    pub failed: AtomicUsize,
    pub success: AtomicUsize,
    pub last_activity: Arc<Mutex<Instant>>,
}

impl Default for Metrics {
    fn default() -> Self {
        Metrics {
            total: AtomicUsize::new(0),
            tunnel: AtomicUsize::new(0),
            proxy: AtomicUsize::new(0),
            failed: AtomicUsize::new(0),
            success: AtomicUsize::new(0),
            last_activity: Arc::new(Mutex::new(Instant::now())),
        }
    }
}
