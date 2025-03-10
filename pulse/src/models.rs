use serde::{Deserialize, Serialize};
use sqlx::FromRow;

#[derive(Debug, FromRow, Serialize, Deserialize)]
pub struct Site {
    pub id: i32,
    pub url: String,
    pub language: Option<String>,
    pub title: Option<String>,
    pub canonical_url: Option<String>,
    pub content_text: Option<String>,
}

#[derive(Debug, FromRow, Serialize, Deserialize)]
pub struct MetaTag {
    pub id: i32,
    pub analysis_id: i32,
    pub name: String,
    pub content: String,
}
