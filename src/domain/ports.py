from __future__ import annotations

from pathlib import Path
from typing import Protocol

from src.domain.entities import ComparisonResult, ParsedDocument, StoredDocument
from src.schemas.insights import LegalSummary, RiskAssessment


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
    def generate_summary(self, comparison: ComparisonResult) -> LegalSummary:
        """Generate lawyer-friendly structured summary for a comparison."""

    def assess_risks(self, comparison: ComparisonResult) -> RiskAssessment:
        """Extract financial risks from changed clauses."""


class FileHasher(Protocol):
    def sha256(self, path: Path) -> str:
        """Return the SHA-256 hash of a local file."""

