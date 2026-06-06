const state = { jobId: null, metadata: null };

const el = (id) => document.getElementById(id);
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

function showError(message) {
  el("errorBox").textContent = message;
  el("errorBox").classList.remove("hidden");
}

function clearError() {
  el("errorBox").classList.add("hidden");
  el("errorBox").textContent = "";
}

function statItem(label, value) {
  return `<div class="rounded-md bg-zinc-950 p-3"><dt class="text-zinc-500">${label}</dt><dd class="mt-1 font-medium text-zinc-100">${value}</dd></div>`;
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
    try {
      const response = JSON.parse(xhr.responseText);
      if (xhr.status >= 400) throw new Error(response.detail || "Upload gagal.");
      state.jobId = response.job_id;
      state.metadata = response.metadata;
      renderMetadata(response.metadata);
      el("originalPreview").src = `/api/media/${state.jobId}/original`;
      el("originalCompare").src = `/api/media/${state.jobId}/original`;
      el("analysisSection").classList.remove("hidden");
      el("optimizeSection").classList.remove("hidden");
      setProgress("Upload complete", 100);
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
  setProgress("Queued", 0);
  const profile = document.querySelector("input[name='profile']:checked").value;

  const response = await fetch("/api/optimize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: state.jobId, profile }),
  });
  const data = await response.json();
  if (!response.ok) {
    el("optimizeBtn").disabled = false;
    showError(data.detail || "Optimasi gagal dimulai.");
    return;
  }
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

  setProgress(data.status, data.progress || 0);
  if (data.status === "completed") {
    await renderComparison();
    el("optimizeBtn").disabled = false;
    return;
  }
  if (data.status === "failed") {
    el("optimizeBtn").disabled = false;
    showError(data.error_message || "Optimasi gagal.");
    return;
  }
  setTimeout(pollStatus, 1000);
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
el("themeToggle").addEventListener("click", () => {
  document.documentElement.classList.toggle("dark");
  el("themeToggle").textContent = document.documentElement.classList.contains("dark") ? "Dark" : "Light";
});
