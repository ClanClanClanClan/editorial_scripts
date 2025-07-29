"""
Browser Configuration for Editorial Assistant

Defines browser types, configurations, and anti-detection settings.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class BrowserType(Enum):
    """Supported browser types."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    UNDETECTED_CHROME = "undetected_chrome"


@dataclass
class BrowserConfig:
    """
    Browser configuration settings.
    
    Provides unified configuration for browser initialization
    with anti-detection and performance optimization.
    """
    
    # Browser type
    browser_type: BrowserType = BrowserType.UNDETECTED_CHROME
    
    # Display settings
    headless: bool = True
    window_size: tuple = (1920, 1080)
    
    # Anti-detection settings
    disable_images: bool = True
    disable_gpu: bool = True
    no_sandbox: bool = True
    disable_dev_shm_usage: bool = True
    
    # Performance settings
    page_load_timeout: int = 30
    implicit_wait: int = 10
    script_timeout: int = 30
    
    # Download settings
    download_directory: Optional[str] = None
    enable_downloads: bool = True
    
    # Proxy settings
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    
    # User agent
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    # Additional Chrome options
    chrome_options: List[str] = field(default_factory=lambda: [
        "--disable-blink-features=AutomationControlled",
        "--disable-extensions-file-access-check",
        "--disable-extensions-http-throttling",
        "--disable-extensions",
        "--disable-hang-monitor",
        "--disable-ipc-flooding-protection",
        "--disable-popup-blocking",
        "--disable-prompt-on-repost",
        "--disable-renderer-backgrounding",
        "--disable-sync",
        "--force-fieldtrials=*BackgroundTracing/default/",
        "--metrics-recording-only",
        "--no-first-run",
        "--safebrowsing-disable-auto-update",
        "--enable-automation",
        "--password-store=basic",
        "--use-mock-keychain"
    ])
    
    # Firefox preferences
    firefox_prefs: Dict[str, any] = field(default_factory=lambda: {
        "dom.webdriver.enabled": False,
        "useAutomationExtension": False,
        "general.useragent.override": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "Gecko/20100101 Firefox/120.0"
        )
    })
    
    def get_chrome_options(self) -> List[str]:
        """
        Get Chrome options based on configuration.
        
        Returns:
            List of Chrome command line options
        """
        options = self.chrome_options.copy()
        
        if self.headless:
            options.append("--headless")
        
        if self.no_sandbox:
            options.append("--no-sandbox")
        
        if self.disable_dev_shm_usage:
            options.append("--disable-dev-shm-usage")
        
        if self.disable_gpu:
            options.append("--disable-gpu")
        
        if self.disable_images:
            options.extend([
                "--blink-settings=imagesEnabled=false",
                "--disable-plugins"
            ])
        
        options.append(f"--window-size={self.window_size[0]},{self.window_size[1]}")
        options.append(f"--user-agent={self.user_agent}")
        
        if self.proxy_host and self.proxy_port:
            options.append(f"--proxy-server={self.proxy_host}:{self.proxy_port}")
        
        return options
    
    def get_firefox_prefs(self) -> Dict[str, any]:
        """
        Get Firefox preferences based on configuration.
        
        Returns:
            Dictionary of Firefox preferences
        """
        prefs = self.firefox_prefs.copy()
        
        if self.disable_images:
            prefs["permissions.default.image"] = 2
        
        if self.download_directory:
            prefs.update({
                "browser.download.folderList": 2,
                "browser.download.dir": self.download_directory,
                "browser.helperApps.neverAsk.saveToDisk": "application/pdf"
            })
        
        return prefs
    
    @classmethod
    def for_stealth_mode(cls, **kwargs) -> 'BrowserConfig':
        """
        Create configuration optimized for stealth/anti-detection.
        
        Returns:
            BrowserConfig instance with stealth settings
        """
        config = cls(**kwargs)
        config.browser_type = BrowserType.UNDETECTED_CHROME
        config.chrome_options.extend([
            "--disable-blink-features=AutomationControlled",
            "--exclude-switches=enable-automation",
            "--useAutomationExtension=false"
        ])
        return config
    
    @classmethod
    def for_performance(cls, **kwargs) -> 'BrowserConfig':
        """
        Create configuration optimized for performance.
        
        Returns:
            BrowserConfig instance with performance settings
        """
        config = cls(**kwargs)
        config.disable_images = True
        config.disable_gpu = True
        config.chrome_options.extend([
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-features=TranslateUI",
            "--disable-ipc-flooding-protection"
        ])
        return config
    
    @classmethod  
    def for_debugging(cls, **kwargs) -> 'BrowserConfig':
        """
        Create configuration optimized for debugging.
        
        Returns:
            BrowserConfig instance with debugging settings
        """
        config = cls(**kwargs)
        config.headless = False
        config.chrome_options.extend([
            "--remote-debugging-port=9222",
            "--enable-logging",
            "--v=1"
        ])
        return config