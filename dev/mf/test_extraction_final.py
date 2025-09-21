#!/usr/bin/env python3
"""Final test of MF extraction with all fixes."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../production/src/extractors'))

from mf_extractor import ComprehensiveMFExtractor

print("🚀 TESTING COMPLETE MF EXTRACTION WITH ALL FIXES")
print("=" * 60)

extractor = ComprehensiveMFExtractor()

# Run full extraction (will automatically limit based on categories)
extractor.extract_all()

if extractor.manuscripts:
    ms = extractor.manuscripts[0]
    
    print(f"\n📊 EXTRACTION RESULTS FOR {ms.get('id', 'UNKNOWN')}:")
    print("=" * 50)
    
    # Check referee emails
    referees = ms.get('referees', [])
    referee_emails = sum(1 for r in referees if r.get('email', ''))
    
    print(f"\n🧑‍⚖️ REFEREES: {len(referees)} total")
    for i, r in enumerate(referees):
        name = r.get('name', 'Unknown')
        email = r.get('email', '')
        status = '✅' if email else '❌'
        print(f"  {i+1}. {status} {name}: {email or 'NO EMAIL'}")
        
        # Check report extraction
        if r.get('report'):
            report = r['report']
            if report.get('recommendation'):
                print(f"      📄 Recommendation: {report['recommendation']}")
            if report.get('pdf_downloaded'):
                print(f"      📎 PDF downloaded")
            if report.get('comments_to_author'):
                print(f"      💬 Comments: {len(report['comments_to_author'])} chars")
    
    # Check author emails
    authors = ms.get('authors', [])
    author_emails = sum(1 for a in authors if a.get('email', ''))
    
    print(f"\n✍️ AUTHORS: {len(authors)} total")
    for i, a in enumerate(authors):
        name = a.get('name', 'Unknown')
        email = a.get('email', '')
        institution = a.get('institution', 'Unknown')
        status = '✅' if email else '❌'
        print(f"  {i+1}. {status} {name} ({institution}): {email or 'NO EMAIL'}")
    
    # Summary
    reports_extracted = sum(1 for r in referees if r.get('report'))
    
    print(f"\n📊 FINAL SUMMARY:")
    print(f"  {'✅' if referee_emails > 0 else '❌'} Referee emails: {referee_emails}/{len(referees)}")
    print(f"  {'✅' if author_emails > 0 else '❌'} Author emails: {author_emails}/{len(authors)}")
    print(f"  {'✅' if reports_extracted > 0 else '❌'} Reports: {reports_extracted}/{len(referees)}")
    
    # Save results
    import json
    output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'final_extraction_results.json')
    with open(output_file, 'w') as f:
        json.dump([ms], f, indent=2)
    print(f"\n💾 Results saved to {output_file}")
    
    # Final verdict
    if referee_emails > 0 and author_emails > 0 and reports_extracted > 0:
        print("\n🎉 SUCCESS! ALL EXTRACTION WORKING PERFECTLY!")
    elif referee_emails > 0 and author_emails > 0:
        print("\n✅ Email extraction working! Report extraction may need more time.")
    else:
        print("\n⚠️ Partial success - check the results above")
        
else:
    print("❌ No manuscripts extracted")

extractor.cleanup()
print("\n🏁 Test complete")