#!/usr/bin/env python3
"""
Configuration Validation Test Suite

Tests the corrected journals configuration to ensure all 8 journals 
are properly configured with the correct platforms and settings.
"""

import yaml
import unittest
from pathlib import Path
import sys

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from editorial_assistant.core.data_models import JournalConfig


class TestJournalConfiguration(unittest.TestCase):
    """Test the corrected journals configuration."""
    
    def setUp(self):
        """Load configuration file."""
        config_path = Path(__file__).parent / "config" / "corrected_journals.yaml"
        self.assertTrue(config_path.exists(), "Configuration file not found")
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def test_config_structure(self):
        """Test overall configuration structure."""
        # Test top-level keys
        required_keys = ["journals", "platforms", "global"]
        for key in required_keys:
            self.assertIn(key, self.config, f"Missing top-level key: {key}")
    
    def test_all_eight_journals_present(self):
        """Test that all 8 journals are configured."""
        expected_journals = ["MF", "MOR", "FS", "SICON", "SIFIN", "NACO", "JOTA", "MAFE"]
        
        for journal in expected_journals:
            self.assertIn(journal, self.config["journals"], f"Missing journal: {journal}")
    
    def test_journal_platform_assignments(self):
        """Test that journals are assigned to correct platforms."""
        expected_platforms = {
            "MF": "scholarone",
            "MOR": "scholarone", 
            "FS": "email_based",
            "SICON": "siam_orcid",
            "SIFIN": "siam_orcid",
            "NACO": "msp_custom",
            "JOTA": "editorial_manager",
            "MAFE": "editorial_manager_cloud"
        }
        
        for journal, expected_platform in expected_platforms.items():
            actual_platform = self.config["journals"][journal]["platform"]
            self.assertEqual(actual_platform, expected_platform, 
                           f"{journal} should use {expected_platform}, got {actual_platform}")
    
    def test_journal_required_fields(self):
        """Test that each journal has required fields."""
        required_fields = ["name", "platform", "patterns", "credentials", "settings"]
        
        for journal_code, journal_data in self.config["journals"].items():
            for field in required_fields:
                self.assertIn(field, journal_data, 
                            f"Journal {journal_code} missing field: {field}")
    
    def test_journal_urls(self):
        """Test journal URLs are correct."""
        expected_urls = {
            "MF": "https://mc.manuscriptcentral.com/mafi",
            "MOR": "https://mc.manuscriptcentral.com/mathor",
            "FS": None,  # Email-based
            "SICON": "https://mc.manuscriptcentral.com/sicon",
            "SIFIN": "https://mc.manuscriptcentral.com/sifin",
            "NACO": "https://ef.msp.org/login.php",
            "JOTA": "https://www.editorialmanager.com/jota/",
            "MAFE": "https://www2.cloud.editorialmanager.com/mafe/default2.aspx"
        }
        
        for journal, expected_url in expected_urls.items():
            actual_url = self.config["journals"][journal]["url"]
            self.assertEqual(actual_url, expected_url,
                           f"{journal} URL mismatch: expected {expected_url}, got {actual_url}")
    
    def test_manuscript_id_patterns(self):
        """Test manuscript ID patterns are valid regex."""
        import re
        
        # Define expected test IDs for each journal
        expected_ids = {
            "MF": "MAFI-2024-1234",
            "MOR": "MOR-2024-1234", 
            "FS": "FS-2024-1234",
            "SICON": "SICON-2024-1234",
            "SIFIN": "SIFIN-2024-1234",
            "NACO": "NACO-2024-1234",
            "JOTA": "JOTA-2024-1234",
            "MAFE": "MAFE-2024-1234"
        }
        
        for journal_code, journal_data in self.config["journals"].items():
            pattern = journal_data["patterns"]["manuscript_id"]
            
            # Test pattern is valid regex
            try:
                re.compile(pattern)
            except re.error as e:
                self.fail(f"Invalid regex pattern for {journal_code}: {pattern} - {e}")
            
            # Test pattern matches expected format
            if journal_code in expected_ids:
                test_id = expected_ids[journal_code]
                self.assertTrue(re.match(pattern, test_id),
                              f"Pattern {pattern} should match {test_id}")
    
    def test_platform_configurations(self):
        """Test platform-specific configurations."""
        expected_platforms = ["scholarone", "email_based", "siam_orcid", 
                            "editorial_manager", "editorial_manager_cloud", "msp_custom"]
        
        for platform in expected_platforms:
            self.assertIn(platform, self.config["platforms"],
                        f"Missing platform configuration: {platform}")
    
    def test_credentials_configuration(self):
        """Test credential configurations."""
        for journal_code, journal_data in self.config["journals"].items():
            credentials = journal_data["credentials"]
            
            # Each journal should have some form of credentials
            self.assertTrue(len(credentials) > 0,
                          f"Journal {journal_code} has no credentials configured")
            
            # Check for appropriate credential types based on platform
            platform = journal_data["platform"]
            
            if platform == "scholarone":
                self.assertIn("username_env", credentials)
                self.assertIn("password_env", credentials)
            elif platform == "email_based":
                self.assertIn("gmail_service", credentials)
            elif platform == "siam_orcid":
                self.assertIn("username_env", credentials)
                self.assertIn("password_env", credentials)
            elif platform in ["editorial_manager", "editorial_manager_cloud"]:
                self.assertIn("username_env", credentials)
                self.assertIn("password_env", credentials)
            elif platform == "msp_custom":
                self.assertIn("username_env", credentials)
                self.assertIn("password_env", credentials)
    
    def test_settings_validation(self):
        """Test settings are properly configured."""
        for journal_code, journal_data in self.config["journals"].items():
            settings = journal_data["settings"]
            
            # Check for required settings
            required_settings = ["max_manuscripts_per_run", "retry_attempts"]
            for setting in required_settings:
                self.assertIn(setting, settings,
                            f"Journal {journal_code} missing setting: {setting}")
            
            # Validate setting values
            self.assertIsInstance(settings["max_manuscripts_per_run"], int)
            self.assertGreater(settings["max_manuscripts_per_run"], 0)
            self.assertIsInstance(settings["retry_attempts"], int)
            self.assertGreater(settings["retry_attempts"], 0)
    
    def test_journal_config_object_creation(self):
        """Test that JournalConfig objects can be created from configuration."""
        for journal_code, journal_data in self.config["journals"].items():
            try:
                config = JournalConfig(
                    code=journal_code,
                    name=journal_data["name"],
                    platform=journal_data["platform"],
                    url=journal_data.get("url"),
                    categories=journal_data.get("categories", []),
                    patterns=journal_data.get("patterns", {}),
                    credentials=journal_data.get("credentials", {}),
                    settings=journal_data.get("settings", {}),
                    platform_config=self.config["platforms"].get(journal_data["platform"], {})
                )
                
                # Validate created object
                self.assertEqual(config.code, journal_code)
                self.assertEqual(config.name, journal_data["name"])
                self.assertEqual(config.platform, journal_data["platform"])
                
            except Exception as e:
                self.fail(f"Failed to create JournalConfig for {journal_code}: {e}")
    
    def test_email_subjects_for_fs(self):
        """Test FS email subjects are properly configured."""
        fs_config = self.config["journals"]["FS"]
        email_subjects = fs_config["patterns"]["email_subjects"]
        
        self.assertIsInstance(email_subjects, list)
        self.assertGreater(len(email_subjects), 0)
        self.assertIn("Finance and Stochastics", email_subjects)
    
    def test_global_settings(self):
        """Test global settings are reasonable."""
        global_settings = self.config["global"]
        
        # Check for required global settings
        required_globals = ["headless_mode", "screenshot_on_error", "max_concurrent_downloads"]
        for setting in required_globals:
            self.assertIn(setting, global_settings,
                        f"Missing global setting: {setting}")
        
        # Validate values
        self.assertIsInstance(global_settings["headless_mode"], bool)
        self.assertIsInstance(global_settings["screenshot_on_error"], bool)
        self.assertIsInstance(global_settings["max_concurrent_downloads"], int)
        self.assertGreater(global_settings["max_concurrent_downloads"], 0)


def run_config_validation():
    """Run configuration validation tests."""
    print("🔧 Starting Configuration Validation Tests...")
    print("=" * 50)
    
    # Run tests
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestJournalConfiguration)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print("📋 CONFIGURATION VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ CONFIGURATION ISSUES:")
        for test, traceback in result.failures:
            print(f"  - {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 CONFIGURATION ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {traceback.split('Exception:')[-1].strip()}")
    
    if result.wasSuccessful():
        print("\n✅ CONFIGURATION VALID!")
        print("🎯 All 8 journals are properly configured!")
    
    return result


if __name__ == "__main__":
    result = run_config_validation()
    sys.exit(0 if result.wasSuccessful() else 1)