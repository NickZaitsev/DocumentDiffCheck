from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from src.domain.entities import StoredDocument
from src.infrastructure.docx_parser import DocxDocumentParser


def test_docx_parser_reads_sample_contract_blocks() -> None:
    sample = Path("samples/dogovor_postavki_v1.docx")
    stored = StoredDocument(
        document_id="sample-v1",
        filename=sample.name,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        path=sample,
        size_bytes=sample.stat().st_size,
        created_at=datetime(2026, 6, 7, tzinfo=UTC),
    )

    parsed = DocxDocumentParser().parse(stored)

    assert parsed.document_id == "sample-v1"
    assert len(parsed.blocks) > 5
    assert all(block.normalized_text for block in parsed.blocks)

