import time
import numpy as np
import torch
import onnxruntime as ort
from transformers import AutoTokenizer, AutoModel
from huggingface_hub import snapshot_download
from sentence_transformers import SentenceTransformer

try:
    from light_embed import TextEmbedding
    LIGHT_EMBED_AVAILABLE = True
except ImportError:
    print("Warning: light_embed library not found. Skipping LightEmbed benchmark.")
    LIGHT_EMBED_AVAILABLE = False
try:
    from fastembed import TextEmbedding as FastTextEmbedding
    FASTEMBED_AVAILABLE = True
except ImportError:
    print("Warning: fastembed library not found. Skipping FastEmbed benchmark.")
    FASTEMBED_AVAILABLE = False

import os
import logging

# --- Configuration ---
MODEL_HF_MINILM = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_BGE = "BAAI/bge-small-en-v1.5"
MODEL_BGE_ONNX_Q_FASTEMBED = "BAAI/bge-small-en-v1.5"
MODEL_ONNX_LE = "all-MiniLM-L6-v2"
MODEL_ONNX_MANUAL = "LightEmbed/sbert-all-MiniLM-L6-v2-onnx"
ITERATIONS = 100

SENTENCES = [
    "This is an example sentence.",
    "Each sentence is converted to a vector.",
    "The quick brown fox jumps over the lazy dog.",
    "Benchmarking embedding models is fun!",
    "Short text.",
    "Another sentence to increase the batch size slightly.",
    "ONNX Runtime can provide significant speedups.",
    "Comparing Hugging Face Transformers with ONNX."
] * 256 # Batch size of 2048 (8 * 256)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Determine Device ---
onnx_providers = ['CPUExecutionProvider']
onnx_provider_name = "CPU"
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

def encode_sentences_hf_automodel(model, tokenizer, sentences, device):
    """Encode using standard Hugging Face AutoModel (like MiniLM)."""
    inputs = tokenizer(sentences, return_tensors="pt", padding=True, truncation=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1).cpu().numpy()
    return embeddings

def encode_sentences_sbert(model, sentences, device):
    """Encode using SentenceTransformer library."""
    embeddings = model.encode(
        sentences,
        device=device,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False
    )
    return embeddings

# --- Hugging Face Transformers (MiniLM) ---
def benchmark_hf_minilm(sentences, iterations, device):
    logging.info(f"--- Benchmarking Hugging Face Transformers [MiniLM] ({device}) ---")
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_HF_MINILM, use_fast=True)
        model = AutoModel.from_pretrained(MODEL_HF_MINILM)
        model.to(device)
        if device == 'cuda':
            try:
                model.half()
                logging.info("Applied .half() to HF MiniLM model for potential FP16 speedup.")
            except Exception as fp16_err:
                logging.warning(f"Could not apply .half() to HF MiniLM model: {fp16_err}. Running in FP32.")
        model.eval()
    except Exception as e:
        logging.error(f"Failed to load HF MiniLM model/tokenizer: {e}")
        return float('inf'), "Failed"

    try:
        _ = encode_sentences_hf_automodel(model, tokenizer, sentences, device)
        if device == 'cuda': torch.cuda.synchronize()
    except Exception as e:
        logging.error(f"HF MiniLM warm-up failed: {e}")
        return float('inf'), "Failed"

    start_time = time.perf_counter()
    for _ in range(iterations):
        _ = encode_sentences_hf_automodel(model, tokenizer, sentences, device)
    if device == 'cuda': torch.cuda.synchronize()
    end_time = time.perf_counter()

    total_time = end_time - start_time
    avg_time = total_time / iterations
    logging.info(f"HF MiniLM Model: Total time for {iterations} iterations: {total_time:.4f} seconds")
    logging.info(f"Average time per iteration (batch of {len(sentences)}): {avg_time:.6f} seconds")
    return avg_time, device

# --- LightEmbed Library (MiniLM ONNX) ---
def benchmark_lightembed(sentences, iterations, provider_name_hint):
    if not LIGHT_EMBED_AVAILABLE:
        return float('inf'), "Skipped"

    logging.info(f"--- Benchmarking LightEmbed [MiniLM ONNX] (Attempting {provider_name_hint}) ---")
    try:
        model = TextEmbedding(MODEL_ONNX_LE)
        logging.info(f"LightEmbed initialized with model ID: {MODEL_ONNX_LE}")
    except Exception as e:
        logging.error(f"Failed to initialize LightEmbed with ID '{MODEL_ONNX_LE}': {e}")
        logging.warning("LightEmbed benchmark failed. The library might not support this model ID.")
        return float('inf'), "Failed"

    try:
        _ = model.encode(sentences)
    except Exception as e:
        logging.error(f"LightEmbed warm-up failed: {e}")
        return float('inf'), "Failed"

    start_time = time.perf_counter()
    for _ in range(iterations):
        try:
            _ = model.encode(sentences)
        except Exception as e:
            logging.error(f"LightEmbed iteration failed: {e}")
            return float('inf'), "Failed"
    end_time = time.perf_counter()

    total_time = end_time - start_time
    avg_time = total_time / iterations
    logging.info(f"LightEmbed Model: Total time for {iterations} iterations: {total_time:.4f} seconds")
    logging.info(f"Average time per iteration (batch of {len(sentences)}): {avg_time:.6f} seconds")

    return avg_time, provider_name_hint


