from __future__ import annotations

import json

import httpx
from pydantic import ValidationError

from src import config
from src.domain.entities import ComparisonResult, ParsedDocument
from src.domain.exceptions import AIProcessingError
from src.infrastructure.insights import (
    clean_report,
    comparison_change_ids,
    document_block_ids,
    iter_comparison_prompt_payloads,
    iter_document_review_payloads,
    merge_reports,
)
from src.schemas.insights import ChangeReport, RiskLevel, RiskType


class OpenRouterInsightProvider:
    def __init__(self) -> None:
        if not config.OPENROUTER_API_KEY.strip():
            raise AIProcessingError("OpenRouter API key is not configured")
        self._api_key = config.OPENROUTER_API_KEY.strip()
        self._model = config.OPENROUTER_MODEL
        self._base_url = config.OPENROUTER_BASE_URL.rstrip("/")

    def analyze_comparison(self, comparison: ComparisonResult) -> ChangeReport:
        reports: list[ChangeReport] = []
        for payload_model in iter_comparison_prompt_payloads(comparison):
            payload = payload_model.model_dump_json(ensure_ascii=False, indent=2)
            prompt = config.COMPARISON_ANALYSIS_PROMPT.format(comparison_payload=payload)
            report = self._generate_json(prompt, schema_name="change_report")
            reports.append(clean_report(report, comparison_change_ids(comparison)))
        return merge_reports(reports, provider="openrouter", model=self._model)

    def analyze_document(self, document: ParsedDocument) -> ChangeReport:
        reports: list[ChangeReport] = []
        for payload_model in iter_document_review_payloads(document):
            payload = payload_model.model_dump_json(ensure_ascii=False, indent=2)
            prompt = config.DOCUMENT_ANALYSIS_PROMPT.format(document_payload=payload)
            report = self._generate_json(prompt, schema_name="change_report")
            reports.append(clean_report(report, document_block_ids(document)))
        return merge_reports(reports, provider="openrouter", model=self._model)

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
                    "schema": _change_report_response_schema(),
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


def _change_report_response_schema() -> dict[str, object]:
    risk_types = [item.value for item in RiskType]
    risk_levels = [item.value for item in RiskLevel]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "summary",
            "overall_risk_level",
            "changes",
            "recommended_review_points",
        ],
        "properties": {
            "summary": {"type": "string", "minLength": 1},
            "overall_risk_level": {"type": "string", "enum": risk_levels},
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "description",
                        "source_change_ids",
                        "financial_risk",
                        "risk_type",
                        "estimated_impact",
                    ],
                    "properties": {
                        "description": {"type": "string", "minLength": 1},
                        "source_change_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "financial_risk": {"type": "boolean"},
                        "risk_type": {
                            "anyOf": [
                                {"type": "string", "enum": risk_types},
                                {"type": "null"},
                            ]
                        },
                        "estimated_impact": {
                            "anyOf": [{"type": "string"}, {"type": "null"}]
                        },
                    },
                },
            },
            "recommended_review_points": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }
