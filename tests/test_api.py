from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from src import config
from src.api.app import create_app


def test_compare_uploads_returns_diff_summary_and_risks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ())
    client = TestClient(create_app())
    old_path = Path("samples/dogovor_postavki_v1.docx")
    new_path = Path("samples/dogovor_postavki_v2.docx")

    with old_path.open("rb") as old_file, new_path.open("rb") as new_file:
        response = client.post(
            "/api/comparisons/upload",
            files={
                "old_file": (
                    old_path.name,
                    old_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
                "new_file": (
                    new_path.name,
                    new_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["comparison"]["comparison_id"]
    assert payload["comparison"]["changes"]
    assert payload["summary"]["plain_language_summary"]
    assert "risk_assessment" in payload
