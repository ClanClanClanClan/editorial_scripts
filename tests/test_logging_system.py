"""Test the centralized logging system."""

import logging
import tempfile
from pathlib import Path
from io import StringIO
import sys

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.ecc.core.logging_system import (
    ExtractorLogger,
    LogLevel,
    LogCategory,
    LoggingContext,
    log_operation,
    setup_extraction_logging,
    get_default_logger
)


def test_extractor_logger_creation():
    """Test basic logger creation."""
    logger = ExtractorLogger("test")
    assert logger.name == "test"
    assert logger.context_depth == 0
    assert len(logger.operation_stack) == 0
    print("✅ Logger creation test passed")


def test_log_levels_and_categories():
    """Test different log levels and categories."""
    # Capture output
    output = StringIO()
    
    logger = ExtractorLogger("test")
    
    # Redirect logger to capture output
    handler = logging.StreamHandler(output)
    logger.logger.handlers = [handler]
    
    # Test different log types
    logger.success("Test success", LogCategory.AUTHENTICATION)
    logger.warning("Test warning", LogCategory.POPUP)
    logger.error("Test error", LogCategory.EXTRACTION)
    logger.info("Test info", LogCategory.DATA)
    
    output_text = output.getvalue()
    
    # Check that emojis and categories are present
    assert "✅" in output_text  # Success emoji
    assert "⚠️" in output_text  # Warning emoji
    assert "❌" in output_text  # Error emoji
    assert "[🔐 AUTH]" in output_text  # Auth category
    assert "[🖼️ POPUP]" in output_text  # Popup category
    assert "[🔍 EXTRACT]" in output_text  # Extract category
    assert "[📊 DATA]" in output_text  # Data category
    
    print("✅ Log levels and categories test passed")


def test_context_management():
    """Test context depth and indentation."""
    output = StringIO()
    
    logger = ExtractorLogger("test")
    handler = logging.StreamHandler(output)
    logger.logger.handlers = [handler]
    
    # Test nested contexts
    logger.info("Top level")
    
    logger.enter_context("operation1")
    logger.info("Level 1")
    
    logger.enter_context("operation2")
    logger.info("Level 2")
    
    logger.exit_context(success=True)
    logger.info("Back to level 1")
    
    logger.exit_context(success=True)
    logger.info("Back to top")
    
    output_text = output.getvalue()
    lines = output_text.strip().split('\n')
    
    # Check indentation pattern
    assert not lines[0].startswith("   ")  # Top level
    assert lines[1].startswith("   ")      # Level 1 (3 spaces)
    assert lines[2].startswith("         ")  # Level 2 (9 spaces)
    assert lines[3].startswith("   ")      # Back to level 1
    assert not lines[4].startswith("   ")  # Back to top
    
    print("✅ Context management test passed")


def test_statistics_tracking():
    """Test statistics collection."""
    logger = ExtractorLogger("test")
    
    # Initial stats
    stats = logger.get_stats()
    assert stats['operations_started'] == 0
    assert stats['operations_completed'] == 0
    assert stats['warnings_count'] == 0
    assert stats['errors_count'] == 0
    
    # Test operations
    logger.enter_context("test_op")
    logger.exit_context(success=True)
    
    logger.warning("Test warning")
    logger.error("Test error")
    
    # Check updated stats
    stats = logger.get_stats()
    assert stats['operations_started'] == 1
    assert stats['operations_completed'] == 1
    assert stats['operations_failed'] == 0
    assert stats['warnings_count'] == 1
    assert stats['errors_count'] == 1
    
    print("✅ Statistics tracking test passed")


def test_logging_context_manager():
    """Test LoggingContext context manager."""
    output = StringIO()
    
    logger = ExtractorLogger("test")
    handler = logging.StreamHandler(output)
    logger.logger.handlers = [handler]
    
    # Test successful operation
    with LoggingContext(logger, "test_operation", LogCategory.EXTRACTION):
        logger.info("Inside context")
    
    # Test failed operation
    try:
        with LoggingContext(logger, "failing_operation", LogCategory.BROWSER):
            logger.info("About to fail")
            raise ValueError("Test error")
    except ValueError:
        pass  # Expected
    
    output_text = output.getvalue()
    
    # Check that start/completion messages are present
    assert "Starting test_operation" in output_text
    assert "Completed test_operation" in output_text
    assert "Starting failing_operation" in output_text
    assert "Failed failing_operation" in output_text
    
    print("✅ Logging context manager test passed")


