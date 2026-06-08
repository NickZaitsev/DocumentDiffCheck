from __future__ import annotations

from typing import Any

from src.domain.exceptions import AIProcessingError
from src.infrastructure.insights import FallbackInsightProvider, ResilientInsightProvider
from src.schemas.insights import ChangeReport


class FailingProvider:
    def analyze_comparison(self, comparison: Any) -> ChangeReport:
        raise AIProcessingError("primary failed")

    def analyze_document(self, document: Any) -> ChangeReport:
        raise AIProcessingError("primary failed")


class SuccessfulProvider:
    def analyze_comparison(self, comparison: Any) -> ChangeReport:
        return ChangeReport(summary="ok", provider="second")

    def analyze_document(self, document: Any) -> ChangeReport:
        return ChangeReport(summary="ok", provider="second")


def test_resilient_provider_tries_next_primary_before_fallback() -> None:
    provider = ResilientInsightProvider(
        primary=(FailingProvider(), SuccessfulProvider()),
        fallback=FallbackInsightProvider(),
    )

    assert provider.analyze_comparison(None).provider == "second"
    assert provider.analyze_document(None).provider == "second"
