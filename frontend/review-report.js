const reviewStatus = document.querySelector("#reviewStatus");
const reviewView = document.querySelector("#reviewView");
const reviewTitle = document.querySelector("#reviewTitle");
const reviewDate = document.querySelector("#reviewDate");
const reviewMeta = document.querySelector("#reviewMeta");
const reviewStats = document.querySelector("#reviewStats");
const reviewPanel = document.querySelector("#panel-review");
const feedCount = document.querySelector("#feedCount");
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
  const report = payload.report;
  const riskCount = (report.changes || []).filter((item) => item.financial_risk).length;
  reviewStats.innerHTML = [
    stat("Блоков", payload.blocks_count, "s-sim"),
    stat("Рисков", riskCount, riskCount ? "s-modified" : "s-added"),
    stat("Риск", riskLevelLabel(report.overall_risk_level), "s-sim"),
  ].join("");
  renderFeed(report);
}

function reviewChip(text) {
  return `<span class="file-chip">${escapeHtml(text)}</span>`;
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
  const levelCls = "lvl-" + String(riskLevel).toLowerCase();
  reviewPanel.innerHTML = `
    <div class="stack">
      <div class="risk-banner">
        <span class="rb-text">${escapeHtml(report.summary)}</span>
        <span class="level-badge ${levelCls}"><span class="dot"></span>${escapeHtml(formatRiskLevelBadge(riskLevel))}</span>
      </div>
      ${riskCount ? `<p class="feed-sub">Финансовых рисков: <b>${riskCount}</b>.</p>` : ""}
      ${
        changes.length
          ? changes.map(renderFeedItem).join("")
          : `<p class="feed-sub">Финансовых рисков не выявлено.</p>`
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

loadReview();
