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
# --- Batch Size Tuning ---
# START HERE: Experiment with CHUNK_BATCH_SIZE.
# 13300 filled VRAM but was slow. Start smaller (e.g., 1024, 2048, 4096)
# and monitor GPU *compute* utilization (nvidia-smi) and chunks/sec.
# Find the size that maximizes chunks/sec.
CHUNK_BATCH_SIZE = 2048  # <<< START EXPERIMENTING HERE
# DB_BATCH_SIZE: Can also be tuned. Larger might be slightly faster but uses more client RAM.
DB_BATCH_SIZE = 5000  # <<< EXPERIMENT (e.g., 2000, 5000, 10000)
MAX_SEQ_LENGTH = 512  # Model's maximum sequence length
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
# (connect_db, create_table_if_not_exists, extract_relevant_text, chunk_text_by_tokens remain the same)
def connect_db():
    """Establishes connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(PRIVATE_DB_URL)
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '300s';") # 5 minutes, adjust if needed
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
    Chunks text based on token count using the model's tokenizer,
    correctly accounting for special tokens added by the model later.
    """
    if not text:
        return []

    # *** FIX: Calculate effective max tokens for chunking ***
    # Determine how many special tokens (e.g., [CLS], [SEP]) the tokenizer adds
    # pair=False because we are encoding single sequences
    num_special_tokens = tokenizer.num_special_tokens_to_add(pair=False)
    effective_max_tokens = max_tokens - num_special_tokens

    if effective_max_tokens <= 0:
        logging.warning(
            f"max_tokens ({max_tokens}) is too small for the model's special tokens ({num_special_tokens}). Cannot chunk effectively. Skipping text."
        )
        return []

    # Tokenize the input text *without* adding special tokens here.
    # We only need the token IDs for splitting.
    tokens = tokenizer.encode(text, add_special_tokens=False, truncation=False)

    # If the whole text fits within the effective limit, return it as one chunk.
    # The main encoding step will add the special tokens later.
    if len(tokens) <= effective_max_tokens:
        # Decode back to text for the current pipeline structure
        return [tokenizer.decode(tokens)]

    chunks = []
    # Stride calculation should be based on the effective length to avoid re-processing overlap too much
    stride = effective_max_tokens - overlap
    # Ensure stride is positive
    if stride <= 0:
        stride = max(1, effective_max_tokens // 2)
        logging.debug(
            f"Overlap ({overlap}) too large for effective_max_tokens ({effective_max_tokens}). Using stride={stride}"
        )

    for i in range(0, len(tokens), stride):
        # Slice the tokens based on the effective max length
        chunk_tokens = tokens[i : i + effective_max_tokens]
        # Decode the chunk's tokens back into text.
        # Note: A more advanced optimization would be to yield token IDs directly.
        chunks.append(tokenizer.decode(chunk_tokens))
        # Stop if the start of the next chunk would be past the end of the tokens
        if i + stride >= len(tokens):
            break # Avoid creating an unnecessary final overlapping chunk if stride takes us past the end

    # Handle the very last segment if it wasn't fully covered
    if (len(tokens) - (i + effective_max_tokens)) > 0 and i > 0 : # Check if there are remaining tokens after the last stride loop
         last_chunk_start = max(0, len(tokens) - effective_max_tokens) # Ensure start isn't negative
         last_chunk_tokens = tokens[last_chunk_start:]
         last_decoded = tokenizer.decode(last_chunk_tokens)
         # Avoid adding duplicate of the last chunk if stride landed perfectly
         if not chunks or chunks[-1] != last_decoded:
              chunks.append(last_decoded)


    return chunks


# --- Worker Function (Filesystem) ---
def process_file_yield_chunks_fs(filepath, tokenizer, max_tokens, overlap):
    """
    Worker function to read local file, process, and yield (url, chunk_id, chunk_text).
    Now uses the corrected chunking function.
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

                    # Use the corrected chunking function
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
        return total_chunks_yielded  # Return count for estimation
    except Exception as e:
        logging.error(f"Failed to open or process file {filepath}: {e}")
        return 0  # Indicate failure/no chunks


# --- Encoding Function ---
def encode_batch_hf_automodel(
    model, tokenizer, chunk_batch, device, max_seq_len
):
    """Encode batch using standard Hugging Face AutoModel."""
    # Tokenizer now correctly handles padding/truncation based on max_seq_len
    # It will also add the special tokens automatically.
    inputs = tokenizer(
        chunk_batch,
        return_tensors="pt",
        padding=True,  # Pad sequences to the longest in the batch
        truncation=True,  # Truncate sequences longer than max_seq_len
        max_length=max_seq_len,
    )
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    # Mean pooling of the last hidden state
    embeddings = outputs.last_hidden_state.mean(dim=1)
    # Move embeddings to CPU *after* pooling
    embeddings = embeddings.cpu().numpy()
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

    # Load Model & Tokenizer
    logging.info(f"Loading model and tokenizer: {MODEL_NAME}")
    try:
        # use_fast=True is generally recommended for performance
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
        model = AutoModel.from_pretrained(MODEL_NAME)
        model.to(device)
        embedding_dim = model.config.hidden_size

        # Apply FP16 / half precision if on CUDA
        if device == "cuda":
            try:
                model.half()
                logging.info("Applied .half() to model for FP16.")
            except Exception as fp16_err:
                logging.warning(
                    f"Could not apply .half(): {fp16_err}. Using FP32."
                )
        model.eval()  # Set model to evaluation mode
    except Exception as e:
        logging.error(f"Failed to load model/tokenizer: {e}", exc_info=True)
        sys.exit(1)

    # Database Setup
    conn = connect_db()
    try:  # Wrap DB and processing in try/finally to ensure connection closure
        create_table_if_not_exists(conn, embedding_dim)

        # --- Find Files ---
        logging.info(f"Finding files matching '{ANALYSES_DIR_PATTERN}'...")
        # Ensure the path is interpreted correctly relative to the script or CWD
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

        # --- Estimate Total Chunks (for better progress bar) ---
        estimated_total_chunks = 0
        logging.info(
            "Estimating total chunks (sampling files)..."
        )
        # Sample a subset of files for estimation to save time
        sample_size = min(100, max(10, total_files // 20)) # Sample up to 100 files or 5%
        sample_files = np.random.choice(all_files, sample_size, replace=False)
        estimation_chunks = 0
        # Use a temporary tokenizer instance for estimation if needed, or reuse main one
        # temp_tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
        with ThreadPoolExecutor(
            max_workers=MAX_CPU_WORKERS, thread_name_prefix="Estimate"
        ) as executor:
            # Submit estimation tasks
            future_to_file_est = {
                executor.submit(
                    process_file_yield_chunks_fs,
                    f,
                    tokenizer, # Reuse main tokenizer
                    MAX_SEQ_LENGTH,
                    CHUNK_OVERLAP,
                ): f
                for f in sample_files
            }
            # Process results as they complete
            for future in tqdm(
                as_completed(future_to_file_est),
                total=len(sample_files),
                desc="Estimating Chunks",
                unit="file",
            ):
                try:
                    # The worker now returns the count directly
                    estimation_chunks += future.result()
                except Exception as est_exc:
                    filepath = future_to_file_est[future]
                    logging.warning(
                        f"Error during chunk estimation for file {filepath}: {est_exc}"
                    )
        # del temp_tokenizer # Delete if you created a temporary one

        if sample_size > 0 and estimation_chunks > 0:
            avg_chunks_per_file = estimation_chunks / sample_size
            estimated_total_chunks = int(avg_chunks_per_file * total_files)
            logging.info(
                f"Estimated average chunks/file: {avg_chunks_per_file:.2f}"
            )
            logging.info(f"Roughly estimated total chunks: {estimated_total_chunks}")
        else:
            estimated_total_chunks = total_files # Fallback if estimation fails
            logging.warning(
                "Could not estimate total chunks effectively. Progress bar will use file count."
            )

        # --- Start Processing ---
        logging.info("Starting main processing (Embedding and DB Insert)...")
        process_start_time = time.time()
        chunks_processed_count = 0
        files_processed_count = 0  # Track processed files for logging
        db_batch = []
        model_input_batch = [] # Stores tuples of (url, chunk_id, chunk_text)
        last_eta_print_time = time.time()

        # Setup tqdm progress bar based on ESTIMATED CHUNKS
        pbar_total = max(1, estimated_total_chunks) # Ensure pbar_total >= 1
        pbar_unit = "chunk" if estimated_total_chunks > total_files else "file"
        pbar = tqdm(total=pbar_total, desc="Processing", unit=pbar_unit)

        # Use a single ThreadPoolExecutor for file processing
        with ThreadPoolExecutor(
            max_workers=MAX_CPU_WORKERS, thread_name_prefix="ProcessFile"
        ) as executor:
            # Submit file processing tasks. The worker yields chunks.
            # We store the generator iterator returned by the future.
            future_to_iterator = {
                executor.submit(
                    process_file_yield_chunks_fs,
                    f,
                    tokenizer,
                    MAX_SEQ_LENGTH,
                    CHUNK_OVERLAP,
                ): None # Placeholder, we don't need file path here anymore
                for f in all_files
            }
            # Keep track of active iterators from completed futures
            active_iterators = []

            while future_to_iterator or active_iterators:
                # Process completed futures first to get new iterators
                done, _ = as_completed(future_to_iterator, timeout=0.1) # Short timeout
                for future in done:
                    try:
                        # Get the generator iterator from the completed future
                        iterator = future.result()
                        active_iterators.append(iterator)
                    except Exception as future_exc:
                        # Log error if the task itself failed (e.g., file open error)
                        # Note: future_to_iterator doesn't store filepath directly anymore
                        logging.error(f"File processing task failed: {future_exc}", exc_info=True)
                        files_processed_count += 1 # Count file as processed (even if failed)
                        if pbar_unit == "file": pbar.update(1)
                    # Remove the processed future
                    del future_to_iterator[future]

                # Round-robin fetch from active iterators to fill the model batch
                iterators_to_remove = []
                for i, iterator in enumerate(active_iterators):
                    try:
                        # Get the next chunk from this file's iterator
                        url, chunk_id, chunk_text = next(iterator)
                        model_input_batch.append((url, chunk_id, chunk_text))

                        # --- Process Model Batch ---
                        if len(model_input_batch) >= CHUNK_BATCH_SIZE:
                            batch_to_encode_data = model_input_batch[:CHUNK_BATCH_SIZE]
                            model_input_batch = model_input_batch[CHUNK_BATCH_SIZE:] # Keep remainder

                            batch_texts = [item[2] for item in batch_to_encode_data]
                            batch_start_time = time.time()
                            try:
                                embeddings = encode_batch_hf_automodel(
                                    model,
                                    tokenizer,
                                    batch_texts,
                                    device,
                                    MAX_SEQ_LENGTH,
                                )
                                # No need for cuda sync here, CPU transfer handles it implicitly

                                # Prepare batch for DB insertion
                                for j, (url_b, chunk_id_b, _) in enumerate(
                                    batch_to_encode_data
                                ):
                                    # Ensure embedding is a list for psycopg2
                                    db_batch.append(
                                        (url_b, chunk_id_b, embeddings[j].tolist())
                                    )

                                chunks_in_batch = len(batch_to_encode_data)
                                chunks_processed_count += chunks_in_batch
                                if pbar_unit == "chunk":
                                    pbar.update(chunks_in_batch) # Update progress bar by chunks

                            except Exception as model_err:
                                logging.error(
                                    f"Error during model encoding batch: {model_err}",
                                    exc_info=True,
                                )
                                # Decide how to handle: skip batch? retry? For now, just log.

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
                                        page_size=DB_BATCH_SIZE, # Use specified page size
                                    )
                                conn.commit()
                                db_batch = [] # Clear batch after successful insert
                            except psycopg2.Error as db_err:
                                logging.error(
                                    f"Database batch insert failed: {db_err}"
                                )
                                conn.rollback() # Rollback transaction on error
                                # Consider adding retry logic or saving failed batches
                                db_batch = [] # Clear batch even on failure for now
                            except Exception as general_db_err:
                                logging.error(
                                    f"Unexpected error during DB insert: {general_db_err}",
                                    exc_info=True,
                                )
                                conn.rollback()
                                db_batch = []

                    except StopIteration:
                        # This iterator is exhausted (file finished)
                        iterators_to_remove.append(iterator)
                        files_processed_count += 1
                        if pbar_unit == "file": pbar.update(1) # Update file progress if using file count
                    except Exception as gen_exc:
                        # Error occurred while getting next item from generator
                        logging.error(f"Error consuming chunk generator: {gen_exc}", exc_info=True)
                        iterators_to_remove.append(iterator) # Remove problematic iterator
                        files_processed_count += 1 # Count file as processed (even if failed)
                        if pbar_unit == "file": pbar.update(1)

                    # Break inner loop if model batch is full to process it immediately
                    if len(model_input_batch) >= CHUNK_BATCH_SIZE:
                        break

                # Remove exhausted iterators
                for it in iterators_to_remove:
                    active_iterators.remove(it)

                # --- Update ETA ---
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
                            else:
                                eta_formatted = "Done" if items_remaining <= 0 else "Calculating..."
                            pbar.set_postfix_str(
                                f"Files: {files_processed_count}/{total_files}, Rate: {chunks_per_sec:.1f} chunks/s, ETA: {eta_formatted}"
                            )
                        else: # Fallback if using file count
                             pbar.set_postfix_str(
                                f"Files: {files_processed_count}/{total_files}, Rate: {chunks_per_sec:.1f} chunks/s (File Prog.)"
                            )

                        last_eta_print_time = current_time

                # If no futures are left and no active iterators, exit main loop
                if not future_to_iterator and not active_iterators:
                    break


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

                for i, (url_b, chunk_id_b, _) in enumerate(model_input_batch):
                    db_batch.append((url_b, chunk_id_b, embeddings[i].tolist()))

                final_chunks_count = len(model_input_batch)
                chunks_processed_count += final_chunks_count
                if pbar_unit == "chunk":
                    pbar.update(final_chunks_count) # Update progress bar
                logging.info(
                    f"Encoded final model batch. Total chunks processed: {chunks_processed_count}"
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
                        page_size=len(db_batch), # Insert all remaining
                    )
                conn.commit()
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
    # Ensure process_start_time exists before calculating processing_runtime
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
    # Use the final count for accuracy
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