#!/usr/bin/env python3
"""
JOTA Editorial Manager Recon v3
- Double-nested iframe for login: default.aspx → iframe#content → iframe[name=login]
- Role dropdown is in TOP frame (default2.aspx), not content iframe
- Select "editor" value (title="Associate Editor") in #RoleDropdown
- Then explore Editor dashboard in content iframe
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    NoSuchFrameException,
    StaleElementReferenceException,
)

CAPTURES = Path(__file__).parent / "captures" / "jota"
CAPTURES.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://www.editorialmanager.com/jota"
USERNAME = os.environ.get("JOTA_USERNAME", "")
PASSWORD = os.environ.get("JOTA_PASSWORD", "")


def save(driver, name):
    ts = datetime.now().strftime("%H%M%S")
    p = CAPTURES / f"{name}_{ts}"
    try:
        driver.save_screenshot(str(p) + ".png")
        with open(str(p) + ".html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    except Exception:
        pass
    print(f"   💾 {name}")


def dump(driver, label):
    print(f"\n--- {label} ---")
    print(f"URL: {driver.current_url}")
    for tag in ["iframe", "select"]:
        els = driver.find_elements(By.TAG_NAME, tag)
        if els:
            print(f"{tag}s: {len(els)}")
            for el in els[:5]:
                print(
                    f"  id={el.get_attribute('id')}, name={el.get_attribute('name')}, src={el.get_attribute('src')}"
                )
    links = driver.find_elements(By.TAG_NAME, "a")
    visible = [
        (a.text.strip()[:60], (a.get_attribute("href") or "")[:100])
        for a in links
        if a.text.strip()
    ]
    if visible:
        print(f"Links ({len(visible)}):")
        for t, h in visible[:25]:
            print(f"  [{t}] → {h}")
    # fieldsets
    fieldsets = driver.find_elements(By.TAG_NAME, "fieldset")
    if fieldsets:
        print(f"Fieldsets ({len(fieldsets)}):")
        for fs in fieldsets[:10]:
            legend = ""
            try:
                legend = fs.find_element(By.TAG_NAME, "legend").text.strip()
            except Exception:
                pass
            print(f"  legend={legend}, text={fs.text.strip()[:100]}")
    # tables
    tables = driver.find_elements(By.TAG_NAME, "table")
    if tables:
        print(f"Tables: {len(tables)}")


def main():
    if not USERNAME or not PASSWORD:
        print("❌ Set JOTA_USERNAME and JOTA_PASSWORD")
        sys.exit(1)

    print(f"🔍 JOTA Recon v3 — {BASE_URL}")

    import subprocess

    chrome_version = None
    try:
        result = subprocess.run(
            ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"],
            capture_output=True,
            text=True,
        )
        chrome_version = int(result.stdout.strip().split()[-1].split(".")[0])
    except Exception:
        pass

    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1400,900")

    driver = uc.Chrome(options=options, headless=False, version_main=chrome_version)

    try:
        # LOGIN
        print("\n📍 Login")
        driver.get(f"{BASE_URL}/default.aspx")
        time.sleep(4)

        driver.switch_to.frame("content")
        driver.switch_to.frame("login")
        print("   ✅ In login iframe")

        driver.find_element(By.ID, "username").send_keys(USERNAME)
        time.sleep(0.3)
        driver.find_element(By.CSS_SELECTOR, "input[name='password']").send_keys(PASSWORD)
        time.sleep(0.3)
        driver.execute_script("arguments[0].click()", driver.find_element(By.ID, "loginButton"))
        print("   ✅ Submitted credentials")

        time.sleep(8)
        driver.switch_to.default_content()
        save(driver, "01_post_login_top")

        # ROLE SWITCH (in TOP frame — use JavaScript since dropdown may be hidden/styled)
        print("\n📍 Role Switch")
        try:
            current = driver.execute_script("return document.getElementById('RoleDropdown').value")
            print(f"   Current role: {current}")

            if current != "editor":
                driver.execute_script(
                    """
                    var dd = document.getElementById('RoleDropdown');
                    dd.value = 'editor';
                    closeSysAdmin();
                    setTimeout(function() { __doPostBack('RoleDropdown',''); }, 0);
                """
                )
                print("   ✅ JS role switch triggered")
                time.sleep(10)
                save(driver, "02_editor_role_top")
            else:
                print("   ✅ Already in editor role")
        except Exception as e:
            print(f"   ⚠️ Role switch error: {e}")
            # Fallback: try __doPostBack directly
            try:
                driver.execute_script(
                    """
                    document.getElementById('RoleDropdown').value = 'editor';
                    __doPostBack('RoleDropdown','');
                """
                )
                print("   ✅ Fallback __doPostBack triggered")
                time.sleep(10)
            except Exception as e2:
                print(f"   ❌ Fallback also failed: {e2}")

        # EDITOR DASHBOARD (in content iframe)
        print("\n📍 Editor Dashboard")
        driver.switch_to.default_content()
        save(driver, "03_editor_top")
        dump(driver, "Editor top frame")

        try:
            driver.switch_to.frame("content")
            print("   ✅ In content iframe")
            save(driver, "04_editor_dashboard")
            dump(driver, "Editor dashboard (content iframe)")
        except Exception as e:
            print(f"   ⚠️ No content iframe: {e}")
            dump(driver, "Editor page (no iframe)")

        # FIND FOLDERS
        print("\n📍 Manuscript Folders")
        folder_links = []

        # Try fieldsets with legends
        fieldsets = driver.find_elements(By.TAG_NAME, "fieldset")
        for fs in fieldsets:
            try:
                legend = fs.find_element(By.TAG_NAME, "legend").text.strip()
                inner_links = fs.find_elements(By.TAG_NAME, "a")
                for link in inner_links:
                    text = link.text.strip()
                    href = link.get_attribute("href") or ""
                    if text:
                        print(f"   [{legend}] {text} → {href[:80]}")
                        folder_links.append((text, href, link))
            except Exception:
                continue

        # Also try all links
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for a in all_links:
            text = a.text.strip()
            href = a.get_attribute("href") or ""
            if any(
                kw in text for kw in ["Referees", "Review", "Revised", "Decision", "New Assign"]
            ):
                if (text, href) not in [(t, h) for t, h, _ in folder_links]:
                    print(f"   [extra] {text} → {href[:80]}")
                    folder_links.append((text, href, a))

        save(driver, "05_folders")

        # CLICK FIRST FOLDER WITH MANUSCRIPTS
        print("\n📍 Click into folder")
        clicked = False
        for text, href, el in folder_links:
            if "(0)" not in text:
                print(f"   Clicking: {text}")
                try:
                    el.click()
                    time.sleep(5)
                    save(driver, "06_folder_listing")
                    dump(driver, f"Folder: {text}")
                    clicked = True
                    break
                except Exception as e:
                    print(f"   ⚠️ Click failed: {e}")
                    # Try JS click
                    try:
                        driver.execute_script("arguments[0].click()", el)
                        time.sleep(5)
                        save(driver, "06_folder_listing")
                        dump(driver, f"Folder (JS): {text}")
                        clicked = True
                        break
                    except Exception:
                        continue

        if not clicked:
            print("   ⚠️ No clickable folder found")

        # MANUSCRIPT LISTING
        if clicked:
            print("\n📍 Manuscript Listing")
            # Look for table rows, action links, manuscript IDs
            tables = driver.find_elements(By.TAG_NAME, "table")
            print(f"   Tables: {len(tables)}")
            for i, tbl in enumerate(tables):
                rows = tbl.find_elements(By.TAG_NAME, "tr")
                if len(rows) > 1:
                    print(f"   table[{i}]: {len(rows)} rows")
                    for j, row in enumerate(rows[:5]):
                        print(f"      row[{j}]: {row.text.strip()[:150]}")
                        # Check links in row
                        row_links = row.find_elements(By.TAG_NAME, "a")
                        for rl in row_links:
                            rtext = rl.text.strip()[:40]
                            rhref = (rl.get_attribute("href") or "")[:80]
                            ronclick = (rl.get_attribute("onclick") or "")[:80]
                            if rtext or ronclick:
                                print(f"        link: [{rtext}] href={rhref} onclick={ronclick}")

            # Also try div-based listings
            divs = driver.find_elements(
                By.CSS_SELECTOR, "[class*='manuscript'], [id*='manuscript']"
            )
            if divs:
                print(f"   Manuscript divs: {len(divs)}")
                for d in divs[:5]:
                    print(f"      {d.text.strip()[:100]}")

            save(driver, "07_manuscripts")

            # CLICK FIRST MANUSCRIPT
            print("\n📍 Click into manuscript")
            ms_clicked = False
            all_links = driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                href = link.get_attribute("href") or ""
                onclick = link.get_attribute("onclick") or ""
                text = link.text.strip()
                combined = (href + onclick).lower()
                if any(
                    kw in combined
                    for kw in [
                        "actiondetail",
                        "manuscriptdetail",
                        "openmanuscript",
                        "viewmanuscript",
                        "edit_ms_code",
                    ]
                ):
                    print(f"   Clicking: [{text[:50]}] href={href[:60]} onclick={onclick[:60]}")
                    try:
                        link.click()
                        time.sleep(6)
                        save(driver, "08_manuscript_detail")
                        dump(driver, "Manuscript detail")
                        ms_clicked = True
                        break
                    except Exception as e:
                        print(f"   ⚠️ Click failed: {e}")

            if ms_clicked:
                # LOOK FOR REFEREE SECTION
                print("\n📍 Referee Section")
                page_text = driver.page_source
                import re

                # Look for common EM patterns
                for pattern in [
                    "reviewerHoverDetails",
                    "referee",
                    "Reviewer",
                    "linkWithFlags",
                    "InviteReviewer",
                    "ReviewerStatus",
                    "reviewerInvite",
                ]:
                    if pattern.lower() in page_text.lower():
                        print(f"   ✅ Found '{pattern}' in page source")

                # Find reviewer tables/sections
                for sel in [
                    "[class*='reviewer']",
                    "[class*='Reviewer']",
                    "[id*='reviewer']",
                    "[id*='Reviewer']",
                    "table.reviewer",
                    "div.reviewer",
                    "[class*='referee']",
                    "table[class*='ActionStatus']",
                ]:
                    try:
                        els = driver.find_elements(By.CSS_SELECTOR, sel)
                        if els:
                            print(f"   ✅ {len(els)} elements: {sel}")
                            for el in els[:3]:
                                print(f"      {el.text.strip()[:100]}")
                    except Exception:
                        continue

                save(driver, "09_referee_section")

                # LOOK FOR HISTORY/AUDIT
                print("\n📍 Audit/History links")
                all_links = driver.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    text = link.text.strip()
                    href = link.get_attribute("href") or ""
                    if any(
                        kw in text.lower() for kw in ["histor", "audit", "log", "event", "timeline"]
                    ):
                        print(f"   [{text}] → {href[:80]}")
                    if any(kw in href.lower() for kw in ["histor", "audit", "actionlog"]):
                        print(f"   [{text}] → {href[:80]}")

                # LOOK FOR DOCUMENTS
                print("\n📍 Document links")
                for link in all_links:
                    text = link.text.strip()
                    href = link.get_attribute("href") or ""
                    if any(
                        kw in (text + href).lower()
                        for kw in ["pdf", "download", "document", "file", "view_manuscript"]
                    ):
                        print(f"   [{text}] → {href[:80]}")

            if not ms_clicked:
                print("   ⚠️ No manuscript detail link found")

        # DONE
        print("\n" + "=" * 60)
        print("✅ RECON COMPLETE — Ctrl+C to exit")
        print("=" * 60)
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n👋 Done")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        save(driver, "error")
        time.sleep(300)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
