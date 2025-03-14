use chrono::Local;
use rand::Rng;
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::sync::Arc;
use tokio::sync::Mutex;

const ANIME_NAMES: &[&str] = &[
    "yuki", "sakura", "mikasa", "miku", "asuka", "rei", "misato", "hinata", "tohru", "zero", "rem",
    "ram", "emilia", "aqua", "nami", "lucy", "erza", "asuna", "misaka", "saber", "rin", "mai",
    "nezuko", "ichigo",
];

pub struct AsyncLogger {
    buffer: Vec<String>,
    file: File,
    buffer_size: usize,
}

impl AsyncLogger {
    pub fn new(buffer_size: usize) -> std::io::Result<Arc<Mutex<Self>>> {
        let mut rng = rand::rng();
        let idx = rng.random_range(0..ANIME_NAMES.len());
        let name = ANIME_NAMES[idx];

        let base_dir = std::env::current_dir()?;
        let log_dir = base_dir.join("logs");
        std::fs::create_dir_all(&log_dir)?;

        let filename = log_dir.join(format!("crawler-{}.log", name));

        println!("Creating log file: {}", filename.display());

        let file = OpenOptions::new()
            .create(true)
            .read(true)
            .write(true)
            .append(true)
            .open(&filename)?;

        Ok(Arc::new(Mutex::new(Self {
            buffer: Vec::with_capacity(buffer_size),
            file,
            buffer_size,
        })))
    }

    pub fn add_entry(&mut self, message: String) -> std::io::Result<()> {
        self.buffer.push(format!(
            "[{}] {}\n",
            Local::now().format("%Y-%m-%d %H:%M:%S"),
            message
        ));

        if self.buffer.len() >= self.buffer_size {
            self.flush()?;
        }
        Ok(())
    }

    pub fn flush(&mut self) -> std::io::Result<()> {
        if !self.buffer.is_empty() {
            self.file.write_all(self.buffer.concat().as_bytes())?;
            self.file.flush()?;
            self.buffer.clear();
        }
        Ok(())
    }
}
