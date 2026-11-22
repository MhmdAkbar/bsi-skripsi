import sqlite3
import os
from transformers import pipeline
from sentiment_rules_2022 import refine_sentiment_2022

# Configure absolute paths to ensure correct directory resolution
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/skripsi_bsi_v2.db'))
LOCAL_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../indobert_bsi_sentiment'))

def map_sentiment_label(raw_label):
    """Standardize raw model output labels to lowercase string."""
    return raw_label.lower()

def run_mass_labeling():
    print("Membaca Model Lokal...")
    
    # Initialize the Hugging Face pipeline with automatic truncation enabled
    model = pipeline(
        "sentiment-analysis", 
        model=LOCAL_MODEL_PATH, 
        tokenizer=LOCAL_MODEL_PATH, 
        device=-1,
        truncation=True, 
        max_length=512
    )
    
    # Establish database connection
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Mencari data yang belum dilabeli...")
    
    # Retrieve all unassigned records from the database
    cursor.execute("SELECT id, raw_content FROM tweets WHERE label IS NULL")
    unlabeled_tweets = cursor.fetchall()
    
    total = len(unlabeled_tweets)
    print(f"Ditemukan {total} tweet yang harus dilabeli.")
    
    if total == 0:
        print("Semua data sudah dilabeli!")
        return

    BATCH_SIZE = 32
    updates = []
    
    # Process records in batches to optimize memory and execution time
    for i in range(0, total, BATCH_SIZE):
        batch = unlabeled_tweets[i:i + BATCH_SIZE]
        
        # Normalize text input for the model
        batch_texts = [str(t['raw_content']).lower() for t in batch]
        
        # Execute batch inference
        preds = model(batch_texts)
        
        for j, t in enumerate(batch):
            tweet_id = t['id']
            text = batch_texts[j]
            pred = preds[j]
            
            ai_label = map_sentiment_label(pred['label'])
            ai_score = float(pred['score'])
            
            # Apply heuristic rules over the base model predictions
            final_label, applied_rule = refine_sentiment_2022(text, ai_label, ai_score)
            
            # Prepare data tuple mapping: (label, label_ai, score_ai, label_hybrid, id)
            updates.append((final_label, ai_label, ai_score, final_label, tweet_id))
            
        print(f"Progress: {min(i + BATCH_SIZE, total)} / {total} data selesai diproses...")

    print("\nMenyimpan hasil ke database (Writing to SQLite)...")
    
    # Execute bulk update transaction
    cursor.executemany("""
        UPDATE tweets 
        SET label = ?, label_ai = ?, score_ai = ?, label_hybrid = ? 
        WHERE id = ?
    """, updates)
    
    conn.commit()
    conn.close()
    
    print("✅ BERHASIL! Seluruh database telah dilabeli dengan model baru.")

if __name__ == '__main__':
    run_mass_labeling()