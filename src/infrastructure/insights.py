from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from pydantic import BaseModel

from src import config
from src.domain.chunking import TokenBudget, chunk_sequence
from src.domain.entities import (
    ChangeType,
    ComparisonResult,
    DocumentBlock,
    DocumentChange,
    ParsedDocument,
)
from src.domain.exceptions import AIProcessingError
from src.domain.ports import InsightProvider
from src.schemas.insights import ChangeItem, ChangeReport, RiskLevel, RiskType

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


class PromptChange(BaseModel):
    change_id: str
    change_type: str
    old_text: str | None
    old_text_truncated: bool = False
    new_text: str | None
    new_text_truncated: bool = False


class ComparisonPromptPayload(BaseModel):
    changes: list[PromptChange]


class PromptDocumentBlock(BaseModel):
    block_id: str
    index: int
    kind: str
    text: str
    text_truncated: bool = False


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
        return self._risk_item(
            self._describe_change(change),
            self._source_text(change),
            change.change_id,
        )

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

    def _overall_level(self, items: Iterable[ChangeItem]) -> RiskLevel:
        financial = [item for item in items if item.financial_risk]
        if any(item.estimated_impact for item in financial):
            return RiskLevel.HIGH
        if financial:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

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

    def _risk_type(self, terms: list[str]) -> RiskType:
        joined = " ".join(terms)
        if (
            "штраф" in joined
            or "пен" in joined
            or "неустойк" in joined
            or "penalty" in joined
            or "fine" in joined
        ):
            return RiskType.PENALTY
        if "ответствен" in joined or "liability" in joined or "убытк" in joined:
            return RiskType.LIABILITY
        if "индексац" in joined:
            return RiskType.INDEXATION
        if "односторонн" in joined or "уменьш" in joined:
            return RiskType.PRICE_CHANGE
        if "удержан" in joined or "невозврат" in joined:
            return RiskType.WITHHOLDING
        return RiskType.OTHER

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
            providers: tuple[InsightProvider, ...] = ()
        elif isinstance(primary, Sequence):
            providers = tuple(primary)
        else:
            providers = (primary,)
        self._primary_providers = providers
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


def merge_reports(
    reports: Sequence[ChangeReport],
    *,
    provider: str,
    model: str | None = None,
) -> ChangeReport:
    if not reports:
        return ChangeReport(
            summary="Анализ не выявил изменений для проверки.",
            provider=provider,
            model=model,
        )
    if len(reports) == 1:
        return reports[0].model_copy(update={"provider": provider, "model": model})

    changes: list[ChangeItem] = []
    review_points: list[str] = []
    for report in reports:
        changes.extend(report.changes)
        for point in report.recommended_review_points:
            if point not in review_points:
                review_points.append(point)

    return ChangeReport(
        summary=_merge_summary(reports),
        overall_risk_level=_merged_risk_level(reports),
        changes=changes,
        recommended_review_points=review_points,
        provider=provider,
        model=model,
    )


def iter_comparison_prompt_payloads(
    comparison: ComparisonResult,
    *,
    max_input_tokens: int | None = None,
) -> list[ComparisonPromptPayload]:
    changes = [
        change
        for change in comparison.changes
        if change.change_type != ChangeType.UNCHANGED
    ]
    budget = TokenBudget(max_input_tokens=max_input_tokens or config.MAX_INPUT_TOKENS)
    batches = chunk_sequence(changes, budget=budget, text_for_item=_change_text)
    return [_comparison_payload(comparison, batch, budget=budget) for batch in batches]


def iter_document_review_payloads(
    document: ParsedDocument,
    *,
    max_input_tokens: int | None = None,
) -> list[DocumentReviewPromptPayload]:
    blocks = [block for block in document.blocks if block.text.strip()]
    budget = TokenBudget(max_input_tokens=max_input_tokens or config.MAX_INPUT_TOKENS)
    batches = chunk_sequence(blocks, budget=budget, text_for_item=lambda block: block.text)
    return [_document_review_payload(document, batch, budget=budget) for batch in batches]


