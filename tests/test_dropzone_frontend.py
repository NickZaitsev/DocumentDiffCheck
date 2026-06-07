from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_selected_dropzone_hides_upload_prompt() -> None:
    script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    review_script = (ROOT / "frontend" / "review.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'renderSelectedFile("Локальный файл", file.name)' in script
    assert 'renderSelectedFile("Загруженный документ", storedDocument.label' in script
    assert 'renderSelectedFile("Локальный файл", file.name)' in review_script
    assert 'renderSelectedFile("Загруженный документ", storedDocument.label' in review_script
    assert ".dropzone.has-file .dz-text" in styles
    rule_start = styles.index(".dropzone.has-file .dz-text")
    rule_end = styles.index("}", rule_start)

    assert "display: none;" in styles[rule_start:rule_end]
    assert ".dropzone.has-file .dz-tag" in styles[rule_start:rule_end]
    assert ".dropzone.has-file .stored-picker" in styles[rule_start:rule_end]


def test_selected_dropzone_uses_structured_file_summary() -> None:
    script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    review_script = (ROOT / "frontend" / "review.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert ".dz-file-kind" in styles
    assert ".dz-file-name" in styles
    assert ".dz-file-meta" in styles
    assert ".dz-clear" in styles
    assert "clearSlotSelection(slot)" in script
    assert "clearDocumentSelection()" in review_script
    assert 'aria-label="Убрать документ"' in script
    assert 'aria-label="Убрать документ"' in review_script
