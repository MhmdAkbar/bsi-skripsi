// ==========================================
// 1. DATA ACCESS LAYER (API)
// ==========================================
class APIService {
  static async fetchDatasets() {
    const response = await fetch("/api/datasets");
    return await response.json();
  }

  static async fetchMonths() {
    const response = await fetch("/api/tweet-stats");
    return await response.json();
  }

  static async saveDataset(payload, isUpdate) {
    const method = isUpdate ? "PUT" : "POST";
    const response = await fetch("/api/datasets", {
      method: method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    return await response.json();
  }

  static async deleteDataset(id) {
    const response = await fetch(`/api/datasets/${id}`, { method: "DELETE" });
    return await response.json();
  }

  static async fetchRawTweets(page, limit, filters, datasetId) {
    let url = `/api/tweets?page=${page}&limit=${limit}&assignment=unassigned`;
    if (datasetId) url += `&dataset_target=${datasetId}`;
    if (filters.search) url += `&search=${encodeURIComponent(filters.search)}`;
    if (filters.status) url += `&label_status=${filters.status}`;
    if (filters.month) url += `&month=${filters.month}`;

    const response = await fetch(url);
    return await response.json();
  }

  static async executeAccuracyTest(datasetId) {
    const response = await fetch("/api/run-accuracy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_id: datasetId }),
    });
    return await response.json();
  }

  static async executeAccuracyTestAll() {
    const response = await fetch("/api/run-accuracy-all", {
      method: "POST"
    });
    return await response.json();
  }
} // <-- Missing brace restored here

// ==========================================
// 2. STATE MANAGEMENT LAYER (LOGIC)
// ==========================================
class AppState {
  constructor() {
    this.datasets = [];
    this.rawTweets = [];
    this.pagination = { current: 1, limit: 50, totalPages: 1 };
    this.filters = { search: "", status: "", month: "" };
    
    // Stores raw data totals per month
    this.rawMonthTotals = {}; 

    this.editorSession = {
      id: null,
      name: "",
      description: "",
      labeledData: new Map(),
    };
  }

  setDatasets(data) {
    this.datasets = data;
  }

  setRawTweets(data, pageData) {
    this.rawTweets = data;
    this.pagination.current = pageData.page;
    this.pagination.totalPages = pageData.total_pages;
  }

  // Store overall database statistics
  setMonthStats(stats) {
    this.rawMonthTotals = {};
    const monthNames = [
      "Januari", "Februari", "Maret", "April", "Mei", "Juni",
      "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ];
    
    stats.forEach((stat) => {
      if (stat.bulan) {
        const [year, month] = stat.bulan.split("-");
        const periodKey = `${monthNames[parseInt(month) - 1]} ${year}`;
        this.rawMonthTotals[periodKey] = stat.jumlah;
      }
    });
  }

  loadExistingData(rawData) {
    if (!rawData) return;
    try {
      const parsedData = typeof rawData === "string" ? JSON.parse(rawData) : rawData;
      if (Array.isArray(parsedData)) {
        parsedData.forEach((item) => {
          const tweetText = item.text || item.content || "";
          this.assignLabel(
            String(item.id),
            tweetText,
            item.expected,
            item.created_at,
          );
        });
      }
    } catch (e) {
      console.error("Critical error while recovering dataset memory state:", e);
    }
  }

  updateEditorField(field, value) {
    this.editorSession[field] = value;
  }

  assignLabel(tweetId, text, label, createdAt) {
    if (!label) {
      this.editorSession.labeledData.delete(String(tweetId));
    } else {
      this.editorSession.labeledData.set(String(tweetId), {
        id: tweetId,
        text: text,
        expected: label,
        created_at: createdAt,
      });
    }
  }

  getLabeledCount() {
    return this.editorSession.labeledData.size;
  }

  generateDatasetPayload() {
    const dataArray = Array.from(this.editorSession.labeledData.values());
    const payload = {
      nama_dataset: this.editorSession.name,
      deskripsi: this.editorSession.description,
      data: dataArray,
    };
    if (this.editorSession.id) payload.id = this.editorSession.id;
    return payload;
  }

  resetEditor() {
    this.editorSession.id = null;
    this.editorSession.name = "";
    this.editorSession.description = "";
    this.editorSession.labeledData.clear();
    this.pagination.current = 1;
    this.filters = { search: "", status: "", month: "" };
  }
}

// ==========================================
// 3. PRESENTATION LAYER (UI)
// ==========================================
class UIRenderer {
  static switchView(viewName) {
    document.getElementById("view-dataset-list").classList.add("view-hidden");
    document.getElementById("view-dataset-editor").classList.add("view-hidden");

    if (viewName === "list")
      document.getElementById("view-dataset-list").classList.remove("view-hidden");
    if (viewName === "editor")
      document.getElementById("view-dataset-editor").classList.remove("view-hidden");
  }

