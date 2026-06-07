const statusBox = document.querySelector("#status");
const results = document.querySelector("#results");
const documentsBox = document.querySelector("#documents");
const documentsMeta = document.querySelector("#documentsMeta");
const statsBox = document.querySelector("#stats");
const summaryBox = document.querySelector("#summary");
const risksBox = document.querySelector("#risks");
const changesBox = document.querySelector("#changes");
const apiState = document.querySelector("#apiState");
const comparisonTitle = document.querySelector("#comparisonTitle");
const providerBadge = document.querySelector("#providerBadge");

const oldFileInput = document.querySelector("#oldFile");
const newFileInput = document.querySelector("#newFile");
const oldDocumentIdInput = document.querySelector("#oldDocumentId");
const newDocumentIdInput = document.querySelector("#newDocumentId");

document.querySelectorAll(".mode-tab").forEach((tab) => {
  tab.addEventListener("click", () => setMode(tab.dataset.mode));
});

document.querySelector("#uploadCompareForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const oldFile = oldFileInput.files[0];
  const newFile = newFileInput.files[0];
  if (!oldFile || !newFile) {
    showStatus("Select both DOCX files.", true);
    return;
  }

  const body = new FormData();
  body.append("old_file", oldFile);
  body.append("new_file", newFile);

  await runComparison(() =>
    fetch("/api/comparisons/upload", {
      method: "POST",
      body,
    }),
  );
  await loadDocuments();
});

document.querySelector("#idCompareForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const oldDocumentId = oldDocumentIdInput.value.trim();
  const newDocumentId = newDocumentIdInput.value.trim();
  if (!oldDocumentId || !newDocumentId) {
    showStatus("Select or paste both document IDs.", true);
    return;
  }

  await runComparison(() =>
    fetch("/api/comparisons", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        old_document_id: oldDocumentId,
        new_document_id: newDocumentId,
      }),
    }),
  );
});

document.querySelector("#refreshDocuments").addEventListener("click", loadDocuments);

[oldFileInput, newFileInput].forEach((input) => {
  input.addEventListener("change", () => updateFileState(input));
});

document.querySelectorAll(".dropzone").forEach((dropzone) => {
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      dropzone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => {
      dropzone.classList.remove("dragging");
    });
  });
});

async function runComparison(requestFactory) {
  showStatus("Comparing documents...");
  results.hidden = true;
  try {
    const response = await requestFactory();
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || "Request failed");
    }
    renderResults(payload);
    showStatus("Comparison complete.");
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function loadDocuments() {
  try {
    const response = await fetch("/api/documents");
    if (!response.ok) {
      throw new Error("Document list request failed");
    }
    const documents = await response.json();
    renderDocuments(documents);
    apiState.textContent = "API online";
    apiState.classList.add("ok");
  } catch {
    documentsBox.className = "documents empty";
    documentsBox.textContent = "Could not load documents.";
    documentsMeta.textContent = "Connection issue";
    apiState.textContent = "API offline";
    apiState.classList.remove("ok");
  }
}

function setMode(mode) {
  document.querySelectorAll(".mode-tab").forEach((tab) => {
    const isActive = tab.dataset.mode === mode;
    tab.classList.toggle("active", isActive);
    tab.setAttribute("aria-selected", String(isActive));
  });

  document.querySelectorAll("[data-mode-panel]").forEach((panel) => {
    panel.classList.toggle("hidden", panel.dataset.modePanel !== mode);
  });
}

function updateFileState(input) {
  const file = input.files[0];
  const prefix = input.id === "oldFile" ? "old" : "new";
  const dropzone = document.querySelector(`[data-dropzone="${prefix}"]`);
  const fileName = document.querySelector(`#${prefix}FileName`);
  const fileMeta = document.querySelector(`#${prefix}FileMeta`);

  dropzone.classList.toggle("has-file", Boolean(file));
  fileName.textContent = file ? file.name : "Select DOCX";
  fileMeta.textContent = file ? formatBytes(file.size) : "Drop file here or browse";
}

function renderDocuments(documents) {
  documentsMeta.textContent =
    documents.length === 1 ? "1 stored file" : `${documents.length} stored files`;

  if (!documents.length) {
    documentsBox.className = "documents empty";
    documentsBox.textContent = "No documents uploaded.";
    return;
  }

  documentsBox.className = "documents";
  documentsBox.innerHTML = documents.map(renderDocument).join("");

  documentsBox.querySelectorAll("[data-copy-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(button.dataset.copyId);
      showStatus("Document ID copied.");
    });
  });

  documentsBox.querySelectorAll("[data-fill-old]").forEach((button) => {
    button.addEventListener("click", () => {
      oldDocumentIdInput.value = button.dataset.fillOld;
      setMode("id");
      showStatus("Old document selected.");
    });
  });

  documentsBox.querySelectorAll("[data-fill-new]").forEach((button) => {
    button.addEventListener("click", () => {
      newDocumentIdInput.value = button.dataset.fillNew;
      setMode("id");
      showStatus("New document selected.");
    });
  });
}

function renderDocument(document) {
  return `
    <article class="document-item">
      <div>
        <strong class="document-name" title="${escapeHtml(document.filename)}">
          ${escapeHtml(document.filename)}
        </strong>
        <p class="document-meta">${formatBytes(document.size_bytes)}</p>
        <div class="doc-id">${escapeHtml(document.document_id)}</div>
      </div>
      <div class="document-actions">
        <button class="button ghost" type="button" data-fill-old="${escapeHtml(document.document_id)}">Old</button>
        <button class="button ghost" type="button" data-fill-new="${escapeHtml(document.document_id)}">New</button>
        <button class="button ghost" type="button" data-copy-id="${escapeHtml(document.document_id)}">Copy</button>
      </div>
    </article>
  `;
}

