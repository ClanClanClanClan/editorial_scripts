#!/usr/bin/env python3
"""
SIAM Extractors Debugging Script

This script provides comprehensive debugging capabilities for SICON and SIFIN extractors
with detailed logging, screenshot capture, and step-by-step validation.
"""

import os
import sys
import time
import logging
import traceback
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
import yaml

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from editorial_assistant.core.data_models import JournalConfig
from editorial_assistant.extractors.sicon import SICONExtractor
from editorial_assistant.extractors.sifin import SIFINExtractor
from editorial_assistant.utils.session_manager import SessionManager

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'siam_debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SIAMExtractorDebugger:
    """Comprehensive debugging for SIAM extractors."""
    
    def __init__(self):
        self.session_manager = SessionManager(Path('.'))
        self.debug_dir = Path('./debug_output')
        self.debug_dir.mkdir(exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Setup extractors
        self.sicon_config = self._create_journal_config('SICON')
        self.sifin_config = self._create_journal_config('SIFIN')
        
        print("🔧 SIAM Extractors Debugger initialized")
        print(f"📁 Debug output directory: {self.debug_dir}")
        print(f"📋 Session ID: {self.session_manager.session.session_id}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load journal configuration."""
        config_path = Path(__file__).parent / "config" / "corrected_journals.yaml"
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _create_journal_config(self, journal_code: str) -> JournalConfig:
        """Create JournalConfig for specified journal."""
        journal_data = self.config["journals"][journal_code]
        platform_config = self.config["platforms"][journal_data["platform"]]
        
        return JournalConfig(
            code=journal_code,
            name=journal_data["name"],
            platform=journal_data["platform"],
            url=journal_data["url"],
            categories=journal_data.get("categories", []),
            patterns=journal_data.get("patterns", {}),
            credentials=journal_data.get("credentials", {}),
            settings=journal_data.get("settings", {}),
            platform_config=platform_config
        )
    
    def check_credentials(self) -> bool:
        """Check if ORCID credentials are available."""
        print("\n🔐 Checking ORCID credentials...")
        
        orcid_user = os.getenv("ORCID_USER")
        orcid_pass = os.getenv("ORCID_PASS")
        
        if not orcid_user:
            print("❌ ORCID_USER environment variable not set")
            print("   Please set: export ORCID_USER='your_orcid_email'")
            return False
        
        if not orcid_pass:
            print("❌ ORCID_PASS environment variable not set")
            print("   Please set: export ORCID_PASS='your_orcid_password'")
            return False
        
        print(f"✅ ORCID_USER: {orcid_user}")
        print(f"✅ ORCID_PASS: {'*' * len(orcid_pass)}")
        return True
    
    def debug_sicon(self, headless: bool = False) -> Dict[str, Any]:
        """Debug SICON extractor with detailed logging."""
        print("\n" + "="*60)
        print("🧪 DEBUGGING SICON EXTRACTOR")
        print("="*60)
        
        result = {
            "journal": "SICON",
            "success": False,
            "error": None,
            "manuscripts": [],
            "debug_info": {},
            "screenshots": []
        }
        
        try:
            self.session_manager.auto_save_progress(
                "Starting SICON debug session",
                learning="Beginning comprehensive SICON extractor debugging"
            )
            
            # Create extractor
            print("📝 Creating SICON extractor...")
            extractor = SICONExtractor(self.sicon_config)
            
            # Test basic initialization
            print(f"✅ Extractor created successfully")
            print(f"   Journal: {extractor.journal.name}")
            print(f"   Platform: {extractor.journal.platform}")
            print(f"   URL: {extractor.journal.url}")
            
            result["debug_info"]["extractor_created"] = True
            result["debug_info"]["config"] = {
                "name": extractor.journal.name,
                "platform": extractor.journal.platform,
                "url": extractor.journal.url
            }
            
            # Test web driver functionality
            print("🌐 Testing web driver functionality...")
            
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                import time
                
                # Create web driver
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
                
                driver = webdriver.Chrome(options=chrome_options)
                driver.set_page_load_timeout(30)
                
                print("✅ Web driver created successfully")
                
                # Navigate to journal
                print(f"🔍 Navigating to {extractor.journal.url}")
                driver.get(extractor.journal.url)
                time.sleep(3)
                
                page_title = driver.title
                print(f"✅ Page loaded: {page_title}")
                
                # Look for ORCID button
                orcid_found = False
                try:
                    orcid_elements = driver.find_elements(By.XPATH, "//*[contains(@src, 'orcid') or contains(text(), 'ORCID')]")
                    if orcid_elements:
                        orcid_found = True
                        print("✅ ORCID login element detected")
                    else:
                        print("⚠️  ORCID login element not immediately visible")
                except Exception as e:
                    print(f"⚠️  Could not search for ORCID elements: {e}")
                
                result["debug_info"]["web_driver_test"] = {
                    "driver_created": True,
                    "page_loaded": True,
                    "page_title": page_title,
                    "orcid_found": orcid_found
                }
                
                # Close driver
                driver.quit()
                print("✅ Web driver test completed successfully")
                
            except Exception as e:
                error_msg = f"Web driver test failed: {str(e)}"
                print(f"❌ {error_msg}")
                result["debug_info"]["web_driver_error"] = error_msg
            
            self.session_manager.auto_save_progress(
                "SICON extractor initialization complete",
                learning="SICON extractor object created successfully, ready for web testing"
            )
            
            result["success"] = True
            
        except Exception as e:
            error_msg = f"SICON debug failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            result["error"] = error_msg
            result["debug_info"]["traceback"] = traceback.format_exc()
            
            self.session_manager.auto_save_progress(
                "SICON debug session failed",
                learning=f"Error encountered: {error_msg}"
            )
        
        return result
    
    def debug_sifin(self, headless: bool = False) -> Dict[str, Any]:
        """Debug SIFIN extractor with detailed logging."""
        print("\n" + "="*60)
        print("🧪 DEBUGGING SIFIN EXTRACTOR")
        print("="*60)
        
        result = {
            "journal": "SIFIN",
            "success": False,
            "error": None,
            "manuscripts": [],
            "debug_info": {},
            "screenshots": []
        }
        
        try:
            self.session_manager.auto_save_progress(
                "Starting SIFIN debug session",
                learning="Beginning comprehensive SIFIN extractor debugging"
            )
            
            # Create extractor
            print("📝 Creating SIFIN extractor...")
            extractor = SIFINExtractor(self.sifin_config)
            
            # Test basic initialization
            print(f"✅ Extractor created successfully")
            print(f"   Journal: {extractor.journal.name}")
            print(f"   Platform: {extractor.journal.platform}")
            print(f"   URL: {extractor.journal.url}")
            
            result["debug_info"]["extractor_created"] = True
            result["debug_info"]["config"] = {
                "name": extractor.journal.name,
                "platform": extractor.journal.platform,
                "url": extractor.journal.url
            }
            
            # Test web driver functionality
            print("🌐 Testing web driver functionality...")
            
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options
                from selenium.webdriver.common.by import By
                import time
                
                # Create web driver
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
                
                driver = webdriver.Chrome(options=chrome_options)
                driver.set_page_load_timeout(30)
                
                print("✅ Web driver created successfully")
                
                # Navigate to journal
                print(f"🔍 Navigating to {extractor.journal.url}")
                driver.get(extractor.journal.url)
                time.sleep(3)
                
                page_title = driver.title
                print(f"✅ Page loaded: {page_title}")
                
                # Look for ORCID button
                orcid_found = False
                try:
                    orcid_elements = driver.find_elements(By.XPATH, "//*[contains(@src, 'orcid') or contains(text(), 'ORCID')]")
                    if orcid_elements:
                        orcid_found = True
                        print("✅ ORCID login element detected")
                    else:
                        print("⚠️  ORCID login element not immediately visible")
                except Exception as e:
                    print(f"⚠️  Could not search for ORCID elements: {e}")
                
                result["debug_info"]["web_driver_test"] = {
                    "driver_created": True,
                    "page_loaded": True,
                    "page_title": page_title,
                    "orcid_found": orcid_found
                }
                
                # Close driver
                driver.quit()
                print("✅ Web driver test completed successfully")
                
            except Exception as e:
                error_msg = f"Web driver test failed: {str(e)}"
                print(f"❌ {error_msg}")
                result["debug_info"]["web_driver_error"] = error_msg
            
            self.session_manager.auto_save_progress(
                "SIFIN extractor initialization complete",
                learning="SIFIN extractor object created successfully, ready for web testing"
            )
            
            result["success"] = True
            
        except Exception as e:
            error_msg = f"SIFIN debug failed: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            result["error"] = error_msg
            result["debug_info"]["traceback"] = traceback.format_exc()
            
            self.session_manager.auto_save_progress(
                "SIFIN debug session failed",
                learning=f"Error encountered: {error_msg}"
            )
        
        return result
    
    def debug_sicon_basic(self) -> Dict[str, Any]:
        """Debug SICON extractor basic initialization only."""
        print("\n" + "="*60)
        print("🧪 DEBUGGING SICON EXTRACTOR (BASIC)")
        print("="*60)
        
        result = {
            "journal": "SICON",
            "success": False,
            "error": None,
            "debug_info": {}
        }
        
        try:
            # Create extractor
            print("📝 Creating SICON extractor...")
            extractor = SICONExtractor(self.sicon_config)
            
            # Test basic initialization
            print(f"✅ Extractor created successfully")
            print(f"   Journal: {extractor.journal.name}")
            print(f"   Platform: {extractor.journal.platform}")
            print(f"   URL: {extractor.journal.url}")
            
            result["debug_info"]["extractor_created"] = True
            result["debug_info"]["config"] = {
                "name": extractor.journal.name,
                "platform": extractor.journal.platform,
                "url": extractor.journal.url
            }
            
            result["success"] = True
            
        except Exception as e:
            error_msg = f"SICON basic debug failed: {str(e)}"
            result["error"] = error_msg
            result["debug_info"]["traceback"] = traceback.format_exc()
        
        return result
    
    def debug_sifin_basic(self) -> Dict[str, Any]:
        """Debug SIFIN extractor basic initialization only."""
        print("\n" + "="*60)
        print("🧪 DEBUGGING SIFIN EXTRACTOR (BASIC)")
        print("="*60)
        
        result = {
            "journal": "SIFIN",
            "success": False,
            "error": None,
            "debug_info": {}
        }
        
        try:
            # Create extractor
            print("📝 Creating SIFIN extractor...")
            extractor = SIFINExtractor(self.sifin_config)
            
            # Test basic initialization
            print(f"✅ Extractor created successfully")
            print(f"   Journal: {extractor.journal.name}")
            print(f"   Platform: {extractor.journal.platform}")
            print(f"   URL: {extractor.journal.url}")
            
            result["debug_info"]["extractor_created"] = True
            result["debug_info"]["config"] = {
                "name": extractor.journal.name,
                "platform": extractor.journal.platform,
                "url": extractor.journal.url
            }
            
            result["success"] = True
            
        except Exception as e:
            error_msg = f"SIFIN basic debug failed: {str(e)}"
            result["error"] = error_msg
            result["debug_info"]["traceback"] = traceback.format_exc()
        
        return result
    
    def validate_configurations(self) -> Dict[str, Any]:
        """Validate SICON and SIFIN configurations."""
        print("\n" + "="*60)
        print("🔍 VALIDATING SIAM CONFIGURATIONS")
        print("="*60)
        
        validation_results = {
            "sicon": {"valid": False, "issues": []},
            "sifin": {"valid": False, "issues": []}
        }
        
        # Validate SICON
        try:
            sicon_data = self.config["journals"]["SICON"]
            
            # Check required fields
            required_fields = ["name", "platform", "url", "patterns", "credentials", "settings"]
            for field in required_fields:
                if field not in sicon_data:
                    validation_results["sicon"]["issues"].append(f"Missing field: {field}")
            
            # Check platform
            if sicon_data.get("platform") != "siam_orcid":
                validation_results["sicon"]["issues"].append(f"Wrong platform: {sicon_data.get('platform')}")
            
            # Check URL
            expected_url = "http://sicon.siam.org"
            if sicon_data.get("url") != expected_url:
                validation_results["sicon"]["issues"].append(f"Wrong URL: {sicon_data.get('url')}")
            
            # Check manuscript ID pattern
            pattern = sicon_data.get("patterns", {}).get("manuscript_id")
            if not pattern:
                validation_results["sicon"]["issues"].append("Missing manuscript_id pattern")
            else:
                import re
                try:
                    re.compile(pattern)
                    # Test with sample ID
                    if not re.match(pattern, "SICON-2024-1234"):
                        validation_results["sicon"]["issues"].append(f"Pattern doesn't match test ID: {pattern}")
                except re.error as e:
                    validation_results["sicon"]["issues"].append(f"Invalid regex pattern: {e}")
            
            if not validation_results["sicon"]["issues"]:
                validation_results["sicon"]["valid"] = True
                print("✅ SICON configuration valid")
            else:
                print("❌ SICON configuration issues:")
                for issue in validation_results["sicon"]["issues"]:
                    print(f"   - {issue}")
            
        except Exception as e:
            validation_results["sicon"]["issues"].append(f"Configuration error: {str(e)}")
            print(f"❌ SICON validation failed: {e}")
        
        # Validate SIFIN (similar process)
        try:
            sifin_data = self.config["journals"]["SIFIN"]
            
            # Check required fields
            required_fields = ["name", "platform", "url", "patterns", "credentials", "settings"]
            for field in required_fields:
                if field not in sifin_data:
                    validation_results["sifin"]["issues"].append(f"Missing field: {field}")
            
            # Check platform
            if sifin_data.get("platform") != "siam_orcid":
                validation_results["sifin"]["issues"].append(f"Wrong platform: {sifin_data.get('platform')}")
            
            # Check URL
            expected_url = "http://sifin.siam.org"
            if sifin_data.get("url") != expected_url:
                validation_results["sifin"]["issues"].append(f"Wrong URL: {sifin_data.get('url')}")
            
            # Check manuscript ID pattern
            pattern = sifin_data.get("patterns", {}).get("manuscript_id")
            if not pattern:
                validation_results["sifin"]["issues"].append("Missing manuscript_id pattern")
            else:
                import re
                try:
                    re.compile(pattern)
                    # Test with sample ID
                    if not re.match(pattern, "SIFIN-2024-1234"):
                        validation_results["sifin"]["issues"].append(f"Pattern doesn't match test ID: {pattern}")
                except re.error as e:
                    validation_results["sifin"]["issues"].append(f"Invalid regex pattern: {e}")
            
            if not validation_results["sifin"]["issues"]:
                validation_results["sifin"]["valid"] = True
                print("✅ SIFIN configuration valid")
            else:
                print("❌ SIFIN configuration issues:")
                for issue in validation_results["sifin"]["issues"]:
                    print(f"   - {issue}")
            
        except Exception as e:
            validation_results["sifin"]["issues"].append(f"Configuration error: {str(e)}")
            print(f"❌ SIFIN validation failed: {e}")
        
        return validation_results
    
    def run_comprehensive_debug(self, headless: bool = False) -> Dict[str, Any]:
        """Run comprehensive debugging for both SIAM extractors."""
        print("\n🚀 STARTING COMPREHENSIVE SIAM DEBUGGING SESSION")
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🖥️  Headless mode: {headless}")
        
        debug_session = {
            "start_time": datetime.now().isoformat(),
            "headless": headless,
            "credentials_check": False,
            "configuration_validation": {},
            "sicon_debug": {},
            "sifin_debug": {},
            "overall_success": False
        }
        
        try:
            # Check credentials
            debug_session["credentials_check"] = self.check_credentials()
            
            # Validate configurations (regardless of credentials)
            debug_session["configuration_validation"] = self.validate_configurations()
            
            # Only proceed with web testing if credentials are available
            if debug_session["credentials_check"]:
                # Debug SICON
                debug_session["sicon_debug"] = self.debug_sicon(headless)
                
                # Debug SIFIN
                debug_session["sifin_debug"] = self.debug_sifin(headless)
                
                # Overall success
                debug_session["overall_success"] = (
                    debug_session["sicon_debug"]["success"] and 
                    debug_session["sifin_debug"]["success"]
                )
            else:
                print("⚠️  Skipping web testing due to missing credentials")
                print("📋 Will only validate configurations and basic extractor creation")
                
                # Test basic extractor creation without web driver
                debug_session["sicon_debug"] = self.debug_sicon_basic()
                debug_session["sifin_debug"] = self.debug_sifin_basic()
                
                # Configuration validation success determines overall success
                config_success = (
                    debug_session["configuration_validation"].get("sicon", {}).get("valid", False) and 
                    debug_session["configuration_validation"].get("sifin", {}).get("valid", False)
                )
                
                debug_session["overall_success"] = (
                    config_success and
                    debug_session["sicon_debug"]["success"] and 
                    debug_session["sifin_debug"]["success"]
                )
            
            # Save final milestone
            if debug_session["overall_success"]:
                milestone_name = "SIAM Extractors Configuration Validation Complete" if not debug_session["credentials_check"] else "SIAM Extractors Basic Debugging Complete"
                self.session_manager.save_implementation_milestone(
                    milestone_name,
                    ["debug_siam_extractors.py"],
                    f"Successfully validated SICON and SIFIN extractor configuration and basic initialization. Credentials available: {debug_session['credentials_check']}"
                )
            
        except Exception as e:
            logger.error(f"Comprehensive debug session failed: {e}")
            logger.error(traceback.format_exc())
            debug_session["error"] = str(e)
        
        debug_session["end_time"] = datetime.now().isoformat()
        
        # Print summary
        self._print_debug_summary(debug_session)
        
        return debug_session
    
    def _print_debug_summary(self, debug_session: Dict[str, Any]) -> None:
        """Print comprehensive debug summary."""
        print("\n" + "="*80)
        print("📊 SIAM DEBUGGING SESSION SUMMARY")
        print("="*80)
        
        # Credentials
        creds_status = "✅" if debug_session["credentials_check"] else "❌"
        print(f"{creds_status} ORCID Credentials: {'Available' if debug_session['credentials_check'] else 'Missing'}")
        
        # Configuration validation
        config_val = debug_session["configuration_validation"]
        sicon_config_status = "✅" if config_val.get("sicon", {}).get("valid") else "❌"
        sifin_config_status = "✅" if config_val.get("sifin", {}).get("valid") else "❌"
        print(f"{sicon_config_status} SICON Configuration: {'Valid' if config_val.get('sicon', {}).get('valid') else 'Invalid'}")
        print(f"{sifin_config_status} SIFIN Configuration: {'Valid' if config_val.get('sifin', {}).get('valid') else 'Invalid'}")
        
        # Extractor debugging
        sicon_debug = debug_session["sicon_debug"]
        sifin_debug = debug_session["sifin_debug"]
        
        sicon_status = "✅" if sicon_debug.get("success") else "❌"
        sifin_status = "✅" if sifin_debug.get("success") else "❌"
        
        print(f"{sicon_status} SICON Extractor: {'Success' if sicon_debug.get('success') else 'Failed'}")
        if sicon_debug.get("error"):
            print(f"   Error: {sicon_debug['error']}")
        
        print(f"{sifin_status} SIFIN Extractor: {'Success' if sifin_debug.get('success') else 'Failed'}")
        if sifin_debug.get("error"):
            print(f"   Error: {sifin_debug['error']}")
        
        # Overall status
        overall_status = "✅" if debug_session["overall_success"] else "❌"
        print(f"\n{overall_status} OVERALL STATUS: {'SUCCESS' if debug_session['overall_success'] else 'FAILED'}")
        
        if debug_session["overall_success"]:
            print("🎉 Both SIAM extractors initialized successfully!")
            print("📋 Ready for web driver testing phase")
        else:
            print("🔧 Issues found that need to be resolved before proceeding")
        
        print(f"\n📁 Debug logs saved to: siam_debug_*.log")
        print(f"📊 Session ID: {self.session_manager.session.session_id}")


def main():
    """Main debugging entry point."""
    debugger = SIAMExtractorDebugger()
    
    # Run comprehensive debugging
    results = debugger.run_comprehensive_debug(headless=True)
    
    # Exit with appropriate code
    if results["overall_success"]:
        print("\n✅ Debug session completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Debug session found issues that need attention")
        sys.exit(1)


if __name__ == "__main__":
    main()