# Vyntr - Developer Onboarding Guide

Welcome to the Vyntr project! This guide will help you understand the project structure, set up your development environment, and get started with contributing to Vyntr - an independent search engine.

## Table of Contents
- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Development Environment Setup](#development-environment-setup)
- [Component-specific Setup](#component-specific-setup)
- [Development Workflow](#development-workflow)
- [Key Concepts](#key-concepts)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)
- [Additional Resources](#additional-resources)

## Project Overview

Vyntr is an independent search engine built with multiple components working together:

- **Genesis**: A Rust-based web crawler and content analyzer that collects and processes web pages
- **Pulse**: A search indexing system built with Tantivy (a Rust-based full-text search engine)
- **Lexicon**: A WordNet-based dictionary lookup service built with Bun
- **Website**: A Svelte-based frontend interface powering vyntr.com

The main functionality includes web search, AI-powered summaries, dictionary lookups, unit conversions, and a chatbot called "Yappatron" that integrates with Bliptext, a platform where users can edit Wikipedia-ported articles.

## Architecture

The Vyntr architecture follows this pipeline:

1. **Genesis crawler** collects and analyzes web pages
2. Data is stored in partitioned JSONL files in **S3/B2**
3. Content is cleaned through **dataset** processing tools
4. Content is processed through **embedding tools** (vector) or **Pulse** (full-text search)
5. The **Website** frontend provides a search interface to users
6. **Lexicon** service provides dictionary lookup functionality

### Database Structure

The system uses PostgreSQL with pgvector for vector embeddings and standard tables for other data:
- User accounts and authentication
- Website registry
- Search preferences
- API usage tracking
- AI summaries and search queries

## Development Environment Setup

### Prerequisites

- Python with [uv](https://github.com/astral-sh/uv) package manager
- Node.js (v18 or newer)
- PostgreSQL with pgvector extension
- Docker and Docker Compose
- Bun runtime (for Lexicon service)
- Rust toolchain (latest stable)
- AWS CLI (for S3 interactions) or rclone for Backblaze B2

### Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/outpoot/vyntr.git
   cd vyntr
   ```

2. Create a `.env` file in the root directory:
   ```bash
   # Database
   PRIVATE_DB_URL="postgresql://postgres:your_password@localhost:5432/postgres"

   # AWS S3/Compatible Storage
   S3_ENDPOINT="https://s3.eu-central-1.amazonaws.com"
   S3_REGION="eu-central-1"
   S3_BUCKET="vyntr"
   AWS_ACCESS_KEY_ID="your-key-id"
   AWS_SECRET_ACCESS_KEY="your-secret-key"
   
   # OpenRouter API (for AI features)
   OPENROUTER_API_KEY="your-openrouter-api-key"
   
   # Search endpoint
   SEARCH_ENDPOINT="http://localhost:3000/search?q="
   ```

3. Set up the database:
   ```bash
   cd genesis/tools/database
   docker compose up -d
   ```

## Component-specific Setup

### Genesis (Crawler)

1. Navigate to the Genesis directory:
   ```bash
   cd genesis
   ```

2. Build the crawler:
   ```bash
   cargo build --release
   ```

3. Create a seed URLs file:
   ```bash
   echo "https://example.com" > data/sites.txt
   ```

4. Run the crawler:
   ```bash
   cargo run --release
   ```

### Lexicon (Dictionary Service)

1. Navigate to the Lexicon directory:
   ```bash
   cd lexicon
   ```

2. Install dependencies:
   ```bash
   bun install
   ```

3. Convert and load WordNet data:
   ```bash
   cd tools
   bun src/convert_wn_xml_to_json.py
   bun src/load_wordnet_into_db.py
   ```

4. Start the service:
   ```bash
   bun run start
   ```

### Pulse (Search Indexing)

1. Navigate to the Pulse directory:
   ```bash
   cd pulse
   ```

2. Build the indexer:
   ```bash
   cargo build --release
   ```

3. Run the server:
   ```bash
   cargo run --release --bin server
   ```

### Website (Frontend)

1. Navigate to the Website directory:
   ```bash
   cd website
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Apply database migrations:
   ```bash
   npx drizzle-kit push
   ```

4. Run the development server:
   ```bash
   npm run dev
   ```

## Development Workflow

### Git Workflow

1. Create a branch for your feature/fix:
   ```bash
   git checkout -b feature/my-feature
   ```

2. Make your changes and commit them:
   ```bash
   git add .
   git commit -m "module(component): description"
   ```

3. Push your changes:
   ```bash
   git push origin feature/my-feature
   ```

4. Create a pull request on GitHub.

### Testing

Each component has its own testing approach:

- **Genesis & Pulse**: Use Rust's built-in testing framework
  ```bash
  cargo test
  ```

- **Website**: Use Vitest for JavaScript/TypeScript testing
  ```bash
  npm test
  ```

- **Lexicon**: Use Bun's testing capabilities
  ```bash
  bun test
  ```

### Database Migrations

For the Website component, we use Drizzle ORM for database interactions:

1. Make changes to schema files in `website/src/lib/server/schema.ts`
2. Generate migration files:
   ```bash
   npx drizzle-kit generate
   ```
3. Apply migrations:
   ```bash
   npx drizzle-kit push
   ```

## Key Concepts

### Content Processing Pipeline

1. **Crawling**: Genesis discovers and downloads web pages.
2. **Analysis**: Pages are analyzed for SEO metadata, content, and links.
3. **Storage**: Data is stored in partitioned JSONL files (by URL hash).
4. **Cleaning**: Content is cleaned to remove boilerplate and irrelevant text.
5. **Embedding**: Text is converted to vector embeddings for semantic search.
6. **Indexing**: Full-text search indexes are built using Tantivy.

### Search Features

- **Web search**: Traditional keyword-based search with ranking
- **Dictionary lookup**: WordNet-based definitions and examples
- **Unit conversion**: Convert between different units of measurement
- **Currency conversion**: Convert between different currencies
- **Date calculation**: Perform date arithmetic and conversions
- **AI summaries**: Generated summaries for popular search queries
- **Chatbot**: "Yappatron" provides conversational responses

### User Features

- **User accounts**: Authentication and user profiles
- **Search preferences**: Customize search behavior
- **Website registry**: Users can register their websites
- **API access**: Developers can use Vyntr's search API

## Common Tasks

### Adding a New Search Feature

1. Create or modify appropriate files in `website/src/lib/utils/`
2. Update the `performSearch` function in `website/src/lib/server/search.ts`
3. Add UI components in `website/src/routes/`
4. Add tests for your new feature

### Modifying the Crawler

1. Update relevant modules in `genesis/src/`
2. Test changes with a small set of seed URLs
3. Monitor logs and metrics during crawling
4. Validate the output data structure

### Updating Database Schema

1. Modify schema in `website/src/lib/server/schema.ts`
2. Generate and apply migrations
3. Update any affected queries in the codebase
4. Test thoroughly to ensure data integrity

## Troubleshooting

### Common Issues

- **Database connection errors**: Verify PostgreSQL is running and credentials are correct
- **S3/B2 access issues**: Check your credentials and bucket permissions
- **API key errors**: Ensure all required environment variables are set
- **Build failures**: Check for compatible versions of dependencies

### Logging

- **Genesis**: Logs to stdout and custom log files
- **Website**: Uses SvelteKit's built-in logging
- **Pulse**: Uses the tracing crate for structured logs

## Additional Resources

- [Genesis README](/genesis/README.md): Details on the web crawler
- [Lexicon README](/lexicon/README.md): Dictionary service documentation
- [Website README](/website/README.md): Frontend application details
- [Pulse README](/pulse/README.md): Search indexing documentation
- [Tools README](/genesis/tools/README.md): Utility scripts and tools