function renderResults(payload) {
  const comparison = payload.comparison;
  results.hidden = false;
  comparisonTitle.textContent = `${comparison.old_filename} -> ${comparison.new_filename}`;
  providerBadge.textContent = providerLabel(payload.summary);
  renderStats(comparison.stats);
  renderSummary(payload.summary);
  renderRisks(payload.risk_assessment);
  renderChanges(comparison.changes);
}

function renderStats(stats) {
  statsBox.innerHTML = [
    stat("Added", stats.added, "added"),
    stat("Removed", stats.removed, "removed"),
    stat("Modified", stats.modified, "modified"),
    stat("Unchanged", stats.unchanged, "unchanged"),
    stat("Similarity", `${Math.round(stats.similarity_score * 100)}%`, "similarity"),
  ].join("");
}

function stat(label, value, type) {
  return `
    <div class="stat stat-${type}">
      <b>${escapeHtml(String(value))}</b>
      <span>${escapeHtml(label)}</span>
    </div>
  `;
}

function renderSummary(summary) {
  summaryBox.innerHTML = `
    <div class="stack">
      <div class="summary-lead">
        <p>${escapeHtml(summary.plain_language_summary)}</p>
      </div>
      <div class="summary-lead">
        <h3>Legal significance</h3>
        <p>${escapeHtml(summary.legal_significance)}</p>
      </div>
      ${summary.key_changes.map(renderKeyChange).join("")}
      ${renderReviewPoints(summary.recommended_review_points)}
    </div>
  `;
}

function renderKeyChange(change) {
  return `
    <div class="key-change">
      <span class="badge ${escapeHtml(change.change_type)}">${escapeHtml(change.change_type)}</span>
      <h3>${escapeHtml(change.title)}</h3>
      <p class="preserve-lines">${escapeHtml(change.description)}</p>
      <p class="muted">${escapeHtml(change.legal_significance)}</p>
    </div>
  `;
}

function renderReviewPoints(points) {
  if (!points.length) {
    return "";
  }

  return `
    <div class="summary-lead">
      <h3>Review checklist</h3>
      <ul class="review-list">
        ${points.map((point) => `<li>${escapeHtml(point)}</li>`).join("")}
      </ul>
    </div>
  `;
}

function renderRisks(assessment) {
  if (!assessment.risks.length) {
    risksBox.innerHTML = `
      <div class="risk-lead">
        <span class="risk-level">${escapeHtml(assessment.overall_risk_level)}</span>
        <p>${escapeHtml(assessment.review_recommendation)}</p>
      </div>
    `;
    return;
  }

  risksBox.innerHTML = `
    <div class="stack">
      <div class="risk-lead">
        <span class="risk-level">${escapeHtml(assessment.overall_risk_level)}</span>
        <p>${escapeHtml(assessment.review_recommendation)}</p>
      </div>
      ${assessment.risks.map(renderRisk).join("")}
    </div>
  `;
}

function renderRisk(risk) {
  return `
    <div class="risk">
      <div class="risk-header">
        <div>
          <h3>${escapeHtml(risk.title)}</h3>
          <p class="muted">${escapeHtml(risk.risk_type)}</p>
        </div>
        <span class="confidence">${Math.round(risk.confidence * 100)}%</span>
      </div>
      <p>${escapeHtml(risk.explanation)}</p>
      ${risk.estimated_impact ? `<p><strong>Impact:</strong> ${escapeHtml(risk.estimated_impact)}</p>` : ""}
      ${risk.detected_terms.length ? `<p class="muted">${risk.detected_terms.map(escapeHtml).join(" · ")}</p>` : ""}
      <div class="text-box">${escapeHtml(risk.source_text)}</div>
    </div>
  `;
}

function renderChanges(changes) {
  if (!changes.length) {
    changesBox.innerHTML = "<p class=\"muted\">No changed blocks found.</p>";
    return;
  }

  changesBox.innerHTML = `<div class="stack">${changes.map(renderChange).join("")}</div>`;
}

function renderChange(change) {
  const oldText = change.old_block ? change.old_block.text : "";
  const newText = change.new_block ? change.new_block.text : "";
  return `
    <div class="change">
      <div class="change-header">
        <span class="badge ${escapeHtml(change.change_type)}">${escapeHtml(change.change_type)}</span>
        <span class="confidence">similarity ${Math.round(change.similarity * 100)}%</span>
      </div>
      <div class="text-pair">
        <div>
          <div class="text-box-label">Before</div>
          <div class="text-box">${escapeHtml(oldText || "-")}</div>
        </div>
        <div>
          <div class="text-box-label">After</div>
          <div class="text-box">${escapeHtml(newText || "-")}</div>
        </div>
      </div>
      ${change.word_diff.length ? `<div class="word-diff">${change.word_diff.map(renderWordSegment).join(" ")}</div>` : ""}
    </div>
  `;
}

function renderWordSegment(segment) {
  return `<span class="${escapeHtml(segment.diff_type)}">${escapeHtml(segment.text)}</span>`;
}

function providerLabel(summary) {
  if (!summary.model) {
    return summary.provider;
  }
  return `${summary.provider} / ${summary.model}`;
}

function showStatus(message, isError = false) {
  statusBox.hidden = false;
  statusBox.textContent = message;
  statusBox.classList.toggle("error", isError);
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) {
    return "";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
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
