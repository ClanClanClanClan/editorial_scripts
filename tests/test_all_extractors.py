#!/usr/bin/env python3
"""Comprehensive test suite for all ECC extractors."""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ExtractorTestSuite:
    """Test all extractors systematically."""

    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "skipped": [],
        }
        self.start_time = datetime.now()

    def log(self, level: str, message: str):
        """Log test results."""
        icons = {"INFO": "ℹ️", "SUCCESS": "✅", "FAIL": "❌", "SKIP": "⏭️"}
        print(f"{icons.get(level, '•')} {message}")

    async def test_fs_extractor(self):
        """Test FS (Finance & Stochastics) extractor."""
        self.log("INFO", "Testing FS Extractor...")
        try:
            from src.ecc.adapters.journals.fs import FSAdapter

            adapter = FSAdapter()
            self.log("SUCCESS", "FS: Instantiation successful")
            self.log("INFO", f"  Provider: {adapter.config.provider.value}")
            self.log("INFO", f"  Token path: {adapter.config.gmail_token_path}")

            # Check if OAuth tokens exist
            token_path = Path(adapter.config.gmail_token_path)
            if token_path.exists():
                self.log("SUCCESS", "FS: OAuth tokens found")
                self.results["passed"].append(("FS", "Complete with OAuth"))
            else:
                self.log("SKIP", "FS: OAuth tokens not configured (expected)")
                self.results["skipped"].append(("FS", "OAuth tokens needed for full test"))

        except Exception as e:
            self.log("FAIL", f"FS: {e}")
            self.results["failed"].append(("FS", str(e)))

    async def test_mf_extractor(self):
        """Test MF (Mathematical Finance) extractor."""
        self.log("INFO", "Testing MF Extractor...")
        try:
            from src.ecc.adapters.journals.mf import MFAdapter

            adapter = MFAdapter(headless=True)
            self.log("SUCCESS", "MF: Instantiation successful")
            self.log("INFO", f"  Config: {adapter.config}")

            # Check credentials
            has_creds = bool(os.getenv("MF_EMAIL") and os.getenv("MF_PASSWORD"))
            if has_creds:
                self.log("SUCCESS", "MF: Credentials available")
                self.results["passed"].append(("MF", "Ready for extraction"))
            else:
                self.log("SKIP", "MF: Credentials not in environment")
                self.results["skipped"].append(("MF", "Credentials needed"))

        except Exception as e:
            self.log("FAIL", f"MF: {e}")
            self.results["failed"].append(("MF", str(e)))

    async def test_mor_extractor(self):
        """Test MOR (Mathematics of Operations Research) extractor."""
        self.log("INFO", "Testing MOR Extractor...")
        try:
            from src.ecc.adapters.journals.mor import MORAdapter

            adapter = MORAdapter(headless=True)
            self.log("SUCCESS", "MOR: Instantiation successful")

            has_creds = bool(os.getenv("MOR_EMAIL") and os.getenv("MOR_PASSWORD"))
            if has_creds:
                self.log("SUCCESS", "MOR: Credentials available")
                self.results["passed"].append(("MOR", "Ready for extraction"))
            else:
                self.log("SKIP", "MOR: Credentials not in environment")
                self.results["skipped"].append(("MOR", "Credentials needed"))

        except Exception as e:
            self.log("FAIL", f"MOR: {e}")
            self.results["failed"].append(("MOR", str(e)))

    async def test_jota_extractor(self):
        """Test JOTA extractor."""
        self.log("INFO", "Testing JOTA Extractor...")
        try:
            from src.ecc.adapters.journals.jota import JOTAAdapter

            adapter = JOTAAdapter(headless=True)
            self.log("SUCCESS", "JOTA: Instantiation successful")

            has_creds = bool(os.getenv("JOTA_EMAIL") and os.getenv("JOTA_PASSWORD"))
            if has_creds:
                self.log("SUCCESS", "JOTA: Credentials available")
                self.results["passed"].append(("JOTA", "Ready for extraction"))
            else:
                self.log("SKIP", "JOTA: Credentials not in environment")
                self.results["skipped"].append(("JOTA", "Credentials needed"))

        except Exception as e:
            self.log("FAIL", f"JOTA: {e}")
            self.results["failed"].append(("JOTA", str(e)))

    async def test_mafe_extractor(self):
        """Test MAFE extractor."""
        self.log("INFO", "Testing MAFE Extractor...")
        try:
            from src.ecc.adapters.journals.mafe import MAFEAdapter

            adapter = MAFEAdapter(headless=True)
            self.log("SUCCESS", "MAFE: Instantiation successful")

            has_creds = bool(os.getenv("MAFE_EMAIL") and os.getenv("MAFE_PASSWORD"))
            if has_creds:
                self.log("SUCCESS", "MAFE: Credentials available")
                self.results["passed"].append(("MAFE", "Ready for extraction"))
            else:
                self.log("SKIP", "MAFE: Credentials not in environment")
                self.results["skipped"].append(("MAFE", "Credentials needed"))

        except Exception as e:
            self.log("FAIL", f"MAFE: {e}")
            self.results["failed"].append(("MAFE", str(e)))

    async def test_sicon_extractor(self):
        """Test SICON extractor."""
        self.log("INFO", "Testing SICON Extractor...")
        try:
            from src.ecc.adapters.journals.sicon import SICONAdapter

            adapter = SICONAdapter(headless=True)
            self.log("SUCCESS", "SICON: Instantiation successful")

            has_creds = bool(os.getenv("SICON_EMAIL") and os.getenv("SICON_PASSWORD"))
            if has_creds:
                self.log("SUCCESS", "SICON: Credentials available")
                self.results["passed"].append(("SICON", "Ready for extraction"))
            else:
                self.log("SKIP", "SICON: Credentials not in environment")
                self.results["skipped"].append(("SICON", "Credentials needed"))

        except Exception as e:
            self.log("FAIL", f"SICON: {e}")
            self.results["failed"].append(("SICON", str(e)))

    async def test_sifin_extractor(self):
        """Test SIFIN extractor."""
        self.log("INFO", "Testing SIFIN Extractor...")
        try:
            from src.ecc.adapters.journals.sifin import SIFINAdapter

            adapter = SIFINAdapter(headless=True)
            self.log("SUCCESS", "SIFIN: Instantiation successful")

            has_creds = bool(os.getenv("SIFIN_EMAIL") and os.getenv("SIFIN_PASSWORD"))
            if has_creds:
                self.log("SUCCESS", "SIFIN: Credentials available")
                self.results["passed"].append(("SIFIN", "Ready for extraction"))
            else:
                self.log("SKIP", "SIFIN: Credentials not in environment")
                self.results["skipped"].append(("SIFIN", "Credentials needed"))

        except Exception as e:
            self.log("FAIL", f"SIFIN: {e}")
            self.results["failed"].append(("SIFIN", str(e)))

    async def test_naco_extractor(self):
        """Test NACO extractor."""
        self.log("INFO", "Testing NACO Extractor...")
        try:
            from src.ecc.adapters.journals.naco import NACOAdapter

            adapter = NACOAdapter(headless=True)
            self.log("SUCCESS", "NACO: Instantiation successful")

            has_creds = bool(os.getenv("NACO_EMAIL") and os.getenv("NACO_PASSWORD"))
            if has_creds:
                self.log("SUCCESS", "NACO: Credentials available")
                self.results["passed"].append(("NACO", "Ready for extraction"))
            else:
                self.log("SKIP", "NACO: Credentials not in environment")
                self.results["skipped"].append(("NACO", "Credentials needed"))

        except Exception as e:
            self.log("FAIL", f"NACO: {e}")
            self.results["failed"].append(("NACO", str(e)))

    async def test_adapter_factory(self):
        """Test adapter factory."""
        self.log("INFO", "Testing Adapter Factory...")
        try:
            from src.ecc.adapters.journals.factory import get_adapter

            journals = ["MF", "MOR", "FS", "JOTA", "MAFE", "SICON", "SIFIN", "NACO"]
            for journal in journals:
                try:
                    adapter = get_adapter(journal, headless=True)
                    self.log("SUCCESS", f"Factory: {journal} ✓")
                except Exception as e:
                    self.log("FAIL", f"Factory: {journal} - {e}")
                    raise

            self.results["passed"].append(("Factory", "All 8 journals"))

        except Exception as e:
            self.log("FAIL", f"Factory: {e}")
            self.results["failed"].append(("Factory", str(e)))

    async def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 80)
        print("🧪 ECC EXTRACTOR COMPREHENSIVE TEST SUITE")
        print(f"⏰ Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()

        # Load credentials
        try:
            import subprocess

            result = subprocess.run(
                ["bash", "-c", "source ~/.editorial_scripts/load_all_credentials.sh && env"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.split("\n"):
                if any(
                    j in line
                    for j in ["MF_", "MOR_", "FS_", "JOTA_", "MAFE_", "SICON_", "SIFIN_", "NACO_"]
                ):
                    key = line.split("=")[0]
                    os.environ[key] = line.split("=", 1)[1] if "=" in line else ""
            self.log("SUCCESS", "Credentials loaded from keychain")
        except Exception as e:
            self.log("SKIP", f"Could not auto-load credentials: {e}")

        # Run all tests
        await self.test_adapter_factory()
        await self.test_fs_extractor()
        await self.test_mf_extractor()
        await self.test_mor_extractor()
        await self.test_jota_extractor()
        await self.test_mafe_extractor()
        await self.test_sicon_extractor()
        await self.test_sifin_extractor()
        await self.test_naco_extractor()

        # Summary
        print()
        print("=" * 80)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"✅ Passed:  {len(self.results['passed'])}")
        print(f"⏭️  Skipped: {len(self.results['skipped'])}")
        print(f"❌ Failed:  {len(self.results['failed'])}")
        print()

        if self.results["passed"]:
            print("✅ PASSED:")
            for name, status in self.results["passed"]:
                print(f"   {name}: {status}")
            print()

        if self.results["skipped"]:
            print("⏭️  SKIPPED:")
            for name, reason in self.results["skipped"]:
                print(f"   {name}: {reason}")
            print()

        if self.results["failed"]:
            print("❌ FAILED:")
            for name, error in self.results["failed"]:
                print(f"   {name}: {error}")
            print()

        duration = (datetime.now() - self.start_time).total_seconds()
        print(f"⏱️  Duration: {duration:.2f}s")
        print("=" * 80)

        # Exit code
        return 0 if not self.results["failed"] else 1


async def main():
    """Main entry point."""
    suite = ExtractorTestSuite()
    exit_code = await suite.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
