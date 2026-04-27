import atexit
import base64
import json
import os
import random
import re
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common.exceptions import (
    NoAlertPresentException,
    NoSuchElementException,
    NoSuchFrameException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin
from core.web_enrichment import enrich_people_from_web

try:
    from core.gmail_search import GmailSearchManager

    GMAIL_SEARCH_AVAILABLE = True
except ImportError:
    GMAIL_SEARCH_AVAILABLE = False


from core.scholarone_utils import with_retry


class EMExtractor(CachedExtractorMixin):
    JOURNAL_CODE = ""
    JOURNAL_NAME = ""
    BASE_URL = ""
    ALT_URL = ""
    MANUSCRIPT_PATTERN = r""
    CATEGORIES = []
    MAX_MANUSCRIPTS = 50
    CREDENTIAL_PREFIX = ""
    EDITOR_ROLE = "editor"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.init_cached_extractor(self.JOURNAL_CODE)
        self.setup_directories()
        self.setup_chrome_options()
        self.driver = None
        self.wait = None
        self.original_window = None
        self.manuscripts_data = []
        self._current_manuscript_id = ""
        self._last_exception_msg = ""
        self._in_content_frame = False

        self.username = os.environ.get(f"{self.CREDENTIAL_PREFIX}_USERNAME") or os.environ.get(
            f"{self.CREDENTIAL_PREFIX}_EMAIL", ""
        )
        self.password = os.environ.get(f"{self.CREDENTIAL_PREFIX}_PASSWORD", "")

        atexit.register(self.cleanup_driver)

    def setup_chrome_options(self):
        self.chrome_options = uc.ChromeOptions()
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        self.chrome_options.add_argument("--disable-popup-blocking")
        self.chrome_options.add_argument("--window-size=1400,900")

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
                self.driver.set_window_size(1400, 900)
            except Exception:
                pass
        self.driver.set_page_load_timeout(120)
        self.driver.implicitly_wait(10)
        self.wait = WebDriverWait(self.driver, 30)
        self.original_window = self.driver.current_window_handle
        self._in_content_frame = False
        print(f"🖥️  Browser configured for {self.JOURNAL_CODE}")

    # ── Frame management ──────────────────────────────────────

    def switch_to_content_frame(self) -> bool:
        if self._in_content_frame:
            return True
        try:
            self.driver.switch_to.default_content()
            self.driver.switch_to.frame("content")
            self._in_content_frame = True
            return True
        except (NoSuchFrameException, WebDriverException):
            try:
                self.driver.switch_to.default_content()
                iframe = self.driver.find_element(By.ID, "content")
                self.driver.switch_to.frame(iframe)
                self._in_content_frame = True
                return True
            except Exception:
                return False

    def switch_to_default(self):
        try:
            self.driver.switch_to.default_content()
        except Exception:
            pass
        self._in_content_frame = False

    # ── Utility methods ───────────────────────────────────────

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
            print(f"   ⚠️  Alert: {alert.text}")
            alert.accept()
        except (NoAlertPresentException, Exception):
            pass

    def _wait_for_page_load(self, timeout: int = 15):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except Exception:
            pass

    def _save_debug_html(self, label: str):
        try:
            debug_dir = Path(self.output_dir) / "debug"
            debug_dir.mkdir(parents=True, exist_ok=True)
            filepath = debug_dir / f"{self.JOURNAL_CODE.lower()}_{label}.html"
            with open(filepath, "w") as f:
                f.write(self.driver.page_source)
        except Exception:
            pass

    # ── Login ─────────────────────────────────────────────────

    @with_retry(max_attempts=3, delay=3.0)
    def login(self) -> bool:
        if not self.username or not self.password:
            print("❌ Missing credentials")
            return False

        login_url = f"{self.BASE_URL}/default.aspx"
        print(f"🔐 Logging in to {login_url}")
        self.driver.get(login_url)
        self.smart_wait(4)

        self.driver.switch_to.frame("content")
        self.driver.switch_to.frame("login")
        print("   ✅ In login iframe")

        username_field = None
        for sel in ["#username", "input[name='username']", "input[type='text']"]:
            try:
                username_field = self.driver.find_element(By.CSS_SELECTOR, sel)
                break
            except NoSuchElementException:
                continue

        password_field = None
        for sel in [
            "#passwordTextbox",
            "input[name='password']",
            "input[type='password']",
        ]:
            try:
                password_field = self.driver.find_element(By.CSS_SELECTOR, sel)
                break
            except NoSuchElementException:
                continue

        if not username_field or not password_field:
            print("   ❌ Login fields not found")
            self._save_debug_html("login_fields_missing")
            self.switch_to_default()
            return False

        username_field.clear()
        username_field.send_keys(self.username)
        time.sleep(0.3)
        password_field.clear()
        password_field.send_keys(self.password)
        time.sleep(0.3)

        login_btn = None
        for sel in ["#loginButton", "input[type='submit']", "input[value='Login']"]:
            try:
                login_btn = self.driver.find_element(By.CSS_SELECTOR, sel)
                break
            except NoSuchElementException:
                continue

        if login_btn:
            self.driver.execute_script("arguments[0].click()", login_btn)
            print("   ✅ Clicked login button")
        else:
            try:
                self.driver.execute_script("doLogin('nobody')")
                print("   ✅ Called doLogin()")
            except Exception:
                from selenium.webdriver.common.keys import Keys

                password_field.send_keys(Keys.RETURN)
                print("   ✅ Pressed Enter")

        self.smart_wait(8)
        self.switch_to_default()

        if not self._verify_login():
            if self.ALT_URL:
                print(f"   ⚠️ Trying alternate URL: {self.ALT_URL}")
                self.driver.get(self.ALT_URL)
                self.smart_wait(5)
                if not self._verify_login():
                    return False
            else:
                return False

        if not self._select_editor_role():
            print("   ⚠️ Could not switch to editor role")

        return True

    def _verify_login(self) -> bool:
        try:
            src = self.driver.page_source
            if "Logout" in src or "Log Out" in src or "logout" in src.lower():
                print("   ✅ Login verified — logout link found")
                return True
        except Exception:
            pass
        return False

    def _select_editor_role(self) -> bool:
        """Switch the user to the configured editor role.

        Editorial Manager UIs vary by tenant + version: the dropdown can
        be a `<select id="RoleDropdown">` on the main page, in an iframe,
        or absent entirely (when the user has only one role). We also
        accept the case where the user is already on an editor dashboard
        (no dropdown needed). Returns True iff the role is now editor or
        a switch is unnecessary.
        """
        self.switch_to_default()

        # Step 1: try every known frame, look for a role dropdown by id
        # OR by name. EM tenants use both forms.
        frames_to_try: list = [None]  # default content
        try:
            for frame in self.driver.find_elements(By.TAG_NAME, "iframe"):
                frames_to_try.append(frame)
            for frame in self.driver.find_elements(By.TAG_NAME, "frame"):
                frames_to_try.append(frame)
        except Exception:
            pass

        dropdown_probe = (
            "var dd = document.getElementById('RoleDropdown') "
            "|| document.querySelector('select[name=\"RoleDropdown\"]') "
            "|| document.querySelector('select[id*=\"Role\"]') "
            "|| document.querySelector('select[name*=\"Role\"]'); "
            "if (!dd) return null; "
            "return JSON.stringify({"
            "  id: dd.id || '', name: dd.name || '', "
            "  value: dd.value, "
            "  options: Array.from(dd.options || []).map(function(o){return {value:o.value,text:o.text};})"
            "});"
        )

        found_in_frame = None
        dd_info = None
        for frame in frames_to_try:
            try:
                self.switch_to_default()
                if frame is not None:
                    self.driver.switch_to.frame(frame)
                raw = self.driver.execute_script(dropdown_probe)
                if raw:
                    import json as _json

                    dd_info = _json.loads(raw)
                    found_in_frame = frame
                    break
            except Exception:
                continue
        # Reset frame context
        self.switch_to_default()

        if dd_info is None:
            # No dropdown anywhere — check whether we're already on the
            # editor menu, in which case there's nothing to switch.
            print("   ⚠️ No RoleDropdown found — checking if already on editor menu")
            try:
                if self.switch_to_content_frame():
                    src = self.driver.page_source or ""
                    self.switch_to_default()
                    if (
                        "EditorMainMenu" in src
                        or "EditorsMainMenu" in src
                        or "aries-folder-item" in src
                    ):
                        print("   ✅ Already on editor dashboard — role switch unnecessary")
                        return True
            except Exception:
                self.switch_to_default()
            return False

        current = dd_info.get("value", "")
        options = dd_info.get("options", [])
        opts_summary = ", ".join(
            f"{o.get('value','')}={o.get('text','')[:30]}" for o in options[:5]
        )
        print(f"   Current role: {current!r}; options: {opts_summary}")

        if current == self.EDITOR_ROLE:
            print("   ✅ Already in editor role")
            return True

        # Try to match EDITOR_ROLE against option values; if our literal
        # value isn't present, fall back to fuzzy match by visible text
        # ("Editor", "Associate Editor", etc.)
        target_value = None
        for o in options:
            if o.get("value", "") == self.EDITOR_ROLE:
                target_value = self.EDITOR_ROLE
                break
        if target_value is None:
            for o in options:
                txt_lower = o.get("text", "").lower()
                if "editor" in txt_lower and "select" not in txt_lower:
                    target_value = o.get("value", "")
                    print(
                        f"   ℹ️ Configured EDITOR_ROLE={self.EDITOR_ROLE!r} not in dropdown; "
                        f"falling back to {o.get('text','')!r} (value={target_value!r})"
                    )
                    break
        if target_value is None:
            print("   ⚠️ No editor-like option in RoleDropdown — staying on current role")
            return False

        # Switch into the frame where we found it (if any) for the postback
        try:
            self.switch_to_default()
            if found_in_frame is not None:
                self.driver.switch_to.frame(found_in_frame)
            self.driver.execute_script(
                f"""
                var dd = document.getElementById('RoleDropdown')
                  || document.querySelector('select[name="RoleDropdown"]')
                  || document.querySelector('select[id*="Role"]')
                  || document.querySelector('select[name*="Role"]');
                if (!dd) return;
                dd.value = '{target_value}';
                dd.dispatchEvent(new Event('change', {{bubbles: true}}));
                if (typeof closeSysAdmin === 'function') closeSysAdmin();
                if (typeof __doPostBack === 'function') {{
                    setTimeout(function() {{ __doPostBack(dd.id || dd.name || 'RoleDropdown',''); }}, 0);
                }}
                """
            )
            self.switch_to_default()
            print(f"   ✅ Switched to role: {target_value}")
            self.smart_wait(10)
            self._save_debug_html("after_role_switch")
            return True

        except Exception as e:
            self.switch_to_default()
            print(f"   ⚠️ Role switch error: {str(e)[:80]}")
            return False

    # ── Navigation ────────────────────────────────────────────

    def _ensure_dashboard_loaded(self) -> bool:
        for attempt in range(3):
            self.smart_wait(3)
            if self.switch_to_content_frame():
                src = self.driver.page_source
                if (
                    "aries-folder-item" in src
                    or "EditorMainMenu" in src
                    or "EditorsMainMenu" in src
                ):
                    print("   ✅ Editor dashboard loaded")
                    self.switch_to_default()
                    return True
                if "RequiredRegistrationQuestions" in self.driver.current_url:
                    print("   ⚠️ Registration questions page — waiting for redirect")
                    self.smart_wait(5)
                    continue
            self.switch_to_default()
            if attempt < 2:
                print(f"   ⚠️ Dashboard not loaded (attempt {attempt + 1}), reloading...")
                self.driver.get(f"{self.BASE_URL}/EditorsMainMenu.aspx")
                self.smart_wait(5)

        print("   ❌ Dashboard failed to load")
        return False

    @with_retry(max_attempts=2, delay=2.0)
    def navigate_to_ae_dashboard(self) -> bool:
        print("📋 Navigating to AE/Editor dashboard...")
        self.switch_to_default()

        current = self.driver.execute_script(
            "var dd = document.getElementById('RoleDropdown');" "return dd ? dd.value : null;"
        )
        if current and current != self.EDITOR_ROLE:
            self._select_editor_role()

        return self._ensure_dashboard_loaded()

    def discover_categories(self) -> list[dict[str, str]]:
        print("📂 Discovering manuscript categories...")
        categories = []

        if not self.switch_to_content_frame():
            return categories

        try:
            folder_items = self.driver.find_elements(By.CSS_SELECTOR, "aries-folder-item")

            for item in folder_items:
                try:
                    text = self.safe_get_text(item)
                    nvgurl = item.get_attribute("nvgurl") or ""
                    link_id = item.get_attribute("link-id") or ""
                    green = item.get_attribute("green") or "0"
                    orange = item.get_attribute("orange") or "0"
                    red = item.get_attribute("red") or "0"

                    total = int(green) + int(orange) + int(red)

                    name_match = re.match(r"^(.+?)\s*\((\d+)\)", text)
                    if name_match:
                        name = name_match.group(1).strip()
                        count = int(name_match.group(2))
                    else:
                        name = text.strip()
                        count = total

                    if count > 0:
                        categories.append(
                            {
                                "name": name,
                                "count": count,
                                "nvgurl": nvgurl,
                                "link_id": link_id,
                            }
                        )
                        print(f"   📁 {name}: {count} manuscripts → {nvgurl}")
                except Exception:
                    continue

        except Exception as e:
            print(f"   ⚠️ Folder discovery error: {str(e)[:60]}")

        self.switch_to_default()

        if self.CATEGORIES:
            categories = [
                c
                for c in categories
                if any(w.lower() in c["name"].lower() for w in self.CATEGORIES)
            ]
            if categories:
                print(f"   🔍 Filtered to: {', '.join(c['name'] for c in categories)}")

        if not categories:
            print("   ⚠️ No categories with manuscripts found")

        return categories

    def collect_manuscript_ids(self, category: dict) -> list[dict[str, str]]:
        name = category["name"]
        nvgurl = category["nvgurl"]
        print(f"   📄 Collecting manuscripts from: {name}")

        if not self.switch_to_content_frame():
            return []

        manuscripts = []

        try:
            if nvgurl and nvgurl != "javascript:void(0);":
                full_url = f"{self.BASE_URL}/{nvgurl}"
                self.switch_to_default()
                self.driver.get(full_url)
                self.smart_wait(5)
                if not self.switch_to_content_frame():
                    return []
            else:
                try:
                    link = self.driver.find_element(
                        By.CSS_SELECTOR,
                        f"aries-folder-item[link-id='{category['link_id']}']",
                    )
                    self.safe_click(link)
                    self.smart_wait(5)
                except Exception:
                    pass

            self._save_debug_html(f"folder_{name.replace(' ', '_')}")
            src = self.driver.page_source
            soup = BeautifulSoup(src, "lxml")

            pattern = re.compile(self.MANUSCRIPT_PATTERN) if self.MANUSCRIPT_PATTERN else None

            rows = soup.find_all("tr", id=re.compile(r"^row\d+"))

            nfr_rows = soup.find_all("tr", id=re.compile(r"^nfr\d+"))
            if nfr_rows:
                nfr_col_map = {}
                nfr_header = None
                for cr in soup.find_all("tr", class_="colresize-row"):
                    nxt = cr.find_next_sibling("tr")
                    if nxt and nxt.get("id", "").startswith("nfr"):
                        nfr_header = cr
                        break
                if nfr_header:
                    for ci, cell in enumerate(nfr_header.find_all("td")):
                        uname = cell.get("data-uniquename", "")
                        if uname and not uname.startswith("_"):
                            nfr_col_map[uname] = ci

                fr_by_index = {}
                for fr in soup.find_all("tr", id=re.compile(r"^fr\d+")):
                    ri = fr.get("data-rowindex", "")
                    if ri:
                        fr_by_index[ri] = fr

                rows = rows + nfr_rows

            if not rows:
                rows = [r for r in soup.find_all("tr") if pattern and pattern.search(r.get_text())]

            for row in rows:
                cells = row.find_all("td")
                row_text = row.get_text()
                if not pattern:
                    continue
                match = pattern.search(row_text)
                if not match:
                    continue

                ms_id = match.group(0)
                if ms_id in [m["manuscript_id"] for m in manuscripts]:
                    continue

                ms_info = {
                    "manuscript_id": ms_id,
                    "category": name,
                    "folder_url": f"{self.BASE_URL}/{nvgurl}" if nvgurl else "",
                    "row_text": row_text.strip()[:300],
                }

                cell_texts = [c.get_text(separator=" ").strip() for c in cells]
                ms_info["row_cells"] = cell_texts

                is_nfr = row.get("id", "").startswith("nfr")

                if is_nfr and nfr_col_map:
                    field_map = {
                        "ArticleType": "article_type",
                        "ArticleTitle": "title",
                        "AuthorName": "author",
                        "InitialDateSubmitted": "submission_date",
                        "StatusDate": "status_date",
                        "CurrentStatus": "status",
                    }
                    for col_name, field in field_map.items():
                        idx = nfr_col_map.get(col_name)
                        if idx is not None and idx < len(cell_texts):
                            val = cell_texts[idx]
                            if val:
                                ms_info[field] = val

                    ri = row.get("data-rowindex", "")
                    fr_row = fr_by_index.get(ri)
                    if fr_row:
                        self._extract_action_links(ms_info, fr_row)

                    docid = row.get("data-identity", "")
                    if docid:
                        ms_info["docid"] = docid
                else:
                    first_cell_html = str(cells[0]) if cells else ""
                    has_action_cell = (
                        "viewPDFs" in first_cell_html
                        or "ReviewerSelectionSummary" in first_cell_html
                        or "popupDetailsWindow" in first_cell_html
                    )
                    off = 1 if has_action_cell else 0

                    if len(cell_texts) > off + 5:
                        ms_info["article_type"] = cell_texts[off + 1]
                        ms_info["title"] = cell_texts[off + 2]
                        ms_info["author"] = cell_texts[off + 3]
                        ms_info["submission_date"] = cell_texts[off + 4]
                        ms_info["status_date"] = cell_texts[off + 5]
                    if len(cell_texts) > off + 6:
                        ms_info["status"] = cell_texts[off + 6]

                    self._extract_action_links(ms_info, row)

                hover_div = row.find("div", class_="reviewerHoverDetails")
                if hover_div:
                    ms_info["reviewer_summary_html"] = str(hover_div)
                    hover_text = hover_div.get_text(separator=", ").strip()
                    ms_info["reviewer_summary"] = hover_text

                manuscripts.append(ms_info)

            if not manuscripts and pattern:
                all_matches = pattern.findall(src)
                for ms_id in set(all_matches):
                    if ms_id not in [m["manuscript_id"] for m in manuscripts]:
                        manuscripts.append(
                            {
                                "manuscript_id": ms_id,
                                "href": "",
                                "category": name,
                            }
                        )

            print(f"      Found {len(manuscripts)} manuscripts in {name}")

        except Exception as e:
            print(f"      ⚠️ Collection error: {str(e)[:60]}")

        self.switch_to_default()
        return manuscripts[: self.MAX_MANUSCRIPTS]

    def _extract_action_links(self, ms_info: dict, action_row) -> None:
        for cell in action_row.find_all("td"):
            cell_html = str(cell)
            has_links = any(
                kw in cell_html
                for kw in (
                    "viewPDFs",
                    "viewEditorPDFs",
                    "popupDetailsWindow",
                    "PopupHistoryWindow",
                    "popupHistoryWindow",
                    "viewReviewsAndComments",
                    "ReviewerSelectionSummary",
                    "PopupFileInventoryWindow",
                    "viewSubmissionFiles",
                )
            )
            if not has_links:
                continue
            for a in cell.find_all("a", href=True):
                href = a.get("href", "")
                if "ReviewerSelectionSummary" in href:
                    ms_info["reviewer_summary_url"] = href
                elif "viewReviewsAndComments" in href:
                    ms_info["reviews_js"] = href
                elif "EditorDecision" in href:
                    ms_info["decision_url"] = href
                elif "popupDetailsWindow" in href:
                    ms_info["details_js"] = href
                elif "PopupHistoryWindow" in href or "popupHistoryWindow" in href:
                    ms_info["history_js"] = href
                elif "PopupFileInventoryWindow" in href or "viewSubmissionFiles" in href:
                    ms_info["file_inventory_js"] = href
                elif "viewPDFs" in href or "viewEditorPDFs" in href:
                    ms_info["view_pdf_js"] = href

            docid_match = re.search(r"(?:docid|docID)=(\d+)", cell_html)
            if not docid_match:
                docid_match = re.search(
                    r"(?:viewReviewsAndComments|popupDetailsWindow|viewEditorPDFs|viewPDFs)\((\d+)",
                    cell_html,
                )
            if docid_match:
                ms_info.setdefault("docid", docid_match.group(1))
            msid_match = re.search(r"msid=(\{[^}]+\})", cell_html)
            if msid_match:
                ms_info["msid_guid"] = msid_match.group(1)
            elif not ms_info.get("msid_guid"):
                guid_match = re.search(
                    r"'(\{?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}?)'",
                    cell_html,
                )
                if guid_match:
                    g = guid_match.group(1)
                    if not g.startswith("{"):
                        g = "{" + g + "}"
                    ms_info["msid_guid"] = g
            break

    # ── Manuscript detail extraction ──────────────────────────

    @with_retry(max_attempts=2, delay=3.0)
    def extract_manuscript_detail(self, ms_info: dict) -> dict | None:
        ms_id = ms_info["manuscript_id"]
        self._current_manuscript_id = ms_id
        print(f"\n   📄 Extracting: {ms_id}")

        manuscript = {
            "manuscript_id": ms_id,
            "journal": self.JOURNAL_CODE,
            "platform": "Editorial Manager",
            "category": ms_info.get("category", ""),
            "metadata": {},
            "authors": [],
            "referees": [],
            "documents": {"files": []},
            "audit_trail": [],
            "extracted_at": datetime.now().isoformat(),
        }

        self._populate_from_row_data(manuscript, ms_info)

        # Order matters: summary page first (lists all assigned referees
        # with status), THEN the reviews page (has the per-review detail
        # popup links + completed-review HTML). Both must run when both
        # are present — without the reviews page, review_detail_links
        # stays empty and `_extract_referee_reports` is skipped, so
        # completed reviews never produce a canonical `referee.reports[0]`.
        if ms_info.get("reviewer_summary_url"):
            self._extract_referees_from_summary_page(manuscript, ms_info)
        if ms_info.get("reviews_js"):
            self._extract_referees_from_reviews_page(manuscript, ms_info)

        if ms_info.get("details_js"):
            self._extract_details_from_popup(manuscript, ms_info)

        if ms_info.get("history_js"):
            self._extract_audit_trail_from_history(manuscript, ms_info)

        self._backfill_referee_dates_from_audit_trail(manuscript)

        if ms_info.get("review_detail_links"):
            self._extract_referee_reports(manuscript, ms_info)

        self._extract_reviewer_attachments(manuscript, ms_info)

        refs_need_contact = [
            r
            for r in manuscript.get("referees", [])
            if r.get("people_id") and not (r.get("email") and r.get("affiliation"))
        ]
        if refs_need_contact and ms_info.get("docid"):
            self._extract_referee_contacts(manuscript, ms_info)

        if ms_info.get("file_inventory_js"):
            self._extract_documents_from_inventory(manuscript, ms_info)

        self._compute_referee_statistics(manuscript)
        self._compute_peer_review_milestones(manuscript)

        title = manuscript.get("metadata", {}).get("title", ms_id)
        n_refs = len(manuscript.get("referees", []))
        n_auths = len(manuscript.get("authors", []))
        print(f"      ✅ {ms_id}: {n_refs} referees, {n_auths} authors — {title[:50]}")

        return manuscript

    def _populate_from_row_data(self, manuscript: dict, ms_info: dict):
        metadata = manuscript["metadata"]

        metadata["manuscript_number"] = ms_info.get("manuscript_id", "")
        metadata["article_type"] = ms_info.get("article_type", "")

        if ms_info.get("title"):
            metadata["title"] = ms_info["title"]
            manuscript["title"] = ms_info["title"]
        else:
            manuscript["title"] = ms_info.get("manuscript_id", "")

        if ms_info.get("submission_date"):
            metadata["submission_date"] = ms_info["submission_date"]

        if ms_info.get("status_date"):
            metadata["status_date"] = ms_info["status_date"]

        if ms_info.get("status"):
            metadata["status"] = ms_info["status"]
            manuscript["status"] = ms_info["status"]

        if ms_info.get("author"):
            author_name = re.sub(r"\s+", " ", ms_info["author"]).strip()
            if author_name:
                manuscript["authors"].append({"name": author_name, "role": "corresponding_author"})

        if ms_info.get("reviewer_summary"):
            metadata["reviewer_summary"] = ms_info["reviewer_summary"]

        if ms_info.get("docid"):
            metadata["docid"] = ms_info["docid"]
        if ms_info.get("msid_guid"):
            metadata["msid_guid"] = ms_info["msid_guid"]

        manuscript["abstract"] = ""
        manuscript["keywords"] = []

    def _extract_referees_from_summary_page(self, manuscript: dict, ms_info: dict):
        reviewer_url = ms_info.get("reviewer_summary_url", "")
        if not reviewer_url:
            return

        try:
            if reviewer_url.startswith("http"):
                full_url = reviewer_url
            else:
                full_url = f"{self.BASE_URL}/{reviewer_url}"

            self.switch_to_default()
            self.driver.get(full_url)
            self.smart_wait(5)

            if not self.switch_to_content_frame():
                print("      ⚠️ Could not switch to content frame for reviewer summary")
                self.switch_to_default()
                return

            self._save_debug_html(f"reviewers_{ms_info['manuscript_id']}")

            page_text = self.driver.page_source
            soup = BeautifulSoup(page_text, "html.parser")

            invited_table = soup.find("table", id="tblInvitedReviewers")
            if invited_table:
                self._parse_invited_reviewers_table(manuscript, invited_table)
            else:
                self._extract_referees(manuscript, page_text, soup)
                if not manuscript["referees"]:
                    self._extract_referees_from_tables(manuscript, soup)

            self.switch_to_default()

        except Exception as e:
            print(f"      ⚠️ Reviewer summary page error: {str(e)[:80]}")
            self.switch_to_default()

    def _parse_invited_reviewers_table(self, manuscript: dict, table):
        referees = manuscript["referees"]
        rows = table.find_all("tr")

        for row in rows:
            if row.get("style") and "display:none" in row.get("style", ""):
                continue

            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            name_link = cells[0].find("a")
            if not name_link:
                continue

            name_text = name_link.get_text().strip()
            name = re.sub(r"\s*\(Reviewer\).*$", "", name_text).strip()
            if not name or len(name) < 2:
                continue
            if name in [r.get("name") for r in referees]:
                continue

            referee = {
                "name": name,
                "role": "referee",
                "status": "",
                "contact_date": "",
                "acceptance_date": "",
                "due_date": "",
                "received_date": "",
                "email": "",
            }

            status_cell = cells[1] if len(cells) > 1 else None
            if status_cell:
                status_text = status_cell.get_text(separator=" ").strip()

                if "Complete" in status_text or "Received" in status_text:
                    referee["status"] = "Complete"
                elif "Agreed" in status_text:
                    referee["status"] = "Agreed"
                elif "Invited" in status_text or "Pending" in status_text:
                    referee["status"] = "Invited"
                elif "Declined" in status_text:
                    referee["status"] = "Declined"
                elif "Overdue" in status_text:
                    referee["status"] = "Overdue"

                date_match = re.search(
                    r"\d{1,2}\s+\w{3}\s+\d{4}|\d{1,2}[-/]\w{3}[-/]\d{4}|\d{4}-\d{2}-\d{2}",
                    status_text,
                )
                if date_match:
                    date_str = date_match.group(0)
                    if referee["status"] == "Complete":
                        referee["received_date"] = date_str
                    elif referee["status"] == "Agreed":
                        referee["acceptance_date"] = date_str
                    elif referee["status"] in ("Invited", "Declined"):
                        referee["contact_date"] = date_str

            referees.append(referee)

    def _extract_referees_from_tables(self, manuscript: dict, soup: BeautifulSoup):
        referees = manuscript["referees"]

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            header_text = rows[0].get_text().lower()
            if not any(
                kw in header_text for kw in ["reviewer", "referee", "name", "status", "invited"]
            ):
                continue

            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                name = ""
                status = ""
                contact_date = ""
                acceptance_date = ""
                due_date = ""
                received_date = ""
                email = ""

                for cell in cells:
                    text = cell.get_text(separator=" ").strip()
                    email_link = cell.find("a", href=re.compile(r"mailto:", re.I))
                    if email_link:
                        email = email_link["href"].replace("mailto:", "").strip()
                        if not name:
                            name = email_link.get_text().strip() or text

                    name_link = cell.find("a")
                    if name_link and not name:
                        candidate = name_link.get_text().strip()
                        if candidate and len(candidate) > 2 and "@" not in candidate:
                            name = candidate

                cell_texts = [c.get_text(separator=" ").strip() for c in cells]

                if not name and cell_texts:
                    for ct in cell_texts:
                        if self._is_valid_referee_name(ct) and "@" not in ct:
                            name = ct
                            break

                if not name:
                    continue
                if name in [r.get("name") for r in referees]:
                    continue

                for ct in cell_texts:
                    ct_lower = ct.lower()
                    date_match = re.search(
                        r"\d{1,2}[-/ ]\w{3}[-/ ]\d{4}|\d{4}-\d{2}-\d{2}",
                        ct,
                    )
                    if "agree" in ct_lower or "accept" in ct_lower:
                        status = "Agreed"
                        if date_match:
                            acceptance_date = date_match.group(0)
                    elif "complet" in ct_lower or "receiv" in ct_lower:
                        status = "Complete"
                        if date_match:
                            received_date = date_match.group(0)
                    elif "declin" in ct_lower:
                        status = "Declined"
                    elif "invited" in ct_lower or "pending" in ct_lower:
                        status = "Invited"
                        if date_match:
                            contact_date = date_match.group(0)
                    elif "overdue" in ct_lower:
                        status = "Overdue"
                    elif date_match and not contact_date:
                        contact_date = date_match.group(0)

                    if "due" in ct_lower and date_match:
                        due_date = date_match.group(0)

                referee = {
                    "name": name,
                    "role": "referee",
                    "status": status,
                    "contact_date": contact_date,
                    "acceptance_date": acceptance_date,
                    "due_date": due_date,
                    "received_date": received_date,
                    "email": email,
                }
                referees.append(referee)

    def _extract_metadata(self, manuscript: dict, page_text: str, soup: BeautifulSoup):
        metadata = manuscript["metadata"]

        for label in ["Manuscript Number", "Manuscript No", "Article ID"]:
            el = soup.find(string=re.compile(label, re.I))
            if el:
                parent = el.find_parent()
                if parent:
                    text = parent.get_text(separator=" ").strip()
                    val = text.split(":", 1)[-1].strip() if ":" in text else ""
                    if val:
                        metadata["manuscript_number"] = val
                        break

        for label, key in [
            ("Title", "title"),
            ("Article Title", "title"),
            ("Manuscript Title", "title"),
            ("Abstract", "abstract"),
            ("Keywords", "keywords"),
        ]:
            el = soup.find(string=re.compile(f"^\\s*{label}\\s*$", re.I))
            if el:
                parent = el.find_parent()
                if parent:
                    sibling = parent.find_next_sibling()
                    if sibling:
                        val = sibling.get_text(separator=" ").strip()
                    else:
                        val = parent.get_text(separator=" ").strip()
                        val = val.replace(label, "").strip().lstrip(":").strip()
                    if val:
                        if key == "keywords":
                            metadata[key] = [k.strip() for k in re.split(r"[;,]", val) if k.strip()]
                        else:
                            metadata[key] = val[:2000]

        for label in ["Date Submitted", "Submission Date", "Original Submission"]:
            el = soup.find(string=re.compile(label, re.I))
            if el:
                parent = el.find_parent()
                if parent:
                    text = parent.get_text(separator=" ")
                    date_match = re.search(
                        r"\d{1,2}[-/]\w{3}[-/]\d{4}|\d{4}-\d{2}-\d{2}|\w+\s+\d{1,2},?\s+\d{4}",
                        text,
                    )
                    if date_match:
                        metadata["submission_date"] = date_match.group(0)
                        break

        for label in ["Current Status", "Status", "Decision"]:
            el = soup.find(string=re.compile(f"^\\s*{label}\\s*$", re.I))
            if el:
                parent = el.find_parent()
                if parent:
                    sibling = parent.find_next_sibling()
                    if sibling:
                        val = sibling.get_text(separator=" ").strip()
                    else:
                        val = parent.get_text(separator=" ").strip()
                        val = val.replace(label, "").strip().lstrip(":").strip()
                    if val and len(val) < 100:
                        metadata["status"] = val
                        manuscript["status"] = val
                        break

        manuscript["title"] = metadata.get("title", manuscript["manuscript_id"])
        manuscript["abstract"] = metadata.get("abstract", "")
        manuscript["keywords"] = metadata.get("keywords", [])

    def _extract_authors(self, manuscript: dict, page_text: str, soup: BeautifulSoup):
        authors = manuscript["authors"]

        for label in ["Author", "Author(s)", "Corresponding Author"]:
            el = soup.find(string=re.compile(f"^\\s*{label}", re.I))
            if el:
                parent = el.find_parent()
                if parent:
                    section = parent.find_parent()
                    if section:
                        links = section.find_all("a")
                        for a in links:
                            name = a.get_text().strip()
                            if (
                                name
                                and len(name) > 2
                                and name not in [au.get("name") for au in authors]
                            ):
                                author = {"name": name, "role": "author"}
                                href = a.get("href", "")
                                if "mailto:" in href:
                                    author["email"] = href.replace("mailto:", "")
                                authors.append(author)
                        if not authors:
                            text = section.get_text(separator="\n")
                            for line in text.split("\n"):
                                line = line.strip()
                                if len(line) > 3 and not any(
                                    kw in line.lower()
                                    for kw in ["author", "corresponding", "title", "abstract"]
                                ):
                                    if line not in [au.get("name") for au in authors]:
                                        authors.append({"name": line, "role": "author"})

    @staticmethod
    def _is_valid_referee_name(name: str) -> bool:
        if not name or len(name) < 4 or " " not in name.strip():
            return False
        if name[0].isdigit() or "(" in name or ")" in name:
            return False
        garbage_keywords = (
            "preference",
            "close",
            "register",
            "select",
            "summary",
            "decline",
            "display",
            "notes ",
            "invited",
            "status",
            "complete",
            "edit ",
            "view ",
            "reviewer",
            "submit",
            "assign",
            "flag",
            "terminate",
            "remind",
        )
        lower = name.lower()
        return not any(kw in lower for kw in garbage_keywords)

    def _extract_referees(self, manuscript: dict, page_text: str, soup: BeautifulSoup):
        referees = manuscript["referees"]

        reviewer_sections = soup.find_all(string=re.compile(r"Reviewer|Referee", re.I))

        for section_text in reviewer_sections:
            parent = section_text.find_parent()
            if not parent:
                continue

            container = (
                parent.find_parent("tr") or parent.find_parent("div") or parent.find_parent("table")
            )
            if not container:
                continue

            name_el = container.find("a")
            name = name_el.get_text().strip() if name_el else ""

            if not name:
                text = container.get_text(separator=" ").strip()
                name_match = re.search(
                    r"(?:Reviewer|Referee)\s*\d*\s*:?\s*(.+?)(?:\s*-|\s*\(|$)",
                    text,
                )
                if name_match:
                    name = name_match.group(1).strip()

            if not name or name in [r.get("name") for r in referees]:
                continue

            referee = {
                "name": name,
                "role": "referee",
                "status": "",
                "contact_date": "",
                "acceptance_date": "",
                "due_date": "",
                "received_date": "",
                "email": "",
            }

            block_text = container.get_text(separator=" ")

            status_patterns = [
                (r"(?:Status|Current Status)\s*:?\s*(.+?)(?:\s*$|\s{3})", "status"),
                (r"(?:Invited|Contacted)\s*:?\s*(\d{1,2}[-/]\w{3}[-/]\d{4})", "contact_date"),
                (r"(?:Agreed|Accepted)\s*:?\s*(\d{1,2}[-/]\w{3}[-/]\d{4})", "acceptance_date"),
                (r"(?:Due Date|Review Due)\s*:?\s*(\d{1,2}[-/]\w{3}[-/]\d{4})", "due_date"),
                (
                    r"(?:Received|Completed|Submitted)\s*:?\s*(\d{1,2}[-/]\w{3}[-/]\d{4})",
                    "received_date",
                ),
            ]

            for pattern, key in status_patterns:
                match = re.search(pattern, block_text, re.I)
                if match:
                    referee[key] = match.group(1).strip()

            email_el = container.find("a", href=re.compile(r"mailto:", re.I))
            if email_el:
                referee["email"] = email_el["href"].replace("mailto:", "").strip()

            referees.append(referee)

        if not referees:
            for cls_pattern in [
                "[class*='reviewer']",
                "[class*='Reviewer']",
                "[class*='referee']",
                ".reviewerHoverDetails",
            ]:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, cls_pattern)
                    for el in elements:
                        text = self.safe_get_text(el)
                        if text and len(text) > 3:
                            name = text.split("\n")[0].strip()
                            if not self._is_valid_referee_name(name):
                                continue
                            if name and name not in [r.get("name") for r in referees]:
                                referees.append(
                                    {
                                        "name": name,
                                        "role": "referee",
                                        "status": "",
                                    }
                                )
                except Exception:
                    continue

    def _extract_documents(self, manuscript: dict, soup: BeautifulSoup):
        files = manuscript["documents"]["files"]

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text().strip()
            if any(
                kw in href.lower()
                for kw in ["download", "pdf", "viewmanuscript", "view_manuscript", "getfile"]
            ):
                file_entry = {
                    "name": text or "Document",
                    "url": href if href.startswith("http") else f"{self.BASE_URL}/{href}",
                    "type": "pdf" if "pdf" in href.lower() else "document",
                }
                files.append(file_entry)

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
        if "latex" in content_type or ".tex" in url.lower():
            return ".tex"
        if "zip" in content_type or ".zip" in url.lower():
            return ".zip"
        return ".pdf"

    def _download_file_from_url(self, url: str, manuscript_id: str, doc_type: str) -> str | None:
        existing = self._check_existing_download(manuscript_id, doc_type, str(self.download_dir))
        if existing:
            print(f"         📦 [CACHE] Already downloaded: {os.path.basename(existing)}")
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
                print(f"            ❌ Fetch: {result['error']}")
                return None

            data = base64.b64decode(result["data"])
            content_type = result.get("type", "")
            file_size = len(data)

            if file_size < 50:
                return None

            ext = self._detect_file_extension(content_type, url, data[:100])
            safe_id = re.sub(r"[^\w\-.]", "_", manuscript_id)
            safe_type = re.sub(r"[^\w\-.]", "_", doc_type)
            filename = f"{safe_id}_{safe_type}{ext}"
            file_path = self.download_dir / filename

            if b"<html" in data[:200].lower() or b"<!doctype html" in data[:200].lower():
                html_text = data.decode("utf-8", errors="ignore")
                redirect_match = re.search(
                    r'location\.href\s*=\s*["\']([^"\']+(?:DOWNLOAD=TRUE|download\.aspx)[^"\']*)["\']',
                    html_text,
                )
                if redirect_match:
                    redirect_url = redirect_match.group(1)
                    if not redirect_url.startswith("http"):
                        redirect_url = f"{self.BASE_URL}/{redirect_url.lstrip('/')}"
                    return self._download_file_from_url(redirect_url, manuscript_id, doc_type)
                return None

            with open(file_path, "wb") as f:
                f.write(data)

            print(f"            ✅ Saved: {filename} ({file_size:,} bytes)")
            return str(file_path)

        except Exception as e:
            print(f"            ❌ Download error: {str(e)[:60]}")
            return None

    def _categorize_file(self, description: str, filename: str) -> str:
        desc_lower = (description + " " + filename).lower()
        if any(k in desc_lower for k in ("cover letter", "coverletter", "cover_letter")):
            return "cover_letter"
        if any(k in desc_lower for k in ("manuscript", "article", "main document", "main text")):
            return "manuscript"
        if any(k in desc_lower for k in ("response", "reply", "rebuttal", "point-by-point")):
            return "response_to_reviewers"
        if any(
            k in desc_lower for k in ("supplement", "appendix", "online resource", "supporting")
        ):
            return "supplementary"
        if any(k in desc_lower for k in ("figure", "fig")):
            return "figure"
        if any(k in desc_lower for k in ("table",)):
            return "table"
        if any(k in desc_lower for k in ("title page", "titlepage")):
            return "title_page"
        if any(k in desc_lower for k in ("conflict", "disclosure", "declaration")):
            return "disclosure"
        return "other"

    def _exec_em_js_and_capture_with_frame_fallback(
        self, js_href: str, ms_id: str, debug_prefix: str, folder_url: str = ""
    ) -> BeautifulSoup | None:
        soup = self._exec_em_js_and_capture(js_href, ms_id, debug_prefix, folder_url)
        if soup:
            return soup

        js_code = js_href.replace("javascript:", "").strip().rstrip(";")
        try:
            if folder_url:
                self.switch_to_default()
                self.driver.get(folder_url)
                self.smart_wait(3)

            if self.switch_to_content_frame():
                main_handle = self.driver.current_window_handle
                existing_handles = set(self.driver.window_handles)

                self.driver.execute_script(js_code)
                self.smart_wait(5)

                new_handles = set(self.driver.window_handles) - existing_handles
                if new_handles:
                    popup_handle = new_handles.pop()
                    self.driver.switch_to.window(popup_handle)
                    self.smart_wait(3)
                    src = self.driver.page_source
                    self._in_content_frame = False
                    self._save_debug_html(f"{debug_prefix}_{ms_id}")
                    self.driver.close()
                    self.driver.switch_to.window(main_handle)
                    self._in_content_frame = False
                    return BeautifulSoup(src, "lxml")
        except Exception as e:
            print(f"      ⚠️ Frame fallback failed ({debug_prefix}): {str(e)[:60]}")
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except Exception:
                pass
            self._in_content_frame = False

        return None

    def _extract_documents_from_inventory(self, manuscript: dict, ms_info: dict):
        js_href = ms_info.get("file_inventory_js")
        if not js_href:
            return

        ms_id = manuscript["manuscript_id"]
        folder_url = ms_info.get("folder_url", "")

        try:
            soup = self._exec_em_js_and_capture_with_frame_fallback(
                js_href, ms_id, "fileinventory", folder_url
            )
            if not soup:
                return

            debug_path = (
                self.output_dir
                / "debug"
                / f"{self.JOURNAL_CODE.lower()}_fileinventory_{ms_id}.html"
            )
            debug_path.parent.mkdir(parents=True, exist_ok=True)
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(str(soup))

            files = manuscript["documents"]["files"]
            download_count = 0
            seen_urls = set()

            grid_table = soup.find("table", id=re.compile(r"gridViewFiles"))
            if not grid_table:
                grid_table = soup.find("table", class_="datatable")
            tables_to_search = [grid_table] if grid_table else soup.find_all("table")

            for table in tables_to_search:
                for tr in table.find_all("tr"):
                    dl_span = tr.find("span", class_="downloadLink")
                    if not dl_span:
                        continue
                    dl_a = dl_span.find("a", href=True)
                    if not dl_a:
                        continue

                    href = dl_a.get("href", "")
                    if not href or href in seen_urls:
                        continue
                    seen_urls.add(href)

                    item_span = tr.find("span", id=re.compile(r"lblItem$"))
                    item_type = item_span.get_text(strip=True) if item_span else ""

                    all_cell_text = []
                    for dc in tr.find_all("td"):
                        if not dc.find("span", class_="downloadLink") and not dc.find(
                            "input", {"type": "checkbox"}
                        ):
                            dc_text = dc.get_text(strip=True)
                            if (
                                dc_text
                                and dc_text not in ("Download", "Preview")
                                and "Confirm" not in dc_text
                            ):
                                all_cell_text.append(dc_text)
                    description = " ".join(all_cell_text)

                    fn_span = tr.find("span", id=re.compile(r"lblFileName"))
                    filename = fn_span.get_text(strip=True) if fn_span else ""

                    sz_span = tr.find("span", id=re.compile(r"lblFileSize"))
                    size_text = sz_span.get_text(strip=True) if sz_span else ""

                    full_url = (
                        href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"
                    )
                    full_url = full_url.replace("&amp;", "&")

                    doc_type = self._categorize_file(item_type + " " + description, filename)
                    file_entry = {
                        "name": filename or description or "Document",
                        "description": item_type or description,
                        "url": full_url,
                        "type": doc_type,
                        "size": size_text,
                    }

                    downloaded = self._download_file_from_url(full_url, ms_id, doc_type)
                    if downloaded:
                        file_entry["local_path"] = downloaded
                        download_count += 1

                    files.append(file_entry)

            if download_count:
                print(f"      📥 Downloaded {download_count} files from inventory")
            elif files:
                print(f"      📋 Found {len(files)} files in inventory (0 downloaded)")

        except Exception as e:
            print(f"      ⚠️ File inventory extraction failed: {str(e)[:80]}")

    def _extract_reviewer_attachments(self, manuscript: dict, ms_info: dict):
        referees = manuscript.get("referees", [])
        if not referees:
            return

        ms_id = manuscript["manuscript_id"]
        files = manuscript["documents"]["files"]
        download_count = 0

        for ref in referees:
            reports = ref.get("reports", [])
            for report in reports:
                attachment_urls = report.get("_attachment_urls", [])
                for att in attachment_urls:
                    href = att.get("url", "")
                    if not href:
                        continue

                    full_url = (
                        href if href.startswith("http") else f"{self.BASE_URL}/{href.lstrip('/')}"
                    )
                    full_url = full_url.replace("&amp;", "&")

                    ref_name = re.sub(r"\s+", "_", ref.get("name", "referee")).strip("_")
                    ref_name = re.sub(r"[^\w\-.]", "", ref_name)
                    rev = report.get("revision", 0)
                    att_desc = att.get("description", "report")
                    att_name = att.get("filename", "")

                    doc_type = f"reviewer_attachment_{ref_name}_r{rev}"
                    file_entry = {
                        "name": att_name or att_desc or "Reviewer Attachment",
                        "description": att_desc,
                        "url": full_url,
                        "type": "reviewer_attachment",
                        "reviewer": ref.get("name", ""),
                        "revision": rev,
                    }

                    downloaded = self._download_file_from_url(full_url, ms_id, doc_type)
                    if downloaded:
                        file_entry["local_path"] = downloaded
                        download_count += 1
                        # Extract text from PDF/DOC attachments and merge
                        # into the canonical report dict so reviewers who
                        # uploaded their report still surface in raw_text /
                        # comments_to_author.
                        if downloaded.lower().endswith((".pdf", ".doc", ".docx")):
                            try:
                                from core.pdf_utils import populate_report_from_pdf

                                populate_report_from_pdf(
                                    report, downloaded, attachment_url=full_url
                                )
                            except Exception as e:
                                print(
                                    f"         ⚠️ Failed to extract text from reviewer attachment: {str(e)[:80]}"
                                )

                    files.append(file_entry)

                if "_attachment_urls" in report:
                    del report["_attachment_urls"]

        if download_count:
            print(f"      📎 Downloaded {download_count} reviewer attachments")

    def _build_audit_trail(self, manuscript: dict):
        audit_trail = manuscript["audit_trail"]

        try:
            history_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "History")
            if not history_links:
                history_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Action")
            if not history_links:
                history_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Audit")

            if history_links:
                self.safe_click(history_links[0])
                self.smart_wait(3)

                src = self.driver.page_source
                history_soup = BeautifulSoup(src, "html.parser")

                rows = history_soup.find_all("tr")
                for row in rows:
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        event = {
                            "date": cells[0].get_text().strip() if cells else "",
                            "description": cells[1].get_text().strip() if len(cells) > 1 else "",
                        }
                        if len(cells) > 2:
                            event["user"] = cells[2].get_text().strip()
                        if len(cells) > 3:
                            event["details"] = cells[3].get_text().strip()

                        event["type"] = self._classify_em_event(event.get("description", ""))
                        event["source"] = "em_platform"

                        if event["date"] or event["description"]:
                            audit_trail.append(event)

                self.driver.back()
                self.smart_wait(2)

        except Exception as e:
            print(f"      ⚠️ Audit trail error: {str(e)[:60]}")

    def _classify_em_event(self, text: str) -> str:
        text_lower = text.lower()

        if any(kw in text_lower for kw in ["invite", "invitation"]):
            return "reviewer_invitation"
        if any(kw in text_lower for kw in ["agreed", "accepted invitation", "accept"]):
            return "reviewer_accepted"
        if any(kw in text_lower for kw in ["declined", "decline"]):
            return "reviewer_declined"
        if any(
            kw in text_lower for kw in ["review received", "report received", "completed review"]
        ):
            return "review_received"
        if any(kw in text_lower for kw in ["reminder", "overdue"]):
            return "reminder"
        if any(kw in text_lower for kw in ["decision", "accept manuscript", "reject"]):
            return "editorial_decision"
        if any(kw in text_lower for kw in ["submitted", "submission"]):
            return "manuscript_submission"
        if any(kw in text_lower for kw in ["assigned", "assignment"]):
            return "editor_assignment"
        if any(kw in text_lower for kw in ["revision", "revised"]):
            return "revision"

        return "other_event"

    # ── Detail page extraction (reviews, details, history) ────

    def _exec_em_js_and_capture(
        self, js_href: str, ms_id: str, debug_prefix: str, folder_url: str = ""
    ) -> BeautifulSoup | None:
        if not js_href:
            return None

        js_code = js_href.replace("javascript:", "").strip().rstrip(";")
        js_code = js_code.replace("PopupHistoryWindow(", "popupHistoryWindow(")

        try:
            if folder_url:
                self.switch_to_default()
                self.driver.get(folder_url)
                self.smart_wait(3)

            self.switch_to_default()
            main_handle = self.driver.current_window_handle
            existing_handles = set(self.driver.window_handles)

            self.driver.execute_script(js_code)
            self.smart_wait(5)

            new_handles = set(self.driver.window_handles) - existing_handles
            if new_handles:
                popup_handle = new_handles.pop()
                self.driver.switch_to.window(popup_handle)
                self.smart_wait(3)
                src = self.driver.page_source
                self._in_content_frame = False
                self._save_debug_html(f"{debug_prefix}_{ms_id}")
                self.driver.close()
                self.driver.switch_to.window(main_handle)
                self._in_content_frame = False
                return BeautifulSoup(src, "lxml")
            else:
                if self.switch_to_content_frame():
                    src = self.driver.page_source
                    self._save_debug_html(f"{debug_prefix}_{ms_id}")
                    self.switch_to_default()
                    return BeautifulSoup(src, "lxml")
                else:
                    src = self.driver.page_source
                    self._save_debug_html(f"{debug_prefix}_{ms_id}")
                    return BeautifulSoup(src, "lxml")

        except Exception as e:
            print(f"      ⚠️ JS exec failed ({debug_prefix}): {str(e)[:60]}")
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except Exception:
                pass
            self._in_content_frame = False
            return None

    def _return_to_dashboard(self):
        try:
            self.switch_to_default()
            self.driver.get(f"{self.BASE_URL}/default.aspx")
            self.smart_wait(3)
            self.navigate_to_ae_dashboard()
        except Exception:
            pass

    def _extract_referees_from_reviews_page(self, manuscript: dict, ms_info: dict):
        ms_id = ms_info["manuscript_id"]
        soup = self._exec_em_js_and_capture(
            ms_info.get("reviews_js", ""),
            ms_id,
            "reviews",
            ms_info.get("folder_url", ""),
        )
        if not soup:
            return

        referees = manuscript["referees"]
        existing_names = {r.get("name", "").lower() for r in referees}

        for span in soup.find_all("span", id=re.compile(r"reviewRepeater_ctl\d+_nameText")):
            role_text = span.get_text(strip=True)
            if "Reviewer" not in role_text:
                continue

            reviewer_num_match = re.search(r"Reviewer\s*(\d+)", role_text)
            reviewer_num = int(reviewer_num_match.group(1)) if reviewer_num_match else 0

            parent_td = span.find_parent("td")
            name_link = parent_td.find("a") if parent_td else None
            name = name_link.get_text(strip=True) if name_link else ""
            if not name or name.lower() in existing_names:
                continue

            referee = {
                "name": name,
                "role": "referee",
                "reviewer_number": reviewer_num,
            }
            if name_link:
                href = name_link.get("href", "")
                pid_match = re.search(r"(?:popupReviewerInfo|showInfo)\((\d+)", href)
                if pid_match:
                    referee["people_id"] = int(pid_match.group(1))

            parent_tr = span.find_parent("tr")
            if parent_tr:
                cells = parent_tr.find_all("td")
                recommendations = []
                for ci, cell in enumerate(cells):
                    if ci == 0:
                        continue
                    term_el = cell.find(
                        ["a", "span"],
                        id=re.compile(r"termLink|termText"),
                    )
                    if term_el:
                        term = term_el.get_text(strip=True)
                        if term and term != "(None)":
                            recommendations.append(term)
                if recommendations:
                    referee["recommendation"] = recommendations[-1]
                    referee["recommendation_history"] = recommendations
                    # Seed a minimal canonical report shell so downstream tooling
                    # knows a review exists, even if popup extraction is later blocked.
                    referee["report"] = {
                        "recommendation": recommendations[-1],
                        "recommendation_raw": recommendations[-1],
                        "comments_to_author": "",
                        "confidential_comments": "",
                        "raw_text": "",
                        "scores": {},
                        "word_count": 0,
                        "source": "em_reviews_page_summary",
                        "extraction_status": "shell_only",
                        "available": True,
                    }

            referees.append(referee)
            existing_names.add(name.lower())

        # Collect review-detail popup hrefs. EM tenants vary in capitalization
        # (popupReviewDetails / PopupReviewDetails / popupReviewerComments) and
        # sometimes attach the JS to onclick rather than href.
        review_detail_pattern = re.compile(
            r"popupReviewDetails|PopupReviewDetails|popupReviewerComments|"
            r"popupReviewerComment|ReviewerComments\.aspx",
            re.IGNORECASE,
        )
        review_detail_links: list[str] = []
        for link in soup.find_all("a"):
            href = link.get("href", "") or ""
            onclick = link.get("onclick", "") or ""
            target = href if review_detail_pattern.search(href) else ""
            if not target and review_detail_pattern.search(onclick):
                target = onclick
            if target and target not in review_detail_links:
                review_detail_links.append(target)

        if review_detail_links:
            ms_info["review_detail_links"] = review_detail_links
        elif referees:
            # Diagnostic: we found referees but no review-detail popup hooks.
            # Likely causes: reviews not yet submitted (status row is invitation-only),
            # tenant uses a different popup function, or the page is showing a stub.
            print(
                f"      ⚠️ Reviews page has {len(referees)} referees but no review-detail "
                "popup links — reviews may not be submitted yet, or popup function name differs."
            )

        attach_link = soup.find("a", href=re.compile(r"Editor_ViewRevAttach|popupViewRevAttach"))
        if attach_link:
            href = attach_link.get("href", "")
            if href.startswith("javascript:"):
                ms_info["view_rev_attach_js"] = href
            else:
                ms_info["view_rev_attach_url"] = href

        print(
            f"      📝 Reviews page: {len(referees)} referees, "
            f"{len(review_detail_links)} review-detail link(s)"
        )

    def _extract_details_from_popup(self, manuscript: dict, ms_info: dict):
        ms_id = ms_info["manuscript_id"]
        soup = self._exec_em_js_and_capture(
            ms_info.get("details_js", ""),
            ms_id,
            "details",
            ms_info.get("folder_url", ""),
        )
        if not soup:
            return

        main_table = soup.find("table", id="MainDataTable")
        if not main_table:
            abstract_el = soup.find(id=re.compile(r"abstract", re.I))
            if abstract_el:
                abstract_text = abstract_el.get_text(strip=True)
                if abstract_text and len(abstract_text) > 20:
                    manuscript["abstract"] = abstract_text
            print(
                f"      📋 Details: abstract={'yes' if manuscript.get('abstract') else 'no'}, "
                f"keywords={len(manuscript.get('keywords', []))}"
            )
            return

        label_map = {}
        sections = {}
        current_section = None

        for tr in main_table.find_all("tr"):
            shaded_td = tr.find("td", class_="shaded")
            if shaded_td:
                section_span = shaded_td.find("span", style=re.compile(r"font-weight"))
                if section_span:
                    current_section = section_span.get_text(strip=True)
                    sections[current_section] = []
                continue

            left_td = tr.find("td", class_="leftWidth")
            if left_td:
                label_span = left_td.find("span")
                label = (
                    label_span.get_text(strip=True).rstrip(":")
                    if label_span
                    else left_td.get_text(strip=True).rstrip(":")
                )
                value_td = left_td.find_next_sibling("td")
                if value_td:
                    label_map[label] = value_td
                current_section = None
                continue

            if current_section:
                colspan_td = tr.find("td", attrs={"colspan": "2"})
                if colspan_td:
                    sections[current_section].append(colspan_td)

        abstract_el = soup.find(id=re.compile(r"txtAbstract", re.I))
        if not abstract_el:
            abstract_el = soup.find(id=re.compile(r"abstract", re.I))
        if abstract_el:
            abstract_text = abstract_el.get_text(strip=True)
            if abstract_text and len(abstract_text) > 20:
                manuscript["abstract"] = abstract_text

        kw_td = label_map.get("Keywords")
        if kw_td:
            kw_text = kw_td.get_text(strip=True)
            if kw_text:
                keywords = [k.strip() for k in re.split(r"[;,]", kw_text) if k.strip()]
                if keywords:
                    manuscript["keywords"] = keywords

        corr_email_td = label_map.get("Corresponding Author E-Mail")
        corr_email = ""
        if corr_email_td:
            mailto_link = corr_email_td.find("a", href=re.compile(r"^mailto:"))
            if mailto_link:
                corr_email = mailto_link["href"].replace("mailto:", "").strip()

        self._parse_authors_from_details(manuscript, label_map, corr_email, ms_info)

        for field, label in [
            ("submission_date", "Initial Date Submitted"),
            ("status_date", "Editorial Status Date"),
            ("current_status", "Current Editorial Status"),
            ("final_disposition", "Final Disposition Term"),
            ("article_type", "Article Type"),
            ("short_title", "Short Title"),
        ]:
            td = label_map.get(label)
            if td:
                val = ""
                for span in td.find_all("span"):
                    t = span.get_text(strip=True)
                    if t and t != "Top":
                        val = t
                        break
                if not val:
                    val = td.get_text(strip=True)
                    val = re.sub(r"^Top\s*", "", val).strip()
                if val and val not in ("", "&nbsp;", "\xa0"):
                    manuscript.setdefault("metadata", {})[field] = val

        if "Editors" in sections:
            self._parse_people_section(manuscript, sections["Editors"], "editors", ms_info)

        if "Reviewers" in sections:
            self._parse_people_section(manuscript, sections["Reviewers"], "reviewers", ms_info)

        print(
            f"      📋 Details: abstract={'yes' if manuscript.get('abstract') else 'no'}, "
            f"keywords={len(manuscript.get('keywords', []))}, "
            f"authors={len(manuscript.get('authors', []))}, "
            f"editors={len(manuscript.get('editors', []))}"
        )

    def _parse_authors_from_details(
        self, manuscript: dict, label_map: dict, corr_email: str, ms_info: dict
    ):
        corr_td = label_map.get("Corresponding Author")
        all_td = label_map.get("All Authors")

        authors = []
        norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
        existing_names = {norm(a.get("name", "")) for a in manuscript.get("authors", [])}

        if all_td:
            authors = self._parse_author_td(all_td, ms_info)
        elif corr_td:
            authors = self._parse_author_td(corr_td, ms_info)

        if corr_td and authors:
            corr_link = corr_td.find("a", href=re.compile(r"popupReviewerInfoEMDetails"))
            if not corr_link:
                corr_link = corr_td.find("a", href=re.compile(r"^mailto:"))
            if corr_link:
                corr_name = corr_link.get_text(strip=True)
                for a in authors:
                    if norm(a["name"]) == norm(corr_name):
                        a["role"] = "corresponding_author"
                        if corr_email:
                            a["email"] = corr_email
                        break
            elif corr_email and authors:
                authors[0]["role"] = "corresponding_author"
                if not authors[0].get("email"):
                    authors[0]["email"] = corr_email

        if (
            not any(a.get("role") == "corresponding_author" for a in authors)
            and corr_email
            and authors
        ):
            authors[0]["role"] = "corresponding_author"
            if not authors[0].get("email"):
                authors[0]["email"] = corr_email

        corr_author = self._parse_author_td(corr_td, ms_info) if corr_td else []
        if corr_author:
            corr_data = corr_author[0]
            for a in authors:
                if norm(a["name"]) == norm(corr_data.get("name", "")):
                    for field in ("country", "affiliation", "affiliation_full", "ringgold_id"):
                        if corr_data.get(field) and not a.get(field):
                            a[field] = corr_data[field]
                    break

        for author in authors:
            author["name"] = re.sub(r"\s+", " ", author["name"]).strip()
            if norm(author["name"]) not in existing_names:
                manuscript["authors"].append(author)
                existing_names.add(norm(author["name"]))
            else:
                for existing in manuscript["authors"]:
                    if norm(existing.get("name", "")) == norm(author["name"]):
                        for field in (
                            "email",
                            "affiliation",
                            "affiliation_full",
                            "ringgold_id",
                            "country",
                            "people_id",
                        ):
                            if author.get(field) and not existing.get(field):
                                existing[field] = author[field]
                        if author.get("role") == "corresponding_author":
                            existing["role"] = "corresponding_author"
                        break

    def _parse_author_td(self, td, ms_info: dict) -> list:
        authors = []
        current = {}

        for el in td.descendants:
            if el.name == "a":
                href = el.get("href", "")
                text = el.get_text(strip=True)

                if not text or el.find("img"):
                    continue

                if href.startswith("mailto:"):
                    email = href.replace("mailto:", "").strip()
                    if current.get("name") and not current.get("email"):
                        current["email"] = email
                    elif not current.get("name") and text:
                        current["name"] = text
                        current["email"] = email
                        current["role"] = "author"
                    continue

                if "popupReviewerInfoEMDetails" in href:
                    pid_match = re.search(r"popupReviewerInfoEMDetails\((\d+)", href)
                    if current.get("name") and current["name"] != text:
                        authors.append(current)
                        current = {}
                    if not current.get("name"):
                        current["name"] = text
                        current["role"] = "author"
                    if pid_match:
                        current["people_id"] = int(pid_match.group(1))
                    continue

                if href == "#top":
                    continue

            if el.name == "span" and el.get("id") and "spnInstitutionName" in el.get("id", ""):
                inst = el.get_text(strip=True)
                if inst and current:
                    current["affiliation"] = inst.split(":")[0].strip() if ":" in inst else inst
                    current["affiliation_full"] = inst

            if (
                el.name == "span"
                and el.get("class")
                and "tooltiptext" in " ".join(el.get("class", []))
            ):
                ringgold_match = re.search(r"Ringgold ID (\d+)", el.get_text())
                if ringgold_match and current:
                    current["ringgold_id"] = ringgold_match.group(1)

            if isinstance(el, str):
                text = el.strip().replace("\xa0", " ").strip()
                if text and current.get("name"):
                    all_upper = re.match(
                        r"^([A-Z][A-Z\s]+(?:FEDERATION|REPUBLIC|KINGDOM|STATES|ISLANDS)?)\s*$", text
                    )
                    if all_upper:
                        current["country"] = all_upper.group(1).strip().title()
                    elif "," in text:
                        last_part = text.rsplit(",", 1)[-1].strip()
                        country_part = re.search(
                            r"([A-Z]{2}[A-Z\s]+(?:FEDERATION|REPUBLIC|KINGDOM|STATES|ISLANDS)?)\s*$",
                            last_part,
                        )
                        if country_part:
                            current["country"] = country_part.group(1).strip().title()
                        elif re.match(r"^[A-Z]", last_part):
                            current["country"] = last_part.strip().title()

        if current.get("name"):
            authors.append(current)

        return authors

    def _parse_people_section(
        self, manuscript: dict, section_tds: list, section_type: str, ms_info: dict
    ):
        people = []
        for td in section_tds:
            nested_table = td.find("table")
            if not nested_table:
                continue

            current = {}
            for row in nested_table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    hr = row.find("hr")
                    if hr and current.get("name"):
                        people.append(current)
                        current = {}
                    continue

                label_cell = cells[0]
                value_cell = cells[1]
                label_span = label_cell.find("span")
                label = (
                    label_span.get_text(strip=True).rstrip(":").rstrip("\xa0").strip()
                    if label_span
                    else label_cell.get_text(strip=True).rstrip(":")
                )

                if label == "Name":
                    if current.get("name"):
                        people.append(current)
                        current = {}
                    name_link = value_cell.find("a", href=re.compile(r"popupReviewerInfoEMDetails"))
                    if name_link:
                        current["name"] = name_link.get_text(strip=True)
                        pid_match = re.search(
                            r"popupReviewerInfoEMDetails\((\d+)", name_link["href"]
                        )
                        if pid_match:
                            current["people_id"] = int(pid_match.group(1))
                    else:
                        current["name"] = value_cell.get_text(strip=True)
                    reviewer_label = value_cell.find("span", string=re.compile(r"\(Reviewer\)"))
                    if reviewer_label:
                        current["role"] = "referee"
                    elif section_type == "reviewers":
                        current["role"] = "referee"
                elif label == "Role":
                    current["editor_role"] = value_cell.get_text(strip=True)
                    current["role"] = "editor"
                elif label == "Review Status":
                    status_span = value_cell.find("span")
                    current["status"] = (
                        status_span.get_text(strip=True)
                        if status_span
                        else value_cell.get_text(strip=True)
                    )
                elif label == "Date Assigned":
                    current["date_assigned"] = value_cell.get_text(strip=True)
                elif label == "Date Completed":
                    val = value_cell.get_text(strip=True)
                    if val:
                        current["date_completed"] = val
                elif label == "Date Reviewer Invited":
                    current["contact_date"] = value_cell.get_text(strip=True)
                elif label == "Date Reviewer Agreed":
                    val = value_cell.get_text(strip=True)
                    if val:
                        current["acceptance_date"] = val
                elif label == "Date Review Due":
                    due_input = value_cell.find("input", id=re.compile(r"inputDate"))
                    if due_input and due_input.get("value"):
                        val = due_input["value"]
                    else:
                        span = value_cell.find("span")
                        val = span.get_text(strip=True) if span else ""
                    if val and re.match(r"\d", val):
                        current["due_date"] = val
                elif label in ("Date Review Completed", "Date Review Returned"):
                    val = value_cell.get_text(strip=True)
                    if val:
                        current["received_date"] = val
                elif label == "Elapsed Days":
                    val = value_cell.get_text(strip=True)
                    if val and val.isdigit():
                        current["elapsed_days"] = int(val)
                elif label == "Recommendation":
                    val = value_cell.get_text(strip=True)
                    if val:
                        current["recommendation"] = val

            if current.get("name"):
                people.append(current)

        norm = lambda s: re.sub(r"\s+", " ", s).strip().lower()
        if section_type == "editors":
            manuscript.setdefault("editors", []).extend(people)
        elif section_type == "reviewers":
            existing = {norm(r.get("name", "")) for r in manuscript.get("referees", [])}
            for person in people:
                person["name"] = re.sub(r"\s+", " ", person["name"]).strip()
                if norm(person["name"]) not in existing:
                    manuscript["referees"].append(person)
                else:
                    for ref in manuscript["referees"]:
                        if norm(ref.get("name", "")) == norm(person["name"]):
                            for key in (
                                "contact_date",
                                "acceptance_date",
                                "due_date",
                                "received_date",
                                "status",
                                "recommendation",
                                "people_id",
                                "elapsed_days",
                            ):
                                if person.get(key) and not ref.get(key):
                                    ref[key] = person[key]
                            break

    def _extract_audit_trail_from_history(self, manuscript: dict, ms_info: dict):
        ms_id = ms_info["manuscript_id"]
        soup = self._exec_em_js_and_capture(
            ms_info.get("history_js", ""),
            ms_id,
            "history",
            ms_info.get("folder_url", ""),
        )
        if not soup:
            return

        audit_trail = manuscript["audit_trail"]

        for fieldset in soup.find_all("fieldset"):
            legend = fieldset.find("legend")
            if not legend:
                continue
            legend_text = legend.get_text(strip=True).upper()

            table = fieldset.find("table")
            if not table:
                continue
            rows = table.find_all("tr")
            if len(rows) < 2:
                continue

            if "STATUS HISTORY" in legend_text:
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) < 6:
                        continue
                    date_text = cells[0].get_text(strip=True)
                    status_text = cells[1].get_text(strip=True)
                    role_text = cells[3].get_text(strip=True)
                    operator_text = cells[5].get_text(strip=True)
                    if not date_text:
                        continue
                    event = {
                        "date": date_text,
                        "action": status_text,
                        "actor": operator_text,
                        "source": "status",
                        "role_family": role_text,
                        "event_type": self._classify_em_event(status_text),
                    }
                    audit_trail.append(event)

            elif "CORRESPONDENCE HISTORY" in legend_text:
                for row in rows[1:]:
                    cells = row.find_all("td")
                    if len(cells) < 6:
                        continue
                    date_text = cells[0].get_text(strip=True)
                    link = cells[1].find("a")
                    letter_text = (
                        link.get_text(strip=True) if link else cells[1].get_text(strip=True)
                    )
                    recipient_text = cells[2].get_text(strip=True)
                    status_text = cells[3].get_text(strip=True)
                    operator_text = cells[5].get_text(strip=True)
                    if not date_text:
                        continue
                    event = {
                        "date": date_text,
                        "action": letter_text,
                        "actor": recipient_text,
                        "performed_by": operator_text,
                        "source": "correspondence",
                        "status": status_text,
                        "event_type": self._classify_em_event(letter_text),
                    }
                    audit_trail.append(event)

        print(f"      📜 History: {len(audit_trail)} events")

    def _extract_referee_reports(self, manuscript: dict, ms_info: dict):
        review_links = ms_info.get("review_detail_links", [])
        if not review_links:
            return

        referees = manuscript.get("referees", [])
        if not referees:
            return

        ref_by_pid = {}
        for ref in referees:
            pid = ref.get("people_id")
            if pid:
                ref_by_pid[pid] = ref

        folder_url = ms_info.get("folder_url", "")
        report_count = 0

        parsed_links = []
        for href in review_links:
            m = re.search(
                r"popupReviewDetails\(\s*(?:false|true)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)",
                href,
            )
            if m:
                parsed_links.append(
                    {
                        "people_id": int(m.group(1)),
                        "doc_id": int(m.group(2)),
                        "revision": int(m.group(3)),
                        "js": href.replace("javascript:", "").strip(),
                    }
                )

        pid_revisions = {}
        for pl in parsed_links:
            pid_revisions.setdefault(pl["people_id"], []).append(pl)
        for pid in pid_revisions:
            pid_revisions[pid].sort(key=lambda x: x["revision"])

        for pid, revs in pid_revisions.items():
            ref = ref_by_pid.get(pid)
            if not ref:
                continue

            reports = ref.get("reports", [])

            for pl in revs:
                try:
                    soup = self._exec_em_js_and_capture(
                        pl["js"],
                        ms_info["manuscript_id"],
                        f"review_r{pl['revision']}_p{pid}",
                        folder_url,
                    )
                    if not soup:
                        continue

                    report = {"revision": pl["revision"]}

                    meta_table = soup.find("table", id="tblSubmissionMetaData")
                    if meta_table:
                        for row in meta_table.find_all("tr"):
                            label_td = row.find("td", class_="label")
                            if label_td:
                                value_td = label_td.find_next_sibling("td")
                                if value_td:
                                    label = label_td.get_text(strip=True).lower()
                                    value = value_td.get_text(strip=True)
                                    if value and value not in ("\xa0", "&nbsp;", "(None)"):
                                        if "recommendation" in label:
                                            report["recommendation"] = value

                        for th in meta_table.find_all("th"):
                            th_text = th.get_text(strip=True).lower()
                            next_row = th.find_parent("tr")
                            if next_row:
                                next_tr = next_row.find_next_sibling("tr")
                                if next_tr:
                                    td = next_tr.find("td")
                                    if td:
                                        value = td.get_text(strip=True)
                                        if value and value not in ("\xa0", "&nbsp;"):
                                            if "comment" in th_text and "author" in th_text:
                                                report["comments_to_author"] = value[:20000]
                                            elif "comment" in th_text and "editor" in th_text:
                                                report["confidential_comments"] = value[:20000]

                    if not meta_table:
                        for table in soup.find_all("table"):
                            for row in table.find_all("tr"):
                                cells = row.find_all("td")
                                if len(cells) < 2:
                                    continue
                                label = cells[0].get_text(strip=True).lower()
                                value = cells[1].get_text(strip=True)
                                if not value or value in ("\xa0", "&nbsp;", "(None)"):
                                    continue
                                if "recommendation" in label:
                                    report["recommendation"] = value
                                elif "remark" in label and "author" in label:
                                    report["comments_to_author"] = value[:20000]
                                elif "confidential" in label or (
                                    "comment" in label and "editor" in label
                                ):
                                    report["confidential_comments"] = value[:20000]

                    bigtitle = soup.find("div", class_="bigtitle")
                    if bigtitle:
                        reviewer_span = bigtitle.find("span", style=re.compile(r"color"))
                        if reviewer_span:
                            num_match = re.search(r"Reviewer\s+(\d+)", reviewer_span.get_text())
                            if num_match:
                                report["reviewer_number"] = int(num_match.group(1))

                    if not report.get("comments_to_author"):
                        comments_box = soup.find("div", class_="reviewerCommentsBox")
                        if comments_box:
                            body_text = comments_box.get_text(separator="\n", strip=True)
                            if len(body_text) > 100:
                                report["raw_text"] = body_text[:20000]

                    attach_panel = soup.find(
                        "div", id="reviewerAttachmentsControl_reviewerAttachmentPanel"
                    )
                    if attach_panel:
                        att_table = attach_panel.find(
                            "table", id=re.compile(r"reviewerAttachmentsControl_Attachments")
                        )
                        if att_table:
                            attachment_urls = []
                            for att_row in att_table.find_all("tr"):
                                att_cells = att_row.find_all("td")
                                if len(att_cells) < 2:
                                    continue
                                dl_link = None
                                for att_a in att_row.find_all("a", href=True):
                                    att_href = att_a.get("href", "")
                                    if "download.aspx" in att_href and "scheme=9" not in att_href:
                                        dl_link = att_a
                                        break
                                if not dl_link:
                                    for att_a in att_row.find_all("a", href=True):
                                        att_href = att_a.get("href", "")
                                        if "download.aspx" in att_href:
                                            dl_link = att_a
                                            break
                                if dl_link:
                                    att_texts = [c.get_text(strip=True) for c in att_cells]
                                    attachment_urls.append(
                                        {
                                            "url": dl_link.get("href", ""),
                                            "description": (
                                                att_texts[1] if len(att_texts) > 1 else ""
                                            ),
                                            "filename": att_texts[2] if len(att_texts) > 2 else "",
                                        }
                                    )
                            if attachment_urls:
                                report["_attachment_urls"] = attachment_urls

                    # Apply canonical schema annotations
                    report.setdefault("source", "em_popup")
                    cta = report.get("comments_to_author") or ""
                    raw = report.get("raw_text") or ""
                    has_attachments = bool(report.get("_attachment_urls"))
                    report["available"] = bool(
                        cta
                        or raw
                        or report.get("scores")
                        or has_attachments
                        or (
                            report.get("recommendation")
                            and report["recommendation"].lower()
                            not in ("", "unknown", "n/a", "(none)")
                        )
                    )
                    if cta or raw:
                        report["extraction_status"] = "ok"
                    elif report.get("recommendation") or has_attachments:
                        report["extraction_status"] = "shell_only"
                    else:
                        report["extraction_status"] = "popup_failed"
                    word_text = cta or raw
                    report["word_count"] = len(word_text.split()) if word_text else 0

                    reports.append(report)
                    report_count += 1

                except Exception as e:
                    print(
                        f"      ⚠️ Review detail failed (pid={pid}, rev={pl['revision']}): {str(e)[:60]}"
                    )

            if reports:
                ref["reports"] = reports
                if not ref.get("report") and reports:
                    latest = reports[-1]
                    ref["report"] = {
                        k: v
                        for k, v in latest.items()
                        if k
                        in (
                            "comments_to_author",
                            "confidential_comments",
                            "recommendation",
                            "review_date",
                            "scores",
                            "word_count",
                            "available",
                            "extraction_status",
                            "source",
                        )
                    }

        if report_count:
            print(f"      📝 Extracted {report_count} referee reports")

    def _extract_referee_contacts(self, manuscript: dict, ms_info: dict):
        referees = manuscript.get("referees", [])
        if not referees:
            return

        docid = ms_info.get("docid", "")
        if not docid:
            return

        folder_url = ms_info.get("folder_url", "")
        enriched = 0

        for ref in referees:
            pid = ref.get("people_id")
            if not pid:
                continue
            if ref.get("email") and ref.get("affiliation"):
                continue

            js_code = f"popupReviewerInfo({pid}, {docid})"

            try:
                soup = self._exec_em_js_and_capture(
                    js_code,
                    ms_info["manuscript_id"],
                    f"refcontact_p{pid}",
                    folder_url,
                )
                if not soup:
                    continue

                mailto = soup.find("a", href=re.compile(r"^mailto:"))
                if mailto and not ref.get("email"):
                    ref["email"] = mailto["href"].replace("mailto:", "").strip()

                gen_info = None
                for fs in soup.find_all("fieldset"):
                    legend = fs.find("legend")
                    if legend and "general information" in legend.get_text(strip=True).lower():
                        gen_info = fs
                        break

                if gen_info:
                    addr_td = None
                    for td in gen_info.find_all("td"):
                        if "address" in td.get_text(strip=True).lower():
                            addr_td = td
                            break
                    if addr_td:
                        value_td = addr_td.find_next_sibling("td")
                        if value_td:
                            lines = []
                            for child in value_td.children:
                                if isinstance(child, str):
                                    t = child.strip().replace("\xa0", " ").strip()
                                    if t:
                                        lines.append(t)
                                elif child.name == "br":
                                    continue
                                elif child.name == "a" and child.get("href", "").startswith(
                                    "mailto:"
                                ):
                                    continue
                                elif child.name == "div":
                                    continue
                                elif child.name:
                                    t = child.get_text(strip=True)
                                    if t:
                                        lines.append(t)

                            if lines and not ref.get("affiliation"):
                                inst = lines[0]
                                ref["affiliation"] = (
                                    inst.split(":")[0].strip() if ":" in inst else inst
                                )
                                ref["affiliation_full"] = inst

                            for line in lines:
                                if not ref.get("country"):
                                    upper_match = re.match(
                                        r"^([A-Z][A-Z\s]+(?:FEDERATION|REPUBLIC|KINGDOM|STATES|ISLANDS)?)\s*$",
                                        line,
                                    )
                                    if upper_match:
                                        ref["country"] = upper_match.group(1).strip().title()

                if not gen_info:
                    inst_span = soup.find("span", id=re.compile(r"spnInstitutionName"))
                    if inst_span and not ref.get("affiliation"):
                        inst = inst_span.get_text(strip=True)
                        ref["affiliation"] = inst.split(":")[0].strip() if ":" in inst else inst

                    for el in soup.descendants:
                        if isinstance(el, str):
                            text = el.strip().replace("\xa0", " ").strip()
                            if text and not ref.get("country"):
                                upper_match = re.match(
                                    r"^([A-Z][A-Z\s]+(?:FEDERATION|REPUBLIC|KINGDOM|STATES|ISLANDS)?)\s*$",
                                    text,
                                )
                                if upper_match:
                                    ref["country"] = upper_match.group(1).strip().title()

                if ref.get("email") or ref.get("affiliation"):
                    enriched += 1

            except Exception as e:
                print(f"      ⚠️ Referee contact failed (pid={pid}): {str(e)[:60]}")

        if enriched:
            print(f"      📧 Enriched {enriched}/{len(referees)} referee contacts")

    def _backfill_referee_dates_from_audit_trail(self, manuscript: dict):
        referees = manuscript.get("referees", [])
        if not referees:
            return
        audit_trail = manuscript.get("audit_trail", [])
        if not audit_trail:
            return

        event_map = {
            "reviewer_invitation": "contact_date",
            "reviewer_accepted": "acceptance_date",
            "review_received": "received_date",
        }

        for ref in referees:
            name_lower = ref.get("name", "").lower()
            if not name_lower:
                continue
            surname = name_lower.split()[-1] if name_lower.split() else ""

            for event in audit_trail:
                ev_type = event.get("event_type", "")
                if ev_type not in event_map:
                    continue

                date_field = event_map[ev_type]
                if ref.get(date_field):
                    continue

                actor = event.get("actor", "").lower()
                performed_by = event.get("performed_by", "").lower()
                event.get("action", "").lower()

                match = False
                if surname and len(surname) > 2:
                    if surname in actor or surname in performed_by:
                        match = True
                if name_lower in actor or name_lower in performed_by:
                    match = True

                if match:
                    ref[date_field] = event.get("date", "")

    # ── Analytics (platform-agnostic, from siam_base.py) ──────

    def _compute_referee_statistics(self, manuscript: dict):
        audit = manuscript.get("audit_trail", [])

        def _parse_date(s):
            if not s:
                return None
            s = re.sub(r"\s+", " ", str(s)).strip()
            for fmt in (
                "%Y-%m-%d",
                "%d-%b-%Y",
                "%d-%B-%Y",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%d %b %Y",
                "%b %d %Y %I:%M%p",
                "%b %d %Y",
            ):
                try:
                    return datetime.strptime(s.split("T")[0], fmt)
                except Exception:
                    continue
            try:
                return datetime.strptime(s.split("T")[0].split()[0], "%Y-%m-%d")
            except Exception:
                pass
            return None

        REMINDER_TYPES = {
            "review_reminder",
            "review_reminder_final",
            "review_overdue",
            "reminder",
            "deadline_reminder",
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

    def _compute_peer_review_milestones(self, manuscript: dict):
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

        for ref in referees:
            for date_str, lst in [
                (ref.get("contact_date", ""), contact_dates),
                (ref.get("received_date", ""), received_dates),
                (ref.get("due_date", ""), due_dates),
            ]:
                if date_str:
                    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%m/%d/%Y"):
                        try:
                            lst.append(datetime.strptime(date_str, fmt))
                            break
                        except Exception:
                            continue

        if contact_dates:
            milestones["all_referees_assigned_date"] = max(contact_dates).strftime("%Y-%m-%d")

        if received_dates:
            milestones["first_report_received_date"] = min(received_dates).strftime("%Y-%m-%d")
            milestones["last_report_received_date"] = max(received_dates).strftime("%Y-%m-%d")

        milestones["reports_received"] = len(received_dates)
        milestones["reports_pending"] = max(0, len(referees) - len(received_dates))
        milestones["all_reports_received"] = len(referees) > 0 and len(received_dates) >= len(
            referees
        )

        now = datetime.now()
        if sub_date:
            milestones["days_since_submission"] = (now - sub_date).days
            if received_dates:
                milestones["days_in_review"] = (max(received_dates) - sub_date).days
            else:
                milestones["days_in_review"] = (now - sub_date).days

        turnarounds = []
        for ref in referees:
            rd = ref.get("received_date", "")
            cd = ref.get("contact_date", "")
            if rd and cd:
                for fmt in ("%Y-%m-%d", "%d-%b-%Y"):
                    try:
                        r = datetime.strptime(rd, fmt)
                        c = datetime.strptime(cd, fmt)
                        days = (r - c).days
                        if days > 0:
                            turnarounds.append(days)
                        break
                    except Exception:
                        continue

        if turnarounds:
            milestones["average_review_turnaround_days"] = round(
                sum(turnarounds) / len(turnarounds), 1
            )
            milestones["fastest_review_days"] = min(turnarounds)
            milestones["slowest_review_days"] = max(turnarounds)

        if due_dates:
            future_dues = [d for d in due_dates if d > now]
            if future_dues:
                next_due = min(future_dues)
                milestones["next_report_due"] = next_due.strftime("%Y-%m-%d")
                milestones["days_until_next_due"] = (next_due - now).days

        manuscript["peer_review_milestones"] = milestones

    def extract_timeline_analytics(self, manuscript: dict) -> dict:
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
                parsed_date = None
                ds = str(date_str)
                try:
                    if "GMT" in ds or "EDT" in ds:
                        clean = ds.replace(" GMT", "").replace(" EDT", "")
                        parsed_date = datetime.strptime(clean, "%d-%b-%Y %I:%M %p").replace(
                            tzinfo=UTC
                        )
                    else:
                        try:
                            parsed_date = datetime.fromisoformat(ds.replace("Z", "+00:00"))
                            if parsed_date.tzinfo is None:
                                parsed_date = parsed_date.replace(tzinfo=UTC)
                        except (ValueError, TypeError):
                            for fmt in (
                                "%d-%b-%Y",
                                "%Y-%m-%d",
                                "%d-%b-%Y %H:%M",
                                "%m/%d/%Y",
                            ):
                                try:
                                    parsed_date = datetime.strptime(ds.strip(), fmt).replace(
                                        tzinfo=UTC
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
            analytics["communication_span_days"] = (event_dates[-1] - event_dates[0]).days

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
        ACCEPTANCE_TYPES = {
            "reviewer_accepted",
            "reviewer_agreement",
            "referee_accepted",
        }

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
            for inv_idx, _inv in invitation_events:
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
        ]
        if reminder_events:
            effective_reminders = 0
            total_reminders = len(reminder_events)
            for rem_idx, _reminder in reminder_events:
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
            f"      📊 Timeline analytics: {analytics['total_events']} events, "
            f"{analytics['communication_span_days']} days span"
        )
        return analytics

    # ── Enrichment (delegated to shared web_enrichment module) ─────

    def _enrich_people_from_web(self, manuscript_data: dict):
        enrich_people_from_web(
            manuscript_data,
            get_cached_web_profile=self.get_cached_web_profile,
            save_web_profile=self.save_web_profile,
            platform_label="em_metadata",
        )

    def _enrich_audit_trail_with_gmail(self, manuscript_data: dict, manuscript_id: str):
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
                print("      ⚠️ Gmail service not available")
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
                print("      📧 No external Gmail communications found")
                return

            audit_trail = manuscript_data.get("audit_trail", [])
            merged = gmail.merge_with_audit_trail(
                audit_trail=audit_trail,
                external_emails=external_emails,
                manuscript_id=manuscript_id,
            )

            for ev in merged:
                if not ev.get("external") and ev.get("source") == "mf_platform":
                    ev["source"] = "em_platform"
            manuscript_data["communication_timeline"] = merged
            ext_count = len([e for e in merged if e.get("external")])
            manuscript_data["external_communications_count"] = ext_count
            print(f"      📧 Gmail enrichment: {ext_count} external emails merged")

            self._backfill_author_emails_from_timeline(manuscript_data, merged)

        except Exception as e:
            print(f"      ⚠️ Gmail search error: {str(e)[:60]}")

    def _backfill_author_emails_from_timeline(self, manuscript_data: dict, timeline: list[dict]):
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
        system_domains = {"editorialmanager.com", "aries.com", "ariessys.com"}
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

    # ── Output ────────────────────────────────────────────────

    def generate_summary(self, manuscripts: list[dict]) -> dict:
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

    def save_results(self, manuscripts: list[dict]):
        if not manuscripts:
            print("⚠️ No manuscripts to save")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"{self.JOURNAL_CODE.lower()}_extraction_{timestamp}.json"

        summary = self.generate_summary(manuscripts)

        results = {
            "extraction_timestamp": datetime.now().isoformat(),
            "journal": self.JOURNAL_CODE,
            "journal_name": self.JOURNAL_NAME,
            "platform": "Editorial Manager",
            "extractor_version": "2.0.0",
            "manuscripts": manuscripts,
            "summary": summary,
        }

        from core.output_schema import normalize_wrapper

        normalize_wrapper(results, self.JOURNAL_CODE)

        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n💾 Results saved: {output_file}")
        print("📊 Summary:")
        for k, v in summary.items():
            print(f"   {k}: {v}")

    # ── Session management ────────────────────────────────────

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
            if not self.login():
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
        self._in_content_frame = False

    # ── Main entry point ──────────────────────────────────────

    def run(self) -> list[dict]:
        print(f"🚀 {self.JOURNAL_CODE} EXTRACTION — EDITORIAL MANAGER")
        print("=" * 60)

        try:
            self.setup_driver()

            if not self.login():
                print("❌ Login failed")
                return []

            self.navigate_to_ae_dashboard()

            categories = self.discover_categories()
            if not self.CATEGORIES:
                print("⚠️  Including archived folders — one-time historical extraction")

            all_manuscript_infos = []
            all_seen = set()

            for cat in categories:
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
                print("⚠️ No manuscripts found")
                self.save_results([])
                return []

            print(f"\n📚 Total unique manuscripts: {len(all_manuscript_infos)}")

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
                        print(f"      ⚠️ Enrichment error: {str(e)[:60]}")
                    try:
                        self._enrich_audit_trail_with_gmail(data, ms_id)
                    except Exception as e:
                        print(f"      ⚠️ Gmail error: {str(e)[:60]}")
                    try:
                        timeline_analytics = self.extract_timeline_analytics(data)
                        if timeline_analytics:
                            data["timeline_analytics"] = timeline_analytics
                    except Exception as e:
                        print(f"      ⚠️ Timeline analytics error: {str(e)[:60]}")
                    self.manuscripts_data.append(data)

            self.save_results(self.manuscripts_data)
            return self.manuscripts_data

        except Exception as e:
            print(f"❌ Extraction failed: {str(e)[:100]}")
            if self.manuscripts_data:
                self.save_results(self.manuscripts_data)
            return self.manuscripts_data
        finally:
            self.cleanup_driver()
