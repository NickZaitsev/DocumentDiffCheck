from __future__ import annotations

from src import config
from src.integrations.gemini_provider import GeminiInsightProvider, _gemini_api_keys


def test_gemini_api_keys_accept_single_string(
    monkeypatch,
) -> None:
    monkeypatch.setattr(config, "GEMINI_API_KEYS", "key-one")

    assert _gemini_api_keys() == ("key-one",)


def test_gemini_provider_exposes_summary_and_risk_methods() -> None:
    assert hasattr(GeminiInsightProvider, "generate_summary")
    assert hasattr(GeminiInsightProvider, "assess_risks")

