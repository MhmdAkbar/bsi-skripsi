# Skripsi BSI — Divergensi Kinerja Pasca-Merger Bank Syariah Indonesia

Repositori kode sumber, data, dan dashboard untuk skripsi:

> **Divergensi Kinerja Pasca-Merger Bank Syariah Indonesia: Analisis Efisiensi Teknis Menggunakan Data Envelopment Analysis (DEA) dan Sentimen Publik Periode 2021–2025**
>
> Muhammad Akbar (NPM 211105040172), Program Studi Ekonomi Syariah,
> Fakultas Agama Islam, Universitas Ibn Khaldun Bogor.

Penelitian ini membandingkan dua sisi kinerja BSI setelah merger (1 Februari 2021):
efisiensi teknis yang diukur dengan DEA dari laporan keuangan bulanan, dan sentimen
publik yang diukur dari cuitan tentang BSI dengan model IndoBERT hasil fine-tuning.
Hasil akhirnya dituangkan dalam Bab IV dan Bab V skripsi.

## Ringkasan hasil utama

| Ukuran | Nilai |
|---|---|
| Cuitan yang dianalisis | 31.804 (Januari 2021 – Desember 2025), seluruhnya sudah berlabel |
| Label sentimen | positif 5.190, netral 6.256, negatif 20.358 |
| Skor DEA rata-rata per tahun | 2021: 0,8416; 2022: 0,8838; 2023: 0,9348; 2024: 0,9761; 2025: 0,9994 |
| NSS (Net Sentiment Score) rata-rata per tahun | 2021: −0,1006; 2022: +0,4536; 2023: −0,3044; 2024: −0,2551; 2025: −0,1026 |
| Gap rata-rata DEA–sentimen (60 bulan) | 0,459 |
| Korelasi NSS dengan skor DEA | −0,157 |
| Akurasi model sentimen (test set, 1.186 cuitan) | 82,63% (makro F1 82,84) |

Rumus yang dipakai (sesuai Bab III skripsi):

- `NSS = (jumlah positif − jumlah negatif) / total cuitan bulan itu`
- `Skor Sentimen = (NSS + 1) / 2`
- `Gap = |Skor DEA − Skor Sentimen|`

Temuan intinya: efisiensi teknis BSI naik secara konsisten selama 2021–2025,
sementara sentimen publik mayoritas negatif (39 dari 60 bulan bernilai NSS
negatif), kecuali tahun 2022 yang positif. Keduanya bergerak berlawanan arah
secara lemah (korelasi −0,157), sehingga kesimpulannya adalah divergensi, bukan
keselarasan, antara kinerja keuangan dan persepsi publik.

## Isi repositori

```
bsi-skripsi/
├── README.md                    <- file ini
├── analytics-py/                <- skrip analisis (Python)
├── dashboard-web/               <- dashboard Flask + laporan HTML
├── data/                        <- database SQLite + data mentah
├── indobert_bsi_sentiment/      <- model IndoBERT hasil fine-tuning
├── sampling/                    <- rencana sampling pelabelan manual
└── scraper-go/                  <- pengimpor data berbasis Go (alat bantu)
```

### `analytics-py/` — skrip analisis

