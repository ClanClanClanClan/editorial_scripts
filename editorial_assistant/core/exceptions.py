"""
Custom exceptions for the Editorial Assistant system.

This module defines specific exception types for different error scenarios,
enabling precise error handling and debugging.
"""


class EditorialAssistantError(Exception):
    """Base exception for all Editorial Assistant errors."""
    pass


class ExtractionError(EditorialAssistantError):
    """General extraction error."""
    pass


class LoginError(ExtractionError):
    """Error during login process."""
    pass


class NavigationError(ExtractionError):
    """Error navigating the journal website."""
    pass


class PDFDownloadError(ExtractionError):
    """Error downloading PDF files."""
    pass


class RefereeDataError(ExtractionError):
    """Error extracting referee data."""
    pass


class ConfigurationError(EditorialAssistantError):
    """Error in configuration files or settings."""
    pass


class BrowserError(EditorialAssistantError):
    """Error related to browser/driver management."""
    pass


class TimeoutError(EditorialAssistantError):
    """Operation timed out."""
    pass


class ValidationError(EditorialAssistantError):
    """Data validation error."""
    pass


class CheckpointError(EditorialAssistantError):
    """Error saving or loading checkpoints."""
    pass


class EmailError(EditorialAssistantError):
    """Error with email operations."""
    pass