  static setGlobalTestButtonState(isProcessing, progressText = "Test All Datasets") {
    const btn = document.getElementById("btn-test-all");
    if (!btn) return;
    
    btn.disabled = isProcessing;
    btn.innerHTML = isProcessing 
      ? `<svg class="animate-spin w-5 h-5 md:w-4 md:h-4 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> ${progressText}`
      : `<svg class="w-5 h-5 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"></path></svg> Test All Datasets`;
  }

  // Calculate DB availability progress and dataset portion
  static renderSessionStats(labeledMap, rawMonthTotals) {
    const container = document.getElementById("session-stats-content");
    container.innerHTML = "";

    const totalSessionLabeled = labeledMap.size;

    if (totalSessionLabeled === 0) {
      container.innerHTML = `<div class="p-4 text-center text-sm text-slate-500 font-medium">Belum ada data yang dilabeli.</div>`;
      return;
    }

    const sessionStats = {};
    const monthNames = [
      "Januari", "Februari", "Maret", "April", "Mei", "Juni",
      "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ];

    // Group current editor session data by month
    labeledMap.forEach((item) => {
      let periodKey = "Periode Tidak Diketahui";
      if (item.created_at) {
        const dateStr = item.created_at.replace(" ", "T");
        const dateObj = new Date(dateStr);
        if (!isNaN(dateObj.getTime())) {
          periodKey = `${monthNames[dateObj.getMonth()]} ${dateObj.getFullYear()}`;
        }
      }
      sessionStats[periodKey] = (sessionStats[periodKey] || 0) + 1;
    });

    // Render HTML with calculations
    for (const [period, countLabeled] of Object.entries(sessionStats)) {
      
      // Calculation 1: Portion in dataset (count / total session)
      const portionPercentage = ((countLabeled / totalSessionLabeled) * 100).toFixed(1);

      // Calculation 2: Monthly progress (count / total raw database)
      const rawTotalForMonth = rawMonthTotals[period] || 0;
      let progressPercentage = "0";
      let rawRatioText = `(0/0)`;

      if (rawTotalForMonth > 0) {
        progressPercentage = ((countLabeled / rawTotalForMonth) * 100).toFixed(1);
        rawRatioText = `(${countLabeled}/${rawTotalForMonth})`;
      } else if (period === "Periode Tidak Diketahui") {
        progressPercentage = "N/A";
        rawRatioText = "";
      }

      const el = document.createElement("div");
      el.className = "flex flex-col gap-2 p-3 hover:bg-slate-50 rounded-xl transition-colors border-b border-slate-100 last:border-0";
      el.innerHTML = `
            <div class="flex justify-between items-center">
                <span class="font-bold text-sm text-slate-800">${period}</span>
                <span class="text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-100 px-2.5 py-0.5 rounded-lg shadow-sm">${countLabeled} Labeled</span>
            </div>
            <div class="flex flex-col gap-1 mt-1">
                <div class="flex justify-between items-center text-xs">
                    <span class="text-slate-500 font-medium">Progress Bulanan</span>
                    <span class="font-semibold text-sky-600">${progressPercentage}% <span class="text-slate-400 font-normal ml-0.5">${rawRatioText}</span></span>
                </div>
                <div class="flex justify-between items-center text-xs">
                    <span class="text-slate-500 font-medium">Porsi di Dataset</span>
                    <span class="font-semibold text-indigo-600">${portionPercentage}% <span class="text-slate-400 font-normal ml-0.5">dari total sesi</span></span>
                </div>
            </div>
        `;
      container.appendChild(el);
    }
  }

  static populateMonthFilter(stats) {
    const select = document.getElementById("filter-month");
    select.innerHTML = '<option value="">Semua Periode</option>';
    const monthNames = [
      "Januari", "Februari", "Maret", "April", "Mei", "Juni",
      "Juli", "Agustus", "September", "Oktober", "November", "Desember",
    ];

    stats.forEach((stat) => {
      if (stat.bulan) {
        const opt = document.createElement("option");
        opt.value = stat.bulan;
        const [year, month] = stat.bulan.split("-");
        opt.textContent = `${monthNames[parseInt(month) - 1]} ${year}`;
        select.appendChild(opt);
      }
    });
  }

  static renderDatasetTable(datasets, onDelete, onEdit, onTest) {
    const tbody = document.getElementById("dataset-table-body");
    const template = document.getElementById("tpl-dataset-row");
    tbody.innerHTML = "";

    if (datasets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" class="py-6 text-center text-slate-400">Belum ada dataset.</td></tr>`;
      return;
    }

    datasets.forEach((ds) => {
      const clone = template.content.cloneNode(true);

      clone.querySelector(".row-name").textContent = ds.nama_dataset;
      clone.querySelector(".row-desc").textContent = ds.deskripsi || "-";
      clone.querySelector(".row-date").textContent = ds.created_at;

      clone.querySelector(".btn-test").addEventListener("click", (e) => onTest(ds.id, e.target));
      clone.querySelector(".btn-edit").addEventListener("click", () => onEdit(ds));
      clone.querySelector(".btn-delete").addEventListener("click", () => onDelete(ds.id));

      tbody.appendChild(clone);
    });
  }

  static renderAnnotationTable(tweets, activeLabelsMap, onLabelChange) {
    const tbody = document.getElementById("annotation-table-body");
    const template = document.getElementById("tpl-annotation-row");
    tbody.innerHTML = "";

    if (tweets.length === 0) {
      tbody.innerHTML = `<tr><td colspan="3" class="py-8 text-center text-slate-400">Data tidak ditemukan atau sudah dilabeli semua.</td></tr>`;
      return;
    }

    tweets.forEach((tweet) => {
      const strId = String(tweet.id);
      const clone = template.content.cloneNode(true);

      clone.querySelector(".row-id").textContent = tweet.id;
      clone.querySelector(".row-content").textContent = tweet.content;

      const existingRecord = activeLabelsMap.get(strId);
      const radios = clone.querySelectorAll(".label-radio");

      radios.forEach((radio) => {
        radio.name = `label-${strId}`;

        if (existingRecord && radio.value === existingRecord.expected) {
          radio.checked = true;
        }

        radio.addEventListener("change", (e) => {
          if (e.target.checked) {
            // Append tweet.date as the final argument
            onLabelChange(strId, tweet.content, e.target.value, tweet.date);
          }
        });
      });

      tbody.appendChild(clone);
    });
  }

static updatePagination(current, total) {
    const inputJump = document.getElementById("input-page-jump");
    const totalSpan = document.getElementById("page-total");
    
    inputJump.value = current;
    inputJump.max = total; // Set batas maksimal input
    totalSpan.innerText = total;
    
    document.getElementById("btn-prev-page").disabled = current <= 1;
    document.getElementById("btn-next-page").disabled = current >= total;
  }

  static updateLabelCounter(count) {
    document.getElementById("label-counter-text").innerText = `${count} Data Labeled`;
  }

  static syncEditorInputs(session) {
    document.getElementById("input-dataset-name").value = session.name;
    document.getElementById("input-dataset-desc").value = session.description;
    document.getElementById("filter-search").value = "";
    document.getElementById("filter-status").value = "";
    document.getElementById("filter-month").value = "";
  }
}

// ==========================================
// 4. APPLICATION CONTROLLER (WIRING)
// ==========================================
const state = new AppState();

const Controller = {
  async initialize() {
    this.bindGlobalEvents();
    await this.loadDependencies();
    await this.loadDatasetList();
  },

  async loadDependencies() {
    const stats = await APIService.fetchMonths();
    // Save total stats to internal state memory
    state.setMonthStats(stats); 
    UIRenderer.populateMonthFilter(stats);
  },

  bindGlobalEvents() {
    const btnLabelCounter = document.getElementById("btn-label-counter");
    const sessionStatsDropdown = document.getElementById("session-stats-dropdown");

    // Handle stats dropdown trigger
    btnLabelCounter.addEventListener("click", (e) => {
      e.stopPropagation();
      // Pass session and database memory to UI layer
      UIRenderer.renderSessionStats(state.editorSession.labeledData, state.rawMonthTotals);
      sessionStatsDropdown.classList.toggle("hidden");
    });

    document.addEventListener("click", (e) => {
      if (!sessionStatsDropdown.contains(e.target) && !btnLabelCounter.contains(e.target)) {
        sessionStatsDropdown.classList.add("hidden");
      }
    });

    document.getElementById("btn-show-manager").addEventListener("click", () => {
      UIRenderer.switchView("list");
      this.loadDatasetList();
    });

    document.getElementById("btn-test-all").addEventListener("click", () => this.handleRunTestAll());

    document.getElementById("btn-create-dataset").addEventListener("click", () => {
      state.resetEditor();
      UIRenderer.syncEditorInputs(state.editorSession);
      UIRenderer.updateLabelCounter(0);
      UIRenderer.switchView("editor");
      this.loadRawTweets();
    });

    document.getElementById("input-dataset-name").addEventListener("input", (e) =>
      state.updateEditorField("name", e.target.value)
    );
    
    document.getElementById("input-dataset-desc").addEventListener("input", (e) =>
      state.updateEditorField("description", e.target.value)
    );

    document.getElementById("filter-search").addEventListener("keyup", (e) => {
      if (e.key === "Enter") {
        state.filters.search = e.target.value;
        state.pagination.current = 1;
        this.loadRawTweets();
      }
    });

    document.getElementById("filter-status").addEventListener("change", (e) => {
      state.filters.status = e.target.value;
      state.pagination.current = 1;
      this.loadRawTweets();
    });

    document.getElementById("filter-month").addEventListener("change", (e) => {
      state.filters.month = e.target.value;
      state.pagination.current = 1;
      this.loadRawTweets();
    });

    document.getElementById("btn-save-dataset").addEventListener("click", () => this.handleSaveDataset());

    document.getElementById("btn-copy-summary").addEventListener("click", () => {
      const datasetItems = Array.from(state.editorSession.labeledData.values());
      handleCopyDistribution(datasetItems, "summary");
    });

    document.getElementById("btn-copy-full").addEventListener("click", () => {
      const datasetItems = Array.from(state.editorSession.labeledData.values());
      handleCopyDistribution(datasetItems, "full");
    });

    document.getElementById("btn-copy-all-stats").addEventListener("click", async () => {
      const stats = await APIService.fetchMonths();
      handleCopyAllStats(stats);
    });
    // --- FITUR LOMPAT HALAMAN ---
    document.getElementById("input-page-jump").addEventListener("change", (e) => {
      let newPage = parseInt(e.target.value);
      const maxPage = parseInt(e.target.max) || 1;
      
      // Validasi agar input tidak ngaco (dibawah 1 atau melebihi batas akhir)
      if (isNaN(newPage) || newPage < 1) newPage = 1;
      if (newPage > maxPage) newPage = maxPage;
      
      e.target.value = newPage; // Kembalikan ke angka valid jika user iseng ketik huruf/minus
      
      if (state.pagination.current !== newPage) {
        state.pagination.current = newPage;
        this.loadRawTweets(); // Panggil ulang data dari API
      }
    });

    // Pertahankan prev & next yang lama
    document.getElementById("btn-prev-page").addEventListener("click", () => this.changePage(-1));
    document.getElementById("btn-next-page").addEventListener("click", () => this.changePage(1));
    document.getElementById("btn-prev-page").addEventListener("click", () => this.changePage(-1));
    document.getElementById("btn-next-page").addEventListener("click", () => this.changePage(1));
  },

  async loadDatasetList() {
    
    try {
      const data = await APIService.fetchDatasets();
      state.setDatasets(data);
      UIRenderer.renderDatasetTable(
        state.datasets,
        this.handleDeleteDataset.bind(this),
        this.handleEditDataset.bind(this),
        this.handleRunTest.bind(this),
      );
    } catch (error) {
      console.error("Failed to load datasets", error);
    }
  },

  async handleEditDataset(dataset) {
    state.resetEditor();
    state.editorSession.id = dataset.id;
    state.editorSession.name = dataset.nama_dataset;
    state.editorSession.description = dataset.deskripsi || "";

    state.loadExistingData(dataset.data);

    UIRenderer.syncEditorInputs(state.editorSession);
    UIRenderer.updateLabelCounter(state.getLabeledCount());
    UIRenderer.switchView("editor");
    await this.loadRawTweets();
  },

  async loadRawTweets() {
    try {
      const data = await APIService.fetchRawTweets(
        state.pagination.current,
        state.pagination.limit,
        state.filters,
        state.editorSession.id,
      );

      state.setRawTweets(data.data, data);

      UIRenderer.renderAnnotationTable(
        state.rawTweets,
        state.editorSession.labeledData,
        this.handleLabelAssignment.bind(this),
      );
      UIRenderer.updatePagination(state.pagination.current, state.pagination.totalPages);
      UIRenderer.updateLabelCounter(state.getLabeledCount());
    } catch (error) {
      console.error("Failed to fetch raw tweets", error);
    }
  },

  handleLabelAssignment(tweetId, text, label, createdAt) {
    state.assignLabel(tweetId, text, label, createdAt);
    UIRenderer.updateLabelCounter(state.getLabeledCount());
  },

  async handleSaveDataset() {
    if (!state.editorSession.name.trim()) {
      alert("Nama Dataset wajib diisi!");
      return;
    }
    if (state.getLabeledCount() === 0 && !state.editorSession.id) {
      alert("Harap berikan label minimal pada 1 data sebelum menyimpan dataset baru.");
      return;
    }

    try {
      const payload = state.generateDatasetPayload();
      const isUpdate = !!state.editorSession.id;
      await APIService.saveDataset(payload, isUpdate);

      alert(isUpdate ? "Perubahan Dataset berhasil disimpan!" : "Dataset baru berhasil dibuat!");
      UIRenderer.switchView("list");
      await this.loadDatasetList();
    } catch (error) {
      alert("Terjadi kesalahan saat menyimpan dataset.");
    }
  },

  async handleDeleteDataset(id) {
    if (confirm("Apakah Anda yakin ingin menghapus dataset ini? Label data di dalamnya akan dikembalikan ke status 'Unassigned'.")) {
      await APIService.deleteDataset(id);
      this.loadDatasetList();
    }
  },

  async handleRunTest(datasetId, buttonElement) {
    const originalText = buttonElement.innerText;
    buttonElement.innerText = "Memproses...";
    buttonElement.disabled = true;

    const progressInterval = setInterval(async () => {
      try {
        const res = await fetch("/api/accuracy-progress");
        const data = await res.json();
        if (data.is_running && data.total > 0)
          buttonElement.innerText = `${data.current} / ${data.total}`;
      } catch (e) {}
    }, 500);

    try {
      const result = await APIService.executeAccuracyTest(datasetId);
      if (result.error) throw new Error(result.error);

      clearInterval(progressInterval);
      window.open("/accuracy-report", "_blank");
    } catch (error) {
      clearInterval(progressInterval);
      alert(`Pengujian Gagal: ${error.message}`);
    } finally {
      clearInterval(progressInterval);
      buttonElement.innerText = originalText;
      buttonElement.disabled = false;
    }
  },

  async handleRunTestAll() {
    UIRenderer.setGlobalTestButtonState(true, "Initializing...");

    const progressInterval = setInterval(async () => {
      try {
        const res = await fetch("/api/accuracy-progress");
        const data = await res.json();
        if (data.is_running && data.total > 0) {
          UIRenderer.setGlobalTestButtonState(true, `Processing ${data.current} / ${data.total}`);
        }
      } catch (e) {
        console.warn("Failed to fetch progress tracker.");
      }
    }, 500);

    try {
      const result = await APIService.executeAccuracyTestAll();
      if (result.error) throw new Error(result.error);

      clearInterval(progressInterval);
      window.open("/accuracy-report", "_blank");
    } catch (error) {
      clearInterval(progressInterval);
      alert(`Macro Evaluation Failed: ${error.message}`);
    } finally {
      clearInterval(progressInterval);
      UIRenderer.setGlobalTestButtonState(false);
    }
  }, 

  changePage(direction) {
    state.pagination.current += direction;
    this.loadRawTweets();
  },
};

// ==========================================
// 5. UTILITIES (COPY DISTRIBUTION)
// ==========================================
function handleCopyDistribution(datasetItems, mode = "full") {
  if (!datasetItems || datasetItems.length === 0) {
    alert("Belum ada data yang dilabeli di dataset ini.");
    return;
  }

  const distributionMap = {};

  datasetItems.forEach((item) => {
    const safeDateStr = item.created_at ? item.created_at.replace(" ", "T") : "";
    const itemDate = new Date(safeDateStr);

    const timelineKey = isNaN(itemDate.getTime())
      ? "Periode Tidak Diketahui"
      : itemDate.toLocaleString("id-ID", { month: "long", year: "numeric" });

    if (!distributionMap[timelineKey]) {
      distributionMap[timelineKey] = {
        total: 0,
        positive: 0,
        negative: 0,
        neutral: 0,
        records: [],
      };
    }

    distributionMap[timelineKey].total++;

    const labelStatus = item.expected;
    if (labelStatus && ["positive", "negative", "neutral"].includes(labelStatus)) {
      distributionMap[timelineKey][labelStatus]++;
    }

    distributionMap[timelineKey].records.push(item);
  });

  let logBuffer = "=========================================\n";
  logBuffer += "📊 LAPORAN DISTRIBUSI DATASET PER BULAN\n";
  logBuffer += "=========================================\n\n";

  for (const [period, metrics] of Object.entries(distributionMap)) {
    logBuffer += `📅 PERIODE: ${period}\n`;
    logBuffer += `   🔹 Total Records : ${metrics.total} Tweet\n`;
    logBuffer += `   🔹 Positive      : ${metrics.positive} (${((metrics.positive / metrics.total) * 100).toFixed(2)}%)\n`;
    logBuffer += `   🔹 Negative      : ${metrics.negative} (${((metrics.negative / metrics.total) * 100).toFixed(2)}%)\n`;
    logBuffer += `   🔹 Neutral       : ${metrics.neutral} (${((metrics.neutral / metrics.total) * 100).toFixed(2)}%)\n`;

    if (mode === "full") {
      logBuffer += "   --------------------------------------------------------\n";
      metrics.records.forEach((record, index) => {
        const statusLabel = record.expected ? record.expected.toUpperCase() : "UNLABELED";
        logBuffer += `   ${index + 1}. [${statusLabel}] ${record.text.replace(/\n/g, " ")}\n`;
      });
    }
    logBuffer += "\n";
  }

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard
      .writeText(logBuffer)
      .then(() => alert(`✅ Berhasil menyalin ${mode === "summary" ? "REKAP" : "SEMUA DATA"} log untuk ${Object.keys(distributionMap).length} periode!`))
      .catch((err) => {
        console.warn("Clipboard API gagal, mencoba fallback...", err);
        fallbackCopyTextToClipboard(logBuffer);
      });
  } else {
    fallbackCopyTextToClipboard(logBuffer);
  }
}

function handleCopyAllStats(stats) {
  if (!stats || stats.length === 0) {
    alert("Data statistik kosong atau gagal ditarik.");
    return;
  }

  const monthNames = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
  ];

