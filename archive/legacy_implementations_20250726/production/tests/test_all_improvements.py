#!/usr/bin/env python3
"""
Test ALL improvements:
1. Deep country search for all referees
2. Email-based affiliation inference when missing
3. Abstract saving to disk
4. Processing ALL manuscripts (not just first)
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import json

def test_all_improvements():
    extractor = ComprehensiveMFExtractor()
    
    print("🚀 TESTING ALL IMPROVEMENTS")
    print("="*80)
    
    try:
        # Run the actual extract_all method which processes ALL manuscripts
        extractor.extract_all()
        
        print("\n" + "="*80)
        print("📊 COMPLETE EXTRACTION RESULTS - ALL IMPROVEMENTS")
        print("="*80)
        
        # Show results for ALL manuscripts
        print(f"\n📋 TOTAL MANUSCRIPTS PROCESSED: {len(extractor.manuscripts)}")
        
        for i, manuscript in enumerate(extractor.manuscripts, 1):
            print(f"\n{'='*60}")
            print(f"📄 MANUSCRIPT {i}: {manuscript.get('id', 'Unknown')}")
            print(f"{'='*60}")
            
            # Basic info
            print(f"📚 Title: {manuscript.get('title', 'Not found')}")
            print(f"👤 Authors: {', '.join(manuscript.get('authors', []))}")
            print(f"📅 Submitted: {manuscript.get('submission_date', 'Not found')}")
            print(f"📊 Status: {manuscript.get('status', 'Not found')}")
            
            # Documents
            docs = manuscript.get('documents', {})
            print(f"\n📂 DOCUMENTS:")
            print(f"   📄 PDF: {'✅' if docs.get('pdf') else '❌'}")
            print(f"   📋 Cover Letter: {'✅' if docs.get('cover_letter') else '❌'}")
            if docs.get('cover_letter_path'):
                path = Path(docs['cover_letter_path'])
                if path.exists():
                    print(f"      Extension: {path.suffix}")
            
            # Abstract
            print(f"   📝 Abstract: {'✅' if docs.get('abstract') else '❌'}")
            if manuscript.get('abstract_path'):
                abstract_path = Path(manuscript['abstract_path'])
                if abstract_path.exists():
                    print(f"      💾 Saved to: {abstract_path}")
                    print(f"      Size: {abstract_path.stat().st_size} bytes")
            
            # Referees with all improvements
            referees = manuscript.get('referees', [])
            print(f"\n👥 REFEREES: {len(referees)}")
            
            for j, referee in enumerate(referees, 1):
                print(f"\n   🔸 Referee {j}: {referee['name']}")
                print(f"      📧 Email: {referee['email']}")
                
                # Check affiliation source
                affiliation = referee.get('affiliation', '')
                if affiliation:
                    print(f"      🏢 Affiliation: {affiliation}")
                    # Check if it was inferred from email
                    if '@' in referee['email']:
                        domain = referee['email'].split('@')[1]
                        if domain in affiliation.lower():
                            print(f"         ℹ️  (Likely inferred from email domain)")
                else:
                    print(f"      🏢 Affiliation: ❌ Not found")
                
                # Country with deep search
                country = referee.get('country', '')
                if country:
                    print(f"      🌍 Country: {country} ✅")
                else:
                    print(f"      🌍 Country: ❌ Not found (deep search may have failed)")
                
                print(f"      📊 Status: {referee.get('status', 'Not found')}")
                print(f"      🆔 ORCID: {referee.get('orcid', 'Not found')}")
                
                # Dates
                dates = referee.get('dates', {})
                if dates:
                    print(f"      📅 Dates:")
                    for date_type, date_val in dates.items():
                        print(f"         - {date_type}: {date_val}")
        
        # Check saved files
        print(f"\n📁 SAVED FILES CHECK:")
        print("="*60)
        
        # Check abstracts
        abstract_dir = Path("downloads/abstracts")
        if abstract_dir.exists():
            abstract_files = list(abstract_dir.glob("*_abstract.txt"))
            print(f"📝 Abstracts saved: {len(abstract_files)}")
            for f in abstract_files:
                print(f"   - {f.name} ({f.stat().st_size} bytes)")
        else:
            print("📝 No abstract directory found")
        
        # Check cover letters
        cover_files = list(Path("downloads").glob("*_cover_letter.*"))
        print(f"\n📋 Cover letters saved: {len(cover_files)}")
        for f in cover_files:
            print(f"   - {f.name} (Extension: {f.suffix}, Size: {f.stat().st_size} bytes)")
        
        # Save complete JSON for verification
        output_path = Path("extraction_results_complete.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extractor.manuscripts, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Complete results saved to: {output_path}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n⏸️ Closing browser...")
        extractor.driver.quit()

if __name__ == "__main__":
    test_all_improvements()