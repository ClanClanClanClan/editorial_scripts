"""
Enhanced Cover Letter Downloader
================================

Handles various popup scenarios to properly download cover letters as PDF/DOCX files.
"""

import time
import logging
from pathlib import Path
from typing import Optional, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class EnhancedCoverLetterDownloader:
    """Enhanced downloader that handles MF cover letter popup complexities."""
    
    def __init__(self, driver, download_dir: str = "downloads/cover_letters"):
        self.driver = driver
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def download_cover_letter(self, cover_link, manuscript_id: str) -> Optional[str]:
        """
        Download cover letter with enhanced popup handling.
        
        Returns path to downloaded file or None if failed.
        """
        original_window = self.driver.current_window_handle
        
        try:
            # Click the cover letter link
            logger.info(f"Clicking cover letter link for {manuscript_id}")
            self.driver.execute_script("arguments[0].scrollIntoView(true);", cover_link)
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", cover_link)
            
            # Wait for popup
            time.sleep(3)
            
            # Switch to popup window
            all_windows = self.driver.window_handles
            popup_window = None
            
            for window in all_windows:
                if window != original_window:
                    self.driver.switch_to.window(window)
                    popup_window = window
                    logger.info(f"Switched to popup window: {self.driver.title}")
                    break
                    
            if not popup_window:
                logger.warning("No popup window found")
                return None
                
            # Try multiple strategies to download
            file_path = None
            
            # Strategy 1: Look for download button/link to click
            file_path = self._try_download_button_click(manuscript_id)
            
            # Strategy 2: Check for embedded viewer with download
            if not file_path:
                file_path = self._try_embedded_viewer_download(manuscript_id)
                
            # Strategy 3: Look for file in iframe
            if not file_path:
                file_path = self._try_iframe_download(manuscript_id)
                
            # Strategy 4: Direct file link
            if not file_path:
                file_path = self._try_direct_file_link(manuscript_id)
                
            # Strategy 5: Text extraction as last resort
            if not file_path:
                logger.info("All download strategies failed, extracting text")
                file_path = self._extract_text_content(manuscript_id)
                
            return file_path
            
        except Exception as e:
            logger.error(f"Error downloading cover letter: {e}")
            return None
            
        finally:
            # Always return to original window
            try:
                if popup_window:
                    self.driver.close()
                self.driver.switch_to.window(original_window)
            except:
                pass
    
    def _try_download_button_click(self, manuscript_id: str) -> Optional[str]:
        """Try clicking download buttons/links in the popup."""
        logger.info("Strategy 1: Looking for download buttons")
        
        # Various selectors for download elements
        download_selectors = [
            # Common download button patterns
            "//button[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]",
            "//a[contains(translate(text(), 'DOWNLOAD', 'download'), 'download')]",
            "//input[@type='button' and contains(translate(@value, 'DOWNLOAD', 'download'), 'download')]",
            
            # View/Open patterns that might trigger download
            "//input[@type='button' and contains(@value, 'View Cover Letter')]",
            "//a[contains(text(), 'View Cover Letter')]",
            "//button[contains(text(), 'View Cover Letter')]",
            
            # File type specific
            "//a[contains(@href, '.pdf') or contains(@href, '.docx') or contains(@href, '.doc')]",
            "//a[contains(text(), '.pdf') or contains(text(), '.docx') or contains(text(), '.doc')]",
            
            # Icon-based download buttons
            "//a[contains(@class, 'download')]//parent::*",
            "//button[contains(@class, 'download')]",
            "//i[contains(@class, 'download')]//parent::button",
            
            # Platform specific patterns
            "//a[contains(@onclick, 'download')]",
            "//a[contains(@href, 'GetFile')]",
            "//a[contains(@href, 'DownloadFile')]",
            "//a[contains(@href, 'ViewFile')]",
        ]
        
        for selector in download_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                
                for elem in elements:
                    if not elem.is_displayed():
                        continue
                        
                    # Monitor downloads folder before clicking
                    files_before = set(self.download_dir.glob("*"))
                    
                    # Try clicking the element
                    try:
                        elem.click()
                    except:
                        # Try JavaScript click if regular click fails
                        self.driver.execute_script("arguments[0].click();", elem)
                    
                    # Wait for download
                    time.sleep(5)
                    
                    # Check for new files
                    files_after = set(self.download_dir.glob("*"))
                    new_files = files_after - files_before
                    
                    if new_files:
                        # Found a new download
                        downloaded_file = list(new_files)[0]
                        
                        # Rename to standard format
                        if downloaded_file.suffix.lower() in ['.pdf', '.docx', '.doc']:
                            new_path = self.download_dir / f"{manuscript_id}_cover_letter{downloaded_file.suffix}"
                            downloaded_file.rename(new_path)
                            logger.info(f"Downloaded cover letter: {new_path}")
                            return str(new_path)
                            
            except Exception as e:
                logger.debug(f"Selector failed: {selector} - {e}")
                continue
                
        return None
    
    def _try_embedded_viewer_download(self, manuscript_id: str) -> Optional[str]:
        """Try to download from embedded document viewers."""
        logger.info("Strategy 2: Checking for embedded viewer")
        
        # Check for PDF viewer
        try:
            # Look for PDF embed/object elements
            pdf_elements = self.driver.find_elements(By.TAG_NAME, "embed") + \
                          self.driver.find_elements(By.TAG_NAME, "object")
            
            for elem in pdf_elements:
                src = elem.get_attribute("src") or elem.get_attribute("data")
                if src and ('.pdf' in src.lower() or 'application/pdf' in elem.get_attribute("type", "")):
                    # Found embedded PDF
                    return self._download_from_url(src, manuscript_id, ".pdf")
                    
        except Exception as e:
            logger.debug(f"Embedded viewer check failed: {e}")
            
        return None
    
    def _try_iframe_download(self, manuscript_id: str) -> Optional[str]:
        """Try to find downloads within iframes."""
        logger.info("Strategy 3: Checking iframes")
        
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            
            for i, iframe in enumerate(iframes):
                try:
                    # Switch to iframe
                    self.driver.switch_to.frame(iframe)
                    
                    # Check if it's a document viewer
                    current_url = self.driver.current_url
                    if any(ext in current_url.lower() for ext in ['.pdf', '.docx', '.doc']):
                        # Direct document URL in iframe
                        self.driver.switch_to.default_content()
                        return self._download_from_url(current_url, manuscript_id)
                    
                    # Look for download buttons within iframe
                    download_btns = self.driver.find_elements(By.XPATH, 
                        "//button[contains(text(), 'Download')] | //a[contains(text(), 'Download')]")
                    
                    if download_btns:
                        # Try clicking first visible button
                        for btn in download_btns:
                            if btn.is_displayed():
                                btn.click()
                                time.sleep(5)
                                # Check for downloads...
                                
                    # Return to main content
                    self.driver.switch_to.default_content()
                    
                except Exception as e:
                    logger.debug(f"iframe {i} processing failed: {e}")
                    self.driver.switch_to.default_content()
                    
        except Exception as e:
            logger.debug(f"iframe strategy failed: {e}")
            
        return None
    
    def _try_direct_file_link(self, manuscript_id: str) -> Optional[str]:
        """Try to find direct file links."""
        logger.info("Strategy 4: Looking for direct file links")
        
        try:
            # Get all links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            
            for link in links:
                href = link.get_attribute("href")
                if not href:
                    continue
                    
                # Check if it's a document link
                if any(ext in href.lower() for ext in ['.pdf', '.docx', '.doc']):
                    # Try to download
                    return self._download_from_url(href, manuscript_id)
                    
        except Exception as e:
            logger.debug(f"Direct link search failed: {e}")
            
        return None
    
    def _download_from_url(self, url: str, manuscript_id: str, force_extension: str = None) -> Optional[str]:
        """Download file from URL using requests."""
        try:
            import requests
            
            # Get cookies from Selenium
            cookies = {c['name']: c['value'] for c in self.driver.get_cookies()}
            
            # Download file
            response = requests.get(url, cookies=cookies, stream=True, timeout=30)
            
            if response.status_code == 200:
                # Determine file extension
                content_type = response.headers.get('content-type', '').lower()
                
                if force_extension:
                    ext = force_extension
                elif 'pdf' in content_type or url.lower().endswith('.pdf'):
                    ext = '.pdf'
                elif 'wordprocessingml' in content_type or url.lower().endswith('.docx'):
                    ext = '.docx'
                elif 'msword' in content_type or url.lower().endswith('.doc'):
                    ext = '.doc'
                else:
                    # Check content
                    content_start = response.content[:4]
                    if content_start.startswith(b'%PDF'):
                        ext = '.pdf'
                    elif content_start == b'PK\x03\x04':  # ZIP format (DOCX)
                        ext = '.docx'
                    else:
                        ext = '.pdf'  # Default
                
                # Save file
                file_path = self.download_dir / f"{manuscript_id}_cover_letter{ext}"
                
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            
                logger.info(f"Downloaded file from URL: {file_path}")
                return str(file_path)
                
        except Exception as e:
            logger.error(f"URL download failed: {e}")
            
        return None
    
    def _extract_text_content(self, manuscript_id: str) -> Optional[str]:
        """Extract text content as last resort."""
        logger.info("Extracting text content from popup")
        
        try:
            # Try various selectors for text content
            text_selectors = [
                "//textarea[@name='cover_letter']",
                "//div[@class='cover_letter']",
                "//div[contains(@class, 'letter-content')]",
                "//div[contains(@class, 'document-content')]",
                "//pre",
                "//div[contains(@class, 'content')]",
                "//div[@id='content']",
                "//body"
            ]
            
            cover_text = ""
            
            for selector in text_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > 100:  # Minimum length check
                            cover_text = text
                            break
                    if cover_text:
                        break
                except:
                    continue
                    
            if cover_text:
                # Save as text file
                file_path = self.download_dir / f"{manuscript_id}_cover_letter.txt"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(cover_text)
                    
                logger.info(f"Extracted text content: {file_path}")
                return str(file_path)
                
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            
        return None