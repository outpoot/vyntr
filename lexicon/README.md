# Lexicon - WordNet API Service

A lightweight REST API service providing WordNet dictionary lookup functionality, built with Bun and PostgreSQL.

## Features

- ⚡ Fast word lookup with fuzzy matching
- Returns detailed word information including:
  - Definitions
  - Part of speech
  - Pronunciations
  - Examples
  - Synonyms
  - Antonyms
  - Similar words

## Prerequisites

- [Bun](https://bun.sh) v1.1.22 or higher
- [uv](https://github.com/astral-sh/uv) for the tools
- PostgreSQL database
- WordNet XML dump from https://en-word.net

## Setup

1. Install dependencies:
```bash
bun install
```

2. Create a `.env` file in the project root `vyntr/.env`:

Read the main README.md for instructions.

3. Prepare the WordNet data:
   - Place WordNet XML file as `wn.xml` in the `tools/src` directory
   - Sync uv:
   ```bash
   cd tools/src
   uv sync
   ```
   - Run the conversion script:
   ```bash
   python convert_wn_xml_to_json.py
   ```
   - Load the data into PostgreSQL:
   ```bash
   python load_wordnet_into_db.py
   ```

## API

Start the API server:

```bash
bun run index.ts
```

## API Endpoints

### GET /lookup/{word}
Look up a word with fuzzy matching support.

**Parameters:**
- `word` (path parameter): The word to look up

**Response:**
```json
[
  {
    "similarity": 1.0,
    "entry": {
      "id": "string",
      "word": "string",
      "partOfSpeech": "string",
      "pronunciations": ["string"],
      "definitions": [
        {
          "pos": "string",
          "gloss": "string",
          "source": "string"
        }
      ],
      "examples": ["string"],
      "synonyms": ["string"],
      "antonyms": ["string"],
      "similarWords": ["string"]
    }
  }
]
```

### GET /health
Health check endpoint.

**Response:**
- `200 OK` with body: "OK"

## License

This project uses WordNet data which is subject to the WordNet [1](en-word.net) License [2](https://creativecommons.org/licenses/by/4.0/).
