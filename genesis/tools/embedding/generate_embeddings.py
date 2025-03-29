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
from botocore.exceptions import ClientError
from botocore.config import Config
# Import AWSRequest for type hinting if desired
# from botocore.awsrequest import AWSRequest
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
MAX_CPU_WORKERS = os.cpu_count() or 4 # for S3 I/O and chunking
ETA_UPDATE_INTERVAL_SEC = 10 # how often to print ETA

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
    # Check if headers exist before deleting to avoid potential KeyErrors
    # if they aren't added by boto3 for a specific request type.
    if 'x-amz-checksum-mode' in request.headers:
        # logging.debug(f"Removing x-amz-checksum-mode from request: {request.method} {request.url}")
        del request.headers['x-amz-checksum-mode']
    if 'x-amz-checksum-crc32' in request.headers:
        # logging.debug(f"Removing x-amz-checksum-crc32 from request: {request.method} {request.url}")
        del request.headers['x-amz-checksum-crc32']
    # Add others here if needed, e.g., x-amz-checksum-sha256, etc.
def get_s3_client():
    """Initializes and returns a boto3 S3 client with header modification."""
    try:
        session = boto3.Session()
        # Register the event handler to modify requests before sending
        # 'before-send.*' catches events for all services,
        # 'before-send.s3.*' would be specific to S3 operations.
        session.events.register('before-send.*', remove_unsupported_headers)

        s3_client = session.client(
            's3',
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=S3_REGION
            # Optional: Explicitly set signature version if needed, though v4 is default
            # config=boto3.session.Config(signature_version='s3v4')
        )
        # Test connection briefly (ListBuckets might not use checksums,
        # but it's a basic connectivity check)
        s3_client.list_buckets()
        logging.info(f"Successfully connected to S3 endpoint: {S3_ENDPOINT_URL}")
        return s3_client
    except ClientError as e:
        # Catch potential connection errors during client creation/test
        logging.error(f"Failed to connect to S3 or initial test failed: {e}")
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
        # First, find all partition folders
        partitions = set()
        # Use Delimiter='/' to find common prefixes (folders)
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter='/'):
            if 'CommonPrefixes' in page:
                for prefix_obj in page['CommonPrefixes']:
                    prefix_path = prefix_obj['Prefix']
                    # Check if it looks like a partition folder
                    if prefix_path.endswith('/') and '=' in prefix_path.split('/')[-2]:
                         partitions.add(prefix_path)

        if not partitions:
            logging.warning(f"No partition folders found directly under s3://{bucket}/{prefix}. Listing files directly in prefix.")
            # Fall back to direct file listing in prefix if no partitions found
            for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        # Ensure it's not a 'directory' object and ends with .jsonl
                        if not key.endswith('/') and key.lower().endswith('.jsonl'):
                            jsonl_files.append(key)
        else:
            logging.info(f"Found {len(partitions)} potential partition folders. Scanning within them...")
            # List files within each identified partition prefix
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
        # Find the part that looks like partition=value
        for part in reversed(parts):
            if '=' in part:
                partition_name = part # Or split further if needed: part.split('=')[1]
                break
        partition_counts[partition_name] += 1


    logging.info(f"Found {len(jsonl_files)} total .jsonl files across {len(partition_counts)} detected partitions/groups:")
    for p_name, count in sorted(partition_counts.items()):
        logging.info(f"  - {p_name}: {count} files")

    if not jsonl_files:
         logging.warning(f"No .jsonl files were ultimately found in s3://{bucket}/{prefix} or its subdirectories.")

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
                 # Log less verbosely for common JSON errors unless debugging
                 # logging.debug(f"Skipping invalid JSON line in {s3_key}")
                 pass
            except Exception as line_exc:
                 logging.warning(f"Error processing line in {s3_key}: {line_exc}")
                 pass # Continue processing other lines
        body.close() # Ensure the body is closed
    except ClientError as e:
        # Check for the specific error if possible, otherwise log generically
        error_code = e.response.get('Error', {}).get('Code')
        logging.warning(f"S3 ClientError ({error_code}) during precompute for {s3_key}: {e}")
    except Exception as e:
        logging.warning(f"Precompute failed for {s3_key}: {e}")
    return item_count, chunk_count

