# F:\skripsi\bsi-skripsi\analytics-py\import_csv_tweets.py
import pandas as pd
import sqlite3
import os
import re

# =========================================================
# CONFIGURATION
# =========================================================

# Database setup
DB_NAME = "skripsi_bsi_v2.db"
DB_PATH = os.path.join("../data", DB_NAME)

# Path to your CSV file
CSV_FILE = "../data/bsi_24k_tweets.csv" 

def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', ' ', text)
    text = re.sub(r'@\w+', ' ', text)
    text = re.sub(r'#', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def import_csv_to_db():
    if not os.path.exists(CSV_FILE):
        print(f"Error: File '{CSV_FILE}' tidak ditemukan.")
        return

    # Load CSV
    print(f"Membaca {CSV_FILE}...")
    df = pd.read_csv(CSV_FILE)

    # Database connection
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Pre-load existing data for deduplication
    cursor.execute("SELECT cleaned_content FROM tweets")
    processed_texts = {row[0] for row in cursor.fetchall()}
    
    saved_count = 0
    dup_count = 0

    print("Memulai proses injeksi ke database...")

    for _, row in df.iterrows():
        # Map CSV columns to Database columns
        raw_content = str(row.get('Tweet', ''))
        cleaned_content = clean_text(raw_content)
        
        # Deduplication check
        if cleaned_content in processed_texts:
            dup_count += 1
            continue
            
        try:
            cursor.execute("""
            INSERT INTO tweets (
                id, raw_content, cleaned_content, username, 
                created_at, lang, like_count, retweet_count, reply_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row.get('ID')),
                raw_content,
                cleaned_content,
                str(row.get('Username')),
                str(row.get('Date')),
                str(row.get('Language')),
                int(row.get('Likes', 0)),
                int(row.get('Reetweets', 0)),
                int(row.get('Replies', 0))
            ))
            processed_texts.add(cleaned_content)
            saved_count += 1
        except Exception as e:
            print(f"Error inserting ID {row.get('ID')}: {e}")

    conn.commit()
    conn.close()
    print(f"\nProses Selesai.")
    print(f"Data baru disimpan: {saved_count}")
    print(f"Duplikat diabaikan: {dup_count}")

if __name__ == "__main__":
    import_csv_to_db()