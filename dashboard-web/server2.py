# dashboard-web/server2.py

from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS
import sqlite3
import os
import re
from collections import Counter
from transformers import pipeline
import json
import matplotlib
matplotlib.use('Agg') # Wajib untuk Flask agar proses gambar grafik tidak error
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from regression_service import generate_linear_regression_chart
from divergence_chart_service import generate_dual_axis_chart

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, '../data/skripsi_bsi_v2.db'))
LOCAL_MODEL_PATH = os.path.abspath(os.path.join(BASE_DIR, '../indobert_bsi_sentiment'))
ACCURACY_REPORT_PATH = os.path.join(BASE_DIR, 'accuracy_report.html')

# Global variables
sentiment_model = None
accuracy_progress = {"current": 0, "total": 0, "is_running": False}

def get_db_connection():
    """Establish and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_sentiment_model():
    """Load and return the Fine-Tuned Hugging Face sentiment analysis pipeline."""
    global sentiment_model

    if sentiment_model is None:
        print("--> Loading Fine-Tuned NLP Model (This may take a few seconds)...")
        
        # Ditambahkan parameter truncation agar aman dari input teks panjang
        sentiment_model = pipeline(
            "sentiment-analysis",
            model=LOCAL_MODEL_PATH,
            tokenizer=LOCAL_MODEL_PATH,
            device=-1,
            truncation=True, 
            max_length=512
        ) 

        print("\n===== MODEL INFO =====")
        print("Model :", sentiment_model.model.name_or_path)
        print("Model Class :", sentiment_model.model.__class__.__name__)
        print("Num Labels :", sentiment_model.model.config.num_labels)
        print("======================\n")

    return sentiment_model

def map_sentiment_label(raw_label):
    """Standardize raw model output labels to lowercase string."""
    return raw_label.lower()

# =========================================================
# ENDPOINT 1: Tweet Statistics (Sentiment Distribution)
# =========================================================
@app.route('/api/tweet-stats')
def get_tweet_stats():
    try:
        conn = get_db_connection()
        query = '''
        SELECT 
            strftime('%Y-%m', created_at) as bulan,
            COUNT(*) as jumlah,
            SUM(CASE WHEN label = 'positive' THEN 1 ELSE 0 END) as positif,
            SUM(CASE WHEN label = 'negative' THEN 1 ELSE 0 END) as negatif,
            SUM(CASE WHEN label = 'neutral' THEN 1 ELSE 0 END) as netral
        FROM tweets 
        GROUP BY bulan 
        ORDER BY bulan ASC
        '''
        rows = conn.execute(query).fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# ENDPOINT 2: Historical Events Data
# =========================================================
@app.route('/api/events')
def get_events():
    events = {
        '2021-02': {'title': 'Resmi Berdiri', 'type': 'Positif', 'impact': 'BSI resmi lahir dari merger tiga bank syariah BUMN, disambut positif publik.', 'color': 'rgb(16, 185, 129)'},
        '2021-11': {'title': 'Keberhasilan Migrasi Sistem Rekening', 'type': 'Positif', 'impact': 'Migrasi jutaan nasabah selesai, optimalisasi BSI Mobile.', 'color': 'rgb(16, 185, 129)'},
        '2022-02': {'title': 'Gangguan BSI Mobile Terpusat', 'type': 'Negatif', 'impact': 'Keluhan massal nasabah terkait kegagalan transaksi dan saldo tertahan.', 'color': 'rgb(244, 63, 94)'},
        '2022-03': {'title': 'Kinerja Gemilang Kuartal 1', 'type': 'Positif', 'impact': 'Pertumbuhan laba signifikan, profitabilitas stabil.', 'color': 'rgb(16, 185, 129)'},
        '2022-10': {'title': 'Isu Kelalaian Agunan', 'type': 'Negatif', 'impact': 'Mencuatnya keluhan publik terkait hilangnya sertifikat agunan nasabah.', 'color': 'rgb(244, 63, 94)'},
        '2023-05': {'title': 'Serangan Ransomware LockBit', 'type': 'Negatif', 'impact': 'Layanan lumpuh berhari-hari, ancaman kebocoran data nasabah.', 'color': 'rgb(244, 63, 94)'},
        '2023-06': {'title': 'Perombakan Jajaran Manajemen', 'type': 'Campuran', 'impact': 'Buntut krisis, direksi IT dirombak. Respon positif tapi kepercayaan masih rendah.', 'color': 'rgb(245, 158, 11)'},
        '2023-08': {'title': 'Ekspansi Global ke Dubai', 'type': 'Positif', 'impact': 'Peningkatan status representative office menjadi full branch di Dubai.', 'color': 'rgb(16, 185, 129)'},
        '2024-02': {'title': 'Top 10 Global Islamic Bank', 'type': 'Positif', 'impact': 'Kapitalisasi pasar BSI menembus 10 besar bank syariah dunia.', 'color': 'rgb(16, 185, 129)'},
        '2024-06': {'title': 'Penarikan Dana Triliunan Muhammadiyah', 'type': 'Negatif', 'impact': 'Saham loyo, dana triliunan ditarik karena diversifikasi.', 'color': 'rgb(244, 63, 94)'},
        '2024-11': {'title': 'Peluncuran SuperApp BYOND', 'type': 'Positif', 'impact': 'Aplikasi baru dengan antarmuka modern dan keamanan lebih baik.', 'color': 'rgb(16, 185, 129)'},
        '2025-01': {'title': 'Migrasi Paksa & Gangguan Sistem BYOND', 'type': 'Negatif', 'impact': 'Migrasi wajib nasabah dari BSI Mobile ke BYOND disertai gangguan teknis masif (gagal login, transaksi, dan QRIS) sepanjang akhir Januari 2025.', 'color': 'rgb(244, 63, 94)'},
        '2025-02': {'title': 'Era Bank Emas', 'type': 'Positif', 'impact': 'Perintis layanan perbankan emas syariah pertama di Indonesia.', 'color': 'rgb(16, 185, 129)'}
    }
    return jsonify(events)

# =========================================================
# ENDPOINT 3: DEA Performance Data & Comprehensive Comparative
# =========================================================
@app.route('/api/data')
def get_data():
    try:
        sort_by = request.args.get('sort', 'periode_asc')
        year_filter = request.args.get('year', '')

        conn = get_db_connection()
        query = 'SELECT * FROM kinerja_bulanans WHERE 1=1'
        params = []

        if year_filter:
            query += ' AND periode LIKE ?'
            params.append(f"{year_filter}%")

        if sort_by == 'dea_asc':
            query += ' ORDER BY skor_dea ASC'
        elif sort_by == 'dea_desc':
            query += ' ORDER BY skor_dea DESC'
        elif sort_by == 'gap_desc':
            query += ' ORDER BY ABS(skor_dea - COALESCE(skor_sentimen, 0.5)) DESC'
        else:
            query += ' ORDER BY periode ASC'

        rows = conn.execute(query, params).fetchall()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# ENDPOINT 4: Raw Tweets Data Exploration
# =========================================================
@app.route('/api/tweets')
def get_tweets():
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        month = request.args.get('month', '')
        search = request.args.get('search', '')
        label_status = request.args.get('label_status', '') 
        assignment = request.args.get('assignment', '') 
        dataset_target = request.args.get('dataset_target', '')
        
        # 1. TAMBAHKAN BARIS INI UNTUK MENANGKAP PARAMETER 'label'
        label = request.args.get('label', '')

        offset = (page - 1) * limit
        conn = get_db_connection()
        
        query_base = "FROM tweets WHERE 1=1"
        params = []
        
        if month:
            query_base += " AND strftime('%Y-%m', created_at) = ?"
            params.append(month)
        if search:
            query_base += " AND raw_content LIKE ?"
            params.append(f"%{search}%")
            
        # 2. TAMBAHKAN BLOK LOGIKA INI UNTUK FILTER SQL-NYA
        if label:
            query_base += " AND label = ?"
            params.append(label)
            
        if label_status == 'labeled':
            query_base += " AND label IS NOT NULL"
        elif label_status == 'unlabeled':
            query_base += " AND label IS NULL"
            
        # Strict isolation: Fetch unassigned OR assigned to the currently edited dataset
        if assignment == 'unassigned':
            if dataset_target:
                query_base += " AND (dataset_id IS NULL OR dataset_id = ?)"
                params.append(dataset_target)
            else:
                query_base += " AND dataset_id IS NULL"
            
        count_query = f"SELECT COUNT(*) as total {query_base}"
        total_rows = conn.execute(count_query, params).fetchone()['total']
        
        data_query = f"SELECT id, created_at as date, raw_content as content, label, label_ai {query_base} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = conn.execute(data_query, params).fetchall()
        conn.close()
        
        return jsonify({
            "data": [dict(row) for row in rows],
            "total": total_rows, "page": page, "limit": limit,
            "total_pages": (total_rows + limit - 1) // limit if limit > 0 else 1
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
# =========================================================
# ENDPOINT 5: Dataset Management (Create, Update, Delete)
# =========================================================
@app.route('/api/datasets', methods=['GET', 'POST', 'PUT'])
def manage_datasets():
    conn = get_db_connection()
    try:
        if request.method == 'POST' or request.method == 'PUT':
            req_data = request.get_json()
            
            dataset_id = req_data.get('id')
            nama_dataset = req_data.get('nama_dataset', 'Untitled Dataset')
            deskripsi = req_data.get('deskripsi', '')
            labeled_data = req_data.get('data', [])
            
            from datetime import datetime
            json_data = json.dumps(labeled_data, ensure_ascii=False)
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            cursor = conn.cursor()
            
            if request.method == 'POST':
                cursor.execute('INSERT INTO datasets (nama_dataset, deskripsi, data, created_at) VALUES (?, ?, ?, ?)', 
                               (nama_dataset, deskripsi, json_data, now))
                active_dataset_id = cursor.lastrowid
            else:
                cursor.execute('UPDATE datasets SET nama_dataset = ?, deskripsi = ?, data = ? WHERE id = ?', 
                               (nama_dataset, deskripsi, json_data, dataset_id))
                active_dataset_id = dataset_id

            # Sync Tweets mapping
            if labeled_data:
                update_values = []
                for item in labeled_data:
                    tweet_id = item.get('id')
                    label_val = item.get('expected')
                    if tweet_id and label_val:
                        update_values.append((label_val, active_dataset_id, tweet_id))
                
                if update_values:
                    cursor.executemany("UPDATE tweets SET label = ?, dataset_id = ? WHERE id = ?", update_values)

            conn.commit()
            return jsonify({"id": active_dataset_id, "nama_dataset": nama_dataset, "status": "success"})

        rows = conn.execute('SELECT * FROM datasets ORDER BY id DESC').fetchall()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/datasets/<int:id>', methods=['DELETE'])
def delete_dataset(id):
    """Delete a dataset and release its associated tweets back to unassigned status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE tweets SET dataset_id = NULL, label = NULL WHERE dataset_id = ?", (id,))
        cursor.execute("DELETE FROM datasets WHERE id = ?", (id,))
        conn.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

