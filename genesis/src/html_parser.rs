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
                                && !is_ignored_file_type(url.path()) {
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
                    let name = el.get_attribute("name")
                        .or_else(|| el.get_attribute("property"))
                        .unwrap_or_default();
                    if let Some(content) = el.get_attribute("content") {
                        result.meta_tags.push(MetaTag {
                            name,
                            content,
                        });
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
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".pdf", 
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", 
        ".tar", ".gz", ".mp3", ".mp4", ".avi", ".mov",
    ];
    let path_lower = path.to_lowercase();
    extensions.iter().any(|&ext| path_lower.ends_with(ext))
}
