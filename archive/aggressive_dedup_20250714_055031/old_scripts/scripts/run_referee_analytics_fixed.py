#!/usr/bin/env python3
"""
Fixed comprehensive referee analytics runner with extended timeouts
"""

import asyncio
import os
import sys
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.referee_analytics import RefereeAnalytics
from src.infrastructure.scrapers.enhanced_referee_extractor import EnhancedRefereeExtractor
from src.infrastructure.scrapers.siam_scraper import SIAMScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_simple_analysis():
    """Run a simplified analysis focusing on SIFIN"""
    logger.info("🚀 Starting Simplified Referee Analytics (SIFIN only)")
    logger.info("=" * 60)
    
    # Set credentials
    os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
    os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
    
    analytics = RefereeAnalytics()
    results_dir = Path.home() / '.editorial_scripts' / 'analytics'
    results_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create SIFIN scraper with extended timeout
        logger.info("📊 Processing SIFIN with extended timeouts...")
        scraper = SIAMScraper('SIFIN')
        
        # Override the timeout settings to handle Cloudflare
        scraper.config.page_timeout = 120000  # 2 minutes
        scraper.config.element_timeout = 30000  # 30 seconds
        
        # Create browser
        browser = await scraper.create_browser()
        context = await scraper.setup_browser_context(browser)
        page = await context.new_page()
        
        # Set extended default timeout for the page
        page.set_default_timeout(120000)
        
        # Authenticate
        logger.info("🔐 Authenticating with extended timeout...")
        auth_result = await scraper.authenticate(page)
        
        if auth_result:
            logger.info("✅ Authentication successful!")
            
            # Extract manuscripts
            logger.info("📄 Extracting manuscripts...")
            manuscripts = await scraper.extract_manuscripts(page)
            logger.info(f"✅ Found {len(manuscripts)} manuscripts")
            
            # Create extractor
            extractor = EnhancedRefereeExtractor('SIFIN', scraper.config.base_url)
            
            # Process first few manuscripts as a test
            for i, ms in enumerate(manuscripts[:2]):  # Just first 2 for testing
                logger.info(f"\n📄 Processing manuscript {i+1}: {ms.id}")
                
                try:
                    # Extract referee timelines
                    timelines = await extractor.extract_referee_timeline_siam(page, ms.id)
                    
                    # Add to analytics
                    for timeline in timelines:
                        analytics.add_timeline(timeline)
                    
                    logger.info(f"   ✅ Found {len(timelines)} referees")
                    
                    # Try to download documents
                    try:
                        documents = await extractor.download_all_manuscript_documents(page, ms.id)
                        logger.info(f"   📎 Downloaded: {len(documents.get('manuscript_pdfs', []))} manuscripts")
                    except Exception as e:
                        logger.warning(f"   ⚠️ Document download failed: {e}")
                        
                except Exception as e:
                    logger.error(f"   ❌ Error processing manuscript: {e}")
        else:
            logger.error("❌ Authentication failed!")
            # Take screenshot for debugging
            await page.screenshot(path="auth_failed_debug.png")
            logger.info("📸 Debug screenshot saved: auth_failed_debug.png")
        
        await context.close()
        await browser.close()
        
    except Exception as e:
        logger.error(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate simple report
    logger.info("\n📊 Generating Report...")
    overall_stats = analytics.get_overall_stats()
    
    report = {
        'generated_at': datetime.now().isoformat(),
        'journal': 'SIFIN',
        'statistics': overall_stats,
        'journal_stats': analytics.get_journal_stats('SIFIN')
    }
    
    # Save report
    report_file = results_dir / f"sifin_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 REFEREE ANALYTICS SUMMARY (SIFIN Test)")
    print("="*60)
    
    if overall_stats and 'overall' in overall_stats:
        overall = overall_stats['overall']
        print(f"\n📈 Statistics:")
        print(f"   Total Referees: {overall.get('total_referees', 0)}")
        print(f"   Total Reports: {overall.get('total_reports', 0)}")
    else:
        print("\n❌ No data collected")
    
    print(f"\n📁 Report saved to: {report_file}")
    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(run_simple_analysis())