from __future__ import annotations

import re

from pydantic import BaseModel

from src.domain.entities import ChangeType, ComparisonResult, DocumentChange
from src.domain.exceptions import AIProcessingError
from src.domain.ports import InsightProvider
from src.schemas.insights import (
    FinancialRisk,
    KeyChange,
    LegalSummary,
    RiskAssessment,
)

_RISK_KEYWORDS = (
    "штраф",
    "пеня",
    "пени",
    "неустойк",
    "ответственност",
    "убытк",
    "просроч",
    "оплат",
    "предоплат",
    "возврат",
    "удержан",
    "процент",
    "liquidated damages",
    "penalty",
    "fine",
    "late payment",
    "late delivery",
    "liability",
)
_MONEY_OR_PERCENT_RE = re.compile(
    r"(\d+(?:[,.]\d+)?\s?%|\d[\d\s.,]*(?:руб\.?|₽|rur|rub|usd|eur))",
    re.IGNORECASE,
)


class PromptStats(BaseModel):
    added: int
    removed: int
    modified: int
    unchanged: int
    similarity_score: float


class PromptChange(BaseModel):
    change_id: str
    change_type: str
    old_index: int | None
    new_index: int | None
    old_text: str | None
    new_text: str | None
    similarity: float


class ComparisonPromptPayload(BaseModel):
    comparison_id: str
    old_filename: str
    new_filename: str
    stats: PromptStats
    changes: list[PromptChange]


class FallbackInsightProvider:
    def generate_summary(self, comparison: ComparisonResult) -> LegalSummary:
        changed = self._changed(comparison)
        key_changes = [
            KeyChange(
                title=self._title_for_change(change),
                change_type=change.change_type.value,
                description=self._describe_change(change),
                legal_significance=self._legal_significance(change),
                source_change_ids=[change.change_id],
            )
            for change in changed[:8]
        ]
        stats = comparison.stats
        return LegalSummary(
            plain_language_summary=(
                "Документы сравнены структурно по абзацам и строкам таблиц. "
                f"Найдено добавлений: {stats.added}, удалений: {stats.removed}, "
                f"изменений: {stats.modified}. Индекс сходства: "
                f"{stats.similarity_score:.0%}."
            ),
            key_changes=key_changes,
            legal_significance=(
                "Автоматическое резюме построено по deterministic diff. "
                "Юристу стоит проверить измененные условия, особенно оплату, "
                "ответственность, сроки и штрафные санкции."
            ),
            recommended_review_points=[
                "Проверить добавленные и измененные положения договора.",
                "Отдельно сверить суммы, проценты, сроки оплаты и поставки.",
                "Проверить, не изменились ли ограничения ответственности сторон.",
            ],
            provider="fallback",
        )

    def assess_risks(self, comparison: ComparisonResult) -> RiskAssessment:
        risks: list[FinancialRisk] = []
        for change in self._changed(comparison):
            source_text = self._source_text(change)
            if not source_text:
                continue
            terms = self._detected_terms(source_text)
            money_terms = _MONEY_OR_PERCENT_RE.findall(source_text)
            if not terms and not money_terms:
                continue
            confidence = 0.55
            if terms:
                confidence += 0.2
            if money_terms:
                confidence += 0.2
            confidence = min(confidence, 0.95)
            risks.append(
                FinancialRisk(
                    title="Потенциальный финансовый риск в измененном условии",
                    risk_type=self._risk_type(terms),
                    source_change_id=change.change_id,
                    source_text=source_text[:1200],
                    explanation=(
                        "В изменении обнаружены формулировки, связанные с "
                        "платежами, ответственностью, санкциями или сроками."
                    ),
                    estimated_impact=self._estimated_impact(money_terms),
                    confidence=confidence,
                    detected_terms=[*terms, *money_terms],
                )
            )

        overall = "low"
        if any(risk.confidence >= 0.85 for risk in risks):
            overall = "high"
        elif risks:
            overall = "medium"

        return RiskAssessment(
            overall_risk_level=overall,
            risks=risks[:12],
            review_recommendation=(
                "Проверить финансовые условия вручную: fallback extractor "
                "показывает риск-кандидаты, а не финальное юридическое заключение."
            ),
            provider="fallback",
        )

    def _changed(self, comparison: ComparisonResult) -> list[DocumentChange]:
        return [
            change
            for change in comparison.changes
            if change.change_type != ChangeType.UNCHANGED
        ]

    def _title_for_change(self, change: DocumentChange) -> str:
        if change.change_type == ChangeType.ADDED:
            return "Добавлено новое положение"
        if change.change_type == ChangeType.REMOVED:
            return "Удалено положение"
        return "Изменено существующее положение"

    def _describe_change(self, change: DocumentChange) -> str:
        old_text = change.old_block.text if change.old_block else None
        new_text = change.new_block.text if change.new_block else None
        if old_text and new_text:
            return f"Было:\n{old_text[:500]}\n\nСтало:\n{new_text[:500]}"
        if new_text:
            return f"Стало:\n{new_text[:500]}"
        if old_text:
            return f"Было:\n{old_text[:500]}"
        return "Изменение без текстового блока."

    def _legal_significance(self, change: DocumentChange) -> str:
        source = self._source_text(change).casefold()
        if self._detected_terms(source):
            return "Может влиять на финансовые обязанности или ответственность сторон."
        return "Требует проверки в контексте договора."

    def _source_text(self, change: DocumentChange) -> str:
        if change.new_block is not None:
            return change.new_block.text
        if change.old_block is not None:
            return change.old_block.text
        return ""

    def _detected_terms(self, text: str) -> list[str]:
        folded = text.casefold()
        return [keyword for keyword in _RISK_KEYWORDS if keyword in folded]

    def _risk_type(self, terms: list[str]) -> str:
        joined = " ".join(terms)
        if "штраф" in joined or "пен" in joined or "неустойк" in joined:
            return "penalty"
        if "оплат" in joined or "payment" in joined or "предоплат" in joined:
            return "payment"
        if "ответствен" in joined or "liability" in joined:
            return "liability"
        return "financial"

    def _estimated_impact(self, money_terms: list[str]) -> str | None:
        if not money_terms:
            return None
        return "Обнаружены финансовые значения: " + ", ".join(money_terms[:6])


