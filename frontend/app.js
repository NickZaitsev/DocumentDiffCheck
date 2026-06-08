const results = document.querySelector("#results");
const loading = document.querySelector("#loading");
const documentsBox = document.querySelector("#documents");
const statsBox = document.querySelector("#stats");
const resultsMeta = document.querySelector("#resultsMeta");
const summaryPanel = document.querySelector("#panel-summary");
const risksPanel = document.querySelector("#panel-risks");
const changesPanel = document.querySelector("#panel-changes");
const riskCount = document.querySelector("#riskCount");
const changeCount = document.querySelector("#changeCount");
const docsCount = document.querySelector("#docsCount");
const docsCard = document.querySelector("#docsCard");
const toasts = document.querySelector("#toasts");
const storedDocumentsList = document.querySelector("#storedDocumentsList");

let allDocuments = [];
const selectedStored = {
  old: null,
  new: null,
};

/* ---------- Theme ---------- */
const themeToggle = document.querySelector("#themeToggle");
const storedTheme = localStorage.getItem("ddc-theme");
if (storedTheme) document.documentElement.dataset.theme = storedTheme;
themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ddc-theme", next);
});

/* ---------- Dropzones ---------- */
document.querySelectorAll(".dropzone").forEach((zone) => {
  const input = zone.querySelector('input[type="file"]');
  const fileLabel = zone.querySelector(".dz-file");
  const searchInput = zone.querySelector("[data-picker]");
  const slot = input.id === "oldFile" ? "old" : "new";

  const reflect = () => {
    const file = input.files[0];
    if (file) {
      selectedStored[slot] = null;
      searchInput.value = "";
      zone.classList.add("has-file");
      zone.classList.remove("has-stored");
      fileLabel.hidden = false;
      fileLabel.innerHTML = renderSelectedFile("Локальный файл", file.name);
    } else {
      zone.classList.remove("has-file");
      if (!selectedStored[slot]) {
        fileLabel.hidden = true;
        fileLabel.innerHTML = "";
      }
    }
  };

  fileLabel.addEventListener("click", (event) => {
    if (!event.target.closest("[data-clear-selection]")) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    clearSlotSelection(slot);
  });

  input.addEventListener("change", reflect);

  ["dragenter", "dragover"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.add("is-dragover");
    }),
  );
  ["dragleave", "drop"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.remove("is-dragover");
    }),
  );
  zone.addEventListener("drop", (e) => {
    const documentId = e.dataTransfer.getData("text/document-id");
    if (documentId) {
      const document = allDocuments.find((item) => item.document_id === documentId);
      if (document) {
        setStoredSlot(slot, document);
      }
      return;
    }
    const file = e.dataTransfer.files[0];
    if (file) {
      input.files = e.dataTransfer.files;
      reflect();
    }
  });
});

document.querySelectorAll("[data-picker]").forEach((input) => {
  input.addEventListener("change", () => {
    const slot = input.dataset.picker;
    if (!input.value.trim()) {
      clearStoredSlot(slot);
      return;
    }

    const document = findDocumentByPickerValue(input.value);
    if (!document) {
      toast("Документ не найден. Введите название или ID из списка.", "err");
      input.value = selectedStored[slot]?.label || "";
      return;
    }
    setStoredSlot(slot, document);
  });
});

/* ---------- Documents collapse (open on desktop, closed on mobile) ---------- */
const docsMq = window.matchMedia("(max-width: 900px)");
const syncDocsOpen = () => {
  docsCard.open = !docsMq.matches;
};
syncDocsOpen();
docsMq.addEventListener("change", syncDocsOpen);

/* ---------- Tabs ---------- */
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const name = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("is-active", t === tab));
    document.querySelectorAll(".tab-panel").forEach((p) =>
      p.classList.toggle("is-active", p.dataset.panel === name),
    );
  });
});

/* ---------- Forms ---------- */
const uploadForm = document.querySelector("#uploadCompareForm");
uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const oldFile = document.querySelector("#oldFile").files[0];
  const newFile = document.querySelector("#newFile").files[0];
  const oldStored = selectedStored.old;
  const newStored = selectedStored.new;

  if (oldStored && newStored) {
    await runComparison(
      () =>
        fetch("/api/comparisons", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            old_document_id: oldStored.document_id,
            new_document_id: newStored.document_id,
          }),
        }),
      uploadForm.querySelector('button[type="submit"]'),
    );
    return;
  }

  if (oldStored || newStored) {
    toast("Выберите два загруженных документа или два локальных файла.", "err");
    return;
  }

  if (!oldFile || !newFile) {
    toast("Выберите два DOCX файла или найдите два загруженных документа.", "err");
    return;
  }
  const body = new FormData();
  body.append("old_file", oldFile);
  body.append("new_file", newFile);
  await runComparison(
    () => fetch("/api/comparisons/upload", { method: "POST", body }),
    uploadForm.querySelector('button[type="submit"]'),
  );
  await loadDocuments();
});

