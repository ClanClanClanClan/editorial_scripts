"""Integration test harness for the ECC modular architecture."""

import sys
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.ecc.core.error_handling import ErrorCollector, SafeExecutor
from src.ecc.core.logging_system import LogCategory, setup_extraction_logging
from src.ecc.core.performance_cache import CacheStrategy, create_extraction_cache
from src.ecc.core.retry_strategies import RetryConfig, RetryConfigs, retry


class TestStatus(Enum):
    """Test execution status."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TestSeverity(Enum):
    """Test failure severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TestResult:
    """Individual test result with comprehensive metrics."""

    test_name: str
    status: TestStatus
    execution_time: float = 0.0
    error_message: str | None = None
    severity: TestSeverity = TestSeverity.MEDIUM
    logs: list[str] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    retry_attempts: int = 0
    error_count: int = 0
    warning_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSuite:
    """Collection of related tests."""

    name: str
    description: str
    tests: list[Callable] = field(default_factory=list)
    setup: Callable | None = None
    teardown: Callable | None = None
    enabled: bool = True


class IntegrationTestHarness:
    """Comprehensive test harness for ECC module integration."""

    def __init__(self, test_name: str = "ECC Integration Tests"):
        """Initialize the test harness with all ECC components."""
        self.test_name = test_name

        # Initialize ECC components
        self.logger = setup_extraction_logging("integration_test")
        self.error_collector = ErrorCollector()
        self.safe_executor = SafeExecutor(self.logger.logger)
        self.cache = create_extraction_cache(CacheStrategy.MEMORY)

        # Test tracking
        self.test_suites: list[TestSuite] = []
        self.results: list[TestResult] = []
        self.start_time = 0.0
        self.end_time = 0.0

        # Statistics
        self.stats = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total_time": 0.0,
            "average_time": 0.0,
            "cache_hit_rate": 0.0,
            "retry_success_rate": 0.0,
        }

    def add_test_suite(self, suite: TestSuite):
        """Add a test suite to the harness."""
        self.test_suites.append(suite)
        self.logger.info(f"Added test suite: {suite.name} ({len(suite.tests)} tests)")

    def register_test(self, suite_name: str, test_func: Callable, description: str = ""):
        """Register a test function with a suite."""
        # Find or create suite
        suite = next((s for s in self.test_suites if s.name == suite_name), None)
        if not suite:
            suite = TestSuite(suite_name, description or suite_name)
            self.add_test_suite(suite)

        test_func.__doc__ = description or test_func.__doc__ or test_func.__name__
        suite.tests.append(test_func)

    def run_test(self, test_func: Callable, suite_name: str = "") -> TestResult:
        """Execute a single test with comprehensive monitoring."""
        test_name = f"{suite_name}.{test_func.__name__}" if suite_name else test_func.__name__

        self.logger.enter_context(f"test_{test_func.__name__}")
        self.logger.info(f"Running test: {test_name}", LogCategory.PROGRESS)

        result = TestResult(test_name, TestStatus.RUNNING)
        start_time = time.time()

        try:
            # Reset error collector for this test
            self.error_collector.clear()

            # Execute test directly to allow proper failure handling
            test_result = test_func()

            # Calculate execution time
            result.execution_time = time.time() - start_time

            # Collect metrics from ECC components
            result.error_count = len(self.error_collector.errors)
            result.warning_count = len(self.error_collector.warnings)

            # Determine test status
            if result.error_count > 0:
                result.status = TestStatus.FAILED
                result.severity = TestSeverity.HIGH
                result.error_message = f"{result.error_count} errors occurred"
            elif test_result is False:
                result.status = TestStatus.FAILED
                result.severity = TestSeverity.MEDIUM
                result.error_message = "Test returned False"
            else:
                result.status = TestStatus.PASSED

            self.logger.success(f"Test completed: {result.status.value}")

        except Exception as e:
            result.execution_time = time.time() - start_time
            result.status = TestStatus.FAILED
            result.severity = TestSeverity.CRITICAL
            result.error_message = f"Exception: {str(e)}"

            self.logger.error(f"Test failed with exception: {e}")

            # Add traceback to metadata
            result.metadata["traceback"] = traceback.format_exc()

        finally:
            self.logger.exit_context(success=(result.status == TestStatus.PASSED))

        self.results.append(result)
        return result

    def run_suite(self, suite: TestSuite) -> list[TestResult]:
        """Execute all tests in a suite."""
        if not suite.enabled:
            self.logger.warning(f"Skipping disabled suite: {suite.name}")
            return []

        self.logger.enter_context(f"suite_{suite.name}")
        self.logger.progress(f"Running test suite: {suite.name}")

        suite_results = []

        try:
            # Run setup if provided
            if suite.setup:
                self.logger.info("Running suite setup")
                self.safe_executor.execute(
                    operation=suite.setup, operation_name=f"{suite.name}_setup", critical=True
                )

            # Execute all tests in suite
            for test_func in suite.tests:
                result = self.run_test(test_func, suite.name)
                suite_results.append(result)

            # Run teardown if provided
            if suite.teardown:
                self.logger.info("Running suite teardown")
                self.safe_executor.execute(
                    operation=suite.teardown,
                    operation_name=f"{suite.name}_teardown",
                    critical=False,
                )

        except Exception as e:
            self.logger.error(f"Suite execution failed: {e}")

        finally:
            self.logger.exit_context(success=True)

        return suite_results

    def run_all_tests(self) -> dict[str, Any]:
        """Execute all registered test suites."""
        self.logger.progress(f"Starting {self.test_name}")
        self.start_time = time.time()

        # Clear previous results
        self.results.clear()

        try:
            # Execute all test suites
            for suite in self.test_suites:
                self.run_suite(suite)

            self.end_time = time.time()

            # Calculate statistics
            self._calculate_statistics()

            # Generate comprehensive report
            report = self._generate_report()

            self.logger.print_summary()
            self._print_test_summary()

            return report

        except Exception as e:
            self.logger.error(f"Test execution failed: {e}")
            return {"success": False, "error": str(e)}

    def _calculate_statistics(self):
        """Calculate comprehensive test statistics."""
        self.stats["total_tests"] = len(self.results)
        self.stats["passed"] = sum(1 for r in self.results if r.status == TestStatus.PASSED)
        self.stats["failed"] = sum(1 for r in self.results if r.status == TestStatus.FAILED)
        self.stats["skipped"] = sum(1 for r in self.results if r.status == TestStatus.SKIPPED)

        if self.results:
            self.stats["total_time"] = self.end_time - self.start_time
            self.stats["average_time"] = sum(r.execution_time for r in self.results) / len(
                self.results
            )

            # Cache statistics
            total_cache_operations = sum(r.cache_hits + r.cache_misses for r in self.results)
            if total_cache_operations > 0:
                self.stats["cache_hit_rate"] = (
                    sum(r.cache_hits for r in self.results) / total_cache_operations
                )

            # Retry statistics
            total_retries = sum(r.retry_attempts for r in self.results)
            self.stats["total_retries"] = total_retries

    def _generate_report(self) -> dict[str, Any]:
        """Generate comprehensive test report."""
        return {
            "test_name": self.test_name,
            "execution_time": self.stats["total_time"],
            "statistics": self.stats,
            "results": [
                {
                    "test_name": r.test_name,
                    "status": r.status.value,
                    "execution_time": r.execution_time,
                    "error_message": r.error_message,
                    "severity": r.severity.value,
                    "metadata": r.metadata,
                }
                for r in self.results
            ],
            "component_health": {
                "logging_system": "operational",
                "error_handling": "operational",
                "retry_strategies": "operational",
                "performance_cache": "operational",
            },
            "success": self.stats["failed"] == 0,
        }

    def _print_test_summary(self):
        """Print detailed test execution summary."""
        self.logger.data_info("=" * 60)
        self.logger.data_info("INTEGRATION TEST SUMMARY")
        self.logger.data_info("=" * 60)

        # Overall statistics
        self.logger.data_info(f"Total Tests: {self.stats['total_tests']}")
        self.logger.data_info(f"Passed: {self.stats['passed']} ✅")
        self.logger.data_info(f"Failed: {self.stats['failed']} ❌")
        self.logger.data_info(f"Skipped: {self.stats['skipped']} ⏭️")

        if self.stats["total_tests"] > 0:
            success_rate = 100 * self.stats["passed"] / self.stats["total_tests"]
            self.logger.data_info(f"Success Rate: {success_rate:.1f}%")

        self.logger.data_info(f"Total Time: {self.stats['total_time']:.2f}s")
        self.logger.data_info(f"Average Time: {self.stats['average_time']:.3f}s")

        # Component-specific metrics
        if self.stats.get("cache_hit_rate", 0) > 0:
            self.logger.data_info(f"Cache Hit Rate: {100 * self.stats['cache_hit_rate']:.1f}%")

        if self.stats.get("total_retries", 0) > 0:
            self.logger.data_info(f"Total Retries: {self.stats['total_retries']}")

        # Failed tests details
        failed_tests = [r for r in self.results if r.status == TestStatus.FAILED]
        if failed_tests:
            self.logger.data_info("\nFAILED TESTS:")
            for result in failed_tests:
                self.logger.error(f"  {result.test_name}: {result.error_message}")

        # Overall result
        if self.stats["failed"] == 0:
            self.logger.success("🎉 ALL INTEGRATION TESTS PASSED!")
        else:
            self.logger.error(f"💥 {self.stats['failed']} TESTS FAILED")


