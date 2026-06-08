from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RiskType(StrEnum):
    PENALTY = "penalty"
    LIABILITY = "liability"
    INDEXATION = "indexation"
    PRICE_CHANGE = "price_change"
    PREPAYMENT = "prepayment"
    WITHHOLDING = "withholding"
    OTHER = "other"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChangeItem(BaseModel):
    """A single change in the unified feed.

    Each item is described by one plain-language ``description`` and points back
    to the diff via ``source_change_ids`` (used as proof anchors in the UI).
    Money-relevant items set ``financial_risk`` and may carry an
    ``estimated_impact``.
    """

    description: str = Field(min_length=1)
    source_change_ids: list[str] = Field(default_factory=list)
    financial_risk: bool = False
    risk_type: RiskType | None = None
    estimated_impact: str | None = None


class ChangeReport(BaseModel):
    """Unified analysis: one short summary plus a single list of changes."""

    summary: str = Field(min_length=1)
    overall_risk_level: RiskLevel = RiskLevel.LOW
    changes: list[ChangeItem] = Field(default_factory=list)
    recommended_review_points: list[str] = Field(default_factory=list)
    provider: str = "fallback"
    model: str | None = None
