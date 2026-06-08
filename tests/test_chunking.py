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
    build_prompt_payload,
    iter_comparison_prompt_payloads,
    iter_document_review_payloads,
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
