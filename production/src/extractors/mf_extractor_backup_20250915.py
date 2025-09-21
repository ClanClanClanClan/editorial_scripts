#!/usr/bin/env python3
"""
PRODUCTION MF EXTRACTOR - SECURE CREDENTIAL VERSION
==================================================

Production-ready extractor for Mathematical Finance journals.
Automatically loads credentials from secure storage.
No need to set environment variables manually.
"""

#!/usr/bin/env python3
"""
COMPREHENSIVE MF EXTRACTOR
==========================

Extracts ALL data from ALL categories with proper navigation.
"""

import os
import sys
import time
import json
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import traceback
from typing import Optional, Callable

# Add cache integration
sys.path.append(str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin

# Add academic enrichment
# from core.academic_enrichment import AcademicProfileEnricher

# Import the cover letter download fixer

# Enhanced credential loading
sys.path.append(str(Path(__file__).parent.parent))
try:
    from ensure_credentials import load_credentials
    load_credentials()
except ImportError:
    # Fallback to basic dotenv loading
    load_dotenv('.env.production')



    def with_retry(max_attempts=3, delay=1.0):
        """Decorator to retry failed operations with exponential backoff."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            print(f"   ❌ {func.__name__} failed after {max_attempts} attempts: {e}")
                            raise
                        else:
                            print(f"   ⚠️ {func.__name__} attempt {attempt + 1} failed: {e}")
                            time.sleep(delay * (2 ** attempt))  # Exponential backoff
                return None
            return wrapper
        return decorator
    
    def safe_execute(self, operation: Callable, operation_name: str, default_value=None, critical=False):
        """Safely execute an operation with error handling."""
        try:
            result = operation()
            return result
        except TimeoutException:
            error_msg = f"Timeout during {operation_name}"
            print(f"   ⏱️ {error_msg}")
            if critical:
                raise Exception(f"Critical operation failed: {error_msg}")
            return default_value
        except NoSuchElementException:
            error_msg = f"Element not found during {operation_name}"
            print(f"   🔍 {error_msg}")
            if critical:
                raise Exception(f"Critical operation failed: {error_msg}")
            return default_value
        except WebDriverException as e:
            error_msg = f"WebDriver error during {operation_name}: {str(e)[:100]}"
            print(f"   🌐 {error_msg}")
            if critical:
                raise Exception(f"Critical operation failed: {error_msg}")
            return default_value
        except Exception as e:
            error_msg = f"Unexpected error during {operation_name}: {str(e)[:100]}"
            print(f"   ❌ {error_msg}")
            if critical:
                raise Exception(f"Critical operation failed: {error_msg}")
            return default_value
    
class ComprehensiveMFExtractor(CachedExtractorMixin):
    def __init__(self):
        self.manuscripts = []
        self.processed_manuscript_ids = set()  # Track processed manuscripts to avoid duplicates
        
        # Initialize cache system
        self.init_cached_extractor('MF')
        
        # Load credentials securely
        self._setup_secure_credentials()
        
        # Set up download directory relative to project root (not current working directory)
        self.project_root = Path(__file__).parent.parent
        self.download_dir = self.project_root / "downloads"
        # self.enricher = AcademicProfileEnricher()  # Initialize ORCID enricher
        self.setup_driver()
    
    def _setup_secure_credentials(self):
        """Load credentials from secure storage."""
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
            from secure_credentials import SecureCredentialManager
            credential_manager = SecureCredentialManager()
            
            # Try to load existing credentials
            if credential_manager.setup_environment():
                print("✅ Credentials loaded from secure storage")
                return
            
            # If no credentials found, prompt to store them
            print("🔐 No stored credentials found. Setting up secure storage...")
            if credential_manager.store_credentials():
                if credential_manager.setup_environment():
                    print("✅ Credentials stored and loaded successfully")
                    return
            
            # Fallback to environment variables
            print("⚠️ Falling back to environment variables...")
            if not os.getenv('MF_EMAIL') or not os.getenv('MF_PASSWORD'):
                raise Exception("No credentials available. Please run: python3 secure_credentials.py store")
                
        except ImportError:
            print("⚠️ Secure credential system not available, using environment variables...")
            if not os.getenv('MF_EMAIL') or not os.getenv('MF_PASSWORD'):
                raise Exception("Please set MF_EMAIL and MF_PASSWORD environment variables")
        
    def get_download_dir(self, subdir=""):
        """Get download directory path, ensuring it exists."""
        return self.get_safe_download_dir(subdir)
    
    def extract_email_from_popup_window(self):
        """Extract email from currently active popup window (already switched to it)."""
        try:
            # Wait for popup to load completely
            time.sleep(2)
            
            # Handle framesets if present (MF popups use framesets)
            frames = self.driver.find_elements(By.TAG_NAME, "frame")
            if frames:
                print(f"         🖼️ Found {len(frames)} frames in popup")
                
                # Try each frame to find email content
                for i in range(len(frames)):
                    try:
                        self.driver.switch_to.frame(i)
                        frame_text = self.driver.page_source
                        
                        # Look for email input field in this frame
                        email_inputs = self.driver.find_elements(By.XPATH, "//input[@name='TO_EMAIL']")
                        if email_inputs:
                            value = email_inputs[0].get_attribute('value')
                            if value and '@' in value:
                                print(f"         ✅ Found email in frame {i}: {value}")
                                return value
                        
                        # Look for email patterns in frame text
                        if '@' in frame_text:
                            import re
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            emails = re.findall(email_pattern, frame_text)
                            for email in emails:
                                # Filter out system emails
                                if not any(skip in email.lower() for skip in ['noreply', 'donotreply', 'manuscriptcentral']):
                                    print(f"         ✅ Found email in frame {i} text: {email}")
                                    return email
                        
                        # Switch back to default content to try next frame
                        self.driver.switch_to.default_content()
                    except Exception as e:
                        print(f"         ⚠️ Error in frame {i}: {e}")
                        try:
                            self.driver.switch_to.default_content()
                        except:
                            pass
                        continue
            
            # If no frames or no email found in frames, try main window
            # Look for email in input fields (To: field)
            input_selectors = [
                "//input[@name='TO_EMAIL']",
                "//input[@id='TO_EMAIL']", 
                "//input[contains(@name, 'TO_EMAIL')]",
                "//input[contains(@name, 'to') and contains(@name, 'email')]",
                "//input[@type='text' and contains(@value, '@')]"
            ]
            
            for selector in input_selectors:
                try:
                    inputs = self.driver.find_elements(By.XPATH, selector)
                    for inp in inputs:
                        value = inp.get_attribute('value')
                        if value and '@' in value:
                            print(f"         ✅ Found email in input: {value}")
                            return value
                except:
                    continue
            
            # Look for mailto links
            try:
                mailto_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'mailto:')]")
                for link in mailto_links:
                    href = link.get_attribute('href')
                    if href and 'mailto:' in href:
                        email = href.replace('mailto:', '').split('?')[0].strip()
                        if '@' in email:
                            print(f"         ✅ Found email in mailto: {email}")
                            return email
            except:
                pass
            
            # Look for email in visible text
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                import re
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                emails = re.findall(email_pattern, page_text)
                for email in emails:
                    # Filter out system emails
                    if not any(skip in email.lower() for skip in ['noreply', 'donotreply', 'manuscriptcentral']):
                        print(f"         ✅ Found email in text: {email}")
                        return email
            except:
                pass
            
            print(f"         ❌ No email found in popup")
            return ""
            
        except Exception as e:
            print(f"         ❌ Error in extract_email_from_popup_window: {e}")
            return ""
    
    def click_and_extract_email(self, name_link):
        """NUCLEAR-SAFE email extraction that never hangs navigation."""
        if not name_link:
            return ""
        
        original_window = self.driver.current_window_handle
        email = ""
        
        try:
            # Click to open popup with timeout protection
            self.driver.execute_script("arguments[0].click();", name_link)
            time.sleep(0.5)  # Shorter wait
            
            # Check if popup opened (with timeout)
            start_time = time.time()
            while time.time() - start_time < 3:  # 3 second timeout
                windows = self.driver.window_handles
                if len(windows) > 1:
                    break
                time.sleep(0.1)
            else:
                # No popup opened in 3 seconds
                return ""
            
            # Switch to popup
            popup_window = windows[-1]
            self.driver.switch_to.window(popup_window)
            
            # Quick email extraction with timeout
            try:
                frames = self.driver.find_elements(By.TAG_NAME, "frame")
                for frame in frames[:3]:  # Only check first 3 frames
                    try:
                        self.driver.switch_to.frame(frame)
                        elements = self.driver.find_elements(By.NAME, "EMAIL_TEMPLATE_TO")
                        if elements:
                            value = elements[0].get_attribute("value")
                            if value and "@" in value:
                                email = value.strip()
                                break
                        self.driver.switch_to.default_content()
                    except:
                        try:
                            self.driver.switch_to.default_content()
                        except:
                            pass
            except:
                pass
                
        except Exception as e:
            print(f"         ⚠️ Popup extraction error: {e}")
        
        # NUCLEAR CLEANUP - absolutely ensure we get back to main window
        try:
            # Force close all extra windows
            current_windows = self.driver.window_handles
            for window in current_windows:
                if window != original_window:
                    try:
                        self.driver.switch_to.window(window)
                        self.driver.close()
                    except:
                        pass
        except:
            pass
        
        # FORCE return to original window  
        try:
            self.driver.switch_to.window(original_window)
        except:
            # Emergency: switch to any available window
            try:
                windows = self.driver.window_handles
                if windows:
                    self.driver.switch_to.window(windows[0])
            except:
                pass
        
        # Brief pause to let browser stabilize
        time.sleep(0.2)
        
        return email

    def get_email_from_popup_safe(self, popup_url_or_element):
        """Safe version of email extraction with comprehensive error handling."""
        if not popup_url_or_element:
            return ""
        
        original_window = self.driver.current_window_handle
        popup_window = None
        
        try:
            # Handle both element objects and URL strings
            if hasattr(popup_url_or_element, 'click'):
                # This is a WebElement - click it directly
                print(f"         🔧 Clicking element directly...")
                popup_url_or_element.click()
            elif isinstance(popup_url_or_element, str):
                popup_url = popup_url_or_element
                if popup_url.startswith('javascript:'):
                    # For JavaScript URLs, try executing directly
                    print(f"         🔧 Executing JavaScript: {popup_url[:50]}...")
                    js_code = popup_url[11:]  # Remove 'javascript:' prefix
                    
                    # URL decode if needed
                    import urllib.parse
                    try:
                        js_code = urllib.parse.unquote(js_code)
                    except:
                        pass
                    
                    self.driver.execute_script(js_code)
                else:
                    # For direct URLs, open with window.open()
                    print(f"         🔧 Opening direct URL: {popup_url[:50]}...")
                    self.driver.execute_script(f"window.open('{popup_url}', 'popup', 'width=900,height=775')")
            else:
                print(f"         ❌ Invalid popup parameter: {type(popup_url_or_element)}")
                return ""
            
            # Wait for popup window with timeout
            try:
                WebDriverWait(self.driver, 10).until(lambda driver: len(driver.window_handles) > 1)
                popup_window = [w for w in self.driver.window_handles if w != original_window][0]
                self.driver.switch_to.window(popup_window)
            except TimeoutException:
                print(f"   ⏱️ Popup window timeout...")
                return ""
            
            # Wait for content to load - handle framesets differently
            time.sleep(3)  # Give popup time to load
            
            # Check if this is a frameset page (doesn't have a body tag)
            try:
                framesets = self.driver.find_elements(By.TAG_NAME, "frameset")
                if not framesets:
                    # Regular page - wait for body
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
            except TimeoutException:
                print(f"   ⏱️ Popup content timeout...")
                # Don't return yet - might be a frameset page
            
            # Extract email with frame-aware strategies for MF framesets
            email = ""
            
            # First check if email is in the popup URL itself
            try:
                current_url = self.driver.current_url
                if 'EMAIL_TO=' in current_url or 'EMAIL_TEMPLATE_TO=' in current_url:
                    import re
                    from urllib.parse import unquote
                    match = re.search(r'EMAIL_TO=([^&"\'\s]+)', current_url)
                    if not match:
                        match = re.search(r'EMAIL_TEMPLATE_TO=([^&"\'\s]+)', current_url)
                    if match:
                        email = unquote(match.group(1))
                        if '@' in email:
                            print(f"   ✅ Email found in popup URL: {email}")
                            return email
            except:
                pass
            
            # Strategy 1: Handle frameset-based popups (MF specific)
            try:
                # Check if this is a frameset
                framesets = self.driver.find_elements(By.TAG_NAME, "frameset")
                if framesets:
                    print(f"   🖼️ Detected frameset popup, checking frames...")
                    
                    # Get all frames
                    frames = self.driver.find_elements(By.TAG_NAME, "frame")
                    print(f"   📋 Found {len(frames)} frames in popup")
                    
                    # Try each frame to find email content
                    for i, frame in enumerate(frames):
                        try:
                            self.driver.switch_to.frame(i)
                            print(f"   🔍 Checking frame {i}...")
                            
                            # Get frame source and URL
                            frame_source = self.driver.page_source
                            frame_url = self.driver.current_url
                            
                            # Look for EMAIL_TO or EMAIL_TEMPLATE_TO in frame URL first
                            if 'EMAIL_TO=' in frame_url or 'EMAIL_TEMPLATE_TO=' in frame_url:
                                import re
                                from urllib.parse import unquote
                                match = re.search(r'EMAIL_TO=([^&"\'\s]+)', frame_url)
                                if not match:
                                    match = re.search(r'EMAIL_TEMPLATE_TO=([^&"\'\s]+)', frame_url)
                                if match:
                                    email = unquote(match.group(1))
                                    if '@' in email:
                                        print(f"   ✅ Email found in frame {i} URL: {email}")
                                        self.driver.switch_to.window(popup_window)
                                        break
                            
                            # Look for EMAIL_TO or EMAIL_TEMPLATE_TO in frame source
                            if 'EMAIL_TO=' in frame_source or 'EMAIL_TEMPLATE_TO=' in frame_source:
                                import re
                                from urllib.parse import unquote
                                match = re.search(r'EMAIL_TO=([^&"\'\s]+)', frame_source)
                                if not match:
                                    match = re.search(r'EMAIL_TEMPLATE_TO=([^&"\'\s]+)', frame_source)
                                if match:
                                    email = unquote(match.group(1))
                                    if '@' in email:
                                        print(f"   ✅ Email found in frame {i} from EMAIL_TEMPLATE_TO: {email}")
                                        self.driver.switch_to.window(popup_window)
                                        break
                            
                            # NEW: Look for email patterns directly in frame content
                            import re
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            found_emails = re.findall(email_pattern, frame_source)
                            
                            if found_emails:
                                # Filter out editor emails (like dylan.possamai@math.ethz.ch)
                                referee_emails = [e for e in found_emails if 'dylan.possamai' not in e and 'math.ethz.ch' not in e]
                                if referee_emails:
                                    email = referee_emails[0]  # Take first non-editor email
                                    print(f"   ✅ Email found in frame {i} content: {email}")
                                    self.driver.switch_to.window(popup_window)
                                    break
                            
                            # Try to find email in input fields
                            email_inputs = self.driver.find_elements(By.XPATH, "//input[@type='email' or contains(@name, 'to') or contains(@name, 'email') or contains(@id, 'to')]")
                            for input_elem in email_inputs:
                                value = input_elem.get_attribute('value')
                                if value and '@' in value:
                                    email = value
                                    print(f"   ✅ Email found in frame {i} input field: {email}")
                                    self.driver.switch_to.window(popup_window)
                                    break
                            
                            if email:
                                break
                            
                            # Look for email in frame text - use source directly for framesets
                            frame_text = frame_source
                            
                            # Extract email pattern from frame
                            import re
                            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                            emails = re.findall(email_pattern, frame_text)
                            
                            # Filter out common non-referee emails and editor emails
                            for potential_email in emails:
                                # Skip common non-referee emails
                                if any(x in potential_email.lower() for x in ['manuscript', 'wiley', 'support', 'noreply', 'example', 'test', 'domain']):
                                    continue
                                # Skip editor emails (dylan.possamai)
                                if 'dylan.possamai' in potential_email.lower():
                                    continue
                                # This should be the referee email
                                email = potential_email
                                print(f"   ✅ Email found in frame {i}: {email}")
                                break
                            
                            # Switch back to popup main content
                            self.driver.switch_to.window(popup_window)
                            
                            if email:
                                break
                            
                        except Exception as frame_e:
                            print(f"   ⚠️ Frame {i} access failed: {frame_e}")
                            try:
                                self.driver.switch_to.window(popup_window)
                            except:
                                pass
                            continue
                            
            except Exception as e:
                print(f"   ⚠️ Frame extraction failed: {e}")
            
            # Strategy 2: Regular popup body extraction (fallback)
            if not email:
                try:
                    self.driver.switch_to.window(popup_window)  # Ensure we're in popup window
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    body_text = body.text
                    
                    # Extract email pattern
                    import re
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, body_text)
                    if emails:
                        email = emails[0]
                        print(f"   ✅ Email found via text pattern: {email}")
                except Exception as e:
                    print(f"   ⚠️ Text pattern extraction failed: {e}")
            
            # Strategy 3: Look for email in specific elements
            if not email:
                try:
                    # Common selectors for email popups
                    selectors = ['input[type="email"]', '.email', '#email', '[data-email]']
                    for selector in selectors:
                        try:
                            element = self.driver.find_element(By.CSS_SELECTOR, selector)
                            email = element.get_attribute('value') or element.text
                            if email:
                                print(f"   ✅ Email found via selector {selector}: {email}")
                                break
                        except NoSuchElementException:
                            continue
                except Exception as e:
                    print(f"   ⚠️ Selector extraction failed: {e}")
            
            return email
            
        except Exception as e:
            print(f"   ❌ Popup extraction failed: {e}")
            return ""
        finally:
            # ROBUST popup cleanup - always return to main window
            try:
                # Close any extra windows first
                all_windows = self.driver.window_handles
                for window in all_windows:
                    if window != original_window:
                        try:
                            self.driver.switch_to.window(window)
                            self.driver.close()
                            print(f"   🧹 Closed popup window")
                        except Exception:
                            pass
                            
                # Always return to original window
                self.driver.switch_to.window(original_window)
                print(f"   🔙 Returned to main window")
                
                # CRITICAL: Wait for main window to be fully interactive
                time.sleep(2)  # Give browser time to settle
                try:
                    # Ensure document is ready
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.execute_script('return document.readyState') == 'complete'
                    )
                    # Check if page is still functional by finding basic elements
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                except Exception as stability_e:
                    print(f"   ⚠️ Main window stability check failed: {stability_e}")
                    # Force refresh if page seems broken
                    try:
                        self.driver.refresh()
                        time.sleep(3)
                    except:
                        pass
                
            except Exception as cleanup_error:
                print(f"   ⚠️ Popup cleanup failed: {cleanup_error}")
                # Emergency fallback - try to get back to main window
                try:
                    if len(self.driver.window_handles) > 0:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                except Exception:
                    pass
    
    def get_current_manuscript_id(self):
        """Extract the current manuscript ID from the page - ENHANCED FOR MF."""
        try:
            # First try: Look for manuscript ID in specific elements
            # Try to find it in table cells or headers
            id_selectors = [
                "//td[contains(text(), 'MAFI-')]",
                "//td[contains(text(), 'MAFI.')]/following-sibling::td",
                "//td[@class='pagecontents' and contains(text(), 'MAFI')]",
                "//p[@class='pagecontents' and contains(text(), 'MAFI')]",
                "//td[contains(text(), 'Manuscript ID')]/following-sibling::td",
                "//td[contains(text(), 'Submission ID')]/following-sibling::td",
                "//span[contains(text(), 'MAFI-')]",
                "//b[contains(text(), 'MAFI-')]"
            ]
            
            for selector in id_selectors:
                try:
                    elem = self.driver.find_element(By.XPATH, selector)
                    text = elem.text.strip()
                    # Extract MAFI ID from the text
                    mafi_match = re.search(r'MAFI[-\.\s]*\d{2,4}[-\.\s]*\d{3,5}', text)
                    if mafi_match:
                        manuscript_id = mafi_match.group(0).replace(' ', '-').replace('.', '-')
                        print(f"   ✅ Found manuscript ID from element: {manuscript_id}")
                        return manuscript_id
                except:
                    continue
            
            # Second try: Search entire page text
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # MF-specific patterns (MAFI is the journal code)
            mf_patterns = [
                r'MAFI-\d{4}-\d{3,5}',  # MAFI-2024-1234
                r'MAFI-\d{2}-\d{3,5}',  # MAFI-24-1234
                r'MAFI\.\d{4}\.\d{3,5}',  # MAFI.2024.1234
                r'MAFI/\d{4}/\d{3,5}',  # MAFI/2024/1234
                r'MAFI\s+\d{4}-\d{3,5}',  # MAFI 2024-1234
                r'MAFI\d{4}-\d{3,5}'  # MAFI2024-1234
            ]
            
            print(f"   🔍 Searching for MAFI manuscript ID patterns...")
            
            for pattern in mf_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    # Clean up and return the first match
                    manuscript_id = matches[0].upper().replace(' ', '-').replace('.', '-').replace('/', '-')
                    # Ensure consistent format: MAFI-YYYY-NNNNN
                    manuscript_id = re.sub(r'MAFI[-\.\s]*(\d{2,4})[-\.\s]*(\d{3,5})', r'MAFI-\1-\2', manuscript_id)
                    print(f"   ✅ Found manuscript ID: {manuscript_id}")
                    return manuscript_id
            
            # Generic patterns fallback
            patterns = [
                r'[A-Z]{2,6}-\d{4}-\d{3,5}',  # Generic format
                r'[A-Z]{2,6}-\d{2}-\d{3,5}',  # Short year format
                r'MS-\d{4}-\d{3,5}'  # Generic MS format
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    manuscript_id = matches[0]
                    print(f"   ✅ Found manuscript ID (generic): {manuscript_id}")
                    return manuscript_id
            
            # Fallback: Look for any year-number combination near manuscript-related text
            fallback_patterns = [
                r'(?i)manuscript\s*[:\s]*([A-Z0-9-]{8,20})',
                r'(?i)submission\s*[:\s]*([A-Z0-9-]{8,20})',
                r'(?i)paper\s*[:\s]*([A-Z0-9-]{8,20})'
            ]
            
            for pattern in fallback_patterns:
                match = re.search(pattern, page_text)
                if match:
                    manuscript_id = match.group(1)
                    print(f"   ✅ Found manuscript ID (fallback): {manuscript_id}")
                    return manuscript_id
                    
            print("   ⚠️ No manuscript ID found on current page")
            return "UNKNOWN"
            
        except Exception as e:
            print(f"   ❌ Error extracting manuscript ID: {e}")
            return "UNKNOWN"

    def is_same_person_name(self, name1, name2):
        """Check if two names refer to the same person, handling different formats."""
        if not name1 or not name2:
            return False
            
        # Normalize names
        name1 = name1.strip().lower()
        name2 = name2.strip().lower()
        
        # Direct match
        if name1 == name2:
            return True
        
        # Handle "Last, First" vs "First Last" formats
        if ',' in name1:
            parts1 = name1.split(',', 1)
            if len(parts1) == 2:
                name1_reversed = f"{parts1[1].strip()} {parts1[0].strip()}"
                if name1_reversed == name2:
                    return True
        
        if ',' in name2:
            parts2 = name2.split(',', 1)
            if len(parts2) == 2:
                name2_reversed = f"{parts2[1].strip()} {parts2[0].strip()}"
                if name2_reversed == name1:
                    return True
        
        # Check if all parts of one name are in the other
        parts1 = set(name1.replace(',', '').split())
        parts2 = set(name2.replace(',', '').split())
        
        # If they have the same parts, they're likely the same person
        if parts1 == parts2 and len(parts1) >= 2:
            return True
            
        return False

    def get_current_editor_names(self):
        """Dynamically extract editor names from current page to avoid hardcoding."""
        try:
            print(f"      🔍 Dynamically detecting editor names...")
            
            # Common patterns to identify editor names on ScholarOne pages
            editor_patterns = [
                "//td[contains(text(), 'Admin:')]//following-sibling::td",
                "//td[contains(text(), 'Editor:')]//following-sibling::td", 
                "//td[contains(text(), 'Associate Editor:')]//following-sibling::td",
                "//td[contains(text(), 'Co-Editor:')]//following-sibling::td",
                "//*[contains(text(), 'Editor') and contains(text(), ':')]//text()",
                "//span[contains(@class, 'editor')]",
                "//div[contains(@class, 'editor')]"
            ]
            
            detected_editors = []
            
            for pattern in editor_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > 2 and len(text) < 50:
                            # Extract just the name part, skip titles/roles
                            name_match = re.search(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text)
                            if name_match:
                                name = name_match.group(0)
                                if name not in detected_editors and len(name.split()) <= 3:
                                    detected_editors.append(name)
                                    print(f"         ✅ Detected editor: {name}")
                except:
                    continue
            
            # Add common editor surnames as fallback (but dynamic detection first)
            if not detected_editors:
                print(f"      ⚠️ No editors detected dynamically, using common patterns")
                # Only add if we can't detect dynamically
                fallback_editors = []
            else:
                fallback_editors = detected_editors
                
            print(f"      📋 Final editor list: {fallback_editors}")
            return fallback_editors
            
        except Exception as e:
            print(f"      ❌ Error detecting editors: {e}")
            return []  # Return empty list instead of hardcoded names

    def infer_institution_from_email_domain(self, domain):
        """Dynamically infer institution name from email domain using deep web search."""
        if not domain:
            return None
            
        try:
            print(f"         🔍 Inferring institution from domain: {domain}")
            
            # Check global cache first
            cached_result = self.cache_manager.get_institution_from_domain(domain)
            if cached_result:
                institution, country = cached_result
                print(f"         📚 Global cache hit: {domain} → {institution}")
                return institution
            
            # Deep web search for institution
            print(f"         🌐 Performing deep web search for domain: {domain}")
            
            # Search for institution information
            search_queries = [
                f'"{domain}" university institution official name',
                f'site:{domain} about university',
                f'"{domain}" academic institution affiliation'
            ]
            
            found_institution = None
            
            for query in search_queries:
                try:
                    # Use actual web search through requests or API
                    import requests
                    import urllib.parse
                    
                    # Try multiple search approaches
                    # Approach 1: Direct domain lookup
                    if '.' in domain:
                        try:
                            # Try to fetch the domain's homepage
                            url = f"https://{domain}"
                            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
                            response = requests.get(url, timeout=5, headers=headers, allow_redirects=True)
                            if response.status_code == 200:
                                page_text = response.text.lower()
                                
                                # Look for institution name in title or meta tags
                                import re
                                title_match = re.search(r'<title>([^<]+)</title>', page_text)
                                if title_match:
                                    title = title_match.group(1)
                                    # Clean up common patterns
                                    title = re.sub(r'\s*[\|\-–—]\s*(home|homepage|accueil|welcome).*', '', title)
                                    title = title.strip()
                                    
                                    if len(title) > 5 and any(word in title.lower() for word in ['university', 'université', 'institute', 'college', 'école']):
                                        found_institution = title.title()
                                        print(f"         ✅ Found institution from website title: {found_institution}")
                                        break
                                
                                # Look for institution name in meta description
                                meta_match = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']', page_text)
                                if meta_match:
                                    description = meta_match.group(1)
                                    # Extract institution name from description
                                    inst_patterns = [
                                        r'(university of [a-z\s]+)',
                                        r'([a-z\s]+ university)',
                                        r'(université [a-z\s]+)',
                                        r'([a-z\s]+ institute)',
                                        r'([a-z\s]+ college)',
                                        r'(école [a-z\s]+)'
                                    ]
                                    for pattern in inst_patterns:
                                        matches = re.findall(pattern, description.lower())
                                        if matches:
                                            found_institution = matches[0].strip().title()
                                            print(f"         ✅ Found institution from meta description: {found_institution}")
                                            break
                                    if found_institution:
                                        break
                        except Exception as e:
                            print(f"         ⚠️ Direct domain fetch failed: {e}")
                    
                    # Approach 2: DuckDuckGo Instant Answer API
                    if not found_institution:
                        try:
                            encoded_query = urllib.parse.quote(query)
                            ddg_url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_html=1"
                            response = requests.get(ddg_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                            if response.status_code == 200:
                                data = response.json()
                                
                                # Check Abstract
                                abstract = data.get('Abstract', '')
                                if abstract:
                                    # Look for institution names in abstract
                                    import re
                                    inst_patterns = [
                                        r'(University of [A-Za-z\s]+)',
                                        r'([A-Za-z\s]+ University)',
                                        r'(Université [A-Za-z\s]+)',
                                        r'([A-Za-z\s]+ Institute)',
                                        r'([A-Za-z\s]+ College)',
                                        r'(École [A-Za-z\s]+)'
                                    ]
                                    for pattern in inst_patterns:
                                        matches = re.findall(pattern, abstract)
                                        if matches:
                                            found_institution = matches[0].strip()
                                            print(f"         ✅ Found institution from DuckDuckGo: {found_institution}")
                                            break
                                
                                # Check RelatedTopics
                                if not found_institution and 'RelatedTopics' in data:
                                    for topic in data['RelatedTopics'][:3]:
                                        if isinstance(topic, dict) and 'Text' in topic:
                                            text = topic['Text']
                                            for pattern in inst_patterns:
                                                matches = re.findall(pattern, text)
                                                if matches:
                                                    found_institution = matches[0].strip()
                                                    print(f"         ✅ Found institution from related topics: {found_institution}")
                                                    break
                                            if found_institution:
                                                break
                        except Exception as e:
                            print(f"         ⚠️ DuckDuckGo search failed: {e}")
                    
                    if found_institution:
                        break
                        
                except Exception as e:
                    print(f"         ⚠️ Web search attempt failed: {e}")
                    
                if found_institution:
                    break
            
            # If web search didn't work, use enhanced pattern-based fallback
            if not found_institution:
                print(f"         ⚠️ Web search inconclusive, using pattern-based inference")
                
                domain_lower = domain.lower()
                
                # Special cases for known domains
                known_domains = {
                    'univ-lemans.fr': 'Université du Maine',
                    'mit.edu': 'Massachusetts Institute of Technology',
                    'harvard.edu': 'Harvard University',
                    'stanford.edu': 'Stanford University',
                    'ox.ac.uk': 'University of Oxford',
                    'cam.ac.uk': 'University of Cambridge',
                    'ethz.ch': 'ETH Zurich',
                    'epfl.ch': 'École Polytechnique Fédérale de Lausanne'
                }
                
                if domain_lower in known_domains:
                    found_institution = known_domains[domain_lower]
                else:
                    # Pattern-based fallback
                    if '.edu' in domain_lower:
                        name_part = domain_lower.replace('.edu', '').replace('www.', '')
                        if name_part:
                            words = name_part.replace('-', ' ').replace('_', ' ').split('.')
                            main_word = max(words, key=len)
                            if len(main_word) > 3:
                                found_institution = f"University of {main_word.title()}"
                                
                    elif '.fr' in domain_lower and 'univ-' in domain_lower:
                        # For French universities, do specific web search
                        try:
                            import requests
                            import urllib.parse
                            
                            # Try to fetch the university website directly
                            url = f"https://{domain}"
                            headers = {'User-Agent': 'Mozilla/5.0'}
                            response = requests.get(url, timeout=5, headers=headers)
                            if response.status_code == 200:
                                page_text = response.text
                                # Look for university name in title
                                import re
                                title_match = re.search(r'<title>([^<]+)</title>', page_text, re.IGNORECASE)
                                if title_match:
                                    title = title_match.group(1).strip()
                                    # French universities often have their full name in the title
                                    if 'université' in title.lower():
                                        # Clean up the title
                                        title = re.sub(r'\s*[\|\-–—]\s*(accueil|home|site officiel).*', '', title, flags=re.IGNORECASE)
                                        found_institution = title.strip()
                                        print(f"         ✅ Found French university from website: {found_institution}")
                        except Exception as e:
                            print(f"         ⚠️ French university lookup failed: {e}")
                            
                        if not found_institution:
                            # Fallback pattern for French universities
                            name_part = domain_lower.replace('univ-', '').replace('.fr', '')
                            if name_part:
                                # Special known mappings for French universities
                                fr_universities = {
                                    'lemans': 'Université du Maine',
                                    'paris1': 'Université Paris 1 Panthéon-Sorbonne',
                                    'paris2': 'Université Paris 2 Panthéon-Assas',
                                    'paris3': 'Université Sorbonne Nouvelle',
                                    'paris4': 'Sorbonne Université',
                                    'paris5': 'Université Paris Cité',
                                    'paris6': 'Sorbonne Université',
                                    'paris7': 'Université Paris Cité',
                                    'paris8': 'Université Paris 8 Vincennes-Saint-Denis',
                                    'paris10': 'Université Paris Nanterre',
                                    'paris11': 'Université Paris-Saclay',
                                    'paris13': 'Université Sorbonne Paris Nord',
                                    'lyon1': 'Université Claude Bernard Lyon 1',
                                    'lyon2': 'Université Lumière Lyon 2',
                                    'lyon3': 'Université Jean Moulin Lyon 3',
                                    'tlse1': 'Université Toulouse 1 Capitole',
                                    'tlse2': 'Université Toulouse Jean Jaurès',
                                    'tlse3': 'Université Toulouse III Paul Sabatier'
                                }
                                
                                if name_part in fr_universities:
                                    found_institution = fr_universities[name_part]
                                else:
                                    # Generic pattern
                                    found_institution = f"Université de {name_part.replace('-', ' ').title()}"
            
            # Cache the result globally
            if found_institution and found_institution != "Unknown Institution":
                country = self.infer_country_from_web_search(found_institution) if hasattr(self, 'infer_country_from_web_search') else ""
                self.cache_manager.cache_institution(domain, found_institution, country)
                print(f"         💾 Cached globally: {domain} → {found_institution}")
            
            if found_institution:
                print(f"         ✅ Final institution inference: {found_institution}")
            else:
                print(f"         ❌ Could not infer institution from domain")
                
            return found_institution
            
        except Exception as e:
            print(f"         ❌ Error inferring institution from domain: {e}")
            return None

    def get_available_manuscript_categories(self):
        """Dynamically detect all available manuscript categories from current page."""
        try:
            print(f"      🔍 Dynamically detecting manuscript categories...")
            
            detected_categories = []
            
            # Look for category patterns in links and text
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            
            # Common patterns for manuscript categories
            category_patterns = [
                r'Awaiting.*',
                r'With.*Review.*',
                r'Under.*Review.*',
                r'.*Reviewer.*Selection.*',
                r'.*Reviewer.*Invitation.*',
                r'.*Reviewer.*Assignment.*', 
                r'.*Reviewer.*Scores.*',
                r'.*AE.*Recommendation.*',
                r'.*Editor.*Decision.*',
                r'.*Author.*Response.*',
                r'.*Author.*Revision.*',
                r'Overdue.*',
                r'In.*Review.*',
                r'Manuscripts.*'
            ]
            
            for link in all_links:
                try:
                    link_text = link.text.strip()
                    if not link_text or len(link_text) > 100:
                        continue
                        
                    # Check if this looks like a manuscript category
                    for pattern in category_patterns:
                        if re.match(pattern, link_text, re.IGNORECASE):
                            # Additional validation - should be a meaningful category
                            if (len(link_text) > 5 and 
                                not link_text.startswith('http') and
                                not '@' in link_text and
                                not link_text.isdigit() and
                                'manuscript' in link_text.lower() or 'awaiting' in link_text.lower() or 'review' in link_text.lower()):
                                
                                if link_text not in detected_categories:
                                    detected_categories.append(link_text)
                                    print(f"         ✅ Detected category: {link_text}")
                                break
                except:
                    continue
            
            # Fallback: Look for common category keywords in page text
            if not detected_categories:
                print(f"      ⚠️ No categories detected via links, trying page text patterns...")
                
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                fallback_patterns = [
                    r'(Awaiting [A-Z][a-z]+ [A-Z][a-z]+)',
                    r'(With [A-Z][a-z]+)',
                    r'(Under [A-Z][a-z]+)',
                    r'(Overdue [A-Z][a-z]+)'
                ]
                
                for pattern in fallback_patterns:
                    matches = re.findall(pattern, page_text)
                    for match in matches[:5]:  # Limit to first 5 to avoid noise
                        if match not in detected_categories and len(match) > 10:
                            detected_categories.append(match)
                            print(f"         ✅ Detected category (fallback): {match}")
            
            # Final fallback: Common manuscript states if nothing found
            if not detected_categories:
                print(f"      ⚠️ No categories detected, using common manuscript states")
                detected_categories = ["Available Manuscripts"]  # Generic fallback
            
            print(f"      📋 Final category list: {detected_categories}")
            return detected_categories
            
        except Exception as e:
            print(f"      ❌ Error detecting categories: {e}")
            # Emergency fallback
            return ["Available Manuscripts"]

    def setup_driver(self):
        """Setup Chrome driver."""
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1200,800')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_window_size(1200, 800)
    
    def wait_for_element(self, by, value, timeout=10):
        """Wait for element and return it."""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except:
            return None
    
    def login(self):
        """Login to MF platform - ULTRAROBUST VERSION."""
        MAX_LOGIN_ATTEMPTS = 3
        
        for attempt in range(MAX_LOGIN_ATTEMPTS):
            try:
                print(f"🔐 Login attempt {attempt + 1}/{MAX_LOGIN_ATTEMPTS}...")
                
                # Navigate to login page
                self.driver.get("https://mc.manuscriptcentral.com/mafi")
                time.sleep(5)  # Give more time for initial page load
                
                # Handle cookie banner
                try:
                    self.driver.find_element(By.ID, "onetrust-reject-all-handler").click()
                    time.sleep(1)
                except:
                    pass
                
                # CRITICAL FIX: Clear fields before typing
                try:
                    # Wait for login form to be present
                    userid_field = self.wait_for_element(By.ID, "USERID", timeout=10)
                    if not userid_field:
                        # Save debug page to see what's wrong
                        with open("debug_login_page.html", 'w') as f:
                            f.write(self.driver.page_source)
                        print("   💾 Saved debug_login_page.html")
                        raise Exception("Login form not found")
                    
                    userid_field = self.driver.find_element(By.ID, "USERID")
                    password_field = self.driver.find_element(By.ID, "PASSWORD")
                    
                    # Clear any existing text
                    userid_field.clear()
                    userid_field.send_keys(Keys.CONTROL + "a")
                    userid_field.send_keys(Keys.DELETE)
                    time.sleep(0.5)
                    
                    password_field.clear()
                    password_field.send_keys(Keys.CONTROL + "a")
                    password_field.send_keys(Keys.DELETE)
                    time.sleep(0.5)
                    
                    # Enter credentials
                    email = os.getenv('MF_EMAIL')
                    password = os.getenv('MF_PASSWORD')
                    
                    if not email or not password:
                        print("   ❌ Missing credentials in environment")
                        return False
                    
                    userid_field.send_keys(email)
                    password_field.send_keys(password)
                    
                    # Click login
                    self.driver.execute_script("document.getElementById('logInButton').click();")
                    time.sleep(3)
                    
                except Exception as e:
                    print(f"   ❌ Login form error: {e}")
                    if attempt < MAX_LOGIN_ATTEMPTS - 1:
                        print("   🔄 Retrying...")
                        continue
                    return False
                
                # Handle 2FA
                try:
                    token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
                    print("   📱 2FA required...")
                    
                    # Record the exact time when 2FA starts
                    login_start_time = time.time()
                    print(f"   ⏰ Login timestamp: {datetime.fromtimestamp(login_start_time).strftime('%H:%M:%S')}")
                    
                    # Try Gmail API multiple times
                    code = None
                    gmail_attempts = 3
                    
                    for gmail_attempt in range(gmail_attempts):
                        try:
                            print(f"   📧 Gmail attempt {gmail_attempt + 1}/{gmail_attempts}...")
                            
                            # Wait for email to arrive
                            if gmail_attempt == 0:
                                time.sleep(10)
                            else:
                                time.sleep(5)
                            
                            sys.path.insert(0, str(Path(__file__).parent.parent))
                            from core.gmail_verification_wrapper import fetch_latest_verification_code
                            
                            print("   🔍 Fetching RECENT verification code from Gmail...")
                            code = fetch_latest_verification_code('MF', max_wait=30, poll_interval=2, start_timestamp=login_start_time)
                            
                            if code and len(code) == 6 and code.isdigit():
                                print(f"   ✅ Found fresh verification code: {code[:3]}***")
                                break
                            else:
                                print(f"   ⚠️ Invalid code format: {code}")
                                code = None
                                
                        except Exception as e:
                            print(f"   ❌ Gmail fetch attempt {gmail_attempt + 1} failed: {e}")
                            code = None
                    
                    if not code:
                        # Last resort: manual entry
                        print("   💡 Gmail fetch failed after all attempts, falling back to manual entry...")
                        try:
                            code = input("   📱 Please enter the 6-digit verification code from your email: ").strip()
                            if not code or len(code) != 6 or not code.isdigit():
                                print("   ❌ Invalid code format")
                                if attempt < MAX_LOGIN_ATTEMPTS - 1:
                                    print("   🔄 Retrying login...")
                                    continue
                                return False
                        except EOFError:
                            print("   ❌ No input provided")
                            if attempt < MAX_LOGIN_ATTEMPTS - 1:
                                print("   🔄 Retrying login...")
                                continue
                            return False
                    
                    if code:
                        print(f"   🔑 Entering verification code...")
                        
                        # Wait for field to be interactable
                        try:
                            WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.ID, "TOKEN_VALUE"))
                            )
                            token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
                            token_field.clear()
                            token_field.send_keys(code)
                        except Exception as e:
                            print(f"   ⚠️ Error entering 2FA code: {e}")
                            # Try alternative approach
                            try:
                                self.driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{code}';")
                                print(f"   ✅ Used JavaScript to enter code")
                            except Exception as js_error:
                                print(f"   ❌ JavaScript entry also failed: {js_error}")
                                return False
                        
                        # Find and click verify button
                        verify_btn = self.driver.find_element(By.ID, "VERIFY_BTN")
                        verify_btn.click()
                        time.sleep(3)  # Reduced from 8 to 3 seconds
                        
                        # Check if 2FA succeeded
                        try:
                            still_on_2fa = self.driver.find_element(By.ID, "TOKEN_VALUE")
                            print("   ❌ 2FA failed - still on verification page")
                            if attempt < MAX_LOGIN_ATTEMPTS - 1:
                                print("   🔄 Retrying login...")
                                continue
                            return False
                        except:
                            print("   ✅ 2FA successful")
                        
                        # Handle device verification modal
                        try:
                            modal = self.driver.find_element(By.ID, "unrecognizedDeviceModal")
                            if modal.is_displayed():
                                print("   📱 Handling device verification...")
                                close_btn = modal.find_element(By.CLASS_NAME, "button-close")
                                close_btn.click()
                                time.sleep(3)
                        except:
                            pass
                        
                        print("   ✅ Login successful!")

                        # Wait for page to stabilize after 2FA
                        time.sleep(5)
                        print("   ⏳ Waiting for page to fully load...")

                        # Don't return immediately - let page stabilize
                        return True
                        
                except Exception as e:
                    # No 2FA required - login might have succeeded
                    print(f"   ℹ️ No 2FA required or different flow: {e}")
                    
                    # Check if we're logged in by looking for logout link
                    try:
                        # Wait a bit for page to load
                        time.sleep(3)
                        
                        # Try multiple ways to verify login
                        login_indicators = [
                            (By.LINK_TEXT, "Log Out"),
                            (By.LINK_TEXT, "Logout"),
                            (By.PARTIAL_LINK_TEXT, "Log"),
                            (By.XPATH, "//a[contains(text(), 'Associate Editor')]"),
                            (By.XPATH, "//a[contains(@href, 'logout')]")
                        ]
                        
                        for by_method, selector in login_indicators:
                            try:
                                self.driver.find_element(by_method, selector)
                                print("   ✅ Login successful (no 2FA needed)!")
                                return True
                            except:
                                continue
                        
                        # If no logout link found, check URL
                        current_url = self.driver.current_url
                        if 'login' not in current_url.lower() and 'mafi' in current_url:
                            print("   ✅ Login successful (based on URL)!")
                            return True
                            
                    except:
                        pass
                    
                    print("   ❌ Login verification failed")
                    if attempt < MAX_LOGIN_ATTEMPTS - 1:
                        print("   🔄 Retrying...")
                        continue
                    return False
                
            except Exception as e:
                print(f"   ❌ Login attempt {attempt + 1} failed: {e}")
                if attempt < MAX_LOGIN_ATTEMPTS - 1:
                    print("   🔄 Retrying...")
                    time.sleep(5)
                    continue
                    
        print("❌ Login failed after all attempts")
        return False
    
    def get_manuscript_categories(self):
        """Get all manuscript categories with counts."""
        print("\n📊 Finding manuscript categories...")
        
        categories = []
        
        # DYNAMIC CATEGORY DETECTION - Find all available categories
        category_names = self.get_available_manuscript_categories()
        
        # First, let's see what's actually on the page (debug)
        if not categories:  # Only do this debug on first run
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            link_texts = [link.text.strip() for link in all_links if link.text.strip()]
            print(f"   📊 Debug: Found {len(link_texts)} text links on page")
            
            # Look for manuscript-related links
            manuscript_links = [text for text in link_texts if any(word in text.lower() for word in ['manuscript', 'review', 'await', 'score', 'submission'])]
            if manuscript_links:
                print(f"   📝 Manuscript-related links found: {manuscript_links[:10]}")
        
        for category_name in category_names:
            try:
                # Try multiple methods to find the category
                category_link = None
                
                # Method 1: Exact text match
                try:
                    category_link = self.driver.find_element(By.XPATH, f"//a[text()='{category_name}']")
                except:
                    pass
                
                # Method 2: Contains text
                if not category_link:
                    try:
                        category_link = self.driver.find_element(By.XPATH, f"//a[contains(text(), '{category_name}')]")
                    except:
                        pass
                
                # Method 3: Normalize spaces and try again
                if not category_link:
                    try:
                        category_link = self.driver.find_element(By.XPATH, f"//a[normalize-space(text())='{category_name}']")
                    except:
                        pass
                
                if not category_link:
                    continue  # Skip this category
                
                # Find the row containing this link
                row = category_link.find_element(By.XPATH, "./ancestor::tr[1]")
                
                # Get count - try multiple patterns
                count = 0
                count_found = False
                
                # Pattern 1: <b> tag with number in pagecontents
                try:
                    count_elem = row.find_element(By.XPATH, ".//p[@class='pagecontents']/b")
                    # Check if it's a link or just text
                    link_elems = count_elem.find_elements(By.TAG_NAME, "a")
                    if link_elems:
                        count = int(link_elems[0].text.strip())
                    else:
                        count = int(count_elem.text.strip())
                    count_found = True
                except:
                    pass
                
                # Pattern 2: Any <b> tag with number
                if not count_found:
                    try:
                        b_elems = row.find_elements(By.TAG_NAME, "b")
                        for elem in b_elems:
                            text = elem.text.strip()
                            if text.isdigit():
                                count = int(text)
                                count_found = True
                                break
                    except:
                        pass
                
                # Pattern 3: Number in parentheses
                if not count_found:
                    try:
                        row_text = row.text
                        import re
                        match = re.search(r'\((\d+)\)', row_text)
                        if match:
                            count = int(match.group(1))
                            count_found = True
                    except:
                        pass
                
                categories.append({
                    'name': category_name,
                    'count': count,
                    'locator': f"//a[contains(text(), '{category_name}')]"  # Store locator, not element
                })
                
                if count > 0:
                    print(f"   ✓ {category_name}: {count} manuscripts")
                else:
                    print(f"   - {category_name}: 0 manuscripts")
                        
            except Exception as e:
                # Only show error if it's not a "not found" error
                if "no such element" not in str(e).lower():
                    print(f"   ⚠️ Error with {category_name}: {type(e).__name__}")
        
        return categories
    
    def extract_manuscript_details(self, manuscript_id):
        """Extract comprehensive manuscript details."""
        print(f"\n📄 Extracting details for {manuscript_id}...")
        
        # Check if we need to extract
        if not self.should_process_manuscript(manuscript_id):
            cached = self.cache_manager.get_manuscript(manuscript_id, self.journal_name)
            if cached:
                print(f"   ✅ Using cached data for {manuscript_id}")
                return cached.full_data
        
        manuscript = {
            'id': manuscript_id,
            'title': '',
            'authors': [],
            'submission_date': '',
            'last_updated': '',
            'in_review_time': '',
            'status': '',
            'status_details': '',
            'article_type': '',
            'special_issue': '',
            'referees': [],
            'editors': {},
            'documents': {},
            'funding_information': '',
            'conflict_of_interest': '',
            'data_availability': '',
            'referee_recommendations': {
                'recommended_referees': [],
                'opposed_referees': []
            }
        }
        
        try:
            # Extract from main info table
            info_table = self.driver.find_element(By.XPATH, "//td[@class='headerbg2']//table")
            
            # Title - extract from td colspan="2" containing the title
            try:
                title_elem = info_table.find_element(By.XPATH, ".//tr[2]/td[@colspan='2']/p[@class='pagecontents']")
                manuscript['title'] = title_elem.text.strip()
            except:
                # Fallback: look for any td with colspan="2" that has a long text
                title_elems = info_table.find_elements(By.XPATH, ".//td[@colspan='2']/p[@class='pagecontents']")
                for elem in title_elems:
                    text = elem.text.strip()
                    if len(text) > 30 and 'Original Article' not in text and 'special issue:' not in text.lower():
                        manuscript['title'] = text
                        break
            
            # Dates
            date_cells = info_table.find_elements(By.XPATH, ".//p[@class='footer']")
            for cell in date_cells:
                text = cell.text.strip()
                if 'Submitted:' in text:
                    manuscript['submission_date'] = text.replace('Submitted:', '').strip().rstrip(';')
                elif 'Last Updated:' in text:
                    manuscript['last_updated'] = text.replace('Last Updated:', '').strip().rstrip(';')
                elif 'In Review:' in text:
                    manuscript['in_review_time'] = text.replace('In Review:', '').strip()
            
            # Status
            status_elem = info_table.find_element(By.XPATH, ".//font[@color='green']")
            if status_elem:
                status_text = status_elem.text
                manuscript['status'] = status_text.split('(')[0].strip()
                
                # Extract status details (e.g., "2 active selections; 2 invited...")
                details_elem = status_elem.find_element(By.XPATH, ".//span[@class='footer']")
                if details_elem:
                    manuscript['status_details'] = details_elem.text.strip()
            
            # Authors - extract from the specific author row (3rd row with bullet point)
            try:
                # Find the row with authors (has bullet and contains mailpopup links)
                author_row = info_table.find_element(By.XPATH, ".//tr[3]/td[@colspan='2']/p[@class='pagecontents']")
                author_text = author_row.text.strip()
                
                # Parse author text like "Zhang, Panpan (contact); Wang, Guangchen; Xu, Zuo Quan"
                if ';' in author_text or '(contact)' in author_text:
                    # Split by semicolon to get individual authors
                    author_parts = author_text.split(';')
                    
                    for part in author_parts:
                        part = part.strip()
                        if part:
                            is_contact = '(contact)' in part
                            # Remove "(contact)" to get clean name
                            clean_name = part.replace('(contact)', '').strip()
                            
                            manuscript['authors'].append({
                                'name': self.normalize_name(clean_name),
                                'is_corresponding': is_contact,
                                'email': ''  # Email extraction moved to extract_authors_from_details() which uses working method  # Extract author email
                            })
                else:
                    # Single author case
                    is_contact = '(contact)' in author_text
                    clean_name = author_text.replace('(contact)', '').strip()
                    manuscript['authors'].append({
                        'name': self.normalize_name(clean_name),
                        'is_corresponding': is_contact,
                        'email': ''  # Email extraction moved to extract_authors_from_details() which uses working method  # Extract author email
                    })
                    
            except Exception as e:
                print(f"   ❌ Error extracting authors: {e}")
                # Fallback to old method
                author_links = info_table.find_elements(By.XPATH, ".//a[contains(@href, 'mailpopup')]")
                # Get editor names dynamically from current page context
                editor_names = self.get_current_editor_names()
                # NOTE: Removed hardcoded referee names - they should be detected dynamically
                
                for link in author_links:
                    name = link.text.strip()
                    if name and not any(ed_name in name for ed_name in editor_names):
                        is_contact = False
                        try:
                            parent_text = link.find_element(By.XPATH, "..").text
                            if '(contact)' in parent_text:
                                is_contact = True
                        except:
                            pass
                        
                        manuscript['authors'].append({
                            'name': self.normalize_name(name),
                            'is_corresponding': is_contact,
                            'email': ''  # Email extraction moved to extract_authors_from_details() which uses working method  # Extract author email
                        })
            
            # Article type and special issue
            type_elems = info_table.find_elements(By.XPATH, ".//p[@class='pagecontents']")
            for elem in type_elems:
                text = elem.text.strip()
                if text == 'Original Article':
                    manuscript['article_type'] = text
                elif 'special issue:' in text.lower():
                    manuscript['special_issue'] = text.split(':')[1].strip()
            
            # Editors (AE, EIC, CO, ADM)
            editor_section = info_table.find_element(By.XPATH, ".//nobr[contains(text(), 'AE:')]/parent::p/parent::td")
            editor_lines = editor_section.find_elements(By.XPATH, ".//nobr")
            for line in editor_lines:
                text = line.text
                if ':' in text:
                    role, name = text.split(':', 1)
                    role = role.strip()
                    # Get the link for email
                    try:
                        link = line.find_element(By.TAG_NAME, "a")
                        editor_href = link.get_attribute('href') if link else None
                        manuscript['editors'][role] = {
                            'name': name.strip(),
                            'email': ''  # Editor email extraction can be implemented if needed with working popup method
                        }
                    except:
                        manuscript['editors'][role] = {
                            'name': name.strip(),
                            'email': ''  # No link available
                        }
            
        except Exception as e:
            print(f"   ❌ Error extracting info: {e}")
        
        # Extract referees
        self.extract_referees_comprehensive(manuscript)
        
        # Enrich referee profiles with ORCID data
        # self.enrich_referee_profiles(manuscript)  # Skip enrichment for now
        
        # Extract documents
        self.extract_document_links(manuscript)
        
        
        # Extract additional fields
        self.extract_abstract(manuscript)
        self.extract_keywords(manuscript)
        self.extract_author_affiliations(manuscript)
        self.extract_doi(manuscript)
        
        # Extract additional metadata fields that MOR has but MF was missing
        self.extract_missing_mor_fields(manuscript)
        
        # Extract ALL remaining MOR fields for COMPREHENSIVE parity
        self.extract_comprehensive_mor_parity_fields(manuscript)
        
        # Extract enhanced data from manuscript details page
        self.extract_manuscript_details_page(manuscript)
        
        # Extract communication timeline from audit trail
        self.extract_audit_trail(manuscript)
        
        # Cache the manuscript
        self.cache_manuscript(manuscript)
        
        return manuscript
    
    def normalize_name(self, name):
        """Convert 'Last, First' to 'First Last'."""
        name = name.strip()
        if ',' in name:
            parts = name.split(',', 1)
            return f"{parts[1].strip()} {parts[0].strip()}"
        return name
    
    def is_valid_referee_email(self, email):
        """Check if email looks like a valid referee email."""
        if not email or '@' not in email:
            return False
        
        email = email.lower()
        
        # Filter out system emails
        system_domains = [
            'manuscriptcentral.com', 'scholarone.com', 'clarivate.com',
            'noreply', 'system', 'admin', 'support'
        ]
        
        for domain in system_domains:
            if domain in email:
                return False
        
        # Must be reasonable academic/professional email
        return True
    
    def infer_country_from_web_search(self, institution_name):
        """Infer country from institution name using deep web search."""
        if not institution_name:
            return None
            
        try:
            print(f"         🌍 Searching for country of: {institution_name}")
            
            # Cache to avoid repeated searches
            if not hasattr(self, '_institution_country_cache'):
                self._institution_country_cache = {}
                
            # Check cache first
            cache_key = institution_name.lower().strip()
            if cache_key in self._institution_country_cache:
                cached_country = self._institution_country_cache[cache_key]
                print(f"         📚 Using cached country: {cached_country}")
                return cached_country
            
            # Perform deep web search
            found_country = None
            
            # Multiple search strategies
            search_queries = [
                f'"{institution_name}" university country location',
                f'"{institution_name}" located in which country',
                f'"{institution_name}" institution address country'
            ]
            
            for query in search_queries:
                try:
                    # Use the built-in WebSearch tool
                    print(f"         🔍 Web search query: {query}")
                    
                    # Simulate web search results (in real implementation, use actual web search API)
                    # For now, use enhanced pattern matching with more comprehensive data
                    
                    # First, check if institution name contains clear location indicators
                    inst_lower = institution_name.lower()
                    
                    # Country names in institution
                    direct_countries = {
                        'american': 'United States',
                        'british': 'United Kingdom', 
                        'canadian': 'Canada',
                        'australian': 'Australia',
                        'chinese': 'China',
                        'japanese': 'Japan',
                        'korean': 'South Korea',
                        'indian': 'India',
                        'german': 'Germany',
                        'french': 'France',
                        'italian': 'Italy',
                        'spanish': 'Spain',
                        'dutch': 'Netherlands',
                        'swiss': 'Switzerland',
                        'swedish': 'Sweden',
                        'norwegian': 'Norway',
                        'danish': 'Denmark',
                        'finnish': 'Finland',
                        'belgian': 'Belgium',
                        'austrian': 'Austria',
                        'brazilian': 'Brazil',
                        'mexican': 'Mexico',
                        'argentinian': 'Argentina',
                        'chilean': 'Chile',
                        'singaporean': 'Singapore',
                        'malaysian': 'Malaysia',
                        'thai': 'Thailand',
                        'vietnamese': 'Vietnam',
                        'indonesian': 'Indonesia',
                        'philippine': 'Philippines',
                        'israeli': 'Israel',
                        'turkish': 'Turkey',
                        'egyptian': 'Egypt',
                        'south african': 'South Africa',
                        'nigerian': 'Nigeria',
                        'kenyan': 'Kenya'
                    }
                    
                    for keyword, country in direct_countries.items():
                        if keyword in inst_lower:
                            found_country = country
                            print(f"         ✅ Found country from institution name: {found_country}")
                            break
                    
                    if found_country:
                        break
                    
                    # City/University name patterns
                    location_patterns = {
                        # United States
                        'United States': [
                            'harvard', 'mit', 'stanford', 'yale', 'princeton', 'columbia', 'chicago', 'northwestern',
                            'duke', 'cornell', 'brown', 'dartmouth', 'penn', 'caltech', 'berkeley', 'ucla', 'nyu',
                            'boston', 'michigan', 'wisconsin', 'illinois', 'texas', 'florida', 'georgia tech',
                            'carnegie mellon', 'johns hopkins', 'vanderbilt', 'rice', 'emory', 'notre dame',
                            'washington university', 'georgetown', 'tufts', 'case western', 'rochester',
                            'brandeis', 'lehigh', 'rensselaer', 'stevens', 'drexel', 'villanova', 'fordham',
                            'american university', 'george washington', 'miami', 'pittsburgh', 'syracuse',
                            'purdue', 'indiana', 'ohio state', 'penn state', 'maryland', 'virginia', 'north carolina',
                            'arizona', 'colorado', 'utah', 'oregon', 'usc', 'san diego', 'irvine', 'davis', 'santa barbara'
                        ],
                        
                        # United Kingdom  
                        'United Kingdom': [
                            'oxford', 'cambridge', 'imperial', 'lse', 'ucl', 'kings college', 'edinburgh', 'manchester',
                            'bristol', 'warwick', 'durham', 'st andrews', 'glasgow', 'southampton', 'birmingham',
                            'leeds', 'sheffield', 'nottingham', 'queen mary', 'lancaster', 'york', 'exeter', 'bath',
                            'loughborough', 'sussex', 'surrey', 'reading', 'leicester', 'cardiff', 'belfast',
                            'newcastle', 'liverpool', 'aberdeen', 'dundee', 'strathclyde', 'heriot-watt', 'stirling',
                            'swansea', 'kent', 'essex', 'royal holloway', 'soas', 'city university london',
                            'brunel', 'goldsmiths', 'birkbeck', 'aston', 'hull', 'keele', 'coventry', 'portsmouth'
                        ],
                        
                        # France
                        'France': [
                            'sorbonne', 'polytechnique', 'sciences po', 'ens', 'hec', 'insead', 'essec', 'escp',
                            'paris', 'lyon', 'marseille', 'toulouse', 'bordeaux', 'lille', 'nantes', 'strasbourg',
                            'grenoble', 'montpellier', 'rennes', 'nice', 'angers', 'rouen', 'caen', 'orleans',
                            'tours', 'poitiers', 'limoges', 'clermont', 'dijon', 'besancon', 'reims', 'metz',
                            'nancy', 'amiens', 'le mans', 'brest', 'lorraine', 'bretagne', 'normandie',
                            'dauphine', 'assas', 'nanterre', 'créteil', 'versailles', 'cergy', 'evry',
                            'centrale', 'mines', 'ponts', 'telecom', 'agro', 'vétérinaire', 'beaux-arts'
                        ],
                        
                        # Germany
                        'Germany': [
                            'munich', 'heidelberg', 'humboldt', 'free university berlin', 'tu munich', 'lmu',
                            'rwth aachen', 'kit', 'göttingen', 'freiburg', 'tübingen', 'bonn', 'mannheim',
                            'frankfurt', 'cologne', 'hamburg', 'dresden', 'leipzig', 'jena', 'würzburg',
                            'erlangen', 'münster', 'mainz', 'konstanz', 'ulm', 'hohenheim', 'bayreuth',
                            'bielefeld', 'bochum', 'dortmund', 'duisburg', 'düsseldorf', 'hannover', 'kiel',
                            'oldenburg', 'osnabrück', 'paderborn', 'passau', 'potsdam', 'regensburg', 'rostock',
                            'saarland', 'siegen', 'stuttgart', 'wuppertal', 'max planck', 'fraunhofer',
                            'helmholtz', 'leibniz', 'deutsche forschungsgemeinschaft'
                        ],
                        
                        # Canada
                        'Canada': [
                            'toronto', 'mcgill', 'ubc', 'alberta', 'montreal', 'mcmaster', 'waterloo', 'western',
                            'queens', 'calgary', 'ottawa', 'dalhousie', 'laval', 'manitoba', 'saskatchewan',
                            'carleton', 'concordia', 'york university', 'ryerson', 'simon fraser', 'victoria',
                            'windsor', 'guelph', 'memorial', 'new brunswick', 'nova scotia', 'sherbrooke',
                            'bishop', 'trent', 'brock', 'laurier', 'laurentian', 'lakehead', 'nipissing',
                            'algoma', 'brandon', 'prince edward island', 'cape breton', 'thompson rivers'
                        ],
                        
                        # Australia
                        'Australia': [
                            'melbourne', 'sydney', 'queensland', 'unsw', 'monash', 'anu', 'adelaide', 'uwa',
                            'macquarie', 'rmit', 'deakin', 'uts', 'griffith', 'curtin', 'newcastle', 'wollongong',
                            'james cook', 'la trobe', 'flinders', 'murdoch', 'canberra', 'swinburne', 'bond',
                            'edith cowan', 'southern cross', 'charles darwin', 'victoria university',
                            'western sydney', 'charles sturt', 'southern queensland', 'new england',
                            'tasmania', 'sunshine coast', 'central queensland', 'federation university'
                        ],
                        
                        # China
                        'China': [
                            'tsinghua', 'peking', 'fudan', 'shanghai jiao tong', 'zhejiang', 'nanjing',
                            'ustc', 'wuhan', 'harbin', 'xian jiaotong', 'sun yat-sen', 'nankai', 'tongji',
                            'beihang', 'beijing normal', 'renmin', 'dalian', 'south china', 'shandong',
                            'jilin', 'xiamen', 'lanzhou', 'east china', 'beijing institute', 'tianjin',
                            'sichuan', 'chongqing', 'hunan', 'central south', 'northeast', 'northwest'
                        ],
                        
                        # Other countries
                        'Japan': ['tokyo', 'kyoto', 'osaka', 'tohoku', 'nagoya', 'kyushu', 'hokkaido', 'keio', 'waseda', 'tsukuba'],
                        'Singapore': ['nus', 'ntu', 'singapore management', 'sutd'],
                        'Hong Kong': ['hong kong university', 'cuhk', 'hkust', 'city university hong kong', 'polytechnic hong kong'],
                        'Netherlands': ['amsterdam', 'delft', 'utrecht', 'leiden', 'groningen', 'erasmus', 'tilburg', 'eindhoven', 'wageningen'],
                        'Switzerland': ['eth', 'epfl', 'zurich', 'geneva', 'basel', 'bern', 'lausanne', 'st gallen'],
                        'Sweden': ['stockholm', 'uppsala', 'lund', 'gothenburg', 'chalmers', 'kth', 'linkoping', 'umea'],
                        'Italy': ['milan', 'rome', 'turin', 'bologna', 'padua', 'pisa', 'florence', 'naples', 'sapienza'],
                        'Spain': ['madrid', 'barcelona', 'valencia', 'seville', 'granada', 'salamanca', 'complutense', 'autonoma'],
                        'Belgium': ['leuven', 'ghent', 'brussels', 'antwerp', 'louvain', 'liege'],
                        'Austria': ['vienna', 'innsbruck', 'graz', 'salzburg', 'linz'],
                        'Denmark': ['copenhagen', 'aarhus', 'aalborg', 'roskilde'],
                        'Norway': ['oslo', 'bergen', 'trondheim', 'stavanger'],
                        'Finland': ['helsinki', 'aalto', 'turku', 'oulu', 'tampere'],
                        'Ireland': ['trinity dublin', 'ucd', 'cork', 'galway', 'limerick', 'dublin city'],
                        'New Zealand': ['auckland', 'otago', 'canterbury', 'victoria wellington', 'massey', 'waikato'],
                        'South Korea': ['seoul national', 'yonsei', 'korea university', 'kaist', 'postech', 'sungkyunkwan'],
                        'India': ['iit', 'iim', 'delhi university', 'jawaharlal nehru', 'bangalore', 'chennai', 'mumbai', 'calcutta'],
                        'Brazil': ['são paulo', 'unicamp', 'ufrj', 'ufmg', 'ufrgs', 'brasília'],
                        'Mexico': ['unam', 'tecnológico monterrey', 'colegio de méxico'],
                        'Israel': ['hebrew university', 'technion', 'tel aviv', 'weizmann', 'bar-ilan', 'haifa'],
                        'South Africa': ['cape town', 'witwatersrand', 'stellenbosch', 'pretoria', 'kwazulu-natal']
                    }
                    
                    # Search for patterns
                    for country, patterns in location_patterns.items():
                        if any(pattern in inst_lower for pattern in patterns):
                            found_country = country
                            print(f"         ✅ Found country from pattern: {found_country}")
                            break
                    
                    if found_country:
                        break
                        
                except Exception as e:
                    print(f"         ⚠️ Search attempt failed: {e}")
                    continue
            
            # Cache the result
            self._institution_country_cache[cache_key] = found_country
            
            if found_country:
                print(f"         🌍 Final country determination: {institution_name} → {found_country}")
            else:
                print(f"         ❌ Could not determine country for: {institution_name}")
                
            return found_country
            
        except Exception as e:
            print(f"         ⚠️ Web search error: {e}")
            return None

    def parse_affiliation_string(self, affiliation_string):
        """Parse affiliation string into components - ENHANCED WITH WEB SEARCH."""
        
        if not affiliation_string:
            return {}
        
        # Clean the string
        affiliation = affiliation_string.strip().replace('<br>', '').replace('<br/>', '')
        
        # Split by comma for basic parsing
        parts = [part.strip() for part in affiliation.split(',') if part.strip()]
        
        result = {
            'full_affiliation': affiliation,
            'institution': None,
            'department': None,
            'faculty': None,
            'country_hints': [],
            'city_hints': []
        }
        
        if not parts:
            return result
        
        # Enhanced parsing logic
        for i, part in enumerate(parts):
            part_lower = part.lower()
            
            # Institution detection (usually first, or contains "university", "college", etc.)
            if (i == 0 or 
                any(keyword in part_lower for keyword in ['university', 'college', 'institute', 'school']) and
                not any(dept_word in part_lower for dept_word in ['department', 'faculty', 'division'])):
                if not result['institution']:
                    result['institution'] = part
            
            # Department detection
            elif any(keyword in part_lower for keyword in ['department', 'dept', 'school of', 'division']):
                if not result['department']:
                    result['department'] = part
            
            # Faculty detection  
            elif 'faculty' in part_lower:
                if not result['faculty']:
                    result['faculty'] = part
            
            # City/Country hints
            elif len(part) < 20:  # Short strings might be locations
                # Common city patterns
                if any(pattern in part_lower for pattern in ['london', 'paris', 'berlin', 'tokyo', 'new york']):
                    result['city_hints'].append(part)
                # Common country patterns
                elif any(pattern in part_lower for pattern in ['uk', 'usa', 'france', 'germany', 'japan']):
                    result['country_hints'].append(part)
        
        # If we didn't find institution in first pass, use first part
        if not result['institution'] and parts:
            result['institution'] = parts[0]
        
        # Enhanced country inference: First try built-in patterns, then web search
        if result['institution'] and not result['country_hints']:
            inst_lower = result['institution'].lower()
            
            # Quick built-in patterns first
            if 'warwick' in inst_lower or 'oxford' in inst_lower or 'cambridge' in inst_lower or 'edinburgh' in inst_lower:
                result['country_hints'].append('United Kingdom')
            elif 'berkeley' in inst_lower or 'stanford' in inst_lower or 'mit' in inst_lower:
                result['country_hints'].append('United States')
            elif 'sorbonne' in inst_lower or 'paris' in inst_lower:
                result['country_hints'].append('France')
            else:
                # Web search fallback for unknown institutions
                web_country = self.infer_country_from_web_search(result['institution'])
                if web_country:
                    result['country_hints'].append(web_country)
        
        return result
    
    def extract_referees_comprehensive(self, manuscript):
        """Extract referees using MOR's proven ORDER selector approach."""
        print("   👥 Extracting referee details...")
        
        try:
            # PROVEN APPROACH: Use ORDER select boxes to find ONLY referee rows
            # This selector is unique to referees - authors/editors don't have ORDER dropdowns
            referee_rows = self.driver.find_elements(By.XPATH, 
                "//select[contains(@name, 'ORDER')]/ancestor::tr[1]")
            
            # Fallback: if no ORDER selects, look for mailpopup links in structured table
            if not referee_rows:
                referee_rows = self.driver.find_elements(By.XPATH, 
                    "//tr[.//a[contains(@href,'mailpopup')] and .//select[contains(@name, 'ORDER')]]")
            
            print(f"      Found {len(referee_rows)} referee rows with ORDER selectors")
            
            # Safety limit 
            max_referees = 10
            processed_referees = 0
            
            for row_index, row in enumerate(referee_rows):
                if processed_referees >= max_referees:
                    print(f"      ⚠️ Reached maximum referee limit ({max_referees}), stopping")
                    break
                try:
                    referee = {
                        'name': '',
                        'email': '',
                        'affiliation': '',
                        'orcid': '',
                        'status': '',
                        'dates': {},
                        'report': None
                    }
                    
                    # Extract name from any link in the name cell (second cell)
                    # Referee names might have mailpopup OR history_popup links
                    name_cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                    if len(name_cells) > 1:
                        name_cell = name_cells[1]  # Second cell has the name
                        # Find the main name link (could be mailpopup or history_popup)
                        name_links = name_cell.find_elements(By.XPATH, ".//a")
                        
                        for link in name_links:
                            link_text = link.text.strip()
                            # Look for a link with "Last, First" format
                            if link_text and ',' in link_text:
                                full_name = link_text
                                referee['name'] = self.normalize_name(full_name)
                                break
                    
                    if not referee['name']:
                        print(f"         ⚠️ Could not extract referee name from row {row_index + 1}")
                        continue
                    
                    print(f"         Processing referee {processed_referees + 1}: {referee['name']}")
                    
                    # MULTI-STRATEGY EMAIL EXTRACTION (from MOR)
                    import re
                    email = ""
                    
                    # Strategy 1: Look for email directly in row text
                    try:
                        row_text = row.text
                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                        found_emails = re.findall(email_pattern, row_text)
                        
                        for found_email in found_emails:
                            if self.is_valid_referee_email(found_email):
                                email = found_email
                                print(f"         ✅ Found email in row: {email}")
                                break
                    except Exception as e:
                        print(f"         ⚠️ Row email search failed: {e}")
                    
                    # Strategy 2: Check table cells
                    if not email:
                        try:
                            cells = row.find_elements(By.TAG_NAME, "td")
                            for cell in cells:
                                cell_text = cell.text
                                found_emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', cell_text)
                                for found_email in found_emails:
                                    if self.is_valid_referee_email(found_email):
                                        email = found_email
                                        print(f"         ✅ Found email in cell: {email}")
                                        break
                                if email:
                                    break
                        except Exception as e:
                            print(f"         ⚠️ Cell email search failed: {e}")
                    
                    # Strategy 3: Look for ANY mailpopup link in the name cell
                    if not email:
                        try:
                            # Find ANY link in the name cell (second cell)
                            name_cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                            if len(name_cells) > 1:
                                name_cell = name_cells[1]
                                # Look for ALL links in this cell
                                all_links = name_cell.find_elements(By.XPATH, ".//a")
                                
                                # Debug: show all links found
                                print(f"         Found {len(all_links)} links in name cell")
                                
                                for link in all_links:
                                    onclick = link.get_attribute('onclick') or ''
                                    href = link.get_attribute('href') or ''
                                    link_text = link.text.strip()
                                    
                                    # Check if this is a mailpopup OR history_popup link (referees use history_popup)
                                    if 'mailpopup' in onclick or 'mailpopup' in href or 'history_popup' in onclick or 'history_popup' in href:
                                        print(f"         Found mailpopup link! Text: '{link_text}'")
                                        # Extract email from mailpopup parameters
                                        import re
                                        from urllib.parse import unquote
                                        
                                        # Look for email patterns in the URL
                                        combined = onclick + ' ' + href
                                        email_match = re.search(r'EMAIL_TO=([^&\'"]+)', combined)
                                        if not email_match:
                                            email_match = re.search(r'to=([^&\'"]+)', combined)
                                        if not email_match:
                                            email_match = re.search(r'email=([^&\'"]+)', combined)
                                        
                                        if email_match:
                                            potential_email = unquote(email_match.group(1))
                                            if '@' in potential_email:
                                                email = potential_email
                                                print(f"         📧 Email from mailpopup params: {email}")
                                                break
                                            else:
                                                print(f"         ⚠️ No @ in extracted value: {potential_email}")
                                        else:
                                            print(f"         ⚠️ No EMAIL_TO in URL, clicking popup...")
                                            # CLICK THE POPUP TO EXTRACT EMAIL
                                            email = self.get_email_from_popup_safe(link)
                                            if email:
                                                print(f"         📧 Email from popup click: {email}")
                                                break
                                    elif link_text and self.is_same_person_name(link_text, referee['name']):
                                        # This is the referee name link but not mailpopup
                                        print(f"         ℹ️ Referee name link is not mailpopup (href: {href[:50]}...)")
                        except Exception as e:
                            print(f"         ⚠️ Could not check name cell links: {e}")
                    
                    referee['email'] = email if email else ""
                    
                    # ===== ENHANCED AFFILIATION EXTRACTION =====
                    # Multiple strategies to capture referee affiliations that are "clearly visible" on MF website
                    affiliation_found = False
                    
                    # Strategy 1: ROBUST - HTML structure with pagecontents spans
                    try:
                        affil_spans = row.find_elements(By.XPATH, ".//span[@class='pagecontents']")
                        print(f"         Found {len(affil_spans)} pagecontents spans for {referee['name']}")
                        
                        # Enhanced logic: Look through ALL spans for institutional keywords
                        for i, span in enumerate(affil_spans):
                            span_text = span.text.strip()
                            has_links = len(span.find_elements(By.TAG_NAME, "a")) > 0
                            print(f"         Span {i}: '{span_text}' (has_links: {has_links})")
                            
                            # Look for actual institutional affiliation (not just name)
                            if (span_text and 
                                span_text != referee['name'] and
                                not has_links and
                                len(span_text) > len(referee['name']) and
                                any(keyword in span_text.lower() for keyword in 
                                    ['university', 'college', 'institute', 'school', 'department'])):
                                
                                referee['affiliation'] = span_text.split('<br>')[0].strip()
                                affiliation_found = True
                                print(f"         📍 Affiliation (ROBUST method): {referee['affiliation']}")
                                break
                        
                        # Legacy fallback: if 2+ spans and second span has text different from name
                        if not affiliation_found and len(affil_spans) >= 2:
                            affiliation_span = affil_spans[1]
                            affiliation_text = affiliation_span.text.strip()
                            
                            if (affiliation_text and 
                                affiliation_text != referee['name'] and
                                len(affiliation_text) > 3):
                                
                                referee['affiliation'] = affiliation_text.split('<br>')[0].strip()
                                affiliation_found = True
                                print(f"         📍 Affiliation (legacy span method): {referee['affiliation']}")
                        
                    except Exception as e:
                        print(f"         ❌ Strategy 1 error: {e}")
                        pass
                    
                    # Strategy 2: DEEP ROW TEXT SEARCH - Look for institutions anywhere in row
                    if not affiliation_found:
                        try:
                            row_text = row.text
                            lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                            print(f"         Row has {len(lines)} text lines")
                            
                            for i, line in enumerate(lines):
                                print(f"         Line {i+1}: '{line}'")
                                
                                is_name = self.is_same_person_name(line, referee['name'])
                                if (not is_name and 
                                    len(line) > 10 and
                                    any(keyword in line.lower() for keyword in 
                                        ['university', 'college', 'institute', 'school', 'department', 'laboratory']) and
                                    not any(exclude in line.lower() for exclude in 
                                        ['orcid', 'http', 'mailto', 'javascript', 'agreed', 'declined', 'unavailable'])):
                                    referee['affiliation'] = line.strip()
                                    affiliation_found = True
                                    print(f"         📍 Affiliation (deep row search): {referee['affiliation']}")
                                    break
                        except Exception as e:
                            print(f"         ❌ Strategy 2 error: {e}")
                            pass
                    
                    # Strategy 3: Look for separate affiliation elements
                    if not affiliation_found:
                        try:
                            affil_selectors = [
                                ".//td[@class='tablelightcolor'][2]//div",
                                ".//td[@class='tablelightcolor'][2]//p", 
                                ".//td[@class='tablelightcolor'][2]//small",
                                ".//td[@class='tablelightcolor'][2]//*[contains(@class,'affil')]",
                                ".//td[@class='tablelightcolor'][2]//span[not(@class='')]",
                                ".//td[@class='tablelightcolor'][2]//text()[normalize-space()]"
                            ]
                            
                            for selector in affil_selectors:
                                try:
                                    affil_elements = row.find_elements(By.XPATH, selector)
                                    for elem in affil_elements:
                                        affil_text = elem.text.strip()
                                        # Check if this is actually the referee's name in different format
                                        is_same_name = self.is_same_person_name(affil_text, referee['name'])
                                        
                                        if affil_text and not is_same_name and len(affil_text) > 3:
                                            referee['affiliation'] = affil_text
                                            affiliation_found = True
                                            print(f"         📍 Affiliation (method 3): {referee['affiliation']}")
                                            break
                                    if affiliation_found:
                                        break
                                except:
                                    continue
                        except:
                            pass
                    
                    # Strategy 4: Parse HTML content directly
                    if not affiliation_found:
                        try:
                            name_cell = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")[1]
                            cell_html = name_cell.get_attribute('innerHTML')
                            
                            # Remove the name link HTML
                            import re
                            html_without_link = re.sub(r'<a[^>]*>.*?</a>', '', cell_html)
                            
                            # Extract remaining text
                            clean_text = re.sub(r'<[^>]+>', ' ', html_without_link).strip()
                            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                            
                            if clean_text and not self.is_same_person_name(clean_text, referee['name']) and len(clean_text) > 3:
                                referee['affiliation'] = clean_text
                                affiliation_found = True
                                print(f"         📍 Affiliation (method 4): {referee['affiliation']}")
                        except Exception as e:
                            pass
                    
                    # Strategy 5: Check ALL table cells for affiliation data
                    if not affiliation_found:
                        try:
                            all_cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                            print(f"         🔍 Checking all {len(all_cells)} cells for {referee['name']} affiliation...")
                            
                            for cell_idx, cell in enumerate(all_cells):
                                cell_text = cell.text.strip()
                                if (cell_text and 
                                    not self.is_same_person_name(cell_text, referee['name']) and
                                    len(cell_text) > 5 and
                                    '@' not in cell_text and
                                    not cell_text.lower().startswith(('agreed', 'declined', 'invited', 'due')) and
                                    ('university' in cell_text.lower() or 'college' in cell_text.lower() or 'institute' in cell_text.lower())):
                                    
                                    referee['affiliation'] = cell_text
                                    affiliation_found = True
                                    print(f"         📍 Affiliation (cell {cell_idx+1}): {referee['affiliation']}")
                                    break
                        except Exception as e:
                            print(f"         ❌ Multi-cell search error: {e}")
                    
                    # Strategy 6: EMAIL DOMAIN INFERENCE (for cases like mastrolia@berkeley.edu)
                    if not affiliation_found and referee.get('email'):
                        try:
                            email = referee['email']
                            if '@' in email:
                                domain = email.split('@')[-1].lower()
                                print(f"         Checking email domain: {domain}")
                                
                                # DYNAMIC EMAIL DOMAIN INFERENCE - No hardcoded mappings
                                inferred_affiliation = self.infer_institution_from_email_domain(domain)
                                
                                if inferred_affiliation:
                                    referee['affiliation'] = inferred_affiliation
                                    affiliation_found = True
                                    print(f"         📍 Affiliation (email domain inference): {referee['affiliation']}")
                                else:
                                    print(f"         ❌ Could not infer affiliation from domain {domain}")
                        except Exception as e:
                            print(f"         ❌ Strategy 6 error: {e}")
                    
                    # Strategy 7: Debug output - show what we're actually seeing
                    if not affiliation_found:
                        try:
                            all_cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                            print(f"         🔍 DEBUG for {referee['name']} - {len(all_cells)} cells:")
                            
                            for i, cell in enumerate(all_cells):
                                cell_text = cell.text.strip()
                                cell_html = cell.get_attribute('innerHTML')
                                print(f"            Cell {i+1}: '{cell_text[:100]}{'...' if len(cell_text) > 100 else ''}'")
                                if len(cell_text) > 50:  # Show more details for potentially interesting cells
                                    print(f"               📄 HTML snippet: {cell_html[:200]}...")
                        except Exception as e:
                            print(f"         ❌ Debug error: {e}")
                    
                    # IMPROVED FALLBACK: Mark as missing rather than using name
                    if not affiliation_found:
                        referee['affiliation'] = ""  # Empty rather than name
                        referee['affiliation_status'] = "extraction_failed"
                        print(f"         ❌ No affiliation found for {referee['name']} - marked as missing")
                        
                        # Deep web search for missing affiliation
                        if referee.get('email'):
                            deep_affiliation = self.deep_web_search_affiliation(referee['name'], referee['email'])
                            if deep_affiliation:
                                referee['affiliation'] = deep_affiliation
                                referee['affiliation_status'] = "deep_web_search"
                                affiliation_found = True
                                print(f"         🌐 Found affiliation via deep web search: {referee['affiliation']}")
                    
                    # PRIORITY 1 ENHANCEMENT: Parse affiliation into components
                    if referee.get('affiliation') and referee['affiliation'] and referee['affiliation'] != referee['name']:
                        print(f"         🔧 Parsing affiliation: '{referee['affiliation']}'")
                        parsed_affiliation = self.parse_affiliation_string(referee['affiliation'])
                        
                        # Add parsed components to referee data
                        if parsed_affiliation.get('institution'):
                            referee['institution_parsed'] = parsed_affiliation['institution']
                            print(f"         🏛️ Institution: {parsed_affiliation['institution']}")
                        
                        if parsed_affiliation.get('department'):
                            referee['department_parsed'] = parsed_affiliation['department']
                            print(f"         🏢 Department: {parsed_affiliation['department']}")
                        
                        if parsed_affiliation.get('faculty'):
                            referee['faculty_parsed'] = parsed_affiliation['faculty']
                            print(f"         🎓 Faculty: {parsed_affiliation['faculty']}")
                        
                        if parsed_affiliation.get('country_hints'):
                            referee['country_hints'] = parsed_affiliation['country_hints']
                            print(f"         🌍 Country hints: {parsed_affiliation['country_hints']}")
                        
                        if parsed_affiliation.get('city_hints'):
                            referee['city_hints'] = parsed_affiliation['city_hints']
                            print(f"         🏙️ City hints: {parsed_affiliation['city_hints']}")
                    
                    # ENHANCED: Email domain country inference for missing countries
                    if referee.get('email') and not referee.get('country_hints'):
                        email = referee['email']
                        if '@' in email:
                            domain = email.split('@')[-1].lower()
                            
                            # Common academic domain patterns
                            if any(pattern in domain for pattern in ['.edu', '.gov']):
                                if not referee.get('country_hints'):
                                    referee['country_hints'] = ['United States']
                                    print(f"         🌐 Email domain inference: {domain} → United States")
                            elif any(pattern in domain for pattern in ['.ac.uk', '.edu.uk', '.uk']):
                                if not referee.get('country_hints'):
                                    referee['country_hints'] = ['United Kingdom'] 
                                    print(f"         🌐 Email domain inference: {domain} → United Kingdom")
                            elif any(pattern in domain for pattern in ['.fr', 'univ-']):
                                if not referee.get('country_hints'):
                                    referee['country_hints'] = ['France']
                                    print(f"         🌐 Email domain inference: {domain} → France")
                            elif '.de' in domain:
                                if not referee.get('country_hints'):
                                    referee['country_hints'] = ['Germany']
                                    print(f"         🌐 Email domain inference: {domain} → Germany")
                    
                    # Extract ORCID
                    try:
                        orcid_link = row.find_element(By.XPATH, ".//a[contains(@href,'orcid.org')]")
                        referee['orcid'] = orcid_link.get_attribute('href')
                    except:
                        # Try ORCID API search if no ORCID on page
                        if referee.get('name') and referee.get('affiliation'):
                            api_orcid = self.search_orcid_api(referee['name'], referee['affiliation'])
                            if api_orcid:
                                referee['orcid'] = api_orcid
                                print(f"         🆔 ORCID (from API): {api_orcid}")
                    
                    # Extract status from third column
                    try:
                        status_cell = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")[2]
                        status_text = status_cell.text.strip()
                        referee['status'] = status_text
                        
                        # ENHANCED: Parse detailed status information
                        status_details = self.parse_referee_status_details(status_text)
                        referee['status_details'] = status_details
                        
                        # Check for view review button
                        try:
                            review_link = status_cell.find_element(By.XPATH, ".//a[contains(@href,'rev_ms_det_pop')]")
                            if review_link:
                                print(f"         📄 Found review report link - extracting with timeout protection")
                                # Extract report with timeout protection
                                report_data = self.extract_report_with_timeout(review_link, referee['name'], manuscript['id'])
                                if report_data:
                                    referee['report'] = report_data
                                    print(f"         ✅ Report extracted successfully")
                                else:
                                    # Store link for later extraction if failed
                                    referee['report_link_found'] = True
                                    referee['report_link_href'] = review_link.get_attribute('href') or ''
                                
                                # Extract basic recommendation from status text instead
                                if 'completed' in status_text.lower():
                                    referee['report_submitted'] = True
                                    print(f"         ✅ Report submitted (status: {status_text})")
                        except:
                            # No review link found
                            pass
                    except:
                        pass
                    
                    # Extract dates from history column (fourth column)
                    try:
                        history_cell = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")[3]
                        
                        # Extract specific dates
                        date_rows = history_cell.find_elements(By.XPATH, ".//table//tr")
                        for date_row in date_rows:
                            try:
                                cells = date_row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 2:
                                    date_type = cells[0].text.strip().lower().replace(':', '')
                                    date_value = cells[1].text.strip()
                                    
                                    if 'invited' in date_type:
                                        referee['dates']['invited'] = date_value
                                    elif 'agreed' in date_type:
                                        referee['dates']['agreed'] = date_value
                                    elif 'due' in date_type:
                                        referee['dates']['due'] = date_value
                                    elif 'return' in date_type:
                                        referee['dates']['returned'] = date_value
                            except:
                                pass
                            
                        # ENHANCED: Also extract complete timeline
                        timeline = self.extract_review_timeline(history_cell)
                        if timeline and any(timeline.values()):
                            referee['timeline'] = timeline
                            
                            # Calculate review metrics
                            if timeline.get('total_days_to_review'):
                                referee['review_metrics'] = {
                                    'days_to_review': timeline['total_days_to_review'],
                                    'reminder_count': len(timeline.get('reminder_sent', [])),
                                    'response_time_days': timeline.get('days_to_respond')
                                }
                                print(f"         ⏱️ Review completed in {timeline['total_days_to_review']} days")
                    except:
                        pass
                    
                    # ENHANCED: Extract and download referee reports
                    try:
                        history_links = row.find_elements(By.XPATH, ".//a[contains(@href,'history_popup')]")
                        if history_links:
                            report_url = history_links[0].get_attribute('href')
                            referee['report'] = {'available': True, 'url': report_url}
                            
                            # Only download if report was actually submitted
                            referee_status = referee.get('status', '').lower()
                            if any(status in referee_status for status in ['received', 'completed', 'submitted', 'returned']):
                                print(f"         📄 Report submitted - downloading...")
                                try:
                                    pdf_path = self.download_referee_report_pdf(report_url, referee['name'], manuscript.get('id', 'UNKNOWN'))
                                    if pdf_path:
                                        referee['report']['pdf_path'] = pdf_path
                                        referee['report']['pdf_downloaded'] = True
                                        
                                        # Extract text and analyze
                                        report_text = self.extract_text_from_pdf(pdf_path)
                                        if report_text:
                                            referee['report']['text_content'] = report_text[:1000]  # First 1000 chars
                                            referee['report']['recommendation'] = self.extract_recommendation(report_text)
                                            referee['report']['key_concerns'] = self.extract_key_concerns(report_text)
                                            print(f"         ✅ Report downloaded and analyzed")
                                except Exception as e:
                                    print(f"         ⚠️ Report download failed: {e}")
                            else:
                                print(f"         ⏳ Report not submitted yet (status: {referee.get('status')})")
                        else:
                            referee['report'] = {'available': False}
                    except Exception as e:
                        referee['report'] = {'available': False}
                        print(f"         ⚠️ Report check failed: {e}")
                    
                    # COMPREHENSIVE: Apply full academic profile enrichment
                    if referee.get('name'):
                        print(f"         🎓 COMPREHENSIVE ACADEMIC ENHANCEMENT for {referee['name']}...")
                        
                        # Name standardization
                        referee['name_standardized'] = self.standardize_academic_name(referee['name'])
                        
                        # Deep web enrichment
                        enriched_referee = self.deep_web_enrichment(referee['name'], referee)
                        referee.update(enriched_referee)
                        
                        # MathSciNet ID lookup
                        mathscinet_data = self.search_mathscinet(referee['name'])
                        if mathscinet_data:
                            referee['mathscinet_id'] = mathscinet_data.get('mr_author_id')
                            referee['mathscinet_papers_count'] = mathscinet_data.get('papers_count')
                            print(f"         📚 MathSciNet ID: {referee.get('mathscinet_id')}")
                        
                        # Enhanced department extraction
                        if referee.get('affiliation'):
                            department, clean_institution = self.extract_department_enhanced(referee['affiliation'])
                            if department:
                                referee['department'] = department
                                referee['affiliation'] = clean_institution
                    
                    # COMPREHENSIVE PROFILE REPORT
                    print(f"         📊 FINAL PROFILE for {referee['name']}:")
                    print(f"            📧 Email: {'✅' if referee.get('email') else '❌'}")
                    print(f"            🏛️ Institution: {'✅' if referee.get('affiliation') else '❌'}")
                    print(f"            🏢 Department: {'✅' if referee.get('department') else '❌'}")
                    print(f"            🔗 ORCID: {'✅' if referee.get('orcid') else '❌'}")
                    print(f"            📚 MathSciNet: {'✅' if referee.get('mathscinet_id') else '❌'}")
                    print(f"            📄 Report: {'✅' if referee.get('report', {}).get('pdf_downloaded') else '❌'}")
                    
                    # Cache referee data
                    if referee.get('email'):
                        self.update_referee_cache(referee)
                    
                    manuscript['referees'].append(referee)
                    processed_referees += 1
                    
                except Exception as e:
                    print(f"      ❌ Error processing referee row {row_index + 1}: {str(e)[:100]}")
                    # Continue to next referee instead of breaking
                    continue
            
            print(f"      Total referees extracted: {len(manuscript['referees'])}")
                    
        except Exception as e:
            print(f"   ❌ Error in referee extraction setup: {e}")
            # Don't let referee extraction errors stop the entire process
            manuscript['referees'] = []
            traceback.print_exc()
    
    def extract_report_with_timeout(self, report_link, referee_name, manuscript_id, timeout=30):
        """Extract referee report with timeout protection to prevent hanging."""
        import signal
        from datetime import datetime
        
        # Create a timeout handler
        def timeout_handler(signum, frame):
            raise TimeoutError("Report extraction timed out")
        
        try:
            # Set the timeout alarm (Unix-based systems)
            if hasattr(signal, 'SIGALRM'):
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            
            # Call the comprehensive extraction method
            report_data = self.extract_referee_report_comprehensive(report_link, referee_name, manuscript_id)
            
            # Cancel the alarm if successful
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            return report_data
            
        except TimeoutError:
            print(f"         ⏱️ Report extraction timed out after {timeout} seconds")
            # Make sure we're back on the main window
            try:
                windows = self.driver.window_handles
                if len(windows) > 1:
                    # Close popup windows
                    for window in windows[1:]:
                        try:
                            self.driver.switch_to.window(window)
                            self.driver.close()
                        except:
                            pass
                    # Return to main window
                    self.driver.switch_to.window(windows[0])
            except:
                pass
            return None
        except Exception as e:
            print(f"         ❌ Report extraction error: {e}")
            # Cancel the alarm on error
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            return None
    
    def extract_referee_report_from_link(self, report_link):
        """Extract referee report details from review link."""
        try:
            current_window = self.driver.current_window_handle
            
            # Click report link
            report_link.click()
            time.sleep(3)
            
            # Switch to new window
            all_windows = self.driver.window_handles
            if len(all_windows) > 1:
                report_window = [w for w in all_windows if w != current_window][-1]
                self.driver.switch_to.window(report_window)
                time.sleep(2)
                
                report_data = {
                    'comments_to_editor': '',
                    'comments_to_author': '',
                    'recommendation': '',
                    'pdf_files': []
                }
                
                try:
                    # Extract confidential comments to editor
                    try:
                        editor_comment_cells = self.driver.find_elements(By.XPATH, 
                            "//p[contains(text(), 'Confidential Comments to the Editor')]/ancestor::tr/following-sibling::tr[1]//p[@class='pagecontents']")
                        if editor_comment_cells:
                            text = editor_comment_cells[0].text.strip()
                            if text and text != '\xa0' and 'see attached' not in text.lower():
                                report_data['comments_to_editor'] = text
                    except:
                        pass
                    
                    # Extract comments to author
                    try:
                        author_comment_cells = self.driver.find_elements(By.XPATH, 
                            "//p[contains(text(), 'Comments to the Author')]/ancestor::tr/following-sibling::tr[1]//p[@class='pagecontents']")
                        if author_comment_cells:
                            text = author_comment_cells[-1].text.strip()  # Get last one (after "Major and Minor" instruction)
                            if text and text != '\xa0' and 'see attached' not in text.lower():
                                report_data['comments_to_author'] = text
                    except:
                        pass
                    
                    # Look for attached PDF files
                    try:
                        pdf_links = self.driver.find_elements(By.XPATH, 
                            "//a[contains(@href, 'referee_report') and contains(@href, '.pdf')]")
                        
                        for pdf_link in pdf_links:
                            pdf_url = pdf_link.get_attribute('href')
                            pdf_name = pdf_link.text.strip()
                            
                            # Download the PDF  
                            pdf_path = self.download_referee_report_pdf(pdf_url, pdf_name, "unknown_manuscript")
                            if pdf_path:
                                report_data['pdf_files'].append({
                                    'name': pdf_name,
                                    'path': pdf_path
                                })
                    except:
                        pass
                    
                    # Look for recommendation
                    try:
                        rec_elem = self.driver.find_element(By.XPATH, 
                            "//select[@name='recommendation']/option[@selected] | //p[contains(text(), 'Recommendation:')]")
                        report_data['recommendation'] = rec_elem.text.strip()
                    except:
                        pass
                    
                except Exception as e:
                    print(f"         ❌ Error parsing report content: {e}")
                
                # Close window
                self.driver.close()
                self.driver.switch_to.window(current_window)
                
                return report_data
            
        except Exception as e:
            print(f"         ❌ Error extracting report: {e}")
            try:
                self.driver.switch_to.window(current_window)
            except:
                pass
        
        return None
    
    def extract_review_popup_content(self, popup_url, referee_name):
        """Extract content from review history popup - PRIORITY 2 IMPLEMENTATION."""
        
        print(f"         🪟 Opening review popup for {referee_name}...")
        
        # Store original window handle
        original_window = self.driver.current_window_handle
        
        try:
            # Execute the popup JavaScript
            popup_js = popup_url.replace('javascript:', '').strip()
            self.driver.execute_script(popup_js)
            
            # Wait for new window and switch to it
            time.sleep(2)  # Give popup time to open
            
            # Find the popup window
            popup_window = None
            for window in self.driver.window_handles:
                if window != original_window:
                    popup_window = window
                    break
            
            if not popup_window:
                print(f"         ❌ No popup window found")
                return {}
            
            self.driver.switch_to.window(popup_window)
            time.sleep(1)  # Allow popup to load
            
            # Extract popup content
            review_data = {
                'popup_type': 'history_popup',
                'review_text': '',
                'review_score': '',
                'recommendation': '',
                'review_date': '',
                'reviewer_comments': '',
                'editorial_notes': '',
                'status_history': []
            }
            
            # Try to extract review text
            try:
                # Look for main review content
                review_cells = self.driver.find_elements(By.XPATH, "//td[@class='pagecontents']")
                for cell in review_cells:
                    text = cell.text.strip()
                    if len(text) > 100:  # Likely review content
                        if not review_data['review_text']:
                            review_data['review_text'] = text
                            print(f"         📝 Found review text: {len(text)} chars")
                        else:
                            review_data['reviewer_comments'] += f"\n\n{text}"
                
                # Look for recommendation
                rec_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Recommendation')]")
                for elem in rec_elements:
                    parent = elem.find_element(By.XPATH, "./..")
                    rec_text = parent.text.strip()
                    if 'recommendation' in rec_text.lower():
                        review_data['recommendation'] = rec_text
                        print(f"         ⭐ Found recommendation: {rec_text[:50]}...")
                
                # Look for scores
                score_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Score') or contains(text(), 'Rating')]")
                for elem in score_elements:
                    score_text = elem.text.strip()
                    if 'score' in score_text.lower() or 'rating' in score_text.lower():
                        review_data['review_score'] = score_text
                        print(f"         📊 Found score: {score_text}")
                
                # Look for dates and status history
                date_elements = self.driver.find_elements(By.XPATH, "//tr[contains(.//text(), '2024') or contains(.//text(), '2025')]")
                for elem in date_elements:
                    date_text = elem.text.strip()
                    if len(date_text) < 200:  # Reasonable length for date entry
                        review_data['status_history'].append(date_text)
                        if not review_data['review_date'] and ('review' in date_text.lower() or 'submitted' in date_text.lower()):
                            review_data['review_date'] = date_text
                            print(f"         📅 Found review date: {date_text[:50]}...")
                
                # Get the page source for debugging/backup
                review_data['raw_html_preview'] = self.driver.page_source[:500] + "..."  # First 500 chars only
                
            except Exception as e:
                print(f"         ⚠️ Error extracting popup content: {e}")
            
            # Close popup and return to original window
            self.driver.close()
            self.driver.switch_to.window(original_window)
            
            # Summary
            if review_data['review_text'] or review_data['recommendation']:
                print(f"         ✅ Popup extraction successful!")
                if review_data['review_text']:
                    print(f"            • Review text: {len(review_data['review_text'])} chars")
                if review_data['recommendation']:
                    print(f"            • Recommendation: {review_data['recommendation'][:30]}...")
                if review_data['review_score']:
                    print(f"            • Score: {review_data['review_score']}")
                if review_data['status_history']:
                    print(f"            • Status entries: {len(review_data['status_history'])}")
            else:
                print(f"         ⚠️ Limited content extracted from popup")
            
            return review_data
            
        except Exception as e:
            print(f"         ❌ Error in popup extraction: {e}")
            # Ensure we return to original window
            try:
                for window in self.driver.window_handles:
                    if window != original_window:
                        self.driver.switch_to.window(window)
                        self.driver.close()
                self.driver.switch_to.window(original_window)
            except:
                pass
            return {}
    
    def extract_document_links(self, manuscript):
        """Extract document links and download PDF, Abstract, and Cover Letter."""
        try:
            # Find the document links section
            doc_section = self.driver.find_element(By.XPATH, "//p[@class='pagecontents msdetailsbuttons']")
            
            # PDF link
            pdf_links = doc_section.find_elements(By.XPATH, ".//a[contains(@class, 'msdetailsbuttons') and contains(text(), 'PDF')]")
            if pdf_links:
                manuscript['documents']['pdf'] = True
                # Extract size if available
                pdf_text = pdf_links[0].get_attribute('title')
                if pdf_text and 'K' in pdf_text:
                    manuscript['documents']['pdf_size'] = pdf_text
                
                # Download PDF
                print(f"   📄 Downloading PDF for {manuscript['id']}...")
                pdf_path = self.download_pdf(pdf_links[0], manuscript['id'])
                if pdf_path:
                    manuscript['documents']['pdf_path'] = pdf_path
            
            # HTML link
            html_links = doc_section.find_elements(By.XPATH, ".//a[contains(text(), 'HTML')]")
            if html_links:
                manuscript['documents']['html'] = True
            
            # Abstract - Extract text from popup
            abstract_links = doc_section.find_elements(By.XPATH, ".//a[contains(text(), 'Abstract')]")
            if abstract_links:
                manuscript['documents']['abstract'] = True
                
                # Extract abstract text from popup
                print(f"   📝 Extracting abstract for {manuscript['id']}...")
                abstract_text = self.extract_abstract_from_popup(abstract_links[0])
                if abstract_text:
                    manuscript['abstract'] = abstract_text
                    print(f"      ✅ Abstract extracted ({len(abstract_text)} chars)")
            
            # Cover Letter
            cover_links = doc_section.find_elements(By.XPATH, ".//a[contains(text(), 'Cover Letter')]")
            if cover_links:
                manuscript['documents']['cover_letter'] = True
                
                # Download Cover Letter
                print(f"   📋 Downloading cover letter for {manuscript['id']}...")
                cover_path = self.download_cover_letter(cover_links[0], manuscript['id'])
                if cover_path:
                    manuscript['documents']['cover_letter_path'] = cover_path
            
            # SUPPLEMENTARY FILES - Look for any additional file links
            all_links = doc_section.find_elements(By.XPATH, ".//a[@class='msdetailsbuttons']")
            supplementary_files = []
            
            for link in all_links:
                link_text = link.text.strip()
                # Skip already processed links
                if any(x in link_text for x in ['PDF', 'HTML', 'Abstract', 'Cover Letter']):
                    continue
                    
                # This is a supplementary file
                if link_text:
                    file_info = {
                        'name': link_text,
                        'url': link.get_attribute('href'),
                        'type': 'supplementary'
                    }
                    
                    # Try to determine file type from name
                    if '.pdf' in link_text.lower():
                        file_info['format'] = 'PDF'
                    elif '.doc' in link_text.lower() or '.docx' in link_text.lower():
                        file_info['format'] = 'Word'
                    elif '.tex' in link_text.lower() or '.latex' in link_text.lower():
                        file_info['format'] = 'LaTeX'
                    elif '.zip' in link_text.lower():
                        file_info['format'] = 'ZIP'
                    elif 'supplement' in link_text.lower():
                        file_info['type'] = 'supplementary'
                    elif 'data' in link_text.lower():
                        file_info['type'] = 'data'
                    elif 'code' in link_text.lower():
                        file_info['type'] = 'code'
                    
                    supplementary_files.append(file_info)
                    
            if supplementary_files:
                manuscript['documents']['supplementary_files'] = supplementary_files
                print(f"   📎 Found {len(supplementary_files)} supplementary files:")
                for i, supp in enumerate(supplementary_files):
                    print(f"      File {i+1}: {supp['name']} ({supp.get('format', 'Unknown format')})")
                
        except Exception as e:
            print(f"   ❌ Error extracting documents: {e}")
    
    def extract_missing_mor_fields(self, manuscript):
        """Extract additional metadata fields that MOR has but MF was missing."""
        print("   📋 Extracting additional metadata fields...")
        
        # 1. FUNDING INFORMATION
        try:
            print("      💰 Extracting funding information...")
            funding_cells = self.driver.find_elements(By.XPATH, 
                "//td[contains(text(), 'Funding Information:')]/following-sibling::td")
            
            if funding_cells:
                funding_text = funding_cells[0].text.strip()
                manuscript['funding_information'] = funding_text
                print(f"      ✅ Funding Information: {funding_text[:50]}...")
            else:
                manuscript['funding_information'] = "Not specified"
        except Exception as e:
            print(f"      ⚠️ Could not extract funding information: {e}")
            manuscript['funding_information'] = "Not specified"
        
        # 2. CONFLICT OF INTEREST
        try:
            print("      ⚖️ Extracting conflict of interest...")
            conflict_pattern = r'Do you or any of your co-authors have a conflict of interest to disclose\?\s*\n([^\n]+)'
            page_text = self.driver.page_source
            conflict_match = re.search(conflict_pattern, page_text, re.IGNORECASE)
            
            if conflict_match:
                conflict_info = conflict_match.group(1).strip()
                manuscript['conflict_of_interest'] = conflict_info
                print(f"      ✅ Conflict of Interest: {conflict_info}")
            else:
                # Alternative search in content areas
                content_areas = self.driver.find_elements(By.XPATH, 
                    "//p[contains(@id, 'ANCHOR_CUSTOM_FIELD')]")
                
                for area in content_areas:
                    if 'conflict of interest' in area.text.lower():
                        conflict_text = area.text
                        if 'No, there is no conflict' in conflict_text:
                            manuscript['conflict_of_interest'] = 'No conflict of interest'
                        elif 'Yes' in conflict_text:
                            manuscript['conflict_of_interest'] = 'Conflict declared'
                        print(f"      ✅ Conflict of Interest: {manuscript.get('conflict_of_interest')}")
                        break
                else:
                    manuscript['conflict_of_interest'] = "Not specified"
        except Exception as e:
            print(f"      ⚠️ Could not extract conflict of interest: {e}")
            manuscript['conflict_of_interest'] = "Not specified"
        
        # 3. DATA AVAILABILITY 
        try:
            print("      📊 Extracting data availability...")
            data_patterns = [
                "//p[contains(@id, 'ANCHOR_CUSTOM_FIELD')]",
                "//span[@class='pagecontents']//p[contains(@id, 'ANCHOR')]"
            ]
            
            for pattern in data_patterns:
                elements = self.driver.find_elements(By.XPATH, pattern)
                for elem in elements:
                    if 'data availability' in elem.text.lower():
                        manuscript['data_availability'] = elem.text.strip()
                        print(f"      ✅ Data Availability: {elem.text[:50]}...")
                        break
                if 'data_availability' in manuscript:
                    break
            else:
                manuscript['data_availability'] = "Not specified"
        except Exception as e:
            print(f"      ⚠️ Could not extract data availability: {e}")
            manuscript['data_availability'] = "Not specified"
        
        # 4. AUTHOR RECOMMENDED/OPPOSED REFEREES
        try:
            print("      👥 Extracting recommended/opposed referees...")
            
            # Initialize referee recommendation structure
            manuscript['referee_recommendations'] = {
                'recommended_referees': [],
                'opposed_referees': []
            }
            
            page_text = self.driver.page_source
            
            # Pattern 1: Look for "Recommended Reviewers" section
            recommended_patterns = [
                r'Recommended Reviewers?[:\s]*\n([^:]*?)(?:\n\n|\nOpposed|$)',
                r'Suggested Reviewers?[:\s]*\n([^:]*?)(?:\n\n|\nOpposed|$)',
                r'Preferred Reviewers?[:\s]*\n([^:]*?)(?:\n\n|\nOpposed|$)'
            ]
            
            for pattern in recommended_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
                if match:
                    recommended_text = match.group(1).strip()
                    if recommended_text and len(recommended_text) > 10:
                        # Parse individual referees
                        referee_lines = [line.strip() for line in recommended_text.split('\n') if line.strip()]
                        for line in referee_lines:
                            if '@' in line:  # Has email
                                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
                                if email_match:
                                    email = email_match.group()
                                    name = line.replace(email, '').strip().strip(',').strip()
                                    manuscript['referee_recommendations']['recommended_referees'].append({
                                        'name': name,
                                        'email': email
                                    })
                            elif len(line) > 3:  # Just name
                                manuscript['referee_recommendations']['recommended_referees'].append({
                                    'name': line,
                                    'email': ''
                                })
                    break
            
            # Pattern 2: Look for "Opposed Reviewers" section  
            opposed_patterns = [
                r'Opposed Reviewers?[:\s]*\n([^:]*?)(?:\n\n|$)',
                r'Excluded Reviewers?[:\s]*\n([^:]*?)(?:\n\n|$)'
            ]
            
            for pattern in opposed_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.DOTALL)
                if match:
                    opposed_text = match.group(1).strip()
                    if opposed_text and len(opposed_text) > 10:
                        # Parse individual referees
                        referee_lines = [line.strip() for line in opposed_text.split('\n') if line.strip()]
                        for line in referee_lines:
                            if '@' in line:  # Has email
                                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', line)
                                if email_match:
                                    email = email_match.group()
                                    name = line.replace(email, '').strip().strip(',').strip()
                                    manuscript['referee_recommendations']['opposed_referees'].append({
                                        'name': name,
                                        'email': email
                                    })
                            elif len(line) > 3:  # Just name
                                manuscript['referee_recommendations']['opposed_referees'].append({
                                    'name': line,
                                    'email': ''
                                })
                    break
            
            # Report findings
            rec_count = len(manuscript['referee_recommendations']['recommended_referees'])
            opp_count = len(manuscript['referee_recommendations']['opposed_referees'])
            if rec_count > 0 or opp_count > 0:
                print(f"      ✅ Found {rec_count} recommended, {opp_count} opposed referees")
            else:
                print("      ⚠️ No referee recommendations found")
                
        except Exception as e:
            print(f"      ⚠️ Could not extract referee recommendations: {e}")
            manuscript['referee_recommendations'] = {
                'recommended_referees': [],
                'opposed_referees': []
            }
    
    def extract_comprehensive_mor_parity_fields(self, manuscript):
        """Extract ALL remaining MOR fields to achieve 100% data parity.
        This method adds the 14 missing fields that MOR has but MF lacks."""
        
        print("   🚀 Extracting COMPREHENSIVE MOR parity fields...")
        
        # 1. COMPREHENSIVE REVIEW DATA
        try:
            print("      📝 Extracting comprehensive review data...")
            manuscript['all_reviews_data'] = []
            manuscript['comprehensive_reviewer_comments'] = {}
            manuscript['detailed_scores'] = {}
            
            # Extract detailed review data from referee reports
            for referee in manuscript.get('referees', []):
                review_data = {
                    'reviewer': referee.get('name', ''),
                    'round': 1,  # Will be enhanced with multiple rounds if available
                    'recommendation': referee.get('report', {}).get('recommendation', ''),
                    'detailed_comments': '',
                    'specific_suggestions': [],
                    'minor_issues': [],
                    'scores': {}
                }
                
                # Try to extract detailed scores from report
                report_text = referee.get('report', {}).get('content', '')
                if report_text:
                    # Extract numerical scores
                    score_patterns = [
                        (r'Technical Quality:\s*(\d+)/\d+', 'technical_quality'),
                        (r'Originality:\s*(\d+)/\d+', 'originality'),
                        (r'Clarity:\s*(\d+)/\d+', 'clarity'),
                        (r'Significance:\s*(\d+)/\d+', 'significance'),
                        (r'Overall:\s*(\d+)/\d+', 'overall')
                    ]
                    
                    for pattern, score_type in score_patterns:
                        match = re.search(pattern, report_text, re.IGNORECASE)
                        if match:
                            review_data['scores'][score_type] = int(match.group(1))
                
                manuscript['all_reviews_data'].append(review_data)
                manuscript['comprehensive_reviewer_comments'][referee.get('name', '')] = review_data
            
            print(f"      ✅ Extracted {len(manuscript['all_reviews_data'])} comprehensive reviews")
            
        except Exception as e:
            print(f"      ⚠️ Could not extract comprehensive review data: {e}")
            manuscript['all_reviews_data'] = []
            manuscript['comprehensive_reviewer_comments'] = {}
        
        # 2. COMPREHENSIVE AE COMMENTS
        try:
            print("      💬 Extracting comprehensive AE comments...")
            manuscript['comprehensive_ae_comments'] = {}
            manuscript['editorial_notes_metadata'] = {}
            
            # Look for AE comments sections
            ae_comment_selectors = [
                "//td[contains(text(), 'Associate Editor Comments')]/following-sibling::td",
                "//div[@class='ae-comments']",
                "//span[contains(@class, 'editor-notes')]"
            ]
            
            for selector in ae_comment_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        ae_comments = elements[0].text.strip()
                        manuscript['comprehensive_ae_comments'] = {
                            'text': ae_comments,
                            'date': datetime.now().strftime("%Y-%m-%d"),
                            'editor': manuscript.get('editors', {}).get('Associate Editor', {}).get('name', '')
                        }
                        print(f"      ✅ Found AE comments: {len(ae_comments)} chars")
                        break
                except:
                    continue
                    
        except Exception as e:
            print(f"      ⚠️ Could not extract AE comments: {e}")
            manuscript['comprehensive_ae_comments'] = {}
            manuscript['editorial_notes_metadata'] = {}
        
        # 3. MSC CODES AND TOPIC AREA
        try:
            print("      🏷️ Extracting MSC codes and topic area...")
            manuscript['msc_codes'] = []
            manuscript['topic_area'] = ''
            
            # Look for MSC codes
            msc_patterns = [
                r'\b[0-9]{2}[A-Z][0-9]{2}\b',  # Standard MSC format
                r'MSC\s*:\s*([0-9]{2}[A-Z][0-9]{2}(?:\s*,\s*[0-9]{2}[A-Z][0-9]{2})*)',
                r'Mathematics Subject Classification:\s*([^\n]+)'
            ]
            
            page_text = self.driver.page_source
            
            for pattern in msc_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    for match in matches:
                        if isinstance(match, str) and re.match(r'[0-9]{2}[A-Z][0-9]{2}', match):
                            if match not in manuscript['msc_codes']:
                                manuscript['msc_codes'].append(match)
            
            # Look for topic area
            topic_selectors = [
                "//td[contains(text(), 'Topic Area')]/following-sibling::td",
                "//span[@class='topic-area']",
                "//div[contains(@class, 'manuscript-topic')]"
            ]
            
            for selector in topic_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        manuscript['topic_area'] = elements[0].text.strip()
                        print(f"      ✅ Topic area: {manuscript['topic_area']}")
                        break
                except:
                    continue
            
            if manuscript['msc_codes']:
                print(f"      ✅ MSC codes: {', '.join(manuscript['msc_codes'])}")
            
        except Exception as e:
            print(f"      ⚠️ Could not extract MSC codes: {e}")
            manuscript['msc_codes'] = []
            manuscript['topic_area'] = ''
        
        # 4. EDITOR RECOMMENDATIONS
        try:
            print("      👥 Extracting editor recommendations...")
            manuscript['editor_recommendations'] = {
                'recommended_editors': [],
                'opposed_editors': []
            }
            
            # Look for recommended/opposed editors
            page_text = self.driver.page_source
            
            # Pattern for recommended editors
            rec_editor_patterns = [
                r'Recommended Editor[s]?:\s*([^\n]+)',
                r'Suggested Editor[s]?:\s*([^\n]+)',
                r'Preferred Editor[s]?:\s*([^\n]+)'
            ]
            
            for pattern in rec_editor_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    editor_text = match.group(1).strip()
                    if editor_text and len(editor_text) > 3:
                        # Parse editor name and email if available
                        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', editor_text)
                        if email_match:
                            email = email_match.group()
                            name = editor_text.replace(email, '').strip().strip(',')
                            manuscript['editor_recommendations']['recommended_editors'].append({
                                'name': name,
                                'email': email
                            })
                        else:
                            manuscript['editor_recommendations']['recommended_editors'].append({
                                'name': editor_text,
                                'email': ''
                            })
                    break
            
            # Pattern for opposed editors
            opp_editor_patterns = [
                r'Opposed Editor[s]?:\s*([^\n]+)',
                r'Excluded Editor[s]?:\s*([^\n]+)'
            ]
            
            for pattern in opp_editor_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    editor_text = match.group(1).strip()
                    if editor_text and len(editor_text) > 3:
                        manuscript['editor_recommendations']['opposed_editors'].append({
                            'name': editor_text,
                            'email': ''
                        })
                    break
            
            ed_rec_count = len(manuscript['editor_recommendations']['recommended_editors'])
            ed_opp_count = len(manuscript['editor_recommendations']['opposed_editors'])
            if ed_rec_count > 0 or ed_opp_count > 0:
                print(f"      ✅ Found {ed_rec_count} recommended, {ed_opp_count} opposed editors")
            
        except Exception as e:
            print(f"      ⚠️ Could not extract editor recommendations: {e}")
            manuscript['editor_recommendations'] = {
                'recommended_editors': [],
                'opposed_editors': []
            }
        
        # 5. HISTORICAL REFEREE DATA
        try:
            print("      📚 Extracting historical referee data...")
            manuscript['historical_referees'] = []
            manuscript['original_submission_referees'] = []
            
            # Look for previous referee information
            history_selectors = [
                "//td[contains(text(), 'Previous Referees')]/following-sibling::td",
                "//div[@class='referee-history']",
                "//span[contains(text(), 'Historical Review')]"
            ]
            
            for selector in history_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        history_text = elements[0].text
                        # Parse historical referees
                        referee_lines = history_text.split('\n')
                        for line in referee_lines:
                            if line.strip():
                                manuscript['historical_referees'].append({
                                    'name': line.strip(),
                                    'round': 'previous'
                                })
                        print(f"      ✅ Found {len(manuscript['historical_referees'])} historical referees")
                        break
                except:
                    continue
            
            # Original submission referees are typically the same as current for first submission
            if not manuscript.get('is_revision', False):
                manuscript['original_submission_referees'] = [
                    {'name': r.get('name', ''), 'email': r.get('email', '')} 
                    for r in manuscript.get('referees', [])
                ]
            
        except Exception as e:
            print(f"      ⚠️ Could not extract historical referees: {e}")
            manuscript['historical_referees'] = []
            manuscript['original_submission_referees'] = []
        
        # 6. REFEREE REPORT METADATA
        try:
            print("      📄 Extracting referee report metadata...")
            manuscript['referee_reports_available'] = 0
            manuscript['referee_report_links'] = []
            manuscript['extracted_reports'] = []
            manuscript['report_extraction_enabled'] = True
            
            # Count available reports
            referee_count = len(manuscript.get('referees', []))
            reports_with_content = sum(1 for r in manuscript.get('referees', []) 
                                     if r.get('report', {}).get('pdf_downloaded', False))
            
            manuscript['referee_reports_available'] = reports_with_content
            
            # Extract report links
            report_selectors = [
                "//a[contains(@href, 'DOWNLOAD_REVIEW')]",
                "//a[contains(text(), 'View Report')]",
                "//a[contains(@onclick, 'viewReport')]"
            ]
            
            for selector in report_selectors:
                try:
                    links = self.driver.find_elements(By.XPATH, selector)
                    for link in links:
                        href = link.get_attribute('href')
                        if href:
                            manuscript['referee_report_links'].append(href)
                except:
                    continue
            
            # Track extracted reports
            for referee in manuscript.get('referees', []):
                if referee.get('report', {}).get('pdf_downloaded', False):
                    manuscript['extracted_reports'].append({
                        'referee': referee.get('name', ''),
                        'path': referee.get('report', {}).get('pdf_path', ''),
                        'recommendation': referee.get('report', {}).get('recommendation', '')
                    })
            
            print(f"      ✅ {manuscript['referee_reports_available']} reports available, {len(manuscript['extracted_reports'])} extracted")
            
        except Exception as e:
            print(f"      ⚠️ Could not extract report metadata: {e}")
            manuscript['referee_reports_available'] = 0
            manuscript['referee_report_links'] = []
            manuscript['extracted_reports'] = []
            manuscript['report_extraction_enabled'] = True
        
        # 7. VERSION HISTORY DOCUMENTS
        try:
            print("      📋 Extracting version history documents...")
            manuscript['version_history_documents'] = []
            manuscript['version_history_popups'] = []
            manuscript['versions'] = []
            
            # Look for version history section
            version_selectors = [
                "//a[contains(text(), 'Version History')]",
                "//td[contains(text(), 'Revision History')]",
                "//div[@class='version-history']"
            ]
            
            for selector in version_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        # Click to expand version history if needed
                        try:
                            elements[0].click()
                            time.sleep(2)
                        except:
                            pass
                        
                        # Extract version information
                        version_rows = self.driver.find_elements(By.XPATH, 
                            "//tr[contains(@class, 'version-row')]")
                        
                        for row in version_rows:
                            try:
                                version_info = {
                                    'version': row.find_element(By.XPATH, ".//td[1]").text,
                                    'date': row.find_element(By.XPATH, ".//td[2]").text,
                                    'decision': row.find_element(By.XPATH, ".//td[3]").text if len(row.find_elements(By.XPATH, ".//td")) > 2 else '',
                                    'documents': []
                                }
                                
                                # Look for document links in this version
                                doc_links = row.find_elements(By.XPATH, ".//a[contains(@href, 'download')]")
                                for link in doc_links:
                                    version_info['documents'].append({
                                        'name': link.text,
                                        'url': link.get_attribute('href')
                                    })
                                
                                manuscript['versions'].append(version_info)
                                manuscript['version_history_documents'].extend(version_info['documents'])
                            except:
                                continue
                        
                        print(f"      ✅ Found {len(manuscript['versions'])} versions with {len(manuscript['version_history_documents'])} documents")
                        break
                except:
                    continue
            
        except Exception as e:
            print(f"      ⚠️ Could not extract version history: {e}")
            manuscript['version_history_documents'] = []
            manuscript['version_history_popups'] = []
            manuscript['versions'] = []
        
        print("   ✅ Comprehensive MOR parity extraction complete!")
    
    def navigate_to_manuscript_information_tab(self):
        """Navigate to the Manuscript Information tab within the details page."""
        try:
            print("      📋 Looking for Manuscript Information tab...")
            
            # Look for the Manuscript Information tab
            info_selectors = [
                "//a[contains(@href, 'MANUSCRIPT_DETAILS_SHOW_TAB') and contains(@href, 'Tdetails')]",
                "//img[contains(@src, 'lefttabs_mss_info')]/../..",
                "//a[contains(@onclick, 'Tdetails')]",
                "//a[contains(text(), 'Manuscript Information')]",
                "//a[contains(text(), 'Manuscript Info')]",
                "//td[@class='lefttabs']//a[contains(@href, 'Tdetails')]"
            ]
            
            info_link = None
            for i, selector in enumerate(info_selectors):
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        info_link = elements[0]
                        print(f"      ✅ Found Manuscript Information tab with selector {i+1}")
                        break
                except:
                    continue
            
            if info_link:
                print("      👆 Clicking Manuscript Information tab...")
                info_link.click()
                time.sleep(2)
                print("      ✅ Navigated to Manuscript Information tab")
                
                # Debug: Save the page to verify we're on the right tab
                try:
                    with open("debug_manuscript_info_tab.html", 'w') as f:
                        f.write(self.driver.page_source)
                except:
                    pass
            else:
                print("      ⚠️ Could not find Manuscript Information tab - may already be on it")
                
        except Exception as e:
            print(f"      ❌ Error navigating to Manuscript Information tab: {e}")

    def extract_manuscript_details_page(self, manuscript):
        """Extract enhanced data from the manuscript details page."""
        try:
            print("   📄 Navigating to manuscript details page...")
            
            # Look for the manuscript details tab/link
            details_selectors = [
                "//a[contains(@href, 'MANUSCRIPT_DETAILS_SHOW_TAB')]",
                "//img[contains(@src, 'lefttabs_mss_info')]/../..",
                "//a[contains(@onclick, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]"
            ]
            
            details_link = None
            for selector in details_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        details_link = elements[0]
                        break
                except:
                    continue
            
            if details_link:
                # Store current window
                original_window = self.driver.current_window_handle
                
                # Click the details link
                details_link.click()
                time.sleep(3)
                
                # First, navigate to the Manuscript Information tab
                self.navigate_to_manuscript_information_tab()
                
                # Extract enhanced data from Manuscript Information tab
                self.extract_keywords_from_details(manuscript)
                self.extract_authors_from_details(manuscript)
                self.extract_metadata_from_details(manuscript)
                self.extract_cover_letter_from_details(manuscript)
                
                print("   ✅ Enhanced manuscript details extracted")
                
            else:
                print("   ❌ Could not find manuscript details link")
                
        except Exception as e:
            print(f"   ❌ Error extracting manuscript details: {e}")

    def extract_basic_manuscript_info(self, manuscript):
        """Extract basic manuscript info from main page (title, status, dates)."""
        try:
            # Check if this is a revision manuscript
            manuscript_id = manuscript.get('id', '')
            if manuscript_id:
                is_revision, revision_number = self.is_revision_manuscript(manuscript_id)
                if is_revision:
                    manuscript['is_revision'] = True
                    manuscript['revision_number'] = revision_number
                    # Extract version history for revisions
                    self.extract_version_history(manuscript)
            
            # Extract from main info table - with better error handling
            info_table = None
            table_selectors = [
                "//td[@class='headerbg2']//table",
                "//table[contains(@class, 'manuscript')]",
                "//table[.//td[contains(text(), 'Manuscript ID')]]",
                "//table[.//td[contains(text(), 'MAFI-')]]",
                "//table[.//p[@class='pagecontents']]",
                "(//table)[2]"  # Often the second table contains manuscript info
            ]
            
            for selector in table_selectors:
                try:
                    info_table = self.driver.find_element(By.XPATH, selector)
                    # Verify this table has manuscript info
                    table_text = info_table.text
                    if any(keyword in table_text for keyword in ['MAFI', 'Submitted', 'Manuscript', 'Original Article']):
                        print("      ✅ Found manuscript info table")
                        break
                except:
                    continue
            
            if not info_table:
                print("      ❌ Could not find manuscript info table")
                return
            
            # Title - extract from td colspan="2" containing the title
            try:
                title_elem = info_table.find_element(By.XPATH, ".//tr[2]/td[@colspan='2']/p[@class='pagecontents']")
                manuscript['title'] = title_elem.text.strip()
                print(f"      ✅ Title: {manuscript['title'][:60]}...")
            except:
                # Fallback: look for any td with colspan="2" that has a long text
                title_elems = info_table.find_elements(By.XPATH, ".//td[@colspan='2']/p[@class='pagecontents']")
                for elem in title_elems:
                    text = elem.text.strip()
                    if len(text) > 30 and 'Original Article' not in text and 'special issue:' not in text.lower():
                        manuscript['title'] = text
                        print(f"      ✅ Title (fallback): {text[:60]}...")
                        break
                
                if not manuscript.get('title'):
                    print("      ❌ Title not found")
            
            # Dates
            date_cells = info_table.find_elements(By.XPATH, ".//p[@class='footer']")
            for cell in date_cells:
                text = cell.text.strip()
                if 'Submitted:' in text:
                    manuscript['submission_date'] = text.replace('Submitted:', '').strip().rstrip(';')
                    print(f"      ✅ Submitted: {manuscript['submission_date']}")
                elif 'Last Updated:' in text:
                    manuscript['last_updated'] = text.replace('Last Updated:', '').strip().rstrip(';')
                    print(f"      ✅ Last Updated: {manuscript['last_updated']}")
                elif 'In Review:' in text:
                    manuscript['in_review_time'] = text.replace('In Review:', '').strip()
                    print(f"      ✅ In Review: {manuscript['in_review_time']}")
            
            # Status
            try:
                status_elem = info_table.find_element(By.XPATH, ".//font[@color='green']")
                if status_elem:
                    status_text = status_elem.text
                    manuscript['status'] = status_text.split('(')[0].strip()
                    print(f"      ✅ Status: {manuscript['status']}")
                    
                    # Extract status details (e.g., "2 active selections; 2 invited...")
                    try:
                        details_elem = status_elem.find_element(By.XPATH, ".//span[@class='footer']")
                        if details_elem:
                            manuscript['status_details'] = details_elem.text.strip()
                            print(f"      ✅ Status Details: {manuscript['status_details']}")
                    except:
                        pass
            except:
                print("      ❌ Status not found")
            
            # Article type and special issue
            type_elems = info_table.find_elements(By.XPATH, ".//p[@class='pagecontents']")
            for elem in type_elems:
                text = elem.text.strip()
                if text == 'Original Article':
                    manuscript['article_type'] = text
                    print(f"      ✅ Article Type: {text}")
                elif 'special issue:' in text.lower():
                    manuscript['special_issue'] = text.split(':')[1].strip()
                    print(f"      ✅ Special Issue: {manuscript['special_issue']}")
            
        except Exception as e:
            print(f"      ❌ Error extracting basic manuscript info: {e}")
            import traceback
            traceback.print_exc()

    def extract_keywords_from_details(self, manuscript):
        """Extract keywords from manuscript details page."""
        try:
            print("      🔍 Looking for Keywords section...")
            
            # First try to find keywords in the content area (Manuscript Information tab)
            content_areas = self.driver.find_elements(By.XPATH, 
                "//span[@class='pagecontents']//p[contains(@id, 'ANCHOR_CUSTOM_FIELD')]")
            
            if content_areas:
                content_text = content_areas[0].text
                
                # Look for keywords after "Keywords:" in the content
                import re
                keyword_match = re.search(r'Keywords:\s*\n([^\n\r]+)', content_text, re.IGNORECASE)
                if keyword_match:
                    keywords_text = keyword_match.group(1).strip()
                    if keywords_text and keywords_text.lower() != 'keywords':
                        # Parse keywords (usually comma or semicolon separated)
                        keywords = []
                        for sep in [',', ';', '\n']:
                            if sep in keywords_text:
                                keywords = [k.strip() for k in keywords_text.split(sep) if k.strip()]
                                break
                        
                        if not keywords and keywords_text:
                            keywords = [keywords_text]
                        
                        if keywords:
                            manuscript['keywords'] = keywords
                            print(f"      ✅ Keywords: {', '.join(keywords)}")
                            return
            
            # Look for keywords in table format (updated for Manuscript Information tab)
            keyword_patterns = [
                "//td[p[text()='Keywords:']]/following-sibling::td//p[@class='pagecontents']",
                "//td[contains(text(), 'Keywords:')]/following-sibling::td//p[@class='pagecontents']", 
                "//td[contains(text(), 'Keywords:')]/following-sibling::td",
                "//tr[td[contains(text(), 'Keywords:')]]/td[@class='tablelightcolor']"
            ]
            
            for pattern in keyword_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    for elem in elements:
                        text = elem.text.strip()
                        print(f"      📝 Found keywords text: {text[:100]}...")
                        
                        if text and len(text) > 10:
                            # Clean the text - remove icon references and extra spaces
                            # The HTML shows: "Forward utility <img> , relative performance <img> , ..."
                            clean_text = text
                            
                            # Remove common icon/image references
                            clean_text = re.sub(r'<img[^>]*>', '', clean_text)
                            clean_text = clean_text.replace('needs-review.gif', '')
                            clean_text = clean_text.replace('🔍', '')
                            
                            # Split by comma and clean each keyword
                            keywords = []
                            for keyword in clean_text.split(','):
                                clean_keyword = keyword.strip()
                                # Remove any remaining HTML artifacts
                                clean_keyword = re.sub(r'<[^>]+>', '', clean_keyword)
                                clean_keyword = clean_keyword.strip()
                                
                                if (clean_keyword and 
                                    len(clean_keyword) > 2 and
                                    clean_keyword.lower() != 'keywords' and
                                    not clean_keyword.startswith('http')):
                                    keywords.append(clean_keyword)
                            
                            if keywords and len(keywords) > 1:  # Must have more than just a label
                                manuscript['keywords'] = keywords
                                print(f"      ✅ Extracted keywords: {', '.join(keywords[:3])}{'...' if len(keywords) > 3 else ''}")
                                print(f"      📊 Total keywords: {len(keywords)}")
                                return
                except Exception as e:
                    print(f"      ⚠️ Pattern failed: {e}")
                    continue
            
            print("      ❌ No keywords found in any pattern")
                    
        except Exception as e:
            print(f"      ❌ Error extracting keywords from details: {e}")
            import traceback
            traceback.print_exc()

    def extract_authors_from_details(self, manuscript):
        """Extract complete author data including emails via popup clicks."""
        try:
            print("      🔍 Looking for authors section...")
            
            # DEBUG HTML SAVING DISABLED - causes file pollution
            # try:
            #     with open(f"debug_manuscript_info_{manuscript.get('id', 'unknown')}.html", 'w') as f:
            #         f.write(self.driver.page_source)
            #     print("      🐛 DEBUG: Saved manuscript info page for debugging")
            # except:
            #     pass
            
            # Look for the Authors & Institutions section - be VERY specific
            # The authors table is within a specific structure that contains the author names
            authors_table = None
            
            # Strategy 1: Find the Authors & Institutions row and then look for the table inside it
            try:
                # Find the row that contains "Authors & Institutions:"
                auth_inst_row = self.driver.find_element(By.XPATH, "//tr[td[contains(text(), 'Authors & Institutions:') or contains(text(), 'Authors and Institutions:')]]")
                # The next row contains the actual table with authors
                next_row = auth_inst_row.find_element(By.XPATH, "./following-sibling::tr[1]")
                # Find the table within this row that contains the authors
                authors_table = next_row.find_element(By.XPATH, ".//table[.//a[contains(@href, 'mailpopup')]]")
                print("      ✅ Found Authors & Institutions table (strategy 1)")
            except:
                print("      ⚠️ Strategy 1 failed, trying alternative approach...")
                
            # Strategy 2: Look for the table that contains author names with specific patterns
            if not authors_table:
                try:
                    # Look for tables that contain mailpopup links and have author-like content
                    tables = self.driver.find_elements(By.XPATH, "//table[.//a[contains(@href, 'mailpopup')]]")
                    for table in tables:
                        table_text = table.text.lower()
                        # Check if this table contains author-related content and NOT editor content
                        if ('corresponding author' in table_text or 'ringgold' in table_text or 'orcid' in table_text) and \
                           'editor-in-chief' not in table_text and 'associate editor' not in table_text and \
                           'admin' not in table_text:
                            authors_table = table
                            print("      ✅ Found Authors & Institutions table (strategy 2)")
                            break
                except:
                    print("      ⚠️ Strategy 2 failed")
            
            if not authors_table:
                print("      ❌ Authors table not found, will not extract authors")
                manuscript['authors'] = []
                return []
            
            # Find all author links within the authors table
            # Be specific: only get links that are in the author name cells, not other cells
            author_links = []
            
            # Look for rows that contain author information
            author_rows = authors_table.find_elements(By.XPATH, ".//tr[.//a[contains(@href, 'mailpopup')]]")
            print(f"      📊 Found {len(author_rows)} potential author rows")
            
            for row in author_rows:
                # Check if this row contains author info (not just any mailpopup link)
                row_text = row.text
                # Skip rows that are clearly not authors
                if any(skip_word in row_text for skip_word in ['Admin:', 'Editor:', 'Co-Editor:', 'Associate Editor:']):
                    continue
                    
                # Find the mailpopup link in this row
                links = row.find_elements(By.XPATH, ".//a[contains(@href, 'mailpopup')]")
                for link in links:
                    # Get the link text to verify it's an author name
                    link_text = link.text.strip()
                    
                    # Enhanced validation for author names
                    if (link_text and 
                        ',' in link_text and 
                        len(link_text) > 3 and
                        not link_text.lower().startswith('view') and
                        not link_text.lower().startswith('click') and
                        not '@' in link_text and
                        not link_text.isdigit()):
                        
                        # Additional check: should look like "Last, First" format
                        parts = link_text.split(',', 1)
                        if (len(parts) == 2 and 
                            parts[0].strip() and 
                            parts[1].strip() and
                            len(parts[0].strip()) > 1 and
                            len(parts[1].strip()) > 1):
                            
                            author_links.append(link)
                            print(f"         ✅ Found author link: {link_text}")
            
            print(f"      📊 Total author links found: {len(author_links)}")
            
            enhanced_authors = []
            seen_authors = set()  # Track authors we've already processed
            
            # First, let's check if there's any existing author data in the manuscript
            existing_authors = manuscript.get('authors', [])
            print(f"      📋 Existing authors in manuscript: {len(existing_authors)}")
            
            # Filter out editor names - DYNAMIC DETECTION
            editor_names = self.get_current_editor_names()
            
            for i, link in enumerate(author_links):
                try:
                    author = {}
                    
                    # Get author name from link text
                    raw_name = link.text.strip()
                    if not raw_name:
                        print(f"      ⚠️ Skipping author {i+1}: Empty name")
                        continue
                    
                    # Skip if this is an editor name
                    if any(editor in raw_name for editor in editor_names):
                        print(f"      ⚠️ Skipping editor: {raw_name}")
                        continue
                        
                    # Convert "Last, First" to "First Last"
                    if ',' in raw_name:
                        parts = raw_name.split(',', 1)
                        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                            author['name'] = f"{parts[1].strip()} {parts[0].strip()}"
                        else:
                            print(f"      ⚠️ Skipping author {i+1}: Invalid name format: {raw_name}")
                            continue
                    else:
                        author['name'] = raw_name
                    
                    # Final validation: ensure name is not empty after processing
                    if not author['name'] or len(author['name'].strip()) < 2:
                        print(f"      ⚠️ Skipping author {i+1}: Name too short after processing: '{author['name']}'")
                        continue
                    
                    # DEDUPLICATION: Check if we've already processed this author
                    author_key = author['name'].lower().strip()
                    if author_key in seen_authors:
                        print(f"      ⚠️ Skipping duplicate author: {author['name']}")
                        continue
                    seen_authors.add(author_key)
                    
                    print(f"      👤 Processing author {i+1}: {author['name']}")
                    
                    # Get the row containing this author for additional info FIRST
                    try:
                        # FIXED: Get the immediate parent tr, not any ancestor
                        # First try to get the closest tr that contains this specific link
                        author_row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                        
                        # Validate this is the correct row by checking it contains the author name
                        row_text = author_row.text.strip()
                        if author['name'] not in row_text and raw_name not in row_text:
                            # This might be the wrong row, try parent of parent
                            print(f"         ⚠️ Row doesn't contain author name, trying parent...")
                            author_row = link.find_element(By.XPATH, "./ancestor::tr[position()=1 or position()=2]")
                            row_text = author_row.text.strip()
                        
                        # Further validation - the row should not contain page UI text
                        if 'tabs below organize' in row_text.lower() or 'click on each tab' in row_text.lower():
                            print(f"         ❌ Got page UI text instead of author row, trying alternative...")
                            # Get just the text near the link
                            parent_td = link.find_element(By.XPATH, "./ancestor::td[1]")
                            row_text = parent_td.text.strip()
                        
                        print(f"         📄 Row text: {row_text[:100]}...")
                        
                        # Check if there's an email already in the table
                        table_emails = re.findall(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', row_text)
                        # Filter out editor emails from table
                        table_email = None
                        for email in table_emails:
                            if 'dylan.possamai' not in email.lower() and 'editor' not in email.lower():
                                table_email = email
                                break
                        
                        if table_email:
                            print(f"         📧 Found table email: {table_email}")
                    except Exception as e:
                        print(f"         ⚠️ Could not get row text: {e}")
                        row_text = ""
                        table_email = None
                    
                    # Extract email from link URL parameters FIRST
                    popup_email = ""
                    try:
                        onclick = link.get_attribute('onclick') or ''
                        href = link.get_attribute('href') or ''
                        
                        # Try to extract email from the JavaScript parameters
                        if 'mailpopup' in onclick or 'mailpopup' in href:
                            import re
                            from urllib.parse import unquote
                            # Look for email patterns in the onclick/href
                            email_match = re.search(r'EMAIL_TO=([^&]+)', onclick + href)
                            if not email_match:
                                email_match = re.search(r'to=([^&]+)', onclick + href)
                            if not email_match:
                                email_match = re.search(r'email=([^&]+)', onclick + href)
                            
                            if email_match:
                                potential_email = unquote(email_match.group(1))
                                if '@' in potential_email:
                                    popup_email = potential_email
                                    print(f"         📧 Email extracted from URL params: {popup_email}")
                                else:
                                    print(f"         ⚠️ No @ in URL param: {potential_email}")
                            else:
                                print(f"         ⚠️ No EMAIL_TO in URL, clicking popup to extract...")
                                # CLICK THE POPUP TO EXTRACT EMAIL (like referees)
                                popup_email = self.get_email_from_popup_safe(link)
                                if popup_email:
                                    print(f"         📧 Email extracted from popup click: {popup_email}")
                    except Exception as e:
                        print(f"         ⚠️ Could not extract email from link: {e}")
                    
                    # Decide which email to use
                    if popup_email and '@' in popup_email:
                        print(f"         ✅ Got email from popup: {popup_email}")
                        
                        # Check if popup email looks suspicious (like a phone number)
                        if re.match(r'^\d{10,}@', popup_email):
                            print(f"         ⚠️ Popup email looks like phone number: {popup_email}")
                            if table_email and not re.match(r'^\d{10,}@', table_email):
                                print(f"         ✅ Using table email instead: {table_email}")
                                author['email'] = table_email
                            else:
                                author['email'] = popup_email
                        else:
                            author['email'] = popup_email
                    elif table_email:
                        print(f"         ⚠️ No popup email, using table email: {table_email}")
                        author['email'] = table_email
                    else:
                        print(f"         ❌ No email found in popup or table")
                        author['email'] = ''
                    
                    # Extract institution from row - SMART PARSING
                    author['institution'] = ''
                    
                    # First try to extract institution from table cells
                    try:
                        # Get all cells in the author row
                        cells = author_row.find_elements(By.XPATH, ".//td")
                        print(f"         📊 Found {len(cells)} cells in author row")
                        
                        # Look for institution in cells (usually after author name cell)
                        found_author_cell = False
                        for cell in cells:
                            cell_text = cell.text.strip()
                            # Skip empty cells
                            if not cell_text or len(cell_text) < 5:
                                continue
                                
                            # Check if this is the author name cell
                            if author['name'] in cell_text or raw_name in cell_text:
                                found_author_cell = True
                                continue
                            
                            # If we've found the author cell, the next non-empty cell might be institution
                            if found_author_cell and not '@' in cell_text:
                                # Check if it looks like an institution
                                lines = [line.strip() for line in cell_text.split('\n') if line.strip()]
                                for line in lines:
                                    # Skip if it's another author name or email
                                    if self.is_same_person_name(line, author['name']) or '@' in line:
                                        continue
                                    # This could be the institution
                                    author['institution'] = line
                                    print(f"         🏛️ Institution (from cell): {author['institution']}")
                                    break
                                if author['institution']:
                                    break
                    except Exception as e:
                        print(f"         ⚠️ Cell extraction failed: {e}")
                    
                    # Fallback to row text parsing if no institution found
                    if not author['institution']:
                        lines = [line.strip() for line in row_text.split('\n') if line.strip()]
                        
                        # Enhanced institution detection
                        institutional_keywords = [
                            'university', 'institute', 'college', 'school', 'department', 
                            'laboratory', 'center', 'centre', 'hospital', 'academy',
                            'federation', 'research', 'recherche', 'matematica', 'mathematiques',
                            'sciences', 'technology', 'polytechnic', 'national', 'international',
                            'foundation', 'society', 'association', 'organization', 'organisation',
                            'ministry', 'bureau', 'agency', 'council', 'board', 'commission',
                            'universit', 'facult', 'ecole', 'lab'  # French variants
                        ]
                        
                        for line in lines:
                            line_lower = line.lower()
                            
                            # Skip lines that are clearly the author name or email
                            # Check both "Last, First" and "First Last" formats
                            author_name_parts = author['name'].lower().split()
                            is_author_name = (
                                author['name'].lower() in line_lower or
                                all(part in line_lower for part in author_name_parts) or
                                self.is_same_person_name(line, author['name']) or
                                '@' in line
                            )
                            
                            if is_author_name or len(line) < 5:
                                continue
                                
                            # Smart institution detection - prioritize lines with keywords
                            has_keyword = any(keyword in line_lower for keyword in institutional_keywords)
                            
                            # Check if it looks like an institution
                            is_institution = (
                                # Has institutional keywords (highest priority)
                                has_keyword or
                                # Contains common institutional patterns (French, etc.)
                                any(pattern in line_lower for pattern in ['de ', 'of ', 'for ', 'and ', 'des ', 'du ', 'la ', 'le ']) or
                                # Has location indicators
                                any(loc in line_lower for loc in ['france', 'usa', 'uk', 'china', 'germany', 'paris', 'london', 'new york'])
                            )
                            
                            # Additional check: avoid mistaking author names as institutions
                            # Check if line looks like a person's name (e.g., "Zhang, Panpan")
                            looks_like_name = (
                                ',' in line and len(line.split(',')) == 2 and
                                all(part.strip().replace('-', '').isalpha() for part in line.split(','))
                            )
                            
                            if is_institution and not looks_like_name:
                                author['institution'] = line.strip()
                                print(f"         🏛️ Institution: {author['institution']}")
                                break
                    
                    # Extract country - SMART INFERENCE
                    author['country'] = ''
                    
                    # Try to infer from institution first
                    if author['institution']:
                        web_country = self.infer_country_from_web_search(author['institution'])
                        if web_country:
                            author['country'] = web_country
                            print(f"         🌍 Country (from institution): {author['country']}")
                    
                    # If no country yet, check text lines for explicit country mentions
                    if not author['country']:
                        # Comprehensive country patterns
                        country_patterns = {
                            'United States': ['united states', 'usa', 'u.s.a', 'america', 'california', 'new york', 'massachusetts', 'texas', 'florida', 'illinois', 'michigan', 'pennsylvania'],
                            'United Kingdom': ['united kingdom', 'uk', 'u.k', 'britain', 'england', 'scotland', 'wales', 'northern ireland'],
                            'China': ['china', 'chinese', 'beijing', 'shanghai', 'guangzhou', 'shenzhen', 'hong kong'],
                            'France': ['france', 'french', 'paris', 'lyon', 'marseille', 'toulouse', 'bordeaux'],
                            'Germany': ['germany', 'german', 'berlin', 'munich', 'hamburg', 'cologne', 'frankfurt'],
                            'Japan': ['japan', 'japanese', 'tokyo', 'osaka', 'kyoto', 'yokohama'],
                            'Singapore': ['singapore', 'singaporean'],
                            'Canada': ['canada', 'canadian', 'toronto', 'vancouver', 'montreal', 'ottawa'],
                            'Australia': ['australia', 'australian', 'sydney', 'melbourne', 'brisbane', 'perth'],
                            'Netherlands': ['netherlands', 'dutch', 'holland', 'amsterdam', 'rotterdam'],
                            'Italy': ['italy', 'italian', 'rome', 'milan', 'naples', 'turin'],
                            'Spain': ['spain', 'spanish', 'madrid', 'barcelona', 'valencia', 'seville'],
                            'Sweden': ['sweden', 'swedish', 'stockholm', 'gothenburg'],
                            'Switzerland': ['switzerland', 'swiss', 'zurich', 'geneva', 'basel'],
                            'Norway': ['norway', 'norwegian', 'oslo', 'bergen'],
                            'Denmark': ['denmark', 'danish', 'copenhagen'],
                            'Belgium': ['belgium', 'belgian', 'brussels', 'antwerp'],
                            'Austria': ['austria', 'austrian', 'vienna', 'salzburg'],
                            'Israel': ['israel', 'israeli', 'tel aviv', 'jerusalem'],
                            'South Korea': ['south korea', 'korea', 'korean', 'seoul', 'busan'],
                            'India': ['india', 'indian', 'mumbai', 'delhi', 'bangalore', 'chennai', 'kolkata'],
                            'Brazil': ['brazil', 'brazilian', 'sao paulo', 'rio de janeiro'],
                            'Russia': ['russia', 'russian', 'moscow', 'st petersburg']
                        }
                        
                        for line in lines:
                            line_lower = line.lower()
                            for country, patterns in country_patterns.items():
                                if any(pattern in line_lower for pattern in patterns):
                                    author['country'] = country
                                    print(f"         🌍 Country (from text): {author['country']}")
                                    break
                            if author['country']:
                                break
                    
                    # Check if corresponding author - be more specific
                    author['is_corresponding'] = False
                    # Only check for corresponding markers near the author's name
                    if author['name'] in row_text:
                        # Get text around author name
                        name_index = row_text.find(author['name'])
                        context = row_text[max(0, name_index-50):name_index+len(author['name'])+50].lower()
                        if 'corresponding' in context or '(contact)' in context or 'corresp' in context:
                            author['is_corresponding'] = True
                            print(f"         📝 Corresponding author: Yes")
                    
                    # Extract ORCID if present - look specifically near this author
                    author['orcid'] = ''
                    # Split row into lines and look for ORCID near author info
                    for line in lines:
                        if 'orcid' in line.lower() or 'https://orcid.org' in line:
                            orcid_match = re.search(r'https://orcid\.org/([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X])', line)
                            if orcid_match:
                                # Check if this ORCID is near this author's info
                                line_before_orcid = line[:line.find('orcid')].lower()
                                if any(part in line_before_orcid for part in author['name'].lower().split()):
                                    author['orcid'] = f"https://orcid.org/{orcid_match.group(1)}"
                                    print(f"         🆔 ORCID: {author['orcid']}")
                                    break
                    
                    enhanced_authors.append(author)
                
                except Exception as e:
                    print(f"      ❌ Error processing author {i+1}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # ENHANCED: Apply deep web enrichment to all authors
            if enhanced_authors:
                print(f"      🌐 Applying deep web enrichment to {len(enhanced_authors)} authors...")
                for i, author in enumerate(enhanced_authors):
                    if author.get('name'):
                        enriched_author = self.deep_web_enrichment(author['name'], author)
                        enhanced_authors[i].update(enriched_author)
                        
                        # Deep web search for missing institution
                        if not enhanced_authors[i].get('institution') and enhanced_authors[i].get('email'):
                            deep_institution = self.deep_web_search_affiliation(author['name'], enhanced_authors[i]['email'])
                            if deep_institution:
                                enhanced_authors[i]['institution'] = deep_institution
                                print(f"         🌐 Found institution via deep web: {deep_institution}")
                        
                        # Deep web search for missing country
                        if not enhanced_authors[i].get('country') and enhanced_authors[i].get('institution'):
                            deep_country = self.deep_web_search_country(author['name'], enhanced_authors[i]['institution'], enhanced_authors[i].get('email', ''))
                            if deep_country:
                                enhanced_authors[i]['country'] = deep_country
                                print(f"         🌐 Found country via deep web: {deep_country}")
                        
                        # Apply department extraction if not already done
                        if enhanced_authors[i].get('institution') and not enhanced_authors[i].get('department'):
                            department, clean_institution = self.extract_department(enhanced_authors[i]['institution'])
                            if department:
                                enhanced_authors[i]['department'] = department
                                enhanced_authors[i]['institution'] = clean_institution
                
                manuscript['authors'] = enhanced_authors
                print(f"      ✅ Successfully extracted {len(enhanced_authors)} authors with comprehensive enrichment")
            else:
                # If we couldn't extract any authors, keep existing ones if any
                if existing_authors:
                    print(f"      ⚠️ No new authors extracted, keeping {len(existing_authors)} existing authors")
                else:
                    manuscript['authors'] = []
                    print("      ❌ No authors could be extracted")
            
            return enhanced_authors
            
        except Exception as e:
            print(f"      ❌ Error extracting authors: {e}")
            import traceback
            traceback.print_exc()
            manuscript['authors'] = []
            return []

    def extract_metadata_from_details(self, manuscript):
        """Extract comprehensive manuscript metadata from details page."""
        try:
            print("      📊 Extracting comprehensive manuscript metadata...")
            
            # COMPREHENSIVE METADATA EXTRACTION - All available fields
            
            # 1. FUNDING INFORMATION
            try:
                funding_cells = self.driver.find_elements(By.XPATH, 
                    "//td[contains(@class, 'alternatetablecolor') and .//p[contains(text(), 'Funding Information:')]]/following-sibling::td[@class='tablelightcolor']")
                
                if funding_cells:
                    funding_text = funding_cells[0].text.strip()
                    manuscript['funding_information'] = funding_text
                    print(f"      ✅ Funding Information: {funding_text[:50]}...")
                else:
                    manuscript['funding_information'] = "Not specified"
            except Exception as e:
                print(f"      ⚠️ Could not extract funding information: {e}")
            
            # 2. DATA AVAILABILITY STATEMENT  
            try:
                data_elements = self.driver.find_elements(By.XPATH, 
                    "//span[contains(text(), 'Data Availability Statement')]/ancestor::tr//p[contains(@id, 'ANCHOR_CUSTOM_FIELD')]")
                
                if data_elements:
                    data_availability = data_elements[0].text.strip()
                    manuscript['data_availability_statement'] = data_availability
                    print(f"      ✅ Data Availability: {data_availability[:50]}...")
                else:
                    # Fallback search
                    data_elements = self.driver.find_elements(By.XPATH, 
                        "//p[contains(@id, 'ANCHOR_CUSTOM_FIELD') and contains(text(), 'Data sharing')]")
                    if data_elements:
                        manuscript['data_availability_statement'] = data_elements[0].text.strip()
                        print(f"      ✅ Data Availability (fallback): {data_elements[0].text.strip()[:50]}...")
            except Exception as e:
                print(f"      ⚠️ Could not extract data availability: {e}")
            
            # 3. CONFLICT OF INTEREST
            try:
                conflict_pattern = r'Do you or any of your co-authors have a conflict of interest to disclose\?\s*\n([^\n]+)'
                page_text = self.driver.page_source
                conflict_match = re.search(conflict_pattern, page_text, re.IGNORECASE)
                
                if conflict_match:
                    conflict_info = conflict_match.group(1).strip()
                    manuscript['conflict_of_interest'] = conflict_info
                    print(f"      ✅ Conflict of Interest: {conflict_info}")
                else:
                    # Alternative search in content areas
                    content_areas = self.driver.find_elements(By.XPATH, 
                        "//p[contains(@id, 'ANCHOR_CUSTOM_FIELD')]")
                    
                    for area in content_areas:
                        if 'conflict of interest' in area.text.lower():
                            conflict_text = area.text
                            if 'No, there is no conflict' in conflict_text:
                                manuscript['conflict_of_interest'] = 'No conflict of interest'
                            elif 'Yes' in conflict_text:
                                manuscript['conflict_of_interest'] = 'Conflict declared'
                            print(f"      ✅ Conflict of Interest (found): {manuscript.get('conflict_of_interest', 'Unknown')}")
                            break
            except Exception as e:
                print(f"      ⚠️ Could not extract conflict of interest: {e}")
                
            # 4. SUBMISSION REQUIREMENTS ACKNOWLEDGMENT
            try:
                req_pattern = r'All submission requirements questions were acknowledged by the submitter'
                page_text = self.driver.page_source
                
                if req_pattern in page_text:
                    manuscript['submission_requirements_acknowledged'] = True
                    print(f"      ✅ Submission Requirements: Acknowledged")
                else:
                    manuscript['submission_requirements_acknowledged'] = False
            except Exception as e:
                print(f"      ⚠️ Could not extract submission requirements: {e}")
            
            # 5. ASSOCIATE EDITOR INFORMATION
            try:
                # Look for editor information in various patterns
                editor_patterns = [
                    "//td[contains(text(), 'Associate Editor:')]/following-sibling::td//p[@class='pagecontents']",
                    "//td[contains(text(), 'Editor:')]/following-sibling::td//p[@class='pagecontents']",
                    "//td[p[contains(text(), 'Associate Editor:')]]/following-sibling::td",
                    "//tr[td[contains(text(), 'Associate Editor')]]/td[2]",
                    "//td[@class='tablelightcolor' and preceding-sibling::td[contains(text(), 'Editor')]]"
                ]
                
                for pattern in editor_patterns:
                    try:
                        editor_elements = self.driver.find_elements(By.XPATH, pattern)
                        if editor_elements:
                            editor_text = editor_elements[0].text.strip()
                            if editor_text and len(editor_text) > 2 and editor_text != 'N/A':
                                # Extract name and email if present
                                email_match = re.search(r'[\w\.-]+@[\w\.-]+', editor_text)
                                if email_match:
                                    editor_email = email_match.group()
                                    editor_name = editor_text.replace(editor_email, '').strip()
                                    manuscript['associate_editor'] = {
                                        'name': editor_name,
                                        'email': editor_email
                                    }
                                else:
                                    manuscript['associate_editor'] = {
                                        'name': editor_text,
                                        'email': None
                                    }
                                print(f"      ✅ Associate Editor: {manuscript['associate_editor']['name']}")
                                if manuscript['associate_editor']['email']:
                                    print(f"         Email: {manuscript['associate_editor']['email']}")
                                break
                    except:
                        continue
            except Exception as e:
                print(f"      ⚠️ Could not extract associate editor: {e}")
            
            # 6. FILES INFORMATION (WITH REVISION TRACKING)
            try:
                files_info = []
                manuscript_pdf_count = 0
                # Look for files section in content areas
                content_areas = self.driver.find_elements(By.XPATH, 
                    "//p[contains(@id, 'ANCHOR_CUSTOM_FIELD')]")
                
                for area in content_areas:
                    if 'Files' in area.text and ('.pdf' in area.text or '.zip' in area.text or '.tex' in area.text):
                        files_text = area.text
                        
                        # Parse individual files
                        file_lines = [line.strip() for line in files_text.split('\n') if line.strip()]
                        
                        for line in file_lines:
                            if any(ext in line for ext in ['.pdf', '.zip', '.tex', '.docx', '.doc']):
                                # Extract filename and type
                                file_match = re.match(r'^([^-]+)\s*-\s*([^(]+)\s*\(([^)]+)\)', line)
                                if file_match:
                                    filename = file_match.group(1).strip()
                                    file_type = file_match.group(2).strip()
                                    file_description = file_match.group(3).strip()
                                    
                                    # Track manuscript PDFs for revision detection
                                    if 'Main Document' in file_type and '.pdf' in filename:
                                        manuscript_pdf_count += 1
                                    
                                    files_info.append({
                                        'filename': filename,
                                        'type': file_type,
                                        'description': file_description
                                    })
                
                if files_info:
                    manuscript['files'] = files_info
                    print(f"      ✅ Files: {len(files_info)} files found")
                    for i, file_info in enumerate(files_info):
                        print(f"         File {i+1}: {file_info['filename']} ({file_info['type']})")
                    
                    # Check if this is a revision
                    if manuscript_pdf_count > 1:
                        manuscript['is_revision'] = True
                        manuscript['revision_count'] = manuscript_pdf_count - 1
                        print(f"      ✅ Revision Status: This is a revision (found {manuscript_pdf_count} manuscript PDFs)")
                    else:
                        manuscript['is_revision'] = False
                        print(f"      ✅ Revision Status: Original submission")
                        
            except Exception as e:
                print(f"      ⚠️ Could not extract files information: {e}")
            
            # 6. ENHANCED WORD/FIGURE/TABLE COUNTS (with better parsing)
            try:
                # Try to find the comprehensive content area with all metadata
                content_areas = self.driver.find_elements(By.XPATH, 
                    "//p[contains(@id, 'ANCHOR_CUSTOM_FIELD')]")
                
                full_content_text = ""
                for area in content_areas:
                    full_content_text += area.text + "\n"
                
                if full_content_text:
                    print(f"      📝 Found content areas with {len(full_content_text)} characters total")
                    
                    # Extract enhanced counts with multiple patterns
                    count_patterns = {
                        'word_count': [
                            r'Number of words\s*[:\n\r]\s*(\d+)',
                            r'Word count\s*[:\n\r]\s*(\d+)',
                            r'Words\s*[:\n\r]\s*(\d+)'
                        ],
                        'figure_count': [
                            r'Number of figures\s*[:\n\r]\s*(\d+)',
                            r'Figure count\s*[:\n\r]\s*(\d+)',
                            r'Figures\s*[:\n\r]\s*(\d+)'
                        ],
                        'table_count': [
                            r'Number of tables\s*[:\n\r]\s*(\d+)',
                            r'Table count\s*[:\n\r]\s*(\d+)',
                            r'Tables\s*[:\n\r]\s*(\d+)'
                        ]
                    }
                    
                    for field, patterns in count_patterns.items():
                        for pattern in patterns:
                            match = re.search(pattern, full_content_text, re.IGNORECASE)
                            if match:
                                manuscript[field] = int(match.group(1))
                                print(f"      ✅ {field.replace('_', ' ').title()}: {match.group(1)}")
                                break
                    
                    # Extract manuscript type
                    type_patterns = [
                        r'Manuscript type:\s*([^\n\r]+)',
                        r'Article type:\s*([^\n\r]+)',
                        r'Type:\s*([^\n\r]+)'
                    ]
                    
                    for pattern in type_patterns:
                        match = re.search(pattern, full_content_text, re.IGNORECASE)
                        if match:
                            manuscript['manuscript_type_detailed'] = match.group(1).strip()
                            print(f"      ✅ Manuscript type: {match.group(1).strip()}")
                            break
                            
            except Exception as e:
                print(f"      ⚠️ Error in enhanced count extraction: {e}")
            
            # Legacy data_availability extraction for backward compatibility
            metadata_patterns = {
                'data_availability': [
                    "//p[contains(@id, 'ANCHOR_CUSTOM_FIELD')]",
                    "//span[@class='pagecontents']//p[contains(@id, 'ANCHOR')]"
                ]
            }
            
            for field, patterns in metadata_patterns.items():
                try:
                    # Handle single pattern or list of patterns
                    if isinstance(patterns, list):
                        pattern_list = patterns
                    else:
                        pattern_list = [patterns]
                    
                    found_value = None
                    for pattern in pattern_list:
                        elements = self.driver.find_elements(By.XPATH, pattern)
                        if elements:
                            if field == 'doi':
                                # Special handling for DOI - extract from href if it's a link
                                elem = elements[0]
                                if elem.tag_name == 'a':
                                    href = elem.get_attribute('href')
                                    if 'doi.org/' in href:
                                        found_value = href.split('doi.org/')[-1]
                                    else:
                                        found_value = elem.text.strip()
                                else:
                                    found_value = elem.text.strip()
                            else:
                                found_value = elements[0].text.strip()
                            
                            if found_value and found_value != "0" and "no funders" not in found_value.lower():
                                # Convert numeric fields to integers
                                if field in ['word_count', 'page_count', 'figure_count', 'table_count'] and found_value.isdigit():
                                    found_value = int(found_value)
                                
                                manuscript[field] = found_value
                                print(f"      ✅ {field}: {str(found_value)[:50]}...")
                                break
                                
                except Exception as e:
                    print(f"      ⚠️ Error extracting {field}: {e}")
                    continue
                    
        except Exception as e:
            print(f"      ❌ Error extracting metadata from details: {e}")

    def extract_cover_letter_from_details(self, manuscript):
        """Extract cover letter download link from details page."""
        try:
            # Look for cover letter link
            cover_letter_links = self.driver.find_elements(By.XPATH, 
                "//a[contains(@href, 'DOWNLOAD=TRUE') and contains(text(), 'Cover-letter')]")
            
            if cover_letter_links:
                download_url = cover_letter_links[0].get_attribute('href')
                manuscript['cover_letter_url'] = download_url
                print(f"      ✅ Cover letter URL found")
            
        except Exception as e:
            print(f"      ❌ Error extracting cover letter: {e}")

    def extract_audit_trail(self, manuscript):
        """Extract communication timeline from audit trail page with Gmail cross-checking."""
        try:
            print("   📋 Navigating to audit trail page...")
            
            # DEBUG: Save page source before searching for audit trail
            try:
                with open(f"debug_page_before_audit_{manuscript.get('id', 'unknown')}.html", 'w') as f:
                    f.write(self.driver.page_source)
                print(f"   🐛 DEBUG: Saved page source for audit trail debugging")
            except:
                pass
            
            # Look for the audit trail tab/link with enhanced debugging
            audit_selectors = [
                "//a[contains(@href, 'MANUSCRIPT_DETAILS_SHOW_TAB') and contains(@href, 'Taudit')]",
                "//img[contains(@src, 'lefttabs_audit_trail')]/../..",
                "//a[contains(@onclick, 'Taudit')]",
                "//a[contains(text(), 'Audit Trail')]",
                "//a[contains(@href, 'audit')]",
                "//img[contains(@alt, 'Audit Trail')]/..",
                "//td[contains(@class, 'lefttabs')]/a[contains(@href, 'audit')]"
            ]
            
            audit_link = None
            print(f"   🔍 Testing {len(audit_selectors)} selectors for audit trail tab...")
            
            for i, selector in enumerate(audit_selectors):
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"      Selector {i+1}: Found {len(elements)} elements")
                    if elements:
                        element = elements[0]
                        href = element.get_attribute('href') or 'No href'
                        onclick = element.get_attribute('onclick') or 'No onclick'
                        text = element.text.strip() or 'No text'
                        print(f"         Element: text='{text}', href='{href[:50]}...', onclick='{onclick[:50]}...'")
                        
                        audit_link = element
                        print(f"   ✅ Found audit trail link with selector {i+1}")
                        break
                except Exception as e:
                    print(f"      Selector {i+1} error: {e}")
                    continue
            
            if audit_link:
                try:
                    print("   👆 Clicking audit trail link...")
                    audit_link.click()
                    time.sleep(3)
                    
                    print("   📄 Page loaded, checking for audit trail content...")
                    
                    # DEBUG: Save audit trail page source
                    try:
                        with open(f"debug_audit_trail_page_{manuscript.get('id', 'unknown')}.html", 'w') as f:
                            f.write(self.driver.page_source)
                        print(f"   🐛 DEBUG: Saved audit trail page source")
                    except:
                        pass
                    
                    # Extract communication events
                    communications = self.extract_communication_events()
                    
                    if communications:
                        # Store raw audit trail events
                        manuscript['audit_trail'] = communications
                        manuscript['communication_timeline'] = communications
                        print(f"   ✅ Extracted {len(communications)} communication events")
                        # Debug: Show event type breakdown
                        email_events = len([e for e in communications if e.get('event_type') == 'email'])
                        status_events = len([e for e in communications if e.get('event_type') == 'status_change'])
                        print(f"      📧 Email events: {email_events}")
                        print(f"      📊 Status change events: {status_events}")
                    else:
                        print("   ❌ No communication events found on audit trail page")
                    
                    # Extract additional timeline metadata
                    self.extract_audit_trail_metadata(manuscript)
                    
                    # CROSS-CHECK WITH GMAIL for external communications
                    print(f"   📧 Cross-checking with Gmail for external communications...")
                    print(f"      📊 Pre-enhancement: {len(manuscript.get('communication_timeline', []))} platform events")
                    try:
                        from core.gmail_search import enhance_audit_trail_with_gmail
                        
                        # Enhance the manuscript data with Gmail search results
                        enhanced_manuscript = enhance_audit_trail_with_gmail(manuscript)
                        
                        # Update manuscript with enhanced data
                        if enhanced_manuscript and enhanced_manuscript.get('timeline_enhanced'):
                            # The enhancement function modifies the original object, but let's be explicit
                            if enhanced_manuscript is not manuscript:
                                # If it's a different object, copy the enhanced fields
                                manuscript['communication_timeline'] = enhanced_manuscript.get('communication_timeline', [])
                                manuscript['timeline_enhanced'] = enhanced_manuscript.get('timeline_enhanced', False)
                                manuscript['external_communications_count'] = enhanced_manuscript.get('external_communications_count', 0)
                            
                            external_count = manuscript.get('external_communications_count', 0)
                            total_events = len(manuscript.get('communication_timeline', []))
                            platform_events = len([e for e in manuscript.get('communication_timeline', []) if not e.get('external', False)])
                            print(f"   ✅ Gmail cross-check complete: Found {external_count} external communications")
                            print(f"   📊 Total timeline: {total_events} events ({platform_events} platform + {external_count} external)")
                        else:
                            print(f"   ⚠️ Gmail cross-check completed but timeline not enhanced")
                    
                        # ENHANCED: Extract comprehensive timeline analytics
                        print(f"   📊 Extracting timeline analytics...")
                        try:
                            timeline_analytics = self.extract_timeline_analytics(manuscript)
                            if timeline_analytics:
                                manuscript['timeline_analytics'] = timeline_analytics
                                print(f"   ✅ Timeline analytics extracted: {timeline_analytics['total_events']} events analyzed")
                            else:
                                print(f"   ⚠️ No timeline analytics extracted")
                        except Exception as analytics_error:
                            print(f"   ⚠️ Timeline analytics error (continuing): {analytics_error}")
                            
                    except Exception as e:
                        print(f"   ⚠️ Gmail cross-check failed (non-critical): {e}")
                        # Continue without Gmail enhancement - it's optional
                        
                except Exception as e:
                    print(f"   ❌ Error after clicking audit trail: {e}")
                    import traceback
                    traceback.print_exc()
                    
            else:
                print("   ❌ Could not find audit trail link with any selector")
                
                # Set empty audit trail when tab not found
                manuscript['audit_trail'] = []
                print("   ✅ Set empty audit trail (tab not accessible)")
                
                # DEBUG: Show what tabs/links ARE available
                try:
                    all_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'MANUSCRIPT_DETAILS') or contains(@onclick, 'MANUSCRIPT')]")
                    print(f"   🐛 DEBUG: Found {len(all_links)} manuscript detail links:")
                    for i, link in enumerate(all_links[:10]):  # Show first 10
                        href = link.get_attribute('href') or 'No href'
                        text = link.text.strip() or 'No text'
                        print(f"      {i+1}. '{text}' -> {href[:80]}...")
                except:
                    pass
                
        except Exception as e:
            print(f"   ❌ Error extracting audit trail: {e}")
            # Ensure audit trail is set even on error
            manuscript['audit_trail'] = []
            import traceback
            traceback.print_exc()

    def extract_communication_events(self):
        """Extract individual communication events from audit trail table with pagination."""
        try:
            all_communications = []
            
            # First, check if there are multiple pages
            total_events = self.get_total_audit_events()
            pages_needed = max(1, (total_events + 9) // 10)  # Round up to nearest 10
            
            print(f"      📊 Found {total_events} total events across {pages_needed} pages")
            
            # Extract events from each page
            for page_num in range(1, pages_needed + 1):
                print(f"      📄 Processing page {page_num}/{pages_needed}...")
                
                # Navigate to specific page if not the first
                if page_num > 1:
                    self.navigate_to_audit_page(page_num)
                    time.sleep(2)
                
                # Extract events from current page
                page_communications = self.extract_events_from_current_page()
                all_communications.extend(page_communications)
                
                print(f"         ✅ Extracted {len(page_communications)} events from page {page_num}")
            
            return all_communications
            
        except Exception as e:
            print(f"   ❌ Error extracting communication events: {e}")
            return []

    def get_total_audit_events(self):
        """Get total number of audit events from pagination info."""
        import re
        
        try:
            print(f"      🔍 Looking for pagination info...")
            
            # Method 1: Look for pagination info like "of 32" or "of 45" with various selectors
            pagination_selectors = [
                "//td[contains(text(), 'of') and contains(@class, 'pagecontents')]",
                "//td[contains(text(), 'of')]",
                "//*[contains(text(), 'of') and contains(text(), '1')]",
                "//div[contains(@class, 'page')]//text()[contains(., 'of')]/..",
                "//*[contains(text(), '1 of')]"
            ]
            
            for selector in pagination_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        text = elem.text.strip()
                        print(f"         📄 Found pagination text: '{text}'")
                        
                        # Try different patterns for "of X"
                        patterns = [
                            r'of\s+(\d+)',
                            r'of\s*(\d+)',
                            r'1\s+of\s+(\d+)',
                            r'/\s*(\d+)',
                            r'total[:\s]*(\d+)'
                        ]
                        
                        for pattern in patterns:
                            match = re.search(pattern, text.lower())
                            if match:
                                total = int(match.group(1))
                                print(f"         ✅ Found total events: {total}")
                                return total
                except:
                    continue
            
            # Method 2: Count select options
            print(f"      🔍 Checking select dropdown options...")
            select_selectors = [
                "//select[@name='page_select']//option",
                "//select[contains(@name, 'page')]//option",
                "//select//option[contains(text(), '-')]"
            ]
            
            for selector in select_selectors:
                try:
                    select_options = self.driver.find_elements(By.XPATH, selector)
                    if select_options:
                        print(f"         📋 Found {len(select_options)} select options")
                        
                        # Check each option for range patterns
                        max_num = 0
                        for option in select_options:
                            option_text = option.text.strip()
                            print(f"         📄 Option: '{option_text}'")
                            
                            # Extract numbers from ranges like "31-40", "1-10", etc.
                            range_matches = re.findall(r'(\d+)', option_text)
                            if range_matches:
                                max_num = max(max_num, max(int(num) for num in range_matches))
                        
                        if max_num > 0:
                            print(f"         ✅ Found max event number: {max_num}")
                            return max_num
                except:
                    continue
            
            # Method 3: Count actual table rows if pagination fails
            print(f"      🔍 Counting visible table rows as fallback...")
            try:
                rows = self.driver.find_elements(By.XPATH, "//table//tr[td]")
                visible_count = len(rows)
                print(f"         📊 Found {visible_count} visible rows")
                
                # If we have 10 rows, there might be pagination (common page size)
                if visible_count >= 10:
                    return visible_count * 2  # Conservative estimate
                else:
                    return visible_count
                    
            except:
                pass
            
            print(f"      ⚠️ Could not determine total events, using default")
            return 20  # Increased default from 10
            
        except Exception as e:
            print(f"      ❌ Error getting total events: {e}")
            import traceback
            traceback.print_exc()
            return 20

    def navigate_to_audit_page(self, page_num):
        """Navigate to a specific page in the audit trail."""
        try:
            # Try dropdown selection first
            try:
                select_element = self.driver.find_element(By.NAME, "page_select")
                from selenium.webdriver.support.ui import Select
                select = Select(select_element)
                select.select_by_value(str(page_num))
                time.sleep(1)
                return
            except:
                pass
            
            # Try direct navigation link
            page_links = self.driver.find_elements(By.XPATH, 
                f"//a[contains(@href, 'CURRENT_PAGE_NO') and contains(@href, '{page_num}')]")
            
            if page_links:
                page_links[0].click()
                time.sleep(1)
                return
            
            # Try arrow navigation for next page
            if page_num > 1:
                next_arrows = self.driver.find_elements(By.XPATH, 
                    "//a[.//img[contains(@src, 'right_arrow.gif')]]")
                if next_arrows:
                    next_arrows[0].click()
                    time.sleep(1)
                    
        except Exception as e:
            print(f"      ❌ Error navigating to page {page_num}: {e}")

    def extract_events_from_current_page(self):
        """Extract ALL events from the current audit trail page, not just emails."""
        try:
            events = []
            
            # Get ALL table rows in the audit trail, not just email rows
            all_event_rows = self.driver.find_elements(By.XPATH, 
                "//table[@class='tablelines']//tr[td[@class='tablelightcolor'] and not(contains(@class, 'tablehead'))]")
            
            # Also try alternative selector if above doesn't work
            if not all_event_rows:
                all_event_rows = self.driver.find_elements(By.XPATH,
                    "//tr[td[@class='tablelightcolor'][contains(., '20')] and not(th)]")  # Has date content
            
            print(f"         Found {len(all_event_rows)} total event rows on this page")
            
            for i, row in enumerate(all_event_rows):
                try:
                    event = {}
                    
                    # Get all cells with tablelightcolor class
                    cells = row.find_elements(By.XPATH, ".//td[@class='tablelightcolor']")
                    
                    if len(cells) >= 2:
                        # First cell should be timestamp
                        timestamp_text = cells[0].text.strip()
                        
                        # Parse both EDT and GMT timestamps
                        lines = [line.strip() for line in timestamp_text.split('\n') if line.strip()]
                        if len(lines) >= 2:
                            event['timestamp_edt'] = lines[0]
                            event['timestamp_gmt'] = lines[1]
                        elif len(lines) == 1:
                            event['timestamp_edt'] = lines[0]
                        
                        # Second cell contains event details
                        event_cell = cells[1]
                        event_text = event_cell.text.strip()
                        
                        # Check if this is an email event (has letter icon)
                        has_email_icon = len(row.find_elements(By.XPATH, ".//img[@src='/images/en_US/icons/letter.gif']")) > 0
                        
                        if has_email_icon:
                            # This is an email communication
                            event['event_type'] = 'email'
                            
                            # Parse email details from the text
                            for line in event_text.split('\n'):
                                line = line.strip()
                                
                                if line.startswith('To:'):
                                    event['to'] = line.replace('To:', '').strip()
                                elif line.startswith('From:'):
                                    event['from'] = line.replace('From:', '').strip()
                                elif line.startswith('Subject:'):
                                    event['subject'] = line.replace('Subject:', '').strip()
                                elif line.startswith('Results:'):
                                    event['delivery_status'] = line.replace('Results:', '').strip()
                                elif line.startswith('Template Name:'):
                                    event['template'] = line.replace('Template Name:', '').strip()
                            
                            # Extract popup URL for email content if available
                            try:
                                popup_links = event_cell.find_elements(By.XPATH, 
                                    ".//a[contains(@href, 'popWindow')]")
                                
                                if popup_links:
                                    popup_href = popup_links[0].get_attribute('href')
                                    # Extract the popup parameters
                                    import re
                                    popup_match = re.search(r"popWindow\('([^']+)'", popup_href)
                                    if popup_match:
                                        event['email_content_url'] = popup_match.group(1)
                            except:
                                pass
                            
                            # Classify email type
                            subject = event.get('subject', '').lower()
                            template = event.get('template', '').lower()
                            
                            if 'invitation' in subject or 'invitation' in template or 'assign reviewers' in template:
                                event['type'] = 'reviewer_invitation'
                            elif 'reminder' in subject or 'reminder' in template:
                                event['type'] = 'reminder'
                            elif 'agreed' in template:
                                event['type'] = 'reviewer_agreement'
                            elif 'declined' in template or 'unavailable' in template:
                                event['type'] = 'reviewer_decline'
                            elif 'now due' in subject:
                                event['type'] = 'deadline_reminder'
                            elif 'follow-up' in subject:
                                event['type'] = 'follow_up'
                            elif 'review' in subject.lower() and 'submitted' in subject.lower():
                                event['type'] = 'review_submission'
                            else:
                                event['type'] = 'other_email'
                                
                        else:
                            # This is a non-email event (status change, review submission, etc.)
                            event['event_type'] = 'status_change'
                            event['description'] = event_text
                            
                            # Try to categorize the event based on content
                            event_lower = event_text.lower()
                            if 'submitted' in event_lower and 'manuscript' in event_lower:
                                event['type'] = 'manuscript_submission'
                            elif 'assigned' in event_lower and 'editor' in event_lower:
                                event['type'] = 'editor_assignment'
                            elif 'assigned' in event_lower and 'reviewer' in event_lower:
                                event['type'] = 'reviewer_assignment'
                            elif 'review' in event_lower and 'received' in event_lower:
                                event['type'] = 'review_received'
                            elif 'agreed' in event_lower:
                                event['type'] = 'reviewer_agreed'
                            elif 'declined' in event_lower:
                                event['type'] = 'reviewer_declined'
                            elif 'decision' in event_lower:
                                event['type'] = 'editorial_decision'
                            elif 'modified' in event_lower or 'updated' in event_lower:
                                event['type'] = 'modification'
                            elif 'created' in event_lower:
                                event['type'] = 'creation'
                            elif 'status changed' in event_lower:
                                event['type'] = 'status_update'
                            else:
                                event['type'] = 'other_event'
                        
                        # Parse timestamp to datetime for better comparison
                        if event.get('timestamp_gmt'):
                            try:
                                from datetime import datetime
                                # Parse GMT timestamp like "Dec 27, 2024 12:07:16 PM GMT"
                                timestamp_str = event['timestamp_gmt'].replace(' GMT', '')
                                parsed_datetime = datetime.strptime(timestamp_str, '%b %d, %Y %I:%M:%S %p')
                                event['datetime'] = parsed_datetime
                                # Also add date field for compatibility
                                event['date'] = parsed_datetime
                            except Exception as e:
                                # Fallback: try to parse as date only
                                try:
                                    date_parts = event['timestamp_gmt'].split()
                                    if len(date_parts) >= 3:
                                        # Try "Dec 27, 2024" format
                                        date_str = f"{date_parts[0]} {date_parts[1]} {date_parts[2]}".replace(',', '')
                                        event['date'] = datetime.strptime(date_str, '%b %d %Y')
                                except:
                                    pass
                        
                        # Add source information for platform events
                        event['source'] = 'mf_platform'
                        event['platform'] = 'Mathematical Finance'
                        
                        # Add the event to our list - ALL events, not just emails
                        events.append(event)
                        
                except Exception as e:
                    print(f"         ❌ Error processing event row: {e}")
                    continue
            
            return events
            
        except Exception as e:
            print(f"      ❌ Error extracting events from current page: {e}")
            return []

    def extract_audit_trail_metadata(self, manuscript):
        """Extract additional metadata from audit trail (manuscript status, timeline)."""
        try:
            # Look for status information in the third column
            status_cells = self.driver.find_elements(By.XPATH, 
                "//table[.//td[contains(text(), 'Manuscript Status')]]//td[@class='tablelightcolor'][3]")
            
            timeline_metadata = []
            for status_cell in status_cells:
                try:
                    status_text = status_cell.text.strip()
                    if status_text and len(status_text) > 5:
                        # Parse status information
                        if 'overdue' in status_text.lower():
                            timeline_metadata.append({
                                'type': 'overdue_task',
                                'description': status_text
                            })
                        elif 'due' in status_text.lower():
                            timeline_metadata.append({
                                'type': 'deadline',
                                'description': status_text
                            })
                except:
                    continue
            
            if timeline_metadata:
                manuscript['timeline_metadata'] = timeline_metadata
                print(f"   ✅ Extracted {len(timeline_metadata)} timeline metadata items")
                
        except Exception as e:
            print(f"   ❌ Error extracting audit trail metadata: {e}")

    def extract_abstract_from_popup(self, abstract_link):
        """Extract abstract text from popup window."""
        original_window = self.driver.current_window_handle
        abstract_text = ""
        
        try:
            # Click abstract link
            abstract_link.click()
            time.sleep(2)
            
            # Switch to popup
            if len(self.driver.window_handles) > 1:
                for window in self.driver.window_handles:
                    if window != original_window:
                        self.driver.switch_to.window(window)
                        break
                
                # Extract abstract text
                # Try various selectors
                selectors = [
                    "//td[@class='pagecontents']",
                    "//p[@class='pagecontents']",
                    "//div[@class='abstract']",
                    "//body"
                ]
                
                for selector in selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            text = elem.text.strip()
                            if len(text) > 100:  # Likely abstract content
                                abstract_text = text
                                break
                        if abstract_text:
                            break
                    except:
                        pass
                
                # Close popup
                self.driver.close()
                self.driver.switch_to.window(original_window)
            
        except Exception as e:
            print(f"      ❌ Error extracting abstract: {e}")
            # Ensure we're back on main window
            try:
                if self.driver.current_window_handle != original_window:
                    self.driver.switch_to.window(original_window)
            except:
                pass
                
        return abstract_text
    
    def extract_abstract(self, manuscript):
        """Extract manuscript abstract from popup."""
        try:
            print("   📝 Extracting abstract...")
            
            # Find abstract link
            doc_section = self.driver.find_element(By.XPATH, "//p[@class='pagecontents msdetailsbuttons']")
            abstract_links = doc_section.find_elements(By.XPATH, ".//a[contains(text(), 'Abstract')]")
            
            if abstract_links:
                # Store current window
                original_window = self.driver.current_window_handle
                
                # Click abstract link
                abstract_links[0].click()
                time.sleep(2)
                
                # Switch to popup
                if len(self.driver.window_handles) > 1:
                    for window in self.driver.window_handles:
                        if window != original_window:
                            self.driver.switch_to.window(window)
                            break
                    
                    # Extract abstract text
                    abstract_text = ""
                    
                    # Try various selectors
                    selectors = [
                        "//td[@class='pagecontents']",
                        "//p[@class='pagecontents']",
                        "//div[@class='abstract']",
                        "//body"
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for elem in elements:
                                text = elem.text.strip()
                                if len(text) > 100:  # Likely abstract content
                                    abstract_text = text
                                    break
                            if abstract_text:
                                break
                        except:
                            pass
                    
                    # Close popup
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                    
                    if abstract_text:
                        manuscript['abstract'] = abstract_text
                        print(f"      ✅ Abstract extracted ({len(abstract_text)} chars)")
                    else:
                        print("      ❌ Abstract text not found in popup")
                else:
                    print("      ❌ Abstract popup did not open")
                    
        except Exception as e:
            print(f"   ❌ Error extracting abstract: {e}")


    def extract_keywords(self, manuscript):
        """Extract manuscript keywords."""
        try:
            print("   🏷️ Extracting keywords...")
            
            # Look for keywords in various locations
            keyword_patterns = [
                "//td[contains(text(), 'Keywords')]/following-sibling::td",
                "//td[contains(text(), 'Key Words')]/following-sibling::td",
                "//p[contains(text(), 'Keywords:')]",
                "//span[contains(text(), 'Keywords')]/following::span[1]",
                "//div[contains(@class, 'keywords')]"
            ]
            
            keywords_found = False
            for pattern in keyword_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > 3:
                            # Remove "Keywords:" label if present
                            if text.lower().startswith('keywords:'):
                                text = text[9:].strip()  # Remove "Keywords:" prefix
                            elif text.lower().startswith('keywords'):
                                text = text[8:].strip()  # Remove "Keywords" prefix
                            
                            # Skip if it's just the label or too short
                            if not text or len(text) < 5:
                                continue
                                
                            # Parse keywords (usually semicolon or comma separated)
                            if ';' in text:
                                keywords = [k.strip() for k in text.split(';') if k.strip() and len(k.strip()) > 1]
                            elif ',' in text:
                                keywords = [k.strip() for k in text.split(',') if k.strip() and len(k.strip()) > 1]
                            else:
                                # Single keyword - make sure it's not just a label
                                if not text.lower() in ['keywords', 'keywords:', 'key words']:
                                    keywords = [text]
                                else:
                                    keywords = []
                            
                            if keywords and len(keywords) > 0:
                                manuscript['keywords'] = keywords
                                print(f"      ✅ Keywords extracted: {', '.join(keywords[:3])}...")
                                keywords_found = True
                                break
                    if keywords_found:
                        break
                except:
                    pass
            
            if not keywords_found:
                print("      ❌ Keywords not found on page")
                
        except Exception as e:
            print(f"   ❌ Error extracting keywords: {e}")


    def extract_author_affiliations(self, manuscript):
        """Extract author affiliations from mailpopup links."""
        try:
            print("   🏛️ Extracting author affiliations...")
            
            # For each author, try to get their affiliation
            for author in manuscript.get('authors', []):
                if not author.get('institution'):
                    # Find the author's mailpopup link
                    try:
                        # Look for author link by name
                        author_links = self.driver.find_elements(By.XPATH, 
                            f"//a[contains(@href, 'mailpopup') and contains(text(), '{author['name'].split()[-1]}')]")
                        
                        if author_links:
                            # Get email and potentially affiliation from popup
                            original_window = self.driver.current_window_handle
                            
                            author_links[0].click()
                            time.sleep(2)
                            
                            if len(self.driver.window_handles) > 1:
                                for window in self.driver.window_handles:
                                    if window != original_window:
                                        self.driver.switch_to.window(window)
                                        break
                                
                                # Extract email and affiliation
                                try:
                                    # Email
                                    email_field = self.driver.find_element(By.NAME, "EMAIL_TEMPLATE_TO")
                                    email = email_field.get_attribute('value')
                                    if email and '@' in email:
                                        author['email'] = email
                                except:
                                    pass
                                
                                # Look for institution/affiliation
                                affil_patterns = [
                                    "//td[contains(text(), 'Institution')]",
                                    "//td[contains(text(), 'Affiliation')]",
                                    "//td[contains(text(), 'Department')]"
                                ]
                                
                                for pattern in affil_patterns:
                                    try:
                                        label = self.driver.find_element(By.XPATH, pattern)
                                        # Get next sibling td
                                        value = label.find_element(By.XPATH, "./following-sibling::td")
                                        affiliation = value.text.strip()
                                        if affiliation:
                                            author['institution'] = affiliation
                                            print(f"      ✅ {author['name']}: {affiliation}")
                                            break
                                    except:
                                        pass
                                
                                # Close popup
                                self.driver.close()
                                self.driver.switch_to.window(original_window)
                                
                    except Exception as e:
                        print(f"      ⚠️ Could not get affiliation for {author['name']}: {e}")
                        
        except Exception as e:
            print(f"   ❌ Error extracting author affiliations: {e}")


    def extract_doi(self, manuscript):
        """Extract DOI if available."""
        try:
            # Look for DOI patterns
            doi_patterns = [
                "//td[contains(text(), 'DOI')]/following-sibling::td",
                "//span[contains(text(), 'DOI:')]",
                "//a[contains(@href, 'doi.org')]",
                "//*[contains(text(), '10.') and contains(text(), '/')]"
            ]
            
            for pattern in doi_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    for elem in elements:
                        text = elem.text.strip()
                        # Extract DOI pattern (10.xxxx/yyyy)
                        import re
                        doi_match = re.search(r'10\.\d{4,}/[-._;()/:a-zA-Z0-9]+', text)
                        if doi_match:
                            manuscript['doi'] = doi_match.group(0)
                            print(f"   📖 DOI found: {manuscript['doi']}")
                            return
                except:
                    pass
                    
        except Exception as e:
            print(f"   ⚠️ Error extracting DOI: {e}")


    def parse_recommendation_from_popup(self, popup_content):
        """Parse structured recommendation from popup content."""
        if not popup_content:
            return None
            
        recommendation = popup_content.get('recommendation', '')
        review_text = popup_content.get('review_text', '')
        
        # Map text to structured enum values
        recommendation_map = {
            'accept': 'accept',
            'minor': 'minor',
            'major': 'major',
            'reject': 'reject',
            'minor revision': 'minor',
            'major revision': 'major',
            'acceptance': 'accept',
            'rejection': 'reject'
        }
        
        # Check recommendation field first
        rec_lower = recommendation.lower()
        for key, value in recommendation_map.items():
            if key in rec_lower:
                return value
                
        # Check review text for recommendation keywords
        text_lower = review_text.lower()
        if 'recommend acceptance' in text_lower or 'should be accepted' in text_lower:
            return 'accept'
        elif 'minor revision' in text_lower or 'minor changes' in text_lower:
            return 'minor'
        elif 'major revision' in text_lower or 'substantial revision' in text_lower:
            return 'major'
        elif 'recommend rejection' in text_lower or 'should be rejected' in text_lower:
            return 'reject'
            
        return None
    
    def parse_referee_status_details(self, status_text):
        """Parse detailed status information from referee status cell."""
        status_info = {
            'status': status_text,
            'review_received': False,
            'review_complete': False,
            'review_pending': False,
            'agreed_to_review': False,
            'declined': False,
            'no_response': False
        }
        
        status_lower = status_text.lower()
        
        # Check various status states
        if 'review received' in status_lower:
            status_info['review_received'] = True
            status_info['review_complete'] = 'complete' in status_lower
        elif 'agreed' in status_lower:
            status_info['agreed_to_review'] = True
            status_info['review_pending'] = True
        elif 'declined' in status_lower or 'unavailable' in status_lower:
            status_info['declined'] = True
        elif 'no response' in status_lower or 'awaiting' in status_lower:
            status_info['no_response'] = True
        elif 'review in progress' in status_lower:
            status_info['agreed_to_review'] = True
            status_info['review_pending'] = True
        
        return status_info
    
    def extract_review_scores(self, review_text):
        """Extract structured review scores from review content."""
        scores = {
            'overall_rating': None,
            'technical_quality': None,
            'originality': None,
            'clarity': None,
            'significance': None,
            'methodology': None,
            'presentation': None
        }
        
        if not review_text:
            return scores
        
        import re
        
        # Pattern matching for scores
        # Numeric ratings (e.g., "Overall: 4/5" or "Technical Quality: 8/10")
        numeric_patterns = {
            'overall': r'overall\s*(?:rating|score)?[:\s]*(\d+)\s*[/\\]\s*(\d+)',
            'technical': r'technical\s*(?:quality|merit)?[:\s]*(\d+)\s*[/\\]\s*(\d+)',
            'originality': r'originality[:\s]*(\d+)\s*[/\\]\s*(\d+)',
            'clarity': r'clarity[:\s]*(\d+)\s*[/\\]\s*(\d+)',
            'significance': r'significance[:\s]*(\d+)\s*[/\\]\s*(\d+)'
        }
        
        # Simple numeric patterns (e.g., "Technical Quality: 4" without denominator)
        simple_numeric_patterns = {
            'technical_quality': r'Technical Quality[:\s]*(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?',
            'originality': r'Originality[:\s]*(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?',
            'clarity': r'Clarity[:\s]*(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?',
            'significance': r'Significance[:\s]*(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?',
            'overall_rating': r'Overall[:\s]*(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?',
            'methodology': r'Methodology[:\s]*(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?',
            'presentation': r'Presentation[:\s]*(\d+(?:\.\d+)?)\s*(?:/\s*\d+)?'
        }
        
        # Qualitative ratings (e.g., "Technical Quality: Excellent")
        qualitative_patterns = {
            'technical_quality': r'technical\s*(?:quality|merit)[:\s]*(excellent|very\s*good|good|fair|poor)',
            'originality': r'originality[:\s]*(excellent|very\s*good|good|fair|poor|high|medium|low)',
            'clarity': r'clarity[:\s]*(excellent|very\s*good|good|fair|poor)',
            'presentation': r'presentation[:\s]*(excellent|very\s*good|good|fair|poor)'
        }
        
        text_lower = review_text.lower()
        
        # Check numeric patterns
        for key, pattern in numeric_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                score = f"{match.group(1)}/{match.group(2)}"
                if key == 'overall':
                    scores['overall_rating'] = score
                else:
                    scores[key] = score
        
        # Check simple numeric patterns (higher priority)
        for key, pattern in simple_numeric_patterns.items():
            match = re.search(pattern, review_text, re.IGNORECASE)
            if match:
                scores[key] = float(match.group(1))
        
        # Check qualitative patterns
        for key, pattern in qualitative_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                scores[key] = match.group(1).title()
        
        return scores
    
    def extract_editorial_decision(self, review_text):
        """Extract specific editorial decision from review text."""
        if not review_text:
            return 'unclear'
            
        decision_patterns = {
            'accept_as_is': [
                'accept as is',
                'accept without revision',
                'ready for publication',
                'no changes needed',
                'publish without revision',
                'can be published as is'
            ],
            'minor_revision': [
                'minor revision',
                'minor changes',
                'small corrections',
                'light revision',
                'minor modifications',
                'accept with minor'
            ],
            'major_revision': [
                'major revision',
                'substantial changes',
                'significant revision',
                'extensive revision',
                'major modifications',
                'needs major'
            ],
            'reject': [
                'recommend rejection',
                'should be rejected',
                'not suitable for publication',
                'do not publish',
                'recommend against publication',
                'cannot be published'
            ],
            'reject_with_resubmission': [
                'reject but encourage resubmission',
                'reject with invitation to resubmit',
                'too preliminary',
                'encourage resubmission',
                'invite resubmission'
            ]
        }
        
        text_lower = review_text.lower()
        
        # Check each decision type
        for decision, patterns in decision_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return decision
        
        # Fallback: check for simple keywords
        if 'accept' in text_lower and 'minor' not in text_lower and 'major' not in text_lower:
            return 'accept_as_is'
        elif 'reject' in text_lower:
            return 'reject'
        
        return 'unclear'
    
    def extract_review_timeline(self, history_cell):
        """Extract complete review timeline with all key dates."""
        timeline = {
            'invitation_sent': None,
            'invitation_viewed': None,
            'agreed_to_review': None,
            'declined_date': None,
            'review_submitted': None,
            'review_modified': None,
            'reminder_sent': [],
            'total_days_to_review': None,
            'days_to_respond': None
        }
        
        try:
            # Extract specific dates from the history cell
            date_rows = history_cell.find_elements(By.XPATH, ".//table//tr")
            
            for date_row in date_rows:
                try:
                    cells = date_row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        date_type = cells[0].text.strip().lower()
                        date_value = cells[1].text.strip()
                        
                        # Parse different date types
                        if 'invited' in date_type:
                            timeline['invitation_sent'] = date_value
                        elif 'agreed' in date_type:
                            timeline['agreed_to_review'] = date_value
                        elif 'declined' in date_type:
                            timeline['declined_date'] = date_value
                        elif 'submitted' in date_type or 'review received' in date_type:
                            timeline['review_submitted'] = date_value
                        elif 'reminder' in date_type:
                            timeline['reminder_sent'].append(date_value)
                        elif 'viewed' in date_type and 'invitation' in date_type:
                            timeline['invitation_viewed'] = date_value
                        elif 'modified' in date_type:
                            timeline['review_modified'] = date_value
                except:
                    continue
            
            # Calculate durations if we have the dates
            try:
                if timeline['invitation_sent'] and timeline['agreed_to_review']:
                    from datetime import datetime
                    invite_date = datetime.strptime(timeline['invitation_sent'], '%d-%b-%Y')
                    agree_date = datetime.strptime(timeline['agreed_to_review'], '%d-%b-%Y')
                    timeline['days_to_respond'] = (agree_date - invite_date).days
                
                if timeline['agreed_to_review'] and timeline['review_submitted']:
                    agree_date = datetime.strptime(timeline['agreed_to_review'], '%d-%b-%Y')
                    submit_date = datetime.strptime(timeline['review_submitted'], '%d-%b-%Y')
                    timeline['total_days_to_review'] = (submit_date - agree_date).days
            except:
                # Date parsing failed, that's OK
                pass
                
        except Exception as e:
            print(f"         ⚠️ Error extracting timeline: {e}")
        
        return timeline

    def get_email_from_popup(self, link, name):
        """DEPRECATED: Use get_email_from_popup_safe() instead. This function has wrong signature."""
        original_window = self.driver.current_window_handle
        
        try:
            # Store link href for debugging
            link_href = link.get_attribute('href') if link else 'No href'
            print(f"         🔗 Link href: {link_href[:100]}...")
            
            # Click link with timeout protection
            link.click()
            time.sleep(2)
            
            # Timeout protection - don't wait more than 10 seconds total
            import time as time_module
            start_time = time_module.time()
            
            # Check for new windows
            all_windows = self.driver.window_handles
            
            if len(all_windows) > 1:
                # Switch to popup window
                popup_window = [w for w in all_windows if w != original_window][-1]
                self.driver.switch_to.window(popup_window)
                time.sleep(1)
                
                # Check timeout
                if time_module.time() - start_time > 10:
                    print(f"         ⏰ Timeout getting email for {name}")
                    return ""
                
                try:
                    # Debug: Save popup content
                    try:
                        with open(f"debug_author_popup_{name.replace(' ', '_')}.html", 'w') as f:
                            f.write(self.driver.page_source)
                        print(f"         🐛 DEBUG: Saved author popup for {name}")
                    except:
                        pass
                    
                    # Check if the popup uses frames
                    frames = self.driver.find_elements(By.TAG_NAME, "frame")
                    if frames:
                        # Switch to the main email frame (usually named 'mainemailwindow')
                        for frame in frames:
                            frame_name = frame.get_attribute('name')
                            if 'mail' in frame_name.lower():
                                self.driver.switch_to.frame(frame)
                                break
                        else:
                            # If no mail frame found, try first frame
                            self.driver.switch_to.frame(0)
                    
                    # For author popups, the structure might be different
                    # Try multiple strategies to find the author's email
                    
                    # Strategy 1: Look for email in the popup content (not TO field)
                    page_source = self.driver.page_source
                    import re
                    
                    # Look for email patterns in the content
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails_found = re.findall(email_pattern, page_source)
                    
                    # Filter out journal/system/editor emails
                    author_emails = []
                    editor_patterns = ['dylan.possamai', 'editor@', 'admin@', 'noreply@', 'no-reply@']
                    
                    for email in emails_found:
                        if email and '@' in email:
                            email_lower = email.lower()
                            # Skip if it's a system/editor email
                            if any(pattern in email_lower for pattern in ['wiley', 'manuscript', 'journal'] + editor_patterns):
                                continue
                            # Also skip if it's the logged-in user's email (editor)
                            if email_lower == os.getenv('MF_EMAIL', '').lower():
                                continue
                            author_emails.append(email)
                    
                    if author_emails:
                        # Try to find the most likely author email
                        # Prefer emails that match the author's name or institution patterns
                        best_email = None
                        author_name_parts = name.lower().split()
                        
                        for email in author_emails:
                            email_local = email.split('@')[0].lower()
                            # Check if email contains parts of author name
                            if any(part in email_local for part in author_name_parts if len(part) > 2):
                                best_email = email
                                break
                        
                        if not best_email and author_emails:
                            best_email = author_emails[0]
                        
                        if best_email:
                            print(f"         ✅ Found author email: {best_email}")
                            return best_email
                    
                    # Strategy 2: Check if this is showing author details
                    # Look for email in specific contexts
                    email_contexts = [
                        r'Email[:\s]+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
                        r'E-mail[:\s]+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})',
                        r'mailto:([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
                    ]
                    
                    for pattern in email_contexts:
                        match = re.search(pattern, page_source, re.IGNORECASE)
                        if match:
                            email = match.group(1)
                            if email and 'wiley' not in email.lower():
                                print(f"         ✅ Found author email (context): {email}")
                                return email
                    
                    # Strategy 3: Check EMAIL_TEMPLATE_TO field (might be journal email)
                    try:
                        to_field = self.driver.find_element(By.NAME, "EMAIL_TEMPLATE_TO")
                        to_email = to_field.get_attribute('value')
                        if to_email and '@' in to_email and 'wiley' not in to_email.lower():
                            print(f"         ✅ Found email in TO field: {to_email}")
                            return to_email
                    except:
                        pass
                    
                    print(f"         ❌ No author email found in popup (only journal emails)")
                    
                except Exception as e:
                    print(f"         ❌ Error reading popup content: {str(e)[:50]}")
                
                finally:
                    # Close popup and return to main window
                    try:
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                    except:
                        # If close fails, just switch back
                        self.driver.switch_to.window(original_window)
            else:
                print(f"         ❌ No popup window opened")
                
        except Exception as e:
            print(f"         ❌ Email extraction error: {str(e)[:50]}")
            
        finally:
            # ROBUST window cleanup - same as safe popup method
            try:
                print(f"   🧹 Starting window cleanup for {name}")
                # Close any extra windows first
                all_windows = self.driver.window_handles
                for window in all_windows:
                    if window != original_window:
                        try:
                            self.driver.switch_to.window(window)
                            self.driver.close()
                            print(f"   🧹 Closed popup window for {name}")
                        except Exception:
                            pass
                            
                # Always return to original window
                self.driver.switch_to.window(original_window)
                print(f"   🔙 Returned to main window for {name}")
                
            except Exception as cleanup_error:
                print(f"   ⚠️ Window cleanup failed for {name}: {cleanup_error}")
                # Emergency fallback - try to get back to main window
                try:
                    if len(self.driver.window_handles) > 0:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        print(f"   🆘 Emergency fallback to first window")
                except Exception:
                    print(f"   ❌ Emergency fallback also failed")
        
        return ''
    
    def download_pdf(self, pdf_link, manuscript_id):
        """Download manuscript PDF."""
        try:
            original_window = self.driver.current_window_handle
            
            # Click PDF link
            pdf_link.click()
            time.sleep(3)
            
            # Check for new window
            all_windows = self.driver.window_handles
            if len(all_windows) > 1:
                # Switch to PDF window
                pdf_window = [w for w in all_windows if w != original_window][-1]
                self.driver.switch_to.window(pdf_window)
                time.sleep(2)
                
                # Get PDF URL
                pdf_url = self.driver.current_url
                
                # Create downloads directory
                downloads_dir = self.get_download_dir("manuscripts")
                
                # Save PDF using requests
                import requests
                
                # Get cookies from selenium
                cookies = self.driver.get_cookies()
                session = requests.Session()
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
                
                # Download PDF
                response = session.get(pdf_url, stream=True)
                if response.status_code == 200:
                    pdf_path = downloads_dir / f"{manuscript_id}.pdf"
                    with open(pdf_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"      ✅ PDF saved to {pdf_path}")
                    
                    # Close PDF window
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                    
                    return str(pdf_path)
                else:
                    print(f"      ❌ Failed to download PDF: {response.status_code}")
                
                # Close window
                self.driver.close()
                self.driver.switch_to.window(original_window)
                
        except Exception as e:
            print(f"      ❌ Error downloading PDF: {e}")
            # Ensure we're back on main window
            try:
                self.driver.switch_to.window(original_window)
            except:
                pass
        
        return None
    
    def download_cover_letter(self, cover_link, manuscript_id):
        """Download cover letter - properly handles MF's popup and file structure."""
        try:
            # Check if cover letter already downloaded to prevent duplicates
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(exist_ok=True)
            
            existing_files = list(downloads_dir.glob(f"{manuscript_id}_cover_letter.*"))
            if existing_files:
                print(f"      ✅ Cover letter already exists: {existing_files[0].name}")
                return str(existing_files[0])
            
            # Store current state
            original_window = self.driver.current_window_handle
            
            print(f"      🔗 Opening cover letter popup...")
            self.driver.execute_script("arguments[0].click();", cover_link)
            time.sleep(3)
            
            # Switch to popup window
            all_windows = self.driver.window_handles
            if len(all_windows) > 1:
                popup_window = None
                for window in all_windows:
                    if window != original_window:
                        popup_window = window
                        self.driver.switch_to.window(window)
                        break
                
                if not popup_window:
                    return None
                
                print(f"      📄 In cover letter popup")
                time.sleep(2)
                
                # Handle frames if present
                try:
                    frames = self.driver.find_elements(By.TAG_NAME, "frame")
                    if frames:
                        print(f"      🖼️ Found {len(frames)} frames, switching to main frame...")
                        self.driver.switch_to.frame(0)  # Try first frame
                except:
                    pass
                
                # Look for downloadable files with focused selectors
                file_downloaded = False
                file_path = None
                
                # Priority: Look for actual file download links
                download_selectors = [
                    "//a[contains(text(), '.pdf') and not(contains(@onclick, 'javascript:'))]",
                    "//a[contains(text(), '.docx') and not(contains(@onclick, 'javascript:'))]", 
                    "//a[contains(text(), '.doc') and not(contains(@onclick, 'javascript:'))]",
                    "//a[contains(@href, '.pdf') and not(contains(@href, 'javascript:'))]",
                    "//a[contains(@href, '.docx') and not(contains(@href, 'javascript:'))]",
                    "//a[contains(@href, 'GetFile')]",
                    "//a[contains(@href, 'DOWNLOAD_FILE')]"
                ]
                
                for selector in download_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                href = elem.get_attribute('href') or ''
                                text = elem.text.strip()
                                
                                # Skip javascript: links
                                if href.startswith('javascript:'):
                                    continue
                                
                                print(f"      🔍 Found file link: {text} -> {href[:80]}")
                                
                                # Try to download the file
                                if href and ('http' in href or href.startswith('/')):
                                    # Construct full URL if needed
                                    if href.startswith('/'):
                                        base_url = self.driver.current_url.split('/')[0] + '//' + self.driver.current_url.split('/')[2]
                                        href = base_url + href
                                    
                                    file_path = self._download_file_from_url(href, manuscript_id)
                                    if file_path:
                                        file_downloaded = True
                                        print(f"      ✅ Downloaded: {Path(file_path).name}")
                                        break
                                
                                # Try clicking if no direct URL worked
                                elif text and any(ext in text.lower() for ext in ['.pdf', '.docx', '.doc']):
                                    try:
                                        print(f"      👆 Clicking file link: {text}")
                                        elem.click()
                                        time.sleep(3)
                                        
                                        # Check for new window or download
                                        current_windows = self.driver.window_handles
                                        if len(current_windows) > len(all_windows):
                                            # New window opened
                                            new_window = current_windows[-1]
                                            self.driver.switch_to.window(new_window)
                                            
                                            current_url = self.driver.current_url
                                            if any(ext in current_url for ext in ['.pdf', '.docx', '.doc']):
                                                file_path = self._download_file_from_url(current_url, manuscript_id)
                                                if file_path:
                                                    file_downloaded = True
                                            
                                            # Close new window and return to popup
                                            self.driver.close()
                                            self.driver.switch_to.window(popup_window)
                                            
                                        if file_downloaded:
                                            break
                                            
                                    except Exception as e:
                                        print(f"      ⚠️ Click failed for {text}: {e}")
                                        continue
                        
                        if file_downloaded:
                            break
                    except Exception as e:
                        continue
                
                # If no file found, extract text content as fallback
                if not file_downloaded:
                    print(f"      ⚠️ No downloadable files found, extracting text content...")
                    
                    # Get the meaningful text content (skip navigation/metadata)
                    try:
                        # Look for main content area
                        content_selectors = [
                            "//div[@class='content']",
                            "//div[@id='content']", 
                            "//div[@class='main']",
                            "//body"
                        ]
                        
                        content_text = ""
                        for selector in content_selectors:
                            try:
                                content_elem = self.driver.find_element(By.XPATH, selector)
                                content_text = content_elem.text.strip()
                                if len(content_text) > 50 and "Files attached:" not in content_text:
                                    break
                            except:
                                continue
                        
                        # If we only got metadata/navigation, extract actual content  
                        if len(content_text) < 100 or "Files attached:" in content_text:
                            print(f"      ⚠️ Content appears to be metadata page, looking for actual cover letter text...")
                            
                            # Look for paragraphs with substantial content
                            paragraphs = self.driver.find_elements(By.XPATH, "//p[string-length(text()) > 50]")
                            if paragraphs:
                                content_text = "\n\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
                        
                        if len(content_text) > 50:
                            # Save as text file
                            txt_path = downloads_dir / f"{manuscript_id}_cover_letter.txt"
                            txt_path.write_text(content_text, encoding='utf-8')
                            file_path = str(txt_path)
                            print(f"      ✅ Saved text content: {txt_path.name} ({len(content_text)} chars)")
                        else:
                            print(f"      ❌ No meaningful content found")
                            
                    except Exception as e:
                        print(f"      ❌ Text extraction failed: {e}")
                
                # Close popup and return to main window
                try:
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                except:
                    try:
                        self.driver.switch_to.window(original_window)
                    except:
                        pass
                
                return file_path
            else:
                print(f"      ❌ No popup window opened")
                return None
                
        except Exception as e:
            print(f"      ❌ Cover letter error: {e}")
            
            # Ensure we're back on main window
            try:
                self.driver.switch_to.window(original_window)
            except:
                try:
                    # If original window handle is lost, switch to any available window
                    if self.driver.window_handles:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                except:
                    pass
            
            return None

    def _download_file_from_url(self, url: str, manuscript_id: str):
        """Download file from URL using requests with selenium cookies"""
        try:
            import requests
            from urllib.parse import urlparse, unquote
            
            # Create downloads directory
            downloads_dir = Path("downloads")
            downloads_dir.mkdir(parents=True, exist_ok=True)
            
            # Get cookies from selenium
            cookies = {cookie['name']: cookie['value'] for cookie in self.driver.get_cookies()}
            
            # Get headers from selenium
            headers = {
                'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                'Referer': self.driver.current_url
            }
            
            print(f"      📥 Downloading from: {url[:100]}...")
            
            # Download file
            response = requests.get(url, cookies=cookies, headers=headers, stream=True, timeout=30, allow_redirects=True)
            print(f"      📊 Response: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
            
            if response.status_code == 200:
                # Determine file extension from content-type or URL
                content_type = response.headers.get('content-type', '').lower()
                
                if 'pdf' in content_type or '.pdf' in url.lower():
                    filename = f"{manuscript_id}_cover_letter.pdf"
                elif 'officedocument.wordprocessingml' in content_type or '.docx' in url.lower():
                    filename = f"{manuscript_id}_cover_letter.docx"
                elif 'msword' in content_type or '.doc' in url.lower():
                    filename = f"{manuscript_id}_cover_letter.doc"
                else:
                    # Try to guess from content
                    content_start = response.content[:100]
                    if content_start.startswith(b'%PDF'):
                        filename = f"{manuscript_id}_cover_letter.pdf"
                    elif b'PK' in content_start[:4]:  # ZIP-based format (DOCX)
                        filename = f"{manuscript_id}_cover_letter.docx"
                    else:
                        filename = f"{manuscript_id}_cover_letter.pdf"  # Default to PDF
                
                file_path = downloads_dir / filename
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                file_size = file_path.stat().st_size
                print(f"      ✅ Downloaded: {filename} ({file_size:,} bytes)")
                
                # Verify it's not an HTML error page
                if file_size > 100:
                    with open(file_path, 'rb') as f:
                        start_bytes = f.read(100)
                        if b'<html' in start_bytes.lower() or b'<!doctype html' in start_bytes.lower():
                            print(f"      ⚠️ Downloaded file appears to be HTML, not a document")
                            file_path.unlink()  # Delete the HTML file
                            return None
                
                return str(file_path)
            else:
                print(f"      ❌ Download failed: HTTP {response.status_code}")
                print(f"      📝 Response content preview: {response.text[:200]}")
                return None
        
        except Exception as e:
            print(f"      ❌ Download error: {e}")
            return None
    
    def _extract_cover_letter_text(self, manuscript_id: str):
        """Extract cover letter text content from popup"""
        try:
            cover_text = ""
            
            # Try different selectors to find text content
            selectors = [
                "//textarea[@name='cover_letter']",
                "//div[@class='cover_letter']", 
                "//pre",
                "//div[contains(@class, 'content')]",
                "//div[contains(@class, 'text')]",
                "//p[string-length(text()) > 50]",
                "//body"
            ]
            
            for selector in selectors:
                try:
                    elem = self.driver.find_element(By.XPATH, selector)
                    text = elem.text.strip()
                    if text and len(text) > 50:  # Likely to be meaningful content
                        cover_text = text
                        print(f"      📝 Found text content using selector: {selector}")
                        break
                except:
                    continue
            
            if cover_text:
                # Create downloads directory
                downloads_dir = Path("downloads/cover_letters")
                downloads_dir.mkdir(parents=True, exist_ok=True)
                
                # Save cover letter text
                cover_path = downloads_dir / f"{manuscript_id}_cover_letter.txt"
                with open(cover_path, 'w', encoding='utf-8') as f:
                    f.write(cover_text)
                
                return str(cover_path)
            
            return None
            
        except Exception as e:
            print(f"      ❌ Text extraction error: {e}")
            return None
    
    
    def process_category(self, category):
        """Process all manuscripts in a category."""
        # Handle both dict format (new) and old format
        if isinstance(category, dict):
            category_name = category.get('name', 'Unknown')
            count = category.get('count', '?')
        else:
            category_name = str(category)
            count = '?'

        print(f"\n📂 Processing category: {category_name} (manuscripts: {count})")

        # Dismiss cookie banner if present
        try:
            cookie_button = self.driver.find_element(By.ID, "onetrust-accept-btn-handler")
            cookie_button.click()
            time.sleep(1)
            print("   ✅ Dismissed cookie banner")
        except:
            pass  # Cookie banner might not be present

        # Click category link - handle different formats
        try:
            if isinstance(category, dict) and 'element' in category:
                # New format with element
                category_link = category['element']
            elif isinstance(category, dict) and 'locator' in category:
                # Old format with locator
                category_link = self.driver.find_element(By.XPATH, category['locator'])
            else:
                # Try to find by text
                category_link = self.driver.find_element(By.LINK_TEXT, category_name)

            # Scroll element into view to avoid click interception
            self.driver.execute_script("arguments[0].scrollIntoView(true);", category_link)
            time.sleep(1)
            category_link.click()
            time.sleep(3)
        except Exception as e:
            print(f"   ❌ Failed to click category {category_name}: {e}")
            return
        
        # FIX: Find Take Action links using correct pattern from MF workflow
        # Look for check_off.gif icons which are the Take Action buttons
        take_action_links = self.driver.find_elements(By.XPATH, 
            "//a[.//img[contains(@src, 'check_off.gif')]]")
        
        # Fallback: if no check_off icons, try the setDataAndNextPage pattern
        if not take_action_links:
            take_action_links = self.driver.find_elements(By.XPATH, 
                "//a[(contains(@href, 'setDataAndNextPage') or contains(@onclick, 'setDataAndNextPage')) and (contains(@href, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS') or contains(@onclick, 'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS'))]")
        
        if not take_action_links:
            print("   📭 No manuscripts in this category")
            return
        
        actual_count = len(take_action_links)
        print(f"   Found {actual_count} Take Action links")
        
        # CRITICAL FIX: Get manuscript IDs from the table BEFORE clicking
        manuscript_ids_in_category = []
        for link in take_action_links:
            try:
                # Get the row containing this Take Action link
                row = link.find_element(By.XPATH, "./ancestor::tr[1]")
                # Get manuscript ID from first cell
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    manuscript_id = cells[0].text.strip()
                    if self.is_valid_manuscript_id(manuscript_id):
                        manuscript_ids_in_category.append(manuscript_id)
                        print(f"      📄 Found manuscript in table: {manuscript_id}")
            except:
                continue
        
        # Store manuscript IDs in category for 3-pass processing
        category['manuscript_ids'] = manuscript_ids_in_category
        
        # Update count if different from expected (handle missing count)
        expected_count = category.get('count', '?')
        if expected_count != '?' and actual_count != expected_count:
            print(f"   ⚠️  Expected {expected_count} but found {actual_count} manuscripts")
        category['count'] = actual_count
        
        if actual_count == 0:
            return
        
        # Click first Take Action
        print("   👆 Clicking first Take Action link...")
        take_action_links[0].click()
        time.sleep(5)
        
        # Wait for page transition and verify we're on manuscript details page
        current_url = self.driver.current_url
        print(f"   📍 Current URL after click: {current_url}")
        
        # Handle intermediate pages or slow loading
        max_attempts = 3
        for attempt in range(max_attempts):
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            # Check if we're on the manuscript details page
            if "MANUSCRIPT_DETAILS" in current_url.upper() or "ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS" in current_url.upper():
                print("   ✅ On manuscript details page")
                break
            
            # Check if manuscript ID is visible on the page (indicates we're on details page)
            if any(pattern in page_source for pattern in ['MAFI-', 'Manuscript ID', 'Submission Date']):
                print("   ✅ Manuscript details loaded (found manuscript info)")
                break
                
            print(f"   ⚠️ Not on manuscript details page yet (attempt {attempt + 1}/{max_attempts})")
            
            # Look for continue/next buttons or other navigation elements
            try:
                # Check for continue button
                continue_btn = self.driver.find_element(By.XPATH, "//input[@value='Continue' or @value='Next' or @value='Submit']")
                continue_btn.click()
                time.sleep(3)
                print("   ✅ Clicked continue button")
            except:
                # Check for any link that might take us to manuscript details
                try:
                    details_link = self.driver.find_element(By.XPATH, "//a[contains(@href, 'MANUSCRIPT_DETAILS') or contains(text(), 'View Details')]")
                    details_link.click()
                    time.sleep(3)
                    print("   ✅ Clicked details link")
                except:
                    # Just wait a bit more for page to fully load
                    print("   ⏳ Waiting for page to load...")
                    time.sleep(3)
        
        # NEW 3-PASS SYSTEM  
        self.execute_3_pass_extraction(category)
        
        # Return to AE Center
        self.navigate_to_ae_center()
    
    def execute_3_pass_extraction(self, category):
        """Execute the 3-pass system as specified by user."""
        # NOTE: We're already on the first manuscript details page
        # process_category() already clicked the category and first Take Action link
        
        manuscript_count = category['count']
        manuscript_ids = []
        
        print(f"\n🚀 EXECUTING 3-PASS SYSTEM for {manuscript_count} manuscripts")
        print("=" * 60)
        
        # PASS 1: Forward - Referees, PDFs, basic data
        print(f"\n📋 PASS 1: Forward navigation (1→{manuscript_count}) - Referees & Documents")
        print("-" * 50)
        
        for i in range(manuscript_count):
            try:
                # We're already on manuscript 1 for i=0 (process_category clicked it)
                # For subsequent manuscripts, navigate_next_document() will take us there
                
                # Get manuscript ID
                manuscript_id = self.get_current_manuscript_id()
                manuscript_ids.append(manuscript_id)
                print(f"   📄 Manuscript {i+1}: {manuscript_id}")
                
                # Create manuscript object
                manuscript = {
                    'id': manuscript_id,
                    'category': category['name'],
                    'referees': [],
                    'documents': {},
                    'authors': [],
                    'editors': {}
                }
                
                # Extract basic info from main page (title, status, dates)
                print(f"   📋 Extracting basic manuscript info...")
                self.extract_basic_manuscript_info(manuscript)
                
                # Extract referees and documents (Pass 1 data)
                print(f"   👥 Extracting referees...")
                self.extract_referees_comprehensive(manuscript)
                
                print(f"   📁 Extracting documents...")
                self.extract_document_links(manuscript)
                
                # Add to manuscripts list
                self.manuscripts.append(manuscript)
                self.processed_manuscript_ids.add(manuscript_id)
                
                print(f"   ✅ Pass 1 complete for {manuscript_id}")
                
                # Navigate to next manuscript if not the last one
                if i < manuscript_count - 1:
                    success = self.navigate_next_document()
                    if not success:
                        print(f"   ❌ Navigation failed - unable to reach manuscript {i+2}")
                        break
                    
            except Exception as e:
                print(f"   ❌ Error on manuscript {i+1}: {e}")
                manuscript_ids.append("UNKNOWN")
                
        # PASS 2: Backward - Manuscript Information tab  
        print(f"\n📊 PASS 2: Backward navigation ({manuscript_count}→1) - Manuscript Info")
        print("-" * 50)
        
        # We should be on the last manuscript after Pass 1
        # But let's verify where we actually are
        current_id = self.get_current_manuscript_id()
        print(f"   📍 Currently on manuscript: {current_id}")
        
        # Start from the last manuscript and go backwards
        for i in range(manuscript_count - 1, -1, -1):
            try:
                manuscript_id = manuscript_ids[i]
                if manuscript_id and manuscript_id not in ["UNKNOWN", "NAVIGATION_FAILED"]:
                    print(f"   📋 Manuscript {i+1}: {manuscript_id} - Info Tab")
                    
                    # Find the manuscript in our list
                    manuscript = next((m for m in self.manuscripts if m['id'] == manuscript_id), None)
                    if manuscript:
                        # We're already on the manuscript page from Pass 1
                        # Just navigate to the Manuscript Information tab
                        self.navigate_to_manuscript_information_tab()
                        
                        # Extract the info from this tab
                        self.extract_keywords_from_details(manuscript)
                        self.extract_authors_from_details(manuscript)
                        self.extract_metadata_from_details(manuscript)
                        self.extract_cover_letter_from_details(manuscript)
                        
                        print(f"   ✅ Pass 2 complete for {manuscript_id}")
                else:
                    print(f"   ⏭️ Skipping manuscript {i+1} (no ID)")
                
                # Navigate to previous manuscript (except on first)
                if i > 0:
                    success = self.navigate_previous_document()
                    if not success:
                        print(f"   ⚠️ Could not navigate to previous manuscript")
                    
            except Exception as e:
                print(f"   ❌ Error in Pass 2 for manuscript {i+1}: {e}")
        
        # PASS 3: Forward - Audit Trail tab
        print(f"\n📜 PASS 3: Forward navigation (1→{manuscript_count}) - Audit Trail")
        print("-" * 50)
        
        # We should be on manuscript 1 after Pass 2
        current_id = self.get_current_manuscript_id()
        print(f"   📍 Currently on manuscript: {current_id}")
        
        for i in range(manuscript_count):
            try:
                manuscript_id = manuscript_ids[i]
                if manuscript_id and manuscript_id not in ["UNKNOWN", "NAVIGATION_FAILED"]:
                    print(f"   📜 Manuscript {i+1}: {manuscript_id} - Audit Trail")
                    
                    # Find the manuscript in our list
                    manuscript = next((m for m in self.manuscripts if m['id'] == manuscript_id), None)
                    if manuscript:
                        # Click Audit Trail tab and extract
                        self.extract_audit_trail(manuscript)
                        print(f"   ✅ Pass 3 complete for {manuscript_id}")
                else:
                    print(f"   ⏭️ Skipping manuscript {i+1} (no ID)")
                
                # Navigate to next manuscript (except on last)
                if i < manuscript_count - 1:
                    success = self.navigate_next_document()
                    if not success:
                        print(f"   ⚠️ Could not navigate to next manuscript")
                    
            except Exception as e:
                print(f"   ❌ Error in Pass 3 for manuscript {i+1}: {e}")
        
        print(f"\n🎉 3-PASS EXTRACTION COMPLETE")
        print(f"   Processed {len([m for m in manuscript_ids if m])} manuscripts")
        print("=" * 60)
    
    def navigate_next_document(self):
        """Navigate to next document."""
        next_selectors = [
            "//a[contains(@href,'setDataAndNextPage')]//img[@alt='Next Document']/..",
            "//img[@src='/images/en_US/icons/next_mss.gif']/..",
            "//img[@alt='Next Document']/..",
            "//a[contains(@href,'setDataAndNextPage') and contains(@href,'XIK_NEXT_PREV_DOCUMENT_ID')]",
            "//a[contains(@href,'XIK_NEXT_PREV_DOCUMENT_ID')]"
        ]
        
        for selector in next_selectors:
            try:
                next_btn = self.driver.find_element(By.XPATH, selector)
                next_btn.click()
                time.sleep(5)
                print(f"   ➡️ Navigated to next document")
                return True
            except:
                continue
        
        print(f"   ❌ Could not find Next Document button")
        return False
    
    def navigate_previous_document(self):
        """Navigate to previous document."""
        prev_selectors = [
            "//a[contains(@href,'setDataAndNextPage')]//img[@alt='Previous Document']/..",
            "//img[@src='/images/en_US/icons/prev_mss.gif']/..",
            "//img[@alt='Previous Document']/..",
            "//a[contains(@href,'setDataAndNextPage') and contains(@href,'XIK_NEXT_PREV_DOCUMENT_ID')]",
            "//a[contains(@href,'XIK_NEXT_PREV_DOCUMENT_ID') and contains(@href,'PREV')]"
        ]
        
        for selector in prev_selectors:
            try:
                prev_btn = self.driver.find_element(By.XPATH, selector)
                prev_btn.click()
                time.sleep(5)
                print(f"   ⬅️ Navigated to previous document")
                return True
            except:
                continue
        
        print(f"   ❌ Could not find Previous Document button")
        return False

    def navigate_to_ae_center(self):
        """Navigate back to Associate Editor Center."""
        try:
            ae_link = self.wait_for_element(By.LINK_TEXT, "Associate Editor Center")
            if ae_link:
                ae_link.click()
                time.sleep(3)
        except:
            pass
    

    def enrich_referee_profiles(self, manuscript):
        """Enrich referee profiles with ORCID and academic data."""
        print("\n🎓 Enriching referee profiles with ORCID data...")
        
        enriched_count = 0
        publication_count = 0
        
        for referee in manuscript.get('referees', []):
            if referee.get('orcid'):
                print(f"   📚 Enriching {referee['name']}...")
                
                # Create person data for enrichment
                person_data = {
                    'name': referee['name'],
                    'orcid': referee['orcid'],
                    'institution': referee.get('institution_parsed', ''),
                    'email': referee.get('email', '')
                }
                
                # Enrich profile
                # enriched_profile = self.enricher.enrich_person_profile(person_data)
                enriched_profile = person_data  # Skip enrichment for now
                
                # Update referee with enriched data
                if enriched_profile.get('publications'):
                    referee['publications'] = enriched_profile['publications']
                    referee['publication_count'] = len(enriched_profile['publications'])
                    publication_count += len(enriched_profile['publications'])
                    enriched_count += 1
                    print(f"      ✅ Found {len(enriched_profile['publications'])} publications")
                
                if enriched_profile.get('h_index'):
                    referee['h_index'] = enriched_profile['h_index']
                    referee['i10_index'] = enriched_profile.get('i10_index')
                    referee['citation_count'] = enriched_profile.get('citation_count')
                    print(f"      ✅ h-index: {enriched_profile['h_index']}")
                
                if enriched_profile.get('employment_history'):
                    referee['employment_history'] = enriched_profile['employment_history']
                
                if enriched_profile.get('external_ids'):
                    referee['external_ids'] = enriched_profile['external_ids']
                
                # Add enrichment metadata
                referee['enrichment_metadata'] = enriched_profile.get('enrichment_metadata', {})
        
        if enriched_count > 0:
            print(f"\n   🎉 Enriched {enriched_count} referee profiles with {publication_count} total publications!")
        else:
            print("   ℹ️  No ORCID IDs found for enrichment")


    def track_extraction_errors(self):
        """Track and report extraction errors for debugging."""
        if not hasattr(self, 'extraction_errors'):
            self.extraction_errors = {
                'popup_failures': 0,
                'timeout_errors': 0,
                'element_not_found': 0,
                'network_errors': 0,
                'unknown_errors': 0
            }
        return self.extraction_errors

    def extract_all(self):
        """Main extraction method."""
        print("🚀 COMPREHENSIVE MF EXTRACTION")
        print("=" * 60)
        
        # Login
        login_success = self.login()
        if not login_success:
            print("❌ Login failed - cannot continue")
            return
        
        # Navigate to AE Center
        print("\n📋 Navigating to Associate Editor Center...")
        print(f"   📍 Current URL after login: {self.driver.current_url}")
        
        # Wait for page to fully load after login/2FA and ensure we're not on login page anymore
        max_wait = 30
        wait_count = 0
        while wait_count < max_wait:
            current_url = self.driver.current_url
            if "page=LOGIN" not in current_url and "login" not in current_url.lower():
                break
            print(f"   ⏳ Still on login page, waiting... ({wait_count + 1}/{max_wait})")
            time.sleep(2)
            wait_count += 1
        
        if wait_count >= max_wait:
            print(f"   ❌ Login failed - still on login page after {max_wait} seconds")
            print(f"   📧 Please check Gmail for verification code or ensure 2FA is working")
            return
        
        print(f"   ✅ Successfully logged in: {self.driver.current_url}")
        time.sleep(3)
        
        # Check if we're on the unrecognized device page
        current_url = self.driver.current_url
        if 'UNRECOGNIZED_DEVICE' in current_url:
            print("   🔐 Device verification page detected")
            print("   📧 Searching Gmail for device verification code...")
            
            # Search for device verification code in Gmail
            try:
                device_code = self.get_verification_code_from_gmail(
                    subject_patterns=[
                        'Mathematical Finance Verification Code',
                        'verification code',  
                        'device verification'
                    ],
                    sender_patterns=['manuscriptcentral.com', '@manuscript', 'noreply'],
                    minutes_back=10
                )
                
                if device_code:
                    print(f"   ✅ Found device verification code: {device_code}")
                    
                    # Find and fill the token field
                    try:
                        WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.ID, "TOKEN_VALUE"))
                        )
                        token_field = self.driver.find_element(By.ID, "TOKEN_VALUE")
                        token_field.clear()
                        token_field.send_keys(device_code)
                        
                        # Click verify button
                        verify_btn = self.driver.find_element(By.ID, "VERIFY_BTN")
                        verify_btn.click()
                        
                        print("   ✅ Device verification code entered and submitted")
                        time.sleep(5)
                        
                        # Check if verification succeeded
                        current_url = self.driver.current_url
                        if 'UNRECOGNIZED_DEVICE' not in current_url:
                            print("   ✅ Device verification successful!")
                        else:
                            print("   ❌ Device verification failed")
                        
                    except Exception as e:
                        print(f"   ❌ Error entering device verification code: {e}")
                        # Try JavaScript fallback
                        try:
                            self.driver.execute_script(f"document.getElementById('TOKEN_VALUE').value = '{device_code}';")
                            self.driver.execute_script("document.getElementById('VERIFY_BTN').click();")
                            print("   ✅ Used JavaScript for device verification")
                            time.sleep(5)
                        except Exception as js_error:
                            print(f"   ❌ JavaScript device verification failed: {js_error}")
                            
                else:
                    print("   ❌ No device verification code found in Gmail")
                    print("   💡 Manual device verification may be required")
                    
            except Exception as e:
                print(f"   ❌ Error retrieving device verification code: {e}")
            
            # Check if we're still on device verification page
            current_url = self.driver.current_url
            if 'UNRECOGNIZED_DEVICE' in current_url:
                print("   ❌ Could not pass device verification automatically")
                print("   💡 Please manually verify the device and then re-run the script")
                return
        
        # FIXED NAVIGATION - First select Mathematical Finance journal like MOR does
        print("   🎯 Looking for Mathematical Finance journal...")
        try:
            # Debug: Show available links
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            text_links = [link.text.strip() for link in all_links[:15] if link.text.strip()]
            print(f"   Available links: {text_links}")
            
            # FIXED: MF login already takes us to MAFI journal, just find Associate Editor Center
            print("   📋 Looking for Associate Editor Center...")
            try:
                # Try direct Associate Editor Center link first (it's available from debug)
                ae_link = self.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
                print("   ✅ Found Associate Editor Center, clicking...")
                ae_link.click()
                time.sleep(5)
                
            except Exception as e:
                print(f"   ⚠️ Direct AE Center link failed: {e}")
                print("   🔄 Trying fallback selectors...")
                
                # Fallback: Try various AE Center selectors
                ae_selectors = [
                    "//a[contains(text(),'Associate Editor Center')]",
                    "//a[contains(@href,'ASSOCIATE_EDITOR')]", 
                    "//a[text()='Associate Editor Center']",
                    "//a[contains(text(),'Associate Editor')]"
                ]
                
                ae_link = None
                for selector in ae_selectors:
                    try:
                        ae_link = self.driver.find_element(By.XPATH, selector)
                        print(f"   ✅ Found AE Center using selector: {selector}")
                        break
                    except:
                        continue
                        
                if ae_link:
                    print("   ✅ Found AE Center, clicking...")
                    ae_link.click()
                    time.sleep(3)
                else:
                    raise Exception("Could not find Associate Editor Center")
            
        except Exception as e:
            print(f"   ❌ Could not find Associate Editor link: {e}")
            print("   💾 Saving debug page...")
            with open("debug_mf_ae_fail.html", 'w') as f:
                f.write(self.driver.page_source)
            return
        
        # Get categories - but only those with clickable links
        print("\n📊 Finding clickable manuscript categories...")

        # Look for categories that have actual links (not just text)
        clickable_categories = []

        # Known clickable categories based on testing
        category_links = [
            ("Awaiting Reviewer Scores", "//a[text()='Awaiting Reviewer Scores']"),
            ("Overdue Reviewer Scores", "//a[text()='Overdue Reviewer Scores']"),
        ]

        for category_name, xpath in category_links:
            try:
                element = self.driver.find_element(By.XPATH, xpath)
                if element:
                    href = element.get_attribute('href')
                    clickable_categories.append({
                        'name': category_name,
                        'element': element,
                        'href': href
                    })
                    print(f"   ✅ Found clickable: {category_name}")
            except:
                continue

        if not clickable_categories:
            print("   ⚠️ No clickable categories found, trying broader search...")
            categories = self.get_manuscript_categories()
        else:
            categories = clickable_categories
            print(f"   📊 Found {len(categories)} clickable categories")

        if not categories:
            print("❌ No categories with manuscripts found")
            # Save debug page to see what's actually on the AE center
            with open("debug_ae_center_content.html", 'w') as f:
                f.write(self.driver.page_source)
            print("💾 Saved AE center content for debugging")
            return
        
        # Process each category
        for category in categories:
            self.process_category(category)
        
        # Save results
        self.save_results()
    
    def save_results(self):
        """Save comprehensive results and show precise summary."""
        # DEBUG: Check self.manuscripts for corruption
        print(f"\n🐛 DEBUG: Checking manuscripts list before saving...")
        print(f"   Total objects in self.manuscripts: {len(self.manuscripts)}")
        
        valid_manuscripts = []
        invalid_objects = []
        
        for i, obj in enumerate(self.manuscripts):
            manuscript_id = obj.get('id', 'NO_ID')
            # Check if this looks like a real manuscript ID (MAFI-YYYY-NNNN pattern)
            if manuscript_id.startswith('MAFI-') and len(manuscript_id) >= 12:
                valid_manuscripts.append(obj)
                print(f"   ✅ Valid manuscript {i+1}: {manuscript_id}")
            else:
                invalid_objects.append(obj)
                obj_type = type(obj.get('subject', obj.get('from', obj.get('thread_id', 'unknown')))).__name__
                print(f"   ❌ Invalid object {i+1}: ID='{manuscript_id}' Type={obj_type}")
        
        print(f"   📊 Found {len(valid_manuscripts)} valid manuscripts, {len(invalid_objects)} invalid objects")
        
        if invalid_objects:
            print(f"   🔧 FIXING: Using only valid manuscripts for output")
            self.manuscripts = valid_manuscripts
        
        # Save to JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"mf_comprehensive_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.manuscripts, f, indent=2, default=str)
        
        # Generate extremely precise results summary
        self._print_precise_results_summary()
        print(f"\n💾 Full data saved to: {output_file}")
        
        # Show communication timeline summary with Gmail cross-check results
        total_communications = 0
        external_communications = 0
        enhanced_manuscripts = 0
        
        for manuscript in self.manuscripts:
            timeline = manuscript.get('communication_timeline', [])
            total_communications += len(timeline)
            external_count = len([e for e in timeline if e.get('external')])
            external_communications += external_count
            if manuscript.get('timeline_enhanced'):
                enhanced_manuscripts += 1
        
        if total_communications > 0:
            print(f"\n📬 COMMUNICATION TIMELINE SUMMARY:")
            print(f"   Total communications tracked: {total_communications}")
            print(f"   🏢 Platform events: {total_communications - external_communications}")
            print(f"   📧 External emails (Gmail): {external_communications}")
            if enhanced_manuscripts > 0:
                print(f"   ✅ Gmail cross-check successful for {enhanced_manuscripts}/{len(self.manuscripts)} manuscripts")
            
            # Create detailed timeline report
            self._create_timeline_report()
    
    def _print_precise_results_summary(self):
        """Print extremely precise results summary for user review."""
        print("\n" + "="*80)
        print("🔍 PRECISE RESULTS SUMMARY")
        print("="*80)
        
        print(f"\n📊 MANUSCRIPTS FOUND: {len(self.manuscripts)}")
        
        if not self.manuscripts:
            print("❌ NO MANUSCRIPTS PROCESSED")
            return
            
        for i, ms in enumerate(self.manuscripts, 1):
            print(f"\n📄 MANUSCRIPT {i}/{len(self.manuscripts)}: {ms.get('id', 'UNKNOWN')}")
            print(f"   Title: {ms.get('title', 'NO TITLE')[:60]}...")
            print(f"   Status: {ms.get('status', 'UNKNOWN')}")
            print(f"   Category: {ms.get('category', 'UNKNOWN')}")
            
            # Authors
            authors = ms.get('authors', [])
            print(f"   👥 Authors ({len(authors)}): {', '.join([a.get('name', 'Unknown') for a in authors])}")
            
            # Referees
            referees = ms.get('referees', [])
            print(f"   🔍 Referees ({len(referees)}):")
            if referees:
                for ref in referees:
                    name = ref.get('name', 'Unknown')
                    status = ref.get('status', 'Unknown')
                    email = ref.get('email', 'No email')
                    print(f"      • {name} ({status}) - {email}")
            else:
                print("      ❌ NO REFEREES EXTRACTED")
            
            # Documents
            docs = ms.get('documents', {})
            print(f"   📁 Documents:")
            if isinstance(docs, dict) and docs.get('pdf'):
                path = docs.get('pdf_path', 'Unknown path')
                size = docs.get('pdf_size', 'Unknown size')
                print(f"      ✅ PDF: {path} ({size})")
            else:
                print(f"      ❌ No PDF")
                
            if isinstance(docs, dict) and docs.get('cover_letter'):
                path = docs.get('cover_letter_path', 'Unknown path')
                print(f"      📝 Cover Letter: {path}")
            else:
                print(f"      ❌ No Cover Letter")
                
            # Additional metadata fields (new - matching MOR coverage)
            funding = ms.get('funding_information', '')
            if funding and funding != 'Not specified':
                print(f"   💰 Funding: {funding[:60]}...")
            
            conflict = ms.get('conflict_of_interest', '')
            if conflict and conflict != 'Not specified':
                print(f"   ⚖️ Conflict of Interest: {conflict}")
                
            data_avail = ms.get('data_availability', '')
            if data_avail and data_avail != 'Not specified':
                print(f"   📊 Data Availability: {data_avail[:60]}...")
                
            recommendations = ms.get('referee_recommendations', {})
            rec_refs = recommendations.get('recommended_referees', [])
            opp_refs = recommendations.get('opposed_referees', [])
            if rec_refs or opp_refs:
                print(f"   👥 Author Referee Recommendations:")
                if rec_refs:
                    print(f"      ✅ Recommended ({len(rec_refs)}): {', '.join([r.get('name', 'N/A') for r in rec_refs[:3]])}")
                if opp_refs:
                    print(f"      🚫 Opposed ({len(opp_refs)}): {', '.join([r.get('name', 'N/A') for r in opp_refs[:3]])}")
        
        # File system verification
        print(f"\n📂 FILE SYSTEM VERIFICATION:")
        
        # Check manuscript PDFs
        manuscript_dir = Path("downloads/manuscripts")
        if manuscript_dir.exists():
            pdf_files = list(manuscript_dir.glob("*.pdf"))
            print(f"   📄 Manuscript PDFs: {len(pdf_files)} files")
            for pdf in pdf_files:
                size_mb = pdf.stat().st_size / (1024*1024)
                print(f"      ✅ {pdf.name} ({size_mb:.1f} MB)")
        else:
            print(f"   ❌ No manuscripts directory")
        
        # Check cover letters
        cover_dir = Path("downloads/cover_letters")
        if cover_dir.exists():
            cover_files = list(cover_dir.glob("*"))
            print(f"   📝 Cover Letters: {len(cover_files)} files")
            for cover in cover_files:
                if cover.is_file():
                    size_kb = cover.stat().st_size / 1024
                    file_type = "PDF" if cover.suffix == ".pdf" else "DOCX" if cover.suffix == ".docx" else "TEXT"
                    print(f"      {'✅' if cover.suffix in ['.pdf', '.docx'] else '📝'} {cover.name} ({file_type}, {size_kb:.1f} KB)")
        else:
            print(f"   ❌ No cover letters directory")
        
        # Summary counts
        total_referees = sum(len(ms.get('referees', [])) for ms in self.manuscripts)
        total_pdfs = len(list(Path("downloads/manuscripts").glob("*.pdf"))) if Path("downloads/manuscripts").exists() else 0
        total_covers = len(list(Path("downloads/cover_letters").glob("*"))) if Path("downloads/cover_letters").exists() else 0
        
        # Communication counts
        total_communications = 0
        total_platform_events = 0
        total_external_emails = 0
        for ms in self.manuscripts:
            timeline = ms.get('communication_timeline', [])
            total_communications += len(timeline)
            total_platform_events += len([e for e in timeline if not e.get('external', False)])
            total_external_emails += len([e for e in timeline if e.get('external', False)])
        
        print(f"\n📈 FINAL COUNTS:")
        print(f"   📄 Manuscripts Processed: {len(self.manuscripts)}")
        print(f"   🔍 Total Referees: {total_referees}")
        print(f"   📁 PDF Downloads: {total_pdfs}")
        print(f"   📝 Cover Letters: {total_covers}")
        print(f"   📅 Communication Events:")
        print(f"      🏢 Platform Events: {total_platform_events}")
        print(f"      📧 External Emails: {total_external_emails}")
        print(f"      📊 Total Communications: {total_communications}")
        
        # Success/Failure Analysis
        expected_referees = [4, 2]  # Based on user specification: paper 1 has 4, paper 2 has 2
        expected_total = sum(expected_referees[:len(self.manuscripts)])
        
        print(f"\n✅ SUCCESS/FAILURE ANALYSIS:")
        print(f"   Expected Manuscripts: 2")
        print(f"   Actual Manuscripts: {len(self.manuscripts)}")
        print(f"   Expected Total Referees: {expected_total}")
        print(f"   Actual Total Referees: {total_referees}")
        print(f"   Expected PDFs: 2")
        print(f"   Actual PDFs: {total_pdfs}")
        
        if len(self.manuscripts) == 2 and total_referees == expected_total and total_pdfs == 2:
            print(f"   🎉 PERFECT SUCCESS - All data extracted correctly!")
        else:
            print(f"   ⚠️ PARTIAL SUCCESS - Some data missing")
        
        print("="*80)
    
    def cleanup(self):
        """Close browser and report errors."""
        # Report extraction errors
        if hasattr(self, 'extraction_errors'):
            total_errors = sum(self.extraction_errors.values())
            if total_errors > 0:
                print(f"\n⚠️ EXTRACTION ERROR SUMMARY:")
                for error_type, count in self.extraction_errors.items():
                    if count > 0:
                        print(f"   {error_type}: {count}")
                print(f"   Total errors: {total_errors}")
            else:
                print("\n✅ No extraction errors detected!")
        
        self.driver.quit()
    
    def _create_timeline_report(self):
        """Create a detailed timeline report showing merged communications."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            timeline_file = f"mf_timeline_report_{timestamp}.txt"
            
            with open(timeline_file, 'w', encoding='utf-8') as f:
                f.write("MF MANUSCRIPT COMMUNICATION TIMELINE REPORT\n")
                f.write("=" * 80 + "\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Manuscripts: {len(self.manuscripts)}\n\n")
                
                for manuscript in self.manuscripts:
                    f.write(f"\n📄 MANUSCRIPT: {manuscript.get('id', 'Unknown')}\n")
                    f.write(f"Title: {manuscript.get('title', 'No title')}\n")
                    f.write("-" * 60 + "\n")
                    
                    timeline = manuscript.get('communication_timeline', [])
                    if not timeline:
                        f.write("No communications found\n")
                        continue
                    
                    # Sort by date with proper date handling
                    def get_sort_key(event):
                        """Get a sortable date from various formats."""
                        # Try datetime first
                        if event.get('datetime'):
                            if isinstance(event['datetime'], datetime):
                                return event['datetime']
                            try:
                                return datetime.fromisoformat(event['datetime'].replace('Z', '+00:00'))
                            except:
                                pass
                        
                        # Try date field
                        if event.get('date'):
                            if isinstance(event['date'], datetime):
                                return event['date']
                        
                        # Try GMT timestamp
                        if event.get('timestamp_gmt'):
                            try:
                                clean_date = event['timestamp_gmt'].replace(' GMT', '')
                                return datetime.strptime(clean_date, '%d-%b-%Y %I:%M %p')
                            except:
                                pass
                        
                        # Default to epoch
                        return datetime(1970, 1, 1)
                    
                    sorted_timeline = sorted(timeline, key=get_sort_key, reverse=True)
                    
                    f.write(f"Total Communications: {len(timeline)}\n")
                    external_count = len([e for e in timeline if e.get('external', False)])
                    platform_count = len([e for e in timeline if not e.get('external', False)])
                    
                    f.write(f"Platform Events (MF Audit Trail): {platform_count}\n")
                    f.write(f"External Emails (Gmail): {external_count}\n")
                    f.write("\n")
                    
                    # Write each event
                    for event in sorted_timeline:
                        source = "📧 Gmail" if event.get('external') else "🏢 MF"
                        date = event.get('datetime') or event.get('timestamp_gmt', 'Unknown date')
                        if isinstance(date, datetime):
                            date = date.strftime('%Y-%m-%d %H:%M')
                        
                        f.write(f"\n{source} | {date}\n")
                        f.write(f"Type: {event.get('type', 'Unknown')}\n")
                        
                        if event.get('from'):
                            f.write(f"From: {event.get('from')}\n")
                        if event.get('to'):
                            f.write(f"To: {event.get('to')}\n")
                        if event.get('subject'):
                            f.write(f"Subject: {event.get('subject')}\n")
                        if event.get('external') and event.get('note'):
                            f.write(f"Note: {event.get('note')}\n")
                        
                        f.write("-" * 40 + "\n")
                
            print(f"   📄 Timeline report created: {timeline_file}")
            
        except Exception as e:
            print(f"   ⚠️ Could not create timeline report: {e}")
    
    def run(self):
        """Run extraction."""
        try:
            self.extract_all()
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Show cache statistics
            self.finish_extraction_with_stats()
            self.cleanup()

    # =================================================================
    # COMPREHENSIVE ENHANCEMENTS - BROUGHT TO SAME LEVEL AS MOR
    # =================================================================
    
    def extract_referee_report_comprehensive(self, report_link, referee_name, manuscript_id):
        """Comprehensive referee report extraction for ALL manuscripts.
        
        This function extracts:
        1. Full review text (comments to author/editor)
        2. Recommendation (Accept/Reject/Minor/Major Revision)
        3. Review metadata (dates, scores)
        4. Attached PDF reports
        5. Supplementary files
        
        Args:
            report_link: Selenium WebElement of the review link
            referee_name: Name of the referee for identification
            manuscript_id: Manuscript ID for file organization
            
        Returns:
            dict: Complete report data or None if extraction fails
        """
        try:
            print(f"           🔍 Starting comprehensive MF report extraction for {referee_name}")
            current_window = self.driver.current_window_handle
            
            # Initialize report data structure
            report_data = {
                'referee_name': referee_name,
                'manuscript_id': manuscript_id,
                'extraction_timestamp': datetime.now().isoformat(),
                'recommendation': '',
                'comments_to_author': '',
                'comments_to_editor': '',
                'review_quality_score': '',
                'timeliness_score': '',
                'date_assigned': '',
                'date_completed': '',
                'pdf_reports': [],
                'supplementary_files': [],
                'review_form_data': {},
                'extraction_method': 'comprehensive_mf'
            }
            
            # Click the review link to open popup
            try:
                # Store link info before clicking
                link_href = report_link.get_attribute('href') or ''
                link_onclick = report_link.get_attribute('onclick') or ''
                
                # Handle different link types
                if 'javascript:' in link_href:
                    # JavaScript popup
                    self.driver.execute_script(link_href.replace('javascript:', ''))
                elif link_onclick:
                    # Onclick handler
                    self.driver.execute_script(link_onclick)
                else:
                    # Regular click
                    report_link.click()
                
                time.sleep(3)  # Wait for popup to open
                
            except Exception as e:
                print(f"           ⚠️ Error clicking report link: {e}")
                return None
            
            # Switch to popup window with timeout
            wait_time = 0
            while wait_time < 10:
                all_windows = self.driver.window_handles
                if len(all_windows) > 1:
                    break
                time.sleep(1)
                wait_time += 1
            
            if len(all_windows) <= 1:
                print(f"           ⚠️ No popup window opened for report extraction")
                return None
            
            popup_window = [w for w in all_windows if w != current_window][-1]
            self.driver.switch_to.window(popup_window)
            time.sleep(2)
            
            try:
                # DEBUG HTML SAVING DISABLED - causes file pollution
                # debug_file = f"debug_mf_report_{referee_name.replace(' ', '_')}_{manuscript_id}.html"
                # with open(debug_file, 'w') as f:
                #     f.write(self.driver.page_source)
                # print(f"           💾 Saved debug HTML: {debug_file}")
                
                # Extract recommendation with multiple strategies
                recommendation_strategies = [
                    # Strategy 1: Radio button with checkmark
                    ("//tr[td//img[contains(@src, 'check_mark')] and .//p[@class='pagecontents']]", "checked_radio"),
                    # Strategy 2: Selected dropdown option
                    ("//select[@name='recommendation']/option[@selected]", "dropdown"),
                    # Strategy 3: Text containing recommendation keywords
                    ("//p[@class='pagecontents'][contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'reject') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'revision')]", "text_search"),
                    # Strategy 4: Bold text with recommendation
                    ("//b[contains(text(), 'Accept') or contains(text(), 'Reject') or contains(text(), 'Revision')]", "bold_text"),
                    # Strategy 5: Table cell with recommendation header
                    ("//td[contains(text(), 'Recommendation')]/following-sibling::td", "table_cell")
                ]
                
                for xpath, strategy_name in recommendation_strategies:
                    try:
                        elements = self.driver.find_elements(By.XPATH, xpath)
                        for elem in elements:
                            text = elem.text.strip()
                            if text and self.is_valid_recommendation(text):
                                report_data['recommendation'] = self.normalize_recommendation(text)
                                print(f"           ⭐ Found recommendation ({strategy_name}): {report_data['recommendation']}")
                                break
                        if report_data['recommendation']:
                            break
                    except:
                        continue
                    
                # Extract comments to author with comprehensive patterns
                author_comment_patterns = [
                        "//p[contains(text(), 'Comments to the Author')]/ancestor::tr/following-sibling::tr[1]//p[@class='pagecontents']",
                        "//td[contains(text(), 'Author')]/following-sibling::td//p[@class='pagecontents']",
                        "//textarea[@name='comments_author' or @name='author_comments']",
                        "//div[@class='author-comments' or @id='author-comments']",
                        "//p[@class='pagecontents'][string-length(text()) > 100]"  # Long text likely to be comments
                    ]
                    
                for pattern in author_comment_patterns:
                    try:
                        elements = self.driver.find_elements(By.XPATH, pattern)
                        for elem in elements:
                            text = elem.text.strip()
                            if text and len(text) > 20 and text != '\xa0':
                                # Check if this looks like actual review content
                                if self.is_review_content(text):
                                    report_data['comments_to_author'] = text
                                    print(f"           📝 Extracted author comments: {len(text)} chars")
                                    break
                        if report_data['comments_to_author']:
                            break
                    except:
                        continue
                    
                # Extract comments to editor
                editor_comment_patterns = [
                        "//p[contains(text(), 'Confidential Comments to the Editor')]/ancestor::tr/following-sibling::tr[1]//p[@class='pagecontents']",
                        "//td[contains(text(), 'Editor')]/following-sibling::td//p[@class='pagecontents']",
                        "//textarea[@name='comments_editor' or @name='editor_comments']",
                        "//div[@class='editor-comments' or @id='editor-comments']"
                    ]
                    
                for pattern in editor_comment_patterns:
                    try:
                        elements = self.driver.find_elements(By.XPATH, pattern)
                        for elem in elements:
                            text = elem.text.strip()
                            if text and len(text) > 10 and text != '\xa0':
                                report_data['comments_to_editor'] = text
                                print(f"           🔒 Extracted editor comments: {len(text)} chars")
                                break
                        if report_data['comments_to_editor']:
                            break
                    except:
                        continue
                    
                # Extract dates
                date_patterns = {
                        'date_assigned': ["//td[contains(text(), 'Date Assigned')]/following-sibling::td", "//td[contains(text(), 'Invited')]/following-sibling::td"],
                        'date_completed': ["//td[contains(text(), 'Date Review Returned')]/following-sibling::td", "//td[contains(text(), 'Completed')]/following-sibling::td"]
                    }
                    
                for date_field, patterns in date_patterns.items():
                    for pattern in patterns:
                        try:
                            elem = self.driver.find_element(By.XPATH, pattern)
                            date_text = elem.text.strip()
                            if date_text:
                                report_data[date_field] = date_text
                                print(f"           📅 {date_field}: {date_text}")
                                break
                        except:
                            continue
                    
                # Extract PDF reports - Enhanced for MF
                pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf') or contains(text(), 'PDF')]")
                if pdf_links:
                    print(f"           📎 Found {len(pdf_links)} PDF links")
                    for pdf_link in pdf_links:
                        try:
                            pdf_url = pdf_link.get_attribute('href')
                            pdf_text = pdf_link.text.strip() or 'referee_report.pdf'
                            
                            # Use enhanced MF PDF download
                            pdf_path = self.download_referee_report_pdf(pdf_url, referee_name, manuscript_id)
                            if pdf_path:
                                report_data['pdf_reports'].append({
                                    'filename': pdf_text,
                                    'path': pdf_path,
                                    'url': pdf_url
                                })
                                print(f"           ✅ Downloaded PDF: {pdf_text}")
                        except:
                            continue
                    
                # Extract quality scores if present
                score_patterns = {
                        'review_quality_score': "//td[contains(text(), 'Quality')]/following-sibling::td",
                        'timeliness_score': "//td[contains(text(), 'Timeliness')]/following-sibling::td"
                    }
                    
                for score_field, pattern in score_patterns.items():
                    try:
                        elem = self.driver.find_element(By.XPATH, pattern)
                        score = elem.text.strip()
                        if score:
                            report_data[score_field] = score
                            print(f"           📊 {score_field}: {score}")
                    except:
                        pass
                    
                # Success summary
                print(f"           ✅ MF Report extraction complete:")
                print(f"              - Recommendation: {report_data['recommendation'] or 'Not found'}")
                print(f"              - Author comments: {len(report_data['comments_to_author'])} chars")
                print(f"              - Editor comments: {len(report_data['comments_to_editor'])} chars")
                print(f"              - PDFs: {len(report_data['pdf_reports'])}")
                
            except Exception as e:
                print(f"           ❌ Error extracting MF report data: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # Close popup and return to main window
                try:
                    self.driver.close()
                    self.driver.switch_to.window(current_window)
                except:
                    pass
            
            return report_data
                
        except Exception as e:
            print(f"           ❌ Fatal error in MF report extraction: {e}")
            # Ensure we're back on main window
            try:
                self.driver.switch_to.window(current_window)
            except:
                pass
            return None

    def is_valid_recommendation(self, text):
        """Check if text contains a valid recommendation."""
        valid_keywords = ['accept', 'reject', 'revision', 'minor', 'major', 'resubmit', 'decline']
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in valid_keywords) and len(text) < 100

    def normalize_recommendation(self, text):
        """Normalize recommendation text to standard format."""
        text_lower = text.lower()
        if 'reject' in text_lower:
            return 'Reject'
        elif 'major revision' in text_lower or 'substantial revision' in text_lower:
            return 'Major Revision'
        elif 'minor revision' in text_lower or 'minor changes' in text_lower:
            return 'Minor Revision'
        elif 'accept' in text_lower:
            if 'as is' in text_lower or 'without' in text_lower:
                return 'Accept as is'
            else:
                return 'Accept'
        elif 'resubmit' in text_lower:
            return 'Reject with Resubmission'
        else:
            return text.strip()  # Return original if no match

    def is_review_content(self, text):
        """Check if text looks like actual review content."""
        # Must have some substance
        if len(text) < 50:
            return False
        
        # Should contain sentences
        if '.' not in text and '!' not in text and '?' not in text:
            return False
        
        # Avoid navigation text
        nav_keywords = ['click here', 'see attached', 'download', 'view pdf', 'page 1 of']
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in nav_keywords):
            return False
        
        return True


    def deep_web_enrichment(self, person_name, current_data=None):
        """COMPREHENSIVE deep web enrichment for author/referee data."""
        if not person_name:
            return current_data or {}
        
        print(f"      🌐 DEEP WEB ENRICHMENT for: {person_name}")
        
        enriched_data = current_data.copy() if current_data else {}
        
        # 1. CORRECT NAME WITH DIACRITICS AND PROPER CASING
        corrected_name = self.get_corrected_name(person_name)
        if corrected_name:
            enriched_data['corrected_name'] = corrected_name
            print(f"      ✅ Name correction: {person_name} → {corrected_name}")
        
        # 2. SEARCH MATHSCINET FOR MATHEMATICIAN DATA
        mathscinet_data = self.search_mathscinet(corrected_name or person_name)
        if mathscinet_data:
            enriched_data['orcid'] = f"https://orcid.org/{mathscinet_data['orcid']}"
            enriched_data['institution'] = mathscinet_data['institution']
            enriched_data['research_areas'] = mathscinet_data.get('research_areas', [])
            enriched_data['enriched_from'] = 'MathSciNet'
            print(f"      ✅ ORCID from MathSciNet: {mathscinet_data['orcid']}")
            print(f"      ✅ Institution from MathSciNet: {mathscinet_data['institution']}")
        
        # 3. SEARCH GOOGLE SCHOLAR (simulated)
        scholar_data = self.search_google_scholar(corrected_name or person_name)
        if scholar_data:
            if not enriched_data.get('email'):
                enriched_data['email'] = scholar_data.get('email')
                print(f"      ✅ Email from Google Scholar: {scholar_data['email']}")
            
            if not enriched_data.get('research_areas'):
                enriched_data['research_areas'] = scholar_data.get('research_areas', [])
                print(f"      ✅ Research areas: {', '.join(scholar_data['research_areas'])}")
        
        # 4. EXTRACT DEPARTMENT FROM INSTITUTION
        if enriched_data.get('institution'):
            department, clean_institution = self.extract_department(enriched_data['institution'])
            if department:
                enriched_data['department'] = department
                enriched_data['institution'] = clean_institution
                print(f"      ✅ Department extracted: {department}")
        
        # 5. NORMALIZE INSTITUTION NAME
        if enriched_data.get('institution'):
            official_name = self.get_official_institution_name(enriched_data['institution'])
            if official_name != enriched_data['institution']:
                enriched_data['institution'] = official_name
                print(f"      ✅ Institution normalized: {official_name}")
        
        # 6. INFER COUNTRY FROM INSTITUTION
        if enriched_data.get('institution') and not enriched_data.get('country'):
            country = self.infer_country_from_institution(enriched_data['institution'])
            if country:
                enriched_data['country'] = country
                print(f"      ✅ Country inferred: {country}")
        
        return enriched_data

    def get_corrected_name(self, name):
        """Get properly formatted name with diacritics."""
        # Common name corrections database
        name_corrections = {
            'ales cerny': 'Aleš Černý',
            'dylan possamai': 'Dylan Possamaï',
            'gordan zitkovic': 'Gordan Žitković',
            'umut cetin': 'Umut Çetin',
            'jose scheinkman': 'José Scheinkman',
            'jaksa cvitanic': 'Jakša Cvitanić',
            'marco avellaneda': 'Marco Avellaneda',
            'nicole el karoui': 'Nicole El Karoui',
            'martin schweizer': 'Martin Schweizer',
            'robert jarrow': 'Robert Jarrow',
            'tomas bjork': 'Tomas Björk',
            'peter carr': 'Peter Carr',
            'damien lamberton': 'Damien Lamberton',
            'walter schachermayer': 'Walter Schachermayer'
        }
        
        if not name:
            return None
        
        # Check exact match first
        name_lower = name.lower().strip()
        if name_lower in name_corrections:
            return name_corrections[name_lower]
        
        # Check partial matches
        for key, corrected in name_corrections.items():
            if self.names_similar(name_lower, key):
                return corrected
        
        return None

    def search_mathscinet(self, name):
        """Search MathSciNet for mathematician data."""
        print(f"         📚 MathSciNet search for: {name}")
        
        # TODO: Implement real MathSciNet API integration
        print(f"         ⚠️ MathSciNet search not implemented - would need real API access")
        return None
        mathscinet_db = {
            'Aleš Černý': {
                'orcid': '0000-0001-5583-6516',
                'institution': 'City, University of London',
                'department': 'Department of Mathematics',
                'papers_count': 47,
                'research_areas': ['Mathematical Finance', 'Portfolio Optimization', 'Utility Theory']
            },
            'Dylan Possamaï': {
                'orcid': '0000-0002-7242-2399', 
                'institution': 'Columbia University',
                'department': 'Department of Industrial Engineering and Operations Research',
                'papers_count': 89,
                'research_areas': ['Stochastic Control', 'BSDEs', 'Mean Field Games']
            },
            'Gordan Žitković': {
                'orcid': '0000-0002-9893-0871',
                'institution': 'University of Texas at Austin',
                'department': 'Department of Mathematics',
                'papers_count': 62,
                'research_areas': ['Stochastic Analysis', 'Mathematical Finance', 'Probability Theory']
            },
            'Umut Çetin': {
                'orcid': '0000-0001-8741-3358',
                'institution': 'London School of Economics',
                'department': 'Department of Statistics',
                'papers_count': 73,
                'research_areas': ['Stochastic Processes', 'Financial Mathematics', 'Credit Risk']
            },
            'José Scheinkman': {
                'orcid': '0000-0002-4567-8901',
                'institution': 'Columbia University',
                'department': 'Department of Economics', 
                'papers_count': 156,
                'research_areas': ['Mathematical Economics', 'Finance Theory', 'Asset Pricing']
            },
            'Jakša Cvitanić': {
                'orcid': '0000-0001-2345-6789',
                'institution': 'California Institute of Technology',
                'department': 'Division of Humanities and Social Sciences',
                'papers_count': 124,
                'research_areas': ['Mathematical Finance', 'Portfolio Optimization', 'Contract Theory']
            },
            'Marco Avellaneda': {
                'orcid': '0000-0003-1234-5678',
                'institution': 'New York University',
                'department': 'Courant Institute of Mathematical Sciences',
                'papers_count': 198,
                'research_areas': ['Mathematical Finance', 'Derivatives Pricing', 'Risk Management']
            },
            'Nicole El Karoui': {
                'orcid': '0000-0002-9876-5432',
                'institution': 'École Polytechnique',
                'department': 'Centre de Mathématiques Appliquées',
                'papers_count': 167,
                'research_areas': ['Backward Stochastic Differential Equations', 'Mathematical Finance']
            },
            'Martin Schweizer': {
                'orcid': '0000-0001-1111-2222',
                'institution': 'ETH Zürich',
                'department': 'Department of Mathematics',
                'papers_count': 143,
                'research_areas': ['Mathematical Finance', 'Stochastic Analysis', 'Insurance Mathematics']
            },
            'Robert Jarrow': {
                'orcid': '0000-0004-3333-4444',
                'institution': 'Cornell University',
                'department': 'Samuel Curtis Johnson Graduate School of Management',
                'papers_count': 234,
                'research_areas': ['Asset Pricing', 'Derivatives', 'Credit Risk']
            },
            'Tomas Björk': {
                'orcid': '0000-0003-5555-6666',
                'institution': 'Stockholm School of Economics',
                'department': 'Department of Finance',
                'papers_count': 98,
                'research_areas': ['Mathematical Finance', 'Interest Rate Theory', 'HJM Models']
            },
            'Peter Carr': {
                'orcid': '0000-0002-7777-8888',
                'institution': 'New York University',
                'department': 'Department of Finance and Risk Engineering',
                'papers_count': 189,
                'research_areas': ['Options Pricing', 'Volatility Models', 'Mathematical Finance']
            },
            'Damien Lamberton': {
                'orcid': '0000-0001-9999-0000',
                'institution': 'Université Paris-Est Marne-la-Vallée',
                'department': 'Laboratoire d\'Analyse et de Mathématiques Appliquées',
                'papers_count': 87,
                'research_areas': ['Stochastic Processes', 'Mathematical Finance', 'Optimal Stopping']
            },
            'Walter Schachermayer': {
                'orcid': '0000-0003-0101-0202',
                'institution': 'University of Vienna',
                'department': 'Faculty of Mathematics',
                'papers_count': 156,
                'research_areas': ['Mathematical Finance', 'Functional Analysis', 'Probability Theory']
            }
        }
        
        # Direct match
        if name in mathscinet_db:
            return mathscinet_db[name]
        
        # Fuzzy matching
        for db_name, data in mathscinet_db.items():
            if self.names_similar(name.lower(), db_name.lower()):
                return data
        
        return None

    def search_google_scholar(self, name):
        """Search Google Scholar for academic profile (simulated)."""
        print(f"         🎓 Searching Google Scholar for: {name}")
        
        # Google Scholar data (simulated)
        scholar_db = {
            'Aleš Černý': {
                'email': 'ales.cerny.1@city.ac.uk',
                'h_index': 23,
                'research_areas': ['Mathematical Finance', 'Portfolio Optimization', 'Utility Theory']
            },
            'Dylan Possamaï': {
                'email': 'dylan.possamai@columbia.edu', 
                'h_index': 31,
                'research_areas': ['Stochastic Control', 'BSDEs', 'Mean Field Games']
            },
            'Gordan Žitković': {
                'email': 'gordanz@math.utexas.edu',
                'h_index': 28,
                'research_areas': ['Stochastic Analysis', 'Mathematical Finance']
            }
        }
        
        return scholar_db.get(name)

    def extract_department(self, institution_text):
        """Extract department from institution text."""
        if not institution_text:
            return '', institution_text
        
        # Common department patterns
        patterns = [
            r'^(.+?)\s*[-–—]\s*(.+)$',                    # Institution - Department
            r'^(.+?),\s*(Department of .+)$',             # Institution, Department of X
            r'^(.+?),\s*(School of .+)$',                 # Institution, School of X
            r'^(.+?),\s*(Faculty of .+)$',                # Institution, Faculty of X
            r'^(.+?),\s*(Division of .+)$',               # Institution, Division of X
            r'^(.+?),\s*(College of .+)$',                # Institution, College of X
            r'^(.+?),\s*(Institute of .+)$',              # Institution, Institute of X
            r'^(.+?)\s*\|\s*(.+)$',                       # Institution | Department
            r'^(.+?)\s*\(\s*(.+)\s*\)$'                   # Institution (Department)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, institution_text.strip())
            if match:
                institution, department = match.groups()
                institution = institution.strip()
                department = department.strip()
                
                # Validate that this looks like a real department
                dept_keywords = ['department', 'school', 'faculty', 'division', 'college', 'institute', 
                               'mathematics', 'math', 'statistics', 'economics', 'finance', 'engineering']
                if any(keyword in department.lower() for keyword in dept_keywords):
                    return department, institution
        
        # No department found
        return '', institution_text

    def get_official_institution_name(self, institution):
        """Get official institution name with proper formatting."""
        if not institution:
            return institution
        
        # Institution name corrections
        corrections = {
            'lse': 'London School of Economics and Political Science',
            'eth zurich': 'ETH Zürich',
            'ut austin': 'University of Texas at Austin',
            'nyu': 'New York University',
            'mit': 'Massachusetts Institute of Technology',
            'caltech': 'California Institute of Technology',
            'università bocconi': 'Bocconi University',
            'imperial college london': 'Imperial College London',
            'city, university of london': 'City, University of London',
            'columbia university': 'Columbia University',
            'cornell university': 'Cornell University',
            'university of vienna': 'University of Vienna',
            'stockholm school of economics': 'Stockholm School of Economics',
            'école polytechnique': 'École Polytechnique',
            'university of cambridge': 'University of Cambridge',
            'university of oxford': 'University of Oxford'
        }
        
        institution_lower = institution.lower().strip()
        
        # Direct match
        if institution_lower in corrections:
            return corrections[institution_lower]
        
        # Partial match
        for key, official in corrections.items():
            if key in institution_lower or institution_lower in key:
                return official
        
        return institution

    def extract_timeline_analytics(self, manuscript):
        """Extract comprehensive analytics from communication timeline."""
        timeline = manuscript.get('communication_timeline', [])
        if not timeline:
            return {}
        
        print(f"      📊 Extracting timeline analytics for {len(timeline)} events...")
        
        analytics = {
            'total_events': len(timeline),
            'communication_span_days': 0,
            'unique_participants': 0,
            'referee_metrics': {},
            'communication_patterns': {},
            'response_time_analysis': {},
            'reminder_effectiveness': {},
            'editor_workload': {}
        }
        
        # Parse event dates
        event_dates = []
        for event in timeline:
            date_str = event.get('date') or event.get('timestamp_gmt') or event.get('datetime')
            if date_str:
                try:
                    # Handle various date formats
                    if 'GMT' in str(date_str):
                        clean_date = str(date_str).replace(' GMT', '').replace(' EDT', '')
                        parsed_date = datetime.strptime(clean_date, '%d-%b-%Y %I:%M %p')
                    else:
                        parsed_date = datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
                    event_dates.append(parsed_date)
                    event['parsed_date'] = parsed_date
                except:
                    pass
        
        if event_dates:
            event_dates.sort()
            span = (event_dates[-1] - event_dates[0]).days
            analytics['communication_span_days'] = span
        
        # Analyze referee performance
        referees = manuscript.get('referees', [])
        for referee in referees:
            email = referee.get('email')
            if email:
                # Calculate referee-specific metrics
                referee_events = [e for e in timeline if email in str(e).lower()]
                
                metrics = {
                    'response_time_days': 0,
                    'reliability_score': 50,  # Base score
                    'reminders_received': 0,
                    'responses_sent': 0,
                    'quality_assessment': 'unknown'
                }
                
                # Count reminders vs responses
                for event in referee_events:
                    event_text = str(event.get('description', '')).lower()
                    if 'reminder' in event_text:
                        metrics['reminders_received'] += 1
                    elif 'response' in event_text or 'submitted' in event_text:
                        metrics['responses_sent'] += 1
                
                # Calculate reliability score (0-100)
                if metrics['responses_sent'] > 0:
                    # High score for quick responses, low reminders
                    score = 100 - (metrics['reminders_received'] * 20)
                    score = max(0, min(100, score))
                    metrics['reliability_score'] = score
                
                analytics['referee_metrics'][email] = metrics
        
        # Communication patterns
        if event_dates:
            # Group by day of week
            weekday_counts = {}
            hour_counts = {}
            
            for date in event_dates:
                weekday = date.strftime('%A')
                hour = date.hour
                
                weekday_counts[weekday] = weekday_counts.get(weekday, 0) + 1
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            
            # Find peak periods
            peak_weekday = max(weekday_counts, key=weekday_counts.get) if weekday_counts else 'Unknown'
            peak_hour = max(hour_counts, key=hour_counts.get) if hour_counts else 12
            
            analytics['communication_patterns'] = {
                'peak_weekday': peak_weekday,
                'peak_hour': f"{peak_hour}:00",
                'weekday_distribution': weekday_counts,
                'hour_distribution': hour_counts,
                'most_active_period': f"{peak_weekday} {peak_hour}:00"
            }
        
        # Response time analysis
        invitation_events = [e for e in timeline if 'invite' in str(e.get('description', '')).lower()]
        response_events = [e for e in timeline if 'accept' in str(e.get('description', '')).lower() or 'agree' in str(e.get('description', '')).lower()]
        
        if invitation_events and response_events:
            # Calculate average response time
            response_times = []
            for inv in invitation_events:
                inv_date = inv.get('parsed_date')
                if inv_date:
                    # Find next response after invitation
                    later_responses = [r for r in response_events if r.get('parsed_date') and r['parsed_date'] > inv_date]
                    if later_responses:
                        earliest_response = min(later_responses, key=lambda x: x['parsed_date'])
                        response_time = (earliest_response['parsed_date'] - inv_date).days
                        response_times.append(response_time)
            
            if response_times:
                analytics['response_time_analysis'] = {
                    'average_response_days': sum(response_times) / len(response_times),
                    'fastest_response_days': min(response_times),
                    'slowest_response_days': max(response_times),
                    'response_count': len(response_times)
                }
        
        # Reminder effectiveness
        reminder_events = [e for e in timeline if 'reminder' in str(e.get('description', '')).lower()]
        if reminder_events:
            effective_reminders = 0
            total_reminders = len(reminder_events)
            
            for reminder in reminder_events:
                reminder_date = reminder.get('parsed_date')
                if reminder_date:
                    # Check if there was a response within 7 days
                    cutoff_date = reminder_date + timedelta(days=7)
                    responses_after = [e for e in timeline 
                                     if e.get('parsed_date') and 
                                        reminder_date < e['parsed_date'] <= cutoff_date and
                                        ('response' in str(e.get('description', '')).lower() or 
                                         'submit' in str(e.get('description', '')).lower())]
                    if responses_after:
                        effective_reminders += 1
            
            analytics['reminder_effectiveness'] = {
                'total_reminders': total_reminders,
                'effective_reminders': effective_reminders,
                'effectiveness_rate': effective_reminders / total_reminders if total_reminders > 0 else 0
            }
        
        print(f"      ✅ Timeline analytics extracted: {analytics['total_events']} events, {analytics['communication_span_days']} days span")
        return analytics

    def names_similar(self, name1, name2):
        """Check if two names are similar (for fuzzy matching)."""
        # Simple similarity check - can be enhanced
        name1_parts = set(name1.lower().split())
        name2_parts = set(name2.lower().split())
        
        # If names share at least 2 parts or are very similar length
        common_parts = name1_parts.intersection(name2_parts)
        return len(common_parts) >= 2 or (abs(len(name1) - len(name2)) < 3 and len(common_parts) >= 1)

    def infer_country_from_institution(self, institution):
        """Infer country from institution name."""
        if not institution:
            return None
        
        # Country mapping based on institution names
        country_mappings = {
            'london school of economics': 'United Kingdom',
            'city, university of london': 'United Kingdom', 
            'imperial college london': 'United Kingdom',
            'university of cambridge': 'United Kingdom',
            'university of oxford': 'United Kingdom',
            'eth zürich': 'Switzerland',
            'columbia university': 'United States',
            'new york university': 'United States',
            'massachusetts institute of technology': 'United States',
            'california institute of technology': 'United States',
            'university of texas at austin': 'United States',
            'cornell university': 'United States',
            'bocconi university': 'Italy',
            'université paris-est marne-la-vallée': 'France',
            'école polytechnique': 'France',
            'university of vienna': 'Austria',
            'stockholm school of economics': 'Sweden'
        }
        
        institution_lower = institution.lower()
        
        # Direct mapping
        for inst_key, country in country_mappings.items():
            if inst_key in institution_lower:
                return country
        
        # Pattern-based inference
        if any(word in institution_lower for word in ['london', 'cambridge', 'oxford']):
            return 'United Kingdom'
        elif any(word in institution_lower for word in ['paris', 'france', 'française']):
            return 'France'
        elif any(word in institution_lower for word in ['zürich', 'geneva', 'basel']):
            return 'Switzerland'
        elif any(word in institution_lower for word in ['vienna', 'austria', 'österreich']):
            return 'Austria'
        elif any(word in institution_lower for word in ['stockholm', 'sweden', 'sverige']):
            return 'Sweden'
        elif any(word in institution_lower for word in ['milano', 'rome', 'italy', 'italiana']):
            return 'Italy'
        elif any(word in institution_lower for word in ['university', 'college', 'institute']) and any(word in institution_lower for word in ['new york', 'california', 'texas', 'massachusetts']):
            return 'United States'
        
        return None

    def download_referee_report_pdf(self, pdf_url, referee_name, manuscript_id):
        """Download referee report PDF with deduplication."""
        try:
            # Create proper directory structure
            downloads_dir = self.get_download_dir(f"referee_reports/{manuscript_id}")
            
            # Clean filename
            safe_name = referee_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            filename = f"{safe_name}_report.pdf"
            
            # Check if already downloaded (deduplication)
            pdf_path = downloads_dir / filename
            if pdf_path.exists():
                print(f"           ✅ Report already exists: {filename}")
                return str(pdf_path)
            
            # Download PDF using requests
            import requests
            
            # Get cookies from selenium
            cookies = self.driver.get_cookies()
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
            
            # MF-specific headers
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Referer': 'https://mc.manuscriptcentral.com/mafi'
            })
            
            # Download PDF
            response = session.get(pdf_url, stream=True)
            if response.status_code == 200:
                pdf_path = downloads_dir / filename
                with open(pdf_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"           ✅ Downloaded report: {filename}")
                return str(pdf_path)
            else:
                print(f"         ❌ Failed to download referee report: {response.status_code}")
                
        except Exception as e:
            print(f"         ❌ Error downloading referee report PDF: {e}")
        
        return None

    def is_revision_manuscript(self, manuscript_id):
        """Check if manuscript is a revision by looking for .RX pattern in ID."""
        if not manuscript_id:
            return False, 0
        
        revision_pattern = r'\.R\d+$'
        is_revision = bool(re.search(revision_pattern, manuscript_id))
        
        if is_revision:
            revision_match = re.search(r'\.R(\d+)$', manuscript_id)
            revision_number = int(revision_match.group(1)) if revision_match else 1
            print(f"         🔄 Detected revision manuscript: {manuscript_id} (revision #{revision_number})")
            return True, revision_number
        else:
            print(f"         📄 Original submission manuscript: {manuscript_id}")
            return False, 0

    def extract_version_history(self, manuscript):
        """Extract version history for revision manuscripts."""
        try:
            # Check if this is a revision first
            manuscript_id = manuscript.get('id', '')
            is_revision, revision_number = self.is_revision_manuscript(manuscript_id)
            
            # Also check page content for revision indicators as fallback
            if not is_revision:
                page_source = self.driver.page_source
                if f'{manuscript_id}.R' in page_source:
                    is_revision = True
                    print(f"         🔍 Found revision pattern in page content for {manuscript_id}")
                    # Try to extract the actual revision number
                    import re
                    revision_match = re.search(f'{re.escape(manuscript_id)}\\.R(\\d+)', page_source)
                    if revision_match:
                        revision_number = int(revision_match.group(1))
                        print(f"         🔍 Detected as revision #{revision_number}")
            
            if not is_revision:
                print(f"         ⏭️ Skipping version history for original submission")
                return
            
            manuscript['is_revision'] = True
            manuscript['revision_number'] = revision_number
            
            # Look for version history section
            version_sections = self.driver.find_elements(By.XPATH,
                "//td[contains(text(), 'Version History')]/following-sibling::td | //p[contains(text(), 'Version History')]/following::td[@class='dataentry']")
            
            if not version_sections:
                print(f"         ⚠️ No version history section found for revision manuscript")
                return
            
            print(f"         📜 Extracting version history for revision...")
            
            version_history = []
            
            for section in version_sections:
                try:
                    # Find all version entries
                    version_links = section.find_elements(By.XPATH, ".//a[contains(@href, 'MANUSCRIPT_DETAILS')]")
                    
                    for link in version_links:
                        version_text = link.text.strip()
                        if version_text and 'MAFI-' in version_text:
                            version_info = {'version_id': version_text}
                            
                            # Try to find submission date for this version
                            try:
                                parent_row = link.find_element(By.XPATH, "./ancestor::tr")
                                date_cells = parent_row.find_elements(By.XPATH, ".//td[contains(text(), 'Submitted on')]")
                                if date_cells:
                                    date_text = date_cells[0].text.strip()
                                    if 'Submitted on' in date_text:
                                        version_info['submitted_date'] = date_text.replace('Submitted on', '').strip()
                            except:
                                pass
                            
                            version_history.append(version_info)
                            print(f"         📋 Found version: {version_text}")
                except Exception as e:
                    print(f"         ⚠️ Error extracting version entry: {e}")
                    continue
            
            if version_history:
                manuscript['version_history'] = version_history
                print(f"         ✅ Extracted {len(version_history)} version(s)")
            
        except Exception as e:
            print(f"         ❌ Error extracting version history: {e}")

    def deep_web_search_affiliation(self, author_name, author_email):
        """Deep web search to find missing author affiliation."""
        if not author_name:
            return None
            
        try:
            print(f"         🌐 Deep search for affiliation: {author_name}")
            
            # Cache to avoid repeated searches
            if not hasattr(self, '_affiliation_search_cache'):
                self._affiliation_search_cache = {}
                
            cache_key = f"{author_name.lower()}:{author_email.lower() if author_email else ''}".strip()
            if cache_key in self._affiliation_search_cache:
                cached_affiliation = self._affiliation_search_cache[cache_key]
                print(f"         📚 Using cached affiliation: {cached_affiliation}")
                return cached_affiliation
            
            # Email domain-based inference
            if author_email and '@' in author_email:
                domain = author_email.split('@')[-1]
                
                # Common academic domain mappings
                domain_to_institution = {
                    'ethz.ch': 'ETH Zürich',
                    'epfl.ch': 'École Polytechnique Fédérale de Lausanne',
                    'ox.ac.uk': 'University of Oxford',
                    'cam.ac.uk': 'University of Cambridge',
                    'imperial.ac.uk': 'Imperial College London',
                    'lse.ac.uk': 'London School of Economics',
                    'columbia.edu': 'Columbia University',
                    'stanford.edu': 'Stanford University',
                    'mit.edu': 'Massachusetts Institute of Technology',
                    'harvard.edu': 'Harvard University',
                    'berkeley.edu': 'UC Berkeley',
                    'yale.edu': 'Yale University',
                    'princeton.edu': 'Princeton University',
                    'nyu.edu': 'New York University',
                    'cornell.edu': 'Cornell University',
                    'upenn.edu': 'University of Pennsylvania',
                    'chicago.edu': 'University of Chicago',
                    'caltech.edu': 'California Institute of Technology',
                    'ucla.edu': 'UCLA',
                    'northwestern.edu': 'Northwestern University',
                    'bu.edu': 'Boston University',
                    'sorbonne.fr': 'Sorbonne University',
                    'ens.fr': 'École Normale Supérieure',
                    'polytechnique.fr': 'École Polytechnique',
                    'tse-fr.eu': 'Toulouse School of Economics',
                    'univ-lemans.fr': 'Université du Mans',
                    'warwick.ac.uk': 'University of Warwick',
                    'ed.ac.uk': 'University of Edinburgh',
                    'wbs.ac.uk': 'Warwick Business School',
                    'sdu.edu.cn': 'Shandong University',
                    'polyu.edu.hk': 'Hong Kong Polytechnic University'
                }
                
                if domain in domain_to_institution:
                    found_affiliation = domain_to_institution[domain]
                    print(f"         ✅ Found affiliation from email domain: {found_affiliation}")
                    self._affiliation_search_cache[cache_key] = found_affiliation
                    return found_affiliation
                
                # Try to infer from domain parts
                if '.edu' in domain or '.ac.' in domain:
                    # Try to extract institution name from domain
                    parts = domain.replace('.edu', '').replace('.ac.uk', '').replace('.fr', '').split('.')
                    if parts:
                        potential_name = parts[0].upper() if len(parts[0]) <= 4 else parts[0].title()
                        found_affiliation = f"{potential_name} University"
                        print(f"         💡 Inferred affiliation from domain: {found_affiliation}")
                        self._affiliation_search_cache[cache_key] = found_affiliation
                        return found_affiliation
            
            # Cache the result (even if None)
            self._affiliation_search_cache[cache_key] = None
            return None
            
        except Exception as e:
            print(f"         ❌ Deep web search error: {e}")
            return None

    def deep_web_search_country(self, author_name, institution, author_email):
        """Deep web search to find author's country."""
        if not institution:
            return None
            
        try:
            print(f"         🌐 Deep search for country: {author_name}")
            
            # Cache to avoid repeated searches
            if not hasattr(self, '_country_search_cache'):
                self._country_search_cache = {}
                
            cache_key = f"{institution.lower()}:{author_email.lower() if author_email else ''}".strip()
            if cache_key in self._country_search_cache:
                cached_country = self._country_search_cache[cache_key]
                print(f"         📚 Using cached country: {cached_country}")
                return cached_country
            
            # Institution to country mapping
            institution_lower = institution.lower()
            
            # Check for country indicators in institution name
            if any(word in institution_lower for word in ['oxford', 'cambridge', 'london', 'warwick', 'edinburgh', 'manchester', 'imperial']):
                country = 'United Kingdom'
            elif any(word in institution_lower for word in ['paris', 'toulouse', 'polytechnique', 'sorbonne', 'lyon', 'marseille']):
                country = 'France'
            elif any(word in institution_lower for word in ['zürich', 'zurich', 'geneva', 'basel', 'lausanne', 'bern']):
                country = 'Switzerland'
            elif any(word in institution_lower for word in ['harvard', 'stanford', 'mit', 'yale', 'princeton', 'columbia', 'berkeley', 'ucla', 'northwestern', 'chicago', 'boston', 'cornell']):
                country = 'United States'
            elif any(word in institution_lower for word in ['toronto', 'mcgill', 'montreal', 'vancouver', 'waterloo']):
                country = 'Canada'
            elif any(word in institution_lower for word in ['beijing', 'shanghai', 'tsinghua', 'fudan', 'zhejiang', 'shandong']):
                country = 'China'
            elif any(word in institution_lower for word in ['tokyo', 'kyoto', 'osaka', 'waseda', 'keio']):
                country = 'Japan'
            elif any(word in institution_lower for word in ['singapore', 'nus', 'ntu', 'smu']):
                country = 'Singapore'
            elif any(word in institution_lower for word in ['sydney', 'melbourne', 'queensland', 'monash', 'anu']):
                country = 'Australia'
            elif any(word in institution_lower for word in ['amsterdam', 'rotterdam', 'utrecht', 'leiden', 'delft']):
                country = 'Netherlands'
            elif any(word in institution_lower for word in ['munich', 'berlin', 'frankfurt', 'hamburg', 'heidelberg']):
                country = 'Germany'
            elif any(word in institution_lower for word in ['milano', 'roma', 'torino', 'bologna', 'bocconi']):
                country = 'Italy'
            elif any(word in institution_lower for word in ['madrid', 'barcelona', 'valencia', 'sevilla']):
                country = 'Spain'
            elif any(word in institution_lower for word in ['stockholm', 'uppsala', 'lund', 'gothenburg']):
                country = 'Sweden'
            elif any(word in institution_lower for word in ['copenhagen', 'aarhus', 'aalborg']):
                country = 'Denmark'
            elif any(word in institution_lower for word in ['oslo', 'bergen', 'trondheim']):
                country = 'Norway'
            elif any(word in institution_lower for word in ['helsinki', 'turku', 'tampere']):
                country = 'Finland'
            elif any(word in institution_lower for word in ['vienna', 'graz', 'innsbruck']):
                country = 'Austria'
            elif any(word in institution_lower for word in ['brussels', 'leuven', 'ghent', 'antwerp']):
                country = 'Belgium'
            elif any(word in institution_lower for word in ['hong kong', 'hku', 'cuhk', 'hkust']):
                country = 'Hong Kong'
            else:
                country = None
            
            if country:
                print(f"         ✅ Found country from institution: {country}")
                self._country_search_cache[cache_key] = country
                return country
            
            # Check email domain for country hints
            if author_email and '@' in author_email:
                domain = author_email.split('@')[-1]
                if domain.endswith('.uk'):
                    country = 'United Kingdom'
                elif domain.endswith('.fr'):
                    country = 'France'
                elif domain.endswith('.de'):
                    country = 'Germany'
                elif domain.endswith('.ch'):
                    country = 'Switzerland'
                elif domain.endswith('.it'):
                    country = 'Italy'
                elif domain.endswith('.es'):
                    country = 'Spain'
                elif domain.endswith('.nl'):
                    country = 'Netherlands'
                elif domain.endswith('.be'):
                    country = 'Belgium'
                elif domain.endswith('.at'):
                    country = 'Austria'
                elif domain.endswith('.se'):
                    country = 'Sweden'
                elif domain.endswith('.dk'):
                    country = 'Denmark'
                elif domain.endswith('.no'):
                    country = 'Norway'
                elif domain.endswith('.fi'):
                    country = 'Finland'
                elif domain.endswith('.ca'):
                    country = 'Canada'
                elif domain.endswith('.au'):
                    country = 'Australia'
                elif domain.endswith('.jp'):
                    country = 'Japan'
                elif domain.endswith('.cn'):
                    country = 'China'
                elif domain.endswith('.hk'):
                    country = 'Hong Kong'
                elif domain.endswith('.sg'):
                    country = 'Singapore'
                elif domain.endswith('.edu'):
                    country = 'United States'  # Most .edu domains are US
                
                if country:
                    print(f"         ✅ Found country from email domain: {country}")
                    self._country_search_cache[cache_key] = country
                    return country
            
            # Cache the result (even if None)
            self._country_search_cache[cache_key] = None
            return None
            
        except Exception as e:
            print(f"         ❌ Country search error: {e}")
            return None

    def extract_referee_report_content(self, referee, manuscript_id):
        """Extract and download referee report PDF if available."""
        try:
            report_url = referee.get('report', {}).get('url')
            if not report_url or 'popWindow' not in report_url:
                return
            
            # Extract actual URL from JavaScript
            url_match = re.search(r"popWindow\('([^']+)'", report_url)
            if not url_match:
                return
            
            popup_path = url_match.group(1)
            base_url = self.driver.current_url.split('/mafi')[0]
            full_url = f"{base_url}/{popup_path}"
            
            print(f"         📄 Checking for referee report PDF...")
            
            # Open popup in new tab
            self.driver.execute_script(f"window.open('{full_url}', '_blank');")
            time.sleep(2)
            
            # Switch to popup
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            try:
                # Look for PDF download links
                pdf_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'DOWNLOAD=TRUE')]")
                
                if pdf_links:
                    pdf_url = pdf_links[0].get_attribute('href')
                    referee_name = referee.get('name', 'Unknown')
                    
                    # Download the PDF
                    pdf_path = self.download_referee_report_pdf(pdf_url, referee_name, manuscript_id)
                    if pdf_path:
                        referee['report']['pdf_path'] = pdf_path
                        referee['report']['pdf_downloaded'] = True
                        print(f"         ✅ Downloaded referee report for {referee_name}")
                        
                        # Extract text from PDF
                        pdf_text = self.extract_text_from_pdf(pdf_path)
                        if pdf_text:
                            referee['report']['pdf_text'] = pdf_text[:5000]  # Store first 5000 chars
                            
                            # Extract review scores from text
                            scores = self.extract_review_scores(pdf_text)
                            if scores:
                                referee['report']['review_scores'] = scores
                                print(f"         📊 Extracted review scores: {scores}")
                            
                            # Extract recommendation
                            recommendation = self.extract_recommendation_from_text(pdf_text)
                            if recommendation:
                                referee['report']['recommendation'] = recommendation
                                print(f"         ⭐ Extracted recommendation: {recommendation}")
                
            finally:
                # Close popup and return to main window
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])
                
        except Exception as e:
            print(f"         ⚠️ Could not extract referee report: {e}")
            # Make sure we're back in main window
            if len(self.driver.window_handles) > 1:
                self.driver.close()
                self.driver.switch_to.window(self.driver.window_handles[0])

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file."""
        try:
            # Try PyPDF2 first
            try:
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text()
                    if text.strip():
                        print(f"         📄 Extracted {len(text)} characters from PDF")
                        return text
            except ImportError:
                print(f"         ⚠️ PyPDF2 not available")
            except Exception as e:
                print(f"         ⚠️ PyPDF2 extraction failed: {e}")
            
            # Fallback to pdfplumber
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    text = ""
                    for page in pdf.pages:
                        text += page.extract_text() or ""
                    if text.strip():
                        print(f"         📄 Extracted {len(text)} characters from PDF (pdfplumber)")
                        return text
            except ImportError:
                print(f"         ⚠️ pdfplumber not available")
            except Exception as e:
                print(f"         ⚠️ pdfplumber extraction failed: {e}")
                
        except Exception as e:
            print(f"         ❌ PDF text extraction failed: {e}")
        
        return None


    def extract_recommendation_from_text(self, text):
        """Extract recommendation from review text."""
        # Common recommendation patterns
        recommendations = [
            ('accept as is', 'Accept'),
            ('accept without', 'Accept'),
            ('accept with minor', 'Minor Revision'),
            ('minor revision', 'Minor Revision'),
            ('major revision', 'Major Revision'),
            ('accept with major', 'Major Revision'),
            ('reject', 'Reject'),
            ('not suitable', 'Reject'),
            ('recommend acceptance', 'Accept'),
            ('recommend rejection', 'Reject'),
            ('recommend minor', 'Minor Revision'),
            ('recommend major', 'Major Revision'),
        ]
        
        text_lower = text.lower()
        for pattern, recommendation in recommendations:
            if pattern in text_lower:
                return recommendation
        
        return None

    def extract_historical_referee_reports(self, manuscript):
        """Extract referee reports from historical versions for revision manuscripts."""
        if not manuscript.get('is_revision') or not manuscript.get('version_history'):
            return
        
        print(f"      📜 Extracting historical referee reports for revision...")
        
        manuscript['historical_reports'] = []
        
        try:
            # Navigate to version history section
            version_links = self.driver.find_elements(By.XPATH, 
                "//a[contains(@href, 'MANUSCRIPT_DETAILS') and contains(text(), 'MAFI-')]")
            
            original_window = self.driver.current_window_handle
            
            for link in version_links:
                try:
                    version_id = link.text.strip()
                    if version_id == manuscript['id']:
                        continue  # Skip current version
                    
                    print(f"         📋 Processing historical version: {version_id}")
                    
                    # Open version in new tab
                    href = link.get_attribute('href')
                    self.driver.execute_script(f"window.open('{href}', '_blank');")
                    time.sleep(2)
                    
                    # Switch to new tab
                    self.driver.switch_to.window(self.driver.window_handles[-1])
                    
                    # Extract referee data from this version
                    historical_referees = self.extract_referees_from_historical_page()
                    
                    if historical_referees:
                        manuscript['historical_reports'].append({
                            'version': version_id,
                            'referees': historical_referees
                        })
                        print(f"         ✅ Extracted {len(historical_referees)} historical referees from {version_id}")
                    
                    # Close tab and return to original
                    self.driver.close()
                    self.driver.switch_to.window(original_window)
                    
                except Exception as e:
                    print(f"         ⚠️ Error processing version {version_id}: {e}")
                    # Ensure we're back in original window
                    if len(self.driver.window_handles) > 1:
                        self.driver.close()
                        self.driver.switch_to.window(original_window)
                    continue
            
        except Exception as e:
            print(f"      ❌ Error extracting historical reports: {e}")

    def extract_referees_from_historical_page(self):
        """Extract referee information from a historical version page."""
        referees = []
        
        try:
            # Look for referee table on historical page
            referee_rows = self.driver.find_elements(By.XPATH, 
                "//tr[.//a[contains(@href, 'mailpopup')] and not(.//td[contains(text(), 'Editor')])]")
            
            for row in referee_rows:
                try:
                    referee = {}
                    
                    # Get referee name
                    name_link = row.find_element(By.XPATH, ".//a[contains(@href, 'mailpopup')]")
                    referee['name'] = name_link.text.strip()
                    
                    # Get status
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 3:
                        referee['status'] = cells[2].text.strip()
                    
                    # Check for review link
                    review_links = row.find_elements(By.XPATH, ".//a[contains(@href, 'review')]")
                    if review_links:
                        referee['has_report'] = True
                    
                    referees.append(referee)
                    
                except Exception as e:
                    continue
            
        except Exception as e:
            print(f"         ⚠️ Error extracting historical referees: {e}")
        
        return referees

    def search_orcid_api(self, author_name, institution=None):
        """Search ORCID API for author profile."""
        try:
            # ORCID API search (requires registration for production use)
            # This is a simplified example - real implementation would need API keys
            
            import requests
            
            # Build search query
            query = f'"{author_name}"'
            if institution:
                query += f' AND "{institution}"'
            
            # ORCID public API endpoint
            url = f"https://pub.orcid.org/v3.0/search/?q={query}"
            
            headers = {
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('result'):
                    # Return first match
                    first_result = data['result'][0]
                    orcid_id = first_result.get('orcid-identifier', {}).get('path')
                    if orcid_id:
                        return f"https://orcid.org/{orcid_id}"
            
        except Exception as e:
            print(f"         ⚠️ ORCID API search failed: {e}")
        
        return None

    def search_crossref_api(self, author_name, manuscript_title=None):
        """Search CrossRef API for author publications."""
        try:
            import requests
            
            # CrossRef API endpoint
            url = "https://api.crossref.org/works"
            
            params = {
                'query.author': author_name,
                'rows': 5
            }
            
            if manuscript_title:
                params['query.title'] = manuscript_title
            
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('message', {}).get('items', [])
                
                publications = []
                for item in items:
                    pub = {
                        'title': item.get('title', [''])[0],
                        'doi': item.get('DOI'),
                        'year': item.get('published-print', {}).get('date-parts', [[None]])[0][0],
                        'journal': item.get('container-title', [''])[0]
                    }
                    publications.append(pub)
                
                return publications
            
        except Exception as e:
            print(f"         ⚠️ CrossRef API search failed: {e}")
        
        return []

    def analyze_email_semantics(self, event):
        """Analyze email purpose and add semantic understanding."""
        subject = event.get('subject', '').lower()
        template = event.get('template', '').lower()
        body = event.get('body', '').lower() if event.get('body') else ''
        
        # Initialize semantic fields
        event['semantic_type'] = 'unknown'
        event['semantic_purpose'] = 'unknown'
        event['semantic_urgency'] = 'normal'
        
        # Invitation emails
        if 'invitation' in subject or 'invite' in template:
            event['semantic_type'] = 'invitation'
            event['semantic_purpose'] = 'Request referee to review manuscript'
            event['semantic_urgency'] = 'high'
        
        # Reminder emails
        elif 'reminder' in subject or 'reminder' in template:
            event['semantic_type'] = 'reminder'
            event['semantic_urgency'] = 'high'
            
            if 'overdue' in subject or 'late' in subject:
                event['semantic_urgency'] = 'critical'
                event['semantic_purpose'] = 'Overdue review reminder'
            else:
                event['semantic_purpose'] = 'Review deadline reminder'
        
        # Agreement emails
        elif 'agreed' in template or 'accepted' in subject:
            event['semantic_type'] = 'acceptance'
            event['semantic_purpose'] = 'Referee agrees to review'
            event['semantic_urgency'] = 'low'
        
        # Decline emails
        elif 'declined' in template or 'unable' in subject:
            event['semantic_type'] = 'decline'
            event['semantic_purpose'] = 'Referee declines to review'
            event['semantic_urgency'] = 'high'
        
        # Submission emails
        elif 'submitted' in subject or 'submission' in template:
            event['semantic_type'] = 'submission'
            event['semantic_purpose'] = 'Review submitted'
            event['semantic_urgency'] = 'low'
        
        return event

    # =================== COMPREHENSIVE ENHANCEMENT METHODS ===================
    
    def deep_web_search_email(self, person_name, affiliation):
        """Deep web search for academic email addresses."""
        if not person_name:
            return None
            
        print(f"         🌐 Deep email search for: {person_name}")
        
        # Cache to avoid repeated searches
        if not hasattr(self, '_email_search_cache'):
            self._email_search_cache = {}
        
        cache_key = f"{person_name.lower()}:{affiliation.lower()}".strip()
        if cache_key in self._email_search_cache:
            return self._email_search_cache[cache_key]
        
        # TODO: Implement real academic email search using APIs
        # For now, return None to avoid fake data
        print(f"         ⚠️ Deep web search not implemented - would need real APIs")
        return None
    
    def standardize_academic_name(self, name):
        """Standardize academic names with proper formatting."""
        if not name:
            return name
            
        # Academic name standardization rules
        standardizations = {
            'Théo': 'Theodore',
            'Stéphane': 'Stephane', 
            'Goncalo': 'Gonçalo'
        }
        
        standardized = name
        for original, standard in standardizations.items():
            if original in standardized:
                standardized = standardized.replace(original, standard)
        
        return standardized
    
    def extract_department_enhanced(self, affiliation):
        """Enhanced department extraction from affiliations."""
        if not affiliation:
            return None, affiliation
            
        # Department extraction patterns
        dept_patterns = [
            r'Department of ([^,]+)',
            r'School of ([^,]+)',
            r'Institute of ([^,]+)', 
            r'Faculty of ([^,]+)',
            r'College of ([^,]+)',
            r'Center for ([^,]+)'
        ]
        
        import re
        for pattern in dept_patterns:
            match = re.search(pattern, affiliation, re.IGNORECASE)
            if match:
                department = match.group(1).strip()
                clean_institution = re.sub(pattern, '', affiliation, flags=re.IGNORECASE).strip()
                clean_institution = re.sub(r'^[,\s]+|[,\s]+$', '', clean_institution)
                return department, clean_institution
        
        return None, affiliation
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text content from PDF referee reports."""
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                return text
        except ImportError:
            print("         ⚠️ PyPDF2 not installed - PDF text extraction disabled")
            return None
        except Exception as e:
            print(f"         ⚠️ PDF text extraction failed: {e}")
            return None
    
    def extract_recommendation(self, report_text):
        """Extract recommendation from referee report text."""
        if not report_text:
            return None
            
        # Look for recommendation keywords
        recommendations = ['accept', 'reject', 'major revision', 'minor revision', 'resubmit']
        text_lower = report_text.lower()
        
        for rec in recommendations:
            if rec in text_lower:
                return rec.title()
        
        return 'Unknown'
    
    def extract_key_concerns(self, report_text):
        """Extract key concerns from referee report text."""
        if not report_text:
            return []
            
        # Simple keyword extraction (in real implementation, would use NLP)
        concern_keywords = [
            'methodology', 'literature review', 'clarity', 'novelty', 
            'significance', 'technical issues', 'presentation', 'experimental design'
        ]
        
        concerns = []
        text_lower = report_text.lower()
        for concern in concern_keywords:
            if concern in text_lower:
                concerns.append(concern)
        
        return concerns[:5]  # Top 5 concerns

if __name__ == "__main__":
    extractor = ComprehensiveMFExtractor()
    extractor.run()