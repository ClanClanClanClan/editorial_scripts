#!/usr/bin/env python3
"""
Real SIFIN extraction test - verify we get ALL data
"""

import json
from datetime import datetime
from pathlib import Path
import sys

def test_sifin_real_extraction():
    """Run SIFIN extraction and verify we get ALL data"""
    
    print("=" * 80)
    print("SIFIN REAL EXTRACTION TEST")
    print("=" * 80)
    print("This will test if SIFIN extraction gets:")
    print("1. ALL manuscripts")
    print("2. ALL referee data (names, emails, statuses)")
    print("3. ALL PDFs")
    print("=" * 80)
    
    try:
        from journals.sifin import SIFIN
        
        print("\nInitializing SIFIN extractor...")
        sifin = SIFIN()
        
        # Run in non-headless mode for debugging
        print("Setting up WebDriver in visible mode for debugging...")
        sifin.setup_driver(headless=False)
        
        print("\nRunning SIFIN extraction...")
        print("This will authenticate with ORCID and extract all data")
        
        # Set up output directory
        output_dir = Path(f'sifin_real_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        output_dir.mkdir(exist_ok=True)
        
        # Run extraction
        try:
            results = sifin.extract()
            
            # Save raw results
            with open(output_dir / 'raw_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            
            print(f"\n{'='*60}")
            print("EXTRACTION RESULTS")
            print(f"{'='*60}")
            
            print(f"\nStatus: {results.get('status', 'unknown')}")
            print(f"Total manuscripts found: {len(results.get('manuscripts', []))}")
            
            # Analyze each manuscript
            total_referees = 0
            referees_with_emails = 0
            referee_statuses = {}
            pdfs_found = 0
            
            print("\nDETAILED MANUSCRIPT BREAKDOWN:")
            print("-" * 60)
            
            for i, ms in enumerate(results.get('manuscripts', [])):
                print(f"\nManuscript #{i+1}:")
                print(f"  ID: {ms.get('id', 'NO ID')}")
                print(f"  Title: {ms.get('title', 'NO TITLE')[:60]}...")
                print(f"  Status: {ms.get('status', 'NO STATUS')}")
                print(f"  Submitted: {ms.get('submitted', 'NO DATE')}")
                print(f"  Corresponding Editor: {ms.get('corresponding_editor', 'NO CE')}")
                print(f"  Associate Editor: {ms.get('associate_editor', 'NO AE')}")
                
                # Check PDF
                if ms.get('documents', {}).get('pdf'):
                    print(f"  PDF: ✅ Downloaded")
                    pdfs_found += 1
                else:
                    print(f"  PDF: ❌ NOT FOUND")
                
                # Analyze referees
                referees = ms.get('referees', [])
                print(f"\n  Referees ({len(referees)} total):")
                
                for ref in referees:
                    name = ref.get('name', 'NO NAME')
                    email = ref.get('email', '')
                    status = ref.get('status', 'Unknown')
                    
                    total_referees += 1
                    if email:
                        referees_with_emails += 1
                    
                    referee_statuses[status] = referee_statuses.get(status, 0) + 1
                    
                    email_status = "✅" if email else "❌"
                    print(f"    - {name}")
                    print(f"      Email: {email_status} {email if email else 'NO EMAIL'}")
                    print(f"      Status: {status}")
                    
                    if status == 'Accepted' and ref.get('due_date'):
                        print(f"      Due: {ref['due_date']}")
                
                # Check for referee reports
                reports = ms.get('documents', {}).get('referee_reports', [])
                if reports:
                    print(f"\n  Referee Reports: {len(reports)} found")
                    for report in reports:
                        print(f"    - {report}")
            
            # Summary statistics
            print(f"\n{'='*60}")
            print("EXTRACTION SUMMARY")
            print(f"{'='*60}")
            
            print(f"\nManuscripts:")
            print(f"  Total: {len(results.get('manuscripts', []))}")
            print(f"  With PDFs: {pdfs_found}")
            print(f"  Missing PDFs: {len(results.get('manuscripts', [])) - pdfs_found}")
            
            print(f"\nReferees:")
            print(f"  Total: {total_referees}")
            print(f"  With emails: {referees_with_emails}")
            print(f"  Missing emails: {total_referees - referees_with_emails}")
            
            print(f"\nReferee Status Breakdown:")
            for status, count in sorted(referee_statuses.items()):
                print(f"  {status}: {count}")
            
            # Check for Unknown statuses
            unknown_count = referee_statuses.get('Unknown', 0)
            if unknown_count > 0:
                print(f"\n⚠️  WARNING: {unknown_count} referees have Unknown status!")
            else:
                print(f"\n✅ SUCCESS: All referees have clear status (no Unknown)!")
            
            # Email percentage
            if total_referees > 0:
                email_percentage = (referees_with_emails / total_referees) * 100
                print(f"\nEmail extraction rate: {email_percentage:.1f}%")
            
            # PDF percentage
            if len(results.get('manuscripts', [])) > 0:
                pdf_percentage = (pdfs_found / len(results['manuscripts'])) * 100
                print(f"PDF download rate: {pdf_percentage:.1f}%")
            
            # Save summary
            summary = {
                'extraction_time': datetime.now().isoformat(),
                'manuscripts_found': len(results.get('manuscripts', [])),
                'total_referees': total_referees,
                'referees_with_emails': referees_with_emails,
                'referee_statuses': referee_statuses,
                'pdfs_found': pdfs_found,
                'unknown_statuses': unknown_count
            }
            
            with open(output_dir / 'extraction_summary.json', 'w') as f:
                json.dump(summary, f, indent=2)
            
            # Generate report
            report = sifin.generate_report()
            with open(output_dir / 'extraction_report.txt', 'w') as f:
                f.write(report)
            
            print(f"\n📁 All results saved to: {output_dir}/")
            
            # Final verdict
            print(f"\n{'='*60}")
            print("FINAL VERDICT")
            print(f"{'='*60}")
            
            all_good = True
            
            if len(results.get('manuscripts', [])) == 0:
                print("❌ NO MANUSCRIPTS FOUND")
                all_good = False
            else:
                print(f"✅ Found {len(results['manuscripts'])} manuscripts")
            
            if total_referees == 0:
                print("❌ NO REFEREES FOUND")
                all_good = False
            elif referees_with_emails < total_referees:
                print(f"⚠️  Missing emails for {total_referees - referees_with_emails} referees")
                all_good = False
            else:
                print("✅ All referees have emails")
            
            if unknown_count > 0:
                print(f"❌ {unknown_count} referees have Unknown status")
                all_good = False
            else:
                print("✅ All referees have clear status")
            
            if pdfs_found < len(results.get('manuscripts', [])):
                print(f"⚠️  Missing PDFs for {len(results['manuscripts']) - pdfs_found} manuscripts")
                all_good = False
            else:
                print("✅ All manuscripts have PDFs")
            
            if all_good:
                print("\n🎉 SIFIN EXTRACTION IS WORKING PERFECTLY!")
                print("   - Getting ALL manuscripts")
                print("   - Getting ALL referee data")
                print("   - Getting ALL PDFs")
            else:
                print("\n⚠️  SIFIN extraction needs attention - see issues above")
            
        except Exception as e:
            print(f"\n❌ EXTRACTION FAILED: {e}")
            import traceback
            traceback.print_exc()
            
            # Save error info
            with open(output_dir / 'error.txt', 'w') as f:
                f.write(f"Error: {e}\n\n")
                import traceback
                traceback.print_exc(file=f)
            
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_sifin_real_extraction()