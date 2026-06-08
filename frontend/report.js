const reportStatus = document.querySelector("#reportStatus");
const reportView = document.querySelector("#reportView");
const reportTitle = document.querySelector("#reportTitle");
const reportDate = document.querySelector("#reportDate");
const resultsMeta = document.querySelector("#resultsMeta");
const statsBox = document.querySelector("#stats");
const summaryPanel = document.querySelector("#panel-summary");
const changesPanel = document.querySelector("#panel-changes");
const feedCount = document.querySelector("#feedCount");
const changeCount = document.querySelector("#changeCount");
const shareReport = document.querySelector("#shareReport");
const toasts = document.querySelector("#toasts");
const themeToggle = document.querySelector("#themeToggle");

let currentComparison = null;
let diffMode = localStorage.getItem("ddc-diff-mode") || "full";

const storedTheme = localStorage.getItem("ddc-theme");
if (storedTheme) document.documentElement.dataset.theme = storedTheme;
themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ddc-theme", next);
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    const name = tab.dataset.tab;
    document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("is-active", item === tab));
    document.querySelectorAll(".tab-panel").forEach((panel) =>
      panel.classList.toggle("is-active", panel.dataset.panel === name),
    );
  });
});

changesPanel.addEventListener("click", (event) => {
  const button = event.target.closest("[data-diff-mode]");
  if (!button) {
    return;
  }
  const nextMode = button.dataset.diffMode;
  if (nextMode === diffMode) {
    return;
  }
  diffMode = nextMode;
  localStorage.setItem("ddc-diff-mode", diffMode);
  renderChanges(currentComparison?.changes || []);
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
  currentComparison = report.comparison;
  const comparison = report.comparison;
  reportTitle.textContent = `${comparison.old_filename} → ${comparison.new_filename}`;
  reportDate.textContent = `Создан: ${formatDate(report.created_at)}`;
  renderMeta(comparison);
  renderStats(comparison.stats);
  renderFeed(report.report);
  renderChanges(comparison.changes);
}

function activateTab(name) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("is-active", tab.dataset.tab === name));
  document.querySelectorAll(".tab-panel").forEach((panel) =>
    panel.classList.toggle("is-active", panel.dataset.panel === name),
  );
}

function gotoChange(changeId) {
  activateTab("changes");
  const row = document.getElementById(`change-${changeId}`);
  if (!row) {
    return;
  }
  row.scrollIntoView({ behavior: "smooth", block: "center" });
  row.classList.add("is-highlighted");
  setTimeout(() => row.classList.remove("is-highlighted"), 1800);
}

summaryPanel.addEventListener("click", (event) => {
  const link = event.target.closest("[data-goto]");
  if (!link) {
    return;
  }
  gotoChange(link.dataset.goto);
});

