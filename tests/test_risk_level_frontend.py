from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_risk_level_badges_are_russian_and_explicit() -> None:
    scripts = [
        ROOT / "frontend" / "app.js",
        ROOT / "frontend" / "report.js",
        ROOT / "frontend" / "review.js",
        ROOT / "frontend" / "review-report.js",
    ]

    for script_path in scripts:
        script = script_path.read_text(encoding="utf-8")

        assert "function formatRiskLevelBadge" in script
        assert 'return `Риск: ${riskLevelLabel(level)}`;' in script
        assert 'low: "низкий"' in script
        assert 'medium: "средний"' in script
        assert 'high: "высокий"' in script


def test_risk_level_badges_do_not_render_raw_low_label() -> None:
    scripts = [
        ROOT / "frontend" / "app.js",
        ROOT / "frontend" / "report.js",
        ROOT / "frontend" / "review.js",
        ROOT / "frontend" / "review-report.js",
    ]

    for script_path in scripts:
        script = script_path.read_text(encoding="utf-8")

        assert "<span class=\"dot\"></span>LOW" not in script
        assert "toUpperCase()" not in script
