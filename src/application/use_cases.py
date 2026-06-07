from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src import config
from src.domain.comparison import DocumentComparisonService
from src.domain.entities import ComparisonResult, ParsedDocument, StoredDocument
from src.domain.exceptions import DocumentValidationError
from src.domain.ports import DocumentParser, DocumentRepository, InsightProvider
from src.schemas.api import CompareResponse, ComparisonOut, DocumentOut, DocumentReviewResponse
from src.schemas.insights import LegalSummary, RiskAssessment


@dataclass(frozen=True, slots=True)
class ComparisonAnalysis:
    comparison: ComparisonResult
    summary: LegalSummary
    risk_assessment: RiskAssessment

    def to_response(self) -> CompareResponse:
        return CompareResponse(
            comparison=ComparisonOut.from_domain(self.comparison),
            summary=self.summary,
            risk_assessment=self.risk_assessment,
        )


@dataclass(frozen=True, slots=True)
class DocumentReviewAnalysis:
    document: StoredDocument
    parsed_document: ParsedDocument
    summary: LegalSummary
    risk_assessment: RiskAssessment

    def to_response(self) -> DocumentReviewResponse:
        return DocumentReviewResponse(
            document=DocumentOut.from_domain(self.document),
            blocks_count=len(self.parsed_document.blocks),
            summary=self.summary,
            risk_assessment=self.risk_assessment,
        )


class UploadDocumentUseCase:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    def execute(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> StoredDocument:
        self._validate_upload(filename=filename, content=content)
        return self._repository.save(filename, content_type, content)

    def _validate_upload(self, *, filename: str, content: bytes) -> None:
        if not filename.strip():
            raise DocumentValidationError("Filename is required")
        suffix = Path(filename).suffix.lower()
        if suffix not in config.SUPPORTED_EXTENSIONS:
            raise DocumentValidationError("Only DOCX uploads are supported")
        if not content:
            raise DocumentValidationError("Uploaded document is empty")
        if len(content) > config.MAX_UPLOAD_BYTES:
            raise DocumentValidationError(
                f"Uploaded document exceeds {config.MAX_UPLOAD_BYTES} bytes"
            )


class CompareDocumentsUseCase:
    def __init__(
        self,
        *,
        repository: DocumentRepository,
        parser: DocumentParser,
        comparison_service: DocumentComparisonService,
        insight_provider: InsightProvider,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._comparison_service = comparison_service
        self._insight_provider = insight_provider

    def execute_by_id(
        self,
        *,
        old_document_id: str,
        new_document_id: str,
    ) -> ComparisonAnalysis:
        old_document = self._repository.get(old_document_id)
        new_document = self._repository.get(new_document_id)
        return self._compare_stored_documents(old_document, new_document)

    def execute_uploads(
        self,
        *,
        old_filename: str,
        old_content_type: str,
        old_content: bytes,
        new_filename: str,
        new_content_type: str,
        new_content: bytes,
    ) -> ComparisonAnalysis:
        uploader = UploadDocumentUseCase(self._repository)
        old_document = uploader.execute(
            filename=old_filename,
            content_type=old_content_type,
            content=old_content,
        )
        new_document = uploader.execute(
            filename=new_filename,
            content_type=new_content_type,
            content=new_content,
        )
        return self._compare_stored_documents(old_document, new_document)

    def _compare_stored_documents(
        self,
        old_document: StoredDocument,
        new_document: StoredDocument,
    ) -> ComparisonAnalysis:
        old_parsed = self._parser.parse(old_document)
        new_parsed = self._parser.parse(new_document)
        comparison = self._comparison_service.compare(old_parsed, new_parsed)
        summary = self._insight_provider.generate_summary(comparison)
        risks = self._insight_provider.assess_risks(comparison)
        return ComparisonAnalysis(
            comparison=comparison,
            summary=summary,
            risk_assessment=risks,
        )


class ReviewDocumentUseCase:
    def __init__(
        self,
        *,
        repository: DocumentRepository,
        parser: DocumentParser,
        insight_provider: InsightProvider,
    ) -> None:
        self._repository = repository
        self._parser = parser
        self._insight_provider = insight_provider

    def execute_by_id(self, *, document_id: str) -> DocumentReviewAnalysis:
        document = self._repository.get(document_id)
        return self._review_stored_document(document)

    def execute_upload(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> DocumentReviewAnalysis:
        uploader = UploadDocumentUseCase(self._repository)
        document = uploader.execute(
            filename=filename,
            content_type=content_type,
            content=content,
        )
        return self._review_stored_document(document)

    def _review_stored_document(self, document: StoredDocument) -> DocumentReviewAnalysis:
        parsed_document = self._parser.parse(document)
        summary = self._insight_provider.generate_document_summary(parsed_document)
        risks = self._insight_provider.assess_document_risks(parsed_document)
        return DocumentReviewAnalysis(
            document=document,
            parsed_document=parsed_document,
            summary=summary,
            risk_assessment=risks,
        )