| File | Kegunaan |
|---|---|
| `finetune_indobert.py` | Fine-tuning IndoBERT (dijalankan di Google Colab, GPU T4). Membaca data berlabel dari tabel `datasets`, deduplikasi berdasarkan id tweet, lalu stratified split 70/15/15. |
| `BSI_Sentiment_Finetuning.ipynb` | Notebook Colab yang sama dengan `finetune_indobert.py`, per cell. |
| `indobert_bsi_sentiment_classification_report.txt` | Laporan evaluasi model (precision/recall/F1 per kelas, akurasi 0,8263). |
| `label_644.py` | Melabeli cuitan yang masih `unlabeled` dengan model hasil fine-tuning. Saat ini tidak ada lagi cuitan tanpa label (0 dari 31.804). |
| `smoke_test.py` | Uji cepat model: mengambil 90 cuitan berlabel secara acak dan membandingkan prediksi model dengan label tersimpan. |
| `predict_new_data.py` | Memprediksi dataset baru dengan model hasil fine-tuning. Jalankan `python predict_new_data.py --help` untuk melihat opsinya. Perhatikan: `DB_PATH` bawaan di dalam file ini adalah `bsi_sentiment.db`, sesuaikan dulu dengan file Anda. |
| `sentiment_analyzer.py` | Pelabelan batch dengan model + aturan override (lihat `config_sentiment.py`). Harus dijalankan dari dalam folder `analytics-py/` karena mengimpor `config_sentiment`. |
| `config_sentiment.py` | Daftar kata kunci override (misalnya kata-kata gangguan layanan yang memaksa label negatif) beserta ambang keyakinan. |
| `hitung_dea.py` | Menghitung skor DEA (VRS output-oriented) dari tabel `kinerja_bulanans` memakai `pulp`. Butuh instalasi tambahan: `pip install pulp sqlalchemy`. |
| `hitung_skor_sentimen2.py` | Menghitung ulang NSS dan skor sentimen untuk seluruh 60 bulan di `kinerja_bulanans`. Inilah skrip yang dipakai pada perhitungan ulang final. |
| `hitung_skor_sentimen.py` | Versi lama dari skrip di atas (menunjuk database lama `skripsi_bsi.db`). |
| `clean_buzzers.py`, `fix_sentiment.py` | Pembersihan dan perbaikan label pada database. |
| `import_tweets.py`, `import_tweets_feb_2021.py`, `import_csv_tweets.py`, `import_data.py` | Mengimpor hasil scraping (JSON/CSV) dan data keuangan ke database SQLite. |
| `evaluate_accuracy.py`, `cek_hasil.py`, `update_db.py` | Utilitas evaluasi dan pengecekan database (menunjuk database lama `skripsi_bsi.db`). |

Sebagian skrip memakai path relatif `../data/...`, jadi jalankan dari dalam folder
`analytics-py/`. Pengecualiannya adalah `label_644.py` dan `smoke_test.py`, yang
menentukan path dari lokasi file skrip itu sendiri sehingga bisa dijalankan dari
mana saja.

### `dashboard-web/` — dashboard Flask

| File | Kegunaan |
|---|---|
| `server2.py` | Server utama. Memuat model saat start, membaca `data/skripsi_bsi_v2.db`, dan menyajikan dashboard di `http://127.0.0.1:5000`. |
| `requirements.txt` | Daftar dependensi Python yang dipin versinya (lihat bagian instalasi). |
| `index2.html` | Halaman utama dashboard. |
| `annotator.html` | Halaman pelabelan manual dan uji akurasi. |
| `accuracy_report.html` | Laporan akurasi yang dihasilkan dari menu "Uji Akurasi" di Annotator. |
| `laporan_bab4.html` | Laporan Bab IV yang bisa dibuka lewat menu "Export Bab IV" (`/export-bab4`). |
| `laporan_keseluruhan_sentimen.html`, `laporan_sentimen_akumulasi.html` | Laporan sentimen lengkap (file HTML statis). |
| `divergence_chart_service.py` | Membuat grafik dual-axis (DEA vs sentimen) beserta penanda peristiwa historis. |
| `regression_service.py` | Membuat grafik dan statistik regresi linear sederhana. |
| `sentiment_rules_2022.py` | Aturan sentimen khusus tahun 2022 (dipakai `auto_label_db.py`). |
| `auto_label_db.py` | Pelabelan otomatis seluruh isi database dengan model + aturan 2022. |
| `cek_statistik.py`, `uji_asumsi.py`, `uji_100_tweets.py`, `regresi_linear_sederhana.py` | Skrip pengecekan statistik dan pengujian tambahan. |
| `static/` | Aset statis dashboard (JavaScript dan gambar grafik yang sudah dihasilkan). |

Halaman dan endpoint yang tersedia setelah server berjalan:

- `/` — dashboard utama
- `/annotator` — pelabelan manual dan uji akurasi
- `/accuracy-report` — laporan akurasi (dibuat dulu lewat "Uji Akurasi" di Annotator)
- `/export-bab4` — laporan Bab IV
- `/api/tweet-stats`, `/api/data`, `/api/tweets`, `/api/word-freq`, `/api/stats`,
  `/api/events`, `/api/datasets`, `/api/test-analyzer`,
  `/api/generate-analysis-charts`, `/api/generate-divergence-chart`,
  `/api/run-accuracy`, `/api/run-accuracy-all`, `/api/accuracy-progress`

