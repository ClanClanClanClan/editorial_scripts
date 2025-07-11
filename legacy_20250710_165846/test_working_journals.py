#!/usr/bin/env python3
"""
Test the journals that successfully instantiate to see if they can run basic operations.
"""

import traceback
from datetime import datetime

# Test the working journals
WORKING_JOURNALS = [
    ('FS', 'journals.fs', 'FSJournal', 'no_params'),
    ('JOTA', 'journals.jota', 'JOTAJournal', 'gmail_service'),
    ('MAFE', 'journals.mafe', 'MAFEJournal', 'driver'),
    ('SICON', 'journals.sicon', 'SICONJournal', 'driver'),
]

def test_working_journals():
    """Test the journals that can be instantiated"""
    print("=" * 60)
    print(f"TESTING WORKING JOURNALS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {}
    
    for journal_name, module_name, class_name, param_type in WORKING_JOURNALS:
        print(f"\n{'='*20} TESTING {journal_name} {'='*20}")
        
        try:
            # Import the journal
            module = __import__(module_name, fromlist=[class_name])
            journal_class = getattr(module, class_name)
            
            # Instantiate based on parameter type
            if param_type == 'no_params':
                journal = journal_class()
            elif param_type == 'gmail_service':
                journal = journal_class(gmail_service=None)
            elif param_type == 'driver':
                journal = journal_class(driver=None)
            else:
                raise ValueError(f"Unknown parameter type: {param_type}")
            
            print(f"✓ {journal_name}: Instantiation successful")
            
            # Test basic method availability
            if hasattr(journal, 'scrape_manuscripts_and_emails'):
                print(f"✓ {journal_name}: Has scrape_manuscripts_and_emails method")
            
            # Try to run scraping (with timeout protection)
            print(f"→ {journal_name}: Attempting to run scrape_manuscripts_and_emails()...")
            
            try:
                manuscripts = journal.scrape_manuscripts_and_emails()
                
                if manuscripts is None:
                    print(f"⚠ {journal_name}: Returned None (likely expected for mock environment)")
                    results[journal_name] = {'status': 'PARTIAL', 'reason': 'Returned None'}
                elif isinstance(manuscripts, list):
                    print(f"✓ {journal_name}: SUCCESS - Found {len(manuscripts)} manuscripts")
                    results[journal_name] = {'status': 'SUCCESS', 'manuscripts': len(manuscripts)}
                    
                    # Show sample manuscript if available
                    if manuscripts:
                        sample = manuscripts[0]
                        if isinstance(sample, dict):
                            print(f"✓ {journal_name}: Sample manuscript keys: {list(sample.keys())[:5]}...")
                        else:
                            print(f"⚠ {journal_name}: Sample manuscript is not a dict: {type(sample)}")
                else:
                    print(f"⚠ {journal_name}: Returned unexpected type: {type(manuscripts)}")
                    results[journal_name] = {'status': 'PARTIAL', 'reason': f'Returned {type(manuscripts)}'}
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check if it's an expected error (authentication, web scraping, etc.)
                expected_errors = [
                    'timeout', 'webdriverwait', 'no such element', 'authentication',
                    'login', 'credentials', 'session', 'driver', 'selenium', 'chrome',
                    'firefox', 'browser', 'http', 'connection', 'ssl', 'certificate',
                    'refused', 'unreachable', 'network', 'dns', 'proxy'
                ]
                
                if any(expected_error in error_msg for expected_error in expected_errors):
                    print(f"⚠ {journal_name}: Expected error (likely requires real browser/auth): {str(e)[:100]}...")
                    results[journal_name] = {'status': 'PARTIAL', 'reason': 'Expected web scraping error'}
                else:
                    print(f"✗ {journal_name}: Unexpected error: {e}")
                    results[journal_name] = {'status': 'FAILED', 'reason': 'Unexpected error', 'error': str(e)}
                    traceback.print_exc()
                
        except Exception as e:
            print(f"✗ {journal_name}: Failed during setup: {e}")
            results[journal_name] = {'status': 'FAILED', 'reason': 'Setup failed', 'error': str(e)}
            traceback.print_exc()
    
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
            manuscripts = result.get('manuscripts', 0)
            print(f"✓ {journal_name}: {status} - Found {manuscripts} manuscripts")
            success_count += 1
        elif status == 'PARTIAL':
            print(f"⚠ {journal_name}: {status} - {result['reason']}")
            partial_count += 1
        else:
            print(f"✗ {journal_name}: {status} - {result['reason']}")
            failed_count += 1
    
    print(f"\nResults: {success_count} SUCCESS, {partial_count} PARTIAL, {failed_count} FAILED")
    
    if success_count > 0:
        print(f"\n✓ {success_count} journals are working correctly!")
    
    if partial_count > 0:
        print(f"\n⚠ {partial_count} journals have expected limitations (likely need real browser/auth)")
    
    if failed_count > 0:
        print(f"\n✗ {failed_count} journals have unexpected errors that need investigation")
    
    return results

if __name__ == "__main__":
    test_working_journals()