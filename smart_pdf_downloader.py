#!/usr/bin/env python3
"""
Smart PDF Downloader - Downloads PDFs with caching and tracking
Only downloads PDFs that haven't been downloaded before
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import json
import hashlib
import requests
import shutil
from typing import Optional, Dict
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SMART_PDF_DOWNLOADER")


class SmartPDFDownloader:
    def __init__(self, download_tracker: Dict, pdf_storage_dir: Path):
        self.download_tracker = download_tracker
        self.pdf_storage_dir = pdf_storage_dir
        self.pdf_storage_dir.mkdir(exist_ok=True)
        self.driver = None
        self.session_cookies = None
        
    def create_driver(self, headless=True):
        """Create Chrome driver with download configuration"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # Configure Chrome to download PDFs
        prefs = {
            "download.default_directory": str(self.pdf_storage_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        try:
            self.driver = uc.Chrome(options=options)
        except:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            chrome_options.add_experimental_option("prefs", prefs)
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def get_pdf_path(self, pdf_type: str, identifier: str) -> Path:
        """Get the storage path for a PDF"""
        # Create subdirectories by type
        type_dir = self.pdf_storage_dir / pdf_type
        type_dir.mkdir(exist_ok=True)
        
        # Create year/month subdirectories
        now = datetime.now()
        date_dir = type_dir / f"{now.year}" / f"{now.month:02d}"
        date_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename
        safe_id = identifier.replace('/', '_').replace('\\', '_')
        filename = f"{safe_id}.pdf"
        
        return date_dir / filename
        
    def is_already_downloaded(self, pdf_type: str, identifier: str) -> Optional[Path]:
        """Check if PDF is already downloaded and return its path"""
        tracker_key = 'manuscripts' if pdf_type == 'manuscript' else 'referee_reports'
        
        if identifier in self.download_tracker.get(tracker_key, {}):
            stored_info = self.download_tracker[tracker_key][identifier]
            stored_path = Path(stored_info['file_path'])
            
            # Verify file still exists
            if stored_path.exists():
                logger.info(f"✓ Already downloaded: {identifier}")
                return stored_path
            else:
                logger.warning(f"⚠️  Tracked file missing: {stored_path}")
                # Remove from tracker since file is gone
                del self.download_tracker[tracker_key][identifier]
                
        return None
        
    def download_with_selenium(self, url: str, pdf_type: str, identifier: str) -> Optional[Path]:
        """Download PDF using Selenium session"""
        try:
            # Check if already downloaded
            existing_path = self.is_already_downloaded(pdf_type, identifier)
            if existing_path:
                return existing_path
                
            logger.info(f"📥 Downloading {pdf_type}: {identifier}")
            
            # Get target path
            pdf_path = self.get_pdf_path(pdf_type, identifier)
            
            # Ensure URL is complete
            if url.startswith('/'):
                url = f"https://mc.manuscriptcentral.com{url}"
            elif not url.startswith('http'):
                url = f"https://mc.manuscriptcentral.com/{url}"
                
            # Try direct download with session
            success = self.download_with_session(url, pdf_path)
            
            if success and pdf_path.exists():
                # Update tracker
                tracker_key = 'manuscripts' if pdf_type == 'manuscript' else 'referee_reports'
                self.download_tracker[tracker_key][identifier] = {
                    'downloaded_date': datetime.now().isoformat(),
                    'file_path': str(pdf_path),
                    'file_size': pdf_path.stat().st_size,
                    'url': url
                }
                logger.info(f"✅ Downloaded to: {pdf_path}")
                return pdf_path
            else:
                logger.error(f"❌ Download failed for {identifier}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error downloading {identifier}: {e}")
            return None
            
    def download_with_session(self, url: str, target_path: Path) -> bool:
        """Download using session cookies from Selenium"""
        try:
            # Get cookies from Selenium if we have a driver
            if self.driver:
                cookies = self.driver.get_cookies()
                session = requests.Session()
                
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
                    
                # Add headers
                headers = {
                    'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                    'Accept': 'application/pdf,*/*',
                    'Referer': self.driver.current_url
                }
            else:
                # Fallback without cookies
                session = requests.Session()
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
                
            # Download file
            response = session.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check if it's actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower():
                # Check first few bytes
                first_bytes = response.raw.read(4)
                response.raw.seek(0)
                if first_bytes != b'%PDF':
                    logger.warning(f"Response is not a PDF (Content-Type: {content_type})")
                    return False
                    
            # Save file
            with open(target_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
                
            return True
            
        except Exception as e:
            logger.error(f"Session download error: {e}")
            return False
            
    def download_manuscript_pdfs(self, extraction_results: Dict, journal_name: str) -> Dict[str, Path]:
        """Download all manuscript PDFs from extraction results"""
        downloaded = {}
        journal = None
        
        try:
            # Create driver and login once
            self.create_driver(headless=True)
            
            if journal_name == "MF":
                journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
            else:
                journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
                
            journal.login()
            
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
            for manuscript in extraction_results.get('manuscripts', []):
                ms_id = manuscript['manuscript_id']
                
                # Check if already downloaded
                if self.is_already_downloaded('manuscript', ms_id):
                    continue
                    
                logger.info(f"\n📄 Processing manuscript: {ms_id}")
                
                try:
                    # Find and click checkbox
                    found = False
                    table = self.driver.find_element(By.TAG_NAME, "table")
                    rows = table.find_elements(By.TAG_NAME, "tr")
                    
                    for row in rows:
                        if row.text.strip().startswith(ms_id):
                            checkboxes = row.find_elements(By.XPATH, ".//img[contains(@src, 'check_off.gif')]")
                            if len(checkboxes) == 1:
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", checkboxes[0])
                                time.sleep(0.5)
                                checkboxes[0].click()
                                time.sleep(3)
                                found = True
                                break
                                
                    if found:
                        # Look for PDF
                        pdf_url = self.find_pdf_url()
                        if pdf_url:
                            pdf_path = self.download_with_selenium(pdf_url, 'manuscript', ms_id)
                            if pdf_path:
                                downloaded[ms_id] = pdf_path
                                
                        # Navigate back
                        ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                        ae_link.click()
                        time.sleep(2)
                        category_link = self.driver.find_element(By.LINK_TEXT, category)
                        category_link.click()
                        time.sleep(3)
                        
                except Exception as e:
                    logger.error(f"Error processing {ms_id}: {e}")
                    
        finally:
            if self.driver:
                self.driver.quit()
                
        return downloaded
        
    def find_pdf_url(self) -> Optional[str]:
        """Find PDF URL on current page"""
        try:
            # Try PDF tab first
            try:
                pdf_tab = self.driver.find_element(By.LINK_TEXT, "PDF")
                pdf_tab.click()
                time.sleep(2)
            except:
                pass
                
            # Look for PDF in iframes
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src")
                if src and ('pdf' in src.lower() or 'download' in src.lower()):
                    return src
                    
            # Look for download links
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                if 'pdf' in href.lower() or 'download' in href.lower():
                    return href
                    
        except Exception as e:
            logger.error(f"Error finding PDF URL: {e}")
            
        return None
        
    def download_referee_reports(self, extraction_results: Dict) -> Dict[str, Path]:
        """Download referee reports from URLs in extraction results"""
        downloaded = {}
        
        # No need for Selenium for these - they have direct URLs
        for manuscript in extraction_results.get('manuscripts', []):
            ms_id = manuscript['manuscript_id']
            
            for referee in manuscript.get('completed_referees', []):
                if referee.get('report_url'):
                    report_id = f"{ms_id}_{referee['name'].replace(' ', '_')}"
                    
                    # Extract actual URL from JavaScript
                    report_url = referee['report_url']
                    if report_url.startswith('javascript:'):
                        import re
                        match = re.search(r"popWindow\('([^']+)'", report_url)
                        if match:
                            report_url = f"https://mc.manuscriptcentral.com/{match.group(1)}"
                        else:
                            continue
                            
                    # Download report
                    pdf_path = self.download_with_selenium(report_url, 'report', report_id)
                    if pdf_path:
                        downloaded[report_id] = pdf_path
                        
        return downloaded


def download_all_pdfs(week_dir: Path, download_tracker: Dict, pdf_storage: Path):
    """Download all PDFs for the current week's extraction"""
    logger.info("\n📥 Starting PDF downloads...")
    
    downloader = SmartPDFDownloader(download_tracker, pdf_storage)
    all_downloads = {
        'manuscripts': {},
        'reports': {}
    }
    
    # Process each journal
    for journal in ['MF', 'MOR']:
        results_file = week_dir / journal.lower() / f"{journal.lower()}_referee_results.json"
        if results_file.exists():
            logger.info(f"\n📚 Processing {journal} PDFs...")
            
            with open(results_file, 'r') as f:
                extraction_data = json.load(f)
                
            # Download manuscript PDFs
            manuscript_pdfs = downloader.download_manuscript_pdfs(extraction_data, journal)
            all_downloads['manuscripts'].update(manuscript_pdfs)
            
            # Download referee reports
            report_pdfs = downloader.download_referee_reports(extraction_data)
            all_downloads['reports'].update(report_pdfs)
            
    logger.info(f"\n✅ PDF downloads completed!")
    logger.info(f"   New manuscript PDFs: {len(all_downloads['manuscripts'])}")
    logger.info(f"   New referee reports: {len(all_downloads['reports'])}")
    
    return all_downloads


if __name__ == '__main__':
    # Test with existing extraction
    from weekly_extraction_system import WeeklyExtractionSystem
    
    system = WeeklyExtractionSystem()
    
    # Download PDFs for current week
    download_all_pdfs(system.week_dir, system.download_tracker, system.pdf_storage)
    
    # Save updated tracker
    system.save_download_tracker()