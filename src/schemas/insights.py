from __future__ import annotations

from pydantic import BaseModel, Field


class KeyChange(BaseModel):
    title: str = Field(min_length=1)
    change_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    legal_significance: str = Field(min_length=1)
    source_change_ids: list[str] = Field(default_factory=list)


class LegalSummary(BaseModel):
    plain_language_summary: str = Field(min_length=1)
    key_changes: list[KeyChange] = Field(default_factory=list)
    legal_significance: str = Field(min_length=1)
    recommended_review_points: list[str] = Field(default_factory=list)
    provider: str = "fallback"
    model: str | None = None


class FinancialRisk(BaseModel):
    title: str = Field(min_length=1)
    risk_type: str = Field(min_length=1)
    source_change_id: str
    source_text: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    estimated_impact: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    detected_terms: list[str] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    overall_risk_level: str = Field(min_length=1)
    risks: list[FinancialRisk] = Field(default_factory=list)
    review_recommendation: str = Field(min_length=1)
    provider: str = "fallback"
    model: str | None = None

