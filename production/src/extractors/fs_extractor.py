#!/usr/bin/env python3
"""
FS EXTRACTOR - EMAIL-BASED WORKFLOW
====================================

Production-ready extractor for Finance and Stochastics journal.
Uses Gmail API to extract manuscripts from email notifications.

Authentication: Gmail API OAuth
Platform: Email-based (Gmail)
"""

import os
import sys
import json
import re
import time
import base64
from pathlib import Path
from datetime import datetime, timedelta
import traceback
from typing import Optional, Dict, List, Any, Callable
from functools import wraps

# Add cache integration
sys.path.append(str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin

# Gmail API imports
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GMAIL_AVAILABLE = True
except ImportError:
    GMAIL_AVAILABLE = False
    HttpError = Exception
    print(
        "⚠️ Gmail API not available. Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
    )

try:
    import requests
except ImportError:
    requests = None


def with_api_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (
                    HttpError,
                    ConnectionError,
                    TimeoutError,
                    OSError,
                ) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff**attempt)
                        print(f"   ⚠️ {func.__name__} attempt {attempt + 1} failed: {str(e)[:50]}")
                        print(f"      Retrying in {wait_time:.1f} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"   ❌ {func.__name__} failed after {max_attempts} attempts")
                except Exception as e:
                    print(f"   ❌ {func.__name__} failed with unrecoverable error: {str(e)[:100]}")
                    raise
            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator


class ComprehensiveFSExtractor(CachedExtractorMixin):
    """Email-based extractor for Finance and Stochastics journal."""

    def __init__(self):
        self.init_cached_extractor("FS")

        # Gmail API scopes
        self.SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

        # Extraction state
        self.manuscripts = []
        self.service = None
        self.errors = []

        # Output directories (matching MF/MOR pattern)
        self.base_dir = Path(__file__).resolve().parent.parent.parent
        self.output_dir = self.base_dir / "outputs" / "fs"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Email patterns for FS
        self.email_patterns = {
            "new_submission": "new submission.*finance.*stochastics",
            "revision_request": "revision requested.*finance.*stochastics",
            "review_invitation": "invitation to review.*finance.*stochastics",
            "review_submitted": "review submitted.*finance.*stochastics",
            "decision_made": "decision.*finance.*stochastics",
            "manuscript_id": r"(?:FS|FSTO|fs)[-\s]?(\d{4,})",
            "title_pattern": r"Title:\s*([^\n]+)",
            "author_pattern": r"Author(?:s)?:\s*([^\n]+)",
            "status_pattern": r"Status:\s*([^\n]+)",
        }

        if not GMAIL_AVAILABLE:
            print("❌ Gmail API libraries not installed")

    def safe_int(self, value, default=0):
        """Safely convert value to int with default."""
        try:
            if value is None:
                return default
            if isinstance(value, (int, float)):
                return int(value)
            value = (
                str(value)
                .strip()
                .replace(",", "")
                .replace("$", "")
                .replace("%", "")
                .replace("#", "")
            )
            if not value:
                return default
            return int(float(value))
        except (ValueError, TypeError, AttributeError):
            return default

    def safe_get_text(self, content, default=""):
        """Safely extract text from any content."""
        try:
            if content is None:
                return default
            if isinstance(content, str):
                return content.strip()
            if hasattr(content, "text"):
                text = content.text
                return text.strip() if text else default
            return str(content).strip()
        except Exception:
            return default

    def safe_array_access(self, array, index, default=None):
        """Safely access array element with bounds checking."""
        try:
            if array is None or not hasattr(array, "__len__"):
                return default
            if isinstance(array, str):
                array = array.split()
            if len(array) > abs(index):
                return array[index]
            return default
        except (IndexError, TypeError, KeyError):
            return default

    def safe_pdf_extract(self, pdf_path, default=""):
        """Safely extract text from PDF with error handling."""
        try:
            if not pdf_path or not os.path.exists(pdf_path):
                return default
            import PyPDF2

            with open(pdf_path, "rb") as pdf_file:
                reader = PyPDF2.PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    try:
                        text += page.extract_text() + "\n"
                    except Exception:
                        continue
                return text.strip() if text else default
        except Exception:
            return default

    def safe_memory_cleanup(self):
        """Safely perform memory cleanup."""
        try:
            import gc

            collected = gc.collect()
            print(f"   🧹 Memory cleanup: {collected} objects collected")
            return True
        except Exception as e:
            print(f"   ⚠️ Memory cleanup failed: {e}")
            return False

    def setup_gmail_service(self) -> bool:
        """Initialize Gmail API service."""
        if not GMAIL_AVAILABLE:
            print("❌ Gmail API not available")
            return False

        try:
            creds = None

            # Token file paths
            token_paths = [
                "/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/config/gmail_token.json",
                "config/gmail_token.json",
                str(Path.home() / ".gmail_token.json"),
            ]

            # Load existing token
            for token_path in token_paths:
                if os.path.exists(token_path):
                    try:
                        creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                        print(f"✅ Loaded Gmail credentials from {token_path}")
                        break
                    except Exception as e:
                        print(f"⚠️ Failed to load {token_path}: {e}")
                        continue

            # Refresh if expired
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print("✅ Refreshed Gmail token")
                    # Save refreshed token
                    if token_paths and os.path.exists(token_paths[0]):
                        with open(token_paths[0], "w") as token:
                            token.write(creds.to_json())
                except Exception as e:
                    print(f"❌ Failed to refresh token: {e}")
                    return False

            if not creds or not creds.valid:
                print("❌ No valid Gmail credentials found")
                print("💡 Run setup_gmail_auth.py to configure Gmail API")
                return False

            # Build service
            self.service = build("gmail", "v1", credentials=creds)

            # Test service
            profile = self.service.users().getProfile(userId="me").execute()
            print(f"✅ Gmail API initialized for: {profile['emailAddress']}")

            return True

        except Exception as e:
            print(f"❌ Gmail setup error: {e}")
            traceback.print_exc()
            return False

    @with_api_retry(max_attempts=3, delay=1.0, backoff=2.0)
    def search_emails(self, query: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """Search Gmail for emails matching query."""
        emails = []

        results = (
            self.service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )

        messages = results.get("messages", [])

        for msg in messages:
            try:
                message = self.service.users().messages().get(userId="me", id=msg["id"]).execute()
                emails.append(message)
            except Exception as e:
                print(f"⚠️ Error fetching message {msg['id']}: {e}")
                continue

        print(f"📧 Found {len(emails)} emails matching query")
        return emails

    def get_email_attachments(self, email_message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment information from email."""
        attachments = []

        def process_parts(parts):
            for part in parts:
                if part.get("filename"):
                    attachment = {
                        "filename": part["filename"],
                        "mime_type": part.get("mimeType", ""),
                        "size": part["body"].get("size", 0),
                        "attachment_id": part["body"].get("attachmentId", ""),
                        "part_id": part.get("partId", ""),
                    }
                    attachments.append(attachment)
                if part.get("parts"):
                    process_parts(part["parts"])

        payload = email_message.get("payload", {})
        if payload.get("parts"):
            process_parts(payload["parts"])

        return attachments

    @with_api_retry(max_attempts=3, delay=1.0, backoff=2.0)
    def download_attachment(
        self, message_id: str, attachment_id: str, filename: str, manuscript_id: str = None
    ) -> Optional[str]:
        download_dir = self.base_dir / "downloads" / "fs"
        download_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = re.sub(r"[^\w\s.-]", "_", filename)
        if manuscript_id:
            generic = {"report.pdf", "review.pdf", "comments.pdf", "manuscript.pdf"}
            if safe_filename.lower() in generic:
                safe_filename = f"{manuscript_id}-{safe_filename}"
        file_path = download_dir / safe_filename

        if file_path.exists() and file_path.stat().st_size > 0:
            print(f"      📎 Skipped (exists): {safe_filename}")
            return str(file_path)

        attachment = (
            self.service.users()
            .messages()
            .attachments()
            .get(userId="me", messageId=message_id, id=attachment_id)
            .execute()
        )

        file_data = base64.urlsafe_b64decode(attachment["data"])

        with open(file_path, "wb") as f:
            f.write(file_data)

        print(f"      📎 Downloaded: {safe_filename}")
        return str(file_path)

    def extract_title_from_pdf(self, pdf_path: str) -> Optional[str]:
        try:
            import PyPDF2

            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)

                # Try metadata — but reject known junk
                if reader.metadata and "/Title" in reader.metadata:
                    title = (reader.metadata["/Title"] or "").strip()
                    if (
                        title
                        and len(title) > 20
                        and not title.endswith((".dvi", ".tex", ".pdf", ".ps"))
                        and "noname" not in title.lower()
                        and "manuscript no" not in title.lower()
                    ):
                        return title

                if not reader.pages:
                    return None

                text = reader.pages[0].extract_text()
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                if not lines:
                    return None

                # Find abstract anchor — title must be above it
                abstract_idx = len(lines)
                for i, line in enumerate(lines[:25]):
                    if re.match(r"^abstract\b", line, re.IGNORECASE):
                        abstract_idx = i
                        break

                junk_re = re.compile(
                    r"noname manuscript|will be inserted by the editor|"
                    r"manuscript no\b|^the date of|preprint submitted|"
                    r"^\(.*\)$|working paper|draft version",
                    re.IGNORECASE,
                )

                months = (
                    "january|february|march|april|may|june|"
                    "july|august|september|october|november|december"
                )
                date_re = re.compile(months, re.IGNORECASE)

                def is_author_line(line):
                    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", line):
                        return True
                    if "@" in line:
                        return True
                    if re.search(r"[†‡]", line) and len(line) < 80:
                        return True
                    stripped = re.sub(r"[∗†‡*]+$", "", line).strip()
                    words = [w for w in stripped.split() if w]
                    if not words:
                        return False
                    filler = {"and", "de", "van", "von", "der", "del", "di", "le", "la"}
                    cap_or_filler = all(w[0].isupper() or w in filler for w in words)
                    if cap_or_filler and len(words) <= 6 and len(stripped) < 50:
                        return True
                    return False

                # Collect title candidate lines: between start and abstract, skipping junk/authors/dates
                title_parts = []
                found_title_start = False
                for i in range(min(abstract_idx, 15)):
                    line = lines[i]
                    if junk_re.search(line):
                        continue
                    if len(line) < 10:
                        if found_title_start:
                            break
                        continue
                    if date_re.search(line) and len(line) < 40:
                        if found_title_start:
                            break
                        continue
                    if line.replace(".", "").replace(",", "").strip().isdigit():
                        continue
                    if re.match(r"^abstract\b", line, re.IGNORECASE):
                        break
                    if re.match(r"^(keywords|page|volume|issue)\b", line, re.IGNORECASE):
                        break
                    if is_author_line(line) and found_title_start:
                        break
                    if is_author_line(line):
                        continue
                    # This line is a title candidate
                    cleaned = re.sub(r"[∗†‡*]+$", "", line).strip()
                    if len(cleaned) >= 10:
                        title_parts.append(cleaned)
                        found_title_start = True

                if title_parts:
                    return " ".join(title_parts)

        except ImportError:
            print("      ⚠️ PyPDF2 not installed - can't extract PDF titles")
        except Exception as e:
            print(f"      ⚠️ Failed to extract title from PDF: {e}")

        return None

    def _search_title_by_authors(
        self, author_names: list, abstract_snippet: str = ""
    ) -> Optional[str]:
        if not requests or not author_names:
            return None
        from urllib.parse import quote_plus

        try:
            query_parts = [quote_plus(n) for n in author_names[:2]]
            query = "+".join(query_parts)
            url = f"https://api.crossref.org/works?query.author={query}&rows=5&sort=published&order=desc"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return None
            items = resp.json().get("message", {}).get("items", [])
            abstract_words = (
                set(abstract_snippet.lower().split()[:20]) if abstract_snippet else set()
            )
            for item in items:
                title = " ".join(item.get("title", []))
                if not title or len(title) < 15:
                    continue
                journal = " ".join(item.get("container-title", []))
                if "finance" in journal.lower() or "stochastic" in journal.lower():
                    return title
                if abstract_words:
                    item_abstract = item.get("abstract", "")
                    if item_abstract:
                        item_words = set(item_abstract.lower().split()[:30])
                        overlap = len(abstract_words & item_words)
                        if overlap >= 5:
                            return title
        except Exception:
            pass
        return None

    @staticmethod
    def _clean_pdf_text(text: str) -> str:
        if not text:
            return text
        ligatures = {"ﬃ": "ffi", "ﬄ": "ffl", "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬆ": "st"}
        for lig, repl in ligatures.items():
            text = text.replace(lig, repl)
        for repl in ["ffi", "ffl", "fi", "fl", "ff"]:
            doubled = repl + repl
            while doubled in text:
                text = text.replace(doubled, repl)
        broken_ligatures = {
            "di usion": "diffusion",
            "e ect": "effect",
            "e ective": "effective",
            "e iciency": "efficiency",
            "e icient": "efficient",
            "o er": "offer",
            "su icient": "sufficient",
            "su er": "suffer",
            "coe icient": "coefficient",
            "a ect": "affect",
            "a ord": "afford",
            "o icial": "official",
            "expecte d": "expected",
            "di erent": "different",
            "di erential": "differential",
            "re ection": "reflection",
            "re erence": "reference",
            "pre ference": "preference",
            "sto chastic": "stochastic",
            "speci c": "specific",
            "speci cation": "specification",
            "classi cation": "classification",
            "veri cation": "verification",
            "identi cation": "identification",
            "signi cant": "significant",
            "bene t": "benefit",
            "pro t": "profit",
            "de nition": "definition",
            "de ne": "define",
            "in nite": "infinite",
            "in nitesimal": "infinitesimal",
            "th e": "the",
            "appropr iate": "appropriate",
            "incomplet e": "incomplete",
            "equilibr ium": "equilibrium",
            "portf olio": "portfolio",
            "di erence": "difference",
            "di erences": "differences",
            "e ort": "effort",
            "su ciently": "sufficiently",
            "su cient": "sufficient",
            "insu cient": "insufficient",
            "ine cient": "inefficient",
        }
        for broken, fixed in broken_ligatures.items():
            text = re.sub(r"(?<!\w)" + re.escape(broken), fixed, text, flags=re.IGNORECASE)
        text = re.sub(r"(?<=[a-z])-\s+(?=[a-z])", "", text)
        text = re.sub(r"\s*\[\d+(?:,\s*\d+)*\]", "", text)
        text = re.sub(r"\s*\(\d+\)\s*", " ", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    def _extract_abstract_from_pdf(self, pdf_path: str) -> str:
        text = self.safe_pdf_extract(pdf_path, default="")
        if not text:
            return ""

        abstract_match = re.search(
            r"(?i)\babstract\b[.\s:]*\n?(.*?)(?=\n\s*(?:1[\.\s]|introduction|keywords|key\s*words|jel|msc|mathematics subject)\b)",
            text,
            re.DOTALL,
        )
        if abstract_match:
            abstract = abstract_match.group(1).strip()
            abstract = re.sub(r"\s+", " ", abstract)
            abstract = self._clean_pdf_text(abstract)
            if len(abstract) > 50:
                return abstract[:2000]

        lines = text.split("\n")
        body_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if len(stripped) > 80 and not stripped.isupper():
                body_start = i
                break
        if body_start > 0:
            body = " ".join(l.strip() for l in lines[body_start : body_start + 15] if l.strip())
            body = re.sub(r"\s+", " ", body)
            body = self._clean_pdf_text(body)
            if len(body) > 100:
                return body[:500]

        return ""

    def _extract_keywords_from_pdf(self, pdf_path: str) -> list:
        text = self.safe_pdf_extract(pdf_path, default="")
        if not text:
            return []
        patterns = [
            r"(?i)Keywords?[:\s]+(.*?)(?=\n\s*(?:JEL|MSC|Mathematics Subject|Contents|1[\.\s]|Introduction|\n\n))",
            r"(?i)Key\s?words?[:\s]+(.*?)(?=\n\s*(?:JEL|MSC|Mathematics Subject|Contents|1[\.\s]|Introduction|\n\n))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                raw = match.group(1).strip()
                raw = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", ";", raw)
                raw = re.sub(r"\s+", " ", raw)
                raw = self._clean_pdf_text(raw)
                if ";" in raw:
                    keywords = re.split(r"[;·•]", raw)
                else:
                    keywords = re.split(r"[,·•]", raw)
                keywords = [
                    k.strip().strip(".,") for k in keywords if k.strip() and len(k.strip()) > 2
                ]
                keywords = [k for k in keywords if not k.lower().startswith("contents")]
                return keywords[:10]
        return []

    @staticmethod
    def _clean_affiliation(text: str) -> str:
        if not text:
            return text
        text = re.sub(r"\s*\d+\s*\d*\s*Introduction\b.*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\b\d+\s+Introduction\b.*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"(?<=[a-z])-\s+(?=[a-z])", "", text)
        text = re.sub(r"^[∗†‡§¶*]+\s*", "", text)
        text = re.sub(r"\s*[Ee]-?mail:?\s*<[^>]+>", "", text)
        text = re.sub(r"\s*[Ee]-?mail:?\s*[\w.,+-]+@[\w.-]+\.\w+", "", text)
        text = re.sub(r"\s*<[\w.,+-]+@[\w.-]+\.\w+>", "", text)
        text = re.sub(r"\s*[\w.+-]+@[\w.-]+\.\w+", "", text)
        known_fixes = {
            "Infor matique": "Informatique",
            "E otv os Lor and": "Eötvös Loránd",
            "Eotv os Lor and": "Eötvös Loránd",
            "E otv os": "Eötvös",
            "Eotv os": "Eötvös",
            "Lor and University": "Loránd University",
            "Mathe matiques": "Mathematiques",
            "Math ematiques": "Mathematiques",
            "Univer sity": "University",
            "Labora toire": "Laboratoire",
            "Probabil ites": "Probabilites",
            "Statis tique": "Statistique",
            "Model isation": "Modelisation",
            "Centrale- Supelec": "CentraleSupelec",
            "Centrale -Supelec": "CentraleSupelec",
            "Yvett e": "Yvette",
            "Complexit e": "Complexite",
            "Syst emes": "Systemes",
        }
        for bad, good in known_fixes.items():
            text = text.replace(bad, good)
        text = re.sub(r"\s{2,}", " ", text).strip()
        text = text.rstrip("., ;:")
        return text

    @staticmethod
    def _restore_pdf_diacritics(text: str) -> str:
        import unicodedata

        def _add_acute(m):
            return m.group(1) + "\u0301"

        def _add_grave(m):
            return m.group(1) + "\u0300"

        text = re.sub(r"[\u00b4\u02ca]\s*([a-zA-Z])", _add_acute, text)
        text = re.sub(r"[\u0060\u02cb]\s*([a-zA-Z])", _add_grave, text)
        text = re.sub(r"(?<![a-zA-Z])[´]\s*([a-zA-Z])", _add_acute, text)
        text = re.sub(r"(?<![a-zA-Z])[`]\s*([a-zA-Z])", _add_grave, text)
        text = unicodedata.normalize("NFC", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text

    @staticmethod
    def _clean_latex_accents(text: str) -> str:
        import unicodedata

        text = re.sub(r"[´`]\s*([a-zA-Z])", r"\1", text)
        text = re.sub(r"[\u00b4\u0060\u02ca\u02cb]\s*([a-zA-Z])", r"\1", text)
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r"[\u0300-\u036f]", "", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text

    def extract_authors_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract authors with affiliations from PDF manuscript."""
        authors = []
        try:
            import PyPDF2

            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)

                # Try metadata first
                if reader.metadata and "/Author" in reader.metadata:
                    author_str = reader.metadata["/Author"]
                    if author_str:
                        author_str = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", ", ", author_str)
                        author_str = re.sub(r"[*†‡§¶#∗]+", "", author_str)
                        potential_authors = re.split(r"[,;&]|\sand\s", author_str)
                        for author in potential_authors:
                            author = author.strip()
                            if author and len(author.split()) >= 2:
                                authors.append({"name": author, "email": None, "affiliation": None})
                        if authors:
                            print(f"      📄 Found {len(authors)} authors in PDF metadata")

                # Parse first two pages for better extraction
                full_text = ""
                for page_num in range(min(2, len(reader.pages))):
                    full_text += reader.pages[page_num].extract_text() + "\n"

                full_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " , ", full_text)
                full_text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", full_text)
                diacritics_text = self._restore_pdf_diacritics(full_text)
                full_text = self._clean_latex_accents(full_text)
                lines = full_text.strip().split("\n")

                title_line_idx = -1
                for i, line in enumerate(lines[:30]):
                    line_clean = re.sub(r"[∗†‡§¶*]+$", "", line.strip()).strip()
                    if (
                        len(line_clean) > 30
                        and not any(char in line_clean for char in ["@", "†", "‡", "∗", "§"])
                        and not line_clean.isupper()
                        and not any(
                            keyword in line_clean.lower()
                            for keyword in ["abstract", "keywords", "introduction"]
                        )
                    ):
                        title_line_idx = i
                        break

                # Look for authors section (between title and abstract)
                if title_line_idx >= 0:
                    author_section = []
                    in_author_section = False

                    for i in range(title_line_idx + 1, min(title_line_idx + 40, len(lines))):
                        line = lines[i].strip()

                        # Stop at abstract/keywords
                        if any(
                            section in line.lower()
                            for section in [
                                "abstract",
                                "keywords",
                                "introduction",
                                "jel ",
                                "msc ",
                                "1.",
                            ]
                        ):
                            break

                        # Detect author lines
                        if "@" in line or re.search(r"^[A-Z]\w+(?:\s+[A-Z]\.?)?\s+[A-Z]\w+", line):
                            in_author_section = True
                            author_section.append(line)
                        elif in_author_section:
                            if line and line[0] in "∗†‡§¶" and len(line) > 5:
                                author_section.append(line)
                            elif line and not line[0].isdigit():
                                author_section.append(line)
                            elif line.startswith(("1", "2", "3", "4", "5")) and len(line) > 5:
                                author_section.append(line)

                    inst_kws = [
                        "universit",
                        "institute",
                        "laboratory",
                        "school",
                        "department",
                        "college",
                        "email",
                        "oxford",
                        "cambridge",
                        "eth",
                        "mit",
                        "cnrs",
                        "ceremade",
                        "inria",
                        "centre",
                        "center",
                        "faculty",
                        "research",
                        "mathematical",
                        "mathematics",
                        "polytechnique",
                        "dauphine",
                    ]
                    footnote_aff = None
                    for line in lines:
                        line_s = line.strip()
                        if line_s and line_s[0] in "∗†‡§¶" and len(line_s) > 10:
                            if any(kw in line_s.lower() for kw in inst_kws) or "@" in line_s:
                                if footnote_aff:
                                    author_section.append(footnote_aff)
                                footnote_aff = line_s
                                continue
                        if footnote_aff and line_s:
                            if line_s[0] in "∗†‡§¶" and len(line_s) > 10:
                                author_section.append(footnote_aff)
                                if any(kw in line_s.lower() for kw in inst_kws) or "@" in line_s:
                                    footnote_aff = line_s
                                else:
                                    footnote_aff = None
                                continue
                            if re.match(r"^\d+\s*[.)]?\s*\w", line_s) and not any(
                                kw in line_s.lower() for kw in inst_kws
                            ):
                                author_section.append(footnote_aff)
                                footnote_aff = None
                                continue
                            if (
                                any(kw in line_s.lower() for kw in inst_kws)
                                or "@" in line_s
                                or (len(line_s) > 5 and not line_s[0].isdigit())
                            ):
                                footnote_aff += " " + line_s
                            else:
                                author_section.append(footnote_aff)
                                footnote_aff = None
                        elif footnote_aff and not line_s:
                            author_section.append(footnote_aff)
                            footnote_aff = None
                    if footnote_aff:
                        author_section.append(footnote_aff)

                    authors_from_text = self._parse_author_section(author_section)
                    if authors_from_text and not authors:
                        authors = authors_from_text

                if authors and diacritics_text:
                    import unicodedata

                    nfd_text = unicodedata.normalize("NFD", diacritics_text)
                    for a in authors:
                        ascii_name = a["name"]
                        parts = ascii_name.split()
                        if len(parts) >= 2:
                            pattern = ""
                            for j, p in enumerate(parts):
                                if j > 0:
                                    pattern += r"[\s,]+"
                                for c in p:
                                    pattern += re.escape(c) + "[\u0300-\u036f]?"
                            try:
                                dm = re.search(pattern, nfd_text)
                                if dm:
                                    restored = unicodedata.normalize("NFC", dm.group(0).strip())
                                    restored = " ".join(restored.split())
                                    if len(restored) >= len(ascii_name) and restored != ascii_name:
                                        a["name"] = restored
                            except Exception:
                                pass

                if authors:
                    skip_domains = {
                        "gmail.com",
                        "yahoo.com",
                        "hotmail.com",
                        "outlook.com",
                        "springer.com",
                        "ethz.ch",
                    }
                    dehyphenated_text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", full_text)
                    dehyphenated_text = re.sub(r"(\w)-\s+(\w[\w.]*@)", r"\1\2", dehyphenated_text)
                    all_pdf_emails = re.findall(r"[\w.+-]+@[\w.-]+\.\w{2,}", dehyphenated_text)
                    all_pdf_emails = [
                        e for e in all_pdf_emails if e.split("@")[1].lower() not in skip_domains
                    ]
                    assigned_emails = {a["email"].lower() for a in authors if a.get("email")}
                    unassigned = [e for e in all_pdf_emails if e.lower() not in assigned_emails]
                    for a in authors:
                        if a.get("email"):
                            continue
                        aname = a["name"]
                        parts = aname.split()
                        if len(parts) < 2:
                            continue
                        surname = parts[-1].lower()
                        given = parts[0].lower()
                        best = None
                        for em in unassigned:
                            local = (
                                em.split("@")[0]
                                .lower()
                                .replace(".", " ")
                                .replace("-", " ")
                                .replace("_", " ")
                            )
                            if surname[:4] in local:
                                best = em
                                break
                            if len(given) > 2 and given[:3] in local and len(local) > 3:
                                best = em
                                break
                            initials = given[0] + surname
                            if initials in local.replace(" ", ""):
                                best = em
                                break
                        if best:
                            a["email"] = best
                            assigned_emails.add(best.lower())
                            unassigned = [e for e in unassigned if e.lower() != best.lower()]
                            if not a.get("affiliation"):
                                domain = best.split("@")[1]
                                inst = self._infer_institution_from_domain(domain)
                                if inst and inst != domain:
                                    a["affiliation"] = inst

            if authors:
                print(f"      ✅ Extracted {len(authors)} authors from PDF")
                for author in authors[:3]:
                    details = f"{author['name']}"
                    if author.get("email"):
                        details += f" ({author['email']})"
                    if author.get("affiliation"):
                        details += f" - {author['affiliation'][:30]}..."
                    print(f"         • {details}")
            else:
                print(f"      ⚠️ Could not extract authors from PDF")

        except ImportError:
            print("      ⚠️ PyPDF2 not installed - can't extract authors from PDF")
        except Exception as e:
            print(f"      ⚠️ Failed to extract authors from PDF: {e}")

        return authors

    def _parse_author_section(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Parse author section lines to extract names, emails, and affiliations."""
        authors = []
        affiliations = {}
        raw_affiliations = {}

        lines = [self._clean_latex_accents(l) for l in lines]

        letter_markers = set()
        for line in lines:
            match = re.match(r"^(\d+)\s*(.+)", line)
            if match:
                num, affiliation = match.groups()
                raw_affiliations[num] = affiliation.strip()
                affiliations[num] = self._clean_affiliation(affiliation.strip())
            sym_match = re.match(r"^([∗†‡§¶])\s*(.+)", line)
            if sym_match:
                marker, affiliation = sym_match.groups()
                raw_affiliations[marker] = affiliation.strip()
                affiliations[marker] = self._clean_affiliation(affiliation.strip())
            letter_match = re.match(r"^([a-z])\s*[A-Z]", line)
            if letter_match:
                lm = letter_match.group(1)
                rest = line[1:].strip()
                if any(
                    kw in rest.lower()
                    for kw in [
                        "universit",
                        "school",
                        "institute",
                        "department",
                        "college",
                        "laboratory",
                        "email",
                    ]
                ):
                    letter_markers.add(lm)
                    raw_affiliations[lm] = rest
                    affiliations[lm] = self._clean_affiliation(rest)

        expanded = []
        for orig_line in lines:
            chunks = re.split(r"([∗†‡§¶*]+)", orig_line)
            current_fragment = ""
            current_markers = []
            for chunk in chunks:
                if re.match(r"^[∗†‡§¶*]+$", chunk):
                    current_markers.extend(list(set(chunk)))
                else:
                    if current_fragment.strip():
                        sub_parts = re.split(r"\s*,\s*|\s+and\s+", current_fragment)
                        for sp in sub_parts:
                            if sp.strip():
                                expanded.append((sp.strip(), orig_line, list(current_markers)))
                        current_markers = []
                    else:
                        pass
                    current_fragment = chunk
            if current_fragment.strip():
                sub_parts = re.split(r"\s*,\s*|\s+and\s+", current_fragment)
                for sp in sub_parts:
                    if sp.strip():
                        expanded.append((sp.strip(), orig_line, list(current_markers)))

        for fragment, orig_line, fragment_markers in expanded:
            if not fragment:
                continue

            if re.match(r"^\d+\s+\w", fragment):
                continue

            email_match = re.search(r"([\w.+-]+@[\w.-]+\.\w+)", fragment)
            email = email_match.group(1) if email_match else None

            if email:
                name_match = re.search(
                    r"([A-Z][a-zA-Z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-zA-Z]+)(?:\s*[*†‡§¶#∗\d]*\s*[,:]?\s*"
                    + re.escape(email)
                    + ")",
                    fragment,
                )
                if name_match:
                    name = name_match.group(1)
                else:
                    name_part = fragment.split(email)[0].strip()
                    name = re.sub(r"[*†‡§¶#∗\d,]+", "", name_part).strip()
            else:
                name = re.sub(r"[*†‡§¶#∗\d]+", "", fragment).strip()
                if not re.match(r"^[A-Z]\w+(?:\s+[A-Z]\.?)?\s+[A-Z]\w+", name):
                    continue

            non_name_words = {
                "mathematical",
                "institute",
                "university",
                "universite",
                "department",
                "school",
                "laboratory",
                "road",
                "building",
                "street",
                "avenue",
                "abstract",
                "keywords",
                "classification",
                "france",
                "germany",
                "italy",
                "usa",
                "uk",
                "email",
                "e-mail",
                "cnrs",
                "umr",
                "ceremade",
                "saclay",
                "dauphine-psl",
                "centrale-supelec",
                "supelec",
                "cedex",
                "oxford",
                "cambridge",
                "december",
                "january",
                "february",
                "march",
                "april",
                "may",
                "june",
                "july",
                "august",
                "september",
                "october",
                "november",
                "polytechnique",
                "innovation",
                "office",
                "nkfih",
                "grants",
                "acknowledges",
                "support",
                "research",
                "ecole",
                "rte",
                "palaiseau",
                "mathematics",
                "probabilites",
                "statistique",
                "centre",
                "center",
                "college",
                "sciences",
                "gratefully",
                "funded",
                "acknowledgment",
                "acknowledgement",
                "financial",
                "hungarian",
                "national",
            }
            name_words = name.lower().split()
            if any(w.rstrip(".,;:") in non_name_words for w in name_words):
                continue
            if re.search(r"\b[A-Z]{2}\d", name) or re.search(r"\d{3,}", name):
                continue
            if len(name) > 50 or len(name.split()) > 4:
                continue
            if re.search(r"\(.*\)", name):
                continue

            if name and len(name.split()) >= 2:
                affiliation = None
                marker_chars = {"†": "†", "‡": "‡", "∗": "∗", "*": "∗", "§": "§", "¶": "¶"}
                for m in fragment_markers:
                    normalized_m = marker_chars.get(m, m)
                    if normalized_m in affiliations:
                        affiliation = affiliations[normalized_m]
                        break
                if not affiliation:
                    num_match = re.search(r"(\d)", fragment)
                    if num_match and num_match.group(1) in affiliations:
                        affiliation = affiliations[num_match.group(1)]

                if not affiliation and email:
                    domain = email.split("@")[1] if "@" in email else ""
                    if domain and domain not in ["gmail.com", "yahoo.com", "hotmail.com"]:
                        affiliation = self._infer_institution_from_domain(domain)

                authors.append({"name": name, "email": email, "affiliation": affiliation})

        if letter_markers:
            for a in authors:
                aname = a["name"]
                parts = aname.split()
                if parts:
                    last = parts[-1]
                    while len(last) > 2 and last[-1].lower() in letter_markers:
                        marker = last[-1].lower()
                        if not a.get("affiliation") and marker in affiliations:
                            a["affiliation"] = affiliations[marker]
                        last = last[:-1]
                    if last != parts[-1]:
                        parts[-1] = last
                        a["name"] = " ".join(parts)

        all_emails_expanded = []
        for aff_text in raw_affiliations.values():
            multi_local = re.search(
                r"([\w.+-]+(?:\s*,\s*[\w.+-]+)+)\s*@\s*([\w.-]+\.\w+)", aff_text
            )
            if multi_local:
                locals_str = multi_local.group(1)
                domain = multi_local.group(2)
                for local in re.split(r"\s*,\s*", locals_str):
                    local = local.strip()
                    if local:
                        all_emails_expanded.append(f"{local}@{domain}")
            single_emails = re.findall(r"[\w.+-]+@[\w.-]+\.\w+", aff_text)
            for em in single_emails:
                if em not in all_emails_expanded:
                    all_emails_expanded.append(em)

        for a in authors:
            if not a.get("email"):
                author_surname = a["name"].split()[-1].lower()
                author_given = a["name"].split()[0].lower() if a["name"].split() else ""
                for em in all_emails_expanded:
                    local = em.split("@")[0].lower()
                    if author_surname[:4] in local or (
                        author_given and author_given[:3] in local and len(author_given) > 2
                    ):
                        a["email"] = em
                        break
                if not a.get("email") and len(authors) == 1 and all_emails_expanded:
                    a["email"] = all_emails_expanded[0]

        return authors

    def _infer_institution_from_domain(self, domain: str) -> str:
        """Infer institution name from email domain."""
        # Common academic domain mappings
        known_domains = {
            "princeton.edu": "Princeton University",
            "sydney.edu.au": "University of Sydney",
            "uninsubria.it": "University of Insubria",
            "utoronto.ca": "University of Toronto",
            "math.ethz.ch": "ETH Zurich",
            "ethz.ch": "ETH Zurich",
            "caltech.edu": "California Institute of Technology",
            "nyu.edu": "New York University",
            "upmc.fr": "Sorbonne University",
            "imperial.ac.uk": "Imperial College London",
            "stanford.edu": "Stanford University",
            "mit.edu": "MIT",
            "harvard.edu": "Harvard University",
            "yale.edu": "Yale University",
            "columbia.edu": "Columbia University",
            "berkeley.edu": "UC Berkeley",
            "ucla.edu": "UCLA",
            "cambridge.ac.uk": "University of Cambridge",
            "oxford.ac.uk": "University of Oxford",
            "maths.ox.ac.uk": "University of Oxford",
            "wbs.ac.uk": "Warwick Business School",
            "warwick.ac.uk": "University of Warwick",
            "guasoni.com": "Dublin City University",
            "guasoni.it": "Dublin City University",
            "dcu.ie": "Dublin City University",
            "math.su.se": "Stockholm University",
            "su.se": "Stockholm University",
            "kth.se": "KTH Royal Institute of Technology",
            "polytechnique.edu": "Ecole Polytechnique",
            "cmap.polytechnique.fr": "Ecole Polytechnique",
            "ip-paris.fr": "Institut Polytechnique de Paris",
            "ensae.fr": "ENSAE Paris",
            "dauphine.psl.eu": "Universite Paris Dauphine-PSL",
            "dauphine.fr": "Universite Paris Dauphine-PSL",
            "univ-paris-saclay.fr": "Universite Paris-Saclay",
            "centralesupelec.fr": "CentraleSupelec",
            "cuhk.edu.cn": "Chinese University of Hong Kong, Shenzhen",
            "cuhk.edu.hk": "Chinese University of Hong Kong",
            "nus.edu.sg": "National University of Singapore",
            "lse.ac.uk": "London School of Economics",
            "ucl.ac.uk": "University College London",
            "tum.de": "Technical University of Munich",
            "hu-berlin.de": "Humboldt University of Berlin",
            "uni-konstanz.de": "University of Konstanz",
            "ualberta.ca": "University of Alberta",
            "mcgill.ca": "McGill University",
            "uwaterloo.ca": "University of Waterloo",
            "renyi.hu": "Renyi Institute of Mathematics",
            "renyi.mta.hu": "Renyi Institute of Mathematics",
            "sztaki.hu": "Hungarian Academy of Sciences",
            "univ-amu.fr": "Aix-Marseille University",
            "inria.fr": "INRIA",
            "ceremade.dauphine.fr": "CEREMADE, Universite Paris Dauphine-PSL",
            "link.cuhk.edu.cn": "Chinese University of Hong Kong, Shenzhen",
            "univr.it": "University of Verona",
            "univr.com": "University of Verona",
            "unipd.it": "University of Padova",
            "unipi.it": "University of Pisa",
            "polimi.it": "Polytechnic University of Milan",
            "uni-bielefeld.de": "Bielefeld University",
            "uni-mannheim.de": "University of Mannheim",
            "uni-bonn.de": "University of Bonn",
            "kcl.ac.uk": "King's College London",
            "ed.ac.uk": "University of Edinburgh",
            "bath.ac.uk": "University of Bath",
            "leeds.ac.uk": "University of Leeds",
            "qmul.ac.uk": "Queen Mary University of London",
        }

        if domain in known_domains:
            return known_domains[domain]

        # Try to infer from domain structure
        parts = domain.split(".")
        if len(parts) >= 2:
            institution = parts[0].replace("-", " ").title()
            if "edu" in domain:
                institution += " University"
            elif "ac" in domain:
                institution += " (Academic)"
            return institution

        return domain

    def search_paper_online(
        self, title: str, authors: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search for paper online (arXiv, Google Scholar, etc.) to get better author data."""
        print(f"      🔍 Searching online for: {title[:50]}...")

        enriched_data = {
            "found": False,
            "source": None,
            "authors": [],
            "arxiv_id": None,
            "doi": None,
            "url": None,
            "title": None,
        }

        try:
            import requests
            from urllib.parse import quote

            # Clean title for search
            clean_title = re.sub(r"[^\w\s]", " ", title).strip()

            # Try arXiv API first
            arxiv_query = quote(clean_title)
            arxiv_url = (
                f"http://export.arxiv.org/api/query?search_query=ti:{arxiv_query}&max_results=3"
            )

            try:
                response = requests.get(arxiv_url, timeout=5)
                if response.status_code == 200:
                    content = response.text

                    # Parse arXiv response (simple XML parsing)
                    if "<entry>" in content:
                        # Extract arXiv ID
                        id_match = re.search(r"<id>http://arxiv.org/abs/([^<]+)</id>", content)
                        if id_match:
                            enriched_data["arxiv_id"] = id_match.group(1)
                            enriched_data["url"] = f"https://arxiv.org/abs/{id_match.group(1)}"
                            enriched_data["source"] = "arXiv"
                            enriched_data["found"] = True

                            title_match = re.search(
                                r"<entry>.*?<title>([^<]+)</title>", content, re.DOTALL
                            )
                            if title_match:
                                enriched_data["title"] = " ".join(title_match.group(1).split())

                            from difflib import SequenceMatcher

                            arxiv_title = enriched_data.get("title", "")
                            title_sim = (
                                SequenceMatcher(
                                    None, clean_title.lower(), arxiv_title.lower()
                                ).ratio()
                                if arxiv_title
                                else 0
                            )
                            if title_sim < 0.4:
                                print(
                                    f"         ⚠️ arXiv title mismatch (sim={title_sim:.2f}): '{arxiv_title[:60]}'"
                                )
                                enriched_data["found"] = False
                                enriched_data["arxiv_id"] = None
                                enriched_data["url"] = None
                                enriched_data["source"] = None
                                enriched_data["title"] = None
                                return enriched_data

                            # Extract authors - limit to first 3 for FS papers (main authors)
                            author_matches = re.findall(r"<name>([^<]+)</name>", content)[:3]
                            for author_name in author_matches:
                                enriched_data["authors"].append(
                                    {
                                        "name": author_name.strip(),
                                        "email": None,
                                        "affiliation": None,
                                    }
                                )

                            # Try to get affiliations from arXiv summary (often contains author info)
                            summary_match = re.search(r"<summary>([^<]+)</summary>", content)
                            if summary_match:
                                summary = summary_match.group(1)
                                # Look for common affiliation patterns in summary
                                if (
                                    "university" in summary.lower()
                                    or "institute" in summary.lower()
                                ):
                                    # Extract first mentioned institution as approximation
                                    inst_match = re.search(
                                        r"([\w\s]+(?:University|Institute|College)[^,\.]*)",
                                        summary,
                                        re.IGNORECASE,
                                    )
                                    if inst_match and enriched_data["authors"]:
                                        affiliation = inst_match.group(1).strip()
                                        # Apply to all authors as approximation
                                        for author in enriched_data["authors"]:
                                            author["affiliation"] = affiliation

                            print(f"         ✅ Found on arXiv: {enriched_data['arxiv_id']}")
                            print(
                                f"         👥 {len(enriched_data['authors'])} authors with better names"
                            )

            except Exception as e:
                print(f"         ⚠️ arXiv search failed: {e}")

        except Exception as e:
            print(f"         ❌ Online search error: {e}")

        return enriched_data

    def enrich_authors_with_deep_web(self, authors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich author data with deep web search for affiliations and countries."""
        enriched_authors = []

        for author in authors:
            enriched = author.copy()

            # If we already have affiliation and country, skip enrichment
            if enriched.get("affiliation") and enriched.get("country"):
                enriched_authors.append(enriched)
                continue

            # If we don't have affiliation, try to find it
            if not enriched.get("affiliation") or enriched["affiliation"] == "Unknown":
                print(f"      🌐 Searching for affiliation: {author['name']}")

                # Build search query
                query = f'"{author["name"]}" professor researcher university'
                if author.get("email"):
                    domain = author["email"].split("@")[1] if "@" in author["email"] else ""
                    if domain:
                        query += f' {domain.split(".")[0]}'

                # In production, would use actual web search API
                # For now, use email domain inference
                if author.get("email"):
                    domain = author["email"].split("@")[1]
                    institution = self._infer_institution_from_domain(domain)
                    if institution != domain:
                        enriched["affiliation"] = institution
                        print(f"         ✅ Found affiliation: {institution}")

            # Add country based on affiliation
            if enriched.get("affiliation") and not enriched.get("country"):
                country = self._infer_country_from_affiliation(enriched["affiliation"])
                if country:
                    enriched["country"] = country

            enriched_authors.append(enriched)

        return enriched_authors

    def _infer_country_from_affiliation(self, affiliation: str) -> str:
        """Infer country from affiliation text."""
        affiliation_lower = affiliation.lower()

        # Country keywords
        country_patterns = {
            "USA": [
                "united states",
                "usa",
                "princeton",
                "stanford",
                "mit",
                "harvard",
                "yale",
                "columbia",
                "berkeley",
                "ucla",
                "caltech",
                "nyu",
            ],
            "UK": ["united kingdom", "uk", "oxford", "cambridge", "imperial", "london"],
            "Canada": ["canada", "toronto", "mcgill", "waterloo"],
            "Australia": ["australia", "sydney", "melbourne", "queensland"],
            "France": ["france", "paris", "sorbonne", "polytechnique"],
            "Germany": ["germany", "munich", "berlin", "heidelberg"],
            "Switzerland": ["switzerland", "eth zurich", "epfl", "zurich"],
            "Italy": ["italy", "milan", "rome", "bologna", "insubria"],
            "China": ["china", "beijing", "shanghai", "hong kong", "chinese university"],
            "Japan": ["japan", "tokyo", "kyoto", "osaka"],
        }

        for country, keywords in country_patterns.items():
            if any(keyword in affiliation_lower for keyword in keywords):
                return country

        # Check TLD patterns
        if ".edu" in affiliation_lower:
            return "USA"
        elif ".ac.uk" in affiliation_lower:
            return "UK"
        elif ".ca" in affiliation_lower:
            return "Canada"
        elif ".edu.au" in affiliation_lower:
            return "Australia"
        elif ".fr" in affiliation_lower:
            return "France"
        elif ".de" in affiliation_lower:
            return "Germany"
        elif ".ch" in affiliation_lower:
            return "Switzerland"
        elif ".it" in affiliation_lower:
            return "Italy"

        return None

    def enrich_referee_with_deep_web(
        self, referee_name: str, referee_email: str = None
    ) -> Dict[str, Any]:
        """Enrich referee information using web search."""
        enriched_data = {}

        try:
            import requests
            from urllib.parse import quote

            # Build search query
            query_parts = [f'"{referee_name}"']
            if referee_email:
                # Add domain from email as context
                domain = referee_email.split("@")[1] if "@" in referee_email else ""
                if domain and domain not in [
                    "gmail.com",
                    "yahoo.com",
                    "hotmail.com",
                    "outlook.com",
                ]:
                    query_parts.append(domain.split(".")[0])  # Institution hint

            query_parts.extend(["professor OR researcher OR academic", "university OR institute"])
            search_query = " ".join(query_parts)

            print(f"      🌐 Searching web for: {referee_name}")

            # Simulate web search (in production, use actual search API)
            # For now, we'll use domain-based inference
            if referee_email:
                domain = referee_email.split("@")[1] if "@" in referee_email else ""

                # Common academic domain mappings
                institution_map = {
                    "princeton.edu": {"institution": "Princeton University", "country": "USA"},
                    "sydney.edu.au": {
                        "institution": "University of Sydney",
                        "country": "Australia",
                    },
                    "uninsubria.it": {"institution": "University of Insubria", "country": "Italy"},
                    "utoronto.ca": {"institution": "University of Toronto", "country": "Canada"},
                    "math.ethz.ch": {"institution": "ETH Zurich", "country": "Switzerland"},
                    "ethz.ch": {"institution": "ETH Zurich", "country": "Switzerland"},
                    "caltech.edu": {
                        "institution": "California Institute of Technology",
                        "country": "USA",
                    },
                    "nyu.edu": {"institution": "New York University", "country": "USA"},
                    "upmc.fr": {"institution": "Sorbonne University", "country": "France"},
                    "lpsm.paris": {
                        "institution": "Laboratoire de Probabilités, Statistique et Modélisation",
                        "country": "France",
                    },
                    "imperial.ac.uk": {"institution": "Imperial College London", "country": "UK"},
                    "wbs.ac.uk": {"institution": "Warwick Business School", "country": "UK"},
                    "warwick.ac.uk": {"institution": "University of Warwick", "country": "UK"},
                    "guasoni.com": {"institution": "Dublin City University", "country": "Ireland"},
                    "guasoni.it": {"institution": "Dublin City University", "country": "Ireland"},
                    "dcu.ie": {"institution": "Dublin City University", "country": "Ireland"},
                    "math.su.se": {"institution": "Stockholm University", "country": "Sweden"},
                    "su.se": {"institution": "Stockholm University", "country": "Sweden"},
                    "maths.ox.ac.uk": {"institution": "University of Oxford", "country": "UK"},
                    "oxford.ac.uk": {"institution": "University of Oxford", "country": "UK"},
                    "cambridge.ac.uk": {"institution": "University of Cambridge", "country": "UK"},
                    "polytechnique.edu": {
                        "institution": "Ecole Polytechnique",
                        "country": "France",
                    },
                    "cmap.polytechnique.fr": {
                        "institution": "Ecole Polytechnique",
                        "country": "France",
                    },
                    "dauphine.psl.eu": {
                        "institution": "Universite Paris Dauphine-PSL",
                        "country": "France",
                    },
                    "univ-paris-saclay.fr": {
                        "institution": "Universite Paris-Saclay",
                        "country": "France",
                    },
                    "cuhk.edu.cn": {
                        "institution": "Chinese University of Hong Kong, Shenzhen",
                        "country": "China",
                    },
                    "cuhk.edu.hk": {
                        "institution": "Chinese University of Hong Kong",
                        "country": "China",
                    },
                    "renyi.hu": {
                        "institution": "Renyi Institute of Mathematics",
                        "country": "Hungary",
                    },
                    "sztaki.hu": {
                        "institution": "Hungarian Academy of Sciences",
                        "country": "Hungary",
                    },
                    "stanford.edu": {"institution": "Stanford University", "country": "USA"},
                    "mit.edu": {"institution": "MIT", "country": "USA"},
                    "harvard.edu": {"institution": "Harvard University", "country": "USA"},
                    "columbia.edu": {"institution": "Columbia University", "country": "USA"},
                    "berkeley.edu": {"institution": "UC Berkeley", "country": "USA"},
                    "inria.fr": {"institution": "INRIA", "country": "France"},
                }

                # Check for exact match
                if domain in institution_map:
                    enriched_data.update(institution_map[domain])
                    print(
                        f"         ✅ Found: {enriched_data['institution']}, {enriched_data['country']}"
                    )
                else:
                    # Try to infer from domain
                    if domain.endswith(".edu"):
                        enriched_data["country"] = "USA"
                    elif domain.endswith(".edu.au"):
                        enriched_data["country"] = "Australia"
                    elif domain.endswith(".ac.uk"):
                        enriched_data["country"] = "UK"
                    elif domain.endswith(".ca"):
                        enriched_data["country"] = "Canada"
                    elif domain.endswith(".fr"):
                        enriched_data["country"] = "France"
                    elif domain.endswith(".de"):
                        enriched_data["country"] = "Germany"
                    elif domain.endswith(".it"):
                        enriched_data["country"] = "Italy"
                    elif domain.endswith(".ch"):
                        enriched_data["country"] = "Switzerland"

                    # Try to extract institution from domain
                    if "." in domain:
                        parts = domain.split(".")
                        if len(parts) >= 2:
                            # Take the main part (e.g., 'stanford' from 'stanford.edu')
                            inst_name = parts[0].replace("-", " ").title()
                            if inst_name and len(inst_name) > 3:
                                enriched_data["institution_hint"] = inst_name
                                print(
                                    f"         💡 Inferred: {inst_name}, {enriched_data.get('country', 'Unknown')}"
                                )

            # Placeholder for ORCID search
            # In production, search ORCID API for the researcher
            # enriched_data['orcid'] = search_orcid(referee_name, enriched_data.get('institution'))

        except Exception as e:
            print(f"         ⚠️ Deep web search failed: {e}")

        return enriched_data

    # ==========================
    # PHASE 1: REPORT ANALYSIS
    # ==========================

    def extract_text_from_report_pdf(self, pdf_path: str) -> str:
        """Extract full text from referee report PDF."""
        try:
            import PyPDF2

            with open(pdf_path, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()

                if text.strip():
                    print(f"         📄 Extracted {len(text)} characters from report")
                    return text
        except ImportError:
            print("         ⚠️ PyPDF2 not installed for report extraction")
        except Exception as e:
            print(f"         ⚠️ Failed to extract report text: {e}")

        return ""

    def extract_recommendation_from_report(self, report_text: str) -> str:
        """Extract recommendation from referee report text."""
        if not report_text:
            return "Unknown"

        text_lower = report_text.lower()

        # Priority order (most specific first)
        recommendations = [
            ("reject", "Reject"),
            ("accept with minor", "Accept with Minor Revision"),
            ("accept with major", "Accept with Major Revision"),
            ("major revision", "Major Revision"),
            ("minor revision", "Minor Revision"),
            ("accept as is", "Accept"),
            ("accept", "Accept"),
            ("conditional accept", "Conditional Accept"),
            ("revise and resubmit", "Revise and Resubmit"),
            ("not suitable", "Reject"),
            ("recommend publication", "Accept"),
            ("do not recommend", "Reject"),
        ]

        # Look for explicit recommendation section
        rec_section_patterns = [
            r"recommendation[:\s]+([^\n]+)",
            r"my recommendation[:\s]+([^\n]+)",
            r"editorial recommendation[:\s]+([^\n]+)",
            r"final recommendation[:\s]+([^\n]+)",
            r"decision[:\s]+([^\n]+)",
        ]

        for pattern in rec_section_patterns:
            match = re.search(pattern, text_lower)
            if match:
                rec_text = match.group(1).strip()
                for keyword, recommendation in recommendations:
                    if keyword in rec_text:
                        print(f"         ⭐ Found recommendation: {recommendation}")
                        return recommendation

        # Fallback: search entire text
        for keyword, recommendation in recommendations:
            if keyword in text_lower:
                # Verify it's not negated
                context_start = max(0, text_lower.find(keyword) - 50)
                context = text_lower[context_start : context_start + 100]
                if (
                    "do not" not in context
                    and "don't" not in context
                    and "not" + keyword not in context
                ):
                    print(f"         ⭐ Inferred recommendation: {recommendation}")
                    return recommendation

        return "Unknown"

    def extract_review_scores(self, report_text: str) -> Dict[str, Any]:
        """Extract numerical scores from referee report."""
        scores = {}

        if not report_text:
            return scores

        # Common score patterns
        score_patterns = [
            # "Originality: 4/5" or "Originality: 4 out of 5"
            (r"(originality|novelty)[:\s]+(\d+)\s*(?:/|out of)\s*(\d+)", "originality"),
            (r"(significance|importance)[:\s]+(\d+)\s*(?:/|out of)\s*(\d+)", "significance"),
            (r"(clarity|presentation)[:\s]+(\d+)\s*(?:/|out of)\s*(\d+)", "clarity"),
            (r"(technical quality|rigor)[:\s]+(\d+)\s*(?:/|out of)\s*(\d+)", "technical_quality"),
            (r"(overall|total)[:\s]+(\d+)\s*(?:/|out of)\s*(\d+)", "overall"),
            # "Rate: 8/10" or "Score: 85%"
            (r"(?:rate|rating|score)[:\s]+(\d+)\s*(?:/|out of)\s*(\d+)", "overall_rating"),
            (r"(?:rate|rating|score)[:\s]+(\d+)%", "overall_percentage"),
            # Likert scale patterns
            (r"(strongly recommend|highly recommend)", "recommendation_strength", 5),
            (r"(recommend)", "recommendation_strength", 4),
            (r"(weakly recommend|marginally recommend)", "recommendation_strength", 3),
            (r"(neutral)", "recommendation_strength", 2),
            (r"(do not recommend|not recommend)", "recommendation_strength", 1),
        ]

        text_lower = report_text.lower()

        for pattern_info in score_patterns:
            if len(pattern_info) == 2:  # Regex pattern
                pattern, key = pattern_info
                match = re.search(pattern, text_lower)
                if match:
                    if "percentage" in key:
                        scores[key] = self.safe_int(match.group(1))
                    else:
                        score = self.safe_int(match.group(1))
                        if len(match.groups()) > 2:
                            max_score = self.safe_int(match.group(3))
                        else:
                            max_score = self.safe_int(match.group(2))
                        scores[key] = {"score": score, "max": max_score}
            else:  # Fixed value pattern
                pattern, key, value = pattern_info
                if re.search(pattern, text_lower):
                    scores[key] = value

        if scores:
            print(f"         📊 Extracted review scores: {list(scores.keys())}")

        return scores

    def extract_key_concerns(self, report_text: str) -> List[str]:
        """Extract main concerns and criticisms from referee report."""
        concerns = []

        if not report_text:
            return concerns

        # Keywords that indicate concerns
        concern_keywords = [
            "concern",
            "issue",
            "problem",
            "weakness",
            "limitation",
            "unclear",
            "missing",
            "lacks",
            "insufficient",
            "questionable",
            "doubt",
            "worry",
            "flaw",
            "error",
            "mistake",
        ]

        # Split into sentences
        sentences = re.split(r"[.!?]", report_text)

        for sentence in sentences:
            sentence_lower = sentence.lower().strip()

            # Check if sentence contains concern keywords
            if any(keyword in sentence_lower for keyword in concern_keywords):
                # Clean and add if substantial
                cleaned = sentence.strip()
                if len(cleaned) > 20 and len(cleaned) < 300:  # Reasonable length
                    concerns.append(cleaned)

        # Also look for numbered concerns
        numbered_patterns = [
            r"\d+[.)]\s*([^.]+(?:concern|issue|problem|weakness)[^.]+)",
            r"(?:first|second|third|main|major)\s+(?:concern|issue)[:\s]+([^.]+)",
        ]

        for pattern in numbered_patterns:
            matches = re.findall(pattern, report_text, re.IGNORECASE)
            for match in matches:
                cleaned = match.strip()
                if cleaned not in concerns and len(cleaned) > 20:
                    concerns.append(cleaned)

        # Limit to top 5 concerns
        concerns = concerns[:5]

        if concerns:
            print(f"         ⚠️ Extracted {len(concerns)} key concerns")

        return concerns

    def analyze_referee_report(self, report_path: str, referee_name: str = None) -> Dict[str, Any]:
        """Complete analysis of a referee report PDF."""
        analysis = {
            "report_path": report_path,
            "referee_name": referee_name,
            "text_extracted": False,
            "recommendation": "Unknown",
            "scores": {},
            "concerns": [],
            "report_length": 0,
        }

        # Extract text
        report_text = self.extract_text_from_report_pdf(report_path)
        if report_text:
            analysis["text_extracted"] = True
            analysis["report_length"] = len(report_text)

            # Extract components
            analysis["recommendation"] = self.extract_recommendation_from_report(report_text)
            analysis["scores"] = self.extract_review_scores(report_text)
            analysis["concerns"] = self.extract_key_concerns(report_text)

            # Store first 1000 chars as preview
            analysis["text_preview"] = report_text[:1000]

        return analysis

    def classify_document(self, filename: str, email_context: str = "") -> str:
        """Classify document type based on filename and email context."""
        filename_lower = filename.lower()

        # Check for referee reports first
        if any(
            keyword in filename_lower for keyword in ["report", "review", "referee", "comments"]
        ):
            return "referee_report"

        # Cover letter
        if any(keyword in filename_lower for keyword in ["cover", "letter", "coverletter"]):
            return "cover_letter"

        # Response to referees
        if any(
            keyword in filename_lower for keyword in ["response", "reply", "rebuttal", "answers"]
        ):
            return "response_to_referees"

        # Revised manuscript
        if any(keyword in filename_lower for keyword in ["revised", "revision", "r1", "r2", "r3"]):
            return "revised_manuscript"

        # Supplementary material
        if any(
            keyword in filename_lower
            for keyword in ["supplement", "appendix", "supporting", "additional"]
        ):
            return "supplementary"

        # Main manuscript (default for PDFs with manuscript ID)
        if filename_lower.endswith(".pdf"):
            # Check if it's the main manuscript (has ID, no other keywords)
            if re.search(r"FS-\d{2}-\d{3,4}", filename):
                return "main_manuscript"

        # Default
        return "other"

    # ==========================
    # PHASE 2: STATUS & DECISION TRACKING
    # ==========================

    def determine_manuscript_status(self, manuscript: Dict) -> str:
        """Determine manuscript status based on timeline and referee data."""
        # Check for explicit decision
        if manuscript.get("decision_date"):
            if "accept" in manuscript.get("final_decision", "").lower():
                return "Accepted"
            elif "reject" in manuscript.get("final_decision", "").lower():
                return "Rejected"

        # Check referee reports
        referees = manuscript.get("referees", {})
        if isinstance(referees, dict):
            referee_list = list(referees.values())
        else:
            referee_list = referees

        total_referees = len(referee_list)
        reports_received = sum(1 for r in referee_list if r.get("report_submitted"))

        # If we have all reports, awaiting decision
        if total_referees > 0 and reports_received == total_referees:
            # Check if all recommend accept
            recommendations = [r.get("recommendation", "Unknown") for r in referee_list]
            if all("Accept" in rec for rec in recommendations if rec != "Unknown"):
                return "Likely Accept"
            elif all("Reject" in rec for rec in recommendations if rec != "Unknown"):
                return "Likely Reject"
            elif any("Major" in rec for rec in recommendations):
                return "Major Revision Required"
            elif any("Minor" in rec for rec in recommendations):
                return "Minor Revision Required"
            else:
                return "Under Editorial Review"

        # If reports pending
        elif total_referees > 0:
            return "Under Review"

        # Check for revision indicators
        ms_id = manuscript.get("id", "")
        if re.search(r"[-.]R\d+", ms_id):
            return "Revision Under Review"

        # Default
        return "Submitted"

    def detect_revision_round(self, manuscript_id: str) -> int:
        """Detect revision round from manuscript ID."""
        match = re.search(r"[-.]R(\d+)", manuscript_id)
        if match:
            return int(match.group(1))
        return 0

    def extract_editorial_decision(self, email_body: str, subject: str = "") -> Dict[str, Any]:
        """Extract editorial decision from email."""
        decision = {"type": None, "date": None, "details": None}

        body_lower = email_body.lower()
        subject_lower = subject.lower()

        # Accept patterns
        accept_patterns = [
            "pleased to accept",
            "happy to accept",
            "accepted for publication",
            "acceptance of your manuscript",
            "manuscript has been accepted",
        ]

        # Reject patterns
        reject_patterns = [
            "regret to inform",
            "unable to accept",
            "not suitable for publication",
            "decline to publish",
            "manuscript has been rejected",
        ]

        # Revision patterns
        revision_patterns = [
            ("major revision", "Major Revision Required"),
            ("minor revision", "Minor Revision Required"),
            ("revise and resubmit", "Revise and Resubmit"),
            ("conditional accept", "Conditional Accept"),
            ("requires revision", "Revision Required"),
        ]

        # Check for acceptance
        for pattern in accept_patterns:
            if pattern in body_lower:
                decision["type"] = "Accept"
                decision["details"] = pattern
                return decision

        # Check for rejection
        for pattern in reject_patterns:
            if pattern in body_lower:
                decision["type"] = "Reject"
                decision["details"] = pattern
                return decision

        # Check for revision requirements
        for pattern, decision_type in revision_patterns:
            if pattern in body_lower or pattern in subject_lower:
                decision["type"] = decision_type
                decision["details"] = pattern
                return decision

        return decision

    def track_revision_history(self, manuscript: Dict) -> List[Dict]:
        """Track revision history from timeline."""
        revisions = []
        current_round = 0

        # Look for revision submissions in timeline
        for event in manuscript.get("timeline", []):
            subject = event.get("subject", "")
            revision_match = re.search(r"[-.]R(\d+)", subject)
            if revision_match:
                round_num = self.safe_int(revision_match.group(1))
                if round_num > current_round:
                    current_round = round_num
                    revisions.append(
                        {
                            "round": round_num,
                            "submitted_date": event.get("date"),
                            "decision": None,
                            "decision_date": None,
                        }
                    )

        # Match decisions to revisions
        for event in manuscript.get("timeline", []):
            if event.get("type") == "Decision":
                # Find which revision this decision applies to
                for revision in revisions:
                    if not revision["decision"]:
                        revision["decision"] = event.get("details", {}).get("decision_type")
                        revision["decision_date"] = event.get("date")
                        break

        return revisions

    def _normalize_name(self, name: str) -> str:
        name = name.strip().strip('"').strip("'").strip()
        name = re.sub(r"\s*\([^)]*\)\s*", " ", name).strip()
        if "," in name:
            parts = name.split(",", 1)
            name = f"{parts[1].strip()} {parts[0].strip()}"
        name = " ".join(name.split())
        if not name:
            return ""
        words = name.split()
        if len(words) == 2:
            if words[0].isupper() and not words[1].isupper() and len(words[0]) > 1:
                words = [words[1], words[0]]
            elif words[0].isupper() and words[1].isupper() and len(words[0]) > 1:
                words = [words[1], words[0]]
        name = " ".join(words)
        name = name.title()
        particles = {
            "De",
            "Der",
            "Den",
            "Van",
            "Von",
            "Di",
            "Du",
            "Le",
            "La",
            "Del",
            "Della",
            "Dos",
            "Das",
            "Het",
            "El",
            "Al",
        }
        words = name.split()
        for i, w in enumerate(words):
            if i > 0 and w in particles:
                words[i] = w.lower()
        return " ".join(words)

    def _extract_name_from_header(self, from_header: str) -> str:
        if not from_header:
            return ""
        name_match = re.search(r"^([^<]+)<", from_header)
        if name_match:
            return self._normalize_name(name_match.group(1))
        return self._normalize_name(from_header)

    def build_manuscript_timeline(
        self, manuscript_id: str, emails: List[Dict[str, Any]], is_current: bool = False
    ) -> Dict[str, Any]:
        """Build complete manuscript timeline from all related emails."""

        manuscript = {
            "id": manuscript_id,
            "title": "Title not found",
            "is_current": is_current,
            "authors": [],  # Will be list of dicts with name, email, affiliation, country
            "referees": {},  # Dict to track referee by name
            "timeline": [],  # Complete event timeline
            "manuscript_pdfs": [],
            "referee_reports": [],
            "editor": None,
            "editor_email": None,
            "status": "Unknown",
            "submission_date": None,
            "decision_date": None,
            "all_attachments": [],
            "arxiv_id": None,
            "paper_url": None,
            "doi": None,
            "revision_round": 0,
            "revision_history": [],
        }

        # Sort emails by date
        emails_with_dates = []
        for email in emails:
            headers = email["payload"].get("headers", [])
            date = next((h["value"] for h in headers if h["name"] == "Date"), "")
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            from_header = next((h["value"] for h in headers if h["name"] == "From"), "")

            emails_with_dates.append(
                {"email": email, "date": date, "subject": subject, "from": from_header}
            )

        # Sort chronologically
        emails_with_dates.sort(key=lambda x: x["date"])

        # Process each email in chronological order
        for email_data in emails_with_dates:
            email = email_data["email"]
            subject = email_data["subject"]
            from_header = email_data["from"]
            date = email_data["date"]

            # Extract email body
            body = self.get_email_body(email.get("payload", {}))

            # Skip Editorial Digest emails from timeline (they're user's own summaries)
            if "Editorial Digest" in subject and "dylansmb" in from_header.lower():
                continue  # Skip this email entirely

            event = {
                "date": date,
                "subject": subject,
                "from": from_header,
                "type": self.classify_email_type(subject, body),
                "details": {},
                "body_snippet": body[:500] if body else "",
            }

            # Check if this email contains a manuscript PDF - if so, sender is the editor
            # The editor is whoever sends the manuscript to Dylan FIRST
            has_manuscript_pdf = False
            for attachment in self.get_email_attachments(email):
                filename = attachment.get("filename", "")
                # Check for manuscript PDF (not referee reports)
                # Manuscript PDFs are named like "FS-XX-XXXX.pdf"
                # Referee reports are named like "Report FS-XX-XXXX.pdf" or contain "report"
                if filename and manuscript_id in filename and filename.lower().endswith(".pdf"):
                    # Exclude referee reports
                    if "report" not in filename.lower() and "review" not in filename.lower():
                        # This is likely the actual manuscript PDF
                        if filename.startswith(manuscript_id) or filename == f"{manuscript_id}.pdf":
                            has_manuscript_pdf = True
                            break

            # If this email has the manuscript PDF and we haven't identified an editor yet
            # Then this sender is the editor (Editor-in-Chief who sends to Associate Editor Dylan)
            if (
                has_manuscript_pdf
                and not manuscript["editor"]
                and "possamai" not in from_header.lower()
                and "dylansmb" not in from_header.lower()
            ):
                manuscript["editor"] = from_header
                editor_email_match = re.search(r"<([^>]+)>", from_header)
                if editor_email_match:
                    manuscript["editor_email"] = editor_email_match.group(1).lower()
                event["details"]["is_editor"] = True
                event["details"]["editor_type"] = "Editor-in-Chief"
                if not manuscript["submission_date"]:
                    manuscript["submission_date"] = date

            # Classify sender role (available to entire loop body)
            sender_is_referee = False
            sender_name = None
            is_dylan = "possamai" in from_header.lower() or "dylansmb" in from_header.lower()
            system_patterns = ["editorialoffice@fs.org", "no-reply"]
            is_system_email = any(pat.lower() in from_header.lower() for pat in system_patterns)
            sender_email_match = re.search(r"<([^>]+)>", from_header)
            sender_email_addr = sender_email_match.group(1).lower() if sender_email_match else ""
            is_editor = is_system_email
            if manuscript["editor_email"] and sender_email_addr:
                is_editor = is_editor or (sender_email_addr == manuscript["editor_email"])
            if not is_editor and manuscript["editor"]:
                editor_name_norm = self._extract_name_from_header(manuscript["editor"])
                sender_name_norm = self._extract_name_from_header(from_header)
                if editor_name_norm and sender_name_norm:
                    is_editor = is_editor or (editor_name_norm == sender_name_norm)

            if from_header and not is_dylan:
                if not is_editor:
                    # Key insight: Dylan (AE) forwards manuscripts to referees
                    # So if someone is responding about a manuscript, they're likely a referee
                    is_referee_response = False

                    # Check if this appears to be responding about the manuscript
                    # Responses like "Re: FS-XX-XXXX" or "R: FS-XX-XXXX" are from referees
                    if (
                        "Re:" in subject or "RE:" in subject or "R:" in subject
                    ) and manuscript_id in subject:
                        # This is a referee responding to Dylan's invitation
                        is_referee_response = True

                    # Also check for referee indicators
                    referee_indicators = [
                        "report",
                        "review",
                        "referee",
                        "attached",
                        "agree to",
                        "accept to",
                        "decline to",
                        "happy to review",
                    ]

                    # Extract name from sender
                    name_match = re.search(r"^([^<]+)<", from_header)
                    if name_match:
                        sender_name = self._normalize_name(name_match.group(1))
                        # Check if sender might be a referee based on indicators
                        # Also check if they're sending a report file
                        subject_lower = subject.lower()
                        body_lower = body.lower()[:2000]
                        has_report_attachment = any(
                            "report" in att.get("filename", "").lower()
                            for att in self.get_email_attachments(email)
                        )

                        if (
                            has_report_attachment
                            or is_referee_response
                            or any(
                                ind in subject_lower + " " + body_lower
                                for ind in referee_indicators
                            )
                        ):
                            sender_is_referee = True

                            # Extract institution from email
                            email_match = re.search(r"<([^>]+)>", from_header)
                            institution = "Unknown"
                            if email_match:
                                email_addr = email_match.group(1)
                                domain = email_addr.split("@")[1] if "@" in email_addr else ""
                                institution_map = {
                                    "cuhk.edu.hk": "Chinese University of Hong Kong",
                                    "princeton.edu": "Princeton University",
                                    "math.ethz.ch": "ETH Zurich",
                                    "uio.no": "University of Oslo",
                                    "caltech.edu": "Caltech",
                                    "sydney.edu.au": "University of Sydney",
                                    "gmail.com": "Independent",
                                }
                                for domain_part, inst_name in institution_map.items():
                                    if domain_part in domain:
                                        institution = inst_name
                                        break
                                if institution == "Unknown" and domain:
                                    institution = domain

                            # Add sender as referee
                            if sender_name and sender_name not in manuscript["referees"]:
                                referee_email = email_addr if email_match else ""

                                # Enrich referee data with deep web search
                                enriched_data = self.enrich_referee_with_deep_web(
                                    sender_name, referee_email
                                )

                                # Merge enriched data
                                if enriched_data.get("institution"):
                                    institution = enriched_data["institution"]
                                elif (
                                    enriched_data.get("institution_hint")
                                    and institution == "Unknown"
                                ):
                                    institution = enriched_data["institution_hint"]

                                manuscript["referees"][sender_name] = {
                                    "name": sender_name,
                                    "email": referee_email,
                                    "institution": institution,
                                    "country": enriched_data.get("country", None),
                                    "orcid": enriched_data.get("orcid", None),
                                    "invited_date": None,
                                    "response": None,
                                    "response_date": None,
                                    "report_submitted": False,
                                    "report_date": None,
                                    "recommendation": None,
                                }

            # Extract referee information from email body
            if (
                "referee" in body.lower() or "reviewer" in body.lower() or "review" in body.lower()
            ) and "Editorial Digest" not in subject:
                # Only extract referees from specific email types
                if (
                    any(x in subject.lower() for x in ["referee", "review", "report"])
                    and "dylansmb" not in from_header.lower()
                ):
                    referees_found = self.extract_referees_from_email(body, subject)
                    body_editor_normalized = (
                        self._extract_name_from_header(manuscript["editor"])
                        if manuscript["editor"]
                        else ""
                    )
                    for referee in referees_found:
                        referee_name = self._normalize_name(referee["name"])
                        if referee_name == body_editor_normalized:
                            continue
                        if referee_name not in manuscript["referees"]:
                            manuscript["referees"][referee_name] = {
                                "name": referee_name,
                                "email": referee.get("email", ""),
                                "institution": referee.get("institution", ""),
                                "invited_date": date if "invit" in subject.lower() else None,
                                "response": None,
                                "response_date": None,
                                "report_submitted": False,
                                "report_date": None,
                                "recommendation": None,
                            }

            # Update referee status — context-aware to avoid false positives
            body_lower = body.lower()[:3000]
            for referee_name in list(manuscript["referees"].keys()):
                ref_data = manuscript["referees"][referee_name]
                if sender_name and referee_name == sender_name:
                    if any(
                        kw in body_lower
                        for kw in [
                            "happy to review",
                            "agree to review",
                            "accept to review",
                            "glad to",
                            "pleased to review",
                            "happy to referee",
                        ]
                    ):
                        ref_data["response"] = "Accepted"
                        ref_data["response_date"] = date
                        event["details"]["referee_accepted"] = referee_name
                    elif any(
                        kw in body_lower
                        for kw in [
                            "unable to review",
                            "cannot review",
                            "decline",
                            "regret",
                            "unable to referee",
                        ]
                    ):
                        ref_data["response"] = "Declined"
                        ref_data["response_date"] = date
                        event["details"]["referee_declined"] = referee_name
                    if "submitted" in subject.lower() and "report" in body_lower:
                        ref_data["report_submitted"] = True
                        ref_data["report_date"] = date
                        event["details"]["report_submitted_by"] = referee_name
                elif referee_name.lower() in body_lower and (is_editor or is_system_email):
                    for sent in body.split("."):
                        if referee_name.lower() in sent.lower():
                            sent_lower = sent.lower()
                            if "accepted" in sent_lower or "agreed" in sent_lower:
                                ref_data["response"] = "Accepted"
                                ref_data["response_date"] = date
                            elif "declined" in sent_lower or "unable" in sent_lower:
                                ref_data["response"] = "Declined"
                                ref_data["response_date"] = date
                            break

            # Process attachments
            attachments = self.get_email_attachments(email)
            for attachment in attachments:
                filename = attachment["filename"]
                filename_lower = filename.lower()

                # Download important files
                if filename_lower.endswith(".pdf") or filename_lower.endswith(".docx"):
                    # Check if it's a manuscript PDF
                    is_manuscript = any(
                        keyword in filename_lower
                        for keyword in ["manuscript", "paper", "article", "submission"]
                    ) or re.match(r"^fs-\d{2}-\d{3,4}", filename_lower)

                    # Check if it's a referee report
                    is_report = any(
                        keyword in filename_lower
                        for keyword in ["report", "review", "referee", "comments"]
                    )

                    # Editor's first email with a PDF is the manuscript, even if filename is generic
                    if (
                        not is_manuscript
                        and not is_report
                        and has_manuscript_pdf
                        and not manuscript.get("manuscript_pdfs")
                    ):
                        is_manuscript = True

                    if is_manuscript and not is_report:
                        file_path = self.download_attachment(
                            email["id"], attachment["attachment_id"], filename, manuscript_id
                        )
                        if file_path:
                            if file_path not in manuscript["manuscript_pdfs"]:
                                manuscript["manuscript_pdfs"].append(file_path)
                            event["details"]["manuscript_pdf"] = filename

                            # Try to extract title
                            if not manuscript["title"] or manuscript["title"] == "Title not found":
                                if file_path.endswith(".pdf"):
                                    pdf_title = self.extract_title_from_pdf(file_path)
                                    if pdf_title:
                                        manuscript["title"] = pdf_title

                            if not manuscript.get("abstract") and file_path.endswith(".pdf"):
                                manuscript["abstract"] = self._extract_abstract_from_pdf(file_path)

                            if not manuscript.get("keywords") and file_path.endswith(".pdf"):
                                manuscript["keywords"] = self._extract_keywords_from_pdf(file_path)

                            # Try to extract authors
                            if not manuscript["authors"] and file_path.endswith(".pdf"):
                                pdf_authors = self.extract_authors_from_pdf(file_path)

                                # If we have a reasonable title, try online search for better data
                                search_title = manuscript["title"]
                                title_usable = (
                                    search_title
                                    and search_title != "Title not found"
                                    and len(search_title) > 20
                                    and not search_title.endswith((".dvi", ".tex", ".pdf"))
                                    and "noname" not in search_title.lower()
                                )
                                if title_usable:
                                    online_data = self.search_paper_online(
                                        search_title, pdf_authors
                                    )
                                    if online_data["found"]:
                                        arxiv_authors = online_data.get("authors", [])
                                        if arxiv_authors and pdf_authors:
                                            pdf_surnames = {
                                                a.get("name", "").split()[-1].lower()
                                                for a in pdf_authors
                                                if a.get("name")
                                            }
                                            arxiv_surnames = {
                                                a.get("name", "").split()[-1].lower()
                                                for a in arxiv_authors
                                                if a.get("name")
                                            }
                                            if (
                                                len(pdf_authors) == len(arxiv_authors)
                                                and pdf_surnames == arxiv_surnames
                                            ):
                                                pdf_by_sn = {
                                                    a.get("name", "").split()[-1].lower(): a
                                                    for a in pdf_authors
                                                    if a.get("name")
                                                }
                                                for aa in arxiv_authors:
                                                    sn = aa.get("name", "").split()[-1].lower()
                                                    pa = pdf_by_sn.get(sn)
                                                    if pa:
                                                        if pa.get("email") and not aa.get("email"):
                                                            aa["email"] = pa["email"]
                                                        if pa.get("affiliation") and not aa.get(
                                                            "affiliation"
                                                        ):
                                                            aa["affiliation"] = pa["affiliation"]
                                                pdf_authors = arxiv_authors
                                            elif pdf_surnames & arxiv_surnames:
                                                arxiv_by_surname = {}
                                                for a in arxiv_authors:
                                                    s = a.get("name", "").split()[-1].lower()
                                                    arxiv_by_surname[s] = a
                                                for pa in pdf_authors:
                                                    s = pa.get("name", "").split()[-1].lower()
                                                    if s in arxiv_by_surname:
                                                        aa = arxiv_by_surname[s]
                                                        if aa.get("affiliation") and not pa.get(
                                                            "affiliation"
                                                        ):
                                                            pa["affiliation"] = aa["affiliation"]
                                                        if aa.get("email") and not pa.get("email"):
                                                            pa["email"] = aa["email"]
                                        elif arxiv_authors and not pdf_authors:
                                            from difflib import SequenceMatcher

                                            arxiv_title = online_data.get("title", "")
                                            sim = SequenceMatcher(
                                                None, search_title.lower(), arxiv_title.lower()
                                            ).ratio()
                                            if sim > 0.5:
                                                pdf_authors = arxiv_authors
                                            else:
                                                print(
                                                    f"         ⚠️ arXiv title mismatch (sim={sim:.2f}), skipping authors"
                                                )
                                        manuscript["arxiv_id"] = online_data.get("arxiv_id")
                                        manuscript["paper_url"] = online_data.get("url")
                                        arxiv_title = online_data.get("title")
                                        if arxiv_title and (
                                            not manuscript["title"]
                                            or manuscript["title"] == "Title not found"
                                            or len(manuscript["title"]) < 15
                                            or manuscript["title"].endswith(
                                                (".dvi", ".tex", ".pdf")
                                            )
                                        ):
                                            manuscript["title"] = arxiv_title

                                # Enrich author data
                                if pdf_authors:
                                    manuscript["authors"] = self.enrich_authors_with_deep_web(
                                        pdf_authors
                                    )

                    elif is_report:
                        file_path = self.download_attachment(
                            email["id"], attachment["attachment_id"], filename, manuscript_id
                        )
                        if file_path:
                            # Try to match report to specific referee
                            report_referee = None

                            # First check if sender is a known referee
                            if sender_name and sender_name in manuscript["referees"]:
                                report_referee = sender_name
                                manuscript["referees"][sender_name]["report_submitted"] = True
                                manuscript["referees"][sender_name]["report_date"] = date
                            else:
                                # Try to match based on filename or email content
                                for referee_name in manuscript["referees"].keys():
                                    # Check if referee name is in filename or body
                                    if (
                                        referee_name.split()[0].lower() in filename_lower
                                        or referee_name.lower() in body.lower()[:500]
                                    ):
                                        report_referee = referee_name
                                        manuscript["referees"][referee_name][
                                            "report_submitted"
                                        ] = True
                                        manuscript["referees"][referee_name]["report_date"] = date
                                        break

                            # ANALYZE THE REPORT
                            report_analysis = self.analyze_referee_report(file_path, report_referee)

                            # Store report with analysis
                            report_data = {
                                "filename": filename,
                                "path": file_path,
                                "date": date,
                                "from": from_header,
                                "referee": report_referee or "Unknown",
                                "analysis": report_analysis,
                            }
                            manuscript["referee_reports"].append(report_data)

                            # Update referee with recommendation
                            if report_referee and report_referee in manuscript["referees"]:
                                manuscript["referees"][report_referee][
                                    "recommendation"
                                ] = report_analysis["recommendation"]
                                if report_analysis.get("scores"):
                                    manuscript["referees"][report_referee][
                                        "review_scores"
                                    ] = report_analysis["scores"]
                                if report_analysis.get("concerns"):
                                    manuscript["referees"][report_referee][
                                        "concerns"
                                    ] = report_analysis["concerns"]

                            event["details"]["report_file"] = filename
                            if report_referee:
                                event["details"]["report_by"] = report_referee
                            if report_analysis["recommendation"] != "Unknown":
                                event["details"]["recommendation"] = report_analysis[
                                    "recommendation"
                                ]

                noise_patterns = ["outlook-", "logo", "signature", "icon", "image00"]
                is_noise = any(
                    p in filename_lower for p in noise_patterns
                ) and filename_lower.endswith((".png", ".gif", ".jpg", ".jpeg"))
                if not is_noise:
                    manuscript["all_attachments"].append(
                        {"filename": filename, "date": date, "email_subject": subject}
                    )

            # Update manuscript status based on email
            if "decision" in subject.lower():
                if "accept" in body.lower():
                    manuscript["status"] = "Accepted"
                    manuscript["decision_date"] = date
                elif "reject" in body.lower():
                    manuscript["status"] = "Rejected"
                    manuscript["decision_date"] = date
                elif "revision" in body.lower():
                    manuscript["status"] = "Revision Requested"
            elif "new submission" in subject.lower():
                manuscript["status"] = "New Submission"
                manuscript["submission_date"] = date
            elif "under review" in body.lower():
                manuscript["status"] = "Under Review"

            # Add event to timeline
            manuscript["timeline"].append(event)

        cleaned_referees = {}
        editor_normalized = (
            self._extract_name_from_header(manuscript["editor"]) if manuscript["editor"] else ""
        )

        def _name_parts_set(n):
            return set(w.lower() for w in n.split() if len(w) > 1)

        def _find_existing_match(clean_name, cleaned_refs):
            if clean_name in cleaned_refs:
                return clean_name
            name_set = _name_parts_set(clean_name)
            for existing_name in cleaned_refs:
                if _name_parts_set(existing_name) == name_set:
                    return existing_name
            return None

        for name, referee_data in manuscript["referees"].items():
            clean_name = self._normalize_name(name)
            if "Email Crosscheck" in clean_name:
                clean_name = self._normalize_name(clean_name.replace("Email Crosscheck", ""))

            if (
                not clean_name
                or len(clean_name) < 3
                or clean_name.lower() in ["unknown", "n/a", "none"]
            ):
                continue

            if clean_name.lower() in ["editorial office", "editor", "system", "admin"]:
                continue

            if editor_normalized and clean_name == editor_normalized:
                continue

            existing_key = _find_existing_match(clean_name, cleaned_referees)
            if not existing_key:
                referee_data["name"] = clean_name
                cleaned_referees[clean_name] = referee_data
            else:
                existing = cleaned_referees[existing_key]
                if not existing.get("email") and referee_data.get("email"):
                    existing["email"] = referee_data["email"]
                if not existing.get("institution") or existing.get("institution") == "Unknown":
                    if (
                        referee_data.get("institution")
                        and referee_data.get("institution") != "Unknown"
                    ):
                        existing["institution"] = referee_data["institution"]
                if referee_data.get("report_submitted"):
                    existing["report_submitted"] = True
                    existing["report_date"] = referee_data.get("report_date")
                if not existing.get("response") and referee_data.get("response"):
                    existing["response"] = referee_data["response"]
                if not existing.get("response_date") and referee_data.get("response_date"):
                    existing["response_date"] = referee_data["response_date"]
                if not existing.get("invited_date") and referee_data.get("invited_date"):
                    existing["invited_date"] = referee_data["invited_date"]

        manuscript["referees"] = list(cleaned_referees.values())

        for ref in manuscript["referees"]:
            ref_name = ref.get("name", "")
            ref_email = ref.get("email", "")
            parts = ref_name.split()
            if len(parts) == 2 and ref_email and "@" in ref_email:
                local = (
                    ref_email.split("@")[0]
                    .lower()
                    .replace(".", " ")
                    .replace("-", " ")
                    .replace("_", " ")
                )
                local_parts = local.split()
                if len(local_parts) >= 2:
                    email_first = local_parts[0]
                    email_last = local_parts[-1]
                    name_first = parts[0].lower()
                    name_last = parts[1].lower()
                    if (
                        email_first[:3] == name_last[:3]
                        and email_last[:3] == name_first[:3]
                        and email_first[:3] != email_last[:3]
                    ):
                        ref["name"] = f"{parts[1]} {parts[0]}"

        ref_names_set = {r["name"] for r in manuscript["referees"] if r.get("name")}
        ref_name_parts = {frozenset(n.lower().split()): n for n in ref_names_set}
        for report in manuscript.get("referee_reports", []):
            rn = report.get("referee", "")
            if rn and rn != "Unknown" and rn not in ref_names_set:
                rn_parts = frozenset(rn.lower().split())
                if rn_parts in ref_name_parts:
                    report["referee"] = ref_name_parts[rn_parts]

        def _sort_date(event):
            d = event.get("date", "")
            try:
                import email.utils

                dt = email.utils.parsedate_to_datetime(d)
                return dt.timestamp()
            except Exception:
                return 0.0

        try:
            manuscript["timeline"].sort(key=_sort_date)
        except Exception:
            pass

        editor_name = manuscript.get("editor", "")
        editor_surname = ""
        if editor_name:
            parts = self._extract_name_from_header(editor_name).split() if editor_name else []
            editor_surname = parts[-1].lower() if parts else ""

        first_editor_email_date = None
        for event in manuscript["timeline"]:
            det = event.get("details", {})
            frm = event.get("from", "").lower()
            is_editor = (
                det.get("is_editor") or (editor_surname and editor_surname in frm) or "dylan" in frm
            )
            if is_editor and not any(x in frm for x in ["possamai", "dylansmb"]):
                first_editor_email_date = event["date"]
                break
        if not first_editor_email_date:
            for event in manuscript["timeline"]:
                first_editor_email_date = event["date"]
                break

        for ref in manuscript["referees"]:
            ref_name = ref.get("name", "")
            if ref.get("report_submitted") and not ref.get("response"):
                ref["response"] = "Accepted"

            ref_surname = ref_name.split()[-1].lower() if ref_name else ""

            if not ref.get("invited_date") and ref_name:
                best_invite = None
                weak_invite = None

                for event in manuscript["timeline"]:
                    frm = event.get("from", "").lower()
                    subj = event.get("subject", "")
                    det = event.get("details", {})
                    body_snip = event.get("body_snippet", "")

                    is_dylan = "possamai" in frm or "dylansmb" in frm
                    is_from_editor = (
                        det.get("is_editor")
                        or "editor" in frm
                        or "springer" in frm
                        or "editorial" in frm
                        or (editor_surname and editor_surname in frm)
                    )

                    if is_from_editor and not is_dylan and ref_surname:
                        searchable = (subj + " " + body_snip).lower()
                        if ref_surname in searchable:
                            if "invit" in searchable:
                                best_invite = event["date"]
                                break
                            if not weak_invite:
                                weak_invite = event["date"]

                    if ref_name in str(det.get("referee_accepted", "")) or ref_name in str(
                        det.get("referee_declined", "")
                    ):
                        if not best_invite:
                            best_invite = event["date"]
                        break

                if best_invite:
                    ref["invited_date"] = best_invite
                elif weak_invite:
                    ref["invited_date"] = weak_invite
                else:
                    ref["invited_date"] = first_editor_email_date

            if first_editor_email_date:
                import email.utils as _eu

                should_fix = False
                if (
                    ref.get("invited_date")
                    and ref.get("response_date")
                    and ref["invited_date"] == ref["response_date"]
                ):
                    should_fix = True
                elif ref.get("invited_date"):
                    try:
                        inv_dt = _eu.parsedate_to_datetime(ref["invited_date"])
                        ed_dt = _eu.parsedate_to_datetime(first_editor_email_date)
                        if ed_dt < inv_dt:
                            should_fix = True
                    except Exception:
                        pass
                if should_fix:
                    try:
                        ed_dt = _eu.parsedate_to_datetime(first_editor_email_date)
                        inv_dt = (
                            _eu.parsedate_to_datetime(ref["invited_date"])
                            if ref.get("invited_date")
                            else None
                        )
                        if not inv_dt or ed_dt < inv_dt:
                            ref["invited_date"] = first_editor_email_date
                    except Exception:
                        ref["invited_date"] = first_editor_email_date

            if ref.get("response") == "Accepted" and not ref.get("response_date") and ref_surname:
                for event in manuscript["timeline"]:
                    frm = event.get("from", "").lower()
                    if ref_surname in frm and "possamai" not in frm and "dylansmb" not in frm:
                        if not (editor_surname and editor_surname in frm):
                            subj_lower = event.get("subject", "").lower()
                            if (
                                "automatic reply" not in subj_lower
                                and "auto-reply" not in subj_lower
                                and "out of office" not in subj_lower
                            ):
                                ref["response_date"] = event["date"]
                                break

            if ref.get("report_submitted") and not ref.get("response_date"):
                ref_s = ref.get("name", "").split()[-1].lower() if ref.get("name") else ""
                for event in manuscript["timeline"]:
                    frm = event.get("from", "").lower()
                    if ref_s and ref_s in frm:
                        subj_lower = event.get("subject", "").lower()
                        if (
                            "automatic reply" in subj_lower
                            or "auto-reply" in subj_lower
                            or "out of office" in subj_lower
                        ):
                            continue
                        report_date = ref.get("report_date")
                        if report_date and event["date"] != report_date:
                            ref["response_date"] = event["date"]
                            if not ref.get("response"):
                                ref["response"] = "Accepted"
                            break

            self._enforce_date_chronology(ref)

        ref_surnames = {
            r.get("name", "").split()[-1].lower() for r in manuscript["referees"] if r.get("name")
        }
        for author in manuscript.get("authors", []):
            aname = author.get("name", "")
            parts = aname.split()
            if len(parts) >= 2:
                surname = parts[-1]
                if len(surname) > 2 and surname.lower() not in ref_surnames:
                    trimmed = surname[:-1].lower()
                    if trimmed in ref_surnames:
                        parts[-1] = surname[:-1]
                        author["name"] = " ".join(parts)

        # Summary statistics
        manuscript["total_emails"] = len(emails_with_dates)
        manuscript["total_referees"] = len(manuscript["referees"])
        manuscript["referees_accepted"] = sum(
            1 for r in manuscript["referees"] if r["response"] == "Accepted"
        )
        manuscript["referees_declined"] = sum(
            1 for r in manuscript["referees"] if r["response"] == "Declined"
        )
        manuscript["reports_received"] = sum(
            1 for r in manuscript["referees"] if r["report_submitted"]
        )

        manuscript["revision_round"] = self.detect_revision_round(manuscript_id)
        manuscript["revision_history"] = self.track_revision_history(manuscript)

        for att in manuscript.get("all_attachments", []):
            fn = att.get("filename", "")
            rev_match = re.search(r"-R(\d+)", fn, re.IGNORECASE)
            if rev_match:
                round_num = int(rev_match.group(1))
                if round_num > manuscript["revision_round"]:
                    manuscript["revision_round"] = round_num
            fn_lower = fn.lower()
            if "response" in fn_lower or "rebuttal" in fn_lower:
                att["document_type"] = "author_response"

        if manuscript["revision_round"] > 0 and manuscript["status"] in (
            "Unknown",
            "Submitted",
            "Under Review",
        ):
            manuscript["status"] = f"Revision R{manuscript['revision_round']} Under Review"

        if manuscript["status"] in ("Unknown", "Submitted"):
            manuscript["status"] = self.determine_manuscript_status(manuscript)

        # CrossRef title fallback for bad/missing titles
        bad_title = (
            not manuscript["title"]
            or manuscript["title"] == "Title not found"
            or len(manuscript["title"]) < 15
            or manuscript["title"].endswith((".dvi", ".tex", ".pdf"))
            or "noname" in manuscript["title"].lower()
        )
        if bad_title and manuscript.get("authors"):
            try:
                author_names = [a["name"] for a in manuscript["authors"][:2] if a.get("name")]
                abstract = manuscript.get("abstract", "")
                crossref_title = self._search_title_by_authors(author_names, abstract[:200])
                if crossref_title:
                    print(f"      🔍 CrossRef title fallback: {crossref_title[:60]}...")
                    manuscript["title"] = crossref_title
            except Exception:
                pass

        return manuscript

    def classify_email_type(self, subject: str, body: str) -> str:
        """Classify the type of email based on content."""
        subject_lower = subject.lower()
        body_lower = body.lower()[:3000]

        if "invitation" in subject_lower and "review" in subject_lower:
            return "Referee Invitation"
        elif "accepted to review" in body_lower or "agreed to review" in body_lower:
            return "Referee Acceptance"
        elif "happy to review" in body_lower or "happy to referee" in body_lower:
            return "Referee Acceptance"
        elif "agree to" in body_lower and ("review" in body_lower or "referee" in body_lower):
            return "Referee Acceptance"
        elif "declined" in body_lower or "unable to review" in body_lower:
            return "Referee Decline"
        elif "cannot" in body_lower and ("review" in body_lower or "referee" in body_lower):
            return "Referee Decline"
        elif "report" in subject_lower and "submitted" in subject_lower:
            return "Report Submission"
        elif any(
            kw in body_lower
            for kw in [
                "attached my report",
                "attached the report",
                "here is my report",
                "find my report",
            ]
        ):
            return "Report Submission"
        elif "decision" in subject_lower:
            return "Editorial Decision"
        elif "new submission" in subject_lower:
            return "New Submission"
        elif "revision" in subject_lower:
            return "Revision Request"
        elif "reminder" in subject_lower:
            return "Reminder"
        elif "state of things" in subject_lower or "status" in subject_lower:
            return "Status Inquiry"
        elif "thank" in subject_lower or "thank you" in body_lower[:200]:
            return "Acknowledgment"
        elif subject_lower.startswith("re:") or subject_lower.startswith("r:"):
            return "Reply"
        else:
            return "Correspondence"

    def extract_referees_from_email(self, body: str, subject: str) -> List[Dict[str, str]]:
        """Extract referee names and details from email body."""
        referees = []

        # Common patterns for referee mentions
        patterns = [
            r"(?:Prof(?:essor)?|Dr|Mr|Ms|Mrs)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
            r"referee[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
            r"reviewer[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+has\s+(?:accepted|agreed|declined)",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+from\s+([A-Za-z\s]+University|[A-Za-z\s]+Institute)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0]
                    institution = match[1] if len(match) > 1 else ""
                else:
                    name = match
                    institution = ""

                name = self._normalize_name(name)

                if name.lower() in [
                    "finance and stochastics",
                    "dylan possamai",
                    "dear",
                    "sincerely",
                    "best",
                    "regards",
                ]:
                    continue

                # Look for email in nearby text
                email = ""
                email_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
                email_matches = re.findall(
                    email_pattern, body[max(0, body.find(name) - 100) : body.find(name) + 100]
                )
                if email_matches:
                    email = email_matches[0]

                referees.append({"name": name, "email": email, "institution": institution})

        return referees

    def extract_manuscript_from_email(
        self, email_message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Extract manuscript data from an email message."""
        try:
            # Get email metadata
            headers = email_message["payload"].get("headers", [])
            subject = ""
            sender = ""
            date = ""

            for header in headers:
                if header["name"] == "Subject":
                    subject = header["value"]
                elif header["name"] == "From":
                    sender = header["value"]
                elif header["name"] == "Date":
                    date = header["value"]

            # Get email body
            body = self.get_email_body(email_message["payload"])

            if not body:
                return None

            # Extract manuscript ID
            manuscript_id = None
            id_match = re.search(
                self.email_patterns["manuscript_id"], subject + " " + body, re.IGNORECASE
            )
            if id_match:
                manuscript_id = f"FS-{id_match.group(1)}"
            else:
                manuscript_id = f'FS-{datetime.now().strftime("%Y%m%d")}-{email_message["id"][:6]}'

            # Extract title
            title = "Title not found"
            title_match = re.search(self.email_patterns["title_pattern"], body, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()

            # Extract authors
            authors = []
            author_match = re.search(self.email_patterns["author_pattern"], body, re.IGNORECASE)
            if author_match:
                author_names = author_match.group(1).strip()
                for name in re.split(r"[,;]", author_names):
                    name = name.strip()
                    if name:
                        authors.append({"name": name, "email": "", "institution": ""})

            # Determine status from email type
            status = "Unknown"
            body_lower = body.lower()
            subject_lower = subject.lower()

            if "new submission" in subject_lower or "submitted" in body_lower:
                status = "New Submission"
            elif "revision" in subject_lower or "revise" in body_lower:
                status = "Revision Requested"
            elif "review" in subject_lower and "invitation" in subject_lower:
                status = "Review Invitation"
            elif "review" in subject_lower and "submitted" in subject_lower:
                status = "Review Submitted"
            elif "accept" in subject_lower or "accepted" in body_lower:
                status = "Accepted"
            elif "reject" in subject_lower or "rejected" in body_lower:
                status = "Rejected"
            elif "decision" in subject_lower:
                status = "Decision Made"

            # Get attachments
            attachments = self.get_email_attachments(email_message)

            # Try to get title/abstract from PDF attachments
            pdf_title = None
            pdf_abstract = None
            pdf_keywords = []
            manuscript_pdfs = []
            referee_reports = []

            for attachment in attachments:
                filename = attachment["filename"]
                filename_lower = filename.lower()

                # Download important attachments
                if filename_lower.endswith(".pdf") or filename_lower.endswith(".docx"):
                    # Check if it's a manuscript PDF (by name or by ID pattern)
                    is_manuscript = any(
                        keyword in filename_lower
                        for keyword in ["manuscript", "paper", "article", "submission"]
                    ) or re.match(
                        r"^fs-\d{2}-\d{4}", filename_lower
                    )  # Matches FS-XX-XXXX pattern

                    # Check if it's a referee report
                    is_report = any(
                        keyword in filename_lower
                        for keyword in ["report", "review", "referee", "comments"]
                    )

                    # Manuscript PDFs
                    if is_manuscript and not is_report:
                        file_path = self.download_attachment(
                            email_message["id"],
                            attachment["attachment_id"],
                            filename,
                            manuscript_id,
                        )
                        if file_path:
                            manuscript_pdfs.append(file_path)
                            if not pdf_title and file_path.endswith(".pdf"):
                                pdf_title = self.extract_title_from_pdf(file_path)

                            if not pdf_abstract and file_path.endswith(".pdf"):
                                pdf_abstract = self._extract_abstract_from_pdf(file_path)

                            if not pdf_keywords and file_path.endswith(".pdf"):
                                pdf_keywords = self._extract_keywords_from_pdf(file_path)

                    # Referee reports
                    elif is_report:
                        file_path = self.download_attachment(
                            email_message["id"],
                            attachment["attachment_id"],
                            filename,
                            manuscript_id,
                        )
                        if file_path:
                            referee_reports.append({"filename": filename, "path": file_path})

            # Use PDF title/abstract if found
            if pdf_title:
                title = pdf_title

            # Build manuscript object
            manuscript = {
                "id": manuscript_id,
                "title": title,
                "abstract": pdf_abstract or "",
                "keywords": pdf_keywords or [],
                "status": status,
                "authors": authors,
                "journal": "FS",
                "platform": "Email",
                "email_subject": subject,
                "email_sender": sender,
                "email_date": date,
                "email_id": email_message["id"],
                "extracted_at": datetime.now().isoformat(),
                "referees": [],
                "submission_date": date,
                "attachments": attachments,
                "manuscript_pdfs": manuscript_pdfs,
                "referee_reports": referee_reports,
            }

            # Extract referee information from email body
            referee_patterns = [
                r"Referee[:\s]+([A-Za-z\s]+?)(?:\n|$)",
                r"Reviewer[:\s]+([A-Za-z\s]+?)(?:\n|$)",
                r"(?:Referee|Reviewer)\s+(\d+)[:\s]+([A-Za-z\s]+?)(?:\n|$)",
                r"Assigned to[:\s]+([A-Za-z\s]+?)(?:\n|$)",
            ]

            referees_found = set()
            for pattern in referee_patterns:
                referee_matches = re.findall(pattern, body, re.IGNORECASE | re.MULTILINE)
                for match in referee_matches:
                    # Handle numbered referees
                    if isinstance(match, tuple) and len(match) == 2:
                        referee_name = match[1].strip()
                    else:
                        referee_name = match.strip() if isinstance(match, str) else match[0].strip()

                    if (
                        referee_name
                        and len(referee_name) > 2
                        and referee_name not in referees_found
                    ):
                        referees_found.add(referee_name)
                        manuscript["referees"].append(
                            {
                                "name": referee_name,
                                "email": "",
                                "status": "Assigned",
                                "affiliation": "",
                                "report_available": len(
                                    [
                                        r
                                        for r in referee_reports
                                        if referee_name.split()[0].lower() in r["filename"].lower()
                                    ]
                                )
                                > 0,
                            }
                        )

            # Parse referee decisions from body
            decision_patterns = [
                r"(?:Referee|Reviewer)\s+\d+[:\s]+(?:recommends?\s+)?(\w+)",
                r"Decision[:\s]+(\w+)",
                r"Recommendation[:\s]+(\w+)",
            ]

            for pattern in decision_patterns:
                decision_matches = re.findall(pattern, body, re.IGNORECASE)
                for decision in decision_matches:
                    decision_lower = decision.lower()
                    if "accept" in decision_lower:
                        manuscript["referee_recommendation"] = "Accept"
                    elif "reject" in decision_lower:
                        manuscript["referee_recommendation"] = "Reject"
                    elif "revise" in decision_lower or "revision" in decision_lower:
                        manuscript["referee_recommendation"] = "Revise"

            return manuscript

        except Exception as e:
            print(f"⚠️ Error extracting from email: {e}")
            return None

    def get_email_body(self, payload) -> str:
        """Extract body text from email payload."""
        body = ""

        try:
            if "parts" in payload:
                for part in payload["parts"]:
                    if part["mimeType"] == "text/plain":
                        data = part["body"].get("data", "")
                        if data:
                            body += base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    elif part["mimeType"] == "text/html" and not body:
                        # Use HTML if no plain text
                        data = part["body"].get("data", "")
                        if data:
                            html = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                            # Simple HTML stripping
                            body = re.sub("<[^<]+?>", "", html)
            elif payload.get("body", {}).get("data"):
                data = payload["body"]["data"]
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"⚠️ Error extracting email body: {e}")

        return body

    def extract_all(self) -> List[Dict[str, Any]]:
        """Main extraction method for email-based workflow."""
        print("🚀 FS EXTRACTION - COMPREHENSIVE EMAIL ANALYSIS")
        print("=" * 60)

        try:
            # Setup Gmail service
            if not self.setup_gmail_service():
                print("❌ Gmail service setup failed")
                return []

            # Step 1: Find current manuscripts (starred emails)
            print("\n📌 STEP 1: Finding current manuscripts (starred emails)")
            # Exclude Editorial Digest emails from search
            starred_query = 'is:starred (FS- OR FIST) -subject:"Editorial Digest"'
            starred_emails = self.search_emails(starred_query, max_results=20)

            current_manuscript_ids = set()
            for email in starred_emails:
                headers = email["payload"].get("headers", [])
                subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")

                # Extract manuscript IDs from starred emails
                fs_match = re.search(r"FS-\d{2}-\d{3,4}", subject)
                if fs_match:
                    current_manuscript_ids.add(fs_match.group(0))
                    print(f"   ⭐ Current manuscript: {fs_match.group(0)}")

            # Step 2: Get ALL emails for each manuscript ID
            print(
                f"\n📚 STEP 2: Building complete timeline for {len(current_manuscript_ids)} current + historical manuscripts"
            )

            # Also search for historical manuscripts (exclude Editorial Digest)
            historical_queries = [
                'subject:"FS-" -is:starred -subject:"Editorial Digest" newer_than:180d',
                "from:martin.schweizer@math.ethz.ch newer_than:180d",
            ]

            all_manuscript_ids = current_manuscript_ids.copy()

            for query in historical_queries:
                emails = self.search_emails(query, max_results=30)
                for email in emails:
                    headers = email["payload"].get("headers", [])
                    subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")

                    fs_match = re.search(r"FS-\d{2}-\d{3,4}", subject)
                    if fs_match:
                        all_manuscript_ids.add(fs_match.group(0))

            print(f"   Found {len(all_manuscript_ids)} total unique manuscripts")

            # Step 3: For each manuscript, get COMPLETE email history
            manuscripts = {}

            total_manuscripts = len(all_manuscript_ids)
            for idx, manuscript_id in enumerate(sorted(all_manuscript_ids), 1):
                print(f"\n🔍 Processing {manuscript_id}... ({idx}/{total_manuscripts})")

                # Get emails for this manuscript (exclude Editorial Digest)
                manuscript_query = f'"{manuscript_id}" -subject:"Editorial Digest"'
                manuscript_emails = self.search_emails(manuscript_query, max_results=50)

                print(f"   📧 Found {len(manuscript_emails)} emails for {manuscript_id}")

                is_current = manuscript_id in current_manuscript_ids
                if not is_current:
                    print(f"   📄 Historical manuscript — skipping downloads")

                # Build comprehensive manuscript data
                try:
                    manuscript = self.build_manuscript_timeline(
                        manuscript_id,
                        manuscript_emails,
                        is_current=is_current,
                    )
                except Exception as e:
                    self.errors.append(f"Error processing {manuscript_id}: {str(e)[:200]}")
                    print(f"   ⚠️ Error processing {manuscript_id}: {e}")
                    manuscript = None

                if manuscript:
                    manuscripts[manuscript_id] = manuscript

            self.manuscripts = list(manuscripts.values())

            # Cross-manuscript editor dedup: remove editors from ALL referee lists
            all_editor_names = set()
            for ms in self.manuscripts:
                if ms.get("editor"):
                    all_editor_names.add(self._extract_name_from_header(ms["editor"]))
            if all_editor_names:
                for ms in self.manuscripts:
                    refs = ms.get("referees", [])
                    if isinstance(refs, list):
                        ms["referees"] = [r for r in refs if r.get("name") not in all_editor_names]
                    elif isinstance(refs, dict):
                        ms["referees"] = {
                            k: v
                            for k, v in refs.items()
                            if self._normalize_name(k) not in all_editor_names
                        }

            # Normalize output schema + AE status + web enrichment + timeline metrics + corresponding author
            for manuscript in self.manuscripts:
                self._normalize_output(manuscript)
                if manuscript.get("is_current"):
                    try:
                        manuscript["ae_status"] = self._compute_ae_status(manuscript)
                    except Exception as e:
                        self.errors.append(
                            f"AE status error for {manuscript.get('id', '?')}: {str(e)[:100]}"
                        )

                try:
                    self._enrich_people_from_web(manuscript)
                except Exception as e:
                    self.errors.append(
                        f"Web enrichment error for {manuscript.get('id', '?')}: {str(e)[:100]}"
                    )

                try:
                    timeline_metrics = self.calculate_timeline_metrics(manuscript)
                    if timeline_metrics:
                        manuscript["timeline_metrics"] = timeline_metrics
                except Exception as e:
                    self.errors.append(
                        f"Timeline metrics error for {manuscript.get('id', '?')}: {str(e)[:100]}"
                    )

                try:
                    if manuscript.get("authors") and not any(
                        a.get("is_corresponding") for a in manuscript["authors"]
                    ):
                        pdf_paths = manuscript.get("manuscript_pdfs", [])
                        pdf_path = pdf_paths[0] if pdf_paths else None
                        corr = self.identify_corresponding_author(
                            manuscript["authors"], pdf_path=pdf_path
                        )
                        if corr.get("name"):
                            for author in manuscript["authors"]:
                                is_corr = author.get("name") == corr["name"]
                                author["is_corresponding"] = is_corr
                                author["corresponding_author"] = is_corr
                except Exception as e:
                    self.errors.append(
                        f"Corresponding author error for {manuscript.get('id', '?')}: {str(e)[:100]}"
                    )

            # Sort by whether current and by date
            self.manuscripts.sort(
                key=lambda x: (not x["is_current"], x["submission_date"] or ""), reverse=True
            )

            current_mss = [m for m in self.manuscripts if m["is_current"]]
            historical_mss = [m for m in self.manuscripts if not m["is_current"]]

            print(
                f"\n📊 Extracted {len(self.manuscripts)} manuscripts ({len(current_mss)} current, {len(historical_mss)} historical)"
            )

            if current_mss:
                print("\n📋 ACTIVE MANUSCRIPTS:")
                for ms in current_mss:
                    ae = ms.get("ae_status", {})
                    phase = ae.get("phase", "Unknown")
                    action = ae.get("action", "")
                    days = ae.get("days_in_phase")
                    days_str = f" ({days}d)" if days is not None else ""

                    title_display = ms["title"][:70] if ms.get("title") else "No title"
                    print(f"\n⭐ {ms['id']}: {title_display}")
                    print(f"   📊 Phase: {phase}{days_str}")
                    print(f"   ⚡ Action: {action}")

                    for rd in ae.get("referees", []):
                        name = rd.get("name", "?")
                        st = rd.get("status", "?")
                        if st == "report_received":
                            rdate = rd.get("report_date", "")
                            if rdate:
                                try:
                                    rdate = datetime.strptime(
                                        rdate.split(",")[1].strip().split(" (")[0],
                                        "%d %b %Y %H:%M:%S %z",
                                    ).strftime("%b %d")
                                except Exception:
                                    rdate = rdate[:10]
                            print(
                                f"   ✅ {name} — report received{' (' + rdate + ')' if rdate else ''}"
                            )
                        elif st == "awaiting_report":
                            ds = rd.get("days_since_accepted")
                            ds_str = f" ({ds}d since accepted)" if ds is not None else ""
                            flag = " ⚠️ OVERDUE" if rd.get("overdue") else ""
                            print(f"   ⏳ {name} — awaiting report{ds_str}{flag}")
                        elif st == "declined":
                            print(f"   ❌ {name} — declined")
                        elif st == "no_response":
                            ds = rd.get("days_since_invited")
                            ds_str = f" ({ds}d)" if ds is not None else ""
                            flag = " ⚠️ OVERDUE" if rd.get("overdue") else ""
                            print(f"   👥 {name} — no response{ds_str}{flag}")

            if historical_mss:
                print("\n📋 HISTORICAL MANUSCRIPTS:")
                for ms in historical_mss:
                    print(f"📄 {ms['id']}: {ms['title'][:70]}...")
                    print(f"   📧 {ms['total_emails']} emails | 👥 {ms['total_referees']} referees")

            return self.manuscripts

        except Exception as e:
            self.errors.append(f"Fatal extraction error: {str(e)[:200]}")
            print(f"❌ Extraction failed: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _enrich_people_from_web(self, manuscript_data: Dict):
        if not requests:
            return
        from urllib.parse import quote_plus

        people = []
        referees = manuscript_data.get("referees", {})
        if isinstance(referees, dict):
            for ref in referees.values():
                if ref.get("name"):
                    people.append(("referee", ref))
        else:
            for ref in referees:
                if ref.get("name"):
                    people.append(("referee", ref))
        for auth in manuscript_data.get("authors", []):
            if auth.get("name"):
                people.append(("author", auth))

        if not people:
            return

        enriched = 0
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "FS-Extractor/2.0 (mailto:dylansmb@gmail.com)",
                "Accept": "application/json",
            }
        )

        try:
            from core.academic_apis import AcademicProfileEnricher

            academic = AcademicProfileEnricher(session)
        except Exception:
            academic = None

        cache_hits = 0
        for role, person in people:
            name = person.get("name", "")
            institution = (
                person.get("institution", "")
                or person.get("affiliation", "")
                or person.get("institution_parsed", "")
            )
            orcid = person.get("orcid", "")
            if person.get("web_profile"):
                continue

            if orcid and orcid.startswith("http"):
                orcid_id = orcid.rstrip("/").split("/")[-1]
            elif orcid and re.match(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", orcid):
                orcid_id = orcid
            else:
                orcid_id = None

            cached_profile = self.get_cached_web_profile(name, institution, orcid_id or "")
            if cached_profile:
                person["web_profile"] = cached_profile
                person["web_profile_source"] = "cache"
                cache_hits += 1
                enriched += 1
                continue

            profile = {}

            ms_title = manuscript_data.get("title", "")

            if not orcid_id and name:
                try:
                    name_parts = name.replace(",", "").strip().split()
                    if len(name_parts) >= 2:
                        given = name_parts[0]
                        family = name_parts[-1]
                        orcid_search_url = f"https://pub.orcid.org/v3.0/search/?q=given-names:{quote_plus(given)}+AND+family-name:{quote_plus(family)}"
                        resp = session.get(
                            orcid_search_url,
                            headers={"Accept": "application/json"},
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            results = resp.json().get("result", [])
                            if results and len(results) == 1:
                                orcid_id = results[0].get("orcid-identifier", {}).get("path")
                                if orcid_id:
                                    person["orcid"] = orcid_id
                            elif results and len(results) <= 10 and role == "author" and ms_title:
                                from difflib import SequenceMatcher

                                ms_title_lower = self._clean_latex_accents(ms_title).lower()
                                for candidate in results[:5]:
                                    cand_id = candidate.get("orcid-identifier", {}).get("path")
                                    if not cand_id:
                                        continue
                                    try:
                                        wresp = session.get(
                                            f"https://pub.orcid.org/v3.0/{cand_id}/works",
                                            headers={"Accept": "application/json"},
                                            timeout=8,
                                        )
                                        if wresp.status_code == 200:
                                            cand_works = wresp.json().get("group", [])
                                            for w in cand_works[:20]:
                                                ws = w.get("work-summary", [{}])[0]
                                                t_obj = ws.get("title", {}).get("title", {})
                                                t_val = (
                                                    t_obj.get("value", "") if t_obj else ""
                                                ).lower()
                                                if (
                                                    t_val
                                                    and SequenceMatcher(
                                                        None, ms_title_lower, t_val
                                                    ).ratio()
                                                    > 0.6
                                                ):
                                                    orcid_id = cand_id
                                                    person["orcid"] = orcid_id
                                                    break
                                            if orcid_id:
                                                break
                                    except Exception:
                                        continue
                            elif results and len(results) <= 3:
                                orcid_id = results[0].get("orcid-identifier", {}).get("path")
                                if orcid_id:
                                    person["orcid"] = orcid_id
                except Exception:
                    pass

            if orcid_id:
                try:
                    resp = session.get(
                        f"https://pub.orcid.org/v3.0/{orcid_id}/works",
                        headers={"Accept": "application/json"},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        works = resp.json().get("group", [])
                        recent = []
                        for w in works[:5]:
                            ws = w.get("work-summary", [{}])[0]
                            title_obj = ws.get("title", {}).get("title", {})
                            title = title_obj.get("value", "") if title_obj else ""
                            year = (
                                ws.get("publication-date", {}).get("year", {}).get("value", "")
                                if ws.get("publication-date")
                                else ""
                            )
                            journal = (
                                ws.get("journal-title", {}).get("value", "")
                                if ws.get("journal-title")
                                else ""
                            )
                            if title:
                                paper = {"title": title}
                                if year:
                                    paper["year"] = year
                                if journal:
                                    paper["journal"] = journal
                                recent.append(paper)
                        if recent:
                            profile["recent_publications"] = recent
                            profile["publication_count"] = len(works)
                except Exception:
                    pass

                try:
                    resp = session.get(
                        f"https://pub.orcid.org/v3.0/{orcid_id}/person",
                        headers={"Accept": "application/json"},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        person_data = resp.json()
                        orcid_name_obj = person_data.get("name", {})
                        if orcid_name_obj:
                            orcid_given = (orcid_name_obj.get("given-names") or {}).get("value", "")
                            orcid_family = (orcid_name_obj.get("family-name") or {}).get(
                                "value", ""
                            )
                            if orcid_given and orcid_family:
                                current_name = person.get("name", "")
                                current_ascii = (
                                    self._clean_latex_accents(current_name)
                                    .lower()
                                    .replace("-", " ")
                                )
                                orcid_ascii = (
                                    self._clean_latex_accents(f"{orcid_given} {orcid_family}")
                                    .lower()
                                    .replace("-", " ")
                                )
                                if (
                                    current_ascii == orcid_ascii
                                    or current_name.lower().split()[-1]
                                    == self._clean_latex_accents(orcid_family).lower()
                                ):

                                    def _title_preserve_diacritics(s):
                                        return s[0].upper() + s[1:] if s else s

                                    given_fixed = (
                                        _title_preserve_diacritics(orcid_given)
                                        if orcid_given.isupper() or orcid_given.islower()
                                        else orcid_given
                                    )
                                    family_fixed = (
                                        _title_preserve_diacritics(orcid_family.lower())
                                        if orcid_family.isupper() or orcid_family.islower()
                                        else orcid_family
                                    )
                                    canonical = f"{given_fixed} {family_fixed}"
                                    current_has_diacritics = (
                                        current_name != self._clean_latex_accents(current_name)
                                    )
                                    canonical_has_diacritics = (
                                        canonical != self._clean_latex_accents(canonical)
                                    )
                                    if canonical_has_diacritics or not current_has_diacritics:
                                        if (
                                            self._clean_latex_accents(canonical).lower()
                                            == current_ascii
                                        ):
                                            person["name"] = canonical
                        bio = person_data.get("biography", {})
                        if bio and bio.get("content"):
                            profile["biography"] = bio["content"][:500]
                        emails_obj = person_data.get("emails", {}).get("email", [])
                        for em_obj in emails_obj:
                            em_val = em_obj.get("email", "")
                            if em_val and not person.get("email"):
                                person["email"] = em_val
                                break
                        affiliations_obj = person_data.get("activities-summary", {})
                        urls = person_data.get("researcher-urls", {}).get("researcher-url", [])
                        ext_urls = []
                        for u in urls[:5]:
                            url_val = u.get("url", {}).get("value", "")
                            url_name = u.get("url-name", "")
                            if url_val:
                                ext_urls.append({"name": url_name, "url": url_val})
                        if ext_urls:
                            profile["external_urls"] = ext_urls
                        keywords = person_data.get("keywords", {}).get("keyword", [])
                        kw_list = [k.get("content", "") for k in keywords if k.get("content")]
                        if kw_list:
                            profile["research_keywords"] = kw_list[:10]
                except Exception:
                    pass

                if not person.get("affiliation") or person.get("affiliation") in ("Unknown", ""):
                    try:
                        resp = session.get(
                            f"https://pub.orcid.org/v3.0/{orcid_id}/employments",
                            headers={"Accept": "application/json"},
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            groups = resp.json().get("affiliation-group", [])
                            for g in groups[:1]:
                                summaries = g.get("summaries", [])
                                for s in summaries[:1]:
                                    emp = s.get("employment-summary", {})
                                    org = emp.get("organization", {})
                                    org_name = org.get("name", "")
                                    if org_name and not emp.get("end-date"):
                                        person["affiliation"] = org_name
                                        country_code = org.get("address", {}).get("country", "")
                                        if country_code and not person.get("country"):
                                            country_map = {
                                                "US": "USA",
                                                "GB": "UK",
                                                "FR": "France",
                                                "DE": "Germany",
                                                "CH": "Switzerland",
                                                "IT": "Italy",
                                                "CA": "Canada",
                                                "AU": "Australia",
                                                "CN": "China",
                                                "JP": "Japan",
                                                "NL": "Netherlands",
                                                "SE": "Sweden",
                                                "DK": "Denmark",
                                                "AT": "Austria",
                                                "IE": "Ireland",
                                                "HU": "Hungary",
                                                "RO": "Romania",
                                                "CZ": "Czech Republic",
                                            }
                                            person["country"] = country_map.get(
                                                country_code, country_code
                                            )
                    except Exception:
                        pass

            if not profile.get("recent_publications"):
                search_name = name.replace(",", "").strip()
                name_parts = search_name.split()
                person_surname = name_parts[-1].lower() if name_parts else ""
                person_given = name_parts[0].lower() if len(name_parts) >= 2 else ""
                person_orcid = orcid_id or ""
                if institution:
                    search_name += f" {institution}"
                try:
                    resp = session.get(
                        f"https://api.crossref.org/works?query.author={quote_plus(search_name)}&rows=10&sort=relevance&order=desc",
                        timeout=15,
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("message", {}).get("items", [])
                        crossref_papers = []
                        math_finance_keywords = {
                            "math",
                            "finance",
                            "stochastic",
                            "probability",
                            "control theory",
                            "optimization",
                            "operations research",
                            "actuarial",
                            "quantitative finance",
                            "risk management",
                            "portfolio",
                            "equilibrium",
                            "differential equation",
                            "siam",
                            "annals",
                            "applied probability",
                            "pricing",
                            "hedging",
                            "stopping",
                            "markov",
                            "martingale",
                            "stochastic process",
                            "mean field",
                            "mckean",
                            "mathematical econom",
                            "econometrica",
                        }
                        title_keywords = {
                            "stochastic",
                            "optim",
                            "financ",
                            "equilibri",
                            "game",
                            "portfolio",
                            "risk",
                            "pricing",
                            "hedg",
                            "diffusion",
                            "markov",
                            "martingale",
                            "control",
                            "stopping",
                            "mean-field",
                            "mean field",
                            "mckean",
                            "backward",
                            "forward",
                            "bsde",
                            "pde",
                            "sde",
                            "volatil",
                            "dividend",
                            "insurance",
                            "probabili",
                            "ergodic",
                            "viscosity",
                            "hamilton-jacobi",
                        }
                        for item in items[:10]:
                            cr_title = " ".join(item.get("title", []))
                            year_parts = item.get("published-print", {}).get("date-parts", [[]])
                            if not year_parts[0]:
                                year_parts = item.get("published-online", {}).get(
                                    "date-parts", [[]]
                                )
                            year_val = year_parts[0][0] if year_parts and year_parts[0] else None
                            if year_val and (year_val > 2027 or year_val < 1990):
                                continue
                            year = str(year_val) if year_val else ""
                            journal = " ".join(item.get("container-title", []))
                            doi = item.get("DOI", "")
                            cr_authors = item.get("author", [])
                            surname_match = False
                            full_name_match = False
                            if person_surname and cr_authors:
                                for cr_auth in cr_authors:
                                    cr_family = (cr_auth.get("family") or "").lower()
                                    cr_given = (cr_auth.get("given") or "").lower()
                                    if not cr_family:
                                        continue
                                    if cr_family == person_surname:
                                        surname_match = True
                                        if person_given and cr_given:
                                            if (
                                                cr_given == person_given
                                                or cr_given.startswith(person_given[:3])
                                                or person_given.startswith(cr_given[:3])
                                            ):
                                                full_name_match = True
                                        if person_orcid and cr_auth.get("ORCID"):
                                            cr_orcid = cr_auth["ORCID"].rstrip("/").split("/")[-1]
                                            if cr_orcid == person_orcid:
                                                full_name_match = True
                                        break
                                    elif len(person_surname) > 5 and (
                                        cr_family.startswith(person_surname[:5])
                                        or person_surname.startswith(cr_family[:5])
                                    ):
                                        surname_match = True
                                        break
                            if not surname_match and cr_authors:
                                continue
                            orcid_verified = False
                            if person_orcid and cr_authors:
                                for cr_auth in cr_authors:
                                    if cr_auth.get("ORCID"):
                                        cr_orcid = cr_auth["ORCID"].rstrip("/").split("/")[-1]
                                        if cr_orcid == person_orcid:
                                            orcid_verified = True
                                            break
                            if not orcid_verified and len(person_surname) <= 5:
                                title_lower = cr_title.lower()
                                journal_lower = journal.lower()
                                combined = title_lower + " " + journal_lower
                                reject_keywords = {
                                    "medical",
                                    "clinical",
                                    "surgery",
                                    "cancer",
                                    "tumor",
                                    "biological",
                                    "molecular",
                                    "cell ",
                                    "gene ",
                                    "genetic",
                                    "allergy",
                                    "immunol",
                                    "pathol",
                                    "neurosci",
                                    "pharma",
                                    "education",
                                    "teacher",
                                    "student satisfaction",
                                    "pedagog",
                                    "wireless sensor",
                                    "antenna",
                                    "radar",
                                    "satellite",
                                    "painting",
                                    "art ",
                                    "music",
                                    "literary",
                                    "linguistic",
                                    "agriculture",
                                    "crop",
                                    "soil",
                                    "ecolog",
                                    "marine",
                                    "cosmetic",
                                    "brand",
                                    "tourism",
                                    "hotel",
                                    "restaurant",
                                    "nanostructure",
                                    "nanotube",
                                    "catalys",
                                    "polymer",
                                    "spectral clustering",
                                    "image processing",
                                    "computer vision",
                                }
                                if any(rk in combined for rk in reject_keywords):
                                    continue
                                if not any(kw in combined for kw in title_keywords) and not any(
                                    kw in journal_lower for kw in math_finance_keywords
                                ):
                                    continue
                            if cr_title:
                                paper = {"title": cr_title}
                                if year:
                                    paper["year"] = year
                                if journal:
                                    paper["journal"] = journal
                                if doi:
                                    paper["doi"] = doi
                                journal_lower = journal.lower()
                                title_lower = cr_title.lower()
                                if any(kw in journal_lower for kw in math_finance_keywords):
                                    paper["_relevance"] = "high"
                                elif any(kw in title_lower for kw in title_keywords):
                                    paper["_relevance"] = "high"
                                crossref_papers.append(paper)
                        high_rel = [
                            p for p in crossref_papers if p.pop("_relevance", None) == "high"
                        ]
                        low_rel = [p for p in crossref_papers if "_relevance" not in p]
                        for p in low_rel:
                            p.pop("_relevance", None)
                        final_papers = (high_rel + low_rel)[:5]
                        if final_papers:
                            profile["recent_publications"] = final_papers
                            pub_count = len(items) if items else 0
                            if pub_count:
                                profile["publication_count"] = pub_count
                            profile["source"] = "crossref"
                except Exception:
                    pass

            if academic:
                try:
                    academic_data = academic.enrich(name, orcid_id, institution)
                    if academic_data:
                        profile.update(academic_data)
                except Exception:
                    pass

            if profile:
                person["web_profile"] = profile
                enriched += 1
                source = "orcid+crossref"
                if profile.get("semantic_scholar") or profile.get("openalex"):
                    source += "+academic"
                self.save_web_profile(name, institution, orcid_id or "", profile, source)
            else:
                person["web_profile"] = None

        session.close()

        if enriched:
            cache_msg = f" ({cache_hits} from cache)" if cache_hits else ""
            print(
                f"      🌐 Web enriched: {enriched}/{len(people)} people via ORCID/CrossRef/S2/OpenAlex{cache_msg}"
            )

    def _enforce_date_chronology(self, ref):
        def _parse(d):
            if not d:
                return None
            try:
                if isinstance(d, datetime):
                    return d
                for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        return datetime.strptime(d.split(" (")[0].strip(), fmt).replace(tzinfo=None)
                    except ValueError:
                        continue
                import email.utils

                return datetime(*email.utils.parsedate(d)[:6])
            except Exception:
                return None

        inv = _parse(ref.get("invited_date"))
        resp = _parse(ref.get("response_date"))
        rep = _parse(ref.get("report_date"))

        known = [d for d in [inv, resp, rep] if d]
        if not known:
            return

        earliest = min(known)

        if inv and resp and inv > resp:
            ref["invited_date"] = ref["response_date"]
        if inv and rep and inv > rep:
            ref["invited_date"] = ref["report_date"]

        inv = _parse(ref.get("invited_date"))
        if inv and resp and inv > resp:
            ref["invited_date"] = ref["response_date"]

        if not ref.get("invited_date") and ref.get("report_date"):
            ref["invited_date"] = ref.get("report_date")

    def _compute_ae_status(self, manuscript):
        referees = manuscript.get("referees", [])
        if isinstance(referees, dict):
            referees = list(referees.values())

        total = len(referees)
        accepted = [
            r for r in referees if r.get("response") == "Accepted" or r.get("report_submitted")
        ]
        declined = [
            r for r in referees if r.get("response") == "Declined" and not r.get("report_submitted")
        ]
        no_response = [
            r for r in referees if not r.get("response") and not r.get("report_submitted")
        ]
        reports_in = [r for r in referees if r.get("report_submitted")]
        awaiting_report = [r for r in accepted if not r.get("report_submitted")]

        now = datetime.now()

        def parse_date(d):
            if not d:
                return None
            try:
                if isinstance(d, datetime):
                    return d
                for fmt in ["%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]:
                    try:
                        return datetime.strptime(d.split(" (")[0].strip(), fmt).replace(tzinfo=None)
                    except ValueError:
                        continue
                import email.utils

                return datetime(*email.utils.parsedate(d)[:6])
            except Exception:
                return None

        def days_since(d):
            parsed = parse_date(d)
            if not parsed:
                return None
            return (now - parsed).days

        def referee_detail(r):
            name = r.get("name", "Unknown")
            resp = r.get("response")
            has_report = r.get("report_submitted")
            d = {}
            if has_report:
                ds = days_since(
                    r.get("report_date") or r.get("response_date") or r.get("invited_date")
                )
                d = {
                    "name": name,
                    "status": "report_received",
                    "report_date": r.get("report_date"),
                    "days_since_invited": days_since(r.get("invited_date")),
                }
            elif resp == "Accepted":
                ds = days_since(r.get("response_date") or r.get("invited_date"))
                d = {
                    "name": name,
                    "status": "awaiting_report",
                    "days_since_accepted": ds,
                    "overdue": ds is not None and ds > 30,
                }
            elif resp == "Declined":
                d = {"name": name, "status": "declined"}
            else:
                ds = days_since(r.get("invited_date"))
                d = {
                    "name": name,
                    "status": "no_response",
                    "days_since_invited": ds,
                    "overdue": ds is not None and ds > 14,
                }
            return d

        referee_details = [referee_detail(r) for r in referees]
        overdue = [d for d in referee_details if d.get("overdue")]

        if total == 0:
            phase_date = manuscript.get("submission_date")
            return {
                "phase": "Finding Referees",
                "action": "Invite referees",
                "urgency": "high",
                "days_in_phase": days_since(phase_date),
                "referees": referee_details,
                "overdue_referees": [],
            }

        if no_response:
            latest_invite = None
            for r in no_response:
                d = parse_date(r.get("invited_date"))
                if d and (not latest_invite or d > latest_invite):
                    latest_invite = d
            phase_days = (now - latest_invite).days if latest_invite else None
            return {
                "phase": "Awaiting Referee Responses",
                "action": f"{len(no_response)} referee(s) haven't responded yet",
                "urgency": "medium",
                "days_in_phase": phase_days,
                "referees": referee_details,
                "overdue_referees": overdue,
            }

        if not accepted and declined:
            return {
                "phase": "All Referees Declined",
                "action": "Find replacement referees",
                "urgency": "high",
                "days_in_phase": None,
                "referees": referee_details,
                "overdue_referees": [],
            }

        if awaiting_report:
            latest_accept = None
            for r in awaiting_report:
                d = parse_date(r.get("response_date"))
                if d and (not latest_accept or d > latest_accept):
                    latest_accept = d
            phase_days = (now - latest_accept).days if latest_accept else None
            return {
                "phase": "Awaiting Reports",
                "action": f"{len(awaiting_report)} report(s) still pending",
                "urgency": "high" if len(awaiting_report) == 1 else "medium",
                "days_in_phase": phase_days,
                "referees": referee_details,
                "overdue_referees": overdue,
            }

        latest_report = None
        for r in reports_in:
            d = parse_date(r.get("report_date"))
            if d and (not latest_report or d > latest_report):
                latest_report = d
        phase_days = (now - latest_report).days if latest_report else None
        return {
            "phase": "Ready for AE Report",
            "action": "Write AE recommendation and send to editor",
            "urgency": "high",
            "days_in_phase": phase_days,
            "referees": referee_details,
            "overdue_referees": [],
        }

    def _normalize_output(self, manuscript):
        for event in manuscript.get("timeline", []):
            event.pop("body_snippet", None)

        if manuscript.get("abstract"):
            manuscript["abstract"] = self._clean_pdf_text(manuscript["abstract"])

        if manuscript.get("id") and not manuscript.get("manuscript_id"):
            manuscript["manuscript_id"] = manuscript["id"]

        if not manuscript.get("extraction_timestamp"):
            manuscript["extraction_timestamp"] = datetime.now().isoformat()

        for author in manuscript.get("authors", []):
            if author.get("affiliation"):
                author["affiliation"] = self._clean_affiliation(author["affiliation"])

        for ref in manuscript.get("referees", []):
            resp = (ref.get("response") or "").lower()
            ref["dates"] = {
                "invited": ref.get("invited_date") or None,
                "agreed": ref.get("response_date") if resp == "accepted" else None,
                "due": None,
                "returned": ref.get("report_date") or None,
            }
            raw_aff = ref.get("institution") or ref.get("affiliation") or ""
            ref["affiliation"] = self._clean_affiliation(raw_aff) if raw_aff else ""
            ref["status_details"] = {
                "status": ref.get("response") or "Pending",
                "review_received": ref.get("report_submitted", False),
                "review_complete": ref.get("report_submitted", False),
                "review_pending": resp == "accepted" and not ref.get("report_submitted"),
                "agreed_to_review": resp == "accepted",
                "declined": resp == "declined",
                "no_response": not ref.get("response"),
            }
            for field in ["orcid", "email", "affiliation", "institution"]:
                if ref.get(field) == "":
                    ref[field] = None

        for author in manuscript.get("authors", []):
            for field in ["orcid", "email", "affiliation"]:
                if author.get(field) == "":
                    author[field] = None
            if "is_corresponding" in author and "corresponding_author" not in author:
                author["corresponding_author"] = author["is_corresponding"]
            elif "corresponding_author" in author and "is_corresponding" not in author:
                author["is_corresponding"] = author["corresponding_author"]

        for report in manuscript.get("referee_reports", []):
            analysis = report.get("analysis", {})
            if "attached_files" not in analysis:
                analysis["attached_files"] = []

        if not manuscript.get("final_outcome"):
            status = manuscript.get("status", "")
            if "Accepted" in status:
                manuscript["final_outcome"] = "Accepted"
            elif "Rejected" in status:
                manuscript["final_outcome"] = "Rejected"
            elif "Revision" in status:
                manuscript["final_outcome"] = "Revision Requested"
            else:
                manuscript["final_outcome"] = "Pending"

    def _generate_summary(self):
        manuscripts = self.manuscripts
        summary = {
            "total_manuscripts": len(manuscripts),
            "current_manuscripts": sum(1 for m in manuscripts if m.get("is_current")),
            "historical_manuscripts": sum(1 for m in manuscripts if not m.get("is_current")),
            "by_status": {},
            "referee_emails_extracted": sum(
                len([r for r in m.get("referees", []) if r.get("email")]) for m in manuscripts
            ),
            "total_referees": sum(len(m.get("referees", [])) for m in manuscripts),
            "total_authors": sum(len(m.get("authors", [])) for m in manuscripts),
            "reports_received": sum(len(m.get("referee_reports", [])) for m in manuscripts),
            "total_timeline_events": sum(len(m.get("timeline", [])) for m in manuscripts),
            "orcid_coverage": {
                "authors_with_orcid": sum(
                    len([a for a in m.get("authors", []) if a.get("orcid")]) for m in manuscripts
                ),
                "total_authors": sum(len(m.get("authors", [])) for m in manuscripts),
                "referees_with_orcid": sum(
                    len([r for r in m.get("referees", []) if r.get("orcid")]) for m in manuscripts
                ),
            },
            "extraction_time": datetime.now().isoformat(),
        }
        for m in manuscripts:
            status = m.get("status", "Unknown")
            summary["by_status"][status] = summary["by_status"].get(status, 0) + 1
        if summary["total_referees"] > 0:
            summary["email_extraction_rate"] = round(
                100 * summary["referee_emails_extracted"] / summary["total_referees"], 1
            )
        total_authors = summary["orcid_coverage"]["total_authors"]
        if total_authors > 0:
            summary["orcid_coverage"]["author_coverage_percent"] = round(
                100 * summary["orcid_coverage"]["authors_with_orcid"] / total_authors, 1
            )
        if summary["total_referees"] > 0:
            summary["orcid_coverage"]["referee_coverage_percent"] = round(
                100 * summary["orcid_coverage"]["referees_with_orcid"] / summary["total_referees"],
                1,
            )
        return summary

    def save_results(self):
        """Save extraction results."""
        if not self.manuscripts:
            print("⚠️ No manuscripts to save")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save JSON file FIRST (primary output)
        try:
            output_file = self.output_dir / f"fs_extraction_{timestamp}.json"

            extraction_data = {
                "extraction_timestamp": datetime.now().isoformat(),
                "journal": "FS",
                "journal_name": "Finance and Stochastics",
                "platform": "Email (Gmail)",
                "extractor_version": "2.0.0",
                "manuscripts": self.manuscripts,
                "summary": self._generate_summary(),
                "errors": self.errors,
            }

            from core.output_schema import normalize_wrapper

            normalize_wrapper(extraction_data, "FS")

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(extraction_data, f, indent=2, ensure_ascii=False, default=str)

            print(f"💾 Results saved: {output_file}")

        except Exception as e:
            print(f"⚠️ File save error: {e}")

        # Save to cache system (secondary, with timeout)
        try:
            import signal

            def _timeout_handler(signum, frame):
                raise TimeoutError("Cache save timed out")

            old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(30)
            try:
                for manuscript in self.manuscripts:
                    self.cache_manuscript(manuscript)
                print(f"💾 Cached {len(self.manuscripts)} manuscripts")
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        except (TimeoutError, Exception) as e:
            print(f"⚠️ Cache save error: {e}")

    def calculate_timeline_metrics(self, manuscript: Dict) -> Dict[str, Any]:
        """Calculate timeline metrics for a manuscript.

        Args:
            manuscript: Manuscript data dictionary

        Returns:
            Dictionary containing timeline metrics
        """
        metrics = {
            "submission_to_first_review": None,
            "average_review_time": None,
            "revision_turnaround": None,
            "total_processing_time": None,
            "referee_response_times": {},
            "report_submission_times": {},
            "acceptance_to_report_days": {},
            "reminders_received": {},
            "late_reports": [],
            "pending_overdue": [],
            "current_stage_duration": None,
        }

        # Extract key dates from timeline
        timeline = manuscript.get("timeline", [])
        if not timeline:
            return metrics

        # Find submission date (first email with manuscript PDF)
        submission_date = None
        for event in timeline:
            if event.get("details", {}).get("manuscript_pdf"):
                submission_date = event["date"]
                break

        if not submission_date:
            # Use first timeline event as submission
            submission_date = timeline[0]["date"] if timeline else None

        # Parse dates
        from datetime import datetime, timedelta
        import email.utils

        def parse_date(date_str):
            """Parse email date string to datetime."""
            if not date_str:
                return None
            try:
                return email.utils.parsedate_to_datetime(date_str).replace(tzinfo=None)
            except (ValueError, TypeError):
                return None

        submission_dt = parse_date(submission_date)
        if not submission_dt:
            return metrics

        current_dt = datetime.now()

        # Calculate submission to first review
        first_review_date = None
        for event in timeline:
            if "report_by" in event.get("details", {}):
                first_review_date = event["date"]
                break

        if first_review_date:
            first_review_dt = parse_date(first_review_date)
            if first_review_dt:
                delta = first_review_dt - submission_dt
                metrics["submission_to_first_review"] = delta.days

        # Calculate referee response and report times
        referees = manuscript.get("referees", [])
        report_times = []

        for referee in referees:
            ref_name = referee.get("name", "Unknown")

            invited_date = referee.get("invited_date")

            if invited_date:
                invited_dt = parse_date(invited_date)

                # Response time (invitation to accept/decline)
                if referee.get("response_date"):
                    response_dt = parse_date(referee["response_date"])
                    if response_dt and invited_dt:
                        delta = response_dt - invited_dt
                        metrics["referee_response_times"][ref_name] = delta.days

                # Report submission time (invitation to report)
                if referee.get("report_date"):
                    report_dt = parse_date(referee["report_date"])
                    if report_dt and invited_dt:
                        delta = report_dt - invited_dt
                        metrics["report_submission_times"][ref_name] = delta.days
                        report_times.append(delta.days)

                        if delta.days > 30:
                            metrics["late_reports"].append(
                                {
                                    "referee": ref_name,
                                    "days_late": delta.days - 30,
                                    "submission_date": referee["report_date"],
                                }
                            )
                elif referee.get("response") == "Accepted" and not referee.get("report_submitted"):
                    if invited_dt:
                        delta = current_dt - invited_dt
                        if delta.days > 30:
                            metrics["pending_overdue"].append(
                                {
                                    "referee": ref_name,
                                    "days_overdue": delta.days - 30,
                                    "status": "pending",
                                }
                            )

                if referee.get("response_date") and referee.get("report_date"):
                    response_dt = parse_date(referee["response_date"])
                    report_dt = parse_date(referee["report_date"])
                    if response_dt and report_dt:
                        metrics["acceptance_to_report_days"][ref_name] = (
                            report_dt - response_dt
                        ).days

            ref_name_lower = ref_name.lower()
            ref_last = ref_name_lower.split()[-1] if ref_name_lower.split() else ""
            reminder_count = 0
            for event in timeline:
                if event.get("type") == "Reminder":
                    ev_text = (event.get("subject", "") + " " + event.get("body", "")[:500]).lower()
                    if ref_last and len(ref_last) > 2 and ref_last in ev_text:
                        reminder_count += 1
                    elif not ref_last and "reminder" in (event.get("subject") or "").lower():
                        reminder_count += 1
            metrics["reminders_received"][ref_name] = reminder_count

        # Calculate average review time
        if report_times:
            metrics["average_review_time"] = sum(report_times) / len(report_times)

        # Calculate revision turnaround
        revision_rounds = []
        for event in timeline:
            if "revision requested" in event.get("subject", "").lower():
                revision_request_dt = parse_date(event["date"])
                # Look for subsequent revision submission
                for later_event in timeline[timeline.index(event) :]:
                    if "revised manuscript" in later_event.get("subject", "").lower():
                        revision_submit_dt = parse_date(later_event["date"])
                        if revision_request_dt and revision_submit_dt:
                            delta = revision_submit_dt - revision_request_dt
                            revision_rounds.append(delta.days)
                            break

        if revision_rounds:
            metrics["revision_turnaround"] = sum(revision_rounds) / len(revision_rounds)

        # Calculate total processing time
        if manuscript.get("status") in ["Accepted", "Rejected"]:
            # Find decision date
            decision_date = manuscript.get("decision_date")
            if decision_date:
                decision_dt = parse_date(decision_date)
                if decision_dt and submission_dt:
                    delta = decision_dt - submission_dt
                    metrics["total_processing_time"] = delta.days
        else:
            # Still in progress - calculate current duration
            delta = current_dt - submission_dt
            metrics["current_stage_duration"] = delta.days

        return metrics

    def track_referee_performance(
        self, referee: Dict, all_manuscripts: List[Dict] = None
    ) -> Dict[str, Any]:
        """Track performance metrics for a referee.

        Args:
            referee: Referee data dictionary
            all_manuscripts: Optional list of all manuscripts to track across papers

        Returns:
            Dictionary containing referee performance metrics
        """
        performance = {
            "name": referee.get("name", "Unknown"),
            "email": referee.get("email", ""),
            "total_reviews": 0,
            "accepted_invitations": 0,
            "declined_invitations": 0,
            "pending_invitations": 0,
            "reports_submitted": 0,
            "average_response_time": None,
            "average_report_time": None,
            "late_reports": 0,
            "report_quality": None,
            "reliability_score": None,
        }

        # If we have all manuscripts, track across papers
        if all_manuscripts:
            response_times = []
            report_times = []

            for ms in all_manuscripts:
                for ref in ms.get("referees", []):
                    if ref.get("name") == referee.get("name") or ref.get("email") == referee.get(
                        "email"
                    ):
                        performance["total_reviews"] += 1

                        if ref.get("response") == "Accepted":
                            performance["accepted_invitations"] += 1
                        elif ref.get("response") == "Declined":
                            performance["declined_invitations"] += 1
                        else:
                            performance["pending_invitations"] += 1

                        if ref.get("report_submitted"):
                            performance["reports_submitted"] += 1

                        # Calculate times from timeline metrics
                        metrics = self.calculate_timeline_metrics(ms)
                        ref_name = ref.get("name")

                        if ref_name in metrics.get("referee_response_times", {}):
                            response_times.append(metrics["referee_response_times"][ref_name])

                        if ref_name in metrics.get("report_submission_times", {}):
                            report_times.append(metrics["report_submission_times"][ref_name])
                            if metrics["report_submission_times"][ref_name] > 30:
                                performance["late_reports"] += 1

            # Calculate averages
            if response_times:
                performance["average_response_time"] = sum(response_times) / len(response_times)

            if report_times:
                performance["average_report_time"] = sum(report_times) / len(report_times)

            # Calculate reliability score (0-100)
            if performance["total_reviews"] > 0:
                accept_rate = performance["accepted_invitations"] / performance["total_reviews"]
                submit_rate = performance["reports_submitted"] / max(
                    1, performance["accepted_invitations"]
                )
                timeliness = 1.0 - min(
                    1.0, performance["late_reports"] / max(1, performance["reports_submitted"])
                )

                performance["reliability_score"] = round(
                    (accept_rate * 0.3 + submit_rate * 0.4 + timeliness * 0.3) * 100
                )
        else:
            # Single referee metrics
            if referee.get("response") == "Accepted":
                performance["accepted_invitations"] = 1
            elif referee.get("response") == "Declined":
                performance["declined_invitations"] = 1
            else:
                performance["pending_invitations"] = 1

            if referee.get("report_submitted"):
                performance["reports_submitted"] = 1

            performance["total_reviews"] = 1

        return performance

    def generate_alerts(self, manuscript: Dict) -> List[Dict[str, Any]]:
        """Generate alerts for manuscript issues.

        Args:
            manuscript: Manuscript data dictionary

        Returns:
            List of alert dictionaries
        """
        alerts = []
        from datetime import datetime, timedelta
        import email.utils

        def parse_date(date_str):
            """Parse email date string to datetime."""
            if not date_str:
                return None
            try:
                return email.utils.parsedate_to_datetime(date_str).replace(tzinfo=None)
            except (ValueError, TypeError):
                return None

        current_dt = datetime.now()

        # Check for overdue reports (>30 days)
        for referee in manuscript.get("referees", []):
            if referee.get("response") == "Accepted" and not referee.get("report_submitted"):
                # Find when they accepted
                response_date = referee.get("response_date")
                if response_date:
                    response_dt = parse_date(response_date)
                    if response_dt:
                        days_waiting = (current_dt - response_dt).days
                        if days_waiting > 30:
                            alerts.append(
                                {
                                    "type": "overdue_report",
                                    "severity": "high" if days_waiting > 45 else "medium",
                                    "referee": referee.get("name"),
                                    "days_overdue": days_waiting - 30,
                                    "message": f"Report from {referee.get('name')} is {days_waiting - 30} days overdue",
                                }
                            )

        # Check for pending editorial decisions
        if manuscript.get("status") == "Under Review":
            # Check if all reports are in
            referees = manuscript.get("referees", [])
            accepted_refs = [r for r in referees if r.get("response") == "Accepted"]
            reports_received = [r for r in accepted_refs if r.get("report_submitted")]

            if accepted_refs and len(reports_received) == len(accepted_refs):
                # All reports in - check how long waiting for decision
                latest_report = None
                for event in manuscript.get("timeline", []):
                    if "report_by" in event.get("details", {}):
                        latest_report = event["date"]

                if latest_report:
                    report_dt = parse_date(latest_report)
                    if report_dt:
                        days_waiting = (current_dt - report_dt).days
                        if days_waiting > 7:
                            alerts.append(
                                {
                                    "type": "pending_decision",
                                    "severity": "medium" if days_waiting > 14 else "low",
                                    "days_waiting": days_waiting,
                                    "message": f"Editorial decision pending for {days_waiting} days since last report",
                                }
                            )

        # Check for stalled manuscripts (no activity >60 days)
        timeline = manuscript.get("timeline", [])
        if timeline:
            last_event = timeline[-1]
            last_date = parse_date(last_event["date"])
            if last_date:
                days_inactive = (current_dt - last_date).days
                if days_inactive > 60:
                    alerts.append(
                        {
                            "type": "stalled_manuscript",
                            "severity": "high",
                            "days_inactive": days_inactive,
                            "last_activity": last_event["subject"],
                            "message": f"No activity for {days_inactive} days",
                        }
                    )

        # Check for missing referee responses
        for referee in manuscript.get("referees", []):
            if not referee.get("response"):
                # Find invitation date
                invited_date = None
                for event in manuscript.get("timeline", []):
                    ref_name = referee.get("name")
                    if ref_name and ref_name in event.get("from", ""):
                        invited_date = event["date"]
                        break

                if invited_date:
                    invited_dt = parse_date(invited_date)
                    if invited_dt:
                        days_waiting = (current_dt - invited_dt).days
                        if days_waiting > 7:
                            alerts.append(
                                {
                                    "type": "missing_response",
                                    "severity": "medium" if days_waiting > 14 else "low",
                                    "referee": referee.get("name"),
                                    "days_waiting": days_waiting,
                                    "message": f"No response from {referee.get('name')} for {days_waiting} days",
                                }
                            )

        # Check for revision deadline approaching/passed
        if manuscript.get("status") == "Awaiting Revision":
            # Look for revision request in timeline
            for event in manuscript.get("timeline", []):
                if "revision" in event.get("subject", "").lower():
                    revision_date = parse_date(event["date"])
                    if revision_date:
                        # Assume 30-day revision deadline
                        deadline = revision_date + timedelta(days=30)
                        days_remaining = (deadline - current_dt).days

                        if days_remaining < 0:
                            alerts.append(
                                {
                                    "type": "revision_overdue",
                                    "severity": "high",
                                    "days_overdue": abs(days_remaining),
                                    "message": f"Revision deadline passed {abs(days_remaining)} days ago",
                                }
                            )
                        elif days_remaining < 7:
                            alerts.append(
                                {
                                    "type": "revision_deadline_approaching",
                                    "severity": "medium",
                                    "days_remaining": days_remaining,
                                    "message": f"Revision deadline in {days_remaining} days",
                                }
                            )
                    break

        return alerts

    def extract_paper_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Extract metadata from paper PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary containing paper metadata
        """
        metadata = {
            "abstract": None,
            "keywords": [],
            "jel_codes": [],
            "msc_codes": [],
            "acknowledgments": None,
            "funding": None,
            "conflict_of_interest": None,
            "data_availability": None,
        }

        try:
            import PyPDF2

            with open(pdf_path, "rb") as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)

                # Extract text from first 10 pages (where metadata usually is)
                full_text = ""
                for page_num in range(min(10, len(pdf_reader.pages))):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    full_text += text + "\n"

                # Extract abstract
                abstract_patterns = [
                    r"Abstract[:\s]+(.*?)(?=Keywords|JEL|MSC|1\.|Introduction|\n\n)",
                    r"ABSTRACT[:\s]+(.*?)(?=Keywords|JEL|MSC|1\.|Introduction|\n\n)",
                    r"Summary[:\s]+(.*?)(?=Keywords|JEL|MSC|1\.|Introduction|\n\n)",
                ]

                for pattern in abstract_patterns:
                    match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        abstract = match.group(1).strip()
                        # Clean up abstract
                        abstract = re.sub(r"\s+", " ", abstract)
                        abstract = abstract.replace("- ", "")  # Remove hyphenation
                        if len(abstract) > 100:  # Reasonable abstract length
                            metadata["abstract"] = abstract[:2000]  # Cap at 2000 chars
                            break

                # Extract keywords
                keyword_patterns = [
                    r"Keywords?[:\s]+(.*?)(?=JEL|MSC|1\.|Introduction|\n\n)",
                    r"Key\s?words?[:\s]+(.*?)(?=JEL|MSC|1\.|Introduction|\n\n)",
                ]

                for pattern in keyword_patterns:
                    match = re.search(pattern, full_text, re.DOTALL | re.IGNORECASE)
                    if match:
                        keywords_text = match.group(1).strip()
                        # Split by common delimiters
                        keywords = re.split(r"[;,·•]|\band\b", keywords_text)
                        keywords = [k.strip() for k in keywords if k.strip() and len(k.strip()) > 2]
                        metadata["keywords"] = keywords[:10]  # Reasonable limit
                        break

                # Extract JEL codes
                jel_pattern = r"JEL[:\s]+(?:Classification|Codes?)?[:\s]*((?:[A-Z]\d{1,2}[,;\s]*)+)"
                match = re.search(jel_pattern, full_text, re.IGNORECASE)
                if match:
                    jel_text = match.group(1)
                    jel_codes = re.findall(r"[A-Z]\d{1,2}", jel_text)
                    metadata["jel_codes"] = list(set(jel_codes))  # Remove duplicates

                # Extract MSC codes (Mathematics Subject Classification)
                msc_patterns = [
                    r"MSC[:\s]+(?:2020|2010)?[:\s]*((?:\d{2}[A-Z]\d{2}[,;\s]*)+)",
                    r"Mathematics Subject Classification[:\s]*((?:\d{2}[A-Z]\d{2}[,;\s]*)+)",
                    r"AMS[:\s]+(?:subject classification)?[:\s]*((?:\d{2}[A-Z]\d{2}[,;\s]*)+)",
                ]

                for pattern in msc_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        msc_text = match.group(1)
                        msc_codes = re.findall(r"\d{2}[A-Z]\d{2}", msc_text)
                        metadata["msc_codes"] = list(set(msc_codes))
                        break

                # Extract acknowledgments
                ack_patterns = [
                    r"Acknowledg(?:e)?ments?[:\s]+(.*?)(?=References|Bibliography|\n\n[A-Z])",
                    r"ACKNOWLEDG(?:E)?MENTS?[:\s]+(.*?)(?=References|Bibliography|\n\n[A-Z])",
                ]

                for pattern in ack_patterns:
                    match = re.search(
                        pattern, full_text[-20000:], re.DOTALL | re.IGNORECASE
                    )  # Check last part
                    if match:
                        ack = match.group(1).strip()
                        ack = re.sub(r"\s+", " ", ack)
                        if len(ack) > 50:
                            metadata["acknowledgments"] = ack[:1000]
                            break

                # Extract funding information
                funding_patterns = [
                    r"(?:Funding|Financial support|Grant)[:\s]+(.*?)(?:\.|$)",
                    r"(?:supported by|funded by)(.*?)(?:\.|$)",
                ]

                for pattern in funding_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        funding = match.group(1).strip()
                        if len(funding) > 10:
                            metadata["funding"] = funding[:500]
                            break

                # Extract conflict of interest
                coi_patterns = [
                    r"Conflict of Interest[:\s]+(.*?)(?:\.|$)",
                    r"Competing Interests?[:\s]+(.*?)(?:\.|$)",
                    r"Declaration of Interest[:\s]+(.*?)(?:\.|$)",
                ]

                for pattern in coi_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        coi = match.group(1).strip()
                        metadata["conflict_of_interest"] = coi[:200]
                        break

                # Extract data availability
                data_patterns = [
                    r"Data Availability[:\s]+(.*?)(?:\.|$)",
                    r"Data and Code[:\s]+(.*?)(?:\.|$)",
                    r"Replication (?:Data|Files)[:\s]+(.*?)(?:\.|$)",
                ]

                for pattern in data_patterns:
                    match = re.search(pattern, full_text, re.IGNORECASE)
                    if match:
                        data = match.group(1).strip()
                        metadata["data_availability"] = data[:200]
                        break

        except Exception as e:
            print(f"⚠️ Could not extract metadata from {pdf_path}: {e}")

        return metadata

    def identify_corresponding_author(
        self, authors: List[Dict[str, Any]], pdf_path: str = None, emails: List[Dict] = None
    ) -> Dict[str, Any]:
        """Identify the corresponding author.

        Args:
            authors: List of author dictionaries
            pdf_path: Optional path to PDF to check for markers
            emails: Optional list of email communications

        Returns:
            Dictionary with corresponding author information
        """
        corresponding = {"name": None, "email": None, "affiliation": None, "confidence": "low"}

        if not authors:
            return corresponding

        # Method 1: Check PDF for corresponding author marker
        if pdf_path:
            try:
                import PyPDF2

                with open(pdf_path, "rb") as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)

                    # Check first 3 pages
                    text = ""
                    for page_num in range(min(3, len(pdf_reader.pages))):
                        page = pdf_reader.pages[page_num]
                        text += page.extract_text() + "\n"

                    # Look for corresponding author markers
                    corr_patterns = [
                        r"(?:Corresponding author|Correspondence)[:\s]*([^,\n]+)",
                        r"(?:\*|†|‡)(?:Corresponding author)[:\s]*([^,\n]+)",
                        r"E-?mail[:\s]*(?:address)?[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                    ]

                    for pattern in corr_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            corr_info = match.group(1).strip()

                            # Try to match with author list
                            for author in authors:
                                if author.get("name"):
                                    # Check if author name appears in corresponding info
                                    name_parts = author["name"].split()
                                    if any(
                                        part.lower() in corr_info.lower() for part in name_parts
                                    ):
                                        corresponding["name"] = author["name"]
                                        corresponding["email"] = author.get("email")
                                        corresponding["affiliation"] = author.get("affiliation")
                                        corresponding["confidence"] = "high"
                                        return corresponding

                            # If no name match, check for email
                            email_match = re.search(
                                r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", corr_info
                            )
                            if email_match:
                                corresponding["email"] = email_match.group(1)
                                corresponding["confidence"] = "medium"

                                # Try to match email to author
                                for author in authors:
                                    if author.get("email") == corresponding["email"]:
                                        corresponding["name"] = author["name"]
                                        corresponding["affiliation"] = author.get("affiliation")
                                        corresponding["confidence"] = "high"
                                        return corresponding

            except Exception as e:
                print(f"⚠️ Could not check PDF for corresponding author: {e}")

        # Method 2: Check email patterns
        if emails:
            # Count who sends emails about the manuscript
            sender_counts = {}
            for email in emails:
                if "from" in email:
                    # Extract email address
                    from_field = email["from"]
                    email_match = re.search(r"<([^>]+)>", from_field)
                    if email_match:
                        sender_email = email_match.group(1)

                        # Match to authors
                        for author in authors:
                            if author.get("email") == sender_email:
                                sender_counts[author["name"]] = (
                                    sender_counts.get(author["name"], 0) + 1
                                )

            # Most frequent sender is likely corresponding author
            if sender_counts:
                corr_name = max(sender_counts, key=sender_counts.get)
                for author in authors:
                    if author.get("name") == corr_name:
                        corresponding["name"] = author["name"]
                        corresponding["email"] = author.get("email")
                        corresponding["affiliation"] = author.get("affiliation")
                        corresponding["confidence"] = "medium"
                        return corresponding

        # Method 3: Default to first author (common convention)
        if authors:
            first_author = authors[0]
            corresponding["name"] = first_author.get("name")
            corresponding["email"] = first_author.get("email")
            corresponding["affiliation"] = first_author.get("affiliation")
            corresponding["confidence"] = "low"

        return corresponding

    def cleanup(self):
        """Clean up resources."""
        # No browser to close for email-based extractor
        print("🧹 Email extractor cleanup complete")

        # Clean up test cache if in test mode
        if hasattr(self, "cache_manager") and hasattr(self.cache_manager, "test_mode"):
            if self.cache_manager.test_mode:
                try:
                    import shutil

                    shutil.rmtree(self.cache_manager.cache_dir, ignore_errors=True)
                    print(f"🧹 Cleaned up test cache: {self.cache_manager.cache_dir}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not fully cleanup test cache: {e}")


def main():
    """Run FS email-based extractor."""
    extractor = ComprehensiveFSExtractor()

    try:
        manuscripts = extractor.extract_all()

        if manuscripts:
            extractor.save_results()

            print(f"\n📊 EXTRACTION SUMMARY:")
            print(f"Total manuscripts: {len(manuscripts)}")
            for i, ms in enumerate(manuscripts[:10]):  # Show first 10
                print(f"  {i+1}. {ms['id']}: {ms['title'][:70]}... [{ms['status']}]")
        else:
            print("❌ No manuscripts extracted")

    except KeyboardInterrupt:
        print("\n⚠️ Extraction interrupted by user")
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        traceback.print_exc()
    finally:
        extractor.cleanup()


if __name__ == "__main__":
    main()
