# uji_100_tweets.py
import json
import sys
from datetime import datetime
from transformers import pipeline
from tqdm import tqdm
from sentiment_rules import refine_sentiment

print("Loading Model IndoBERT w11wo... (Please wait)")
try:
    model = pipeline(
        "sentiment-analysis",
        model="w11wo/indonesian-roberta-base-sentiment-classifier",
        device=-1
    )
except Exception as e:
    print(f"Failed to load the deep learning model: {e}")
    sys.exit(1)

def evaluate_vanilla(dataset, dataset_name="dataset"):
    results = []
    correct = 0

    print(f"Running VANILLA evaluation for {dataset_name} ({len(dataset)} tweets)...")
    for data in tqdm(dataset):
        text = data['text']
        expected = data['expected']
        pred = model(text.lower())[0]
        vanilla_label = pred['label'].lower()
        vanilla_score = pred['score']

        is_correct = (vanilla_label == expected)
        if is_correct:
            correct += 1

        results.append({
            "text": text,
            "expected": expected,
            "vanilla_label": vanilla_label,
            "vanilla_score": vanilla_score,
            "is_correct_vanilla": is_correct
        })

    accuracy = (correct / len(dataset)) * 100
    return results, accuracy, correct

def evaluate_hybrid(dataset, dataset_name="dataset"):
    results = []
    correct = 0

    print(f"Running HYBRID evaluation for {dataset_name} ({len(dataset)} tweets)...")
    for data in tqdm(dataset):
        text = data['text']
        lower_text = text.lower().strip()
        expected = data['expected']

        pred = model(lower_text)[0]
        ai_label = pred['label'].lower()
        ai_score = pred['score']

        final_label, applied_rule = refine_sentiment(lower_text, ai_label, ai_score)

        is_correct = (final_label == expected)
        if is_correct:
            correct += 1

        results.append({
            "text": text,
            "expected": expected,
            "ai_label": f"{ai_label} ({ai_score:.2f})",
            "final_label": final_label,
            "rule": applied_rule,
            "is_correct_hybrid": is_correct
        })

    accuracy = (correct / len(dataset)) * 100
    return results, accuracy, correct

def generate_unified_html(all_runs, output_filename="laporan_keseluruhan_sentimen.html"):
    total_datasets = len(all_runs)
    global_total_tweets = sum(run['total_tweets'] for run in all_runs)
    global_vanilla_correct = sum(run['vanilla_correct'] for run in all_runs)
    global_hybrid_correct = sum(run['hybrid_correct'] for run in all_runs)
    
    global_vanilla_acc = (global_vanilla_correct / global_total_tweets * 100) if global_total_tweets > 0 else 0
    global_hybrid_acc = (global_hybrid_correct / global_total_tweets * 100) if global_total_tweets > 0 else 0

    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sesi Eksperimen: Laporan Akurasi Sentimen Komulatif</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body {{ font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f1f5f9; }}</style>