const refreshBtn = document.querySelector("#refreshDocuments");
const refresh = (event) => {
  event.preventDefault();
  event.stopPropagation();
  loadDocuments();
  toast("Список документов обновлён.", "info");
};
refreshBtn.addEventListener("click", refresh);
refreshBtn.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") refresh(e);
});

/* ---------- Comparison flow ---------- */
async function runComparison(requestFactory, button) {
  loading.hidden = false;
  if (button) setLoading(button, true);
  loading.scrollIntoView({ behavior: "smooth", block: "nearest" });
  try {
    const response = await requestFactory();
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || "Request failed");
    }
    const reportUrl = payload.report_url || (payload.report_id ? `/report.html?id=${payload.report_id}` : "");
    if (!reportUrl) {
      throw new Error("Сервер не вернул report_id. Перезапустите python run.py и повторите сравнение.");
    }
    toast("Анализ готов. Открываю отчет.", "ok");
    window.location.assign(reportUrl);
  } catch (error) {
    toast(error.message, "err");
  } finally {
    loading.hidden = true;
    if (button) setLoading(button, false);
  }
}

function setLoading(button, isLoading) {
  button.disabled = isLoading;
  const spinner = button.querySelector(".spinner");
  const label = button.querySelector(".btn-label");
  if (spinner) spinner.hidden = !isLoading;
  if (label) {
    if (isLoading) {
      label.dataset.orig = label.textContent;
      label.textContent = "Анализирую…";
    } else if (label.dataset.orig) {
      label.textContent = label.dataset.orig;
    }
  }
}

/* ---------- Documents ---------- */
async function loadDocuments() {
  try {
    const response = await fetch("/api/documents");
    const documents = withDisplayLabels(sortDocumentsNewestFirst(await response.json()));
    allDocuments = documents;
    renderDocuments(documents);
  } catch {
    documentsBox.className = "documents empty";
    documentsBox.innerHTML = `<p class="empty-note">Не удалось загрузить список.</p>`;
  }
}

function renderDocuments(documents) {
  docsCount.hidden = !documents.length;
  docsCount.textContent = documents.length;
  populateSelects(documents);

  if (!documents.length) {
    documentsBox.className = "documents empty";
    documentsBox.innerHTML = `<p class="empty-note">Пока документов нет.<br />Загрузите DOCX слева.</p>`;
    return;
  }
  documentsBox.className = "documents";
  const fileIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>`;
  documentsBox.innerHTML = documents
    .map(
      (doc) => `
        <div class="document-item" draggable="true" data-document-id="${escapeHtml(doc.document_id)}">
          <span class="doc-icon" aria-hidden="true">${fileIcon}</span>
          <div class="doc-body">
            <strong title="${escapeHtml(doc.label)}">${escapeHtml(doc.label)}</strong>
            <div class="doc-meta">${formatDate(doc.created_at)} · ${formatBytes(doc.size_bytes)}</div>
            <div class="doc-id" title="${escapeHtml(doc.document_id)}">${escapeHtml(displayDocumentId(doc.document_id))}</div>
          </div>
          <button class="copy-id-btn" type="button" data-copy-id="${escapeHtml(doc.document_id)}" title="Скопировать ID" aria-label="Скопировать ID">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
          </button>
          <a class="download-doc-btn" href="/api/documents/${encodeURIComponent(doc.document_id)}/download" title="Скачать документ" aria-label="Скачать документ">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <path d="M7 10l5 5 5-5"></path>
              <path d="M12 15V3"></path>
            </svg>
          </a>
        </div>
      `,
    )
    .join("");
  documentsBox.querySelectorAll(".document-item").forEach((item) => {
    item.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("text/document-id", item.dataset.documentId);
      event.dataTransfer.effectAllowed = "copy";
    });
  });
  documentsBox.querySelectorAll("[data-copy-id]").forEach((button) => {
    button.addEventListener("click", async (event) => {
      event.stopPropagation();
      await navigator.clipboard.writeText(button.dataset.copyId);
      toast("Document ID скопирован.", "ok");
    });
  });
}

// Disambiguate repeated filenames so dropdown options are distinguishable.
function withDisplayLabels(documents) {
  const counts = {};
  documents.forEach((d) => (counts[d.filename] = (counts[d.filename] || 0) + 1));
  const seen = {};
  return documents.map((d) => {
    let label = d.filename;
    if (counts[d.filename] > 1) {
      seen[d.filename] = (seen[d.filename] || 0) + 1;
      label = `${d.filename} (${seen[d.filename]})`;
    }
    return { ...d, label };
  });
}

function populateSelects(documents) {
  storedDocumentsList.innerHTML = documents
    .map(
      (doc) =>
        `<option value="${escapeHtml(doc.label)}">${escapeHtml(displayDocumentId(doc.document_id))} · ${formatDate(doc.created_at)}</option>`,
    )
    .join("");
}

function sortDocumentsNewestFirst(documents) {
  return [...documents].sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

function setStoredSlot(slot, storedDocument) {
  selectedStored[slot] = storedDocument;
  const fileInput = document.querySelector(`#${slot}File`);
  const searchInput = document.querySelector(`[data-picker="${slot}"]`);
  const zone = document.querySelector(`[data-for="${slot}File"]`);
  const fileLabel = zone.querySelector(".dz-file");

  fileInput.value = "";
  searchInput.value = storedDocument.label;
  zone.classList.add("has-file", "has-stored");
  zone.classList.remove("is-dragover");
  fileLabel.hidden = false;
  fileLabel.innerHTML = renderSelectedFile("Загруженный документ", storedDocument.label, {
    date: formatDate(storedDocument.created_at),
    code: displayDocumentId(storedDocument.document_id),
    id: storedDocument.document_id,
  });
}

