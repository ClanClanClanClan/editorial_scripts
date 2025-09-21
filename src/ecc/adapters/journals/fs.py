"""FS (Finance and Stochastics) email-based adapter using Gmail API.

Builds Manuscript objects from editorial email threads and enriches
people with ORCID when requested.
"""

import re
from datetime import datetime
from pathlib import Path

from src.ecc.adapters.messaging.email_client import EmailClient, EmailConfig, EmailProvider
from src.ecc.core.domain.models import (
    Author,
    DocumentType,
    File,
    Manuscript,
    ManuscriptStatus,
)


class FSAdapter:
    """Email-based adapter for the FS journal."""

    def __init__(self, headless: bool = True, download_dir: Path | None = None):
        self.journal_id = "FS"
        self.name = "Finance and Stochastics"
        self.config = EmailConfig(provider=EmailProvider.GMAIL_API)
        self.client = EmailClient(self.config)
        self.download_dir = download_dir or (Path.cwd() / "downloads" / self.journal_id)

    async def __aenter__(self):
        ok = await self.client.initialize()
        if not ok:
            raise RuntimeError("Failed to initialize Gmail client for FS")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Nothing to clean up for Gmail client
        return False

    async def authenticate(self) -> bool:
        """Gmail API initialization validation."""
        return self.client.gmail_service is not None

    async def fetch_all_manuscripts(self) -> list[Manuscript]:
        """Fetch messages and group into Manuscript objects by inferred ID.

        Heuristics:
        - Search newer messages related to FS editorial: subjects including 'Finance and Stochastics', 'FS -', or 'Manuscript ID'
        - Derive a manuscript ID from subject when possible; otherwise use thread/message id as surrogate
        - Populate basic metadata, author (from 'From' fields), and attach downloaded files
        """
        # Search queries (tune as needed)
        queries = [
            "newer_than:365d (subject:Finance and Stochastics OR subject:'Manuscript ID' OR subject:'FS -')",
        ]

        collected: dict[str, Manuscript] = {}

        for q in queries:
            messages = await self.client.search_messages(q, max_results=100)
            for m in messages:
                try:
                    msg = await self.client.get_message(m["id"], format="full")
                    headers = {
                        h["name"].lower(): h["value"]
                        for h in msg.get("payload", {}).get("headers", [])
                    }
                    subject = headers.get("subject", "")
                    date_str = headers.get("date", "")
                    from_field = headers.get("from", "")
                    to_field = headers.get("to", "")

                    external_id = self._infer_external_id(subject) or f"FS-{msg['id']}"
                    ms = collected.get(external_id)
                    if not ms:
                        ms = Manuscript(
                            journal_id=self.journal_id,
                            external_id=external_id,
                            title=subject[:200],
                            current_status=ManuscriptStatus.UNDER_REVIEW,
                            submission_date=datetime.utcnow(),
                        )
                        ms.metadata["fs_email_thread"] = []
                        collected[external_id] = ms

                    # Parse author/referee from From field heuristically
                    author_name, author_email = self._parse_name_email(from_field)
                    if author_name or author_email:
                        ms.authors.append(
                            Author(name=author_name or author_email, email=author_email or "")
                        )

                    # Save attachment files
                    saved = await self.client.download_attachments(msg, self.download_dir)
                    from src.ecc.infrastructure.storage.utils import (
                        compute_checksum,
                        guess_mime_type,
                    )

                    for sp in saved:
                        doc_type = self._classify_file(subject, sp.name)
                        checksum = compute_checksum(sp)
                        mime = guess_mime_type(sp)
                        size = sp.stat().st_size
                        if not any(getattr(f, "checksum", "") == checksum for f in ms.files):
                            ms.files.append(
                                File(
                                    manuscript_id=ms.id,
                                    document_type=doc_type,
                                    filename=sp.name,
                                    storage_path=str(sp),
                                    checksum=checksum,
                                    mime_type=mime,
                                    size_bytes=size,
                                )
                            )

                    # Append email metadata into audit-like trail
                    ms.metadata["fs_email_thread"].append(
                        {
                            "subject": subject,
                            "from": from_field,
                            "to": to_field,
                            "date": date_str,
                            "message_id": msg.get("id"),
                        }
                    )
                except Exception:
                    continue

        return list(collected.values())

    async def extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
        """FS has no browser details; return the collected object or a stub."""
        # In a stateless fetcher we would re-run search; here we return a stub
        ms = Manuscript(journal_id=self.journal_id, external_id=manuscript_id)
        return ms

    async def enrich_people_with_orcid(self, manuscript: Manuscript) -> None:
        """Enrich FS authors and referees using ORCID client."""
        try:
            from core.orcid_client import ORCIDClient

            client = ORCIDClient()

            for a in manuscript.authors:
                try:
                    e = client.enrich_person_profile(
                        {"name": a.name, "email": a.email, "institution": a.institution or ""}
                    )
                    if e.get("orcid"):
                        a.orcid = e["orcid"]
                    if e.get("current_affiliation"):
                        cur = e["current_affiliation"]
                        a.institution = cur.get("organization") or a.institution
                        a.department = cur.get("department") or a.department
                        a.country = cur.get("country") or a.country
                except Exception:
                    continue

            for r in manuscript.referees:
                try:
                    e = client.enrich_person_profile(
                        {"name": r.name, "email": r.email, "institution": r.institution or ""}
                    )
                    hp = r.historical_performance or {}
                    if e.get("orcid"):
                        hp["orcid"] = e["orcid"]
                    if e.get("research_interests"):
                        hp["research_interests"] = e["research_interests"]
                    if e.get("publication_count") is not None:
                        hp["publication_count"] = e["publication_count"]
                    r.historical_performance = hp
                except Exception:
                    continue
        except Exception:
            pass

    def _infer_external_id(self, subject: str) -> str | None:
        # Try to match patterns like FS-YYYY-XXXX or generic Document IDs
        m = re.search(r"\bFS[-\s]?\d{4}[-\s]?\d{3,5}\b", subject)
        if m:
            return m.group(0).replace(" ", "")
        m = re.search(r"\bManuscript ID[:\s]*([A-Za-z]+[-\s]?\d{4}[-\s]?\d+)\b", subject, re.I)
        if m:
            return m.group(1).replace(" ", "")
        return None

    def _parse_name_email(self, field: str) -> tuple[str | None, str | None]:
        # Very basic "Name <email>" or just email parse
        m = re.search(r"([^<]+)<([^>]+)>", field)
        if m:
            return m.group(1).strip().strip('"'), m.group(2).strip()
        m = re.search(r"([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})", field)
        if m:
            return None, m.group(1)
        return None, None

    def _classify_file(self, subject: str, filename: str) -> DocumentType:
        s = f"{subject} {filename}".lower()
        if "report" in s or "review" in s:
            return DocumentType.REFEREE_REPORT
        if "cover" in s:
            return DocumentType.COVER_LETTER
        if "decision" in s:
            return DocumentType.DECISION_LETTER
        if filename.lower().endswith(".pdf"):
            return DocumentType.MANUSCRIPT
        return DocumentType.SUPPLEMENTARY
