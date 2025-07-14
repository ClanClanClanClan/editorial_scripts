"""
Advanced stealth and anti-bot detection manager
Provides sophisticated evasion techniques for journal scrapers
"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from playwright.async_api import Page, BrowserContext, Route


@dataclass
class StealthConfig:
    """Configuration for stealth measures"""
    randomize_viewport: bool = True
    randomize_user_agent: bool = True
    inject_webdriver_stealth: bool = True
    randomize_timing: bool = True
    block_tracking: bool = True
    fake_permissions: bool = True
    randomize_language: bool = True
    base_delay_range: tuple = (1.5, 4.0)
    typing_delay_range: tuple = (0.05, 0.15)
    mouse_move_delay: tuple = (0.1, 0.3)


class StealthManager:
    """Advanced stealth and anti-detection manager"""
    
    USER_AGENTS = [
        # Chrome on macOS
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        
        # Chrome on Windows
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        
        # Safari on macOS
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
        
        # Firefox on Windows/macOS
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
    ]
    
    VIEWPORTS = [
        {'width': 1920, 'height': 1080},
        {'width': 1440, 'height': 900},
        {'width': 1536, 'height': 864},
        {'width': 1366, 'height': 768},
        {'width': 1280, 'height': 720},
        {'width': 1680, 'height': 1050}
    ]
    
    LANGUAGES = [
        ['en-US', 'en'],
        ['en-GB', 'en'],
        ['en-CA', 'en'],
        ['en-AU', 'en']
    ]
    
    def __init__(self, config: Optional[StealthConfig] = None):
        """Initialize stealth manager"""
        self.config = config or StealthConfig()
        self.session_fingerprint = self._generate_session_fingerprint()
    
    def _generate_session_fingerprint(self) -> Dict[str, Any]:
        """Generate consistent session fingerprint"""
        return {
            'user_agent': random.choice(self.USER_AGENTS),
            'viewport': random.choice(self.VIEWPORTS),
            'language': random.choice(self.LANGUAGES),
            'timezone': random.choice(['America/New_York', 'America/Los_Angeles', 'America/Chicago', 'America/Denver']),
            'screen_depth': random.choice([24, 32]),
            'platform': random.choice(['MacIntel', 'Win32', 'Win64']),
            'session_id': f"sess_{int(time.time())}_{random.randint(1000, 9999)}"
        }
    
    async def configure_context(self, context: BrowserContext) -> BrowserContext:
        """Configure browser context with stealth measures"""
        
        # Set up request/response interception
        if self.config.block_tracking:
            await self._setup_request_blocking(context)
        
        # Add stealth scripts
        if self.config.inject_webdriver_stealth:
            await self._inject_stealth_scripts(context)
        
        return context
    
    async def _setup_request_blocking(self, context: BrowserContext):
        """Block tracking and analytics requests"""
        blocked_domains = [
            'google-analytics.com',
            'googletagmanager.com',
            'facebook.com',
            'twitter.com',
            'linkedin.com',
            'doubleclick.net',
            'googlesyndication.com',
            'amazon-adsystem.com',
            'adsystem.amazon.com',
            'scorecardresearch.com',
            'quantserve.com',
            'hotjar.com',
            'crazyegg.com',
            'mouseflow.com'
        ]
        
        blocked_types = ['image', 'font', 'media']  # Block non-essential resources
        
        async def route_handler(route: Route):
            url = route.request.url
            resource_type = route.request.resource_type
            
            # Block tracking domains
            if any(domain in url for domain in blocked_domains):
                await route.abort()
                return
            
            # Block non-essential resource types
            if resource_type in blocked_types:
                await route.abort()
                return
            
            # Continue with request
            await route.continue_()
        
        await context.route("**/*", route_handler)
    
    async def _inject_stealth_scripts(self, context: BrowserContext):
        """Inject comprehensive stealth scripts"""
        stealth_script = f"""
        // Override webdriver detection
        Object.defineProperty(navigator, 'webdriver', {{
            get: () => undefined,
        }});
        
        // Override automation flags
        delete window.navigator.__proto__.webdriver;
        delete window.navigator.webdriver;
        
        // Mock Chrome runtime
        window.chrome = {{
            runtime: {{
                onConnect: undefined,
                onMessage: undefined
            }}
        }};
        
        // Override permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({{ state: Notification.permission }}) :
                originalQuery(parameters)
        );
        
        // Mock plugins
        Object.defineProperty(navigator, 'plugins', {{
            get: () => [
                {{
                    name: 'Chrome PDF Plugin',
                    description: 'Portable Document Format',
                    filename: 'internal-pdf-viewer'
                }},
                {{
                    name: 'Chrome PDF Viewer',
                    description: 'PDF Viewer',
                    filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'
                }},
                {{
                    name: 'Native Client',
                    description: 'Native Client',
                    filename: 'internal-nacl-plugin'
                }}
            ]
        }});
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {{
            get: () => {self.session_fingerprint['language']}
        }});
        
        // Override platform
        Object.defineProperty(navigator, 'platform', {{
            get: () => '{self.session_fingerprint['platform']}'
        }});
        
        // Mock hardware concurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: () => {random.choice([4, 8, 12, 16])}
        }});
        
        // Override screen properties
        Object.defineProperty(screen, 'colorDepth', {{
            get: () => {self.session_fingerprint['screen_depth']}
        }});
        
        Object.defineProperty(screen, 'pixelDepth', {{
            get: () => {self.session_fingerprint['screen_depth']}
        }});
        
        // Mock timezone
        Date.prototype.getTimezoneOffset = function() {{
            return -{random.randint(-720, 720)};
        }};
        
        // Override iframe contentWindow
        const originalContentWindow = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {{
            get: function() {{
                const contentWindow = originalContentWindow.get.call(this);
                if (contentWindow) {{
                    contentWindow.navigator = window.navigator;
                }}
                return contentWindow;
            }}
        }});
        
        // Disable automation detection
        const originalToString = Function.prototype.toString;
        Function.prototype.toString = function() {{
            if (this === window.navigator.webdriver) {{
                return 'function webdriver() {{ [native code] }}';
            }}
            return originalToString.call(this);
        }};
        
        // Mock battery API
        Object.defineProperty(navigator, 'getBattery', {{
            get: () => undefined
        }});
        
        // Session fingerprint for consistency
        window.__stealth_session = '{self.session_fingerprint['session_id']}';
        """
        
        await context.add_init_script(stealth_script)
    
    async def human_like_delay(self, min_delay: Optional[float] = None, max_delay: Optional[float] = None):
        """Add human-like delay with randomization"""
        if min_delay is None or max_delay is None:
            min_delay, max_delay = self.config.base_delay_range
        
        # Add some randomness to make delays less predictable
        base_delay = random.uniform(min_delay, max_delay)
        
        # Add occasional longer pauses (simulating human behavior)
        if random.random() < 0.1:  # 10% chance of longer pause
            base_delay += random.uniform(2, 5)
        
        await asyncio.sleep(base_delay)
    
    async def human_like_typing(self, page: Page, selector: str, text: str, clear_first: bool = True):
        """Type text with human-like timing"""
        element = page.locator(selector)
        
        if clear_first:
            await element.clear()
        
        # Type with random delays between characters
        for char in text:
            await element.type(char)
            if self.config.randomize_timing:
                delay = random.uniform(*self.config.typing_delay_range)
                await asyncio.sleep(delay)
    
    async def human_like_click(self, page: Page, selector: str, button: str = 'left'):
        """Click with human-like behavior"""
        element = page.locator(selector)
        
        # Move mouse to element first (if possible)
        try:
            await element.hover()
            if self.config.randomize_timing:
                await asyncio.sleep(random.uniform(*self.config.mouse_move_delay))
        except:
            pass
        
        # Click with slight randomization
        await element.click(button=button)
        
        # Add small delay after click
        if self.config.randomize_timing:
            await self.human_like_delay(0.1, 0.5)
    
    async def scroll_like_human(self, page: Page, direction: str = 'down', distance: int = 300):
        """Scroll page like a human would"""
        scroll_steps = random.randint(3, 8)
        step_distance = distance // scroll_steps
        
        for _ in range(scroll_steps):
            if direction == 'down':
                await page.evaluate(f"window.scrollBy(0, {step_distance})")
            else:
                await page.evaluate(f"window.scrollBy(0, -{step_distance})")
            
            # Random delay between scroll steps
            await asyncio.sleep(random.uniform(0.1, 0.3))
    
    async def random_mouse_movement(self, page: Page):
        """Add random mouse movements to simulate human behavior"""
        if random.random() < 0.3:  # 30% chance of mouse movement
            viewport = await page.viewport_size()
            x = random.randint(0, viewport['width'])
            y = random.randint(0, viewport['height'])
            
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.4))
    
    def get_context_options(self) -> Dict[str, Any]:
        """Get browser context options with stealth settings"""
        options = {
            'user_agent': self.session_fingerprint['user_agent'],
            'viewport': self.session_fingerprint['viewport'],
            'locale': self.session_fingerprint['language'][0],
            'timezone_id': self.session_fingerprint['timezone'],
            'java_script_enabled': True,
            'bypass_csp': True,
            'extra_http_headers': {
                'Accept-Language': ','.join(self.session_fingerprint['language']) + ';q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-User': '?1',
                'Sec-Fetch-Dest': 'document',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': f'"{self.session_fingerprint["platform"]}"'
            }
        }
        
        return options
    
    async def wait_for_page_stability(self, page: Page, timeout: int = 30000):
        """Wait for page to be stable (no network activity)"""
        try:
            await page.wait_for_load_state('networkidle', timeout=timeout)
        except:
            # Fallback to domcontentloaded if networkidle fails
            await page.wait_for_load_state('domcontentloaded', timeout=timeout//2)
    
    async def detect_captcha_or_challenge(self, page: Page) -> bool:
        """Detect if page contains CAPTCHA or bot challenge"""
        captcha_indicators = [
            'captcha',
            'recaptcha', 
            'hcaptcha',
            'bot detection',
            'access denied',
            'blocked',
            'verify you are human',
            'security check',
            'unusual traffic'
        ]
        
        try:
            page_content = await page.content()
            page_content_lower = page_content.lower()
            
            for indicator in captcha_indicators:
                if indicator in page_content_lower:
                    return True
            
            # Check for specific CAPTCHA elements
            captcha_elements = [
                'iframe[src*="captcha"]',
                'iframe[src*="recaptcha"]',
                '.g-recaptcha',
                '#captcha',
                '.captcha'
            ]
            
            for selector in captcha_elements:
                element = page.locator(selector)
                if await element.count() > 0:
                    return True
            
            return False
            
        except:
            return False
    
    async def handle_detection_response(self, page: Page) -> bool:
        """Handle detection response (CAPTCHA, blocks, etc.)"""
        if await self.detect_captcha_or_challenge(page):
            # For now, just return False - could implement CAPTCHA solving later
            return False
        
        return True
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        return {
            'session_id': self.session_fingerprint['session_id'],
            'user_agent': self.session_fingerprint['user_agent'],
            'viewport': self.session_fingerprint['viewport'],
            'language': self.session_fingerprint['language'],
            'timezone': self.session_fingerprint['timezone'],
            'stealth_config': {
                'randomize_viewport': self.config.randomize_viewport,
                'randomize_user_agent': self.config.randomize_user_agent,
                'inject_webdriver_stealth': self.config.inject_webdriver_stealth,
                'block_tracking': self.config.block_tracking,
                'randomize_timing': self.config.randomize_timing
            }
        }
    
    def _check_chrome_available(self) -> bool:
        """Check if Chrome browser is available on the system"""
        import shutil
        import subprocess
        import os
        
        # Common Chrome executable names by platform
        chrome_names = [
            'google-chrome',
            'google-chrome-stable', 
            'chromium',
            'chromium-browser',
            'chrome',
            'Google Chrome'
        ]
        
        # Check PATH for Chrome executables
        for name in chrome_names:
            if shutil.which(name):
                return True
        
        # Check common installation paths
        import platform
        system = platform.system().lower()
        
        if system == 'darwin':  # macOS
            chrome_paths = [
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                '/Applications/Chromium.app/Contents/MacOS/Chromium'
            ]
        elif system == 'windows':
            chrome_paths = [
                'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
                'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
                'C:\\Users\\%USERNAME%\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe'
            ]
        else:  # Linux
            chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
                '/opt/google/chrome/chrome'
            ]
        
        # Check each path
        for path in chrome_paths:
            try:
                if os.path.exists(path):
                    return True
            except Exception:
                continue
        
        # Final check: try to run chrome with --version
        try:
            result = subprocess.run(['chrome', '--version'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            pass
        
        try:
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            pass
        
        return False