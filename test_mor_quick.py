#!/usr/bin/env python3
"""Quick MOR test - 2 manuscripts only"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "production" / "src"))

required_env_vars = ["MOR_EMAIL", "MOR_PASSWORD"]
missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

if missing_vars:
    print("❌ Missing required environment variables:")
    for var in missing_vars:
        print(f"   - {var}")
    sys.exit(1)

print("✅ Credentials loaded")

from extractors.mor_extractor_enhanced import MORExtractor


def main():
    print("\n🧪 QUICK MOR TEST - 2 MANUSCRIPTS")

    extractor = MORExtractor()

    try:
        from selenium import webdriver
        from selenium.webdriver.support.ui import WebDriverWait

        extractor.driver = webdriver.Chrome(options=extractor.chrome_options)
        extractor.driver.set_page_load_timeout(30)
        extractor.driver.implicitly_wait(10)
        extractor.wait = WebDriverWait(extractor.driver, 10)
        extractor.original_window = extractor.driver.current_window_handle

        if not extractor.login():
            print("❌ Login failed")
            return 1

        if not extractor.navigate_to_ae_center():
            print("❌ Navigation failed")
            return 1

        # Process just first category, limit to 2 manuscripts
        category = "Awaiting Reviewer Reports"
        print(f"\n🔗 Processing category: {category} (2 manuscripts max)")

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import re

        wait_short = WebDriverWait(extractor.driver, 5)
        category_link = wait_short.until(EC.element_to_be_clickable((By.LINK_TEXT, category)))
        extractor.safe_click(category_link)
        extractor.smart_wait(3)

        manuscripts = []
        max_manuscripts = 2
        processed = 0

        while processed < max_manuscripts:
            try:
                current_rows = extractor.driver.find_elements(By.XPATH, "//tr[contains(., 'MOR-')]")
                if processed >= len(current_rows):
                    break

                row = current_rows[processed]
                row_text = extractor.safe_get_text(row)
                match = re.search(r"MOR-\d{4}-\d+(?:-R\d+)?", row_text)

                if not match:
                    processed += 1
                    continue

                manuscript_id = match.group()
                print(f"\n📄 [{processed+1}/{max_manuscripts}] {manuscript_id}")

                check_icon = row.find_element(By.XPATH, ".//img[contains(@src, 'check')]/parent::*")
                extractor.safe_click(check_icon)
                extractor.smart_wait(3)

                manuscript_data = extractor.extract_manuscript_details(manuscript_id)
                manuscript_data["category"] = category
                manuscripts.append(manuscript_data)

                print(
                    f"   ✅ {len(manuscript_data.get('referees', []))} referees, {len(manuscript_data.get('authors', []))} authors"
                )

                extractor.driver.back()
                extractor.smart_wait(3)
                processed += 1

            except Exception as e:
                print(f"   ❌ Error: {e}")
                processed += 1
                try:
                    extractor.driver.back()
                except:
                    pass

        print(f"\n✅ Extracted {len(manuscripts)} manuscripts")

        # Show summary
        for ms in manuscripts:
            print(f"\n📋 {ms['id']}")
            print(f"   Referees: {len(ms.get('referees', []))}")
            for ref in ms.get("referees", []):
                email_status = "✅" if ref.get("email") else "❌"
                print(f"      {email_status} {ref.get('name')} - {ref.get('email') or 'NO EMAIL'}")

        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    finally:
        try:
            if extractor.driver:
                extractor.driver.quit()
        except:
            pass


if __name__ == "__main__":
    sys.exit(main())
