from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Awaitable
from uuid import uuid4

from fastapi import FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from src import config
from src.application.use_cases import (
    CompareDocumentsUseCase,
    ReviewDocumentUseCase,
    UploadDocumentUseCase,
)
from src.domain.comparison import DocumentComparisonService
from src.domain.exceptions import (
    AIProcessingError,
    ComparisonError,
    DocumentNotFoundError,
    DocumentParsingError,
    DocumentValidationError,
    DomainError,
    ReportNotFoundError,
)
from src.infrastructure.docx_parser import DocxDocumentParser
from src.infrastructure.insights import FallbackInsightProvider, ResilientInsightProvider
from src.infrastructure.reports import LocalComparisonReportRepository
from src.infrastructure.storage import LocalDocumentRepository
from src.integrations.gemini_provider import GeminiInsightProvider
from src.integrations.openrouter_provider import OpenRouterInsightProvider
from src.schemas.api import (
    CompareByIdRequest,
    CompareResponse,
    ComparisonReportOut,
    ComparisonReportSummaryOut,
    DocumentReviewResponse,
    DocumentOut,
    ReviewByIdRequest,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    app = FastAPI(title="Document Diff Check", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_context_middleware)
    app.add_exception_handler(DomainError, domain_error_handler)

    repository = LocalDocumentRepository()
    report_repository = LocalComparisonReportRepository()
    parser = DocxDocumentParser()
    comparison_service = DocumentComparisonService()
    insight_provider = ResilientInsightProvider(
        primary=_build_primary_insight_providers(),
        fallback=FallbackInsightProvider(),
    )
    upload_use_case = UploadDocumentUseCase(repository)
    compare_use_case = CompareDocumentsUseCase(
        repository=repository,
        parser=parser,
        comparison_service=comparison_service,
        insight_provider=insight_provider,
    )
    review_use_case = ReviewDocumentUseCase(
        repository=repository,
        parser=parser,
        insight_provider=insight_provider,
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/documents", response_model=DocumentOut)
    async def upload_document(file: UploadFile = File(...)) -> DocumentOut:
        content = await file.read()
        document = upload_use_case.execute(
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            content=content,
        )
        return DocumentOut.from_domain(document)

    @app.get("/api/documents", response_model=list[DocumentOut])
    def list_documents() -> list[DocumentOut]:
        return [DocumentOut.from_domain(document) for document in repository.list()]

    @app.get("/api/documents/{document_id}/download")
    def download_document(document_id: str) -> FileResponse:
        document = repository.get(document_id)
        return FileResponse(
            document.path,
            media_type=document.content_type,
            filename=document.filename,
        )

    @app.get(
        "/api/documents/{document_id}/reports",
        response_model=list[ComparisonReportSummaryOut],
    )
    def list_document_reports(document_id: str) -> list[ComparisonReportSummaryOut]:
        repository.get(document_id)
        return list(report_repository.list_by_document(document_id))

    @app.post("/api/comparisons", response_model=CompareResponse)
    def compare_by_id(payload: CompareByIdRequest) -> CompareResponse:
        result = compare_use_case.execute_by_id(
            old_document_id=payload.old_document_id,
            new_document_id=payload.new_document_id,
        )
        return report_repository.save(result.to_response()).to_response()

    @app.post("/api/comparisons/upload", response_model=CompareResponse)
    async def compare_uploads(
        old_file: UploadFile = File(...),
        new_file: UploadFile = File(...),
    ) -> CompareResponse:
        old_content = await old_file.read()
        new_content = await new_file.read()
        result = compare_use_case.execute_uploads(
            old_filename=old_file.filename or "",
            old_content_type=old_file.content_type or "application/octet-stream",
            old_content=old_content,
            new_filename=new_file.filename or "",
            new_content_type=new_file.content_type or "application/octet-stream",
            new_content=new_content,
        )
        return report_repository.save(result.to_response()).to_response()

    @app.post("/api/reviews", response_model=DocumentReviewResponse)
    def review_by_id(payload: ReviewByIdRequest) -> DocumentReviewResponse:
        result = review_use_case.execute_by_id(document_id=payload.document_id)
        return result.to_response()

    @app.post("/api/reviews/upload", response_model=DocumentReviewResponse)
    async def review_upload(file: UploadFile = File(...)) -> DocumentReviewResponse:
        content = await file.read()
        result = review_use_case.execute_upload(
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            content=content,
        )
        return result.to_response()

    @app.get("/api/reports", response_model=list[ComparisonReportSummaryOut])
    def list_reports() -> list[ComparisonReportSummaryOut]:
        return list(report_repository.list())

    @app.get("/api/reports/{report_id}", response_model=ComparisonReportOut)
    def get_report(report_id: str) -> ComparisonReportOut:
        return report_repository.get(report_id)

    if config.FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="ui")

    return app


async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        execution_time = time.perf_counter() - started_at
        logger.info(
            "request finished",
            extra={
                "request_id": request_id,
                "operation": f"{request.method} {request.url.path}",
                "execution_time": round(execution_time, 4),
                "document_id": None,
            },
        )
    response.headers["X-Request-ID"] = request_id
    return response


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = _status_for_domain_error(exc)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": type(exc).__name__,
            "message": str(exc),
            "request_id": request.headers.get("X-Request-ID"),
        },
    )


def _status_for_domain_error(exc: DomainError) -> int:
    if isinstance(exc, DocumentValidationError):
        return 400
    if isinstance(exc, DocumentNotFoundError):
        return 404
    if isinstance(exc, ReportNotFoundError):
        return 404
    if isinstance(exc, (DocumentParsingError, ComparisonError)):
        return 422
    if isinstance(exc, AIProcessingError):
        return 502
    return 500


def _build_primary_insight_providers() -> tuple[GeminiInsightProvider | OpenRouterInsightProvider, ...]:
    providers: list[GeminiInsightProvider | OpenRouterInsightProvider] = []
    for provider_factory in (GeminiInsightProvider, OpenRouterInsightProvider):
        try:
            providers.append(provider_factory())
        except AIProcessingError:
            continue
    return tuple(providers)


app = create_app()
