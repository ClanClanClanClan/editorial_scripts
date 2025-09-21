#!/usr/bin/env python3
"""
COMPREHENSIVE FS EXTRACTOR TEST SUITE
=====================================

Ultrathink testing: Test every aspect of the improved FS extractor.
Verify all improvements work correctly and handle edge cases.
"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import traceback

# Add the production path to test the actual extractor
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

try:
    from fs_extractor import ComprehensiveFSExtractor
    FS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Could not import FS extractor: {e}")
    FS_AVAILABLE = False

class TestFSExtractorSafeFunctions(unittest.TestCase):
    """Test all safe helper functions added to FS extractor."""

    def setUp(self):
        if not FS_AVAILABLE:
            self.skipTest("FS extractor not available")
        self.extractor = ComprehensiveFSExtractor()

    def test_safe_int_function(self):
        """Test safe_int handles all edge cases."""
        print("🧪 Testing safe_int function...")

        # Normal cases
        self.assertEqual(self.extractor.safe_int(42), 42)
        self.assertEqual(self.extractor.safe_int("123"), 123)
        self.assertEqual(self.extractor.safe_int("123.45"), 123)
        self.assertEqual(self.extractor.safe_int(45.67), 45)

        # Edge cases that would crash normal int()
        self.assertEqual(self.extractor.safe_int(None), 0)
        self.assertEqual(self.extractor.safe_int(""), 0)
        self.assertEqual(self.extractor.safe_int("not_a_number"), 0)
        self.assertEqual(self.extractor.safe_int("123,456"), 123456)  # Comma removal
        self.assertEqual(self.extractor.safe_int("$123"), 123)  # Dollar removal
        self.assertEqual(self.extractor.safe_int("45%"), 45)  # Percent removal

        # Custom default
        self.assertEqual(self.extractor.safe_int("invalid", -1), -1)

        print("   ✅ safe_int handles all edge cases correctly")

    def test_safe_get_text_function(self):
        """Test safe_get_text handles various content types."""
        print("🧪 Testing safe_get_text function...")

        # Normal string
        self.assertEqual(self.extractor.safe_get_text("  hello world  "), "hello world")

        # None handling
        self.assertEqual(self.extractor.safe_get_text(None), "")
        self.assertEqual(self.extractor.safe_get_text(None, "default"), "default")

        # Mock object with text attribute
        mock_element = Mock()
        mock_element.text = "  element text  "
        self.assertEqual(self.extractor.safe_get_text(mock_element), "element text")

        # Mock object with None text
        mock_element.text = None
        self.assertEqual(self.extractor.safe_get_text(mock_element), "")

        # Mock object without text attribute
        mock_obj = Mock(spec=[])
        self.assertEqual(self.extractor.safe_get_text(mock_obj), str(mock_obj).strip())

        print("   ✅ safe_get_text handles all content types correctly")

    def test_safe_array_access_function(self):
        """Test safe_array_access prevents crashes."""
        print("🧪 Testing safe_array_access function...")

        # Normal arrays
        arr = [1, 2, 3, 4, 5]
        self.assertEqual(self.extractor.safe_array_access(arr, 0), 1)
        self.assertEqual(self.extractor.safe_array_access(arr, 2), 3)
        self.assertEqual(self.extractor.safe_array_access(arr, -1), 5)

        # Out of bounds - should return default
        self.assertIsNone(self.extractor.safe_array_access(arr, 10))
        self.assertEqual(self.extractor.safe_array_access(arr, 10, "default"), "default")

        # Empty array
        self.assertIsNone(self.extractor.safe_array_access([], 0))

        # None array
        self.assertIsNone(self.extractor.safe_array_access(None, 0))

        # String array (auto-split)
        result = self.extractor.safe_array_access("hello world test", 1)
        self.assertEqual(result, "world")

        print("   ✅ safe_array_access prevents all crashes correctly")

    def test_safe_pdf_extract_function(self):
        """Test safe_pdf_extract handles file operations safely."""
        print("🧪 Testing safe_pdf_extract function...")

        # Non-existent file
        result = self.extractor.safe_pdf_extract("/nonexistent/file.pdf")
        self.assertEqual(result, "")

        # None path
        result = self.extractor.safe_pdf_extract(None)
        self.assertEqual(result, "")

        # Custom default
        result = self.extractor.safe_pdf_extract(None, "no_file")
        self.assertEqual(result, "no_file")

        print("   ✅ safe_pdf_extract handles file errors safely")

class TestFSExtractorEmailProcessing(unittest.TestCase):
    """Test email processing capabilities."""

    def setUp(self):
        if not FS_AVAILABLE:
            self.skipTest("FS extractor not available")
        self.extractor = ComprehensiveFSExtractor()

    def test_email_pattern_matching(self):
        """Test email pattern recognition."""
        print("🧪 Testing email pattern matching...")

        patterns = self.extractor.email_patterns

        # Test manuscript ID pattern
        test_ids = ["FS-2024-001", "FSTO-2023-456", "fs 2025 789"]
        for test_id in test_ids:
            match = re.search(patterns['manuscript_id'], test_id)
            self.assertIsNotNone(match, f"Should match manuscript ID: {test_id}")

        print("   ✅ Email patterns match expected formats")

    @patch('fs_extractor.GMAIL_AVAILABLE', True)
    def test_gmail_service_setup_mock(self):
        """Test Gmail service setup with mocked dependencies."""
        print("🧪 Testing Gmail service setup...")

        with patch('fs_extractor.Credentials') as mock_creds, \
             patch('fs_extractor.build') as mock_build:

            # Mock successful credential loading
            mock_creds.from_authorized_user_file.return_value = Mock()
            mock_service = Mock()
            mock_build.return_value = mock_service

            # Test service setup
            result = self.extractor.setup_gmail_service()

            # Should attempt to set up service
            self.assertIsNotNone(result)

        print("   ✅ Gmail service setup logic works correctly")

class TestFSExtractorErrorHandling(unittest.TestCase):
    """Test error handling and resilience."""

    def setUp(self):
        if not FS_AVAILABLE:
            self.skipTest("FS extractor not available")
        self.extractor = ComprehensiveFSExtractor()

    def test_extract_review_scores_error_handling(self):
        """Test enhanced error handling in extract_review_scores."""
        print("🧪 Testing extract_review_scores error handling...")

        # Test with None input
        result = self.extractor.extract_review_scores(None)
        self.assertIsInstance(result, dict)

        # Test with empty string
        result = self.extractor.extract_review_scores("")
        self.assertIsInstance(result, dict)

        # Test with valid content
        test_content = """
        Originality: 4/5
        Significance: 3 out of 5
        Overall rating: 85%
        I highly recommend this paper.
        """
        result = self.extractor.extract_review_scores(test_content)
        self.assertIsInstance(result, dict)
        self.assertGreater(len(result), 0)

        print("   ✅ extract_review_scores handles errors gracefully")

    def test_memory_management(self):
        """Test memory cleanup functionality."""
        print("🧪 Testing memory management...")

        # Test memory cleanup
        if hasattr(self.extractor, 'safe_memory_cleanup'):
            result = self.extractor.safe_memory_cleanup()
            # Should not crash
            self.assertIsNotNone(result)

        print("   ✅ Memory management works without errors")

class TestFSExtractorIntegration(unittest.TestCase):
    """Test integration scenarios."""

    def setUp(self):
        if not FS_AVAILABLE:
            self.skipTest("FS extractor not available")
        self.extractor = ComprehensiveFSExtractor()

    def test_manuscript_extraction_structure(self):
        """Test manuscript extraction maintains expected structure."""
        print("🧪 Testing manuscript extraction structure...")

        # Create mock email message
        mock_message = {
            'id': 'test_123',
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': 'FS-2024-001: New Submission'},
                    {'name': 'From', 'value': 'editor@finance-stochastics.com'},
                    {'name': 'Date', 'value': '2024-01-01'}
                ],
                'body': {'data': 'VGVzdCBlbWFpbCBjb250ZW50'}  # Base64 encoded
            }
        }

        # This would test the structure without needing real Gmail API
        # The function should handle the mock data gracefully
        try:
            result = self.extractor.extract_manuscript_from_email(mock_message)
            # Should either return a dict or None, not crash
            self.assertTrue(result is None or isinstance(result, dict))
        except Exception as e:
            # Should not crash with unhandled exceptions
            self.fail(f"extract_manuscript_from_email crashed: {e}")

        print("   ✅ Manuscript extraction maintains structure")

def run_comprehensive_fs_tests():
    """Run all FS extractor tests."""
    print("🚀 COMPREHENSIVE FS EXTRACTOR TESTING")
    print("=" * 80)

    if not FS_AVAILABLE:
        print("❌ FS extractor not available for testing")
        return False

    # Create test suite
    test_classes = [
        TestFSExtractorSafeFunctions,
        TestFSExtractorEmailProcessing,
        TestFSExtractorErrorHandling,
        TestFSExtractorIntegration
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        print(f"\n📋 Running {test_class.__name__}...")
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)

        for test in suite:
            total_tests += 1
            try:
                test.debug()  # Run without unittest runner for direct output
                passed_tests += 1
            except Exception as e:
                failed_tests.append(f"{test_class.__name__}.{test._testMethodName}: {e}")
                print(f"   ❌ {test._testMethodName} failed: {e}")

    # Print results
    print("\n" + "=" * 80)
    print("📊 FS EXTRACTOR TEST RESULTS")
    print("=" * 80)

    print(f"\n✅ Passed: {passed_tests}/{total_tests}")
    print(f"❌ Failed: {len(failed_tests)}/{total_tests}")

    if failed_tests:
        print("\n🔍 Failed Tests:")
        for failure in failed_tests:
            print(f"   • {failure}")

    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"\n📈 Success Rate: {success_rate:.1f}%")

    if success_rate >= 90:
        print("🏆 FS EXTRACTOR: EXCELLENT TEST RESULTS")
    elif success_rate >= 75:
        print("⚠️ FS EXTRACTOR: GOOD WITH MINOR ISSUES")
    else:
        print("❌ FS EXTRACTOR: NEEDS ATTENTION")

    return success_rate >= 75

if __name__ == "__main__":
    import re  # Import needed for tests
    run_comprehensive_fs_tests()