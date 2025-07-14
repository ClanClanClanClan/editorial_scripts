#!/usr/bin/env python3
"""
Direct extraction bypassing 1Password session manager
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / 'core'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_extraction():
    """Run extraction with direct credential access"""
    try:
        # Set service account token
        os.environ['OP_SERVICE_ACCOUNT_TOKEN'] = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjNnZkpDeW1iMGJBRHRYWmlGWGVuWUJyX1Y5T3R6UHVSLUFwNVcyZVgwRW8iLCJ0eXAiOiJKV1QifQ.eyJhZXMiOiJNRFVYUUxBV0I3WktFWDNBSktVQ0RFTEZIK1pSSktGUVJOSzVBVkxKNVdZSkNOR0FDUlJRPT09PSIsImF1ZCI6ImJFN3hZVGNJUXlzWXZpanEzN2tQM1kiLCJjbGQiOjAsImV4cCI6MTc2ODI1ODM0MiwiaWF0IjoxNzM2NjM1MzQyLCJpc3MiOiJzZXJ2aWNlYWNjb3VudC50b2tlbi4xUGFzc3dvcmQuZXUiLCJqdGkiOiJ6cGl0M2xqaTNidGVmZDV6NzN1ZzNxY3l1NCIsInN0YSI6MTA0LCJ1aWQiOiJSSjdQNklPWEVSQU9URlRXTDNDUEtHR1lUUSIsInZlciI6Mn0.oKgBMaNSdQ6zJ1JG7YqcPQ4bVE8KK6F-BfHVzZtYaMQhQD5ELqrqEgbdISDhEE-rqkR9rCo8oFfJF_CJo4TG3D0wAaXM0v5X6zznL5EfnMJCVQqOa-Z02KPHbW4e_GZqPP2jKMPi2KnB9zKgBGgRWjGPkfKyOJv1K0Z7bNqV6wkGDe0W2xXWJhWEKwxOu6r6rjQ8G4VZfzYWdmHeCq4FHbWwW3xnOeqKQZSfCnXEyKCN7N2fIHLV0wGjQWJjgN_1fZ8vU_fVm7XzjmIZaGO_LpCLRt_Bz_W8-9MfVR5l5M1F5TsGQkNnHrY-yz1P2mS5rIiGhBL8xF_E_1QgmGCw"
        
        logger.info("🎭 DIRECT UNIFIED SYSTEM EXTRACTION")
        logger.info("🤖 BYPASSING SESSION MANAGER")
        logger.info("="*60)
        
        # Import unified extractors
        from unified_system import SICONExtractor, SIFINExtractor
        
        # Create extractors
        extractors = {
            'SICON': SICONExtractor(),
            'SIFIN': SIFINExtractor()
        }
        
        results = {}
        
        for journal_name, extractor in extractors.items():
            logger.info(f"\n{'='*40}")
            logger.info(f"🎯 Extracting from {journal_name}")
            logger.info(f"{'='*40}")
            
            try:
                result = await extractor.extract(
                    username="",  # Will be retrieved directly from 1Password CLI
                    password="",  # Will be retrieved directly from 1Password CLI
                    headless=True
                )
                
                if result:
                    results[journal_name] = result
                    logger.info(f"✅ {journal_name} completed: {result['total_manuscripts']} manuscripts")
                else:
                    logger.error(f"❌ {journal_name} failed")
                    results[journal_name] = None
                    
            except Exception as e:
                logger.error(f"❌ {journal_name} error: {e}")
                results[journal_name] = None
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("🎯 EXTRACTION SUMMARY")
        logger.info(f"{'='*60}")
        
        successful = sum(1 for r in results.values() if r is not None)
        total = len(results)
        total_manuscripts = sum(r['total_manuscripts'] for r in results.values() if r)
        
        logger.info(f"Successful: {successful}/{total}")
        logger.info(f"Total manuscripts: {total_manuscripts}")
        
        if successful > 0:
            logger.info("🎉 EXTRACTION COMPLETED!")
        else:
            logger.error("❌ ALL EXTRACTIONS FAILED")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    try:
        results = asyncio.run(run_extraction())
        success = results and any(r for r in results.values())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("⚠️ Interrupted")
        sys.exit(1)