function renderMeta(comparison) {
  resultsMeta.innerHTML = `
    <a class="file-chip old" href="/documents.html?id=${encodeURIComponent(comparison.old_document_id)}">
      <span class="dot"></span>${escapeHtml(comparison.old_filename)}
    </a>
    <span class="meta-arrow">→</span>
    <a class="file-chip new" href="/documents.html?id=${encodeURIComponent(comparison.new_document_id)}">
      <span class="dot"></span>${escapeHtml(comparison.new_filename)}
    </a>
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

function renderFeed(report) {
  const changes = report.changes || [];
  const riskCount = changes.filter((item) => item.financial_risk).length;
  feedCount.hidden = !changes.length;
  feedCount.textContent = changes.length;

  const riskLevel = report.overall_risk_level || "low";
  const levelClass = `lvl-${String(riskLevel).toLowerCase()}`;
  summaryPanel.innerHTML = `
    <div class="stack">
      <div class="risk-banner">
        <div class="rb-main">
          <span class="rb-label">Саммари</span>
          <span class="rb-text">${escapeHtml(report.summary)}</span>
        </div>
        <span class="level-badge ${levelClass}"><span class="dot"></span>${escapeHtml(formatRiskLevelBadge(riskLevel))}</span>
      </div>
      ${riskCount ? `<p class="feed-sub">Финансовых рисков: <b>${riskCount}</b> из ${changes.length} изменений.</p>` : ""}
      ${
        changes.length
          ? changes.map(renderFeedItem).join("")
          : `<p class="feed-sub">Существенных изменений не найдено.</p>`
      }
      ${
        (report.recommended_review_points || []).length
          ? `<h3 class="section-title">Что проверить</h3><ul class="review-list">${report.recommended_review_points
              .map((point) => `<li>${escapeHtml(point)}</li>`)
              .join("")}</ul>`
          : ""
      }
      <span class="provider-tag">${escapeHtml(report.provider)}${report.model ? ` · ${escapeHtml(report.model)}` : ""}</span>
    </div>
  `;
}

function renderFeedItem(item) {
  const ids = item.source_change_ids || [];
  const proof = ids.length
    ? `<button type="button" class="proof-link" data-goto="${escapeHtml(ids[0])}">Показать в сравнении →</button>`
    : "";
  const badge = item.financial_risk
    ? `<span class="fin-badge">₽ финансовый риск${item.risk_type ? ` · ${escapeHtml(item.risk_type)}` : ""}</span>`
    : "";
  return `
    <div class="feed-item${item.financial_risk ? " is-financial" : ""}">
      <div class="feed-row">
        <p class="feed-desc">${escapeHtml(item.description)}</p>
        ${badge}
      </div>
      ${item.estimated_impact ? `<div class="impact">${escapeHtml(item.estimated_impact)}</div>` : ""}
      ${proof}
    </div>
  `;
}

function renderChanges(changes) {
  const visibleChanges =
    diffMode === "diff" ? changes.filter((change) => change.change_type !== "unchanged") : changes;
  changeCount.hidden = !visibleChanges.length;
  changeCount.textContent = visibleChanges.length;
  if (!visibleChanges.length) {
    changesPanel.innerHTML = `${renderDiffToolbar()}<div class="risk-banner"><span class="rb-text">Отличия не найдены.</span></div>`;
    return;
  }
  changesPanel.innerHTML = `${renderDiffToolbar()}<div class="diff-view diff-view-${escapeHtml(diffMode)}">${visibleChanges
    .map(renderChange)
    .join("")}</div>`;
}

function renderChange(change) {
  const oldText = change.old_block ? change.old_block.text : "";
  const newText = change.new_block ? change.new_block.text : "";
  const isTable = change.old_block?.kind === "table_row" || change.new_block?.kind === "table_row";
  if (diffMode === "split" && change.change_type === "modified") {
    return `
      <div id="change-${escapeHtml(change.change_id)}" class="diff-row diff-row-${change.change_type} diff-row-split">
        <div class="diff-split">
          <div class="diff-side diff-old">${renderDiffSide(change, "old", oldText, isTable)}</div>
          <div class="diff-side diff-new">${renderDiffSide(change, "new", newText, isTable)}</div>
        </div>
      </div>
    `;
  }

  const content = renderUnifiedChange(change, oldText, newText, isTable);
  return `
    <div id="change-${escapeHtml(change.change_id)}" class="diff-row diff-row-${change.change_type}">
      <div class="diff-single">${content}</div>
    </div>
  `;
}

function renderUnifiedChange(change, oldText, newText, isTable) {
  if (change.change_type === "added") {
    return renderSingleBlock(newText, isTable, "added");
  }
  if (change.change_type === "removed") {
    return renderSingleBlock(oldText, isTable, "removed");
  }
  if (change.change_type === "unchanged") {
    return renderSingleBlock(oldText || newText, isTable, "unchanged");
  }
  return renderUnifiedDiff(change, isTable);
}

function renderDiffSide(change, side, text, isTable) {
  if (!text) {
    return `<span class="diff-empty">&nbsp;</span>`;
  }
  if (change.change_type === "modified" && change.word_diff && change.word_diff.length) {
    return `<div class="inline-diff">${renderInlineDiff(change.word_diff, side)}</div>`;
  }
  if (isTable) {
    return renderTableRow(text, side, change.change_type);
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

function renderUnifiedDiff(change, isTable) {
  if (isTable) {
    return renderUnifiedTable(change);
  }
  return `<div class="diff-text diff-text-unified">${renderUnifiedSegments(change.word_diff)}</div>`;
}

function renderUnifiedSegments(segments) {
  return segments
    .map((segment) => {
      const cls = escapeHtml(segment.diff_type);
      if (segment.diff_type === "equal") {
        return `<span class="equal">${escapeHtml(segment.text)}</span>`;
      }
      return `<span class="${cls}">${escapeHtml(segment.text)}</span>`;
    })
    .join(" ");
}

function renderSingleBlock(text, isTable, tone = "unchanged") {
  if (isTable) {
    return renderTableRow(text, "single", tone);
  }
  return `<div class="diff-text diff-text-single diff-text-${escapeHtml(tone)}">${escapeHtml(text)}</div>`;
}

function renderUnifiedTable(change) {
  const oldCells = parseTableCells(change.old_block?.text || "");
  const newCells = parseTableCells(change.new_block?.text || "");
  const cellCount = Math.max(oldCells.length, newCells.length);
  const cells = Array.from({ length: cellCount }, (_, index) => {
    const oldCell = oldCells[index] || "";
    const newCell = newCells[index] || "";
    if (oldCell === newCell) {
      return `<td><span class="equal">${escapeHtml(oldCell || newCell)}</span></td>`;
    }
    const pieces = [];
    if (oldCell) {
      pieces.push(`<span class="removed">${escapeHtml(oldCell)}</span>`);
    }
    if (newCell) {
      pieces.push(`<span class="added">${escapeHtml(newCell)}</span>`);
    }
    return `<td>${pieces.join(" ")}</td>`;
  });
  return `<table class="diff-table diff-table-unified"><tbody><tr>${cells.join("")}</tr></tbody></table>`;
}

function renderTableRow(text, side, changeType) {
  const cells = parseTableCells(text);
  if (cells.length < 2) {
    return `<div class="diff-text">${escapeHtml(text)}</div>`;
  }
  return `<table class="diff-table diff-table-${escapeHtml(changeType)} diff-table-${escapeHtml(side)}"><tbody><tr>${cells
    .map((cell) => `<td>${escapeHtml(cell)}</td>`)
    .join("")}</tr></tbody></table>`;
}

function renderDiffToolbar() {
  return `
    <div class="diff-toolbar" role="toolbar" aria-label="Режим сравнения">
      <button class="diff-toggle ${diffMode === "full" ? "is-active" : ""}" type="button" data-diff-mode="full">Полный текст</button>
      <button class="diff-toggle ${diffMode === "diff" ? "is-active" : ""}" type="button" data-diff-mode="diff">Только различия</button>
      <button class="diff-toggle ${diffMode === "split" ? "is-active" : ""}" type="button" data-diff-mode="split">Сравнение</button>
    </div>
  `;
}

function parseTableCells(text) {
  return String(text)
    .split("|")
    .map((cell) => cell.trim())
    .filter((cell, index, array) => !(index === 0 && array.length === 1 && !cell));
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

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadReport();