### `data/` — data

File kanonis yang dipakai dashboard dan seluruh skrip final adalah
**`skripsi_bsi_v2.db`** (sekitar 20 MB). Isinya:

| Tabel | Isi |
|---|---|
| `tweets` | 31.804 cuitan. Kolom: `id`, `raw_content`, `cleaned_content`, `username`, `display_name`, `created_at`, `lang`, `like_count`, `retweet_count`, `reply_count`, `label`, `label_ai`, `score_ai`, `label_hybrid`, `dataset_id`. |
| `kinerja_bulanans` | 60 baris (periode `2021-01` sampai `2025-12`). Kolom: `periode`, `dpk_input`, `beban_personel_input`, `beban_operasional_input`, `pembiayaan_output`, `pendapatan_output`, `skor_dea`, `skor_sentimen`. Nilai keuangan dalam jutaan rupiah. |
| `datasets` | Dataset berlabel yang dipakai untuk fine-tuning (berisi JSON array berisi `id`, `text`, `expected`, `created_at`). |

File lain di folder ini adalah bahan mentah atau arsip:

- `skripsi_bsi.db` dan `skripsi_bsi_v2 copy.db` — database versi lama/salinan. Jangan dipakai untuk perhitungan final.
- `tweets_bsi.csv`, `bsi_24k_tweets.csv` — ekspor mentah hasil scraping.
- `tweets_<bulan>_<tahun>.json` — hasil scraping per bulan.
- `data.zip` — arsip data.
- `data_keuangan_bsi.xlsx` — data keuangan sumber.

### `indobert_bsi_sentiment/` — model hasil fine-tuning

- `config.json` — konfigurasi model (`BertForSequenceClassification`, 3 label:
  `0 = negative`, `1 = neutral`, `2 = positive`).
- `model.safetensors` — bobot model, **498 MB, disimpan lewat Git LFS**
  (lihat peringatan penting di bagian instalasi).
- `tokenizer.json`, `tokenizer_config.json` — tokenizer IndoBERT.
- `training_args.bin` — argumen training yang tersimpan.

Model dasar: `indobenchmark/indobert-base-p1`. Konfigurasi fine-tuning:
stratified split 70/15/15 (seed 42), max length 128, batch 16, 4 epoch,
learning rate 2e-5, weight decay 0,01, early stopping patience 2,
model terbaik dipilih berdasarkan macro F1. Dijalankan di Google Colab (GPU T4).

Hasil evaluasi pada test set (1.186 cuitan):

| Kelas | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| negative | 0,8442 | 0,8155 | 0,8296 | 412 |
| neutral | 0,8073 | 0,8000 | 0,8036 | 445 |
| positive | 0,8300 | 0,8754 | 0,8521 | 329 |
| **akurasi** | | | **0,8263** | 1.186 |
| **macro avg** | 0,8271 | 0,8303 | 0,8284 | 1.186 |

### `sampling/` — rencana sampling pelabelan

- `sampling_plan.py` — membuat rencana sampling stratified per hari untuk
  pelabelan manual.
- `tweets_to_label.csv` — daftar tweet terpilih untuk dilabeli.
- `labeling_plan_summary.csv` — **ringkasan rencana lama, bukan angka final.**
  Angka final ada di Bab IV skripsi dan di tabel `kinerja_bulanans`.

### `scraper-go/` — pengimpor data (alat bantu, Go)

Modul Go `bsi-scraper` untuk mengimpor CSV hasil scraping (Apify) ke SQLite.
Hanya diperlukan bila ingin mengulang impor data dari nol; data hasil impor
sudah ada di `data/`. Membutuhkan Go 1.25 atau yang lebih baru, lalu
`go run ./cmd/scraper` dari dalam folder `scraper-go/`.

Perhatian: `cmd/scraper/main.go` masih berisi path Windows yang ditulis keras
untuk file CSV (`F:\skripsi\bsi-skripsi\data\tweets_feb_2021.csv`) dan DSN
yang menunjuk database lama (`../data/skripsi_bsi.db`). Sesuaikan kedua nilai
itu sebelum menjalankan.

