# F:\skripsi\bsi-skripsi\analytics-py\fix_sentiment.py

import sqlite3
import pandas as pd
import re
from tqdm import tqdm

DB_PATH = '../data/skripsi_bsi_v2.db'

# 1. Tambahkan frasa negasi (penyangkalan pujian) ke daftar negatif
NEG_KEYWORDS = [
    'gangguan', 'error', 'eror', 'lelet', 'lemot', 'down', 'maintenance', 'lola',
    'ngadat', 'muter', 'loading', 'timeout', 'bug', 'crash', 'gagal', 'gabisa',
    'ga bisa', 'ketahan', 'nyangkut', 'belum masuk', 'blm masuk', 'potong saldo',
    'saldo hilang', 'duit ilang', 'uang hilang', 'kembalikan',
    'hack', 'hacker', 'bobol', 'dibobol', 'retas', 'diretas', 'ransomware', 'lockbit',
    'bocor', 'kebocoran', 'dark web', 'darkweb', '1,5 tb', '1.5 tb', 'tebusan',
    'kecewa', 'kcewa', 'parah', 'buruk', 'jelek', 'hancur', 'payah', 'nyesel', 'menyesal',
    'males', 'ribet', 'repot', 'kacau', 'capek', 'pusing', 'muak', 'gaguna',
    'ga guna', 'sampah', 'ampas', 'tolol', 'goblok', 'gblk', 'bego', 'anjing',
    'anjg', 'bangsat', 'bgst', 'tai', 'taik', 'babi', 'monyet', 'sialan',
    'brengsek', 'jancok', 'cuk', 'kocak', 'lawak', 'badut', 'sekelas', 'cuaks',
    'pindah bank', 'tutup rekening', 'uninstall', 'hapus aplikasi', 'ganti bank',
    'tarik semua', 'tarik dana', 'mending bca', 'mending mandiri',
    'mending bank sebelah', 'gembel', 'bosok', 'nilep', 'korupsi', 'blokir', 'keblokir',
    'bapuk', 'kurang enak', 'tidak aman', 'gak aman', 'ga aman', 'kurang bagus'
]

NEG_PATTERN = re.compile(r'(?:' + '|'.join(map(re.escape, NEG_KEYWORDS)) + r')', re.IGNORECASE)

CS_KEYWORDS = ['bantu', 'tolong', 'cara', 'min', 'kak', 'tanya']

# 2. Gunakan Regex dengan batas kata \b untuk POSITIVE KEYWORDS
# Ini mencegah "Obamanya" atau "keamanan" terdeteksi sebagai "aman"
POS_KEYWORDS = [
    'syukur', 'terima kasih', 'makasih', 'alhamdulillah', 'mantap', 
    'keren', 'bagus', 'terbaik', 'puas', 'lancar', 'mudah', 'aman'
]
POS_PATTERN = re.compile(r'\b(?:' + '|'.join(map(re.escape, POS_KEYWORDS)) + r')\b', re.IGNORECASE)

def run_recalibration():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = "SELECT id, raw_content, created_at, label_ai FROM tweets WHERE label_ai IS NOT NULL"
    df = pd.read_sql(query, conn)

    if df.empty:
        print("No AI-labeled data found.")
        return

    print(f"Recalibrating {len(df)} records with strict negation & boundary logic...")
    results = []

    for _, row in tqdm(df.iterrows(), total=len(df)):
        tweet_id = row['id']
        content = str(row['raw_content']).lower()
        
        ai_label = row['label_ai']
        final_label = ai_label

        # Layer 1: Cek kata negatif atau negasi (tidak aman, dll)
        if NEG_PATTERN.search(content):
            final_label = 'negative'
            
        # Layer 2: Turunkan derajat tweet CS
        elif final_label == 'positive' and any(word in content for word in CS_KEYWORDS):
            final_label = 'neutral'
            
        # Layer 3: Pengecekan pujian ketat (menghindari Obamanya)
        elif final_label == 'positive':
            if not POS_PATTERN.search(content):
                # Jika tweet tidak benar-benar memuji, paksa jadi netral (bukan negatif, agar lebih adil)
                final_label = 'neutral'

        results.append((final_label, tweet_id))

        if len(results) >= 5000:
            cursor.executemany("UPDATE tweets SET label = ? WHERE id = ?", results)
            conn.commit()
            results = []

    if results:
        cursor.executemany("UPDATE tweets SET label = ? WHERE id = ?", results)
        conn.commit()

    conn.close()
    print("Recalibration completed successfully.")

if __name__ == "__main__":
    run_recalibration()