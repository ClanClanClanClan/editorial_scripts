#!/usr/bin/env python3
import os
import re
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementClickInterceptedException,
)
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin
from core.web_enrichment import enrich_people_from_web

try:
    from core.gmail_search import GmailSearchManager

    GMAIL_SEARCH_AVAILABLE = True
except ImportError:
    GMAIL_SEARCH_AVAILABLE = False


class NACOExtractor(CachedExtractorMixin):
    JOURNAL_CODE = "NACO"
    JOURNAL_NAME = "Numerical Algebra, Control and Optimization"
    LOGIN_URL = "https://ef.msp.org/login.php"
    PLATFORM = "EditFlow (MSP)"

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

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.wait = None
        self.manuscripts: List[Dict[str, Any]] = []
        self._last_exception_msg = ""

        self.username = os.environ.get("NACO_USERNAME")
        self.password = os.environ.get("NACO_PASSWORD")

        self.output_dir = Path(__file__).parent.parent.parent / "outputs" / "naco"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.debug_dir = self.output_dir / "debug"
        self.debug_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(self.JOURNAL_CODE)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        self.init_cached_extractor(self.JOURNAL_CODE)

    def setup_driver(self):
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--window-size=1280,900")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.wait = WebDriverWait(self.driver, 20)
        self.logger.info("Browser ready")

    def login(self) -> bool:
        if not self.username or not self.password:
            self.logger.error("NACO_USERNAME / NACO_PASSWORD not set")
            return False

        self.logger.info(f"Navigating to {self.LOGIN_URL}")
        self.driver.get(self.LOGIN_URL)
        time.sleep(2)
        self._save_debug_html("login_page")

        try:
            username_field = self.wait.until(EC.presence_of_element_located((By.ID, "login")))
            password_field = self.driver.find_element(By.NAME, "password")

            username_field.clear()
            username_field.send_keys(self.username)
            time.sleep(0.5)

            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(0.5)

            signin_button = self.driver.find_element(
                By.CSS_SELECTOR, "input[type='submit'][name='signin']"
            )
            signin_button.click()
            self.logger.info("Login submitted")
            time.sleep(3)

            self._save_debug_html("post_login")

            if self._is_logged_in():
                self.logger.info("Login successful")
                return True

            self.logger.error("Login may have failed — 'Mine' link not found")
            return False

        except TimeoutException:
            self.logger.error("Login form not found")
            self._save_debug_html("login_timeout")
            return False
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            self._save_debug_html("login_error")
            return False

    def _is_logged_in(self) -> bool:
        selectors = [
            (By.LINK_TEXT, "Mine"),
            (By.PARTIAL_LINK_TEXT, "Mine"),
            (By.XPATH, "//a[contains(text(), 'Mine')]"),
            (By.CSS_SELECTOR, "a[href*='mine']"),
        ]
        for by, selector in selectors:
            try:
                el = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((by, selector))
                )
                if el and el.is_displayed():
                    return True
            except (TimeoutException, NoSuchElementException):
                continue
        return False

    def _find_mine_link(self):
        selectors = [
            (By.LINK_TEXT, "Mine"),
            (By.PARTIAL_LINK_TEXT, "Mine"),
            (By.XPATH, "//a[contains(text(), 'Mine')]"),
            (By.CSS_SELECTOR, "a[href*='mine']"),
        ]
        for by, selector in selectors:
            try:
                el = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((by, selector)))
                if el and el.is_displayed():
                    return el
            except (TimeoutException, NoSuchElementException):
                continue

        try:
            for link in self.driver.find_elements(By.TAG_NAME, "a"):
                text = link.text.strip().lower()
                href = (link.get_attribute("href") or "").lower()
                if ("mine" in text or "mine" in href) and link.is_displayed():
                    return link
        except Exception:
            pass

        return None

    def navigate_to_mine(self) -> bool:
        mine_link = self._find_mine_link()
        if not mine_link:
            self.logger.error("'Mine' link not found")
            self._save_debug_html("no_mine_link")
            return False

        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", mine_link)
            time.sleep(0.5)

            for attempt in range(5):
                if mine_link.is_displayed() and mine_link.is_enabled():
                    try:
                        mine_link.click()
                        self.logger.info(f"Clicked 'Mine' link (attempt {attempt + 1})")
                        time.sleep(3)
                        self._save_debug_html("mine_page")
                        return True
                    except ElementClickInterceptedException:
                        time.sleep(0.8)
                else:
                    time.sleep(0.8)

            self.logger.warning("Normal click failed, trying JS click")
            self.driver.execute_script("arguments[0].click();", mine_link)
            time.sleep(3)
            self._save_debug_html("mine_page_js_click")
            return True

        except Exception as e:
            self.logger.error(f"Failed to click Mine link: {e}")
            self._save_debug_html("mine_click_error")
            return False

    def parse_manuscripts(self) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        articles = soup.find_all("article", class_="JournalView-Listing")

        if not articles:
            self.logger.info("No article elements found (empty AE queue)")
            return []

        manuscripts = []
        for article in articles:
            try:
                name_span = article.find("span", {"data-tooltip": "Associate Editor"})
                if not name_span or "Possamai" not in name_span.text:
                    continue

                h2 = article.find("h2")
                if h2 and "no articles" in h2.text.lower():
                    self.logger.info("AE block says 'no articles'")
                    continue

                ms = self._parse_single_manuscript(article)
                if ms:
                    manuscripts.append(ms)

            except Exception as e:
                self.logger.warning(f"Failed to parse article element: {e}")
                continue

        self.logger.info(f"Parsed {len(manuscripts)} manuscripts")
        return manuscripts

    def _parse_single_manuscript(self, article) -> Optional[Dict[str, Any]]:
        ms: Dict[str, Any] = {
            "manuscript_id": "",
            "title": "",
            "authors": [],
            "status": "",
            "submission_date": "",
            "referees": [],
            "audit_trail": [],
            "communication_timeline": [],
            "journal": self.JOURNAL_CODE,
            "platform": self.PLATFORM,
            "extracted_at": datetime.now().isoformat(),
        }

        for link in article.find_all("a", href=True):
            text = link.text.strip()
            href = link.get("href", "")
            if "NACO" in text.upper() or "manuscript" in href.lower():
                ms["manuscript_id"] = text.strip()
                break
            match = re.search(r"id=(\d+)", href)
            if match:
                ms["manuscript_id"] = f"NACO-{match.group(1)}"
                break

        for tag in article.find_all(["h3", "strong", "b"]):
            text = tag.text.strip()
            if text and len(text) > 10 and not text.startswith("Associate"):
                ms["title"] = text
                break

        for tag in article.find_all(["i", "em", "span"]):
            text = tag.text.strip()
            if text and ("by " in text.lower() or "@" in text):
                author_name = re.sub(r"^[Bb]y\s+", "", text).strip()
                if author_name:
                    ms["authors"].append(
                        {
                            "name": author_name,
                            "is_corresponding": True,
                        }
                    )
                    ms["contact_author"] = author_name
                    break

        status_keywords = ["under review", "awaiting", "assigned", "pending", "revision"]
        for tag in article.find_all(["span", "div"]):
            text = tag.text.strip().lower()
            if any(kw in text for kw in status_keywords):
                ms["status"] = tag.text.strip()
                break

        for tag in article.find_all(["span", "div", "small"]):
            text = tag.text.strip()
            if any(kw in text.lower() for kw in ["submitted", "received", "date"]):
                date_match = re.search(
                    r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4}", text
                )
                if date_match:
                    ms["submission_date"] = date_match.group(0)
                    break

        for container in article.find_all(["ul", "ol", "div"]):
            if "referee" in container.text.lower() or "reviewer" in container.text.lower():
                refs = self._extract_referees(container)
                if refs:
                    ms["referees"] = refs
                    break

        if ms["manuscript_id"] or ms["title"]:
            return ms
        return None

    def _extract_referees(self, container) -> List[Dict[str, Any]]:
        referees = []
        for item in container.find_all(["li", "div", "p"]):
            text = item.text.strip()
            if not text or len(text) < 5:
                continue
            emails = re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", text)
            if not emails:
                continue

            name_part = text.split("@")[0] if "@" in text else text
            name = re.sub(r"[^\w\s]", "", name_part).strip()

            status = "Contacted"
            if any(kw in text.lower() for kw in ["accepted", "agreed", "confirmed"]):
                status = "Accepted"
            elif any(kw in text.lower() for kw in ["declined", "rejected", "refused"]):
                status = "Declined"

            referee = {
                "name": name,
                "email": emails[0],
                "status": status,
            }

            date_matches = re.findall(r"\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}", text)
            if date_matches:
                referee["contacted_date"] = date_matches[0]

            referees.append(referee)
        return referees

    # --- Session Recovery ---

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
            if not self.navigate_to_mine():
                print("      ❌ Could not navigate to Mine after recovery")
                return False
            print("      ✅ Session recovered successfully")
            return True
        except Exception as e:
            print(f"      ❌ Session recovery failed: {str(e)[:100]}")
            return False

    # --- Web Enrichment ---

    def _enrich_people_from_web(self, manuscript_data: Dict):
        enrich_people_from_web(
            manuscript_data,
            get_cached_web_profile=self.get_cached_web_profile,
            save_web_profile=self.save_web_profile,
            platform_label="editflow_metadata",
        )

    # --- Gmail Integration ---

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
                print("      ⚠️ Gmail service not available")
                return

            sub_date_str = manuscript_data.get("submission_date", "")
            date_range = None
            if sub_date_str:
                for fmt in ["%Y-%m-%d", "%d-%b-%Y", "%d-%B-%Y", "%m/%d/%Y"]:
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
                    ev["source"] = "editflow_platform"
            manuscript_data["communication_timeline"] = merged
            ext_count = len([e for e in merged if e.get("external")])
            manuscript_data["external_communications_count"] = ext_count
            manuscript_data["timeline_enhanced"] = True
            print(f"      📧 Gmail enrichment: {ext_count} external emails merged into timeline")

            self._backfill_author_emails_from_timeline(manuscript_data, merged)

        except Exception as e:
            print(f"      ⚠️ Gmail search error: {str(e)[:60]}")

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
        system_domains = {"msp.org"}
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

    # --- Timeline Analytics ---

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
            f"      📊 Timeline analytics: {analytics['total_events']} events, "
            f"{analytics['communication_span_days']} days span"
        )
        return analytics

    # --- Save & Cleanup ---

    def save_results(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = self.output_dir / f"naco_{timestamp}.json"

        extraction_data = {
            "journal": self.JOURNAL_CODE,
            "journal_name": self.JOURNAL_NAME,
            "platform": self.PLATFORM,
            "extraction_time": timestamp,
            "manuscripts_count": len(self.manuscripts),
            "manuscripts": self.manuscripts,
            "summary": {
                "total_manuscripts": len(self.manuscripts),
                "total_referees": sum(len(m.get("referees", [])) for m in self.manuscripts),
                "total_authors": sum(len(m.get("authors", [])) for m in self.manuscripts),
                "enriched_people": sum(
                    1
                    for m in self.manuscripts
                    for p in m.get("referees", []) + m.get("authors", [])
                    if p.get("web_profile")
                ),
            },
        }

        from core.output_schema import normalize_wrapper

        normalize_wrapper(extraction_data, "NACO")

        with open(output_file, "w") as f:
            json.dump(extraction_data, f, indent=2, default=str)

        self.logger.info(f"Results saved: {output_file}")

    def _save_debug_html(self, suffix: str):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.debug_dir / f"naco_debug_{suffix}_{timestamp}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            self.logger.debug(f"Debug HTML saved: {filename}")
        except Exception as e:
            self.logger.warning(f"Failed to save debug HTML: {e}")

    def cleanup_driver(self):
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser closed")
            except Exception:
                pass
            self.driver = None

    # --- Main Orchestration ---

    def run(self) -> List[Dict[str, Any]]:
        print(f"🚀 {self.JOURNAL_CODE} EXTRACTION — {self.PLATFORM}")
        print("=" * 60)

        try:
            self.setup_driver()

            if not self.login():
                print("❌ Login failed")
                return []

            if not self.navigate_to_mine():
                print("❌ Could not navigate to Mine page")
                return []

            self.manuscripts = self.parse_manuscripts()

            if not self.manuscripts:
                print("ℹ️  No manuscripts in AE queue (expected if none assigned)")
                self.save_results()
                self.finish_extraction_with_stats()
                return []

            for idx, ms in enumerate(self.manuscripts):
                ms_id = ms.get("manuscript_id", "")
                print(f"\n   [{idx + 1}/{len(self.manuscripts)}] {ms_id}")

                try:
                    self._enrich_people_from_web(ms)
                except Exception as e:
                    print(f"      ⚠️ Enrichment error: {str(e)[:60]}")

                try:
                    self._enrich_audit_trail_with_gmail(ms, ms_id)
                except Exception as e:
                    print(f"      ⚠️ Gmail error: {str(e)[:60]}")

                try:
                    analytics = self.extract_timeline_analytics(ms)
                    if analytics:
                        ms["timeline_analytics"] = analytics
                except Exception as e:
                    print(f"      ⚠️ Timeline analytics error: {str(e)[:60]}")

            self.save_results()
            self.finish_extraction_with_stats()
            return self.manuscripts

        except Exception as e:
            self.logger.error(f"Extraction failed: {e}")
            self._last_exception_msg = str(e).lower()
            if self.manuscripts:
                self.save_results()
            self.finish_extraction_with_stats()
            return self.manuscripts

        finally:
            self.cleanup_driver()


if __name__ == "__main__":
    headless = os.environ.get("EXTRACTOR_HEADLESS", "true").lower() == "true"
    extractor = NACOExtractor(headless=headless)
    try:
        results = extractor.run()
        if results:
            print(f"\n✅ NACO extraction complete: {len(results)} manuscripts")
        else:
            print("\n⚠️ No manuscripts extracted")
    except KeyboardInterrupt:
        print("\n⚠️ Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
