import json
import tiktoken
import os
import glob
import multiprocessing
from functools import partial

# --- Configuration ---
DIRECTORY_PATH = '../analyses'
GLOB_PATTERN = 'partition=*/batch_*.jsonl'
PRICE_PER_MILLION_TOKENS = 0.02
TIKTOKEN_ENCODING = "cl100k_base"  # encoding for text-embedding-3-small, ada-002 etc.
# ---               ---

# --- Do not change! Unless you modified the structure in the dataset / crawler ---
PRIMARY_TEXT_FIELD_KEYS = ['content_text']
META_TAGS_KEY = 'meta_tags'
META_TAG_CONTENT_KEY = 'content'


def count_tokens(text, encoding):
    """Counts the number of tokens in a text string."""
    if not isinstance(text, str):
        return 0
    return len(encoding.encode(text))

def process_file(filepath, encoding, primary_text_keys, meta_tags_key, meta_tag_content_key):
    """Processes a single JSONL file and returns its token count."""
    file_tokens = 0
    filename = os.path.basename(filepath)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                line_tokens = 0
                try:
                    data = json.loads(line)

                    primary_text_content = None
                    for key in primary_text_keys:
                        primary_text_content = data.get(key)
                        if primary_text_content:
                            break # found primary text, stop checking keys

                    if primary_text_content:
                        line_tokens += count_tokens(primary_text_content, encoding)

                    # process meta_tags
                    meta_tags_list = data.get(meta_tags_key)
                    if meta_tags_list and isinstance(meta_tags_list, list):
                        for tag in meta_tags_list:
                            if isinstance(tag, dict):
                                tag_content = tag.get(meta_tag_content_key)
                                if tag_content: # check if content exists
                                     line_tokens += count_tokens(tag_content, encoding)

                    file_tokens += line_tokens

                except json.JSONDecodeError:
                    print(f"Warning: Could not decode JSON in line {i+1} of {filename}")
                except Exception as e:
                    print(f"Warning: Error processing line {i+1} in {filename}: {e}")
        print(f"Debug: {filename} - Tokens: {file_tokens}")

        return file_tokens, filepath # return tokens and filepath for progress
    except FileNotFoundError:
        print(f"Warning: File not found during processing: {filename}")
        return 0, filepath
    except Exception as e:
        print(f"Warning: Error reading file {filename}: {e}")
        return 0, filepath

def calculate_cost_parallel(directory, pattern, price_per_million, encoding_name, primary_text_keys, meta_tags_key, meta_tag_content_key):
    """
    Calculates the approximate cost using multiprocessing and shows progress.
    """
    full_pattern = os.path.join(directory, pattern)
    print(f"Searching for files matching: {full_pattern}")
    jsonl_files = glob.glob(full_pattern, recursive=False)
    total_files = len(jsonl_files)

    if total_files == 0:
        print("No .jsonl files found matching the pattern.")
        return 0.0

    print(f"Found {total_files} files to process.")

    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception as e:
        print(f"Error getting tiktoken encoding '{encoding_name}': {e}")
        return 0.0

    total_tokens = 0
    files_processed = 0

    worker_func = partial(process_file,
                          encoding=encoding,
                          primary_text_keys=primary_text_keys,
                          meta_tags_key=meta_tags_key,
                          meta_tag_content_key=meta_tag_content_key)

    num_processes = multiprocessing.cpu_count()
    print(f"Starting processing with {num_processes} workers...")
    with multiprocessing.Pool(processes=num_processes) as pool:
        results_iterator = pool.imap_unordered(worker_func, jsonl_files)

        for file_token_count, _ in results_iterator:
            total_tokens += file_token_count
            files_processed += 1
            print(f"Progress: {files_processed}/{total_files} files processed...", end='\r')

    print("\nProcessing complete.")

    cost = (total_tokens / 1_000_000) * price_per_million
    print(f"-------------------------------------")
    print(f"Total files processed: {files_processed}")
    print(f"Total tokens estimated (incl. meta_tags): {total_tokens}")
    print(f"Estimated cost: ${cost:.4f}")
    print(f"-------------------------------------")
    return cost

if __name__ == "__main__":
    print(f"Script starting in directory: {os.getcwd()}")
    abs_directory_path = os.path.abspath(DIRECTORY_PATH)
    print(f"Looking in base directory: {abs_directory_path}")

    if not os.path.isdir(abs_directory_path):
        print(f"Error: Directory not found: {abs_directory_path}")
    else:
        estimated_cost = calculate_cost_parallel(
            DIRECTORY_PATH,
            GLOB_PATTERN,
            PRICE_PER_MILLION_TOKENS,
            TIKTOKEN_ENCODING,
            PRIMARY_TEXT_FIELD_KEYS,
            META_TAGS_KEY,
            META_TAG_CONTENT_KEY
        )
