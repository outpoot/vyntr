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
from collections import defaultdict
from dotenv import load_dotenv
import sys

# --- Load Environment Variables ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.abspath(os.path.join(script_dir, "..", "..", "..", ".env"))
    logging.info(f"Attempting to load .env file from: {dotenv_path}")
    if not os.path.exists(dotenv_path):
        raise FileNotFoundError(
            f".env file not found at calculated path: {dotenv_path}"
        )
    load_dotenv(dotenv_path=dotenv_path)
    logging.info(".env file loaded successfully.")
except FileNotFoundError as e:
    logging.error(f"Error loading .env file: {e}")
    sys.exit(1)
except Exception as e:
    logging.error(f"An unexpected error occurred loading .env: {e}")
    sys.exit(1)

# --- Configuration ---
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
ANALYSES_DIR_PATTERN = "../analyses/partition=*/*.jsonl"  # Filesystem pattern
DB_TABLE_NAME = "document_chunk_embeddings"
CHUNK_BATCH_SIZE = 2048
DB_BATCH_SIZE = 4096
MAX_SEQ_LENGTH = 256
CHUNK_OVERLAP = 50
MAX_CPU_WORKERS = min((os.cpu_count() or 4), 8)
ETA_UPDATE_INTERVAL_SEC = 10

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Database Configuration ---
PRIVATE_DB_URL = os.getenv("PRIVATE_DB_URL")
if not PRIVATE_DB_URL:
    logging.error("Database URL not configured (PRIVATE_DB_URL). Exiting.")
    sys.exit(1)


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


def load_processed_chunks(conn):
    """Queries the database and returns a set of (url, chunk_id) tuples already processed."""
    processed_chunks = set()
    try:
        with conn.cursor() as cur:
            logging.info(f"Querying DB for already processed chunks in '{DB_TABLE_NAME}'...")
            start_time = time.time()
            
            cur.execute(f"SELECT url, chunk_id FROM {DB_TABLE_NAME};")
            rows = cur.fetchall()
            processed_chunks.update(rows)
            
            end_time = time.time()
            logging.info(f"Loaded {len(processed_chunks):,} existing chunk identifiers in {end_time - start_time:.2f} seconds.")
            return processed_chunks

    except psycopg2.Error as e:
        logging.error(f"Database error loading processed chunks: {e}", exc_info=True)
        raise  # Re-raise to handle in main
    except Exception as e:
        logging.error(f"Unexpected error loading processed chunks: {e}", exc_info=True)
        raise  # Re-raise to handle in main


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
    combined_text = (
        f"Title: {title}\nDescription: {description}\nContent: {content}".strip()
    )
    return combined_text


def chunk_text_by_tokens(text, tokenizer, max_tokens, overlap):
    """Chunks text based on token count using the model's tokenizer."""
    if not text:
        return []
    # Tokenizer is essential here for accurate chunking based on model limits
    tokens = tokenizer.encode(text, add_special_tokens=False, truncation=False)
    if len(tokens) <= max_tokens:
        return [tokenizer.decode(tokens)]

    chunks = []
    stride = max_tokens - overlap
    if stride <= 0:
        stride = max(1, max_tokens // 2)

    for i in range(0, len(tokens), stride):
        chunk_tokens = tokens[i : i + max_tokens]
        chunks.append(tokenizer.decode(chunk_tokens))
        if i + max_tokens >= len(tokens):
            break
    return chunks


# --- Worker Function (Filesystem) ---
def process_file_yield_chunks_fs(filepath, tokenizer, max_tokens, overlap):
    """Worker function to read local file, process, and yield (url, chunk_id, chunk_text)."""
    chunk_counts = defaultdict(int)
    processed_successfully = False  # Flag to track if at least one chunk was yielded
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)
                    url = entry.get("url")
                    if not url:
                        continue

                    text = extract_relevant_text(entry)
                    if not text:
                        continue

                    chunks = chunk_text_by_tokens(text, tokenizer, max_tokens, overlap)
                    if not chunks:
                        continue

                    start_chunk_id = chunk_counts[url]
                    for i, chunk_text in enumerate(chunks):
                        yield (url, start_chunk_id + i, chunk_text)
                        processed_successfully = (
                            True  # Mark success if we yield anything
                        )
                    chunk_counts[url] += len(chunks)

                except json.JSONDecodeError:
                    logging.warning(
                        f"Skipping invalid JSON on line {line_num} in {filepath}"
                    )
                except Exception as e:
                    logging.warning(
                        f"Error processing line {line_num} in {filepath}: {e}"
                    )
        # Return True if the file was processed (at least partially), False otherwise
        return processed_successfully
    except Exception as e:
        logging.error(f"Failed to open or process file {filepath}: {e}")
        return False  # Indicate failure for this file


