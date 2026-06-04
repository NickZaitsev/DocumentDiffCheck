from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class DocumentBlockKind(StrEnum):
    PARAGRAPH = "paragraph"
    TABLE_ROW = "table_row"


class ChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


class WordDiffType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    EQUAL = "equal"


@dataclass(frozen=True, slots=True)
class StoredDocument:
    document_id: str
    filename: str
    content_type: str
    path: Path
    size_bytes: int


@dataclass(frozen=True, slots=True)
class DocumentBlock:
    block_id: str
    index: int
    kind: DocumentBlockKind
    text: str
    normalized_text: str


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    document_id: str
    filename: str
    blocks: tuple[DocumentBlock, ...]


@dataclass(frozen=True, slots=True)
class WordDiffSegment:
    diff_type: WordDiffType
    text: str


@dataclass(frozen=True, slots=True)
class DocumentChange:
    change_id: str
    change_type: ChangeType
    old_block: DocumentBlock | None
    new_block: DocumentBlock | None
    similarity: float
    word_diff: tuple[WordDiffSegment, ...]


@dataclass(frozen=True, slots=True)
class ComparisonStats:
    added: int
    removed: int
    modified: int
    unchanged: int
    similarity_score: float


@dataclass(frozen=True, slots=True)
class ComparisonResult:
    comparison_id: str
    old_document: ParsedDocument
    new_document: ParsedDocument
    stats: ComparisonStats
    changes: tuple[DocumentChange, ...]

