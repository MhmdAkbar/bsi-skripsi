import pandas as pd
import matplotlib.pyplot as plt
import os
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson

def compute_ols_stats(X, y):
    """
    Execute OLS regression using statsmodels to obtain significance tests.
    Returns a dictionary containing regression coefficients, p-values, and Durbin-Watson statistics.
    """
    # Append constant for the intercept term
    X_const = sm.add_constant(X)  
    model = sm.OLS(y, X_const).fit()
    
    # Calculate Durbin-Watson statistic for autocorrelation
    dw_stat = durbin_watson(model.resid)

    return {
        "koefisien_slope": round(model.params.iloc[1], 4),
        "koefisien_intercept": round(model.params.iloc[0], 4),
        "p_value_slope": round(model.pvalues.iloc[1], 4),
        "p_value_model_f": round(model.f_pvalue, 4),
        "signifikan_5persen": bool(model.pvalues.iloc[1] < 0.05),
        "durbin_watson": round(dw_stat, 4)
    }


def generate_linear_regression_chart(conn, static_dir):
    """
    Menghitung NSS dan DEA, melakukan regresi linear keseluruhan & tahunan,
    menyimpan 6 grafik (.png), dan mengembalikan data statistik R-Squared.
    """
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
    df_dea = pd.read_sql_query("SELECT periode, skor_dea FROM kinerja_bulanans", conn)
    
    # Merge data dan ekstrak tahun
    df_merge = pd.merge(df_sent, df_dea, on='periode', how='inner')
    df_merge['tahun'] = df_merge['periode'].str[:4]
    
    stats_result = {"overall": {}, "yearly": {}}
    if df_merge.empty:
        return stats_result

    # ========================================================
    # 1. REGRESI KESELURUHAN (60 BULAN)
    # ========================================================
    X_all = df_merge[['nss']].values
    y_all = df_merge['skor_dea'].values
    
    model_all = LinearRegression().fit(X_all, y_all)
    y_pred_all = model_all.predict(X_all)
    r2_all = r2_score(y_all, y_pred_all)
    ols_all = compute_ols_stats(df_merge['nss'], y_all)
    
    plt.figure(figsize=(7, 5))
    plt.scatter(X_all, y_all, color='#00A39D', label='Data Bulanan (2021-2025)', zorder=5)
    plt.plot(X_all, y_pred_all, color='#F37021', linewidth=2, label=f'Garis Regresi ($R^2$ = {r2_all:.3f})')
    plt.title('Divergensi Keseluruhan: Pengaruh NSS terhadap Efisiensi DEA', fontsize=12, fontweight='bold')
    plt.xlabel('Net Sentiment Score (NSS)')
    plt.ylabel('Skor Efisiensi DEA')
    plt.xlim(-1.1, 1.1)
    plt.ylim(0, 1.1)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend()
    plt.tight_layout()
    
    overall_path = os.path.join(static_dir, 'regresi_dinamis.png')
    plt.savefig(overall_path, dpi=150)
    plt.close()
    
    stats_result['overall'] = {"r2": round(r2_all, 4), **ols_all}

    # ========================================================
    # 2. REGRESI TAHUNAN (5 GRAFIK TERPISAH)
    # ========================================================
    years = sorted(df_merge['tahun'].unique())
    
    for year in years:
        df_year = df_merge[df_merge['tahun'] == year]
        
        if len(df_year) > 1: # Syarat regresi minimal butuh 2 titik data
            X_yr = df_year[['nss']].values
            y_yr = df_year['skor_dea'].values
            
            model_yr = LinearRegression().fit(X_yr, y_yr)
            y_pred_yr = model_yr.predict(X_yr)
            r2_yr = r2_score(y_yr, y_pred_yr)
            # n minimal 3 baris (12 bulan per tahun cukup, tapi p-value butuh > 2 titik
            # untuk punya derajat kebebasan; kalau cuma 2 titik, OLS akan sempurna & p-value tidak informatif)
            ols_yr = compute_ols_stats(df_year['nss'], y_yr) if len(df_year) > 2 else None
            
            plt.figure(figsize=(6, 4))
            plt.scatter(X_yr, y_yr, color='#00A39D', label=f'Data {year}', zorder=5)
            plt.plot(X_yr, y_pred_yr, color='#F37021', linewidth=2, label=f'Regresi ($R^2$ = {r2_yr:.3f})')
            plt.title(f'Divergensi Tahun {year}', fontsize=11, fontweight='bold')
            plt.xlabel('Net Sentiment Score (NSS)')
            plt.ylabel('Skor DEA')
            plt.xlim(-1.1, 1.1)
            plt.ylim(0, 1.1)
            plt.grid(True, linestyle='--', alpha=0.5)
            plt.legend()
            plt.tight_layout()
            
            yr_path = os.path.join(static_dir, f'regresi_{year}.png')
            plt.savefig(yr_path, dpi=150)
            plt.close()
            
            # Simpan agregat ke dictionary untuk dikirim ke laporan HTML
            stats_result['yearly'][year] = {
                "r2": round(r2_yr, 4),
                "rata_nss": round(df_year['nss'].mean(), 4),
                "rata_dea": round(df_year['skor_dea'].mean(), 4),
                **(ols_yr if ols_yr else {"catatan": "n terlalu kecil untuk uji signifikansi"})
            }
            
    print(stats_result)
    return stats_result