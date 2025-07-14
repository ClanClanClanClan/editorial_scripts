#!/usr/bin/env python3
"""
Universal paper download utility for all journals.
This module provides functionality to download papers and referee reports
from various journal platforms for AI analysis.
"""

import os
import logging
import time
import requests
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from urllib.parse import urljoin, urlparse
import hashlib
import mimetypes

logger = logging.getLogger(__name__)

class PaperDownloader:
    """Universal paper downloader for all journal platforms"""
    
    def __init__(self, base_dir: str = "downloads"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        # Create subdirectories for different content types
        self.papers_dir = self.base_dir / "papers"
        self.reports_dir = self.base_dir / "reports"
        self.papers_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def _safe_filename(self, filename: str) -> str:
        """Create a safe filename for the filesystem"""
        # Replace problematic characters
        safe_chars = "-_.() abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        safe_filename = ''.join(c if c in safe_chars else '_' for c in filename)
        
        # Limit length
        if len(safe_filename) > 200:
            safe_filename = safe_filename[:200]
        
        return safe_filename
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Get SHA-256 hash of a file"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _download_file(self, url: str, save_path: Path, driver: webdriver.Chrome = None) -> bool:
        """Download a file from URL"""
        try:
            if driver:
                # Use driver's session cookies
                cookies = driver.get_cookies()
                for cookie in cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
            
            response = self.session.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check if it's actually a PDF or document
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and 'document' not in content_type and 'application' not in content_type:
                logger.warning(f"Unexpected content type: {content_type} for URL: {url}")
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            logger.info(f"Downloaded: {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            return False
    
    def download_paper(self, manuscript_id: str, title: str, url: str, journal: str, 
                      driver: webdriver.Chrome = None) -> Optional[Path]:
        """Download a paper from a manuscript URL"""
        try:
            # Create safe filename
            safe_title = self._safe_filename(title)
            filename = f"{journal}_{manuscript_id}_{safe_title}.pdf"
            save_path = self.papers_dir / filename
            
            # Skip if already downloaded
            if save_path.exists():
                logger.info(f"Paper already downloaded: {save_path}")
                return save_path
            
            # Try to download
            if self._download_file(url, save_path, driver):
                return save_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error downloading paper {manuscript_id}: {e}")
            return None
    
    def download_referee_report(self, manuscript_id: str, referee_name: str, url: str, 
                               journal: str, driver: webdriver.Chrome = None) -> Optional[Path]:
        """Download a referee report"""
        try:
            # Create safe filename
            safe_referee = self._safe_filename(referee_name)
            filename = f"{journal}_{manuscript_id}_{safe_referee}_report.pdf"
            save_path = self.reports_dir / filename
            
            # Skip if already downloaded
            if save_path.exists():
                logger.info(f"Report already downloaded: {save_path}")
                return save_path
            
            # Try to download
            if self._download_file(url, save_path, driver):
                return save_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error downloading report for {manuscript_id}: {e}")
            return None
    
    def find_paper_links(self, driver: webdriver.Chrome, journal: str) -> List[Dict]:
        """Find downloadable paper links on the current page"""
        paper_links = []
        
        try:
            # Common selectors for paper download links
            paper_selectors = [
                "a[href*='pdf']",
                "a[href*='PDF']",
                "a[href*='download']",
                "a[href*='manuscript']",
                "a[href*='paper']",
                "a[href*='article']",
                "a[contains(text(), 'PDF')]",
                "a[contains(text(), 'Download')]",
                "a[contains(text(), 'View Paper')]",
                "a[contains(text(), 'Manuscript')]",
                "button[onclick*='pdf']",
                "button[onclick*='download']"
            ]
            
            for selector in paper_selectors:
                try:
                    links = driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            onclick = link.get_attribute('onclick')
                            text = link.text.strip()
                            
                            if href and any(ext in href.lower() for ext in ['.pdf', 'pdf', 'download']):
                                paper_links.append({
                                    'url': href,
                                    'text': text,
                                    'type': 'href'
                                })
                            elif onclick and 'pdf' in onclick.lower():
                                paper_links.append({
                                    'url': onclick,
                                    'text': text,
                                    'type': 'onclick'
                                })
                        except:
                            continue
                except:
                    continue
            
            logger.info(f"Found {len(paper_links)} potential paper download links")
            return paper_links
            
        except Exception as e:
            logger.error(f"Error finding paper links: {e}")
            return []
    
    def find_report_links(self, driver: webdriver.Chrome, journal: str) -> List[Dict]:
        """Find downloadable referee report links on the current page"""
        report_links = []
        
        try:
            # Common selectors for report download links
            report_selectors = [
                "a[href*='report']",
                "a[href*='review']",
                "a[href*='referee']",
                "a[href*='reviewer']",
                "a[contains(text(), 'Report')]",
                "a[contains(text(), 'Review')]",
                "a[contains(text(), 'Referee')]",
                "a[contains(text(), 'Reviewer')]",
                "button[onclick*='report']",
                "button[onclick*='review']"
            ]
            
            for selector in report_selectors:
                try:
                    links = driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            onclick = link.get_attribute('onclick')
                            text = link.text.strip()
                            
                            if href and any(keyword in href.lower() for keyword in ['report', 'review', 'referee']):
                                report_links.append({
                                    'url': href,
                                    'text': text,
                                    'type': 'href'
                                })
                            elif onclick and any(keyword in onclick.lower() for keyword in ['report', 'review']):
                                report_links.append({
                                    'url': onclick,
                                    'text': text,
                                    'type': 'onclick'
                                })
                        except:
                            continue
                except:
                    continue
            
            logger.info(f"Found {len(report_links)} potential report download links")
            return report_links
            
        except Exception as e:
            logger.error(f"Error finding report links: {e}")
            return []
    
    def download_from_manuscript_page(self, driver: webdriver.Chrome, manuscript_id: str, 
                                    title: str, journal: str) -> Dict:
        """Download paper and reports from a manuscript page"""
        downloads = {
            'paper': None,
            'reports': []
        }
        
        try:
            # Find and download paper
            paper_links = self.find_paper_links(driver, journal)
            for link in paper_links:
                if link['type'] == 'href':
                    paper_path = self.download_paper(manuscript_id, title, link['url'], journal, driver)
                    if paper_path:
                        downloads['paper'] = str(paper_path)
                        break
            
            # Find and download reports
            report_links = self.find_report_links(driver, journal)
            for link in report_links:
                if link['type'] == 'href':
                    report_path = self.download_referee_report(
                        manuscript_id, link['text'], link['url'], journal, driver
                    )
                    if report_path:
                        downloads['reports'].append(str(report_path))
            
            return downloads
            
        except Exception as e:
            logger.error(f"Error downloading from manuscript page {manuscript_id}: {e}")
            return downloads
    
    def get_download_stats(self) -> Dict:
        """Get statistics about downloaded files"""
        stats = {
            'papers': len(list(self.papers_dir.glob('*.pdf'))),
            'reports': len(list(self.reports_dir.glob('*.pdf'))),
            'total_size': 0
        }
        
        for file_path in self.papers_dir.glob('*'):
            if file_path.is_file():
                stats['total_size'] += file_path.stat().st_size
        
        for file_path in self.reports_dir.glob('*'):
            if file_path.is_file():
                stats['total_size'] += file_path.stat().st_size
        
        # Convert bytes to MB
        stats['total_size_mb'] = stats['total_size'] / (1024 * 1024)
        
        return stats
    
    def cleanup_old_downloads(self, days_old: int = 30):
        """Clean up downloads older than specified days"""
        import time
        
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        removed_count = 0
        
        for directory in [self.papers_dir, self.reports_dir]:
            for file_path in directory.glob('*'):
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        removed_count += 1
                    except Exception as e:
                        logger.error(f"Error removing {file_path}: {e}")
        
        logger.info(f"Cleaned up {removed_count} old download files")
        return removed_count

# Global instance
paper_downloader = PaperDownloader()

def get_paper_downloader() -> PaperDownloader:
    """Get the global paper downloader instance"""
    return paper_downloader