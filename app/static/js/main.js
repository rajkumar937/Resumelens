/**
 * main.js — ResumeLens Enhanced Frontend
 * Handles upload, analysis, tab switching, score ring, progress bars.
 * Chart.js completely removed. Focus on clean cards and progress indicators.
 */

"use strict";

// ── DOM refs ──
const dropZone       = document.getElementById("dropZone");
const fileInput      = document.getElementById("fileInput");
const jdTextarea     = document.getElementById("jdTextarea");
const wordCountLabel = document.getElementById("wordCountLabel");
const analyseBtn     = document.getElementById("analyseBtn");
const uploadError    = document.getElementById("uploadError");
const dashboard      = document.getElementById("dashboard");
const uploadSection  = document.getElementById("uploadSection");
const warningsBar    = document.getElementById("warningsBar");
const newAnalysisBtn = document.getElementById("newAnalysisBtn");
const copyBtn        = document.getElementById("copyBtn");

let selectedFile = null;
let allPages     = [];

// ════════════════════════════════════════════
// DROP ZONE
// ════════════════════════════════════════════
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });

dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("dragging"); });
dropZone.addEventListener("dragleave", ()  => dropZone.classList.remove("dragging"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("dragging");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

function handleFile(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showError("Only PDF files accepted");
    return;
  }
  selectedFile = file;
  document.getElementById("selectedFilename").textContent = file.name;
  dropZone.querySelector(".drop-zone__idle").classList.add("hidden");
  dropZone.querySelector(".drop-zone__selected").classList.remove("hidden");
  analyseBtn.disabled = false;
  analyseBtn.setAttribute("aria-disabled", "false");
  hideError();
}

// ════════════════════════════════════════════
// WORD COUNTER
// ════════════════════════════════════════════
jdTextarea.addEventListener("input", () => {
  const words = jdTextarea.value.trim().split(/\s+/).filter(Boolean).length;
  wordCountLabel.textContent = `${words} word${words !== 1 ? "s" : ""}`;
});

// ════════════════════════════════════════════
// ANALYSE
// ════════════════════════════════════════════
analyseBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  setLoading(true);
  hideError();

  const fd = new FormData();
  fd.append("resume", selectedFile);
  fd.append("job_description", jdTextarea.value);

  try {
    const res = await fetch("/analyse", { method: "POST", body: fd });
    const data = await res.json();

    if (!res.ok || data.error) {
      showError(data.error || "Analysis failed.");
      setLoading(false);
      return;
    }

    renderDashboard(data);
    setLoading(false);
    dashboard.classList.remove("hidden");
    dashboard.scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    showError("Network error. Is the server running?");
    setLoading(false);
  }
});

// ════════════════════════════════════════════
// RENDER DASHBOARD
// ════════════════════════════════════════════
function renderDashboard(data) {
  const scores = data.scores || {};
  const skills = data.skills || {};
  const info   = data.resume_info || {};
  allPages = data.pages || [];

  // Warnings
  if (data.warnings && data.warnings.length) {
    warningsBar.innerHTML = data.warnings.map(w => `<span>⚠ ${w}</span>`).join("");
    warningsBar.classList.remove("hidden");
  } else {
    warningsBar.classList.add("hidden");
  }

  // Score ring
  const overall = scores.overall ?? null;
  renderRing(overall);

  // Progress bars
  setBar("barText",     "pctText",     scores.text_similarity ?? null);
  setBar("barSkill",    "pctSkill",    scores.skill_match ?? null);
  const matchedCount = (skills.matched_skills || []).length;
  const totalJD      = (skills.jd_skills
    ? Object.values(skills.jd_skills).flat().length
    : 0);
  const matchPct = totalJD > 0 ? (matchedCount / totalJD) * 100 : null;
  setBar("barMatched",  "pctMatched",  matchPct, `${matchedCount}/${totalJD}`);

  // Stat cards
  setText("statPages",      data.page_count ?? "—");
  setText("statWords",      (data.word_count ?? 0).toLocaleString());
  const resumeSkillTotal = Object.values(skills.resume_skills || {}).flat().length;
  setText("statSkillsFound", resumeSkillTotal);
  setText("statMatched",    matchedCount);
  setText("statMissing",    (skills.missing_skills || []).length);

  // Explanation
  const expBox = document.getElementById("explanationBody");
  if (scores.explanation) {
    expBox.innerHTML = `<pre>${scores.explanation}</pre>`;
  } else {
    expBox.innerHTML = "<p>Overall = 40% text similarity + 40% skill match + 20% matched count ratio.</p>";
  }

  // Skills tab
  renderSkills(skills);

  // Resume info tab
  renderInfo(info);

  // Raw text tab
  renderRaw(allPages);
}

