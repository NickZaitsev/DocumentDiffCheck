from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.application.use_cases import UploadDocumentUseCase
from src.domain.entities import StoredDocument


class RecordingRepository:
    def __init__(self) -> None:
        self.saved: tuple[str, str, bytes] | None = None

    def save(self, filename: str, content_type: str, content: bytes) -> StoredDocument:
        self.saved = (filename, content_type, content)
        return StoredDocument(
            document_id="document-1",
            filename=filename,
            content_type=content_type,
            path=Path("document-1.docx"),
            size_bytes=len(content),
            created_at=datetime(2026, 6, 7, tzinfo=UTC),
        )


def test_upload_document_use_case_saves_valid_docx() -> None:
    repository = RecordingRepository()
    use_case = UploadDocumentUseCase(repository)

    result = use_case.execute(
        filename="contract.docx",
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        content=b"docx-bytes",
    )

    assert result.document_id == "document-1"
    assert repository.saved == (
        "contract.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"docx-bytes",
    )
