#!/usr/bin/env python3
"""
Hybrid Selenium+Playwright approach for MAFE journal scraping.
This combines the stealth capabilities of Playwright with Selenium's robustness.
"""

import os
import time
import logging
import asyncio
import json
import random
from typing import Dict, List, Optional, Any
from pathlib import Path
from core.paper_downloader import get_paper_downloader

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import undetected_chromedriver as uc

# Playwright imports
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

# Local imports
from core.credential_manager import get_credential_manager
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class MAFEHybridScraper:
    """
    Hybrid scraper that uses both Selenium and Playwright for maximum success.
    Strategy:
    1. Use Playwright for initial navigation and stealth
    2. Use Selenium for complex interactions and form filling
    3. Fall back between methods as needed
    """
    
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.selenium_driver = None
        self.playwright_page = None
        self.playwright_browser = None
        self.playwright_context = None
        self.playwright_engine = None
        
        self.paper_downloader = get_paper_downloader()
        # URLs
        self.base_url = "https://www2.cloud.editorialmanager.com/mafe/"
        self.login_url = "https://www2.cloud.editorialmanager.com/mafe/login.asp"
        self.main_url = "https://www2.cloud.editorialmanager.com/mafe/default2.aspx"
        
        # Get credentials
        cred_manager = get_credential_manager()
        mafe_creds = cred_manager.get_journal_credentials("MAFE")
        self.username = mafe_creds.get('username')
        self.password = mafe_creds.get('password')
        
        if not self.username or not self.password:
            raise ValueError("MAFE credentials not found in credential manager")
    
    async def setup_playwright(self):
        """Initialize Playwright with stealth settings"""
        try:
            self.playwright_engine = await async_playwright().start()
            
            # Launch browser with stealth settings
            self.playwright_browser = await self.playwright_engine.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',
                    '--disable-javascript',
                    '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )
            
            # Create context with additional stealth
            self.playwright_context = await self.playwright_browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                java_script_enabled=True,
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            )
            
            # Add stealth script
            await self.playwright_context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                window.chrome = {
                    runtime: {},
                };
                
                Object.defineProperty(navigator, 'permissions', {
                    get: () => ({
                        query: () => Promise.resolve({ state: 'granted' }),
                    }),
                });
            """)
            
            self.playwright_page = await self.playwright_context.new_page()
            
            if self.debug:
                logger.info("Playwright setup complete")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Playwright: {e}")
            return False
    
    def setup_selenium(self):
        """Initialize Selenium with undetected Chrome"""
        try:
            # Configure Chrome options
            options = uc.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-setuid-sandbox')
            options.add_argument('--disable-extensions')
            options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Create unique profile directory
            profile_dir = Path.home() / ".mafe_chrome_profile" / str(int(time.time()))
            profile_dir.mkdir(parents=True, exist_ok=True)
            options.add_argument(f'--user-data-dir={profile_dir}')
            
            # Initialize undetected Chrome
            self.selenium_driver = uc.Chrome(options=options)
            
            if self.debug:
                logger.info("Selenium setup complete")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Selenium: {e}")
            return False
    
    async def playwright_navigate_and_analyze(self, url: str) -> Dict[str, Any]:
        """Use Playwright to navigate and analyze the page structure"""
        try:
            await self.playwright_page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(3)
            
            # Analyze page structure
            page_info = {
                'title': await self.playwright_page.title(),
                'url': self.playwright_page.url,
                'has_iframes': len(await self.playwright_page.query_selector_all('iframe')) > 0,
                'iframes': [],
                'forms': [],
                'login_fields': []
            }
            
            # Analyze iframes
            iframes = await self.playwright_page.query_selector_all('iframe')
            for i, iframe in enumerate(iframes):
                src = await iframe.get_attribute('src')
                page_info['iframes'].append({
                    'index': i,
                    'src': src,
                    'is_login': src and 'login' in src.lower() if src else False
                })
            
            # Analyze forms
            forms = await self.playwright_page.query_selector_all('form')
            for form in forms:
                action = await form.get_attribute('action')
                method = await form.get_attribute('method')
                page_info['forms'].append({
                    'action': action,
                    'method': method
                })
            
            # Look for login fields
            username_selectors = ['#username', '[name="username"]', '[type="text"]']
            password_selectors = ['#password', '#passwordTextbox', '[name="password"]', '[type="password"]']
            
            for selector in username_selectors:
                element = await self.playwright_page.query_selector(selector)
                if element:
                    page_info['login_fields'].append({
                        'type': 'username',
                        'selector': selector,
                        'found': True
                    })
                    break
            
            for selector in password_selectors:
                element = await self.playwright_page.query_selector(selector)
                if element:
                    page_info['login_fields'].append({
                        'type': 'password',
                        'selector': selector,
                        'found': True
                    })
                    break
            
            return page_info
            
        except Exception as e:
            logger.error(f"Playwright navigation failed: {e}")
            return {}
    
    async def playwright_login_attempt(self) -> bool:
        """Attempt login using Playwright"""
        try:
            # Navigate to login page
            await self.playwright_page.goto(self.login_url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Try to fill login form
            username_filled = False
            password_filled = False
            
            # Try different username selectors
            username_selectors = ['#username', '[name="username"]', 'input[type="text"]']
            for selector in username_selectors:
                try:
                    await self.playwright_page.fill(selector, self.username)
                    username_filled = True
                    if self.debug:
                        logger.info(f"Filled username with selector: {selector}")
                    break
                except:
                    continue
            
            # Try different password selectors
            password_selectors = ['#passwordTextbox', '#password', '[name="password"]', 'input[type="password"]']
            for selector in password_selectors:
                try:
                    await self.playwright_page.fill(selector, self.password)
                    password_filled = True
                    if self.debug:
                        logger.info(f"Filled password with selector: {selector}")
                    break
                except:
                    continue
            
            if not (username_filled and password_filled):
                logger.error("Could not fill login fields with Playwright")
                return False
            
            # Try to submit form
            submit_selectors = [
                '[name="editorLogin"]',
                '[value="Editor Login"]',
                'input[type="submit"]',
                'button[type="submit"]'
            ]
            
            for selector in submit_selectors:
                try:
                    await self.playwright_page.click(selector)
                    if self.debug:
                        logger.info(f"Clicked submit with selector: {selector}")
                    break
                except:
                    continue
            
            # Wait for navigation
            await self.playwright_page.wait_for_load_state('networkidle', timeout=30000)
            
            # Check if login was successful
            current_url = self.playwright_page.url
            page_content = await self.playwright_page.content()
            
            if 'Associate Editor' in page_content or 'default2.aspx' in current_url:
                logger.info("Playwright login successful")
                return True
            else:
                logger.error("Playwright login failed")
                return False
                
        except Exception as e:
            logger.error(f"Playwright login attempt failed: {e}")
            return False
    
    def selenium_login_attempt(self) -> bool:
        """Attempt login using Selenium"""
        try:
            self.selenium_driver.get(self.login_url)
            time.sleep(3)
            
            # Try to find and fill login fields
            username_field = None
            password_field = None
            
            # Try different selectors
            username_selectors = [
                (By.ID, "username"),
                (By.NAME, "username"),
                (By.CSS_SELECTOR, 'input[type="text"]')
            ]
            
            password_selectors = [
                (By.ID, "passwordTextbox"),
                (By.ID, "password"),
                (By.NAME, "password"),
                (By.CSS_SELECTOR, 'input[type="password"]')
            ]
            
            for by, selector in username_selectors:
                try:
                    username_field = WebDriverWait(self.selenium_driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if username_field:
                        break
                except:
                    continue
            
            for by, selector in password_selectors:
                try:
                    password_field = WebDriverWait(self.selenium_driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if password_field:
                        break
                except:
                    continue
            
            if not (username_field and password_field):
                logger.error("Could not find login fields with Selenium")
                return False
            
            # Fill fields
            username_field.clear()
            username_field.send_keys(self.username)
            password_field.clear()
            password_field.send_keys(self.password)
            
            # Find and click submit button
            submit_selectors = [
                (By.NAME, "editorLogin"),
                (By.XPATH, "//input[@value='Editor Login']"),
                (By.CSS_SELECTOR, 'input[type="submit"]'),
                (By.CSS_SELECTOR, 'button[type="submit"]')
            ]
            
            for by, selector in submit_selectors:
                try:
                    submit_btn = WebDriverWait(self.selenium_driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    submit_btn.click()
                    if self.debug:
                        logger.info(f"Clicked submit with Selenium selector: {selector}")
                    break
                except:
                    continue
            
            # Wait for navigation
            WebDriverWait(self.selenium_driver, 30).until(
                lambda d: "Associate Editor" in d.page_source or "default2.aspx" in d.current_url
            )
            
            logger.info("Selenium login successful")
            return True
            
        except Exception as e:
            logger.error(f"Selenium login attempt failed: {e}")
            return False
    
    async def hybrid_login(self) -> bool:
        """Perform hybrid login using both Playwright and Selenium"""
        try:
            # Setup both engines
            if not await self.setup_playwright():
                logger.error("Failed to setup Playwright")
                return False
            
            if not self.setup_selenium():
                logger.error("Failed to setup Selenium")
                return False
            
            # First, analyze the page with Playwright
            logger.info("Analyzing page structure with Playwright...")
            page_info = await self.playwright_navigate_and_analyze(self.main_url)
            
            if self.debug:
                logger.info(f"Page analysis: {json.dumps(page_info, indent=2)}")
            
            # Try Playwright login first
            logger.info("Attempting login with Playwright...")
            if await self.playwright_login_attempt():
                return True
            
            # If Playwright fails, try Selenium
            logger.info("Playwright login failed, trying Selenium...")
            if self.selenium_login_attempt():
                return True
            
            # If both fail, try iframe approach with Selenium
            logger.info("Both direct logins failed, trying iframe approach...")
            return self.selenium_iframe_login()
            
        except Exception as e:
            logger.error(f"Hybrid login failed: {e}")
            return False
    
    def selenium_iframe_login(self) -> bool:
        """Use Selenium to handle iframe-based login"""
        try:
            self.selenium_driver.get(self.main_url)
            time.sleep(5)
            
            # Find all iframes
            iframes = self.selenium_driver.find_elements(By.TAG_NAME, "iframe")
            logger.info(f"Found {len(iframes)} iframes")
            
            for i, iframe in enumerate(iframes):
                try:
                    iframe_src = iframe.get_attribute("src")
                    if self.debug:
                        logger.info(f"Checking iframe {i+1}: {iframe_src}")
                    
                    # Switch to iframe
                    self.selenium_driver.switch_to.frame(iframe)
                    time.sleep(2)
                    
                    # Try to find login fields
                    username_field = None
                    password_field = None
                    
                    try:
                        username_field = self.selenium_driver.find_element(By.ID, "username")
                        password_field = self.selenium_driver.find_element(By.ID, "passwordTextbox")
                    except:
                        try:
                            username_field = self.selenium_driver.find_element(By.NAME, "username")
                            password_field = self.selenium_driver.find_element(By.NAME, "password")
                        except:
                            pass
                    
                    if username_field and password_field:
                        logger.info(f"Found login fields in iframe {i+1}")
                        
                        # Fill and submit
                        username_field.clear()
                        username_field.send_keys(self.username)
                        password_field.clear()
                        password_field.send_keys(self.password)
                        
                        # Find submit button
                        try:
                            submit_btn = self.selenium_driver.find_element(By.NAME, "editorLogin")
                            submit_btn.click()
                            
                            # Switch back to main frame
                            self.selenium_driver.switch_to.default_content()
                            time.sleep(3)
                            
                            # Check if login was successful
                            if "Associate Editor" in self.selenium_driver.page_source:
                                logger.info("Iframe login successful")
                                return True
                        except:
                            pass
                    
                    # Switch back to main frame
                    self.selenium_driver.switch_to.default_content()
                    
                except Exception as e:
                    logger.error(f"Error with iframe {i+1}: {e}")
                    try:
                        self.selenium_driver.switch_to.default_content()
                    except:
                        pass
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Iframe login failed: {e}")
            return False
    
    def extract_manuscripts(self) -> List[Dict[str, Any]]:
        """Extract manuscripts using Selenium after successful login"""
        try:
            if not self.selenium_driver:
                logger.error("Selenium driver not initialized")
                return []
            
            # Navigate to manuscripts page or use current page
            manuscripts = []
            
            # Find manuscript table
            soup = BeautifulSoup(self.selenium_driver.page_source, 'html.parser')
            table = soup.find('table')
            
            if not table:
                logger.error("No manuscript table found")
                return []
            
            # Extract manuscripts from table
            for row in table.find_all('tr')[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    try:
                        manuscript = {
                            'manuscript_id': cells[0].get_text(strip=True),
                            'title': cells[1].get_text(strip=True),
                            'author': cells[2].get_text(strip=True),
                            'status': cells[3].get_text(strip=True),
                            'referees': []
                        }
                        manuscripts.append(manuscript)
                    except Exception as e:
                        logger.error(f"Error extracting manuscript row: {e}")
                        continue
            
            logger.info(f"Extracted {len(manuscripts)} manuscripts")
            return manuscripts
            
        except Exception as e:
            logger.error(f"Error extracting manuscripts: {e}")
            return []
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.selenium_driver:
                self.selenium_driver.quit()
            
            if self.playwright_context:
                asyncio.create_task(self.playwright_context.close())
            
            if self.playwright_browser:
                asyncio.create_task(self.playwright_browser.close())
            
            if self.playwright_engine:
                asyncio.create_task(self.playwright_engine.stop())
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def scrape_manuscripts_and_emails(self) -> List[Dict[str, Any]]:
        """Main scraping method using hybrid approach"""
        try:
            # Perform hybrid login
            if not await self.hybrid_login():
                logger.error("Hybrid login failed")
                return []
            
            # Extract manuscripts
            manuscripts = self.extract_manuscripts()
            
            return manuscripts
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return []
        finally:
            self.cleanup()

# Compatibility wrapper for existing code
class MAFEJournal:
    """Wrapper class for compatibility with existing code"""
    
    def __init__(self, driver=None, debug=True):
        self.driver = driver
        self.debug = debug
        self.hybrid_scraper = MAFEHybridScraper(debug=debug)
    
    def scrape_manuscripts_and_emails(self):
        """Main method for compatibility"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.hybrid_scraper.scrape_manuscripts_and_emails()
            )
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Hybrid scraping failed: {e}")
        # Download papers and reports
        enhanced_manuscripts = self.download_and_analyze_manuscripts([])
        return enhanced_manuscripts