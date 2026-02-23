#!/usr/bin/env python3
"""
ScholarOne Base Extractor
=========================

Shared base class for ScholarOne (Manuscript Central) extractors.
MF and MOR both inherit from this class and override only journal-specific logic.
"""

import os
import sys
import time
import json
import re
import requests
import random
import atexit
from pathlib import Path
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Dict, List, Optional, Any, Tuple, Callable
from urllib.parse import quote_plus

from core.web_enrichment import enrich_people_from_web

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)

try:
    from bs4 import BeautifulSoup
except ImportError:
    os.system("pip install beautifulsoup4")
    from bs4 import BeautifulSoup

sys.path.append(str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin
from core.scholarone_utils import (
    with_retry,
    safe_click as _safe_click,
    safe_get_text as _safe_get_text,
    safe_array_access as _safe_array_access,
    safe_int as _safe_int,
    smart_wait as _smart_wait,
    parse_date,
    parse_ev_date,
    capture_page as _capture_page_fn,
)

try:
    from core.orcid_lookup import ORCIDLookup
except ImportError:
    ORCIDLookup = None

try:
    from core.gmail_search import GmailSearchManager

    GMAIL_SEARCH_AVAILABLE = True
except ImportError:
    GMAIL_SEARCH_AVAILABLE = False

from core.gmail_verification_wrapper import fetch_latest_verification_code


class ScholarOneBaseExtractor(CachedExtractorMixin):
    """Base class for ScholarOne platform extractors.

    Subclasses MUST set these class-level attributes:
        JOURNAL_CODE: str          e.g. "MF", "MOR"
        JOURNAL_NAME: str          e.g. "Mathematical Finance"
        LOGIN_URL: str             e.g. "https://mc.manuscriptcentral.com/mafi"
        EMAIL_ENV_VAR: str         e.g. "MF_EMAIL"
        PASSWORD_ENV_VAR: str      e.g. "MF_PASSWORD"
    """

    JOURNAL_CODE: str = ""
    JOURNAL_NAME: str = ""
    LOGIN_URL: str = ""
    EMAIL_ENV_VAR: str = ""
    PASSWORD_ENV_VAR: str = ""

    def __init__(
        self,
        use_cache: bool = True,
        cache_ttl_hours: int = 24,
        max_manuscripts_per_category: int = None,
        headless: bool = True,
        capture_html: bool = False,
    ):
        self.use_cache = use_cache
        self.cache_ttl_hours = cache_ttl_hours
        self.max_manuscripts_per_category = max_manuscripts_per_category
        self.headless = headless
        self.capture_html = capture_html
        self._current_manuscript_id = ""

        if self.use_cache:
            self.init_cached_extractor(self.JOURNAL_CODE)

        self.setup_chrome_options()
        self.setup_directories()
        self.driver = None
        self.wait = None
        self.original_window = None
        self.service = None
        self.manuscripts_data = []

        atexit.register(self.cleanup_driver)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def setup_chrome_options(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option("useAutomationExtension", False)
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")

        if self.headless:
            self.chrome_options.add_argument("--headless=new")
            self.chrome_options.add_argument("--disable-gpu")
            self.chrome_options.add_argument(
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )

        self.chrome_options.add_argument("--window-size=800,600")

        download_dir = str(
            Path(__file__).parent.parent.parent / "downloads" / self.JOURNAL_CODE.lower()
        )
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
        }
        self.chrome_options.add_experimental_option("prefs", prefs)

    def setup_directories(self):
        self.base_dir = Path(__file__).parent.parent.parent
        jc = self.JOURNAL_CODE.lower()
        self.download_dir = self.base_dir / "downloads" / jc
        self.output_dir = self.base_dir / "outputs" / jc
        self.log_dir = self.base_dir / "logs" / jc
        self.cache_dir = self.base_dir / "cache" / jc

        for directory in [self.download_dir, self.output_dir, self.log_dir, self.cache_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def setup_driver(self):
        try:
            from webdriver_manager.chrome import ChromeDriverManager

            self.service = Service(ChromeDriverManager().install())
        except ImportError:
            self.service = Service()
        self.driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
        )
        self.driver.set_page_load_timeout(45)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 20)
        self.original_window = self.driver.current_window_handle

    # ------------------------------------------------------------------
    # Utility wrappers (delegate to module-level utils)
    # ------------------------------------------------------------------

    def _capture_page(self, page_type, manuscript_id="", is_popup=False):
        if not self.capture_html:
            return
        _capture_page_fn(self.driver, self.JOURNAL_CODE, page_type, manuscript_id, is_popup)

    def safe_click(self, element) -> bool:
        return _safe_click(self.driver, element)

    def safe_get_text(self, element) -> str:
        return _safe_get_text(element)

    def safe_array_access(self, array: list, index: int, default=None):
        return _safe_array_access(array, index, default)

    def safe_int(self, value, default=0):
        return _safe_int(value, default)

    def smart_wait(self, seconds: float = 1.0):
        _smart_wait(seconds)

    def wait_for_element(self, by, value, timeout=10):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except (TimeoutException, WebDriverException):
            return None

    # ------------------------------------------------------------------
    # Session management (IDENTICAL in MF and MOR)
    # ------------------------------------------------------------------

    def _is_session_dead(self) -> bool:
        try:
            if not self.driver:
                return True
            self.driver.set_page_load_timeout(10)
            _ = self.driver.current_url
            self.driver.set_page_load_timeout(45)
            return False
        except Exception:
            return True

    def _recover_session(self) -> bool:
        print("      🔄 Session died, recovering...")
        try:
            self.cleanup_driver()
        except Exception:
            pass
        time.sleep(2)
        try:
            self.setup_driver()
            if not self.login():
                print("      ❌ Re-login failed")
                return False
            if not self.navigate_to_ae_center():
                print("      ❌ Could not reach AE Center after recovery")
                return False
            print("      ✅ Session recovered successfully")
            return True
        except Exception as e:
            print(f"      ❌ Session recovery failed: {str(e)[:100]}")
            return False

    def is_session_alive(self) -> bool:
        try:
            _ = self.driver.current_url
            return True
        except Exception as e:
            error_str = str(e).lower()
            if any(
                x in error_str
                for x in [
                    "connection refused",
                    "invalid session",
                    "no such window",
                    "chrome not reachable",
                ]
            ):
                print(f"         ❌ ChromeDriver session died: {str(e)[:80]}")
                return False
            return True

    def cleanup_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
        if self.service:
            try:
                service_pid = self.service.process.pid if self.service.process else None
                if service_pid:
                    import subprocess

                    try:
                        subprocess.run(
                            ["kill", "-9", str(service_pid)], capture_output=True, timeout=2
                        )
                    except Exception:
                        pass
            except Exception:
                pass
            self.service = None

    # ------------------------------------------------------------------
    # Login & Navigation
    # ------------------------------------------------------------------

    @with_retry(max_attempts=3, delay=2.0)
    def login(self) -> bool:
        try:
            print(f"🔐 Logging in to {self.JOURNAL_CODE}...")

            self.driver.get(self.LOGIN_URL)
            self.smart_wait(5)

            try:
                reject_btn = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))
                )
                self.safe_click(reject_btn)
                self.smart_wait(2)
            except TimeoutException:
                pass

            userid_field = self.wait.until(EC.presence_of_element_located((By.ID, "USERID")))
            userid_field.clear()
            userid_field.send_keys(os.getenv(self.EMAIL_ENV_VAR))

            password_field = self.driver.find_element(By.ID, "PASSWORD")
            password_field.clear()
            password_field.send_keys(os.getenv(self.PASSWORD_ENV_VAR))

            login_btn = self.driver.find_element(By.ID, "logInButton")
            self.safe_click(login_btn)
            self.smart_wait(3)

            try:
                wait_short = WebDriverWait(self.driver, 5)
                token_field = wait_short.until(EC.element_to_be_clickable((By.ID, "TOKEN_VALUE")))
                print("   🔑 2FA required, fetching code...")

                login_time = time.time()
                self.smart_wait(2)

                code = None
                try:
                    code = fetch_latest_verification_code(
                        self.JOURNAL_CODE, max_wait=30, poll_interval=2, start_timestamp=login_time
                    )
                except Exception as e:
                    print(f"   ⚠️ Gmail API not available: {e}")

                if not code:
                    print("   📱 Please enter the 6-digit 2FA code from your email:")
                    try:
                        code = input("   Code: ").strip()
                        if not code or len(code) != 6:
                            print("   ❌ Invalid code format")
                            return False
                    except (EOFError, KeyboardInterrupt):
                        print("   ❌ No code entered")
                        return False

                if code:
                    print(f"   ✅ Entering 2FA code...")
                    token_field.clear()
                    token_field.send_keys(code)
                    verify_btn = self.driver.find_element(By.ID, "VERIFY_BTN")
                    self.safe_click(verify_btn)
                    self.smart_wait(10)
                else:
                    print("   ❌ No 2FA code received")
                    return False
            except TimeoutException:
                pass

            try:
                wait_success = WebDriverWait(self.driver, 15)
                wait_success.until(
                    EC.presence_of_element_located((By.LINK_TEXT, "Associate Editor Center"))
                )
                print("✅ Login successful!")
                return True
            except TimeoutException:
                print("   ❌ Login verification failed")
                return False

        except Exception as e:
            error_msg = str(e)[:200] if str(e) else type(e).__name__
            print(f"❌ Login failed: {error_msg}")
            return False

    @with_retry(max_attempts=2)
    def navigate_to_ae_center(self) -> bool:
        try:
            print("📍 Navigating to Associate Editor Center...")
            ae_link = self.wait.until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            self.safe_click(ae_link)
            self.smart_wait(5)
            print("   ✅ In Associate Editor Center")
            self._capture_page("ae_center")
            return True
        except TimeoutException as e:
            print(f"   ❌ Navigation failed: {str(e)[:50]}")
            raise

    # ------------------------------------------------------------------
    # Email validation (merged MF blocklist + MOR regex)
    # ------------------------------------------------------------------

    def is_valid_referee_email(self, email: str) -> bool:
        if not email:
            return False
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            return False
        domain = email.split("@")[1].lower()
        invalid_domains = [
            "example.com",
            "test.com",
            "email.com",
            "mail.com",
            "manuscriptcentral.com",
            "scholarone.com",
            "clarivate.com",
        ]
        if domain in invalid_domains:
            return False
        invalid_prefixes = ["noreply", "donotreply", "no-reply", "system", "admin", "support"]
        local_part = email.split("@")[0].lower()
        if local_part in invalid_prefixes:
            return False
        if len(email) < 5 or len(email) > 100:
            return False
        return True

    # ------------------------------------------------------------------
    # Popup/Download helpers (IDENTICAL in MF and MOR)
    # ------------------------------------------------------------------

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
            print(f"         📦 [CACHE] Already downloaded: {os.path.basename(existing)}")
            return existing

        import base64 as _b64

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
                print(f"            ❌ No fetch result")
                return None

            if result.get("error"):
                print(f"            ❌ Fetch: {result['error']}")
                return None

            data = _b64.b64decode(result["data"])
            content_type = result.get("type", "")
            file_size = len(data)

            if file_size < 50:
                print(f"            ❌ File too small ({file_size} bytes)")
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
                        base = url.rsplit("/", 1)[0]
                        redirect_url = base + "/" + redirect_url
                    print(f"            🔄 Found redirect to download URL")
                    return self._download_file_from_url(redirect_url, manuscript_id, doc_type)
                print(f"            ⚠️ Got HTML page instead of file")
                return None

            with open(file_path, "wb") as f:
                f.write(data)

            print(f"            ✅ Saved: {filename} ({file_size:,} bytes)")
            return str(file_path)

        except Exception as e:
            print(f"            ❌ Download error: {str(e)[:60]}")
            return None

    def _open_popup_and_switch(self, link_element, wait_for_content: bool = False) -> Optional[str]:
        all_before = set(self.driver.window_handles)
        self.driver.execute_script("arguments[0].click();", link_element)
        for _ in range(16):
            time.sleep(0.5)
            new_windows = set(self.driver.window_handles) - all_before
            if new_windows:
                popup = new_windows.pop()
                self.driver.switch_to.window(popup)
                if wait_for_content:
                    for _ in range(15):
                        time.sleep(1)
                        try:
                            ct = self.driver.execute_script("return document.contentType;") or ""
                            if "pdf" in ct.lower():
                                break
                            body_len = (
                                self.driver.execute_script(
                                    "return document.body ? document.body.innerHTML.length : 0;"
                                )
                                or 0
                            )
                            has_embed = self.driver.execute_script(
                                "return document.querySelector('embed, object, iframe') !== null;"
                            )
                            if body_len > 100 or has_embed:
                                break
                        except Exception:
                            pass
                else:
                    time.sleep(2)
                return popup
        return None

    def _close_popup_safely(self, original_window: str):
        try:
            self.driver.close()
        except Exception:
            pass
        try:
            self.driver.switch_to.window(original_window)
        except Exception:
            if self.driver.window_handles:
                self.driver.switch_to.window(self.driver.window_handles[0])

    def _download_via_popup_window(
        self, link_element, doc_type: str, manuscript_id: str
    ) -> Optional[str]:
        existing = self._check_existing_download(manuscript_id, doc_type, str(self.download_dir))
        if existing:
            print(f"         📦 [CACHE] Already downloaded: {os.path.basename(existing)}")
            return existing

        original_window = self.driver.current_window_handle
        try:
            print(f"         📥 Downloading {doc_type}...")
            popup = self._open_popup_and_switch(link_element, wait_for_content=True)
            if not popup:
                print(f"            ❌ No popup window opened")
                return None
            file_url = self.driver.current_url
            if not file_url or file_url == "about:blank":
                time.sleep(3)
                file_url = self.driver.current_url
            print(f"            🔗 Popup URL: {file_url[:100]}...")

            content_type = ""
            try:
                content_type = self.driver.execute_script("return document.contentType;") or ""
            except Exception:
                pass

            if "pdf" in content_type.lower():
                import base64 as _b64_popup

                try:
                    pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {})
                    if pdf_data and pdf_data.get("data"):
                        data = _b64_popup.b64decode(pdf_data["data"])
                        if len(data) > 500:
                            filename = f"{manuscript_id}_{doc_type}.pdf"
                            file_path = self.download_dir / filename
                            with open(file_path, "wb") as f:
                                f.write(data)
                            print(f"            ✅ Saved via CDP: {filename} ({len(data):,} bytes)")
                            self._close_popup_safely(original_window)
                            return str(file_path)
                except Exception:
                    pass

            result = self._download_file_from_url(file_url, manuscript_id, doc_type)
            if result:
                self._close_popup_safely(original_window)
                return result

            print(f"            🔍 Content-Type: {content_type}")
            self._capture_page(f"popup_{doc_type}", manuscript_id, is_popup=True)

            diag = self.driver.execute_script(
                """
                var info = {};
                info.embeds = document.querySelectorAll('embed').length;
                info.objects = document.querySelectorAll('object').length;
                info.iframes = document.querySelectorAll('iframe').length;
                info.frames = document.querySelectorAll('frame').length;
                var links = document.querySelectorAll('a[href]');
                info.links = links.length;
                var linkHrefs = [];
                for (var j = 0; j < Math.min(links.length, 10); j++) {
                    linkHrefs.push(links[j].href.substring(0, 80));
                }
                info.linkHrefs = linkHrefs;
                info.title = document.title;
                info.bodyLen = document.body ? document.body.innerHTML.length : 0;
                var pluginEl = document.querySelector('embed[type*="pdf"], object[type*="pdf"]');
                if (pluginEl) info.pdfPlugin = pluginEl.outerHTML.substring(0, 200);
                return info;
            """
            )
            if diag:
                print(
                    f"            🔍 Page: title='{diag.get('title','')[:40]}' body={diag.get('bodyLen',0)} embeds={diag.get('embeds',0)} objects={diag.get('objects',0)} iframes={diag.get('iframes',0)} frames={diag.get('frames',0)} links={diag.get('links',0)}"
                )
                if diag.get("linkHrefs"):
                    for lh in diag["linkHrefs"][:3]:
                        print(f"            🔗 Link: {lh}")

            embedded_url = self.driver.execute_script(
                """
                var e = document.querySelector('embed');
                if (e && e.src) return e.src;
                var o = document.querySelector('object[data]');
                if (o && o.data) return o.data;
                var i = document.querySelector('iframe');
                if (i && i.src && i.src !== 'about:blank') return i.src;
                var links = document.querySelectorAll('a[href]');
                for (var j = 0; j < links.length; j++) {
                    var h = links[j].href;
                    if (h && (h.indexOf('.pdf') > -1 || h.indexOf('DOWNLOAD=TRUE') > -1 || h.indexOf('GetFile') > -1))
                        return h;
                }
                return null;
            """
            )
            if embedded_url:
                print(f"            🔗 Found embedded URL: {embedded_url[:80]}...")
                result = self._download_file_from_url(embedded_url, manuscript_id, doc_type)
                if result:
                    self._close_popup_safely(original_window)
                    return result

            try:
                frames = self.driver.find_elements(By.TAG_NAME, "frame")
                if not frames:
                    frames = self.driver.find_elements(By.TAG_NAME, "iframe")
                for frame in frames:
                    try:
                        self.driver.switch_to.frame(frame)
                        frame_ct = self.driver.execute_script("return document.contentType;") or ""
                        if "pdf" in frame_ct.lower():
                            frame_url = self.driver.current_url
                            result = self._download_file_from_url(
                                frame_url, manuscript_id, doc_type
                            )
                            self.driver.switch_to.default_content()
                            if result:
                                self._close_popup_safely(original_window)
                                return result
                        inner_url = self.driver.execute_script(
                            """
                            var e = document.querySelector('embed, object[data], iframe');
                            if (e) return e.src || e.data || null;
                            var a = document.querySelector('a[href*=".pdf"], a[href*="DOWNLOAD"], a[href*="GetFile"]');
                            if (a) return a.href;
                            return null;
                        """
                        )
                        self.driver.switch_to.default_content()
                        if inner_url:
                            result = self._download_file_from_url(
                                inner_url, manuscript_id, doc_type
                            )
                            if result:
                                self._close_popup_safely(original_window)
                                return result
                    except Exception:
                        try:
                            self.driver.switch_to.default_content()
                        except Exception:
                            pass
            except Exception:
                pass

            import base64 as _b64_fallback

            try:
                print(f"            🔄 Trying CDP Page.printToPDF fallback...")
                pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {})
                if pdf_data and pdf_data.get("data"):
                    data = _b64_fallback.b64decode(pdf_data["data"])
                    print(f"            📏 printToPDF returned {len(data):,} bytes")
                    if len(data) > 2000:
                        filename = f"{manuscript_id}_{doc_type}.pdf"
                        file_path = self.download_dir / filename
                        with open(file_path, "wb") as f:
                            f.write(data)
                        print(
                            f"            ✅ Saved via print-to-PDF: {filename} ({len(data):,} bytes)"
                        )
                        self._close_popup_safely(original_window)
                        return str(file_path)
            except Exception:
                pass

            print(f"            ❌ Could not extract file from popup")
            self._close_popup_safely(original_window)
            return None
        except Exception as e:
            print(f"            ❌ Popup download error: {str(e)[:50]}")
            self._close_popup_safely(original_window)
            return None

    def _download_from_popup_listing(
        self, link_element, doc_type: str, manuscript_id: str
    ) -> Optional[str]:
        existing = self._check_existing_download(manuscript_id, doc_type, str(self.download_dir))
        if existing:
            print(f"         📦 [CACHE] Already downloaded: {os.path.basename(existing)}")
            return existing

        original_window = self.driver.current_window_handle
        try:
            print(f"         📥 Downloading {doc_type}...")
            popup = self._open_popup_and_switch(link_element)
            if not popup:
                print(f"            ❌ No popup window opened")
                return None

            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text
                print(f"            ⚠️ Alert: {alert_text[:60]}")
                alert.accept()
                self._close_popup_safely(original_window)
                return None
            except Exception:
                pass

            print(f"            🔗 Popup URL: {self.driver.current_url[:100]}...")
            self._capture_page(f"popup_{doc_type}", manuscript_id, is_popup=True)

            try:
                frames = self.driver.find_elements(By.TAG_NAME, "frame")
                if frames:
                    self.driver.switch_to.frame(0)
            except Exception:
                pass

            download_selectors = [
                "//a[contains(@href, '.pdf') and not(contains(@href, 'javascript:'))]",
                "//a[contains(@href, '.docx') and not(contains(@href, 'javascript:'))]",
                "//a[contains(@href, '.doc') and not(contains(@href, 'javascript:'))]",
                "//a[contains(@href, 'GetFile')]",
                "//a[contains(@href, 'DOWNLOAD_FILE')]",
                "//a[contains(@href, 'DOWNLOAD=TRUE')]",
            ]

            for sel in download_selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, sel)
                    for link in links:
                        href = link.get_attribute("href") or ""
                        if href and href != "#":
                            link_text = link.text.strip() or "document"
                            safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", link_text)[:20]
                            label = f"{doc_type}_{safe_name}" if len(links) > 1 else doc_type
                            result = self._download_file_from_url(href, manuscript_id, label)
                            if result:
                                self._close_popup_safely(original_window)
                                return result
                except Exception:
                    continue

            self._close_popup_safely(original_window)
            return None
        except Exception as e:
            print(f"            ❌ Popup listing error: {str(e)[:50]}")
            self._close_popup_safely(original_window)
            return None

    # ------------------------------------------------------------------
    # Extraction: Abstract, Recommended/Opposed, Funding (IDENTICAL/NEAR)
    # ------------------------------------------------------------------

    def extract_abstract(self) -> str:
        try:
            print("      📝 Extracting abstract...")

            abstract_links = self.driver.find_elements(
                By.XPATH,
                "//a[contains(text(), 'Abstract')]"
                "[not(contains(text(), 'Abstract:'))]"
                "[not(ancestor::*[contains(@class,'menu')])]",
            )

            if not abstract_links:
                abstract_links = self.driver.find_elements(
                    By.XPATH,
                    "//p[@class='pagecontents msdetailsbuttons']//a[contains(text(), 'Abstract')]",
                )

            if not abstract_links:
                print("      ❌ No abstract link found")
                return ""

            original_window = self.driver.current_window_handle

            self.safe_click(abstract_links[0])
            self.smart_wait(2)

            if len(self.driver.window_handles) <= 1:
                print("      ❌ Abstract popup did not open")
                return ""

            for window in self.driver.window_handles:
                if window != original_window:
                    self.driver.switch_to.window(window)
                    break

            self._capture_page("abstract_popup", self._current_manuscript_id)

            abstract_text = ""
            selectors = [
                "//td[@class='pagecontents']",
                "//p[@class='pagecontents']",
                "//div[@class='abstract']",
                "//div[@id='abstract']",
                "//body",
            ]

            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if len(text) > 100:
                            abstract_text = text
                            break
                    if abstract_text:
                        break
                except Exception:
                    pass

            try:
                self.driver.close()
                self.driver.switch_to.window(original_window)
            except Exception:
                if self.driver.current_window_handle != original_window:
                    self.driver.switch_to.window(original_window)

            if abstract_text:
                print(f"      ✅ Abstract extracted ({len(abstract_text)} chars)")
            else:
                print("      ❌ Abstract text not found in popup")

            return abstract_text

        except Exception as e:
            print(f"      ❌ Error extracting abstract: {str(e)[:50]}")
            try:
                if self.driver.current_window_handle != original_window:
                    self.driver.switch_to.window(original_window)
            except Exception:
                pass
            return ""

    def extract_recommended_opposed(self) -> Dict[str, list]:
        result = {
            "recommended_referees": [],
            "opposed_referees": [],
            "recommended_editors": [],
            "opposed_editors": [],
        }
        labels = {
            "Author Recommended Reviewers": "recommended_referees",
            "Author Opposed Reviewers": "opposed_referees",
            "Author Recommended Editors": "recommended_editors",
            "Author Opposed Editors": "opposed_editors",
        }
        for label_text, key in labels.items():
            try:
                label_td = self.driver.find_element(
                    By.XPATH,
                    f"//td[@class='alternatetablecolor']"
                    f"[.//p[@class='pagecontents'][contains(text(), '{label_text}')]]",
                )
                row = label_td.find_element(By.XPATH, "./parent::tr")
                content_td = row.find_element(By.XPATH, ".//td[@class='tablelightcolor']")
                inner_html = content_td.get_attribute("innerHTML") or ""
                entries = re.split(r"<br\s*/?>", inner_html, flags=re.IGNORECASE)
                for entry in entries:
                    clean = re.sub(r"<[^>]+>", "", entry).strip()
                    clean = re.sub(r"\s+", " ", clean)
                    if not clean or len(clean) < 3:
                        continue
                    email = ""
                    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean)
                    if email_match:
                        email = email_match.group()
                    name = ""
                    institution = ""
                    department = ""
                    if " - " in clean:
                        name_inst, _ = clean.rsplit(" - ", 1)
                    else:
                        name_inst = clean
                    name_inst = (
                        re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "", name_inst).strip().rstrip("-").strip()
                    )
                    if ", " in name_inst:
                        parts = name_inst.split(", ", 1)
                        possible_dept = parts[-1].strip()
                        if any(
                            kw in possible_dept.lower()
                            for kw in ["department", "dept", "school", "faculty", "division"]
                        ):
                            department = possible_dept
                            name_inst = parts[0].strip()
                    inst_kw = r"(?:University|Institute|College|School|ETH|MIT|CEREMADE|ORFE|IEOR|CREST|INRIA|Polytechnic|Academy|Universität|Université|Sciences?\s+Po)"
                    inst_match = re.search(
                        rf"(\S+\s+{inst_kw}|{inst_kw}\s+of\s+\S+)",
                        name_inst,
                        re.IGNORECASE,
                    )
                    if inst_match:
                        inst_start = inst_match.start()
                        name = name_inst[:inst_start].strip()
                        institution = name_inst[inst_start:].strip()
                        if ", " in institution:
                            inst_parts = institution.split(", ", 1)
                            institution = inst_parts[0].strip()
                            if not department:
                                department = inst_parts[1].strip()
                    else:
                        name = name_inst
                        institution = ""
                    if name:
                        result[key].append(
                            {
                                "name": name,
                                "email": email,
                                "institution": institution,
                                "department": department,
                            }
                        )
            except Exception:
                continue
        total = sum(len(v) for v in result.values())
        if total:
            print(
                f"      📋 Recommended/opposed: {len(result['recommended_referees'])} rec reviewers, "
                f"{len(result['opposed_referees'])} opp reviewers, "
                f"{len(result['recommended_editors'])} rec editors, "
                f"{len(result['opposed_editors'])} opp editors"
            )
        return result

    def parse_structured_funding(self, cell_html: str) -> list:
        grants = []
        grant_blocks = re.split(r"<br\s*/?>\s*<br\s*/?>", cell_html, flags=re.IGNORECASE)
        for block in grant_blocks:
            block = block.strip()
            if not block:
                continue
            parts = re.split(r"<br\s*/?>", block, flags=re.IGNORECASE)
            funder_chain = []
            program = ""
            grant_number = ""
            for part in parts:
                clean = re.sub(r"<[^>]+>", "", part).strip()
                clean = re.sub(r"&gt;", ">", clean).strip()
                if not clean:
                    continue
                if "<b>" in part.lower():
                    program = clean.rstrip(">").strip()
                elif clean.endswith(">"):
                    funder_chain.append(clean.rstrip(">").strip())
                elif re.match(r"^[A-Z0-9][A-Z0-9\-/]+$", clean) and len(clean) < 30:
                    grant_number = clean
                elif "no fund" in clean.lower() or "there are no" in clean.lower():
                    continue
                else:
                    funder_chain.append(clean)
            if funder_chain or program or grant_number:
                grants.append(
                    {
                        "funder_hierarchy": funder_chain,
                        "program": program,
                        "grant_number": grant_number,
                        "full_text": " > ".join(funder_chain + ([program] if program else [])),
                    }
                )
        return grants

    # ------------------------------------------------------------------
    # Report/Letter/Response popup extraction (IDENTICAL)
    # ------------------------------------------------------------------

    def extract_referee_report_from_popup(
        self, referee: Dict, manuscript_id: str = ""
    ) -> Optional[Dict]:
        report_url = referee.get("report_url", "")
        if not report_url:
            return None
        try:
            original_window = self.driver.current_window_handle
            all_before = set(self.driver.window_handles)

            self.driver.execute_script(
                f"window.open('{report_url}', 'report_popup', 'width=700,height=600');"
            )
            time.sleep(3)

            all_after = set(self.driver.window_handles)
            new_windows = all_after - all_before
            if not new_windows:
                return None

            popup = new_windows.pop()
            self.driver.switch_to.window(popup)
            time.sleep(2)

            referee_name = referee.get("name", "unknown")
            safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", referee_name.split(",")[0].strip())

            if manuscript_id:
                self._capture_page(f"referee_report_{safe_name}", manuscript_id, is_popup=True)

            report = {
                "recommendation": referee.get("recommendation", ""),
                "scores": {},
                "comments_to_author": "",
                "confidential_comments": "",
                "raw_text": "",
                "attached_files": [],
            }

            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                full_text = body.text.strip()
                report["raw_text"] = full_text

                tables = self.driver.find_elements(By.XPATH, "//table")
                for table in tables:
                    rows = table.find_elements(By.XPATH, ".//tr")
                    for tr in rows:
                        cells = tr.find_elements(By.XPATH, ".//td")
                        if len(cells) >= 2:
                            label = cells[0].text.strip().rstrip(":")
                            value = cells[-1].text.strip()
                            if label and value and len(label) < 80:
                                score_match = re.match(r"(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?$", value)
                                if score_match:
                                    report["scores"][label] = value
                                elif label.lower() in ["recommendation", "overall recommendation"]:
                                    report["recommendation"] = value

                sections = {
                    "comments_to_author": [
                        "Comments to Author",
                        "Comments to the Author",
                        "Review Comments",
                        "Comments for the Author",
                    ],
                    "confidential_comments": [
                        "Confidential Comments to Editor",
                        "Confidential Comments",
                        "Comments to the Editor",
                        "Confidential",
                    ],
                }
                for field, headers in sections.items():
                    for header in headers:
                        pattern = re.compile(
                            rf"{re.escape(header)}[:\s]*\n(.*?)(?=\n(?:Comments|Confidential|Recommendation|$))",
                            re.DOTALL | re.IGNORECASE,
                        )
                        m = pattern.search(full_text)
                        if m:
                            report[field] = m.group(1).strip()
                            break

                if not report["comments_to_author"] and full_text:
                    lines = full_text.split("\n")
                    content_lines = []
                    capture = False
                    for line in lines:
                        lower = line.lower().strip()
                        if any(
                            h.lower() in lower
                            for h in [
                                "comments to author",
                                "review comments",
                                "comments for the author",
                            ]
                        ):
                            capture = True
                            continue
                        if capture:
                            if any(
                                h.lower() in lower
                                for h in ["confidential", "recommendation", "score"]
                            ):
                                break
                            content_lines.append(line)
                    if content_lines:
                        report["comments_to_author"] = "\n".join(content_lines).strip()

                if manuscript_id:
                    file_links = self.driver.find_elements(
                        By.XPATH,
                        "//a[contains(@href, '.pdf') or contains(@href, '.doc') or contains(@href, 'GetFile') or contains(@href, 'DOWNLOAD')]",
                    )
                    for fl in file_links:
                        href = fl.get_attribute("href") or ""
                        if href.startswith("javascript:"):
                            onclick = fl.get_attribute("onclick") or ""
                            url_m = re.search(r"popWindow\('([^']+)'", onclick)
                            if url_m:
                                href = url_m.group(1)
                            else:
                                continue
                        if not href or href == "#":
                            continue
                        if href.startswith("/"):
                            base = (
                                self.driver.current_url.split("/")[0]
                                + "//"
                                + self.driver.current_url.split("/")[2]
                            )
                            href = base + href
                        link_text = fl.text.strip() or "report_attachment"
                        safe_lt = re.sub(r"[^a-zA-Z0-9_.]", "_", link_text)[:30]
                        doc_label = f"referee_report_{safe_name}_{safe_lt}"
                        self.driver.switch_to.window(original_window)
                        saved = self._download_file_from_url(href, manuscript_id, doc_label)
                        self.driver.switch_to.window(popup)
                        if saved:
                            report["attached_files"].append(saved)
                            print(f"            📎 Saved referee attachment: {Path(saved).name}")

                if manuscript_id and report["raw_text"]:
                    report_dir = self.download_dir / "referee_reports"
                    report_dir.mkdir(exist_ok=True)
                    txt_path = report_dir / f"{manuscript_id}_report_{safe_name}.txt"
                    txt_path.write_text(report["raw_text"], encoding="utf-8")
                    report["report_text_file"] = str(txt_path)

            except Exception:
                pass

            self.driver.close()
            self.driver.switch_to.window(original_window)

            if report["comments_to_author"] or report["raw_text"]:
                print(
                    f"         📝 Report extracted: {len(report.get('comments_to_author', ''))} chars"
                )
                return report
            return None

        except Exception as e:
            try:
                self.driver.switch_to.window(original_window)
            except Exception:
                pass
            print(f"         ⚠️ Report extraction error: {str(e)[:50]}")
            return None

    def extract_decision_letter_from_popup(self, popup_url: str) -> Optional[str]:
        if not popup_url:
            return None
        try:
            original_window = self.driver.current_window_handle
            all_before = set(self.driver.window_handles)
            self.driver.execute_script(
                f"window.open('{popup_url}', 'dl_popup', 'width=800,height=500');"
            )
            time.sleep(3)
            new_windows = set(self.driver.window_handles) - all_before
            if not new_windows:
                return None
            popup = new_windows.pop()
            self.driver.switch_to.window(popup)
            time.sleep(2)
            body = self.driver.find_element(By.TAG_NAME, "body")
            text = body.text.strip()
            self.driver.close()
            self.driver.switch_to.window(original_window)
            if text and len(text) > 20:
                return text
            return None
        except Exception:
            try:
                self.driver.switch_to.window(original_window)
            except Exception:
                pass
            return None

    def extract_author_response_from_popup(self, popup_url: str) -> Optional[str]:
        if not popup_url:
            return None
        try:
            original_window = self.driver.current_window_handle
            all_before = set(self.driver.window_handles)
            self.driver.execute_script(
                f"window.open('{popup_url}', 'ar_popup', 'width=600,height=500');"
            )
            time.sleep(3)
            new_windows = set(self.driver.window_handles) - all_before
            if not new_windows:
                return None
            popup = new_windows.pop()
            self.driver.switch_to.window(popup)
            time.sleep(2)
            body = self.driver.find_element(By.TAG_NAME, "body")
            text = body.text.strip()
            self.driver.close()
            self.driver.switch_to.window(original_window)
            if text and len(text) > 20:
                return text
            return None
        except Exception:
            try:
                self.driver.switch_to.window(original_window)
            except Exception:
                pass
            return None

    # ------------------------------------------------------------------
    # Version history & milestones (NEAR-IDENTICAL — MOR superset)
    # ------------------------------------------------------------------

    def extract_peer_review_milestones(self) -> Dict[str, Any]:
        milestones = {}
        try:
            try:
                toggle = self.driver.find_elements(
                    By.XPATH,
                    "//a[@name='itemMS_PEER_REVIEW_MILESTONES']/ancestor::tr//a[contains(@onclick,'toggle') or contains(@onclick,'show') or contains(@onclick,'expand')]",
                )
                if toggle:
                    self.safe_click(toggle[0])
                    time.sleep(0.5)
            except Exception:
                pass

            brn_div = self.driver.find_elements(
                By.XPATH,
                "//a[@name='itemMS_PEER_REVIEW_MILESTONES']/ancestor::tr/following-sibling::tr//div[starts-with(@id,'brn')]",
            )
            if not brn_div:
                brn_div = self.driver.find_elements(
                    By.XPATH,
                    "//b[text()='Peer Review Milestones']/ancestor::tr/following-sibling::tr//div[starts-with(@id,'brn')]",
                )
            if not brn_div:
                return milestones

            rows = brn_div[0].find_elements(By.XPATH, ".//tr")
            for row in rows:
                label_cells = row.find_elements(By.XPATH, ".//td[@class='alternatetablecolor']")
                value_cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                for i, lc in enumerate(label_cells):
                    label = lc.text.strip().rstrip(":")
                    if not label:
                        continue
                    if i < len(value_cells):
                        vc = value_cells[i]
                        val_text = vc.text.strip()
                        name_link = vc.find_elements(By.XPATH, ".//a")
                        if "Date" in label:
                            milestones[self._milestone_key(label)] = val_text
                        elif name_link:
                            raw_name = name_link[0].text.strip()
                            clean = re.sub(
                                r"\s+(?:AU\s+REV\s+AE|AU\s+REV|AE|AreaED|EIC|ME|VC|CO|ADM|PROD)\s*",
                                " ",
                                raw_name,
                            ).strip()
                            if ", " in clean:
                                parts = clean.split(", ", 1)
                                clean = f"{parts[1].strip()} {parts[0].strip()}"
                            role = label.lower().replace(" ", "_")
                            if clean:
                                milestones[role] = clean
                        elif val_text and "Date" not in label:
                            role = label.lower().replace(" ", "_")
                            milestones[role] = val_text

            if milestones:
                print(f"      📅 Peer review milestones: {len(milestones)} fields")
        except Exception as e:
            print(f"         ❌ Error extracting milestones: {str(e)[:50]}")
        return milestones

    def _milestone_key(self, label: str) -> str:
        label = label.lower().strip().rstrip(":")
        label = label.replace("date to ", "date_to_")
        label = label.replace("date submitted", "date_submitted")
        label = label.replace(" ", "_")
        return label

    def extract_version_history(self, manuscript_id: str) -> List[Dict]:
        version_history = []
        try:
            try:
                toggle = self.driver.find_elements(
                    By.XPATH,
                    "//a[@name='itemMS_VERSION_HISTORY']/ancestor::tr//a[contains(@onclick,'toggle') or contains(@onclick,'show') or contains(@onclick,'expand')]",
                )
                if toggle:
                    self.safe_click(toggle[0])
                    time.sleep(0.5)
            except Exception:
                pass

            brn_div = self.driver.find_elements(
                By.XPATH,
                "//a[@name='itemMS_VERSION_HISTORY']/ancestor::tr/following-sibling::tr//div[starts-with(@id,'brn')]",
            )
            if not brn_div:
                brn_div = self.driver.find_elements(
                    By.XPATH,
                    "//b[text()='Version History']/ancestor::tr/following-sibling::tr//div[starts-with(@id,'brn')]",
                )
            if not brn_div:
                return version_history

            rows = brn_div[0].find_elements(By.XPATH, ".//tr[td[@class='tablelightcolor']]")
            for row in rows:
                cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                if len(cells) < 4:
                    continue
                try:
                    ms_id_cell = cells[1]
                    ms_id_text = ms_id_cell.text.strip()
                    ms_id_clean = re.sub(r"\s+", " ", ms_id_text).split(" ")[0].strip()
                    if not ms_id_clean:
                        continue

                    title_cell = cells[2]
                    title = title_cell.text.strip()

                    date_cell = cells[3]
                    date_submitted = date_cell.text.strip()

                    decision_letter_url = ""
                    author_response_url = ""
                    if len(cells) > 4:
                        decision_cell = cells[4]
                        dl_links = decision_cell.find_elements(By.XPATH, ".//a")
                        for lnk in dl_links:
                            href = lnk.get_attribute("href") or ""
                            txt = lnk.text.strip().lower()
                            if "decision letter" in txt:
                                onclick = lnk.get_attribute("onclick") or href
                                url_match = re.search(r"popWindow\('([^']+)'", onclick)
                                if url_match:
                                    decision_letter_url = url_match.group(1)
                            elif "author" in txt and "response" in txt:
                                onclick = lnk.get_attribute("onclick") or href
                                url_match = re.search(r"popWindow\('([^']+)'", onclick)
                                if url_match:
                                    author_response_url = url_match.group(1)

                    if not decision_letter_url and not author_response_url and len(cells) > 4:
                        all_links_in_row = row.find_elements(
                            By.XPATH, ".//a[contains(@href,'popWindow') or contains(@href,'view')]"
                        )
                        for lnk in all_links_in_row:
                            href = lnk.get_attribute("href") or ""
                            onclick = lnk.get_attribute("onclick") or ""
                            combined = onclick + " " + href
                            txt = lnk.text.strip().lower()
                            if "decision" in txt or "person_details_pop" in combined:
                                url_match = re.search(r"popWindow\('([^']+)'", combined)
                                if url_match and not decision_letter_url:
                                    decision_letter_url = url_match.group(1)
                            elif "response" in txt or "view_comments" in combined:
                                url_match = re.search(r"popWindow\('([^']+)'", combined)
                                if url_match and not author_response_url:
                                    author_response_url = url_match.group(1)

                    switch_url = ""
                    if len(cells) > 5:
                        sw_links = cells[5].find_elements(By.XPATH, ".//a")
                        if sw_links:
                            onclick = sw_links[0].get_attribute("onclick") or ""
                            if onclick:
                                switch_url = onclick

                    is_current = ms_id_clean == manuscript_id
                    revision_match = re.search(r"\.R(\d+)$", ms_id_clean)
                    version_num = int(revision_match.group(1)) if revision_match else 0

                    version_data = {
                        "manuscript_id": ms_id_clean,
                        "title": title,
                        "date_submitted": date_submitted,
                        "version_number": version_num,
                        "is_current_version": is_current,
                        "decision_letter_url": decision_letter_url,
                        "author_response_url": author_response_url,
                        "switch_details_url": switch_url,
                        "review_details_url": "",
                    }
                    version_history.append(version_data)
                    status = "← current" if is_current else ""
                    has_dl = " [DL]" if decision_letter_url else ""
                    print(f"         • {ms_id_clean} ({date_submitted}){has_dl} {status}")
                except Exception:
                    continue

            if version_history and len(version_history) > 1:
                all_vh_links = brn_div[0].find_elements(By.XPATH, ".//a")
                for lnk in all_vh_links:
                    try:
                        href = lnk.get_attribute("href") or ""
                        outer = lnk.get_attribute("outerHTML") or ""
                        txt = lnk.text.strip().lower()
                        if "person_details_pop" in outer or (
                            "decision" in txt and "popWindow" in outer
                        ):
                            url_match = re.search(r"popWindow\('([^']+)'", outer)
                            if url_match:
                                for vh in version_history:
                                    if not vh.get("is_current_version") and not vh.get(
                                        "decision_letter_url"
                                    ):
                                        vh["decision_letter_url"] = url_match.group(1)
                                        print(
                                            f"         📨 Found DL popup for {vh['manuscript_id']}"
                                        )
                                        break
                        elif "view_comments" in outer or (
                            "response" in txt and "popWindow" in outer
                        ):
                            url_match = re.search(r"popWindow\('([^']+)'", outer)
                            if url_match:
                                for vh in version_history:
                                    if not vh.get("is_current_version") and not vh.get(
                                        "author_response_url"
                                    ):
                                        vh["author_response_url"] = url_match.group(1)
                                        print(
                                            f"         📝 Found AR popup for {vh['manuscript_id']}"
                                        )
                                        break
                        elif "reviewer_view_details" in outer:
                            url_match = re.search(r"popWindow\('([^']+)'", outer)
                            if url_match:
                                for vh in version_history:
                                    if not vh.get("is_current_version") and not vh.get(
                                        "review_details_url"
                                    ):
                                        vh["review_details_url"] = url_match.group(1)
                                        print(
                                            f"         🔍 Found Review Details popup for {vh['manuscript_id']}"
                                        )
                                        break
                        elif (
                            "details.gif" in href
                            or "MANUSCRIPT_DETAILS" in href
                            or "MANUSCRIPT_DETAILS" in outer
                            or "setNextPage" in outer
                        ):
                            sw_href = href
                            if (
                                not sw_href
                                or sw_href == "javascript:void(0)"
                                or "MANUSCRIPT_DETAILS" not in sw_href
                            ):
                                sw_href = outer
                                js_match = re.search(r'href="(javascript:[^"]+)"', sw_href)
                                if js_match:
                                    sw_href = js_match.group(1)
                            for vh in version_history:
                                if not vh.get("is_current_version") and not vh.get(
                                    "switch_details_url"
                                ):
                                    vh["switch_details_url"] = sw_href
                                    print(f"         🔗 Found switch link for {vh['manuscript_id']}")
                                    break
                    except Exception:
                        continue

            if version_history:
                version_history.sort(key=lambda v: v["version_number"])
                print(f"         📊 Found {len(version_history)} versions")
        except Exception as e:
            print(f"         ❌ Error extracting version history: {str(e)[:50]}")

        return version_history

    # ------------------------------------------------------------------
    # AE Recommendation (IDENTICAL)
    # ------------------------------------------------------------------

    def extract_ae_recommendation_data(self, manuscript_data: Dict):
        try:
            print(f"      🎯 Extracting AE recommendation data...")
            ae_data = {
                "recommendation_available": True,
                "referee_summary": [],
                "recommendation_form": {},
            }

            tabs_to_try = [
                "Make a Recommendation",
                "Make Recommendation",
                "AE Recommendation",
                "Recommendation",
            ]
            tab_found = False
            for tab_name in tabs_to_try:
                try:
                    tab_xpaths = [
                        f"//a[contains(text(), '{tab_name}')]",
                        f"//td[contains(text(), '{tab_name}')]",
                        f"//span[contains(text(), '{tab_name}')]",
                        f"//li[contains(text(), '{tab_name}')]",
                    ]
                    for xp in tab_xpaths:
                        try:
                            el = self.driver.find_element(By.XPATH, xp)
                            self.safe_click(el)
                            time.sleep(2)
                            tab_found = True
                            print(f"         ✅ Found tab: {tab_name}")
                            break
                        except Exception:
                            continue
                    if tab_found:
                        break
                except Exception:
                    continue

            if not tab_found:
                print(f"         ⚠️ No recommendation tab found, extracting from current page")

            ms_id = manuscript_data.get("id", "") or manuscript_data.get("manuscript_id", "")
            self._capture_page("ae_recommendation", ms_id)

            selects = self.driver.find_elements(By.XPATH, "//select")
            for sel in selects:
                try:
                    sel_name = sel.get_attribute("name") or sel.get_attribute("id") or ""
                    label_text = ""
                    try:
                        label_el = sel.find_element(By.XPATH, "./preceding::label[1]")
                        label_text = label_el.text.strip()
                    except Exception:
                        try:
                            parent_td = sel.find_element(
                                By.XPATH, "./ancestor::td[1]/preceding-sibling::td[1]"
                            )
                            label_text = parent_td.text.strip()
                        except Exception:
                            pass
                    selected_option = sel.find_element(By.XPATH, ".//option[@selected]")
                    selected_text = selected_option.text.strip() if selected_option else ""
                    all_options = [
                        o.text.strip()
                        for o in sel.find_elements(By.XPATH, ".//option")
                        if o.text.strip()
                    ]
                    if any(
                        kw in (label_text + sel_name).lower()
                        for kw in ["recommend", "decision", "disposition"]
                    ):
                        ae_data["recommendation_form"]["field_name"] = label_text or sel_name
                        ae_data["recommendation_form"]["selected_value"] = selected_text
                        ae_data["recommendation_form"]["available_options"] = all_options
                except Exception:
                    continue

            textareas = self.driver.find_elements(By.XPATH, "//textarea")
            comments = []
            for ta in textareas:
                try:
                    ta_name = ta.get_attribute("name") or ta.get_attribute("id") or ""
                    ta_text = ta.get_attribute("value") or ta.text or ""
                    label_text = ""
                    try:
                        label_el = ta.find_element(By.XPATH, "./preceding::label[1]")
                        label_text = label_el.text.strip()
                    except Exception:
                        try:
                            parent_td = ta.find_element(
                                By.XPATH, "./ancestor::td[1]/preceding-sibling::td[1]"
                            )
                            label_text = parent_td.text.strip()
                        except Exception:
                            pass
                    comments.append(
                        {
                            "field": label_text or ta_name,
                            "content": ta_text.strip(),
                        }
                    )
                except Exception:
                    continue
            ae_data["recommendation_form"]["comment_fields"] = comments

            summary_tables = self.driver.find_elements(
                By.XPATH,
                "//table[contains(.,'Recommendation') or contains(.,'Score') or contains(.,'Reviewer')]",
            )
            for table in summary_tables[:3]:
                try:
                    rows = table.find_elements(By.XPATH, ".//tr")
                    for row in rows[1:]:
                        cells = row.find_elements(By.XPATH, ".//td")
                        if len(cells) >= 2:
                            cell_texts = [c.text.strip() for c in cells]
                            if any(cell_texts):
                                ae_data["referee_summary"].append(cell_texts)
                except Exception:
                    continue

            manuscript_data["ae_recommendation_data"] = ae_data
            rec_form = ae_data.get("recommendation_form", {})
            if rec_form.get("selected_value"):
                print(f"         📋 Current recommendation: {rec_form['selected_value']}")
            print(f"         📊 Referee summary rows: {len(ae_data['referee_summary'])}")
            print(f"         ✅ AE recommendation data extracted")

        except Exception as e:
            print(f"         ❌ Error extracting AE recommendation data: {str(e)[:100]}")
            manuscript_data["ae_recommendation_data"] = {
                "recommendation_available": False,
                "error": str(e)[:200],
            }

    # ------------------------------------------------------------------
    # Enrichment (IDENTICAL / NEAR-IDENTICAL)
    # ------------------------------------------------------------------

    def _enrich_people_from_web(self, manuscript_data: Dict):
        enrich_people_from_web(
            manuscript_data,
            get_cached_web_profile=self.get_cached_web_profile,
            save_web_profile=self.save_web_profile,
            platform_label="scholarone_metadata",
        )

    def _enrich_audit_trail_with_gmail(self, manuscript_data: Dict, manuscript_id: str):
        if not GMAIL_SEARCH_AVAILABLE:
            return

        audit_trail = manuscript_data.get(
            "audit_trail", manuscript_data.get("communication_timeline", [])
        )
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
                print(f"      ⚠️ Gmail service not available")
                return

            sub_date_str = manuscript_data.get("metadata", {}).get("submission_date", "")
            if not sub_date_str:
                sub_date_str = manuscript_data.get("submission_date", "")
            date_range = None
            if sub_date_str:
                for fmt in ["%d-%b-%Y", "%Y-%m-%d", "%d-%B-%Y"]:
                    try:
                        sub_date = datetime.strptime(sub_date_str, fmt)
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
                print(f"      📧 No external Gmail communications found")
                return

            merged = gmail.merge_with_audit_trail(
                audit_trail=audit_trail,
                external_emails=external_emails,
                manuscript_id=manuscript_id,
            )

            manuscript_data["communication_timeline"] = merged
            ext_count = len([e for e in merged if e.get("external")])
            manuscript_data["external_communications_count"] = ext_count
            manuscript_data["timeline_enhanced"] = True
            print(f"      📧 Gmail enrichment: {ext_count} external emails merged into timeline")

        except Exception as e:
            print(f"      ⚠️ Gmail search error: {str(e)[:60]}")

    def _enrich_revision_referee_data(self, manuscript_data: Dict):
        audit = manuscript_data.get("audit_trail", manuscript_data.get("_r0_audit_trail", []))
        if not isinstance(audit, list):
            audit = []

        referees = manuscript_data.get("referees", [])
        if not referees:
            return

        prev_reviewer_names = set()
        prev_recommendations = {}
        for event in audit:
            ev_text = (
                event.get("raw_event", "")
                or event.get("event", "")
                or event.get("description", "")
                or ""
            )
            ev_lower = ev_text.lower()
            name_match = re.search(
                r"(?:reviewer|referee)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", ev_text
            )
            if not name_match:
                name_match = re.search(
                    r"(?:agreed|declined|invitation sent to|review from)\s+([A-Z][a-z]+(?:,\s*[A-Z][a-z]+)?(?:\s+[A-Z][a-z]+)*)",
                    ev_text,
                )
            if name_match:
                raw_name = name_match.group(1).strip()
                clean_name = re.sub(
                    r"\s+AU\s+REV\s+AE|\s+AU\s+REV|\s+AE$|\s+EIC$", "", raw_name
                ).strip()
                if clean_name and len(clean_name) > 3:
                    prev_reviewer_names.add(clean_name.lower())

            for rec_kw in ["minor revision", "major revision", "accept", "reject"]:
                if rec_kw in ev_lower and any(
                    p in ev_lower
                    for p in [
                        "became completed",
                        "recommendation",
                        "review completed",
                        "submitted review",
                    ]
                ):
                    if name_match:
                        prev_recommendations[clean_name.lower()] = rec_kw.title()

        if not prev_reviewer_names:
            return

        matched = 0
        for ref in referees:
            ref_name = ref.get("name", "").lower()
            if not ref_name:
                continue

            ref_last = (
                ref_name.split(",")[0].strip()
                if "," in ref_name
                else ref_name.split()[-1]
                if ref_name.split()
                else ""
            )

            for prev_name in prev_reviewer_names:
                prev_parts = prev_name.split()
                prev_last = prev_parts[-1] if prev_parts else ""

                if ref_name == prev_name:
                    ref["returning_reviewer"] = True
                    matched += 1
                    break
                elif ref_last and prev_last and ref_last == prev_last:
                    ref["returning_reviewer"] = True
                    matched += 1
                    break
                elif ref_last and any(ref_last == p for p in prev_parts):
                    ref["returning_reviewer"] = True
                    matched += 1
                    break

            if ref.get("returning_reviewer"):
                for prev_name, rec in prev_recommendations.items():
                    prev_last = prev_name.split()[-1] if prev_name.split() else ""
                    if ref_last == prev_last:
                        ref["previous_recommendation"] = rec
                        break

        if matched:
            print(f"      🔄 Identified {matched} returning reviewers from previous version")

    def search_orcid_api(self, name: str) -> str:
        if not name:
            return ""

        strategies = [
            f'"{name}"',
            name.replace(",", ""),
            " ".join(name.split(", ")[::-1]),
            name.split(",")[0] if "," in name else name,
        ]

        headers = {
            "Accept": "application/json",
            "User-Agent": f"{self.JOURNAL_CODE} Extractor/1.0 (mailto:admin@example.com)",
        }

        for strategy in strategies:
            try:
                url = f"https://pub.orcid.org/v3.0/search?q={requests.utils.quote(strategy)}"
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if "result" in data and data["result"]:
                        for result in data["result"][:5]:
                            orcid = result.get("orcid-identifier", {}).get("path", "")
                            if orcid:
                                return orcid
            except Exception:
                continue

        return ""

    def infer_country_from_web_search(self, institution_name):
        if not institution_name:
            return None

        try:
            print(f"         🌍 Searching for country of: {institution_name}")

            if not hasattr(self, "_institution_country_cache"):
                self._institution_country_cache = {}

            cache_key = institution_name.lower().strip()
            if cache_key in self._institution_country_cache:
                cached_country = self._institution_country_cache.get(cache_key)
                print(f"         📚 Using cached country: {cached_country}")
                return cached_country

            found_country = None

            search_queries = [
                f'"{institution_name}" university country location',
                f'"{institution_name}" located in which country',
                f'"{institution_name}" institution address country',
            ]

            direct_countries = {
                "ETH Zurich": "Switzerland",
                "ETH": "Switzerland",
                "ETHZ": "Switzerland",
                "MIT": "United States",
                "Harvard": "United States",
                "Stanford": "United States",
                "Princeton": "United States",
                "Yale": "United States",
                "Columbia": "United States",
                "Cornell": "United States",
                "Berkeley": "United States",
                "Caltech": "United States",
                "Carnegie Mellon": "United States",
                "University of Chicago": "United States",
                "Northwestern": "United States",
                "Oxford": "United Kingdom",
                "Cambridge": "United Kingdom",
                "Imperial College": "United Kingdom",
                "LSE": "United Kingdom",
                "UCL": "United Kingdom",
                "Ecole Polytechnique": "France",
                "CEREMADE": "France",
                "Sciences Po": "France",
                "Sorbonne": "France",
                "INRIA": "France",
                "Bocconi": "Italy",
                "Politecnico": "Italy",
                "Universität": "Germany",
                "Max Planck": "Germany",
                "Humboldt": "Germany",
                "University of Tokyo": "Japan",
                "Peking University": "China",
                "Tsinghua": "China",
                "NUS": "Singapore",
                "ANU": "Australia",
                "University of Melbourne": "Australia",
                "University of Sydney": "Australia",
                "University of Toronto": "Canada",
                "McGill": "Canada",
                "Technion": "Israel",
                "Hebrew University": "Israel",
                "KAIST": "South Korea",
                "Seoul National": "South Korea",
            }

            for key, country in direct_countries.items():
                if key.lower() in institution_name.lower():
                    found_country = country
                    break

            if found_country:
                self._institution_country_cache[cache_key] = found_country
                print(f"         ✅ Country found (direct match): {found_country}")
                return found_country

            try:
                ror_url = f"https://api.ror.org/organizations?query={requests.utils.quote(institution_name)}"
                resp = requests.get(ror_url, timeout=5)
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    if items:
                        country_obj = items[0].get("country", {})
                        found_country = country_obj.get("country_name", "")
                        if found_country:
                            self._institution_country_cache[cache_key] = found_country
                            print(f"         ✅ Country found (ROR): {found_country}")
                            return found_country
            except Exception:
                pass

            self._institution_country_cache[cache_key] = None
            return None

        except Exception as e:
            print(f"         ⚠️ Country search error: {str(e)[:50]}")
            return None

    # ------------------------------------------------------------------
    # Analytics (NEAR-IDENTICAL — parameterized for both MF and MOR)
    # ------------------------------------------------------------------

    def _compute_final_outcome(self, manuscript_data: Dict):
        status = manuscript_data.get("metadata", {}).get("status", "")
        if not status:
            status = manuscript_data.get("status_details", {}).get("status", "")
        if not status:
            status = manuscript_data.get("status", "")
        audit = manuscript_data.get(
            "audit_trail", manuscript_data.get("communication_timeline", [])
        )
        if not isinstance(audit, list):
            audit = []

        final_decision = ""
        final_decision_date = ""
        decision_keywords = {
            "accept": "Accept",
            "reject": "Reject",
            "minor revision": "Minor Revision",
            "major revision": "Major Revision",
            "withdraw": "Withdrawn",
        }

        for event in audit:
            ev_text = (
                event.get("raw_event", "") or event.get("event", "") or event.get("description", "")
            ).lower()
            ev_date = event.get("date", "")
            if any(
                p in ev_text
                for p in ["final decision", "editor decision", "eic decision", "a decision of"]
            ):
                for kw, label in decision_keywords.items():
                    if kw in ev_text:
                        final_decision = label
                        final_decision_date = ev_date
                        break

        if not final_decision and status:
            status_lower = status.lower()
            for kw, label in decision_keywords.items():
                if kw in status_lower:
                    final_decision = label
                    break

        manuscript_data["final_outcome"] = {
            "status": status,
            "decision": final_decision,
            "decision_date": final_decision_date,
        }

    def extract_timeline_analytics(self, manuscript):
        timeline = manuscript.get("communication_timeline") or manuscript.get("audit_trail", [])
        if not timeline:
            return {}

        print(f"      📊 Extracting timeline analytics for {len(timeline)} events...")

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
                parsed_date = None
                ds = str(date_str)
                try:
                    if "GMT" in ds or "EDT" in ds:
                        clean_date = ds.replace(" GMT", "").replace(" EDT", "")
                        parsed_date = datetime.strptime(clean_date, "%d-%b-%Y %I:%M %p").replace(
                            tzinfo=timezone.utc
                        )
                    else:
                        try:
                            parsed_date = datetime.fromisoformat(ds.replace("Z", "+00:00"))
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%d-%b-%Y %H:%M"):
                                try:
                                    parsed_date = datetime.strptime(ds.strip(), fmt).replace(
                                        tzinfo=timezone.utc
                                    )
                                    break
                                except ValueError:
                                    continue
                except Exception:
                    pass
                if parsed_date:
                    event_dates.append(parsed_date)
                    parsed_dates[idx] = parsed_date

        if event_dates:
            event_dates.sort()
            span = (event_dates[-1] - event_dates[0]).days
            analytics["communication_span_days"] = span

        REMINDER_TYPES = {"reminder", "deadline_reminder", "Reminder"}
        RESPONSE_TYPES = {"review_submission", "review_received", "Report Submission"}
        INVITATION_TYPES = {"reviewer_invitation", "referee_invited", "Referee Invitation"}
        ACCEPTANCE_TYPES = {
            "reviewer_agreement",
            "reviewer_agreed",
            "referee_accepted",
            "Referee Acceptance",
        }

        referees = manuscript.get("referees", [])
        for referee in referees:
            ref_email = (referee.get("email") or "").lower()
            ref_name = (referee.get("name") or "").lower()
            ref_last = (
                ref_name.split(",")[0].strip()
                if "," in ref_name
                else ref_name.split()[-1]
                if ref_name.split()
                else ""
            )
            if not ref_email and not ref_last:
                continue

            def _is_ref_event(ev):
                ev_to = (ev.get("to") or "").lower()
                ev_desc = (
                    ev.get("description")
                    or ev.get("event")
                    or ev.get("raw_event")
                    or ev.get("subject")
                    or ""
                ).lower()
                if ref_email and (ref_email == ev_to or ref_email in ev_desc or ref_email in ev_to):
                    return True
                if ref_last and len(ref_last) > 2 and ref_last in ev_desc:
                    return True
                return False

            referee_events = [e for e in timeline if _is_ref_event(e)]
            metrics = {
                "response_time_days": 0,
                "reliability_score": 50,
                "reminders_received": 0,
                "responses_sent": 0,
                "quality_assessment": "unknown",
            }
            first_invite_date = None
            first_accept_date = None
            for ev in referee_events:
                ev_type = ev.get("type", "")
                ev_text = (
                    ev.get("description") or ev.get("event") or ev.get("subject") or ""
                ).lower()
                if ev_type in REMINDER_TYPES or "reminder" in ev_text or "remind" in ev_text:
                    metrics["reminders_received"] += 1
                if ev_type in RESPONSE_TYPES or "submitted" in ev_text or "completed" in ev_text:
                    metrics["responses_sent"] += 1
                ev_idx = timeline.index(ev) if ev in timeline else None
                ev_date = parsed_dates.get(ev_idx) if ev_idx is not None else None
                if ev_date:
                    if (
                        ev_type in INVITATION_TYPES
                        or "invite" in ev_text
                        or "invitation" in ev_text
                    ) and not first_invite_date:
                        first_invite_date = ev_date
                    if (
                        ev_type in ACCEPTANCE_TYPES or "agreed" in ev_text or "accepted" in ev_text
                    ) and not first_accept_date:
                        first_accept_date = ev_date
            if first_invite_date and first_accept_date:
                metrics["response_time_days"] = (first_accept_date - first_invite_date).days
            if metrics["responses_sent"] > 0:
                score = 100 - (metrics["reminders_received"] * 20)
                score = max(0, min(100, score))
                metrics["reliability_score"] = score
            ref_key = ref_email or ref_name
            analytics["referee_metrics"][ref_key] = metrics

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
                "hour_distribution": hour_counts,
                "most_active_period": f"{peak_weekday} {peak_hour}:00",
            }

        invitation_events = [
            (idx, e)
            for idx, e in enumerate(timeline)
            if e.get("type") in INVITATION_TYPES
            or "invite"
            in (e.get("description") or e.get("event") or e.get("subject") or "").lower()
            or "invitation"
            in (e.get("description") or e.get("event") or e.get("subject") or "").lower()
        ]
        response_events = [
            (idx, e)
            for idx, e in enumerate(timeline)
            if e.get("type") in ACCEPTANCE_TYPES
            or "accept"
            in (e.get("description") or e.get("event") or e.get("subject") or "").lower()
            or "agree" in (e.get("description") or e.get("event") or e.get("subject") or "").lower()
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
                        earliest_ri, earliest_response = min(
                            later_responses, key=lambda x: parsed_dates[x[0]]
                        )
                        response_time = (parsed_dates[earliest_ri] - inv_date).days
                        response_times.append(response_time)
            if response_times:
                analytics["response_time_analysis"] = {
                    "average_response_days": sum(response_times) / len(response_times),
                    "fastest_response_days": min(response_times),
                    "slowest_response_days": max(response_times),
                    "response_count": len(response_times),
                }

        reminder_events = [
            (idx, e)
            for idx, e in enumerate(timeline)
            if e.get("type") in REMINDER_TYPES
            or "reminder"
            in (e.get("description") or e.get("event") or e.get("subject") or "").lower()
            or "remind"
            in (e.get("description") or e.get("event") or e.get("subject") or "").lower()
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
                            or "response"
                            in (
                                e.get("description") or e.get("event") or e.get("subject") or ""
                            ).lower()
                            or "submit"
                            in (
                                e.get("description") or e.get("event") or e.get("subject") or ""
                            ).lower()
                            or "agreed"
                            in (
                                e.get("description") or e.get("event") or e.get("subject") or ""
                            ).lower()
                        )
                    ]
                    if responses_after:
                        effective_reminders += 1
            analytics["reminder_effectiveness"] = {
                "total_reminders": total_reminders,
                "effective_reminders": effective_reminders,
                "effectiveness_rate": effective_reminders / total_reminders
                if total_reminders > 0
                else 0,
            }

        print(
            f"      ✅ Timeline analytics: {analytics['total_events']} events, {analytics['communication_span_days']} days span"
        )
        return analytics

    def _compute_referee_statistics(self, manuscript_data: Dict):
        referees = manuscript_data.get("referees", [])
        audit = manuscript_data.get(
            "audit_trail", manuscript_data.get("communication_timeline", [])
        )
        if not referees:
            return

        for ref in referees:
            stats = {}
            ref_name = ref.get("name", "")
            ref_email = (ref.get("email") or "").lower()
            if not ref_name and not ref_email:
                continue

            inv_date = (
                ref.get("invitation_date", "")
                or ref.get("inv_date", "")
                or ref.get("date_invited", "")
            )
            resp_date = (
                ref.get("agreed_date", "")
                or ref.get("response_date", "")
                or ref.get("date_agreed", "")
            )
            if inv_date and resp_date:
                try:
                    d1 = datetime.strptime(inv_date, "%d-%b-%Y")
                    d2 = datetime.strptime(resp_date, "%d-%b-%Y")
                    stats["invitation_to_response_days"] = (d2 - d1).days
                except Exception:
                    pass

            ref_name_lower = ref_name.lower()
            last_name = (
                ref_name_lower.split(",")[0].strip()
                if "," in ref_name_lower
                else ref_name_lower.split()[-1]
                if ref_name_lower.split()
                else ""
            )

            reminder_count = 0
            invite_event_date = None
            agree_event_date = None
            submit_event_date = None
            for event in audit:
                ev = (
                    event.get("raw_event", "")
                    or event.get("event", "")
                    or event.get("description", "")
                ).lower()
                ev_date_str = str(event.get("date", "") or "")
                ev_type = event.get("type", "")
                ev_to = (event.get("to") or "").lower()
                is_this_ref = False
                if last_name and last_name in ev:
                    is_this_ref = True
                if ref_email and (ref_email == ev_to or ref_email in ev):
                    is_this_ref = True
                if not is_this_ref:
                    continue

                if ev_type in ("reminder", "deadline_reminder") or "remind" in ev:
                    reminder_count += 1
                if not invite_event_date:
                    if (
                        ev_type == "reviewer_invitation"
                        or ("invite" in ev and "pending" in ev)
                        or "invitation" in ev
                    ):
                        invite_event_date = parse_ev_date(ev_date_str)
                if not agree_event_date:
                    if (
                        ev_type in ("reviewer_agreement", "reviewer_agreed")
                        or "agreed" in ev
                        or "accepted" in ev
                    ):
                        agree_event_date = parse_ev_date(ev_date_str)
                if not submit_event_date:
                    if ev_type in ("review_submission", "review_received"):
                        submit_event_date = parse_ev_date(ev_date_str)
                    elif "became completed" in ev and any(
                        x in ev for x in ["accept", "reject", "revision", "minor", "major"]
                    ):
                        submit_event_date = parse_ev_date(ev_date_str)

            stats["reminders_received"] = reminder_count

            if invite_event_date and agree_event_date:
                stats["invitation_to_agreement_days"] = (agree_event_date - invite_event_date).days
            if agree_event_date and submit_event_date:
                stats["agreement_to_submission_days"] = (submit_event_date - agree_event_date).days
            if invite_event_date and submit_event_date:
                stats["total_review_days"] = (submit_event_date - invite_event_date).days

            stats["was_author_recommended"] = ref.get("author_recommended", False)

            if ref.get("r_score") is not None:
                stats["r_score"] = ref["r_score"]
            if ref.get("current_assignments") is not None:
                stats["current_assignments"] = ref["current_assignments"]

            if stats:
                ref["statistics"] = stats

    # ------------------------------------------------------------------
    # Email popup extraction (shared helper)
    # ------------------------------------------------------------------

    def extract_email_from_popup_window(self):
        try:
            time.sleep(1)

            try:
                self.driver.switch_to.frame("mainemailwindow")
                email_inputs = self.driver.find_elements(By.XPATH, "//input[@name='TO_EMAIL']")
                if email_inputs:
                    value = email_inputs[0].get_attribute("value")
                    if value and "@" in value:
                        self.driver.switch_to.default_content()
                        return value
                self.driver.switch_to.default_content()
            except Exception:
                try:
                    self.driver.switch_to.default_content()
                except Exception:
                    pass

            frames = self.driver.find_elements(By.TAG_NAME, "frame")
            for i in range(len(frames)):
                try:
                    self.driver.switch_to.frame(i)
                    email_inputs = self.driver.find_elements(By.XPATH, "//input[@name='TO_EMAIL']")
                    if email_inputs:
                        value = email_inputs[0].get_attribute("value")
                        if value and "@" in value:
                            self.driver.switch_to.default_content()
                            return value
                    self.driver.switch_to.default_content()
                except Exception:
                    try:
                        self.driver.switch_to.default_content()
                    except Exception:
                        pass

            page_text = self.driver.page_source
            if "@" in page_text:
                email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
                emails = re.findall(email_pattern, page_text)
                for email in emails:
                    if not any(
                        skip in email.lower()
                        for skip in ["noreply", "donotreply", "manuscriptcentral"]
                    ):
                        return email

        except Exception as e:
            print(f"         ⚠️ Popup email extraction error: {e}")

        return None

    # ------------------------------------------------------------------
    # Abstract methods (subclasses must implement)
    # ------------------------------------------------------------------

    def run(self) -> List[Dict]:
        raise NotImplementedError("Subclasses must implement run()")