# =========================================================
# ENDPOINT 6: Word Frequency (Word Cloud)
# =========================================================
@app.route('/api/word-freq')
def get_word_freq():
    try:
        month = request.args.get('month', '')
        label = request.args.get('label', '')
        
        conn = get_db_connection()
        query = "SELECT raw_content as content FROM tweets WHERE 1=1"
        params = []
        if month:
            query += " AND strftime('%Y-%m', created_at) = ?"
            params.append(month)
        if label:
            query += " AND label = ?"
            params.append(label)
            
        rows = conn.execute(query, params).fetchall()
        conn.close()
        
        all_text = " ".join([r['content'] for r in rows]).lower()
        words = re.findall(r'\b[a-z]{4,}\b', all_text)
        
        stopwords = {'yang', 'untuk', 'pada', 'ke', 'dari', 'ini', 'itu', 'dengan', 
                     'dan', 'atau', 'saya', 'kamu', 'dia', 'mereka', 'kita', 'kami',
                     'bank', 'bsi', 'syariah', 'indonesia', 'mobile', 'bikin', 'buat',
                     'lagi', 'bisa', 'tidak', 'gak', 'enggak', 'udah', 'sudah', 'kalau',
                     'ada', 'aja', 'saja', 'juga', 'terus', 'sama', 'sampai', 'tapi', 'https', 'masih', 'rochmatpurwanto', 'bewizebisnisjadimudah', 'secgron', 'bewize'}
                     
        filtered_words = [w for w in words if w not in stopwords]
        word_counts = Counter(filtered_words).most_common(50)
        
        return jsonify([{"word": w, "weight": c} for w, c in word_counts])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# ENDPOINT 7: Basic NLP Stats (Cleaned)
