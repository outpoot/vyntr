# Pulse Component Guidelines

## Overview
Pulse is the search indexing system of Vyntr, built with Tantivy (a Rust-based full-text search engine).

## Coding Standards
- Follow the Rust Style Guide
- Use `cargo fmt` to format code
- Use `cargo clippy` to catch common mistakes
- Include documentation for public APIs

## Guidelines
- Benchmark search performance
- Document indexing strategies
- Test with realistic data volumes
- Optimize for query speed and relevance
- Handle large-scale data efficiently

## Component Structure
- `main.rs`: Entry point
- `models.rs`: Data models
- `bin/search.rs`: Search functionality
- `bin/server.rs`: Server implementation