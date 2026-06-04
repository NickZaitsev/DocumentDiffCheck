from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from src import config
from src.domain.entities import StoredDocument
from src.domain.exceptions import DocumentNotFoundError, DocumentValidationError


class DocumentRecord(BaseModel):
    document_id: str
    filename: str
    content_type: str
    path: str
    size_bytes: int

    def to_domain(self) -> StoredDocument:
        return StoredDocument(
            document_id=self.document_id,
            filename=self.filename,
            content_type=self.content_type,
            path=Path(self.path),
            size_bytes=self.size_bytes,
        )


class LocalDocumentRepository:
    def __init__(self, storage_dir: Path = config.DOCUMENT_STORAGE_DIR) -> None:
        self._storage_dir = storage_dir
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
            for record in self._load_records().values()
            if Path(record.path).exists()
        )

    def _load_records(self) -> dict[str, DocumentRecord]:
        if not self._index_path.exists():
            return {}
        raw = json.loads(self._index_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise DocumentValidationError("Document index is malformed")
        records = [DocumentRecord.model_validate(item) for item in raw]
        return {record.document_id: record for record in records}

    def _save_records(self, records: dict[str, DocumentRecord]) -> None:
        payload = [
            record.model_dump(mode="json")
            for record in sorted(records.values(), key=lambda item: item.document_id)
        ]
        self._index_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