  let grandTotal = 0;
  let grandPos = 0;
  let grandNeg = 0;
  let grandNeu = 0;

  let logBuffer = "=========================================\n";
  logBuffer += "📊 LAPORAN SEBARAN SELURUH TWEETS (REAL DATA)\n";
  logBuffer += "=========================================\n\n";

  stats.forEach((stat) => {
    if (stat.bulan) {
      const [year, month] = stat.bulan.split("-");
      const periodName = `${monthNames[parseInt(month) - 1]} ${year}`;

      logBuffer += `📅 PERIODE: ${periodName}\n`;
      logBuffer += `   🔹 Total Records : ${stat.jumlah} Tweet\n`;
      logBuffer += `   🔹 Positive      : ${stat.positif} (${((stat.positif / stat.jumlah) * 100).toFixed(2)}%)\n`;
      logBuffer += `   🔹 Negative      : ${stat.negatif} (${((stat.negatif / stat.jumlah) * 100).toFixed(2)}%)\n`;
      logBuffer += `   🔹 Neutral       : ${stat.netral} (${((stat.netral / stat.jumlah) * 100).toFixed(2)}%)\n`;
      logBuffer += "   --------------------------------------------------------\n";

      grandTotal += stat.jumlah;
      grandPos += stat.positif;
      grandNeg += stat.negatif;
      grandNeu += stat.netral;
    }
  });

