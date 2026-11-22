import sqlite3
import pandas as pd

DB_PATH = '../data/skripsi_bsi.db'

def update_skor_sentimen():
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Ambil data tweet yang sudah berlabel
    query = "SELECT date, label FROM tweets WHERE label IN ('positive', 'negative', 'neutral')"
    df = pd.read_sql(query, conn)
    
    if df.empty:
        print("Belum ada data yang dilabeli.")
        return

    # 2. Buat kolom periode (YYYY-MM) dari kolom date (YYYY-MM-DD HH:MM:SS)
    df['periode'] = df['date'].str[:7]
    
    # 3. Hitung jumlah tiap label per bulan
    pivot = df.pivot_table(index='periode', columns='label', aggfunc='size', fill_value=0)
    
    # Pastikan kolom ada untuk menghindari error
    for col in ['positive', 'negative', 'neutral']:
        if col not in pivot.columns:
            pivot[col] = 0
            
    pivot['total'] = pivot['positive'] + pivot['negative'] + pivot['neutral']
    
    # 4. Rumus Normalisasi Sentimen (0 sampai 1)
    pivot['nss'] = (pivot['positive'] - pivot['negative']) / pivot['total']
    pivot['skor_sentimen'] = (pivot['nss'] + 1) / 2
    
    # 5. Update ke tabel kinerja_bulanans
    cursor = conn.cursor()
    for index, row in pivot.iterrows():
        periode = index
        skor = row['skor_sentimen']
        cursor.execute("UPDATE kinerja_bulanans SET skor_sentimen = ? WHERE periode = ?", (skor, periode))
        
    conn.commit()
    conn.close()
    print("Skor Sentimen berhasil dihitung dan di-update ke tabel kinerja_bulanans!")

if __name__ == "__main__":
    update_skor_sentimen()