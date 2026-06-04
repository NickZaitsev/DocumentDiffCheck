from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from src import config
from src.api.app import _build_primary_insight_providers
from src.integrations.openrouter_provider import OpenRouterInsightProvider, _extract_json_content
from src.schemas.insights import LegalSummary


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
                            "content": LegalSummary(
                                plain_language_summary="ok",
                                legal_significance="ok",
                            ).model_dump_json()
                        }
                    }
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    result = OpenRouterInsightProvider()._generate_json(
        "prompt",
        LegalSummary,
        schema_name="legal_summary",
    )

    assert result.plain_language_summary == "ok"
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer openrouter-key"
    assert captured["json"]["response_format"]["type"] == "json_schema"
    assert captured["json"]["response_format"]["json_schema"]["strict"] is True


def test_extract_json_content_accepts_markdown_fenced_json() -> None:
    content = '```json\n{"ok": true, "message": "done"}\n```'

    assert _extract_json_content(content) == '{"ok": true, "message": "done"}'


def test_primary_provider_falls_back_to_openrouter_when_gemini_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", ())
    monkeypatch.setattr(config, "OPENROUTER_API_KEY", "openrouter-key")

    providers = _build_primary_insight_providers()

    assert len(providers) == 1
    assert isinstance(providers[0], OpenRouterInsightProvider)
