#!/usr/bin/env python3
"""
Test SIFIN extraction pipeline with all production features
"""

import json
from datetime import datetime
from pathlib import Path


def test_sifin_extraction():
    """Test SIFIN extraction with all features"""
    
    print("=" * 80)
    print("SIFIN Full Extraction Pipeline Test")
    print("=" * 80)
    
    try:
        from journals.sifin import SIFIN
        
        print("\n1. Initializing SIFIN extractor...")
        sifin = SIFIN()
        print("✅ SIFIN initialized with enhanced features")
        
        print("\n2. Testing extraction capabilities...")
        print("Note: This will attempt to connect to SIFIN and extract data")
        print("Make sure you have:")
        print("- ORCID credentials set in environment or credential manager")
        print("- Internet connection")
        print("- Chrome/Chromium installed")
        
        # Check for credentials
        import os
        has_creds = (
            os.getenv('ORCID_USER') or os.getenv('ORCID_USERNAME')
        ) and (
            os.getenv('ORCID_PASS') or os.getenv('ORCID_PASSWORD')
        )
        
        if not has_creds:
            print("\n⚠️  No ORCID credentials found in environment")
            print("Set ORCID_USER and ORCID_PASS environment variables")
            return
        
        print("\n3. Running SIFIN extraction...")
        print("This will:")
        print("- Authenticate with ORCID")
        print("- Navigate to SIFIN dashboard")
        print("- Extract manuscripts")
        print("- Extract referee details")
        print("- Detect changes")
        print("- Generate reports")
        
        try:
            # Run extraction
            results = sifin.extract()
            
            print("\n✅ Extraction completed successfully!")
            
            # Print summary
            print(f"\nResults Summary:")
            print(f"- Journal: {results['journal']}")
            print(f"- Status: {results['status']}")
            print(f"- Manuscripts found: {len(results['manuscripts'])}")
            print(f"- Extraction time: {results['extraction_time']}")
            
            # Print manuscript details
            if results['manuscripts']:
                print("\nManuscripts extracted:")
                for ms in results['manuscripts']:
                    print(f"\n  {ms['id']}: {ms['title'][:50]}...")
                    print(f"    Status: {ms.get('status', 'N/A')}")
                    print(f"    Submitted: {ms.get('submitted', 'N/A')}")
                    print(f"    Referees: {len(ms.get('referees', []))}")
                    
                    # Show referee summary
                    by_status = {}
                    for ref in ms.get('referees', []):
                        status = ref.get('status', 'Unknown')
                        by_status[status] = by_status.get(status, 0) + 1
                    
                    for status, count in by_status.items():
                        print(f"      - {status}: {count}")
            
            # Print changes detected
            if results.get('changes'):
                print("\nChanges detected:")
                changes = results['changes']
                for change_type, items in changes.items():
                    if items:
                        print(f"  - {change_type}: {len(items)}")
            
            # Save results
            output_file = Path(f'sifin_test_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\nFull results saved to: {output_file}")
            
            # Generate report
            if hasattr(sifin, 'generate_report'):
                report = sifin.generate_report()
                report_file = Path(f'sifin_test_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
                with open(report_file, 'w') as f:
                    f.write(report)
                print(f"Report saved to: {report_file}")
            
        except Exception as e:
            print(f"\n❌ Extraction failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    test_sifin_extraction()