# F:\skripsi\bsi-skripsi\analytics-py\sentiment_analyzer.py

import sqlite3
import pandas as pd
from transformers import pipeline
from tqdm import tqdm
from config_sentiment import HARD_NEG_PATTERN, CS_KEYWORDS, CONFIDENCE_THRESHOLD

DB_PATH = '../data/skripsi_bsi_v2.db'
BATCH_SIZE = 128

def ensure_database_schema():
    """Ensure database schema includes AI label and confidence score columns."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("PRAGMA table_info(tweets)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'label_ai' not in columns:
        cursor.execute("ALTER TABLE tweets ADD COLUMN label_ai TEXT")
        
    if 'score_ai' not in columns:
        cursor.execute("ALTER TABLE tweets ADD COLUMN score_ai REAL")
        
    conn.commit()
    conn.close()

def run_sentiment_pipeline():
    """Execute AI inference, apply rule-based corrections, and store scores."""
    ensure_database_schema()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT id, cleaned_content, raw_content FROM tweets WHERE label = 'unlabeled' LIMIT 200000"
    df = pd.read_sql(query, conn)

    if df.empty:
        print("No unlabelled data found.")
        return

    print(f"Processing {len(df)} records with threshold {CONFIDENCE_THRESHOLD}...")

    analyzer = pipeline(
        "sentiment-analysis", 
        model="w11wo/indonesian-roberta-base-sentiment-classifier",
        device=-1
    )

    results = []
    
    for i in tqdm(range(0, len(df), BATCH_SIZE)):
        batch = df.iloc[i : i + BATCH_SIZE]
        texts = batch['cleaned_content'].astype(str).tolist()
        raw_texts = batch['raw_content'].astype(str).tolist()
        
        preds = analyzer(texts, truncation=True, max_length=128)
        
        for idx, pred in enumerate(preds):
            tweet_id = batch.iloc[idx]['id']
            content = raw_texts[idx].lower()
            
            raw_label = pred['label']
            ai_score = pred['score']
            
            ai_label = 'negative' if raw_label == 'LABEL_0' else ('neutral' if raw_label == 'LABEL_1' else 'positive')
            final_label = ai_label
            
            # Rule 1: Ambiguity filtering based on confidence score
            if ai_score < CONFIDENCE_THRESHOLD:
                final_label = 'neutral'
                
            # Rule 2: Hard negative structural override
            elif HARD_NEG_PATTERN.search(content):
                final_label = 'negative'
                
            # Rule 3: Downgrade operational inquiries misclassified as positive
            elif final_label == 'positive' and any(word in content for word in CS_KEYWORDS):
                final_label = 'neutral'
            
            results.append((final_label, ai_label, ai_score, tweet_id))
            
            if len(results) >= 500:
                cursor.executemany("UPDATE tweets SET label = ?, label_ai = ?, score_ai = ? WHERE id = ?", results)
                conn.commit()
                results = []

    if results:
        cursor.executemany("UPDATE tweets SET label = ?, label_ai = ?, score_ai = ? WHERE id = ?", results)
        conn.commit()

    conn.close()
    print("Pipeline execution completed successfully.")

if __name__ == "__main__":
    run_sentiment_pipeline()