from __future__ import annotations

import builtins
import json as json_module
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from src import config
from src.api.app import _build_primary_insight_providers
from src.domain.entities import DocumentBlock, DocumentBlockKind, ParsedDocument
from src.integrations.openrouter_provider import OpenRouterInsightProvider, _extract_json_content
from src.schemas.insights import ChangeReport


def test_openrouter_provider_requires_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")

    with pytest.raises(Exception, match="OpenRouter API key"):
        OpenRouterInsightProvider()


def test_openrouter_provider_validates_structured_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setattr(config, "OPENROUTER_MODEL", "test/model")

    captured: dict[str, Any] = {}

    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> SimpleNamespace:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": ChangeReport(summary="ok").model_dump_json()
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = OpenRouterInsightProvider()._generate_json(
        "prompt",
        schema_name="change_report",
    )

    assert result.summary == "ok"
    assert result.provider == "openrouter"
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer openrouter-key"
    assert captured["json"]["response_format"]["type"] == "json_schema"
    assert captured["json"]["response_format"]["json_schema"]["strict"] is True


def test_extract_json_content_accepts_markdown_fenced_json() -> None:
    content = '```json\n{"ok": true, "message": "done"}\n```'

    assert _extract_json_content(content) == '{"ok": true, "message": "done"}'


def test_openrouter_document_prompt_includes_russian_monetary_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "openrouter-key")
    monkeypatch.setattr(config, "OPENROUTER_MODEL", "test/model")
    captured_requests: list[dict[str, Any]] = []

    def fake_post(
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: int,
    ) -> SimpleNamespace:
        captured_requests.append(json)
        schema_name = json["response_format"]["json_schema"]["name"]
        if schema_name == "contract_amount_extraction":
            content = {
                "contract_amount": "1 200 000 руб.",
                "source_block_id": "block-price",
                "explanation": "Это прямо названо суммой договора.",
            }
        else:
            content = ChangeReport(summary="ok").model_dump()
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "choices": [
                    {
                        "message": {
                            "content": json_module_dumps(content)
                        }
                    }
                ]
            },
        )

    document = ParsedDocument(
        document_id="doc",
        filename="doc.docx",
        blocks=(
            DocumentBlock(
                block_id="block-price",
                index=1,
                kind=DocumentBlockKind.PARAGRAPH,
                text="Сумма договора составляет 1 200 000 руб.",
                normalized_text="сумма договора составляет 1 200 000 руб",
            ),
            DocumentBlock(
                block_id="block-risk",
                index=2,
                kind=DocumentBlockKind.PARAGRAPH,
                text="Штраф не может превышать 10% от суммы договора.",
                normalized_text="штраф не может превышать 10 от суммы договора",
            ),
        ),
    )
    monkeypatch.setattr(httpx, "post", fake_post)

    OpenRouterInsightProvider().analyze_document(document)

    assert len(captured_requests) == 2
    extraction_prompt = captured_requests[0]["messages"][0]["content"]
    analysis_prompt = captured_requests[1]["messages"][0]["content"]
    assert "Кандидатные блоки" in extraction_prompt
    assert "Сумма договора составляет 1 200 000 руб." in extraction_prompt
    assert "Денежный контекст для оценки рисков" in analysis_prompt
    assert "Известная сумма договора: 1 200 000 руб." in analysis_prompt
    assert "Почему выбрана эта сумма: Это прямо названо суммой договора." in analysis_prompt
    assert "Штраф не может превышать 10% от суммы договора." in analysis_prompt


def json_module_dumps(value: dict[str, Any]) -> str:
    return json_module.dumps(value, ensure_ascii=False)


def test_primary_provider_falls_back_to_openrouter_when_gemini_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ())
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "openrouter-key")

    providers = _build_primary_insight_providers()

    assert len(providers) == 1
    assert isinstance(providers[0], OpenRouterInsightProvider)


def test_primary_provider_initialization_tolerates_gemini_import_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ("gemini-key",))
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "")
    real_import = builtins.__import__

    def fail_gemini_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "gemini_gateway":
            raise ImportError("missing gemini gateway")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_gemini_import)

    providers = _build_primary_insight_providers()

    assert providers == ()
