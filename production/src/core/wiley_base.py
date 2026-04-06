"""Wiley ScienceConnect (Research Exchange Review) base extractor.

Handles login via CONNECT SSO (ORCID), Cloudflare Turnstile bypass,
and extraction from the React/Ant Design SPA at review.wiley.com.
"""

import atexit
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import undetected_chromedriver as uc
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin
from core.web_enrichment import enrich_people_from_web

try:
    from core.gmail_search import GmailSearchManager  # noqa: F401

    GMAIL_SEARCH_AVAILABLE = True
except ImportError:
    GMAIL_SEARCH_AVAILABLE = False


class WileyBaseExtractor(CachedExtractorMixin):
    JOURNAL_CODE = ""
    JOURNAL_NAME = ""
    LOGIN_URL = "https://wiley.scienceconnect.io/login"
    DASHBOARD_URL = "https://review.wiley.com"
    CLOUDFLARE_WAIT = 300
    MANUSCRIPT_PATTERN = r"\d{7}"
    COOKIE_FILE = "wiley_cookies.json"

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.init_cached_extractor(self.JOURNAL_CODE)
        self.setup_directories()
        self.setup_chrome_options()
        self.driver = None
        self.wait = None
        self.original_window = None
        self.manuscripts_data = []

        self.email = (
            os.environ.get(f"{self.JOURNAL_CODE}_EMAIL")
            or os.environ.get("SICON_EMAIL")
            or os.environ.get("MF_EMAIL")
        )
        self.password = (
            os.environ.get(f"{self.JOURNAL_CODE}_PASSWORD")
            or os.environ.get("SICON_PASSWORD")
            or os.environ.get("MF_PASSWORD")
        )

        atexit.register(self.cleanup_driver)

    def setup_chrome_options(self):
        self.chrome_options = uc.ChromeOptions()
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
                ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
                capture_output=True,
                text=True,
            )
            ver = result.stdout.strip().split()[-1].split(".")[0]
            chrome_version = int(ver)
        except Exception:
            pass

        uc_binary = Path.home() / "Library/Application Support/undetected_chromedriver"
        uc_binary = uc_binary / "undetected_chromedriver"
        if uc_binary.exists():
            uc_binary.unlink()
            print("  Cleaned stale UC binary")

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
            try:
                subprocess.Popen(
                    [
                        "osascript",
                        "-e",
                        'tell application "System Events" to set visible of process "Google Chrome" to false',
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass
        time.sleep(5)
        for attempt in range(3):
            try:
                self.driver.set_page_load_timeout(120)
                self.driver.implicitly_wait(10)
                self.wait = WebDriverWait(self.driver, 30)
                self.original_window = self.driver.current_window_handle
                break
            except Exception:
                if attempt < 2:
                    print(f"   \u26a0\ufe0f Browser init attempt {attempt + 1} failed, retrying...")
                    time.sleep(5)
                else:
                    raise
        print(f"\U0001f5a5\ufe0f  Browser configured for {self.JOURNAL_CODE}")

    def cleanup_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _wait_for_cloudflare(self, timeout=None):
        timeout = timeout or self.CLOUDFLARE_WAIT
        prompted = False
        for i in range(timeout):
            try:
                title = self.driver.title.lower()
            except Exception:
                time.sleep(1)
                continue
            if "just a moment" in title or "un instant" in title or title == "":
                if i == 20 and not prompted:
                    self._prompt_cloudflare_click()
                    prompted = True
                if i % 30 == 0 and i > 0:
                    print(f"   \u23f3 Cloudflare challenge... ({i}s)")
                time.sleep(1)
                continue
            return True
        print(f"   \u26a0\ufe0f Cloudflare timeout after {timeout}s")
        return False

    def _prompt_cloudflare_click(self):
        import subprocess

        try:
            self.driver.set_window_position(200, 100)
            self.driver.set_window_size(800, 600)
        except Exception:
            pass
        try:
            subprocess.run(
                [
                    "osascript",
                    "-e",
                    'display notification "Click the Cloudflare checkbox in the Chrome window" '
                    'with title "Wiley Extractor" sound name "Glass"',
                ],
                check=False,
                timeout=5,
            )
        except Exception:
            pass
        print("   \U0001f446 Please click the Cloudflare 'Verify you are human' checkbox")
        print("      (browser window brought to foreground)")

    def _save_cookies(self):
        cookie_path = self.cache_dir_path / self.COOKIE_FILE
        try:
            cookies = self.driver.get_cookies()
            with open(cookie_path, "w") as f:
                json.dump(cookies, f)
        except Exception:
            pass

    def _restore_cookies(self):
        cookie_path = self.cache_dir_path / self.COOKIE_FILE
        if not cookie_path.exists():
            return False
        try:
            with open(cookie_path) as f:
                cookies = json.load(f)
            self.driver.get(self.DASHBOARD_URL)
            time.sleep(2)
            for cookie in cookies:
                cookie.pop("sameSite", None)
                cookie.pop("expiry", None)
                try:
                    self.driver.add_cookie(cookie)
                except Exception:
                    pass
            return True
        except Exception:
            return False

    def _wait_for_element(self, by, value, timeout=30):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def _wait_for_clickable(self, by, value, timeout=30):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
        except TimeoutException:
            return None

    def _safe_click(self, element):
        if not element:
            return False
        try:
            element.click()
            return True
        except Exception:
            try:
                self.driver.execute_script("arguments[0].click();", element)
                return True
            except Exception:
                return False

    def _dismiss_cookie_banners(self):
        try:
            self.driver.execute_script(
                """
                // OneTrust (ORCID uses this)
                var ot = document.getElementById('onetrust-accept-btn-handler');
                if (ot) { ot.click(); return; }
                // Generic cookie-policy overlays
                var overlay = document.getElementById('cookie-policy-layer-bg');
                if (overlay) overlay.remove();
                var layer = document.getElementById('cookie-policy-layer');
                if (layer) layer.remove();
                // Reject all / accept all buttons
                var btns = document.querySelectorAll(
                    'button[id*="accept"], button[id*="reject"], button[class*="cookie"], ' +
                    'button[class*="consent"], a[id*="cookie"], .cc-dismiss'
                );
                for (var i = 0; i < btns.length; i++) {
                    var t = btns[i].textContent.toLowerCase();
                    if (t.indexOf('reject') >= 0 || t.indexOf('decline') >= 0 || t.indexOf('deny') >= 0) {
                        btns[i].click(); return;
                    }
                }
                for (var i = 0; i < btns.length; i++) {
                    var t = btns[i].textContent.toLowerCase();
                    if (t.indexOf('accept') >= 0 || t.indexOf('agree') >= 0 || t.indexOf('ok') >= 0) {
                        btns[i].click(); return;
                    }
                }
            """
            )
        except Exception:
            pass

    def _is_session_dead(self):
        try:
            _ = self.driver.title
            return False
        except Exception:
            return True

    # ── Login ──────────────────────────────────────────────────────────────

    def login(self) -> bool:
        print("\n\U0001f510 Logging in to Wiley ScienceConnect...")

        if self._restore_cookies():
            self.driver.get(self.DASHBOARD_URL)
            if self._wait_for_cloudflare():
                if self._ensure_dashboard_loaded():
                    print("   \u2705 Restored session from cookies")
                    return True

        self.driver.get(self.LOGIN_URL)
        if not self._wait_for_cloudflare():
            print("   \u274c Cloudflare blocked on login page")
            return False

        print("   \u2705 Login page loaded")
        time.sleep(2)

        orcid_btn = self._wait_for_clickable(
            By.CSS_SELECTOR, 'button[aria-label="ORCID button"]', timeout=15
        )
        if not orcid_btn:
            print("   \u274c ORCID button not found")
            return False

        self._safe_click(orcid_btn)
        print("   \U0001f517 Clicked ORCID login")
        time.sleep(3)

        if not self._wait_for_cloudflare(timeout=60):
            print("   \u274c Cloudflare blocked on ORCID redirect")
            return False

        if not self._fill_orcid_credentials():
            return False

        if not self._wait_for_dashboard_redirect():
            return False

        self._save_cookies()
        print("   \u2705 Logged in successfully")
        return True

    def _fill_orcid_credentials(self) -> bool:
        if "orcid.org" not in self.driver.current_url:
            for _ in range(30):
                time.sleep(1)
                if "orcid.org" in self.driver.current_url:
                    break
            else:
                current = self.driver.current_url
                if "review.wiley.com" in current:
                    print("   \u2705 Already authenticated (ORCID session active)")
                    return True
                print(f"   \u274c Did not reach ORCID login. URL: {current}")
                return False

        time.sleep(2)
        self._dismiss_cookie_banners()
        print("   \U0001f4dd Filling ORCID credentials...")

        username_field = self._wait_for_element(By.ID, "username-input", timeout=15)
        if not username_field:
            username_field = self._wait_for_element(By.ID, "username", timeout=5)
        if not username_field:
            if "review.wiley.com" in self.driver.current_url:
                return True
            print("   \u274c ORCID username field not found")
            return False

        username_field.clear()
        username_field.send_keys(self.email)

        password_field = self._wait_for_element(By.ID, "password", timeout=5)
        if not password_field:
            print("   \u274c ORCID password field not found")
            return False

        password_field.clear()
        password_field.send_keys(self.password)

        signin_btn = self._wait_for_clickable(By.ID, "signin-button", timeout=5)
        if not signin_btn:
            print("   \u274c ORCID sign-in button not found")
            return False

        self._safe_click(signin_btn)
        print("   \U0001f511 ORCID credentials submitted")

        for wait_i in range(60):
            time.sleep(2)
            url = self.driver.current_url
            if "review.wiley.com" in url:
                print("   \u2705 ORCID redirect to dashboard")
                return True
            if "scienceconnect.io" in url and "orcid" not in url:
                print("   \u2705 ORCID redirect to ScienceConnect")
                return True
            if "orcid.org" in url and "/signin" not in url and "/oauth" not in url:
                break
            if wait_i == 5:
                try:
                    error_el = self.driver.find_element(
                        By.CSS_SELECTOR, ".alert-error, .orcid-error, #orcid-errors, .mat-error"
                    )
                    err_text = error_el.text.strip()
                    if err_text:
                        print(f"   \u274c ORCID error: {err_text[:100]}")
                        return False
                except NoSuchElementException:
                    pass
            if wait_i == 10:
                print(f"   \u23f3 Waiting for ORCID redirect... (URL: {url[:80]})")

        authorize_btn = self._wait_for_clickable(By.ID, "authorize", timeout=10)
        if authorize_btn:
            self._safe_click(authorize_btn)
            print("   \u2705 Authorization granted")
            time.sleep(3)

        for _ in range(30):
            time.sleep(2)
            url = self.driver.current_url
            if "review.wiley.com" in url:
                return True
            if "scienceconnect.io" in url and "orcid" not in url:
                return True

        print(f"   \u26a0\ufe0f Still on ORCID after submit. URL: {self.driver.current_url}")
        return True

    def _wait_for_dashboard_redirect(self, timeout=120) -> bool:
        for _ in range(timeout):
            try:
                url = self.driver.current_url
            except Exception:
                time.sleep(1)
                continue
            if "review.wiley.com" in url:
                if self._wait_for_cloudflare(timeout=60):
                    if self._ensure_dashboard_loaded():
                        return True
                return False
            if "wiley.scienceconnect.io" in url and "/login" not in url:
                print("   \U0001f517 Redirected to ScienceConnect, navigating to dashboard...")
                time.sleep(2)
                self.driver.get(self.DASHBOARD_URL)
                if self._wait_for_cloudflare(timeout=120):
                    return self._ensure_dashboard_loaded()
                return False
            time.sleep(1)
        print(f"   \u274c Dashboard redirect timeout. URL: {self.driver.current_url}")
        return False

    def _ensure_dashboard_loaded(self) -> bool:
        el = self._wait_for_element(
            By.CSS_SELECTOR, '[data-test-id="dashboard-list-items"]', timeout=20
        )
        return el is not None

    # ── Manuscript Collection ──────────────────────────────────────────────

    def collect_manuscript_ids(self) -> list[dict]:
        print("\n\U0001f4cb Collecting manuscripts from dashboard...")

        all_btn = self._wait_for_clickable(
            By.CSS_SELECTOR, '[data-test-id="bin-radio-all"]', timeout=10
        )
        if all_btn:
            self._safe_click(all_btn)
            time.sleep(3)

        manuscripts = []
        cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-test-id^="manuscript-card"]')
        for card in cards:
            try:
                tid = card.get_attribute("data-test-id") or ""
                ms_id = tid.replace("manuscript-card", "")
                if not ms_id:
                    continue
                title_el = card.find_element(By.CSS_SELECTOR, '[data-test-id="manuscript-title"]')
                link = title_el.find_element(By.XPATH, "./ancestor::a")
                href = link.get_attribute("href") or ""
                title = title_el.text.strip()

                status_el = card.find_element(By.CSS_SELECTOR, '[data-test-id="manuscript-status"]')
                status = status_el.text.strip() if status_el else ""

                manuscripts.append(
                    {
                        "manuscript_id": ms_id,
                        "title": title,
                        "status": status,
                        "href": href,
                    }
                )
            except Exception:
                continue

        print(f"   Found {len(manuscripts)} manuscript(s)")
        return manuscripts

    # ── Manuscript Detail Extraction ───────────────────────────────────────

    def extract_manuscript_detail(self, ms_info: dict) -> dict:
        ms_id = ms_info["manuscript_id"]
        href = ms_info.get("href", "")
        if not href:
            return {}

        print(f"\n\U0001f50d Extracting {ms_id}...")
        self.driver.get(href)
        time.sleep(3)

        if not self._wait_for_element(
            By.CSS_SELECTOR, '[data-test-id="manuscript-id"]', timeout=20
        ):
            print(f"   \u274c Detail page failed to load for {ms_id}")
            return {}

        time.sleep(2)
        data = {
            "manuscript_id": ms_id,
            "extraction_timestamp": datetime.now().isoformat(),
        }

        data.update(self._extract_metadata())
        data["authors"] = self._extract_authors()
        data["editors"] = self._extract_editors()
        data["referees"] = self._extract_referees()
        data["documents"] = self._extract_files()

        return data

    def _extract_metadata(self) -> dict:
        def _text(selector):
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                return el.text.strip()
            except NoSuchElementException:
                return ""

        ms_id_raw = _text('[data-test-id="manuscript-id"]')
        ms_id = re.sub(r"^ID\s*", "", ms_id_raw).strip()

        keywords_raw = _text('[data-test-id="manuscript-keywords"]')
        keywords = [k.strip() for k in keywords_raw.split(";") if k.strip()] if keywords_raw else []

        return {
            "manuscript_id": ms_id,
            "title": _text('[data-test-id="manuscript-title"]'),
            "status": _text('[data-test-id="manuscript-status"]'),
            "article_type": _text('[data-test-id="article-type"]'),
            "keywords": keywords,
            "metadata": {
                "journal": _text('[data-test-id="journal-title"]'),
                "version": _text('[data-test-id="manuscript-current-version"]'),
            },
        }

    def _extract_authors(self) -> list[dict]:
        authors = []
        els = self.driver.find_elements(By.CSS_SELECTOR, '[data-test-id^="author-name-"]')
        for el in els:
            tid = el.get_attribute("data-test-id") or ""
            email = tid.replace("author-name-", "")
            name = el.text.strip()
            if name and email:
                authors.append({"name": name, "email": email})
        return authors

    def _extract_editors(self) -> list[dict]:
        editors = []
        els = self.driver.find_elements(By.CSS_SELECTOR, '[data-test-id^="editor-label-"]')
        for el in els:
            tid = el.get_attribute("data-test-id") or ""
            email = tid.replace("editor-label-", "")
            text = el.text.strip()
            role = ""
            name = text
            if ":" in text:
                role, name = text.split(":", 1)
                role = role.strip()
                name = name.strip()
            editors.append({"name": name, "email": email, "role": role})
        return editors

    def _extract_referees(self) -> list[dict]:
        expand_btns = self.driver.find_elements(
            By.CSS_SELECTOR, '[data-test-id="more-details-button"]'
        )
        for btn in expand_btns:
            try:
                self._safe_click(btn)
                time.sleep(0.5)
            except Exception:
                pass
        time.sleep(1)

        referees = []
        cards = self.driver.find_elements(
            By.CSS_SELECTOR, '[data-test-id="reviewer-invitation-log-card"]'
        )
        for card in cards:
            ref = self._extract_single_referee(card)
            if ref:
                referees.append(ref)

        print(f"   \U0001f465 {len(referees)} referee(s) extracted")
        return referees

    def _extract_single_referee(self, card) -> dict:
        try:
            name_el = card.find_element(By.CSS_SELECTOR, '[data-test-id*="reviewer-name-"]')
            name = name_el.text.strip()
            name_tid = name_el.get_attribute("data-test-id") or ""
        except NoSuchElementException:
            return {}

        source = "unknown"
        for prefix in ("reviewerInvitedManually-", "reviewerSuggestions-", "reviewerSearch-"):
            if prefix in name_tid:
                source = prefix.rstrip("-").replace("reviewer", "").lower()
                break

        try:
            email = card.find_element(
                By.CSS_SELECTOR, '[data-test-id="reviewer-email"]'
            ).text.strip()
        except NoSuchElementException:
            email = ""

        try:
            aff_el = card.find_element(By.CSS_SELECTOR, '[data-test-id^="aff-"]')
            institution = aff_el.text.strip()
        except NoSuchElementException:
            institution = ""

        try:
            status = card.find_element(
                By.CSS_SELECTOR, '[data-test-id="reviewer-card-status"]'
            ).text.strip()
        except NoSuchElementException:
            status = ""

        try:
            kw_el = card.find_element(By.CSS_SELECTOR, '[data-test-id="footer-keywords-list"]')
            kw_text = kw_el.text.strip()
        except NoSuchElementException:
            kw_text = ""

        dates = self._extract_referee_dates(card)

        canonical_status = self._map_status(status)

        ref = {
            "name": name,
            "email": email,
            "institution": institution,
            "status": canonical_status,
            "dates": {
                "invited": dates.get("invited"),
                "agreed": dates.get("accepted"),
                "due": dates.get("due"),
                "returned": dates.get("submitted"),
            },
            "platform_specific": {
                "wiley_status": status,
                "source": source,
                "invited_date": dates.get("invited"),
                "accepted_date": dates.get("accepted"),
                "expired_date": dates.get("expired"),
                "due_date": dates.get("due"),
                "submitted_date": dates.get("submitted"),
            },
        }

        if kw_text and "no keywords" not in kw_text.lower():
            topics = [k.strip() for k in kw_text.split(";") if k.strip()]
            ref["web_profile"] = {"research_topics": topics}

        return ref

    def _extract_referee_dates(self, card) -> dict:
        dates = {}
        date_pattern = re.compile(
            r"^(Invited|Accepted|Declined|Expired|Submitted|Due)\s*:\s*(.+)", re.IGNORECASE
        )
        divs = card.find_elements(By.TAG_NAME, "div")
        for div in divs:
            text = div.text.strip()
            if len(text) > 80 or not text:
                continue
            m = date_pattern.match(text)
            if m:
                key = m.group(1).lower()
                raw_date = m.group(2).strip()
                normalized = self._parse_wiley_date(raw_date)
                if normalized and key not in dates:
                    dates[key] = normalized
        return dates

    @staticmethod
    def _parse_wiley_date(text: str) -> str:
        if not text:
            return ""
        text = text.strip()
        for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return ""

    @staticmethod
    def _map_status(wiley_status: str) -> str:
        s = wiley_status.lower()
        if "accepted" in s:
            return "Agreed"
        if "pending" in s:
            return "Invited"
        if "declined" in s:
            return "Declined"
        if "expired" in s:
            return "No Response"
        if "revoked" in s:
            return "Terminated"
        if "submitted" in s or "complete" in s:
            return "Report Submitted"
        return wiley_status

    def _extract_files(self) -> dict:
        files = []
        try:
            collapse = self.driver.find_element(
                By.CSS_SELECTOR, '[data-test-id="files-collapsible"]'
            )
            header = collapse.find_element(By.CSS_SELECTOR, ".ant-collapse-header")
            self._safe_click(header)
            time.sleep(1)

            items = collapse.find_elements(By.CSS_SELECTOR, "span")
            current_name = ""
            for item in items:
                text = item.text.strip()
                if not text or text == "Files":
                    continue
                if "MB" in text or "KB" in text:
                    files.append({"filename": current_name, "size": text})
                elif len(text) > 3:
                    current_name = text
        except NoSuchElementException:
            pass
        return {"files": files}

    # ── Web Enrichment ─────────────────────────────────────────────────────

    def _enrich_people_from_web(self, data: dict):
        try:
            enrich_people_from_web(data, self.JOURNAL_CODE, cache=self._cache)
        except Exception as e:
            print(f"   \u26a0\ufe0f Enrichment failed: {e}")

    # ── Orchestration ──────────────────────────────────────────────────────

    def run(self) -> list[dict]:
        try:
            self.setup_driver()

            if not self.login():
                print("\u274c Login failed")
                return []

            manuscripts = self.collect_manuscript_ids()
            if not manuscripts:
                print("\u274c No manuscripts found")
                return []

            for ms_info in manuscripts:
                if self._is_session_dead():
                    print("   \u26a0\ufe0f Session died, attempting recovery...")
                    if not self.login():
                        break

                data = self.extract_manuscript_detail(ms_info)
                if data:
                    self._enrich_people_from_web(data)
                    self.manuscripts_data.append(data)

            if self.manuscripts_data:
                self.save_results(self.manuscripts_data)

            return self.manuscripts_data

        except KeyboardInterrupt:
            print("\n\u26a0\ufe0f Interrupted")
            if self.manuscripts_data:
                self.save_results(self.manuscripts_data)
            return self.manuscripts_data
        finally:
            self.cleanup_driver()

    def save_results(self, manuscripts: list[dict]):
        from core.output_schema import normalize_wrapper

        results = {
            "extraction_timestamp": datetime.now().isoformat(),
            "journal": self.JOURNAL_CODE,
            "journal_name": self.JOURNAL_NAME,
            "extractor_version": "1.0.0",
            "manuscripts": manuscripts,
            "summary": {
                "total": len(manuscripts),
                "statuses": {},
            },
        }

        for ms in manuscripts:
            status = ms.get("status", "Unknown")
            results["summary"]["statuses"][status] = (
                results["summary"]["statuses"].get(status, 0) + 1
            )

        normalize_wrapper(results, self.JOURNAL_CODE)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        jc = self.JOURNAL_CODE.lower()
        output_file = self.output_dir / f"{jc}_extraction_{ts}.json"
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n\U0001f4be Saved: {output_file}")
        print(f"   {len(manuscripts)} manuscript(s), schema v{results.get('schema_version', '?')}")

    def generate_summary(self, manuscripts: list[dict]) -> dict:
        statuses = {}
        for ms in manuscripts:
            s = ms.get("status", "Unknown")
            statuses[s] = statuses.get(s, 0) + 1
        return {"total": len(manuscripts), "statuses": statuses}
