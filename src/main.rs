mod db;
mod meta_tags;

use crate::db::{create_db_client, save_analysis, MetaTag, SeoAnalysis};
use crate::meta_tags::META_SELECTORS;
use reqwest;
use scraper::{Html, Selector};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Fetch website HTML
    let response = reqwest::get("https://www.nytimes.com")
        .await?
        .text()
        .await?;
    println!("Website fetched successfully");

    let document = Html::parse_document(&response);
    let client = create_db_client().await?;

    let mut analysis = SeoAnalysis {
        language: String::new(),
        title: String::new(),
        meta_tags: Vec::new(),
        canonical_url: None,
        content_text: String::new(),
    };

    // ====== LANGUAGE EXTRACTION ======
    if let Ok(html_selector) = Selector::parse("html") {
        if let Some(html_element) = document.select(&html_selector).next() {
            if let Some(lang) = html_element.value().attr("lang") {
                analysis.language = lang.to_string();
            }
        }
    }

    // ====== TITLE EXTRACTION ======
    if let Ok(selector) = Selector::parse("title") {
        if let Some(title) = document.select(&selector).next() {
            analysis.title = title.text().collect();
        }
    }

    // ====== META TAGS EXTRACTION ======
    for selector in META_SELECTORS {
        if let Ok(sel) = Selector::parse(&format!("meta[{}='{}']", selector.attr, selector.value)) {
            for element in document.select(&sel) {
                if let Some(content) = element.value().attr("content") {
                    analysis.meta_tags.push(MetaTag {
                        name: selector.value.to_string(),
                        content: content.to_string(),
                    });
                }
            }
        }
    }

    // ====== CANONICAL URL EXTRACTION ======
    if let Ok(selector) = Selector::parse("link[rel='canonical']") {
        if let Some(link) = document.select(&selector).next() {
            analysis.canonical_url = link.value().attr("href").map(|s| s.to_string());
        }
    }

    if let Ok(links_selector) = Selector::parse("a[href]") {
        println!("\nFound links:");
        for link in document.select(&links_selector) {
            if let Some(href) = link.value().attr("href") {
                println!("{}", href);
            }
        }
    }

    // ====== CONTENT TEXT EXTRACTION ======
    let content_selector = Selector::parse("h1, h2, h3, h4, h5, h6, p, li").unwrap();
    for element in document.select(&content_selector) {
        let text = element.text().collect::<String>();
        analysis.content_text.push_str(&text);
        analysis.content_text.push('\n');
    }

    match save_analysis(&client, &analysis).await {
        Ok(_) => println!("SEO analysis saved successfully!"),
        Err(e) => eprintln!("Error saving analysis: {}", e),
    }

    println!("SEO analysis saved successfully!");
    Ok(())
}
