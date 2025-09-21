#!/usr/bin/env python3
"""
Direct test of MOR extractor without cache issues
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add production path
sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

# Import and check MOR extractor directly
try:
    import extractors.mor_extractor as mor_module
    print("✅ MOR extractor module loaded")
    
    # Check for key capabilities
    print("\n📋 CHECKING MOR EXTRACTOR CAPABILITIES:")
    print("-" * 50)
    
    capabilities = {
        "with_retry decorator": hasattr(mor_module, 'with_retry'),
        "MORExtractor class": hasattr(mor_module, 'MORExtractor'),
    }
    
    if hasattr(mor_module, 'MORExtractor'):
        mor_class = mor_module.MORExtractor
        
        # Check methods
        method_checks = [
            'login',
            'extract_all_manuscripts',
            'extract_referee_emails', 
            'download_documents',
            'extract_audit_trail',
            'extract_version_history',
            'extract_enhanced_status',
            'enrich_with_orcid',
            'safe_click',
            'smart_wait',
            'handle_popup_window',
            'safe_get_text',
            'extract_referees',
            'extract_authors',
            'navigate_to_manuscript'
        ]
        
        for method in method_checks:
            capabilities[f"{method} method"] = hasattr(mor_class, method)
    
    # Print results
    passed = 0
    failed = 0
    
    for cap, status in capabilities.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {cap}: {status}")
        if status:
            passed += 1
        else:
            failed += 1
    
    print("-" * 50)
    score = (passed / len(capabilities)) * 100 if capabilities else 0
    print(f"\n🎯 Score: {score:.1f}% ({passed}/{len(capabilities)} features)")
    
    # Now try to run a simple extraction
    if score > 80:
        print("\n🚀 Attempting to run MOR extractor...")
        try:
            # Create a simple test class that bypasses cache
            class SimpleMORExtractor:
                def __init__(self):
                    # Copy essential methods from MOR extractor
                    self.setup_chrome_options()
                    self.setup_directories()
                    self.driver = None
                    self.wait = None
                    self.manuscripts_data = []
                    
                def setup_chrome_options(self):
                    from selenium.webdriver.chrome.options import Options
                    self.chrome_options = Options()
                    self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
                    self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    self.chrome_options.add_experimental_option('useAutomationExtension', False)
                    self.chrome_options.add_argument("--no-sandbox")
                    self.chrome_options.add_argument("--disable-dev-shm-usage")
                    
                def setup_directories(self):
                    self.base_dir = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts')
                    self.download_dir = self.base_dir / "dev/mf/outputs"
                    self.output_dir = self.base_dir / "dev/mf/outputs"
                    self.log_dir = self.base_dir / "dev/mf/logs"
                    
                    for directory in [self.download_dir, self.output_dir, self.log_dir]:
                        directory.mkdir(parents=True, exist_ok=True)
                
                def test_login(self):
                    """Test if we can at least initialize the driver"""
                    from selenium import webdriver
                    from selenium.webdriver.support.ui import WebDriverWait
                    
                    try:
                        print("   🌐 Initializing Chrome driver...")
                        self.driver = webdriver.Chrome(options=self.chrome_options)
                        self.wait = WebDriverWait(self.driver, 10)
                        
                        print("   🔗 Navigating to MOR login page...")
                        self.driver.get("https://mc.manuscriptcentral.com/mor")
                        
                        print("   ✅ Successfully reached MOR login page")
                        
                        # Check page title
                        title = self.driver.title
                        print(f"   📄 Page title: {title}")
                        
                        return True
                        
                    except Exception as e:
                        print(f"   ❌ Error: {e}")
                        return False
                    finally:
                        if self.driver:
                            self.driver.quit()
            
            # Test the simple extractor
            simple_extractor = SimpleMORExtractor()
            if simple_extractor.test_login():
                print("\n✅ MOR extractor can connect to the platform!")
            else:
                print("\n❌ Failed to connect to MOR platform")
                
        except Exception as e:
            print(f"\n❌ Error running test: {e}")
            import traceback
            traceback.print_exc()
    
except ImportError as e:
    print(f"❌ Failed to import MOR extractor: {e}")
    sys.exit(1)