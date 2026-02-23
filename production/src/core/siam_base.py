import atexit
import base64
import glob
import os
import random
import re
import sys
import time
import json
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin
from core.web_enrichment import enrich_people_from_web

try:
    from core.gmail_search import GmailSearchManager

    GMAIL_SEARCH_AVAILABLE = True
except ImportError:
    GMAIL_SEARCH_AVAILABLE = False


def with_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (
                    TimeoutException,
                    NoSuchElementException,
                    WebDriverException,
                    StaleElementReferenceException,
                ) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff**attempt)
                        print(
                            f"   \u26a0\ufe0f {func.__name__} attempt {attempt + 1} failed: {str(e)[:50]}"
                        )
                        print(f"      Retrying in {wait_time:.1f} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"   \u274c {func.__name__} failed after {max_attempts} attempts")
                except Exception as e:
                    print(
                        f"   \u274c {func.__name__} failed with unrecoverable error: {str(e)[:100]}"
                    )
                    raise
            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator


class SIAMExtractor(CachedExtractorMixin):
    JOURNAL_CODE = ""
    JOURNAL_NAME = ""
    BASE_URL = ""
    MAIN_URL = ""
    MANUSCRIPT_PATTERN = r"M\d{6}"
    CLOUDFLARE_WAIT = 10

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.init_cached_extractor(self.JOURNAL_CODE)
        self.setup_directories()
        self.setup_chrome_options()
        self.driver = None
        self.wait = None
        self.service = None
        self.original_window = None
        self.manuscripts_data = []
        self._current_manuscript_id = ""
        self._last_exception_msg = ""

        self.email = os.environ.get(f"{self.JOURNAL_CODE}_EMAIL") or os.environ.get("SICON_EMAIL")
        self.password = os.environ.get(f"{self.JOURNAL_CODE}_PASSWORD") or os.environ.get(
            "SICON_PASSWORD"
        )

        atexit.register(self.cleanup_driver)

    def setup_chrome_options(self):
        self.chrome_options = uc.ChromeOptions()
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--window-size=1200,800")

    def setup_directories(self):
        self.base_dir = Path(__file__).parent.parent.parent
        jc = self.JOURNAL_CODE.lower()
        self.download_dir = self.base_dir / "downloads" / jc
        self.output_dir = self.base_dir / "outputs" / jc
        self.cache_dir_path = self.base_dir / "cache" / jc

        for d in [self.download_dir, self.output_dir, self.cache_dir_path]:
            d.mkdir(parents=True, exist_ok=True)

    def setup_driver(self):
        import subprocess

        chrome_version = None
        try:
            result = subprocess.run(
                [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    "--version",
                ],
                capture_output=True,
                text=True,
            )
            ver = result.stdout.strip().split()[-1].split(".")[0]
            chrome_version = int(ver)
        except Exception:
            pass

        self.driver = uc.Chrome(
            options=self.chrome_options,
            headless=self.headless,
            version_main=chrome_version,
        )
        if not self.headless:
            try:
                self.driver.set_window_position(-2000, 0)
                self.driver.set_window_size(1200, 800)
            except Exception:
                pass
        self.driver.set_page_load_timeout(120)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 30)
        self.original_window = self.driver.current_window_handle
        print(f"\U0001f5a5\ufe0f  Browser configured for {self.JOURNAL_CODE}")

    def safe_click(self, element) -> bool:
        if not element:
            return False
        try:
            element.click()
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                return False

    def safe_get_text(self, element) -> str:
        if not element:
            return ""
        try:
            return element.text.strip()
        except Exception:
            try:
                return element.get_attribute("textContent").strip()
            except Exception:
                return ""

    def smart_wait(self, seconds: float = 1.0):
        wait_time = seconds + random.uniform(-0.2, 0.5)
        time.sleep(max(0.3, wait_time))

    def _dismiss_alerts(self):
        try:
            alert = self.driver.switch_to.alert
            print(f"   \u26a0\ufe0f  Alert: {alert.text}")
            alert.accept()
        except (NoAlertPresentException, Exception):
            pass

    def _dismiss_cookie_overlay(self):
        try:
            self.driver.execute_script(
                """
                var overlay = document.getElementById('cookie-policy-layer-bg');
                if (overlay) overlay.remove();
                var layer = document.getElementById('cookie-policy-layer');
                if (layer) layer.remove();
            """
            )
        except Exception:
            pass

    def _wait_for_cloudflare(self, timeout=None):
        timeout = timeout or self.CLOUDFLARE_WAIT
        for i in range(timeout):
            self._dismiss_alerts()
            try:
                title = self.driver.title.lower()
            except Exception:
                time.sleep(1)
                continue
            if "just a moment" in title or title in ("404 not found", ""):
                if i % 15 == 0:
                    print(f"   \u23f3 Cloudflare challenge... ({i}s)")
                time.sleep(1)
                continue
            return True
        return False

    def _wait_for_page_load(self, timeout: int = 15):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

    ORCID_CLIENT_ID = "APP-JXX1CVPHKDQQ05O1"

    def _build_orcid_url(self) -> str:
        from urllib.parse import quote

        redirect_uri = quote(f"{self.BASE_URL}/cgi-bin/main.plex", safe="")
        return (
            f"https://orcid.org/signin?client_id={self.ORCID_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&state=orcid%7C%7C%7C%7C%7C%7C%7C"
            f"&response_type=code&scope=%2Fread-limited"
        )

    @with_retry(max_attempts=3, delay=3.0)
    def login_via_orcid(self) -> bool:
        if not self.email or not self.password:
            print("\u274c Missing ORCID credentials")
            return False

        base_domain = self.BASE_URL.replace("https://", "").replace("http://", "").split("/")[0]

        print(f"\U0001f510 Navigating to {self.MAIN_URL}")
        self.driver.get(self.MAIN_URL)
        if not self._wait_for_cloudflare():
            print("\u274c Cloudflare challenge not resolved")
            return False

        self.smart_wait(2)
        print(f"   \u2705 Page loaded: {self.driver.title}")
        self._save_debug_html("01_main_page")

        src = self.driver.page_source
        has_dashboard = "form_type=dt_folder" in src or "form_type=view_ms" in src
        has_logout = "Logout" in src or "Log Out" in src
        if has_logout and has_dashboard:
            print("\u2705 Already logged in with dashboard visible")
            return True

        self._dismiss_cookie_overlay()

        orcid_url = self._build_orcid_url()
        print(f"\u2705 Navigating directly to ORCID login...")
        self.driver.get(orcid_url)
        self.smart_wait(3)

        url = self.driver.current_url
        if url.startswith(("https://" + base_domain, "http://" + base_domain)):
            print("\u2705 Already authenticated via saved session")
            return self._ensure_dashboard_loaded()

        if "orcid.org" not in url:
            print(f"\u274c Unexpected page: {url[:100]}")
            self._save_debug_html("02_unexpected")
            return False

        print(f"\u2705 On ORCID login page")
        self._save_debug_html("02_orcid_login")

        try:
            try:
                username_field = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "username-input"))
                )
            except TimeoutException:
                username_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "username"))
                )
            password_field = self.driver.find_element(By.ID, "password")

            username_field.clear()
            username_field.send_keys(self.email)
            time.sleep(0.5)

            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(0.5)

            login_button = self.driver.find_element(By.ID, "signin-button")
            login_button.click()
            print("\u2705 Submitted ORCID credentials")

        except TimeoutException:
            print(f"\u274c ORCID login form not found")
            self._save_debug_html("03_orcid_form_missing")
            return False

        for i in range(30):
            time.sleep(1)
            try:
                url = self.driver.current_url
            except Exception:
                continue
            if url.startswith(("https://" + base_domain, "http://" + base_domain)):
                print(f"\u2705 ORCID login successful")
                self._save_debug_html("04_post_redirect")
                return self._ensure_dashboard_loaded()

        try:
            authorize_button = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.ID, "authorize"))
            )
            authorize_button.click()
            print("\u2705 Authorized access")
            time.sleep(3)
        except (TimeoutException, NoSuchElementException):
            pass

        for i in range(30):
            time.sleep(1)
            try:
                url = self.driver.current_url
            except Exception:
                continue
            if url.startswith(("https://" + base_domain, "http://" + base_domain)):
                print(f"\u2705 ORCID login successful")
                return self._ensure_dashboard_loaded()

        print(f"\u274c Still on: {self.driver.current_url}")
        self._save_debug_html("05_login_failed")
        return False

    def _save_debug_html(self, label: str):
        try:
            debug_dir = Path(self.output_dir) / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            filepath = debug_dir / f"{self.JOURNAL_CODE.lower()}_{label}.html"
            with open(filepath, "w") as f:
                f.write(self.driver.page_source)
        except Exception:
            pass

    def _ensure_dashboard_loaded(self) -> bool:
        for attempt in range(3):
            self._wait_for_cloudflare(self.CLOUDFLARE_WAIT)
            self.smart_wait(5)
            try:
                src = self.driver.page_source
                title = self.driver.title
                logged_in = "Logout" in src or "Log Out" in src
                has_dashboard = (
                    "form_type=dt_folder" in src
                    or "form_type=view_ms" in src
                    or "ndt_folder" in src
                )
                has_ae = "AE" in src or "ndt_task" in src
                print(
                    f"   Dashboard check: title='{title}', logged_in={logged_in}, has_dashboard={has_dashboard}"
                )
                if logged_in and (has_dashboard or has_ae):
                    print(f"   \u2705 Dashboard loaded")
                    self._save_debug_html("dashboard")
                    try:
                        self.driver.minimize_window()
                    except Exception:
                        pass
                    return True
                if logged_in and not has_dashboard:
                    print(f"   \u26a0\ufe0f  Logged in but not on dashboard")
            except Exception:
                pass
            if attempt < 2:
                print(f"   \u26a0\ufe0f  Dashboard not loaded (attempt {attempt+1}), reloading...")
                self.driver.get(self.MAIN_URL)
                self.smart_wait(5)
        print(f"\u274c Dashboard failed to load after 3 attempts")
        return False

    @with_retry(max_attempts=2, delay=2.0)
    def navigate_to_ae_dashboard(self) -> bool:
        print("\U0001f4cb Navigating to AE dashboard...")
        page_source = self.driver.page_source

        has_folders = "form_type=dt_folder" in page_source
        has_manuscripts = "form_type=view_ms" in page_source
        has_ae_pattern = bool(re.search(r"\d+\s*AE", page_source))

        if has_folders or has_manuscripts or has_ae_pattern:
            print("\u2705 Already on AE dashboard")
            return True

        try:
            ae_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(text(), 'Associate Editor') and not(contains(text(), 'FAQ')) and not(contains(text(), 'Instructions'))]",
            )
            if not ae_links:
                ae_links = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'AE ')]")

            for link in ae_links:
                try:
                    if link.is_displayed():
                        href = link.get_attribute("href") or ""
                        if "instructions" in href.lower() or "faq" in href.lower():
                            continue
                        self.safe_click(link)
                        self.smart_wait(3)
                        print(f"\u2705 Clicked: {self.safe_get_text(link)}")
                        return True
                except Exception:
                    continue
        except Exception as e:
            print(f"\u26a0\ufe0f AE dashboard navigation: {str(e)[:60]}")

        print(
            "\u26a0\ufe0f Could not find explicit AE dashboard link, continuing with current page"
        )
        return True

    def _find_ae_section_links(self) -> List:
        try:
            ae_links = self.driver.execute_script(
                """
                var aeSection = document.querySelector('tbody.desktop-section[role="assoc_ed"]');
                if (!aeSection) {
                    var tbodies = document.querySelectorAll('tbody.desktop-section');
                    for (var i = 0; i < tbodies.length; i++) {
                        var text = tbodies[i].textContent.toLowerCase();
                        if (text.indexOf('associate editor') !== -1) {
                            aeSection = tbodies[i];
                            break;
                        }
                    }
                }
                if (!aeSection) return null;
                var links = aeSection.querySelectorAll('a.ndt_task_link, a.ndt_folder_link');
                if (links.length === 0) links = aeSection.querySelectorAll('a');
                return Array.from(links);
            """
            )
            return ae_links or []
        except Exception:
            return []

    def _get_ae_section_hrefs(self) -> set:
        try:
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            ae_section = soup.find("tbody", {"role": "assoc_ed"})
            if not ae_section:
                for tbody in soup.find_all("tbody", class_="desktop-section"):
                    if "associate editor" in tbody.get_text().lower():
                        ae_section = tbody
                        break
            if ae_section:
                hrefs = set()
                for a in ae_section.find_all("a", href=True):
                    raw = a["href"]
                    qs = raw.split("?", 1)[-1] if "?" in raw else raw
                    hrefs.add(qs)
                return hrefs
        except Exception:
            pass
        return set()

    def discover_categories(self) -> List[Dict[str, str]]:
        print("\U0001f50d Discovering manuscript categories...")
        categories = []
        seen_hrefs = set()
        self._dashboard_manuscripts = []

        ae_hrefs = self._get_ae_section_hrefs()
        if ae_hrefs:
            print(f"   📍 Found {len(ae_hrefs)} links in Associate Editor section")

        try:
            ae_section_links = self._find_ae_section_links()

            if ae_section_links:
                task_links = ae_section_links
                print(f"   📍 Scoped to Associate Editor section ({len(task_links)} links)")
            else:
                task_links = self.driver.find_elements(
                    By.CSS_SELECTOR, "a.ndt_folder_link, a.ndt_task_link"
                )
                if not task_links:
                    task_links = self.driver.find_elements(By.TAG_NAME, "a")

            ms_pattern = re.compile(self.MANUSCRIPT_PATTERN)

            for link in task_links:
                try:
                    text = self.safe_get_text(link)
                    if not text:
                        continue
                    href = link.get_attribute("href") or ""

                    if ae_hrefs:
                        href_qs = href.split("?", 1)[-1] if "?" in href else href
                        if href_qs not in ae_hrefs:
                            continue

                    if "form_type=view_ms" in href:
                        ms_match = ms_pattern.search(text)
                        if ms_match:
                            self._dashboard_manuscripts.append(
                                {"manuscript_id": ms_match.group(0), "href": href}
                            )
                        continue

                    if "form_type=dt_folder" not in href and "form_type=ndt_folder" not in href:
                        continue

                    match = re.search(r"(\d+)\s*AE", text)
                    if not match:
                        match = re.search(r"\((\d+)\)\s*$", text)
                    if match:
                        count = int(match.group(1))
                        if count > 0:
                            if href in seen_hrefs:
                                continue
                            seen_hrefs.add(href)
                            cat_name = text.strip()
                            try:
                                row = link.find_element(By.XPATH, "..")
                                title_span = row.find_element(By.CSS_SELECTOR, "span.ndt_title")
                                if title_span:
                                    cat_name = title_span.text.strip()
                            except Exception:
                                pass
                            cat_name = re.sub(r"\s*\(\d+\)\s*$", "", cat_name).strip()
                            cat_name = re.sub(r"\s*\d+\s*AE\s*$", "", cat_name).strip()
                            if not cat_name:
                                cat_name = text.strip()
                            categories.append(
                                {
                                    "name": cat_name,
                                    "count": count,
                                    "href": href,
                                    "element": link,
                                }
                            )
                except Exception:
                    continue

        except Exception as e:
            print(f"\u274c Category discovery error: {str(e)[:60]}")

        for cat in categories:
            print(f"   \u2705 {cat['name']} ({cat['count']} manuscripts)")

        if self._dashboard_manuscripts:
            print(
                f"   \U0001f4c4 {len(self._dashboard_manuscripts)} manuscripts found directly on dashboard"
            )

        if not categories and not self._dashboard_manuscripts:
            print("\u26a0\ufe0f No categories with manuscripts found")

        return categories

    @with_retry(max_attempts=2, delay=3.0)
    def collect_manuscript_ids(self, category: Dict) -> List[Dict[str, str]]:
        cat_name = category["name"]
        print(f"\n\U0001f4c2 Processing category: {cat_name}")

        href = category.get("href", "")
        if href:
            self.driver.get(href)
            self.smart_wait(3)
            self._wait_for_cloudflare(60)
            self.smart_wait(2)
        else:
            try:
                self.safe_click(category.get("element"))
                self.smart_wait(3)
            except Exception as e:
                print(f"\u274c Could not navigate to category: {str(e)[:60]}")
                return []

        manuscripts = []
        seen_ids = set()

        try:
            view_ms_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='view_ms']")
            if not view_ms_links:
                view_ms_links = self.driver.find_elements(By.TAG_NAME, "a")

            pattern = re.compile(self.MANUSCRIPT_PATTERN)
            for link in view_ms_links:
                try:
                    href = link.get_attribute("href") or ""
                    text = self.safe_get_text(link)
                    combined = f"{href} {text}"

                    if "form_type=view_ms" not in href and "M" not in text[:10]:
                        continue

                    match = pattern.search(combined)
                    if not match:
                        try:
                            row = link.find_element(By.XPATH, "./ancestor::tr")
                            row_text = row.text or ""
                            match = pattern.search(row_text)
                        except Exception:
                            pass

                    if match:
                        ms_id = match.group(0)
                        if ms_id not in seen_ids:
                            seen_ids.add(ms_id)
                            manuscripts.append({"manuscript_id": ms_id, "href": href})
                except Exception:
                    continue
        except Exception as e:
            print(f"\u274c Manuscript collection error: {str(e)[:60]}")

        if not manuscripts and category.get("count", 0) > 0:
            debug_path = self.output_dir / f"debug_category_{cat_name.replace(' ', '_')}.html"
            try:
                with open(debug_path, "w") as f:
                    f.write(self.driver.page_source)
                print(
                    f"   ⚠️ Expected {category['count']} but found 0 — debug HTML saved: {debug_path.name}"
                )
            except Exception:
                pass

        print(f"   \U0001f4c4 Found {len(manuscripts)} manuscripts")
        return manuscripts

    @with_retry(max_attempts=2, delay=3.0)
    def extract_manuscript_detail(self, ms_info: Dict) -> Optional[Dict]:
        ms_id = ms_info["manuscript_id"]
        self._current_manuscript_id = ms_id
        print(f"\n   \U0001f4c4 Extracting: {ms_id}")

        href = ms_info.get("href", "")
        if not href:
            print(f"      \u274c No URL for manuscript")
            return None

        try:
            self.driver.get(href)
            self.smart_wait(3)
            self._wait_for_cloudflare(60)
            self.smart_wait(2)
        except Exception as e:
            print(f"      \u274c Could not navigate to manuscript: {str(e)[:60]}")
            return None

        manuscript = {
            "manuscript_id": ms_id,
            "extraction_timestamp": datetime.now().isoformat(),
            "journal": self.JOURNAL_CODE,
            "authors": [],
            "referees": [],
            "editors": [],
            "metadata": {},
            "documents": {},
        }

        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")
        page_text = soup.get_text()
        self._save_debug_html(f"ms_{ms_id}")

        self._extract_metadata(manuscript, page_text, soup)
        self._extract_referees(manuscript, page_text, soup)
        self._extract_authors_from_page(manuscript, page_text, soup)

        for ref in manuscript["referees"]:
            if not ref.get("email"):
                if self._is_session_dead():
                    break
                self._extract_referee_contact_via_click(ref)

        for author in manuscript["authors"]:
            if not author.get("email") and author.get("biblio_url"):
                if self._is_session_dead():
                    break
                self._extract_author_contact_via_biblio(author)

        author_email_count = sum(1 for a in manuscript["authors"] if a.get("email"))
        if author_email_count:
            print(f"      📧 Author emails: {author_email_count}/{len(manuscript['authors'])}")

        ms_href = ms_info.get("href", "")
        if ms_href and "view_ms" not in self.driver.current_url:
            self.driver.get(ms_href)
            self.smart_wait(2)
        self._wait_for_cloudflare(30)
        self._wait_for_page_load()
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        self._extract_documents(manuscript, soup)
        self._extract_decision_letter(manuscript, soup)
        self._extract_author_response(manuscript, soup)
        self._extract_referee_reports(manuscript, soup)
        self._extract_version_history(manuscript, soup)

        status_soup = None
        email_soup = None
        try:
            status_soup = self._scrape_status_details_page(manuscript, soup)
        except Exception:
            pass
        try:
            email_soup = self._scrape_email_log_page(manuscript, soup)
        except Exception:
            pass

        self._populate_editors(manuscript)
        self._compute_status_details(manuscript)
        self._build_audit_trail(manuscript, status_soup, email_soup)
        self._backfill_referee_dates_from_trail(manuscript)
        self._compute_peer_review_milestones(manuscript)
        self._compute_referee_statistics(manuscript)

        has_emails = any(r.get("email") for r in manuscript["referees"])
        manuscript["emails_extracted"] = has_emails
        manuscript["status"] = manuscript.get("metadata", {}).get("current_stage", "")
        rev_num = manuscript.get("metadata", {}).get("revision_number")
        manuscript["is_revision"] = bool(rev_num and rev_num > 0)
        manuscript["revision_number"] = rev_num or 0

        ref_count = len(manuscript["referees"])
        auth_count = len(manuscript["authors"])
        doc_count = len(manuscript.get("documents", {}).get("files", []))
        email_count = sum(1 for r in manuscript["referees"] if r.get("email"))
        print(
            f"      \u2705 {ms_id}: {ref_count} referees ({email_count} emails), {auth_count} authors, {doc_count} documents"
        )

        return manuscript

    def _extract_metadata(self, manuscript: Dict, page_text: str, soup: BeautifulSoup):
        metadata = {}
        field_map = {}

        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                label = th.get_text(strip=True).rstrip(":")
                value = td.get_text(strip=True)
                if label and value:
                    field_map[label.lower()] = value

        for key in ("manuscript #", "manuscript"):
            if key in field_map:
                ms_match = re.search(r"(M\d{6})", field_map[key])
                if ms_match:
                    metadata["manuscript_id"] = ms_match.group(1)
                break

        if "submission date" in field_map:
            metadata["submission_date"] = field_map["submission date"][:19]

        if "current stage" in field_map:
            metadata["current_stage"] = field_map["current stage"]

        if "title" in field_map:
            metadata["title"] = field_map["title"][:500]
            manuscript["title"] = field_map["title"][:500]

        if "abstract" in field_map:
            manuscript["abstract"] = field_map["abstract"][:2000]

        if "keywords" in field_map:
            kw_text = field_map["keywords"]
            manuscript["keywords"] = [k.strip() for k in kw_text.split(",") if k.strip()]

        if "associate editor" in field_map:
            metadata["associate_editor"] = field_map["associate editor"]

        if "corresponding editor" in field_map:
            metadata["corresponding_editor"] = field_map["corresponding editor"]

        if "current revision #" in field_map:
            try:
                metadata["revision_number"] = int(field_map["current revision #"])
            except ValueError:
                pass

        if "manuscript type" in field_map:
            metadata["manuscript_type"] = field_map["manuscript type"]

        if "running title" in field_map:
            metadata["running_title"] = field_map["running title"][:200]

        if "submission page count" in field_map:
            metadata["page_count"] = field_map["submission page count"]

        manuscript["metadata"] = metadata

    def _extract_referees(self, manuscript: Dict, page_text: str, soup: BeautifulSoup):
        referees = []
        seen_names = set()

        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()

            if label in ("potential referees", "potential referee"):
                self._parse_referee_cell(td, referees, seen_names, "potential")
            elif label in ("referees", "referee"):
                self._parse_referee_cell(td, referees, seen_names, "active")

        if not referees:
            self._extract_referees_from_text(referees, seen_names, page_text)

        for ref in referees:
            self._extract_referee_contact(ref, soup)

        manuscript["referees"] = referees
        if referees:
            print(
                f"      \U0001f465 Referees: {len(referees)} "
                f"({len([r for r in referees if r.get('section') == 'potential'])} potential, "
                f"{len([r for r in referees if r.get('section') == 'active'])} active)"
            )

    def _parse_referee_cell(self, td, referees, seen_names, section):
        td_text = td.get_text(strip=True)
        if td_text.lower() in ("n/a", "none", ""):
            return

        links = td.find_all("a")
        for link in links:
            href = link.get("href", "")
            if "biblio_dump" not in href:
                continue
            link_text = link.get_text(strip=True)
            if not link_text:
                continue

            name_match = re.match(r"(.+?)\s*#(\d+)", link_text)
            if not name_match:
                continue

            name = name_match.group(1).strip()
            num = int(name_match.group(2))
            if name in seen_names:
                continue
            seen_names.add(name)

            ref = {"name": name, "referee_number": num, "section": section}

            next_text = ""
            next_sib = link.next_sibling
            while next_sib and not (hasattr(next_sib, "name") and next_sib.name == "a"):
                if hasattr(next_sib, "get_text"):
                    next_text += next_sib.get_text(strip=True)
                elif isinstance(next_sib, str):
                    next_text += next_sib.strip()
                next_sib = next_sib.next_sibling

            if section == "potential":
                cd = re.search(r"Last\s+Contact\s+Date\s*:\s*(\d{4}-\d{2}-\d{2})", next_text)
                if cd:
                    ref["contact_date"] = cd.group(1)
                st = re.search(r"Status\s*:\s*([^)]+)", next_text)
                ref["status"] = st.group(1).strip() if st else "Contacted"
            else:
                rcvd = re.search(r"Rcvd\s*:\s*(\d{4}-\d{2}-\d{2})", next_text)
                due = re.search(r"Due\s*:\s*(\d{4}-\d{2}-\d{2})", next_text)
                if rcvd:
                    ref["status"] = "Report Submitted"
                    ref["received_date"] = rcvd.group(1)
                elif due:
                    ref["status"] = "Awaiting Report"
                    ref["due_date"] = due.group(1)
                else:
                    ref["status"] = "Accepted"

            referees.append(ref)

    def _extract_referees_from_text(self, referees, seen_names, page_text):
        for section_name, section_type in [
            ("Potential Referees", "potential"),
            ("Referees", "active"),
        ]:
            pattern = re.compile(
                rf"{section_name}\s*:?\s*(.*?)(?=(?:Potential Referees|Manuscript Items|Decision|$))",
                re.IGNORECASE | re.DOTALL,
            )
            match = pattern.search(page_text)
            if not match:
                continue
            section = match.group(1)
            entries = re.findall(
                r"([\w\u00c0-\u024f][\w\u00c0-\u024f .-]+?)\s*#(\d+)",
                section,
            )
            non_names = {
                "current revision",
                "article file",
                "source file",
                "referee",
                "manuscript",
                "revision",
                "attachment",
                "version",
                "file",
            }
            for name, num in entries:
                name = name.strip()
                if name in seen_names or len(name) < 3:
                    continue
                if name.lower() in non_names:
                    continue
                seen_names.add(name)
                ref = {
                    "name": name,
                    "referee_number": int(num),
                    "section": section_type,
                    "status": "Unknown",
                }
                referees.append(ref)

    def _extract_referees_from_tables(self, referees: List, seen_names: set, soup: BeautifulSoup):
        for heading in soup.find_all(["h2", "h3", "h4", "strong", "b"]):
            heading_text = heading.get_text(strip=True).lower()
            if "referee" not in heading_text and "reviewer" not in heading_text:
                continue

            section = "potential" if "potential" in heading_text else "active"
            sibling = heading.find_next("table")
            if not sibling:
                sibling = heading.find_next(["ul", "ol", "div"])
            if not sibling:
                continue

            for row in sibling.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                name_text = cells[0].get_text(strip=True)
                name_match = re.match(
                    r"([A-Z][a-z\u00e0-\u00ff]+(?:\s+[A-Za-z\u00e0-\u00ff]+)+)", name_text
                )
                if not name_match:
                    continue
                name = name_match.group(1).strip()
                if name in seen_names:
                    continue
                seen_names.add(name)

                status_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                ref = {
                    "name": name,
                    "status": status_text or "Unknown",
                    "section": section,
                }
                referees.append(ref)

    def _extract_referee_contact(self, ref: Dict, soup: BeautifulSoup):
        name = ref.get("name", "")
        if not name:
            return

        try:
            links = soup.find_all("a")
            for link in links:
                link_text = link.get_text(strip=True)
                if name.lower() in link_text.lower() or link_text.lower() in name.lower():
                    href = link.get("href", "")
                    if "mailto:" in href:
                        ref["email"] = href.replace("mailto:", "").strip()
                        return

            name_parts = name.split()
            surname = name_parts[-1].lower() if name_parts else ""
            if surname:
                mailto_links = soup.find_all("a", href=re.compile(r"mailto:", re.I))
                for ml in mailto_links:
                    email = ml.get("href", "").replace("mailto:", "").strip()
                    if surname in email.lower():
                        ref["email"] = email
                        return

            email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
            page_text = soup.get_text()
            name_idx = page_text.lower().find(name.lower())
            if name_idx >= 0:
                nearby = page_text[name_idx : name_idx + 500]
                emails = email_pattern.findall(nearby)
                system_emails = {
                    "noreply",
                    "donotreply",
                    "support",
                    "admin",
                    "help",
                    "info",
                    "editor",
                }
                for em in emails:
                    if not any(se in em.lower() for se in system_emails):
                        ref["email"] = em
                        return

        except Exception:
            pass

    def _extract_referee_contact_via_click(self, ref: Dict):
        name = ref.get("name", "")
        if not name or ref.get("email"):
            return

        current_url = self.driver.current_url

        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            biblio_url = None
            for link in links:
                try:
                    link_text = self.safe_get_text(link)
                    if name.lower() not in link_text.lower():
                        continue
                    href = link.get_attribute("href") or ""
                    if "biblio_dump" in href:
                        biblio_url = href
                        break
                except Exception:
                    continue

            if not biblio_url:
                return

            self.driver.get(biblio_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

            page_source = self.driver.page_source
            bio_soup = BeautifulSoup(page_source, "html.parser")

            email_match = re.search(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                page_source,
            )
            if email_match:
                candidate = email_match.group(0)
                system_emails = {
                    "noreply",
                    "donotreply",
                    "no-reply",
                    "do-not-reply",
                    "support",
                    "admin",
                    "help",
                    "info",
                    "bounce",
                    "mailer",
                    "robot",
                    "editor",
                    "system",
                }
                if not any(se in candidate.lower() for se in system_emails):
                    ref["email"] = candidate

            bio_text = bio_soup.get_text()
            orcid_match = re.search(r"ORCID:\s*([\d]{4}-[\d]{4}-[\d]{4}-[\d]{3}[\dX])", bio_text)
            if orcid_match:
                ref["orcid"] = orcid_match.group(1)

            inst_match = re.search(r"Primary Work\s*(.+?)(?:\n|Address|Phone|Fax|$)", bio_text)
            if inst_match:
                inst = inst_match.group(1).strip()
                if inst and len(inst) > 3 and "@" not in inst:
                    ref["institution"] = inst[:200]
            if not ref.get("institution"):
                for td in bio_soup.find_all("td"):
                    td_text = td.get_text(separator=" ", strip=True)
                    if len(td_text) < 200 and len(td_text) > 5 and "@" not in td_text:
                        td_lower = td_text.lower()
                        if "university" in td_lower or "institute" in td_lower:
                            ref["institution"] = td_text[:200]
                            break

            secondary_email = re.search(
                r"Secondary Email.*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                bio_text,
            )
            if secondary_email:
                ref["secondary_email"] = secondary_email.group(1)

            self.driver.get(current_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

        except Exception as e:
            print(f"         \u26a0\ufe0f Popup email error for {name}: {str(e)[:60]}")
            try:
                self.driver.get(current_url)
                self.smart_wait(2)
            except Exception:
                pass

    def _extract_author_contact_via_biblio(self, author: Dict):
        biblio_url = author.get("biblio_url", "")
        if not biblio_url:
            return
        name = author.get("name", "")
        current_url = self.driver.current_url
        try:
            full_url = self._resolve_url(biblio_url)
            self.driver.get(full_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

            page_source = self.driver.page_source
            bio_soup = BeautifulSoup(page_source, "html.parser")
            bio_text = bio_soup.get_text()

            system_emails = {
                "noreply",
                "donotreply",
                "no-reply",
                "do-not-reply",
                "support",
                "admin",
                "help",
                "info",
                "bounce",
                "mailer",
                "robot",
                "editor",
                "system",
            }
            email_match = re.search(
                r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                page_source,
            )
            if email_match:
                candidate = email_match.group(0)
                if not any(se in candidate.lower() for se in system_emails):
                    author["email"] = candidate
                    author["email_domain"] = candidate.split("@")[-1]

            orcid_match = re.search(r"ORCID:\s*([\d]{4}-[\d]{4}-[\d]{4}-[\d]{3}[\dX])", bio_text)
            if orcid_match:
                author["orcid"] = orcid_match.group(1)

            if not author.get("institution"):
                inst_match = re.search(r"Primary Work\s*(.+?)(?:\n|Address|Phone|Fax|$)", bio_text)
                if inst_match:
                    inst = inst_match.group(1).strip()
                    if inst and len(inst) > 3 and "@" not in inst:
                        author["institution"] = inst[:200]

            pw_th = bio_soup.find("th", string=re.compile(r"Primary\s+Work", re.IGNORECASE))
            if pw_th:
                pw_td = pw_th.find_next("td")
                if pw_td:
                    lines = [
                        l.strip() for l in pw_td.get_text(separator="\n").split("\n") if l.strip()
                    ]
                    addr_lines = []
                    for line in lines:
                        if "@" in line or re.match(r"^\(?\+?\d[\d\s\-()]+$", line):
                            continue
                        addr_lines.append(line)
                    seen = set()
                    unique_addr = []
                    for line in addr_lines:
                        if line.lower() not in seen:
                            seen.add(line.lower())
                            unique_addr.append(line)
                    if len(unique_addr) >= 2 and not author.get("department"):
                        dept_candidate = unique_addr[1]
                        dept_keywords = [
                            "department",
                            "school",
                            "faculty",
                            "division",
                            "institute",
                            "lab",
                            "center",
                            "centre",
                            "program",
                        ]
                        if any(kw in dept_candidate.lower() for kw in dept_keywords) or (
                            not any(c.isdigit() for c in dept_candidate)
                            and "," not in dept_candidate
                            and len(dept_candidate) > 3
                        ):
                            author["department"] = dept_candidate[:200]
                    if not author.get("institution") and unique_addr:
                        author["institution"] = unique_addr[0][:200]
                    for line in reversed(unique_addr):
                        cleaned = line.rstrip(",").strip()
                        if (
                            len(cleaned) > 2
                            and not any(c.isdigit() for c in cleaned)
                            and cleaned.lower()
                            not in (
                                author.get("institution", "").lower(),
                                author.get("department", "").lower(),
                            )
                        ):
                            author["country"] = cleaned
                            break

            secondary = re.search(
                r"Secondary Email.*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                bio_text,
            )
            if secondary:
                author["secondary_email"] = secondary.group(1)

            safe_name = re.sub(r"[^a-zA-Z0-9]", "_", name)[:30]
            self._save_debug_html(f"biblio_{safe_name}")

            self.driver.get(current_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)
        except Exception as e:
            print(f"         ⚠️ Author biblio error for {name}: {str(e)[:60]}")
            try:
                self.driver.get(current_url)
                self.smart_wait(2)
            except Exception:
                pass

    def _extract_suggested_reviewers(self, manuscript: Dict, soup: BeautifulSoup):
        referee_recommendations = {
            "recommended_referees": [],
            "opposed_referees": [],
        }
        skip_phrases = {
            "suggest",
            "when",
            "please",
            "authors should",
            "conflict",
            "potential referees",
            "n/a",
            "none",
            "no suggestion",
        }

        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()
            if "suggest" not in label and "oppose" not in label:
                continue

            is_opposed = "oppose" in label
            text_block = td.get_text(separator="\n", strip=True)

            for line in text_block.split("\n"):
                line = line.strip()
                if not line or len(line) < 3:
                    continue
                line_lower = line.lower().strip("- \t")
                if any(line_lower.startswith(sp) for sp in skip_phrases):
                    continue
                if ":" in line and "@" not in line:
                    continue

                email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", line)
                if not email_match:
                    continue

                email = email_match.group(0)
                before_email = line[: email_match.start()]
                before_email = re.sub(r"(?i)\b(e-?mail|mail)\s*:\s*$", "", before_email).strip()
                before_email = re.sub(r"^\d+[\.\)\-]\s*", "", before_email).strip()
                before_email = before_email.lstrip("-").strip()
                before_email = before_email.rstrip(",;( ").strip()

                parts = [p.strip() for p in before_email.split(",") if p.strip()]
                name = parts[0] if parts else ""
                institution = parts[1] if len(parts) > 1 else ""

                if not name or len(name) < 2:
                    continue

                entry = {"name": name, "email": email}
                if institution and len(institution) > 2:
                    entry["institution"] = institution

                key = "opposed_referees" if is_opposed else "recommended_referees"
                referee_recommendations[key].append(entry)

        if any(referee_recommendations.values()):
            manuscript["referee_recommendations"] = referee_recommendations
            rec_count = len(referee_recommendations["recommended_referees"])
            opp_count = len(referee_recommendations["opposed_referees"])
            if rec_count or opp_count:
                print(f"         📋 Suggested: {rec_count} recommended, {opp_count} opposed")

    def _extract_version_history(self, manuscript: Dict, soup: BeautifulSoup):
        version_history = []
        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()
            if label not in ("other version", "other versions", "related manuscripts"):
                continue

            for a_tag in td.find_all("a", href=True):
                href = a_tag["href"]
                link_text = a_tag.get_text(strip=True)
                if "view_ms" in href or "form_type" in href:
                    rev_no_match = re.search(r"ms_rev_no=(\d+)", href)
                    rev_no = int(rev_no_match.group(1)) if rev_no_match else 0
                    version_history.append(
                        {
                            "manuscript_id": link_text,
                            "version_number": rev_no,
                            "href": href,
                        }
                    )

        if version_history:
            manuscript["version_history"] = version_history

    def _compute_referee_statistics(self, manuscript: Dict):
        audit = manuscript.get("audit_trail", [])

        def _parse_date(s):
            if not s:
                return None
            try:
                return datetime.strptime(str(s).split("T")[0].split()[0], "%Y-%m-%d")
            except Exception:
                return None

        REMINDER_TYPES = {
            "review_reminder",
            "review_reminder_final",
            "review_overdue",
        }

        for ref in manuscript.get("referees", []):
            stats = {}
            contact = ref.get("contact_date", "")
            received = ref.get("received_date", "")
            due = ref.get("due_date", "")
            acceptance = ref.get("acceptance_date", "")
            email_lower = ref.get("email", "").lower()
            name_lower = ref.get("name", "").lower()

            reminder_count = 0
            first_invitation_date = None
            first_acceptance_date = None
            first_report_date = None

            for ev in audit:
                ev_type = ev.get("type", "")
                ev_to = ev.get("to", "").lower()
                ev_desc = ev.get("description", "").lower()
                ev_date = ev.get("date", "")

                is_this_referee = (email_lower and ev_to == email_lower) or (
                    name_lower and name_lower in ev_desc
                )
                if not is_this_referee:
                    continue

                if ev_type == "reviewer_invitation":
                    d = _parse_date(ev_date)
                    if d and (first_invitation_date is None or d < first_invitation_date):
                        first_invitation_date = d
                elif ev_type in REMINDER_TYPES:
                    reminder_count += 1
                elif ev_type == "reviewer_accepted":
                    d = _parse_date(ev_date)
                    if d and (first_acceptance_date is None or d < first_acceptance_date):
                        first_acceptance_date = d
                elif ev_type in ("review_received", "review_report_confirmation"):
                    d = _parse_date(ev_date)
                    if d and (first_report_date is None or d < first_report_date):
                        first_report_date = d

            stats["reminders_received"] = reminder_count

            c_date = _parse_date(contact) or first_invitation_date
            a_date = _parse_date(acceptance) or first_acceptance_date
            r_date = _parse_date(received) or first_report_date
            d_date = _parse_date(due)

            if c_date and a_date:
                days = (a_date - c_date).days
                if days >= 0:
                    stats["invitation_to_agreement_days"] = days
            if a_date and r_date:
                days = (r_date - a_date).days
                if days >= 0:
                    stats["agreement_to_submission_days"] = days
            if c_date and r_date:
                days = (r_date - c_date).days
                if days > 0:
                    stats["total_review_days"] = days
                    stats["invitation_to_submission_days"] = days
            if c_date and d_date:
                days = (d_date - c_date).days
                if days > 0:
                    stats["allowed_review_days"] = days
            if r_date and d_date:
                stats["days_ahead_of_deadline"] = (d_date - r_date).days

            if stats:
                ref["statistics"] = stats

    def _compute_status_details(self, manuscript: Dict):
        referees = manuscript.get("referees", [])
        if not referees:
            return

        status_counts = {
            "total_referees": len(referees),
            "active_referees": 0,
            "potential_referees": 0,
            "reports_received": 0,
            "reports_pending": 0,
            "contacted": 0,
        }

        for ref in referees:
            section = ref.get("section", "")
            status = (ref.get("status") or "").lower()

            if section == "active":
                status_counts["active_referees"] += 1
                if ref.get("received_date"):
                    status_counts["reports_received"] += 1
                else:
                    status_counts["reports_pending"] += 1
            elif section == "potential":
                status_counts["potential_referees"] += 1

            if "contact" in status:
                status_counts["contacted"] += 1

        manuscript["status_details"] = status_counts

    def _resolve_url(self, relative_url: str) -> str:
        if relative_url.startswith("http"):
            return relative_url
        from urllib.parse import urlparse

        parsed = urlparse(self.driver.current_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if relative_url.startswith("/"):
            return base + relative_url
        return base + "/" + relative_url

    def _extract_decision_letter(self, manuscript: Dict, soup: BeautifulSoup):
        try:
            decision_url = None
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "display_ed_decision_summary" in href:
                    decision_url = href
                    break
                text = a.get_text(strip=True).lower()
                if "decision" in text and "previous" in text:
                    decision_url = href
                    break

            if not decision_url:
                return

            decision_url = self._resolve_url(decision_url)

            current_url = self.driver.current_url
            self.driver.get(decision_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

            page_source = self.driver.page_source
            dec_soup = BeautifulSoup(page_source, "html.parser")
            letter_text = dec_soup.get_text(separator="\n", strip=True)

            if len(letter_text) > 50:
                manuscript["decision_letter_text"] = letter_text[:20000]
                print(f"         📝 Decision letter extracted ({len(letter_text)} chars)")

            self.driver.get(current_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

        except Exception as e:
            print(f"         ⚠️ Decision letter error: {str(e)[:60]}")
            try:
                self.driver.get(current_url)
                self.smart_wait(2)
            except Exception:
                pass

    def _extract_author_response(self, manuscript: Dict, soup: BeautifulSoup):
        try:
            response_url = None
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True).lower()
                href = a["href"]
                if ("response" in text and "referee" in text) or (
                    "author" in text and "response" in text
                ):
                    if ".pdf" not in href.lower():
                        response_url = href
                        break

            if not response_url:
                return

            response_url = self._resolve_url(response_url)

            current_url = self.driver.current_url
            self.driver.get(response_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

            page_source = self.driver.page_source
            resp_soup = BeautifulSoup(page_source, "html.parser")
            response_text = resp_soup.get_text(separator="\n", strip=True)

            if len(response_text) > 50:
                manuscript["author_response_text"] = response_text[:20000]
                print(f"         📝 Author response extracted ({len(response_text)} chars)")

            self.driver.get(current_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

        except Exception as e:
            print(f"         ⚠️ Author response error: {str(e)[:60]}")
            try:
                self.driver.get(current_url)
                self.smart_wait(2)
            except Exception:
                pass

    def _extract_referee_reports(self, manuscript: Dict, soup: BeautifulSoup):
        try:
            reviews_url = None
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "display_all_reviews" in href:
                    reviews_url = href
                    break

            if not reviews_url:
                return

            reviews_url = self._resolve_url(reviews_url)

            current_url = self.driver.current_url
            self.driver.get(reviews_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

            page_source = self.driver.page_source
            rev_soup = BeautifulSoup(page_source, "html.parser")
            self._save_debug_html(f"reviews_{manuscript['manuscript_id']}")

            referees = manuscript.get("referees", [])

            def _match_referee(name_text: str, ref_num_text: str = ""):
                name_lower = name_text.lower().strip()
                for ref in referees:
                    ref_name = ref.get("name", "").lower()
                    if ref_name and ref_name in name_lower:
                        return ref
                    if ref_name and name_lower in ref_name:
                        return ref
                if ref_num_text:
                    num_match = re.search(r"(\d+)", ref_num_text)
                    if num_match:
                        num = num_match.group(1)
                        for ref in referees:
                            if str(ref.get("referee_number")) == num:
                                return ref
                return None

            eval_header = rev_soup.find("b", string=re.compile(r"Evaluations", re.IGNORECASE))
            if eval_header:
                eval_table = eval_header.find_next("table")
                if eval_table:
                    rows = eval_table.find_all("tr")
                    headers = []
                    for cell in rows[0].find_all(["th", "td"]) if rows else []:
                        headers.append(cell.get_text(strip=True))

                    for row in rows[1:]:
                        cells = row.find_all(["th", "td"])
                        if len(cells) < 4:
                            continue
                        ref_name = cells[0].get_text(strip=True)
                        if not ref_name:
                            continue
                        role_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        recommendation = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        quality = cells[3].get_text(strip=True) if len(cells) > 3 else ""

                        ref = _match_referee(ref_name, role_text)
                        if not ref:
                            continue

                        report = ref.get("report", {})
                        if recommendation:
                            report["recommendation"] = recommendation
                            ref["recommendation"] = recommendation
                        if quality:
                            report["manuscript_quality"] = quality

                        scores = {}
                        for i in range(4, min(len(cells), len(headers))):
                            val = cells[i].get_text(strip=True)
                            if val:
                                scores[headers[i]] = val
                        if scores:
                            report["scores"] = scores

                        ref["report"] = report

            for p in rev_soup.find_all("p", style=re.compile(r"font-weight:\s*bold")):
                p_text = p.get_text(strip=True)
                match = re.match(r"(.+?)'s\s+Comments\s+\(Referee\s+#(\d+)\)\s*-\s*(.+)", p_text)
                if not match:
                    continue
                ref_name = match.group(1)
                ref_num = match.group(2)
                report_date = match.group(3).strip()

                ref = _match_referee(ref_name, f"#{ref_num}")
                if not ref:
                    continue

                report = ref.get("report", {})
                report["report_date"] = report_date

                comment_table = p.find_next("table")
                if comment_table:
                    for row in comment_table.find_all("tr"):
                        th = row.find("th")
                        td = row.find("td")
                        if not th or not td:
                            continue
                        label = th.get_text(strip=True).lower()
                        value = td.get_text(strip=True)
                        if not value or value == "\xa0":
                            continue
                        if "remark" in label and "author" in label:
                            report["comments_to_author"] = value[:10000]
                        elif "confidential" in label or ("message" in label and "editor" in label):
                            report["confidential_comments"] = value[:10000]

                ref["report"] = report

            if not any(r.get("report") for r in referees):
                full_text = rev_soup.get_text(separator="\n", strip=True)
                if len(full_text) > 100:
                    manuscript["reviews_page_text"] = full_text[:20000]
                    print(f"         📝 Reviews page saved as raw text ({len(full_text)} chars)")

            report_count = sum(1 for r in referees if r.get("report"))
            if report_count:
                print(f"         📝 Extracted {report_count} structured referee reports")

            self.driver.get(current_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

        except Exception as e:
            print(f"         ⚠️ Referee reports error: {str(e)[:60]}")
            try:
                self.driver.get(current_url)
                self.smart_wait(2)
            except Exception:
                pass

    def _scrape_status_details_page(
        self, manuscript: Dict, soup: BeautifulSoup
    ) -> Optional[BeautifulSoup]:
        try:
            href = None
            for a in soup.find_all("a", href=True):
                if "status_details" in a["href"]:
                    href = a["href"]
                    break
            if not href:
                return None

            current_url = self.driver.current_url
            self.driver.get(self._resolve_url(href))
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

            status_soup = BeautifulSoup(self.driver.page_source, "html.parser")
            self._save_debug_html(f"status_{manuscript['manuscript_id']}")

            self.driver.get(current_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)
            return status_soup
        except Exception as e:
            print(f"         ⚠️ Status details scrape error: {str(e)[:60]}")
            try:
                self.driver.get(current_url)
                self.smart_wait(2)
            except Exception:
                pass
            return None

    def _scrape_email_log_page(
        self, manuscript: Dict, soup: BeautifulSoup
    ) -> Optional[BeautifulSoup]:
        try:
            href = None
            for a in soup.find_all("a", href=True):
                if "view_email" in a["href"]:
                    href = a["href"]
                    break
            if not href:
                return None

            current_url = self.driver.current_url
            self.driver.get(self._resolve_url(href))
            self.smart_wait(2)
            self._wait_for_cloudflare(30)

            email_soup = BeautifulSoup(self.driver.page_source, "html.parser")
            self._save_debug_html(f"email_log_{manuscript['manuscript_id']}")

            self.driver.get(current_url)
            self.smart_wait(2)
            self._wait_for_cloudflare(30)
            return email_soup
        except Exception as e:
            print(f"         ⚠️ Email log scrape error: {str(e)[:60]}")
            try:
                self.driver.get(current_url)
                self.smart_wait(2)
            except Exception:
                pass
            return None

    def _build_audit_trail(
        self,
        manuscript: Dict,
        status_soup: Optional[BeautifulSoup] = None,
        email_soup: Optional[BeautifulSoup] = None,
    ):
        events = []
        ms_id = manuscript.get("manuscript_id", "")
        metadata = manuscript.get("metadata", {})

        def _make_event(
            date_str: str,
            event_type: str,
            description: str,
            etype: str = "status_change",
            from_email: str = "",
            to_email: str = "",
        ) -> Optional[Dict]:
            if not date_str:
                return None
            date_part = date_str.split()[0].split("T")[0]
            dt = None
            for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%m/%d/%Y"):
                try:
                    dt = datetime.strptime(date_part, fmt).replace(tzinfo=timezone.utc)
                    break
                except Exception:
                    continue
            if not dt:
                return None
            return {
                "date": dt.strftime("%Y-%m-%d"),
                "datetime": dt,
                "type": event_type,
                "event_type": etype,
                "description": description,
                "source": "siam_platform",
                "external": False,
                "from": from_email,
                "to": to_email,
                "manuscript_id": ms_id,
            }

        sub_date = metadata.get("submission_date", "")
        ev = _make_event(sub_date, "manuscript_submission", f"Manuscript {ms_id} submitted")
        if ev:
            events.append(ev)

        for ref in manuscript.get("referees", []):
            name = ref.get("name", "unknown")
            email = ref.get("email", "")

            cd = ref.get("contact_date", "")
            if cd:
                ev = _make_event(
                    cd,
                    "reviewer_invitation",
                    f"Reviewer {name} invited",
                    to_email=email,
                )
                if ev:
                    events.append(ev)

            status = ref.get("status", "").lower()
            if "decline" in status and cd:
                ev = _make_event(
                    cd,
                    "reviewer_declined",
                    f"Reviewer {name} declined",
                    from_email=email,
                )
                if ev:
                    events.append(ev)

            dd = ref.get("due_date", "")
            if dd:
                ev = _make_event(
                    dd,
                    "review_deadline_set",
                    f"Review deadline for {name}: {dd}",
                    to_email=email,
                )
                if ev:
                    events.append(ev)

            rd = ref.get("received_date", "")
            if rd:
                ev = _make_event(
                    rd,
                    "review_received",
                    f"Review received from {name}",
                    from_email=email,
                )
                if ev:
                    events.append(ev)

            report = ref.get("report", {})
            report_date = report.get("report_date", "")
            if report_date and report_date != rd:
                ev = _make_event(
                    report_date,
                    "review_submitted",
                    f"Report submitted by {name}",
                    from_email=email,
                )
                if ev:
                    events.append(ev)

            rec = report.get("recommendation", "")
            if rec and rd:
                ev = _make_event(
                    rd,
                    "recommendation_recorded",
                    f"{name} recommends: {rec}",
                    from_email=email,
                )
                if ev:
                    events.append(ev)

        for version in manuscript.get("version_history", []):
            vid = version.get("manuscript_id", "")
            vnum = version.get("version_number", "")
            ev = _make_event(
                sub_date,
                "revision_submitted",
                f"Version {vnum} ({vid}) available",
            )
            if ev:
                events.append(ev)

        if manuscript.get("decision_letter"):
            rev_num = metadata.get("revision_number", 0)
            ev = _make_event(
                sub_date,
                "decision_letter_sent",
                f"Decision letter sent for revision {rev_num}",
            )
            if ev:
                events.append(ev)

        if status_soup:
            self._parse_status_details_into_trail(events, status_soup, ms_id)

        if email_soup:
            self._parse_email_log_into_trail(events, email_soup, ms_id)

        seen_keys = set()
        unique_events = []
        for ev in events:
            key = f"{ev['date']}_{ev['type']}_{ev.get('from', '')}_{ev.get('to', '')}"
            if key not in seen_keys:
                seen_keys.add(key)
                unique_events.append(ev)

        unique_events.sort(key=lambda e: e.get("date", ""), reverse=True)
        for i, ev in enumerate(unique_events):
            ev["sequence"] = i + 1

        manuscript["audit_trail"] = unique_events
        if unique_events:
            print(f"         📋 Audit trail: {len(unique_events)} platform events synthesized")

    def _parse_status_details_into_trail(
        self, events: List, status_soup: BeautifulSoup, ms_id: str
    ):
        STAGE_TYPE_MAP = {
            "preliminary manuscript data submitted": "manuscript_submission",
            "author approved converted files": "author_approval",
            "initial qc started": "qc_started",
            "initial qc complete": "qc_complete",
            "waiting for corresponding editor assignment": "awaiting_editor",
            "corresponding editor assigned": "editor_assigned",
            "waiting for potential associate editor assignment": "awaiting_ae",
            "potential associate editor assigned": "ae_candidate_assigned",
            "associate editor assigned": "ae_assigned",
            "waiting for potential referee assignment": "awaiting_referee",
            "potential referees assigned": "referees_candidate_assigned",
            "contacting potential referees": "contacting_referees",
            "potential referees decline": "referees_declined",
            "all referees assigned": "all_referees_assigned",
            "review started": "review_started",
            "review complete": "review_complete",
            "awaiting ae recommendation": "awaiting_ae_recommendation",
            "awaiting ce decision": "awaiting_ce_decision",
            "awaiting admin processing": "awaiting_admin",
            "decision letter being prepared": "decision_preparation",
            "decision letter sent": "decision_sent",
            "revision submitted": "revision_submitted",
            "author revision started": "author_revision_started",
        }
        try:
            table = status_soup.find("table", class_="dump_history_table")
            if not table:
                return
            rows = table.find_all("tr")
            count = 0
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                stage = cells[0].get_text(strip=True)
                date_str = cells[1].get_text(strip=True)
                if not stage or not date_str:
                    continue
                stage_lower = stage.lower().strip()
                event_type = STAGE_TYPE_MAP.get(stage_lower, "stage_change")
                date_part = date_str.split()[0]
                dt = None
                for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%m/%d/%Y"):
                    try:
                        dt = datetime.strptime(date_part, fmt).replace(tzinfo=timezone.utc)
                        break
                    except Exception:
                        continue
                if not dt:
                    continue
                events.append(
                    {
                        "date": dt.strftime("%Y-%m-%d"),
                        "datetime": dt,
                        "type": event_type,
                        "event_type": "status_change",
                        "description": f"{stage}",
                        "source": "siam_platform",
                        "external": False,
                        "from": "",
                        "to": "",
                        "manuscript_id": ms_id,
                    }
                )
                count += 1
            if count:
                print(f"         📊 Status history: {count} stage transitions parsed")
        except Exception as e:
            print(f"         ⚠️ Status details parse error: {str(e)[:60]}")

    def _classify_siam_email(self, subject: str) -> str:
        s = subject.lower()
        if "request to review" in s:
            return "reviewer_invitation"
        if "referee accepts" in s:
            return "reviewer_accepted"
        if "potential referee declines" in s:
            return "reviewer_declined"
        if "follow-up to referee report received" in s:
            return "review_report_confirmation"
        if "review pending" in s and "third notice" in s:
            return "review_reminder_final"
        if "review pending" in s:
            return "review_reminder"
        if "overdue" in s:
            return "review_overdue"
        if "receipt of" in s:
            return "submission_receipt"
        if "assignment" in s and any(x in s for x in ("ce ", "ae ", "editor")):
            return "editor_assignment"
        if "revision received" in s or "revised manuscript" in s:
            return "revision_notification"
        if "review received" in s or "report received" in s:
            return "review_report_confirmation"
        if "review instruction" in s:
            return "review_instructions"
        if "follow-up message" in s:
            return "general_followup"
        return "platform_email"

    def _parse_email_log_into_trail(self, events: List, email_soup: BeautifulSoup, ms_id: str):
        try:
            table = email_soup.find("table", class_="view_email_table")
            if not table:
                return
            rows = table.find_all("tr")
            count = 0
            type_counts = {}
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) < 6:
                    continue
                date_str = cells[0].get_text(strip=True)
                triggered_by = cells[2].get_text(strip=True)
                to_cell = cells[4]
                to_parts = to_cell.get_text(separator="\n").strip().split("\n")
                to_name = to_parts[0].strip() if to_parts else ""
                to_email = to_parts[1].strip() if len(to_parts) > 1 else ""
                msg_link = cells[5].find("a")
                subject = (
                    msg_link.get_text(strip=True) if msg_link else cells[5].get_text(strip=True)
                )
                if not date_str:
                    continue
                dt = None
                for fmt in ("%Y-%m-%d  %H:%M", "%Y-%m-%d %H:%M"):
                    try:
                        dt = datetime.strptime(date_str.strip(), fmt).replace(tzinfo=timezone.utc)
                        break
                    except Exception:
                        continue
                if not dt:
                    date_part = date_str.split()[0]
                    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%m/%d/%Y"):
                        try:
                            dt = datetime.strptime(date_part, fmt).replace(tzinfo=timezone.utc)
                            break
                        except Exception:
                            continue
                if not dt:
                    continue
                email_type = self._classify_siam_email(subject)
                desc = subject if subject else f"Email to {to_name}"
                events.append(
                    {
                        "date": dt.strftime("%Y-%m-%d"),
                        "datetime": dt,
                        "type": email_type,
                        "event_type": "email",
                        "description": desc,
                        "source": "siam_platform",
                        "external": False,
                        "from": triggered_by,
                        "to": to_email or to_name,
                        "manuscript_id": ms_id,
                    }
                )
                type_counts[email_type] = type_counts.get(email_type, 0) + 1
                count += 1
            if count:
                classified = sum(v for k, v in type_counts.items() if k != "platform_email")
                print(
                    f"         📧 Email log: {count} platform emails parsed ({classified} classified)"
                )
        except Exception as e:
            print(f"         ⚠️ Email log parse error: {str(e)[:60]}")

    def _backfill_referee_dates_from_trail(self, manuscript: Dict):
        referees = manuscript.get("referees", [])
        audit = manuscript.get("audit_trail", [])
        if not referees or not audit:
            return

        invitation_events = sorted(
            [e for e in audit if e.get("type") == "reviewer_invitation"],
            key=lambda e: e.get("date", ""),
        )
        acceptance_events = sorted(
            [e for e in audit if e.get("type") == "reviewer_accepted"],
            key=lambda e: e.get("date", ""),
        )

        ref_by_email = {}
        for ref in referees:
            email = ref.get("email", "").lower()
            if email:
                ref_by_email[email] = ref
            sec = ref.get("secondary_email", "").lower()
            if sec:
                ref_by_email[sec] = ref

        def _match_ref_by_email_or_name(target_email):
            ref = ref_by_email.get(target_email)
            if ref:
                return ref
            if not target_email:
                return None
            local_part = target_email.split("@")[0].lower()
            for r in referees:
                name = r.get("name", "").lower()
                surname = name.split()[-1] if name.split() else ""
                if surname and len(surname) > 2 and surname in local_part:
                    ref_by_email[target_email] = r
                    return r
            return None

        for ev in invitation_events:
            to_email = ev.get("to", "").lower()
            ref = _match_ref_by_email_or_name(to_email)
            if ref and not ref.get("contact_date"):
                ref["contact_date"] = ev["date"]

        declined_names = {
            r.get("name", "").lower() for r in referees if r.get("status", "").lower() == "declined"
        }

        used_acceptances = set()
        for acc_ev in acceptance_events:
            acc_date = acc_ev.get("date", "")
            if not acc_date:
                continue
            best_ref = None
            best_inv_date = None
            for inv_ev in invitation_events:
                inv_to = inv_ev.get("to", "").lower()
                inv_date = inv_ev.get("date", "")
                ref = _match_ref_by_email_or_name(inv_to)
                if not ref:
                    continue
                if ref.get("name", "").lower() in declined_names:
                    continue
                if ref.get("acceptance_date"):
                    continue
                if ref.get("name", "") in used_acceptances:
                    continue
                if inv_date <= acc_date:
                    if best_inv_date is None or inv_date > best_inv_date:
                        best_ref = ref
                        best_inv_date = inv_date
            if best_ref:
                best_ref["acceptance_date"] = acc_date
                used_acceptances.add(best_ref.get("name", ""))

        backfilled = sum(
            1 for r in referees if r.get("contact_date") and r.get("section") == "active"
        )
        if backfilled:
            print(
                f"         📅 Backfilled dates: {backfilled} active referees got contact_date from email log"
            )

    def _populate_editors(self, manuscript: Dict):
        metadata = manuscript.get("metadata", {})
        editors = []
        generic_names = {"assigned", "n/a", "none", "tbd", "pending", ""}
        if metadata.get("associate_editor"):
            name = metadata["associate_editor"]
            if name.lower().strip() not in generic_names:
                editors.append({"name": name, "role": "associate_editor"})
        if metadata.get("corresponding_editor"):
            name = metadata["corresponding_editor"]
            if name.lower().strip() not in generic_names:
                editors.append({"name": name, "role": "corresponding_editor"})
        manuscript["editors"] = editors

    def _compute_peer_review_milestones(self, manuscript: Dict):
        milestones = {}
        metadata = manuscript.get("metadata", {})
        referees = manuscript.get("referees", [])

        sub_date_str = metadata.get("submission_date", "")
        sub_date = None
        if sub_date_str:
            date_part = sub_date_str.split()[0].split("T")[0]
            for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%m/%d/%Y"):
                try:
                    sub_date = datetime.strptime(date_part, fmt)
                    milestones["submission_date"] = sub_date.strftime("%Y-%m-%d")
                    break
                except Exception:
                    continue

        contact_dates = []
        received_dates = []
        due_dates = []
        active_referees = [r for r in referees if r.get("section") == "active"]

        for ref in referees:
            cd = ref.get("contact_date", "")
            if cd:
                try:
                    contact_dates.append(datetime.strptime(cd, "%Y-%m-%d"))
                except Exception:
                    pass

        for ref in active_referees:
            rd = ref.get("received_date", "")
            dd = ref.get("due_date", "")
            if rd:
                try:
                    received_dates.append(datetime.strptime(rd, "%Y-%m-%d"))
                except Exception:
                    pass
            if dd:
                try:
                    due_dates.append(datetime.strptime(dd, "%Y-%m-%d"))
                except Exception:
                    pass

        if contact_dates:
            latest = max(contact_dates)
            milestones["all_referees_assigned_date"] = latest.strftime("%Y-%m-%d")

        if received_dates:
            milestones["first_report_received_date"] = min(received_dates).strftime("%Y-%m-%d")
            milestones["last_report_received_date"] = max(received_dates).strftime("%Y-%m-%d")

        milestones["reports_received"] = len(received_dates)
        milestones["reports_pending"] = max(0, len(active_referees) - len(received_dates))
        milestones["all_reports_received"] = len(active_referees) > 0 and len(
            received_dates
        ) >= len(active_referees)

        now = datetime.now()
        if sub_date:
            milestones["days_since_submission"] = (now - sub_date).days
            if received_dates:
                milestones["days_in_review"] = (max(received_dates) - sub_date).days
            else:
                milestones["days_in_review"] = (now - sub_date).days

        turnarounds = []
        for ref in active_referees:
            rd = ref.get("received_date", "")
            cd = ref.get("contact_date", "")
            if rd and cd:
                try:
                    r = datetime.strptime(rd, "%Y-%m-%d")
                    c = datetime.strptime(cd, "%Y-%m-%d")
                    days = (r - c).days
                    if days > 0:
                        turnarounds.append(days)
                except Exception:
                    pass
            elif rd and sub_date:
                try:
                    r = datetime.strptime(rd, "%Y-%m-%d")
                    days = (r - sub_date).days
                    if days > 0:
                        turnarounds.append(days)
                except Exception:
                    pass

        if turnarounds:
            milestones["average_review_turnaround_days"] = round(
                sum(turnarounds) / len(turnarounds), 1
            )
            milestones["fastest_review_days"] = min(turnarounds)
            milestones["slowest_review_days"] = max(turnarounds)

        if due_dates:
            next_due = (
                min(d for d in due_dates if d > now) if any(d > now for d in due_dates) else None
            )
            if next_due:
                milestones["next_report_due"] = next_due.strftime("%Y-%m-%d")
                milestones["days_until_next_due"] = (next_due - now).days

        manuscript["peer_review_milestones"] = milestones

    def extract_timeline_analytics(self, manuscript: Dict) -> Dict:
        timeline = manuscript.get("communication_timeline") or manuscript.get("audit_trail", [])
        if not timeline:
            return {}

        analytics = {
            "total_events": len(timeline),
            "communication_span_days": 0,
            "unique_participants": 0,
            "referee_metrics": {},
            "communication_patterns": {},
            "response_time_analysis": {},
            "reminder_effectiveness": {},
        }

        event_dates = []
        parsed_dates = {}
        for idx, event in enumerate(timeline):
            date_str = event.get("date") or event.get("timestamp_gmt") or event.get("datetime")
            if date_str:
                try:
                    if "GMT" in str(date_str):
                        clean_date = str(date_str).replace(" GMT", "").replace(" EDT", "")
                        parsed_date = datetime.strptime(clean_date, "%d-%b-%Y %I:%M %p").replace(
                            tzinfo=timezone.utc
                        )
                    else:
                        parsed_date = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                        if parsed_date.tzinfo is None:
                            parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                    event_dates.append(parsed_date)
                    parsed_dates[idx] = parsed_date
                except Exception:
                    pass

        if event_dates:
            event_dates.sort()
            span = (event_dates[-1] - event_dates[0]).days
            analytics["communication_span_days"] = span

        participants = set()
        for event in timeline:
            for field in ("from_email", "from", "to"):
                val = event.get(field, "")
                if val and "@" in str(val):
                    participants.add(str(val).lower())
        analytics["unique_participants"] = len(participants)

        REMINDER_TYPES = {
            "review_reminder",
            "review_reminder_final",
            "review_overdue",
            "reminder",
            "deadline_reminder",
        }
        RESPONSE_TYPES = {
            "review_report_confirmation",
            "review_received",
            "review_submission",
            "review_submitted",
        }
        INVITATION_TYPES = {"reviewer_invitation", "referee_invited"}
        ACCEPTANCE_TYPES = {"reviewer_accepted", "reviewer_agreement", "referee_accepted"}

        referees = manuscript.get("referees", [])
        for referee in referees:
            email = referee.get("email")
            if not email:
                continue
            email_lower = email.lower()
            ref_name_lower = referee.get("name", "").lower()
            referee_events = [
                e
                for e in timeline
                if email_lower
                in (
                    e.get("to", "").lower()
                    + " "
                    + e.get("from", "").lower()
                    + " "
                    + e.get("from_email", "").lower()
                )
                or (
                    ref_name_lower
                    and ref_name_lower in str(e.get("description", e.get("subject", ""))).lower()
                )
            ]
            metrics = {
                "response_time_days": 0,
                "reliability_score": 50,
                "reminders_received": 0,
                "responses_sent": 0,
            }
            for ev in referee_events:
                ev_type = ev.get("type", "")
                ev_text = str(ev.get("description", ev.get("subject", ""))).lower()
                if ev_type in REMINDER_TYPES or (
                    ev_type == "platform_email"
                    and any(kw in ev_text for kw in ("reminder", "overdue", "pending"))
                ):
                    metrics["reminders_received"] += 1
                elif ev_type in RESPONSE_TYPES or (
                    ev_type == "platform_email"
                    and any(kw in ev_text for kw in ("submitted", "report received"))
                ):
                    metrics["responses_sent"] += 1
            if metrics["responses_sent"] > 0:
                score = 100 - (metrics["reminders_received"] * 20)
                metrics["reliability_score"] = max(0, min(100, score))
            analytics["referee_metrics"][email] = metrics

        if event_dates:
            weekday_counts = {}
            hour_counts = {}
            for date in event_dates:
                weekday = date.strftime("%A")
                hour = date.hour
                weekday_counts[weekday] = weekday_counts.get(weekday, 0) + 1
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            peak_weekday = (
                max(weekday_counts, key=weekday_counts.get) if weekday_counts else "Unknown"
            )
            peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 12
            analytics["communication_patterns"] = {
                "peak_weekday": peak_weekday,
                "peak_hour": f"{peak_hour}:00",
                "weekday_distribution": weekday_counts,
                "hour_distribution": {str(k): v for k, v in hour_counts.items()},
                "most_active_period": f"{peak_weekday} {peak_hour}:00",
            }

        invitation_events = [
            (idx, e)
            for idx, e in enumerate(timeline)
            if e.get("type") in INVITATION_TYPES
            or "invite" in str(e.get("description", e.get("subject", ""))).lower()
            or "request to review" in str(e.get("description", e.get("subject", ""))).lower()
        ]
        response_events = [
            (idx, e)
            for idx, e in enumerate(timeline)
            if e.get("type") in ACCEPTANCE_TYPES
            or "accept" in str(e.get("description", e.get("subject", ""))).lower()
            or "agree" in str(e.get("description", e.get("subject", ""))).lower()
        ]
        if invitation_events and response_events:
            response_times = []
            for inv_idx, inv in invitation_events:
                inv_date = parsed_dates.get(inv_idx)
                if inv_date:
                    later_responses = [
                        (ri, r)
                        for ri, r in response_events
                        if parsed_dates.get(ri) and parsed_dates[ri] > inv_date
                    ]
                    if later_responses:
                        earliest_ri, _ = min(later_responses, key=lambda x: parsed_dates[x[0]])
                        response_time = (parsed_dates[earliest_ri] - inv_date).days
                        response_times.append(response_time)
            if response_times:
                analytics["response_time_analysis"] = {
                    "average_response_days": round(sum(response_times) / len(response_times), 1),
                    "fastest_response_days": min(response_times),
                    "slowest_response_days": max(response_times),
                    "response_count": len(response_times),
                }

        reminder_events = [
            (idx, e)
            for idx, e in enumerate(timeline)
            if e.get("type") in REMINDER_TYPES
            or "reminder" in str(e.get("description", e.get("subject", ""))).lower()
            or "overdue" in str(e.get("description", e.get("subject", ""))).lower()
            or (
                "pending" in str(e.get("description", e.get("subject", ""))).lower()
                and e.get("event_type") == "email"
            )
        ]
        if reminder_events:
            effective_reminders = 0
            total_reminders = len(reminder_events)
            for rem_idx, reminder in reminder_events:
                reminder_date = parsed_dates.get(rem_idx)
                if reminder_date:
                    cutoff_date = reminder_date + timedelta(days=7)
                    responses_after = [
                        e
                        for ei, e in enumerate(timeline)
                        if parsed_dates.get(ei)
                        and reminder_date < parsed_dates[ei] <= cutoff_date
                        and (
                            e.get("type") in RESPONSE_TYPES
                            or e.get("type") in ACCEPTANCE_TYPES
                            or "submit" in str(e.get("description", e.get("subject", ""))).lower()
                        )
                    ]
                    if responses_after:
                        effective_reminders += 1
            analytics["reminder_effectiveness"] = {
                "total_reminders": total_reminders,
                "effective_reminders": effective_reminders,
                "effectiveness_rate": round(
                    effective_reminders / total_reminders if total_reminders > 0 else 0,
                    2,
                ),
            }

        print(
            f"      \U0001f4ca Timeline analytics: {analytics['total_events']} events, "
            f"{analytics['communication_span_days']} days span"
        )
        return analytics

    def _extract_authors_from_page(self, manuscript: Dict, page_text: str, soup: BeautifulSoup):
        authors = []
        author_labels = {
            "corresponding author",
            "contributing author",
            "contributing authors",
            "author",
            "authors",
        }

        for row in soup.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()
            if label not in author_labels:
                continue

            is_corresponding = "corresponding" in label

            for a_tag in td.find_all("a", href=True):
                href = a_tag["href"]
                link_text = a_tag.get_text(strip=True)
                if not link_text or len(link_text) < 2:
                    continue

                inst_match = re.match(r"(.+?)\s*\(([^)]+)\)\s*$", link_text)
                if inst_match:
                    name = inst_match.group(1).strip()
                    institution = inst_match.group(2).strip()
                else:
                    name = link_text.strip()
                    institution = ""

                if not name or len(name) < 2:
                    continue

                author = {"name": name}
                if institution:
                    author["institution"] = institution
                if is_corresponding:
                    author["role"] = "corresponding"
                if "biblio_dump" in href:
                    author["biblio_url"] = href

                has_orcid = a_tag.find_next("img", alt="orcid")
                if has_orcid:
                    author["has_orcid"] = True

                authors.append(author)

            if not td.find_all("a", href=True):
                author_text = td.get_text(strip=True)
                inst_match = re.match(r"(.+?)\s*\(([^)]+)\)\s*$", author_text)
                if inst_match:
                    name = inst_match.group(1).strip()
                    institution = inst_match.group(2).strip()
                    if name and len(name) > 2:
                        author = {"name": name, "institution": institution}
                        if is_corresponding:
                            author["role"] = "corresponding"
                        authors.append(author)
                else:
                    for name in re.split(r"[;,]\s*|\s+and\s+", author_text):
                        name = name.strip()
                        if name and len(name) > 2:
                            authors.append({"name": name})

        self._extract_suggested_reviewers(manuscript, soup)

        manuscript["authors"] = authors

    def _extract_documents(self, manuscript: Dict, soup: BeautifulSoup):
        ms_id = manuscript["manuscript_id"]
        documents = {"files": []}
        seen_urls = set()

        items_section = None
        for font_tag in soup.find_all("font", size="4"):
            if "manuscript items" in font_tag.get_text(strip=True).lower():
                items_section = font_tag.parent
                break

        if items_section:
            for li in items_section.find_all("li"):
                li_text = li.get_text(strip=True)
                pdf_links = li.find_all("a", href=re.compile(r"\.pdf|view_ms_obj", re.I))
                for link in pdf_links:
                    href = link.get("href", "")
                    link_text = link.get_text(strip=True)
                    if not href or href in seen_urls:
                        continue
                    if "Save File As" in link_text or not link_text:
                        continue
                    seen_urls.add(href)
                    if not href.startswith("http"):
                        href = f"{self.BASE_URL}/{href.lstrip('/')}"

                    doc_info = {"url": href, "description": li_text[:200]}

                    li_lower = li_text.lower()
                    if "article file" in li_lower:
                        doc_info["type"] = "manuscript"
                    elif "cover letter" in li_lower:
                        doc_info["type"] = "cover_letter"
                    elif "response to referee" in li_lower:
                        doc_info["type"] = "author_response"
                    elif "referee" in li_lower and (
                        "review" in li_lower or "attachment" in li_lower
                    ):
                        num_match = re.search(r"Referee\s*#?(\d+)", li_text, re.I)
                        doc_info["type"] = (
                            f"referee_report_{num_match.group(1)}"
                            if num_match
                            else "referee_report"
                        )
                    elif "source file" in li_lower or "supp" in li_lower:
                        doc_info["type"] = "supplementary"
                    else:
                        doc_info["type"] = "other"

                    size_match = re.search(r"\((\d+(?:KB|MB|kb|mb))\)", li_text)
                    if size_match:
                        doc_info["size"] = size_match.group(1)

                    if "PDF" in link_text:
                        documents["files"].append(doc_info)

        if not documents["files"]:
            doc_links = soup.find_all("a", href=re.compile(r"\.pdf", re.I))
            for link in doc_links:
                href = link.get("href", "")
                text = link.get_text(strip=True)
                if not href or href in seen_urls or not text:
                    continue
                if "_files/" not in href:
                    continue
                seen_urls.add(href)
                if not href.startswith("http"):
                    href = f"{self.BASE_URL}/{href.lstrip('/')}"
                doc_info = {"url": href, "type": "other", "description": text[:200]}
                if "art_file" in href:
                    doc_info["type"] = "manuscript"
                elif "cover_letter" in href:
                    doc_info["type"] = "cover_letter"
                elif "supp_data" in href:
                    doc_info["type"] = "supplementary"
                documents["files"].append(doc_info)

        for doc in documents["files"]:
            if doc["type"] in ("manuscript",) or doc["type"].startswith("referee_report"):
                downloaded = self._download_file_from_url(doc["url"], ms_id, doc["type"])
                if downloaded:
                    doc["local_path"] = downloaded

        manuscript["documents"] = documents

    def _detect_file_extension(self, content_type: str, url: str, content_start: bytes) -> str:
        if "pdf" in content_type or ".pdf" in url.lower():
            return ".pdf"
        if "officedocument.wordprocessingml" in content_type or ".docx" in url.lower():
            return ".docx"
        if "msword" in content_type or ".doc" in url.lower():
            return ".doc"
        if "html" in content_type:
            return ".html"
        if content_start.startswith(b"%PDF"):
            return ".pdf"
        if content_start[:4].startswith(b"PK"):
            return ".docx"
        return ".pdf"

    def _download_file_from_url(self, url: str, manuscript_id: str, doc_type: str) -> Optional[str]:
        existing = self._check_existing_download(manuscript_id, doc_type, str(self.download_dir))
        if existing:
            print(f"         \U0001f4e6 [CACHE] Already downloaded: {os.path.basename(existing)}")
            return existing

        try:
            self.driver.set_script_timeout(30)
            result = self.driver.execute_async_script(
                """
                var url = arguments[0];
                var done = arguments[1];
                fetch(url, {credentials: 'include'})
                    .then(function(r) {
                        if (!r.ok) throw new Error('HTTP ' + r.status);
                        return r.blob();
                    })
                    .then(function(blob) {
                        var reader = new FileReader();
                        reader.onload = function() {
                            done({
                                data: reader.result.split(',')[1],
                                type: blob.type,
                                size: blob.size
                            });
                        };
                        reader.readAsDataURL(blob);
                    })
                    .catch(function(e) { done({error: e.message}); });
            """,
                url,
            )

            if not result:
                return None
            if result.get("error"):
                print(f"            \u274c Fetch: {result['error']}")
                return None

            data = base64.b64decode(result["data"])
            content_type = result.get("type", "")
            file_size = len(data)

            if file_size < 50:
                return None

            ext = self._detect_file_extension(content_type, url, data[:100])
            filename = f"{manuscript_id}_{doc_type}{ext}"
            file_path = self.download_dir / filename

            if b"<html" in data[:200].lower() or b"<!doctype html" in data[:200].lower():
                html_text = data.decode("utf-8", errors="ignore")
                redirect_match = re.search(
                    r'location\.href\s*=\s*"([^"]+DOWNLOAD=TRUE[^"]*)"', html_text
                )
                if redirect_match:
                    redirect_url = redirect_match.group(1)
                    if not redirect_url.startswith("http"):
                        redirect_url = f"{self.BASE_URL}/{redirect_url.lstrip('/')}"
                    return self._download_file_from_url(redirect_url, manuscript_id, doc_type)
                return None

            with open(file_path, "wb") as f:
                f.write(data)

            print(f"            \u2705 Saved: {filename} ({file_size:,} bytes)")
            return str(file_path)

        except Exception as e:
            print(f"            \u274c Download error: {str(e)[:60]}")
            return None

    SESSION_DEATH_KEYWORDS = [
        "httpconnectionpool",
        "read timed out",
        "connection refused",
        "invalid session id",
        "no such window",
        "unable to connect",
        "target window already closed",
        "web view not found",
        "session not created",
        "chrome not reachable",
    ]

    def _is_session_dead(self) -> bool:
        if self._last_exception_msg:
            for kw in self.SESSION_DEATH_KEYWORDS:
                if kw in self._last_exception_msg:
                    self._last_exception_msg = ""
                    return True
        try:
            if not self.driver:
                return True
            self.driver.set_page_load_timeout(10)
            _ = self.driver.current_url
            self.driver.set_page_load_timeout(60)
            return False
        except Exception:
            return True

    def _recover_session(self) -> bool:
        print("      🔄 Session died, recovering...")
        self._last_exception_msg = ""
        try:
            self.cleanup_driver()
        except Exception:
            pass
        time.sleep(2)
        try:
            self.setup_driver()
            if not self.login_via_orcid():
                print("      ❌ Re-login failed")
                return False
            self.navigate_to_ae_dashboard()
            if not self._ensure_dashboard_loaded():
                print("      ❌ Dashboard not loaded after recovery")
                return False
            print("      ✅ Session recovered successfully")
            return True
        except Exception as e:
            print(f"      ❌ Session recovery failed: {str(e)[:100]}")
            return False

    def cleanup_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _enrich_people_from_web(self, manuscript_data: Dict):
        enrich_people_from_web(
            manuscript_data,
            get_cached_web_profile=self.get_cached_web_profile,
            save_web_profile=self.save_web_profile,
            platform_label="siam_metadata",
        )

    def _enrich_audit_trail_with_gmail(self, manuscript_data: Dict, manuscript_id: str):
        if not GMAIL_SEARCH_AVAILABLE:
            return

        referees = manuscript_data.get("referees", [])
        authors = manuscript_data.get("authors", [])

        referee_emails = [r.get("email") for r in referees if r.get("email")]
        author_emails = [a.get("email") for a in authors if a.get("email")]
        all_emails = list(set(referee_emails + author_emails))

        if not manuscript_id and not all_emails:
            return

        try:
            gmail = GmailSearchManager()
            if not gmail.initialize():
                print(f"      \u26a0\ufe0f Gmail service not available")
                return

            sub_date_str = manuscript_data.get("metadata", {}).get("submission_date", "")
            date_range = None
            if sub_date_str:
                for fmt in ["%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y"]:
                    try:
                        sub_date = datetime.strptime(sub_date_str.split()[0], fmt)
                        start_date = sub_date - timedelta(days=30)
                        end_date = datetime.now()
                        date_range = (start_date, end_date)
                        break
                    except Exception:
                        continue

            external_emails = gmail.search_manuscript_emails(
                manuscript_id=manuscript_id,
                referee_emails=all_emails,
                date_range=date_range,
            )

            if not external_emails:
                print(f"      \U0001f4e7 No external Gmail communications found")
                return

            audit_trail = manuscript_data.get("audit_trail", [])
            merged = gmail.merge_with_audit_trail(
                audit_trail=audit_trail,
                external_emails=external_emails,
                manuscript_id=manuscript_id,
            )

            for ev in merged:
                if not ev.get("external") and ev.get("source") == "mf_platform":
                    ev["source"] = "siam_platform"
            manuscript_data["communication_timeline"] = merged
            ext_count = len([e for e in merged if e.get("external")])
            manuscript_data["external_communications_count"] = ext_count
            print(
                f"      \U0001f4e7 Gmail enrichment: {ext_count} external emails merged into timeline"
            )

            self._backfill_author_emails_from_timeline(manuscript_data, merged)

        except Exception as e:
            print(f"      \u26a0\ufe0f Gmail search error: {str(e)[:60]}")

    def _backfill_author_emails_from_timeline(self, manuscript_data: Dict, timeline: List[Dict]):
        authors = manuscript_data.get("authors", [])
        authors_without_email = [a for a in authors if not a.get("email") and a.get("name")]
        if not authors_without_email:
            return

        timeline_emails = set()
        for event in timeline:
            for field in ("from_email", "from", "to"):
                val = str(event.get(field, ""))
                if "@" in val:
                    timeline_emails.add(val.lower().strip())

        referee_emails = {
            r.get("email", "").lower()
            for r in manuscript_data.get("referees", [])
            if r.get("email")
        }
        system_domains = {"siam.org", "info.siam.org", "siamjournal.com"}
        candidate_emails = {
            e
            for e in timeline_emails
            if e not in referee_emails and not any(e.endswith(f"@{d}") for d in system_domains)
        }

        backfilled = 0
        for author in authors_without_email:
            name = author.get("name", "")
            name_parts = name.lower().replace(",", " ").split()
            if not name_parts:
                continue
            surname = name_parts[0] if "," in name else name_parts[-1]
            for email in candidate_emails:
                if surname in email.split("@")[0]:
                    author["email"] = email
                    author["email_source"] = "gmail_backfill"
                    author["email_domain"] = email.split("@")[-1]
                    backfilled += 1
                    candidate_emails.discard(email)
                    break

        if backfilled:
            print(f"      📧 Backfilled {backfilled} author email(s) from Gmail timeline")

    def generate_summary(self, manuscripts: List[Dict]) -> Dict:
        total_referees = sum(len(m.get("referees", [])) for m in manuscripts)
        total_authors = sum(len(m.get("authors", [])) for m in manuscripts)
        total_docs = sum(len(m.get("documents", {}).get("files", [])) for m in manuscripts)
        referees_with_email = sum(
            1 for m in manuscripts for r in m.get("referees", []) if r.get("email")
        )
        enriched_count = sum(
            1
            for m in manuscripts
            for p in m.get("referees", []) + m.get("authors", [])
            if p.get("web_profile")
        )
        total_people = total_referees + total_authors

        return {
            "total_manuscripts": len(manuscripts),
            "total_referees": total_referees,
            "total_authors": total_authors,
            "total_documents": total_docs,
            "referee_email_rate": (
                f"{referees_with_email}/{total_referees}" if total_referees else "0/0"
            ),
            "enrichment_coverage": (f"{enriched_count}/{total_people}" if total_people else "0/0"),
        }

    def save_results(self, manuscripts: List[Dict]):
        if not manuscripts:
            print("\u26a0\ufe0f No manuscripts to save")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"{self.JOURNAL_CODE.lower()}_extraction_{timestamp}.json"

        summary = self.generate_summary(manuscripts)

        results = {
            "extraction_timestamp": datetime.now().isoformat(),
            "journal": self.JOURNAL_CODE,
            "journal_name": self.JOURNAL_NAME,
            "extractor_version": "2.0.0",
            "manuscripts": manuscripts,
            "summary": summary,
        }

        from core.output_schema import normalize_wrapper

        normalize_wrapper(results, self.JOURNAL_CODE)

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n\U0001f4be Results saved: {output_file}")
        print(f"\U0001f4ca Summary:")
        for k, v in summary.items():
            print(f"   {k}: {v}")

    def run(self) -> List[Dict]:
        print(f"\U0001f680 {self.JOURNAL_CODE} EXTRACTION \u2014 SIAM PLATFORM")
        print("=" * 60)

        try:
            self.setup_driver()

            if not self.login_via_orcid():
                print("\u274c ORCID login failed")
                return []

            self.navigate_to_ae_dashboard()

            categories = self.discover_categories()

            all_manuscript_infos = []
            all_seen = set()

            for ms_info in getattr(self, "_dashboard_manuscripts", []):
                ms_id = ms_info["manuscript_id"]
                if ms_id not in all_seen:
                    all_seen.add(ms_id)
                    all_manuscript_infos.append(ms_info)

            for cat in categories:
                if cat["name"].lower() in ("all pending manuscripts",):
                    continue

                if self._is_session_dead():
                    if not self._recover_session():
                        break

                manuscripts = self.collect_manuscript_ids(cat)
                for ms_info in manuscripts:
                    ms_id = ms_info["manuscript_id"]
                    if ms_id not in all_seen:
                        all_seen.add(ms_id)
                        all_manuscript_infos.append(ms_info)

            if not all_manuscript_infos:
                print("\u26a0\ufe0f No manuscripts found")
                self.save_results([])
                return []

            print(f"\n\U0001f4da Total unique manuscripts: {len(all_manuscript_infos)}")

            for ms_info in all_manuscript_infos:
                ms_id = ms_info["manuscript_id"]

                if self._is_session_dead():
                    if not self._recover_session():
                        break

                data = None
                try:
                    data = self.extract_manuscript_detail(ms_info)
                except Exception as e:
                    self._last_exception_msg = str(e).lower()
                    print(f"      ❌ Extraction failed for {ms_id}: {str(e)[:80]}")
                    if self._is_session_dead():
                        if not self._recover_session():
                            break

                if data:
                    try:
                        self._enrich_people_from_web(data)
                    except Exception as e:
                        print(f"      \u26a0\ufe0f Enrichment error: {str(e)[:60]}")
                    try:
                        self._enrich_audit_trail_with_gmail(data, ms_id)
                    except Exception as e:
                        print(f"      \u26a0\ufe0f Gmail error: {str(e)[:60]}")
                    try:
                        timeline_analytics = self.extract_timeline_analytics(data)
                        if timeline_analytics:
                            data["timeline_analytics"] = timeline_analytics
                    except Exception as e:
                        print(f"      \u26a0\ufe0f Timeline analytics error: {str(e)[:60]}")
                    self.manuscripts_data.append(data)

            self.save_results(self.manuscripts_data)
            return self.manuscripts_data

        except Exception as e:
            print(f"\u274c Extraction failed: {str(e)[:100]}")
            if self.manuscripts_data:
                self.save_results(self.manuscripts_data)
            return self.manuscripts_data
        finally:
            self.cleanup_driver()
