const historyBox = document.querySelector("#reports");
const refreshReports = document.querySelector("#refreshReports");
const historySearch = document.querySelector("#historySearch");
const historyCountAll = document.querySelector("#historyCountAll");
const historyCountReports = document.querySelector("#historyCountReports");
const historyCountReviews = document.querySelector("#historyCountReviews");
const toasts = document.querySelector("#toasts");
const themeToggle = document.querySelector("#themeToggle");
const filterDocumentId = new URLSearchParams(window.location.search).get("document_id");

const historyState = {
  filter: "all",
  query: filterDocumentId || "",
};

let allHistoryItems = [];

const storedTheme = localStorage.getItem("ddc-theme");
if (storedTheme) document.documentElement.dataset.theme = storedTheme;
themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ddc-theme", next);
});

historySearch.value = historyState.query;
historySearch.addEventListener("input", () => {
  historyState.query = historySearch.value.trim();
  renderHistory();
});

document.querySelectorAll(".history-filter").forEach((button) => {
  button.addEventListener("click", () => {
    historyState.filter = button.dataset.filter;
    document.querySelectorAll(".history-filter").forEach((item) =>
      item.classList.toggle("is-active", item === button),
    );
    renderHistory();
  });
});

refreshReports.addEventListener("click", () => {
  loadHistory();
  toast("История обновлена.", "info");
});

async function loadHistory() {
  try {
    const [reportsResponse, reviewsResponse] = await Promise.all([
      fetch("/api/reports"),
      fetch("/api/reviews"),
    ]);
    if (!reportsResponse.ok || !reviewsResponse.ok) {
      throw new Error("History request failed");
    }
    const reports = await reportsResponse.json();
    const reviews = await reviewsResponse.json();
    allHistoryItems = [
      ...reports.map((report) => normalizeComparison(report)),
      ...reviews.map((review) => normalizeReview(review)),
    ].sort((left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime());
    updateFilterCounts(allHistoryItems);
    renderHistory();
  } catch {
    historyBox.className = "reports-list empty";
    historyBox.innerHTML = `<p class="empty-note">Не удалось загрузить историю.</p>`;
  }
}

function updateFilterCounts(items) {
  const counts = {
    all: items.length,
    reports: items.filter((item) => item.kind === "report").length,
    reviews: items.filter((item) => item.kind === "review").length,
  };
  setCount(historyCountAll, counts.all);
  setCount(historyCountReports, counts.reports);
  setCount(historyCountReviews, counts.reviews);
}

function setCount(element, value) {
  element.hidden = !value;
  element.textContent = value;
}

function renderHistory() {
  const filtered = allHistoryItems.filter((item) => {
    if (historyState.filter !== "all" && item.kind !== historyState.filter) {
      return false;
    }
    if (filterDocumentId && !item.document_ids.includes(filterDocumentId)) {
      return false;
    }
    if (!historyState.query) {
      return true;
    }
    return item.search_text.includes(historyState.query.toLowerCase());
  });

  if (!filtered.length) {
    historyBox.className = "reports-list empty";
    historyBox.innerHTML = `<p class="empty-note">${
      allHistoryItems.length ? "Ничего не найдено." : "Пока истории нет."
    }</p>`;
    return;
  }

  historyBox.className = "reports-list";
  historyBox.innerHTML = filtered.map(renderHistoryItem).join("");
  historyBox.querySelectorAll("[data-share-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(new URL(button.dataset.shareUrl, window.location.origin).toString());
      toast("Ссылка скопирована.", "ok");
    });
  });
}

function renderHistoryItem(item) {
  const url = escapeHtml(item.url);
  const badgeClass = item.kind === "report" ? "report" : "review";
  return `
    <article class="report-item history-item">
      <span class="history-badge ${badgeClass}">${escapeHtml(item.kind_label)}</span>
      <a class="report-main" href="${url}">
        <strong>${escapeHtml(item.title)}</strong>
        <span>${escapeHtml(item.meta)}</span>
      </a>
      <div class="report-actions">
        <button class="btn-mini" type="button" data-share-url="${escapeHtml(item.url)}">Поделиться</button>
        <a class="btn-mini btn-mini-primary" href="${url}">Открыть</a>
      </div>
    </article>
  `;
}

function normalizeComparison(report) {
  return {
    kind: "report",
    kind_label: "Сравнение",
    created_at: report.created_at,
    title: `${report.old_filename} → ${report.new_filename}`,
    meta: `${formatDate(report.created_at)} · ${report.modified} изменено · ${report.risk_count} рисков`,
    url: report.report_url,
    document_ids: [report.old_document_id, report.new_document_id],
    search_text: [
      "сравнение",
      report.old_filename,
      report.new_filename,
      report.old_document_id,
      report.new_document_id,
      report.report_id,
      report.risk_level,
      String(report.modified),
      String(report.risk_count),
      formatDate(report.created_at),
    ]
      .join(" ")
      .toLowerCase(),
  };
}

function normalizeReview(review) {
  return {
    kind: "review",
    kind_label: "Ревью",
    created_at: review.created_at,
    title: review.filename,
    meta: `${formatDate(review.created_at)} · ${review.blocks_count} блоков · ${review.risk_count} рисков`,
    url: review.review_url,
    document_ids: [review.document_id],
    search_text: [
      "ревью",
      review.filename,
      review.document_id,
      review.review_id,
      review.risk_level,
      String(review.blocks_count),
      String(review.risk_count),
      formatDate(review.created_at),
    ]
      .join(" ")
      .toLowerCase(),
  };
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

loadHistory();
