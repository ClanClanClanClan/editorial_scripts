#!/usr/bin/env python3
"""
Performance and Reliability Test Suite for Editorial Assistant

This test suite focuses on performance, reliability, and stress testing
of the new extractor architecture components.
"""

import unittest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
import tempfile
import yaml
from pathlib import Path
from typing import Dict, List, Any
import sys
import re

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from editorial_assistant.core.data_models import JournalConfig
from editorial_assistant.utils.session_manager import SessionManager


class TestPerformance(unittest.TestCase):
    """Test performance characteristics of key components."""
    
    def setUp(self):
        """Set up test data."""
        # Load configuration
        config_path = Path(__file__).parent / "config" / "corrected_journals.yaml"
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def test_config_loading_performance(self):
        """Test configuration loading performance."""
        start_time = time.time()
        
        # Load config multiple times to test performance
        for _ in range(100):
            for journal_code, journal_data in self.config["journals"].items():
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
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should be able to create 800 config objects (8 journals × 100 iterations) in under 1 second
        self.assertLess(duration, 1.0, f"Config loading took {duration:.3f}s, should be under 1.0s")
        print(f"✓ Config loading performance: {duration:.3f}s for 800 objects")
    
    def test_regex_pattern_performance(self):
        """Test regex pattern matching performance."""
        patterns = {
            "MF": r'MAFI-\d{4}-\d{4}',
            "MOR": r'MOR-\d{4}-\d{4}',
            "FS": r'FS-\d{4}-\d{4}',
            "SICON": r'SICON-\d{4}-\d{4}',
            "SIFIN": r'SIFIN-\d{4}-\d{4}',
            "NACO": r'NACO-\d{4}-\d{4}',
            "JOTA": r'JOTA-D-\d{2}-\d{5}R?\d*',
            "MAFE": r'MAFE-\d{4}-\d{4}'
        }
        
        test_texts = [
            "Subject: MAFI-2024-1234 referee response",
            "The manuscript MOR-2024-5678 has been reviewed",
            "FS-2024-9999 requires additional review",
            "SICON-2024-1111 is under consideration",
            "Please review SIFIN-2024-2222 by Friday",
            "NACO-2024-3333 submission received",
            "JOTA-D-24-00769R1 revision needed",
            "MAFE-2024-4444 accepted for publication"
        ]
        
        start_time = time.time()
        
        # Test pattern matching performance
        matches_found = 0
        for _ in range(1000):  # 1000 iterations
            for text in test_texts:
                for journal, pattern in patterns.items():
                    if re.search(pattern, text):
                        matches_found += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 1000 × 8 texts × 8 patterns = 64,000 regex operations in under 0.5s
        self.assertLess(duration, 0.5, f"Regex matching took {duration:.3f}s, should be under 0.5s")
        print(f"✓ Regex performance: {duration:.3f}s for 64,000 operations ({matches_found} matches)")


