import requests
import zipfile
import os
import json
import psycopg2
import psycopg2.extras
import os
import sys
import time
import math
from dotenv import load_dotenv

SPELLING_DATA_BASE="https://raw.githubusercontent.com/first20hours/google-10000-english/refs/heads/master/google-10000-english.txt"
FILE="words_alpha.txt"

script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(script_dir, '..', '..', '..', '.env'))
BATCH_SIZE = 100
TABLE_NAME = "dictionary"

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

# spelling_correction

def download_spelling_data():
    """
    Download the spelling data from the given URL and save it to the current directory.
    """
    response = requests.get(SPELLING_DATA_BASE)
    if response.status_code == 200:
        with open(FILE, "wb") as f:
            f.write(response.content)
        print("Spelling data downloaded successfully.")
    else:
        print(f"Failed to download spelling data. Status code: {response.status_code}")

def insert_data(conn, data):
    """Inserts data into the wordnet table using execute_values."""
    insert_sql = f"""
    INSERT INTO {TABLE_NAME} (
        word, weight
    ) VALUES %s
    ON CONFLICT DO NOTHING;
    """
    values_to_insert = []
    total_inserted = 0
    start_time = time.time()

    print(f"Preparing and inserting data in batches of {BATCH_SIZE}...")

    for i, entry in enumerate(data):
        values_to_insert.append(entry)

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

                        print(
                            f"  Processed batch ending at item {i + 1}. Total inserted/updated so far: ~{total_inserted}/{len(data)}")
                        values_to_insert = []
                except psycopg2.Error as e:
                    print(f"\nError inserting batch ending at item {i + 1}: {e}")
                    print("Attempted values (first item):", values_to_insert[0] if values_to_insert else "N/A")
                    conn.rollback()
                    values_to_insert = []

    end_time = time.time()
    print(f"\nData insertion finished in {end_time - start_time:.2f} seconds.")
    print(f"Total entries processed/attempted: {len(data)}, Estimated inserted/updated: ~{total_inserted}")


def upload_spelling():
    with open(FILE, "r") as f:
        lines = f.readlines()
        data = [(line.strip(), -math.sqrt(i)) for i, line in enumerate(lines)]

    conn = None
    try:
        db_host_info = DB_URI.split('@')[-1] if '@' in DB_URI else DB_URI
        print(f"Connecting to database: {db_host_info}...")
        conn = psycopg2.connect(DB_URI)
        print("Connection successful.")

        insert_data(conn, data)

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

if __name__ == "__main__":
    download_spelling_data()
    upload_spelling()
    os.remove(FILE)