class ResilientInsightProvider:
    def __init__(
        self,
        *,
        primary: InsightProvider | None,
        fallback: InsightProvider,
    ) -> None:
        self._primary = primary
        self._fallback = fallback

    def generate_summary(self, comparison: ComparisonResult) -> LegalSummary:
        if self._primary is None:
            return self._fallback.generate_summary(comparison)
        try:
            return self._primary.generate_summary(comparison)
        except AIProcessingError:
            summary = self._fallback.generate_summary(comparison)
            return summary.model_copy(update={"provider": "fallback_after_llm_error"})

    def assess_risks(self, comparison: ComparisonResult) -> RiskAssessment:
        if self._primary is None:
            return self._fallback.assess_risks(comparison)
        try:
            return self._primary.assess_risks(comparison)
        except AIProcessingError:
            risks = self._fallback.assess_risks(comparison)
            return risks.model_copy(update={"provider": "fallback_after_llm_error"})


def build_prompt_payload(
    comparison: ComparisonResult,
    *,
    risk_only: bool = False,
    max_changes: int = 40,
) -> ComparisonPromptPayload:
    changes = [
        change
        for change in comparison.changes
        if change.change_type != ChangeType.UNCHANGED
    ]
    if risk_only:
        fallback = FallbackInsightProvider()
        changes = [
            change
            for change in changes
            if fallback._detected_terms(fallback._source_text(change))
            or _MONEY_OR_PERCENT_RE.search(fallback._source_text(change))
        ]

    return ComparisonPromptPayload(
        comparison_id=comparison.comparison_id,
        old_filename=comparison.old_document.filename,
        new_filename=comparison.new_document.filename,
        stats=PromptStats(
            added=comparison.stats.added,
            removed=comparison.stats.removed,
            modified=comparison.stats.modified,
            unchanged=comparison.stats.unchanged,
            similarity_score=comparison.stats.similarity_score,
        ),
        changes=[
            PromptChange(
                change_id=change.change_id,
                change_type=change.change_type.value,
                old_index=change.old_block.index if change.old_block else None,
                new_index=change.new_block.index if change.new_block else None,
                old_text=_trim(change.old_block.text if change.old_block else None),
                new_text=_trim(change.new_block.text if change.new_block else None),
                similarity=round(change.similarity, 4),
            )
            for change in changes[:max_changes]
        ],
    )


def _trim(text: str | None, *, limit: int = 1400) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
