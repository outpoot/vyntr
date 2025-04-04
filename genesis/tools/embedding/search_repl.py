import os
import sys
import logging
import time
import torch
import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv
import numpy as np

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

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

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TARGET_TABLE_NAME = "document_embeddings"
TOP_K = 10
MAX_SEQ_LENGTH = 512

PRIVATE_DB_URL = os.getenv("PRIVATE_DB_URL")
if not PRIVATE_DB_URL:
    logging.error("Database URL not configured (PRIVATE_DB_URL). Exiting.")
    sys.exit(1)


def connect_db():
    try:
        conn = psycopg2.connect(PRIVATE_DB_URL)
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '30s';")
        logging.info("Successfully connected to database")
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        raise


def load_model_and_tokenizer():
    logging.info(f"Loading tokenizer and model: {MODEL_NAME}")
    model = None
    tokenizer = None
    device = "cpu"
    model_precision = "FP32"

    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logging.info(f"GPU detected: {gpu_name}. Attempting to load model on GPU.")
            try:
                device = "cuda"
                model = AutoModel.from_pretrained(MODEL_NAME)
                model.to(device)
                model_precision = "FP32"
                logging.info(f"Successfully loaded model in FP32 on {device}.")
            except Exception as e:
                logging.warning(
                    f"Failed to load model on GPU: {e}. Falling back to CPU."
                )
                device = "cpu"
                model = AutoModel.from_pretrained(MODEL_NAME)
                model_precision = "FP32"
        else:
            logging.warning(
                "CUDA not available. Using CPU with default precision (FP32)."
            )
            device = "cpu"
            model = AutoModel.from_pretrained(MODEL_NAME)
            model_precision = "FP32"

        model.eval()
        embedding_dim = model.config.hidden_size
        logging.info(
            f"Model ready. Precision: {model_precision}. Device: {device}. Embedding Dim: {embedding_dim}"
        )
        return model, tokenizer, device, embedding_dim

    except Exception as e:
        logging.error(f"Model or Tokenizer loading failed: {e}", exc_info=True)
        sys.exit(1)


def get_query_embedding(query_text, model, tokenizer, device, max_seq_len):
    try:
        inputs = tokenizer(
            query_text,
            return_tensors="pt",
            truncation=True,
            padding="max_length",
            max_length=max_seq_len,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)

        embedding = outputs.last_hidden_state.mean(dim=1)
        return embedding.cpu().numpy()[0]
    except Exception as e:
        logging.error(f"Error generating query embedding: {e}", exc_info=True)
        return None


def search_similar_documents(conn, query_embedding, table_name, top_k):
    if query_embedding is None:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT url, embedding <=> %s::vector AS distance
                FROM {table_name}
                ORDER BY distance ASC
                LIMIT %s;
                """,
                (query_embedding.tolist(), top_k),
            )
            results = cur.fetchall()
            return results
    except psycopg2.Error as db_err:
        logging.error(f"Database search failed: {db_err}")
        conn.rollback()
        return []
    except Exception as e:
        logging.error(f"Unexpected error during search: {e}", exc_info=True)
        return []


if __name__ == "__main__":
    model, tokenizer, device, embedding_dim = load_model_and_tokenizer()
    conn = None
    try:
        conn = connect_db()

        while True:
            try:
                query = input("\nEnter search query (or 'quit' to exit): ").strip()
                if query.lower() == "quit":
                    break
                if not query:
                    continue

                start_time = time.time()

                query_vec = get_query_embedding(
                    query, model, tokenizer, device, MAX_SEQ_LENGTH
                )

                if query_vec is not None:
                    search_results = search_similar_documents(
                        conn, query_vec, TARGET_TABLE_NAME, TOP_K
                    )
                    end_time = time.time()

                    logging.info(
                        f"Search completed in {end_time - start_time:.4f} seconds."
                    )

                    if search_results:
                        print(f"\n--- Top {len(search_results)} Results ---")
                        for i, (url, distance) in enumerate(search_results):
                            print(f"{i+1}. URL: {url} (Distance: {distance:.4f})")
                    else:
                        print("No results found or error during search.")
                else:
                    print("Failed to generate embedding for the query.")

            except EOFError:
                break
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as loop_err:
                logging.error(f"Error in REPL loop: {loop_err}", exc_info=True)
                time.sleep(1)

    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")
