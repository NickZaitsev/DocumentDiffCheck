from __future__ import annotations

import re

from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from src.domain.entities import (
    ChangeType,
    ComparisonResult,
    DocumentBlock,
    DocumentChange,
    ParsedDocument,
)
from src.domain.exceptions import AIProcessingError
from src.domain.ports import InsightProvider
from src.schemas.insights import ChangeItem, ChangeReport

# Contingent / asymmetric exposures only. The agreed price, quantity and a
# normal payment schedule are NOT risks, so cost/price words are excluded here.
_RISK_KEYWORDS = (
    "штраф",
    "пеня",
    "пени",
    "неустойк",
    "ответственност",
    "убытк",
    "просроч",
    "удержан",
    "невозврат",
    "индексац",
    "пропорционально уменьш",
    "в одностороннем порядке",
    "liquidated damages",
    "penalty",
    "fine",
    "late payment",
    "late delivery",
    "liability",
    "default",
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


class PromptDocumentBlock(BaseModel):
    block_id: str
    index: int
    kind: str
    text: str


class DocumentReviewPromptPayload(BaseModel):
    document_id: str
    filename: str
    blocks_count: int
    blocks: list[PromptDocumentBlock]


class FallbackInsightProvider:
    def analyze_comparison(self, comparison: ComparisonResult) -> ChangeReport:
        items: list[ChangeItem] = []
        for change in self._changed(comparison):
            items.append(self._change_item(change))

        stats = comparison.stats
        summary = (
            "Документы сравнены структурно по абзацам и строкам таблиц. "
            f"Добавлений: {stats.added}, удалений: {stats.removed}, "
            f"изменений: {stats.modified}. Сходство: "
            f"{stats.similarity_score:.0%}."
        )
        return ChangeReport(
            summary=summary,
            overall_risk_level=self._overall_level(items),
            changes=items,
            recommended_review_points=[
                "Проверить добавленные и изменённые положения договора.",
                "Сверить суммы, проценты, сроки оплаты и поставки.",
                "Проверить, не изменились ли ограничения ответственности сторон.",
            ],
            provider="fallback",
        )

    def analyze_document(self, document: ParsedDocument) -> ChangeReport:
        blocks = [block for block in document.blocks if block.text.strip()]
        risk_blocks = [block for block in blocks if self._is_risk(block.text)]
        # Risk audit: focus on contingent risks; fall back to leading blocks only
        # when the contract has no detectable risk clauses.
        selected = self._dedupe_blocks(risk_blocks[:20]) or blocks[:5]

        items = [self._block_item(block) for block in selected]
        return ChangeReport(
            summary=(
                f"Документ «{document.filename}» разобран на {len(blocks)} "
                f"блоков; найдено потенциальных финансовых рисков: "
                f"{len(risk_blocks)}."
            ),
            overall_risk_level=self._overall_level(items),
            changes=items,
            recommended_review_points=[
                "Проверить предмет договора и ключевые обязанности.",
                "Сверить суммы, проценты, сроки оплаты и поставки.",
                "Проверить санкции, ответственность и порядок расторжения.",
            ],
            provider="fallback",
        )

    def _change_item(self, change: DocumentChange) -> ChangeItem:
        return self._risk_item(self._describe_change(change), self._source_text(change), change.change_id)

    def _block_item(self, block: DocumentBlock) -> ChangeItem:
        description = _trim(block.text, limit=400) or block.text
        return self._risk_item(description, block.text, block.block_id)

    def _risk_item(self, description: str, source_text: str, source_id: str) -> ChangeItem:
        terms = self._detected_terms(source_text)
        financial = bool(terms)
        money_terms = _MONEY_OR_PERCENT_RE.findall(source_text) if financial else []
        return ChangeItem(
            description=description,
            source_change_ids=[source_id],
            financial_risk=financial,
            risk_type=self._risk_type(terms) if financial else None,
            estimated_impact=self._estimated_impact(money_terms) if money_terms else None,
        )

    def _changed(self, comparison: ComparisonResult) -> list[DocumentChange]:
        return [
            change
            for change in comparison.changes
            if change.change_type != ChangeType.UNCHANGED
        ]

    def _describe_change(self, change: DocumentChange) -> str:
        old_text = change.old_block.text if change.old_block else None
        new_text = change.new_block.text if change.new_block else None
        if change.change_type == ChangeType.ADDED and new_text:
            return f"Добавлено: {_trim(new_text, limit=300)}"
        if change.change_type == ChangeType.REMOVED and old_text:
            return f"Удалено: {_trim(old_text, limit=300)}"
        if old_text and new_text:
            return (
                f"Изменено: «{_trim(old_text, limit=180)}» → "
                f"«{_trim(new_text, limit=180)}»"
            )
        return _trim(new_text or old_text, limit=300) or "Изменение без текста."

    def _overall_level(self, items: Iterable[ChangeItem]) -> str:
        financial = [item for item in items if item.financial_risk]
        if any(item.estimated_impact for item in financial):
            return "high"
        if financial:
            return "medium"
        return "low"

    def _dedupe_blocks(self, blocks: Iterable[DocumentBlock]) -> list[DocumentBlock]:
        seen: set[str] = set()
        unique: list[DocumentBlock] = []
        for block in blocks:
            if block.block_id in seen:
                continue
            seen.add(block.block_id)
            unique.append(block)
        return sorted(unique, key=lambda block: block.index)

    def _is_risk(self, text: str) -> bool:
        return bool(self._detected_terms(text))

    def _source_text(self, change: DocumentChange) -> str:
        if change.new_block is not None:
            return change.new_block.text
        if change.old_block is not None:
            return change.old_block.text
        return ""

    def _detected_terms(self, text: str) -> list[str]:
        # Drop the "ООО" legal form so "ограниченной ответственностью" in party
        # names is not mistaken for a liability clause.
        folded = text.casefold().replace("ограниченной ответственностью", " ")
        return [keyword for keyword in _RISK_KEYWORDS if keyword in folded]

    def _risk_type(self, terms: list[str]) -> str:
        joined = " ".join(terms)
        if "штраф" in joined or "пен" in joined or "неустойк" in joined or "penalty" in joined or "fine" in joined:
            return "penalty"
        if "ответствен" in joined or "liability" in joined or "убытк" in joined:
            return "liability"
        if "индексац" in joined:
            return "indexation"
        if "односторонн" in joined or "уменьш" in joined:
            return "price_change"
        if "удержан" in joined or "невозврат" in joined:
            return "withholding"
        return "other"

    def _estimated_impact(self, money_terms: list[str]) -> str | None:
        if not money_terms:
            return None
        return "Финансовые значения в пункте: " + ", ".join(money_terms[:6])


class ResilientInsightProvider:
    def __init__(
        self,
        *,
        primary: InsightProvider | Sequence[InsightProvider] | None,
        fallback: InsightProvider,
    ) -> None:
        if primary is None:
            self._primary_providers = ()
        elif isinstance(primary, Sequence):
            self._primary_providers = tuple(primary)
        else:
            self._primary_providers = (primary,)
        self._fallback = fallback

    def analyze_comparison(self, comparison: ComparisonResult) -> ChangeReport:
        for provider in self._primary_providers:
            try:
                return provider.analyze_comparison(comparison)
            except AIProcessingError:
                continue
        report = self._fallback.analyze_comparison(comparison)
        return report.model_copy(update={"provider": self._fallback_name()})

    def analyze_document(self, document: ParsedDocument) -> ChangeReport:
        for provider in self._primary_providers:
            try:
                return provider.analyze_document(document)
            except AIProcessingError:
                continue
        report = self._fallback.analyze_document(document)
        return report.model_copy(update={"provider": self._fallback_name()})

    def _fallback_name(self) -> str:
        return "fallback_after_llm_error" if self._primary_providers else "fallback"


def clean_report(report: ChangeReport, valid_ids: Iterable[str]) -> ChangeReport:
    """Drop hallucinated source ids the model returned that do not exist."""

    allowed = set(valid_ids)
    cleaned = [
        item.model_copy(
            update={
                "source_change_ids": [
                    cid for cid in item.source_change_ids if cid in allowed
                ]
            }
        )
        for item in report.changes
    ]
    return report.model_copy(update={"changes": cleaned})


def build_prompt_payload(
    comparison: ComparisonResult,
    *,
    max_changes: int = 60,
) -> ComparisonPromptPayload:
    changes = [
        change
        for change in comparison.changes
        if change.change_type != ChangeType.UNCHANGED
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


def build_document_review_payload(
    document: ParsedDocument,
    *,
    max_blocks: int = 120,
) -> DocumentReviewPromptPayload:
    blocks = [block for block in document.blocks if block.text.strip()]

    return DocumentReviewPromptPayload(
        document_id=document.document_id,
        filename=document.filename,
        blocks_count=len(document.blocks),
        blocks=[
            PromptDocumentBlock(
                block_id=block.block_id,
                index=block.index,
                kind=block.kind.value,
                text=_trim(block.text) or "",
            )
            for block in blocks[:max_blocks]
        ],
    )


def comparison_change_ids(comparison: ComparisonResult) -> list[str]:
    return [change.change_id for change in comparison.changes]


def document_block_ids(document: ParsedDocument) -> list[str]:
    return [block.block_id for block in document.blocks]


def _trim(text: str | None, *, limit: int = 1400) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
