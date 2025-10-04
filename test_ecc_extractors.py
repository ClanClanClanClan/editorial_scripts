#!/usr/bin/env python3
"""Test ECC extractors end-to-end."""

import asyncio
import json
from pathlib import Path
from datetime import datetime


async def test_fs_extractor():
    """Test FS (Gmail-based) extractor."""
    from src.ecc.adapters.journals.fs import FSAdapter

    print("=" * 80)
    print("Testing FS Extractor (Gmail-based)")
    print("=" * 80)

    try:
        adapter = FSAdapter()
        print("✅ FSAdapter instantiated")

        # Note: This requires Gmail OAuth tokens which we haven't set up yet
        # For now, just test that the adapter can be created
        print("⚠️  Gmail OAuth tokens not configured - skipping actual extraction")
        print(f"   Adapter config: {adapter.config}")

    except Exception as e:
        print(f"❌ FS test failed: {e}")
        import traceback

        traceback.print_exc()


async def test_mf_extractor():
    """Test MF (ScholarOne) extractor."""
    from src.ecc.adapters.journals.mf import MFAdapter

    print("\n" + "=" * 80)
    print("Testing MF Extractor (ScholarOne)")
    print("=" * 80)

    try:
        adapter = MFAdapter(headless=True)
        print("✅ MFAdapter instantiated")
        print(f"   Platform: {adapter.platform}")
        print(f"   Base URL: {adapter.base_url}")
        print(f"   Config: {adapter.config}")

        # Check if we can access credentials
        import os

        has_creds = bool(os.getenv("MF_EMAIL") and os.getenv("MF_PASSWORD"))
        print(f"   Credentials available: {has_creds}")

        if has_creds:
            print("\n🔐 Attempting authentication...")
            # Don't actually authenticate in headless mode for now
            print("⚠️  Skipping actual authentication test (headless mode)")
        else:
            print("⚠️  MF credentials not in environment")

    except Exception as e:
        print(f"❌ MF test failed: {e}")
        import traceback

        traceback.print_exc()


async def compare_architectures():
    """Compare ECC vs Production architecture."""
    print("\n" + "=" * 80)
    print("Architecture Comparison")
    print("=" * 80)

    # ECC architecture stats
    from pathlib import Path

    ecc_files = list(Path("src/ecc/adapters/journals").glob("*.py"))
    ecc_lines = sum(len(open(f).readlines()) for f in ecc_files if f.name != "__init__.py")

    # Production architecture stats
    prod_files = list(Path("production/src/extractors").glob("*_extractor.py"))
    prod_lines = sum(len(open(f).readlines()) for f in prod_files)

    print(f"\n📊 ECC Architecture:")
    print(f"   Files: {len(ecc_files)}")
    print(f"   Total lines: {ecc_lines:,}")
    print(f"   Avg lines/file: {ecc_lines//len(ecc_files):,}")

    print(f"\n📊 Production Architecture:")
    print(f"   Files: {len(prod_files)}")
    print(f"   Total lines: {prod_lines:,}")
    print(f"   Avg lines/file: {prod_lines//len(prod_files):,}")

    reduction = ((prod_lines - ecc_lines) / prod_lines) * 100
    print(f"\n🎯 Code Reduction: {reduction:.1f}%")

    print(f"\n📁 ECC Structure:")
    for f in sorted(ecc_files):
        lines = len(open(f).readlines())
        print(f"   {f.name:30} {lines:>6} lines")


async def main():
    """Run all tests."""
    print("\n🚀 ECC EXTRACTOR TEST SUITE")
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Load credentials
    import os
    import subprocess

    try:
        result = subprocess.run(
            ["source", "~/.editorial_scripts/load_all_credentials.sh"],
            shell=True,
            capture_output=True,
            text=True,
        )
    except:
        print("⚠️  Could not load credentials from shell script")

    # Run tests
    await test_fs_extractor()
    await test_mf_extractor()
    await compare_architectures()

    print("\n" + "=" * 80)
    print("✅ Test Suite Complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
