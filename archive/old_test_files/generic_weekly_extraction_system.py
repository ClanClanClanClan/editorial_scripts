#!/usr/bin/env python3
"""
Generic Weekly Extraction System - Handles all configured journals
Scalable system that can process any number of journals
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

from generic_referee_extractor import GenericRefereeExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GENERIC_WEEKLY_EXTRACTION")


class GenericWeeklyExtractionSystem:
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
        
        # Load journal configuration
        self.config_file = Path("config/journals_config.json")
        self.journals_config = self.load_journals_config()
        
    def load_journals_config(self) -> Dict:
        """Load the journals configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            logger.error(f"Configuration file not found: {self.config_file}")
            return {'journals': {}, 'extraction_settings': {}}
        
    def get_active_journals(self) -> List[str]:
        """Get list of active journal codes"""
        active = []
        for code, config in self.journals_config['journals'].items():
            if config.get('active', True):
                active.append(code)
        return sorted(active)
        
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
        
    def run_weekly_extraction(self, journal_codes: List[str] = None):
        """Run the complete weekly extraction process for specified or all active journals"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🗓️  GENERIC WEEKLY EXTRACTION SYSTEM - {self.current_week}")
        logger.info(f"{'='*80}\n")
        
        # Get journals to process
        if journal_codes is None:
            journal_codes = self.get_active_journals()
        else:
            # Validate provided journal codes
            active_journals = self.get_active_journals()
            journal_codes = [j for j in journal_codes if j in active_journals]
            
        logger.info(f"Processing journals: {', '.join(journal_codes)}")
        
        # Track overall progress
        extraction_summary = {
            'week': self.current_week,
            'start_time': datetime.now().isoformat(),
            'journals': {}
        }
        
        # Process each journal
        for journal_code in journal_codes:
            logger.info(f"\n📚 Processing {journal_code}...")
            journal_results = self.process_journal(journal_code)
            extraction_summary['journals'][journal_code] = journal_results
            
        # Save summary
        extraction_summary['end_time'] = datetime.now().isoformat()
        summary_file = self.week_dir / "extraction_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(extraction_summary, f, indent=2)
            
        # Generate reports
        self.generate_weekly_report(extraction_summary)
        self.create_email_digest(journal_codes)
        
        logger.info(f"\n✅ Weekly extraction completed!")
        logger.info(f"📁 Results saved to: {self.week_dir}")
        
        return extraction_summary
        
    def process_journal(self, journal_code: str) -> Dict:
        """Process a single journal"""
        journal_dir = self.week_dir / journal_code.lower()
        journal_dir.mkdir(exist_ok=True)
        
        results = {
            'journal_code': journal_code,
            'journal_name': self.journals_config['journals'][journal_code]['name'],
            'extraction_time': datetime.now().isoformat(),
            'manuscripts_processed': 0,
            'referees_found': 0,
            'completed_referees_found': 0,
            'new_pdfs_needed': 0,
            'skipped_pdfs': 0,
            'errors': []
        }
        
        try:\n            # Run referee extraction using generic extractor\n            logger.info(f\"📊 Extracting referee data for {journal_code}...\")\n            extractor = GenericRefereeExtractor(journal_code)\n            extractor.output_dir = journal_dir  # Save to weekly directory\n            \n            # Extract data for all manuscripts in this journal\n            extraction_results = extractor.extract_referee_data(headless=True)\n            \n            # Process results\n            manuscripts = extraction_results.get('manuscripts', [])\n            results['manuscripts_processed'] = len(manuscripts)\n            \n            for manuscript in manuscripts:\n                # Count referees\n                active_refs = len(manuscript.get('referees', []))\n                completed_refs = len(manuscript.get('completed_referees', []))\n                results['referees_found'] += active_refs\n                results['completed_referees_found'] += completed_refs\n                \n                # Track PDFs to download\n                ms_id = manuscript['manuscript_id']\n                \n                # Check if manuscript PDF needed\n                if not self.is_pdf_downloaded('manuscript', ms_id):\n                    logger.info(f\"   📄 Need to download PDF for {ms_id}\")\n                    results['new_pdfs_needed'] += 1\n                else:\n                    logger.info(f\"   ✓ PDF already downloaded for {ms_id}\")\n                    results['skipped_pdfs'] += 1\n                    \n                # Check referee reports\n                for ref in manuscript.get('completed_referees', []):\n                    if ref.get('report_url'):\n                        report_id = f\"{ms_id}_{ref['name'].replace(' ', '_')}\"\n                        if not self.is_pdf_downloaded('report', report_id):\n                            logger.info(f\"   📑 Need to download report from {ref['name']} for {ms_id}\")\n                            results['new_pdfs_needed'] += 1\n                        else:\n                            logger.info(f\"   ✓ Report already downloaded from {ref['name']}\")\n                            results['skipped_pdfs'] += 1\n                            \n        except Exception as e:\n            logger.error(f\"❌ Error processing {journal_code}: {e}\")\n            results['errors'].append(str(e))\n            \n        return results\n        \n    def generate_weekly_report(self, summary: Dict):\n        \"\"\"Generate a comprehensive weekly report\"\"\"\n        report_file = self.week_dir / \"weekly_report.txt\"\n        \n        with open(report_file, 'w') as f:\n            f.write(f\"GENERIC WEEKLY EXTRACTION REPORT\\n\")\n            f.write(f\"{'='*60}\\n\")\n            f.write(f\"Week: {summary['week']}\\n\")\n            f.write(f\"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\")\n            f.write(f\"{'='*60}\\n\\n\")\n            \n            # Overall statistics\n            total_journals = len(summary['journals'])\n            total_manuscripts = sum(j['manuscripts_processed'] for j in summary['journals'].values())\n            total_referees = sum(j['referees_found'] for j in summary['journals'].values())\n            total_completed = sum(j['completed_referees_found'] for j in summary['journals'].values())\n            total_new_pdfs = sum(j['new_pdfs_needed'] for j in summary['journals'].values())\n            total_skipped = sum(j['skipped_pdfs'] for j in summary['journals'].values())\n            \n            f.write(\"OVERALL SUMMARY\\n\")\n            f.write(f\"Journals processed: {total_journals}\\n\")\n            f.write(f\"Total manuscripts: {total_manuscripts}\\n\")\n            f.write(f\"Active referees: {total_referees}\\n\")\n            f.write(f\"Completed referees: {total_completed}\\n\")\n            f.write(f\"New PDFs to download: {total_new_pdfs}\\n\")\n            f.write(f\"PDFs already downloaded: {total_skipped}\\n\")\n            f.write(f\"\\n{'-'*60}\\n\\n\")\n            \n            # Journal details\n            for journal_code, data in summary['journals'].items():\n                f.write(f\"{journal_code} ({data['journal_name']})\\n\")\n                f.write(f\"Manuscripts: {data['manuscripts_processed']}\\n\")\n                f.write(f\"Active referees: {data['referees_found']}\\n\")\n                f.write(f\"Completed referees: {data['completed_referees_found']}\\n\")\n                f.write(f\"New PDFs needed: {data['new_pdfs_needed']}\\n\")\n                f.write(f\"PDFs skipped: {data['skipped_pdfs']}\\n\")\n                if data['errors']:\n                    f.write(f\"Errors: {len(data['errors'])}\\n\")\n                    for error in data['errors']:\n                        f.write(f\"  - {error}\\n\")\n                f.write(f\"\\n{'-'*60}\\n\\n\")\n                \n            # PDF tracking summary\n            f.write(\"PDF TRACKING SUMMARY\\n\")\n            f.write(f\"Total manuscript PDFs downloaded: {len(self.download_tracker.get('manuscripts', {}))}\\n\")\n            f.write(f\"Total referee reports downloaded: {len(self.download_tracker.get('referee_reports', {}))}\\n\")\n            f.write(f\"Last tracker update: {self.download_tracker.get('last_updated', 'Never')}\\n\")\n            \n        logger.info(f\"📄 Weekly report saved to: {report_file}\")\n        \n    def create_email_digest(self, journal_codes: List[str]):\n        \"\"\"Create a concise email digest of active referees across all journals\"\"\"\n        digest_file = self.week_dir / \"email_digest.txt\"\n        \n        with open(digest_file, 'w') as f:\n            f.write(f\"REFEREE STATUS DIGEST - Week of {datetime.now().strftime('%Y-%m-%d')}\\n\")\n            f.write(f\"{'='*60}\\n\\n\")\n            \n            total_active_manuscripts = 0\n            total_active_referees = 0\n            \n            # Process each journal\n            for journal_code in journal_codes:\n                results_file = self.week_dir / journal_code.lower() / f\"{journal_code.lower()}_referee_results.json\"\n                if results_file.exists():\n                    with open(results_file, 'r') as rf:\n                        data = json.load(rf)\n                        \n                    journal_name = self.journals_config['journals'][journal_code]['name']\n                    f.write(f\"\\n{journal_code} - {journal_name}\\n\")\n                    f.write(f\"{'-'*40}\\n\")\n                    \n                    manuscripts_with_active = 0\n                    journal_active_referees = 0\n                    \n                    for ms in data.get('manuscripts', []):\n                        active_refs = ms.get('referees', [])\n                        if active_refs:  # Only show manuscripts with active referees\n                            manuscripts_with_active += 1\n                            journal_active_referees += len(active_refs)\n                            \n                            f.write(f\"\\n📄 {ms['manuscript_id']}: {ms.get('title', 'N/A')[:50]}...\\n\")\n                            f.write(f\"   Due: {ms.get('due_date', 'N/A')}\\n\")\n                            f.write(f\"   Active Referees ({len(active_refs)}):\" )\n                            \n                            for ref in active_refs:\n                                f.write(f\"\\n   • {ref['name']}\")\n                                if ref.get('email'):\n                                    f.write(f\" ({ref['email']})\")\n                                if ref.get('acceptance_date'):\n                                    try:\n                                        # Try to calculate days since acceptance\n                                        from email.utils import parsedate_to_datetime\n                                        acc_date = parsedate_to_datetime(ref['acceptance_date'])\n                                        days_active = (datetime.now() - acc_date.replace(tzinfo=None)).days\n                                        f.write(f\" - {days_active} days in review\")\n                                    except:\n                                        pass\n                            f.write(\"\\n\")\n                            \n                    if manuscripts_with_active == 0:\n                        f.write(\"   No manuscripts with active referees.\\n\")\n                    else:\n                        f.write(f\"\\n   Summary: {manuscripts_with_active} manuscripts, {journal_active_referees} active referees\\n\")\n                        \n                    total_active_manuscripts += manuscripts_with_active\n                    total_active_referees += journal_active_referees\n                    \n            f.write(f\"\\n{'='*60}\\n\")\n            f.write(f\"TOTALS ACROSS ALL JOURNALS\\n\")\n            f.write(f\"Active manuscripts: {total_active_manuscripts}\\n\")\n            f.write(f\"Active referees: {total_active_referees}\\n\")\n            f.write(f\"Journals processed: {len(journal_codes)}\\n\")\n                    \n        logger.info(f\"📧 Email digest saved to: {digest_file}\")\n        \n    def cleanup_old_extractions(self, keep_weeks: int = 4):\n        \"\"\"Clean up old extraction directories, keeping only recent weeks\"\"\"\n        all_weeks = sorted([d for d in self.base_dir.iterdir() if d.is_dir() and d.name.startswith(\"20\")])\n        \n        if len(all_weeks) > keep_weeks:\n            for old_week in all_weeks[:-keep_weeks]:\n                logger.info(f\"🗑️  Removing old extraction: {old_week}\")\n                shutil.rmtree(old_week)\n                \n    def get_status(self) -> Dict:\n        \"\"\"Get current system status\"\"\"\n        active_journals = self.get_active_journals()\n        \n        status = {\n            'last_extraction': self.download_tracker.get('last_updated', 'Never'),\n            'active_journals': active_journals,\n            'total_journals_configured': len(self.journals_config['journals']),\n            'manuscript_pdfs_downloaded': len(self.download_tracker.get('manuscripts', {})),\n            'referee_reports_downloaded': len(self.download_tracker.get('referee_reports', {})),\n            'pdf_storage_location': str(self.pdf_storage),\n            'total_pdfs_in_storage': len(list(self.pdf_storage.rglob('*.pdf'))),\n            'current_week_dir': str(self.week_dir)\n        }\n        \n        return status\n\n\ndef main():\n    \"\"\"Main function\"\"\"\n    import argparse\n    parser = argparse.ArgumentParser(description='Generic Weekly Extraction System')\n    parser.add_argument('--journals', nargs='+', help='Specific journal codes to process')\n    parser.add_argument('--list-journals', action='store_true', help='List all configured journals')\n    parser.add_argument('--status', action='store_true', help='Show system status')\n    parser.add_argument('--cleanup', action='store_true', help='Clean up old extractions')\n    \n    args = parser.parse_args()\n    \n    system = GenericWeeklyExtractionSystem()\n    \n    if args.list_journals:\n        active = system.get_active_journals()\n        all_journals = system.journals_config['journals']\n        \n        logger.info(\"📚 CONFIGURED JOURNALS:\")\n        for code, config in all_journals.items():\n            status = \"✅ Active\" if config.get('active', True) else \"❌ Inactive\"\n            logger.info(f\"   {code}: {config['name']} - {status}\")\n        logger.info(f\"\\nTotal: {len(all_journals)} configured, {len(active)} active\")\n        \n    elif args.status:\n        status = system.get_status()\n        logger.info(\"📊 SYSTEM STATUS:\")\n        for key, value in status.items():\n            logger.info(f\"   {key}: {value}\")\n            \n    elif args.cleanup:\n        system.cleanup_old_extractions()\n        \n    else:\n        # Run extraction\n        journal_codes = args.journals if args.journals else None\n        system.run_weekly_extraction(journal_codes)\n\n\nif __name__ == '__main__':\n    main()