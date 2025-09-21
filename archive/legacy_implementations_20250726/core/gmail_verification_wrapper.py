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

    The production MF extractor passes start_timestamp but the Gmail verification
    doesn't use it. This wrapper makes them compatible.

    TODO: Implement proper timestamp filtering to only get codes sent after login.
    """
    # For now, ignore start_timestamp and call the original function
    # This will get the latest code regardless of when it was sent
    return original_fetch(journal_code, max_wait, poll_interval)
