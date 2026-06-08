from __future__ import annotations

import builtins
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from src import config
from src.api.app import _build_primary_insight_providers
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
