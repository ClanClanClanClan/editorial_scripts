#!/usr/bin/env python3
"""
MANIAC COMPREHENSIVE TEST SUITE
===============================

ULTRATHINK TESTING: Test both MF and MOR extractors to their absolute limits.
Push every system, every function, every edge case to breaking point.
"""

import sys
import os
import json
import time
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

# Test tracking
test_results = {
    'mf': {'passed': 0, 'failed': 0, 'errors': []},
    'mor': {'passed': 0, 'failed': 0, 'errors': []},
    'total': {'passed': 0, 'failed': 0, 'errors': []}
}

def log_test_result(extractor, test_name, success, error=None):
    """Log test results with detailed tracking."""
    if success:
        test_results[extractor]['passed'] += 1
        test_results['total']['passed'] += 1
        print(f"   ✅ {test_name}")
    else:
        test_results[extractor]['failed'] += 1
        test_results['total']['failed'] += 1
        test_results[extractor]['errors'].append(f"{test_name}: {error}")
        print(f"   ❌ {test_name}: {error}")

def test_mf_maniac():
    """Test MF extractor to its absolute limits."""
    print("🔥 MANIAC TESTING MF EXTRACTOR...")

    try:
        from mf_extractor import ComprehensiveMFExtractor
        log_test_result('mf', 'Import MF extractor', True)
    except Exception as e:
        log_test_result('mf', 'Import MF extractor', False, str(e))
        return

    # Test 1: Basic instantiation
    try:
        extractor = ComprehensiveMFExtractor()
        log_test_result('mf', 'Create MF instance', True)
    except Exception as e:
        log_test_result('mf', 'Create MF instance', False, str(e))
        return

    # Test 2: All safe functions with extreme inputs
    try:
        # Test safe_int with every conceivable input
        test_inputs = [None, "", "abc", "123", "123.45", "123,456", "$123", "45%",
                      float('inf'), float('-inf'), float('nan'), [], {}, object()]
        for inp in test_inputs:
            result = extractor.safe_int(inp)
            assert isinstance(result, int), f"safe_int({inp}) returned {type(result)}"
        log_test_result('mf', 'safe_int extreme inputs', True)
    except Exception as e:
        log_test_result('mf', 'safe_int extreme inputs', False, str(e))

    # Test 3: safe_get_text with various objects
    try:
        class MockElement:
            def __init__(self, text):
                self.text = text

        test_objects = [None, "", "  hello  ", MockElement("test"), MockElement(None), object()]
        for obj in test_objects:
            result = extractor.safe_get_text(obj)
            assert isinstance(result, str), f"safe_get_text returned {type(result)}"
        log_test_result('mf', 'safe_get_text various objects', True)
    except Exception as e:
        log_test_result('mf', 'safe_get_text various objects', False, str(e))

    # Test 4: safe_array_access with edge cases
    try:
        arrays = [None, [], [1,2,3], "hello world", range(5)]
        indices = [-10, -1, 0, 1, 10, 100]
        for arr in arrays:
            for idx in indices:
                result = extractor.safe_array_access(arr, idx)
                # Should never crash
        log_test_result('mf', 'safe_array_access edge cases', True)
    except Exception as e:
        log_test_result('mf', 'safe_array_access edge cases', False, str(e))

    # Test 5: Browser navigation (if driver exists)
    try:
        if hasattr(extractor, 'driver') and extractor.driver:
            current_url = extractor.driver.current_url
            log_test_result('mf', 'Browser driver accessible', True)

            # Test navigation to MF
            extractor.driver.get("https://mc.manuscriptcentral.com/mafi")
            time.sleep(2)
            final_url = extractor.driver.current_url
            assert "manuscriptcentral.com" in final_url
            log_test_result('mf', 'Navigate to MF platform', True)

        else:
            log_test_result('mf', 'Browser driver accessible', False, "No driver found")
    except Exception as e:
        log_test_result('mf', 'Navigate to MF platform', False, str(e))

    # Test 6: Credential loading
    try:
        has_email = hasattr(extractor, 'email') and extractor.email
        has_password = hasattr(extractor, 'password') and extractor.password

        if has_email and has_password:
            log_test_result('mf', 'Credentials loaded', True)
        else:
            log_test_result('mf', 'Credentials loaded', False, "Missing email or password")
    except Exception as e:
        log_test_result('mf', 'Credentials loaded', False, str(e))

    # Test 7: Memory management
    try:
        if hasattr(extractor, 'safe_memory_cleanup'):
            result = extractor.safe_memory_cleanup()
            log_test_result('mf', 'Memory cleanup function', True)
        else:
            log_test_result('mf', 'Memory cleanup function', False, "No cleanup method")
    except Exception as e:
        log_test_result('mf', 'Memory cleanup function', False, str(e))

    # Test 8: Cleanup
    try:
        extractor.cleanup()
        log_test_result('mf', 'Extractor cleanup', True)
    except Exception as e:
        log_test_result('mf', 'Extractor cleanup', False, str(e))

