from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from src.domain.entities import (
    ChangeType,
    ComparisonResult,
    ComparisonStats,
    DocumentBlock,
    DocumentBlockKind,
    DocumentChange,
    StoredDocument,
    WordDiffSegment,
    WordDiffType,
)
from src.schemas.insights import ChangeReport


class DocumentOut(BaseModel):
    document_id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    @classmethod
    def from_domain(cls, document: StoredDocument) -> DocumentOut:
        return cls(
            document_id=document.document_id,
            filename=document.filename,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            created_at=document.created_at,
        )


class DocumentBlockOut(BaseModel):
    block_id: str
    index: int
    kind: DocumentBlockKind
    text: str

    @classmethod
    def from_domain(cls, block: DocumentBlock | None) -> DocumentBlockOut | None:
        if block is None:
            return None
        return cls(
            block_id=block.block_id,
            index=block.index,
            kind=block.kind,
            text=block.text,
        )


class WordDiffSegmentOut(BaseModel):
    diff_type: WordDiffType
    text: str

    @classmethod
    def from_domain(cls, segment: WordDiffSegment) -> WordDiffSegmentOut:
        return cls(diff_type=segment.diff_type, text=segment.text)


class DocumentChangeOut(BaseModel):
    change_id: str
    change_type: ChangeType
    old_block: DocumentBlockOut | None
    new_block: DocumentBlockOut | None
    similarity: float = Field(ge=0.0, le=1.0)
    word_diff: list[WordDiffSegmentOut]

    @classmethod
    def from_domain(cls, change: DocumentChange) -> DocumentChangeOut:
        return cls(
            change_id=change.change_id,
            change_type=change.change_type,
            old_block=DocumentBlockOut.from_domain(change.old_block),
            new_block=DocumentBlockOut.from_domain(change.new_block),
            similarity=round(change.similarity, 4),
            word_diff=[
                WordDiffSegmentOut.from_domain(segment)
                for segment in change.word_diff
            ],
        )


class ComparisonStatsOut(BaseModel):
    added: int
    removed: int
    modified: int
    unchanged: int
    similarity_score: float

    @classmethod
    def from_domain(cls, stats: ComparisonStats) -> ComparisonStatsOut:
        return cls(
            added=stats.added,
            removed=stats.removed,
            modified=stats.modified,
            unchanged=stats.unchanged,
            similarity_score=stats.similarity_score,
        )


class ComparisonOut(BaseModel):
    comparison_id: str
    old_document_id: str
    new_document_id: str
    old_filename: str
    new_filename: str
    stats: ComparisonStatsOut
    changes: list[DocumentChangeOut]

    @classmethod
    def from_domain(cls, comparison: ComparisonResult) -> ComparisonOut:
        return cls(
            comparison_id=comparison.comparison_id,
            old_document_id=comparison.old_document.document_id,
            new_document_id=comparison.new_document.document_id,
            old_filename=comparison.old_document.filename,
            new_filename=comparison.new_document.filename,
            stats=ComparisonStatsOut.from_domain(comparison.stats),
            changes=[
                DocumentChangeOut.from_domain(change)
                for change in comparison.changes
            ],
        )


class CompareByIdRequest(BaseModel):
    old_document_id: str
    new_document_id: str


class ReviewByIdRequest(BaseModel):
    document_id: str


class CompareResponse(BaseModel):
    report_id: str | None = None
    report_url: str | None = None
    comparison: ComparisonOut
    report: ChangeReport


class DocumentReviewResponse(BaseModel):
    review_id: str | None = None
    review_url: str | None = None
    document: DocumentOut
    blocks_count: int
    report: ChangeReport


class DocumentReviewOut(BaseModel):
    review_id: str
    review_url: str
    created_at: datetime
    document: DocumentOut
    blocks_count: int
    report: ChangeReport

    def to_response(self) -> DocumentReviewResponse:
        return DocumentReviewResponse(
            review_id=self.review_id,
            review_url=self.review_url,
            document=self.document,
            blocks_count=self.blocks_count,
            report=self.report,
        )


class DocumentReviewSummaryOut(BaseModel):
    review_id: str
    review_url: str
    created_at: datetime
    document_id: str
    filename: str
    blocks_count: int
    risk_count: int
    risk_level: str


class ComparisonReportOut(BaseModel):
    report_id: str
    report_url: str
    created_at: datetime
    comparison: ComparisonOut
    report: ChangeReport

    def to_response(self) -> CompareResponse:
        return CompareResponse(
            report_id=self.report_id,
            report_url=self.report_url,
            comparison=self.comparison,
            report=self.report,
        )


class ComparisonReportSummaryOut(BaseModel):
    report_id: str
    report_url: str
    created_at: datetime
    old_document_id: str
    new_document_id: str
    old_filename: str
    new_filename: str
    added: int
    removed: int
    modified: int
    risk_count: int
    risk_level: str

