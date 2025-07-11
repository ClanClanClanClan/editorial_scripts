import logging
import argparse
from concurrent.futures import ThreadPoolExecutor
import subprocess
import time
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

DEFAULT_USE_PLAYWRIGHT = True

from core.email_utils import (
    fetch_starred_emails,
    send_digest_email,
    robust_match_email_for_referee,
    robust_match_email_for_referee_mor,
    robust_match_email_for_referee_mf,
    robust_match_email_for_referee_fs,
    robust_match_email_for_referee_jota,
    robust_match_email_for_referee_mafe,
)
from core.digest_utils import build_html_digest, collect_unmatched_and_urgent
from journals.sicon import SICONJournal
from journals.sifin import SIFINJournal
from journals.mor import MORJournal
from journals.mf import MFJournal
from journals.naco import NACOJournal
from journals.fs import FSJournal
from journals.jota import JOTAJournal  # <- import here!
from journals.mafe import MAFEJournal

match_funcs = {
    "SICON": robust_match_email_for_referee,
    "SIFIN": robust_match_email_for_referee,
    "MOR": robust_match_email_for_referee_mor,
    "MF": robust_match_email_for_referee_mf,
    "NACO": lambda *a, **kw: ("", ""),
    "FS": robust_match_email_for_referee_fs,
    "JOTA": robust_match_email_for_referee_jota,
    "MAFE": robust_match_email_for_referee_mafe,
}

JOURNAL_HEADLESS = {
    "SICON": True,
    "SIFIN": True,
    "MOR": True,
    "MF": True,
    "NACO": True,
    "FS": True,
    "JOTA": True,
    "MAFE": True,
}

def hide_chrome():
    time.sleep(1.5)
    applescript = '''
    tell application "Google Chrome" to activate
    tell application "System Events" to keystroke "h" using {command down}
    '''
    try:
        subprocess.run(['osascript', '-e', applescript], check=True)
    except Exception as e:
        print(f"[WARNING] Could not hide Chrome windows: {e}")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate and send editorial digests for all journals."
    )
    parser.add_argument(
        "--journals",
        nargs="+",
        default=["SICON", "SIFIN", "MOR", "MF", "NACO", "FS", "JOTA", "MAFE"],
        help="Journals to process (default: all supported). Choices: %(choices)s",
        choices=["SICON", "SIFIN", "MOR", "MF", "NACO", "FS", "JOTA", "MAFE"],
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the digest HTML but do not send email")
    parser.add_argument("--output", type=str, help="Write digest HTML to a file instead of sending email")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--show-browser", action="store_true", help="Show browser window instead of headless Chrome/Playwright (default: headless)")
    parser.add_argument(
        "--chrome-profile-dir",
        type=str,
        default=os.path.expanduser("~/Library/Application Support/Google/Chrome"),
        help="Base path to persistent Chrome user data dir for session/cookie reuse (MOR/MF/NACO, default Chrome path)."
    )
    parser.add_argument(
        "--use-playwright", action="store_true", default=DEFAULT_USE_PLAYWRIGHT,
        help="Use Playwright for JOTA/MAFE automation instead of Selenium/undetected-chromedriver."
    )
    parser.add_argument(
        "--force-headless", action="store_true", default=False,
        help="Force headless mode for all browsers, overriding --show-browser"
    )
    return parser.parse_args()

def create_journals(selected_names, show_browser=False, chrome_profile_dir=None, use_playwright=True, force_headless=False, gmail_service=None):
    journals = {}
    drivers = {}
    playwright_sessions = {}

    for name in selected_names:
        # FS needs no browser
        if name == "FS":
            journals[name] = FSJournal(driver=None)
            continue

        # JOTA will use the email-based scraping with Gmail API
        if name == "JOTA":
            if gmail_service is None:
                raise ValueError("gmail_service is required for JOTA journal email scraping")
            journals[name] = JOTAJournal(gmail_service)
            drivers[name] = None
            continue

        headless = (not show_browser and JOURNAL_HEADLESS.get(name, True)) or force_headless

        # Playwright for MAFE only
        if name == "MAFE":
            from playwright.sync_api import sync_playwright
            playwright = sync_playwright().start()

            if chrome_profile_dir is None:
                base_profile_dir = os.path.expanduser("~/playwright-profiles")
            else:
                base_profile_dir = chrome_profile_dir

            profile_dir = os.path.join(base_profile_dir, f"playwright_{name.lower()}_profile")
            os.makedirs(profile_dir, exist_ok=True)

            browser_ctx = playwright.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=headless,
                args=[
                    "--window-size=1200,900",
                    "--disable-blink-features=AutomationControlled"
                ],
            )
            # set_jota_consent_cookies(browser_ctx)  # Not needed for MAFE
            page = browser_ctx.new_page()
            drivers[name] = (playwright, browser_ctx, page)
            journals[name] = MAFEJournal(page)
            playwright_sessions[name] = (playwright, browser_ctx, page)

        else:
            chrome_options = Options()
            if headless:
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1200,900")
            chrome_options.add_argument("--no-sandbox")

            if name == "MOR":
                profile_dir = (
                    os.path.join(chrome_profile_dir, "mor_profile")
                    if chrome_profile_dir else os.path.expanduser("~/.mor_chrome_profile")
                )
                chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            elif name == "MF":
                profile_dir = (
                    os.path.join(chrome_profile_dir, "mf_profile")
                    if chrome_profile_dir else os.path.expanduser("~/.mf_chrome_profile")
                )
                chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            elif name == "NACO":
                profile_dir = (
                    os.path.join(chrome_profile_dir, "naco_profile")
                    if chrome_profile_dir else os.path.expanduser("~/.naco_chrome_profile")
                )
                chrome_options.add_argument(f"--user-data-dir={profile_dir}")
            elif chrome_profile_dir:
                chrome_options.add_argument(f"--user-data-dir={chrome_profile_dir}")

            driver = webdriver.Chrome(options=chrome_options)
            drivers[name] = driver

            if name == "SICON":
                journals[name] = SICONJournal(driver)
            elif name == "SIFIN":
                journals[name] = SIFINJournal(driver)
            elif name == "MOR":
                journals[name] = MORJournal(driver, chrome_profile_dir=profile_dir)
            elif name == "MF":
                journals[name] = MFJournal(driver, chrome_profile_dir=profile_dir)
            elif name == "NACO":
                journals[name] = NACOJournal(driver, chrome_profile_dir=profile_dir)
            else:
                raise ValueError(f"Unknown journal name: {name}")

        if show_browser and not headless and name not in ("JOTA", "MAFE"):
            try:
                driver.set_window_position(-2000, 0)
            except Exception as e:
                print(f"[WARNING] Could not move window off-screen: {e}")
            hide_chrome()

    return journals, drivers

