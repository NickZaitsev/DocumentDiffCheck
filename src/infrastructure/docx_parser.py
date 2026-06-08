from __future__ import annotations

import re
from collections.abc import Iterator

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from src.domain.entities import (
    DocumentBlock,
    DocumentBlockKind,
    ParsedDocument,
    StoredDocument,
)
from src.domain.exceptions import DocumentParsingError


class DocxDocumentParser:
    def parse(self, stored_document: StoredDocument) -> ParsedDocument:
        try:
            document = Document(str(stored_document.path))
            blocks = tuple(self._extract_blocks(document))
        except Exception as exc:
            raise DocumentParsingError(
                f"Failed to parse DOCX document {stored_document.document_id}"
            ) from exc

        if not blocks:
            raise DocumentParsingError("Document has no readable text blocks")

        return ParsedDocument(
            document_id=stored_document.document_id,
            filename=stored_document.filename,
            blocks=blocks,
        )

    def _extract_blocks(self, document: DocumentObject) -> Iterator[DocumentBlock]:
        index = 0
        for item in _iter_block_items(document):
            if isinstance(item, Paragraph):
                text = item.text.strip()
                normalized = normalize_text(text)
                if not normalized:
                    continue
                yield DocumentBlock(
                    block_id=f"p-{index}",
                    index=index,
                    kind=DocumentBlockKind.PARAGRAPH,
                    text=text,
                    normalized_text=normalized,
                )
                index += 1
            elif isinstance(item, Table):
                for row in item.rows:
                    text = " | ".join(
                        cell.text.strip()
                        for cell in row.cells
                        if normalize_text(cell.text)
                    )
                    normalized = normalize_text(text)
                    if not normalized:
                        continue
                    yield DocumentBlock(
                        block_id=f"t-{index}",
                        index=index,
                        kind=DocumentBlockKind.TABLE_ROW,
                        text=text,
                        normalized_text=normalized,
                    )
                    index += 1


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _iter_block_items(parent: DocumentObject | _Cell) -> Iterator[Paragraph | Table]:
    if isinstance(parent, DocumentObject):
        parent_element = parent.element.body
    elif isinstance(parent, _Cell):
        parent_element = parent._tc
    else:
        raise DocumentParsingError(f"Unsupported DOCX parent: {type(parent)!r}")

    for child in parent_element.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)

