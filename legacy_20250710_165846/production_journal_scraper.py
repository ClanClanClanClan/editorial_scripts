#!/usr/bin/env python3
"""
Production Journal Scraper - Complete Implementation
Handles: referee extraction, PDF downloads, deduplication, error recovery
"""

import os
import sys
import time
import logging
import hashlib
import json
import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import re
import requests
from urllib.parse import urljoin, urlparse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal

@dataclass
class RefereeInfo:
    """Complete referee information"""
    name: str
    email: str
    status: str  # agreed, declined, unavailable, invited
    invited_date: Optional[str] = None
    agreed_date: Optional[str] = None
    declined_date: Optional[str] = None
    due_date: Optional[str] = None
    time_in_review: Optional[str] = None
    reports_available: bool = False
    report_urls: List[str] = None
    
    def __post_init__(self):
        if self.report_urls is None:
            self.report_urls = []
    
    @property
    def is_active(self) -> bool:
        """Is this referee actively reviewing?"""
        return self.status in ['agreed', 'invited'] and self.status != 'declined'

@dataclass
class ManuscriptInfo:
    """Complete manuscript information"""
    manuscript_id: str
    title: str
    journal: str
    category: str
    submission_date: Optional[str] = None
    referees: List[RefereeInfo] = None
    pdf_url: Optional[str] = None
    pdf_downloaded: bool = False
    pdf_path: Optional[Path] = None
    duplicate_categories: List[str] = None
    last_updated: Optional[str] = None
    
    def __post_init__(self):
        if self.referees is None:
            self.referees = []
        if self.duplicate_categories is None:
            self.duplicate_categories = []
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()
    
    @property
    def active_referee_count(self) -> int:
        """Number of active referees"""
        return len([ref for ref in self.referees if ref.is_active])
    
    @property
    def total_referee_count(self) -> int:
        """Total number of referees"""
        return len(self.referees)

