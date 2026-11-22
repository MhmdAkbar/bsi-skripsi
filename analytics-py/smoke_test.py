import sqlite3, random
from pathlib import Path
from transformers import pipeline

# Paths are resolved relative to the repository root, so this script works
# from any fresh clone of the repo (no machine-specific paths).
BASE = Path(__file__).resolve().parent.parent
MODEL = str(BASE / 'indobert_bsi_sentiment')
DB = str(BASE / 'data' / 'skripsi_bsi_v2.db')

clf = pipeline('sentiment-analysis', model=MODEL, tokenizer=MODEL, device=-1, truncation=True, max_length=512)
print('model loaded OK')

conn = sqlite3.connect(DB)
rows = conn.execute("SELECT raw_content, label FROM tweets WHERE label IN ('positive','neutral','negative')").fetchall()
random.seed(42)
sample = random.sample(rows, 90)
texts = [r[0].lower() for r in sample]
gold = [r[1] for r in sample]
preds = clf(texts, batch_size=32)
agree = sum(1 for p, g in zip(preds, gold) if p['label'].lower() == g)
print(f'agreement with stored label: {agree}/90 = {100*agree/90:.1f}%')
from collections import Counter
print('pred distribution:', Counter(p['label'].lower() for p in preds))
print('gold distribution:', Counter(gold))
# confusion
conf = Counter((g, p['label'].lower()) for g, p in zip(gold, preds))
for k in sorted(conf): print(f'  gold={k[0]:8} pred={k[1]:8} n={conf[k]}')
scores = [p['score'] for p in preds]
print(f'confidence: min={min(scores):.3f} mean={sum(scores)/len(scores):.3f} max={max(scores):.3f}')
low = sum(1 for s in scores if s < 0.65)
print(f'below 0.65 confidence: {low}/90')
conn.close()
