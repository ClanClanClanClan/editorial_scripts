"""
PDF handling utilities for the Editorial Assistant system.

This module provides functionality for downloading, validating,
and managing PDF files.
"""

import logging
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import hashlib
import requests
from urllib.parse import urlparse, unquote

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .exceptions import PDFDownloadError


class PDFHandler:
    """Handles PDF download and management operations."""
    
    def __init__(self, base_dir: Path):
        """
        Initialize PDF handler.
        
        Args:
            base_dir: Base directory for storing PDFs
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger("editorial_assistant.pdf_handler")
        
        # PDF validation settings
        self.min_pdf_size = 1024  # 1KB minimum
        self.pdf_header = b'%PDF'
        
    def download_pdf_from_url(self, url: str, filename: str, 
                              cookies: Optional[Dict[str, str]] = None) -> Optional[Path]:
        """
        Download PDF from direct URL.
        
        Args:
            url: PDF URL
            filename: Target filename
            cookies: Optional cookies for authentication
            
        Returns:
            Path to downloaded file if successful
        """
        output_path = self.base_dir / filename
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, cookies=cookies, 
                                    stream=True, timeout=30)
            response.raise_for_status()
            
            # Download with progress
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Validate PDF
            if self.validate_pdf(output_path):
                self.logger.info(f"Downloaded PDF: {output_path} ({output_path.stat().st_size} bytes)")
                return output_path
            else:
                output_path.unlink()
                raise PDFDownloadError(f"Invalid PDF downloaded from {url}")
                
        except Exception as e:
            self.logger.error(f"Failed to download PDF from {url}: {e}")
            if output_path.exists():
                output_path.unlink()
            return None
    
    def download_pdf_from_browser(self, driver: WebDriver, target_dir: Path, 
                                  expected_filename: Optional[str] = None,
                                  timeout: int = 30) -> Optional[Path]:
        """
        Handle PDF download triggered in browser.
        
        Args:
            driver: WebDriver instance
            target_dir: Directory where browser downloads files
            expected_filename: Expected filename pattern
            timeout: Maximum wait time
            
        Returns:
            Path to downloaded file if successful
        """
        # Get initial file list
        initial_files = set(target_dir.glob("*.pdf"))
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check for new PDF files
            current_files = set(target_dir.glob("*.pdf"))
            new_files = current_files - initial_files
            
            if new_files:
                # Get the newest file
                new_file = max(new_files, key=lambda p: p.stat().st_mtime)
                
                # Wait for download to complete
                if self._wait_for_download_complete(new_file):
                    # Validate and move to proper location
                    if self.validate_pdf(new_file):
                        if expected_filename:
                            final_path = self.base_dir / expected_filename
                            shutil.move(str(new_file), str(final_path))
                            self.logger.info(f"Moved PDF to: {final_path}")
                            return final_path
                        else:
                            final_path = self.base_dir / new_file.name
                            shutil.move(str(new_file), str(final_path))
                            return final_path
            
            # Check for .crdownload files (Chrome downloading)
            downloading = list(target_dir.glob("*.crdownload"))
            if downloading:
                self.logger.debug(f"Download in progress: {[f.name for f in downloading]}")
            
            time.sleep(1)
        
        self.logger.warning(f"PDF download timeout after {timeout} seconds")
        return None
    
    def extract_pdf_from_page(self, driver: WebDriver, manuscript_id: str) -> Optional[Path]:
        """
        Extract PDF from current page (ScholarOne style).
        
        Args:
            driver: WebDriver instance
            manuscript_id: Manuscript ID for naming
            
        Returns:
            Path to downloaded PDF if successful
        """
        current_url = driver.current_url
        
        # Check if we're already on a PDF page
        if self._is_pdf_url(current_url):
            return self._download_pdf_from_current_page(driver, f"{manuscript_id}_manuscript.pdf")
        
        # Try to find PDF link/button
        pdf_selectors = [
            "a[href*='.pdf']",
            "a[href*='DOWNLOAD=TRUE']",
            "button:contains('Download PDF')",
            "a:contains('PDF')",
            "a[title*='PDF']",
            "[class*='pdf-link']",
            "[class*='download-pdf']"
        ]
        
        for selector in pdf_selectors:
            try:
                pdf_element = driver.find_element(By.CSS_SELECTOR, selector)
                if pdf_element:
                    # Get the href if it's a link
                    href = pdf_element.get_attribute('href')
                    if href and self._is_pdf_url(href):
                        # Direct download
                        cookies = self._get_browser_cookies(driver)
                        return self.download_pdf_from_url(href, f"{manuscript_id}_manuscript.pdf", cookies)
                    else:
                        # Click to trigger download
                        pdf_element.click()
                        time.sleep(2)
                        
                        # Check if we navigated to PDF
                        if self._is_pdf_url(driver.current_url):
                            return self._download_pdf_from_current_page(driver, f"{manuscript_id}_manuscript.pdf")
                        
                        # Otherwise check downloads folder
                        return self.download_pdf_from_browser(
                            driver, 
                            Path(driver.capabilities.get('chrome', {}).get('userDataDir', '.')) / 'Downloads',
                            f"{manuscript_id}_manuscript.pdf"
                        )
            except Exception as e:
                self.logger.debug(f"PDF selector {selector} failed: {e}")
                continue
        
        self.logger.warning(f"No PDF found on page for {manuscript_id}")
        return None
    
    def validate_pdf(self, file_path: Path) -> bool:
        """
        Validate that a file is a valid PDF.
        
        Args:
            file_path: Path to file to validate
            
        Returns:
            True if valid PDF
        """
        if not file_path.exists():
            return False
        
        # Check file size
        if file_path.stat().st_size < self.min_pdf_size:
            self.logger.warning(f"PDF too small: {file_path} ({file_path.stat().st_size} bytes)")
            return False
        
        # Check PDF header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(4)
                if header != self.pdf_header:
                    self.logger.warning(f"Invalid PDF header in {file_path}: {header}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"Error validating PDF {file_path}: {e}")
            return False
    
    def organize_pdfs(self, journal_code: str, date_str: str) -> None:
        """
        Organize PDFs into proper directory structure.
        
        Args:
            journal_code: Journal code
            date_str: Date string for organization
        """
        target_dir = self.base_dir / journal_code.lower() / date_str
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Move all PDFs to organized structure
        for pdf in self.base_dir.glob("*.pdf"):
            target = target_dir / pdf.name
            shutil.move(str(pdf), str(target))
            self.logger.info(f"Organized PDF: {pdf.name} -> {target}")
    
    def get_pdf_metadata(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract metadata from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dictionary of metadata
        """
        metadata = {
            'filename': file_path.name,
            'size': file_path.stat().st_size,
            'size_mb': round(file_path.stat().st_size / (1024 * 1024), 2),
            'modified': file_path.stat().st_mtime,
            'hash': self._calculate_hash(file_path)
        }
        
        # Could add PyPDF2 metadata extraction here if needed
        
        return metadata
    
    def _is_pdf_url(self, url: str) -> bool:
        """Check if URL points to a PDF."""
        return bool(url and ('.pdf' in url.lower() or 'DOWNLOAD=TRUE' in url))
    
    def _download_pdf_from_current_page(self, driver: WebDriver, filename: str) -> Optional[Path]:
        """Download PDF when browser is on PDF page."""
        current_url = driver.current_url
        
        # Get cookies for authenticated download
        cookies = self._get_browser_cookies(driver)
        
        # Download using requests
        return self.download_pdf_from_url(current_url, filename, cookies)
    
    def _get_browser_cookies(self, driver: WebDriver) -> Dict[str, str]:
        """Get cookies from browser for authenticated downloads."""
        cookies = {}
        for cookie in driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        return cookies
    
    def _wait_for_download_complete(self, file_path: Path, check_interval: float = 0.5) -> bool:
        """Wait for a file download to complete."""
        if not file_path.exists():
            return False
        
        # Wait for file size to stabilize
        prev_size = -1
        stable_count = 0
        
        while stable_count < 3:  # File size stable for 3 checks
            try:
                current_size = file_path.stat().st_size
                
                if current_size == prev_size:
                    stable_count += 1
                else:
                    stable_count = 0
                    prev_size = current_size
                
                time.sleep(check_interval)
                
            except FileNotFoundError:
                return False
        
        return True
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def cleanup_incomplete_downloads(self) -> None:
        """Clean up incomplete download files."""
        patterns = ["*.crdownload", "*.tmp", "*.part"]
        
        for pattern in patterns:
            for file in self.base_dir.glob(pattern):
                try:
                    file.unlink()
                    self.logger.info(f"Cleaned up incomplete download: {file}")
                except Exception as e:
                    self.logger.error(f"Failed to clean up {file}: {e}")