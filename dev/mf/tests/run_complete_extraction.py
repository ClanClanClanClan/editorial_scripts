#!/usr/bin/env python3
"""Complete extraction of ALL manuscripts with working email extraction."""

from mf_extractor import ComprehensiveMFExtractor
import json
from datetime import datetime

print('🚀 COMPLETE MF EXTRACTION - ALL MANUSCRIPTS')
print('=' * 70)
print(f'Started at: {datetime.now().strftime("%H:%M:%S")}')
print()

extractor = ComprehensiveMFExtractor()
try:
    # Run full extraction on all manuscripts
    extractor.extract_all()
    
    if extractor.manuscripts:
        print(f'\n📊 COMPLETE EXTRACTION RESULTS:')
        print('=' * 70)
        print(f'TOTAL MANUSCRIPTS EXTRACTED: {len(extractor.manuscripts)}')
        print()
        
        for i, ms in enumerate(extractor.manuscripts):
            manuscript_id = ms.get('id', 'NO_ID')
            
            print('\n' + '='*70)
            print(f'📄 MANUSCRIPT {i+1}: {manuscript_id}')
            print('='*70)
            
            # Basic info
            print(f'📝 Title: {ms.get("title", "N/A")}')
            print(f'📊 Status: {ms.get("status", "N/A")}')
            print(f'📅 Submission Date: {ms.get("submission_date", "N/A")}')
            print(f'⏱️ In Review Time: {ms.get("in_review_time", "N/A")}')
            print(f'📃 Article Type: {ms.get("article_type", "N/A")}')
            
            # Keywords
            keywords = ms.get('keywords', [])
            if keywords:
                print(f'🏷️ Keywords: {", ".join(keywords)}')
            
            # Referees with emails
            referees = ms.get('referees', [])
            print(f'\n🧑‍⚖️ REFEREES ({len(referees)} total):')
            referee_emails = 0
            for j, r in enumerate(referees):
                name = r.get('name', 'Unknown')
                email = r.get('email', '')
                affiliation = r.get('affiliation', 'N/A')
                status = r.get('status', 'N/A')
                
                if email:
                    referee_emails += 1
                    
                print(f'  {j+1}. {name}')
                print(f'     📧 Email: {email if email else "❌ NOT EXTRACTED"}')
                print(f'     🏛️ Affiliation: {affiliation}')
                print(f'     📊 Status: {status}')
                
                # Check dates
                dates = r.get('dates', {})
                if dates:
                    invited = dates.get('invited', 'N/A')
                    agreed = dates.get('agreed', 'N/A')
                    due = dates.get('due', 'N/A')
                    print(f'     📅 Invited: {invited}, Agreed: {agreed}, Due: {due}')
            
            print(f'  >>> Referee emails extracted: {referee_emails}/{len(referees)}')
            
            # Authors with emails
            authors = ms.get('authors', [])
            print(f'\n✍️ AUTHORS ({len(authors)} total):')
            author_emails = 0
            for j, a in enumerate(authors):
                name = a.get('name', 'Unknown')
                email = a.get('email', '')
                institution = a.get('institution', 'N/A')
                
                if email:
                    author_emails += 1
                    
                print(f'  {j+1}. {name}')
                print(f'     📧 Email: {email if email else "❌ NOT EXTRACTED"}')
                print(f'     🏛️ Institution: {institution}')
            
            print(f'  >>> Author emails extracted: {author_emails}/{len(authors)}')
            
            # Documents
            documents = ms.get('documents', {})
            if documents:
                print(f'\n📂 DOCUMENTS:')
                if documents.get('pdf'):
                    print(f'  ✅ PDF available')
                if documents.get('html'):
                    print(f'  ✅ HTML available')
                if documents.get('cover_letter'):
                    print(f'  ✅ Cover letter available')
                supplementary = documents.get('supplementary_files', [])
                if supplementary:
                    print(f'  📎 Supplementary files: {len(supplementary)}')
            
            # Abstract preview
            abstract = ms.get('abstract', '')
            if abstract:
                print(f'\n📖 ABSTRACT (first 200 chars):')
                print(f'  {abstract[:200]}...')
            
            # Funding and other info
            funding = ms.get('funding_information', 'N/A')
            if funding and funding != 'N/A':
                print(f'\n💰 Funding: {funding}')
            
            conflict = ms.get('conflict_of_interest', 'N/A')
            if conflict and conflict != 'N/A':
                print(f'⚠️ Conflict of Interest: {conflict}')
        
        # Overall summary
        print('\n' + '='*70)
        print(f'📊 OVERALL EXTRACTION SUMMARY:')
        print('='*70)
        
        total_referees = sum(len(ms.get('referees', [])) for ms in extractor.manuscripts)
        total_referee_emails = sum(sum(1 for r in ms.get('referees', []) if r.get('email')) for ms in extractor.manuscripts)
        total_authors = sum(len(ms.get('authors', [])) for ms in extractor.manuscripts)
        total_author_emails = sum(sum(1 for a in ms.get('authors', []) if a.get('email')) for ms in extractor.manuscripts)
        
        print(f'📄 Total manuscripts: {len(extractor.manuscripts)}')
        print(f'🧑‍⚖️ Total referees: {total_referees}')
        print(f'📧 Referee emails extracted: {total_referee_emails}/{total_referees} ({100*total_referee_emails/total_referees if total_referees > 0 else 0:.1f}%)')
        print(f'✍️ Total authors: {total_authors}')
        print(f'📧 Author emails extracted: {total_author_emails}/{total_authors} ({100*total_author_emails/total_authors if total_authors > 0 else 0:.1f}%)')
        print(f'📧 TOTAL EMAILS EXTRACTED: {total_referee_emails + total_author_emails}')
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'mf_complete_fixed_{timestamp}.json'
        with open(filename, 'w') as f:
            json.dump(extractor.manuscripts, f, indent=2, default=str)
        print(f'\n💾 Complete data saved to: {filename}')
        
        print(f'\nExtraction completed at: {datetime.now().strftime("%H:%M:%S")}')
        
        if total_referee_emails > 0:
            print('\n🎉 SUCCESS: REFEREE EMAIL EXTRACTION IS WORKING!')
        else:
            print('\n❌ WARNING: NO REFEREE EMAILS EXTRACTED')
    else:
        print('❌ NO MANUSCRIPTS EXTRACTED')
    
except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    try:
        extractor.cleanup()
    except:
        pass