## Prasyarat

- **Git** dan **Git LFS** (wajib, lihat peringatan di bawah).
- **Python 3.12 atau yang lebih baru.** Langkah-langkah di bawah ini diuji pada
  Python 3.12.3. Pada Windows, pasang Python dari
  <https://www.python.org/downloads/> dan centang "Add Python to PATH"
  saat instalasi.
- Ruang disk kosong sekitar 2 GB (repositori + virtual environment; instalasi
  PyTorch versi CUDA bisa menambah beberapa GB lagi, lihat catatan di bawah).
- RAM minimal 4 GB. **Tidak butuh GPU**: model dijalankan di CPU
  (`device=-1` di `server2.py`).
- Go 1.25+ hanya bila ingin menjalankan `scraper-go/`.
- Setelah setup selesai, **tidak butuh internet**: model dan data sudah
  tersimpan lokal. Internet hanya diperlukan saat clone, `git lfs pull`,
  dan instalasi dependensi.

### Peringatan penting: Git LFS

Bobot model (`indobert_bsi_sentiment/model.safetensors`, 498 MB) disimpan
dengan Git LFS. **Tanpa Git LFS, file yang ter-clone hanyalah pointer teks
sebesar 134 byte, dan dashboard akan gagal memuat model.** Karena itu:

1. Pasang Git LFS terlebih dahulu: <https://git-lfs.com>
   (Windows: installer di tautan itu; macOS: `brew install git-lfs`;
   Debian/Ubuntu: `sudo apt install git-lfs`).
2. Aktifkan sekali di mesin Anda: `git lfs install`.
3. Setelah clone, jalankan `git lfs pull` di dalam folder repositori.
4. Periksa hasilnya: `indobert_bsi_sentiment/model.safetensors` harus
   berukuran sekitar **497.798.148 byte** (kurang-lebih 498 MB). Kalau ukurannya
   masih 134 byte, berarti file tersebut masih pointer dan `git lfs pull`
   belum berhasil.

## Cara menjalankan dashboard

Langkah-langkah ini sudah diuji dari clone baru: server menyala di
`http://127.0.0.1:5000`, halaman utama terbuka (HTTP 200), dan
`/api/stats` mengembalikan angka yang sama dengan yang tertulis di skripsi
(akurasi 82,63; total data 31.804).

### 1. Clone repositori

```bash
git clone https://github.com/MhmdAkbar/bsi-skripsi.git
cd bsi-skripsi
```

### 2. Unduh bobot model lewat Git LFS

```bash
git lfs install
git lfs pull
```

Periksa ukuran file model (harus sekitar 498 MB, bukan 134 byte):

```powershell
# Windows (PowerShell)
(Get-Item indobert_bsi_sentiment\model.safetensors).Length
```

```bash
# Linux / macOS
ls -la indobert_bsi_sentiment/model.safetensors
```

### 3. Buat virtual environment

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

Kalau PowerShell menolak menjalankan `Activate.ps1` (kebijakan eksekusi),
pakai saja Python dari virtual environment secara langsung tanpa aktivasi,
seperti pada contoh langkah 4 dan 5 di bawah (`.venv\Scripts\python.exe ...`).

### 4. Instal dependensi

```powershell
# Windows (PowerShell)
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r dashboard-web\requirements.txt
```

```bash
# Linux / macOS
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r dashboard-web/requirements.txt
```

Isi `dashboard-web/requirements.txt` (versi sudah dipin):
Flask 3.1.3, flask-cors 6.0.2, matplotlib 3.11.2, numpy 2.5.5,
pandas 3.1.1, safetensors 0.8.0, scikit-learn 1.9.1, scipy 1.18.1,
statsmodels 0.15.0, torch 2.15.0, tqdm 4.70.1, transformers 5.23.0.

**Catatan untuk laptop tanpa GPU (disarankan):** perintah di atas menginstal
PyTorch versi CUDA yang berukuran beberapa GB, padahal dashboard ini hanya
memakai CPU. Supaya unduhan jauh lebih ringan, instal dulu PyTorch versi CPU,
baru kemudian requirements lainnya. Cara ini sudah diuji: pip tetap memakai
torch CPU tersebut dan tidak mengunduh ulang versi CUDA.

