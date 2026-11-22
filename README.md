# Skripsi BSI

Kode sumber pengumpulan data, analisis sentimen, dan dashboard untuk penelitian BSI.

## Menjalankan dashboard di Windows

Pasang Python 3.14 dan Git LFS. Setelah repository di-clone, jalankan dari
PowerShell pada folder repository:

```powershell
git lfs install
git lfs pull
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r dashboard-web\requirements.txt
.\.venv\Scripts\python.exe dashboard-web\server2.py
```

Buka `http://127.0.0.1:5000` setelah model selesai dimuat.

Dataset, database SQLite, dan konfigurasi model tersedia di repository. Bobot
`model.safetensors` diunduh melalui Git LFS. Virtual environment, cache, output,
dan credential lokal tetap tidak disimpan di Git.
