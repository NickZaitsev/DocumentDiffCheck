from __future__ import annotations

from typing import Protocol

from src.domain.entities import ComparisonResult, ParsedDocument, StoredDocument
from src.schemas.insights import ChangeReport


class DocumentParser(Protocol):
    def parse(self, stored_document: StoredDocument) -> ParsedDocument:
        """Parse a stored document into deterministic structural blocks."""


class DocumentRepository(Protocol):
    def save(self, filename: str, content_type: str, content: bytes) -> StoredDocument:
        """Persist document content and return storage metadata."""

    def get(self, document_id: str) -> StoredDocument:
        """Return storage metadata for a document."""

    def list(self) -> tuple[StoredDocument, ...]:
        """Return known documents."""


class InsightProvider(Protocol):
    def analyze_comparison(self, comparison: ComparisonResult) -> ChangeReport:
        """Produce a unified change feed (with financial flags) for a diff."""

    def analyze_document(self, document: ParsedDocument) -> ChangeReport:
        """Produce a unified findings feed (with financial flags) for one document."""
