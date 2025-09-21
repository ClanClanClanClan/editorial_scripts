#!/usr/bin/env python3
"""Test MF extractor on ALL manuscripts in ALL categories."""

from mf_extractor import ComprehensiveMFExtractor
import json
from datetime import datetime

print('🚀 MF EXTRACTOR - TESTING ALL MANUSCRIPTS IN ALL CATEGORIES')
print('=' * 70)

extractor = ComprehensiveMFExtractor()
try:
    # Run actual extraction on all manuscripts
    extractor.extract_all()
    
    if extractor.manuscripts:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        total_referees = 0
        total_emails = 0
        
        for i, ms in enumerate(extractor.manuscripts):
            referees = ms.get('referees', [])
            emails = sum(1 for r in referees if r.get('email', ''))
            
            total_referees += len(referees)
            total_emails += emails
            
            print(f'Manuscript {i+1}: {ms.get("id")} - {len(referees)} referees, {emails} emails')
        
        success_rate = 100 * total_emails / total_referees if total_referees > 0 else 0
        print(f'RESULT: {total_emails}/{total_referees} emails extracted ({success_rate:.1f}%)')
        
        extractor.save_results()
    
except Exception as e:
    print(f'Error: {e}')
finally:
    try:
        extractor.cleanup()
    except:
        pass