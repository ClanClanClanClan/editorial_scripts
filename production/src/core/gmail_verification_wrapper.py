"""
Gmail Verification Wrapper
==========================

Wraps the gmail_verification to handle different parameter signatures.
"""

import sys
from pathlib import Path

# Import from the same directory
try:
    from .gmail_verification import fetch_latest_verification_code as original_fetch
except ImportError:
    # Fallback to absolute import when running as script
    from gmail_verification import fetch_latest_verification_code as original_fetch

def fetch_latest_verification_code(journal_code, max_wait=60, poll_interval=3, start_timestamp=None):
    """
    Wrapper for fetch_latest_verification_code that handles the start_timestamp parameter.
    
    The production MF extractor passes start_timestamp but the Gmail verification
    doesn't use it. This wrapper makes them compatible.
    """
    # Ignore start_timestamp and call the original function
    return original_fetch(journal_code, max_wait, poll_interval)