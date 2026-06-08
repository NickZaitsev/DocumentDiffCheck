from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_report_summary_banners_have_summary_heading() -> None:
    report_script = (ROOT / "frontend" / "report.js").read_text(encoding="utf-8")
    review_report_script = (ROOT / "frontend" / "review-report.js").read_text(
        encoding="utf-8"
    )
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert '<span class="rb-label">Саммари</span>' in report_script
    assert '<span class="rb-label">Саммари</span>' in review_report_script
    assert ".risk-banner .rb-label" in styles
