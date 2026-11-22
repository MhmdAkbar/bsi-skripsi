"""
================================================================================
PREDIKSI DATASET BARU MEMAKAI MODEL HASIL FINE-TUNING
================================================================================
Pakai skrip ini setiap kali Anda punya dataset/bulan baru yang ingin diuji.
Tidak perlu menulis regex/aturan baru -- model sudah belajar pola umum dari
fine-tuning, bukan menghafal kalimat spesifik, sehingga seharusnya tetap
akurat di data baru yang belum pernah dilihat.

CARA PAKAI:
    python predict_new_data.py --dataset_name "nama_dataset_di_tabel"

Atau import fungsinya langsung kalau mau dipakai di notebook lain.
================================================================================
"""

import json
import sqlite3
import argparse
import pandas as pd
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

DB_PATH = "bsi_sentiment.db"
TABLE_NAME = "datasets"
JSON_COLUMN = "data"
MODEL_DIR = "indobert_bsi_sentiment"   # folder hasil fine-tuning sebelumnya
MAX_LENGTH = 128
BATCH_SIZE = 32


def load_one_dataset(db_path: str, nama_dataset: str) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    row = pd.read_sql_query(
        f"SELECT {JSON_COLUMN} FROM {TABLE_NAME} WHERE nama_dataset = ?",
        conn, params=(nama_dataset,)
    )
    conn.close()
    if row.empty:
        raise ValueError(f"Dataset '{nama_dataset}' tidak ditemukan di tabel {TABLE_NAME}.")
    items = json.loads(row.iloc[0][JSON_COLUMN])
    df = pd.DataFrame(items)
    return df


def predict_batch(texts, tokenizer, model, device):
    model.eval()
    all_preds, all_probs = [], []
    id2label = model.config.id2label

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        enc = tokenizer(batch, truncation=True, padding=True,
                         max_length=MAX_LENGTH, return_tensors="pt").to(device)
        with torch.no_grad():
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu().numpy()
            preds = np.argmax(probs, axis=-1)
        all_preds.extend([id2label[p] for p in preds])
        all_probs.extend(probs.max(axis=-1).tolist())

    return all_preds, all_probs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name", required=True,
                         help="Nilai kolom nama_dataset di tabel datasets")
    parser.add_argument("--output_csv", default=None,
                         help="Path output CSV (default: <dataset_name>_predicted.csv)")
    args = parser.parse_args()

    output_csv = args.output_csv or f"{args.dataset_name}_predicted.csv"

    print(f"Memuat dataset '{args.dataset_name}' dari SQLite...")
    df = load_one_dataset(DB_PATH, args.dataset_name)
    print(f"Jumlah tweet: {len(df)}")

    print(f"Memuat model dari '{MODEL_DIR}'...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR).to(device)

    print("Memprediksi...")
    preds, confidences = predict_batch(df["text"].tolist(), tokenizer, model, device)
    df["predicted_sentiment"] = preds
    df["confidence"] = confidences

    if "expected" in df.columns:
        df["correct"] = df["expected"].str.lower() == df["predicted_sentiment"]
        acc = df["correct"].mean()
        print(f"\nAkurasi pada dataset ini (jika ada label 'expected'): {acc*100:.2f}%")
        print(df.groupby("expected")["correct"].mean())

    df.to_csv(output_csv, index=False)
    print(f"\nHasil prediksi disimpan ke: {output_csv}")


if __name__ == "__main__":
    main()
