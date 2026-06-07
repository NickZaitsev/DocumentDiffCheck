const reportStatus = document.querySelector("#reportStatus");
const reportView = document.querySelector("#reportView");
const reportTitle = document.querySelector("#reportTitle");
const reportDate = document.querySelector("#reportDate");
const resultsMeta = document.querySelector("#resultsMeta");
const statsBox = document.querySelector("#stats");
const summaryPanel = document.querySelector("#panel-summary");
const risksPanel = document.querySelector("#panel-risks");
const changesPanel = document.querySelector("#panel-changes");
const riskCount = document.querySelector("#riskCount");
const changeCount = document.querySelector("#changeCount");
const shareReport = document.querySelector("#shareReport");
const toasts = document.querySelector("#toasts");

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const name = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("is-active", item === tab));
    document.querySelectorAll(".tab-panel").forEach((panel) =>
      panel.classList.toggle("is-active", panel.dataset.panel === name),
    );
  });
});

shareReport.addEventListener("click", async () => {
  await navigator.clipboard.writeText(window.location.href);
  toast("Ссылка на отчет скопирована.", "ok");
});

async function loadReport() {
  const reportId = new URLSearchParams(window.location.search).get("id");
  if (!reportId) {
    showError("В ссылке нет report ID.");
    return;
  }

  try {
    const response = await fetch(`/api/reports/${encodeURIComponent(reportId)}`);
    const report = await response.json();
    if (!response.ok) {
      throw new Error(report.message || "Report request failed");
    }
    renderReport(report);
  } catch (error) {
    showError(error.message);
  }
}

function renderReport(report) {
  reportStatus.hidden = true;
  reportView.hidden = false;
  const comparison = report.comparison;
  reportTitle.textContent = `${comparison.old_filename} → ${comparison.new_filename}`;
  reportDate.textContent = `Создан: ${formatDate(report.created_at)}`;
  renderMeta(comparison);
  renderStats(comparison.stats);
  renderSummary(report.summary);
  renderRisks(report.risk_assessment);
  renderChanges(comparison.changes);
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
          <span class="level-badge level-low"><span class="dot"></span>LOW</span>
        </div>
        <span class="provider-tag">${escapeHtml(assessment.provider)}</span>
      </div>
    `;
    return;
  }

  const levelClass = `lvl-${assessment.overall_risk_level.toLowerCase()}`;
  risksPanel.innerHTML = `
    <div class="stack">
      <div class="risk-banner">
        <span class="rb-text">${escapeHtml(assessment.review_recommendation)}</span>
        <span class="level-badge ${levelClass}"><span class="dot"></span>${escapeHtml(assessment.overall_risk_level)}</span>
      </div>
      ${assessment.risks.map(renderRisk).join("")}
      <span class="provider-tag">${escapeHtml(assessment.provider)}${assessment.model ? ` · ${escapeHtml(assessment.model)}` : ""}</span>
    </div>
  `;
}

function renderRisk(risk) {
  const pct = Math.round(risk.confidence * 100);
  return `
    <div class="risk">
      <div class="risk-head">
        <div>
          <h3>${escapeHtml(risk.title)}</h3>
          <span class="risk-type">${escapeHtml(risk.risk_type)}</span>
        </div>
        <div class="confidence"><span>${pct}%</span><div class="conf-bar"><div class="conf-fill" style="width:${pct}%"></div></div></div>
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

function renderChanges(changes) {
  changeCount.hidden = !changes.length;
  changeCount.textContent = changes.length;
  if (!changes.length) {
    changesPanel.innerHTML = `<div class="risk-banner"><span class="rb-text">Отличия не найдены.</span></div>`;
    return;
  }
  changesPanel.innerHTML = `<div class="stack">${changes.map(renderChange).join("")}</div>`;
}

function renderChange(change) {
  const oldText = change.old_block ? change.old_block.text : "";
  const newText = change.new_block ? change.new_block.text : "";
  const hasDiff = change.word_diff && change.word_diff.length;
  return `
    <div class="change">
      <div class="change-head">
        <span class="badge ${escapeHtml(change.change_type)}">${escapeHtml(change.change_type)}</span>
        <span class="sim-note">сходство ${Math.round(change.similarity * 100)}%</span>
      </div>
      <div class="text-pair">
        <div class="text-col">
          <h4>Было</h4>
          <div class="text-box box-old">${escapeHtml(oldText || "—")}</div>
        </div>
        <div class="text-col">
          <h4>Стало</h4>
          <div class="text-box box-new">${escapeHtml(newText || "—")}</div>
        </div>
      </div>
      ${
        hasDiff
          ? `<div class="word-diff-label" style="margin-top:12px">Пословный diff</div>
             <div class="word-diff">${change.word_diff.map(renderWordSegment).join(" ")}</div>`
          : ""
      }
    </div>
  `;
}

function renderWordSegment(segment) {
  return `<span class="${escapeHtml(segment.diff_type)}">${escapeHtml(segment.text)}</span>`;
}

function showError(message) {
  reportStatus.innerHTML = `<p>${escapeHtml(message)}</p><a class="btn-mini" href="/">Вернуться на главную</a>`;
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

function formatDate(value) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadReport();
