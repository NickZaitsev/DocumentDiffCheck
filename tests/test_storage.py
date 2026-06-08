from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

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


def test_document_repository_parallel_saves_do_not_lose_records(tmp_path) -> None:
    repository = LocalDocumentRepository(tmp_path)

    def save_document(index: int) -> str:
        document = repository.save(
            f"document-{index}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            f"content-{index}".encode(),
        )
        return document.document_id

    with ThreadPoolExecutor(max_workers=8) as executor:
        document_ids = list(executor.map(save_document, range(20)))

    stored_ids = {document.document_id for document in repository.list()}

    assert stored_ids == set(document_ids)