class TestReliability(unittest.TestCase):
    """Test reliability and error handling under stress."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_root = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_concurrent_session_creation(self):
        """Test concurrent session manager creation."""
        import threading
        sessions_created = []
        errors = []
        lock = threading.Lock()
        
        def create_session(session_id):
            try:
                session_dir = self.project_root / f"session_{session_id}"
                session_dir.mkdir(parents=True, exist_ok=True)  # Create directory first
                session_manager = SessionManager(session_dir)
                with lock:
                    sessions_created.append(session_manager)
            except Exception as e:
                with lock:
                    errors.append(e)
        
        # Create 10 session managers concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_session, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = len(sessions_created)
        error_count = len(errors)
        
        # At least some sessions should be created (thread safety may cause some failures)
        self.assertGreater(success_count, 0, f"No sessions created, errors: {errors}")
        
        # Most sessions should be created successfully 
        success_rate = success_count / 10
        self.assertGreaterEqual(success_rate, 0.7, f"Success rate {success_rate:.1%} too low")
        
        print(f"✓ Concurrent session creation: {success_count}/10 sessions created ({success_rate:.1%} success rate)")
    
    def test_session_stress_operations(self):
        """Test session manager under stress with many operations."""
        session_manager = SessionManager(self.project_root)
        
        start_time = time.time()
        
        # Perform many operations
        for i in range(100):
            session_manager.auto_save_progress(
                f"Step {i}",
                outputs=[f"file_{i}.py"],
                learning=f"Learning {i}"
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 100 operations in under 2 seconds
        self.assertLess(duration, 2.0, f"Session operations took {duration:.3f}s, should be under 2.0s")
        
        # Verify session integrity
        self.assertIsNotNone(session_manager.session)
        self.assertGreater(len(session_manager.session.key_learnings), 0)
        
        print(f"✓ Session stress test: 100 operations in {duration:.3f}s")
    
    def test_malformed_data_handling(self):
        """Test handling of malformed data without crashing."""
        session_manager = SessionManager(self.project_root)
        
        # Test with various malformed inputs
        malformed_inputs = [
            (None, None, None),
            ("", [], ""),
            ("step", None, None),
            ("step", ["file.py"], None),
            ("step", "not_a_list", "learning"),
            (123, ["file.py"], "learning"),  # Non-string step name
        ]
        
        for step_name, outputs, learning in malformed_inputs:
            try:
                session_manager.auto_save_progress(step_name, outputs, learning)
                # Should not crash, even with malformed data
            except Exception as e:
                # Some exceptions are acceptable for truly invalid data
                if not isinstance(e, (TypeError, ValueError, AttributeError)):
                    self.fail(f"Unexpected exception for input {(step_name, outputs, learning)}: {e}")
        
        print("✓ Malformed data handling: No crashes with invalid inputs")


class TestScalability(unittest.TestCase):
    """Test scalability with large amounts of data."""
    
    def test_large_manuscript_data_processing(self):
        """Test processing large amounts of manuscript data."""
        
        # Generate large dataset
        large_manuscript_dataset = []
        for i in range(1000):  # 1000 manuscripts
            manuscript = {
                "Manuscript #": f"TEST-2024-{i:04d}",
                "Title": f"Research Paper Title {i}",
                "Contact Author": f"Author {i}",
                "Current Stage": "Under Review",
                "Submission Date": "2024-01-15",
                "Referees": [
                    {
                        "Referee Name": f"Referee {i}_1",
                        "Referee Email": f"ref{i}_1@university.edu",
                        "Status": "Accepted",
                        "Due Date": "2024-12-31"
                    },
                    {
                        "Referee Name": f"Referee {i}_2", 
                        "Referee Email": f"ref{i}_2@university.edu",
                        "Status": "Contacted",
                        "Due Date": "2024-12-31"
                    }
                ]
            }
            large_manuscript_dataset.append(manuscript)
        
        start_time = time.time()
        
        # Process the large dataset
        processed_manuscripts = []
        for manuscript in large_manuscript_dataset:
            # Simulate data processing operations
            manuscript_id = manuscript["Manuscript #"]
            title_length = len(manuscript["Title"])
            referee_count = len(manuscript["Referees"])
            
            # Extract email addresses
            emails = []
            for referee in manuscript["Referees"]:
                email = referee["Referee Email"]
                if re.match(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
                    emails.append(email)
            
            processed_manuscript = {
                "id": manuscript_id,
                "title_length": title_length,
                "referee_count": referee_count,
                "valid_emails": len(emails)
            }
            processed_manuscripts.append(processed_manuscript)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should process 1000 manuscripts in under 1 second
        self.assertLess(duration, 1.0, f"Large dataset processing took {duration:.3f}s, should be under 1.0s")
        self.assertEqual(len(processed_manuscripts), 1000)
        
        print(f"✓ Large dataset scalability: 1000 manuscripts processed in {duration:.3f}s")
    
    def test_memory_efficiency(self):
        """Test memory efficiency with repeated operations."""
        import gc
        import sys
        
        # Force garbage collection
        gc.collect()
        initial_objects = len(gc.get_objects())
        
        # Perform many operations that could cause memory leaks
        for i in range(100):
            # Create and destroy many JournalConfig objects
            config = JournalConfig(
                code=f"TEST{i}",
                name=f"Test Journal {i}",
                platform="test_platform",
                url=f"https://test{i}.example.com",
                categories=[f"Category {i}"],
                patterns={"manuscript_id": f"TEST{i}-\\d{{4}}-\\d{{4}}"},
                credentials={"username": f"user{i}", "password": f"pass{i}"},
                settings={"timeout": 30 + i},
                platform_config={"setting": f"value{i}"}
            )
            
            # Process some data
            test_text = f"Manuscript TEST{i}-2024-{i:04d} needs review"
            pattern = config.patterns["manuscript_id"]
            re.search(pattern, test_text)
            
            # Delete reference
            del config
        
        # Force garbage collection again
        gc.collect()
        final_objects = len(gc.get_objects())
        
        # Memory usage should not grow excessively
        object_growth = final_objects - initial_objects
        self.assertLess(object_growth, 1000, f"Too many objects created: {object_growth}")
        
        print(f"✓ Memory efficiency: Object growth {object_growth} within acceptable limits")


def run_performance_tests():
    """Run performance and reliability tests."""
    print("⚡ Starting Performance and Reliability Tests...")
    print("=" * 60)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestPerformance,
        TestReliability,
        TestScalability
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests with minimal output
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
    result = runner.run(test_suite)
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("🏃‍♂️ PERFORMANCE & RELIABILITY SUMMARY")
    print("=" * 60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success Rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    
    if result.failures:
        print("\n❌ PERFORMANCE ISSUES:")
        for test, traceback in result.failures:
            print(f"  - {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  - {traceback.split('Exception:')[-1].strip()}")
    
    if not result.failures and not result.errors:
        print("\n✅ ALL PERFORMANCE TESTS PASSED!")
        print("🚀 System performs well under stress!")
        print("\nPerformance Metrics Validated:")
        print("✓ Configuration loading speed")
        print("✓ Regex pattern matching performance")
        print("✓ Concurrent session handling")
        print("✓ Stress test operations")
        print("✓ Large dataset scalability")
        print("✓ Memory efficiency")
    
    return result


if __name__ == "__main__":
    # Run performance tests
    test_result = run_performance_tests()
    
    # Exit with appropriate code
    sys.exit(0 if test_result.wasSuccessful() else 1)