# Vyntr Project Overview

Vyntr is an independent search engine project consisting of multiple components:

- **Genesis**: Web crawler and content analyzer written in Rust
- **Pulse**: Search indexing system using Tantivy written in Rust
- **Lexicon**: WordNet-based dictionary lookup service 
- **Website**: Frontend interface written in SvelteKit

The project uses PostgreSQL with pgvector for storage, AWS S3 for file storage, and requires Python, Node.js, Docker, Bun runtime, and Rust toolchain for development.
