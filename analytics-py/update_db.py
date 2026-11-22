# analytics-py/update_db.py
import sqlite3

DB_PATH = '../data/skripsi_bsi.db'

def update_schema():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Menambahkan kolom label_ai ke tabel tweets
        cursor.execute("ALTER TABLE tweets ADD COLUMN label_ai TEXT")
        conn.commit()
        print("✅ Kolom 'label_ai' berhasil ditambahkan ke database!")
    except sqlite3.OperationalError as e:
        # Jika kolom sudah ada, lewati
        if "duplicate column name" in str(e):
            print("⚠️ Kolom 'label_ai' sudah ada di database.")
        else:
            print(f"❌ Terjadi kesalahan: {e}")
            
    conn.close()

if __name__ == "__main__":
    update_schema()