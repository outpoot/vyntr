import time
import glob
import json
import os
import numpy as np
import torch
import onnxruntime as ort
from transformers import AutoTokenizer, AutoModel
from sentence_transformers import SentenceTransformer
from huggingface_hub import snapshot_download
import logging
import argparse

# --- Configuration ---
MODEL_HF_MINILM = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_BGE = "BAAI/bge-small-en-v1.5"
MODEL_ONNX_MANUAL_REPO = "LightEmbed/sbert-all-MiniLM-L6-v2-onnx"

CHUNK_BATCH_SIZE = 2048     # Number of text CHUNKS to process in one model batch
MAX_SEQ_LENGTH_MINILM = 256 # Check model card if unsure
MAX_SEQ_LENGTH_BGE = 512    # From model card
CHUNK_OVERLAP = 50

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Determine device ---
onnx_providers = ['CPUExecutionProvider']
onnx_provider_name_for_report = "CPU"
pytorch_device = "cpu"

if torch.cuda.is_available():
    pytorch_device = "cuda"
    logging.info("CUDA (GPU) is available via PyTorch.")
    available_providers = ort.get_available_providers()
    logging.info(f"ONNX Runtime Available Providers: {available_providers}")
    if 'TensorrtExecutionProvider' in available_providers:
        onnx_providers = ['TensorrtExecutionProvider', 'CPUExecutionProvider']
        onnx_provider_name_for_report = "GPU (TRT)"
        logging.info("Attempting ONNX benchmarks on GPU (TensorrtExecutionProvider).")
    elif 'CUDAExecutionProvider' in available_providers:
        onnx_providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
        onnx_provider_name_for_report = "GPU"
        logging.info("Attempting ONNX benchmarks on GPU (CUDAExecutionProvider).")
    else:
        logging.warning("ONNX Runtime CUDA/TensorRT ExecutionProvider is NOT available. ONNX benchmarks will run on CPU.")
        onnx_provider_name_for_report = "CPU"
else:
    logging.info("CUDA (GPU) not available via PyTorch. Benchmarking all models on CPU.")
    onnx_provider_name_for_report = "CPU"


# --- Helper Functions ---
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
    if not text:
        return []
    tokens = tokenizer.encode(text, add_special_tokens=False, truncation=False)
    if len(tokens) <= max_tokens:
        return [tokenizer.decode(tokens)]

    chunks = []
    stride = max_tokens - overlap
    if stride <= 0:
        stride = max_tokens // 2 if max_tokens > 1 else 1

    for i in range(0, len(tokens), stride):
        chunk_tokens = tokens[i : i + max_tokens]
        chunks.append(tokenizer.decode(chunk_tokens))
        if i + max_tokens >= len(tokens):
            break
    return chunks

# --- Model Loading Functions ---

