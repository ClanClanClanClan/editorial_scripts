#!/usr/bin/env python3
"""
Single MOR extraction test - Ultrathink version
"""
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Import the MOR extractor
from mor_extractor import MORExtractor

def main():
    print("\n" + "="*60)
    print("🚀 MOR SINGLE EXTRACTION TEST - ULTRATHINK")
    print("="*60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load credentials
    import subprocess
    result = subprocess.run(['bash', '-c', 'source ~/.editorial_scripts/load_all_credentials.sh && echo "OK"'],
                          capture_output=True, text=True)
    if "OK" in result.stdout:
        print("✅ Credentials loaded")

    # Initialize extractor
    extractor = MORExtractor()

    try:
        print("\n📌 Running MOR extractor...")
        # Run the full extraction (this includes browser setup, login, navigation, extraction)
        results = extractor.run()

        print(f"\n📊 EXTRACTION RESULTS:")
        print(f"Timestamp: {results.get('extraction_timestamp', 'N/A')}")
        print(f"Journal: {results.get('journal', 'N/A')}")
        print(f"Version: {results.get('extractor_version', 'N/A')}")
        print(f"Manuscripts found: {len(results.get('manuscripts', []))}")
        print(f"Errors: {len(results.get('errors', []))}")

        if results.get('manuscripts'):
            print(f"\n🔍 FIRST MANUSCRIPT DETAILS:")
            manuscript = results['manuscripts'][0]
            print(f"  • ID: {manuscript.get('id', 'N/A')}")
            print(f"  • Title: {manuscript.get('title', 'N/A')[:100]}...")
            print(f"  • Authors: {manuscript.get('authors', 'N/A')}")
            print(f"  • Referees: {len(manuscript.get('referees', []))}")

            if manuscript.get('referees'):
                print(f"\n  📋 REFEREE DETAILS:")
                for i, referee in enumerate(manuscript['referees'][:3], 1):  # Show first 3
                    print(f"    {i}. {referee.get('name', 'N/A')} - {referee.get('status', 'N/A')}")
                    if referee.get('institution'):
                        print(f"       Institution: {referee['institution']}")
                    if referee.get('orcid'):
                        verified = "✓" if referee.get('orcid_verified') else "✗"
                        print(f"       ORCID: {referee['orcid']} [{verified}]")

        if results.get('errors'):
            print(f"\n⚠️ ERRORS:")
            for error in results['errors'][:5]:  # Show first 5
                print(f"  • {error}")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = Path(__file__).parent / "results"
        results_dir.mkdir(exist_ok=True)

        results_file = results_dir / f"mor_single_test_{timestamp}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Results saved to: {results_file}")

        print("\n" + "="*60)
        print("📊 TEST SUMMARY:")
        print(f"  • Status: {'✅ SUCCESS' if results.get('manuscripts') else '⚠️ NO DATA'}")
        print(f"  • Manuscripts: {len(results.get('manuscripts', []))}")
        total_referees = sum(len(m.get('referees', [])) for m in results.get('manuscripts', []))
        print(f"  • Total referees: {total_referees}")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()