// =====================================================================
// CORE DASHBOARD SCRIPT (CLEAN ARCHITECTURE SEPARATION)
// =====================================================================
Chart.defaults.font.family = '"Plus Jakarta Sans", sans-serif';

const customCanvasBackgroundColor = {
  id: "customCanvasBackgroundColor",
  beforeDraw: (chart, args, options) => {
    const { ctx } = chart;
    ctx.save();
    ctx.globalCompositeOperation = "destination-over";
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, chart.width, chart.height);
    ctx.restore();
  },
};
Chart.register(customCanvasBackgroundColor);

function exportChart(chartId, filename) {
  const canvas = document.getElementById(chartId);
  const link = document.createElement("a");
  link.download = filename;
  link.href = canvas.toDataURL("image/png", 1.0);
  link.click();
}

let barChartInstance = null;
let barChartMode = "ratio";
let rawTweetStatsCache = [];
let deaLineChartInstance = null;
let detailDeaChartInstance = null;
let globalDashboardData = [];

async function loadNLPStats() {
  try {
    const response = await fetch("/api/stats");
    const data = await response.json();
    document.getElementById("nlp-accuracy").innerText = data.accuracy + "%";
    document.getElementById("nlp-precision").innerText = data.precision + "%";
    document.getElementById("nlp-recall").innerText = data.recall + "%";
    document.getElementById("nlp-f1").innerText = data.f1_score + "%";
    document.getElementById("dataset-info-badge").innerText =
      `Total Dataset Valid: ${data.total_data.toLocaleString("id-ID")} Opini`;
  } catch (e) {
    console.error("Gagal load NLP Stats", e);
  }
}

async function loadTweetStats() {
  try {
    const response = await fetch("/api/tweet-stats");
    const data = await response.json();
    rawTweetStatsCache = data;

    const grid = document.getElementById("tweet-grid");
    const totalBadge = document.getElementById("total-tweets-badge");
    const filterMonthSelect = document.getElementById("filter-month");

    let total = 0;
    let gridHTML = "";
    let monthOptions = '<option value="">Semua Bulan</option>';

    data.forEach((item) => {
      total += item.jumlah;
      gridHTML += `
                <div class="p-3 bg-white border border-slate-200 rounded-xl shadow-sm hover:border-indigo-200 transition">
                    <p class="text-[10px] font-bold text-slate-400 uppercase">${item.bulan}</p>
                    <p class="text-xl font-black text-slate-800 mt-0.5">${item.jumlah.toLocaleString("id-ID")}</p>
                </div>
            `;
      monthOptions += `<option value="${item.bulan}">${item.bulan}</option>`;
    });

    grid.innerHTML = gridHTML;
    totalBadge.innerHTML = `Total Dataset: <span class="text-lg">${total.toLocaleString("id-ID")}</span> Opini Publik`;
    filterMonthSelect.innerHTML = monthOptions;

    renderSentimentBarChart();
  } catch (error) {
    console.error("Failed fetch tweet stats", error);
  }
}

function toggleBarChartMode(mode) {
  barChartMode = mode;
  document.getElementById("mode-actual").className =
    mode === "actual"
      ? "px-4 py-1.5 text-xs font-bold rounded-md bg-white text-slate-800 shadow-sm transition"
      : "px-4 py-1.5 text-xs font-bold rounded-md text-slate-500 hover:text-slate-800 transition";
  document.getElementById("mode-ratio").className =
    mode === "ratio"
      ? "px-4 py-1.5 text-xs font-bold rounded-md bg-white text-slate-800 shadow-sm transition"
      : "px-4 py-1.5 text-xs font-bold rounded-md text-slate-500 hover:text-slate-800 transition";
  renderSentimentBarChart();
}

