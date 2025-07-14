#!/usr/bin/env python3
"""
Weekly Extraction System - Complete referee data extraction with PDF management
Runs weekly, tracks downloaded PDFs to avoid re-downloading
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import json
import shutil
from typing import Dict, List, Set

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from final_working_referee_extractor import FinalWorkingRefereeExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WEEKLY_EXTRACTION")


class WeeklyExtractionSystem:
    def __init__(self):
        self.base_dir = Path("weekly_extractions")
        self.base_dir.mkdir(exist_ok=True)
        
        # Create dated directory for this week's extraction
        self.current_week = datetime.now().strftime("%Y_week_%V")
        self.week_dir = self.base_dir / self.current_week
        self.week_dir.mkdir(exist_ok=True)
        
        # PDF storage directory (persistent across weeks)
        self.pdf_storage = Path("referee_pdfs")
        self.pdf_storage.mkdir(exist_ok=True)
        
        # Download tracking file
        self.download_tracker_file = self.base_dir / "download_tracker.json"
        self.download_tracker = self.load_download_tracker()
        
    def load_download_tracker(self) -> Dict:
        """Load the download tracking data"""
        if self.download_tracker_file.exists():
            with open(self.download_tracker_file, 'r') as f:
                return json.load(f)
        return {
            'manuscripts': {},
            'referee_reports': {},
            'last_updated': None
        }
        
    def save_download_tracker(self):
        """Save the download tracking data"""
        self.download_tracker['last_updated'] = datetime.now().isoformat()
        with open(self.download_tracker_file, 'w') as f:
            json.dump(self.download_tracker, f, indent=2)
            
    def is_pdf_downloaded(self, pdf_type: str, identifier: str) -> bool:
        """Check if a PDF has already been downloaded"""
        if pdf_type == 'manuscript':
            return identifier in self.download_tracker.get('manuscripts', {})
        elif pdf_type == 'report':
            return identifier in self.download_tracker.get('referee_reports', {})
        return False
        
    def mark_pdf_downloaded(self, pdf_type: str, identifier: str, file_path: str):
        """Mark a PDF as downloaded"""
        download_info = {
            'downloaded_date': datetime.now().isoformat(),
            'file_path': file_path,
            'file_size': Path(file_path).stat().st_size if Path(file_path).exists() else 0
        }
        
        if pdf_type == 'manuscript':
            self.download_tracker['manuscripts'][identifier] = download_info
        elif pdf_type == 'report':
            self.download_tracker['referee_reports'][identifier] = download_info
            
        self.save_download_tracker()
        
    def run_weekly_extraction(self):
        """Run the complete weekly extraction process"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🗓️  WEEKLY EXTRACTION SYSTEM - {self.current_week}")
        logger.info(f"{'='*80}\n")
        
        # Track overall progress
        extraction_summary = {
            'week': self.current_week,
            'start_time': datetime.now().isoformat(),
            'journals': {}
        }
        
        # Process each journal
        for journal in ['MF', 'MOR']:
            logger.info(f"\n📚 Processing {journal}...")
            journal_results = self.process_journal(journal)
            extraction_summary['journals'][journal] = journal_results
            
        # Save summary
        extraction_summary['end_time'] = datetime.now().isoformat()
        summary_file = self.week_dir / "extraction_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(extraction_summary, f, indent=2)
            
        # Generate report
        self.generate_weekly_report(extraction_summary)
        
        logger.info(f"\n✅ Weekly extraction completed!")
        logger.info(f"📁 Results saved to: {self.week_dir}")
        
    def process_journal(self, journal_name: str) -> Dict:
        """Process a single journal"""
        journal_dir = self.week_dir / journal_name.lower()
        journal_dir.mkdir(exist_ok=True)
        
        results = {
            'extraction_time': datetime.now().isoformat(),
            'manuscripts_processed': 0,
            'referees_found': 0,
            'new_pdfs_downloaded': 0,
            'skipped_pdfs': 0,
            'errors': []
        }
        
        try:
            # Run referee extraction
            logger.info(f"📊 Extracting referee data for {journal_name}...")
            extractor = FinalWorkingRefereeExtractor(journal_name)
            extractor.output_dir = journal_dir  # Save to weekly directory
            extractor.extract_referee_data(headless=True)
            
            # Load extraction results
            results_file = journal_dir / f"{journal_name.lower()}_referee_results.json"
            if results_file.exists():
                with open(results_file, 'r') as f:
                    extraction_data = json.load(f)
                    
                # Process results
                manuscripts = extraction_data.get('manuscripts', [])
                results['manuscripts_processed'] = len(manuscripts)
                
                for manuscript in manuscripts:
                    # Count referees
                    active_refs = len(manuscript.get('referees', []))
                    completed_refs = len(manuscript.get('completed_referees', []))
                    results['referees_found'] += active_refs + completed_refs
                    
                    # Track PDFs to download
                    ms_id = manuscript['manuscript_id']
                    
                    # Check if manuscript PDF needed
                    if not self.is_pdf_downloaded('manuscript', ms_id):
                        logger.info(f"   📄 Need to download PDF for {ms_id}")
                        # TODO: Implement actual PDF download
                        # For now, just mark as needed
                        results['new_pdfs_downloaded'] += 1
                    else:
                        logger.info(f"   ✓ PDF already downloaded for {ms_id}")
                        results['skipped_pdfs'] += 1
                        
                    # Check referee reports
                    for ref in manuscript.get('completed_referees', []):
                        if ref.get('report_url'):
                            report_id = f"{ms_id}_{ref['name']}"
                            if not self.is_pdf_downloaded('report', report_id):
                                logger.info(f"   📑 Need to download report from {ref['name']} for {ms_id}")
                                results['new_pdfs_downloaded'] += 1
                            else:
                                logger.info(f"   ✓ Report already downloaded from {ref['name']}")
                                results['skipped_pdfs'] += 1
                                
        except Exception as e:
            logger.error(f"❌ Error processing {journal_name}: {e}")
            results['errors'].append(str(e))
            
        return results
        
    def generate_weekly_report(self, summary: Dict):
        """Generate a comprehensive weekly report"""
        report_file = self.week_dir / "weekly_report.txt"
        
        with open(report_file, 'w') as f:
            f.write(f"WEEKLY EXTRACTION REPORT\n")
            f.write(f"{'='*60}\n")
            f.write(f"Week: {summary['week']}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            
            # Overall statistics
            total_manuscripts = sum(j['manuscripts_processed'] for j in summary['journals'].values())
            total_referees = sum(j['referees_found'] for j in summary['journals'].values())
            total_new_pdfs = sum(j['new_pdfs_downloaded'] for j in summary['journals'].values())
            total_skipped = sum(j['skipped_pdfs'] for j in summary['journals'].values())
            
            f.write("OVERALL SUMMARY\n")
            f.write(f"Total manuscripts processed: {total_manuscripts}\n")
            f.write(f"Total referees found: {total_referees}\n")
            f.write(f"New PDFs to download: {total_new_pdfs}\n")
            f.write(f"PDFs already downloaded: {total_skipped}\n")
            f.write(f"\n{'-'*60}\n\n")
            
            # Journal details
            for journal, data in summary['journals'].items():
                f.write(f"{journal} RESULTS\n")
                f.write(f"Manuscripts: {data['manuscripts_processed']}\n")
                f.write(f"Referees: {data['referees_found']}\n")
                f.write(f"New PDFs needed: {data['new_pdfs_downloaded']}\n")
                f.write(f"PDFs skipped: {data['skipped_pdfs']}\n")
                if data['errors']:
                    f.write(f"Errors: {len(data['errors'])}\n")
                    for error in data['errors']:
                        f.write(f"  - {error}\n")
                f.write(f"\n{'-'*60}\n\n")
                
            # PDF tracking summary
            f.write("PDF TRACKING SUMMARY\n")
            f.write(f"Total manuscript PDFs downloaded: {len(self.download_tracker.get('manuscripts', {}))}\n")
            f.write(f"Total referee reports downloaded: {len(self.download_tracker.get('referee_reports', {}))}\n")
            f.write(f"Last tracker update: {self.download_tracker.get('last_updated', 'Never')}\n")
            
        logger.info(f"📄 Weekly report saved to: {report_file}")
        
        # Also create a digest for emailing
        self.create_email_digest()
        
    def create_email_digest(self):
        """Create a concise email digest of active referees"""
        digest_file = self.week_dir / "email_digest.txt"
        
        with open(digest_file, 'w') as f:
            f.write(f"REFEREE STATUS DIGEST - Week of {datetime.now().strftime('%Y-%m-%d')}\n")
            f.write(f"{'='*60}\n\n")
            
            # Process each journal
            for journal in ['MF', 'MOR']:
                results_file = self.week_dir / journal.lower() / f"{journal.lower()}_referee_results.json"
                if results_file.exists():
                    with open(results_file, 'r') as rf:
                        data = json.load(rf)
                        
                    f.write(f"{journal} MANUSCRIPTS\n")
                    f.write(f"{'-'*40}\n")
                    
                    for ms in data.get('manuscripts', []):
                        if ms.get('referees'):  # Only show manuscripts with active referees
                            f.write(f"\n📄 {ms['manuscript_id']}: {ms.get('title', 'N/A')}\n")
                            f.write(f"   Due: {ms.get('due_date', 'N/A')}\n")
                            f.write(f"   Active Referees:\n")
                            
                            for ref in ms['referees']:
                                f.write(f"   • {ref['name']}")
                                if ref.get('email'):
                                    f.write(f" ({ref['email']})")
                                if ref.get('acceptance_date'):
                                    # Calculate days since acceptance
                                    try:
                                        acc_date = datetime.strptime(ref['acceptance_date'].split()[1], "%d")
                                        days_active = (datetime.now() - acc_date).days
                                        f.write(f" - {days_active} days in review")
                                    except:
                                        pass
                                f.write("\n")
                                
                    f.write(f"\n{'='*60}\n\n")
                    
        logger.info(f"📧 Email digest saved to: {digest_file}")
        
    def cleanup_old_extractions(self, keep_weeks: int = 4):
        """Clean up old extraction directories, keeping only recent weeks"""
        all_weeks = sorted([d for d in self.base_dir.iterdir() if d.is_dir() and d.name.startswith("20")])
        
        if len(all_weeks) > keep_weeks:
            for old_week in all_weeks[:-keep_weeks]:
                logger.info(f"🗑️  Removing old extraction: {old_week}")
                shutil.rmtree(old_week)


def main():
    """Main function"""
    import argparse
    parser = argparse.ArgumentParser(description='Weekly Extraction System')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old extractions')
    parser.add_argument('--check-only', action='store_true', help='Only check what needs downloading')
    
    args = parser.parse_args()
    
    system = WeeklyExtractionSystem()
    
    if args.cleanup:
        system.cleanup_old_extractions()
    elif args.check_only:
        # Just load tracker and report status
        logger.info("📊 Current download status:")
        logger.info(f"   Manuscript PDFs: {len(system.download_tracker.get('manuscripts', {}))}")
        logger.info(f"   Referee reports: {len(system.download_tracker.get('referee_reports', {}))}")
        logger.info(f"   Last updated: {system.download_tracker.get('last_updated', 'Never')}")
    else:
        system.run_weekly_extraction()


if __name__ == '__main__':
    main()