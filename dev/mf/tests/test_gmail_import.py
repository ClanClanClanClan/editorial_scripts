#!/usr/bin/env python3
"""Test if Gmail verification imports work"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src'))

try:
    from core.gmail_verification_wrapper import fetch_latest_verification_code
    print("✅ Gmail wrapper imported successfully")

    # Test calling with all parameters
    print("Testing function signature with start_timestamp...")
    # This will fail but we just want to check the signature
    try:
        result = fetch_latest_verification_code('MF', max_wait=1, poll_interval=1, start_timestamp=1234567890)
        print(f"Function call worked: {result}")
    except Exception as e:
        print(f"Function call error (expected): {e}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()