from src.ecc.adapters.journals.fs import FSAdapter
from src.ecc.core.domain.models import DocumentType


def test_fs_classify_file():
    adapter = FSAdapter()
    assert adapter._classify_file("Review report", "report.pdf") == DocumentType.REFEREE_REPORT
    assert (
        adapter._classify_file("Decision letter", "decision_letter.pdf")
        == DocumentType.DECISION_LETTER
    )
    assert adapter._classify_file("Cover", "cover_letter.docx") == DocumentType.COVER_LETTER
    assert adapter._classify_file("Proof", "paper.pdf") == DocumentType.MANUSCRIPT
    assert adapter._classify_file("Other", "data.zip") == DocumentType.SUPPLEMENTARY
