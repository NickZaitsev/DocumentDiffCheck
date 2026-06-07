const reportsBox = document.querySelector("#reports");
const refreshReports = document.querySelector("#refreshReports");
const toasts = document.querySelector("#toasts");
const themeToggle = document.querySelector("#themeToggle");

const storedTheme = localStorage.getItem("ddc-theme");
if (storedTheme) document.documentElement.dataset.theme = storedTheme;
themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ddc-theme", next);
});

refreshReports.addEventListener("click", () => {
  loadReports();
  toast("История сравнений обновлена.", "info");
});

async function loadReports() {
  try {
    const response = await fetch("/api/reports");
    const reports = await response.json();
    renderReports(reports);
  } catch {
    reportsBox.className = "reports-list empty";
    reportsBox.innerHTML = `<p class="empty-note">Не удалось загрузить историю сравнений.</p>`;
  }
}

function renderReports(reports) {
  if (!reports.length) {
    reportsBox.className = "reports-list empty";
    reportsBox.innerHTML = `<p class="empty-note">Пока отчетов нет.</p>`;
    return;
  }

  reportsBox.className = "reports-list";
  reportsBox.innerHTML = reports
    .map(
      (report) => `
        <article class="report-item">
          <div class="report-main">
            <strong>${escapeHtml(report.old_filename)} → ${escapeHtml(report.new_filename)}</strong>
            <span>${formatDate(report.created_at)} · ${report.modified} изменено · ${report.risk_count} рисков</span>
          </div>
          <div class="report-actions">
            <button class="btn-mini" type="button" data-share-url="${escapeHtml(report.report_url)}">Поделиться</button>
            <a class="btn-mini btn-mini-primary" href="${escapeHtml(report.report_url)}">Открыть</a>
          </div>
        </article>
      `,
    )
    .join("");

  reportsBox.querySelectorAll("[data-share-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(new URL(button.dataset.shareUrl, window.location.origin).toString());
      toast("Ссылка на отчет скопирована.", "ok");
    });
  });
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

loadReports();
