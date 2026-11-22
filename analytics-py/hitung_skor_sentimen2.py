# F:\skripsi\bsi-skripsi\analytics-py\hitung_skor_sentimen2.py
import sqlite3
import pandas as pd

DB_PATH = '../data/skripsi_bsi_v2.db'

def update_skor_sentimen():
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Ambil data tweet yang sudah berlabel
    # Mengubah 'date' menjadi 'created_at' agar sesuai dengan database kamu
    query = "SELECT created_at, label FROM tweets WHERE label IN ('positive', 'negative', 'neutral')"
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("Belum ada data yang dilabeli.")
        conn.close()
        return

    # 2. Buat kolom periode (YYYY-MM) dari kolom created_at (format: YYYY-MM-DD HH:MM:SS)
    df['periode'] = df['created_at'].str[:7]
    
    # 3. Hitung jumlah tiap label per bulan
    pivot = df.pivot_table(index='periode', columns='label', aggfunc='size', fill_value=0)
    
    # Pastikan kolom ada untuk menghindari error
    for col in ['positive', 'negative', 'neutral']:
        if col not in pivot.columns:
            pivot[col] = 0
            
    pivot['total'] = pivot['positive'] + pivot['negative'] + pivot['neutral']
    
    # 4. Rumus Normalisasi Sentimen (0 sampai 1)
    # Menambahkan pengecekan pembagian dengan nol
    pivot['nss'] = (pivot['positive'] - pivot['negative']) / pivot['total'].replace(0, 1)
    pivot['skor_sentimen'] = (pivot['nss'] + 1) / 2
    
    # 5. Update ke tabel kinerja_bulanans
    cursor = conn.cursor()
    
    # Memastikan kolom skor_sentimen ada di tabel kinerja_bulanans
    cursor.execute("PRAGMA table_info(kinerja_bulanans)")
    cols = [row[1] for row in cursor.fetchall()]
    if 'skor_sentimen' not in cols:
        cursor.execute("ALTER TABLE kinerja_bulanans ADD COLUMN skor_sentimen REAL")
    
    for index, row in pivot.iterrows():
        periode = index
        skor = row['skor_sentimen']
        cursor.execute("UPDATE kinerja_bulanans SET skor_sentimen = ? WHERE periode = ?", (skor, periode))
        
    conn.commit()
    conn.close()
    print("Skor Sentimen berhasil dihitung dan di-update ke tabel kinerja_bulanans!")

if __name__ == "__main__":
    update_skor_sentimen()