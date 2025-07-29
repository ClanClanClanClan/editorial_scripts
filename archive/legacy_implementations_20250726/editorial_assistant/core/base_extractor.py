"""
Base extractor class for all journal extractors.

This module provides the abstract base class that all journal-specific
extractors must inherit from, ensuring a consistent interface.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import json

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from .data_models import (
    Journal, Manuscript, Referee, ExtractionResult,
    ManuscriptStatus, RefereeStatus
)
from .exceptions import (
    ExtractionError, LoginError, NavigationError, 
    CheckpointError
)
from .browser_manager import BrowserManager
from .pdf_handler import PDFHandler


class BaseExtractor(ABC):
    """Abstract base class for journal extractors."""
    
    def __init__(self, journal: Journal, headless: bool = True, 
                 checkpoint_dir: Optional[Path] = None):
        """
        Initialize the extractor.
        
        Args:
            journal: Journal configuration
            headless: Run browser in headless mode
            checkpoint_dir: Directory for saving checkpoints
        """
        self.journal = journal
        self.headless = headless
        self.logger = self._setup_logger()
        
        # Setup directories
        self.base_dir = Path(f"data/exports/{journal.code.lower()}")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.checkpoint_dir = checkpoint_dir or Path(f"data/checkpoints/{journal.code.lower()}")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.browser_manager = BrowserManager(headless=headless)
        self.pdf_handler = PDFHandler(base_dir=self.base_dir / "pdfs")
        
        # State management
        self.driver: Optional[WebDriver] = None
        self.current_state: Dict[str, Any] = {}
        self.manuscripts: List[Manuscript] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for this extractor."""
        logger = logging.getLogger(f"editorial_assistant.{self.journal.code}")
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = Path(f"logs/extraction/{self.journal.code.lower()}.log")
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def extract(self) -> ExtractionResult:
        """
        Main extraction method.
        
        Returns:
            ExtractionResult containing all extracted data
        """
        start_time = datetime.now()
        
        try:
            self.logger.info(f"Starting extraction for {self.journal.name}")
            
            # Load checkpoint if exists
            self._load_checkpoint()
            
            # Initialize browser
            self.driver = self.browser_manager.create_driver()
            
            # Perform extraction steps
            self._login()
            self._navigate_to_manuscripts()
            manuscripts = self._extract_manuscripts()
            
            # Process each manuscript
            for manuscript in manuscripts:
                if self._should_skip_manuscript(manuscript):
                    continue
                    
                try:
                    self._process_manuscript(manuscript)
                    self.manuscripts.append(manuscript)
                    self._save_checkpoint()
                except Exception as e:
                    self.logger.error(f"Error processing {manuscript.manuscript_id}: {e}")
                    self.errors.append(f"Failed to process {manuscript.manuscript_id}: {str(e)}")
            
            # Create result
            duration = (datetime.now() - start_time).total_seconds()
            result = ExtractionResult(
                journal=self.journal,
                manuscripts=self.manuscripts,
                duration_seconds=duration,
                errors=self.errors,
                warnings=self.warnings,
                stats=self._generate_stats()
            )
            
            # Save results
            self._save_results(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Extraction failed: {e}", exc_info=True)
            raise ExtractionError(f"Extraction failed for {self.journal.code}: {str(e)}")
        finally:
            if self.driver:
                self.browser_manager.quit_driver(self.driver)
    
    @abstractmethod
    def _login(self) -> None:
        """
        Login to the journal submission system.
        
        Raises:
            LoginError: If login fails
        """
        pass
    
    @abstractmethod
    def _navigate_to_manuscripts(self) -> None:
        """
        Navigate to the manuscripts list page.
        
        Raises:
            NavigationError: If navigation fails
        """
        pass
    
    @abstractmethod
    def _extract_manuscripts(self) -> List[Manuscript]:
        """
        Extract list of manuscripts from the current page.
        
        Returns:
            List of Manuscript objects with basic information
        """
        pass
    
    @abstractmethod
    def _process_manuscript(self, manuscript: Manuscript) -> None:
        """
        Process a single manuscript to extract detailed information.
        
        Args:
            manuscript: Manuscript object to populate with details
        """
        pass
    
    def _should_skip_manuscript(self, manuscript: Manuscript) -> bool:
        """
        Check if manuscript should be skipped based on checkpoint.
        
        Args:
            manuscript: Manuscript to check
            
        Returns:
            True if manuscript should be skipped
        """
        processed = self.current_state.get('processed_manuscripts', [])
        return manuscript.manuscript_id in processed
    
    def _save_checkpoint(self) -> None:
        """Save current extraction state."""
        checkpoint = {
            'journal': self.journal.code,
            'timestamp': datetime.now().isoformat(),
            'processed_manuscripts': [m.manuscript_id for m in self.manuscripts],
            'errors': self.errors,
            'warnings': self.warnings,
            'state': self.current_state
        }
        
        checkpoint_file = self.checkpoint_dir / f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)
            self.logger.info(f"Checkpoint saved to {checkpoint_file}")
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            raise CheckpointError(f"Failed to save checkpoint: {str(e)}")
    
    def _load_checkpoint(self) -> None:
        """Load most recent checkpoint if exists."""
        checkpoints = list(self.checkpoint_dir.glob("checkpoint_*.json"))
        
        if not checkpoints:
            self.logger.info("No checkpoint found, starting fresh")
            return
            
        # Get most recent checkpoint
        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
        
        try:
            with open(latest, 'r') as f:
                checkpoint = json.load(f)
            
            self.current_state = checkpoint.get('state', {})
            self.logger.info(f"Loaded checkpoint from {latest}")
            self.logger.info(f"Previously processed: {checkpoint.get('processed_manuscripts', [])}")
            
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            raise CheckpointError(f"Failed to load checkpoint: {str(e)}")
    
    def _save_results(self, result: ExtractionResult) -> None:
        """Save extraction results to file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save JSON results
        json_file = self.base_dir / f"results_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(result.dict(), f, indent=2, default=str)
        
        self.logger.info(f"Results saved to {json_file}")
    
    def _generate_stats(self) -> Dict[str, Any]:
        """Generate extraction statistics."""
        return {
            'total_manuscripts': len(self.manuscripts),
            'total_referees': sum(len(m.referees) for m in self.manuscripts),
            'total_pdfs': sum(1 for m in self.manuscripts if m.pdf_path),
            'referee_status_breakdown': self._get_referee_status_breakdown(),
            'manuscript_status_breakdown': self._get_manuscript_status_breakdown(),
        }
    
    def _get_referee_status_breakdown(self) -> Dict[str, int]:
        """Get breakdown of referee statuses."""
        breakdown = {}
        for manuscript in self.manuscripts:
            for referee in manuscript.referees:
                status = referee.status.value if isinstance(referee.status, RefereeStatus) else str(referee.status)
                breakdown[status] = breakdown.get(status, 0) + 1
        return breakdown
    
    def _get_manuscript_status_breakdown(self) -> Dict[str, int]:
        """Get breakdown of manuscript statuses."""
        breakdown = {}
        for manuscript in self.manuscripts:
            status = manuscript.status.value if isinstance(manuscript.status, ManuscriptStatus) else str(manuscript.status)
            breakdown[status] = breakdown.get(status, 0) + 1
        return breakdown
    
    def wait_and_click(self, selector: str, by: By = By.CSS_SELECTOR, 
                       timeout: int = 10) -> bool:
        """
        Wait for element and click it.
        
        Args:
            selector: Element selector
            by: Selector type
            timeout: Maximum wait time
            
        Returns:
            True if successful, False otherwise
        """
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            element.click()
            return True
        except TimeoutException:
            self.logger.warning(f"Element not found or clickable: {selector}")
            return False
        except Exception as e:
            self.logger.error(f"Error clicking element {selector}: {e}")
            return False
    
    def safe_find_element(self, selector: str, by: By = By.CSS_SELECTOR) -> Optional[Any]:
        """
        Safely find an element without raising exceptions.
        
        Args:
            selector: Element selector
            by: Selector type
            
        Returns:
            Element if found, None otherwise
        """
        try:
            return self.driver.find_element(by, selector)
        except:
            return None