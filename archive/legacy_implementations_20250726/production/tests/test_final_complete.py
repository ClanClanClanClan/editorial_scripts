#!/usr/bin/env python3
"""
Final complete test with all improvements including fixed tab navigation
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import json
from datetime import datetime

def test_final_complete():
    print("🚀 FINAL COMPLETE MF EXTRACTION TEST")
    print("="*70)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 Testing all improvements:")
    print("   ✓ Deep online search for referee countries")
    print("   ✓ Email-based affiliation inference")
    print("   ✓ Abstract saving to disk")
    print("   ✓ Processing ALL manuscripts")
    print("   ✓ Fixed tab navigation with JavaScript clicks")
    print("="*70)
    
    extractor = ComprehensiveMFExtractor()
    all_results = []
    
    try:
        login_success = extractor.login()
        if not login_success:
            print("❌ Login failed!")
            return
        
        print("\n✅ Login successful!")
        
        # Extract all manuscripts
        results = extractor.extract_all()
        if not results:
            print("❌ No manuscripts found!")
            return
        
        print(f"\n📚 Processed {len(results)} manuscripts")
        all_results = results
        
        # Print summary for each manuscript
        for idx, result in enumerate(all_results):
            print(f"\n{'='*70}")
            print(f"📄 MANUSCRIPT {idx+1}/{len(all_results)}: {result['id']}")
            print(f"{'='*70}")
            
            # Print summary
            print(f"\n📊 Summary for {result['id']}:")
            print(f"   • Title: {result.get('title', 'N/A')[:60]}...")
            print(f"   • Referees: {len(result.get('referees', []))}")
            print(f"   • Documents: PDF={result['documents'].get('pdf', False)}, " +
                  f"Cover Letter={result['documents'].get('cover_letter', False)}, " +
                  f"Abstract={result['documents'].get('abstract', False)}")
            
            # Check referee data quality
            for ref in result.get('referees', []):
                print(f"\n   👤 {ref['name']}:")
                print(f"      • Email: {ref.get('email', 'N/A')}")
                print(f"      • Affiliation: {ref.get('affiliation', 'N/A')}")
                print(f"      • Country: {ref.get('country', 'N/A')}")
                print(f"      • Status: {ref.get('status', 'N/A')}")
                print(f"      • ORCID: {ref.get('orcid', 'N/A')}")
                
                # Check dates
                dates = ref.get('dates', {})
                if dates:
                    date_info = []
                    for key, value in dates.items():
                        if value:
                            date_info.append(f"{key}={value}")
                    if date_info:
                        print(f"      • Dates: {', '.join(date_info)}")
                
                # Check review links
                if ref.get('review_links'):
                    print(f"      • Review links: {len(ref['review_links'])} found")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f'mf_final_complete_{timestamp}.json'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n\n✅ EXTRACTION COMPLETE!")
        print(f"📁 Results saved to: {output_file}")
        
        # Final statistics
        total_referees = sum(len(r.get('referees', [])) for r in all_results)
        referees_with_country = sum(1 for r in all_results 
                                   for ref in r.get('referees', []) 
                                   if ref.get('country'))
        referees_with_inferred_affiliation = sum(1 for r in all_results 
                                                for ref in r.get('referees', []) 
                                                if ref.get('affiliation') and '@' in ref.get('email', ''))
        
        print(f"\n📊 FINAL STATISTICS:")
        print(f"   • Total manuscripts: {len(all_results)}")
        print(f"   • Total referees: {total_referees}")
        print(f"   • Referees with country data: {referees_with_country}")
        print(f"   • Possible email-inferred affiliations: {referees_with_inferred_affiliation}")
        
        # Check abstract files
        abstract_files = list(Path('downloads/abstracts').glob('*.txt'))
        print(f"   • Abstract files saved: {len(abstract_files)}")
        
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        extractor.driver.quit()

if __name__ == "__main__":
    test_final_complete()