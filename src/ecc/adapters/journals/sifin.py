"""SIFIN journal adapter (SIAM platform) – scaffold implementation."""

from src.ecc.adapters.journals.base import AsyncJournalAdapter, JournalConfig
from src.ecc.core.domain.models import Manuscript


class SIFINAdapter(AsyncJournalAdapter):
    def __init__(self, headless: bool = True):
        super().__init__(
            JournalConfig(
                journal_id="SIFIN",
                name="SIAM Journal on Financial Mathematics",
                url="https://www.siam.org/journals/sifin",
                platform="SIAM",
                headless=headless,
            )
        )

    async def authenticate(self) -> bool:
        return True

    async def get_default_categories(self) -> list[str]:
        return ["Under Review", "Awaiting Referee Reports", "Awaiting Decision"]

    async def fetch_manuscripts(self, categories: list[str]) -> list[Manuscript]:
        try:
            await self.navigate_with_retry(self.config.url)
            if hasattr(self.page, "query_selector") and categories:
                from .category_selectors import select_category

                for cat in categories:
                    if await select_category(self.page, self.config.journal_id, cat):
                        break
            html = await self.page.content()
            from src.platforms.siam_parsers import parse_list_html

            items = parse_list_html(html, r"SIFIN-\d{4}-\d{4}")
            return [
                Manuscript(
                    journal_id=self.config.journal_id,
                    external_id=it["external_id"],
                    title=it.get("title", ""),
                )
                for it in items
            ]
        except Exception:
            return []

    async def extract_manuscript_details(self, manuscript_id: str) -> Manuscript:
        try:
            if hasattr(self.page, "query_selector"):
                try:
                    link = await self.page.query_selector(f"a:has-text('{manuscript_id}')")
                    if link:
                        await link.click()
                        await self.page.wait_for_load_state("networkidle")
                except Exception:
                    pass
            html = await self.page.content()
            from src.platforms.siam_parsers import (
                parse_audit_trail_html,
                parse_details_html,
                parse_referees_html,
            )

            details = parse_details_html(html)
            refs = parse_referees_html(html)
            events = parse_audit_trail_html(html)
            from src.ecc.core.audit_normalization import normalize_events

            ms = Manuscript(journal_id=self.config.journal_id, external_id=manuscript_id)
            from src.ecc.core.domain.models import Author, Referee

            for a in details.get("authors", []):
                ms.authors.append(Author(name=a.get("name", ""), email=a.get("email", "")))
            for r in refs:
                ref = Referee(name=r.get("name", ""))
                ref.historical_performance = {
                    k: r[k] for k in ("invited", "agreed", "due", "returned") if r.get(k)
                }
                ms.referees.append(ref)
            if events:
                ms.metadata["audit_trail"] = normalize_events(events)
            ms.metadata["file_links"] = details.get("files", [])
            return ms
        except Exception:
            return Manuscript(journal_id=self.config.journal_id, external_id=manuscript_id)

    async def download_manuscript_files(self, manuscript: Manuscript):
        downloaded = []
        try:
            links = manuscript.metadata.get("file_links", []) if manuscript.metadata else []
            if not links or not hasattr(self.page, "request"):
                return []
            self.config.download_dir.mkdir(parents=True, exist_ok=True)
            from src.ecc.core.domain.models import DocumentType, File
            from src.ecc.infrastructure.storage.utils import compute_checksum, guess_mime_type

            for f in links:
                try:
                    url = f.get("url", "")
                    fname = f.get("filename", "file")
                    resp = await self.page.request.get(url)
                    if resp.status != 200:
                        continue
                    save_path = self.config.download_dir / f"{manuscript.external_id}_{fname}"
                    body = await resp.body()
                    with open(save_path, "wb") as fh:
                        fh.write(body)
                    checksum = compute_checksum(save_path)
                    mime = guess_mime_type(save_path)
                    size = save_path.stat().st_size
                    if not any(getattr(fp, "checksum", "") == checksum for fp in manuscript.files):
                        dtype = (
                            DocumentType.MANUSCRIPT
                            if fname.lower().endswith(".pdf")
                            else DocumentType.SUPPLEMENTARY
                        )
                        manuscript.files.append(
                            File(
                                manuscript_id=manuscript.id,
                                document_type=dtype,
                                filename=save_path.name,
                                storage_path=str(save_path),
                                checksum=checksum,
                                mime_type=mime,
                                size_bytes=size,
                            )
                        )
                        downloaded.append(save_path)
                except Exception:
                    continue
        except Exception:
            return downloaded
        return downloaded

    async def fetch_all_manuscripts(self) -> list[Manuscript]:
        return await self.fetch_manuscripts(await self.get_default_categories())