def test_operation_decorator():
    """Test log_operation decorator."""
    output = StringIO()
    
    logger = ExtractorLogger("test")
    handler = logging.StreamHandler(output)
    logger.logger.handlers = [handler]
    
    class TestClass:
        def __init__(self):
            self.logger = logger
        
        @log_operation("test_method", LogCategory.AUTHENTICATION)
        def test_method(self):
            self.logger.info("Inside decorated method")
            return "success"
    
    test_obj = TestClass()
    result = test_obj.test_method()
    
    assert result == "success"
    
    output_text = output.getvalue()
    assert "Starting test_method" in output_text
    assert "Completed test_method" in output_text
    
    print("✅ Operation decorator test passed")


def test_file_logging():
    """Test logging to file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        log_file = f.name
    
    try:
        logger = ExtractorLogger("test", log_file=log_file)
        
        logger.success("Test file logging")
        logger.warning("Test warning to file")
        
        # Read log file
        log_content = Path(log_file).read_text()
        
        # Check content is written to file (without colors)
        assert "Test file logging" in log_content
        assert "Test warning to file" in log_content
        
        print("✅ File logging test passed")
        
    finally:
        # Cleanup
        Path(log_file).unlink(missing_ok=True)


def test_convenience_functions():
    """Test convenience logging functions."""
    from src.ecc.core.logging_system import (
        print_success, print_warning, print_error, 
        print_info, print_progress, print_data
    )
    
    # These should not throw errors
    print_success("Test success")
    print_warning("Test warning")
    print_error("Test error")
    print_info("Test info")
    print_progress("Test progress")
    print_data("Test data")
    
    print("✅ Convenience functions test passed")


def test_setup_extraction_logging():
    """Test setup function."""
    logger = setup_extraction_logging("test_setup")
    
    assert logger.name == "test_setup"
    
    # Test that it becomes the default logger
    default_logger = get_default_logger()
    assert default_logger == logger
    
    print("✅ Setup extraction logging test passed")


def test_legacy_emoji_patterns():
    """Test that legacy emoji patterns are preserved."""
    output = StringIO()
    
    logger = ExtractorLogger("test")
    handler = logging.StreamHandler(output)
    logger.logger.handlers = [handler]
    
    # Test all the main emoji patterns from legacy code
    logger.auth_success("Credentials loaded from secure storage")
    logger.popup_warning("Popup window timeout")
    logger.extraction_error("No email found in popup")
    logger.frame_info("Found 3 frames in popup")
    logger.timing_info("Operation completed in 2.5s")
    logger.progress("Processing manuscript 5/10")
    
    output_text = output.getvalue()
    
    # Check key emoji patterns exist
    assert "✅" in output_text  # Success
    assert "⚠️" in output_text  # Warning
    assert "❌" in output_text  # Error
    assert "📋" in output_text  # Frame
    assert "⏱️" in output_text  # Timing
    assert "🎯" in output_text  # Progress
    
    print("✅ Legacy emoji patterns test passed")


def test_summary_output():
    """Test summary generation."""
    output = StringIO()
    
    logger = ExtractorLogger("test")
    handler = logging.StreamHandler(output)
    logger.logger.handlers = [handler]
    
    # Simulate some operations
    logger.enter_context("op1")
    logger.exit_context(success=True)
    
    logger.enter_context("op2")
    logger.exit_context(success=False)
    
    logger.warning("Test warning")
    logger.error("Test error")
    
    # Generate summary
    logger.print_summary()
    
    output_text = output.getvalue()
    
    # Check summary contains expected info
    assert "EXECUTION SUMMARY" in output_text
    assert "Operations started: 2" in output_text
    assert "Operations completed: 1" in output_text
    assert "Operations failed: 1" in output_text
    assert "Warnings: 1" in output_text
    assert "Errors: 1" in output_text
    assert "Runtime:" in output_text
    
    print("✅ Summary output test passed")


if __name__ == "__main__":
    print("Testing centralized logging system...")
    print("=" * 60)
    
    # Run all tests
    test_extractor_logger_creation()
    test_log_levels_and_categories()
    test_context_management()
    test_statistics_tracking()
    test_logging_context_manager()
    test_operation_decorator()
    test_file_logging()
    test_convenience_functions()
    test_setup_extraction_logging()
    test_legacy_emoji_patterns()
    test_summary_output()
    
    print("\n✅ All logging system tests passed!")