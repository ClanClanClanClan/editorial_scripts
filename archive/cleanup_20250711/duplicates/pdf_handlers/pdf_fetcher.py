#!/usr/bin/env python3
"""
PDF Fetcher - Downloads PDFs for manuscripts using existing extraction results
Works alongside the existing referee extractor to get PDFs
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import json
import re
import requests
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PDF_FETCHER")


class PDFFetcher:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_pdfs")
        self.output_dir.mkdir(exist_ok=True)
        
    def create_driver(self, headless=False):
        """Create Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # Configure downloads
        prefs = {
            "download.default_directory": str(self.output_dir.absolute()),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        try:
            self.driver = uc.Chrome(options=options)
        except:
            from selenium import webdriver
            self.driver = webdriver.Chrome(options=options)
            
    def fetch_pdfs(self, manuscripts, headless=True):
        """Fetch PDFs for given manuscripts"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 PDF FETCHER - {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=headless)
        results = []
        
        try:
            # Login
            if self.journal_name == "MF":
                self.journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
            else:
                self.journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
                
            self.journal.login()
            
            # Navigate to AE Center
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(2)
            
            # Navigate to category
            category_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, category))
            )
            category_link.click()
            time.sleep(3)
            
            # Process each manuscript
            for ms_id in manuscripts:
                logger.info(f"\n{'='*60}")
                logger.info(f"📄 Processing: {ms_id}")
                
                result = {
                    'manuscript_id': ms_id,
                    'pdf_downloaded': False,
                    'pdf_path': '',
                    'report_pdfs': []
                }
                
                try:
                    # Method 1: Try direct PDF download from checkbox click
                    found_checkbox = None
                    table = self.driver.find_element(By.TAG_NAME, "table")
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    for row in rows:
                        row_text = row.text.strip()
                        if row_text.startswith(ms_id):
                            checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                            if len(checkboxes) == 1:
                                found_checkbox = checkboxes[0]
                                break
                                
                    if found_checkbox:
                        logger.info("✅ Found checkbox, clicking...")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", found_checkbox)
                        time.sleep(0.5)
                        found_checkbox.click()
                        time.sleep(3)
                        
                        # Try to find PDF download
                        logger.info("🔍 Looking for PDF download options...")
                        
                        # Method A: Click PDF tab if available
                        try:
                            pdf_tab = self.driver.find_element(By.LINK_TEXT, "PDF")
                            logger.info("📄 Found PDF tab!")
                            pdf_tab.click()
                            time.sleep(2)
                            
                            # Check for iframe with PDF
                            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                            for iframe in iframes:
                                src = iframe.get_attribute("src")
                                if src and ('pdf' in src.lower() or 'download' in src.lower()):
                                    logger.info(f"📥 Found PDF iframe: {src[:50]}...")
                                    
                                    # Download using session
                                    pdf_path = self.download_with_session(src, f"{ms_id}_manuscript.pdf")
                                    if pdf_path:
                                        result['pdf_downloaded'] = True
                                        result['pdf_path'] = pdf_path
                                        break
                                        
                        except Exception as e:
                            logger.info(f"   ℹ️  No PDF tab found: {e}")
                            
                        # Method B: Look for download links
                        if not result['pdf_downloaded']:
                            download_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "Download")
                            for link in download_links:
                                href = link.get_attribute("href")
                                if href and 'pdf' in href.lower():
                                    logger.info(f"📥 Found download link")
                                    pdf_path = self.download_with_session(href, f"{ms_id}_manuscript.pdf")
                                    if pdf_path:
                                        result['pdf_downloaded'] = True
                                        result['pdf_path'] = pdf_path
                                        break
                                        
                        # Navigate back
                        logger.info("🔄 Navigating back...")
                        ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                        ae_link.click()
                        time.sleep(2)
                        category_link = self.driver.find_element(By.LINK_TEXT, category)
                        category_link.click()
                        time.sleep(3)
                        
                except Exception as e:
                    logger.error(f"❌ Error processing {ms_id}: {e}")
                    result['error'] = str(e)
                    
                results.append(result)
                
            # Save results
            self.save_results(results)
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()
            
        return results
        
    def download_with_session(self, url, filename):
        """Download file using session cookies"""
        try:
            # Ensure full URL
            if url.startswith('/'):
                url = f"https://mc.manuscriptcentral.com{url}"
            elif not url.startswith('http'):
                url = f"https://mc.manuscriptcentral.com/{self.journal_name.lower()}/{url}"
                
            logger.info(f"   📥 Downloading from: {url[:80]}...")
            
            # Get cookies
            cookies = self.driver.get_cookies()
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
                
            # Download
            headers = {
                'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                'Referer': self.driver.current_url
            }
            
            response = session.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Save file
            file_path = self.output_dir / filename
            with open(file_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
                
            file_size = file_path.stat().st_size
            logger.info(f"   ✅ Saved: {file_path} ({file_size:,} bytes)")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"   ❌ Download failed: {e}")
            return None
            
    def save_results(self, results):
        """Save download results"""
        summary_file = self.output_dir / f"{self.journal_name.lower()}_pdf_summary.txt"
        with open(summary_file, 'w') as f:
            f.write(f"PDF FETCH SUMMARY - {self.journal_name}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            
            total = len(results)
            downloaded = sum(1 for r in results if r.get('pdf_downloaded'))
            
            f.write(f"Total manuscripts: {total}\n")
            f.write(f"PDFs downloaded: {downloaded}\n")
            f.write(f"Success rate: {downloaded/total*100:.1f}%\n\n")
            
            for result in results:
                f.write(f"Manuscript: {result['manuscript_id']}\n")
                f.write(f"PDF: {'✅ Downloaded' if result.get('pdf_downloaded') else '❌ Not downloaded'}\n")
                if result.get('pdf_path'):
                    f.write(f"Path: {result['pdf_path']}\n")
                if result.get('error'):
                    f.write(f"Error: {result['error']}\n")
                f.write(f"{'-'*60}\n\n")
                
        logger.info(f"\n✅ Summary saved to: {summary_file}")


def main():
    """Main function"""
    # Load existing extraction results to get manuscript IDs
    mor_results_file = Path("mor_final_working_results/mor_referee_results.json")
    mf_results_file = Path("mf_final_working_results/mf_referee_results.json")
    
    if mor_results_file.exists():
        logger.info("📊 Processing MOR PDFs...")
        with open(mor_results_file) as f:
            mor_data = json.load(f)
        
        manuscripts = [ms['manuscript_id'] for ms in mor_data.get('manuscripts', [])]
        if manuscripts:
            fetcher = PDFFetcher("MOR")
            fetcher.fetch_pdfs(manuscripts, headless=True)
            
    if mf_results_file.exists():
        logger.info("\n📊 Processing MF PDFs...")
        with open(mf_results_file) as f:
            mf_data = json.load(f)
            
        manuscripts = [ms['manuscript_id'] for ms in mf_data.get('manuscripts', [])]
        if manuscripts:
            fetcher = PDFFetcher("MF") 
            fetcher.fetch_pdfs(manuscripts, headless=True)


if __name__ == '__main__':
    main()