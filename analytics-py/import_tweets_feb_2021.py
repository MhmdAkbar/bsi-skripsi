import json
import sqlite3
import dateutil.parser

# Load JSON hasil scraping
with open('../data/hasil_scrape_feb_2021.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# Koneksi ke DB
conn = sqlite3.connect('../data/skripsi_bsi.db')
cursor = conn.cursor()

# Keyword untuk memastikan ini tentang BANK
keywords = ['bank', 'syariah', 'merger', 'wadiah', 'bris', 'bnis', 'bsm', 'atm', 'mobile', 'rekening']

count_saved = 0
count_ignored = 0

for item in raw_data:
    text = item.get('text', '').lower()
    lang = item.get('lang', '')
    
    # FILTER LOGIC: Harus bahasa Indonesia DAN punya keyword relevan
    is_relevant = any(kw in text for kw in keywords)
    
    if lang == 'in' and is_relevant:
        # Konversi format tanggal Twitter ke format DB (YYYY-MM-DD)
        dt = dateutil.parser.parse(item['createdAt'])
        clean_date = dt.strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute("""
                INSERT INTO tweets (id, content, date, label) 
                VALUES (?, ?, ?, ?)
            """, (item['id'], item['text'], clean_date, ""))
            count_saved += 1
        except sqlite3.IntegrityError:
            # Lewati jika ID sudah ada (duplikat)
            pass
    else:
        count_ignored += 1

conn.commit()
conn.close()

print(f"Selesai! Disimpan: {count_saved} tweet | Dibuang (Noise): {count_ignored} tweet")