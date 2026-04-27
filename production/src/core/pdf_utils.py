"""Shared PDF text extraction + report-attachment helpers.

Used by every extractor to handle the case where reviewers submit their
report as a PDF attachment instead of (or in addition to) typing inline
into the platform's form. Without this, `referee.reports[0].raw_text`
ends up containing only section headers from the empty inline form.

Public API:
    extract_pdf_text(path: str | Path) -> str
        Robust PyPDF2-based text extraction. Returns "" on any failure.

    populate_report_from_pdf(report: dict, pdf_path: str | Path,
                             *, attachment_url: str = "") -> bool
        Read the PDF, set raw_text/comments_to_author/word_count on the
        canonical report dict, append to attachments[]. Returns True iff
        we successfully extracted text.

    derive_recommendation_from_text(text: str) -> str
        Lightweight phrase-match for "Reject"/"Accept"/"Major Revision"
        etc. Used as a fallback when the platform doesn't surface the
        recommendation field.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

PathLike = Union[str, Path, os.PathLike]


def extract_pdf_text(pdf_path: PathLike) -> str:
    """Extract full text from a PDF. Returns "" on any failure.

    Tries pdfplumber first (better at preserving layout / paragraph
    breaks), falls back to PyPDF2.
    """
    p = Path(pdf_path)
    if not p.exists() or p.stat().st_size == 0:
        return ""

    # Try pdfplumber first — handles columnar reports and preserves
    # paragraph spacing better than PyPDF2 alone.
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(p) as pdf:
            pages = []
            for page in pdf.pages:
                txt = page.extract_text() or ""
                if txt.strip():
                    pages.append(txt)
            text = "\n".join(pages)
            if text.strip():
                return text
    except Exception:
        pass

    # Fallback: PyPDF2 (already vendored everywhere in this codebase).
    try:
        import PyPDF2  # type: ignore

        with open(p, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            chunks = []
            for page in reader.pages:
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                if txt.strip():
                    chunks.append(txt)
            return "\n".join(chunks).strip()
    except Exception:
        return ""


def derive_recommendation_from_text(text: str) -> str | None:
    """Lightweight phrase-match recommendation extraction.

    Returns one of: 'Reject', 'Accept', 'Minor Revision', 'Major Revision'
    or None if no clear signal. Used as a fallback when the platform
    doesn't surface the recommendation in structured form.
    """
    if not text:
        return None
    t = text.lower()
    # Order matters — most specific first
    if "reject" in t and "accept" not in t[:200]:
        return "Reject"
    if "major revision" in t or "major revisions" in t:
        return "Major Revision"
    if "minor revision" in t or "minor revisions" in t:
        return "Minor Revision"
    if "accept with minor" in t:
        return "Minor Revision"
    if "accept with major" in t:
        return "Major Revision"
    if "recommend acceptance" in t or "recommend accept" in t:
        return "Accept"
    if "accept" in t[:500]:
        return "Accept"
    return None


def populate_report_from_pdf(
    report: dict,
    pdf_path: PathLike,
    *,
    attachment_url: str = "",
    max_chars: int = 20_000,
    overwrite: bool = False,
) -> bool:
    """Populate a canonical report dict with text extracted from a PDF.

    Conservative merge:
      - Always appends to `report['attachments']` (with local_path + url).
      - If `raw_text` is empty / shorter than the PDF text, replace it.
      - If `comments_to_author` is empty, set it to the PDF text.
      - Recompute `word_count`.
      - Set `extraction_status='ok'` and `available=True` when we got text.
      - Mirror PDF-derived recommendation only when missing (never overwrite
        a recommendation already captured from the platform's evaluations
        table).

    Returns True iff text was successfully extracted from the PDF.
    """
    if report is None:
        return False

    p = Path(pdf_path)
    text = extract_pdf_text(p)

    # Always record the attachment metadata, even if text extraction failed.
    attachments = report.setdefault("attachments", [])
    if not isinstance(attachments, list):
        attachments = []
        report["attachments"] = attachments
    entry = {"local_path": str(p), "filename": p.name}
    if attachment_url:
        entry["url"] = attachment_url
    if not any(
        (a.get("local_path") == entry["local_path"]) for a in attachments if isinstance(a, dict)
    ):
        attachments.append(entry)

    if not text:
        return False

    text = text[:max_chars]

    existing_raw = (report.get("raw_text") or "").strip()
    if overwrite or len(text) > len(existing_raw):
        report["raw_text"] = text

    # Replace comments_to_author with the PDF text if:
    #   - explicit overwrite, OR
    #   - existing is empty, OR
    #   - existing is a "stub pointer" (very short and contains common
    #     phrases reviewers use when they uploaded the report:
    #     "see attached", "see report", "see the file", "see the PDF",
    #     etc.), OR
    #   - PDF text is materially longer (>3x) than existing.
    existing_cta = (report.get("comments_to_author") or "").strip()
    existing_cta_lower = existing_cta.lower()
    stub_markers = (
        "see attached",
        "see the attached",
        "see attachment",
        "see the attachment",
        "see report",
        "see the report",
        "see the file",
        "see the pdf",
        "see pdf",
        "in the attached",
        "uploaded report",
    )
    is_stub = (len(existing_cta) < 200) and any(m in existing_cta_lower for m in stub_markers)
    if (
        overwrite
        or not existing_cta
        or is_stub
        or (existing_cta and len(text) >= 3 * len(existing_cta))
    ):
        report["comments_to_author"] = text

    wc_text = report.get("comments_to_author") or report.get("raw_text") or ""
    report["word_count"] = len(wc_text.split())

    if not (report.get("recommendation") or "").strip():
        guess = derive_recommendation_from_text(text)
        if guess:
            report["recommendation"] = guess

    report["available"] = True
    if report.get("extraction_status") in (None, "", "shell_only"):
        report["extraction_status"] = "ok"

    return True