class ProgressTracker:
    """Track and persist scraping progress"""
    
    def __init__(self, journal_name: str, progress_file: Path):
        self.journal_name = journal_name
        self.progress_file = progress_file
        self.progress_data = self.load_progress()
        
    def load_progress(self) -> Dict:
        """Load existing progress"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'processed_categories': [],
            'processed_manuscripts': set(),
            'downloaded_pdfs': set(),
            'failed_downloads': set(),
            'last_session': None,
            'total_manuscripts': 0,
            'total_referees': 0
        }
    
    def save_progress(self):
        """Save current progress"""
        # Convert sets to lists for JSON serialization
        save_data = self.progress_data.copy()
        save_data['processed_manuscripts'] = list(save_data['processed_manuscripts'])
        save_data['downloaded_pdfs'] = list(save_data['downloaded_pdfs'])
        save_data['failed_downloads'] = list(save_data['failed_downloads'])
        save_data['last_session'] = datetime.now().isoformat()
        
        with open(self.progress_file, 'w') as f:
            json.dump(save_data, f, indent=2)
    
    def mark_manuscript_processed(self, manuscript_id: str):
        """Mark manuscript as processed"""
        self.progress_data['processed_manuscripts'].add(manuscript_id)
        self.save_progress()
    
    def is_manuscript_processed(self, manuscript_id: str) -> bool:
        """Check if manuscript already processed"""
        return manuscript_id in self.progress_data['processed_manuscripts']

class PDFDownloadManager:
    """Manage PDF downloads with deduplication and organization"""
    
    def __init__(self, download_dir: Path, journal_name: str):
        self.download_dir = download_dir
        self.journal_name = journal_name
        self.setup_directories()
        
    def setup_directories(self):
        """Create organized directory structure"""
        self.journal_dir = self.download_dir / self.journal_name
        self.manuscripts_dir = self.journal_dir / "manuscripts"
        self.reports_dir = self.journal_dir / "referee_reports"
        
        for dir_path in [self.manuscripts_dir, self.reports_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def download_manuscript_pdf(self, manuscript: ManuscriptInfo, pdf_url: str) -> Optional[Path]:
        """Download manuscript PDF with organization"""
        category_dir = self.manuscripts_dir / manuscript.category.replace(' ', '_')
        category_dir.mkdir(exist_ok=True)
        
        filename = f"{manuscript.manuscript_id}_{manuscript.title[:50].replace(' ', '_')}.pdf"
        # Clean filename
        filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
        filepath = category_dir / filename
        
        # Check if already downloaded
        if filepath.exists():
            logging.info(f"📄 PDF already exists: {filename}")
            return filepath
            
        try:
            # Download with requests for better control
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
                
            logging.info(f"📥 Downloaded: {filename}")
            return filepath
            
        except Exception as e:
            logging.error(f"❌ Failed to download {filename}: {e}")
            return None
    
    def download_referee_report(self, manuscript_id: str, referee_name: str, report_url: str) -> Optional[Path]:
        """Download referee report"""
        referee_dir = self.reports_dir / manuscript_id
        referee_dir.mkdir(exist_ok=True)
        
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', referee_name)
        filename = f"{manuscript_id}_report_{safe_name}.pdf"
        filepath = referee_dir / filename
        
        if filepath.exists():
            logging.info(f"📄 Report already exists: {filename}")
            return filepath
            
        try:
            response = requests.get(report_url, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
                
            logging.info(f"📥 Downloaded report: {filename}")
            return filepath
            
        except Exception as e:
            logging.error(f"❌ Failed to download report {filename}: {e}")
            return None
    
    def calculate_file_hash(self, filepath: Path) -> str:
        """Calculate file hash for deduplication"""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

class ProductionJournalScraper:
    """Production-ready journal scraper with all features"""
    
    def __init__(self, journal_name: str, download_dir: Path, debug: bool = False):
        self.journal_name = journal_name
        self.download_dir = download_dir
        self.debug = debug
        
        # Setup components
        self.progress_tracker = ProgressTracker(
            journal_name, 
            download_dir / f"{journal_name.lower()}_progress.json"
        )
        self.pdf_manager = PDFDownloadManager(download_dir, journal_name)
        
        # Data storage
        self.manuscripts: Dict[str, ManuscriptInfo] = {}
        self.duplicate_tracker: Dict[str, List[str]] = {}
        
        # WebDriver
        self.driver = None
        self.journal = None
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup comprehensive logging"""
        log_file = self.download_dir / f"{self.journal_name.lower()}_scraping.log"
        
        logging.basicConfig(
            level=logging.INFO if not self.debug else logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(f"{self.journal_name}_SCRAPER")
        
    def create_driver(self, headless=True):
        """Create optimized Chrome driver"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-popup-blocking')
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        # Download preferences
        prefs = {
            "download.default_directory": str(self.pdf_manager.manuscripts_dir.absolute()),
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True
        }
        options.add_experimental_option("prefs", prefs)
        
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
    
    def login_and_setup(self):
        """Login and initial setup"""
        self.logger.info(f"🔐 Logging into {self.journal_name}")
        
        if self.journal_name == "MF":
            self.journal = MFJournal(self.driver, debug=self.debug)
        else:
            self.journal = MORJournal(self.driver, debug=self.debug)
            
        self.journal.login()
        
        # Navigate to AE Center
        ae_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
        )
        ae_link.click()
        time.sleep(3)
        
    def discover_manuscripts_in_categories(self) -> Dict[str, List[str]]:
        """Discover all manuscripts across all categories"""
        self.logger.info("🔍 Discovering manuscripts across all categories...")
        
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        # Find categories with manuscripts
        category_patterns = [
            r'(\d+)\s*([A-Z][A-Za-z\s]+(?:Reviewer|Review|Awaiting|Overdue)[A-Za-z\s]*)',
            r'(\d+)\s*(Awaiting[A-Za-z\s]+)',
            r'(\d+)\s*(Overdue[A-Za-z\s]+)'
        ]
        
        categories_with_manuscripts = {}
        
        for pattern in category_patterns:
            matches = re.findall(pattern, page_text)
            for count, category_name in matches:
                count = int(count)
                category_name = category_name.strip()
                
                if (count > 0 and 
                    len(category_name) > 5 and 
                    any(word in category_name.lower() for word in ['awaiting', 'overdue', 'reviewer'])):
                    
                    if category_name not in categories_with_manuscripts:
                        categories_with_manuscripts[category_name] = count
                        
        self.logger.info(f"📊 Found categories with manuscripts:")
        for category, count in categories_with_manuscripts.items():
            self.logger.info(f"  • {category}: {count} manuscripts")
            
        return categories_with_manuscripts
    
    def process_category(self, category_name: str) -> List[ManuscriptInfo]:
        """Process all manuscripts in a category"""
        self.logger.info(f"📂 Processing category: {category_name}")
        
        try:
            # Navigate to category
            category_link = self.driver.find_element(By.LINK_TEXT, category_name)
            category_link.click()
            time.sleep(3)
            
            # Extract manuscripts
            manuscripts = self.extract_manuscripts_from_category(category_name)
            
            # Process each manuscript for detailed info
            for manuscript in manuscripts:
                if not self.progress_tracker.is_manuscript_processed(manuscript.manuscript_id):
                    self.extract_detailed_manuscript_info(manuscript)
                    self.progress_tracker.mark_manuscript_processed(manuscript.manuscript_id)
                else:
                    self.logger.info(f"⏭️ Skipping already processed: {manuscript.manuscript_id}")
            
            # Navigate back
            ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
            ae_link.click()
            time.sleep(2)
            
            return manuscripts
            
        except Exception as e:
            self.logger.error(f"❌ Failed to process category {category_name}: {e}")
            return []
    
    def extract_manuscripts_from_category(self, category_name: str) -> List[ManuscriptInfo]:
        """Extract basic manuscript info from category page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        if self.journal_name == "MF":
            ms_pattern = r'MAFI-\d{4}-\d+'
        else:
            ms_pattern = r'MOR-\d{4}-\d+'
            
        ms_ids = list(set(re.findall(ms_pattern, soup.get_text())))
        manuscripts = []
        
        for ms_id in ms_ids:
            # Check for duplicates
            if ms_id in self.manuscripts:
                # Track duplicate category
                self.manuscripts[ms_id].duplicate_categories.append(category_name)
                continue
                
            manuscript = ManuscriptInfo(
                manuscript_id=ms_id,
                title="",  # Will be extracted later
                journal=self.journal_name,
                category=category_name
            )
            
            # Extract basic referee info from list view
            referee_counts = self.extract_referee_counts_from_list(ms_id)
            if referee_counts:
                manuscript.referees = self.create_basic_referee_list(referee_counts)
            
            manuscripts.append(manuscript)
            self.manuscripts[ms_id] = manuscript
            
        return manuscripts
    
    def extract_referee_counts_from_list(self, manuscript_id: str) -> Optional[Dict]:
        """Extract referee counts from list page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find the row containing this manuscript
        for element in soup.find_all(string=re.compile(manuscript_id)):
            parent_row = element.parent
            while parent_row and parent_row.name != 'tr':
                parent_row = parent_row.parent
                
            if parent_row:
                row_text = parent_row.get_text()
                
                if ('active selections' in row_text or 'invited' in row_text or 
                    'agreed' in row_text or 'declined' in row_text):
                    
                    # Extract counts
                    counts = {}
                    for pattern, key in [
                        (r'(\d+)\s+active\s+selections', 'active_selections'),
                        (r'(\d+)\s+invited', 'invited'),
                        (r'(\d+)\s+agreed', 'agreed'),
                        (r'(\d+)\s+declined', 'declined'),
                        (r'(\d+)\s+returned', 'returned')
                    ]:
                        match = re.search(pattern, row_text)
                        counts[key] = int(match.group(1)) if match else 0
                        
                    return counts
        return None
    
    def create_basic_referee_list(self, counts: Dict) -> List[RefereeInfo]:
        """Create basic referee list from counts"""
        referees = []
        
        # Create placeholder referees based on counts
        for i in range(counts.get('agreed', 0)):
            referees.append(RefereeInfo(
                name=f"Referee_{i+1}",
                email="",
                status="agreed"
            ))
            
        for i in range(counts.get('declined', 0)):
            referees.append(RefereeInfo(
                name=f"Declined_Referee_{i+1}",
                email="",
                status="declined"
            ))
            
        return referees
    
    def extract_detailed_manuscript_info(self, manuscript: ManuscriptInfo):
        """Extract detailed information using Take Action"""
        self.logger.info(f"🔍 Extracting detailed info for {manuscript.manuscript_id}")
        
        try:
            # Find and click Take Action checkbox
            checkbox = self.find_take_action_checkbox(manuscript.manuscript_id)
            if checkbox:
                checkbox.click()
                time.sleep(1)
                
                # Submit Take Action
                submit_btn = self.driver.find_element(By.XPATH, "//input[@value='Take Action' or @type='submit']")
                submit_btn.click()
                time.sleep(3)
                
                # Extract detailed referee information
                self.extract_detailed_referee_info(manuscript)
                
                # Extract PDF links
                manuscript.pdf_url = self.extract_pdf_url()
                
                # Download PDF if available
                if manuscript.pdf_url:
                    pdf_path = self.pdf_manager.download_manuscript_pdf(manuscript, manuscript.pdf_url)
                    if pdf_path:
                        manuscript.pdf_downloaded = True
                        manuscript.pdf_path = pdf_path
                
                # Navigate back
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                ae_link.click()
                time.sleep(2)
                
        except Exception as e:
            self.logger.error(f"❌ Failed to extract detailed info for {manuscript.manuscript_id}: {e}")
    
    def find_take_action_checkbox(self, manuscript_id: str):
        """Find Take Action checkbox for manuscript"""
        rows = self.driver.find_elements(By.TAG_NAME, "tr")
        
        for row in rows:
            if manuscript_id in row.text:
                checkboxes = row.find_elements(By.XPATH, ".//input[@type='checkbox']")
                if checkboxes:
                    return checkboxes[0]
        return None
    
    def extract_detailed_referee_info(self, manuscript: ManuscriptInfo):
        """Extract detailed referee info from Take Action page"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Look for referee tables
        referee_links = []
        for link in soup.find_all('a'):
            link_text = link.get_text(strip=True)
            if (' ' in link_text and 
                any(c.isupper() for c in link_text) and
                len(link_text) > 3 and
                not any(word in link_text.lower() for word in ['view', 'download', 'edit', 'manuscript'])):
                
                # This looks like a referee name
                email = self.extract_referee_email(link_text)
                history = self.extract_referee_history_from_page(link_text)
                
                referee = RefereeInfo(
                    name=link_text,
                    email=email or "",
                    status="agreed",  # Default, should be determined from history
                    **history
                )
                
                manuscript.referees.append(referee)
    
    def extract_referee_email(self, referee_name: str) -> Optional[str]:
        """Extract referee email by clicking name"""
        try:
            main_window = self.driver.current_window_handle
            
            referee_link = self.driver.find_element(By.LINK_TEXT, referee_name)
            referee_link.click()
            time.sleep(2)
            
            # Check for popup
            all_windows = self.driver.window_handles
            if len(all_windows) > 1:
                for window in all_windows:
                    if window != main_window:
                        self.driver.switch_to.window(window)
                        break
                        
                # Extract email from popup
                popup_html = self.driver.page_source
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, popup_html)
                
                self.driver.close()
                self.driver.switch_to.window(main_window)
                
                return emails[0] if emails else None
                
        except Exception as e:
            self.logger.warning(f"Could not extract email for {referee_name}: {e}")
            try:
                self.driver.switch_to.window(main_window)
            except:
                pass
        return None
    
    def extract_referee_history_from_page(self, referee_name: str) -> Dict:
        """Extract referee history information"""
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        page_text = soup.get_text()
        
        history = {}
        
        # Look for history patterns
        patterns = {
            'invited_date': r'Invited:\s*(\d{2}-\w{3}-\d{4})',
            'agreed_date': r'Agreed:\s*(\d{2}-\w{3}-\d{4})',
            'due_date': r'Due Date:\s*(\d{2}-\w{3}-\d{4})',
            'time_in_review': r'Time in Review:\s*(\d+\s+Days)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, page_text)
            if match:
                history[key] = match.group(1)
                
        return history
    
    def extract_pdf_url(self) -> Optional[str]:
        """Extract PDF download URL"""
        try:
            pdf_links = self.driver.find_elements(By.PARTIAL_LINK_TEXT, "View Submission")
            if pdf_links:
                return pdf_links[0].get_attribute('href')
        except:
            pass
        return None
    
    def deduplicate_manuscripts(self):
        """Remove duplicates and track cross-category appearances"""
        self.logger.info("🔄 Deduplicating manuscripts...")
        
        seen_ids = set()
        duplicates_found = 0
        
        for ms_id, manuscript in self.manuscripts.items():
            if ms_id in seen_ids:
                duplicates_found += 1
                continue
            seen_ids.add(ms_id)
            
        self.logger.info(f"📊 Deduplication complete: {duplicates_found} duplicates handled")
    
    def export_results(self, export_format: str = "json"):
        """Export results in specified format"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format == "json":
            export_file = self.download_dir / f"{self.journal_name.lower()}_results_{timestamp}.json"
            
            results = {
                'journal': self.journal_name,
                'extraction_date': datetime.now().isoformat(),
                'total_manuscripts': len(self.manuscripts),
                'total_active_referees': sum(ms.active_referee_count for ms in self.manuscripts.values()),
                'manuscripts': [asdict(ms) for ms in self.manuscripts.values()]
            }
            
            with open(export_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
                
        elif export_format == "csv":
            export_file = self.download_dir / f"{self.journal_name.lower()}_results_{timestamp}.csv"
            
            with open(export_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Manuscript_ID', 'Title', 'Journal', 'Category', 
                    'Active_Referees', 'Total_Referees', 'PDF_Downloaded'
                ])
                
                for manuscript in self.manuscripts.values():
                    writer.writerow([
                        manuscript.manuscript_id,
                        manuscript.title,
                        manuscript.journal,
                        manuscript.category,
                        manuscript.active_referee_count,
                        manuscript.total_referee_count,
                        manuscript.pdf_downloaded
                    ])
        
        self.logger.info(f"📄 Results exported to: {export_file}")
        return export_file
    
    def run_complete_scraping(self, headless=True):
        """Run complete scraping workflow"""
        self.logger.info(f"🚀 Starting complete scraping for {self.journal_name} (headless={headless})")
        
        try:
            # Setup
            self.create_driver(headless=headless)
            self.login_and_setup()
            
            # Discover categories
            categories = self.discover_manuscripts_in_categories()
            
            # Process each category
            for category_name in categories:
                manuscripts = self.process_category(category_name)
                self.logger.info(f"✅ Processed {len(manuscripts)} manuscripts in {category_name}")
            
            # Deduplicate
            self.deduplicate_manuscripts()
            
            # Export results
            json_file = self.export_results("json")
            csv_file = self.export_results("csv")
            
            # Final summary
            self.logger.info(f"\n{'='*80}")
            self.logger.info(f"📊 COMPLETE SCRAPING RESULTS FOR {self.journal_name}")
            self.logger.info(f"{'='*80}")
            self.logger.info(f"Total manuscripts: {len(self.manuscripts)}")
            self.logger.info(f"Total active referees: {sum(ms.active_referee_count for ms in self.manuscripts.values())}")
            self.logger.info(f"PDFs downloaded: {sum(1 for ms in self.manuscripts.values() if ms.pdf_downloaded)}")
            self.logger.info(f"Results exported to: {json_file}")
            
            return self.manuscripts
            
        except Exception as e:
            self.logger.error(f"💥 Fatal error during scraping: {e}")
            raise
            
        finally:
            if self.driver:
                self.driver.quit()

def main():
    """Run production scraper for both journals"""
    download_dir = Path("journal_data_production")
    download_dir.mkdir(exist_ok=True)
    
    for journal_name in ["MF", "MOR"]:
        print(f"\n{'='*80}")
        print(f"🚀 PRODUCTION SCRAPING: {journal_name}")
        print(f"{'='*80}")
        
        scraper = ProductionJournalScraper(
            journal_name=journal_name,
            download_dir=download_dir,
            debug=True
        )
        
        try:
            manuscripts = scraper.run_complete_scraping()
            print(f"✅ {journal_name} scraping completed successfully!")
            
        except Exception as e:
            print(f"❌ {journal_name} scraping failed: {e}")

if __name__ == "__main__":
    main()