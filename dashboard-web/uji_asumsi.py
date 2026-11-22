import sqlite3
import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy import stats
import os

# Tentukan path database (sesuaikan jika berbeda)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/skripsi_bsi_v2.db'))

def run_statistical_tests():
    print("Mengambil data dari database...")
    conn = sqlite3.connect(DB_PATH)
    
    # Ambil nilai NSS
    query_sentiment = """
        SELECT strftime('%Y-%m', created_at) as periode,
               (CAST(SUM(CASE WHEN label = 'positive' THEN 1 ELSE 0 END) AS FLOAT) - 
                CAST(SUM(CASE WHEN label = 'negative' THEN 1 ELSE 0 END) AS FLOAT)) / 
                NULLIF(COUNT(*), 0) as nss
        FROM tweets 
        WHERE label IN ('positive', 'negative', 'neutral')
        GROUP BY periode
    """
    df_sent = pd.read_sql_query(query_sentiment, conn)
    
    # Ambil nilai DEA
    df_dea = pd.read_sql_query("SELECT periode, skor_dea FROM kinerja_bulanans", conn)
    conn.close()

    # Gabungkan data berdasarkan bulan
    df_merge = pd.merge(df_sent, df_dea, on='periode', how='inner')
    
    if df_merge.empty:
        print("Data kosong. Periksa path database.")
        return

    # Siapkan variabel X (Independen: NSS) dan Y (Dependen: DEA)
    X = df_merge['nss'].values
    Y = df_merge['skor_dea'].values
    
    # Tambahkan konstanta untuk model regresi (Syarat OLS statsmodels)
    X_sm = sm.add_constant(X)

    # 1. BUAT MODEL REGRESI & DAPATKAN RESIDUAL
    model = sm.OLS(Y, X_sm).fit()
    residuals = model.resid

    # 2. UJI NORMALITAS (Shapiro-Wilk)
    # Shapiro-Wilk lebih akurat dan disarankan untuk sampel kecil-menengah (N = 60)
    stat_sw, p_val_sw = stats.shapiro(residuals)

    # 3. UJI HOMOGENITAS / HETEROSKEDASTISITAS (Uji Glejser)
    # Regresikan nilai Absolut Residual terhadap X (NSS)
    abs_residuals = np.abs(residuals)
    model_glejser = sm.OLS(abs_residuals, X_sm).fit()
    p_val_glejser = model_glejser.pvalues[1] # Ambil p-value dari koefisien X (NSS)

    # CETAK HASIL UNTUK DRAFT BAB 4
    print("\n" + "="*50)
    print("HASIL UJI PERSYARATAN ANALISIS (BAB IV)")
    print("="*50)
    
    print("\n[A. UJI NORMALITAS (Shapiro-Wilk)]")
    print(f"Nilai Signifikansi (P-Value) : {p_val_sw:.4f}")
    if p_val_sw > 0.05:
        print("Kesimpulan: P-Value > 0.05. Residual BERDISTRIBUSI NORMAL (Syarat Terpenuhi).")
    else:
        print("Kesimpulan: P-Value < 0.05. Residual TIDAK NORMAL.")

    print("\n[B. UJI HOMOGENITAS / HETEROSKEDASTISITAS (Uji Glejser)]")
    print(f"Nilai Signifikansi (P-Value) : {p_val_glejser:.4f}")
    if p_val_glejser > 0.05:
        print("Kesimpulan: P-Value > 0.05. TIDAK TERJADI Heteroskedastisitas (Syarat Terpenuhi).")
    else:
        print("Kesimpulan: P-Value < 0.05. TERJADI Heteroskedastisitas.")
    print("="*50 + "\n")

if __name__ == '__main__':
    run_statistical_tests()