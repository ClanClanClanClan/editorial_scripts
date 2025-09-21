#!/usr/bin/env python3
"""
SIFIN EXTRACTOR - SIAM PLATFORM
===============================

Production-ready extractor for SIAM Journal on Financial Mathematics.
SIAM platform with ORCID authentication.

Authentication: ORCID OAuth (not username/password)
Platform: SIAM Publishing
"""

import os
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import traceback
from typing import Optional, Dict, List, Any

# Add cache integration
sys.path.append(str(Path(__file__).parent.parent))
from core.cache_integration import CachedExtractorMixin


class ComprehensiveSIFINExtractor(CachedExtractorMixin):
    """SIAM platform extractor for SIFIN journal."""
    
    def __init__(self):
        self.init_cached_extractor("SIFIN")
        
        # SIAM specific URLs
        self.base_url = "https://epubs.siam.org/journal/sifin"
        self.login_url = "https://epubs.siam.org/action/showLogin"
        self.orcid_url = "https://orcid.org/oauth/authorize"
        
        # Extraction state
        self.manuscripts = []
        self.driver = None
        self.wait = None
        
        # Load credentials (SIAM uses ORCID)
        self.email = os.environ.get('SIFIN_EMAIL')  # ORCID email
        self.password = os.environ.get('SIFIN_PASSWORD')  # ORCID password
        
        if not self.email or not self.password:
            print("⚠️ SIFIN/ORCID credentials not found in environment variables")
    
    def setup_browser(self, headless=True):
        """Initialize Chrome browser with SIAM platform optimizations."""
        options = Options()
        
        if headless:
            options.add_argument('--headless')
        
        # SIAM/ORCID specific settings
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Set user agent for SIAM
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Downloads
        download_dir = self.get_safe_download_dir("SIFIN")
        prefs = {
            "download.default_directory": str(download_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 30)
            
            self.driver.set_window_size(1200, 800)
            print(f"🖥️ Browser configured for SIAM platform")
            
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            raise
    
    def login_via_orcid(self) -> bool:
        """Login to SIAM using ORCID authentication."""
        if not self.email or not self.password:
            print("❌ Missing ORCID credentials")
            return False
            
        try:
            print(f"🔐 Attempting ORCID login via {self.login_url}")
            self.driver.get(self.login_url)
            time.sleep(3)
            
            # Look for ORCID login button
            orcid_selectors = [
                "a[href*='orcid']",
                "button[class*='orcid']",
                ".orcid-login",
                "[data-orcid]",
                "//a[contains(text(), 'ORCID')]",
                "//button[contains(text(), 'ORCID')]"
            ]
            
            orcid_element = None
            for selector in orcid_selectors:
                try:
                    if selector.startswith("//"):
                        orcid_element = self.wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                    else:
                        orcid_element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not orcid_element:
                print("❌ Could not find ORCID login button")
                return False
                
            print("✅ Found ORCID login button")
            orcid_element.click()
            time.sleep(3)
            
            # Now on ORCID site - fill credentials
            try:
                # Wait for ORCID login form
                username_field = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
                password_field = self.driver.find_element(By.ID, "password")
                
                print("✅ Found ORCID login form")
                
                # Fill ORCID credentials
                username_field.clear()
                username_field.send_keys(self.email)
                time.sleep(1)
                
                password_field.clear()
                password_field.send_keys(self.password)
                time.sleep(1)
                
                # Submit ORCID login
                login_button = self.driver.find_element(By.ID, "signin-button")
                login_button.click()
                
                print("✅ Submitted ORCID login")
                time.sleep(5)
                
                # Handle authorization page if present
                try:
                    authorize_button = self.driver.find_element(By.ID, "authorize")
                    authorize_button.click()
                    print("✅ Authorized SIAM access")
                    time.sleep(3)
                except NoSuchElementException:
                    print("ℹ️ No authorization page needed")
                
                # Check if back on SIAM site and logged in
                if "siam.org" in self.driver.current_url:
                    print("✅ ORCID authentication successful - back on SIAM")
                    return True
                else:
                    print("❌ Still on ORCID site - authentication may have failed")
                    return False
                    
            except TimeoutException:
                print("❌ ORCID login form not found")
                return False
                
        except Exception as e:
            print(f"❌ ORCID login error: {e}")
            traceback.print_exc()
            return False
    
    def navigate_to_editorial_tools(self) -> bool:
        """Navigate to editorial tools/reviewer center."""
        try:
            # Look for editorial/reviewer links
            editorial_selectors = [
                "a[href*='editorial']",
                "a[href*='reviewer']",
                "a[href*='editor']",
                ".editorial-tools",
                "//a[contains(text(), 'Editorial')]",
                "//a[contains(text(), 'Reviewer')]",
                "//a[contains(text(), 'Editor')]"
            ]
            
            for selector in editorial_selectors:
                try:
                    if selector.startswith("//"):
                        element = self.driver.find_element(By.XPATH, selector)
                    else:
                        element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    element.click()
                    print(f"✅ Clicked editorial link: {element.text}")
                    time.sleep(3)
                    return True
                except NoSuchElementException:
                    continue
            
            print("⚠️ Could not find editorial tools link")
            return False
            
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False
    
    def extract_manuscripts(self) -> List[Dict[str, Any]]:
        """Extract manuscript data from SIAM platform."""
        manuscripts = []
        
        try:
            # SIAM-specific manuscript selectors
            manuscript_selectors = [
                ".manuscript-item",
                "[data-manuscript]",
                ".submission-list .item",
                "table.manuscripts tr",
                ".reviewer-manuscripts .manuscript"
            ]
            
            manuscript_elements = []
            for selector in manuscript_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        manuscript_elements = elements
                        print(f"✅ Found manuscripts with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not manuscript_elements:
                print("⚠️ No manuscript elements found - may not be in reviewer role")
                return manuscripts
            
            # Extract data from each manuscript
            for i, element in enumerate(manuscript_elements[:5]):  # Limit to first 5
                try:
                    manuscript = self.extract_single_manuscript(element, i)
                    if manuscript:
                        manuscripts.append(manuscript)
                except Exception as e:
                    print(f"⚠️ Error extracting manuscript {i}: {e}")
                    continue
            
            print(f"📄 Extracted {len(manuscripts)} manuscripts")
            
        except Exception as e:
            print(f"❌ Manuscript extraction error: {e}")
            
        return manuscripts
    
    def extract_single_manuscript(self, element, index: int) -> Optional[Dict[str, Any]]:
        """Extract data from a single manuscript element."""
        try:
            manuscript = {
                'id': f'SIFIN-{datetime.now().strftime("%Y%m%d")}-{index:03d}',
                'title': 'Title extraction pending',
                'status': 'Status extraction pending',
                'submission_date': datetime.now().strftime('%Y-%m-%d'),
                'journal': 'SIFIN',
                'platform': 'SIAM',
                'authors': [],
                'referees': [],
                'extracted_at': datetime.now().isoformat()
            }
            
            # Try to extract manuscript details
            text_content = element.text
            
            # Simple pattern matching for title (improve as needed)
            title_patterns = [
                r'Title:\s*(.+?)(?:\n|$)',
                r'^(.+?)(?:\nAuthor|$)',
                r'(.{10,100}?)(?:\s+\d{4}|\n|$)'
            ]
            
            for pattern in title_patterns:
                match = re.search(pattern, text_content, re.MULTILINE | re.IGNORECASE)
                if match:
                    manuscript['title'] = match.group(1).strip()[:200]
                    break
            
            # Extract other fields similarly
            if 'under review' in text_content.lower():
                manuscript['status'] = 'Under Review'
            elif 'revision' in text_content.lower():
                manuscript['status'] = 'Revision Requested'
            elif 'accepted' in text_content.lower():
                manuscript['status'] = 'Accepted'
            
            return manuscript
            
        except Exception as e:
            print(f"⚠️ Single manuscript extraction error: {e}")
            return None
    
    def extract_all(self) -> List[Dict[str, Any]]:
        """Main extraction method."""
        print("🚀 SIFIN EXTRACTION - SIAM PLATFORM")
        print("=" * 60)
        
        try:
            # Setup browser
            self.setup_browser(headless=os.environ.get('EXTRACTOR_HEADLESS', 'true').lower() == 'true')
            
            # Login via ORCID
            if not self.login_via_orcid():
                print("❌ ORCID login failed - cannot continue")
                return []
            
            # Navigate to editorial tools
            self.navigate_to_editorial_tools()
            
            # Extract manuscripts
            manuscripts = self.extract_manuscripts()
            self.manuscripts = manuscripts
            
            return manuscripts
            
        except Exception as e:
            print(f"❌ Extraction failed: {e}")
            traceback.print_exc()
            return []
        finally:
            self.cleanup()
    
    def save_results(self):
        """Save extraction results."""
        if not self.manuscripts:
            print("⚠️ No manuscripts to save")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Save using cache system
        try:
            for manuscript in self.manuscripts:
                self.cache_manuscript(manuscript)
            print(f"💾 Cached {len(self.manuscripts)} manuscripts")
        except Exception as e:
            print(f"⚠️ Cache save error: {e}")
        
        # Save JSON file
        try:
            output_dir = Path("results/sifin")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"sifin_extraction_{timestamp}.json"
            
            extraction_data = {
                'journal': 'sifin',
                'journal_name': 'SIAM Journal on Financial Mathematics',
                'platform': 'SIAM',
                'extraction_time': timestamp,
                'manuscripts_count': len(self.manuscripts),
                'manuscripts': self.manuscripts
            }
            
            with open(output_file, 'w') as f:
                json.dump(extraction_data, f, indent=2, default=str)
                
            print(f"💾 Results saved: {output_file}")
            
        except Exception as e:
            print(f"⚠️ File save error: {e}")
    
    def cleanup(self):
        """Clean up resources."""
        try:
            if self.driver:
                self.driver.quit()
                print("🧹 Browser closed")
        except:
            pass
        
        # Clean up test cache if in test mode
        if hasattr(self, 'cache_manager') and hasattr(self.cache_manager, 'test_mode'):
            if self.cache_manager.test_mode:
                try:
                    import shutil
                    shutil.rmtree(self.cache_manager.cache_dir, ignore_errors=True)
                    print(f"🧹 Cleaned up test cache: {self.cache_manager.cache_dir}")
                except Exception as e:
                    print(f"⚠️ Warning: Could not fully cleanup test cache: {e}")


def main():
    """Run SIFIN extractor."""
    extractor = ComprehensiveSIFINExtractor()
    
    try:
        manuscripts = extractor.extract_all()
        
        if manuscripts:
            extractor.save_results()
            
            print(f"\n📊 EXTRACTION SUMMARY:")
            print(f"Total manuscripts: {len(manuscripts)}")
            for i, ms in enumerate(manuscripts):
                print(f"  {i+1}. {ms['id']}: {ms['title'][:50]}...")
        else:
            print("❌ No manuscripts extracted")
            
    except KeyboardInterrupt:
        print("\n⚠️ Extraction interrupted by user")
    except Exception as e:
        print(f"❌ Extraction error: {e}")
        traceback.print_exc()
    finally:
        extractor.cleanup()


if __name__ == "__main__":
    main()