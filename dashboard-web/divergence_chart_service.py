import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os

# Event tracker historis - sama seperti yang dipakai di endpoint /api/events server2.py
EVENTS = [
    ("2021-02", "Resmi Berdiri", "positif"),
    ("2021-11", "Migrasi Sistem Sukses", "positif"),
    ("2022-02", "Gangguan BSI Mobile", "negatif"),
    ("2022-03", "Kinerja Gemilang Q1", "positif"),
    ("2022-10", "Isu Kelalaian Agunan", "negatif"),
    ("2023-05", "Ransomware LockBit", "negatif"),
    ("2023-06", "Perombakan Manajemen", "campuran"),
    ("2023-08", "Ekspansi ke Dubai", "positif"),
    ("2024-02", "Top 10 Global Islamic Bank", "positif"),
    ("2024-06", "Penarikan Dana Muhammadiyah", "negatif"),
    ("2024-11", "Peluncuran SuperApp BYOND", "positif"),
    ("2025-01", "Migrasi Paksa & Gangguan Sistem BYOND", "negatif"),
    ("2025-02", "Era Bank Emas", "positif"),
]
WARNA_POLARITAS = {"positif": "#10b981", "negatif": "#f43f5e", "campuran": "#f59e0b"}


def generate_dual_axis_chart(conn, static_dir):
    """
    Menghasilkan grafik dual-axis (twin-axis) untuk memvisualisasikan
    Divergensi Kinerja BSI, TANPA mengubah/menormalisasi nilai asli:
      - Sumbu kiri : Net Sentiment Score (NSS), rentang asli -1 s/d 1
      - Sumbu kanan: Skor Efisiensi DEA, rentang asli 0 s/d 1

    Tidak ada rescaling/normalisasi apa pun pada kedua data. Divergensi
    ditunjukkan secara visual: ketika garis NSS anjlok tapi garis DEA
    tetap datar/naik, itu sudah menggambarkan divergensi kinerja.

    Return: dict berisi path file .png dan ringkasan statistik deskriptif
    (bukan uji hipotesis - itu tetap ditangani oleh regression_service.py).
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

    df_merge = pd.merge(df_sent, df_dea, on='periode', how='inner')
    df_merge = df_merge.sort_values('periode')

    result = {"chart": None, "highlight_gap_bulan": None}
    if df_merge.empty:
        return result

    # Konversi periode (YYYY-MM) ke datetime agar sumbu-X rapi & bisa diformat
    df_merge['periode_dt'] = pd.to_datetime(df_merge['periode'], format='%Y-%m')

    # ========================================================
    # GRAFIK DUAL-AXIS: NSS (kiri, -1..1) vs Skor DEA (kanan, 0..1)
    # ========================================================
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()

    # --- Sumbu kiri: Sentimen ---
    line1, = ax1.plot(df_merge['periode_dt'], df_merge['nss'],
                       color='#E63946', linewidth=2, marker='o', markersize=3,
                       label='Net Sentiment Score (NSS)')
    ax1.set_ylabel('Net Sentiment Score (skala asli: -1 s/d 1)', color='#E63946', fontweight='bold')
    ax1.set_ylim(-1.1, 1.1)
    ax1.tick_params(axis='y', labelcolor='#E63946')
    ax1.axhline(0, color='#E63946', linewidth=0.6, linestyle=':', alpha=0.5)

    # --- Sumbu kanan: Efisiensi DEA ---
    line2, = ax2.plot(df_merge['periode_dt'], df_merge['skor_dea'],
                       color='#00A39D', linewidth=2, marker='s', markersize=3,
                       label='Skor Efisiensi DEA')
    ax2.set_ylabel('Skor Efisiensi DEA (skala asli: 0 s/d 1)', color='#00A39D', fontweight='bold')
    ax2.set_ylim(0, 1.1)
    ax2.tick_params(axis='y', labelcolor='#00A39D')

    # ========================================================
    # Anotasi 12 Peristiwa Historis (Event Tracker)
    # Garis vertikal tipis berwarna sesuai polaritas peristiwa,
    # dengan nomor urut di atas chart (keterangan lengkap ada di
    # tabel kronologi peristiwa - Tabel 4.3 - yang sudah ada di Bab IV)
    # ========================================================
    for idx, (periode_event, judul_event, polaritas) in enumerate(EVENTS, start=1):
        tanggal_event = pd.to_datetime(periode_event, format='%Y-%m')
        warna = WARNA_POLARITAS.get(polaritas, '#6b7280')

        ax1.axvline(tanggal_event, color=warna, linestyle='--', linewidth=1, alpha=0.55, zorder=1)
        ax1.annotate(
            str(idx),
            xy=(tanggal_event, 1.05), xycoords=('data', 'axes fraction'),
            ha='center', va='center', fontsize=8, fontweight='bold', color='white',
            bbox=dict(boxstyle='circle,pad=0.25', facecolor=warna, edgecolor='none')
        )

    # Legenda kecil untuk kode warna polaritas peristiwa
    from matplotlib.lines import Line2D
    legenda_polaritas = [
        Line2D([0], [0], color=WARNA_POLARITAS['positif'], lw=2, linestyle='--', label='Peristiwa Positif'),
        Line2D([0], [0], color=WARNA_POLARITAS['negatif'], lw=2, linestyle='--', label='Peristiwa Negatif'),
        Line2D([0], [0], color=WARNA_POLARITAS['campuran'], lw=2, linestyle='--', label='Peristiwa Campuran'),
    ]

    # --- Format sumbu-X (bulan-tahun) ---
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b-%Y'))
    fig.autofmt_xdate(rotation=45)

    ax1.set_title('Visualisasi Divergensi Kinerja BSI: NSS vs Skor DEA (2021-2025)\n'
                   'Kedua sumbu ditampilkan dalam skala aslinya masing-masing, tanpa normalisasi',
                   fontsize=11, fontweight='bold', pad=28)
    ax1.grid(True, linestyle='--', alpha=0.3)

    # Legenda gabungan: dua garis data + tiga kode warna polaritas peristiwa
    ax1.legend(handles=[line1, line2] + legenda_polaritas, loc='lower left', framealpha=0.9, ncol=1, fontsize=8)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    chart_path = os.path.join(static_dir, 'divergensi_dual_axis.png')
    plt.savefig(chart_path, dpi=150)
    plt.close()

    # ========================================================
    # Ringkasan deskriptif (bukan uji hipotesis) untuk narasi Bab IV:
    # bulan dengan jarak paling ekstrem antara "sentimen sangat negatif"
    # dan "DEA tetap tinggi" -> bukti visual divergensi paling tajam
    # ========================================================
    df_merge['nss_terbalik'] = -df_merge['nss']  # makin negatif sentimen -> makin besar nilainya
    df_merge['indikasi_divergensi'] = df_merge['nss_terbalik'] * df_merge['skor_dea']
    baris_puncak = df_merge.loc[df_merge['indikasi_divergensi'].idxmax()]

    result['chart'] = 'divergensi_dual_axis.png'
    result['highlight_gap_bulan'] = {
        "periode": baris_puncak['periode'],
        "nss": round(float(baris_puncak['nss']), 4),
        "skor_dea": round(float(baris_puncak['skor_dea']), 4)
    }

    # ========================================================
    # Statistik deskriptif volatilitas: dihitung TERPISAH per
    # variabel di skala aslinya masing-masing (tidak dicampur/
    # dinormalisasi). Coefficient of Variation (CV = SD/mean)
    # memungkinkan perbandingan volatilitas relatif meski unit beda.
    # ========================================================
    nss_mean, nss_sd = df_merge['nss'].mean(), df_merge['nss'].std()
    dea_mean, dea_sd = df_merge['skor_dea'].mean(), df_merge['skor_dea'].std()

    # CATATAN: Coefficient of Variation (SD/mean) TIDAK dipakai untuk NSS karena
    # rata-rata NSS mendekati nol, sehingga CV bisa meledak jadi ratusan persen
    # dan menyesatkan (kelemahan matematis CV yang dikenal luas dalam statistik).
    # Sebagai gantinya, dipakai "Rasio Volatilitas terhadap Rentang Teoritis":
    # SD dibandingkan terhadap rentang desain masing-masing variabel
    # (NSS: -1 s/d 1 -> rentang 2; DEA: 0 s/d 1 -> rentang 1).
    # Ini tetap adil karena tiap variabel dibandingkan ke skalanya sendiri,
    # bukan skala campuran/dinormalisasi silang.
    NSS_RENTANG_TEORITIS = 2.0   # dari -1 sampai 1
    DEA_RENTANG_TEORITIS = 1.0  # dari 0 sampai 1

    nss_volatilitas_persen = (nss_sd / NSS_RENTANG_TEORITIS) * 100
    dea_volatilitas_persen = (dea_sd / DEA_RENTANG_TEORITIS) * 100

    # Korelasi Pearson keseluruhan (informasi tambahan, konsisten dengan R² di regression_service.py)
    korelasi_pearson = df_merge['nss'].corr(df_merge['skor_dea'])

    result['statistik_volatilitas'] = {
        "nss": {
            "rata_rata": round(float(nss_mean), 4),
            "std_dev": round(float(nss_sd), 4),
            "volatilitas_persen_dari_rentang_teoritis": round(float(nss_volatilitas_persen), 2),
            "min": round(float(df_merge['nss'].min()), 4),
            "max": round(float(df_merge['nss'].max()), 4),
        },
        "skor_dea": {
            "rata_rata": round(float(dea_mean), 4),
            "std_dev": round(float(dea_sd), 4),
            "volatilitas_persen_dari_rentang_teoritis": round(float(dea_volatilitas_persen), 2),
            "min": round(float(df_merge['skor_dea'].min()), 4),
            "max": round(float(df_merge['skor_dea'].max()), 4),
        },
        "korelasi_pearson_r": round(float(korelasi_pearson), 4)
    }

    # Daftar event bernomor (cocok dengan nomor lingkaran di chart) untuk dijadikan
    # keterangan/caption di bawah Gambar Bab IV
    result['daftar_event_bernomor'] = [
        {"no": idx, "periode": p, "judul": j, "polaritas": pol}
        for idx, (p, j, pol) in enumerate(EVENTS, start=1)
    ]

    return result