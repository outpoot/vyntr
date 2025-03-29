import time
import glob
import json
import os
import numpy as np
import torch
import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from transformers import AutoTokenizer, AutoModel, BitsAndBytesConfig
from tqdm import tqdm
import math
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from collections import defaultdict
from dotenv import load_dotenv
import sys

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
ANALYSES_DIR_PATTERN = "../analyses/partition=*/*.jsonl"  # Filesystem pattern
DB_TABLE_NAME = "document_chunk_embeddings"
CHUNK_BATCH_SIZE = 2048
DB_BATCH_SIZE = 5000
MAX_SEQ_LENGTH = 512
CHUNK_OVERLAP = 50
MAX_CPU_WORKERS = os.cpu_count()
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

def estimate_chunks_in_file_fast(filepath, approx_chars_per_chunk):
    """Estimates chunks based on character count, avoiding tokenization."""
    count = 0
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    text = extract_relevant_text(entry)
                    if text:
                        count += math.ceil(len(text) / approx_chars_per_chunk)
                except json.JSONDecodeError:
                    pass
                except Exception:
                    pass
    except Exception as e:
        logging.debug(f"Ignoring error during fast estimation for {filepath}: {e}")
        pass
    return count

def chunk_text_by_tokens(text, tokenizer, max_tokens, overlap):
    """
    Chunks text based on token count with safety buffer to prevent overflow.
    """
    if not text:
        return []

    SAFETY_BUFFER = 5  # Reduce target length for safety
    num_special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
    effective_max_tokens = max(1, max_tokens - num_special_tokens - SAFETY_BUFFER)

    if effective_max_tokens <= overlap:
        overlap = max(0, effective_max_tokens // 4)
        logging.debug(f"Overlap reduced to {overlap} due to effective_max_tokens limit.")

    if (max_tokens - num_special_tokens) <= 0:
        logging.warning(
            f"max_tokens ({max_tokens}) too small for special tokens ({num_special_tokens})."
        )
        return []

    tokens = tokenizer.encode(text, add_special_tokens=False, truncation=False)

    if len(tokens) <= effective_max_tokens:
        return [tokenizer.decode(tokens)]

    chunks = []
    stride = effective_max_tokens - overlap
    if stride <= 0:
        stride = max(1, effective_max_tokens // 2)
        logging.warning(f"Stride was <= 0, adjusted to {stride}")

    current_pos = 0
    while current_pos < len(tokens):
        chunk_tokens = tokens[current_pos : current_pos + effective_max_tokens]
        if not chunk_tokens:
            break
        chunks.append(tokenizer.decode(chunk_tokens))
        if current_pos + effective_max_tokens >= len(tokens):
            break
        current_pos += stride

    return chunks

def process_file_yield_chunks_fs(filepath, tokenizer, max_tokens, overlap):
    """
    Worker function to read local file, process, and yield (url, chunk_id, chunk_text).
    Returns the number of chunks yielded by this file.
    """
    chunk_counts = defaultdict(int)
    total_chunks_yielded = 0
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
                    total_chunks_yielded += len(chunks)

                except json.JSONDecodeError:
                    logging.warning(
                        f"Skipping invalid JSON on line {line_num} in {filepath}"
                    )
                except Exception as e:
                    logging.warning(
                        f"Error processing line {line_num} in {filepath}: {e}"
                    )
        return total_chunks_yielded
    except Exception as e:
        logging.error(f"Failed to open or process file {filepath}: {e}")
        return 0


def encode_batch_hf_automodel(
    model, tokenizer, chunk_batch, device, max_seq_len
):
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
    embeddings = outputs.last_hidden_state.mean(dim=1)
    embeddings = embeddings.cpu().numpy()
    return embeddings


if __name__ == "__main__":
    logging.info(
        "--- Starting Embedding Generation from Filesystem (No Pre-computation) ---"
    )
    overall_start_time = time.time()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logging.info(f"Using device: {device}")
    if device == "cpu":
        logging.warning("Running on CPU, this will be significantly slower!")

    logging.info(f"Loading model and tokenizer: {MODEL_NAME}")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
        
        # Configure 8-bit quantization
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=True,
        )

        model = AutoModel.from_pretrained(
            MODEL_NAME,
            quantization_config=quantization_config,
            device_map="auto"  # Let bitsandbytes handle device mapping
        )
        embedding_dim = model.config.hidden_size
        model.eval()
        logging.info("Loaded model with 8-bit quantization.")
    except Exception as e:
        logging.error(f"Failed to load model/tokenizer (check bitsandbytes install?): {e}", exc_info=True)
        sys.exit(1)

    conn = connect_db()
    try:
        create_table_if_not_exists(conn, embedding_dim)

        logging.info(f"Finding files matching '{ANALYSES_DIR_PATTERN}'...")
        base_search_path = os.path.abspath(
            os.path.join(script_dir, ANALYSES_DIR_PATTERN)
        )
        logging.info(f"Searching with absolute path pattern: {base_search_path}")
        all_files = glob.glob(base_search_path, recursive=True)
        total_files = len(all_files)

        if not all_files:
            logging.error(
                f"No .jsonl files found matching pattern: {base_search_path}"
            )
            sys.exit(1)
        logging.info(f"Found {total_files} files to process.")

        # --- Estimate Total Chunks (Using Faster Logic) ---
        estimated_total_chunks = 0
        logging.info(
            "Estimating total chunks (using fast character-based approximation)..."
        )
        approx_chars_per_chunk = MAX_SEQ_LENGTH * 3  # Heuristic: ~3 chars per token
        sample_size = min(100, max(10, total_files // 20))
        if sample_size > len(all_files):
            sample_size = len(all_files)

        if sample_size == 0:
            logging.warning("No files found to sample for estimation.")
            estimated_total_chunks = total_files
        else:
            sample_files = np.random.choice(all_files, sample_size, replace=False)
            estimation_chunks = 0
            with ThreadPoolExecutor(
                max_workers=max(1, os.cpu_count() // 2),  # Reduced workers for estimation
                thread_name_prefix="EstimateFast"
            ) as executor:
                future_to_file_est = {
                    executor.submit(estimate_chunks_in_file_fast, f, approx_chars_per_chunk): f
                    for f in sample_files
                }
                for future in tqdm(
                    as_completed(future_to_file_est),
                    total=len(sample_files),
                    desc="Estimating Chunks (Fast)",
                    unit="file",
                ):
                    filepath = future_to_file_est[future]
                    try:
                        count = future.result()
                        estimation_chunks += count
                    except Exception as est_exc:
                        logging.warning(
                            f"Error during fast chunk estimation for {filepath}: {est_exc}"
                        )

            if sample_size > 0 and estimation_chunks > 0:
                avg_chunks_per_file = estimation_chunks / sample_size
                estimated_total_chunks = int(avg_chunks_per_file * total_files)
                logging.info(
                    f"Estimated chunks/file: {avg_chunks_per_file:.2f} (from {sample_size} samples)"
                )
                logging.info(f"Estimated total chunks: {estimated_total_chunks}")
            else:
                estimated_total_chunks = total_files
                logging.warning("Chunk estimation failed. Using file count for progress.")

        # Adjust CHUNK_BATCH_SIZE based on available VRAM
        if torch.cuda.is_available():
            free_vram = torch.cuda.get_device_properties(0).total_memory
            # Start with conservative batch size, can be tuned
            CHUNK_BATCH_SIZE = min(4096, max(512, int(free_vram / (2 ** 30) * 512)))
            logging.info(f"Adjusted CHUNK_BATCH_SIZE to {CHUNK_BATCH_SIZE} based on VRAM")

        # --- Start Processing ---
        logging.info("Starting main processing (Embedding and DB Insert)...")
        process_start_time = time.time()
        chunks_processed_count = 0
        files_processed_count = 0
        db_batch = []
        model_input_batch = []
        last_eta_print_time = time.time()

        pbar_total = max(1, estimated_total_chunks)
        pbar_unit = "chunk" if estimated_total_chunks > total_files else "file"
        pbar = tqdm(total=pbar_total, desc="Processing", unit=pbar_unit)

        with ThreadPoolExecutor(
            max_workers=MAX_CPU_WORKERS, thread_name_prefix="ProcessFile"
        ) as executor:
            submitted_futures = {
                executor.submit(
                    process_file_yield_chunks_fs,
                    f,
                    tokenizer,
                    MAX_SEQ_LENGTH,
                    CHUNK_OVERLAP,
                )
                for f in all_files
            }
            active_iterators = []
            completed_futures_queue = []

            while submitted_futures or active_iterators:
                try:
                    for future in as_completed(submitted_futures, timeout=0.1):
                        completed_futures_queue.append(future)
                        submitted_futures.remove(future)
                except TimeoutError:
                    pass

                while completed_futures_queue:
                    future = completed_futures_queue.pop(0)
                    try:
                        iterator = future.result()
                        active_iterators.append(iterator)
                    except Exception as future_exc:
                        logging.error(f"File processing task failed: {future_exc}", exc_info=True)
                        files_processed_count += 1
                        if pbar_unit == "file": pbar.update(1)

                iterators_to_remove = []
                if len(model_input_batch) < CHUNK_BATCH_SIZE:
                    for i, iterator in enumerate(active_iterators):
                        try:
                            url, chunk_id, chunk_text = next(iterator)
                            model_input_batch.append((url, chunk_id, chunk_text))

                            if len(model_input_batch) >= CHUNK_BATCH_SIZE:
                                break

                        except StopIteration:
                            iterators_to_remove.append(iterator)
                            files_processed_count += 1
                            if pbar_unit == "file": pbar.update(1)
                        except Exception as gen_exc:
                            logging.error(f"Error consuming chunk generator: {gen_exc}", exc_info=True)
                            iterators_to_remove.append(iterator)
                            files_processed_count += 1
                            if pbar_unit == "file": pbar.update(1)

                for it in iterators_to_remove:
                    if it in active_iterators:
                        active_iterators.remove(it)

                process_model_batch_now = len(model_input_batch) >= CHUNK_BATCH_SIZE
                is_finalizing = not submitted_futures and not active_iterators and model_input_batch

                if process_model_batch_now or is_finalizing:
                    items_to_process_count = min(len(model_input_batch), CHUNK_BATCH_SIZE)
                    if items_to_process_count > 0:
                        batch_to_encode_data = model_input_batch[:items_to_process_count]
                        model_input_batch = model_input_batch[items_to_process_count:]

                        batch_texts = [item[2] for item in batch_to_encode_data]
                        try:
                            embeddings = encode_batch_hf_automodel(
                                model,
                                tokenizer,
                                batch_texts,
                                device,
                                MAX_SEQ_LENGTH,
                            )

                            for j, (url_b, chunk_id_b, _) in enumerate(batch_to_encode_data):
                                db_batch.append(
                                    (url_b, chunk_id_b, embeddings[j].tolist())
                                )

                            chunks_in_batch = len(batch_to_encode_data)
                            chunks_processed_count += chunks_in_batch
                            if pbar_unit == "chunk":
                                pbar.update(chunks_in_batch)

                        except Exception as model_err:
                            logging.error(
                                f"Error during model encoding batch: {model_err}",
                                exc_info=True,
                            )

                process_db_batch_now = len(db_batch) >= DB_BATCH_SIZE
                is_final_db_batch = not submitted_futures and not active_iterators and db_batch

                if process_db_batch_now or is_final_db_batch:
                    items_to_insert_count = len(db_batch)
                    if items_to_insert_count > 0:
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
                                    page_size=min(items_to_insert_count, DB_BATCH_SIZE),
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

                current_time = time.time()
                if current_time - last_eta_print_time > ETA_UPDATE_INTERVAL_SEC:
                    elapsed_proc_time = current_time - process_start_time
                    if chunks_processed_count > 0 and elapsed_proc_time > 1:
                        chunks_per_sec = chunks_processed_count / elapsed_proc_time
                        if pbar_unit == "chunk":
                            items_remaining = pbar_total - chunks_processed_count
                            if chunks_per_sec > 0 and items_remaining > 0:
                                eta_seconds = items_remaining / chunks_per_sec
                                eta_formatted = time.strftime(
                                    "%H:%M:%S", time.gmtime(eta_seconds)
                                )
                            elif items_remaining <= 0:
                                eta_formatted = "Done"
                            else:
                                eta_formatted = "Calculating..."

                            pbar.set_postfix_str(
                                f"Files: {files_processed_count}/{total_files}, Rate: {chunks_per_sec:.1f} chunks/s, ETA: {eta_formatted}"
                            )
                        else:
                            pbar.set_postfix_str(
                                f"Files: {files_processed_count}/{total_files}, Rate: {chunks_per_sec:.1f} chunks/s (File Prog.)"
                            )

                        last_eta_print_time = current_time

        logging.info("Main processing loop finished.")
        pbar.close()

        if db_batch:
            logging.warning(f"Found {len(db_batch)} items remaining in DB batch after main loop. Inserting...")
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
                logging.info("Safeguard final DB batch inserted successfully.")
                db_batch = []
            except psycopg2.Error as db_err:
                logging.error(f"Safeguard final database batch insert failed: {db_err}")
                conn.rollback()
            except Exception as general_db_err:
                logging.error(f"Unexpected error during safeguard final DB insert: {general_db_err}", exc_info=True)
                conn.rollback()

    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

    overall_end_time = time.time()
    total_runtime = overall_end_time - overall_start_time
    processing_runtime = 0
    if 'process_start_time' in locals():
        processing_runtime = overall_end_time - process_start_time

    logging.info("\n--- Embedding Generation Complete ---")
    logging.info(
        f"Total Runtime: {time.strftime('%H:%M:%S', time.gmtime(total_runtime))}"
    )
    if processing_runtime > 0:
        logging.info(f"  (Main Processing: {processing_runtime:.2f}s)")
    logging.info(f"Total Files Processed: {files_processed_count}/{total_files}")
    logging.info(f"Total Chunks Embedded: {chunks_processed_count}")
    if processing_runtime > 0 and chunks_processed_count > 0:
        avg_chunks_per_sec = chunks_processed_count / processing_runtime
        logging.info(
            f"Average Processing Throughput: {avg_chunks_per_sec:.2f} chunks/sec"
        )
    elif chunks_processed_count > 0:
        logging.info(
            "Processing runtime was zero or negative, cannot calculate throughput."
        )