<img style="width: 128px; height: 128px" src="website/static/favicon.svg" /><h1 style="font-size: 48px"><a href="https://bliptext.com">Vyntr.com</a> - the independent search engine.</h1>
[Privacy Policy](https://vyntr.com/legal/privacy) | [Terms of Service](https://vyntr.com/legal/terms) | [License](LICENSE) | [YouTube video](https://vyntr.com)

Vyntr is a search engine project with multiple components:

## Components

- [Genesis](genesis/README.md) - Web crawler and content analyzer
- [Pulse](pulse/README.md) - Search indexing system using Tantivy
- [Lexicon](lexicon/README.md) - WordNet-based dictionary lookup service
- [Website](website/README.md) - Frontend interface at vyntr.com

## Setup

1. Create a `.env` file in the root directory:

```bash
# Database
PRIVATE_DB_URL="postgresql://postgres:your_password@serverip:port/postgres"

# AWS S3/Compatible Storage
S3_ENDPOINT="https://s3.eu-central-1.amazonaws.com"
S3_REGION="eu-central-1"
S3_BUCKET="vyntr"
AWS_ACCESS_KEY_ID="your-key-id"
AWS_SECRET_ACCESS_KEY="your-secret-key"
```

2. Set up the database:
```bash
cd genesis/tools/database
docker compose up -d
```

3. Set up individual components:
- Genesis crawler: Follow [genesis setup](genesis/README.md)
- Lexicon service: Follow [lexicon setup](lexicon/README.md)
- Website: Follow [website setup](website/README.md)

## Pipeline

1. `Genesis` crawler collects and analyzes web pages
2. Data is stored in partitioned JSONL files in `S3`
3. Content is cleaned through `dataset`.
3. Content is processed through `embedding` tools (vector), or `Pulse` (full-text).
4. Website frontend provides search interface.

## Requirements

- Python with [uv](https://github.com/astral-sh/uv) package manager
- Node.js
- PostgreSQL with pgvector
- Docker
- Bun runtime (for Lexicon service)
- Rust toolchain

## Dataset
The Vyntr dataset is not publicly available. For licensing inquiries, please contact contact@outpoot.com.

You may also use the official API provided at https://vyntr.com/api.
## License

This project is licensed under the **Creative Commons Attribution-NonCommercial 4.0 International** License (**CC BY-NC 4.0)**. See the [LICENSE](LICENSE) file for details.

Individual components may have additional licensing requirements. See their respective directories for specific licensing information.

WordNet data used in Lexicon is subject to the [WordNet License](https://creativecommons.org/licenses/by/4.0/).

