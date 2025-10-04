#!/usr/bin/env python3
import sys
from pathlib import Path

print("1. Starting...")
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "production" / "src"))

print("2. Importing extractor...")
from extractors.mor_extractor_enhanced import MORExtractor

print("3. Creating instance (use_cache=False)...")
extractor = MORExtractor(use_cache=False, max_manuscripts_per_category=1)

print("4. Instance created!")
print(f"   - driver: {extractor.driver}")
print(f"   - wait: {extractor.wait}")
print(f"   - chrome_options: {extractor.chrome_options}")

print("5. Setting up driver...")
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

extractor.driver = webdriver.Chrome(options=extractor.chrome_options)
print("6. Driver created!")

extractor.wait = WebDriverWait(extractor.driver, 10)
print("7. Wait created!")

print("8. Testing login...")
extractor.driver.get("https://mc.manuscriptcentral.com/mor")
print(f"9. Loaded page: {extractor.driver.title[:50]}...")

extractor.driver.quit()
print("10. ✅ All steps successful!")