```powershell
# Windows (PowerShell)
.\.venv\Scripts\python.exe -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r dashboard-web\requirements.txt
```

```bash
# Linux / macOS
.venv/bin/python -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r dashboard-web/requirements.txt
```

### 5. Jalankan server

Dari folder repositori:

```powershell
# Windows (PowerShell)
.\.venv\Scripts\python.exe dashboard-web\server2.py
```

```bash
# Linux / macOS
.venv/bin/python dashboard-web/server2.py
```

Tunggu sampai muncul di terminal:

```
=== PRELOAD MODEL ===
--> Loading Fine-Tuned NLP Model (This may take a few seconds)...
===== MODEL INFO =====
Model : .../indobert_bsi_sentiment
Model Class : BertForSequenceClassification
Num Labels : 3
======================

=== MODEL READY ===
 * Running on http://127.0.0.1:5000
```

Pemuatan model pertama kali bisa memakan waktu 1–3 menit di laptop biasa,
itu normal. Setelah `MODEL READY`, buka **<http://127.0.0.1:5000>** di
browser. Server hanya melayani akses lokal (127.0.0.1), jadi dashboard tidak
terekspos ke jaringan. Untuk menghentikan server, tekan `Ctrl+C` di terminal
tempat server berjalan.

### 6. Periksa bahwa dashboard benar-benar bekerja

Setelah server menyala, cek tiga hal ini:

1. Halaman utama terbuka di <http://127.0.0.1:5000> dan menampilkan grafik
   serta angka ringkasan.
2. Buka <http://127.0.0.1:5000/api/stats> di browser. Jawaban yang benar:
   `{"accuracy":82.63,"f1_score":82.84,"precision":82.71,"recall":83.03,"total_data":31804}`.
3. Di halaman Annotator (`/annotator`), menu "Uji Akurasi" menghasilkan
   laporan yang bisa dibuka di `/accuracy-report`.

## Menjalankan ulang analisis

Semua perintah di bawah memakai virtual environment yang sama dengan
dashboard (langkah 3–4 di atas). Dependensi dasarnya sudah tercakup oleh
`dashboard-web/requirements.txt`, kecuali yang disebutkan secara eksplisit.

### Uji cepat model

```bash
python analytics-py/smoke_test.py
```

Mengambil 90 cuitan berlabel secara acak dan menampilkan persentase
kesepakatan prediksi model dengan label tersimpan. Bisa dijalankan dari
folder mana saja.

### Menghitung ulang skor sentimen bulanan

```bash
cd analytics-py
python hitung_skor_sentimen2.py
```

Memperbarui kolom `skor_sentimen` di tabel `kinerja_bulanans` untuk seluruh
60 bulan. Jalankan dari dalam folder `analytics-py/`.

### Menghitung ulang skor DEA

```bash
cd analytics-py
pip install pulp sqlalchemy
python hitung_dea.py
```

`pulp` dan `sqlalchemy` tidak ada di `requirements.txt`, jadi instal dulu
secara terpisah seperti pada perintah di atas.

### Melabeli cuitan baru

```bash
python analytics-py/label_644.py
```

Melabeli semua baris `tweets` yang masih `label = 'unlabeled'` dengan model
hasil fine-tuning. Bisa dijalankan dari folder mana saja.

### Memprediksi dataset baru

```bash
python analytics-py/predict_new_data.py --help
```

Lihat opsi di `--help` terlebih dahulu. Sesuaikan `DB_PATH` di dalam file
bila dataset Anda tidak bernama `bsi_sentiment.db`.

### Mengulang fine-tuning (opsional, butuh GPU)

Buka `analytics-py/BSI_Sentiment_Finetuning.ipynb` di Google Colab
(dianjurkan GPU T4), atau jalankan `analytics-py/finetune_indobert.py`
dengan menyesuaikan `DB_PATH` di bagian konfigurasi file tersebut. Skrip ini
membaca data berlabel dari tabel `datasets` di database, jadi pastikan
database yang dipakai adalah `data/skripsi_bsi_v2.db`. Instalasi tambahan
di Colab: `transformers datasets scikit-learn torch accelerate`.

## Peta skripsi

