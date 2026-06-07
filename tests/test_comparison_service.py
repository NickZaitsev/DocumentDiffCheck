from __future__ import annotations

from src.domain.comparison import DocumentComparisonService
from src.domain.entities import (
    ChangeType,
    DocumentBlock,
    DocumentBlockKind,
    ParsedDocument,
    WordDiffType,
)


def _document(document_id: str, texts: list[str]) -> ParsedDocument:
    return ParsedDocument(
        document_id=document_id,
        filename=f"{document_id}.docx",
        blocks=tuple(
            DocumentBlock(
                block_id=f"b-{index}",
                index=index,
                kind=DocumentBlockKind.PARAGRAPH,
                text=text,
                normalized_text=text.casefold(),
            )
            for index, text in enumerate(texts)
        ),
    )


def _table_document(document_id: str, rows: list[str]) -> ParsedDocument:
    return ParsedDocument(
        document_id=document_id,
        filename=f"{document_id}.docx",
        blocks=tuple(
            DocumentBlock(
                block_id=f"t-{index}",
                index=index,
                kind=DocumentBlockKind.TABLE_ROW,
                text=row,
                normalized_text=row.casefold(),
            )
            for index, row in enumerate(rows)
        ),
    )


def test_compare_detects_added_removed_and_modified_blocks() -> None:
    old = _document("old", ["Clause one", "Penalty is 5%", "Warranty remains unlimited"])
    new = _document("new", ["Clause one", "Penalty is 10%", "Delivery address was added"])

    result = DocumentComparisonService().compare(old, new)

    assert result.stats.modified == 1
    assert result.stats.removed == 1
    assert result.stats.added == 1
    assert result.stats.unchanged == 1
    changed_types = [change.change_type for change in result.changes]
    assert ChangeType.MODIFIED in changed_types
    assert ChangeType.REMOVED in changed_types
    assert ChangeType.ADDED in changed_types


def test_modified_change_contains_word_level_diff() -> None:
    old = _document("old", ["Payment due in 10 days"])
    new = _document("new", ["Payment due in 15 days"])

    result = DocumentComparisonService().compare(old, new)
    modified = result.changes[0]

    assert modified.change_type == ChangeType.MODIFIED
    assert any(segment.diff_type == WordDiffType.REMOVED for segment in modified.word_diff)
    assert any(segment.diff_type == WordDiffType.ADDED for segment in modified.word_diff)


def test_numbered_headings_are_matched_without_number_noise() -> None:
    old = _document("old", ["4. Порядок оплаты", "4.1. Покупатель оплачивает товар"])
    new = _document("new", ["5. Порядок оплаты", "5.1. Покупатель оплачивает товар"])

    result = DocumentComparisonService().compare(old, new)

    assert result.stats.unchanged == 2
    assert result.stats.modified == 0
    assert all(change.change_type == ChangeType.UNCHANGED for change in result.changes)


def test_table_row_numbering_is_ignored_for_matching() -> None:
    old = _table_document(
        "old",
        ["1 | Насос | 2 | 185 000,00 | 370 000,00"],
    )
    new = _table_document(
        "new",
        ["2 | Насос | 2 | 185 000,00 | 370 000,00"],
    )

    result = DocumentComparisonService().compare(old, new)

    assert result.stats.unchanged == 1
    assert result.stats.modified == 0
    assert result.changes[0].change_type == ChangeType.UNCHANGED