function renderSentimentBarChart() {
  const ctxBar = document.getElementById("sentimentBarChart").getContext("2d");
  if (barChartInstance) barChartInstance.destroy();

  const labels = rawTweetStatsCache.map((item) => item.bulan);
  let datasets = [];
  const barStyle = {
    borderWidth: 0,
    borderRadius: 4,
    barPercentage: 0.6,
    categoryPercentage: 0.8,
  };

  if (barChartMode === "actual") {
    datasets = [
      {
        label: "Positif",
        data: rawTweetStatsCache.map((i) => i.positif),
        backgroundColor: "#10b981",
        ...barStyle,
      },
      {
        label: "Netral",
        data: rawTweetStatsCache.map((i) => i.netral),
        backgroundColor: "#94a3b8",
        ...barStyle,
      },
      {
        label: "Negatif",
        data: rawTweetStatsCache.map((i) => i.negatif),
        backgroundColor: "#f43f5e",
        ...barStyle,
      },
    ];
  } else {
    datasets = [
      {
        label: "Positif (%)",
        data: rawTweetStatsCache.map((i) => (i.positif / i.jumlah) * 100),
        backgroundColor: "#10b981",
        ...barStyle,
      },
      {
        label: "Netral (%)",
        data: rawTweetStatsCache.map((i) => (i.netral / i.jumlah) * 100),
        backgroundColor: "#94a3b8",
        ...barStyle,
      },
      {
        label: "Negatif (%)",
        data: rawTweetStatsCache.map((i) => (i.negatif / i.jumlah) * 100),
        backgroundColor: "#f43f5e",
        ...barStyle,
      },
    ];
  }

  barChartInstance = new Chart(ctxBar, {
    type: "bar",
    data: { labels: labels, datasets: datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          stacked: true,
          grid: { display: false },
          ticks: { font: { size: 10 }, color: "#64748b", maxRotation: 45 },
        },
        y: {
          stacked: true,
          max: barChartMode === "ratio" ? 100 : undefined,
          grid: { color: "#f1f5f9", borderDash: [4, 4] },
          ticks: {
            font: { size: 10 },
            color: "#64748b",
            callback: function (val) {
              return barChartMode === "ratio"
                ? val + "%"
                : val.toLocaleString("id-ID");
            },
          },
        },
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            usePointStyle: true,
            boxWidth: 8,
            font: { size: 11, weight: "600" },
          },
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          padding: 12,
          cornerRadius: 8,
        },
      },
    },
  });
}

let isEventLineVisible = true;
let historicalEventsData = {};

async function fetchHistoricalEvents() {
  try {
    const response = await fetch("/api/events");
    historicalEventsData = await response.json();
  } catch (error) {
    console.error("Failed to fetch historical events", error);
  }
}

function generateAnnotations() {
  let chartAnnotations = {};
  Object.keys(historicalEventsData).forEach((key, index) => {
    chartAnnotations["eventLine" + index] = {
      type: "line",
      xMin: key,
      xMax: key,
      borderColor: historicalEventsData[key].color,
      borderDash: [5, 4],
      borderWidth: 1.5,
    };
  });
  return chartAnnotations;
}

function toggleEventLines() {
  if (!deaLineChartInstance) return;
  isEventLineVisible = !isEventLineVisible;
  const toggleBtn = document.getElementById("toggle-lines-btn");

  if (isEventLineVisible) {
    toggleBtn.className =
      "inline-flex items-center gap-2 px-4 py-2 bg-teal-50 text-teal-700 border border-teal-200 text-xs font-bold rounded-lg transition shadow-sm";
    toggleBtn.innerHTML = "Garis Peristiwa: ON";
    deaLineChartInstance.options.plugins.annotation.annotations =
      generateAnnotations();
  } else {
    toggleBtn.className =
      "inline-flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-500 border border-slate-200 text-xs font-bold rounded-lg transition shadow-sm";
    toggleBtn.innerHTML = "Garis Peristiwa: OFF";
    deaLineChartInstance.options.plugins.annotation.annotations = {};
  }
  deaLineChartInstance.update();
}

function exportDeaChart(withLines) {
  const originalState = isEventLineVisible;
  if (withLines !== isEventLineVisible) {
    deaLineChartInstance.options.plugins.annotation.annotations = withLines
      ? generateAnnotations()
      : {};
    deaLineChartInstance.update();
  }
  setTimeout(() => {
    const canvas = document.getElementById("deaChart");
    const link = document.createElement("a");
    link.download = `Grafik_Divergensi_DEA_${withLines ? "Dengan_Garis" : "Tanpa_Garis"}.png`;
    link.href = canvas.toDataURL("image/png", 1.0);
    link.click();
    if (withLines !== originalState) {
      deaLineChartInstance.options.plugins.annotation.annotations =
        originalState ? generateAnnotations() : {};
      deaLineChartInstance.update();
    }
  }, 300);
}

