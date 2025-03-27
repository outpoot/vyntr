import json
import psycopg2
import psycopg2.extras
import os
import sys
import time
from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '.env'))

if os.path.exists(env_path):
    print(f"Loading environment variables from: {env_path}")
    load_dotenv(dotenv_path=env_path)
else:
    print(f"Warning: .env file not found at {env_path}.")
    sys.exit(1)

DB_URI = os.getenv("PRIVATE_DB_URL")

if not os.getenv("PRIVATE_DB_URL"):
     print("Warning: PRIVATE_DB_URL not found in environment or .env file.")
     sys.exit(1)

# --- Configuration ---
JSON_FILE_PATH = "wn.json"
TABLE_NAME = "wordnet"
BATCH_SIZE = 1000
# --- End Configuration ---

def create_table(conn):
    """Creates the wordnet table if it doesn't exist."""
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
        id TEXT PRIMARY KEY,
        word TEXT NOT NULL,
        part_of_speech VARCHAR(50),
        pronunciations TEXT[],
        definitions JSONB,
        examples TEXT[],
        synonyms TEXT[],
        antonyms TEXT[],
        similar_words TEXT[]
    );
    """
    try:
        with conn.cursor() as cur:
            print(f"Creating table '{TABLE_NAME}' if it doesn't exist...")
            cur.execute(create_table_sql)
            conn.commit()
            print("Table check/creation complete.")
    except psycopg2.Error as e:
        print(f"Error creating table: {e}")
        conn.rollback()
        raise

def create_indexes(conn):
    """Creates necessary indexes, including the trigram index."""

    create_trgm_index_sql = f"""
    CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_word_trgm
    ON {TABLE_NAME}
    USING gin (word gin_trgm_ops);
    """
    try:
        with conn.cursor() as cur:
            print("Creating GIN trigram index on 'word' column (if needed)...")
            cur.execute(create_trgm_index_sql)
            conn.commit()
            print("Index creation complete.")
    except psycopg2.Error as e:
        print(f"Error creating indexes: {e}")
        conn.rollback()
        raise

def load_data_from_json(file_path):
    """Loads word entries from the JSON file."""
    if not os.path.exists(file_path):
        print(f"Error: JSON file not found at '{file_path}'")
        sys.exit(1)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            print(f"Loading data from '{file_path}'...")
            data = json.load(f)
            print(f"Loaded {len(data)} entries from JSON.")
            return data
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        sys.exit(1)
    except IOError as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)


def insert_data(conn, data):
    """Inserts data into the wordnet table using execute_values."""
    insert_sql = f"""
    INSERT INTO {TABLE_NAME} (
        id, word, part_of_speech, pronunciations, definitions,
        examples, synonyms, antonyms, similar_words
    ) VALUES %s
    ON CONFLICT (id) DO NOTHING; -- Ignore duplicates based on primary key 'id'
    """
    values_to_insert = []
    total_inserted = 0
    start_time = time.time()

    print(f"Preparing and inserting data in batches of {BATCH_SIZE}...")

    for i, entry in enumerate(data):
        definitions_json = json.dumps(entry.get('definitions')) if entry.get('definitions') else None

        values_to_insert.append((
            entry.get('id'),
            entry.get('word'),
            entry.get('partOfSpeech'),
            entry.get('pronunciations'),
            definitions_json,
            entry.get('examples'),
            entry.get('synonyms'),
            entry.get('antonyms'),
            entry.get('similar_words')
        ))

        if len(values_to_insert) >= BATCH_SIZE or (i + 1) == len(data):
            if values_to_insert:
                try:
                    with conn.cursor() as cur:
                        psycopg2.extras.execute_values(
                            cur, insert_sql, values_to_insert, page_size=BATCH_SIZE
                        )
                        inserted_count = cur.rowcount
                        # use actual count if available and > 0, otherwise assume batch size for progress
                        actual_inserted_this_batch = inserted_count if inserted_count > 0 else len(values_to_insert)
                        total_inserted += actual_inserted_this_batch
                        conn.commit()

                        print(f"  Processed batch ending at item {i+1}. Total inserted/updated so far: ~{total_inserted}/{len(data)}")
                        values_to_insert = []
                except psycopg2.Error as e:
                    print(f"\nError inserting batch ending at item {i+1}: {e}")
                    print("Attempted values (first item):", values_to_insert[0] if values_to_insert else "N/A")
                    conn.rollback()
                    values_to_insert = []

    end_time = time.time()
    print(f"\nData insertion finished in {end_time - start_time:.2f} seconds.")
    print(f"Total entries processed/attempted: {len(data)}, Estimated inserted/updated: ~{total_inserted}")


if __name__ == "__main__":
    word_data = load_data_from_json(JSON_FILE_PATH)

    conn = None
    try:
        db_host_info = DB_URI.split('@')[-1] if '@' in DB_URI else DB_URI
        print(f"Connecting to database: {db_host_info}...")
        conn = psycopg2.connect(DB_URI)
        print("Connection successful.")

        create_table(conn)
        insert_data(conn, word_data)
        create_indexes(conn)

        print("\nDatabase setup and data loading complete.")

    except psycopg2.OperationalError as e:
        print(f"\nDatabase connection failed: {e}")
        print("Please ensure the database server is running and accessible,")
        print(f"and the connection URI (read from PRIVATE_DB_URL or default) is correct: {db_host_info}")
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")

