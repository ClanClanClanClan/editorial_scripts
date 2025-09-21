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
        """FIXED: Simplified popup handling that doesn't get stuck."""
        if not popup_url_or_element:
            return ""

        original_window = self.driver.current_window_handle
        email = ""

        try:
            # Step 1: Open the popup
            if hasattr(popup_url_or_element, 'click'):
                popup_url_or_element.click()
            else:
                return ""  # Skip non-clickable elements

            # Step 2: Wait briefly for popup
            time.sleep(2)

            # Step 3: Check if popup opened
            windows = self.driver.window_handles
            if len(windows) <= 1:
                print("         ⚠️ No popup opened")
                return ""

            # Step 4: Switch to popup
            popup_window = windows[-1]
            self.driver.switch_to.window(popup_window)

            # Step 5: Quick email extraction - just check URL and basic page
            try:
                current_url = self.driver.current_url

                # Check URL for email
                if 'EMAIL_TO=' in current_url or '@' in current_url:
                    import re
                    from urllib.parse import unquote

                    # Look for email pattern in URL
                    email_pattern = r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
                    matches = re.findall(email_pattern, unquote(current_url))

                    for match in matches:
                        if 'dylan.possamai' not in match.lower():
                            email = match
                            print(f"         ✅ Email from URL: {email}")
                            break

                # If no email in URL, do a VERY quick check of page
                if not email:
                    # Just grab first 5000 chars of page source
                    try:
                        page_text = self.driver.page_source[:5000]

                        # Quick email pattern search
                        import re
                        email_pattern = r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})'
                        matches = re.findall(email_pattern, page_text)

                        for match in matches:
                            if 'dylan.possamai' not in match.lower() and 'manuscript' not in match.lower():
                                email = match
                                print(f"         ✅ Email from page: {email}")
                                break
                    except:
                        pass

            except Exception as e:
                print(f"         ⚠️ Email extraction error: {e}")

        except Exception as e:
            print(f"         ❌ Popup handling error: {e}")

        finally:
            # CRITICAL: Clean return to original window
            try:
                # Close all popups
                for window in self.driver.window_handles:
                    if window != original_window:
                        try:
                            self.driver.switch_to.window(window)
                            self.driver.close()
                        except:
                            pass

                # Return to original
                self.driver.switch_to.window(original_window)

                # IMPORTANT: Reset any frame context
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass

            except:
                # Emergency recovery
                try:
                    if self.driver.window_handles:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        self.driver.switch_to.default_content()
                except:
                    pass

        return email


if __name__ == "__main__":
    extractor = ComprehensiveMFExtractor()
    extractor.run()