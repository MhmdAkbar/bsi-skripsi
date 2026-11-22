import json  # <- SEKARANG SUDAH DITAMBAHKAN
import sqlite3
import dateutil.parser
import os
import re

# =========================================================
# INPUT FILE (Diubah dari folder menjadi file spesifik)
# =========================================================

file_path = "../data/" + input(
    "Masukkan nama/path file JSON (contoh: data.json atau ../folder/data.json): "
).strip()

if not os.path.exists(file_path):
    print(f"Error: File '{file_path}' tidak ditemukan.")
    exit()

# Kita bungkus dalam list agar perulangan di bawahnya tetap berjalan normal
json_files = [file_path]

print(f"\nFile JSON ditemukan dan siap diproses.")

# =========================================================
# DATABASE SETUP
# =========================================================

db_name = "skripsi_bsi_v2.db"

db_path = os.path.join("../data", db_name)

# Memastikan folder ../data sudah ada sebelum membuat database
os.makedirs(os.path.dirname(db_path), exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# =========================================================
# DATABASE SCHEMA
# =========================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS tweets (
    id TEXT PRIMARY KEY,
    raw_content TEXT NOT NULL,
    cleaned_content TEXT NOT NULL UNIQUE,
    username TEXT,
    display_name TEXT,
    created_at DATETIME,
    lang TEXT,
    like_count INTEGER DEFAULT 0,
    retweet_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    label TEXT DEFAULT 'unlabeled'
)
""")
conn.commit()

# =========================================================
# PRE-LOAD MEMORY DEDUPLICATION
# =========================================================

cursor.execute("SELECT cleaned_content FROM tweets")
processed_texts = {row[0] for row in cursor.fetchall()}
print(f"Memuat {len(processed_texts)} tweet dari database untuk deduplikasi memori.")

# =========================================================
# CONFIGURATION
# =========================================================

BLACKLIST_USERS = {
    'bankbsi_id', 'bsihelp', 'lifewithbsi', 'kontan_id',
    'detikcom', 'kompascom', 'cnbcindonesia', 'tokopediacare',
    'pdi_perjuangan', 'schfess', 'bemfikomunisba'
}

BOT_NAME_KEYWORDS = {
    'bot', 'news', 'berita', 'info', 'update',
    'base', 'campus', 'pts', 'autobase'
}

# =========================================================
# REGEX PATTERNS
# =========================================================

BSI_PATTERN = re.compile(
    r'\b('
    r'bsi|'
    r'bank syariah indonesia|'
    r'bank syariah|'
    r'bsi mobile|'
    r'byond|'
    r'bank emas'
    r')\b',
    re.IGNORECASE
)

SECONDARY_PATTERN = re.compile(
    r'\b('
    r'atm|'
    r'rekening|'
    r'saldo|'
    r'transfer|'
    r'qris|'
    r'otp|'
    r'tabungan|'
    r'error|'
    r'gangguan|'
    r'maintenance|'
    r'cs|'
    r'lelet|'
    r'nyangkut'
    r')\b',
    re.IGNORECASE
)

BSI_STRICT_PATTERN = re.compile(r'\bbsi\b', re.IGNORECASE)

# =========================================================
# TEXT CLEANING
# =========================================================

def clean_text(text):
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', ' ', text)
    text = re.sub(r'@\w+', ' ', text)
    text = re.sub(r'#', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# =========================================================
# METRICS
# =========================================================

count_saved = 0
count_duplicate = 0
count_irrelevant = 0
count_retweet = 0
count_bot = 0
count_short = 0
count_error = 0
count_total_processed = 0

# =========================================================
# MAIN PROCESS
# =========================================================

print("\n" + "=" * 60)
print("MEMULAI PROSES DATA INGESTION")
print("=" * 60)

for file_index, json_file in enumerate(json_files, start=1):

    print(f"\n[{file_index}/{len(json_files)}] Processing: {os.path.basename(json_file)}")

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except Exception as e:
        print(f"❌ Gagal membaca file: {e}")
        continue

    file_saved = 0

    for item_index, item in enumerate(raw_data, start=1):

        count_total_processed += 1

        if item_index % 500 == 0:
            print(
                f"   -> {item_index}/{len(raw_data)} tweet diproses | "
                f"Saved: {count_saved} | "
                f"Duplicate: {count_duplicate}",
                end="\r"
            )

        try:
            raw_content = item.get("text", "").strip()

            if not raw_content:
                count_irrelevant += 1
                continue

            cleaned_content = clean_text(raw_content)
            lang = item.get("lang", "").lower()
            username = item.get("author.username", "").lower().strip()
            display_name = item.get("author.name", "").lower().strip()

            # =============================================
            # RETWEET FILTER
            # =============================================
            is_retweet = (
                cleaned_content.startswith("rt ")
                or cleaned_content.startswith("rt@")
                or item.get("isRetweet", False)
            )

            if is_retweet:
                count_retweet += 1
                continue

            # =============================================
            # SHORT TEXT FILTER
            # =============================================
            if len(cleaned_content.split()) < 3:
                count_short += 1
                continue

            # =============================================
            # SPAM FILTER
            # =============================================
            if cleaned_content.count("bsi") > 5:
                count_irrelevant += 1
                continue

            # =============================================
            # RELEVANCE FILTER
            # =============================================
            is_primary_match = bool(BSI_PATTERN.search(cleaned_content))
            is_secondary_match = (
                bool(BSI_STRICT_PATTERN.search(cleaned_content))
                and bool(SECONDARY_PATTERN.search(cleaned_content))
            )

            is_relevant = is_primary_match or is_secondary_match

            if not is_relevant:
                count_irrelevant += 1
                continue

            # =============================================
            # LANGUAGE FILTER
            # =============================================
            if lang not in ["id", "in"]:
                count_irrelevant += 1
                continue

            # =============================================
            # BOT FILTER
            # =============================================
            is_blacklist_user = username in BLACKLIST_USERS
            is_bot_name = any(
                keyword in display_name
                for keyword in BOT_NAME_KEYWORDS
            )

            if is_blacklist_user or is_bot_name:
                count_bot += 1
                continue

            # =============================================
            # MEMORY DEDUPLICATION
            # =============================================
            if cleaned_content in processed_texts:
                count_duplicate += 1
                continue

            # =============================================
            # DATE PARSING
            # =============================================
            created_at_raw = item.get("createdAt")

            if not created_at_raw:
                count_error += 1
                continue

            dt = dateutil.parser.parse(created_at_raw)
            created_at = dt.strftime("%Y-%m-%d %H:%M:%S")

            # =============================================
            # ENGAGEMENT
            # =============================================
            like_count = item.get("likeCount", 0)
            retweet_count = item.get("retweetCount", 0)
            reply_count = item.get("replyCount", 0)

            # =============================================
            # INSERT DATABASE
            # =============================================
            cursor.execute("""
            INSERT OR IGNORE INTO tweets (
                id, raw_content, cleaned_content, username, display_name,
                created_at, lang, like_count, retweet_count, reply_count, label
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item.get("id"), raw_content, cleaned_content, username, display_name,
                created_at, lang, like_count, retweet_count, reply_count, "unlabeled"
            ))

            if cursor.rowcount == 1:
                processed_texts.add(cleaned_content)
                count_saved += 1
                file_saved += 1
            else:
                count_duplicate += 1

        except Exception as e:
            count_error += 1
            print(f"\n❌ Error ID {item.get('id')}: {e}")

    conn.commit()

    print(
        f"\n✅ File selesai | "
        f"Saved dari file ini: {file_saved}"
    )

# =========================================================
# FINALIZE
# =========================================================
conn.close()

# =========================================================
# FINAL REPORT
# =========================================================
print("\n" + "=" * 60)
print("FINAL DATA INGESTION REPORT")
print("=" * 60)

print(f"Total Tweet Diproses     : {count_total_processed}")
print(f"Berhasil Disimpan        : {count_saved}")
print(f"Duplicate Dibuang        : {count_duplicate}")
print(f"Retweet Dibuang          : {count_retweet}")
print(f"Bot/Blacklist Dibuang    : {count_bot}")
print(f"Tweet Pendek Dibuang     : {count_short}")
print(f"Tweet Tidak Relevan      : {count_irrelevant}")
print(f"Error Processing         : {count_error}")

print("=" * 60)
print(f"Database tersimpan di: {db_path}")
print("SELESAI\n")