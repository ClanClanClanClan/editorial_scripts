"""
Optimized SICON Extractor - Ultimate Production Version
Fixes all SICON-specific issues identified in the audit:
- Metadata parsing regression (empty titles/authors)
- PDF download failures
- Inconsistent manuscript discovery
- Missing referee emails
"""

import asyncio
import logging
import re

# Import base extractor and models
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

# Add the ultimate directory to path
ultimate_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ultimate_dir))

from core.models.optimized_models import OptimizedReferee
from extractors.base.optimized_base_extractor import ConnectionConfig, OptimizedBaseExtractor

logger = logging.getLogger(__name__)


class OptimizedSICONExtractor(OptimizedBaseExtractor):
    """
    Optimized SICON extractor that fixes all critical issues
    Based on July 11 working baseline
    """

    journal_name = "SICON"
    base_url = "https://sicon.siam.org"
    login_type = "orcid"
    requires_cloudflare_wait = True
    cloudflare_wait_seconds = 60

    # SICON-specific configuration
    AE_LINK_PATTERNS = [
        r"(\d+) AE",  # "4 AE", "2 AE", etc.
        r"AE \((\d+)\)",  # "AE (4)", "AE (2)", etc.
    ]

    MANUSCRIPT_ID_PATTERN = r"M(\d{6})"

    def __init__(self, output_dir: Path | None = None):
        """Initialize SICON extractor with optimized settings"""
        config = ConnectionConfig(
            timeout_ms=120000,  # 2 minutes for SICON
            max_retries=3,
            retry_delay_base=2.0,
            browser_pool_size=2,  # SICON doesn't need many concurrent browsers
            concurrent_limit=3,
        )
        super().__init__(output_dir, config)

        # SICON-specific tracking
        self.discovered_categories = {}
        self.failed_manuscripts = []

    async def _perform_authentication(self) -> bool:
        """
        SICON ORCID authentication with CloudFlare handling
        """
        try:
            logger.info("🔐 Starting SICON ORCID authentication")

            # Look for ORCID login button with multiple selectors
            orcid_selectors = [
                'a[href*="orcid"]',
                'button[href*="orcid"]',
                ".orcid-login",
                '[class*="orcid"]',
                'a:contains("ORCID")',
                'button:contains("ORCID")',
            ]

            orcid_button = None
            for selector in orcid_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        orcid_button = elements[0]
                        break
                except:
                    continue

            if not orcid_button:
                logger.error("ORCID login button not found")
                return False

            # Click ORCID login
            logger.info("Clicking ORCID login button")
            await orcid_button.click()
            await self.page.wait_for_load_state("networkidle", timeout=30000)

            # Check if we're on ORCID login page
            current_url = self.page.url
            if "orcid.org" not in current_url:
                logger.error(f"Not redirected to ORCID page. Current URL: {current_url}")
                return False

            # Fill ORCID credentials
            logger.info("Filling ORCID credentials")

            # Email field
            email_selectors = ["#username", '[name="userId"]', "#userId", 'input[type="email"]']
            email_filled = False
            for selector in email_selectors:
                try:
                    email_field = await self.page.query_selector(selector)
                    if email_field:
                        await email_field.fill(self.username)
                        email_filled = True
                        break
                except:
                    continue

            if not email_filled:
                logger.error("Could not find email field")
                return False

            # Password field
            password_selectors = ["#password", '[name="password"]', 'input[type="password"]']
            password_filled = False
            for selector in password_selectors:
                try:
                    password_field = await self.page.query_selector(selector)
                    if password_field:
                        await password_field.fill(self.password)
                        password_filled = True
                        break
                except:
                    continue

            if not password_filled:
                logger.error("Could not find password field")
                return False

            # Submit login
            submit_selectors = [
                "#signin-button",
                '[type="submit"]',
                'button:contains("Sign in")',
                ".btn-primary",
            ]
            submit_clicked = False
            for selector in submit_selectors:
                try:
                    submit_button = await self.page.query_selector(selector)
                    if submit_button:
                        await submit_button.click()
                        submit_clicked = True
                        break
                except:
                    continue

            if not submit_clicked:
                logger.error("Could not find submit button")
                return False

            # Wait for redirect back to SICON
            logger.info("Waiting for redirect back to SICON...")
            await self.page.wait_for_load_state("networkidle", timeout=60000)

            # Handle privacy/consent modal if it appears
            await self._handle_privacy_modal()

            # Verify authentication success
            final_url = self.page.url
            if "sicon.siam.org" in final_url and "cgi-bin/main.plex" in final_url:
                logger.info("✅ SICON authentication successful")
                return True
            else:
                logger.error(f"Authentication verification failed. Final URL: {final_url}")
                return False

        except Exception as e:
            logger.error(f"SICON authentication failed: {e}")
            return False

    async def _handle_privacy_modal(self):
        """Handle privacy/consent modal that sometimes appears"""
        try:
            # Look for common modal patterns
            modal_selectors = [
                'button:contains("Continue")',
                'button:contains("Accept")',
                'button:contains("Agree")',
                ".modal button",
                '[role="dialog"] button',
            ]

            for selector in modal_selectors:
                try:
                    button = await self.page.query_selector(selector)
                    if button and await button.is_visible():
                        logger.info("Found privacy modal, clicking continue")
                        await button.click()
                        await asyncio.sleep(2)
                        break
                except:
                    continue
        except Exception as e:
            logger.debug(f"No privacy modal found or error handling it: {e}")

    async def _discover_manuscripts(self) -> dict[str, str]:
        """
        Discover all manuscripts by finding AE categories
        Fixed to consistently find all manuscripts
        """
        logger.info("🔍 Discovering SICON manuscripts")

        manuscripts = {}

        try:
            # Get main page content
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            # Find AE category links
            ae_links = await self._find_ae_category_links(soup)
            logger.info(f"Found {len(ae_links)} AE categories: {list(ae_links.keys())}")

            # Process each category
            for category_name, category_url in ae_links.items():
                try:
                    logger.info(f"Processing category: {category_name}")
                    category_manuscripts = await self._extract_manuscripts_from_category(
                        category_url
                    )
                    manuscripts.update(category_manuscripts)

                    # Track category
                    self.discovered_categories[category_name] = len(category_manuscripts)

                except Exception as e:
                    logger.error(f"Failed to process category {category_name}: {e}")
                    continue

            logger.info(f"📋 Total manuscripts discovered: {len(manuscripts)}")
            logger.info(f"Category breakdown: {self.discovered_categories}")

            return manuscripts

        except Exception as e:
            logger.error(f"Manuscript discovery failed: {e}")
            return {}

    async def _find_ae_category_links(self, soup: BeautifulSoup) -> dict[str, str]:
        """Find AE category links with improved detection"""
        ae_links = {}

        # Look for links with AE patterns
        for pattern in self.AE_LINK_PATTERNS:
            links = soup.find_all("a", string=re.compile(pattern))
            for link in links:
                link_text = link.get_text(strip=True)
                href = link.get("href")

                if href and ("main.plex" in href or "cgi-bin" in href):
                    # Make URL absolute
                    if href.startswith("/"):
                        full_url = f"{self.base_url}{href}"
                    elif href.startswith("cgi-bin"):
                        full_url = f"{self.base_url}/{href}"
                    else:
                        full_url = href

                    ae_links[link_text] = full_url

        # Alternative: look for any links containing manuscript counts
        if not ae_links:
            # Look for any links with numbers that might be manuscript counts
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                text = link.get_text(strip=True)
                href = link.get("href")

                # Look for patterns like "Under Review (4)", "AE Tasks (2)", etc.
                if re.search(r"\(\d+\)", text) and ("main.plex" in href or "cgi-bin" in href):
                    if href.startswith("/"):
                        full_url = f"{self.base_url}{href}"
                    elif href.startswith("cgi-bin"):
                        full_url = f"{self.base_url}/{href}"
                    else:
                        full_url = href

                    ae_links[text] = full_url

        return ae_links

    async def _extract_manuscripts_from_category(self, category_url: str) -> dict[str, str]:
        """Extract manuscript IDs and URLs from a category page"""
        manuscripts = {}

        try:
            # Navigate to category page
            await self.connection_manager.robust_navigate(self.page, category_url)

            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, "html.parser")

            # Find manuscript links
            manuscript_links = soup.find_all("a", href=re.compile(r"M\d{6}"))

            for link in manuscript_links:
                href = link.get("href")

                # Extract manuscript ID
                id_match = re.search(self.MANUSCRIPT_ID_PATTERN, href)
                if id_match:
                    manuscript_id = f"M{id_match.group(1)}"

                    # Make URL absolute
                    if href.startswith("/"):
                        full_url = f"{self.base_url}{href}"
                    elif href.startswith("cgi-bin"):
                        full_url = f"{self.base_url}/{href}"
                    else:
                        full_url = href

                    manuscripts[manuscript_id] = full_url

            logger.info(f"Found {len(manuscripts)} manuscripts in category")

        except Exception as e:
            logger.error(f"Failed to extract manuscripts from category {category_url}: {e}")

        return manuscripts

    async def _parse_manuscript_metadata_optimized(self, soup: BeautifulSoup) -> dict[str, Any]:
        """
        CRITICAL FIX: Parse manuscript metadata FIRST before creating object
        This fixes the empty titles/authors regression
        """
        metadata = {
            "title": "",
            "authors": [],
            "status": "",
            "submission_date": "",
            "corresponding_editor": "",
            "associate_editor": "",
        }

        try:
            # Title extraction with multiple strategies
            title = await self._extract_title(soup)
            if title:
                metadata["title"] = title

            # Authors extraction
            authors = await self._extract_authors(soup)
            if authors:
                metadata["authors"] = authors

            # Status extraction
            status = await self._extract_status(soup)
            if status:
                metadata["status"] = status

            # Submission date extraction
            submission_date = await self._extract_submission_date(soup)
            if submission_date:
                metadata["submission_date"] = submission_date

            # Editor extraction
            ce = await self._extract_corresponding_editor(soup)
            if ce:
                metadata["corresponding_editor"] = ce

            ae = await self._extract_associate_editor(soup)
            if ae:
                metadata["associate_editor"] = ae

            logger.debug(
                f"Parsed metadata: title='{metadata['title'][:50]}...', authors={len(metadata['authors'])}"
            )

        except Exception as e:
            logger.error(f"Metadata parsing error: {e}")

        return metadata

    async def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract manuscript title with multiple fallback strategies"""
        title_selectors = [
            "h1",
            ".title",
            '[class*="title"]',
            'td:contains("Title:")',
            'strong:contains("Title")',
        ]

        for selector in title_selectors:
            try:
                if ":contains(" in selector:
                    # Handle text-based selectors
                    elements = soup.find_all(string=re.compile("Title", re.I))
                    for element in elements:
                        parent = element.parent
                        if parent:
                            # Look for title in next sibling or parent
                            title_text = self._extract_text_after_label(parent, "title")
                            if title_text:
                                return title_text
                else:
                    element = soup.select_one(selector)
                    if element:
                        title = element.get_text(strip=True)
                        if title and len(title) > 10:  # Reasonable title length
                            return title
            except Exception:
                continue

        # Fallback: look in HTML tables
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True).lower()
                    if "title" in cell_text and i + 1 < len(cells):
                        title = cells[i + 1].get_text(strip=True)
                        if title and len(title) > 10:
                            return title

        return ""

    async def _extract_authors(self, soup: BeautifulSoup) -> list[str]:
        """Extract authors with institution information"""
        authors = []

        try:
            # Look for author information in various places
            author_patterns = ["Authors?:", "Author\\(s\\):", "By:", "Written by:"]

            for pattern in author_patterns:
                elements = soup.find_all(string=re.compile(pattern, re.I))
                for element in elements:
                    parent = element.parent
                    if parent:
                        author_text = self._extract_text_after_label(parent, pattern)
                        if author_text:
                            # Parse multiple authors
                            parsed_authors = self._parse_author_string(author_text)
                            if parsed_authors:
                                authors.extend(parsed_authors)
                                break

            # Fallback: look in tables
            if not authors:
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        for i, cell in enumerate(cells):
                            cell_text = cell.get_text(strip=True).lower()
                            if "author" in cell_text and i + 1 < len(cells):
                                author_text = cells[i + 1].get_text(strip=True)
                                parsed_authors = self._parse_author_string(author_text)
                                if parsed_authors:
                                    authors.extend(parsed_authors)

        except Exception as e:
            logger.warning(f"Author extraction error: {e}")

        return authors[:10]  # Limit to reasonable number

    def _extract_text_after_label(self, element, label_pattern: str) -> str:
        """Extract text that comes after a label"""
        try:
            # Get all text content
            full_text = element.get_text()

            # Find text after the label
            match = re.search(f"{label_pattern}\\s*:?\\s*(.+)", full_text, re.I | re.DOTALL)
            if match:
                return match.group(1).strip()

            # Alternative: look in next sibling
            next_sibling = element.next_sibling
            if next_sibling:
                if hasattr(next_sibling, "get_text"):
                    return next_sibling.get_text(strip=True)
                elif isinstance(next_sibling, str):
                    return next_sibling.strip()

        except Exception:
            pass

        return ""

    def _parse_author_string(self, author_text: str) -> list[str]:
        """Parse author string into individual authors with affiliations"""
        if not author_text or len(author_text.strip()) < 2:
            return []

        authors = []

        # Split by common delimiters
        delimiters = [";", " and ", ","]
        current_text = author_text

        for delimiter in delimiters:
            if delimiter in current_text:
                parts = current_text.split(delimiter)
                for part in parts:
                    cleaned = part.strip()
                    if cleaned and len(cleaned) > 2:
                        authors.append(cleaned)
                break

        # If no delimiters found, treat as single author
        if not authors:
            cleaned = author_text.strip()
            if cleaned and len(cleaned) > 2:
                authors.append(cleaned)

        return authors

    async def _extract_status(self, soup: BeautifulSoup) -> str:
        """Extract manuscript status"""
        status_patterns = ["Status:", "Current Status:", "Manuscript Status:"]

        for pattern in status_patterns:
            elements = soup.find_all(string=re.compile(pattern, re.I))
            for element in elements:
                parent = element.parent
                if parent:
                    status = self._extract_text_after_label(parent, pattern)
                    if status:
                        return status

        # Default status
        return "Under Review"

    async def _extract_submission_date(self, soup: BeautifulSoup) -> str:
        """Extract submission date"""
        date_patterns = ["Submitted:", "Submission Date:", "Date Submitted:", "Received:"]

        for pattern in date_patterns:
            elements = soup.find_all(string=re.compile(pattern, re.I))
            for element in elements:
                parent = element.parent
                if parent:
                    date_text = self._extract_text_after_label(parent, pattern)
                    if date_text:
                        # Parse and format date
                        formatted_date = self._parse_date(date_text)
                        if formatted_date:
                            return formatted_date

        return ""

    def _parse_date(self, date_text: str) -> str:
        """Parse various date formats to YYYY-MM-DD"""
        try:
            # Clean up the date text
            date_text = re.sub(r"[^\d\-\/\s]", "", date_text).strip()

            # Common date patterns
            date_patterns = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"]

            for pattern in date_patterns:
                try:
                    parsed_date = datetime.strptime(date_text, pattern)
                    return parsed_date.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        except Exception:
            pass

        return ""

    async def _extract_corresponding_editor(self, soup: BeautifulSoup) -> str:
        """Extract corresponding editor"""
        editor_patterns = ["Corresponding Editor:", "Chief Editor:", "Editor:", "CE:"]

        for pattern in editor_patterns:
            elements = soup.find_all(string=re.compile(pattern, re.I))
            for element in elements:
                parent = element.parent
                if parent:
                    editor = self._extract_text_after_label(parent, pattern)
                    if editor:
                        return editor

        return ""

    async def _extract_associate_editor(self, soup: BeautifulSoup) -> str:
        """Extract associate editor"""
        ae_patterns = ["Associate Editor:", "AE:", "Assigned to:"]

        for pattern in ae_patterns:
            elements = soup.find_all(string=re.compile(pattern, re.I))
            for element in elements:
                parent = element.parent
                if parent:
                    ae = self._extract_text_after_label(parent, pattern)
                    if ae:
                        return ae

        return ""

    async def _extract_referees_optimized(
        self, soup: BeautifulSoup, manuscript_id: str
    ) -> list[OptimizedReferee]:
        """
        Extract referees from both 'Potential Referees' and 'Referees' sections
        """
        referees = []

        try:
            # Extract from "Potential Referees" section (declined/no response)
            potential_referees = await self._extract_potential_referees(soup)
            referees.extend(potential_referees)

            # Extract from "Referees" section (active/accepted)
            active_referees = await self._extract_active_referees(soup)
            referees.extend(active_referees)

            logger.info(f"Found {len(referees)} referees for {manuscript_id}")

        except Exception as e:
            logger.error(f"Referee extraction error for {manuscript_id}: {e}")

        return referees

    async def _extract_potential_referees(self, soup: BeautifulSoup) -> list[OptimizedReferee]:
        """Extract referees from 'Potential Referees' section"""
        referees = []

        # Find the Potential Referees section
        potential_section = soup.find(string=re.compile("Potential Referees", re.I))
        if not potential_section:
            return referees

        # Get the parent container
        section_parent = potential_section.parent
        while section_parent and section_parent.name not in ["div", "section", "table"]:
            section_parent = section_parent.parent

        if not section_parent:
            return referees

        # Find referee links in this section
        referee_links = section_parent.find_all("a", href=True)

        for link in referee_links:
            try:
                referee_name = link.get_text(strip=True)
                if referee_name and len(referee_name) > 2:
                    # Check for status information
                    status = "Declined"  # Default for potential referees

                    # Look for status patterns
                    link_parent = link.parent
                    if link_parent:
                        parent_text = link_parent.get_text()
                        if "(Status:" in parent_text:
                            status_match = re.search(r"\(Status:\s*([^)]+)\)", parent_text)
                            if status_match:
                                status = status_match.group(1).strip()

                    # Extract biblio URL
                    biblio_url = link.get("href")
                    if biblio_url:
                        if biblio_url.startswith("/"):
                            biblio_url = f"{self.base_url}{biblio_url}"
                        elif biblio_url.startswith("cgi-bin"):
                            biblio_url = f"{self.base_url}/{biblio_url}"

                    referee = OptimizedReferee(
                        name=referee_name,
                        email="",  # To be extracted later
                        status=status,
                        biblio_url=biblio_url,
                    )

                    referees.append(referee)

            except Exception as e:
                logger.warning(f"Error processing potential referee: {e}")
                continue

        return referees

    async def _extract_active_referees(self, soup: BeautifulSoup) -> list[OptimizedReferee]:
        """Extract referees from 'Referees' section"""
        referees = []

        # Find the Referees section
        referees_section = soup.find(string=re.compile("^Referees$", re.I))
        if not referees_section:
            return referees

        # Get the parent container
        section_parent = referees_section.parent
        while section_parent and section_parent.name not in ["div", "section", "table"]:
            section_parent = section_parent.parent

        if not section_parent:
            return referees

        # Find referee information in this section
        referee_links = section_parent.find_all("a", href=True)

        for link in referee_links:
            try:
                referee_name = link.get_text(strip=True)
                if referee_name and len(referee_name) > 2:
                    # Determine status based on surrounding text
                    status = "Accepted, awaiting report"  # Default for active referees
                    contact_date = ""
                    due_date = ""
                    report_date = ""

                    # Look for status and date information
                    link_parent = link.parent
                    if link_parent:
                        parent_text = link_parent.get_text()

                        # Check for report submission
                        if "Report submitted" in parent_text:
                            status = "Report submitted"
                            # Look for date
                            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", parent_text)
                            if date_match:
                                report_date = date_match.group(1)

                        # Look for contact date
                        contact_match = re.search(
                            r"Last Contact Date:\s*(\d{4}-\d{2}-\d{2})", parent_text
                        )
                        if contact_match:
                            contact_date = contact_match.group(1)

                        # Look for due date
                        due_match = re.search(r"Due:\s*(\d{4}-\d{2}-\d{2})", parent_text)
                        if due_match:
                            due_date = due_match.group(1)

                    # Extract biblio URL
                    biblio_url = link.get("href")
                    if biblio_url:
                        if biblio_url.startswith("/"):
                            biblio_url = f"{self.base_url}{biblio_url}"
                        elif biblio_url.startswith("cgi-bin"):
                            biblio_url = f"{self.base_url}/{biblio_url}"

                    referee = OptimizedReferee(
                        name=referee_name,
                        email="",  # To be extracted later
                        status=status,
                        contact_date=contact_date if contact_date else None,
                        due_date=due_date if due_date else None,
                        report_date=report_date if report_date else None,
                        biblio_url=biblio_url,
                    )

                    referees.append(referee)

            except Exception as e:
                logger.warning(f"Error processing active referee: {e}")
                continue

        return referees

    async def _extract_pdf_urls(self, soup: BeautifulSoup) -> dict[str, str]:
        """Extract PDF URLs with improved detection"""
        pdf_urls = {}

        try:
            # Look for PDF links
            pdf_links = soup.find_all("a", href=re.compile(r"\.pdf$", re.I))

            for link in pdf_links:
                href = link.get("href")
                link_text = link.get_text(strip=True).lower()

                # Make URL absolute
                if href.startswith("/"):
                    full_url = f"{self.base_url}{href}"
                elif href.startswith("sicon_files"):
                    full_url = f"{self.base_url}/{href}"
                else:
                    full_url = href

                # Categorize PDF type
                if "cover" in link_text or "cover" in href:
                    pdf_urls["cover_letter"] = full_url
                elif "supplement" in link_text or "supplement" in href:
                    pdf_urls["supplement"] = full_url
                elif "manuscript" in link_text or "art_file" in href:
                    pdf_urls["manuscript"] = full_url
                else:
                    # Default to manuscript if unclear
                    pdf_urls["manuscript"] = full_url

            # Also look for AE recommendation links
            ae_links = soup.find_all("a", href=re.compile(r"display_me_review", re.I))
            for link in ae_links:
                href = link.get("href")
                if href.startswith("/"):
                    full_url = f"{self.base_url}{href}"
                elif href.startswith("cgi-bin"):
                    full_url = f"{self.base_url}/{href}"
                else:
                    full_url = href

                pdf_urls["ae_recommendation"] = full_url

            logger.debug(f"Found {len(pdf_urls)} PDF URLs: {list(pdf_urls.keys())}")

        except Exception as e:
            logger.error(f"PDF URL extraction error: {e}")

        return pdf_urls

    async def _extract_email_from_page(self) -> str | None:
        """Extract email from referee bio page"""
        try:
            content = await self.page.content()

            # Look for email patterns
            email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
            emails = re.findall(email_pattern, content)

            if emails:
                # Return first valid email
                for email in emails:
                    if "@" in email and "." in email:
                        return email.lower()

        except Exception as e:
            logger.warning(f"Email extraction error: {e}")

        return None

    async def _parse_html_content(self, content: str) -> BeautifulSoup:
        """Parse HTML content using BeautifulSoup"""
        return BeautifulSoup(content, "html.parser")
