from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_selected_dropzone_hides_upload_prompt() -> None:
    script = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert 'renderSelectedFile("Локальный файл", file.name)' in script
    assert 'renderSelectedFile("Загруженный документ", storedDocument.label' in script
    assert ".dropzone.has-file .dz-text" in styles
    assert "display: none;" in styles[styles.index(".dropzone.has-file .dz-text") :]


def test_selected_dropzone_uses_structured_file_summary() -> None:
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")

    assert ".dz-file-kind" in styles
    assert ".dz-file-name" in styles
    assert ".dz-file-meta" in styles