def load_hf_minilm(device):
    logging.info(f"Loading HF MiniLM ({MODEL_HF_MINILM})...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_HF_MINILM, use_fast=True)
        model = AutoModel.from_pretrained(MODEL_HF_MINILM)
        model.to(device)
        if device == 'cuda':
            try:
                model.half()
                logging.info("Applied .half() to HF MiniLM model.")
            except Exception as fp16_err:
                logging.warning(f"Could not apply .half() to HF MiniLM model: {fp16_err}. Using FP32.")
        model.eval()
        return model, tokenizer
    except Exception as e:
        logging.error(f"Failed to load HF MiniLM: {e}")
        return None, None

def load_sbert_bge(device):
    logging.info(f"Loading SentenceTransformer BGE ({MODEL_BGE})...")
    try:
        model = SentenceTransformer(MODEL_BGE, device=device)
        if device == 'cuda':
             try:
                 model.half()
                 logging.info("Applied .half() to BGE model.")
             except Exception as fp16_err:
                 logging.warning(f"Could not apply .half() to BGE model: {fp16_err}. Using FP32.")
        model.eval()
        return model, model.tokenizer
    except Exception as e:
        logging.error(f"Failed to load SentenceTransformer BGE: {e}")
        return None, None

def load_onnx_minilm(providers_list):
    logging.info(f"Loading Manual ONNX MiniLM ({MODEL_ONNX_MANUAL_REPO})...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_HF_MINILM, use_fast=True)

        logging.info(f"Downloading ONNX model files from Hub ID: {MODEL_ONNX_MANUAL_REPO}")
        model_dir = snapshot_download(MODEL_ONNX_MANUAL_REPO)
        model_filename = "model.onnx"
        model_path = os.path.join(model_dir, model_filename)

        if not os.path.exists(model_path):
            onnx_files = [f for f in os.listdir(model_dir) if f.endswith(".onnx")]
            if not onnx_files:
                raise FileNotFoundError(f"No ONNX file found in {model_dir} for {MODEL_ONNX_MANUAL_REPO}")
            model_path = os.path.join(model_dir, onnx_files[0])
            logging.info(f"Found ONNX file: {onnx_files[0]}")

        logging.info(f"Loading ONNX model from: {model_path}")
        logging.info(f"Attempting ONNX Runtime providers: {providers_list}")
        session = ort.InferenceSession(model_path, providers=providers_list)
        actual_provider = session.get_providers()[0]
        logging.info(f"Successfully created ONNX session with provider: {actual_provider}")
        return session, tokenizer, actual_provider
    except Exception as e:
        logging.error(f"Failed to load ONNX MiniLM or tokenizer: {e}")
        return None, None, None

# --- Encoding Functions ---

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

def encode_batch_sbert(model, chunk_batch, device):
    """Encode batch using SentenceTransformer."""
    embeddings = model.encode(
        chunk_batch,
        device=device,
        batch_size=len(chunk_batch),
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )
    return embeddings

def encode_batch_onnx_manual(session, tokenizer, chunk_batch, max_seq_len):
    """Encode batch using manually loaded ONNX session."""
    inputs_tokenized = tokenizer(
        chunk_batch,
        return_tensors="np",
        padding=True,
        truncation=True,
        max_length=max_seq_len
    )

    ort_inputs = {}
    input_names = {inp.name for inp in session.get_inputs()}
    for key, value in inputs_tokenized.items():
        if key in input_names:
             ort_inputs[key] = np.array(value, dtype=np.int64)

    if not ort_inputs:
         raise ValueError("Could not map tokenizer outputs to ONNX model inputs.")

    ort_outs = session.run(None, ort_inputs)

    if isinstance(ort_outs, list) and len(ort_outs) > 0:
        embeddings = ort_outs[0]
        if len(embeddings.shape) == 3 and embeddings.shape[1] > 1:
             input_mask = ort_inputs.get('attention_mask')
             if input_mask is not None:
                 mask_expanded = np.expand_dims(input_mask, axis=-1)
                 sum_embeddings = np.sum(embeddings * mask_expanded, axis=1)
                 sum_mask = np.sum(mask_expanded, axis=1)
                 embeddings = sum_embeddings / np.maximum(sum_mask, 1e-9)
             else:
                  embeddings = np.mean(embeddings, axis=1)
    else:
        raise TypeError(f"Unexpected ONNX output format: {type(ort_outs)}")

    return embeddings


# --- Main Benchmark Function ---

def benchmark_partition(
    model_name,
    model_or_session,
    tokenizer,
    encode_func,
    device_or_provider,
    partition_file_path,
    chunk_batch_size,
    max_seq_len,
    is_onnx=False
):
    """Reads a partition file, chunks text, and benchmarks embedding speed."""
    logging.info(f"--- Starting Benchmark for: {model_name} on {device_or_provider} ---")
    if not os.path.exists(partition_file_path):
        logging.error(f"Partition file not found: {partition_file_path}")
        return None

    processed_items = 0
    total_chunks_generated = 0
    total_batches_processed = 0
    chunk_batch = []

    start_time = time.perf_counter()

    try:
        with open(partition_file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                try:
                    entry = json.loads(line)
                    url = entry.get("url")
                    if not url: continue

                    text_to_process = extract_relevant_text(entry)
                    if not text_to_process: continue

                    chunks = chunk_text_by_tokens(
                        text_to_process,
                        tokenizer,
                        max_seq_len,
                        CHUNK_OVERLAP
                    )
                    if not chunks: continue

                    processed_items += 1
                    total_chunks_generated += len(chunks)
                    chunk_batch.extend(chunks)

                    while len(chunk_batch) >= chunk_batch_size:
                        batch_to_encode = chunk_batch[:chunk_batch_size]
                        chunk_batch = chunk_batch[chunk_batch_size:]

                        if is_onnx:
                            _ = encode_func(model_or_session, tokenizer, batch_to_encode, max_seq_len)
                        else:
                            if encode_func == encode_batch_hf_automodel:
                                _ = encode_func(model_or_session, tokenizer, batch_to_encode, device_or_provider, max_seq_len)
                            elif encode_func == encode_batch_sbert:
                                _ = encode_func(model_or_session, batch_to_encode, device_or_provider)
                            else:
                                logging.error(f"Unknown encode_func type: {encode_func.__name__}")
                                continue

                        if not is_onnx and device_or_provider == 'cuda':
                            torch.cuda.synchronize()

                        total_batches_processed += 1

                except json.JSONDecodeError:
                    logging.warning(f"Skipping invalid JSON on line {line_num} in {partition_file_path}")
                except Exception as e:
                    logging.warning(f"Error processing batch near line {line_num} in {partition_file_path}: {e}", exc_info=True) # Add traceback

        if chunk_batch:
            try:
                if is_onnx:
                    _ = encode_func(model_or_session, tokenizer, chunk_batch, max_seq_len)
                else:
                    if encode_func == encode_batch_hf_automodel:
                        _ = encode_func(model_or_session, tokenizer, chunk_batch, device_or_provider, max_seq_len)
                    elif encode_func == encode_batch_sbert:
                        _ = encode_func(model_or_session, chunk_batch, device_or_provider)
                    else:
                         logging.error(f"Unknown encode_func type for final batch: {encode_func.__name__}")

                if not is_onnx and device_or_provider == 'cuda':
                    torch.cuda.synchronize()
                total_batches_processed += 1
            except Exception as e:
                 logging.error(f"Error processing final batch in {partition_file_path}: {e}", exc_info=True)


    except Exception as e:
        logging.error(f"Failed to read or process file {partition_file_path}: {e}")
        return None

    end_time = time.perf_counter()
    total_time = end_time - start_time

    items_per_sec = processed_items / total_time if total_time > 0 else 0
    chunks_per_sec = total_chunks_generated / total_time if total_time > 0 else 0

    logging.info(f"--- Finished Benchmark for: {model_name} ---")
    logging.info(f"  Total Time: {total_time:.2f} seconds")
    logging.info(f"  Processed JSONL Items: {processed_items}")
    logging.info(f"  Generated Text Chunks: {total_chunks_generated}")
    logging.info(f"  Model Batches Processed: {total_batches_processed}")
    logging.info(f"  Throughput (Items/sec): {items_per_sec:.2f}")
    logging.info(f"  Throughput (Chunks/sec): {chunks_per_sec:.2f}")

    return {
        "model_name": model_name,
        "device_provider": device_or_provider,
        "total_time_sec": total_time,
        "processed_items": processed_items,
        "total_chunks": total_chunks_generated,
        "items_per_sec": items_per_sec,
        "chunks_per_sec": chunks_per_sec,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark embedding models on a single partition.")
    parser.add_argument(
        "partition_name",
        help="Name of the partition directory (e.g., 'partition=0', 'partition=123')",
    )
    parser.add_argument(
        "--base_dir",
        default="analyses",
        help="Base directory containing the partitions (default: 'analyses')",
    )
    args = parser.parse_args()

    partition_dir = os.path.join(args.base_dir, args.partition_name)
    partition_files = glob.glob(os.path.join(partition_dir, "*.jsonl"))

    if not partition_files:
        logging.error(f"No .jsonl files found in specified partition: {partition_dir}")
        exit(1)

    file_to_benchmark = partition_files[0]
    logging.info(f"Selected file for benchmarking: {file_to_benchmark}")

    results = []

    # --- Benchmark HF MiniLM ---
    hf_model, hf_tokenizer = load_hf_minilm(pytorch_device)
    if hf_model and hf_tokenizer:
        result = benchmark_partition(
            model_name="HF Transformers MiniLM (FP16)",
            model_or_session=hf_model,
            tokenizer=hf_tokenizer,
            encode_func=encode_batch_hf_automodel,
            device_or_provider=pytorch_device,
            partition_file_path=file_to_benchmark,
            chunk_batch_size=CHUNK_BATCH_SIZE,
            max_seq_len=MAX_SEQ_LENGTH_MINILM,
            is_onnx=False
        )
        if result: results.append(result)
        del hf_model, hf_tokenizer # Free memory
        if pytorch_device == 'cuda': torch.cuda.empty_cache()

    # --- Benchmark SBERT BGE ---
    sbert_model, sbert_tokenizer = load_sbert_bge(pytorch_device)
    if sbert_model and sbert_tokenizer:
        result = benchmark_partition(
            model_name="SentenceTransformer BGE (FP16)",
            model_or_session=sbert_model,
            tokenizer=sbert_tokenizer,
            encode_func=encode_batch_sbert,
            device_or_provider=pytorch_device,
            partition_file_path=file_to_benchmark,
            chunk_batch_size=CHUNK_BATCH_SIZE,
            max_seq_len=MAX_SEQ_LENGTH_BGE,
            is_onnx=False
        )
        if result: results.append(result)
        del sbert_model, sbert_tokenizer # Free memory
        if pytorch_device == 'cuda': torch.cuda.empty_cache()

    # --- Benchmark ONNX MiniLM ---
    onnx_session, onnx_tokenizer, actual_onnx_provider = load_onnx_minilm(onnx_providers)
    if onnx_session and onnx_tokenizer:
        actual_provider_name = "GPU" if "CUDA" in actual_onnx_provider or "Tensorrt" in actual_onnx_provider else "CPU"
        result = benchmark_partition(
            model_name=f"Manual ONNX MiniLM",
            model_or_session=onnx_session,
            tokenizer=onnx_tokenizer,
            encode_func=encode_batch_onnx_manual,
            device_or_provider=actual_provider_name,
            partition_file_path=file_to_benchmark,
            chunk_batch_size=CHUNK_BATCH_SIZE,
            max_seq_len=MAX_SEQ_LENGTH_MINILM,
            is_onnx=True
        )
        if result: results.append(result)
        del onnx_session, onnx_tokenizer

    print("\n--- Benchmark Summary ---")
    if not results:
        print("No benchmarks completed successfully.")
    else:
        results.sort(key=lambda x: x["chunks_per_sec"], reverse=True)
        for res in results:
            print(
                f"Model: {res['model_name']} [{res['device_provider']}] | "
                f"Time: {res['total_time_sec']:.2f}s | "
                f"Items: {res['processed_items']} ({res['items_per_sec']:.2f}/s) | "
                f"Chunks: {res['total_chunks']} ({res['chunks_per_sec']:.2f}/s)"
            )
