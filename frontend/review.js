const loading = document.querySelector("#loading");
const documentsBox = document.querySelector("#documents");
const docsCount = document.querySelector("#docsCount");
const docsCard = document.querySelector("#docsCard");
const toasts = document.querySelector("#toasts");
const storedDocumentsList = document.querySelector("#storedDocumentsList");
const reviewForm = document.querySelector("#reviewForm");
const reviewFile = document.querySelector("#reviewFile");
const reviewStoredSearch = document.querySelector("#reviewStoredSearch");
const reviewResults = document.querySelector("#reviewResults");
const reviewTitle = document.querySelector("#reviewTitle");
const reviewMeta = document.querySelector("#reviewMeta");
const reviewStats = document.querySelector("#reviewStats");
const summaryPanel = document.querySelector("#panel-summary");
const risksPanel = document.querySelector("#panel-risks");
const riskCount = document.querySelector("#riskCount");

let allDocuments = [];
let selectedStored = null;

/* ---------- Theme ---------- */
const themeToggle = document.querySelector("#themeToggle");
const storedTheme = localStorage.getItem("ddc-theme");
if (storedTheme) document.documentElement.dataset.theme = storedTheme;
themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ddc-theme", next);
});

/* ---------- Dropzone ---------- */
const zone = document.querySelector(".single-dropzone");
const fileLabel = zone.querySelector(".dz-file");

function reflectFileSelection() {
  const file = reviewFile.files[0];
  if (file) {
    selectedStored = null;
    reviewStoredSearch.value = "";
    zone.classList.add("has-file");
    zone.classList.remove("has-stored");
    fileLabel.hidden = false;
    fileLabel.innerHTML = renderSelectedFile("Локальный файл", file.name);
    return;
  }
  zone.classList.remove("has-file");
  if (!selectedStored) {
    fileLabel.hidden = true;
    fileLabel.innerHTML = "";
  }
}

fileLabel.addEventListener("click", (event) => {
  if (!event.target.closest("[data-clear-selection]")) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  clearDocumentSelection();
});

reviewFile.addEventListener("change", reflectFileSelection);

["dragenter", "dragover"].forEach((eventName) =>
  zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.add("is-dragover");
  }),
);
["dragleave", "drop"].forEach((eventName) =>
  zone.addEventListener(eventName, (event) => {
    event.preventDefault();
    zone.classList.remove("is-dragover");
  }),
);
zone.addEventListener("drop", (event) => {
  const documentId = event.dataTransfer.getData("text/document-id");
  if (documentId) {
    const document = allDocuments.find((item) => item.document_id === documentId);
    if (document) setStoredDocument(document);
    return;
  }
  const file = event.dataTransfer.files[0];
  if (file) {
    reviewFile.files = event.dataTransfer.files;
    reflectFileSelection();
  }
});

reviewStoredSearch.addEventListener("change", () => {
  if (!reviewStoredSearch.value.trim()) {
    clearStoredDocument();
    return;
  }
  const document = findDocumentByPickerValue(reviewStoredSearch.value);
  if (!document) {
    toast("Документ не найден. Введите название или ID из списка.", "err");
    reviewStoredSearch.value = selectedStored?.label || "";
    return;
  }
  setStoredDocument(document);
});

/* ---------- Documents collapse ---------- */
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
    document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("is-active", item === tab));
    document.querySelectorAll(".tab-panel").forEach((panel) =>
      panel.classList.toggle("is-active", panel.dataset.panel === name),
    );
  });
});

/* ---------- Review flow ---------- */
reviewForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = reviewFile.files[0];
  if (selectedStored) {
    await runReview(
      () =>
        fetch("/api/reviews", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ document_id: selectedStored.document_id }),
        }),
      reviewForm.querySelector('button[type="submit"]'),
    );
    return;
  }
  if (!file) {
    toast("Выберите DOCX файл или загруженный документ.", "err");
    return;
  }
  const body = new FormData();
  body.append("file", file);
  await runReview(
    () => fetch("/api/reviews/upload", { method: "POST", body }),
    reviewForm.querySelector('button[type="submit"]'),
  );
  await loadDocuments();
});

async function runReview(requestFactory, button) {
  loading.hidden = false;
  if (button) setLoading(button, true);
  loading.scrollIntoView({ behavior: "smooth", block: "nearest" });
  try {
    const response = await requestFactory();
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || "Request failed");
    }
    const reviewUrl =
      payload.review_url || (payload.review_id ? `/review-report.html?id=${encodeURIComponent(payload.review_id)}` : "");
    if (!reviewUrl) {
      throw new Error("Сервер не вернул ссылку на отчет ревью.");
    }
    toast("Ревью готово. Открываю отчет.", "ok");
    window.location.assign(reviewUrl);
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

