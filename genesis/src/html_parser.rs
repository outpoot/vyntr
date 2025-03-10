use crate::db::MetaTag;
use lol_html::{element, text, HtmlRewriter, Settings};
use std::collections::HashSet;
use std::sync::Arc;
use std::sync::Mutex;
use url::Url;

pub struct ParsedHtml {
    pub links: Vec<String>,
    pub language: String,
    pub title: String,
    pub meta_tags: Vec<MetaTag>,
    pub canonical_url: Option<String>,
    pub content_text: String,
}

pub fn parse_html(html: &[u8], base_url: &str) -> Result<ParsedHtml, Box<dyn std::error::Error>> {
    let mut result = ParsedHtml {
        links: Vec::new(),
        language: String::new(),
        title: String::new(),
        meta_tags: Vec::new(),
        canonical_url: None,
        content_text: String::new(),
    };

    let base_url = Url::parse(base_url)?;
    let links = Arc::new(Mutex::new(HashSet::new()));
    let title = Arc::new(Mutex::new(String::new()));
    let content = Arc::new(Mutex::new(String::new()));

    let links_clone = links.clone();
    let title_clone = title.clone();
    let content_clone = content.clone();

    let mut rewriter = HtmlRewriter::new(
        Settings {
            element_content_handlers: vec![
                element!("a[href]", move |el| {
                    if let Some(href) = el.get_attribute("href") {
                        if let Ok(mut url) = base_url.join(&href) {
                            url.set_fragment(None);
                            if (url.scheme() == "http" || url.scheme() == "https")
                                && !is_ignored_file_type(url.path())
                            {
                                links_clone.lock().unwrap().insert(url.to_string());
                            }
                        }
                    }
                    Ok(())
                }),
                element!("html", |el| {
                    if let Some(lang) = el.get_attribute("lang") {
                        result.language = lang;
                    }
                    Ok(())
                }),
                element!("title", |_| Ok(())),
                text!("title", move |t| {
                    title_clone.lock().unwrap().push_str(t.as_str());
                    Ok(())
                }),
                element!("meta[name], meta[property]", |el| {
                    let name = el
                        .get_attribute("name")
                        .or_else(|| el.get_attribute("property"))
                        .unwrap_or_default();
                    if let Some(content) = el.get_attribute("content") {
                        result.meta_tags.push(MetaTag { name, content });
                    }
                    Ok(())
                }),
                element!("link[rel='canonical']", |el| {
                    if let Some(href) = el.get_attribute("href") {
                        result.canonical_url = Some(href);
                    }
                    Ok(())
                }),
                element!("h1, h2, h3, h4, h5, h6, p, li", |_| Ok(())),
                text!("h1, h2, h3, h4, h5, h6, p, li", move |t| {
                    let mut content = content_clone.lock().unwrap();
                    if !content.is_empty() {
                        content.push(' ');
                    }
                    content.push_str(t.as_str().trim());
                    Ok(())
                }),
            ],
            ..Settings::default()
        },
        |_: &[u8]| {},
    );

    rewriter.write(html)?;
    rewriter.end()?;

    result.links = links.lock().unwrap().iter().cloned().collect();
    result.title = title.lock().unwrap().clone();
    result.content_text = content.lock().unwrap().clone();

    Ok(result)
}

fn is_ignored_file_type(path: &str) -> bool {
    let extensions = [
        // Media files
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff", ".pdf", ".epub",
        ".mobi", // Documents
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf", ".csv",
        // Archives
        ".zip", ".rar", ".tar", ".gz", ".7z", ".bz2", ".iso", // Audio/Video
        ".mp3", ".mp4", ".wav", ".avi", ".mov", ".wmv", ".flv", ".ogg", ".ogv", ".webm", ".m4a",
        ".m4v", ".3gp", // Other
        ".exe", ".dmg", ".pkg", ".deb", ".rpm", ".apk", ".ipa",
    ];

    let blocked_patterns = [
        "/download/",
        "/compress/",
        "/stream/",
        "/pdf/",
        "/static/",
        "/content/uploads/",
        "arxiv.org/pdf/",
        "arxiv.org/ps/",
        "arxiv.org/src/",
        ".pdf?",
        "/lectures/",
        "/video/",
        "/audio/",
        "/rss",
        ".rss",
        "/feed",
        "/atom",
    ];

    let path_lower = path.to_lowercase();

    if extensions.iter().any(|&ext| path_lower.ends_with(ext)) {
        return true;
    }

    if blocked_patterns
        .iter()
        .any(|&pattern| path_lower.contains(pattern))
    {
        return true;
    }

    if path_lower.contains("/pdf/")
        && path_lower
            .split('/')
            .last()
            .map(|s| s.chars().all(|c| c.is_numeric() || c == '.'))
            .unwrap_or(false)
    {
        return true;
    }

    false
}
