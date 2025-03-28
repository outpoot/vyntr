import time
import glob
import json
import os
import numpy as np
import torch
import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm
import math
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
from collections import defaultdict
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(dotenv_path)

# --- Configuration ---
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DB_TABLE_NAME = "document_chunk_embeddings"
CHUNK_BATCH_SIZE = 2048  # How many CHUNKS to feed to the GPU at once
DB_BATCH_SIZE = 4096     # How many embeddings to insert into DB at once
MAX_SEQ_LENGTH = 256     # Effective max length for all-MiniLM-L6-v2
CHUNK_OVERLAP = 50
MAX_CPU_WORKERS = os.cpu_count() or 4 # for S3 I/O and chunking
ETA_UPDATE_INTERVAL_SEC = 10 # how often to print ETA

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- S3 Configuration ---
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_REGION = os.getenv("S3_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "analyses/")

# --- Database Configuration ---
DB_NAME = os.getenv("DB_NAME", "mydatabase")
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

# --- Validate S3 Config ---
if not all([S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET]):
    logging.error("S3 environment variables not fully configured (S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET). Exiting.")
    exit(1)


# --- Helper Functions ---
def connect_db():
    """Establishes connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        register_vector(conn)
        logging.info(
            f"Successfully connected to database '{DB_NAME}' on {DB_HOST}:{DB_PORT}"
        )
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        raise

def create_table_if_not_exists(conn, embedding_dim):
    """Creates the chunk embeddings table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute(f"CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {DB_TABLE_NAME} (
                url TEXT NOT NULL,
                chunk_id INTEGER NOT NULL,
                embedding VECTOR({embedding_dim}),
                PRIMARY KEY (url, chunk_id)
            );
            """
        )
        conn.commit()
        logging.info(
            f"Ensured table '{DB_TABLE_NAME}' exists with vector dimension {embedding_dim}."
        )

def extract_relevant_text(entry):
    """Extracts and combines relevant text fields from a JSON entry."""
    title = entry.get("title", "") or ""
    content = entry.get("content_text", "") or ""
    description = ""
    if "meta_tags" in entry and isinstance(entry["meta_tags"], list):
        for tag in entry["meta_tags"]:
            if (
                isinstance(tag, dict)
                and tag.get("name") == "description"
                and tag.get("content")
            ):
                description = tag["content"]
                break
    combined_text = f"Title: {title}\nDescription: {description}\nContent: {content}".strip()
    return combined_text

def chunk_text_by_tokens(text, tokenizer, max_tokens, overlap):
    """Chunks text based on token count using the model's tokenizer."""
    if not text: return []
    tokens = tokenizer.encode(text, add_special_tokens=False, truncation=False)
    if len(tokens) <= max_tokens: return [tokenizer.decode(tokens)]

    chunks = []
    stride = max_tokens - overlap
    if stride <= 0: stride = max(1, max_tokens // 2)

    for i in range(0, len(tokens), stride):
        chunk_tokens = tokens[i : i + max_tokens]
        chunks.append(tokenizer.decode(chunk_tokens))
        if i + max_tokens >= len(tokens): break
    return chunks

def get_s3_client():
    """Initializes and returns a boto3 S3 client."""
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=S3_REGION
        )
        # test connection briefly
        s3_client.list_buckets()
        logging.info(f"Successfully connected to S3 endpoint: {S3_ENDPOINT_URL}")
        return s3_client
    except ClientError as e:
        logging.error(f"Failed to connect to S3: {e}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during S3 client creation: {e}")
        raise

def list_s3_files(s3_client, bucket, prefix):
    """Lists all .jsonl files in the S3 bucket with the given prefix."""
    logging.info(f"Listing files in s3://{bucket}/{prefix}...")
    jsonl_files = []
    paginator = s3_client.get_paginator('list_objects_v2')
    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    key = obj['Key']
                    if not key.endswith('/') and key.lower().endswith('.jsonl'):
                        jsonl_files.append(key)
    except ClientError as e:
        logging.error(f"Failed to list S3 objects: {e}")
        raise
    logging.info(f"Found {len(jsonl_files)} .jsonl files in S3.")
    return jsonl_files

def precompute_chunk_counts_s3(s3_client, bucket, s3_key, tokenizer, max_tokens, overlap):
    """Worker function to read an S3 object and count items and chunks."""
    item_count = 0
    chunk_count = 0
    try:
        response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        body = response['Body']
        for line_bytes in body.iter_lines():
            try:
                line = line_bytes.decode('utf-8')
                entry = json.loads(line)
                if not entry.get("url"): continue
                text = extract_relevant_text(entry)
                if not text: continue
                chunks = chunk_text_by_tokens(text, tokenizer, max_tokens, overlap)
                if chunks:
                    item_count += 1
                    chunk_count += len(chunks)
            except UnicodeDecodeError:
                 logging.warning(f"Skipping line due to decode error in {s3_key}")
            except json.JSONDecodeError:
                 pass
            except Exception:
                 pass
        body.close()
    except ClientError as e:
        logging.warning(f"S3 ClientError during precompute for {s3_key}: {e}")
    except Exception as e:
        logging.warning(f"Precompute failed for {s3_key}: {e}")
    return item_count, chunk_count

def process_s3_object_yield_chunks(s3_client, bucket, s3_key, tokenizer, max_tokens, overlap):
    """Worker function to read S3 object, process, and yield (url, chunk_id, chunk_text)."""
    chunk_counts = defaultdict(int)
    try:
        response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        body = response['Body']
        line_num = 0
        for line_bytes in body.iter_lines():
            line_num += 1
            try:
                line = line_bytes.decode('utf-8')
                entry = json.loads(line)
                url = entry.get("url")
                if not url: continue

                text = extract_relevant_text(entry)
                if not text: continue

                chunks = chunk_text_by_tokens(text, tokenizer, max_tokens, overlap)
                if not chunks: continue

                start_chunk_id = chunk_counts[url]
                for i, chunk_text in enumerate(chunks):
                    yield (url, start_chunk_id + i, chunk_text)
                chunk_counts[url] += len(chunks)

            except UnicodeDecodeError:
                logging.warning(f"Skipping line {line_num} due to decode error in {s3_key}")
            except json.JSONDecodeError:
                logging.warning(f"Skipping invalid JSON on line {line_num} in {s3_key}")
            except Exception as e:
                logging.warning(f"Error processing line {line_num} in {s3_key}: {e}")
        body.close()
    except ClientError as e:
        logging.error(f"S3 ClientError processing object {s3_key}: {e}")
    except Exception as e:
        logging.error(f"Failed to process S3 object {s3_key}: {e}")


def encode_batch_hf_automodel(model, tokenizer, chunk_batch, device, max_seq_len):
    """Encode batch using standard Hugging Face AutoModel."""
    inputs = tokenizer(
        chunk_batch,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_seq_len
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
    return embeddings


if __name__ == "__main__":
    logging.info("--- Starting Embedding Generation from S3 ---")
    overall_start_time = time.time()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Using device: {device}")
    if device == "cpu":
        logging.warning("Running on CPU, this will be significantly slower!")

    logging.info(f"Loading model and tokenizer: {MODEL_NAME}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
        model = AutoModel.from_pretrained(MODEL_NAME)
        model.to(device)
        embedding_dim = model.config.hidden_size

        if device == 'cuda':
            try:
                model.half()
                logging.info("Applied .half() to model for FP16.")
            except Exception as fp16_err:
                logging.warning(f"Could not apply .half(): {fp16_err}. Using FP32.")
        model.eval()
    except Exception as e:
        logging.error(f"Failed to load model/tokenizer: {e}")
        exit(1)

    conn = connect_db()
    create_table_if_not_exists(conn, embedding_dim)

    # S3 Client Setup
    s3_client = get_s3_client()

    logging.info("Phase 1: Listing S3 files and pre-computing total chunks for ETA...")
    precompute_start_time = time.time()
    try:
        all_s3_keys = list_s3_files(s3_client, S3_BUCKET, S3_PREFIX)
    except Exception as e:
        logging.error(f"Failed during S3 listing or client creation: {e}")
        exit(1)

    if not all_s3_keys:
        logging.error(f"No .jsonl files found in s3://{S3_BUCKET}/{S3_PREFIX}")
        exit(1)
    logging.info(f"Found {len(all_s3_keys)} .jsonl files in S3.")

    total_items_estimate = 0
    total_chunks_estimate = 0

    with ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS) as executor:
        futures = [
            executor.submit(precompute_chunk_counts_s3, s3_client, S3_BUCKET, key, tokenizer, MAX_SEQ_LENGTH, CHUNK_OVERLAP)
            for key in all_s3_keys
        ]
        for future in tqdm(as_completed(futures), total=len(all_s3_keys), desc="Pre-computing Chunks"):
            try:
                item_count, chunk_count = future.result()
                total_items_estimate += item_count
                total_chunks_estimate += chunk_count
            except Exception as exc:
                logging.error(f"Pre-computation task generated an exception: {exc}")

    precompute_time = time.time() - precompute_start_time
    logging.info(f"Pre-computation finished in {precompute_time:.2f}s.")
    logging.info(f"Estimated Items to Process: {total_items_estimate}")
    logging.info(f"Estimated Chunks to Embed: {total_chunks_estimate}")
    if total_chunks_estimate == 0:
        logging.warning("No processable chunks found. Exiting.")
        exit(0)

    logging.info("Phase 2: Starting main processing...")
    process_start_time = time.time()
    chunks_processed_count = 0
    db_batch = []
    model_input_batch = []
    last_eta_print_time = time.time()

    pbar = tqdm(total=total_chunks_estimate, desc="Embedding Chunks", unit="chunk")

    with ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS) as executor:
        chunk_futures = [
            executor.submit(process_s3_object_yield_chunks, s3_client, S3_BUCKET, key, tokenizer, MAX_SEQ_LENGTH, CHUNK_OVERLAP)
            for key in all_s3_keys
        ]

        for future in as_completed(chunk_futures):
            try:
                for url, chunk_id, chunk_text in future.result():
                    model_input_batch.append((url, chunk_id, chunk_text))

                    if len(model_input_batch) >= CHUNK_BATCH_SIZE:
                        batch_to_encode_data = model_input_batch[:CHUNK_BATCH_SIZE]
                        model_input_batch = model_input_batch[CHUNK_BATCH_SIZE:]

                        batch_texts = [item[2] for item in batch_to_encode_data]

                        try:
                            embeddings = encode_batch_hf_automodel(
                                model, tokenizer, batch_texts, device, MAX_SEQ_LENGTH
                            )
                            if device == 'cuda': torch.cuda.synchronize()

                            for i, (url_b, chunk_id_b, _) in enumerate(batch_to_encode_data):
                                db_batch.append((url_b, chunk_id_b, embeddings[i]))

                            chunks_processed_count += len(batch_to_encode_data)
                            pbar.update(len(batch_to_encode_data))

                            current_time = time.time()
                            if current_time - last_eta_print_time > ETA_UPDATE_INTERVAL_SEC:
                                elapsed_proc_time = current_time - process_start_time
                                if chunks_processed_count > 0 and elapsed_proc_time > 1:
                                    chunks_per_sec = chunks_processed_count / elapsed_proc_time
                                    chunks_remaining = total_chunks_estimate - chunks_processed_count
                                    eta_seconds = chunks_remaining / chunks_per_sec if chunks_per_sec > 0 else 0
                                    eta_formatted = time.strftime('%H:%M:%S', time.gmtime(eta_seconds)) if eta_seconds > 0 else "N/A"
                                    pbar.set_postfix_str(f"Rate: {chunks_per_sec:.2f} chunks/s, ETA: {eta_formatted}")
                                    last_eta_print_time = current_time

                        except Exception as model_err:
                            logging.error(f"Error during model encoding batch: {model_err}", exc_info=True)
                            pbar.update(len(batch_to_encode_data))

                    if len(db_batch) >= DB_BATCH_SIZE:
                        try:
                            with conn.cursor() as cur:
                                psycopg2.extras.execute_values(
                                    cur,
                                    f"""
                                    INSERT INTO {DB_TABLE_NAME} (url, chunk_id, embedding)
                                    VALUES %s
                                    ON CONFLICT (url, chunk_id) DO UPDATE SET embedding = EXCLUDED.embedding;
                                    """,
                                    db_batch,
                                    template="(%s, %s, %s)",
                                )
                            conn.commit()
                            db_batch = []
                        except psycopg2.Error as db_err:
                            logging.error(f"Database batch insert failed: {db_err}")
                            conn.rollback()
                            db_batch = []

            except Exception as future_exc:
                logging.error(f"Chunk processing task generated an exception: {future_exc}", exc_info=True)


    logging.info("Processing final batches...")

    if model_input_batch:
        try:
            batch_texts = [item[2] for item in model_input_batch]
            embeddings = encode_batch_hf_automodel(
                model, tokenizer, batch_texts, device, MAX_SEQ_LENGTH
            )
            if device == 'cuda': torch.cuda.synchronize()

            for i, (url_b, chunk_id_b, _) in enumerate(model_input_batch):
                db_batch.append((url_b, chunk_id_b, embeddings[i]))

            chunks_processed_count += len(model_input_batch)
            pbar.update(len(model_input_batch))
        except Exception as model_err:
            logging.error(f"Error during final model encoding batch: {model_err}", exc_info=True)

    pbar.close()

    if db_batch:
        try:
            logging.info(f"Inserting final batch of {len(db_batch)} embeddings into DB...")
            with conn.cursor() as cur:
                psycopg2.extras.execute_values(
                    cur,
                    f"""
                    INSERT INTO {DB_TABLE_NAME} (url, chunk_id, embedding)
                    VALUES %s
                    ON CONFLICT (url, chunk_id) DO UPDATE SET embedding = EXCLUDED.embedding;
                    """,
                    db_batch,
                    template="(%s, %s, %s)",
                )
            conn.commit()
            logging.info("Final DB batch inserted successfully.")
        except psycopg2.Error as db_err:
            logging.error(f"Final database batch insert failed: {db_err}")
            conn.rollback()

    conn.close()
    overall_end_time = time.time()
    total_runtime = overall_end_time - overall_start_time
    processing_runtime = overall_end_time - process_start_time

    logging.info("--- Embedding Generation Complete ---")
    logging.info(f"Total Runtime: {time.strftime('%H:%M:%S', time.gmtime(total_runtime))}")
    logging.info(f"  (Pre-computation: {precompute_time:.2f}s)")
    logging.info(f"  (Main Processing: {processing_runtime:.2f}s)")
    logging.info(f"Total Items Processed (estimate): {total_items_estimate}")
    logging.info(f"Total Chunks Embedded: {chunks_processed_count}")
    if processing_runtime > 0:
        avg_chunks_per_sec = chunks_processed_count / processing_runtime
        logging.info(f"Average Processing Throughput: {avg_chunks_per_sec:.2f} chunks/sec")