def process_s3_object_yield_chunks(s3_client, bucket, s3_key, tokenizer, max_tokens, overlap):
    """Worker function to read S3 object, process, and yield (url, chunk_id, chunk_text)."""
    # Keep track of chunk IDs per URL *within this file*
    chunk_counts_in_file = defaultdict(int)
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
                if not url:
                    # logging.debug(f"Skipping line {line_num} in {s3_key}: missing URL")
                    continue

                text = extract_relevant_text(entry)
                if not text:
                    # logging.debug(f"Skipping line {line_num} in {s3_key} (URL: {url}): no text extracted")
                    continue

                chunks = chunk_text_by_tokens(text, tokenizer, max_tokens, overlap)
                if not chunks:
                    # logging.debug(f"Skipping line {line_num} in {s3_key} (URL: {url}): no chunks generated")
                    continue

                # Assign chunk IDs sequentially for this URL within this file's processing context
                start_chunk_id = chunk_counts_in_file[url]
                for i, chunk_text in enumerate(chunks):
                    yield (url, start_chunk_id + i, chunk_text)
                chunk_counts_in_file[url] += len(chunks) # Update count for the next potential entry with the same URL in this file

            except UnicodeDecodeError:
                logging.warning(f"Skipping line {line_num} due to decode error in {s3_key}")
            except json.JSONDecodeError:
                logging.warning(f"Skipping invalid JSON on line {line_num} in {s3_key}")
            except Exception as e:
                logging.warning(f"Error processing line {line_num} in {s3_key}: {e}")
        body.close() # Ensure the body is closed
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        logging.error(f"S3 ClientError ({error_code}) processing object {s3_key}: {e}")
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
    # Mean pooling: Average the token embeddings across the sequence length dimension
    embeddings = outputs.last_hidden_state.mean(dim=1)
    # Ensure embeddings are on CPU and converted to numpy for DB insertion
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
        # Ensure trust_remote_code=True if model requires it, but be cautious
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
        model = AutoModel.from_pretrained(MODEL_NAME)
        model.to(device)
        embedding_dim = model.config.hidden_size # Get embedding dimension

        # Try FP16 only on CUDA
        if device == 'cuda':
            try:
                model.half()
                logging.info("Applied .half() to model for potential FP16 speedup.")
            except Exception as fp16_err:
                logging.warning(f"Could not apply .half(): {fp16_err}. Using FP32.")
        model.eval() # Set model to evaluation mode
    except Exception as e:
        logging.error(f"Failed to load model/tokenizer: {e}", exc_info=True)
        exit(1)

    conn = connect_db()
    create_table_if_not_exists(conn, embedding_dim)

    # S3 Client Setup (now uses the updated function with before-sign hook)
    s3_client = get_s3_client()

    logging.info("Phase 1: Listing S3 files and pre-computing total chunks for ETA...")
    precompute_start_time = time.time()
    try:
        all_s3_keys = list_s3_files(s3_client, S3_BUCKET, S3_PREFIX)
    except Exception as e:
        logging.error(f"Failed during S3 listing or client creation: {e}", exc_info=True)
        if conn: conn.close() # Ensure DB connection is closed on early exit
        exit(1)

    if not all_s3_keys:
        logging.error(f"No .jsonl files found in s3://{S3_BUCKET}/{S3_PREFIX}. Exiting.")
        if conn: conn.close()
        exit(1)

    # Group files by partition for potentially better progress tracking / organization
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

    # Precompute counts per partition first
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
                    # Log the specific file key along with the exception
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
    model_input_batch = [] # Stores tuples: (url, chunk_id, chunk_text)
    last_eta_print_time = time.time()

    # Process each partition sequentially for embedding
    for partition_name, partition_files in partition_groups.items():
        partition_total_chunks = partition_chunk_estimates.get(partition_name, 0)
        if partition_total_chunks == 0:
            logging.info(f"\nSkipping partition {partition_name} as it has 0 estimated chunks.")
            continue

        logging.info(f"\nProcessing partition: {partition_name} (Est. Chunks: {partition_total_chunks})")
        partition_chunks_processed = 0
        pbar = tqdm(total=partition_total_chunks, desc=f"Embedding ({partition_name})", unit="chunk")

        # Use ThreadPoolExecutor for reading/chunking S3 files in parallel
        with ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS, thread_name_prefix=f'Process_{partition_name[:10]}') as executor:
            # Submit tasks to yield chunks from each file
            chunk_futures = {
                executor.submit(process_s3_object_yield_chunks, s3_client, S3_BUCKET, key, tokenizer, MAX_SEQ_LENGTH, CHUNK_OVERLAP): key
                for key in partition_files
            }

            # Process results as they become available
            for future in as_completed(chunk_futures):
                key = chunk_futures[future]
                try:
                    # Iterate through chunks yielded by the worker
                    for url, chunk_id, chunk_text in future.result():
                        model_input_batch.append((url, chunk_id, chunk_text))

                        # --- Batch Encoding ---
                        if len(model_input_batch) >= CHUNK_BATCH_SIZE:
                            # Take a full batch
                            batch_to_encode_data = model_input_batch[:CHUNK_BATCH_SIZE]
                            # Keep the remainder
                            model_input_batch = model_input_batch[CHUNK_BATCH_SIZE:]

                            batch_texts = [item[2] for item in batch_to_encode_data]

                            try:
                                embeddings = encode_batch_hf_automodel(
                                    model, tokenizer, batch_texts, device, MAX_SEQ_LENGTH
                                )
                                # No need to sync explicitly here unless debugging timing issues

                                # Prepare for DB batch insert
                                for i, (url_b, chunk_id_b, _) in enumerate(batch_to_encode_data):
                                    # Ensure embedding is a list or tuple for psycopg2
                                    db_batch.append((url_b, chunk_id_b, embeddings[i].tolist()))

                                # Update progress
                                batch_size = len(batch_to_encode_data)
                                chunks_processed_count += batch_size
                                partition_chunks_processed += batch_size
                                pbar.update(batch_size)

                                # --- ETA Calculation ---
                                current_time = time.time()
                                if current_time - last_eta_print_time > ETA_UPDATE_INTERVAL_SEC:
                                    elapsed_proc_time = current_time - process_start_time
                                    if chunks_processed_count > 0 and elapsed_proc_time > 1:
                                        # Use overall progress for ETA calculation
                                        chunks_per_sec = chunks_processed_count / elapsed_proc_time
                                        chunks_remaining = total_chunks_overall - chunks_processed_count
                                        # Prevent division by zero or negative remaining chunks
                                        if chunks_per_sec > 0 and chunks_remaining > 0:
                                            eta_seconds = chunks_remaining / chunks_per_sec
                                            eta_formatted = time.strftime('%H:%M:%S', time.gmtime(eta_seconds))
                                        else:
                                             eta_formatted = "N/A" if chunks_per_sec <=0 else "Done"

                                        pbar.set_postfix_str(f"Overall Rate: {chunks_per_sec:.1f} c/s, ETA: {eta_formatted}, DB Batch: {len(db_batch)}")
                                        last_eta_print_time = current_time

                            except Exception as model_err:
                                logging.error(f"Error during model encoding batch: {model_err}", exc_info=True)
                                # Still update pbar to avoid getting stuck if errors occur
                                pbar.update(len(batch_to_encode_data)) # Use actual batch size attempted


                        # --- Batch DB Insert ---
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
                                        template="(%s, %s, %s::vector)", # Cast embedding explicitly
                                        page_size=DB_BATCH_SIZE # Optional: control internal batching
                                    )
                                conn.commit()
                                # logging.debug(f"Inserted batch of {len(db_batch)} embeddings.")
                                db_batch = [] # Clear the batch
                            except psycopg2.Error as db_err:
                                logging.error(f"Database batch insert failed: {db_err}")
                                conn.rollback() # Rollback the failed transaction
                                # Consider adding a retry mechanism or exiting if DB errors persist
                                db_batch = [] # Clear the batch even on error to avoid re-inserting bad data
                            except Exception as general_db_err:
                                 logging.error(f"Unexpected error during DB insert: {general_db_err}", exc_info=True)
                                 conn.rollback()
                                 db_batch = []


                except GeneratorExit:
                     # This can happen if the main thread exits while the generator is running
                     logging.warning(f"GeneratorExit caught for file {key}. Main thread likely shutting down.")
                     break # Exit the loop for this future
                except Exception as future_exc:
                    logging.error(f"Chunk processing task for file '{key}' generated an exception: {future_exc}", exc_info=True)

        pbar.close() # Close progress bar for the partition
        # Make sure final partition progress is accurate if loop finishes early
        pbar.refresh()
        logging.info(f"Finished processing partition {partition_name}. Processed {partition_chunks_processed} chunks.")


    # --- Final Processing ---
    logging.info("Processing any remaining chunks in the final batches...")

    # Process remaining items in model_input_batch
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

    # Insert any remaining items in db_batch
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
                    template="(%s, %s, %s::vector)", # Cast embedding explicitly
                    page_size=len(db_batch) # Process the whole remaining batch
                )
            conn.commit()
            logging.info("Final DB batch inserted successfully.")
        except psycopg2.Error as db_err:
            logging.error(f"Final database batch insert failed: {db_err}")
            conn.rollback()
        except Exception as general_db_err:
            logging.error(f"Unexpected error during final DB insert: {general_db_err}", exc_info=True)
            conn.rollback()


    # --- Cleanup and Summary ---
    if conn:
        conn.close()
        logging.info("Database connection closed.")

    overall_end_time = time.time()
    total_runtime = overall_end_time - overall_start_time
    # Ensure process_start_time was set
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