#!/usr/bin/env python3
"""
Enhanced Base Journal Class with All Production Features
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging
from pathlib import Path
import hashlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from core.email_utils import get_gmail_service
from core.credential_manager import get_credential_manager


class EnhancedBaseJournal(ABC):
    """Enhanced base class with all production features for journal extractors"""
    
    def __init__(self, config: dict):
        """Initialize with configuration"""
        self.config = config
        self.journal_name = config['journal_name']
        self.journal_code = config.get('journal_code', self.journal_name)
        
        # Setup services first
        self.logger = self.setup_logger()
        
        # State management
        self.state_dir = Path('state')
        self.state_dir.mkdir(exist_ok=True)
        self.state_file = self.state_dir / f"{self.journal_code}_state.json"
        self.previous_state = self.load_state()
        
        # Change tracking
        self.changes = {
            'new_manuscripts': [],
            'status_changes': [],
            'new_reports': [],
            'new_referees': [],
            'overdue_reviews': [],
            'approaching_deadlines': []
        }
        self.gmail_service = None
        self.driver = None
        self.wait = None
        
        # Output directory
        self.output_dir = Path(f'./extractions/{self.journal_code}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Credential management
        self.cred_manager = get_credential_manager()
    
    def setup_logger(self) -> logging.Logger:
        """Setup journal-specific logger"""
        logger = logging.getLogger(f'editorial.{self.journal_code}')
        logger.setLevel(logging.INFO)
        
        # File handler
        log_file = Path('logs') / f'{self.journal_code}.log'
        log_file.parent.mkdir(exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def setup_driver(self, headless: bool = True):
        """Setup Selenium WebDriver with stealth options"""
        chrome_options = Options()
        
        # Stealth settings
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        if headless:
            chrome_options.add_argument('--headless=new')
        
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        chrome_options.add_argument('--max_old_space_size=4096')
        chrome_options.add_argument('--memory-pressure-off')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Download settings
        prefs = {
            "download.default_directory": str(self.output_dir / 'downloads'),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)
        
        # Enable downloads in headless mode
        self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
            "behavior": "allow",
            "downloadPath": str(self.output_dir / 'downloads')
        })
        
        self.logger.info(f"WebDriver initialized for {self.journal_name}")
    
    def setup_gmail_service(self):
        """Setup Gmail service for email verification"""
        try:
            self.gmail_service = get_gmail_service()
            self.logger.info("Gmail service initialized")
        except Exception as e:
            self.logger.warning(f"Gmail service not available: {e}")
            self.gmail_service = None
    
    def load_state(self) -> dict:
        """Load previous extraction state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                    self.logger.info(f"Loaded previous state from {self.state_file}")
                    return state
            except Exception as e:
                self.logger.error(f"Error loading state: {e}")
        return {'manuscripts': {}, 'extraction_time': None}
    
    def save_state(self, current_state: dict):
        """Save current extraction state"""
        try:
            current_state['extraction_time'] = datetime.now().isoformat()
            with open(self.state_file, 'w') as f:
                json.dump(current_state, f, indent=2)
            self.logger.info(f"Saved state to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")
    
    def generate_manuscript_hash(self, manuscript: dict) -> str:
        """Generate hash for manuscript to detect changes"""
        # Create a stable hash from key manuscript properties
        hash_data = {
            'id': manuscript.get('id'),
            'referees': [
                {
                    'name': r['name'],
                    'status': r['status'],
                    'email': r.get('email')
                }
                for r in manuscript.get('referees', [])
            ]
        }
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def detect_changes(self, current_manuscripts: List[dict]) -> dict:
        """Detect changes since last extraction"""
        self.logger.info("Detecting changes since last extraction")
        
        # Convert to dict for easier comparison
        current_dict = {ms['id']: ms for ms in current_manuscripts}
        previous_dict = self.previous_state.get('manuscripts', {})
        
        # New manuscripts
        new_ids = set(current_dict.keys()) - set(previous_dict.keys())
        for ms_id in new_ids:
            self.changes['new_manuscripts'].append({
                'id': ms_id,
                'title': current_dict[ms_id].get('title'),
                'submitted': current_dict[ms_id].get('submitted')
            })
            self.logger.info(f"New manuscript: {ms_id}")
        
        # Check existing manuscripts
        for ms_id in set(current_dict.keys()) & set(previous_dict.keys()):
            self._detect_manuscript_changes(
                previous_dict[ms_id],
                current_dict[ms_id]
            )
        
        # Check for overdue reviews
        self._check_overdue_reviews(current_manuscripts)
        
        # Check approaching deadlines
        self._check_approaching_deadlines(current_manuscripts)
        
        return self.changes
    
    def _detect_manuscript_changes(self, prev_ms: dict, curr_ms: dict):
        """Detect changes within a manuscript"""
        ms_id = curr_ms['id']
        
        # Compare referee lists
        prev_refs = {r['name']: r for r in prev_ms.get('referees', [])}
        curr_refs = {r['name']: r for r in curr_ms.get('referees', [])}
        
        # New referees
        for name in set(curr_refs.keys()) - set(prev_refs.keys()):
            self.changes['new_referees'].append({
                'manuscript_id': ms_id,
                'manuscript_title': curr_ms.get('title'),
                'referee_name': name,
                'referee_email': curr_refs[name].get('email'),
                'status': curr_refs[name].get('status')
            })
            self.logger.info(f"New referee for {ms_id}: {name}")
        
        # Status changes
        for name in set(curr_refs.keys()) & set(prev_refs.keys()):
            prev_status = prev_refs[name].get('status', 'Unknown')
            curr_status = curr_refs[name].get('status', 'Unknown')
            
            if prev_status != curr_status:
                self.changes['status_changes'].append({
                    'manuscript_id': ms_id,
                    'manuscript_title': curr_ms.get('title'),
                    'referee_name': name,
                    'referee_email': curr_refs[name].get('email'),
                    'old_status': prev_status,
                    'new_status': curr_status,
                    'change_detected': datetime.now().isoformat()
                })
                self.logger.info(f"Status change for {ms_id}/{name}: {prev_status} → {curr_status}")
                
                # Check if report was submitted
                if curr_status in ['Report Submitted', 'Accepted'] and prev_status != curr_status:
                    if curr_refs[name].get('report_available'):
                        self.changes['new_reports'].append({
                            'manuscript_id': ms_id,
                            'manuscript_title': curr_ms.get('title'),
                            'referee_name': name,
                            'referee_email': curr_refs[name].get('email'),
                            'submission_detected': datetime.now().isoformat()
                        })
                        self.logger.info(f"New report available for {ms_id} from {name}")
    
    def _check_overdue_reviews(self, manuscripts: List[dict]):
        """Check for overdue reviews"""
        today = datetime.now().date()
        
        for ms in manuscripts:
            for ref in ms.get('referees', []):
                if ref.get('status') == 'Accepted' and ref.get('due_date'):
                    try:
                        due_date = datetime.strptime(ref['due_date'], '%Y-%m-%d').date()
                        if due_date < today:
                            days_overdue = (today - due_date).days
                            self.changes['overdue_reviews'].append({
                                'manuscript_id': ms['id'],
                                'manuscript_title': ms.get('title'),
                                'referee_name': ref['name'],
                                'referee_email': ref.get('email'),
                                'due_date': ref['due_date'],
                                'days_overdue': days_overdue
                            })
                            self.logger.warning(f"Overdue review: {ms['id']}/{ref['name']} - {days_overdue} days")
                    except:
                        pass
    
    def _check_approaching_deadlines(self, manuscripts: List[dict]):
        """Check for approaching deadlines (within 7 days)"""
        today = datetime.now().date()
        warning_days = 7
        
        for ms in manuscripts:
            for ref in ms.get('referees', []):
                if ref.get('status') == 'Accepted' and ref.get('due_date'):
                    try:
                        due_date = datetime.strptime(ref['due_date'], '%Y-%m-%d').date()
                        days_until_due = (due_date - today).days
                        
                        if 0 < days_until_due <= warning_days:
                            self.changes['approaching_deadlines'].append({
                                'manuscript_id': ms['id'],
                                'manuscript_title': ms.get('title'),
                                'referee_name': ref['name'],
                                'referee_email': ref.get('email'),
                                'due_date': ref['due_date'],
                                'days_remaining': days_until_due
                            })
                            self.logger.info(f"Approaching deadline: {ms['id']}/{ref['name']} - {days_until_due} days")
                    except:
                        pass
    
    def verify_referee_with_email(self, referee: dict, manuscript: dict) -> dict:
        """Verify referee information with Gmail API"""
        if not self.gmail_service:
            return referee
        
        # Search for manuscript-specific emails
        search_results = self.search_referee_emails(
            referee_name=referee['name'],
            referee_email=referee.get('email'),
            manuscript_id=manuscript['id'],
            submission_date=manuscript.get('submitted'),
            title=manuscript.get('title')
        )
        
        if search_results['found']:
            referee['email_verification'] = {
                'verified': True,
                'emails_found': search_results['email_count'],
                'invitation_date': search_results.get('invitation_date'),
                'last_verified': datetime.now().isoformat()
            }
            
            self.logger.info(
                f"Email verification for {referee['name']}: "
                f"{search_results['email_count']} emails found"
            )
        
        return referee
    
    def search_referee_emails(self, referee_name: str, referee_email: str, 
                             manuscript_id: str, submission_date: str, 
                             title: str) -> dict:
        """Search for referee emails - to be implemented by subclasses"""
        # This will use the perfected email search logic
        return {'found': False, 'emails': [], 'email_count': 0}
    
    def generate_digest_data(self) -> dict:
        """Generate data for digest email"""
        return {
            'journal': self.journal_name,
            'extraction_time': datetime.now().isoformat(),
            'changes': self.changes,
            'summary': {
                'new_manuscripts': len(self.changes['new_manuscripts']),
                'status_changes': len(self.changes['status_changes']),
                'new_reports': len(self.changes['new_reports']),
                'new_referees': len(self.changes['new_referees']),
                'overdue_reviews': len(self.changes['overdue_reviews']),
                'approaching_deadlines': len(self.changes['approaching_deadlines'])
            }
        }
    
    def format_state(self, manuscripts: List[dict]) -> dict:
        """Format manuscripts for state storage"""
        state = {
            'manuscripts': {},
            'extraction_time': datetime.now().isoformat()
        }
        
        for ms in manuscripts:
            state['manuscripts'][ms['id']] = {
                'id': ms['id'],
                'title': ms.get('title'),
                'submitted': ms.get('submitted'),
                'hash': self.generate_manuscript_hash(ms),
                'referees': ms.get('referees', [])
            }
        
        return state
    
    def save_results(self, manuscripts: List[dict], changes: dict):
        """Save extraction results"""
        # Save full results
        results_file = self.output_dir / 'extraction_results.json'
        with open(results_file, 'w') as f:
            json.dump({
                'journal': self.journal_name,
                'extraction_time': datetime.now().isoformat(),
                'manuscripts': manuscripts,
                'changes': changes
            }, f, indent=2)
        
        # Save changes separately
        if any(changes.values()):
            changes_file = self.output_dir / 'changes_detected.json'
            with open(changes_file, 'w') as f:
                json.dump(changes, f, indent=2)
        
        self.logger.info(f"Results saved to {self.output_dir}")
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Journal-specific authentication"""
        pass
    
    @abstractmethod
    def extract_manuscripts(self) -> List[dict]:
        """Extract manuscript data - to be implemented by each journal"""
        pass
    
    def run_extraction(self) -> dict:
        """Main extraction workflow with all features"""
        try:
            self.logger.info(f"Starting {self.journal_name} extraction")
            start_time = datetime.now()
            
            # Setup services
            self.setup_driver()
            self.setup_gmail_service()
            
            # Authenticate
            if not self.authenticate():
                raise Exception("Authentication failed")
            
            # Extract manuscripts
            manuscripts = self.extract_manuscripts()
            self.logger.info(f"Extracted {len(manuscripts)} manuscripts")
            
            # Verify with email
            if self.gmail_service:
                for ms in manuscripts:
                    for ref in ms.get('referees', []):
                        self.verify_referee_with_email(ref, ms)
            
            # Detect changes
            current_state = self.format_state(manuscripts)
            self.detect_changes(manuscripts)
            
            # Save results
            self.save_results(manuscripts, self.changes)
            
            # Save state for next run
            self.save_state(current_state)
            
            # Generate digest data
            digest_data = self.generate_digest_data()
            
            # Log summary
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                f"Completed {self.journal_name} extraction in {duration:.1f}s - "
                f"{len(manuscripts)} manuscripts, "
                f"{sum(len(m.get('referees', [])) for m in manuscripts)} referees"
            )
            
            return digest_data
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}", exc_info=True)
            raise
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("WebDriver closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        if self.driver:
            self.driver.quit()