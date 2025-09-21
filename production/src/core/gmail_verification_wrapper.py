"""
Gmail Verification Wrapper
==========================

Wraps the gmail_verification to handle different parameter signatures.
"""


# Import from the same directory
try:
    from .gmail_verification import fetch_latest_verification_code as original_fetch
except ImportError:
    # Fallback to absolute import when running as script
    from gmail_verification import fetch_latest_verification_code as original_fetch


def fetch_latest_verification_code(
    journal_code, max_wait=60, poll_interval=3, start_timestamp=None
):
    """
    Wrapper for fetch_latest_verification_code that handles the start_timestamp parameter.

    The production MF extractor passes start_timestamp to ensure we only get codes
    sent AFTER credentials were submitted.
    """
    # Pass ALL parameters including start_timestamp
    return original_fetch(journal_code, max_wait, poll_interval, start_timestamp)
