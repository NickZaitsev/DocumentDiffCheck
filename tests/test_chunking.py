from __future__ import annotations

from src.domain.entities import (
    ChangeType,
    ComparisonResult,
    ComparisonStats,
    DocumentBlock,
    DocumentBlockKind,
    DocumentChange,
    ParsedDocument,
)
from src.infrastructure.insights import (
    ContractAmountExtraction,
    build_monetary_context_payload,
    build_prompt_payload,
    document_monetary_context,
    iter_comparison_prompt_payloads,
    iter_document_review_payloads,
    monetary_context_from_extraction,
)


def test_comparison_prompt_payloads_batch_without_dropping_changes() -> None:
    comparison = _comparison_with_changes(8)

    payloads = iter_comparison_prompt_payloads(comparison, max_input_tokens=2001)

    payload_change_ids = [
        change.change_id
        for payload in payloads
        for change in payload.changes
    ]
    assert len(payloads) > 1
    assert payload_change_ids == [f"change-{index}" for index in range(8)]


def test_comparison_prompt_payload_contains_only_minimal_change_fields() -> None:
    comparison = _comparison_with_changes(1)

    payload = build_prompt_payload(comparison).model_dump()

    assert set(payload) == {"changes"}
    assert set(payload["changes"][0]) == {
        "change_id",
        "change_type",
        "old_text",
        "old_text_truncated",
        "new_text",
        "new_text_truncated",
    }


def test_document_review_payloads_mark_oversized_single_block_truncated() -> None:
    document = ParsedDocument(
        document_id="doc",
        filename="doc.docx",
        blocks=(
            DocumentBlock(
                block_id="block-1",
                index=1,
                kind=DocumentBlockKind.PARAGRAPH,
                text="x" * 100,
                normalized_text="x" * 100,
            ),
        ),
    )

    payloads = iter_document_review_payloads(document, max_input_tokens=2001)

    assert len(payloads) == 1
    assert payloads[0].blocks[0].text_truncated is True
    assert payloads[0].blocks[0].text.endswith("...")


def test_document_monetary_context_extracts_contract_amount_in_russian() -> None:
    document = ParsedDocument(
        document_id="doc",
        filename="doc.docx",
        blocks=(
            DocumentBlock(
                block_id="block-1",
                index=1,
                kind=DocumentBlockKind.PARAGRAPH,
                text="Цена договора составляет 1 200 000 руб., включая НДС.",
                normalized_text="цена договора составляет 1 200 000 руб включая ндс",
            ),
        ),
    )

    context = document_monetary_context(document)

    assert "Известная сумма договора: 1 200 000 руб." in context
    assert "Фрагмент с суммой договора" in context
    assert "не помечай как financial_risk" in context


def test_monetary_context_payload_keeps_money_candidates_for_llm() -> None:
    document = ParsedDocument(
        document_id="doc",
        filename="doc.docx",
        blocks=(
            DocumentBlock(
                block_id="block-penalty",
                index=2,
                kind=DocumentBlockKind.PARAGRAPH,
                text="Штраф составляет 50 000 руб.",
                normalized_text="штраф составляет 50 000 руб",
            ),
            DocumentBlock(
                block_id="block-price",
                index=1,
                kind=DocumentBlockKind.PARAGRAPH,
                text="Общая стоимость договора составляет 1 200 000 руб.",
                normalized_text="общая стоимость договора составляет 1 200 000 руб",
            ),
        ),
    )

    payload = build_monetary_context_payload(document)

    assert [candidate.block_id for candidate in payload.candidates] == [
        "block-price",
        "block-penalty",
    ]


def test_monetary_context_uses_llm_extraction_result() -> None:
    document = ParsedDocument(
        document_id="doc",
        filename="doc.docx",
        blocks=(
            DocumentBlock(
                block_id="block-price",
                index=1,
                kind=DocumentBlockKind.PARAGRAPH,
                text="Цена договора составляет 1 200 000 руб., включая НДС.",
                normalized_text="цена договора составляет 1 200 000 руб включая ндс",
            ),
        ),
    )

    context = monetary_context_from_extraction(
        document,
        ContractAmountExtraction(
            contract_amount="1 200 000 руб.",
            source_block_id="block-price",
            explanation="Это прямо названо ценой договора.",
        ),
    )

    assert "Известная сумма договора: 1 200 000 руб." in context
    assert "Почему выбрана эта сумма: Это прямо названо ценой договора." in context


def _comparison_with_changes(count: int) -> ComparisonResult:
    old_document = ParsedDocument(document_id="old", filename="old.docx", blocks=())
    new_document = ParsedDocument(document_id="new", filename="new.docx", blocks=())
    changes = tuple(
        DocumentChange(
            change_id=f"change-{index}",
            change_type=ChangeType.ADDED,
            old_block=None,
            new_block=DocumentBlock(
                block_id=f"block-{index}",
                index=index,
                kind=DocumentBlockKind.PARAGRAPH,
                text="risk clause " * 20,
                normalized_text="risk clause",
            ),
            similarity=0.0,
            word_diff=(),
        )
        for index in range(count)
    )
    return ComparisonResult(
        comparison_id="comparison",
        old_document=old_document,
        new_document=new_document,
        stats=ComparisonStats(
            added=count,
            removed=0,
            modified=0,
            unchanged=0,
            similarity_score=0.0,
        ),
        changes=changes,
    )