def test_mor_maniac():
    """Test MOR extractor to its absolute limits."""
    print("🔥 MANIAC TESTING MOR EXTRACTOR...")

    try:
        from mor_extractor import ComprehensiveMORExtractor
        log_test_result('mor', 'Import MOR extractor', True)
    except Exception as e:
        log_test_result('mor', 'Import MOR extractor', False, str(e))
        return

    # Test 1: Basic instantiation
    try:
        extractor = ComprehensiveMORExtractor()
        log_test_result('mor', 'Create MOR instance', True)
    except Exception as e:
        log_test_result('mor', 'Create MOR instance', False, str(e))
        return

    # Test 2: All safe functions with extreme inputs
    try:
        # Test safe_int with every conceivable input
        test_inputs = [None, "", "abc", "123", "123.45", "123,456", "$123", "45%",
                      float('inf'), float('-inf'), float('nan'), [], {}, object()]
        for inp in test_inputs:
            result = extractor.safe_int(inp)
            assert isinstance(result, int), f"safe_int({inp}) returned {type(result)}"
        log_test_result('mor', 'safe_int extreme inputs', True)
    except Exception as e:
        log_test_result('mor', 'safe_int extreme inputs', False, str(e))

    # Test 3: safe_get_text with various objects
    try:
        class MockElement:
            def __init__(self, text):
                self.text = text

        test_objects = [None, "", "  hello  ", MockElement("test"), MockElement(None), object()]
        for obj in test_objects:
            result = extractor.safe_get_text(obj)
            assert isinstance(result, str), f"safe_get_text returned {type(result)}"
        log_test_result('mor', 'safe_get_text various objects', True)
    except Exception as e:
        log_test_result('mor', 'safe_get_text various objects', False, str(e))

    # Test 4: safe_click with mock elements
    try:
        class MockClickElement:
            def click(self):
                pass

        class MockBadElement:
            def click(self):
                raise Exception("Click failed")

        # Test successful click
        result1 = extractor.safe_click(MockClickElement())
        assert result1 == True

        # Test failed click
        result2 = extractor.safe_click(MockBadElement())
        # Should handle gracefully

        # Test None element
        result3 = extractor.safe_click(None)
        assert result3 == False

        log_test_result('mor', 'safe_click with mock elements', True)
    except Exception as e:
        log_test_result('mor', 'safe_click with mock elements', False, str(e))

    # Test 5: Browser navigation (if driver exists)
    try:
        if hasattr(extractor, 'driver') and extractor.driver:
            current_url = extractor.driver.current_url
            log_test_result('mor', 'Browser driver accessible', True)

            # Test navigation to MOR
            extractor.driver.get("https://mc.manuscriptcentral.com/mathor")
            time.sleep(2)
            final_url = extractor.driver.current_url
            assert "manuscriptcentral.com" in final_url
            log_test_result('mor', 'Navigate to MOR platform', True)

        else:
            log_test_result('mor', 'Browser driver accessible', False, "No driver found")
    except Exception as e:
        log_test_result('mor', 'Navigate to MOR platform', False, str(e))

    # Test 6: WebDriver safe functions
    try:
        if hasattr(extractor, 'driver') and extractor.driver:
            # Test safe_find_element
            result = extractor.safe_find_element("tag name", "body")
            # Should not crash
            log_test_result('mor', 'safe_find_element function', True)
        else:
            log_test_result('mor', 'safe_find_element function', False, "No driver")
    except Exception as e:
        log_test_result('mor', 'safe_find_element function', False, str(e))

    # Test 7: smart_wait function
    try:
        start_time = time.time()
        extractor.smart_wait(1)
        end_time = time.time()
        duration = end_time - start_time
        # Should wait approximately 1 second
        assert 0.5 <= duration <= 2.0, f"Wait duration was {duration}"
        log_test_result('mor', 'smart_wait timing', True)
    except Exception as e:
        log_test_result('mor', 'smart_wait timing', False, str(e))

    # Test 8: Cleanup
    try:
        extractor.cleanup()
        log_test_result('mor', 'Extractor cleanup', True)
    except Exception as e:
        log_test_result('mor', 'Extractor cleanup', False, str(e))

