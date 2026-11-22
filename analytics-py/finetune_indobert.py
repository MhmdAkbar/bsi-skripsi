"""
================================================================================
FINE-TUNING INDOBERT UNTUK ANALISIS SENTIMEN BSI
================================================================================
Pipeline ini menggantikan pendekatan lexicon-override yang overfit dengan
fine-tuning IndoBERT yang sesungguhnya, dievaluasi secara jujur pada test set
yang TIDAK PERNAH dilihat selama training maupun pembuatan aturan apa pun.

CARA PAKAI DI GOOGLE COLAB:
1. Runtime > Change runtime type > pilih GPU (T4)
2. Upload file database SQLite Anda ke Colab (klik ikon folder di kiri,
   lalu drag-drop file .db / .sqlite Anda), atau mount Google Drive.
3. Sesuaikan DB_PATH di bawah ini ke lokasi file Anda.
4. Jalankan: !pip install -q transformers datasets scikit-learn torch accelerate
5. Jalankan seluruh skrip ini (atau copy-paste per blok ke cell Colab).

STRUKTUR DATA YANG DIASUMSIKAN:
Tabel `datasets` dengan kolom:
  - nama_dataset   (TEXT)
  - deskripsi      (TEXT)
  - data           (TEXT, berisi JSON array of objects dengan field:
                     "id", "text", "expected", "created_at")

Skrip ini akan MENGGABUNGKAN semua baris dari semua dataset di tabel ini,
melakukan dedup berdasarkan "id" tweet (supaya satu tweet yang sama tidak
muncul di train DAN test sekaligus -- ini penting untuk validitas evaluasi),
lalu melakukan stratified split 70/15/15.
================================================================================
"""

import json
import sqlite3
import re
import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================
# KONFIGURASI -- SESUAIKAN BAGIAN INI
# ============================================================
DB_PATH = "bsi_sentiment.db"          # path ke file SQLite Anda
TABLE_NAME = "datasets"
JSON_COLUMN = "data"
OUTPUT_DIR = "indobert_bsi_sentiment"  # folder untuk menyimpan model hasil fine-tune
MODEL_NAME = "indobenchmark/indobert-base-p1"  # bisa ganti ke -p2 jika mau coba

RANDOM_SEED = 42
TEST_SIZE = 0.15
VAL_SIZE = 0.15   # diambil dari sisa setelah test, lihat perhitungan di bawah
MAX_LENGTH = 128
BATCH_SIZE = 16
NUM_EPOCHS = 4
LEARNING_RATE = 2e-5

LABEL2ID = {"negative": 0, "neutral": 1, "positive": 2}
ID2LABEL = {v: k for k, v in LABEL2ID.items()}


# ============================================================
# 1. LOAD DATA DARI SQLITE
# ============================================================
def load_all_data_from_sqlite(db_path: str) -> pd.DataFrame:
    """
    Membaca semua baris dari tabel `datasets`, mem-parse kolom JSON `data`,
    menggabungkan jadi satu DataFrame panjang (long format): satu baris = satu tweet.
    """
    conn = sqlite3.connect(db_path)
    meta = pd.read_sql_query(f"SELECT nama_dataset, deskripsi, {JSON_COLUMN} FROM {TABLE_NAME}", conn)
    conn.close()

    print(f"Ditemukan {len(meta)} baris dataset di tabel '{TABLE_NAME}':")
    for _, row in meta.iterrows():
        try:
            n_items = len(json.loads(row[JSON_COLUMN]))
        except Exception:
            n_items = "GAGAL PARSE"
        print(f"  - {row['nama_dataset']}: {n_items} tweet | {row['deskripsi']}")

    all_rows = []
    for _, row in meta.iterrows():
        try:
            items = json.loads(row[JSON_COLUMN])
        except json.JSONDecodeError as e:
            print(f"  [SKIP] Gagal parse JSON untuk dataset '{row['nama_dataset']}': {e}")
            continue
        for item in items:
            all_rows.append({
                "tweet_id": item.get("id"),
                "text": item.get("text"),
                "expected": item.get("expected"),
                "created_at": item.get("created_at"),
                "source_dataset": row["nama_dataset"],
            })

    df = pd.DataFrame(all_rows)
    print(f"\nTotal baris tweet sebelum cleaning: {len(df)}")
    return df