async function loadDashboard() {
  const sort = document.getElementById("sort-table").value;
  const year = document.getElementById("filter-year-table").value;

  try {
    const response = await fetch(`/api/data?sort=${sort}&year=${year}`);
    globalDashboardData = await response.json();
    if (Object.keys(historicalEventsData).length === 0)
      await fetchHistoricalEvents();
  } catch (error) {
    console.error("Failed to fetch dashboard data", error);
    return;
  }

  if (!globalDashboardData || globalDashboardData.length === 0) return;

  const labels = globalDashboardData.map((d) => d.periode);
  const scoresDEA = globalDashboardData.map((d) => d.skor_dea || 0);
  const scoresSentimen = globalDashboardData.map((d) => {
    const val =
      d.skor_sentimen !== null && d.skor_sentimen !== undefined
        ? d.skor_sentimen
        : 0.5;
    return val * 2 - 1; // Konversi ke NSS (-1 sampai 1)
  });

  const ctxLine = document.getElementById("deaChart").getContext("2d");
  if (deaLineChartInstance) deaLineChartInstance.destroy();

  let gradientDEA = ctxLine.createLinearGradient(0, 0, 0, 350);
  gradientDEA.addColorStop(0, "rgba(0, 163, 157, 0.15)");
  gradientDEA.addColorStop(1, "rgba(0, 163, 157, 0.0)");

  deaLineChartInstance = new Chart(ctxLine, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Kinerja Fundamental (DEA)",
          data: scoresDEA,
          borderColor: "#00A39D",
          backgroundColor: gradientDEA,
          borderWidth: 2.5,
          fill: true,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 6,
        },
        {
          label: "Sentimen Publik (NLP)",
          data: scoresSentimen,
          borderColor: "#F37021",
          backgroundColor: "transparent",
          borderWidth: 2.5,
          borderDash: [5, 4],
          fill: false,
          tension: 0.3,
          pointRadius: 2,
          pointHoverRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          position: "top",
          labels: {
            usePointStyle: true,
            boxWidth: 8,
            font: { size: 11, weight: "600" },
          },
        },
        annotation: {
          annotations: isEventLineVisible ? generateAnnotations() : {},
        },
        tooltip: {
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          padding: 12,
          cornerRadius: 8,
          callbacks: {
            label: (context) =>
              ` ${context.dataset.label}: ${context.raw.toFixed(4)}`,
            footer: (tooltipItems) => {
              const periode = tooltipItems[0].label;
              if (historicalEventsData[periode]) {
                const evt = historicalEventsData[periode];
                return [
                  "",
                  `📌 PERISTIWA (${evt.type.toUpperCase()}):`,
                  evt.title,
                  "",
                  `⚡ DAMPAK VARIABEL:`,
                  evt.impact,
                ];
              }
              return null;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { font: { size: 10 }, color: "#64748b", maxRotation: 45 },
        },
        y: {
          min: -1.0,
          max: 1.1,
          grid: { color: "#f1f5f9", borderDash: [4, 4] },
          ticks: { font: { size: 10 }, color: "#64748b", stepSize: 0.2 },
        },
      },
    },
  });

  const tableBody = document.getElementById("dashboard-table-body");
  let tableHTML = "";

  globalDashboardData.forEach((row) => {
    // Ambil skor sentimen (default 0.5 jika null)
    const sentimenVal = row.skor_sentimen !== null ? row.skor_sentimen : 0.5;

    // Konversi skor (0 s/d 1) kembali menjadi NSS (-1 s/d 1)
    const nss = (sentimenVal * 2 - 1).toFixed(4);

    // Warna dinamis: Merah (negatif), Hijau (positif), Abu-abu (netral)
    const nssColor =
      nss < 0
        ? "text-rose-600"
        : nss > 0
          ? "text-emerald-600"
          : "text-slate-500";

    tableHTML += `
            <tr class="hover:bg-teal-50 cursor-pointer transition duration-150" onclick="openDeaModal('${row.periode}')">
                <td class="py-3.5 px-6 text-sm font-bold text-slate-700">${row.periode}</td>
                <td class="py-3.5 px-6 text-sm font-mono text-teal-700 font-bold text-right">${row.skor_dea.toFixed(4)}</td>
                <td class="py-3.5 px-6 text-sm font-mono text-orange-600 font-bold text-right">${sentimenVal.toFixed(4)}</td>
                <td class="py-3.5 px-6 text-sm font-mono text-right bg-amber-50/30 font-bold border-l border-slate-100 ${nssColor}">${nss}</td>
            </tr>
        `;
  });
  tableBody.innerHTML = tableHTML;
}