</head>
<body class="p-6 md:p-12 text-slate-800">
    <div class="max-w-7xl mx-auto">
        <header class="mb-10 bg-gradient-to-r from-slate-900 to-indigo-950 p-8 rounded-3xl shadow-xl border border-slate-800 text-white">
            <span class="px-3 py-1 bg-indigo-500/20 text-indigo-300 rounded-full text-xs font-bold tracking-wider uppercase border border-indigo-500/30">Unified Master Logging Room</span>
            <h1 class="text-3xl font-extrabold mt-2 tracking-tight">Dashboard Hasil Pengujian Komulatif</h1>
            <p class="text-slate-400 mt-1">Menampilkan ringkasan seluruh dataset dalam satu sesi eksekusi aktif.</p>
            
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8 pt-6 border-t border-slate-800">
                <div class="bg-slate-800/40 p-4 rounded-2xl border border-slate-800">
                    <p class="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Dataset</p>
                    <p class="text-3xl font-black text-indigo-400 mt-1">{total_datasets}</p>
                </div>
                <div class="bg-slate-800/40 p-4 rounded-2xl border border-slate-800">
                    <p class="text-xs font-bold text-slate-400 uppercase tracking-wider">Total Seluruh Tweet</p>
                    <p class="text-3xl font-black text-slate-200 mt-1">{global_total_tweets}</p>
                </div>
                <div class="bg-slate-800/40 p-4 rounded-2xl border border-slate-800">
                    <p class="text-xs font-bold text-slate-400 uppercase tracking-wider">Akurasi Makro Vanilla</p>
                    <p class="text-3xl font-black text-rose-400 mt-1">{global_vanilla_acc:.2f}%</p>
                </div>
                <div class="bg-slate-800/40 p-4 rounded-2xl border border-slate-800">
                    <p class="text-xs font-bold text-slate-400 uppercase tracking-wider">Akurasi Makro Hybrid</p>
                    <p class="text-3xl font-black text-emerald-400 mt-1">{global_hybrid_acc:.2f}%</p>
                </div>
            </div>
        </header>
        <div class="space-y-12">"""

    for run in all_runs:
        ds_id = run["dataset_id"]
        ts = run["timestamp"]
        v_acc = run["vanilla_acc"]
        v_corr = run["vanilla_correct"]
        h_acc = run["hybrid_acc"]
        h_corr = run["hybrid_correct"]
        total = run["total_tweets"]

        html_content += f"""
            <section class="bg-white rounded-3xl shadow-sm border border-slate-200 overflow-hidden">
                <div class="p-6 bg-slate-50 border-b border-slate-200 flex flex-wrap justify-between items-center gap-4">
                    <div>
                        <h2 class="text-xl font-bold text-slate-900">📦 Dataset #{ds_id}</h2>
                        <p class="text-xs text-slate-400 mt-0.5">Waktu Eksekusi: {ts}</p>
                    </div>
                    <div class="flex gap-4">
                        <div class="text-right">
                            <span class="text-xs font-bold text-slate-400 uppercase block">IndoBERT Vanilla</span>
                            <span class="text-lg font-extrabold text-slate-700">{v_acc:.2f}% ({v_corr}/{total})</span>
                        </div>
                        <div class="text-right border-l pl-4 border-slate-300">
                            <span class="text-xs font-bold text-slate-400 uppercase block">Tuned Hybrid Engine</span>
                            <span class="text-lg font-extrabold text-indigo-600">{h_acc:.2f}% ({h_corr}/{total})</span>
                        </div>
                    </div>
                </div>

                <div class="overflow-x-auto max-h-[450px] overflow-y-auto">
                    <table class="w-full text-left border-collapse text-sm">
                        <thead class="bg-slate-100 text-slate-500 text-xs uppercase font-bold tracking-wider border-b border-slate-200 sticky top-0 z-10">
                            <tr>
                                <th class="py-3 px-6 text-center w-12 bg-slate-100">No</th>
                                <th class="py-3 px-6 bg-slate-100">Teks Tweet</th>
                                <th class="py-3 px-6 w-28 bg-slate-100">Ground Truth</th>
                                <th class="py-3 px-6 w-28 bg-slate-100">Predictions Vanilla</th>
                                <th class="py-3 px-6 w-28 bg-slate-100">Predictions Hybrid</th>
                                <th class="py-3 px-6 bg-slate-100">Aturan Penalaan (RBO)</th>
                                <th class="py-3 px-6 text-center w-20 bg-slate-100">Vanilla</th>
                                <th class="py-3 px-6 text-center w-20 bg-slate-100">Hybrid</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100 bg-white">"""

        for idx, row in enumerate(run["combined_rows"], 1):
            expected_badge = "bg-emerald-50 text-emerald-700 border-emerald-200" if row['expected'] == 'positive' else ("bg-rose-50 text-rose-700 border-rose-200" if row['expected'] == 'negative' else "bg-slate-100 text-slate-600 border-slate-200")
            vanilla_badge = "bg-emerald-600 text-white" if row['vanilla_label'] == 'positive' else ("bg-rose-600 text-white" if row['vanilla_label'] == 'negative' else "bg-slate-700 text-white")
            hybrid_badge = "bg-emerald-600 text-white" if row['hybrid_label'] == 'positive' else ("bg-rose-600 text-white" if row['hybrid_label'] == 'negative' else "bg-slate-700 text-white")

            v_icon, v_color = ("✓", "text-emerald-600") if row['vanilla_correct'] else ("✗", "text-rose-600")
            h_icon, h_color = ("✓", "text-emerald-600") if row['hybrid_correct'] else ("✗", "text-rose-600")
            row_class = "bg-emerald-50/30" if (not row['vanilla_correct'] and row['hybrid_correct']) else ("bg-amber-50/30" if (row['vanilla_correct'] and not row['hybrid_correct']) else "")

            html_content += f"""
                            <tr class="{row_class} hover:bg-slate-50/80 transition">
                                <td class="py-3 px-6 text-center font-bold text-slate-400">{idx}</td>
                                <td class="py-3 px-6 font-medium text-slate-700 leading-relaxed">{row['text']}</td>
                                <td class="py-3 px-6"><span class="px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider {expected_badge}">{row['expected']}</span></td>
                                <td class="py-3 px-6"><span class="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider shadow-sm {vanilla_badge}">{row['vanilla_label']}</span><br><span class="text-[9px] text-slate-400">({row['vanilla_score']})</span></td>
                                <td class="py-3 px-6"><span class="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider shadow-sm {hybrid_badge}">{row['hybrid_label']}</span></td>
                                <td class="py-3 px-6 text-xs text-slate-500 font-medium">{row['hybrid_rule']}</td>
                                <td class="py-3 px-6 text-center text-lg font-bold {v_color}">{v_icon}</td>
                                <td class="py-3 px-6 text-center text-lg font-bold {h_color}">{h_icon}</td>
                            </tr>"""

        html_content += """
                        </tbody>
                    </table>
                </div>
            </section>"""

    html_content += """
        </div>
    </div>
</body>
</html>"""

    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

