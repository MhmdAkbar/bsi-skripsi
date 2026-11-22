# analytics-py/import_data.py
import pandas as pd
from sqlalchemy import create_engine

print("Memulai proses injeksi data ke SQLite...")

# 1. Buat koneksi ke database SQLite
# Path naik satu tingkat (../) dari analytics-py, masuk ke data/
engine = create_engine('sqlite:///../data/skripsi_bsi_v2.db')

# 2. Baca file Excel
# Sesuaikan nama file ini jika berbeda
file_excel = '../data/data_keuangan_bsi.xlsx' 

try:
    df = pd.read_excel(file_excel)
    print(f"Berhasil membaca {len(df)} baris dari Excel.")
except FileNotFoundError:
    print(f"Error: File {file_excel} tidak ditemukan. Pastikan sudah di folder yang benar.")
    exit()

# 3. Mapping Kolom (SANGAT PENTING)
# KIRI: Nama kolom persis seperti yang ada di baris pertama Excel-mu
# KANAN: Nama kolom di database (sudah disesuaikan dengan standar GORM)
mapping_kolom = {
    'Periode': 'periode', 
    'DPK Input': 'dpk_input',
    'Beban Personel Input': 'beban_personel_input',
    'Beban Operasional Input': 'beban_operasional_input',
    'Pembiayaan Output': 'pembiayaan_output',
    'Pendapatan Operasional Output': 'pendapatan_output'
}

# Ubah nama kolom DataFrame sesuai mapping
df = df.rename(columns=mapping_kolom)

# Filter hanya kolom yang dibutuhkan database
kolom_db = ['periode', 'dpk_input', 'beban_personel_input', 'beban_operasional_input', 'pembiayaan_output', 'pendapatan_output']

# Pastikan semua kolom yang dibutuhkan ada setelah mapping
for col in kolom_db:
    if col not in df.columns:
        print(f"PERINGATAN: Kolom '{col}' tidak ditemukan setelah mapping. Cek nama kolom di Excel!")
        exit()

df_to_insert = df[kolom_db]

# 4. Eksekusi Injeksi ke Database
try:
    # if_exists='append' berarti kita menambahkan data ke tabel yang sudah dibuat oleh Golang
    # index=False agar index bawaan pandas tidak ikut masuk jadi kolom baru
    df_to_insert.to_sql('kinerja_bulanans', con=engine, if_exists='append', index=False)
    
    print("\n✅ SUKSES BESAR!")
    print("Data hasil begadangmu sudah terkunci aman di dalam database SQLite.")
    print("Sekarang datanya siap digeber pakai algoritma DEA kapan saja.")
except Exception as e:
    print("\n❌ Gagal memasukkan data. Detail error:")
    print(e)