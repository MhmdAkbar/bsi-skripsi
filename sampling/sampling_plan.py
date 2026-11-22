"""
================================================================================
RENCANA SAMPLING UNTUK PELABELAN MANUAL (MULTI-TAHUN)
================================================================================
Tujuan: dari tabel `tweets` mentah (yang belum dilabeli), tentukan tweet mana
saja yang perlu dilabeli manual, dengan aturan:

  - Bulan dengan volume <= FULL_LABEL_THRESHOLD  -> LABEL SEMUA (sensus penuh)
  - Bulan dengan volume >  FULL_LABEL_THRESHOLD  -> SAMPLING, stratified per
    hari supaya pola harian (mis. lonjakan sentimen akibat insiden tertentu)
    tetap bisa dianalisis, bukan hanya rata-rata bulanan yang menghilangkan
    dinamika harian.

Output: file CSV berisi daftar tweet yang TERPILIH untuk dilabeli, siap
diimpor ke dashboard labeling Anda, plus ringkasan rencana per bulan supaya
Anda tahu perkiraan beban kerja sebelum mulai.

STRUKTUR TABEL YANG DIASUMSIKAN (sesuaikan jika beda):
  tweets(id, raw_content, created_at, dataset_id)
================================================================================
"""

import sqlite3
import math
import pandas as pd
import numpy as np

# ============================================================
# KONFIGURASI
# ============================================================
DB_PATH = "../data/skripsi_bsi_v2.db"
TWEETS_TABLE = "tweets"

FULL_LABEL_THRESHOLD = 300      # <= ini, label semua (sensus)
DEFAULT_SAMPLE_TARGET = 384     # rumus Cochran, 95% confidence, margin 5%
CRISIS_MONTHS_TARGET = {        # override target sampel untuk bulan2 kritis
    "2023-05": 900,             # contoh: lonjakan volume di Mei 2023
}
MIN_PER_DAY_IN_SAMPLED_MONTH = 5   # minimum tweet/hari yang diambil kalau hari itu ada datanya
RANDOM_SEED = 42

OUTPUT_CSV = "tweets_to_label.csv"
SUMMARY_CSV = "labeling_plan_summary.csv"


# ============================================================
# 1. LOAD & HITUNG VOLUME PER BULAN
# ============================================================
def load_tweets(db_path: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        f"SELECT id, raw_content, created_at, dataset_id FROM {TWEETS_TABLE}",
        conn
    )
    conn.close()
    df["created_at"] = pd.to_datetime(
    df["created_at"],
    format="ISO8601",
    utc=True
)
    df["year_month"] = df["created_at"].dt.strftime("%Y-%m")
    df["date"] = df["created_at"].dt.date
    print(f"Total tweet di tabel '{TWEETS_TABLE}': {len(df)}")
    return df


def monthly_volume_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = df.groupby("year_month").size().reset_index(name="volume")
    summary = summary.sort_values("year_month")
    return summary


# ============================================================
# 2. TENTUKAN STRATEGI PER BULAN: SENSUS PENUH ATAU SAMPLING
# ============================================================
def determine_sample_size(month: str, volume: int) -> int:
    if volume <= FULL_LABEL_THRESHOLD:
        return volume  # label semua
    target = CRISIS_MONTHS_TARGET.get(month, DEFAULT_SAMPLE_TARGET)
    return min(target, volume)  # jangan minta lebih dari yang ada