// ── Score ring ──
function renderRing(score) {
  const label = document.getElementById("scoreValue");

  if (!label) return;

  if (score === null || score === undefined) {
    label.textContent = "—";
    return;
  }

  label.textContent = `${Math.round(score)}%`;
}
  
// ── Progress bars ──
function setBar(barId, pctId, value, overrideLabel) {
  const bar  = document.getElementById(barId);
  const pct  = document.getElementById(pctId);
  if (value === null || value === undefined) {
    bar.style.width = "0%";
    pct.textContent = "—";
  } else {
    const v = Math.min(Math.max(value, 0), 100);
    bar.style.width = `${v}%`;
    pct.textContent = overrideLabel ?? `${v.toFixed(1)}%`;
    bar.parentElement.setAttribute("aria-valuenow", Math.round(v));
  }
}

// ── Skills tab ──
function renderSkills(skills) {
  const matched  = skills.matched_skills  || [];
  const missing  = skills.missing_skills  || [];
  const resume   = skills.resume_skills   || {};
  const jd       = skills.jd_skills       || {};

  const matchedEl = document.getElementById("skillsMatched");
  const missingEl = document.getElementById("skillsMissing");
  const resumeEl  = document.getElementById("skillsResume");
  const jdEl      = document.getElementById("skillsJD");

  matchedEl.innerHTML = matched.length
    ? `<h2 class="section-title">✅ Matched Skills (${matched.length})</h2>
       <div class="chip-group">${matched.map(s => `<span class="chip chip--green">${s}</span>`).join("")}</div>`
    : `<p class="empty-hint">No matched skills.</p>`;

  missingEl.innerHTML = missing.length
    ? `<h2 class="section-title">❌ Missing Skills (${missing.length})</h2>
       <div class="chip-group">${missing.map(s => `<span class="chip chip--red">${s}</span>`).join("")}</div>`
    : "";

  const resumeFlat = Object.entries(resume);
  resumeEl.innerHTML = resumeFlat.length
    ? `<h2 class="section-title">🟣 All Resume Skills</h2>` +
      resumeFlat.map(([cat, arr]) =>
        `<div class="category-row"><span class="cat-label">${cat}</span>
         <div class="chip-group">${arr.map(s => `<span class="chip chip--purple">${s}</span>`).join("")}</div></div>`
      ).join("")
    : `<p class="empty-hint">No skills detected in resume.</p>`;

  const jdFlat = Object.entries(jd);
  jdEl.innerHTML = jdFlat.length
    ? `<h2 class="section-title">💼 Job-Required Skills</h2>` +
      jdFlat.map(([cat, arr]) =>
        `<div class="category-row"><span class="cat-label">${cat}</span>
         <div class="chip-group">${arr.map(s => `<span class="chip chip--blue">${s}</span>`).join("")}</div></div>`
      ).join("")
    : "";
}

