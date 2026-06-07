const documentsPageList = document.querySelector("#documentsPageList");
const refreshDocumentsPage = document.querySelector("#refreshDocumentsPage");
const toasts = document.querySelector("#toasts");
const themeToggle = document.querySelector("#themeToggle");

const storedTheme = localStorage.getItem("ddc-theme");
if (storedTheme) document.documentElement.dataset.theme = storedTheme;
themeToggle.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("ddc-theme", next);
});

refreshDocumentsPage.addEventListener("click", () => {
  loadDocuments();
  toast("Список документов обновлен.", "info");
});

async function loadDocuments() {
  try {
    const response = await fetch("/api/documents");
    const documents = sortDocumentsNewestFirst(await response.json());
    renderDocuments(withDisplayLabels(documents));
  } catch {
    documentsPageList.className = "documents page-documents empty";
    documentsPageList.innerHTML = `<p class="empty-note">Не удалось загрузить документы.</p>`;
  }
}

function renderDocuments(documents) {
  if (!documents.length) {
    documentsPageList.className = "documents page-documents empty";
    documentsPageList.innerHTML = `<p class="empty-note">Пока документов нет.</p>`;
    return;
  }

  const selectedId = new URLSearchParams(window.location.search).get("id");
  const fileIcon = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>`;
  documentsPageList.className = "documents page-documents";
  documentsPageList.innerHTML = documents
    .map(
      (doc) => `
        <article class="document-item ${doc.document_id === selectedId ? "is-selected" : ""}" id="document-${escapeHtml(doc.document_id)}">
          <span class="doc-icon" aria-hidden="true">${fileIcon}</span>
          <div class="doc-body">
            <strong title="${escapeHtml(doc.label)}">${escapeHtml(doc.label)}</strong>
            <div class="doc-meta">${formatDate(doc.created_at)} · ${formatBytes(doc.size_bytes)}</div>
            <div class="doc-id" title="${escapeHtml(doc.document_id)}">Код: ${escapeHtml(documentCode(doc.document_id))}</div>
          </div>
          <button class="copy-id-btn" type="button" data-copy-id="${escapeHtml(doc.document_id)}" title="Скопировать ID" aria-label="Скопировать ID">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
          </button>
        </article>
      `,
    )
    .join("");

  documentsPageList.querySelectorAll("[data-copy-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      await navigator.clipboard.writeText(button.dataset.copyId);
      toast("Document ID скопирован.", "ok");
    });
  });

  if (selectedId) {
    document.querySelector(`#document-${CSS.escape(selectedId)}`)?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  }
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

function sortDocumentsNewestFirst(documents) {
  return [...documents].sort(
    (left, right) => new Date(right.created_at).getTime() - new Date(left.created_at).getTime(),
  );
}

function documentCode(value) {
  return `DOC-${String(value).slice(-4).toUpperCase()}`;
}

function formatBytes(bytes) {
  if (!bytes) return "0 КБ";
  const kb = bytes / 1024;
  if (kb < 1024) return `${Math.max(1, Math.round(kb))} КБ`;
  return `${(kb / 1024).toFixed(1)} МБ`;
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
