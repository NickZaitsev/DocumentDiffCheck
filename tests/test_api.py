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
    assert payload["report"]["summary"]
    assert "changes" in payload["report"]

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


def test_review_upload_returns_single_document_summary_and_risks(
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
        response = client.post(
            "/api/reviews/upload",
            files={
                "file": (
                    sample_path.name,
                    sample_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["filename"] == sample_path.name
    assert payload["blocks_count"] > 0
    assert payload["review_id"]
    assert payload["review_url"] == f"/review-report.html?id={payload['review_id']}"
    assert payload["report"]["summary"]
    assert "changes" in payload["report"]

    reviews_response = client.get("/api/reviews")
    assert reviews_response.status_code == 200
    reviews = reviews_response.json()
    assert reviews[0]["review_id"] == payload["review_id"]


def test_review_existing_document_by_id(
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
    response = client.post("/api/reviews", json={"document_id": document_id})

    assert response.status_code == 200
    payload = response.json()
    assert payload["document"]["document_id"] == document_id
    assert payload["review_id"]
    assert payload["review_url"] == f"/review-report.html?id={payload['review_id']}"
    assert payload["report"]["provider"] == "fallback"

    review_response = client.get(f"/api/reviews/{payload['review_id']}")
    assert review_response.status_code == 200
    assert review_response.json()["document"]["document_id"] == document_id


def test_document_reports_returns_only_related_comparisons(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ())
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DOCUMENT_STORAGE_DIR", tmp_path / "documents")
    client = TestClient(create_app())

    first_id = _upload_sample_document(client, "first.docx")
    second_id = _upload_sample_document(client, "second.docx")
    third_id = _upload_sample_document(client, "third.docx")

    first_second = client.post(
        "/api/comparisons",
        json={"old_document_id": first_id, "new_document_id": second_id},
    )
    second_third = client.post(
        "/api/comparisons",
        json={"old_document_id": second_id, "new_document_id": third_id},
    )

    assert first_second.status_code == 200
    assert second_third.status_code == 200

    first_reports_response = client.get(f"/api/documents/{first_id}/reports")
    second_reports_response = client.get(f"/api/documents/{second_id}/reports")

    assert first_reports_response.status_code == 200
    assert second_reports_response.status_code == 200

    first_report_ids = {
        report["report_id"] for report in first_reports_response.json()
    }
    second_report_ids = {
        report["report_id"] for report in second_reports_response.json()
    }

    assert first_report_ids == {first_second.json()["report_id"]}
    assert second_report_ids == {
        first_second.json()["report_id"],
        second_third.json()["report_id"],
    }
    assert all(
        first_id in (report["old_document_id"], report["new_document_id"])
        for report in first_reports_response.json()
    )


def test_document_reports_returns_not_found_for_missing_document(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ())
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DOCUMENT_STORAGE_DIR", tmp_path / "documents")
    client = TestClient(create_app())

    response = client.get("/api/documents/missing-document/reports")

    assert response.status_code == 404


def _upload_sample_document(client: TestClient, filename: str) -> str:
    sample_path = Path("samples/dogovor_postavki_v1.docx")
    with sample_path.open("rb") as sample_file:
        response = client.post(
            "/api/documents",
            files={
                "file": (
                    filename,
                    sample_file,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert response.status_code == 200
    return str(response.json()["document_id"])