# --- Manual ONNX Runtime (MiniLM ONNX) ---
def load_onnx_model_manual(model_id=MODEL_ONNX_MANUAL, providers_list=None):
    """Downloads and loads ONNX model manually, specifying provider list."""
    if providers_list is None:
        providers_list = ['CPUExecutionProvider']
    logging.info(f"Downloading ONNX model files from Hub ID: {model_id}")
    try:
        model_dir = snapshot_download(model_id)
    except Exception as e:
        logging.error(f"Failed to download ONNX model {model_id}: {e}")
        raise

    model_filename = "model.onnx"
    model_path = os.path.join(model_dir, model_filename)

    if not os.path.exists(model_path):
         onnx_files = [f for f in os.listdir(model_dir) if f.endswith(".onnx")]
         if not onnx_files:
              raise FileNotFoundError(f"No ONNX file found in {model_dir} for {model_id}")
         model_path = os.path.join(model_dir, onnx_files[0])
         logging.info(f"Found ONNX file: {onnx_files[0]}")

    logging.info(f"Loading ONNX model from: {model_path}")
    logging.info(f"Attempting ONNX Runtime providers: {providers_list}")
    try:
        session = ort.InferenceSession(model_path, providers=providers_list)
        actual_provider = session.get_providers()[0]
        logging.info(f"Successfully created ONNX session with provider: {actual_provider}")
        return session, actual_provider
    except Exception as e:
        logging.error(f"Failed to create ONNX session with providers {providers_list}. Error: {e}")
        raise

def encode_sentences_onnx_manual(session, tokenizer, sentences):
    """Encode using manually loaded ONNX session."""
    max_len = tokenizer.model_max_length if hasattr(tokenizer, 'model_max_length') else 512
    inputs_tokenized = tokenizer(sentences, return_tensors="np", padding=True,
                                 truncation=True, max_length=max_len)

    ort_inputs = {}
    input_names = {inp.name for inp in session.get_inputs()}
    for key, value in inputs_tokenized.items():
        if key in input_names:
             ort_inputs[key] = np.array(value, dtype=np.int64)

    if not ort_inputs:
         logging.error(f"Could not map tokenizer outputs {list(inputs_tokenized.keys())} to ONNX model inputs {input_names}")
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

def benchmark_onnx_manual(sentences, iterations, providers_list):
    expected_provider_name = "GPU" if 'CUDAExecutionProvider' in providers_list or 'TensorrtExecutionProvider' in providers_list else "CPU"
    logging.info(f"--- Benchmarking Manual ONNX Runtime [MiniLM ONNX] (Attempting {expected_provider_name}) ---")

    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_HF_MINILM, use_fast=True)
        session, actual_provider = load_onnx_model_manual(model_id=MODEL_ONNX_MANUAL, providers_list=providers_list)
        actual_provider_name = "GPU" if "CUDA" in actual_provider or "Tensorrt" in actual_provider else "CPU"
        logging.info(f"Manual ONNX will run on: {actual_provider_name}")
    except Exception as e:
        logging.error(f"Failed to load manual ONNX model or tokenizer: {e}")
        return float('inf'), "Failed"

    try:
        _ = encode_sentences_onnx_manual(session, tokenizer, sentences)
    except Exception as e:
        logging.error(f"Manual ONNX warm-up failed: {e}")
        return float('inf'), "Failed"

    start_time = time.perf_counter()
    for _ in range(iterations):
        try:
            _ = encode_sentences_onnx_manual(session, tokenizer, sentences)
        except Exception as e:
            logging.error(f"Manual ONNX iteration failed: {e}")
            return float('inf'), "Failed"
    end_time = time.perf_counter()

    total_time = end_time - start_time
    avg_time = total_time / iterations
    logging.info(f"Manual ONNX Model ({actual_provider_name}): Total time for {iterations} iterations: {total_time:.4f} seconds")
    logging.info(f"Average time per iteration (batch of {len(sentences)}): {avg_time:.6f} seconds")
    return avg_time, actual_provider_name