| Bagian skripsi | File terkait di repositori ini |
|---|---|
| Bab III (metode, fine-tuning) | `analytics-py/finetune_indobert.py`, `analytics-py/BSI_Sentiment_Finetuning.ipynb`, `sampling/sampling_plan.py` |
| Bab IV (hasil DEA dan sentimen) | `dashboard-web/server2.py`, `analytics-py/hitung_dea.py`, `analytics-py/hitung_skor_sentimen2.py`, `dashboard-web/laporan_bab4.html` |
| Lampiran 2 (data keuangan bulanan) | `data/data_keuangan_bsi.xlsx`, tabel `kinerja_bulanans` di `data/skripsi_bsi_v2.db` |
| Lampiran 4 (daftar script dan file fine-tuning) | `analytics-py/` dan `indobert_bsi_sentiment/` |
| Grafik Bab IV (Gambar 4.1–4.9) | Dihasilkan dashboard (`divergence_chart_service.py`, `regression_service.py`, dan endpoint `/api/generate-analysis-charts` serta `/api/generate-divergence-chart`) dari `data/skripsi_bsi_v2.db` |

## Troubleshooting

**Model gagal dimuat / error menyebut `model.safetensors` atau pointer LFS.**
File model kemungkinan masih pointer 134 byte. Jalankan `git lfs pull` di
folder repositori, lalu periksa ukurannya (harus sekitar 498 MB). Pastikan
juga Git LFS sudah terpasang (`git lfs version`).

**`pip install` mengunduh sangat besar / sangat lama.**
Itu PyTorch versi CUDA. Batalkan, lalu ikuti cara instalasi CPU pada
langkah 4 di atas (instal `torch==2.15.0` dari `--index-url
https://download.pytorch.org/whl/cpu` terlebih dahulu).

**`ModuleNotFoundError: No module named 'pulp'` (atau `sqlalchemy`).**
Kedua paket itu hanya dipakai `hitung_dea.py` dan `import_data.py`, dan
tidak ada di `requirements.txt`. Instal dengan `pip install pulp sqlalchemy`.

**`Address already in use` / port 5000 sudah dipakai.**
Ada server lain yang masih berjalan di port 5000. Hentikan dulu server lama
(`Ctrl+C` di terminalnya), atau ubah `port=5000` pada baris terakhir
`dashboard-web/server2.py`.

**Dashboard terbuka tetapi grafik atau data kosong.**
Periksa `data/skripsi_bsi_v2.db` ada dan berukuran sekitar 20 MB. Server
mencari database di `../data/skripsi_bsi_v2.db` relatif terhadap folder
`dashboard-web/`, jadi jalankan server dari folder repositori atau dari
dalam `dashboard-web/`, bukan dari folder lain.

**PowerShell menolak `Activate.ps1`.**
Itu kebijakan eksekusi skrip Windows. Lewati aktivasi dan pakai Python
virtual environment secara langsung: `.\.venv\Scripts\python.exe ...`
untuk semua perintah.

**`python` tidak dikenali (Windows).**
Python belum terpasang atau belum masuk PATH. Pasang dari
<https://www.python.org/downloads/> dan centang "Add Python to PATH",
lalu buka terminal baru.

**Server berhenti sendiri saat pertama dijalankan.**
Baca pesan error di terminal. Penyebab paling umum: file model belum
terunduh lewat LFS (lihat poin pertama di atas), atau dependensi belum
terinstal lengkap (ulangi langkah 4 dan pastikan tidak ada error).

## Catatan

- Naskah skripsi (file `.docx`) tidak disimpan di repositori ini; yang ada
  di sini adalah kode, data, dan model pendukungnya.
- File `sampling/labeling_plan_summary.csv` adalah ringkasan rencana lama.
  Jangan pakai angka di dalamnya sebagai hasil akhir.
- Beberapa skrip lama (`cek_hasil.py`, `evaluate_accuracy.py`,
  `hitung_skor_sentimen.py`, `update_db.py`, `import_data.py`) masih
  menunjuk database lama `skripsi_bsi.db`. Untuk perhitungan final, pakai
  `skripsi_bsi_v2.db` beserta skrip-skrip final yang disebutkan di atas.
- Data tweet adalah cuitan publik tentang BSI yang dikumpulkan pada
  2021–2025 untuk keperluan penelitian ini.
