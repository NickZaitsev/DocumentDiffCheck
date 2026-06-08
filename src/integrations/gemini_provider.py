from __future__ import annotations

from src import config
from src.domain.entities import ComparisonResult, ParsedDocument
from src.domain.exceptions import AIProcessingError
from src.infrastructure.insights import (
    ContractAmountExtraction,
    build_monetary_context_payload,
    clean_report,
    comparison_change_ids,
    document_block_ids,
    iter_comparison_prompt_payloads,
    iter_document_review_payloads,
    merge_reports,
    monetary_context_from_extraction,
)
from src.schemas.insights import ChangeReport


class GeminiInsightProvider:
    def __init__(self) -> None:
        api_keys = _gemini_api_keys()
        if not api_keys:
            raise AIProcessingError("Gemini API keys are not configured")
        try:
            from gemini_gateway import GeminiGateway, GeminiGatewayConfig
        except ImportError as exc:
            raise AIProcessingError("Gemini gateway dependency is not installed") from exc

        gateway_config = GeminiGatewayConfig(
            model=config.GEMINI_MODEL,
            api_keys=api_keys,
            requests_per_minute=config.GEMINI_REQUESTS_PER_MINUTE,
            tokens_per_minute=config.GEMINI_TOKENS_PER_MINUTE,
            requests_per_day=config.GEMINI_REQUESTS_PER_DAY,
            request_timeout_ms=config.GEMINI_TIMEOUT_MS,
            max_retries=config.GEMINI_MAX_RETRIES,
            temperature=config.GEMINI_TEMPERATURE,
        )
        self._gateway = GeminiGateway(gateway_config)
        self._model = gateway_config.model

    def analyze_comparison(self, comparison: ComparisonResult) -> ChangeReport:
        reports: list[ChangeReport] = []
        monetary_context = self._extract_monetary_context(comparison.new_document)
        for payload_model in iter_comparison_prompt_payloads(comparison):
            payload = payload_model.model_dump_json(ensure_ascii=False, indent=2)
            prompt = config.COMPARISON_ANALYSIS_PROMPT.format(
                monetary_context=monetary_context,
                comparison_payload=payload,
            )
            report = self._generate(prompt)
            reports.append(clean_report(report, comparison_change_ids(comparison)))
        return merge_reports(reports, provider="gemini", model=self._model)

    def analyze_document(self, document: ParsedDocument) -> ChangeReport:
        reports: list[ChangeReport] = []
        monetary_context = self._extract_monetary_context(document)
        for payload_model in iter_document_review_payloads(document):
            payload = payload_model.model_dump_json(ensure_ascii=False, indent=2)
            prompt = config.DOCUMENT_ANALYSIS_PROMPT.format(
                monetary_context=monetary_context,
                document_payload=payload,
            )
            report = self._generate(prompt)
            reports.append(clean_report(report, document_block_ids(document)))
        return merge_reports(reports, provider="gemini", model=self._model)

    def _extract_monetary_context(self, document: ParsedDocument) -> str:
        payload_model = build_monetary_context_payload(document)
        if not payload_model.candidates:
            return monetary_context_from_extraction(document, ContractAmountExtraction())
        payload = payload_model.model_dump_json(ensure_ascii=False, indent=2)
        prompt = config.CONTRACT_AMOUNT_EXTRACTION_PROMPT.format(
            monetary_payload=payload
        )
        try:
            result = self._gateway.generate_json_result(
                prompt,
                ContractAmountExtraction,
                max_output_tokens=1000,
            )
        except Exception as exc:
            raise AIProcessingError("Gemini monetary extraction failed") from exc
        extraction: ContractAmountExtraction = result.payload
        return monetary_context_from_extraction(document, extraction)

    def _generate(self, prompt: str) -> ChangeReport:
        try:
            result = self._gateway.generate_json_result(
                prompt,
                ChangeReport,
                max_output_tokens=4000,
            )
        except Exception as exc:
            raise AIProcessingError("Gemini analysis failed") from exc
        report: ChangeReport = result.payload
        return report.model_copy(
            update={"provider": "gemini", "model": self._model}
        )


def _gemini_api_keys() -> tuple[str, ...]:
    raw_keys = config.GEMINI_API_KEYS
    if isinstance(raw_keys, str):
        return tuple(value.strip() for value in raw_keys.split(",") if value.strip())
    return tuple(raw_keys)