  logBuffer += "\n=========================================\n";
  logBuffer += "📈 KESIMPULAN TOTAL KESELURUHAN\n";
  logBuffer += "=========================================\n";
  logBuffer += `   🔹 Total Semua Tweet : ${grandTotal}\n`;
  logBuffer += `   🔹 Total Positive    : ${grandPos} (${((grandPos / grandTotal) * 100).toFixed(2)}%)\n`;
  logBuffer += `   🔹 Total Negative    : ${grandNeg} (${((grandNeg / grandTotal) * 100).toFixed(2)}%)\n`;
  logBuffer += `   🔹 Total Neutral     : ${grandNeu} (${((grandNeu / grandTotal) * 100).toFixed(2)}%)\n`;
  logBuffer += "=========================================\n";

  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard
      .writeText(logBuffer)
      .then(() => alert(`✅ Berhasil menyalin total sebaran keseluruhan dataset!`))
      .catch((err) => {
        console.warn("Clipboard API gagal, mencoba fallback...", err);
        fallbackCopyTextToClipboard(logBuffer);
      });
  } else {
    fallbackCopyTextToClipboard(logBuffer);
  }
}

function fallbackCopyTextToClipboard(text) {
  const textArea = document.createElement("textarea");
  textArea.value = text;
  textArea.style.position = "fixed";
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const successful = document.execCommand("copy");
    if (successful) {
      alert("✅ Berhasil menyalin log data!");
    } else {
      alert("❌ Gagal menyalin data.");
    }
  } catch (err) {
    console.error("Fallback: Gagal menyalin", err);
    alert("Browser tidak mengizinkan aksi salin otomatis.");
  }
  document.body.removeChild(textArea);
}

// ==========================================
// BOOTSTRAP APP
// ==========================================
document.addEventListener("DOMContentLoaded", () => Controller.initialize());