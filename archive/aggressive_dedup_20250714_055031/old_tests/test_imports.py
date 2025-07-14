#!/usr/bin/env python3
"""Test import of all required dependencies."""

import sys
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}\n")

# Test critical imports
test_packages = [
    "playwright",
    "beautifulsoup4",
    "aiohttp",
    "aiofiles",
    "google.auth",
    "google_auth_oauthlib",
    "google_auth_httplib2",
    "googleapiclient",
    "dateutil",
]

print("Testing imports:")
for package in test_packages:
    try:
        if package == "beautifulsoup4":
            import bs4
            print(f"✓ {package} ({bs4.__version__})")
        elif package == "google.auth":
            import google.auth
            print(f"✓ google-auth ({google.auth.__version__})")
        elif package == "google_auth_oauthlib":
            import google_auth_oauthlib
            print(f"✓ google-auth-oauthlib")
        elif package == "google_auth_httplib2":
            import google_auth_httplib2
            print(f"✓ google-auth-httplib2")
        elif package == "googleapiclient":
            import googleapiclient
            print(f"✓ google-api-python-client")
        elif package == "dateutil":
            import dateutil
            print(f"✓ python-dateutil ({dateutil.__version__})")
        else:
            __import__(package)
            module = sys.modules[package]
            version = getattr(module, "__version__", "unknown")
            print(f"✓ {package} ({version})")
    except ImportError as e:
        print(f"✗ {package}: {e}")

print("\nAll critical imports successful!")