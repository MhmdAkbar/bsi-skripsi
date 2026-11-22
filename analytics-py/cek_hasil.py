# analytics-py/cek_hasil.py
import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect('../data/skripsi_bsi.db')

# Execute query and load to dataframe for neat formatting
query = "SELECT id, content, label FROM tweets WHERE label IS NOT NULL LIMIT 50;"
df = pd.read_sql(query, conn)

# Display results
print("\n--- HASIL 10 DATA PERTAMA ---")
print(df.to_string(index=False))
print("-----------------------------\n")

conn.close()