function clearStoredSlot(slot) {
  selectedStored[slot] = null;
  const searchInput = document.querySelector(`[data-picker="${slot}"]`);
  const fileInput = document.querySelector(`#${slot}File`);
  const zone = document.querySelector(`[data-for="${slot}File"]`);
  const fileLabel = zone.querySelector(".dz-file");

  searchInput.value = "";
  zone.classList.remove("has-stored");
  if (!fileInput.files[0]) {
    zone.classList.remove("has-file");
    fileLabel.hidden = true;
    fileLabel.innerHTML = "";
  }
}

function clearSlotSelection(slot) {
  selectedStored[slot] = null;
  const fileInput = document.querySelector(`#${slot}File`);
  const searchInput = document.querySelector(`[data-picker="${slot}"]`);
  const zone = document.querySelector(`[data-for="${slot}File"]`);
  const fileLabel = zone.querySelector(".dz-file");

  fileInput.value = "";
  searchInput.value = "";
  zone.classList.remove("has-file", "has-stored", "is-dragover");
  fileLabel.hidden = true;
  fileLabel.innerHTML = "";
}

function renderSelectedFile(kind, name, meta = null) {
  return `
    <button class="dz-clear" type="button" data-clear-selection aria-label="Убрать документ" title="Убрать документ">×</button>
    <span class="dz-file-kind">${escapeHtml(kind)}</span>
    <span class="dz-file-name" title="${escapeHtml(name)}">${escapeHtml(name)}</span>
    ${
      meta
        ? `<span class="dz-file-meta">${escapeHtml(meta.date)} · <span title="${escapeHtml(meta.id)}">${escapeHtml(meta.code)}</span></span>`
        : ""
    }
  `;
}

function findDocumentByPickerValue(value) {
  const normalized = value.trim().toLowerCase();
  if (!normalized) {
    return null;
  }
  return (
    allDocuments.find((document) => document.document_id.toLowerCase() === normalized) ||
    allDocuments.find((document) => displayDocumentId(document.document_id).toLowerCase() === normalized) ||
    allDocuments.find((document) => document.label.toLowerCase() === normalized) ||
    allDocuments.find((document) => document.filename.toLowerCase() === normalized) ||
    allDocuments.find(
      (document) =>
        document.document_id.toLowerCase().includes(normalized) ||
        displayDocumentId(document.document_id).toLowerCase().includes(normalized) ||
        document.label.toLowerCase().includes(normalized),
    ) ||
    null
  );
}

