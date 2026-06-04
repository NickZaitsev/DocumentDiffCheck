from __future__ import annotations

import sys

from src import config
from src.domain.entities import ComparisonResult
from src.domain.exceptions import AIProcessingError
from src.infrastructure.insights import build_prompt_payload
from src.schemas.insights import LegalSummary, RiskAssessment


class GeminiInsightProvider:
    def __init__(self) -> None:
        if not config.GEMINI_API_KEYS:
            raise AIProcessingError("Gemini API keys are not configured")
        if config.GEMINI_GATEWAY_SRC_PATH.exists():
            path = str(config.GEMINI_GATEWAY_SRC_PATH)
            if path not in sys.path:
                sys.path.insert(0, path)

        from gemini_gateway import GeminiGateway, GeminiGatewayConfig

        gateway_config = GeminiGatewayConfig(
            model=config.GEMINI_MODEL,
            api_keys=config.GEMINI_API_KEYS,
            requests_per_minute=config.GEMINI_REQUESTS_PER_MINUTE,
            tokens_per_minute=config.GEMINI_TOKENS_PER_MINUTE,
            requests_per_day=config.GEMINI_REQUESTS_PER_DAY,
            request_timeout_ms=config.GEMINI_TIMEOUT_MS,
            max_retries=config.GEMINI_MAX_RETRIES,
            temperature=config.GEMINI_TEMPERATURE,
        )
        self._gateway = GeminiGateway(gateway_config)
        self._model = gateway_config.model

    def generate_summary(self, comparison: ComparisonResult) -> LegalSummary:
        payload = build_prompt_payload(comparison).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.LEGAL_SUMMARY_PROMPT.format(comparison_payload=payload)
        try:
            result = self._gateway.generate_json_result(
                prompt,
                LegalSummary,
                max_output_tokens=4000,
            )
        except Exception as exc:
            raise AIProcessingError("Gemini legal summary generation failed") from exc
        return result.payload.model_copy(
            update={"provider": "gemini", "model": self._model}
        )

    def assess_risks(self, comparison: ComparisonResult) -> RiskAssessment:
        payload = build_prompt_payload(comparison, risk_only=True).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.FINANCIAL_RISK_PROMPT.format(comparison_payload=payload)
        try:
            result = self._gateway.generate_json_result(
                prompt,
                RiskAssessment,
                max_output_tokens=4000,
            )
        except Exception as exc:
            raise AIProcessingError("Gemini risk assessment generation failed") from exc
        return result.payload.model_copy(
            update={"provider": "gemini", "model": self._model}
        )