# --- Encoding Function ---
def encode_batch_hf_automodel(model, tokenizer, chunk_batch, device, max_seq_len):
    """Encode batch using standard Hugging Face AutoModel."""
    inputs = tokenizer(
        chunk_batch,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_seq_len,
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
    return embeddings


# --- Main Execution ---
if __name__ == "__main__":
    logging.info(
        "--- Starting Embedding Generation from Filesystem (No Pre-computation) ---"
    )
    overall_start_time = time.time()

    # --- Setup ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Using device: {device}")
    if device == "cpu":
        logging.warning("Running on CPU, this will be significantly slower!")

    # Load Model & Tokenizer (Tokenizer is needed for chunking)
    logging.info(f"Loading model and tokenizer: {MODEL_NAME}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
        model = AutoModel.from_pretrained(MODEL_NAME)
        model.to(device)
        embedding_dim = model.config.hidden_size

        if device == "cuda":
            try:
                model.half()
                logging.info("Applied .half() to model for FP16.")
            except Exception as fp16_err:
                logging.warning(f"Could not apply .half(): {fp16_err}. Using FP32.")
        model.eval()
    except Exception as e:
        logging.error(f"Failed to load model/tokenizer: {e}", exc_info=True)
        sys.exit(1)

    # Database Setup and Loading Existing Chunks
    conn = None
    try:
        conn = connect_db()
        create_table_if_not_exists(conn, embedding_dim)
        
        # Load existing chunks - this is required for resumption/deduplication
        try:
            processed_chunks_set = load_processed_chunks(conn)
            if not isinstance(processed_chunks_set, set):
                raise ValueError("load_processed_chunks did not return a set")
            logging.info(f"Successfully loaded {len(processed_chunks_set):,} existing chunks for deduplication.")
        except Exception as e:
            logging.error("Failed to load existing chunks from database. This is required for correct operation.")
            logging.error(f"Error details: {e}")
            sys.exit(1)

        # --- Find Files ---
        logging.info(f"Finding files matching '{ANALYSES_DIR_PATTERN}'...")
        base_search_path = os.path.join(".", ANALYSES_DIR_PATTERN)
        all_files = glob.glob(base_search_path, recursive=True)
        total_files = len(all_files)

        if not all_files:
            logging.error(f"No .jsonl files found matching pattern: {base_search_path}")
            sys.exit(1)
        logging.info(f"Found {total_files} files to process.")

        # --- Start Processing ---
        logging.info("Starting main processing (Embedding and DB Insert)...")
        process_start_time = time.time()
        chunks_to_process_count = 0  # Chunks added to model batch
        chunks_skipped_count = 0  # Chunks skipped due to checkpoint
        files_processed_count = 0  # Track processed files for ETA
        db_batch = []
        model_input_batch = []  # Stores (url, chunk_id, chunk_text)
        last_eta_print_time = time.time()

        # Setup tqdm progress bar based on FILES
        pbar = tqdm(total=total_files, desc="Processing Files", unit="file")

        with ThreadPoolExecutor(
            max_workers=MAX_CPU_WORKERS, thread_name_prefix="Process"
        ) as executor:
            future_to_file = {
                executor.submit(
                    process_file_yield_chunks_fs,
                    f,
                    tokenizer,
                    MAX_SEQ_LENGTH,
                    CHUNK_OVERLAP,
                ): f
                for f in all_files
            }

            for future in as_completed(future_to_file):
                filepath = future_to_file[future]
                try:
                    # Iterate through the generator returned by the worker
                    for url, chunk_id, chunk_text in future.result():
                        # <<< --- Checkpoint Check --- >>>
                        if (url, chunk_id) in processed_chunks_set:
                            chunks_skipped_count += 1
                            # logging.debug(f"Skipping existing chunk: ({url}, {chunk_id})") # Optional: very verbose
                            continue  # Skip to the next chunk

                        # If not skipped, add to batch for encoding
                        model_input_batch.append((url, chunk_id, chunk_text))

                        # --- Process Model Batch ---
                        if len(model_input_batch) >= CHUNK_BATCH_SIZE:
                            batch_to_encode_data = model_input_batch[:CHUNK_BATCH_SIZE]
                            model_input_batch = model_input_batch[CHUNK_BATCH_SIZE:]

                            batch_texts = [item[2] for item in batch_to_encode_data]

                            try:
                                embeddings = encode_batch_hf_automodel(
                                    model,
                                    tokenizer,
                                    batch_texts,
                                    device,
                                    MAX_SEQ_LENGTH,
                                )
                                if device == "cuda":
                                    torch.cuda.synchronize()

                                for i, (
                                    url_b,
                                    chunk_id_b,
                                    _,
                                ) in enumerate(batch_to_encode_data):
                                    db_batch.append(
                                        (
                                            url_b,
                                            chunk_id_b,
                                            embeddings[i].tolist(),
                                        )
                                    )

                                chunks_to_process_count += len(batch_to_encode_data)

                            except Exception as model_err:
                                logging.error(
                                    f"Error during model encoding batch (file: {filepath}): {model_err}",
                                    exc_info=True,
                                )

                        # --- Process DB Batch ---
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
                                        page_size=DB_BATCH_SIZE,
                                    )
                                conn.commit()
                                # Add processed chunks to the set *after* successful commit
                                for url_db, chunk_id_db, _ in db_batch:
                                    processed_chunks_set.add((url_db, chunk_id_db))
                                db_batch = []
                            except psycopg2.Error as db_err:
                                logging.error(f"Database batch insert failed: {db_err}")
                                conn.rollback()
                                # Don't clear db_batch, maybe retry later? Or clear and log loss.
                                # For simplicity here, we clear it, potentially losing this batch on error.
                                db_batch = []
                            except Exception as general_db_err:
                                logging.error(
                                    f"Unexpected error during DB insert: {general_db_err}",
                                    exc_info=True,
                                )
                                conn.rollback()
                                db_batch = []

                except GeneratorExit:
                    logging.warning(
                        f"GeneratorExit caught for file {filepath}. Main thread likely shutting down."
                    )
                    break  # Exit loop over futures
                except Exception as future_exc:
                    logging.error(
                        f"Chunk processing task for file '{filepath}' generated an exception: {future_exc}",
                        exc_info=True,
                    )

                # --- Update File Progress and ETA ---
                files_processed_count += 1
                pbar.update(1)
                current_time = time.time()
                if current_time - last_eta_print_time > ETA_UPDATE_INTERVAL_SEC:
                    elapsed_proc_time = current_time - process_start_time
                    if files_processed_count > 0 and elapsed_proc_time > 1:
                        files_per_sec = files_processed_count / elapsed_proc_time
                        # Base ETA on files, as chunk rate varies with skipping
                        files_remaining = total_files - files_processed_count
                        if files_per_sec > 0 and files_remaining > 0:
                            eta_seconds = files_remaining / files_per_sec
                            eta_formatted = time.strftime(
                                "%H:%M:%S", time.gmtime(eta_seconds)
                            )
                        else:
                            eta_formatted = "N/A" if files_per_sec <= 0 else "Done"

                        # Display both processed and skipped counts
                        pbar.set_postfix_str(
                            f"Files: {files_processed_count}/{total_files}, "
                            f"Processed: {chunks_to_process_count:,}, "
                            f"Skipped: {chunks_skipped_count:,}, "
                            f"ETA: {eta_formatted}"
                        )
                        last_eta_print_time = current_time

        # --- Process Final Batches ---
        logging.info("Processing final batches...")
        # Final Model Batch
        if model_input_batch:
            try:
                logging.info(
                    f"Encoding final model batch of {len(model_input_batch)} chunks..."
                )
                batch_texts = [item[2] for item in model_input_batch]
                embeddings = encode_batch_hf_automodel(
                    model, tokenizer, batch_texts, device, MAX_SEQ_LENGTH
                )
                if device == "cuda":
                    torch.cuda.synchronize()

                for i, (url_b, chunk_id_b, _) in enumerate(model_input_batch):
                    db_batch.append((url_b, chunk_id_b, embeddings[i].tolist()))

                chunks_to_process_count += len(model_input_batch)
                logging.info(
                    f"Encoded final model batch. Total chunks processed in this run: {chunks_to_process_count:,}"
                )
            except Exception as model_err:
                logging.error(
                    f"Error during final model encoding batch: {model_err}",
                    exc_info=True,
                )

        pbar.close()  # Close progress bar

        # Final DB Batch
        if db_batch:
            try:
                logging.info(
                    f"Inserting final batch of {len(db_batch)} embeddings into DB..."
                )
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
                        page_size=len(db_batch),  # Process the whole remaining batch
                    )
                conn.commit()
                # Add final batch to processed set
                for url_db, chunk_id_db, _ in db_batch:
                    processed_chunks_set.add((url_db, chunk_id_db))
                logging.info("Final DB batch inserted successfully.")
            except psycopg2.Error as db_err:
                logging.error(f"Final database batch insert failed: {db_err}")
                conn.rollback()
            except Exception as general_db_err:
                logging.error(
                    f"Unexpected error during final DB insert: {general_db_err}",
                    exc_info=True,
                )
                conn.rollback()

    finally:  # Ensure DB connection is closed even if errors occur
        if conn:
            conn.close()
            logging.info("Database connection closed.")

    # --- Wrap Up ---
    overall_end_time = time.time()
    total_runtime = overall_end_time - overall_start_time
    processing_runtime = (
        overall_end_time - process_start_time if "process_start_time" in locals() else 0
    )

    logging.info("\n--- Embedding Generation Complete ---")
    logging.info(
        f"Total Runtime: {time.strftime('%H:%M:%S', time.gmtime(total_runtime))}"
    )
    if processing_runtime > 0:
        logging.info(f"  (Main Processing: {processing_runtime:.2f}s)")
    logging.info(f"Total Files Scanned: {files_processed_count}/{total_files}")
    logging.info(
        f"Chunks Processed (Encoded & Upserted) in this run: {chunks_to_process_count:,}"
    )
    logging.info(f"Chunks Skipped (Already in DB): {chunks_skipped_count:,}")
    total_chunks_in_db = len(processed_chunks_set)  # Get final count from the set
    logging.info(f"Estimated Total Chunks Now in DB: {total_chunks_in_db:,}")

    if processing_runtime > 0 and chunks_to_process_count > 0:
        avg_chunks_per_sec = chunks_to_process_count / processing_runtime
        logging.info(
            f"Average Processing Throughput (This Run): {avg_chunks_per_sec:.2f} chunks/sec"
        )
    elif chunks_to_process_count > 0:
        logging.info(
            "Processing runtime was zero or negative, cannot calculate throughput."
        )
