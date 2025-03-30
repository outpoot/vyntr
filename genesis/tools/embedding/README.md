# Embedding Tools

Collection of tools for benchmarking, generating, and cost estimation of embeddings.

## Overview

### Benchmarking
- `benchmark.py`
  - Benchmarks different embedding models and implementations to find the fastest option. Based on dummy data.
```bash
python benchmark.py
```
Compares **HuggingFace**, **ONNX**, **LightEmbed**, and **FastEmbed** implementations.

- `partition_benchmark.py`
  - Tests embedding generation on a single partition for performance analysis. Based on a real sample.
```bash
python partition_benchmark.py partition=00
```
Useful for estimating full dataset processing time.

### Generation
- `generate_embeddings.py`
  - Generates embeddings from S3-stored dataset files and stores them in PostgreSQL.
```bash
python generate_embeddings.py
```
Requires environment variables for S3 and PostgreSQL configuration. Refer to the **main** `README.md`.

- `price.py`
  - Estimates embedding generation costs based on token count.
```bash
python price.py
```
Uses current OpenAI pricing for text-embedding-3-small.
> [!NOTE]
> We use `all-MiniLM-L6-v2` internally. However, this script was written before we decided what model to use.
> We used `price.py` to calculate the token count for estimations on total duration.

If the script doesn't detect CUDA, run the following commands:
```
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
uv pip install beautifulsoup4 boto3 chardet python-dotenv fastembed h5py huggingface-hub light-embed nltk onnxruntime-gpu pgvector psycopg2-binary sentence-transformers tiktoken transformers tqdm numpy psycopg2
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"
```

If you see `"CUDA available: True"`and `PyTorch version: x.x.x+cu1xx`, you should be good to go.

## Environment Setup
### .env
For `.env`, head to the main **README.md**, section "Environment".

### Python
We use [uv](https://github.com/astral-sh/uv), a Python package & project manager. 

1. Install [uv](https://github.com/astral-sh/uv)
    - 🐧 Linux / macOS `curl -LsSf https://astral.sh/uv/install.sh | sh`
    - 🪟 Windows `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
    - or, with `pip install uv`
    - or, with `pipx install uv` 
2. Run `uv sync`
3. You are done! Files inside this folder should now run flawlessly via `uv run <script>`

## Technical Details
- ONNX acceleration available when configured
- Batch processing for optimal performance
- Automatic device selection (CUDA/CPU)

> [!NOTE]
> GPU support requires CUDA toolkit and appropriate drivers to be installed.
> Embedding generation has run on Linux for the official Vyntr dataset.

## Recommendations
1. Run `benchmark.py` first to identify the fastest model for your setup
2. Use `price.py` to estimate embedding costs
3. Run `partition_benchmark.py` for a quick real-world performance test
4. Start full dataset processing with `generate_embeddings.py`

> [!TIP]
> For large datasets, consider running a small partition first to verify the entire pipeline.