# --- Hugging Face SentenceTransformer (BGE) ---
def benchmark_bge(sentences, iterations, device):
    logging.info(f"--- Benchmarking SentenceTransformer [BGE] ({device}) ---")
    try:
        model = SentenceTransformer(MODEL_BGE, device=device)
        if device == 'cuda' and hasattr(torch.cuda, 'amp') and torch.cuda.is_available():
             try:
                 model.half()
                 logging.info("Applied .half() to BGE model for potential FP16 speedup.")
             except Exception as fp16_err:
                 logging.warning(f"Could not apply .half() to BGE model: {fp16_err}. Running in FP32.")
        model.eval()
    except Exception as e:
        logging.error(f"Failed to load BGE model: {e}")
        return float('inf'), "Failed"

    try:
        _ = encode_sentences_sbert(model, sentences, device)
        if device == 'cuda': torch.cuda.synchronize()
    except Exception as e:
        logging.error(f"BGE warm-up failed: {e}")
        return float('inf'), "Failed"

    start_time = time.perf_counter()
    for _ in range(iterations):
        try:
            _ = encode_sentences_sbert(model, sentences, device)
        except Exception as e:
            logging.error(f"BGE iteration failed: {e}")
            return float('inf'), "Failed"
    if device == 'cuda': torch.cuda.synchronize()
    end_time = time.perf_counter()

    total_time = end_time - start_time
    avg_time = total_time / iterations
    logging.info(f"BGE Model: Total time for {iterations} iterations: {total_time:.4f} seconds")
    logging.info(f"Average time per iteration (batch of {len(sentences)}): {avg_time:.6f} seconds")
    return avg_time, device

# --- FastEmbed (Quantized BGE ONNX) ---
def benchmark_fastembed_bge_onnx_q(sentences, iterations, provider_name_hint):
    if not FASTEMBED_AVAILABLE:
        return float('inf'), "Skipped"

    logging.info(f"--- Benchmarking FastEmbed [Quantized BGE ONNX] (Attempting {provider_name_hint}) ---")
    try:
        model = FastTextEmbedding(model_name=MODEL_BGE_ONNX_Q_FASTEMBED, providers=None)
        logging.info(f"FastEmbed initialized using ID '{MODEL_BGE_ONNX_Q_FASTEMBED}' (maps to Qdrant quantized ONNX)")
    except Exception as e:
        logging.error(f"Failed to initialize FastEmbed with ID '{MODEL_BGE_ONNX_Q_FASTEMBED}': {e}")
        return float('inf'), "Failed"

    try:
        # Warm-up run
        _ = list(model.embed(sentences))
    except Exception as e:
        logging.error(f"FastEmbed warm-up failed: {e}")
        return float('inf'), "Failed"

    start_time = time.perf_counter()
    for _ in range(iterations):
        try:
            _ = list(model.embed(sentences))
        except Exception as e:
            logging.error(f"FastEmbed iteration failed: {e}")
            return float('inf'), "Failed"
    end_time = time.perf_counter()

    total_time = end_time - start_time
    avg_time = total_time / iterations
    logging.info(f"FastEmbed Model: Total time for {iterations} iterations: {total_time:.4f} seconds")
    logging.info(f"Average time per iteration (batch of {len(sentences)}): {avg_time:.6f} seconds")

    return avg_time, provider_name_hint

def main():
    logging.info(f"Benchmarking with {ITERATIONS} iterations on a batch of {len(SENTENCES)} sentences.")

    avg_hf_minilm, dev_hf_minilm = benchmark_hf_minilm(SENTENCES, ITERATIONS, pytorch_device)
    avg_bge, dev_bge = benchmark_bge(SENTENCES, ITERATIONS, pytorch_device)
    avg_le, dev_le = benchmark_lightembed(SENTENCES, ITERATIONS, onnx_provider_name)
    avg_onnx, dev_onnx = benchmark_onnx_manual(SENTENCES, ITERATIONS, providers_list=onnx_providers)

    avg_fe_bge_q, dev_fe_bge_q = benchmark_fastembed_bge_onnx_q(SENTENCES, ITERATIONS, onnx_provider_name)

    results = {
        f"HF Transformers (MiniLM) [{dev_hf_minilm}]": avg_hf_minilm,
        f"SentenceTransformer (BGE) [{dev_bge}]": avg_bge,
        f"FastEmbed (BGE Quant ONNX) [{dev_fe_bge_q}]": avg_fe_bge_q,
        f"LightEmbed (MiniLM ONNX) [{dev_le}]": avg_le,
        f"Manual ONNX (MiniLM ONNX) [{dev_onnx}]": avg_onnx
    }

    valid_results = {k: v for k, v in results.items() if v != float('inf')}

    if not valid_results:
        print("\nAll benchmarks failed or were skipped.")
        return

    fastest_method = min(valid_results, key=valid_results.get)

    print("\n--- Comparison ---")

    for method, avg_time in results.items():
        status = f"{avg_time:.6f} seconds" if avg_time != float('inf') else "Failed/Skipped"
        print(f"Avg {method}: {status}")


    print(f"\nResult: {fastest_method} was fastest.")


if __name__ == "__main__":
    main()