def test_concurrent_stress():
    """Test both extractors under concurrent stress."""
    print("🔥 CONCURRENT STRESS TESTING...")

    def stress_safe_functions(extractor_name):
        """Stress test safe functions."""
        results = []
        try:
            if extractor_name == 'mf':
                from mf_extractor import ComprehensiveMFExtractor
                ext = ComprehensiveMFExtractor()
            else:
                from mor_extractor import ComprehensiveMORExtractor
                ext = ComprehensiveMORExtractor()

            # Hammer safe functions with rapid calls
            for i in range(100):
                ext.safe_int(f"test{i}")
                ext.safe_get_text(f"text{i}")
                ext.safe_array_access([1,2,3], i % 4)

            ext.cleanup()
            results.append(f"{extractor_name} stress test passed")
            return True

        except Exception as e:
            results.append(f"{extractor_name} stress test failed: {e}")
            return False

    # Run concurrent tests
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(stress_safe_functions, 'mf'),
                executor.submit(stress_safe_functions, 'mor'),
                executor.submit(stress_safe_functions, 'mf'),
                executor.submit(stress_safe_functions, 'mor')
            ]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

            all_passed = all(results)
            log_test_result('total', 'Concurrent stress test', all_passed,
                          "Some concurrent tests failed" if not all_passed else None)

    except Exception as e:
        log_test_result('total', 'Concurrent stress test', False, str(e))

def print_final_results():
    """Print comprehensive test results."""
    print("\n" + "=" * 80)
    print("🏆 MANIAC COMPREHENSIVE TEST RESULTS")
    print("=" * 80)

    print(f"\n📊 MF EXTRACTOR:")
    print(f"   ✅ Passed: {test_results['mf']['passed']}")
    print(f"   ❌ Failed: {test_results['mf']['failed']}")

    if test_results['mf']['errors']:
        print(f"   🔍 MF Errors:")
        for error in test_results['mf']['errors']:
            print(f"      • {error}")

    print(f"\n📊 MOR EXTRACTOR:")
    print(f"   ✅ Passed: {test_results['mor']['passed']}")
    print(f"   ❌ Failed: {test_results['mor']['failed']}")

    if test_results['mor']['errors']:
        print(f"   🔍 MOR Errors:")
        for error in test_results['mor']['errors']:
            print(f"      • {error}")

    total_tests = test_results['total']['passed'] + test_results['total']['failed']
    success_rate = (test_results['total']['passed'] / total_tests * 100) if total_tests > 0 else 0

    print(f"\n📈 OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   ✅ Passed: {test_results['total']['passed']}")
    print(f"   ❌ Failed: {test_results['total']['failed']}")
    print(f"   📊 Success Rate: {success_rate:.1f}%")

    if success_rate >= 90:
        print("🏆 EXCELLENT: Both extractors are in excellent condition!")
    elif success_rate >= 75:
        print("⚠️ GOOD: Extractors are functional with minor issues")
    elif success_rate >= 50:
        print("🔧 NEEDS WORK: Extractors have significant issues")
    else:
        print("❌ CRITICAL: Extractors need major repairs")

    print("\n🔥 MANIAC TESTING COMPLETE!")

def run_maniac_tests():
    """Run all maniac tests."""
    print("🚀 STARTING MANIAC COMPREHENSIVE TESTING")
    print("=" * 80)
    print("🔥 ULTRATHINK MODE: Testing both MF and MOR to absolute limits")
    print("⚡ Pushing every system, function, and edge case to breaking point")
    print("=" * 80)

    # Sequential testing for better visibility
    test_mf_maniac()
    print()
    test_mor_maniac()
    print()
    test_concurrent_stress()

    print_final_results()

if __name__ == "__main__":
    run_maniac_tests()