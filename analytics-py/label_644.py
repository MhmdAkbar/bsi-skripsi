import sqlite3
from pathlib import Path
from transformers import pipeline
from collections import Counter

# Paths are resolved relative to the repository root, so this script works
# from any fresh clone of the repo (no machine-specific paths).
BASE = Path(__file__).resolve().parent.parent
MODEL = str(BASE / 'indobert_bsi_sentiment')
DB = str(BASE / 'data' / 'skripsi_bsi_v2.db')

clf = pipeline('sentiment-analysis', model=MODEL, tokenizer=MODEL, device=-1, truncation=True, max_length=512)
print('model loaded OK', flush=True)

conn = sqlite3.connect(DB)
rows = conn.execute("SELECT id, raw_content, created_at FROM tweets WHERE label = 'unlabeled' ORDER BY created_at").fetchall()
print(f'unlabeled tweets: {len(rows)}', flush=True)
texts = [str(r[1]).lower() for r in rows]
preds = clf(texts, batch_size=32)
updates = []
dist = Counter()
for (tid, _, _), p in zip(rows, preds):
    lab = p['label'].lower()
    dist[lab] += 1
    updates.append((lab, lab, float(p['score']), lab, tid))
conn.executemany("UPDATE tweets SET label=?, label_ai=?, score_ai=?, label_hybrid=? WHERE id=?", updates)
conn.commit()
print('distribution:', dict(dist), flush=True)
print('remaining unlabeled:', conn.execute("SELECT COUNT(*) FROM tweets WHERE label='unlabeled'").fetchone()[0])
print('label_ai NULL remaining:', conn.execute("SELECT COUNT(*) FROM tweets WHERE label_ai IS NULL").fetchone()[0])
print('total labeled:', conn.execute("SELECT COUNT(*) FROM tweets WHERE label IN ('positive','neutral','negative')").fetchone()[0])
conn.close()
print('DONE', flush=True)