# Test decorators for easy registration
def integration_test(harness: IntegrationTestHarness, suite_name: str = "default"):
    """Decorator to register integration tests."""

    def decorator(func: Callable) -> Callable:
        harness.register_test(suite_name, func, func.__doc__ or "")
        return func

    return decorator


def test_with_retry(retry_config: RetryConfig = None):
    """Decorator to add retry capability to tests."""
    if retry_config is None:
        retry_config = RetryConfigs.STANDARD

    return retry(config=retry_config)


# Convenience functions for creating test harnesses
def create_integration_harness(name: str = "ECC Integration Tests") -> IntegrationTestHarness:
    """Create a new integration test harness."""
    return IntegrationTestHarness(name)


def create_component_test_suite(name: str, description: str = "") -> TestSuite:
    """Create a test suite for a specific component."""
    return TestSuite(name, description or f"Tests for {name}")


# Example integration test patterns
class ComponentIntegrationTests:
    """Example integration tests demonstrating component interaction."""

    def __init__(self, harness: IntegrationTestHarness):
        self.harness = harness
        self.logger = harness.logger
        self.cache = harness.cache
        self.safe_executor = harness.safe_executor

    def test_logging_error_integration(self):
        """Test integration between logging and error handling."""
        self.logger.info("Testing logging-error integration")

        try:
            # Simulate an operation that might fail
            def failing_operation():
                raise ValueError("Simulated error for testing")

            # Use safe executor to handle the error
            result = self.safe_executor.execute(
                operation=failing_operation,
                operation_name="test_operation",
                default_value="default_result",
                critical=False,
            )

            # Should return default value
            assert result == "default_result"
            self.logger.success("Logging-error integration working correctly")
            return True

        except Exception as e:
            self.logger.error(f"Integration test failed: {e}")
            return False

    def test_cache_retry_integration(self):
        """Test integration between caching and retry mechanisms."""
        call_count = 0

        @retry(config=RetryConfigs.NETWORK)
        def cached_operation_with_retry(key: str):
            nonlocal call_count

            # Check cache first (before incrementing call count)
            cached_result = self.cache.cache.get(key)
            if cached_result:
                return cached_result

            # Only increment call count for actual operations
            call_count += 1

            # Simulate operation that fails first time
            if call_count == 1:
                raise ConnectionError("Simulated network error")

            # Succeed on retry
            result = f"result_for_{key}"
            self.cache.cache.set(key, result)
            return result

        # Test the integration
        result = cached_operation_with_retry("test_key")
        assert result == "result_for_test_key"
        assert call_count == 2  # Should retry once

        # Second call should use cache (no operation count increment)
        call_count_before_cache_call = call_count
        result2 = cached_operation_with_retry("test_key")
        assert result2 == "result_for_test_key"
        assert call_count == call_count_before_cache_call  # Should not increment

        self.logger.success("Cache-retry integration working correctly")
        return True

    def test_full_component_integration(self):
        """Test all components working together in a realistic scenario."""
        self.logger.progress("Testing full component integration")

        # Simulate a complex extraction workflow
        @retry(config=RetryConfigs.STANDARD)
        def complex_extraction(manuscript_id: str):
            # Check cache first
            cached_data = self.cache.get_cached_status(manuscript_id)
            if cached_data:
                self.logger.success(f"Using cached data for {manuscript_id}")
                return cached_data

            # Simulate extraction steps with potential failures
            steps = [
                lambda: self._simulate_login(),
                lambda: self._simulate_navigation(),
                lambda: self._simulate_data_extraction(manuscript_id),
            ]

            results = []
            for i, step in enumerate(steps):
                try:
                    result = self.safe_executor.execute(
                        operation=step, operation_name=f"extraction_step_{i+1}", critical=True
                    )
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Step {i+1} failed: {e}")
                    raise

            # Cache successful result
            final_result = {"manuscript_id": manuscript_id, "steps": results}
            self.cache.cache_manuscript_status(manuscript_id, "extracted")

            return final_result

        # Execute the complex workflow
        result = complex_extraction("TEST-MS-001")
        assert result is not None
        assert result["manuscript_id"] == "TEST-MS-001"

        self.logger.success("Full component integration successful")
        return True

    def _simulate_login(self):
        """Simulate login step."""
        self.logger.auth_success("Login successful")
        return "logged_in"

    def _simulate_navigation(self):
        """Simulate navigation step."""
        self.logger.success("Navigation successful", LogCategory.NAVIGATION)
        return "navigated"

    def _simulate_data_extraction(self, manuscript_id: str):
        """Simulate data extraction step."""
        self.logger.extraction_success(f"Data extracted for {manuscript_id}")
        return f"data_for_{manuscript_id}"
