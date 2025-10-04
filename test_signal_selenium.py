#!/usr/bin/env python3
import signal
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def timeout_handler(signum, frame):
    print("⏱️ SIGALRM fired!")
    raise TimeoutError("Timeout")


chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")

driver = webdriver.Chrome(options=chrome_options)

print("Testing SIGALRM with Selenium...")

# Set 2-second timeout
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(2)

try:
    print("Starting long wait (10s)...")
    driver.get("https://www.google.com")
    time.sleep(10)  # This should be interrupted
    print("❌ Completed sleep (timeout didn't work)")
except TimeoutError as e:
    print(f"✅ Timeout worked: {e}")
finally:
    signal.alarm(0)
    driver.quit()
