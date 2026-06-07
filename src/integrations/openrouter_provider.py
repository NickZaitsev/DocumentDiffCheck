from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

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


class OpenRouterInsightProvider:
    def __init__(self) -> None:
        if not config.OPENROUTER_API_KEY.strip():
            raise AIProcessingError("OpenRouter API key is not configured")
        self._api_key = config.OPENROUTER_API_KEY.strip()
        self._model = config.OPENROUTER_MODEL
        self._base_url = config.OPENROUTER_BASE_URL.rstrip("/")

    def analyze_comparison(self, comparison: ComparisonResult) -> ChangeReport:
        payload = build_prompt_payload(comparison).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.COMPARISON_ANALYSIS_PROMPT.format(comparison_payload=payload)
        report = self._generate_json(prompt, schema_name="change_report")
        return clean_report(report, comparison_change_ids(comparison))

    def analyze_document(self, document: ParsedDocument) -> ChangeReport:
        payload = build_document_review_payload(document).model_dump_json(
            ensure_ascii=False,
            indent=2,
        )
        prompt = config.DOCUMENT_ANALYSIS_PROMPT.format(document_payload=payload)
        report = self._generate_json(prompt, schema_name="change_report")
        return clean_report(report, document_block_ids(document))

    def _generate_json(self, prompt: str, *, schema_name: str) -> ChangeReport:
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
                    "schema": ChangeReport.model_json_schema(),
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
            report = ChangeReport.model_validate_json(_extract_json_content(content))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProcessingError("OpenRouter request failed") from exc
        except ValidationError as exc:
            raise AIProcessingError("OpenRouter returned invalid structured JSON") from exc
        return report.model_copy(update={"provider": "openrouter", "model": self._model})

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
