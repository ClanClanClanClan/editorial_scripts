from uuid import uuid4

from src.ecc.core.domain.models import DocumentType, File


def _add_file_if_unique(files: list[File], new: File):
    if not any(getattr(f, "checksum", "") == new.checksum for f in files):
        files.append(new)


def test_file_deduplication_by_checksum():
    files: list[File] = []
    f1 = File(
        manuscript_id=uuid4(),
        document_type=DocumentType.MANUSCRIPT,
        filename="a.pdf",
        storage_path="/tmp/a.pdf",
        checksum="abc",
    )
    f2 = File(
        manuscript_id=uuid4(),
        document_type=DocumentType.MANUSCRIPT,
        filename="b.pdf",
        storage_path="/tmp/b.pdf",
        checksum="abc",
    )
    _add_file_if_unique(files, f1)
    _add_file_if_unique(files, f2)
    assert len(files) == 1
