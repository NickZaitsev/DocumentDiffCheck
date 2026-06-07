const reviewStatus = document.querySelector("#reviewStatus");
const reviewView = document.querySelector("#reviewView");
const reviewTitle = document.querySelector("#reviewTitle");
const reviewDate = document.querySelector("#reviewDate");
const reviewMeta = document.querySelector("#reviewMeta");
const reviewStats = document.querySelector("#reviewStats");
const reviewPanel = document.querySelector("#panel-review");
const risksPanel = document.querySelector("#panel-risks");
const riskCount = document.querySelector("#riskCount");
const shareReview = document.querySelector("#shareReview");
const toasts = document.querySelector("#toasts");
const themeToggle = document.querySelector("#themeToggle");

const reviewId = new URLSearchParams(window.location.search).get("id");

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

shareReview.addEventListener("click", async () => {
  await navigator.clipboard.writeText(window.location.href);
  toast("Ссылка на ревью скопирована.", "ok");
});

async function loadReview() {
  if (!reviewId) {
    showError("Не указан ID ревью.");
    return;
  }
  try {
    const response = await fetch(`/api/reviews/${encodeURIComponent(reviewId)}`);
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.message || payload.error || "Request failed");
    }
    renderReview(payload);
    reviewStatus.hidden = true;
    reviewView.hidden = false;
  } catch (error) {
    showError(error.message);
  }
}

function showError(message) {
  reviewStatus.innerHTML = `<p>${escapeHtml(message)}</p>`;
}

function renderReview(payload) {
  reviewTitle.textContent = payload.document.filename;
  reviewDate.textContent = formatDate(payload.created_at);
  reviewMeta.innerHTML = [
    reviewChip(payload.document.filename),
    reviewChip(displayDocumentId(payload.document.document_id)),
    reviewChip(formatBytes(payload.document.size_bytes)),
  ].join("");
  reviewStats.innerHTML = [
    stat("Блоков", payload.blocks_count, "s-sim"),
    stat("Рисков", payload.risk_assessment.risks.length, payload.risk_assessment.risks.length ? "s-modified" : "s-added"),
    stat("Уровень", payload.risk_assessment.overall_risk_level.toUpperCase(), "s-sim"),
  ].join("");
  renderReviewPanel(payload.summary);
  renderRisks(payload.risk_assessment);
}

function reviewChip(text) {
  return `<span class="file-chip">${escapeHtml(text)}</span>`;
}

function stat(label, value, cls) {
  return `<div class="stat ${cls}"><b>${escapeHtml(String(value))}</b><span>${label}</span></div>`;
}

function renderReviewPanel(summary) {
  reviewPanel.innerHTML = `
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
          <span class="level-badge level-low"><span class="dot"></span>LOW</span>
        </div>
        <span class="provider-tag">${escapeHtml(assessment.provider)}</span>
      </div>
    `;
    return;
  }

  const levelCls = "lvl-" + String(assessment.overall_risk_level).toLowerCase();
  risksPanel.innerHTML = `
    <div class="stack">
      <div class="risk-banner">
        <span class="rb-text">${escapeHtml(assessment.review_recommendation)}</span>
        <span class="level-badge ${levelCls}"><span class="dot"></span>${escapeHtml(assessment.overall_risk_level)}</span>
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

loadReview();
