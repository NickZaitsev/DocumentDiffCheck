const statusBox = document.querySelector("#status");
const results = document.querySelector("#results");
const documentsBox = document.querySelector("#documents");
const statsBox = document.querySelector("#stats");
const summaryBox = document.querySelector("#summary");
const risksBox = document.querySelector("#risks");
const changesBox = document.querySelector("#changes");

document.querySelector("#uploadCompareForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const oldFile = document.querySelector("#oldFile").files[0];
  const newFile = document.querySelector("#newFile").files[0];
  if (!oldFile || !newFile) {
    showStatus("Выберите два DOCX файла.", true);
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
  const oldDocumentId = document.querySelector("#oldDocumentId").value.trim();
  const newDocumentId = document.querySelector("#newDocumentId").value.trim();
  if (!oldDocumentId || !newDocumentId) {
    showStatus("Укажите оба document ID.", true);
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

async function runComparison(requestFactory) {
  showStatus("Сравниваю документы...");
  results.hidden = true;
  try {
    const response = await requestFactory();
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || "Request failed");
    }
    renderResults(payload);
    showStatus("Готово.");
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function loadDocuments() {
  try {
    const response = await fetch("/api/documents");
    const documents = await response.json();
    renderDocuments(documents);
  } catch {
    documentsBox.textContent = "Не удалось загрузить список документов.";
  }
}

function renderDocuments(documents) {
  if (!documents.length) {
    documentsBox.className = "documents empty";
    documentsBox.textContent = "Пока документов нет.";
    return;
  }
  documentsBox.className = "documents";
  documentsBox.innerHTML = documents
    .map(
      (document) => `
        <div class="document-item">
          <div>
            <strong>${escapeHtml(document.filename)}</strong>
            <div class="doc-id">${escapeHtml(document.document_id)}</div>
          </div>
          <button type="button" data-document-id="${escapeHtml(document.document_id)}">ID</button>
        </div>
      `,
    )
    .join("");
  documentsBox.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(button.dataset.documentId);
      showStatus("Document ID скопирован.");
    });
  });
}

function renderResults(payload) {
  results.hidden = false;
  renderStats(payload.comparison.stats);
  renderSummary(payload.summary);
  renderRisks(payload.risk_assessment);
  renderChanges(payload.comparison.changes);
}

function renderStats(stats) {
  statsBox.innerHTML = [
    stat("Added", stats.added),
    stat("Removed", stats.removed),
    stat("Modified", stats.modified),
    stat("Unchanged", stats.unchanged),
    stat("Similarity", `${Math.round(stats.similarity_score * 100)}%`),
  ].join("");
}

function stat(label, value) {
  return `<div class="stat"><b>${escapeHtml(String(value))}</b><span>${label}</span></div>`;
}

function renderSummary(summary) {
  summaryBox.innerHTML = `
    <div class="stack">
      <p>${escapeHtml(summary.plain_language_summary)}</p>
      <p><strong>Юридическое значение:</strong> ${escapeHtml(summary.legal_significance)}</p>
      <p class="muted">Provider: ${escapeHtml(summary.provider)}${summary.model ? ` / ${escapeHtml(summary.model)}` : ""}</p>
      ${summary.key_changes.map(renderKeyChange).join("")}
      ${
        summary.recommended_review_points.length
          ? `<div><h3>Что проверить</h3><ul>${summary.recommended_review_points
              .map((point) => `<li>${escapeHtml(point)}</li>`)
              .join("")}</ul></div>`
          : ""
      }
    </div>
  `;
}

function renderKeyChange(change) {
  return `
    <div class="key-change">
      <h3>${escapeHtml(change.title)}</h3>
      <p>${escapeHtml(change.description)}</p>
      <p class="muted">${escapeHtml(change.legal_significance)}</p>
    </div>
  `;
}

function renderRisks(assessment) {
  if (!assessment.risks.length) {
    risksBox.innerHTML = `
      <p>Финансовые риск-кандидаты не найдены.</p>
      <p class="muted">Provider: ${escapeHtml(assessment.provider)}</p>
    `;
    return;
  }
  risksBox.innerHTML = `
    <div class="stack">
      <p><strong>Уровень:</strong> ${escapeHtml(assessment.overall_risk_level)}</p>
      <p>${escapeHtml(assessment.review_recommendation)}</p>
      <p class="muted">Provider: ${escapeHtml(assessment.provider)}${assessment.model ? ` / ${escapeHtml(assessment.model)}` : ""}</p>
      ${assessment.risks.map(renderRisk).join("")}
    </div>
  `;
}

function renderRisk(risk) {
  return `
    <div class="risk">
      <h3>${escapeHtml(risk.title)}</h3>
      <p><strong>${escapeHtml(risk.risk_type)}</strong> · confidence ${Math.round(risk.confidence * 100)}%</p>
      <p>${escapeHtml(risk.explanation)}</p>
      ${risk.estimated_impact ? `<p><strong>Impact:</strong> ${escapeHtml(risk.estimated_impact)}</p>` : ""}
      <div class="text-box">${escapeHtml(risk.source_text)}</div>
    </div>
  `;
}

function renderChanges(changes) {
  if (!changes.length) {
    changesBox.innerHTML = "<p>Отличия не найдены.</p>";
    return;
  }
  changesBox.innerHTML = `<div class="stack">${changes.map(renderChange).join("")}</div>`;
}

function renderChange(change) {
  const oldText = change.old_block ? change.old_block.text : "";
  const newText = change.new_block ? change.new_block.text : "";
  return `
    <div class="change">
      <span class="badge ${escapeHtml(change.change_type)}">${escapeHtml(change.change_type)}</span>
      <span class="muted"> similarity ${Math.round(change.similarity * 100)}%</span>
      <div class="text-pair">
        <div>
          <h3>Было</h3>
          <div class="text-box">${escapeHtml(oldText || "—")}</div>
        </div>
        <div>
          <h3>Стало</h3>
          <div class="text-box">${escapeHtml(newText || "—")}</div>
        </div>
      </div>
      <div class="word-diff">${change.word_diff.map(renderWordSegment).join(" ")}</div>
    </div>
  `;
}

function renderWordSegment(segment) {
  return `<span class="${escapeHtml(segment.diff_type)}">${escapeHtml(segment.text)}</span>`;
}

function showStatus(message, isError = false) {
  statusBox.hidden = false;
  statusBox.textContent = message;
  statusBox.style.borderColor = isError ? "#e17b73" : "";
}

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadDocuments();

