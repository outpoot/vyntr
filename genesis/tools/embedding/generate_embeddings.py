import time
import glob
import json
import os
import torch
import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from transformers import AutoTokenizer, AutoModel, DataCollatorWithPadding
from tqdm import tqdm
import logging
from collections import defaultdict
from dotenv import load_dotenv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

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
DB_TABLE_NAME = "document_chunk_embeddings"
CHUNK_BATCH_SIZE = 1000
DB_BATCH_SIZE = 50000
MAX_SEQ_LENGTH = 512
CHUNK_OVERLAP = 50
SAFETY_BUFFER = 15
MAX_CPU_WORKERS = os.cpu_count()
ETA_UPDATE_INTERVAL_SEC = 10

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
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

def chunk_text_yield_token_ids(text, tokenizer, max_tokens, overlap):
    """Chunks text and yields lists of token IDs with length validation."""
    if not text:
        return

    num_special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
    effective_max_tokens = max(1, max_tokens - num_special_tokens - SAFETY_BUFFER)

    if effective_max_tokens <= overlap:
        overlap = max(0, effective_max_tokens // 4)

    if (max_tokens - num_special_tokens) <= 0:
        return

    try:
        tokens = tokenizer.encode(
            text,
            add_special_tokens=False,
            truncation=False
        )
    except Exception as e:
        logging.error(f"Failed to tokenize text (length {len(text)}): {e}")
        return

    if len(tokens) <= effective_max_tokens:
        if len(tokens) > max_tokens:
            logging.warning(f"Single chunk ({len(tokens)} tokens) exceeds max_tokens ({max_tokens}). Truncating.")
            yield tokens[:max_tokens]
        else:
            logging.debug(f"Input fits in one chunk ({len(tokens)} tokens).")
            yield tokens
        return

    stride = effective_max_tokens - overlap
    if stride <= 0:
        stride = max(1, effective_max_tokens // 2)

    current_pos = 0
    chunk_count = 0
    while current_pos < len(tokens):
        chunk_tokens = tokens[current_pos : current_pos + effective_max_tokens]
        if not chunk_tokens:
            break

        if len(chunk_tokens) > effective_max_tokens:
            logging.error(f"Chunk slice yielded {len(chunk_tokens)} tokens, exceeding effective_max_tokens {effective_max_tokens}. Truncating.")
            chunk_tokens = chunk_tokens[:effective_max_tokens]

        logging.debug(f"Yielding chunk {chunk_count} with {len(chunk_tokens)} tokens (effective_max={effective_max_tokens}).")
        yield chunk_tokens
        chunk_count += 1

        next_pos = current_pos + stride
        if next_pos <= current_pos:
            logging.error(f"Chunking loop stalled at position {current_pos}. Breaking.")
            break
        current_pos = next_pos

    logging.debug(f"Finished yielding {chunk_count} token ID chunks")

def process_file_yield_token_ids_fs(filepath, tokenizer, max_tokens, overlap):
    """Worker function yielding (url, chunk_id, List[int]) tuples."""
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

                    start_chunk_id = chunk_counts[url]
                    chunk_index = 0
                    for token_ids in chunk_text_yield_token_ids(
                        text, tokenizer, max_tokens, overlap
                    ):
                        yield (url, start_chunk_id + chunk_index, token_ids)
                        chunk_index += 1
                    chunk_counts[url] += chunk_index

                except json.JSONDecodeError:
                    logging.warning(f"Invalid JSON on line {line_num} in {filepath}")
                except Exception as e:
                    logging.warning(f"Error on line {line_num} in {filepath}: {e}")
    except Exception as e:
        logging.error(f"Failed to process file {filepath}: {e}")

def encode_batch_token_ids(model, tokenizer, batch_data, device, max_seq_len):
    """Encodes a batch of token ID lists with forced truncation."""
    try:
        token_id_lists = [item[2] for item in batch_data]
        batch_dicts = [{"input_ids": ids} for ids in token_id_lists]

        data_collator = DataCollatorWithPadding(
            tokenizer=tokenizer,
            padding='max_length',
            max_length=max_seq_len,
            return_tensors="pt"
        )
        inputs = data_collator(batch_dicts)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        logging.debug(f"Padded/Truncated batch shape: {inputs['input_ids'].shape}")

        with torch.no_grad():
            outputs = model(**inputs)

        embeddings = outputs.last_hidden_state.mean(dim=1)
        return embeddings.cpu().numpy()
    except Exception as e:
        logging.error(f"Error in encode_batch_token_ids: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    logging.info("--- Starting Embedding Generation from Filesystem ---")
    overall_start_time = time.time()

    # --- Model and Tokenizer Loading ---
    logging.info(f"Loading tokenizer: {MODEL_NAME}")
    model = None
    tokenizer = None
    device = "cpu"  # Default to CPU
    model_precision = "FP32" # Track precision for logging

    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logging.info(f"GPU detected: {gpu_name}. Attempting to load model in 8-bit.")
            try:
                # Requires bitsandbytes and accelerate libraries
                model = AutoModel.from_pretrained(
                    MODEL_NAME,
                    load_in_8bit=True,
                )
                # Check where the model was actually placed
                device = str(next(model.parameters()).device)
                model_precision = "INT8"
                logging.info(f"Successfully loaded model in 8-bit on {device}.")

            except ImportError:
                logging.warning(
                    "bitsandbytes or accelerate not installed. Falling back to default precision (FP32) on GPU."
                )
                device = "cuda"
                model = AutoModel.from_pretrained(MODEL_NAME)
                model.to(device)
                model_precision = "FP32"
            except Exception as e:
                logging.warning(
                    f"Failed to load model in 8-bit: {e}. Falling back to default precision (FP32) on GPU."
                )
                device = "cuda"
                model = AutoModel.from_pretrained(MODEL_NAME)
                model.to(device)
                model_precision = "FP32"
        else:
            logging.warning(
                "CUDA not available. Using CPU with default precision (FP32)."
            )
            device = "cpu"
            model = AutoModel.from_pretrained(MODEL_NAME)
            model_precision = "FP32"

        model.eval()  # Set model to evaluation mode
        embedding_dim = model.config.hidden_size
        logging.info(f"Model ready. Precision: {model_precision}. Device: {device}. Embedding Dim: {embedding_dim}")

    except Exception as e:
        logging.error(f"Model or Tokenizer loading failed: {e}", exc_info=True)
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
                    process_file_yield_token_ids_fs,
                    f,
                    tokenizer,
                    MAX_SEQ_LENGTH,
                    CHUNK_OVERLAP,
                ): f
                for f in all_files
            }

            for future in as_completed(submitted_futures):
                file_path = submitted_futures[future]
                try:
                    for url, chunk_id, token_ids in future.result():
                        if len(token_ids) > MAX_SEQ_LENGTH * 1.1:
                            logging.warning(f"Received abnormally long token list ({len(token_ids)} tokens) from chunker for {url} chunk {chunk_id}. Skipping.")
                            continue

                        model_input_batch.append((url, chunk_id, token_ids))

                        if len(model_input_batch) >= CHUNK_BATCH_SIZE:
                            batch_to_encode = model_input_batch[:CHUNK_BATCH_SIZE]
                            model_input_batch = model_input_batch[CHUNK_BATCH_SIZE:]

                            try:
                                embeddings = encode_batch_token_ids(
                                    model, tokenizer, batch_to_encode, device, MAX_SEQ_LENGTH
                                )

                                for j, (url_b, chunk_id_b, _) in enumerate(batch_to_encode):
                                    db_batch.append((url_b, chunk_id_b, embeddings[j].tolist()))
                                chunks_processed_count += len(batch_to_encode)

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
            batch_to_encode = model_input_batch
            try:
                embeddings = encode_batch_token_ids(
                    model, tokenizer, batch_to_encode, device, MAX_SEQ_LENGTH
                )

                for j, (url_b, chunk_id_b, _) in enumerate(batch_to_encode):
                    db_batch.append((url_b, chunk_id_b, embeddings[j].tolist()))
                chunks_processed_count += len(batch_to_encode)
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

    # --- Final Summary ---
    overall_end_time = time.time()
    total_runtime = overall_end_time - overall_start_time

    logging.info("\n--- Embedding Generation Complete ---")
    logging.info(
        f"Total Runtime: {time.strftime('%H:%M:%S', time.gmtime(total_runtime))}"
    )
    logging.info(f"Model Precision Used: {model_precision}")
    logging.info(f"Total Chunks Embedded: {chunks_processed_count}")
    logging.info(f"Total Files Processed: {files_processed_count}/{total_files}")