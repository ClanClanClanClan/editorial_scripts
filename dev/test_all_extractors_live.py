#!/usr/bin/env python3
"""
Live extraction testing for all 8 ECC extractors.
Tests actual authentication and data extraction.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ecc.adapters.journals.mf import MFAdapter
from src.ecc.adapters.journals.mor import MORAdapter
from src.ecc.adapters.journals.fs import FSAdapter
from src.ecc.adapters.journals.jota import JOTAAdapter
from src.ecc.adapters.journals.mafe import MAFEAdapter
from src.ecc.adapters.journals.sicon import SICONAdapter
from src.ecc.adapters.journals.sifin import SIFINAdapter
from src.ecc.adapters.journals.naco import NACOAdapter


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


class ExtractorTester:
    """Live testing for all extractors."""

    def __init__(self):
        self.results = {}
        self.start_time = datetime.now()
        self.output_dir = Path(__file__).parent / "test_outputs"
        self.output_dir.mkdir(exist_ok=True)

    def log(self, level: str, message: str):
        """Colorized logging."""
        colors = {
            "INFO": Colors.BLUE,
            "SUCCESS": Colors.GREEN,
            "ERROR": Colors.RED,
            "WARNING": Colors.YELLOW,
            "HEADER": Colors.CYAN + Colors.BOLD,
        }
        color = colors.get(level, Colors.RESET)
        print(f"{color}[{level}]{Colors.RESET} {message}")

    def save_result(self, journal: str, data: dict):
        """Save extraction result to JSON."""
        filepath = (
            self.output_dir
            / f"{journal}_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        self.log("INFO", f"Saved to {filepath}")

    async def test_scholarone_adapter(
        self, adapter_class, journal_id: str, categories: list[str] = None
    ):
        """Test ScholarOne-based adapter (MF, MOR)."""
        self.log("HEADER", f"\n{'='*80}\nTesting {journal_id} Extractor\n{'='*80}")

        try:
            # Check credentials
            email = os.getenv(f"{journal_id}_EMAIL")
            password = os.getenv(f"{journal_id}_PASSWORD")

            if not email or not password:
                self.log("ERROR", f"Missing credentials for {journal_id}")
                self.results[journal_id] = {
                    "status": "skipped",
                    "reason": "Missing credentials",
                    "timestamp": datetime.now().isoformat(),
                }
                return

            self.log("INFO", f"Credentials found: {email}")

            # Initialize adapter
            async with adapter_class(headless=True) as adapter:
                self.log("INFO", f"Adapter initialized: {adapter.config.url}")

                # Authenticate
                self.log("INFO", "Attempting authentication...")
                if not await adapter.authenticate():
                    raise Exception("Authentication failed")

                self.log("SUCCESS", "Authentication successful!")

                # Get default categories if not provided
                if not categories:
                    categories = await adapter.get_default_categories()
                    self.log("INFO", f"Using categories: {categories[:2]}...")  # First 2

                # Fetch manuscripts
                self.log("INFO", f"Fetching manuscripts from {len(categories)} categories...")
                manuscripts = await adapter.fetch_manuscripts(
                    categories[:2]
                )  # Limit to 2 categories

                self.log("SUCCESS", f"Found {len(manuscripts)} manuscripts")

                if manuscripts:
                    # Extract details from first manuscript
                    first_ms = manuscripts[0]
                    self.log("INFO", f"Extracting details for: {first_ms.external_id}")

                    details = await adapter.extract_manuscript_details(first_ms.external_id)

                    self.log("SUCCESS", f"Extracted details:")
                    self.log("INFO", f"  Title: {details.title[:80]}...")
                    self.log("INFO", f"  Authors: {len(details.authors)}")
                    self.log("INFO", f"  Referees: {len(details.referees)}")
                    self.log("INFO", f"  Files: {len(details.files)}")

                    # Save results
                    result_data = {
                        "journal_id": journal_id,
                        "status": "success",
                        "timestamp": datetime.now().isoformat(),
                        "manuscripts_found": len(manuscripts),
                        "sample_manuscript": {
                            "id": details.external_id,
                            "title": details.title,
                            "authors_count": len(details.authors),
                            "referees_count": len(details.referees),
                            "files_count": len(details.files),
                            "authors": [
                                {"name": a.name, "email": a.email, "orcid": a.orcid}
                                for a in details.authors
                            ],
                            "referees": [
                                {
                                    "name": r.name,
                                    "email": r.email,
                                    "status": r.status.value if r.status else None,
                                }
                                for r in details.referees
                            ],
                        },
                    }

                    self.save_result(journal_id, result_data)
                    self.results[journal_id] = result_data

                else:
                    self.log("WARNING", "No manuscripts found")
                    self.results[journal_id] = {
                        "status": "success_no_data",
                        "manuscripts_found": 0,
                        "timestamp": datetime.now().isoformat(),
                    }

        except Exception as e:
            self.log("ERROR", f"{journal_id} extraction failed: {e}")
            self.results[journal_id] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def test_fs_adapter(self):
        """Test FS (Gmail-based) adapter."""
        journal_id = "FS"
        self.log("HEADER", f"\n{'='*80}\nTesting {journal_id} Extractor\n{'='*80}")

        try:
            # FS uses Gmail API, not email/password
            self.log("INFO", "FS uses Gmail API (not traditional credentials)")

            async with FSAdapter(headless=True) as adapter:
                self.log("INFO", "Adapter initialized")

                # FS doesn't have traditional authentication
                # It fetches directly from Gmail
                self.log("INFO", "Fetching manuscripts from Gmail...")

                manuscripts = await adapter.fetch_manuscripts([])

                self.log("SUCCESS", f"Found {len(manuscripts)} manuscripts")

                if manuscripts:
                    first_ms = manuscripts[0]
                    self.log("INFO", f"Extracting details for: {first_ms.external_id}")

                    details = await adapter.extract_manuscript_details(first_ms.external_id)

                    self.log("SUCCESS", f"Extracted details:")
                    self.log(
                        "INFO", f"  Title: {details.title[:80] if details.title else 'N/A'}..."
                    )
                    self.log("INFO", f"  Authors: {len(details.authors)}")

                    result_data = {
                        "journal_id": journal_id,
                        "status": "success",
                        "timestamp": datetime.now().isoformat(),
                        "manuscripts_found": len(manuscripts),
                        "sample_manuscript": {
                            "id": details.external_id,
                            "title": details.title,
                            "authors_count": len(details.authors),
                        },
                    }

                    self.save_result(journal_id, result_data)
                    self.results[journal_id] = result_data
                else:
                    self.log("WARNING", "No manuscripts found")
                    self.results[journal_id] = {
                        "status": "success_no_data",
                        "manuscripts_found": 0,
                        "timestamp": datetime.now().isoformat(),
                    }

        except Exception as e:
            self.log("ERROR", f"{journal_id} extraction failed: {e}")
            self.results[journal_id] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def test_editorial_manager_adapter(self, adapter_class, journal_id: str):
        """Test Editorial Manager-based adapter (JOTA, MAFE)."""
        self.log("HEADER", f"\n{'='*80}\nTesting {journal_id} Extractor\n{'='*80}")

        try:
            # Check credentials
            username = os.getenv(f"{journal_id}_USERNAME")
            password = os.getenv(f"{journal_id}_PASSWORD")

            if not username or not password:
                self.log("ERROR", f"Missing credentials for {journal_id}")
                self.results[journal_id] = {
                    "status": "skipped",
                    "reason": "Missing credentials",
                    "timestamp": datetime.now().isoformat(),
                }
                return

            self.log("INFO", f"Credentials found: {username}")

            async with adapter_class(headless=True) as adapter:
                self.log("INFO", f"Adapter initialized: {adapter.config.url}")

                # Authenticate
                self.log("INFO", "Attempting authentication...")
                if not await adapter.authenticate():
                    raise Exception("Authentication failed")

                self.log("SUCCESS", "Authentication successful!")

                # Fetch manuscripts
                self.log("INFO", "Fetching manuscripts...")
                categories = ["Under Review", "Awaiting Decision"]
                manuscripts = await adapter.fetch_manuscripts(categories)

                self.log("SUCCESS", f"Found {len(manuscripts)} manuscripts")

                if manuscripts:
                    first_ms = manuscripts[0]
                    self.log("INFO", f"Extracting details for: {first_ms.external_id}")

                    details = await adapter.extract_manuscript_details(first_ms.external_id)

                    self.log("SUCCESS", f"Extracted details:")
                    self.log(
                        "INFO", f"  Title: {details.title[:80] if details.title else 'N/A'}..."
                    )
                    self.log("INFO", f"  Authors: {len(details.authors)}")

                    result_data = {
                        "journal_id": journal_id,
                        "status": "success",
                        "timestamp": datetime.now().isoformat(),
                        "manuscripts_found": len(manuscripts),
                        "sample_manuscript": {
                            "id": details.external_id,
                            "title": details.title,
                            "authors_count": len(details.authors),
                        },
                    }

                    self.save_result(journal_id, result_data)
                    self.results[journal_id] = result_data
                else:
                    self.log("WARNING", "No manuscripts found")
                    self.results[journal_id] = {
                        "status": "success_no_data",
                        "manuscripts_found": 0,
                        "timestamp": datetime.now().isoformat(),
                    }

        except Exception as e:
            self.log("ERROR", f"{journal_id} extraction failed: {e}")
            self.results[journal_id] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def test_siam_adapter(self, adapter_class, journal_id: str):
        """Test SIAM-based adapter (SICON, SIFIN, NACO)."""
        self.log("HEADER", f"\n{'='*80}\nTesting {journal_id} Extractor\n{'='*80}")

        try:
            # Check credentials
            email = os.getenv(f"{journal_id}_EMAIL")
            username = os.getenv(f"{journal_id}_USERNAME")
            password = os.getenv(f"{journal_id}_PASSWORD")

            cred = email or username
            if not cred or not password:
                self.log("ERROR", f"Missing credentials for {journal_id}")
                self.results[journal_id] = {
                    "status": "skipped",
                    "reason": "Missing credentials",
                    "timestamp": datetime.now().isoformat(),
                }
                return

            self.log("INFO", f"Credentials found: {cred}")

            async with adapter_class(headless=True) as adapter:
                self.log("INFO", f"Adapter initialized: {adapter.config.url}")

                # Authenticate
                self.log("INFO", "Attempting authentication...")
                if not await adapter.authenticate():
                    raise Exception("Authentication failed")

                self.log("SUCCESS", "Authentication successful!")

                # Fetch manuscripts
                self.log("INFO", "Fetching manuscripts...")
                categories = ["Under Review", "Awaiting Decision"]
                manuscripts = await adapter.fetch_manuscripts(categories)

                self.log("SUCCESS", f"Found {len(manuscripts)} manuscripts")

                if manuscripts:
                    first_ms = manuscripts[0]
                    self.log("INFO", f"Extracting details for: {first_ms.external_id}")

                    details = await adapter.extract_manuscript_details(first_ms.external_id)

                    self.log("SUCCESS", f"Extracted details:")
                    self.log(
                        "INFO", f"  Title: {details.title[:80] if details.title else 'N/A'}..."
                    )
                    self.log("INFO", f"  Authors: {len(details.authors)}")

                    result_data = {
                        "journal_id": journal_id,
                        "status": "success",
                        "timestamp": datetime.now().isoformat(),
                        "manuscripts_found": len(manuscripts),
                        "sample_manuscript": {
                            "id": details.external_id,
                            "title": details.title,
                            "authors_count": len(details.authors),
                        },
                    }

                    self.save_result(journal_id, result_data)
                    self.results[journal_id] = result_data
                else:
                    self.log("WARNING", "No manuscripts found")
                    self.results[journal_id] = {
                        "status": "success_no_data",
                        "manuscripts_found": 0,
                        "timestamp": datetime.now().isoformat(),
                    }

        except Exception as e:
            self.log("ERROR", f"{journal_id} extraction failed: {e}")
            self.results[journal_id] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def run_all_tests(self):
        """Run all extractor tests."""
        self.log("HEADER", f"\n{'='*80}\n🧪 LIVE EXTRACTOR TESTING - ALL JOURNALS\n{'='*80}\n")

        # Test ScholarOne adapters
        await self.test_scholarone_adapter(MFAdapter, "MF")
        await self.test_scholarone_adapter(MORAdapter, "MOR")

        # Test FS (Gmail)
        await self.test_fs_adapter()

        # Test Editorial Manager adapters
        await self.test_editorial_manager_adapter(JOTAAdapter, "JOTA")
        await self.test_editorial_manager_adapter(MAFEAdapter, "MAFE")

        # Test SIAM adapters
        await self.test_siam_adapter(SICONAdapter, "SICON")
        await self.test_siam_adapter(SIFINAdapter, "SIFIN")
        await self.test_siam_adapter(NACOAdapter, "NACO")

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        duration = (datetime.now() - self.start_time).total_seconds()

        self.log("HEADER", f"\n{'='*80}\n📊 TEST SUMMARY\n{'='*80}")

        success = [
            j for j, r in self.results.items() if r.get("status") in ["success", "success_no_data"]
        ]
        failed = [j for j, r in self.results.items() if r["status"] == "failed"]
        skipped = [j for j, r in self.results.items() if r["status"] == "skipped"]

        self.log("SUCCESS", f"✅ Passed:  {len(success)}/8")
        if success:
            for j in success:
                ms_count = self.results[j].get("manuscripts_found", 0)
                self.log("INFO", f"   {j}: {ms_count} manuscripts")

        self.log("ERROR", f"❌ Failed:  {len(failed)}/8")
        if failed:
            for j in failed:
                error = self.results[j].get("error", "Unknown error")
                self.log("INFO", f"   {j}: {error}")

        self.log("WARNING", f"⏭️  Skipped: {len(skipped)}/8")
        if skipped:
            for j in skipped:
                reason = self.results[j].get("reason", "Unknown")
                self.log("INFO", f"   {j}: {reason}")

        self.log("INFO", f"\n⏱️  Duration: {duration:.1f}s")
        self.log("INFO", f"📁 Output: {self.output_dir}")
        self.log("HEADER", f"{'='*80}\n")

        # Save summary
        summary_file = self.output_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, "w") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "duration_seconds": duration,
                    "results": self.results,
                    "summary": {
                        "total": 8,
                        "success": len(success),
                        "failed": len(failed),
                        "skipped": len(skipped),
                    },
                },
                f,
                indent=2,
                default=str,
            )

        self.log("INFO", f"Summary saved to: {summary_file}")


async def main():
    """Main entry point."""
    tester = ExtractorTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
