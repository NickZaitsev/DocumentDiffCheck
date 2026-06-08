from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, ValidationError

from src import config
from src.domain.exceptions import DocumentValidationError, ReportNotFoundError
from src.infrastructure.atomic_json import locked, update_json_index, write_json_atomic
from src.schemas.api import (
    CompareResponse,
    ComparisonReportOut,
    ComparisonReportSummaryOut,
)

logger = logging.getLogger(__name__)


class ComparisonReportRecord(BaseModel):
    report_id: str
    created_at: datetime
    response: CompareResponse

    def to_report(self) -> ComparisonReportOut:
        return ComparisonReportOut(
            report_id=self.report_id,
            report_url=_report_url(self.report_id),
            created_at=self.created_at,
            comparison=self.response.comparison,
            report=self.response.report,
        )

    def to_summary(self) -> ComparisonReportSummaryOut:
        stats = self.response.comparison.stats
        report = self.response.report
        risk_count = sum(item.financial_risk for item in report.changes)
        return ComparisonReportSummaryOut(
            report_id=self.report_id,
            report_url=_report_url(self.report_id),
            created_at=self.created_at,
            old_document_id=self.response.comparison.old_document_id,
            new_document_id=self.response.comparison.new_document_id,
            old_filename=self.response.comparison.old_filename,
            new_filename=self.response.comparison.new_filename,
            added=stats.added,
            removed=stats.removed,
            modified=stats.modified,
            risk_count=risk_count,
            risk_level=report.overall_risk_level,
        )


class LocalComparisonReportRepository:
    def __init__(self, data_dir: Path | None = None) -> None:
        self._reports_dir = (data_dir or config.DATA_DIR) / "reports"
        self._index_path = self._reports_dir / "index.json"
        self._reports_dir.mkdir(parents=True, exist_ok=True)

    def save(self, response: CompareResponse) -> ComparisonReportOut:
        report_id = str(uuid4())
        record = ComparisonReportRecord(
            report_id=report_id,
            created_at=datetime.now(UTC),
            response=response.model_copy(
                update={
                    "report_id": report_id,
                    "report_url": _report_url(report_id),
                }
            ),
        )
        update_json_index(
            self._index_path,
            load=self._load_records,
            save=self._save_records,
            mutate=lambda records: {**records, record.report_id: record},
        )
        return record.to_report()

    def get(self, report_id: str) -> ComparisonReportOut:
        record = self._load_records().get(report_id)
        if record is None:
            raise ReportNotFoundError(f"Report {report_id} was not found")
        return record.to_report()

    def list(self) -> tuple[ComparisonReportSummaryOut, ...]:
        return tuple(
            record.to_summary()
            for record in sorted(
                self._load_records().values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
        )

    def list_by_document(self, document_id: str) -> tuple[ComparisonReportSummaryOut, ...]:
        return tuple(
            record.to_summary()
            for record in sorted(
                self._load_records().values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
            if record.response.comparison.old_document_id == document_id
            or record.response.comparison.new_document_id == document_id
        )

    def _load_records(self) -> dict[str, ComparisonReportRecord]:
        with locked(self._index_path):
            if not self._index_path.exists():
                return {}
            raw = json.loads(self._index_path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise DocumentValidationError("Report index is malformed")
            records: dict[str, ComparisonReportRecord] = {}
            for item in raw:
                try:
                    record = ComparisonReportRecord.model_validate(item)
                except ValidationError:
                    logger.warning("Skipping report record with incompatible schema")
                    continue
                records[record.report_id] = record
            return records

    def _save_records(self, records: dict[str, ComparisonReportRecord]) -> None:
        payload = [
            record.model_dump(mode="json")
            for record in sorted(
                records.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
        ]
        write_json_atomic(self._index_path, payload)


def _report_url(report_id: str) -> str:
    return f"/report.html?id={report_id}"
