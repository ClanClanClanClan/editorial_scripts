#!/usr/bin/env python3
"""
Run Generic Weekly Extraction - Main script for all journals
This is the corrected version that handles all 8+ journals
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import json
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from generic_referee_extractor import GenericRefereeExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RUN_GENERIC_WEEKLY")


class GenericWeeklySystem:
    def __init__(self):
        # Load journal configuration
        self.config_file = Path("config/journals_config.json")
        self.journals_config = self.load_journals_config()
        
        # Setup directories
        self.base_dir = Path("weekly_extractions")
        self.base_dir.mkdir(exist_ok=True)
        
        self.current_week = datetime.now().strftime("%Y_week_%V")
        self.week_dir = self.base_dir / self.current_week
        self.week_dir.mkdir(exist_ok=True)
        
    def load_journals_config(self):
        """Load journals configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {'journals': {}}
        
    def get_active_journals(self):
        """Get list of active journal codes"""
        active = []
        for code, config in self.journals_config['journals'].items():
            if config.get('active', True):
                active.append(code)
        return sorted(active)
        
    def run_extraction_for_journals(self, journal_codes=None):
        """Run extraction for specified journals"""
        if journal_codes is None:
            journal_codes = self.get_active_journals()
            
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 GENERIC WEEKLY EXTRACTION - {self.current_week}")
        logger.info(f"Processing journals: {', '.join(journal_codes)}")
        logger.info(f"{'='*80}\n")
        
        results = {}
        
        for journal_code in journal_codes:
            logger.info(f"\n📚 Processing {journal_code}...")
            
            try:
                # Create journal directory
                journal_dir = self.week_dir / journal_code.lower()
                journal_dir.mkdir(exist_ok=True)
                
                # Run extraction
                extractor = GenericRefereeExtractor(journal_code)
                extractor.output_dir = journal_dir
                
                extraction_result = extractor.extract_referee_data(headless=True)
                results[journal_code] = extraction_result
                
                # Log summary
                manuscripts = extraction_result.get('manuscripts', [])
                total_active = sum(len(ms.get('referees', [])) for ms in manuscripts)
                total_completed = sum(len(ms.get('completed_referees', [])) for ms in manuscripts)
                
                logger.info(f"✅ {journal_code} completed:")
                logger.info(f"   Manuscripts: {len(manuscripts)}")
                logger.info(f"   Active referees: {total_active}")
                logger.info(f"   Completed referees: {total_completed}")
                
            except Exception as e:
                logger.error(f"❌ Error processing {journal_code}: {e}")
                results[journal_code] = {'error': str(e)}
                
        # Generate summary
        self.generate_summary(results, journal_codes)
        return results
        
    def generate_summary(self, results, journal_codes):
        """Generate summary report and email digest"""
        # Summary report
        summary_file = self.week_dir / "extraction_summary.txt"
        with open(summary_file, 'w') as f:
            f.write(f"WEEKLY EXTRACTION SUMMARY - {self.current_week}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            
            total_manuscripts = 0
            total_active = 0
            total_completed = 0
            
            for journal_code in journal_codes:
                result = results.get(journal_code, {})
                
                if 'error' in result:
                    f.write(f"{journal_code}: ERROR - {result['error']}\n\n")
                    continue
                    
                manuscripts = result.get('manuscripts', [])
                active_refs = sum(len(ms.get('referees', [])) for ms in manuscripts)
                completed_refs = sum(len(ms.get('completed_referees', [])) for ms in manuscripts)
                
                journal_name = self.journals_config['journals'][journal_code]['name']
                f.write(f"{journal_code} - {journal_name}\n")
                f.write(f"  Manuscripts: {len(manuscripts)}\n")
                f.write(f"  Active referees: {active_refs}\n")
                f.write(f"  Completed referees: {completed_refs}\n\n")
                
                total_manuscripts += len(manuscripts)
                total_active += active_refs
                total_completed += completed_refs
                
            f.write(f"TOTALS:\n")
            f.write(f"  Total manuscripts: {total_manuscripts}\n")
            f.write(f"  Total active referees: {total_active}\n")
            f.write(f"  Total completed referees: {total_completed}\n")
            
        logger.info(f"📄 Summary saved to: {summary_file}")
        
        # Email digest
        self.create_email_digest(results, journal_codes)
        
    def create_email_digest(self, results, journal_codes):
        """Create email digest for weekly updates"""
        digest_file = self.week_dir / "email_digest.txt"
        
        with open(digest_file, 'w') as f:
            f.write(f"REFEREE STATUS DIGEST - Week of {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"{'='*60}\n\n")
            
            for journal_code in journal_codes:
                result = results.get(journal_code, {})
                
                if 'error' in result:
                    continue
                    
                manuscripts = result.get('manuscripts', [])
                manuscripts_with_active = [ms for ms in manuscripts if ms.get('referees')]
                
                if not manuscripts_with_active:
                    continue
                    
                journal_name = self.journals_config['journals'][journal_code]['name']
                f.write(f"\n{journal_code} - {journal_name}\n")
                f.write(f"{'-'*40}\n")
                
                for ms in manuscripts_with_active:
                    active_refs = ms.get('referees', [])
                    f.write(f"\n📄 {ms['manuscript_id']}: {ms.get('title', 'N/A')[:50]}...\n")
                    f.write(f"   Due: {ms.get('due_date', 'N/A')}\n")
                    f.write(f"   Active Referees ({len(active_refs)}):\n")
                    
                    for ref in active_refs:
                        f.write(f"   • {ref['name']}")
                        if ref.get('email'):
                            f.write(f" ({ref['email']})")
                        if ref.get('acceptance_date'):
                            try:
                                from email.utils import parsedate_to_datetime
                                acc_date = parsedate_to_datetime(ref['acceptance_date'])
                                days_active = (datetime.now() - acc_date.replace(tzinfo=None)).days
                                f.write(f" - {days_active} days in review")
                            except:
                                pass
                        f.write("\n")
                        
        logger.info(f"📧 Email digest saved to: {digest_file}")


def main():
    """Main function"""
    import argparse
    parser = argparse.ArgumentParser(description='Generic Weekly Extraction for All Journals')
    parser.add_argument('--journals', nargs='+', help='Specific journal codes to process (e.g., MF MOR JFE)')
    parser.add_argument('--list', action='store_true', help='List all configured journals')
    parser.add_argument('--test', choices=['MF', 'MOR'], help='Test with a single known-working journal')
    
    args = parser.parse_args()
    
    system = GenericWeeklySystem()
    
    if args.list:
        active = system.get_active_journals()
        all_journals = system.journals_config['journals']
        
        logger.info("📚 CONFIGURED JOURNALS:")
        for code, config in all_journals.items():
            status = "✅ Active" if config.get('active', True) else "❌ Inactive"
            logger.info(f"   {code}: {config['name']} - {status}")
        logger.info(f"\nTotal: {len(all_journals)} configured, {len(active)} active")
        
    elif args.test:
        # Test with a single journal
        logger.info(f"🧪 Testing with {args.test}")
        system.run_extraction_for_journals([args.test])
        
    else:
        # Run full extraction
        journal_codes = args.journals if args.journals else None
        system.run_extraction_for_journals(journal_codes)
        

if __name__ == '__main__':
    main()