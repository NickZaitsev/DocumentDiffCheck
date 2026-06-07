from __future__ import annotations

import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from src import config
from src.domain.entities import ComparisonResult, ParsedDocument
from src.domain.exceptions import AIProcessingError
from src.infrastructure.insights import build_document_review_payload, build_prompt_payload
from src.schemas.insights import LegalSummary, RiskAssessment

T = TypeVar("T", bound=BaseModel)


class OpenRouterInsightProvider:
    def __init__(self) -> None:
        if not config.OPENROUTER_API_KEY.strip():
            raise AIProcessingError("OpenRouter API key is not configured")
        self._api_key = config.OPENROUTER_API_KEY.strip()
        self._model = config.OPENROUTER_MODEL
        self._base_url = config.OPENROUTER_BASE_URL.rstrip("/")

    def generate_summary(self, comparison: ComparisonResult) -> LegalSummary:
        payload = build_prompt_payload(comparison).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.LEGAL_SUMMARY_PROMPT.format(comparison_payload=payload)
        result = self._generate_json(prompt, LegalSummary, schema_name="legal_summary")
        return result.model_copy(update={"provider": "openrouter", "model": self._model})

    def assess_risks(self, comparison: ComparisonResult) -> RiskAssessment:
        payload = build_prompt_payload(comparison, risk_only=True).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.FINANCIAL_RISK_PROMPT.format(comparison_payload=payload)
        result = self._generate_json(prompt, RiskAssessment, schema_name="risk_assessment")
        return result.model_copy(update={"provider": "openrouter", "model": self._model})

    def generate_document_summary(self, document: ParsedDocument) -> LegalSummary:
        payload = build_document_review_payload(document).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.DOCUMENT_REVIEW_SUMMARY_PROMPT.format(document_payload=payload)
        result = self._generate_json(
            prompt,
            LegalSummary,
            schema_name="document_review_summary",
        )
        return result.model_copy(update={"provider": "openrouter", "model": self._model})

    def assess_document_risks(self, document: ParsedDocument) -> RiskAssessment:
        payload = build_document_review_payload(document, risk_only=True).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.DOCUMENT_REVIEW_RISK_PROMPT.format(document_payload=payload)
        result = self._generate_json(
            prompt,
            RiskAssessment,
            schema_name="document_review_risk_assessment",
        )
        return result.model_copy(update={"provider": "openrouter", "model": self._model})

    def _generate_json(
        self,
        prompt: str,
        schema: type[T],
        *,
        schema_name: str,
    ) -> T:
        request_payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": config.OPENROUTER_TEMPERATURE,
            "max_tokens": config.OPENROUTER_MAX_TOKENS,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=request_payload,
                timeout=config.OPENROUTER_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            return schema.model_validate_json(_extract_json_content(content))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProcessingError("OpenRouter request failed") from exc
        except ValidationError as exc:
            raise AIProcessingError("OpenRouter returned invalid structured JSON") from exc

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        if config.OPENROUTER_SITE_URL:
            headers["HTTP-Referer"] = config.OPENROUTER_SITE_URL
        if config.OPENROUTER_APP_NAME:
            headers["X-Title"] = config.OPENROUTER_APP_NAME
        return headers


def _extract_json_content(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    if stripped.startswith("{"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return stripped
    return stripped[start : end + 1]