function formatRupiah(number) {
  if (number === undefined || number === null) return "-";
  let inMiliar = number / 1000000000;
  return (
    "Rp " +
    inMiliar.toLocaleString("id-ID", { maximumFractionDigits: 0 }) +
    " M"
  );
}

function openDeaModal(periode) {
  const rowData = globalDashboardData.find((d) => d.periode === periode);
  if (!rowData) return;
  document.getElementById("modal-title").innerText =
    `Rincian Variabel DEA - ${periode}`;
  document.getElementById("modal-skor-dea").innerText = rowData.skor_dea
    ? rowData.skor_dea.toFixed(4)
    : "-";
  document.getElementById("modal-dpk").innerText = formatRupiah(
    rowData.dpk_input,
  );
  document.getElementById("modal-pembiayaan").innerText = formatRupiah(
    rowData.pembiayaan_output,
  );
  document.getElementById("modal-bopo").innerText = formatRupiah(
    rowData.beban_operasional_input,
  );

  const ctxDetail = document.getElementById("deaDetailChart").getContext("2d");
  if (detailDeaChartInstance) detailDeaChartInstance.destroy();
  detailDeaChartInstance = new Chart(ctxDetail, {
    type: "bar",
    data: {
      labels: [
        "DPK (Input)",
        "Beban Personel",
        "Beban Operasional",
        "Pembiayaan (Output)",
        "Pendapatan (Output)",
      ],
      datasets: [
        {
          data: [
            rowData.dpk_input || 0,
            rowData.beban_personel_input || 0,
            rowData.beban_operasional_input || 0,
            rowData.pembiayaan_output || 0,
            rowData.pendapatan_output || 0,
          ],
          backgroundColor: [
            "#f43f5e",
            "#f43f5e",
            "#f43f5e",
            "#10b981",
            "#10b981",
          ],
          borderRadius: 4,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { font: { size: 10 } } },
        y: {
          type: "logarithmic",
          ticks: {
            callback: function (value) {
              return formatRupiah(value);
            },
            font: { size: 10 },
          },
        },
      },
    },
  });
  document.getElementById("deaModal").classList.add("modal-active");
}

function closeDeaModal() {
  document.getElementById("deaModal").classList.remove("modal-active");
}
let currentTopWord = [];
async function loadWordCloud() {
    const month = document.getElementById("filter-month").value;
    const label = document.getElementById("filter-label").value;
    try {
        const res = await fetch(`/api/word-freq?month=${month}&label=${label}`);
        const data = await res.json();
        const canvas = document.getElementById("wordCloudCanvas");
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // --- LOGIKA BARU: TANGKAP 10 KATA TERATAS ---
        const btnCopyTop = document.getElementById('btn-copy-top-word');
        if (data && data.length > 0) {
            // Ambil maksimal 10 kata urutan pertama
            topWordsList = data.slice(0, 10).map(item => item.word); 
            
            btnCopyTop.classList.remove('hidden'); 
            btnCopyTop.innerHTML = `
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
                Salin Sampel 10 Topik
            `;
        } else {
            topWordsList = [];
            btnCopyTop.classList.add('hidden'); 
        }
        // ---------------------------------------------

        if (!data || data.length === 0) {
            ctx.font = "12px sans-serif";
            ctx.fillStyle = "#94a3b8";
            ctx.textAlign = "center";
            ctx.fillText(
                "Tidak cukup data ulasan teks",
                canvas.width / 2,
                canvas.height / 2,
            );
            return;
        }
        const maxWeight = Math.max(...data.map((d) => d.weight));
        const listData = data.map((item) => [
            item.word,
            (item.weight / maxWeight) * 46 + 14,
        ]);

        WordCloud(canvas, {
            list: listData,
            fontFamily: '"Plus Jakarta Sans", sans-serif',
            fontWeight: "bold",
            color: function () {
                if (label === "negative") return Math.random() > 0.5 ? "#f43f5e" : "#be123c";
                if (label === "positive") return Math.random() > 0.5 ? "#10b981" : "#047857";
                return Math.random() > 0.5 ? "#64748b" : "#334155";
            },
            backgroundColor: "transparent",
            rotateRatio: 0.3,
            gridSize: 8,
            shrinkToFit: true,
            drawOutOfBound: false,
        });
    } catch (e) {
        console.error("Gagal load wordcloud", e);
    }
}

