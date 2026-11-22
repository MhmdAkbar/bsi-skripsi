import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import statsmodels.api as sm
import json

# Pastikan path ini sesuai dengan lokasi database Anda
DB_PATH = '../data/skripsi_bsi_v2.db' 

def compute_ols_stats(X, y):
    X_const = sm.add_constant(X)
    model = sm.OLS(y, X_const).fit()
    return {
        "koefisien_slope": round(model.params[1], 4),
        "koefisien_intercept": round(model.params[0], 4),
        "p_value_slope": round(model.pvalues[1], 4),
        "p_value_model_f": round(model.f_pvalue, 4),
        "signifikan_5persen": bool(model.pvalues[1] < 0.05),
    }

def get_fast_stats():
    conn = sqlite3.connect(DB_PATH)
    
    # Ambil Sentimen
    query_sent = """
        SELECT strftime('%Y-%m', created_at) as periode,
               (CAST(SUM(CASE WHEN label = 'positive' THEN 1 ELSE 0 END) AS FLOAT) - 
                CAST(SUM(CASE WHEN label = 'negative' THEN 1 ELSE 0 END) AS FLOAT)) / 
                NULLIF(COUNT(*), 0) as nss
        FROM tweets WHERE label IN ('positive', 'negative', 'neutral') GROUP BY periode
    """
    df_sent = pd.read_sql_query(query_sent, conn)
    
    # Ambil DEA
    df_dea = pd.read_sql_query("SELECT periode, skor_dea FROM kinerja_bulanans", conn)
    conn.close()

    # Gabungkan Data
    df_merge = pd.merge(df_sent, df_dea, on='periode', how='inner')
    df_merge['tahun'] = df_merge['periode'].str[:4]
    
    stats_result = {"KESELURUHAN (2021-2025)": {}, "TAHUNAN": {}}
    
    # 1. Hitung Keseluruhan
    X_all = df_merge[['nss']].values
    y_all = df_merge['skor_dea'].values
    r2_all = r2_score(y_all, LinearRegression().fit(X_all, y_all).predict(X_all))
    stats_result["KESELURUHAN (2021-2025)"] = {"R-Squared": round(r2_all, 4), **compute_ols_stats(df_merge['nss'], y_all)}

    # 2. Hitung Tahunan
    for year in sorted(df_merge['tahun'].unique()):
        df_year = df_merge[df_merge['tahun'] == year]
        if len(df_year) > 2:
            X_yr = df_year[['nss']].values
            y_yr = df_year['skor_dea'].values
            r2_yr = r2_score(y_yr, LinearRegression().fit(X_yr, y_yr).predict(X_yr))
            stats_result["TAHUNAN"][year] = {"R-Squared": round(r2_yr, 4), **compute_ols_stats(df_year['nss'], y_yr)}

    # Cetak hasil dengan rapi ke layar
    print(json.dumps(stats_result, indent=4))

if __name__ == "__main__":
    print("Menghitung statistik murni (tanpa render grafik)...")
    get_fast_stats()