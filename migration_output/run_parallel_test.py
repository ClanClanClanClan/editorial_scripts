#!/usr/bin/env python3
"""
Parallel Extraction Test
Run both legacy and new systems for comparison
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

async def run_parallel_extraction():
    results = {
        'timestamp': datetime.now().isoformat(),
        'legacy': {},
        'new': {},
        'comparison': {}
    }
    
    # Run legacy SICON (if available)
    try:
        from journals.sicon import SICON
        legacy_sicon = SICON()
        legacy_results = legacy_sicon.extract()
        results['legacy']['sicon'] = {
            'manuscript_count': len(legacy_results.get('manuscripts', [])),
            'success': True
        }
    except Exception as e:
        results['legacy']['sicon'] = {'success': False, 'error': str(e)}
    
    # Run new SICON
    try:
        import sys
        sys.path.insert(0, 'src')
        from infrastructure.browser_pool import PlaywrightBrowserPool
        from infrastructure.scrapers.sicon_scraper import SICONScraper
        
        browser_pool = PlaywrightBrowserPool(size=1)
        await browser_pool.start()
        
        new_sicon = SICONScraper(browser_pool)
        # Note: Would need authentication setup for full test
        results['new']['sicon'] = {'available': True}
        
        await browser_pool.stop()
    except Exception as e:
        results['new']['sicon'] = {'available': False, 'error': str(e)}
    
    # Save results
    output_file = Path('migration_output/parallel_test_results.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Parallel extraction test completed. Results saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(run_parallel_extraction())