# ============================================================
# 2. CLEANING & VALIDASI LABEL
# ============================================================
def clean_dataset(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    # Normalisasi label
    df["expected"] = df["expected"].astype(str).str.strip().str.lower()

    # Buang baris dengan teks kosong atau label tidak dikenal
    valid_labels = set(LABEL2ID.keys())
    df = df[df["text"].notna() & (df["text"].str.strip() != "")]
    invalid_label_mask = ~df["expected"].isin(valid_labels)
    if invalid_label_mask.any():
        bad_labels = df.loc[invalid_label_mask, "expected"].unique()
        print(f"[WARNING] Ditemukan label tidak dikenal, baris ini akan dibuang: {bad_labels}")
        df = df[~invalid_label_mask]

    # Dedup berdasarkan tweet_id (kalau ada id sama persis -- tweet betul2 sama)
    n_dup_id = df.duplicated(subset=["tweet_id"]).sum()
    if n_dup_id > 0:
        print(f"[INFO] Membuang {n_dup_id} baris duplikat berdasarkan tweet_id yang sama persis.")
        df = df.drop_duplicates(subset=["tweet_id"], keep="first")

    # Dedup berdasarkan teks yang SAMA PERSIS (bisa beda id tapi retweet/repost identik)
    n_dup_text = df.duplicated(subset=["text"]).sum()
    if n_dup_text > 0:
        print(f"[INFO] Membuang {n_dup_text} baris duplikat berdasarkan teks yang identik persis.")
        df = df.drop_duplicates(subset=["text"], keep="first")

    df = df.reset_index(drop=True)
    print(f"Total baris setelah cleaning: {len(df)} (dibuang {before - len(df)} baris)")
    print("\nDistribusi label setelah cleaning:")
    print(df["expected"].value_counts())
    print("\nProporsi label:")
    print((df["expected"].value_counts(normalize=True) * 100).round(2).astype(str) + "%")

    return df


def basic_text_normalize(text: str) -> str:
    """
    Normalisasi ringan -- TIDAK menghapus informasi sentimen (mis. tidak
    menghapus emoji/tanda seru karena itu bisa membawa sinyal sentimen).
    Hanya membersihkan noise teknis seperti URL dan whitespace berlebih.
    """
    text = re.sub(r"https?://\S+", "", text)         # buang URL
    text = re.sub(r"\s+", " ", text).strip()           # rapikan whitespace
    return text


# ============================================================
# 3. STRATIFIED SPLIT (TRAIN / VAL / TEST)
# ============================================================
def stratified_split(df: pd.DataFrame):
    from sklearn.model_selection import train_test_split

    df["text"] = df["text"].apply(basic_text_normalize)
    df["label_id"] = df["expected"].map(LABEL2ID)

    # Split 1: pisahkan test set (15%) -- ini akan DIKUNCI, tidak boleh
    # disentuh lagi sampai evaluasi akhir.
    train_val_df, test_df = train_test_split(
        df, test_size=TEST_SIZE, stratify=df["label_id"], random_state=RANDOM_SEED
    )

    # Split 2: dari sisa, pisahkan validation set (proporsional, ~15% dari total awal)
    val_relative_size = VAL_SIZE / (1 - TEST_SIZE)
    train_df, val_df = train_test_split(
        train_val_df, test_size=val_relative_size,
        stratify=train_val_df["label_id"], random_state=RANDOM_SEED
    )

    print(f"\nUkuran split:")
    print(f"  Train      : {len(train_df)} ({len(train_df)/len(df)*100:.1f}%)")
    print(f"  Validation : {len(val_df)} ({len(val_df)/len(df)*100:.1f}%)")
    print(f"  Test       : {len(test_df)} ({len(test_df)/len(df)*100:.1f}%)  <-- DIKUNCI, jangan disentuh sebelum evaluasi final")

    for name, split_df in [("Train", train_df), ("Validation", val_df), ("Test", test_df)]:
        print(f"\nDistribusi label di {name}:")
        print(split_df["expected"].value_counts(normalize=True).round(3))

    return train_df.reset_index(drop=True), val_df.reset_index(drop=True), test_df.reset_index(drop=True)


# ============================================================
# 4. TOKENIZATION & DATASET HUGGINGFACE
# ============================================================
def build_hf_datasets(train_df, val_df, test_df, tokenizer):
    from datasets import Dataset

    def tokenize_fn(batch):
        return tokenizer(
            batch["text"],
            truncation=True,
            max_length=MAX_LENGTH,
            padding="max_length",
        )

    def to_hf(df):
        ds = Dataset.from_pandas(df[["text", "label_id"]].rename(columns={"label_id": "labels"}))
        ds = ds.map(tokenize_fn, batched=True)
        ds = ds.remove_columns(["text"])
        return ds

    return to_hf(train_df), to_hf(val_df), to_hf(test_df)


# ============================================================
# 5. METRIK EVALUASI
# ============================================================
def compute_metrics(eval_pred):
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "accuracy": accuracy_score(labels, preds),
        "f1_macro": f1_score(labels, preds, average="macro"),
        "precision_macro": precision_score(labels, preds, average="macro", zero_division=0),
        "recall_macro": recall_score(labels, preds, average="macro", zero_division=0),
    }


