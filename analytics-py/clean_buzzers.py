# clean_buzzers.py

import sqlite3
import pandas as pd
import re

DB_PATH = '../data/skripsi_bsi_v2.db'

# Kata kunci yang sering di-copy-paste oleh buzzer promosi
PROMO_KEYWORDS = [
    'bewizebisnisjadimudah', 'kemilauemassilaturahmibsi', 'inovasi terbaru',
    'fitur digital single access', 'newest global sharia banking technology',
    'open banking, technology stack', 'platform terpadu', 'resmi diluncurkan pada'
]

PROMO_PATTERN = re.compile(r'\b(?:' + '|'.join(map(re.escape, PROMO_KEYWORDS)) + r')\b', re.IGNORECASE)

def clean_and_deduplicate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Ambil semua data
    print("Mengambil data dari database...")
    df = pd.read_sql("SELECT id, raw_content, label, label_ai FROM tweets", conn)
    awal = len(df)

    # 2. Normalisasi teks untuk keperluan deduplikasi (hilangkan mention dan URL)
    print("Memproses deduplikasi teks...")
    df['clean_text'] = df['raw_content'].astype(str).str.lower()
    df['clean_text'] = df['clean_text'].apply(lambda x: re.sub(r'@[a-z0-9_]+', '', x)) # Hapus mention
    df['clean_text'] = df['clean_text'].apply(lambda x: re.sub(r'http\S+', '', x)) # Hapus URL
    df['clean_text'] = df['clean_text'].str.replace(r'[^a-z0-9\s]', '', regex=True) # Hapus tanda baca
    df['clean_text'] = df['clean_text'].str.strip()

    # 3. Hapus duplikat (pertahankan tweet pertama yang masuk)
    df_dedup = df.drop_duplicates(subset=['clean_text'], keep='first').copy()
    akhir = len(df_dedup)
    print(f"Berhasil menghapus {awal - akhir} baris duplikat/spam buzzer.")

    # 4. Paksa tweet berskema promosi menjadi 'neutral'
    print("Mengoreksi label promosi menjadi netral...")
    updates = []
    for _, row in df_dedup.iterrows():
        current_label = row['label']
        content = str(row['raw_content']).lower()
        
        # Jika terdeteksi bahasa kampanye/brosur, jadikan netral
        if PROMO_PATTERN.search(content) and current_label == 'positive':
            updates.append(('neutral', row['id']))
            
    # Eksekusi update ke database
    if updates:
        cursor.executemany("UPDATE tweets SET label = ? WHERE id = ?", updates)
        conn.commit()
        print(f"Berhasil mengoreksi {len(updates)} label promosi menjadi netral.")

    conn.close()
    print("Pembersihan selesai.")

if __name__ == "__main__":
    clean_and_deduplicate()