// ── Resume info tab ──
function renderInfo(info) {
  const panel = document.getElementById("resumeInfoPanel");
  const contact = info.contact || {};
  const sections = info.sections || {};

  const contactHtml = `
    <div class="info-card">
      <h2 class="section-title">Contact</h2>
      <div class="contact-grid">
        <span class="contact-label">Name</span>  <span>${info.name  || "Not found"}</span>
        <span class="contact-label">Email</span> <span>${contact.email  || "Not found"}</span>
        <span class="contact-label">Phone</span> <span>${contact.phone  || "Not found"}</span>
      </div>
    </div>`;

  const sectionHtml = Object.entries(sections).map(([key, lines]) => {
    const content = Array.isArray(lines) && lines.length
      ? lines.map(l => `<li>${l}</li>`).join("")
      : "<li class='empty-hint'>Not found</li>";
    return `<div class="info-card">
      <h2 class="section-title">${key.charAt(0).toUpperCase() + key.slice(1)}</h2>
      <ul class="section-list">${content}</ul>
    </div>`;
  }).join("");

  panel.innerHTML = contactHtml + sectionHtml;
}

// ── Raw text tab ──
function renderRaw(pages) {
  const pageTabs = document.getElementById("pageTabs");
  const rawText  = document.getElementById("rawText");

  pageTabs.innerHTML = "";

  if (pages.length > 1) {
    pages.forEach((_, i) => {
      const btn = document.createElement("button");
      btn.className = "page-tab-btn" + (i === 0 ? " active" : "");
      btn.textContent = `Page ${i + 1}`;
      btn.setAttribute("role", "tab");
      btn.setAttribute("aria-selected", i === 0 ? "true" : "false");
      btn.addEventListener("click", () => {
        document.querySelectorAll(".page-tab-btn").forEach(b => {
          b.classList.remove("active");
          b.setAttribute("aria-selected", "false");
        });
        btn.classList.add("active");
        btn.setAttribute("aria-selected", "true");
        rawText.textContent = pages[i];
      });
      pageTabs.appendChild(btn);
    });
  }
  rawText.textContent = pages[0] || "No text extracted.";
}

// ── Copy button ──
copyBtn && copyBtn.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(document.getElementById("rawText").textContent);
    copyBtn.textContent = "Copied!";
    setTimeout(() => { copyBtn.textContent = "Copy"; }, 2000);
  } catch { copyBtn.textContent = "Failed"; }
});

// ════════════════════════════════════════════
// TABS
// ════════════════════════════════════════════
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => {
      b.classList.remove("active");
      b.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.add("hidden"));
    btn.classList.add("active");
    btn.setAttribute("aria-selected", "true");
    const panel = document.getElementById("tab" + capitalise(btn.dataset.tab));
    if (panel) panel.classList.remove("hidden");
  });
});

function capitalise(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ════════════════════════════════════════════
// NEW ANALYSIS
// ════════════════════════════════════════════
newAnalysisBtn && newAnalysisBtn.addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  jdTextarea.value = "";
  wordCountLabel.textContent = "0 words";
  analyseBtn.disabled = true;
  analyseBtn.setAttribute("aria-disabled", "true");
  dropZone.querySelector(".drop-zone__idle").classList.remove("hidden");
  dropZone.querySelector(".drop-zone__selected").classList.add("hidden");
  dashboard.classList.add("hidden");
  hideError();
  uploadSection.scrollIntoView({ behavior: "smooth" });
});

// ════════════════════════════════════════════
// HELPERS
// ════════════════════════════════════════════
function showError(msg) {
  uploadError.textContent = msg;
  uploadError.classList.remove("hidden");
}
function hideError() { uploadError.classList.add("hidden"); }

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function setLoading(on) {
  const text    = analyseBtn.querySelector(".btn-text");
  const spinner = analyseBtn.querySelector(".btn-spinner");
  analyseBtn.disabled = on;
  if (on) {
    text.textContent = "Analysing…";
    spinner.classList.remove("hidden");
  } else {
    text.textContent = "Analyse Resume";
    spinner.classList.add("hidden");
  }
}
