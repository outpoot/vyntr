# Vyntr Genesis

Genesis is the crawler behind Vyntr.

## Overview
The system stores SEO analysis data in AWS S3 using a partitioned JSONL file format for efficient querying and processing.

## Storage Structure

```
s3://vyntr/
└── analyses/
    ├── partition=00/
    │   ├── batch_550e8400-e29b-41d4-a716-446655440000.jsonl
    │   └── batch_6ba7b810-9dad-11d1-80b4-00c04fd430c8.jsonl
    ├── partition=01/
    │   └── batch_*.jsonl
    └── ...
```

- Data is partitioned by URL hash (first byte, hex encoded)
- Each file contains up to 10,000 records
- Files use JSONL format (one JSON object per line)

## Record Format

Each line in the JSONL files contains a record with this structure:
```json
{
  "url": "https://example.com",
  "language": "en",
  "title": "Example Page",
  "meta_tags": [
    {"name": "description", "content": "Page description"},
    {"name": "keywords", "content": "key, words"}
  ],
  "canonical_url": "https://example.com/canonical",
  "content_text": "Main page content..."
}
```

## Configuration

Required environment variables:
```bash
S3_ENDPOINT="https://s3.eu-central-1.amazonaws.com"
S3_REGION="eu-central-1"
S3_BUCKET="vyntr"
AWS_ACCESS_KEY_ID="your-key-id"
AWS_SECRET_ACCESS_KEY="your-secret-key"
```

## Working with the Data
1. First get a list of all partitions from S3 (analyses/partition=XX/)
2. Download only partitions you need (by URL first byte, 00-FF)
3. Process the data
4. Delete downloaded files after processing