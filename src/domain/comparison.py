from __future__ import annotations

import re
from difflib import SequenceMatcher
from uuid import uuid4

from src.domain.entities import (
    ChangeType,
    ComparisonResult,
    ComparisonStats,
    DocumentBlock,
    DocumentBlockKind,
    DocumentChange,
    ParsedDocument,
    WordDiffSegment,
    WordDiffType,
)
from src.domain.exceptions import ComparisonError

_WORD_RE = re.compile(r"\S+")
_LEADING_NUMBERING_RE = re.compile(r"^\s*(?:\(?\d+(?:\.\d+)*\)?[.)])(?:\s+|$)+")
_NUMBERING_ONLY_RE = re.compile(r"^\s*(?:\(?\d+(?:\.\d+)*\)?[.)])(?:\s+|$)*$")
_TABLE_ROW_NUMBER_RE = re.compile(r"^\d+$")


class DocumentComparisonService:
    def __init__(self, *, modified_similarity_threshold: float = 0.52) -> None:
        self._modified_similarity_threshold = modified_similarity_threshold

    def compare(
        self,
        old_document: ParsedDocument,
        new_document: ParsedDocument,
    ) -> ComparisonResult:
        if not old_document.blocks:
            raise ComparisonError("Old document has no readable text blocks")
        if not new_document.blocks:
            raise ComparisonError("New document has no readable text blocks")

        old_keys = [self._comparison_key(block) for block in old_document.blocks]
        new_keys = [self._comparison_key(block) for block in new_document.blocks]
        matcher = SequenceMatcher(a=old_keys, b=new_keys, autojunk=False)

        changes: list[DocumentChange] = []
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            old_span = old_document.blocks[old_start:old_end]
            new_span = new_document.blocks[new_start:new_end]
            if tag == "equal":
                changes.extend(self._unchanged_changes(old_span, new_span))
            elif tag == "delete":
                changes.extend(self._removed_changes(old_span))
            elif tag == "insert":
                changes.extend(self._added_changes(new_span))
            elif tag == "replace":
                changes.extend(self._replace_changes(old_span, new_span))
            else:
                raise ComparisonError(f"Unsupported diff opcode: {tag}")

        stats = self._build_stats(changes)
        return ComparisonResult(
            comparison_id=str(uuid4()),
            old_document=old_document,
            new_document=new_document,
            stats=stats,
            changes=tuple(changes),
        )

    def _unchanged_changes(
        self,
        old_span: tuple[DocumentBlock, ...],
        new_span: tuple[DocumentBlock, ...],
    ) -> list[DocumentChange]:
        return [
            DocumentChange(
                change_id=str(uuid4()),
                change_type=ChangeType.UNCHANGED,
                old_block=old_block,
                new_block=new_block,
                similarity=1.0,
                word_diff=(WordDiffSegment(WordDiffType.EQUAL, new_block.text),),
            )
            for old_block, new_block in zip(old_span, new_span, strict=True)
        ]

    def _removed_changes(
        self,
        old_span: tuple[DocumentBlock, ...],
    ) -> list[DocumentChange]:
        return [
            DocumentChange(
                change_id=str(uuid4()),
                change_type=ChangeType.REMOVED,
                old_block=old_block,
                new_block=None,
                similarity=0.0,
                word_diff=(WordDiffSegment(WordDiffType.REMOVED, old_block.text),),
            )
            for old_block in old_span
        ]

    def _added_changes(
        self,
        new_span: tuple[DocumentBlock, ...],
    ) -> list[DocumentChange]:
        return [
            DocumentChange(
                change_id=str(uuid4()),
                change_type=ChangeType.ADDED,
                old_block=None,
                new_block=new_block,
                similarity=0.0,
                word_diff=(WordDiffSegment(WordDiffType.ADDED, new_block.text),),
            )
            for new_block in new_span
        ]

    def _replace_changes(
        self,
        old_span: tuple[DocumentBlock, ...],
        new_span: tuple[DocumentBlock, ...],
    ) -> list[DocumentChange]:
        paired = self._pair_similar_blocks(old_span, new_span)
        old_by_index = {index: block for index, block in enumerate(old_span)}
        new_by_index = {index: block for index, block in enumerate(new_span)}
        used_old = {old_index for old_index, _, _ in paired}
        used_new = {new_index for _, new_index, _ in paired}

        changes: list[DocumentChange] = []
        for old_index, new_index, similarity in paired:
            old_block = old_by_index[old_index]
            new_block = new_by_index[new_index]
            changes.append(
                DocumentChange(
                    change_id=str(uuid4()),
                    change_type=ChangeType.MODIFIED,
                    old_block=old_block,
                    new_block=new_block,
                    similarity=similarity,
                    word_diff=self._word_diff(old_block.text, new_block.text),
                )
            )

        for old_index, old_block in old_by_index.items():
            if old_index not in used_old:
                changes.extend(self._removed_changes((old_block,)))
        for new_index, new_block in new_by_index.items():
            if new_index not in used_new:
                changes.extend(self._added_changes((new_block,)))

        return sorted(
            changes,
            key=lambda change: self._change_position(change),
        )

    def _pair_similar_blocks(
        self,
        old_span: tuple[DocumentBlock, ...],
        new_span: tuple[DocumentBlock, ...],
    ) -> list[tuple[int, int, float]]:
        candidates: list[tuple[float, int, int]] = []
        for old_index, old_block in enumerate(old_span):
            for new_index, new_block in enumerate(new_span):
                similarity = SequenceMatcher(
                    a=self._comparison_key(old_block),
                    b=self._comparison_key(new_block),
                    autojunk=False,
                ).ratio()
                if similarity >= self._modified_similarity_threshold:
                    candidates.append((similarity, old_index, new_index))

        pairs: list[tuple[int, int, float]] = []
        used_old: set[int] = set()
        used_new: set[int] = set()
        for similarity, old_index, new_index in sorted(candidates, reverse=True):
            if old_index in used_old or new_index in used_new:
                continue
            used_old.add(old_index)
            used_new.add(new_index)
            pairs.append((old_index, new_index, similarity))

        return sorted(pairs, key=lambda pair: (pair[0], pair[1]))

    def _word_diff(self, old_text: str, new_text: str) -> tuple[WordDiffSegment, ...]:
        old_words = _WORD_RE.findall(old_text)
        new_words = _WORD_RE.findall(new_text)
        matcher = SequenceMatcher(a=old_words, b=new_words, autojunk=False)
        segments: list[WordDiffSegment] = []
        for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
            if tag == "equal":
                segments.append(
                    WordDiffSegment(
                        WordDiffType.EQUAL,
                        " ".join(new_words[new_start:new_end]),
                    )
                )
            elif tag == "delete":
                segments.append(
                    WordDiffSegment(
                        WordDiffType.REMOVED,
                        " ".join(old_words[old_start:old_end]),
                    )
                )
            elif tag == "insert":
                segments.append(
                    WordDiffSegment(
                        WordDiffType.ADDED,
                        " ".join(new_words[new_start:new_end]),
                    )
                )
            elif tag == "replace":
                segments.append(
                    WordDiffSegment(
                        WordDiffType.REMOVED,
                        " ".join(old_words[old_start:old_end]),
                    )
                )
                segments.append(
                    WordDiffSegment(
                        WordDiffType.ADDED,
                        " ".join(new_words[new_start:new_end]),
                    )
                )
        return tuple(segment for segment in segments if segment.text)

    def _build_stats(self, changes: list[DocumentChange]) -> ComparisonStats:
        added = sum(change.change_type == ChangeType.ADDED for change in changes)
        removed = sum(change.change_type == ChangeType.REMOVED for change in changes)
        modified = sum(change.change_type == ChangeType.MODIFIED for change in changes)
        unchanged = sum(change.change_type == ChangeType.UNCHANGED for change in changes)
        total = max(1, added + removed + modified + unchanged)
        changed_weight = added + removed + modified
        similarity_score = round(max(0.0, 1.0 - changed_weight / total), 4)
        return ComparisonStats(
            added=added,
            removed=removed,
            modified=modified,
            unchanged=unchanged,
            similarity_score=similarity_score,
        )

    def _change_position(self, change: DocumentChange) -> int:
        block = change.new_block or change.old_block
        return block.index if block is not None else 0

    def _comparison_key(self, block: DocumentBlock) -> str:
        if block.kind == DocumentBlockKind.TABLE_ROW:
            return self._table_row_key(block.normalized_text)
        return self._strip_leading_numbering(block.normalized_text)

    def _table_row_key(self, text: str) -> str:
        cells = [cell.strip() for cell in text.split("|")]
        if len(cells) > 1 and _TABLE_ROW_NUMBER_RE.fullmatch(cells[0]):
            remainder = " | ".join(cell for cell in cells[1:] if cell)
            if remainder:
                return remainder
            return "__table_row_number__"
        return text

    def _strip_leading_numbering(self, text: str) -> str:
        stripped = _LEADING_NUMBERING_RE.sub("", text).strip()
        if stripped:
            return stripped
        if _NUMBERING_ONLY_RE.fullmatch(text):
            return "__numbering_only__"
        return text