def build_prompt_payload(
    comparison: ComparisonResult,
    *,
    max_changes: int | None = None,
) -> ComparisonPromptPayload:
    payloads = iter_comparison_prompt_payloads(comparison)
    payload = payloads[0] if payloads else _comparison_payload(comparison, [], budget=None)
    if max_changes is not None:
        return payload.model_copy(update={"changes": payload.changes[:max_changes]})
    return payload


def _comparison_payload(
    comparison: ComparisonResult,
    changes: Sequence[DocumentChange],
    *,
    budget: TokenBudget | None,
) -> ComparisonPromptPayload:
    text_limit = budget.available_chars if budget is not None and len(changes) == 1 else None
    return ComparisonPromptPayload(
        changes=[
            PromptChange(
                change_id=change.change_id,
                change_type=change.change_type.value,
                old_text=_trim(_old_block_text(change), limit=text_limit),
                old_text_truncated=_is_truncated(
                    _old_block_text(change),
                    limit=text_limit,
                ),
                new_text=_trim(_new_block_text(change), limit=text_limit),
                new_text_truncated=_is_truncated(
                    _new_block_text(change),
                    limit=text_limit,
                ),
            )
            for change in changes
        ],
    )


def build_document_review_payload(
    document: ParsedDocument,
    *,
    max_blocks: int | None = None,
) -> DocumentReviewPromptPayload:
    payloads = iter_document_review_payloads(document)
    payload = payloads[0] if payloads else _document_review_payload(document, [], budget=None)
    if max_blocks is not None:
        return payload.model_copy(update={"blocks": payload.blocks[:max_blocks]})
    return payload


def _document_review_payload(
    document: ParsedDocument,
    blocks: Sequence[DocumentBlock],
    *,
    budget: TokenBudget | None,
) -> DocumentReviewPromptPayload:
    text_limit = budget.available_chars if budget is not None and len(blocks) == 1 else None
    return DocumentReviewPromptPayload(
        document_id=document.document_id,
        filename=document.filename,
        blocks_count=len(document.blocks),
        blocks=[
            PromptDocumentBlock(
                block_id=block.block_id,
                index=block.index,
                kind=block.kind.value,
                text=_trim(block.text, limit=text_limit) or "",
                text_truncated=_is_truncated(block.text, limit=text_limit),
            )
            for block in blocks
        ],
    )


def comparison_change_ids(comparison: ComparisonResult) -> list[str]:
    return [change.change_id for change in comparison.changes]


def document_block_ids(document: ParsedDocument) -> list[str]:
    return [block.block_id for block in document.blocks]


def _trim(text: str | None, *, limit: int | None = None) -> str | None:
    if text is None:
        return None
    if limit is None:
        return text
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _is_truncated(text: str | None, *, limit: int | None) -> bool:
    return text is not None and limit is not None and len(text) > limit


def _change_text(change: DocumentChange) -> str:
    return "\n".join(
        value
        for value in (
            _old_block_text(change) or "",
            _new_block_text(change) or "",
        )
        if value
    )


def _old_block_text(change: DocumentChange) -> str | None:
    return change.old_block.text if change.old_block else None


def _new_block_text(change: DocumentChange) -> str | None:
    return change.new_block.text if change.new_block else None


def _merged_risk_level(reports: Sequence[ChangeReport]) -> RiskLevel:
    levels = {report.overall_risk_level for report in reports}
    if RiskLevel.HIGH in levels:
        return RiskLevel.HIGH
    if RiskLevel.MEDIUM in levels:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _merge_summary(reports: Sequence[ChangeReport]) -> str:
    financial_count = sum(
        1
        for report in reports
        for item in report.changes
        if item.financial_risk
    )
    return (
        f"Проанализировано {len(reports)} пакет(ов) документа; "
        f"найдено финансовых рисков: {financial_count}."
    )