# ============================================================
# 3. SAMPLING -- SENSUS UNTUK BULAN KECIL, STRATIFIED PER HARI UNTUK BULAN BESAR
# ============================================================
def stratified_sample_by_day(month_df: pd.DataFrame, target_n: int, rng) -> pd.DataFrame:
    """
    Alokasi proporsional per hari (berdasarkan volume harian), dengan floor
    minimum per hari supaya hari-hari dengan volume kecil tetap terwakili,
    lalu disesuaikan agar totalnya mendekati target_n.
    """
    daily_counts = month_df.groupby("date").size()
    total_month = daily_counts.sum()

    # Alokasi proporsional awal
    raw_alloc = (daily_counts / total_month * target_n).round().astype(int)

    # Terapkan floor minimum per hari (kalau hari itu punya tweet >= floor)
    alloc = raw_alloc.copy()
    for date, count in daily_counts.items():
        floor_n = min(MIN_PER_DAY_IN_SAMPLED_MONTH, count)
        if alloc[date] < floor_n:
            alloc[date] = floor_n
        if alloc[date] > count:
            alloc[date] = count

    # Koreksi supaya total mendekati target (kurangi dari hari dengan alokasi terbesar
    # jika kelebihan, tambah ke hari dengan slack jika kekurangan)
    diff = target_n - alloc.sum()
    sorted_days = alloc.sort_values(ascending=False).index.tolist()
    i = 0
    while diff != 0 and i < 10000:
        day = sorted_days[i % len(sorted_days)]
        cap = daily_counts[day]
        if diff > 0 and alloc[day] < cap:
            alloc[day] += 1
            diff -= 1
        elif diff < 0 and alloc[day] > MIN_PER_DAY_IN_SAMPLED_MONTH:
            alloc[day] -= 1
            diff += 1
        i += 1

    # Ambil sampel sesuai alokasi per hari
    sampled_parts = []
    for date, n in alloc.items():
        day_pool = month_df[month_df["date"] == date]
        n = min(n, len(day_pool))
        if n > 0:
            sampled_parts.append(day_pool.sample(n=n, random_state=rng))

    return pd.concat(sampled_parts, ignore_index=True) if sampled_parts else month_df.iloc[0:0]


def build_labeling_plan(df: pd.DataFrame):
    rng = np.random.RandomState(RANDOM_SEED)
    monthly = monthly_volume_summary(df)

    plan_rows = []
    selected_parts = []

    for _, row in monthly.iterrows():
        month, volume = row["year_month"], row["volume"]
        month_df = df[df["year_month"] == month]
        target_n = determine_sample_size(month, volume)

        if volume <= FULL_LABEL_THRESHOLD:
            method = "sensus_penuh"
            selected = month_df.copy()
        else:
            method = "stratified_by_day"
            selected = stratified_sample_by_day(month_df, target_n, rng)

        selected = selected.copy()
        selected["sampling_method"] = method
        selected_parts.append(selected)

        plan_rows.append({
            "year_month": month,
            "volume_total": volume,
            "target_dilabeli": len(selected),
            "persentase": round(len(selected) / volume * 100, 1),
            "metode": method,
        })

    plan_df = pd.DataFrame(plan_rows)
    selected_df = pd.concat(selected_parts, ignore_index=True)
    return plan_df, selected_df


# ============================================================
# MAIN
# ============================================================
def main():
    df = load_tweets(DB_PATH)
    plan_df, selected_df = build_labeling_plan(df)

    print("\n" + "=" * 70)
    print("RENCANA PELABELAN PER BULAN")
    print("=" * 70)
    print(plan_df.to_string(index=False))

    total_to_label = plan_df["target_dilabeli"].sum()
    total_volume = plan_df["volume_total"].sum()
    print(f"\nTotal tweet di seluruh periode : {total_volume}")
    print(f"Total yang perlu dilabeli manual: {total_to_label} ({total_to_label/total_volume*100:.1f}% dari keseluruhan)")

    # Estimasi waktu kasar (asumsi kecepatan rata2 100 tweet/jam, sesuaikan sendiri)
    est_hours = total_to_label / 100
    print(f"Estimasi waktu (asumsi 100 tweet/jam per orang): ~{est_hours:.1f} jam")
    print("(Sesuaikan asumsi kecepatan ini dengan kondisi tim Anda yang sebenarnya)")

    # Simpan output
    plan_df.to_csv(SUMMARY_CSV, index=False)
    selected_df[["id", "raw_content", "created_at", "dataset_id", "year_month", "sampling_method"]].to_csv(
        OUTPUT_CSV, index=False
    )
    print(f"\nRingkasan rencana disimpan ke: {SUMMARY_CSV}")
    print(f"Daftar tweet terpilih untuk dilabeli disimpan ke: {OUTPUT_CSV}")
    print("\nLangkah selanjutnya: impor file ini ke dashboard labeling Anda,")
    print("beri label 'expected' (negative/neutral/positive) untuk tiap baris,")
    print("lalu masukkan hasilnya ke tabel `datasets` seperti dataset 2021-2022 sebelumnya.")


if __name__ == "__main__":
    main()
