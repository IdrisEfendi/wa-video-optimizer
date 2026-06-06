const state = { jobId: null, metadata: null };
const HISTORY_KEY = "wa_video_optimizer_history";

const el = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
}[char]));
const safePath = (value, prefix) => {
  const text = String(value || "");
  return text.startsWith(prefix) ? text : "";
};
const fmtBytes = (bytes) => {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return `${value.toFixed(value >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
};
const fmtBitrate = (bitrate) => bitrate ? `${(bitrate / 1000000).toFixed(2)} Mbps` : "-";
const fmtDuration = (seconds) => {
  seconds = Math.round(seconds || 0);
  const min = Math.floor(seconds / 60);
  const sec = seconds % 60;
  return `${min}:${String(sec).padStart(2, "0")}`;
};

function setProgress(label, percent) {
  el("progressLabel").textContent = label;
  el("progressPercent").textContent = `${percent}%`;
  el("progressBar").style.width = `${percent}%`;
}

function statusLabel(status) {
  const labels = {
    uploaded: "Ready",
    queued: "Waiting",
    processing: "Encoding",
    encoding: "Encoding",
    finalizing: "Finalizing",
    cancel_requested: "Canceling",
    canceled: "Canceled",
    completed: "Completed",
    failed: "Failed",
  };
  return labels[status] || status;
}

function showError(message) {
  el("errorBox").textContent = message;
  el("errorBox").classList.remove("hidden");
}

function clearError() {
  el("errorBox").classList.add("hidden");
  el("errorBox").textContent = "";
}

function statItem(label, value) {
  return `<div class="rounded-md bg-zinc-950 p-3"><dt class="text-zinc-500">${escapeHtml(label)}</dt><dd class="mt-1 font-medium text-zinc-100">${escapeHtml(value)}</dd></div>`;
}

function renderMetadata(metadata) {
  el("metadataGrid").innerHTML = [
    statItem("Resolution", metadata.resolution),
    statItem("Width", metadata.width),
    statItem("Height", metadata.height),
    statItem("FPS", metadata.fps),
    statItem("Duration", fmtDuration(metadata.duration)),
    statItem("Codec", metadata.video_codec),
    statItem("Audio", metadata.audio_codec),
    statItem("Bitrate", fmtBitrate(metadata.bitrate)),
    statItem("File Size", fmtBytes(metadata.file_size)),
  ].join("");
}

function estimateSizeLabel(estimatedSize) {
  if (!estimatedSize || !estimatedSize.low_bytes || !estimatedSize.high_bytes) return "-";
  return `${fmtBytes(estimatedSize.low_bytes)} - ${fmtBytes(estimatedSize.high_bytes)}`;
}

function selectedProfile() {
  return document.querySelector("input[name='profile']:checked").value;
}

function hideResultSections() {
  el("comparisonSection").classList.add("hidden");
  el("resultSection").classList.add("hidden");
}

function renderEstimate(estimate) {
  el("estimateProfile").textContent = estimate.profile.toUpperCase();
  el("estimateGrid").innerHTML = [
    statItem("Resolution", estimate.resolution),
    statItem("FPS", estimate.fps),
    statItem("CRF", estimate.crf),
    statItem("Maxrate", estimate.maxrate),
    statItem("Est. Size", estimateSizeLabel(estimate.estimated_size)),
    statItem("Audio", `${estimate.audio_codec.toUpperCase()} ${estimate.audio_bitrate}`),
  ].join("");
  el("estimateChanges").innerHTML = estimate.changes
    .map((change) => `<li>${escapeHtml(change)}</li>`)
    .join("");
  if (estimate.warnings?.length) {
    el("estimateWarnings").innerHTML = estimate.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("");
    el("estimateWarnings").classList.remove("hidden");
  } else {
    el("estimateWarnings").innerHTML = "";
    el("estimateWarnings").classList.add("hidden");
  }
  el("estimateSection").classList.remove("hidden");
}

function readHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
  } catch (error) {
    return [];
  }
}

function writeHistory(items) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(0, 8)));
}

function upsertHistory(item) {
  const items = readHistory().filter((entry) => entry.job_id !== item.job_id);
  writeHistory([{ ...item, updated_at: new Date().toISOString() }, ...items]);
  renderHistory();
}

function removeHistory(jobId) {
  writeHistory(readHistory().filter((entry) => entry.job_id !== jobId));
  renderHistory();
}

async function renderHistory() {
  const items = readHistory();
  if (!items.length) {
    el("historySection").classList.add("hidden");
    el("historyList").innerHTML = "";
    return;
  }

  el("historySection").classList.remove("hidden");
  el("historyList").innerHTML = items
    .map((item) => {
      const thumbnailUrl = safePath(item.thumbnail_url, "/api/thumbnail/");
      const downloadUrl = `/api/download/${encodeURIComponent(item.job_id || "")}`;
      return `
      <div class="flex flex-wrap items-center justify-between gap-2 rounded-md bg-zinc-950 p-3">
        <div class="flex min-w-0 items-center gap-3">
          ${
            thumbnailUrl
              ? `<img class="h-12 w-20 rounded-md object-cover" src="${escapeHtml(thumbnailUrl)}" alt="">`
              : `<div class="flex h-12 w-20 items-center justify-center rounded-md bg-zinc-900 text-xs text-zinc-500">No thumb</div>`
          }
          <div class="min-w-0">
            <div class="truncate font-medium text-zinc-100">${escapeHtml(item.filename || item.job_id)}</div>
            <div class="mt-1 text-xs text-zinc-500">${escapeHtml(item.resolution || "-")} | ${escapeHtml(statusLabel(item.status || "uploaded"))}</div>
          </div>
        </div>
        <div class="flex flex-wrap gap-2">
          <a class="${item.status === "completed" ? "" : "pointer-events-none opacity-40"} rounded-md border border-zinc-700 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800" href="${escapeHtml(downloadUrl)}">Download</a>
          <button class="rounded-md border border-zinc-700 px-3 py-2 text-xs text-zinc-200 hover:bg-zinc-800" data-action="delete-history" data-job-id="${escapeHtml(item.job_id)}" type="button">Delete</button>
        </div>
      </div>
    `;
    })
    .join("");

  for (const item of items) {
    try {
      const response = await fetch(`/api/jobs/${item.job_id}`);
      if (!response.ok) continue;
      const data = await response.json();
      if (data.job.status !== item.status) {
        upsertHistory({
          ...item,
          status: data.job.status,
          resolution: data.job.optimized?.resolution || data.job.original?.resolution || item.resolution,
        });
        break;
      }
    } catch (error) {
      // History is best-effort; stale jobs can remain until user clears them.
    }
  }
}

async function loadEstimate() {
  if (!state.jobId) return;
  try {
    const response = await fetch(`/api/estimate/${state.jobId}?profile=${encodeURIComponent(selectedProfile())}`);
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Gagal membuat estimasi output.");
    renderEstimate(data.estimate);
  } catch (error) {
    showError(error.message);
  }
}

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    const box = el("healthBox");
    if (!response.ok || !data.success) {
      const ffmpegError = data.health?.ffmpeg?.error || "FFmpeg tidak tersedia.";
      const ffprobeError = data.health?.ffprobe?.error || "FFprobe tidak tersedia.";
      box.textContent = `${ffmpegError} ${ffprobeError}`;
      box.className = "rounded-md border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-200";
      return;
    }
    box.textContent = "FFmpeg dan FFprobe siap digunakan.";
    box.className = "rounded-md border border-emerald-500/30 bg-emerald-950/30 p-3 text-sm text-emerald-200";
  } catch (error) {
    el("healthBox").textContent = "Gagal mengecek FFmpeg. Pastikan server berjalan.";
    el("healthBox").className = "rounded-md border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-200";
  }
}

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    if (!response.ok || !data.success) throw new Error("Gagal memuat konfigurasi.");
    const config = data.config;
    el("activeJobsBadge").textContent = `Active jobs: ${data.active_jobs}`;
    el("configGrid").innerHTML = [
      statItem("Max Upload", `${config.max_upload_mb} MB`),
      statItem("Expiry", `${config.job_expiry_hours} hours`),
      statItem("Concurrent Jobs", config.max_concurrent_jobs),
      statItem("FFmpeg", config.ffmpeg_bin),
      statItem("FFprobe", config.ffprobe_bin),
      statItem("Formats", config.allowed_extensions.join(", ")),
    ].join("");
  } catch (error) {
    el("activeJobsBadge").textContent = "Active jobs: -";
    el("configGrid").innerHTML = [statItem("Settings", "Unavailable")].join("");
  }
}

async function uploadFile(file) {
  clearError();
  setProgress("Uploading", 0);

  const formData = new FormData();
  formData.append("video", file);

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/upload");
  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable) {
      setProgress("Uploading", Math.round((event.loaded / event.total) * 100));
    }
  };
  xhr.onload = () => {
    setProgress("Analyzing", 100);
    try {
      const response = JSON.parse(xhr.responseText);
      if (xhr.status >= 400) throw new Error(response.detail || "Upload gagal.");
      state.jobId = response.job_id;
      state.metadata = response.metadata;
      upsertHistory({
        job_id: response.job_id,
        filename: response.job?.original_filename || "Video",
        resolution: response.metadata.resolution,
        status: "uploaded",
        thumbnail_url: response.thumbnail_url,
      });
      renderMetadata(response.metadata);
      el("originalPreview").src = `/api/media/${state.jobId}/original`;
      if (response.thumbnail_url) {
        el("originalPreview").poster = response.thumbnail_url;
        el("thumbnailFallback").classList.add("hidden");
      } else {
        el("originalPreview").removeAttribute("poster");
        el("thumbnailFallback").classList.remove("hidden");
      }
      el("originalCompare").src = `/api/media/${state.jobId}/original`;
      el("analysisSection").classList.remove("hidden");
      el("optimizeSection").classList.remove("hidden");
      el("resetBtn").classList.remove("hidden");
      hideResultSections();
      loadEstimate();
      setProgress("Ready", 100);
    } catch (error) {
      showError(error.message);
      setProgress("Upload failed", 0);
    }
  };
  xhr.onerror = () => {
    showError("Upload gagal. Periksa koneksi atau server.");
    setProgress("Upload failed", 0);
  };
  xhr.send(formData);
}

async function optimize() {
  if (!state.jobId) return;
  clearError();
  el("optimizeBtn").disabled = true;
  el("cancelBtn").classList.remove("hidden");
  el("cancelBtn").disabled = false;
  setProgress("Waiting", 0);
  const profile = selectedProfile();

  const response = await fetch("/api/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: state.jobId, profile }),
  });
  const data = await response.json();
  if (!response.ok) {
    el("optimizeBtn").disabled = false;
    el("cancelBtn").classList.add("hidden");
    showError(data.detail || "Optimasi gagal dimulai.");
    return;
  }
  loadConfig();
  pollStatus();
}

async function pollStatus() {
  const response = await fetch(`/api/optimize/${state.jobId}/status`);
  const data = await response.json();
  if (!response.ok) {
    el("optimizeBtn").disabled = false;
    showError(data.detail || "Gagal membaca status.");
    return;
  }

  setProgress(statusLabel(data.status), data.progress || 0);
  const currentHistory = readHistory().find((entry) => entry.job_id === state.jobId);
  if (currentHistory && currentHistory.status !== data.status) {
    upsertHistory({ ...currentHistory, status: data.status });
  }
  if (data.status === "completed") {
    await renderComparison();
    const existing = readHistory().find((entry) => entry.job_id === state.jobId);
    if (existing) upsertHistory({ ...existing, status: "completed" });
    el("optimizeBtn").disabled = false;
    el("cancelBtn").classList.add("hidden");
    loadConfig();
    return;
  }
  if (data.status === "failed") {
    el("optimizeBtn").disabled = false;
    el("cancelBtn").classList.add("hidden");
    showError(data.error_message || "Optimasi gagal.");
    loadConfig();
    return;
  }
  if (data.status === "canceled") {
    el("optimizeBtn").disabled = false;
    el("cancelBtn").classList.add("hidden");
    loadConfig();
    return;
  }
  setTimeout(pollStatus, 1000);
}

async function cancelOptimize() {
  if (!state.jobId) return;
  el("cancelBtn").disabled = true;
  setProgress("Canceling", 99);
  try {
    const response = await fetch(`/api/jobs/${state.jobId}/cancel`, { method: "POST" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Gagal membatalkan proses.");
    const existing = readHistory().find((entry) => entry.job_id === state.jobId);
    if (existing) upsertHistory({ ...existing, status: data.status });
    loadConfig();
  } catch (error) {
    showError(error.message);
    el("cancelBtn").disabled = false;
  }
}

async function renderComparison() {
  const response = await fetch(`/api/compare/${state.jobId}`);
  const data = await response.json();
  const original = data.original;
  const optimized = data.optimized;
  const result = data.result;

  el("optimizedCompare").src = `/api/media/${state.jobId}/optimized`;
  el("originalStats").innerHTML = [
    statItem("Resolution", original.resolution),
    statItem("FPS", original.fps),
    statItem("Bitrate", fmtBitrate(original.bitrate)),
    statItem("File Size", fmtBytes(original.file_size)),
  ].join("");
  el("optimizedStats").innerHTML = [
    statItem("Resolution", optimized.resolution),
    statItem("FPS", optimized.fps),
    statItem("Bitrate", fmtBitrate(optimized.bitrate)),
    statItem("File Size", fmtBytes(optimized.file_size)),
  ].join("");
  el("resultSummary").innerHTML = [
    statItem("Original Size", fmtBytes(original.file_size)),
    statItem("Optimized Size", fmtBytes(optimized.file_size)),
    statItem("Reduction", `${result.reduction_percent}%`),
    statItem("Processing Time", `${result.processing_seconds}s`),
  ].join("");
  el("downloadLink").href = `/api/download/${state.jobId}`;
  el("comparisonSection").classList.remove("hidden");
  el("resultSection").classList.remove("hidden");
}

async function resetApp() {
  const jobId = state.jobId;
  state.jobId = null;
  state.metadata = null;
  clearError();
  setProgress("Idle", 0);

  el("fileInput").value = "";
  el("originalPreview").removeAttribute("src");
  el("originalPreview").removeAttribute("poster");
  el("originalPreview").load();
  el("originalCompare").removeAttribute("src");
  el("originalCompare").load();
  el("optimizedCompare").removeAttribute("src");
  el("optimizedCompare").load();

  el("metadataGrid").innerHTML = "";
  el("estimateGrid").innerHTML = "";
  el("estimateChanges").innerHTML = "";
  el("estimateWarnings").innerHTML = "";
  el("estimateWarnings").classList.add("hidden");
  el("originalStats").innerHTML = "";
  el("optimizedStats").innerHTML = "";
  el("resultSummary").innerHTML = "";
  el("downloadLink").href = "#";

  el("analysisSection").classList.add("hidden");
  el("optimizeSection").classList.add("hidden");
  el("estimateSection").classList.add("hidden");
  hideResultSections();
  el("resetBtn").classList.add("hidden");
  el("cancelBtn").classList.add("hidden");
  el("cancelBtn").disabled = false;
  el("thumbnailFallback").classList.add("hidden");
  el("optimizeBtn").disabled = false;

  if (jobId) {
    try {
      await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
      removeHistory(jobId);
    } catch (error) {
      // Reset UI should still work even when server-side cleanup is already done.
    }
  }
}

const dropZone = el("dropZone");
dropZone.addEventListener("click", () => el("fileInput").click());
dropZone.addEventListener("dragover", (event) => {
  event.preventDefault();
  dropZone.classList.add("border-emerald-300");
});
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("border-emerald-300"));
dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropZone.classList.remove("border-emerald-300");
  const file = event.dataTransfer.files[0];
  if (file) uploadFile(file);
});
el("fileInput").addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (file) uploadFile(file);
});
el("optimizeBtn").addEventListener("click", optimize);
el("cancelBtn").addEventListener("click", cancelOptimize);
el("resetBtn").addEventListener("click", resetApp);
el("clearHistoryBtn").addEventListener("click", () => {
  writeHistory([]);
  renderHistory();
});
el("historyList").addEventListener("click", async (event) => {
  const button = event.target.closest("[data-action='delete-history']");
  if (!button) return;
  const jobId = button.dataset.jobId;
  button.disabled = true;
  try {
    await fetch(`/api/jobs/${jobId}`, { method: "DELETE" });
  } catch (error) {
    // Local history deletion should still work for expired or missing jobs.
  }
  removeHistory(jobId);
  loadConfig();
});
document.querySelectorAll("input[name='profile']").forEach((input) => {
  input.addEventListener("change", () => {
    hideResultSections();
    loadEstimate();
  });
});
el("themeToggle").addEventListener("click", () => {
  document.documentElement.classList.toggle("dark");
  el("themeToggle").textContent = document.documentElement.classList.contains("dark") ? "Dark" : "Light";
});
loadHealth();
loadConfig();
renderHistory();
