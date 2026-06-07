from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_uploaded_documents_heading_mentions_drag_and_drop() -> None:
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert '<span class="docs-hint">Файлы можно перетаскивать</span>' in index
    assert ".docs-heading" in styles
    assert ".docs-hint" in styles


def test_top_navigation_links_to_single_document_review() -> None:
    index = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    review = (ROOT / "frontend" / "review.html").read_text(encoding="utf-8")
    review_js = (ROOT / "frontend" / "review.js").read_text(encoding="utf-8")

    assert '<a href="/review.html">Ревью документа</a>' in index
    assert '<form id="reviewForm"' in review
    assert 'fetch("/api/reviews/upload"' in review_js
    assert 'fetch("/api/reviews"' in review_js
