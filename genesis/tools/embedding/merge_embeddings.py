import time, os, psycopg2, psycopg2.extras, numpy as np
from pgvector.psycopg2 import register_vector
from tqdm import tqdm
import logging
from collections import defaultdict
from dotenv import load_dotenv
import sys

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
try:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.abspath(os.path.join(script_dir, "..", "..", "..", ".env"))
    if not os.path.exists(dotenv_path):
        raise FileNotFoundError(f".env not found: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)
except Exception as e:
    logging.error(e)
    sys.exit(1)

SOURCE_TABLE_NAME = "document_chunk_embeddings"
TARGET_TABLE_NAME = "document_embeddings"
URL_FETCH_BATCH_SIZE = 1000
DB_INSERT_BATCH_SIZE = 5000

PRIVATE_DB_URL = os.getenv("PRIVATE_DB_URL")
if not PRIVATE_DB_URL:
    logging.error("DB URL not set")
    sys.exit(1)


def connect_db():
    try:
        conn = psycopg2.connect(PRIVATE_DB_URL)
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '600s';")
        return conn
    except Exception as e:
        logging.error(e)
        raise


def get_embedding_dimension(conn):
    with conn.cursor() as cur:
        cur.execute(f"SELECT embedding FROM {SOURCE_TABLE_NAME} LIMIT 1;")
        result = cur.fetchone()
        if result and result[0] is not None:
            return len(result[0])
        logging.error("Embedding dimension not determined.")
        return None


def create_merged_table_if_not_exists(conn, embedding_dim):
    if embedding_dim is None:
        logging.error("No embedding dimension.")
        return False
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TARGET_TABLE_NAME} (
                url TEXT PRIMARY KEY,
                embedding VECTOR({embedding_dim})
            );
        """
        )
        cur.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_{TARGET_TABLE_NAME}_embedding
            ON {TARGET_TABLE_NAME} USING hnsw (embedding vector_l2_ops);
        """
        )
        conn.commit()
    return True


def fetch_distinct_urls(conn):
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT DISTINCT s.url
            FROM {SOURCE_TABLE_NAME} s
            LEFT JOIN {TARGET_TABLE_NAME} t ON s.url = t.url
            WHERE t.url IS NULL;
        """
        )
        return [row[0] for row in cur.fetchall()]


def process_url_batch(conn, urls_batch):
    merged = {}
    if not urls_batch:
        return merged
    query = f"SELECT url, embedding FROM {SOURCE_TABLE_NAME} WHERE url = ANY(%s);"
    groups = {}
    with conn.cursor() as cur:
        cur.execute(query, (urls_batch,))
        for url, emb in cur.fetchall():
            if emb is not None:
                groups.setdefault(url, []).append(np.array(emb))
    for url, arr in groups.items():
        merged[url] = np.mean(np.stack(arr), axis=0).tolist()
    return merged


def insert_merged_embeddings(conn, data_batch):
    if not data_batch:
        return 0
    query = f"""
        INSERT INTO {TARGET_TABLE_NAME} (url, embedding)
        VALUES %s
        ON CONFLICT (url) DO UPDATE SET embedding = EXCLUDED.embedding;
    """
    try:
        with conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                query,
                data_batch,
                template="(%s, %s::vector)",
                page_size=len(data_batch),
            )
        conn.commit()
        return len(data_batch)
    except Exception as e:
        logging.error(e)
        conn.rollback()
        return 0


if __name__ == "__main__":
    overall_start = time.time()
    conn = connect_db()
    embedding_dim = get_embedding_dimension(conn)
    if embedding_dim is None or not create_merged_table_if_not_exists(
        conn, embedding_dim
    ):
        sys.exit(1)
    urls = fetch_distinct_urls(conn)
    if not urls:
        sys.exit(0)
    total = len(urls)
    processed = 0
    batch_data = []
    pbar = tqdm(total=total, desc="Merging", unit="url")
    for i in range(0, total, URL_FETCH_BATCH_SIZE):
        batch_urls = urls[i : i + URL_FETCH_BATCH_SIZE]
        merged_results = process_url_batch(conn, batch_urls)
        for url, emb in merged_results.items():
            batch_data.append((url, emb))
        if len(batch_data) >= DB_INSERT_BATCH_SIZE:
            processed += insert_merged_embeddings(conn, batch_data)
            batch_data = []
        pbar.update(len(batch_urls))
    if batch_data:
        processed += insert_merged_embeddings(conn, batch_data)
    pbar.close()
    conn.close()
    logging.info(
        f"Completed in {time.time()-overall_start:.2f} sec. Processed: {processed}"
    )