function renderReview(payload) {
  reviewResults.hidden = false;
  reviewTitle.textContent = payload.document.filename;
  reviewMeta.textContent = `${formatDate(payload.document.created_at)} · ${formatBytes(payload.document.size_bytes)}`;
  reviewStats.innerHTML = [
    stat("Блоков", payload.blocks_count, "s-sim"),
    stat("Рисков", payload.risk_assessment.risks.length, payload.risk_assessment.risks.length ? "s-modified" : "s-added"),
    stat("Риск", riskLevelLabel(payload.risk_assessment.overall_risk_level), "s-sim"),
  ].join("");
  renderSummary(payload.summary);
  renderRisks(payload.risk_assessment);
  document.querySelector('.tab[data-tab="summary"]').click();
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
          ? `<h3 class="section-title">Ключевые блоки</h3>${summary.key_changes.map(renderKeyChange).join("")}`
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
  const confidence = Math.round(risk.confidence * 100);
  return `
    <div class="risk">
      <div class="risk-head">
        <div>
          <h3>${escapeHtml(risk.title)}</h3>
          <span class="risk-type">${escapeHtml(risk.risk_type)}</span>
        </div>
        <div class="confidence">
          <span>${confidence}%</span>
          <div class="conf-bar"><div class="conf-fill" style="width:${confidence}%"></div></div>
        </div>
      </div>
      <p>${escapeHtml(risk.explanation)}</p>
      ${risk.estimated_impact ? `<div class="impact">${escapeHtml(risk.estimated_impact)}</div>` : ""}
      <div class="source-text">${escapeHtml(risk.source_text)}</div>
      ${
        risk.detected_terms && risk.detected_terms.length
          ? `<div class="terms">${risk.detected_terms.map((term) => `<span class="term">${escapeHtml(term)}</span>`).join("")}</div>`
          : ""
      }
    </div>
  `;
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
    documentsBox.innerHTML = `<p class="empty-note">Пока документов нет.</p>`;
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
          <button class="btn-mini btn-mini-primary" type="button" data-review-id="${escapeHtml(doc.document_id)}">Ревью</button>
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
  documentsBox.querySelectorAll("[data-review-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const document = allDocuments.find((item) => item.document_id === button.dataset.reviewId);
      if (document) setStoredDocument(document);
    });
  });
}

function withDisplayLabels(documents) {
  const counts = {};
  documents.forEach((document) => (counts[document.filename] = (counts[document.filename] || 0) + 1));
  const seen = {};
  return documents.map((document) => {
    let label = document.filename;
    if (counts[document.filename] > 1) {
      seen[document.filename] = (seen[document.filename] || 0) + 1;
      label = `${document.filename} (${seen[document.filename]})`;
    }
    return { ...document, label };
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

function setStoredDocument(storedDocument) {
  selectedStored = storedDocument;
  reviewFile.value = "";
  reviewStoredSearch.value = storedDocument.label;
  zone.classList.add("has-file", "has-stored");
  zone.classList.remove("is-dragover");
  fileLabel.hidden = false;
  fileLabel.innerHTML = renderSelectedFile("Загруженный документ", storedDocument.label, {
    date: formatDate(storedDocument.created_at),
    code: displayDocumentId(storedDocument.document_id),
    id: storedDocument.document_id,
  });
}

function clearStoredDocument() {
  selectedStored = null;
  reviewStoredSearch.value = "";
  zone.classList.remove("has-stored");
  if (!reviewFile.files[0]) {
    zone.classList.remove("has-file");
    fileLabel.hidden = true;
    fileLabel.innerHTML = "";
  }
}

function clearDocumentSelection() {
  selectedStored = null;
  reviewFile.value = "";
  reviewStoredSearch.value = "";
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
  if (!normalized) return null;
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

const refreshBtn = document.querySelector("#refreshDocuments");
const refresh = (event) => {
  event.preventDefault();
  event.stopPropagation();
  loadDocuments();
  toast("Список документов обновлён.", "info");
};
refreshBtn.addEventListener("click", refresh);
refreshBtn.addEventListener("keydown", (event) => {
  if (event.key === "Enter" || event.key === " ") refresh(event);
});

/* ---------- Utils ---------- */
function formatBytes(bytes) {
  if (!bytes) return "0 КБ";
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.max(1, Math.round(kb))} КБ`;
  return `${(kb / 1024).toFixed(1)} МБ`;
}

function formatDate(value) {
  if (!value) return "";
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
  if (text.length <= 18) return text;
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadDocuments();
