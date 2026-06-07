from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_history_actions_prioritize_open_report_button() -> None:
    script = (ROOT / "frontend" / "history.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    actions_start = script.index('<div class="report-actions">')
    actions_end = script.index("</div>", actions_start)
    actions_markup = script[actions_start:actions_end]

    assert actions_markup.index("Поделиться") < actions_markup.index("Открыть")
    assert 'class="btn-mini btn-mini-primary"' in actions_markup
    assert ".btn-mini-primary" in styles


def test_history_report_main_links_to_report() -> None:
    script = (ROOT / "frontend" / "history.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert '<a class="report-main" href="${escapeHtml(report.report_url)}">' in script
    assert "</a>" in script
    assert ".report-main:hover strong" in styles


def test_history_uses_document_reports_endpoint_when_filtered() -> None:
    script = (ROOT / "frontend" / "history.js").read_text(encoding="utf-8")
    documents_script = (ROOT / "frontend" / "documents.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'get("document_id")' in script
    assert "/api/documents/${encodeURIComponent(filterDocumentId)}/reports" in script
    assert "/history.html?document_id=${encodeURIComponent(doc.document_id)}" in documents_script
    assert ".comparison-history-btn" in styles