# =========================================================
@app.route('/api/stats')
def get_nlp_stats():
    try:
        conn = get_db_connection()
        total = conn.execute("SELECT COUNT(*) as t FROM tweets").fetchone()['t']
        conn.close()

        # Diperbarui: nilai berikut adalah hasil evaluasi jujur pada test-set
        # (belum pernah dilihat model selama training) dari fine-tuning IndoBERT murni,
        # sesuai indobert_bsi_sentiment_classification_report.txt. Rule-Based Override
        # SUDAH TIDAK DIPAKAI lagi - angka lama (83.3/83.7/83.5/83.6) adalah peninggalan
        # dari metode hybrid yang sudah tidak relevan dengan metodologi final di Bab III.
        return jsonify({
            "accuracy": 82.63, "precision": 82.71, "recall": 83.03, "f1_score": 82.84,
            "total_data": total
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# ENDPOINT 8: Test Live Analyzer (No Hybrid Rules needed anymore)
# =========================================================
@app.route('/api/test-analyzer', methods=['POST'])
def test_analyzer():
    """Evaluate raw text sentiment based purely on the Fine-Tuned Model."""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"error": "Empty text payload."}), 400
            
        lower_text = text.lower()
        model = get_sentiment_model()
        pred = model(lower_text)[0]

        ai_label = map_sentiment_label(pred['label'])
        ai_score = pred['score']
                
        return jsonify({
            "ai_label": ai_label,
            "confidence_score": round(ai_score, 4),
            "final_label": ai_label,
            "applied_rule": "Fine-Tuned Model"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# ENDPOINT: Auto-Generate Diagram Regresi Linear (Bab 4)
# =========================================================
@app.route('/api/generate-analysis-charts')
def generate_analysis_charts():
    try:
        # Pastikan folder static tersedia
        static_dir = os.path.join(BASE_DIR, 'static')
        os.makedirs(static_dir, exist_ok=True)
        
        conn = get_db_connection()

        # --- GENERATE LINEAR REGRESSION CHART (keseluruhan + tahunan) ---
        regression_stats = generate_linear_regression_chart(conn, static_dir)
        conn.close()

        import time
        return jsonify({
            "status": "success", 
            "regresi": f"/static/regresi_dinamis.png?t={int(time.time())}", 
            "stats": regression_stats # Teruskan data statistik regresi ke Frontend
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# ENDPOINT: Grafik Dual-Axis Divergensi (NSS vs DEA, skala asli)
# =========================================================
@app.route('/api/generate-divergence-chart')
def generate_divergence_chart():
    try:
        static_dir = os.path.join(BASE_DIR, 'static')
        os.makedirs(static_dir, exist_ok=True)

        conn = get_db_connection()
        divergence_result = generate_dual_axis_chart(conn, static_dir)
        conn.close()

        import time
        return jsonify({
            "status": "success",
            "chart": f"/static/{divergence_result['chart']}?t={int(time.time())}" if divergence_result['chart'] else None,
            "highlight_gap_bulan": divergence_result['highlight_gap_bulan'],
            "statistik_volatilitas": divergence_result.get('statistik_volatilitas'),
            "daftar_event_bernomor": divergence_result.get('daftar_event_bernomor')
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# =========================================================
# VIEW ROUTINGS
# =========================================================
@app.route('/')
def index():
    try:
        index2_path = os.path.join(BASE_DIR, 'index2.html')
        filename = index2_path if os.path.exists(index2_path) else os.path.join(BASE_DIR, 'index.html')
        with open(filename, 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return jsonify({"error": "File HTML tidak ditemukan!"}), 404

@app.route('/annotator')
def annotator_page():
    try:
        with open(os.path.join(BASE_DIR, 'annotator.html'), 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return "File annotator.html tidak ditemukan!", 404

@app.route('/api/accuracy-progress')
def get_accuracy_progress():
    return jsonify(accuracy_progress)

@app.route('/export-bab4')
def export_bab4():
    try:
        with open(os.path.join(BASE_DIR, 'laporan_bab4.html'), 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return "File laporan_bab4.html belum dibuat!", 404

# =========================================================
# ENDPOINT: Run Accuracy Evaluation (Cleaned - Pure Model Evaluation)
# =========================================================
@app.route('/api/run-accuracy', methods=['POST'])
def run_accuracy():
    """Evaluate predictions against a specific dataset and generate an HTML report."""
    global accuracy_progress 
    
    try:
        req_data = request.get_json()
        dataset_id = req_data.get('dataset_id')

        if not dataset_id:
            return jsonify({"error": "Dataset ID is required to run the accuracy test."}), 400

        conn = get_db_connection()
        dataset_row = conn.execute('SELECT nama_dataset, data FROM datasets WHERE id = ?', (dataset_id,)).fetchone()
        conn.close()

        if not dataset_row:
            return jsonify({"error": "Target dataset not found."}), 404

        dataset_name = dataset_row['nama_dataset']
        tweets = json.loads(dataset_row['data'])
        
        if not tweets:
            return jsonify({"error": "Dataset is empty."}), 400

        model = get_sentiment_model()
        
        correct_model = 0
        total = len(tweets)
        report_data = [] 
        
        accuracy_progress["current"] = 0
        accuracy_progress["total"] = total
        accuracy_progress["is_running"] = True
        
        BATCH_SIZE = 16 
        
        for i in range(0, total, BATCH_SIZE):
            batch_tweets = tweets[i:i + BATCH_SIZE]
            batch_texts = [t.get('text', '').lower() for t in batch_tweets]
            preds = model(batch_texts)
            
            for j, t in enumerate(batch_tweets):
                text = t.get('text', '')
                expected = t.get('expected', '')
                ai_label = map_sentiment_label(preds[j]['label'])
                
                is_correct = ai_label == expected
                if is_correct: correct_model += 1

                report_data.append({
                    "no": len(report_data) + 1,
                    "text": text,
                    "expected": expected,
                    "model_pred": ai_label,
                    "is_correct": is_correct
                })
                
                accuracy_progress["current"] += 1

        acc_model = (correct_model / total) * 100 if total > 0 else 0

        # === DYNAMIC HTML REPORT GENERATION (STREAMLINED) ===
        html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laporan Evaluasi: {dataset_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-50 text-slate-800 p-4 sm:p-6 lg:p-8">
    <div class="max-w-[1200px] mx-auto w-full flex flex-col gap-6">
        <header class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row justify-between gap-5">
            <div>
                <h1 class="text-3xl font-extrabold text-slate-900">Hasil Uji: {dataset_name}</h1>
                <p class="text-sm text-slate-500 mt-1">Evaluasi performa Fine-Tuned IndoBERT vs Golden Data.</p>
            </div>
            <div class="flex gap-3">
                <select id="report-match-filter" class="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer">
                    <option value="all">Semua Data</option>
                    <option value="mismatch">Hanya Yang Tidak Sesuai (Error Analysis)</option>
                </select>
                <button onclick="copyToAI()" class="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2 rounded-xl text-sm font-bold shadow-md transition-all">Copy to AI</button>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 border-t-4 border-t-slate-500">
                <p class="text-xs font-bold text-slate-400 uppercase">Total Golden Data</p>
                <p class="text-4xl font-black text-slate-800 mt-2">{total} <span class="text-sm font-medium text-slate-500">Tweet</span></p>
            </div>
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 border-t-4 border-t-emerald-400">
                <p class="text-xs font-bold text-slate-400 uppercase">Akurasi Model BSI</p>
                <p class="text-4xl font-black text-emerald-600 mt-2">{acc_model:.2f}%</p>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="overflow-y-auto max-h-[700px]">
                <table class="w-full text-left text-sm">
                    <thead class="bg-slate-50 text-slate-600 font-bold sticky top-0 shadow-sm border-b border-slate-200">
                        <tr>
                            <th class="py-4 px-6 text-center w-16">No</th>
                            <th class="py-4 px-6 w-1/2">Teks Raw</th>
                            <th class="py-4 px-6 text-center">Ground Truth</th>
                            <th class="py-4 px-6 text-center">Prediksi Model</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
        """
        
        for row in report_data:
            color_class = "text-emerald-700 bg-emerald-50 border-emerald-200" if row['is_correct'] else "text-rose-600 bg-rose-50 border-rose-200"
            row_bg = "bg-white" if row['is_correct'] else "bg-rose-50/30"
            
            html_content += f"""
                        <tr class="{row_bg} hover:bg-slate-50 transition-colors report-row" data-expected="{row['expected']}" data-pred="{row['model_pred']}">
                            <td class="py-4 px-6 text-center text-slate-500 font-bold">{row['no']}</td>
                            <td class="py-4 px-6 text-slate-700 leading-relaxed">{row['text']}</td>
                            <td class="py-4 px-6 text-center">
                                <span class="inline-block bg-slate-100 border border-slate-200 px-3 py-1 rounded-lg font-bold uppercase text-xs">{row['expected']}</span>
                            </td>
                            <td class="py-4 px-6 text-center">
                                <span class="inline-block border px-3 py-1 rounded-lg font-bold uppercase text-xs {color_class}">{row['model_pred']}</span>
                            </td>
                        </tr>
            """

        html_content += f"""
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script>
        const rawData = {json.dumps(report_data)};
        const filterDropdown = document.getElementById('report-match-filter');
        
        filterDropdown.addEventListener('change', (e) => {{
            const filter = e.target.value;
            document.querySelectorAll('.report-row').forEach(row => {{
                const exp = row.getAttribute('data-expected');
                const pred = row.getAttribute('data-pred');
                row.style.display = (filter === 'mismatch' && exp === pred) ? 'none' : '';
            }});
        }});

        function copyToAI() {{
            const filter = filterDropdown.value;
            let filtered = rawData;
            let filterLabel = "SEMUA DATA";

            if (filter === 'mismatch') {{
                filtered = rawData.filter(d => !d.is_correct);
                filterLabel = "HANYA PREDIKSI SALAH (ERROR ANALYSIS)";
            }}

            let copyText = `========== LAPORAN AKURASI ==========\\n`;
            copyText += `Total Data : {total} Tweet\\nAkurasi    : {acc_model:.2f}%\\nFilter     : ${{filterLabel}}\\n\\n`;
            
            filtered.forEach(d => {{
                copyText += `${{d.no}}. "${{d.text}}"\\n   Ground Truth: ${{d.expected.toUpperCase()}} | Prediksi Model: ${{d.model_pred.toUpperCase()}}\\n\\n`;
            }});

            const ta = document.createElement("textarea");
            ta.value = copyText; ta.style.position = "fixed"; document.body.appendChild(ta);
            ta.focus(); ta.select();
            try {{ document.execCommand('copy'); alert("Tersalin! Silakan Paste ke chat AI."); }} 
            catch(err) {{ alert("Gagal menyalin."); }}
            document.body.removeChild(ta);
        }}
    </script>
</body>
</html>
        """
        
        with open(ACCURACY_REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        accuracy_progress["is_running"] = False

        return jsonify({
            "status": "success",
            "dataset_name": dataset_name,
            "total": total,
            "acc_vanilla": round(acc_model, 2), # Keep key name for frontend compatibility
            "acc_hybrid": round(acc_model, 2)
        })
    except Exception as e:
        accuracy_progress["is_running"] = False
        return jsonify({"error": str(e)}), 500

# =========================================================
# ENDPOINT: Run Accuracy Evaluation for ALL Datasets
# =========================================================
@app.route('/api/run-accuracy-all', methods=['POST'])
def run_accuracy_all():
    global accuracy_progress 
    
    try:
        conn = get_db_connection()
        datasets = conn.execute('SELECT nama_dataset, data FROM datasets').fetchall()
        conn.close()

        if not datasets:
            return jsonify({"error": "No datasets available in the database."}), 404

        all_tweets_dict = {}
        for row in datasets:
            for item in json.loads(row['data']):
                tweet_id = item.get('id')
                if tweet_id and item.get('expected') in ['positive', 'negative', 'neutral']:
                    all_tweets_dict[tweet_id] = item
                    
        all_tweets = list(all_tweets_dict.values())
            
        if not all_tweets:
            return jsonify({"error": "All datasets are empty or have no valid labels."}), 400

        total = len(all_tweets)
        report_data = [] 
        correct_model = 0
        
        accuracy_progress["current"] = 0
        accuracy_progress["total"] = total
        accuracy_progress["is_running"] = True
        
        model = get_sentiment_model()
        BATCH_SIZE = 16 
        
        for i in range(0, total, BATCH_SIZE):
            batch_tweets = all_tweets[i:i + BATCH_SIZE]
            batch_texts = [t.get('text', '').lower() for t in batch_tweets]
            preds = model(batch_texts)
            
            for j, t in enumerate(batch_tweets):
                text = t.get('text', '')
                expected = t.get('expected', '')
                ai_label = map_sentiment_label(preds[j]['label'])
                
                is_correct = ai_label == expected
                if is_correct: correct_model += 1

                report_data.append({
                    "no": len(report_data) + 1,
                    "text": text,
                    "expected": expected,
                    "model_pred": ai_label,
                    "is_correct": is_correct
                })
                
                accuracy_progress["current"] += 1

        acc_model = (correct_model / total) * 100 if total > 0 else 0

        dataset_name_display = f"Gabungan Semua Dataset ({len(datasets)} File)"
        
        # === DYNAMIC HTML REPORT GENERATION (STREAMLINED) ===
        html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laporan Evaluasi Makro</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}</style>
</head>
<body class="bg-slate-50 text-slate-800 p-4 sm:p-6 lg:p-8">
    <div class="max-w-[1200px] mx-auto w-full flex flex-col gap-6">
        <header class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col md:flex-row justify-between gap-5">
            <div>
                <h1 class="text-3xl font-extrabold text-slate-900">Hasil Uji Makro: {dataset_name_display}</h1>
                <p class="text-sm text-slate-500 mt-1">Evaluasi performa Fine-Tuned IndoBERT vs Seluruh Golden Data.</p>
            </div>
            <div class="flex gap-3">
                <select id="report-match-filter" class="bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer">
                    <option value="all">Semua Data</option>
                    <option value="mismatch">Hanya Yang Tidak Sesuai (Error Analysis)</option>
                </select>
                <button onclick="copyToAI()" class="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2 rounded-xl text-sm font-bold shadow-md transition-all">Copy to AI</button>
            </div>
        </header>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 border-t-4 border-t-slate-500">
                <p class="text-xs font-bold text-slate-400 uppercase">Total Golden Data</p>
                <p class="text-4xl font-black text-slate-800 mt-2">{total} <span class="text-sm font-medium text-slate-500">Tweet</span></p>
            </div>
            <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 border-t-4 border-t-emerald-400">
                <p class="text-xs font-bold text-slate-400 uppercase">Akurasi Makro Model BSI</p>
                <p class="text-4xl font-black text-emerald-600 mt-2">{acc_model:.2f}%</p>
            </div>
        </div>

        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div class="overflow-y-auto max-h-[700px]">
                <table class="w-full text-left text-sm">
                    <thead class="bg-slate-50 text-slate-600 font-bold sticky top-0 shadow-sm border-b border-slate-200">
                        <tr>
                            <th class="py-4 px-6 text-center w-16">No</th>
                            <th class="py-4 px-6 w-1/2">Teks Raw</th>
                            <th class="py-4 px-6 text-center">Ground Truth</th>
                            <th class="py-4 px-6 text-center">Prediksi Model</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
        """
        
        for row in report_data:
            color_class = "text-emerald-700 bg-emerald-50 border-emerald-200" if row['is_correct'] else "text-rose-600 bg-rose-50 border-rose-200"
            row_bg = "bg-white" if row['is_correct'] else "bg-rose-50/30"
            
            html_content += f"""
                        <tr class="{row_bg} hover:bg-slate-50 transition-colors report-row" data-expected="{row['expected']}" data-pred="{row['model_pred']}">
                            <td class="py-4 px-6 text-center text-slate-500 font-bold">{row['no']}</td>
                            <td class="py-4 px-6 text-slate-700 leading-relaxed">{row['text']}</td>
                            <td class="py-4 px-6 text-center">
                                <span class="inline-block bg-slate-100 border border-slate-200 px-3 py-1 rounded-lg font-bold uppercase text-xs">{row['expected']}</span>
                            </td>
                            <td class="py-4 px-6 text-center">
                                <span class="inline-block border px-3 py-1 rounded-lg font-bold uppercase text-xs {color_class}">{row['model_pred']}</span>
                            </td>
                        </tr>
            """

        html_content += f"""
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script>
        const rawData = {json.dumps(report_data)};
        const filterDropdown = document.getElementById('report-match-filter');
        
        filterDropdown.addEventListener('change', (e) => {{
            const filter = e.target.value;
            document.querySelectorAll('.report-row').forEach(row => {{
                const exp = row.getAttribute('data-expected');
                const pred = row.getAttribute('data-pred');
                row.style.display = (filter === 'mismatch' && exp === pred) ? 'none' : '';
            }});
        }});

        function copyToAI() {{
            const filter = filterDropdown.value;
            let filtered = rawData;
            let filterLabel = "SEMUA DATA";

            if (filter === 'mismatch') {{
                filtered = rawData.filter(d => !d.is_correct);
                filterLabel = "HANYA PREDIKSI SALAH (ERROR ANALYSIS)";
            }}

            let copyText = `========== LAPORAN AKURASI MAKRO ==========\\n`;
            copyText += `Total Data : {total} Tweet\\nAkurasi    : {acc_model:.2f}%\\nFilter     : ${{filterLabel}}\\n\\n`;
            
            filtered.forEach(d => {{
                copyText += `${{d.no}}. "${{d.text}}"\\n   Ground Truth: ${{d.expected.toUpperCase()}} | Prediksi Model: ${{d.model_pred.toUpperCase()}}\\n\\n`;
            }});

            const ta = document.createElement("textarea");
            ta.value = copyText; ta.style.position = "fixed"; document.body.appendChild(ta);
            ta.focus(); ta.select();
            try {{ document.execCommand('copy'); alert("Tersalin! Silakan Paste ke chat AI."); }} 
            catch(err) {{ alert("Gagal menyalin."); }}
            document.body.removeChild(ta);
        }}
    </script>
</body>
</html>
        """
        
        with open(ACCURACY_REPORT_PATH, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        accuracy_progress["is_running"] = False

        return jsonify({
            "status": "success",
            "dataset_name": dataset_name_display,
            "total": total,
            "acc_vanilla": round(acc_model, 2),
            "acc_hybrid": round(acc_model, 2)
        })

    except Exception as e:
        accuracy_progress["is_running"] = False
        return jsonify({"error": str(e)}), 500

@app.route('/accuracy-report')
def show_accuracy_report():
    try:
        with open(ACCURACY_REPORT_PATH, 'r', encoding='utf-8') as f:
            return render_template_string(f.read())
    except FileNotFoundError:
        return "File laporan belum dibuat. Jalankan 'Uji Akurasi' di Annotator terlebih dahulu.", 404


print("=== PRELOAD MODEL ===")
get_sentiment_model()
print("=== MODEL READY ===")

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
