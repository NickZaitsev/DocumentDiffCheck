from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_history_page_exposes_search_and_filters() -> None:
    html = (ROOT / "frontend" / "history.html").read_text(encoding="utf-8")
    script = (ROOT / "frontend" / "history.js").read_text(encoding="utf-8")

    assert 'id="historySearch"' in html
    assert 'data-filter="reports"' in html
    assert 'data-filter="reviews"' in html
    assert 'fetch("/api/reports")' in script
    assert 'fetch("/api/reviews")' in script
    assert 'normalizeComparison(report)' in script
    assert 'normalizeReview(review)' in script
    assert 'reports: "report"' in script
    assert 'reviews: "review"' in script


def test_history_report_main_links_to_detail_pages() -> None:
    script = (ROOT / "frontend" / "history.js").read_text(encoding="utf-8")

    assert '<a class="report-main" href="${url}">' in script
    assert 'review-report.html?id=' not in script
    assert 'report.html?id=' not in script


def test_history_buttons_keep_open_after_share() -> None:
    script = (ROOT / "frontend" / "history.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    actions_start = script.index('<div class="report-actions">')
    actions_end = script.index("</div>", actions_start)
    actions_markup = script[actions_start:actions_end]

    assert actions_markup.index("Поделиться") < actions_markup.index("Открыть")
    assert 'class="btn-mini btn-mini-primary"' in actions_markup
    assert ".history-badge.review" in styles
