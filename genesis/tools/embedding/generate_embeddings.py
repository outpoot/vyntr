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
from collections import defaultdict
from dotenv import load_dotenv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError

# --- Load Environment Variables ---
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '.env'))
    logging.info(f"Attempting to load .env file from: {dotenv_path}")
    if not os.path.exists(dotenv_path):
         raise FileNotFoundError(f".env file not found at calculated path: {dotenv_path}")
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
ANALYSES_DIR_PATTERN = "../analyses/partition=*/*.jsonl"
DB_TABLE_NAME = "document_chunk_embeddings"  # Restored original table name
CHUNK_BATCH_SIZE = 1024  # Conservative initial size
DB_BATCH_SIZE = 5000  # Restored original batch size
MAX_SEQ_LENGTH = 512
CHUNK_OVERLAP = 50
SAFETY_BUFFER = 15  # Added missing configuration
MAX_CPU_WORKERS = os.cpu_count()
ETA_UPDATE_INTERVAL_SEC = 10
USE_QUANTIZATION = False  # Keep quantization disabled for now

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,  # Restored to INFO level
    format="%(asctime)s - %(levelname)s - %(message)s"
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
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '300s';")
        logging.info("Successfully connected to database")
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        raise


def create_table_if_not_exists(conn, embedding_dim):
    """Creates the chunk embeddings table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
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
    """
    Enhanced chunking with robust error handling and logging.
    """
    if not text:
        return []

    logging.debug(f"chunk_text_by_tokens received text of length {len(text)} chars")

    num_special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
    effective_max_tokens = max(1, max_tokens - num_special_tokens - SAFETY_BUFFER)

    if effective_max_tokens <= overlap:
        overlap = max(0, effective_max_tokens // 4)
        logging.debug(f"Overlap reduced to {overlap} due to effective_max_tokens limit")

    if (max_tokens - num_special_tokens) <= 0:
        logging.warning(f"max_tokens ({max_tokens}) too small. Skipping text.")
        return []

    try:
        tokens = tokenizer.encode(
            text, 
            add_special_tokens=False, 
            max_length=MAX_SEQ_LENGTH,
            truncation=True
        )
        logging.debug(f"Input text tokenized into {len(tokens)} tokens")
    except Exception as e:
        logging.error(f"Failed to tokenize input text (length {len(text)}): {e}")
        return []

    if len(tokens) <= effective_max_tokens:
        try:
            decoded_chunk = tokenizer.decode(tokens)
            logging.debug(f"Input fits in one chunk ({len(tokens)} tokens)")
            return [decoded_chunk]
        except Exception as decode_err:
            logging.warning(f"Failed to decode single chunk ({len(tokens)} tokens): {decode_err}")
            return []

    chunks = []
    stride = effective_max_tokens - overlap
    if stride <= 0:
        stride = max(1, effective_max_tokens // 2)
        logging.warning(f"Stride was <= 0, adjusted to {stride}")

    current_pos = 0
    chunk_count = 0
    while current_pos < len(tokens):
        chunk_tokens = tokens[current_pos : current_pos + effective_max_tokens]
        if not chunk_tokens:
            break

        try:
            decoded_chunk = tokenizer.decode(chunk_tokens)
            chunks.append(decoded_chunk)
            chunk_count += 1
            if chunk_count % 1000 == 0:
                logging.debug(f"Generated chunk {chunk_count} ({len(chunk_tokens)} tokens) at pos {current_pos}")
        except Exception as decode_err:
            logging.warning(f"Failed to decode chunk at pos {current_pos}: {decode_err}")
            current_pos += stride
            continue

        next_pos = current_pos + stride
        if next_pos <= current_pos:
            logging.error(f"Chunking loop stalled at position {current_pos}. Breaking.")
            break
        current_pos = next_pos

    logging.debug(f"Finished chunking {len(text)} chars into {len(chunks)} chunks")
    return chunks

def process_file_yield_chunks_fs(filepath, tokenizer, max_tokens, overlap):
    """
    Worker function to read local file, process, and yield (url, chunk_id, chunk_text).
    Returns the number of chunks yielded by this file.
    """
    chunk_counts = defaultdict(int)
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

                    chunks = chunk_text_by_tokens(
                        text, tokenizer, max_tokens, overlap
                    )
                    if not chunks:
                        continue

                    start_chunk_id = chunk_counts[url]
                    for i, chunk_text in enumerate(chunks):
                        yield (url, start_chunk_id + i, chunk_text)
                    chunk_counts[url] += len(chunks)

                except json.JSONDecodeError:
                    logging.warning(
                        f"Skipping invalid JSON on line {line_num} in {filepath}"
                    )
                except Exception as e:
                    logging.warning(
                        f"Error processing line {line_num} in {filepath}: {e}"
                    )
    except Exception as e:
        logging.error(f"Failed to open or process file {filepath}: {e}")

def encode_batch_hf_automodel(model, tokenizer, chunk_batch, device, max_seq_len):
    """Encode batch with simplified device logging."""
    try:
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

        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.cpu().numpy()
    except Exception as e:
        logging.error(f"Error in encode_batch_hf_automodel: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.info(
        "--- Starting Embedding Generation from Filesystem ---"
    )
    overall_start_time = time.time()

    # Model loading with simplified verification
    logging.info(f"Loading model and tokenizer: {MODEL_NAME}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
        model = AutoModel.from_pretrained(MODEL_NAME)
        
        if torch.cuda.is_available():
            device = "cuda"
            model.to(device)
            # Log device placement without comparison
            logging.info(f"Model moved to GPU. Example parameter device: {next(model.parameters()).device}")
        else:
            device = "cpu"
            logging.warning("CUDA not available. Using CPU.")

        model.eval()
        embedding_dim = model.config.hidden_size

    except Exception as e:
        logging.error(f"Model loading failed: {e}", exc_info=True)
        sys.exit(1)

    conn = connect_db()
    try:
        create_table_if_not_exists(conn, embedding_dim)

        # Find all files (no longer limiting to one)
        all_files = glob.glob(os.path.abspath(os.path.join(script_dir, ANALYSES_DIR_PATTERN)))
        if not all_files:
            logging.error("No files found.")
            sys.exit(1)
        total_files = len(all_files)
        logging.info(f"Found {total_files} files to process.")

        # --- Start Processing (Parallel) ---
        process_start_time = time.time()
        chunks_processed_count = 0
        files_processed_count = 0
        db_batch = []
        model_input_batch = []
        last_eta_print_time = time.time()

        pbar_total = max(1, total_files)
        pbar_unit = "file"
        pbar = tqdm(total=pbar_total, desc="Processing", unit=pbar_unit)

        with ThreadPoolExecutor(max_workers=MAX_CPU_WORKERS) as executor:
            submitted_futures = {
                executor.submit(
                    process_file_yield_chunks_fs,
                    f,
                    tokenizer,
                    MAX_SEQ_LENGTH,
                    CHUNK_OVERLAP,
                ): f
                for f in all_files
            }
            active_iterators = []
            completed_futures_queue = []

            for future in as_completed(submitted_futures):
                file_path = submitted_futures[future]
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

                                for j, (url_b, chunk_id_b, _) in enumerate(batch_to_encode_data):
                                    db_batch.append((url_b, chunk_id_b, embeddings[j].tolist()))
                                chunks_processed_count += len(batch_to_encode_data)

                            except Exception as model_err:
                                logging.error(f"Fatal model error: {model_err}", exc_info=True)
                                sys.exit(1)

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
                                            page_size=len(db_batch),
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

                    files_processed_count += 1
                    pbar.update(1)

                except Exception as e:
                    logging.error(f"Error processing file {file_path}: {e}", exc_info=True)

        if model_input_batch:
            batch_texts = [item[2] for item in model_input_batch]
            try:
                embeddings = encode_batch_hf_automodel(
                    model, tokenizer, batch_texts, device, MAX_SEQ_LENGTH
                )

                for j, (url_b, chunk_id_b, _) in enumerate(model_input_batch):
                    db_batch.append((url_b, chunk_id_b, embeddings[j].tolist()))
                chunks_processed_count += len(model_input_batch)
            except Exception as model_err:
                logging.error(f"Fatal model error: {model_err}", exc_info=True)
                sys.exit(1)

        if db_batch:
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
                        page_size=len(db_batch),
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

    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

    overall_end_time = time.time()
    total_runtime = overall_end_time - overall_start_time

    logging.info("\n--- Embedding Generation Complete ---")
    logging.info(
        f"Total Runtime: {time.strftime('%H:%M:%S', time.gmtime(total_runtime))}"
    )
    logging.info(f"Total Chunks Embedded: {chunks_processed_count}")
    logging.info(f"Total Files Processed: {files_processed_count}")