def run_sicon_then_others(args, gmail_service=None):
    selected = args.journals[:]
    sicon_data, sicon_digest = {}, ""
    rest_data, rest_digest = {}, ""
    sicon_error_journals = []
    rest_error_journals = []

    if "SICON" in selected:
        sicon_args = argparse.Namespace(**vars(args))
        sicon_args.journals = ["SICON"]
        logging.info("[INFO] Running SICON alone first...")
        sicon_data, sicon_digest, sicon_error_journals = run_journal_batch(sicon_args, gmail_service=gmail_service)
        selected = [j for j in selected if j != "SICON"]

    if selected:
        rest_args = argparse.Namespace(**vars(args))
        rest_args.journals = selected
        rest_data, rest_digest, rest_error_journals = run_journal_batch(rest_args, gmail_service=gmail_service)

    digests = []
    if sicon_digest:
        digests.append(sicon_digest)
    if rest_digest:
        digests.append(rest_digest)
    html_digest = "<br><br>".join(digests)
    return html_digest

def run_journal_batch(args, gmail_service=None):
    journals, drivers = create_journals(
        args.journals,
        show_browser=args.show_browser,
        chrome_profile_dir=args.chrome_profile_dir,
        use_playwright=getattr(args, "use_playwright", DEFAULT_USE_PLAYWRIGHT),
        force_headless=getattr(args, "force_headless", False),
        gmail_service=gmail_service,
    )
    manuscript_data = {}
    logging.info(f"Processing journals: {', '.join(journals.keys())}")

    error_journals = set()
    try:
        use_playwright = getattr(args, "use_playwright", DEFAULT_USE_PLAYWRIGHT)
        parallel = all(
            not (j in ("JOTA", "MAFE") and use_playwright)
            for j in journals.keys()
        )
        if parallel:
            with ThreadPoolExecutor(max_workers=len(journals)) as executor:
                futures = {
                    name: executor.submit(j.scrape_manuscripts_and_emails)
                    for name, j in journals.items()
                }
                for name, fut in futures.items():
                    try:
                        manuscript_data[name] = fut.result()
                        logging.info(f"Finished scraping {name}. Manuscripts: {len(manuscript_data[name]) if hasattr(manuscript_data[name], '__len__') else 'N/A'}")
                    except Exception as e:
                        logging.error(f"Error scraping {name}: {e}")
                        manuscript_data[name] = []
                        error_journals.add(name)
        else:
            for name, journal in journals.items():
                try:
                    manuscript_data[name] = journal.scrape_manuscripts_and_emails()
                    logging.info(f"Finished scraping {name}. Manuscripts: {len(manuscript_data[name]) if hasattr(manuscript_data[name], '__len__') else 'N/A'}")
                except Exception as e:
                    logging.error(f"Error scraping {name}: {e}")
                    manuscript_data[name] = []
                    error_journals.add(name)

        flagged = {}
        for name in journals.keys():
            try:
                # For JOTA, manuscript_data already comes from email scraping; fallback to fetch_starred_emails only for others
                if name == "JOTA":
                    flagged[name] = []  # Already included in manuscript_data[name]
                else:
                    flagged[name] = fetch_starred_emails(name)
                logging.info(f"Fetched {len(flagged[name])} starred emails for {name}")
            except Exception as e:
                logging.error(f"Failed to fetch emails for {name}: {e}")
                flagged[name] = []

        unmatched = {}
        urgent = {}
        digests = {}

        activation_msgs = []
        if "MOR" in journals and getattr(journals["MOR"], "activation_required", False):
            activation_msgs.append(
                "<div style='background:#ffe5b4;border:2px solid #b45700;color:#b45700;"
                "padding:9px 15px;font-weight:bold;margin-bottom:10px;font-size:15px;'>"
                "⚠️ <b>MOR required activation code</b>: "
                "Please re-authorise your Chrome profile at <a href='https://mc.manuscriptcentral.com/mathor'>MOR ScholarOne</a>.<br>"
                "Future automated runs may fail until the profile is trusted again."
                "</div>"
            )
        if "MF" in journals and getattr(journals["MF"], "activation_required", False):
            activation_msgs.append(
                "<div style='background:#ffe5b4;border:2px solid #b45700;color:#b45700;"
                "padding:9px 15px;font-weight:bold;margin-bottom:10px;font-size:15px;'>"
                "⚠️ <b>MF required activation code</b>: "
                "Please re-authorise your Chrome profile at <a href='https://mc.manuscriptcentral.com/mafi'>MF ScholarOne</a>.<br>"
                "Future automated runs may fail until the profile is trusted again."
                "</div>"
            )

        for name in journals.keys():
            match_func = match_funcs.get(name, robust_match_email_for_referee)
            unmatched[name], urgent[name] = collect_unmatched_and_urgent(
                manuscript_data[name], flagged[name], match_func
            )
            digests[name] = build_html_digest(
                name, manuscript_data[name], flagged[name], unmatched[name], urgent[name], match_func
            )
            if (name in error_journals) and name in args.journals:
                warning = (
                    f"<div style='background:#ffe2e2;border:2px solid #b30000;color:#b30000;"
                    "padding:12px 15px;font-weight:bold;margin-bottom:13px;font-size:15px;'>"
                    f"⚠️ <b>WARNING:</b> Could not retrieve manuscripts for <b>{name}</b> "
                    "due to an execution error. Please check the logs.<br></div>"
                )
                digests[name] = warning + (digests[name] or "")

            if name == "MOR" and activation_msgs:
                digests["MOR"] = "".join([msg for msg in activation_msgs if "MOR" in msg]) + digests["MOR"]
            if name == "MF" and activation_msgs:
                digests["MF"] = "".join([msg for msg in activation_msgs if "MF" in msg]) + digests["MF"]

        html_digest = "<br><br>".join(digests.values())
        return manuscript_data, html_digest, error_journals
    finally:
        for name, drv in drivers.items():
            try:
                if name in ("MAFE",) and isinstance(drv, tuple):
                    playwright, browser_ctx, page = drv
                    browser_ctx.close()
                    playwright.stop()
                elif name != "FS" and drv is not None:
                    drv.quit()
            except Exception:
                pass

def main():
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    # Initialize Gmail API client (you must implement this part according to your credentials setup)
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/gmail.readonly'])
    gmail_service = build('gmail', 'v1', credentials=creds)

    html_digest = run_sicon_then_others(args, gmail_service=gmail_service)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(html_digest)
        print(f"Digest HTML written to {args.output}")
    if args.dry_run or not args.output:
        print("\n========== DIGEST EMAIL HTML ==========")
        print(html_digest)
        print("=======================================\n")
    if not args.dry_run and not args.output:
        send_digest_email(html_digest)
        print("Digest email sent successfully.")

if __name__ == "__main__":
    main()