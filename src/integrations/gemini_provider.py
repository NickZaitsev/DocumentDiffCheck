from __future__ import annotations

import sys

from src import config
from src.domain.entities import ComparisonResult, ParsedDocument
from src.domain.exceptions import AIProcessingError
from src.infrastructure.insights import (
    build_document_review_payload,
    build_prompt_payload,
    clean_report,
    comparison_change_ids,
    document_block_ids,
)
from src.schemas.insights import ChangeReport


class GeminiInsightProvider:
    def __init__(self) -> None:
        api_keys = _gemini_api_keys()
        if not api_keys:
            raise AIProcessingError("Gemini API keys are not configured")
        if config.GEMINI_GATEWAY_SRC_PATH.exists():
            path = str(config.GEMINI_GATEWAY_SRC_PATH)
            if path not in sys.path:
                sys.path.insert(0, path)

        from gemini_gateway import GeminiGateway, GeminiGatewayConfig

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
        payload = build_prompt_payload(comparison).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.COMPARISON_ANALYSIS_PROMPT.format(comparison_payload=payload)
        report = self._generate(prompt)
        return clean_report(report, comparison_change_ids(comparison))

    def analyze_document(self, document: ParsedDocument) -> ChangeReport:
        payload = build_document_review_payload(document).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.DOCUMENT_ANALYSIS_PROMPT.format(document_payload=payload)
        report = self._generate(prompt)
        return clean_report(report, document_block_ids(document))

    def _generate(self, prompt: str) -> ChangeReport:
        try:
            result = self._gateway.generate_json_result(
                prompt,
                ChangeReport,
                max_output_tokens=4000,
            )
        except Exception as exc:
            raise AIProcessingError("Gemini analysis failed") from exc
        return result.payload.model_copy(
            update={"provider": "gemini", "model": self._model}
        )


def _gemini_api_keys() -> tuple[str, ...]:
    raw_keys = config.GEMINI_API_KEYS
    if isinstance(raw_keys, str):
        return tuple(value.strip() for value in raw_keys.split(",") if value.strip())
    return tuple(raw_keys)
