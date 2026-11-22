# F:\skripsi\bsi-skripsi\analytics-py\config_sentiment.py

import re

# Hard negatives that mandate an absolute override
HARD_NEG_KEYWORDS = [
    'gangguan', 'error', 'eror', 'lelet', 'lemot', 'down', 'maintenance', 'lola',
    'ngadat', 'muter', 'loading', 'timeout', 'bug', 'crash', 'gagal', 'gabisa',
    'ga bisa', 'ketahan', 'nyangkut', 'belum masuk', 'blm masuk', 'potong saldo',
    'saldo hilang', 'duit ilang', 'uang hilang', 'kembalikan', 'hack', 'hacker',
    'bobol', 'dibobol', 'retas', 'diretas', 'ransomware', 'lockbit', 'bocor',
    'kebocoran', 'dark web', 'darkweb', '1,5 tb', '1.5 tb', 'tebusan',
    'kecewa', 'kcewa', 'parah', 'buruk', 'jelek', 'hancur', 'payah', 'nyesel',
    'menyesal', 'males', 'ribet', 'repot', 'kacau', 'capek', 'pusing', 'muak',
    'gaguna', 'ga guna', 'sampah', 'ampas', 'tolol', 'goblok', 'gblk', 'bego',
    'anjing', 'anjg', 'bangsat', 'bgst', 'tai', 'taik', 'babi', 'monyet', 'sialan',
    'brengsek', 'jancok', 'cuk', 'pindah bank', 'tutup rekening', 'uninstall',
    'hapus aplikasi', 'ganti bank', 'tarik semua', 'tarik dana', 'mending bca',
    'mending mandiri', 'mending bank sebelah', 'gembel', 'bosok', 'nilep',
    'korupsi', 'blokir', 'keblokir', 'bapuk', 'kurang enak', 'tidak aman',
    'gak aman', 'ga aman', 'kurang bagus'
]

# Customer service interaction indicators
CS_KEYWORDS = ['bantu', 'tolong', 'cara', 'min', 'kak', 'tanya']

# Pre-compiled pattern for performance
HARD_NEG_PATTERN = re.compile(r'(?:' + '|'.join(map(re.escape, HARD_NEG_KEYWORDS)) + r')', re.IGNORECASE)

# Confidence threshold for AI predictions
CONFIDENCE_THRESHOLD = 0.65