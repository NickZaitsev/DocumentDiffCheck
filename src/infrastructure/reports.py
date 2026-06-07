from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel

from src import config
from src.domain.exceptions import DocumentValidationError, ReportNotFoundError
from src.schemas.api import (
    CompareResponse,
    ComparisonReportOut,
    ComparisonReportSummaryOut,
)


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
            summary=self.response.summary,
            risk_assessment=self.response.risk_assessment,
        )

    def to_summary(self) -> ComparisonReportSummaryOut:
        stats = self.response.comparison.stats
        risks = self.response.risk_assessment.risks
        return ComparisonReportSummaryOut(
            report_id=self.report_id,
            report_url=_report_url(self.report_id),
            created_at=self.created_at,
            old_filename=self.response.comparison.old_filename,
            new_filename=self.response.comparison.new_filename,
            added=stats.added,
            removed=stats.removed,
            modified=stats.modified,
            risk_count=len(risks),
            risk_level=self.response.risk_assessment.overall_risk_level,
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
        records = self._load_records()
        records[record.report_id] = record
        self._save_records(records)
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

    def _load_records(self) -> dict[str, ComparisonReportRecord]:
        if not self._index_path.exists():
            return {}
        raw = json.loads(self._index_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise DocumentValidationError("Report index is malformed")
        records = [ComparisonReportRecord.model_validate(item) for item in raw]
        return {record.report_id: record for record in records}

    def _save_records(self, records: dict[str, ComparisonReportRecord]) -> None:
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


def _report_url(report_id: str) -> str:
    return f"/report.html?id={report_id}"
