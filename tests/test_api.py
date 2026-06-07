from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from src import config
from src.api.app import create_app


def test_compare_uploads_returns_diff_summary_and_risks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ())
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DOCUMENT_STORAGE_DIR", tmp_path / "documents")
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
    assert payload["report_id"]
    assert payload["report_url"] == f"/report.html?id={payload['report_id']}"
    assert payload["comparison"]["comparison_id"]
    assert payload["comparison"]["changes"]
    assert payload["summary"]["plain_language_summary"]
    assert "risk_assessment" in payload

    reports_response = client.get("/api/reports")
    assert reports_response.status_code == 200
    reports = reports_response.json()
    assert reports[0]["report_id"] == payload["report_id"]

    report_response = client.get(f"/api/reports/{payload['report_id']}")
    assert report_response.status_code == 200
    assert report_response.json()["comparison"]["comparison_id"] == payload["comparison"]["comparison_id"]


def test_document_download_returns_stored_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ())
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DOCUMENT_STORAGE_DIR", tmp_path / "documents")
    client = TestClient(create_app())
    sample_path = Path("samples/dogovor_postavki_v1.docx")

    with sample_path.open("rb") as sample_file:
        upload_response = client.post(
            "/api/documents",
            files={
                "file": (
                    sample_path.name,
                    sample_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    document_id = upload_response.json()["document_id"]
    response = client.get(f"/api/documents/{document_id}/download")

    assert response.status_code == 200
    assert response.content == sample_path.read_bytes()
    assert sample_path.name in response.headers["content-disposition"]
