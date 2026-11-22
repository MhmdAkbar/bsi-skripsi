import re


DOMAIN_KEYWORDS = {
    "negative": [
        r"saldo\s+kepotong", r"waktu\s+habis", r"request\s+timeout",
        r"permintaan\s+kehabisan\s+waktu", r"belum\s+masuk", "error",
        "nyangkut", "maintenance", "hilang", r"cs\s+robot", "gangguan",
        "lelet", "lemot", "down", "gagal", "gabisa", r"ga\s+bisa",
        "ketahan", r"potong\s+saldo", "kembalikan", "kecewa", "parah",
        "buruk", "jelek", "ribet", r"pindah\s+bank",
        r"tutup\s+rekening", "uninstall", r"tidak\s+aman", r"gak\s+aman",
        "kecewa", "susah",
    ],
    "positive": [
        "mantap", "lancar", "terbantu", "kemudahan", "alhamdulillah",
        r"terima\s+kasih", "makasih", "keren", "bagus", "terbaik",
        "puas", "aman", "cuan", "untung", "mudah", "praktis", "solusi",
    ],
    "neutral": [
        "giveaway", "#zonauang", r"laba\s+bersih", r"jumat\s+berkah",
        "kpop", "#repost", "kuisioner", r"tugas\s+akhir", "jualan",
        "loker", "lowongan", "beasiswa", "oprec",
    ],
}

COMPILED_RULES = {
    category: re.compile(
        r"\b(?:" + "|".join(patterns) + r")\b", re.IGNORECASE
    )
    for category, patterns in DOMAIN_KEYWORDS.items()
}


def refine_sentiment_2022(text, ai_label, ai_score):
    """
    Evaluates domain-specific keywords to override general sentiment predictions.
    Filters noise first, then checks for critical technical issues or praises.
    """
    if COMPILED_RULES["neutral"].search(text):
        return "neutral", "Rule: Neutral/Noise Topic Filter"

    if COMPILED_RULES["negative"].search(text):
        return "negative", "Rule: Domain Negative Context"

    if COMPILED_RULES["positive"].search(text):
        return "positive", "Rule: Domain Positive Context"

    return ai_label, "IndoBERT Base Model"
