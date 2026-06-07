from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from src import config
from src.domain.entities import StoredDocument
from src.domain.exceptions import DocumentNotFoundError, DocumentValidationError


class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    content_type: str
    path: str
    size_bytes: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_domain(self) -> StoredDocument:
        return StoredDocument(
            document_id=self.document_id,
            filename=self.filename,
            content_type=self.content_type,
            path=Path(self.path),
            size_bytes=self.size_bytes,
            created_at=self.created_at,
        )


class LocalDocumentRepository:
    def __init__(self, storage_dir: Path | None = None) -> None:
        self._storage_dir = storage_dir or config.DOCUMENT_STORAGE_DIR
        self._index_path = self._storage_dir / "index.json"
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, filename: str, content_type: str, content: bytes) -> StoredDocument:
        suffix = Path(filename).suffix.lower()
        if suffix not in config.SUPPORTED_EXTENSIONS:
            raise DocumentValidationError("Only DOCX uploads are supported")

        document_id = str(uuid4())
        target_path = self._storage_dir / f"{document_id}{suffix}"
        target_path.write_bytes(content)

        record = DocumentRecord(
            document_id=document_id,
            filename=Path(filename).name,
            content_type=content_type or "application/octet-stream",
            path=str(target_path),
            size_bytes=len(content),
            created_at=datetime.now(UTC),
        )
        records = self._load_records()
        records[record.document_id] = record
        self._save_records(records)
        return record.to_domain()

    def get(self, document_id: str) -> StoredDocument:
        records = self._load_records()
        record = records.get(document_id)
        if record is None or not Path(record.path).exists():
            raise DocumentNotFoundError(f"Document {document_id} was not found")
        return record.to_domain()

    def list(self) -> tuple[StoredDocument, ...]:
        return tuple(
            record.to_domain()
            for record in sorted(
                self._load_records().values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
            if Path(record.path).exists()
        )

    def _load_records(self) -> dict[str, DocumentRecord]:
        if not self._index_path.exists():
            return {}
        raw = json.loads(self._index_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise DocumentValidationError("Document index is malformed")
        records = [self._record_from_index_item(item) for item in raw]
        return {record.document_id: record for record in records}

    def _record_from_index_item(self, item: object) -> DocumentRecord:
        if isinstance(item, dict) and "created_at" not in item:
            path = Path(str(item.get("path", "")))
            timestamp = path.stat().st_mtime if path.exists() else 0
            item = {
                **item,
                "created_at": datetime.fromtimestamp(timestamp, UTC),
            }
        return DocumentRecord.model_validate(item)

    def _save_records(self, records: dict[str, DocumentRecord]) -> None:
        payload = [
            record.model_dump(mode="json")
            for record in sorted(
                records.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
        ]
        self._index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

