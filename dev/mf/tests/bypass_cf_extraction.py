#!/usr/bin/env python3
"""Production MF extraction bypassing Cloudflare challenge."""

import os
import sys
import time
import json
import signal
from datetime import datetime

# Force disable test mode completely
os.environ['EXTRACTOR_TEST_MODE'] = 'false'
os.environ['EXTRACTOR_BYPASS_CACHE'] = 'true'

def timeout_handler(signum, frame):
    print('\n⏰ TIMEOUT - Extraction took too long')
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(600)  # 10 minute timeout

print('🚀 PRODUCTION MF EXTRACTION - BYPASSING CLOUDFLARE')
print('=' * 70)
print(f'Started at: {datetime.now().strftime("%H:%M:%S")}')
print()

try:
    # Import production extractor
    from mf_extractor import ComprehensiveMFExtractor
    
    print('✅ Production extractor imported successfully')
    
    # Create extractor instance  
    extractor = ComprehensiveMFExtractor()
    print('✅ Extractor instance created')
    
    # Force production mode
    if hasattr(extractor, '_test_mode'):
        extractor._test_mode = False
    if hasattr(extractor, 'test_mode'):
        extractor.test_mode = False
        
    print('✅ Production mode enforced')
    
    # Run complete extraction
    print('\n📄 Starting complete extraction on ALL manuscripts...')
    extractor.extract_all()
    
    # Check results
    if extractor.manuscripts:
        print(f'\n📊 COMPLETE EXTRACTION RESULTS:')
        print('=' * 70)
        print(f'TOTAL MANUSCRIPTS EXTRACTED: {len(extractor.manuscripts)}')
        
        total_referees = 0
        total_referee_emails = 0
        total_authors = 0
        total_author_emails = 0
        
        for i, ms in enumerate(extractor.manuscripts):
            manuscript_id = ms.get('id', 'NO_ID')
            
            print(f'\n📄 MANUSCRIPT {i+1}: {manuscript_id}')
            print(f'📝 Title: {ms.get("title", "N/A")}')
            print(f'📊 Status: {ms.get("status", "N/A")}')
            
            # Referees
            referees = ms.get('referees', [])
            referee_emails = sum(1 for r in referees if r.get('email'))
            total_referees += len(referees)
            total_referee_emails += referee_emails
            
            print(f'\n🧑‍⚖️ REFEREES ({len(referees)} total, {referee_emails} with emails):')
            for j, r in enumerate(referees):
                name = r.get('name', 'Unknown')
                email = r.get('email', '')
                status = '✅' if email else '❌'
                print(f'  {j+1}. {status} {name}: {email or "NO EMAIL"}')
            
            # Authors
            authors = ms.get('authors', [])
            author_emails = sum(1 for a in authors if a.get('email'))
            total_authors += len(authors)
            total_author_emails += author_emails
            
            print(f'\n✍️ AUTHORS ({len(authors)} total, {author_emails} with emails):')
            for j, a in enumerate(authors):
                name = a.get('name', 'Unknown')
                email = a.get('email', '')
                status = '✅' if email else '❌'
                print(f'  {j+1}. {status} {name}: {email or "NO EMAIL"}')
        
        # Overall summary
        print(f'\n📊 OVERALL SUMMARY:')
        print('=' * 50)
        print(f'📄 Total manuscripts: {len(extractor.manuscripts)}')
        print(f'🧑‍⚖️ Total referees: {total_referees}')
        print(f'📧 Referee emails: {total_referee_emails}/{total_referees} ({100*total_referee_emails/total_referees if total_referees > 0 else 0:.1f}%)')
        print(f'✍️ Total authors: {total_authors}')
        print(f'📧 Author emails: {total_author_emails}/{total_authors} ({100*total_author_emails/total_authors if total_authors > 0 else 0:.1f}%)')
        print(f'📧 TOTAL EMAILS: {total_referee_emails + total_author_emails}')
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'mf_production_complete_{timestamp}.json'
        with open(filename, 'w') as f:
            json.dump(extractor.manuscripts, f, indent=2, default=str)
        print(f'\n💾 Results saved to: {filename}')
        
        if total_referee_emails > 0:
            print('\n🎉 SUCCESS: REFEREE EMAIL EXTRACTION WORKING!')
        else:
            print('\n❌ NO REFEREE EMAILS EXTRACTED')
    else:
        print('❌ NO MANUSCRIPTS EXTRACTED')
        
except Exception as e:
    print(f'❌ ERROR: {e}')
    import traceback
    traceback.print_exc()
finally:
    signal.alarm(0)
    print(f'\nExtraction completed at: {datetime.now().strftime("%H:%M:%S")}')