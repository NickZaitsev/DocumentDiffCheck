from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_documents_page_exposes_search_controls() -> None:
    html = (ROOT / "frontend" / "documents.html").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'id="documentsSearch"' in html
    assert 'type="search"' in html
    assert 'aria-label="Поиск по документам"' in html
    assert ".documents-search" in styles


def test_documents_search_filters_by_document_metadata() -> None:
    script = (ROOT / "frontend" / "documents.js").read_text(encoding="utf-8")

    assert "let allDocuments = [];" in script
    assert 'documentsSearch.addEventListener("input"' in script
    assert "renderFilteredDocuments()" in script
    assert "filterDocuments(allDocuments, query)" in script
    assert "Ничего не найдено." in script

    for searchable_field in (
        "document.label",
        "document.filename",
        "document.document_id",
        "displayDocumentId(document.document_id)",
        "formatDate(document.created_at)",
        "formatBytes(document.size_bytes)",
    ):
        assert searchable_field in script
