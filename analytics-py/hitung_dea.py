# analytics-py/hitung_dea.py
import pandas as pd
from sqlalchemy import create_engine, text
import pulp

print("Memulai komputasi DEA (VRS Output-Oriented)...")

# 1. Tarik data dari Database
engine = create_engine('sqlite:///../data/skripsi_bsi_v2.db')
df = pd.read_sql('SELECT * FROM kinerja_bulanans ORDER BY periode ASC', con=engine)

# Definisi Variabel
inputs = ['dpk_input', 'beban_personel_input', 'beban_operasional_input']
outputs = ['pembiayaan_output', 'pendapatan_output']

hasil_skor = []

# 2. Iterasi setiap bulan sebagai 1 DMU
for target_idx, target_row in df.iterrows():
    periode_target = target_row['periode']
    
    # Inisialisasi Problem LP: Karena Output-Oriented, kita memaksimalkan efisiensi (Phi)
    prob = pulp.LpProblem(f"DEA_{periode_target}", pulp.LpMaximize)
    
    # Variabel Keputusan: Bobot/Lambda untuk setiap DMU (bulan) >= 0
    lambdas = pulp.LpVariable.dicts("Lambda", df.index, lowBound=0)
    
    # Variabel Skalar Efisiensi (Phi)
    phi = pulp.LpVariable("Phi", lowBound=0)
    
    # Fungsi Objektif: Maksimalkan skor Phi
    prob += phi
    
    # --- KENDALA MATEMATIS (CONSTRAINTS) ---
    
    # 1. Kendala Input: Total input kombinasi <= Input target
    for inp in inputs:
        prob += pulp.lpSum([lambdas[i] * df.loc[i, inp] for i in df.index]) <= target_row[inp]
        
    # 2. Kendala Output: Total output kombinasi >= Output target * Phi
    for out in outputs:
        prob += pulp.lpSum([lambdas[i] * df.loc[i, out] for i in df.index]) >= phi * target_row[out]
        
    # 3. Kendala VRS (Variable Returns to Scale): Total bobot (Lambda) harus = 1
    prob += pulp.lpSum([lambdas[i] for i in df.index]) == 1
    
    # Eksekusi Solver (Sembunyikan log default solver)
    prob.solve(pulp.PULP_CBC_CMD(msg=False))
    
    # Dalam Output-Oriented DEA, skor efisiensi sejati adalah 1 / Phi
    # Skor 1.0 berarti efisien sempurna (berada di garis frontier)
    skor_efisiensi = 1.0 / pulp.value(phi)
    
    hasil_skor.append({'periode': periode_target, 'skor': skor_efisiensi})
    print(f"Bulan {periode_target}: Skor DEA = {skor_efisiensi:.4f}")

# 3. Simpan Hasil Kembali ke SQLite
print("\nMenyimpan skor efisiensi ke database...")
with engine.begin() as conn:
    for hasil in hasil_skor:
        conn.execute(
            text("UPDATE kinerja_bulanans SET skor_dea = :skor WHERE periode = :periode"),
            {"skor": hasil['skor'], "periode": hasil['periode']}
        )

print("SUKSES! Skor efisiensi teknis bulanan berhasil dihitung dan diperbarui di database.")