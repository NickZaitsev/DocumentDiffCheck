from __future__ import annotations

from typing import Any

from src.domain.exceptions import AIProcessingError
from src.infrastructure.insights import FallbackInsightProvider, ResilientInsightProvider
from src.schemas.insights import LegalSummary, RiskAssessment


class FailingProvider:
    def generate_summary(self, comparison: Any) -> LegalSummary:
        raise AIProcessingError("primary failed")

    def assess_risks(self, comparison: Any) -> RiskAssessment:
        raise AIProcessingError("primary failed")

    def generate_document_summary(self, document: Any) -> LegalSummary:
        raise AIProcessingError("primary failed")

    def assess_document_risks(self, document: Any) -> RiskAssessment:
        raise AIProcessingError("primary failed")


class SuccessfulProvider:
    def generate_summary(self, comparison: Any) -> LegalSummary:
        return LegalSummary(
            plain_language_summary="ok",
            legal_significance="ok",
            provider="second",
        )

    def assess_risks(self, comparison: Any) -> RiskAssessment:
        return RiskAssessment(
            overall_risk_level="low",
            review_recommendation="ok",
            provider="second",
        )

    def generate_document_summary(self, document: Any) -> LegalSummary:
        return LegalSummary(
            plain_language_summary="ok",
            legal_significance="ok",
            provider="second",
        )

    def assess_document_risks(self, document: Any) -> RiskAssessment:
        return RiskAssessment(
            overall_risk_level="low",
            review_recommendation="ok",
            provider="second",
        )


def test_resilient_provider_tries_next_primary_before_fallback() -> None:
    provider = ResilientInsightProvider(
        primary=(FailingProvider(), SuccessfulProvider()),
        fallback=FallbackInsightProvider(),
    )

    assert provider.generate_summary(None).provider == "second"
    assert provider.assess_risks(None).provider == "second"
    assert provider.generate_document_summary(None).provider == "second"
    assert provider.assess_document_risks(None).provider == "second"

