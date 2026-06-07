from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from src import config
from src.domain.exceptions import DocumentValidationError, ReviewNotFoundError
from src.schemas.api import (
    DocumentReviewOut,
    DocumentReviewResponse,
    DocumentReviewSummaryOut,
)


class ReviewRecord(BaseModel):
    review_id: str
    created_at: datetime
    response: DocumentReviewResponse

    def to_review(self) -> DocumentReviewOut:
        return DocumentReviewOut(
            review_id=self.review_id,
            review_url=_review_url(self.review_id),
            created_at=self.created_at,
            document=self.response.document,
            blocks_count=self.response.blocks_count,
            summary=self.response.summary,
            risk_assessment=self.response.risk_assessment,
        )

    def to_summary(self) -> DocumentReviewSummaryOut:
        return DocumentReviewSummaryOut(
            review_id=self.review_id,
            review_url=_review_url(self.review_id),
            created_at=self.created_at,
            document_id=self.response.document.document_id,
            filename=self.response.document.filename,
            blocks_count=self.response.blocks_count,
            risk_count=len(self.response.risk_assessment.risks),
            risk_level=self.response.risk_assessment.overall_risk_level,
        )


class LocalDocumentReviewRepository:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._reviews_dir = (data_dir or config.DATA_DIR) / "reviews"
        self._index_path = self._reviews_dir / "index.json"
        self._reviews_dir.mkdir(parents=True, exist_ok=True)

    def save(self, response: DocumentReviewResponse) -> DocumentReviewOut:
        review_id = str(uuid4())
        record = ReviewRecord(
            review_id=review_id,
            created_at=datetime.now(UTC),
            response=response.model_copy(
                update={
                    "review_id": review_id,
                    "review_url": _review_url(review_id),
                }
            ),
        )
        records = self._load_records()
        records[record.review_id] = record
        self._save_records(records)
        return record.to_review()

    def get(self, review_id: str) -> DocumentReviewOut:
        record = self._load_records().get(review_id)
        if record is None:
            raise ReviewNotFoundError(f"Review {review_id} was not found")
        return record.to_review()

    def list(self) -> tuple[DocumentReviewSummaryOut, ...]:
        return tuple(
            record.to_summary()
            for record in sorted(
                self._load_records().values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
        )

    def list_by_document(self, document_id: str) -> tuple[DocumentReviewSummaryOut, ...]:
        return tuple(
            record.to_summary()
            for record in sorted(
                self._load_records().values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
            if record.response.document.document_id == document_id
        )

    def _load_records(self) -> dict[str, ReviewRecord]:
        if not self._index_path.exists():
            return {}
        raw = json.loads(self._index_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise DocumentValidationError("Review index is malformed")
        records = [ReviewRecord.model_validate(item) for item in raw]
        return {record.review_id: record for record in records}

    def _save_records(self, records: dict[str, ReviewRecord]) -> None:
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


def _review_url(review_id: str) -> str:
    return f"/review-report.html?id={review_id}"
