from __future__ import annotations

from src.infrastructure.storage import LocalDocumentRepository


def test_document_repository_lists_newest_uploads_first(tmp_path) -> None:
    repository = LocalDocumentRepository(tmp_path)

    first = repository.save(
        "first.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"first",
    )
    second = repository.save(
        "second.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"second",
    )

    documents = repository.list()

    assert [document.document_id for document in documents] == [
        second.document_id,
        first.document_id,
    ]
    assert documents[0].created_at >= documents[1].created_at
