#!/usr/bin/env python3
"""
Basic test script to quickly check journal imports and basic functionality.
"""

import importlib
import sys
import traceback
from datetime import datetime

# List of all journals to test
JOURNALS_TO_TEST = [
    ('FS', 'journals.fs', 'FSJournal'),
    ('MF', 'journals.mf', 'MFJournal'),
    ('MOR', 'journals.mor', 'MORJournal'), 
    ('JOTA', 'journals.jota', 'JOTAJournal'),
    ('MAFE', 'journals.mafe', 'MAFEJournal'),
    ('NACO', 'journals.naco', 'NACOJournal'),
    ('SICON', 'journals.sicon', 'SICONJournal'),
    ('SIFIN', 'journals.sifin', 'SIFINJournal'),
]

def test_journal_basics():
    """Test basic journal functionality without running full scraping"""
    print("=" * 60)
    print(f"BASIC JOURNAL TESTING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {}
    
    for journal_name, module_name, class_name in JOURNALS_TO_TEST:
        print(f"\n{'='*20} TESTING {journal_name} {'='*20}")
        
        # Test 1: Import
        try:
            module = importlib.import_module(module_name)
            journal_class = getattr(module, class_name)
            print(f"✓ {journal_name}: Import successful")
        except Exception as e:
            print(f"✗ {journal_name}: Import failed - {e}")
            results[journal_name] = {'status': 'FAILED', 'reason': 'Import failed', 'error': str(e)}
            continue
        
        # Test 2: Check class structure
        try:
            # Check if it has required methods
            required_methods = ['scrape_manuscripts_and_emails']
            missing_methods = []
            
            for method_name in required_methods:
                if not hasattr(journal_class, method_name):
                    missing_methods.append(method_name)
            
            if missing_methods:
                print(f"⚠ {journal_name}: Missing methods: {missing_methods}")
                results[journal_name] = {'status': 'PARTIAL', 'reason': 'Missing methods', 'details': missing_methods}
            else:
                print(f"✓ {journal_name}: Has all required methods")
        except Exception as e:
            print(f"✗ {journal_name}: Method check failed - {e}")
            results[journal_name] = {'status': 'FAILED', 'reason': 'Method check failed', 'error': str(e)}
            continue
        
        # Test 3: Basic instantiation test (without running scraping)
        try:
            # Try different instantiation patterns
            journal = None
            instantiation_method = None
            
            # Try with no parameters (like FS)
            try:
                journal = journal_class()
                instantiation_method = "no parameters"
            except TypeError:
                pass
            
            # Try with driver=None
            if journal is None:
                try:
                    journal = journal_class(driver=None)
                    instantiation_method = "driver=None"
                except (TypeError, Exception):
                    pass
            
            # Try with gmail_service=None
            if journal is None:
                try:
                    journal = journal_class(gmail_service=None)
                    instantiation_method = "gmail_service=None"
                except (TypeError, Exception):
                    pass
            
            if journal is not None:
                print(f"✓ {journal_name}: Instantiation successful ({instantiation_method})")
                
                # Quick method availability check
                if hasattr(journal, 'scrape_manuscripts_and_emails'):
                    print(f"✓ {journal_name}: scrape_manuscripts_and_emails method available")
                
                results[journal_name] = {'status': 'SUCCESS', 'instantiation': instantiation_method}
            else:
                print(f"⚠ {journal_name}: Could not instantiate with common patterns")
                results[journal_name] = {'status': 'PARTIAL', 'reason': 'Instantiation issues'}
                
        except Exception as e:
            print(f"✗ {journal_name}: Instantiation test failed - {e}")
            results[journal_name] = {'status': 'FAILED', 'reason': 'Instantiation failed', 'error': str(e)}
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = 0
    failed_count = 0
    partial_count = 0
    
    for journal_name, result in results.items():
        status = result['status']
        if status == 'SUCCESS':
            print(f"✓ {journal_name}: {status} - {result.get('instantiation', 'OK')}")
            success_count += 1
        elif status == 'PARTIAL':
            print(f"⚠ {journal_name}: {status} - {result['reason']}")
            partial_count += 1
        else:
            print(f"✗ {journal_name}: {status} - {result['reason']}")
            failed_count += 1
    
    print(f"\nResults: {success_count} SUCCESS, {partial_count} PARTIAL, {failed_count} FAILED")
    
    # Test FS journal specifically (since we know it works)
    print(f"\n{'='*20} TESTING FS JOURNAL SPECIFICALLY {'='*20}")
    try:
        from journals.fs import FSJournal
        fs_journal = FSJournal()
        print("✓ FS Journal: Instantiated successfully")
        
        # Try scraping (this should work)
        manuscripts = fs_journal.scrape_manuscripts_and_emails()
        print(f"✓ FS Journal: Scraping successful - Found {len(manuscripts)} manuscripts")
        
        # Show a sample manuscript
        if manuscripts:
            sample_ms = manuscripts[0]
            print(f"✓ FS Journal: Sample manuscript keys: {list(sample_ms.keys())}")
            print(f"✓ FS Journal: Sample manuscript ID: {sample_ms.get('Manuscript #', 'N/A')}")
            print(f"✓ FS Journal: Sample manuscript referees: {len(sample_ms.get('Referees', []))}")
    except Exception as e:
        print(f"✗ FS Journal: Failed - {e}")
        traceback.print_exc()
    
    return results

if __name__ == "__main__":
    test_journal_basics()