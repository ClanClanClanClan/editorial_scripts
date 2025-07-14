"""
Base SIAM Extractor - FIXED with better timeout handling and retry logic
"""

import asyncio
import logging
import re
import os
import sys
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
from pathlib import Path

# Add paths for credential manager
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from unified_system.core.base_extractor import BaseExtractor, Manuscript, Referee

# Import credential manager (supports secure storage and 1Password)
try:
    from src.core.credential_manager import get_credential_manager
    HAS_CREDENTIAL_MANAGER = True
except ImportError:
    try:
        from core.credential_manager import get_credential_manager
        HAS_CREDENTIAL_MANAGER = True
    except ImportError:
        HAS_CREDENTIAL_MANAGER = False
        logging.warning("Credential manager not available - falling back to environment variables")

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False
    logging.warning("PyPDF2 not installed - PDF text extraction will be limited")

logger = logging.getLogger(__name__)


class SIAMBaseExtractor(BaseExtractor):
    """Base class for SIAM journal extractors with improved timeout handling"""
    
    # Common SIAM settings
    login_type = "orcid"
    requires_cloudflare_wait = True
    cloudflare_wait_seconds = 60  # Proven working time
    
    # Improved timeout settings
    DEFAULT_TIMEOUT = 120000  # 2 minutes instead of 1
    NAVIGATION_TIMEOUT = 90000  # 90 seconds for page navigation
    ELEMENT_TIMEOUT = 30000  # 30 seconds for element waiting
    
    # Retry settings
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._manuscript_urls = []
        self.session_cookies = None
        self._setup_credential_manager()
    
    def _setup_credential_manager(self):
        """Set up credential manager and verify 1Password access"""
        if HAS_CREDENTIAL_MANAGER:
            try:
                # Test credential manager
                cred_manager = get_credential_manager()
                test_creds = cred_manager.get_credentials('SICON')
                
                if test_creds.get('email') and test_creds.get('password'):
                    logger.info(f"✅ Secure credential manager ready: {test_creds['email'][:3]}****")
                    self._has_secure_creds = True
                else:
                    logger.warning("⚠️ Credential manager available but no ORCID credentials found")
                    self._has_secure_creds = False
            except Exception as e:
                logger.warning(f"⚠️ Credential manager failed: {e}")
                self._has_secure_creds = False
        else:
            logger.warning("⚠️ Credential manager not available")
            self._has_secure_creds = False
    
    async def _goto_with_retry(self, url: str, timeout: Optional[int] = None) -> bool:
        """Navigate to URL with retry logic"""
        timeout = timeout or self.NAVIGATION_TIMEOUT
        
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"🌐 Navigating to {url} (attempt {attempt + 1}/{self.MAX_RETRIES})")
                await self.page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                
                # Give page time to settle
                await asyncio.sleep(2)
                return True
                
            except asyncio.TimeoutError:
                logger.warning(f"⏱️ Navigation timeout (attempt {attempt + 1})")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                else:
                    logger.error(f"❌ Failed to navigate to {url} after {self.MAX_RETRIES} attempts")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Navigation error: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                    continue
                else:
                    return False
        
        return False
    
    async def _authenticate_custom(self) -> bool:
        """SIAM journals use ORCID, handled by base class"""
        return True
    
    async def _authenticate_orcid(self) -> bool:
        """ORCID authentication flow with improved error handling"""
        try:
            logger.info(f"🔐 Starting ORCID authentication for {self.journal_name}")
            
            # Navigate to login page with retry
            login_url = f"{self.base_url}/cgi-bin/main.plex"
            if not await self._goto_with_retry(login_url):
                return False
            
            # Handle Cloudflare - proven 60 second wait
            await self._handle_cloudflare_challenge()
            
            # Handle modals
            await self._handle_privacy_modals()
            
            # Find and click ORCID login - with retry
            if not await self._click_orcid_login_with_retry():
                return False
            
            # Enter ORCID credentials
            if not await self._enter_orcid_credentials():
                return False
            
            # Verify authentication
            await asyncio.sleep(5)
            success = await self._verify_authentication()
            
            if success:
                # Store cookies for authenticated downloads
                self.session_cookies = await self.page.context.cookies()
                logger.info(f"✅ Authentication successful for {self.journal_name}")
                return True
            else:
                logger.error(f"❌ Authentication failed for {self.journal_name}")
                return False
                
        except Exception as e:
            logger.error(f"❌ ORCID authentication error: {e}")
            return False
    
    async def _handle_cloudflare_challenge(self):
        """Handle Cloudflare with improved detection"""
        try:
            content = await self.page.content()
            if "cloudflare" in content.lower() or "checking your browser" in content.lower():
                logger.info("🛡️ Cloudflare detected - waiting up to 60 seconds...")
                
                # Try multiple detection methods
                try:
                    await self.page.wait_for_function(
                        """() => {
                            const content = document.body ? document.body.innerText.toLowerCase() : '';
                            return content.includes('login') || 
                                   content.includes('orcid') || 
                                   content.includes('sign in') ||
                                   !content.includes('cloudflare');
                        }""",
                        timeout=self.cloudflare_wait_seconds * 1000
                    )
                    logger.info("✅ Cloudflare challenge passed")
                except:
                    # Fallback: just wait
                    logger.info("⏳ Waiting for Cloudflare...")
                    await asyncio.sleep(15)
                    
        except Exception as e:
            logger.warning(f"Cloudflare handling error: {e}")
            await asyncio.sleep(15)
    
    async def _handle_privacy_modals(self):
        """Handle cookie and privacy modals"""
        try:
            await asyncio.sleep(3)
            
            # Dismiss cookie modal with JavaScript
            await self.page.evaluate("""
                const cookieModal = document.getElementById('cookie-policy-layer-bg');
                if (cookieModal) cookieModal.style.display = 'none';
                
                const cookieLayer = document.getElementById('cookie-policy-layer');
                if (cookieLayer) cookieLayer.style.display = 'none';
                
                // Also try to click any accept buttons
                const acceptButtons = document.querySelectorAll('[id*="accept"], [class*="accept"], button:contains("Accept")');
                acceptButtons.forEach(btn => {
                    if (btn && btn.click) btn.click();
                });
            """)
            
            logger.info("✅ Privacy modals dismissed")
            
        except Exception as e:
            logger.debug(f"Modal handling: {e}")
    
    async def _click_orcid_login_with_retry(self) -> bool:
        """Click ORCID login button with retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"🔍 Looking for ORCID login button (attempt {attempt + 1})")
                
                # Try multiple selectors
                selectors = [
                    'a[href*="orcid"]:has-text("Log in with ORCID")',
                    'a[href*="orcid"]:has-text("Login with ORCID")',
                    'a[href*="orcid"]:has-text("ORCID")',
                    'a:has-text("Log in with ORCID")',
                    'button:has-text("ORCID")',
                    'a[onclick*="orcid"]'
                ]
                
                clicked = False
                for selector in selectors:
                    try:
                        btn = self.page.locator(selector).first
                        if await btn.is_visible(timeout=5000):
                            await btn.click()
                            logger.info(f"✅ Clicked ORCID login: {selector}")
                            clicked = True
                            break
                    except:
                        continue
                
                if clicked:
                    # Wait for navigation
                    try:
                        await self.page.wait_for_url("*orcid.org*", timeout=self.ELEMENT_TIMEOUT)
                        logger.info("✅ Navigated to ORCID login page")
                        return True
                    except:
                        # Check if we're on ORCID page
                        if "orcid.org" in self.page.url:
                            return True
                
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
                    
            except Exception as e:
                logger.error(f"Error clicking ORCID login: {e}")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAY)
        
        logger.error("❌ Failed to click ORCID login after all attempts")
        return False
    
    async def _enter_orcid_credentials(self) -> bool:
        """Enter ORCID credentials with better error handling"""
        try:
            # Wait for ORCID page
            await self.page.wait_for_load_state('domcontentloaded')
            await asyncio.sleep(3)
            
            # Get credentials
            email, password = self._get_orcid_credentials()
            if not email or not password:
                logger.error("❌ No ORCID credentials available")
                return False
            
            logger.info(f"📝 Entering ORCID credentials for: {email}")
            
            # Try multiple selectors for email field
            email_entered = False
            email_selectors = [
                'input[name="userId"]',
                'input[id="userId"]',
                'input[type="email"]',
                'input[name="username"]',
                'input[placeholder*="email"]'
            ]
            
            for selector in email_selectors:
                try:
                    email_field = self.page.locator(selector).first
                    if await email_field.is_visible(timeout=5000):
                        await email_field.fill(email)
                        email_entered = True
                        logger.info(f"✅ Email entered using: {selector}")
                        break
                except:
                    continue
            
            if not email_entered:
                logger.error("❌ Could not find email field")
                return False
            
            # Password field
            password_entered = False
            password_selectors = [
                'input[name="password"]',
                'input[id="password"]',
                'input[type="password"]'
            ]
            
            for selector in password_selectors:
                try:
                    password_field = self.page.locator(selector).first
                    if await password_field.is_visible(timeout=5000):
                        await password_field.fill(password)
                        password_entered = True
                        logger.info(f"✅ Password entered using: {selector}")
                        break
                except:
                    continue
            
            if not password_entered:
                logger.error("❌ Could not find password field")
                return False
            
            # Submit
            submit_clicked = False
            submit_selectors = [
                "button:has-text('Sign in')",
                "button:has-text('Sign in to ORCID')",
                "button[type='submit']",
                "input[type='submit']"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = self.page.locator(selector).first
                    if await submit_btn.is_visible(timeout=5000):
                        await submit_btn.click()
                        submit_clicked = True
                        logger.info(f"✅ Clicked submit: {selector}")
                        break
                except:
                    continue
            
            if not submit_clicked:
                logger.error("❌ Could not find submit button")
                return False
            
            logger.info("🔑 Submitted ORCID credentials")
            
            # Wait for redirect back to journal
            try:
                await self.page.wait_for_url(f"{self.base_url}*", timeout=30000)
                logger.info("✅ Redirected back to journal")
                return True
            except:
                # Check if we need to authorize access
                try:
                    authorize_btn = self.page.locator("button:has-text('Continue')")
                    if await authorize_btn.is_visible(timeout=5000):
                        await authorize_btn.click()
                        logger.info("🔗 Authorized journal access")
                        await self.page.wait_for_url(f"{self.base_url}*", timeout=15000)
                        logger.info("✅ Redirected back to journal after authorization")
                        return True
                except:
                    logger.warning("⚠️ Still on ORCID page after credentials")
                    
                # Check if we're actually authenticated
                if self.base_url in self.page.url:
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"❌ Error entering ORCID credentials: {e}")
            return False
    
    async def _verify_authentication(self) -> bool:
        """Verify authentication success with multiple checks"""
        try:
            # Wait for page to load
            await asyncio.sleep(5)
            
            # Handle any post-auth modals
            await self._handle_post_auth_modals()
            
            current_url = self.page.url
            content = await self.page.content()
            content_lower = content.lower()
            
            # Multiple verification methods
            auth_checks = [
                # URL checks
                self.base_url in current_url and "login" not in current_url.lower(),
                
                # Content checks
                any(word in content_lower for word in ["logout", "sign out", "manuscripts", "editorial"]),
                
                # Element checks (with error handling)
                await self._check_auth_elements()
            ]
            
            if any(auth_checks):
                logger.info("✅ Authentication verified")
                return True
            else:
                logger.error(f"❌ Authentication failed - current URL: {current_url}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Authentication verification error: {e}")
            return False
    
    async def _check_auth_elements(self) -> bool:
        """Check for authenticated elements"""
        try:
            auth_selectors = [
                "a:has-text('Under Review')",
                "a[href*='manuscript']",
                "a.ndt_task_link",
                "a:has-text('Manuscripts')",
                "[class*='logout']"
            ]
            
            for selector in auth_selectors:
                try:
                    if await self.page.locator(selector).count() > 0:
                        return True
                except:
                    continue
                    
            return False
            
        except:
            return False
    
    async def _handle_post_auth_modals(self):
        """Handle privacy and other modals after authentication"""
        try:
            await asyncio.sleep(2)
            
            # Try to click Continue/Accept buttons
            modal_buttons = [
                "input[value='Continue']",
                "button:has-text('Continue')",
                "button:has-text('Accept')",
                "button:has-text('OK')"
            ]
            
            for selector in modal_buttons:
                try:
                    btn = self.page.locator(selector).first
                    if await btn.is_visible(timeout=3000):
                        await btn.click()
                        await asyncio.sleep(2)
                        logger.info(f"✅ Clicked modal button: {selector}")
                        break
                except:
                    continue
            
            # JavaScript fallback
            await self.page.evaluate("""
                // Remove modal overlays
                const modals = document.querySelectorAll('.modal, .popup, .overlay, [id*="modal"]');
                modals.forEach(modal => modal.remove());
                
                // Remove high z-index elements
                const elements = document.querySelectorAll('*');
                elements.forEach(el => {
                    const zIndex = window.getComputedStyle(el).zIndex;
                    if (zIndex && parseInt(zIndex) > 9999) {
                        el.style.display = 'none';
                    }
                });
            """)
            
        except Exception as e:
            logger.debug(f"Modal handling: {e}")
    
    def _get_orcid_credentials(self) -> tuple:
        """Get ORCID credentials from secure storage or environment"""
        email = None
        password = None
        
        # Try secure credential manager first
        if self._has_secure_creds:
            try:
                cred_manager = get_credential_manager()
                creds = cred_manager.get_credentials('SICON')
                email = creds.get('email') or creds.get('username')
                password = creds.get('password')
                if email and password:
                    logger.info("✅ Using secure credentials")
                    return email, password
            except Exception as e:
                logger.warning(f"Secure credentials failed: {e}")
        
        # Fallback to environment variables
        email = os.getenv('ORCID_EMAIL')
        password = os.getenv('ORCID_PASSWORD')
        
        if email and password:
            logger.info("✅ Using environment credentials")
        else:
            logger.warning("⚠️ No credentials found")
            
        return email, password