// Tambahkan fungsi ini untuk mengatasi error fallbackCopyTextToClipboard
function fallbackCopyTextToClipboard(text) {
    const textArea = document.createElement("textarea");
    textArea.value = text;
    // Hindari scroll ke bawah
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        const successful = document.execCommand('copy');
        if (successful) {
            alert(`✅ Berhasil menyalin sampel untuk ${topWordsList.length} topik teratas! (Mode Fallback)`);
        } else {
            alert("Gagal menyalin otomatis. Silakan coba lagi.");
        }
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
        alert("Terjadi kesalahan saat menyalin data.");
    }

    document.body.removeChild(textArea);
}

async function copyTopWordTweets() {
    if (!topWordsList || topWordsList.length === 0) {
        alert("Tidak ada topik untuk disalin.");
        return;
    }

    const btn = document.getElementById('btn-copy-top-word');
    const originalText = btn.innerHTML;
    btn.innerHTML = "Menyalin Data...";
    btn.disabled = true;

    const month = document.getElementById("filter-month").value;
    const label = document.getElementById("filter-label").value;

    try {
        let copyText = `========== SAMPEL 10 TOPIK TERATAS ==========\n`;
        copyText += `Filter -> Bulan: ${month || 'Semua Periode'}, Sentimen: ${label || 'Semua Sentimen'}\n\n`;

        // Lakukan perulangan untuk menarik 1 tweet dari setiap 10 kata teratas
        // Menggunakan Promise.all agar fetch berjalan paralel & cepat
        const fetchPromises = topWordsList.map(async (word, index) => {
            const response = await fetch(`/api/tweets?page=1&limit=1&month=${month}&label=${label}&search=${encodeURIComponent(word)}`);
            const resData = await response.json();
            return { word: word, rank: index + 1, tweets: resData.data };
        });

        const results = await Promise.all(fetchPromises);

        // Susun teks dari hasil yang sudah ditangkap
        results.forEach(res => {
            copyText += `[Peringkat ${res.rank}: Kata "${res.word.toUpperCase()}"]\n`;
            
            if (res.tweets && res.tweets.length > 0) {
                const tweet = res.tweets[0]; // Ambil cuitan pertama
                const dateObj = new Date(tweet.date);
                const formattedDate = dateObj.toLocaleDateString("id-ID", { year: "numeric", month: "short", day: "numeric" });
                const sentimen = tweet.label ? tweet.label.toUpperCase() : "UNLABELED";
                
                copyText += `Tgl: ${formattedDate} | Label: ${sentimen}\n"${tweet.content}"\n\n`;
            } else {
                copyText += `(Tidak menemukan sampel cuitan utuh untuk kata ini)\n\n`;
            }
        });

        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(copyText);
            alert(`✅ Berhasil menyalin sampel untuk ${topWordsList.length} topik teratas!`);
        } else {
            fallbackCopyTextToClipboard(copyText);
        }
    } catch (error) {
        console.error("Gagal menyalin tweet", error);
        alert("Gagal menarik data dari server. Silakan coba lagi.");
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

let currentTweetPage = 1;
const tweetsLimit = 1000;
function resetAndFetchTweets() {
  currentTweetPage = 1;
  fetchRawTweets();
}
function changePage(direction) {
  currentTweetPage += direction;
  fetchRawTweets();
}

async function fetchRawTweets() {
  const tbody = document.getElementById("raw-tweets-body");
  const month = document.getElementById("filter-month").value;
  const label = document.getElementById("filter-label").value;
  const search = document.getElementById("search-tweet").value;

  try {
    const response = await fetch(
      `/api/tweets?page=${currentTweetPage}&limit=${tweetsLimit}&month=${month}&label=${label}&search=${encodeURIComponent(search)}`,
    );
    const resData = await response.json();
    let html = "";
    resData.data.forEach((tweet) => {
      let badgeClass =
        tweet.label === "negative"
          ? "bg-rose-50 text-rose-700 border-rose-200"
          : tweet.label === "positive"
            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
            : "bg-slate-100 text-slate-600 border-slate-200";
      const dateObj = new Date(tweet.date);
      const formattedDate = dateObj.toLocaleDateString("id-ID", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
      html += `
                <tr>
                    <td class="py-3 px-6 text-xs text-slate-500 whitespace-nowrap">${formattedDate}</td>
                    <td class="py-3 px-6 text-sm text-slate-800 leading-relaxed">${tweet.content}</td>
                    <td class="py-3 px-6 text-center"><span class="inline-flex px-2.5 py-1 rounded border text-[10px] font-bold uppercase ${badgeClass}">${tweet.label || "NULL"}</span></td>
                </tr>
            `;
    });
    tbody.innerHTML =
      html ||
      '<tr><td colspan="3" class="text-center py-10 text-slate-400">Data tidak ditemukan</td></tr>';

    document.getElementById("pagination-info").innerHTML =
      `Halaman <strong>${resData.page}</strong> dari <strong>${resData.total_pages}</strong>`;
    document.getElementById("btn-prev-tweet").disabled = resData.page <= 1;
    document.getElementById("btn-next-tweet").disabled =
      resData.page >= resData.total_pages || resData.total_pages === 0;
  } catch (e) {}
}

const simulatorModal = document.getElementById("simulatorModal");
const inputSimulator = document.getElementById("simulator-input");
const btnRunAnalyzer = document.getElementById("btn-run-analyzer");
const resultContainer = document.getElementById("simulator-result-container");

function toggleSimulatorModal(isVisible) {
  if (isVisible) {
    simulatorModal.classList.add("modal-active");
    inputSimulator.focus();
  } else {
    simulatorModal.classList.remove("modal-active");
    inputSimulator.value = "";
    resultContainer.classList.add("hidden");
  }
}

async function executeLiveAnalysis() {
  const payloadText = inputSimulator.value.trim();
  if (!payloadText) return;
  btnRunAnalyzer.disabled = true;
  btnRunAnalyzer.innerHTML = "Memproses...";
  try {
    const response = await fetch("/api/test-analyzer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: payloadText }),
    });
    const data = await response.json();
    if (response.ok) {
      resultContainer.classList.remove("hidden");
      const formatBadge = (label) => {
        if (label === "positive")
          return "bg-emerald-50 text-emerald-700 border-emerald-200";
        if (label === "negative")
          return "bg-rose-50 text-rose-700 border-rose-200";
        return "bg-slate-100 text-slate-600 border-slate-200";
      };
      const aiLabelEl = document.getElementById("res-ai-label");
      aiLabelEl.className = `inline-flex px-2.5 py-1 rounded border text-xs font-bold uppercase ${formatBadge(data.ai_label)}`;
      aiLabelEl.innerText = data.ai_label;
      document.getElementById("res-ai-score").innerText =
        `Confidence: ${(data.confidence_score * 100).toFixed(2)}%`;

      const finalLabelEl = document.getElementById("res-final-label");
      finalLabelEl.className = `inline-flex px-3 py-1.5 rounded border text-sm font-black uppercase mb-3 shadow-sm ${formatBadge(data.final_label)}`;
      finalLabelEl.innerText = data.final_label;
      document.getElementById("res-applied-rule").innerText = data.applied_rule;
    } else {
      alert("Analysis failed: " + data.error);
    }
  } catch (error) {
    alert("Gagal menghubungi server NLP.");
  } finally {
    btnRunAnalyzer.disabled = false;
    btnRunAnalyzer.innerHTML = "Analisis Teks";
  }
}

async function generateAnalysisCharts() {
  const statusRegresi = document.getElementById("status-text-regresi");
  const progressRegresi = document.getElementById("progress-bar-regresi");
  const statusSVM = document.getElementById("status-text-svm");
  const progressSVM = document.getElementById("progress-bar-svm");

  // Daftar tahapan proses agar user tahu apa yang sedang dikerjakan server
  const steps = [
    { text: "Mengambil data sentimen & DEA...", progress: "25%" },
    { text: "Menghitung regresi OLS & P-Value...", progress: "45%" },
    { text: "Ekstraksi fitur TF-IDF (1.500 cuitan)...", progress: "65%" },
    { text: "Mereduksi dimensi (PCA) & melatih SVM...", progress: "85%" },
    { text: "Merender visualisasi grafik...", progress: "95%" },
  ];

  let currentStep = 0;

  // Ubah status dan perpanjang progress bar setiap 2,5 detik
  const stepInterval = setInterval(() => {
    currentStep = (currentStep + 1) % steps.length;
    if (statusRegresi && progressRegresi) {
      statusRegresi.innerText = steps[currentStep].text;
      progressRegresi.style.width = steps[currentStep].progress;
    }
    if (statusSVM && progressSVM) {
      statusSVM.innerText = steps[currentStep].text;
      progressSVM.style.width = steps[currentStep].progress;
    }
  }, 2500);

  try {
    const response = await fetch("/api/generate-analysis-charts");
    const data = await response.json();

    // Hentikan animasi loading jika server sudah selesai menjawab
    clearInterval(stepInterval);

    if (data.status === "success") {
      // Tampilkan Gambar Regresi
      const imgRegresi = document.getElementById("img-regresi");
      imgRegresi.src = data.regresi;
      imgRegresi.classList.remove("hidden");
      document.getElementById("loader-regresi").classList.add("hidden");
      document.getElementById("btn-download-regresi").href = data.regresi;

      // Tampilkan Gambar SVM
      const imgSVM = document.getElementById("img-svm");
      imgSVM.src = data.svm;
      imgSVM.classList.remove("hidden");
      document.getElementById("loader-svm").classList.add("hidden");
      document.getElementById("btn-download-svm").href = data.svm;

      // Tampilkan tabel statistik regresi jika ada
      if (data.stats && data.stats.overall) {
        const statData = data.stats.overall;
        document
          .getElementById("regression-stats-container")
          .classList.remove("hidden");
        document.getElementById("stat-r2").innerText = statData.r2;
        document.getElementById("stat-slope").innerText =
          statData.koefisien_slope;
        document.getElementById("stat-pvalue").innerText =
          statData.p_value_slope;

        const sigElem = document.getElementById("stat-sig");
        if (statData.signifikan_5persen) {
          sigElem.innerHTML =
            '<span class="text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">Signifikan</span>';
        } else {
          sigElem.innerHTML =
            '<span class="text-rose-500 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">Tdk Signifikan</span>';
        }
      }
    }
  } catch (e) {
    clearInterval(stepInterval);
    console.error("Gagal men-generate gambar analisis", e);
    if (statusRegresi) statusRegresi.innerText = "Gagal memuat visualisasi.";
    if (statusSVM) statusSVM.innerText = "Gagal memuat visualisasi.";
  }
}
document.addEventListener("DOMContentLoaded", () => {
  document
    .getElementById("btn-open-simulator")
    .addEventListener("click", () => toggleSimulatorModal(true));
  document
    .getElementById("btn-close-simulator")
    .addEventListener("click", () => toggleSimulatorModal(false));
  btnRunAnalyzer.addEventListener("click", executeLiveAnalysis);

  loadNLPStats();
  loadTweetStats();
  loadDashboard();
  fetchRawTweets();
  setTimeout(loadWordCloud, 1000);
  generateAnalysisCharts();
});