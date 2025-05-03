# Genesis Component Guidelines

## Overview
Genesis is the web crawler and content analyzer component of Vyntr, written in Rust.

## Coding Standards
- Follow the Rust Style Guide
- Use `cargo fmt` to format code
- Use `cargo clippy` to catch common mistakes

## Guidelines
- Monitor resource usage (memory, network)
- Document any changes to the data format
- Optimize for performance and efficiency
- Follow web crawling best practices and respect robots.txt

## Component Structure
- `crawler.rs`: Web crawling functionality
- `db.rs`: Database interactions
- `fingerprint.rs`: Content fingerprinting
- `html_parser.rs`: HTML parsing and extraction
- `logger.rs`: Logging functionality
- `metrics.rs`: Performance metrics tracking
- `network.rs`: Network request handling
- `proxy.rs`: Proxy management
- `utils.rs`: Utility functions