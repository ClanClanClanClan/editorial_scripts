from playwright.sync_api import sync_playwright

USER_DATA_DIR = "./my_jota_profile"  # your existing profile folder

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=USER_DATA_DIR,
        headless=False,  # show browser so you can interact
        viewport={"width": 1280, "height": 800},
        args=[
            "--disable-blink-features=AutomationControlled"
        ],
    )
    page = browser.new_page()
    page.goto("https://www.editorialmanager.com/jota/default1.aspx")
    print("Browser opened with persistent profile. Please log in manually.")
    input("After login and navigation, press Enter here to close browser and exit...")
    browser.close()