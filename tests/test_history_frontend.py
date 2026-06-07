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
