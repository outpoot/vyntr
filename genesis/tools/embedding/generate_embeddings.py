import time
import glob
import json
import os
import torch
import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from transformers import AutoTokenizer, AutoModel
from tqdm import tqdm
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import boto3
from botocore.exceptions import ClientError, ReadTimeoutError, ConnectionClosedError
from botocore.config import Config
from urllib3.exceptions import IncompleteRead as Urllib3IncompleteRead
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(dotenv_path)
print("Loading .env from: ", dotenv_path)
# --- Configuration ---
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DB_TABLE_NAME = "document_chunk_embeddings"
CHUNK_BATCH_SIZE = 2048  # How many CHUNKS to feed to the GPU at once
DB_BATCH_SIZE = 4096     # How many embeddings to insert into DB at once
MAX_SEQ_LENGTH = 256     # Effective max length for all-MiniLM-L6-v2
CHUNK_OVERLAP = 50
MAX_CPU_WORKERS = (os.cpu_count() or 4) // 2  # Reduced for stability
ETA_UPDATE_INTERVAL_SEC = 10 # how often to print ETA

# --- Retry Configuration ---
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- S3 Configuration ---
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT")
S3_REGION = os.getenv("S3_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_PREFIX = os.getenv("S3_PREFIX", "")

# --- Database Configuration ---
PRIVATE_DB_URL = os.getenv("PRIVATE_DB_URL")
if not PRIVATE_DB_URL:
    logging.error("Database URL not configured (PRIVATE_DB_URL). Exiting.")
    exit(1)

# --- Validate S3 Config ---
if not all([S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET]):
    logging.error("S3 environment variables not fully configured (S3_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET). Exiting.")
    exit(1)


# --- Helper Functions ---
def connect_db():
    """Establishes connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(PRIVATE_DB_URL)
        register_vector(conn)
        logging.info("Successfully connected to database")
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

def remove_unsupported_headers(request, **kwargs):
    """Removes unsupported checksum headers from S3 requests for compatibility."""
    if 'x-amz-checksum-mode' in request.headers:
        del request.headers['x-amz-checksum-mode']
    if 'x-amz-checksum-crc32' in request.headers:
        del request.headers['x-amz-checksum-crc32']

def get_s3_client():
    """Initializes and returns a boto3 S3 client with header modification and timeouts."""
    try:
        session = boto3.Session()
        session.events.register('before-send.*', remove_unsupported_headers)

        s3_config = Config(
            connect_timeout=10,
            read_timeout=300,   # 5 minutes for large files
            retries={'max_attempts': 0}  # We handle retries ourselves
        )

        s3_client = session.client(
            's3',
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=S3_REGION,
            config=s3_config
        )
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
    """Lists all .jsonl files in the S3 bucket with the given prefix, handling partitions."""
    logging.info(f"Listing files in s3://{bucket}/{prefix}...")
    jsonl_files = []
    paginator = s3_client.get_paginator('list_objects_v2')
    try:
        partitions = set()
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
            if 'CommonPrefixes' in page:
                for prefix_obj in page['CommonPrefixes']:
                    prefix_path = prefix_obj['Prefix']
                    if prefix_path.endswith('/') and '=' in prefix_path.split('/')[-2]:
                         partitions.add(prefix_path)

        if not partitions:
            logging.warning(f"No partition folders found directly under s3://{bucket}/{prefix}. Listing files directly in prefix.")
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        if not key.endswith('/') and key.lower().endswith('.jsonl'):
                            jsonl_files.append(key)
        else:
            logging.info(f"Found {len(partitions)} potential partition folders. Scanning within them...")
            for partition_prefix in partitions:
                logging.info(f"Scanning partition prefix: {partition_prefix}")
                for page in paginator.paginate(Bucket=bucket, Prefix=partition_prefix):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            key = obj['Key']
                            if not key.endswith('/') and key.lower().endswith('.jsonl'):
                                jsonl_files.append(key)

    except ClientError as e:
        logging.error(f"Failed to list S3 objects: {e}")
        raise

    partition_counts = defaultdict(int)
    for file_key in jsonl_files:
        partition_name = "root_or_unknown"
        parts = file_key.split('/')
        for part in reversed(parts):
            if '=' in part:
                partition_name = part
                break
        partition_counts[partition_name] += 1

    logging.info(f"Found {len(jsonl_files)} total .jsonl files across {len(partition_counts)} detected partitions/groups:")
    for p_name, count in sorted(partition_counts.items()):
        logging.info(f"  - {p_name}: {count} files")

    if not jsonl_files:
         logging.warning(f"No .jsonl files were ultimately found in s3://{bucket}/{prefix} or its subdirectories.")

    return jsonl_files

def precompute_chunk_counts_s3(s3_client, bucket, s3_key, tokenizer, max_tokens, overlap):
    """Worker function with retries to read an S3 object and count items and chunks."""
    item_count = 0
    chunk_count = 0
    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            response = s3_client.get_object(Bucket=bucket, Key=s3_key)
            body = response['Body']
            item_count = chunk_count = 0  # Reset counts for retry
            
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
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                except Exception as inner_e:
                    logging.warning(f"Error processing line in {s3_key}: {inner_e}")
                    continue
            
            body.close()
            return item_count, chunk_count

        except (ClientError, ReadTimeoutError, ConnectionClosedError, Urllib3IncompleteRead) as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_SECONDS * (attempt + 1)
                logging.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {s3_key}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logging.error(f"Precompute failed for {s3_key} after {MAX_RETRIES} attempts: {e}")
                return 0, 0

    return 0, 0

def process_s3_object_yield_chunks(s3_client, bucket, s3_key, tokenizer, max_tokens, overlap):
    """Worker function with retries to process S3 object and yield chunks."""
    chunk_counts = defaultdict(int)
    last_exception = None

    for attempt in range(MAX_RETRIES):
        try:
            response = s3_client.get_object(Bucket=bucket, Key=s3_key)
            body = response['Body']
            results = []
            chunk_counts.clear()  # Reset state for retry
            
            for line_bytes in body.iter_lines():
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
                        results.append((url, start_chunk_id + i, chunk_text))
                    chunk_counts[url] += len(chunks)

                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
                except Exception as e:
                    logging.warning(f"Error processing line in {s3_key}: {e}")
                    continue

            body.close()
            for result in results:
                yield result
            return

        except (ClientError, ReadTimeoutError, ConnectionClosedError, Urllib3IncompleteRead) as e:
            last_exception = e
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY_SECONDS * (attempt + 1)
                logging.warning(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {s3_key}: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logging.error(f"Processing failed for {s3_key} after {MAX_RETRIES} attempts: {e}")
                return

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
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.cpu().numpy()

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
                logging.info("Applied .half() to model for potential FP16 speedup.")
            except Exception as fp16_err:
                logging.warning(f"Could not apply .half(): {fp16_err}. Using FP32.")
        model.eval()
    except Exception as e:
        logging.error(f"Failed to load model/tokenizer: {e}", exc_info=True)
        exit(1)

    conn = connect_db()
    create_table_if_not_exists(conn, embedding_dim)

    s3_client = get_s3_client()

    logging.info("Phase 1: Listing S3 files and pre-computing total chunks for ETA...")
    precompute_start_time = time.time()
    try:
        all_s3_keys = list_s3_files(s3_client, S3_BUCKET, S3_PREFIX)
    except Exception as e:
        logging.error(f"Failed during S3 listing or client creation: {e}", exc_info=True)
        if conn: conn.close()
        exit(1)

    if not all_s3_keys:
        logging.error(f"No .jsonl files found in s3://{S3_BUCKET}/{S3_PREFIX}. Exiting.")
        if conn: conn.close()
        exit(1)

    partition_groups = defaultdict(list)
    for key in all_s3_keys:
        partition_name = "root_or_unknown"
        parts = key.split('/')
        for part in reversed(parts):
            if '=' in part:
                partition_name = part
                break
        partition_groups[partition_name].append(key)

    logging.info(f"Starting pre-computation across {len(partition_groups)} detected partitions/groups...")

    total_items_overall = 0
    total_chunks_overall = 0
    partition_chunk_estimates = {}

    for partition_name, partition_files in partition_groups.items():
        logging.info(f"\nPre-computing for partition: {partition_name} ({len(partition_files)} files)")
        partition_items_estimate = 0
        partition_chunks_estimate = 0

        with ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS, thread_name_prefix=f'Precomp_{partition_name[:10]}') as executor:
            futures = {
                executor.submit(precompute_chunk_counts_s3, s3_client, S3_BUCKET, key,
                              tokenizer, MAX_SEQ_LENGTH, CHUNK_OVERLAP): key
                for key in partition_files
            }
            for future in tqdm(as_completed(futures),
                             total=len(partition_files),
                             desc=f"Pre-computing Chunks ({partition_name})",
                             unit="file"):
                key = futures[future]
                try:
                    item_count, chunk_count = future.result()
                    partition_items_estimate += item_count
                    partition_chunks_estimate += chunk_count
                except Exception as exc:
                    logging.error(f"Pre-computation task for file '{key}' generated an exception: {exc}", exc_info=True)

        logging.info(f"Pre-computation finished for partition={partition_name}.")
        logging.info(f"  Estimated Items: {partition_items_estimate}")
        logging.info(f"  Estimated Chunks: {partition_chunks_estimate}")
        partition_chunk_estimates[partition_name] = partition_chunks_estimate
        total_items_overall += partition_items_estimate
        total_chunks_overall += partition_chunks_estimate

    precompute_time = time.time() - precompute_start_time
    logging.info(f"\nTotal Estimated Items across all partitions: {total_items_overall}")
    logging.info(f"Total Estimated Chunks across all partitions: {total_chunks_overall}")
    logging.info(f"Pre-computation phase took: {precompute_time:.2f} seconds.")

    if total_chunks_overall == 0:
        logging.error("No processable chunks found in any partition. Exiting.")
        if conn: conn.close()
        exit(1)

    logging.info("\nPhase 2: Starting main processing (Embedding and DB Insert)...")
    process_start_time = time.time()
    chunks_processed_count = 0
    db_batch = []
    model_input_batch = []
    last_eta_print_time = time.time()

    for partition_name, partition_files in partition_groups.items():
        partition_total_chunks = partition_chunk_estimates.get(partition_name, 0)
        if partition_total_chunks == 0:
            logging.info(f"\nSkipping partition {partition_name} as it has 0 estimated chunks.")
            continue

        logging.info(f"\nProcessing partition: {partition_name} (Est. Chunks: {partition_total_chunks})")
        partition_chunks_processed = 0
        pbar = tqdm(total=partition_total_chunks, desc=f"Embedding ({partition_name})", unit="chunk")

        with ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS, thread_name_prefix=f'Process_{partition_name[:10]}') as executor:
            chunk_futures = {
                executor.submit(process_s3_object_yield_chunks, s3_client, S3_BUCKET, key, tokenizer, MAX_SEQ_LENGTH, CHUNK_OVERLAP): key
                for key in partition_files
            }

            for future in as_completed(chunk_futures):
                key = chunk_futures[future]
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

                                for i, (url_b, chunk_id_b, _) in enumerate(batch_to_encode_data):
                                    db_batch.append((url_b, chunk_id_b, embeddings[i].tolist()))

                                batch_size = len(batch_to_encode_data)
                                chunks_processed_count += batch_size
                                partition_chunks_processed += batch_size
                                pbar.update(batch_size)

                                current_time = time.time()
                                if current_time - last_eta_print_time > ETA_UPDATE_INTERVAL_SEC:
                                    elapsed_proc_time = current_time - process_start_time
                                    if chunks_processed_count > 0 and elapsed_proc_time > 1:
                                        chunks_per_sec = chunks_processed_count / elapsed_proc_time
                                        chunks_remaining = total_chunks_overall - chunks_processed_count
                                        if chunks_per_sec > 0 and chunks_remaining > 0:
                                            eta_seconds = chunks_remaining / chunks_per_sec
                                            eta_formatted = time.strftime('%H:%M:%S', time.gmtime(eta_seconds))
                                        else:
                                             eta_formatted = "N/A" if chunks_per_sec <=0 else "Done"

                                        pbar.set_postfix_str(f"Overall Rate: {chunks_per_sec:.1f} c/s, ETA: {eta_formatted}, DB Batch: {len(db_batch)}")
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
                                        template="(%s, %s, %s::vector)",
                                        page_size=DB_BATCH_SIZE
                                    )
                                conn.commit()
                                db_batch = []
                            except psycopg2.Error as db_err:
                                logging.error(f"Database batch insert failed: {db_err}")
                                conn.rollback()
                                db_batch = []
                            except Exception as general_db_err:
                                 logging.error(f"Unexpected error during DB insert: {general_db_err}", exc_info=True)
                                 conn.rollback()
                                 db_batch = []

                except GeneratorExit:
                     logging.warning(f"GeneratorExit caught for file {key}. Main thread likely shutting down.")
                     break
                except Exception as future_exc:
                    logging.error(f"Chunk processing task for file '{key}' generated an exception: {future_exc}", exc_info=True)

        pbar.close()
        pbar.refresh()
        logging.info(f"Finished processing partition {partition_name}. Processed {partition_chunks_processed} chunks.")

    logging.info("Processing any remaining chunks in the final batches...")

    if model_input_batch:
        try:
            logging.info(f"Encoding final model batch of {len(model_input_batch)} chunks...")
            batch_texts = [item[2] for item in model_input_batch]
            embeddings = encode_batch_hf_automodel(
                model, tokenizer, batch_texts, device, MAX_SEQ_LENGTH
            )

            for i, (url_b, chunk_id_b, _) in enumerate(model_input_batch):
                 db_batch.append((url_b, chunk_id_b, embeddings[i].tolist()))

            chunks_processed_count += len(model_input_batch)
            logging.info(f"Encoded final model batch. Total chunks processed: {chunks_processed_count}")
        except Exception as model_err:
            logging.error(f"Error during final model encoding batch: {model_err}", exc_info=True)

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
                    template="(%s, %s, %s::vector)",
                    page_size=len(db_batch)
                )
            conn.commit()
            logging.info("Final DB batch inserted successfully.")
        except psycopg2.Error as db_err:
            logging.error(f"Final database batch insert failed: {db_err}")
            conn.rollback()
        except Exception as general_db_err:
            logging.error(f"Unexpected error during final DB insert: {general_db_err}", exc_info=True)
            conn.rollback()

    if conn:
        conn.close()
        logging.info("Database connection closed.")

    overall_end_time = time.time()
    total_runtime = overall_end_time - overall_start_time
    processing_runtime = overall_end_time - process_start_time if 'process_start_time' in locals() else 0

    logging.info("\n--- Embedding Generation Complete ---")
    logging.info(f"Total Runtime: {time.strftime('%H:%M:%S', time.gmtime(total_runtime))}")
    logging.info(f"  (Pre-computation: {precompute_time:.2f}s)")
    if processing_runtime > 0:
        logging.info(f"  (Main Processing: {processing_runtime:.2f}s)")
    logging.info(f"Total Items Processed (estimate): {total_items_overall}")
    logging.info(f"Total Chunks Embedded: {chunks_processed_count}")
    if processing_runtime > 0 and chunks_processed_count > 0:
        avg_chunks_per_sec = chunks_processed_count / processing_runtime
        logging.info(f"Average Processing Throughput: {avg_chunks_per_sec:.2f} chunks/sec")
    elif chunks_processed_count > 0:
         logging.info("Processing runtime was zero or negative, cannot calculate throughput.")