def main():
    print("\n" + "="*60)
    print("      INTERACTIVE SENTIMENT MODEL ACCURACY TEST BENCH")
    print("="*60)
    print("Instructions: Paste your raw JSON array data strings below.")
    print("Trigger computation by hitting ENTER twice on a clean empty line.\n")

    all_runs_memory = []
    dataset_counter = 1

    while True:
        try:
            print(f"\n--- Dataset #{dataset_counter} ---")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            
            user_input = "\n".join(lines).strip()
            if not user_input:
                print("Empty execution sequence requested. Terminal loop reset.")
                continue

            try:
                dataset = json.loads(user_input)
            except json.JSONDecodeError:
                print("Invalid JSON serialization template. Ensure standard double quotes are preserved.")
                continue

            if not isinstance(dataset, list):
                print("Structural context error: Root entity must remain an array of objects.")
                continue

            is_valid_schema = True
            for index, item in enumerate(dataset):
                if not isinstance(item, dict) or 'text' not in item or 'expected' not in item:
                    print(f"Data entry structural failure at position {index+1}: 'text' or 'expected' key missing.")
                    is_valid_schema = False
                    break
            
            if not is_valid_schema:
                continue

            vanilla_res, vanilla_acc, vanilla_corr = evaluate_vanilla(dataset, f"dataset_{dataset_counter}")
            hybrid_res, hybrid_acc, hybrid_corr = evaluate_hybrid(dataset, f"dataset_{dataset_counter}")

            print("\n" + "="*40)
            print("📊 EVALUATION RESULTS SUMMARY")
            print(f"🤖 IndoBERT Vanilla     : {vanilla_acc:.2f}%  ({vanilla_corr}/{len(dataset)})")
            print(f"⚙️ Tuned Hybrid Engine  : {hybrid_acc:.2f}%  ({hybrid_corr}/{len(dataset)})")
            print("="*40)

            combined_rows_data = []
            for v, h in zip(vanilla_res, hybrid_res):
                combined_rows_data.append({
                    "text": v["text"],
                    "expected": v["expected"],
                    "vanilla_label": v["vanilla_label"],
                    "vanilla_score": f"{v['vanilla_score']:.2f}",
                    "vanilla_correct": v["is_correct_vanilla"],
                    "hybrid_label": h["final_label"],
                    "hybrid_rule": h["rule"],
                    "hybrid_correct": h["is_correct_hybrid"]
                })

            all_runs_memory.append({
                "dataset_id": dataset_counter,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_tweets": len(dataset),
                "vanilla_acc": vanilla_acc,
                "vanilla_correct": vanilla_corr,
                "hybrid_acc": hybrid_acc,
                "hybrid_correct": hybrid_corr,
                "combined_rows": combined_rows_data
            })

            master_html_filename = "laporan_keseluruhan_sentimen.html"
            generate_unified_html(all_runs_memory, master_html_filename)

            print(f"📄 Dataset added to master sheet! Active items block: {len(all_runs_memory)}")
            print(f"🔗 Master dashboard generated securely at: {master_html_filename}")
            
            dataset_counter += 1

        except KeyboardInterrupt:
            print("\n\n👋 Execution stopped via user terminal command. Have a nice day!")
            break
        except Exception as e:
            print(f"An unexpected tracking anomaly occurred: {e}")

if __name__ == "__main__":
    main()