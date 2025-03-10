use url::Url;
use colored::Colorize;
use crate::debug_only;

pub fn normalize_url(url: &str) -> Result<String, Box<dyn std::error::Error>> {
    let parsed = Url::parse(url).or_else(|_| Url::parse(&format!("http://{}", url)))?;
    Ok(parsed.to_string())
}

pub fn is_cloudflare_error(text: &str) -> bool {
    text.contains("Cloudflare") && text.contains("Worker threw exception")
}

pub fn print_request_status(url: &str, method: &str, status: &str, details: Option<&str>) {
    let timestamp = chrono::Local::now().format("%H:%M:%S");
    let details_str = details.unwrap_or("");

    let colored_method = match method {
        "TUNNEL" => method.bright_blue(),
        "PROXY" => method.bright_yellow(),
        _ => method.normal(),
    };

    let colored_status = match status {
        "SUCCESS" => status.bright_green(),
        "FAILED" => status.bright_red(),
        "RETRY" => status.bright_yellow(),
        _ => status.normal(),
    };

    debug_only! { println!(
        "[{}] {} | {} | {} {}",
        timestamp.to_string().bright_black(),
        colored_method,
        colored_status,
        url,
        details_str
    ) }
}