function formatBytes(bytes) {
  if (!bytes) return "0 КБ";
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.max(1, Math.round(kb))} КБ`;
  return `${(kb / 1024).toFixed(1)} МБ`;
}

function formatDate(value) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function displayDocumentId(value) {
  const text = String(value);
  if (text.length <= 18) {
    return text;
  }
  return `${text.slice(0, 8)}...${text.slice(-6)}`;
}

function formatRiskLevelBadge(level) {
  return `Риск: ${riskLevelLabel(level)}`;
}

function riskLevelLabel(level) {
  const labels = {
    low: "низкий",
    medium: "средний",
    high: "высокий",
    critical: "критический",
    none: "не выявлен",
  };
  return labels[String(level || "low").toLowerCase()] || String(level);
}

/* ---------- Render results ---------- */
function renderResults(payload) {
  results.hidden = false;
  renderMeta(payload.comparison);
  renderStats(payload.comparison.stats);
  renderSummary(payload.summary);
  renderRisks(payload.risk_assessment);
  renderChanges(payload.comparison.changes);
  // reset to first tab
  document.querySelector('.tab[data-tab="summary"]').click();
}

function renderMeta(comparison) {
  resultsMeta.innerHTML = `
    <span class="file-chip old"><span class="dot"></span>${escapeHtml(comparison.old_filename)}</span>
    <span class="meta-arrow">→</span>
    <span class="file-chip new"><span class="dot"></span>${escapeHtml(comparison.new_filename)}</span>
  `;
}

function renderStats(stats) {
  statsBox.innerHTML = [
    stat("Добавлено", stats.added, "s-added"),
    stat("Удалено", stats.removed, "s-removed"),
    stat("Изменено", stats.modified, "s-modified"),
    stat("Без изменений", stats.unchanged, ""),
    stat("Сходство", `${Math.round(stats.similarity_score * 100)}%`, "s-sim"),
  ].join("");
}

function stat(label, value, cls) {
  return `<div class="stat ${cls}"><b>${escapeHtml(String(value))}</b><span>${label}</span></div>`;
}

function renderSummary(summary) {
  summaryPanel.innerHTML = `
    <div class="stack">
      <p class="lead">${escapeHtml(summary.plain_language_summary)}</p>
      <div class="callout">
        <h3>Юридическое значение</h3>
        <p>${escapeHtml(summary.legal_significance)}</p>
      </div>
      ${
        summary.key_changes.length
          ? `<h3 class="section-title">Ключевые изменения</h3>${summary.key_changes.map(renderKeyChange).join("")}`
          : ""
      }
      ${
        summary.recommended_review_points.length
          ? `<h3 class="section-title">Что проверить</h3><ul class="review-list">${summary.recommended_review_points
              .map((point) => `<li>${escapeHtml(point)}</li>`)
              .join("")}</ul>`
          : ""
      }
      <span class="provider-tag">${escapeHtml(summary.provider)}${summary.model ? ` · ${escapeHtml(summary.model)}` : ""}</span>
    </div>
  `;
}

function renderKeyChange(change) {
  return `
    <div class="key-change">
      <h3>${escapeHtml(change.title)}</h3>
      <p class="kc-desc">${escapeHtml(change.description)}</p>
      <p class="kc-sig">${escapeHtml(change.legal_significance)}</p>
    </div>
  `;
}

function renderRisks(assessment) {
  const count = assessment.risks.length;
  riskCount.hidden = !count;
  riskCount.textContent = count;

  if (!count) {
    risksPanel.innerHTML = `
      <div class="stack">
        <div class="risk-banner">
          <span class="rb-text">Финансовые риск-кандидаты не найдены.</span>
          <span class="level-badge level-low"><span class="dot"></span>${escapeHtml(formatRiskLevelBadge("low"))}</span>
        </div>
        <span class="provider-tag">${escapeHtml(assessment.provider)}</span>
      </div>
    `;
    return;
  }
  const riskLevel = assessment.overall_risk_level || "low";
  const levelCls = "lvl-" + String(riskLevel).toLowerCase();
  risksPanel.innerHTML = `
    <div class="stack">
      <div class="risk-banner">
        <span class="rb-text">${escapeHtml(assessment.review_recommendation)}</span>
        <span class="level-badge ${levelCls}"><span class="dot"></span>${escapeHtml(formatRiskLevelBadge(riskLevel))}</span>
      </div>
      ${assessment.risks.map(renderRisk).join("")}
      <span class="provider-tag">${escapeHtml(assessment.provider)}${assessment.model ? ` · ${escapeHtml(assessment.model)}` : ""}</span>
    </div>
  `;
}

function renderRisk(risk) {
  const conf = Math.round(risk.confidence * 100);
  return `
    <div class="risk">
      <div class="risk-head">
        <div>
          <h3>${escapeHtml(risk.title)}</h3>
          <span class="risk-type">${escapeHtml(risk.risk_type)}</span>
        </div>
        <div class="confidence">
          <span>${conf}%</span>
          <div class="conf-bar"><div class="conf-fill" style="width:${conf}%"></div></div>
        </div>
      </div>
      <p>${escapeHtml(risk.explanation)}</p>
      ${risk.estimated_impact ? `<div class="impact">💰 ${escapeHtml(risk.estimated_impact)}</div>` : ""}
      <div class="source-text">${escapeHtml(risk.source_text)}</div>
      ${
        risk.detected_terms && risk.detected_terms.length
          ? `<div class="terms">${risk.detected_terms.map((t) => `<span class="term">${escapeHtml(t)}</span>`).join("")}</div>`
          : ""
      }
    </div>
  `;
}

function renderChanges(changes) {
  changeCount.hidden = !changes.length;
  changeCount.textContent = changes.length;
  if (!changes.length) {
    changesPanel.innerHTML = `<div class="risk-banner"><span class="rb-text">Отличия не найдены.</span></div>`;
    return;
  }
  changesPanel.innerHTML = `<div class="diff-view">${changes.map(renderChange).join("")}</div>`;
}

function renderChange(change) {
  const oldText = change.old_block ? change.old_block.text : "";
  const newText = change.new_block ? change.new_block.text : "";
  const rowClass = `diff-row diff-row-${change.change_type}`;
  const isTable = change.old_block?.kind === "table_row" || change.new_block?.kind === "table_row";
  const oldContent = renderDiffSide(change, "old", oldText, isTable);
  const newContent = renderDiffSide(change, "new", newText, isTable);
  return `
    <div class="${rowClass}">
      <div class="diff-row-meta">
        <span class="diff-badge ${escapeHtml(change.change_type)}">${changeLabel(change.change_type)}</span>
        <span class="sim-note">${Math.round(change.similarity * 100)}%</span>
      </div>
      <div class="diff-split">
        <div class="diff-side diff-old">
          <div class="diff-line-no">${formatBlockIndex(change.old_block)}</div>
          <div class="diff-content">${oldContent}</div>
        </div>
        <div class="diff-side diff-new">
          <div class="diff-line-no">${formatBlockIndex(change.new_block)}</div>
          <div class="diff-content">${newContent}</div>
        </div>
      </div>
    </div>
  `;
}

function renderDiffSide(change, side, text, isTable) {
  if (!text) {
    return `<span class="diff-empty">Нет блока</span>`;
  }
  if (change.change_type === "modified" && change.word_diff && change.word_diff.length) {
    return `<div class="inline-diff">${renderInlineDiff(change.word_diff, side)}</div>`;
  }
  if (isTable) {
    return renderTableRow(text);
  }
  return `<div class="diff-text">${escapeHtml(text)}</div>`;
}

function renderInlineDiff(segments, side) {
  return segments
    .filter((segment) => {
      if (side === "old") return segment.diff_type !== "added";
      return segment.diff_type !== "removed";
    })
    .map((segment) => `<span class="${escapeHtml(segment.diff_type)}">${escapeHtml(segment.text)}</span>`)
    .join(" ");
}

function renderTableRow(text) {
  const cells = String(text).split("|").map((cell) => cell.trim());
  if (cells.length < 2) {
    return `<div class="diff-text">${escapeHtml(text)}</div>`;
  }
  return `<table class="diff-table"><tbody><tr>${cells
    .map((cell) => `<td>${escapeHtml(cell)}</td>`)
    .join("")}</tr></tbody></table>`;
}

function formatBlockIndex(block) {
  return block ? block.index + 1 : "";
}

function changeLabel(type) {
  const labels = {
    unchanged: "Без изменений",
    added: "Добавлено",
    removed: "Удалено",
    modified: "Изменено",
  };
  return labels[type] || escapeHtml(type);
}

/* ---------- Toasts ---------- */
function toast(message, type = "info") {
  const icons = { ok: "✓", err: "!", info: "i" };
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="t-icon">${icons[type] || "i"}</span><span>${escapeHtml(message)}</span>`;
  toasts.appendChild(el);
  setTimeout(() => {
    el.classList.add("leaving");
    el.addEventListener("animationend", () => el.remove(), { once: true });
  }, 3600);
}

/* ---------- Utils ---------- */
function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadDocuments();