# ============================================================
# 6. TRAINING
# ============================================================
def train_model(train_ds, val_ds, tokenizer):
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        TrainingArguments,
        Trainer,
        EarlyStoppingCallback,
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=3,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    args = TrainingArguments(
        output_dir=f"./{OUTPUT_DIR}_checkpoints",
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=LEARNING_RATE,
        per_device_train_batch_size=BATCH_SIZE,
        per_device_eval_batch_size=BATCH_SIZE,
        num_train_epochs=NUM_EPOCHS,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        logging_steps=20,
        save_total_limit=2,
        report_to="none",
        fp16=torch.cuda.is_available(),
        seed=RANDOM_SEED,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    trainer.train()
    return trainer


# ============================================================
# 7. EVALUASI FINAL DI TEST SET (HANYA SEKALI, DI AKHIR)
# ============================================================
def evaluate_on_test(trainer, test_ds, test_df):
    from sklearn.metrics import classification_report, confusion_matrix
    import matplotlib.pyplot as plt
    import seaborn as sns

    print("\n" + "=" * 60)
    print("EVALUASI FINAL PADA TEST SET (tidak pernah dilihat sebelumnya)")
    print("=" * 60)

    preds_output = trainer.predict(test_ds)
    y_true = preds_output.label_ids
    y_pred = np.argmax(preds_output.predictions, axis=-1)

    target_names = [ID2LABEL[i] for i in range(3)]
    report = classification_report(y_true, y_pred, target_names=target_names, digits=4)
    print(report)

    # Simpan classification report ke file teks untuk dilampirkan di skripsi
    with open(f"{OUTPUT_DIR}_classification_report.txt", "w") as f:
        f.write(report)

    # Confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=target_names, yticklabels=target_names)
    plt.xlabel("Prediksi")
    plt.ylabel("Label Sebenarnya")
    plt.title("Confusion Matrix - Test Set (IndoBERT Fine-tuned)")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}_confusion_matrix.png", dpi=150)
    plt.show()
    print(f"\nConfusion matrix disimpan ke: {OUTPUT_DIR}_confusion_matrix.png")
    print(f"Classification report disimpan ke: {OUTPUT_DIR}_classification_report.txt")

    # Simpan juga prediksi per-baris untuk audit manual / lampiran skripsi
    result_df = test_df.copy()
    result_df["predicted"] = [ID2LABEL[p] for p in y_pred]
    result_df["correct"] = result_df["expected"] == result_df["predicted"]
    result_df.to_csv(f"{OUTPUT_DIR}_test_predictions.csv", index=False)
    print(f"Detail prediksi test set disimpan ke: {OUTPUT_DIR}_test_predictions.csv")

    return result_df


# ============================================================
# MAIN
# ============================================================
def main():
    from transformers import AutoTokenizer

    print("STEP 1: Memuat data dari SQLite...")
    df = load_all_data_from_sqlite(DB_PATH)

    print("\nSTEP 2: Membersihkan data...")
    df = clean_dataset(df)

    print("\nSTEP 3: Membagi data (stratified train/val/test)...")
    train_df, val_df, test_df = stratified_split(df)

    print(f"\nSTEP 4: Memuat tokenizer & model dasar '{MODEL_NAME}'...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    print("\nSTEP 5: Tokenisasi data...")
    train_ds, val_ds, test_ds = build_hf_datasets(train_df, val_df, test_df, tokenizer)

    print("\nSTEP 6: Fine-tuning IndoBERT...")
    trainer = train_model(train_ds, val_ds, tokenizer)

    print("\nSTEP 7: Menyimpan model hasil fine-tuning...")
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Model tersimpan di folder: {OUTPUT_DIR}")

    print("\nSTEP 8: Evaluasi final di test set...")
    evaluate_on_test(trainer, test_ds, test_df)

    print("\nSELESAI. Gunakan model di folder "
          f"'{OUTPUT_DIR}' untuk prediksi data baru (lihat predict_new_data.py).")


if __name__ == "__main__":
    main()
