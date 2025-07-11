#!/usr/bin/env python3
"""
Run Weekly Extraction - Main script to run the complete weekly extraction
This is the script you run once per week to get all referee data and PDFs
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

from weekly_extraction_system import WeeklyExtractionSystem
from smart_pdf_downloader import download_all_pdfs

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RUN_WEEKLY")


def main():
    """Run the complete weekly extraction process"""
    start_time = time.time()
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🚀 STARTING WEEKLY REFEREE EXTRACTION")
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"{'='*80}\n")
    
    # Initialize the system
    system = WeeklyExtractionSystem()
    
    # Step 1: Run referee data extraction
    logger.info("STEP 1: Extracting referee data from ScholarOne...")
    logger.info("-" * 60)
    
    try:
        system.run_weekly_extraction()
        logger.info("✅ Referee data extraction completed successfully!")
    except Exception as e:
        logger.error(f"❌ Error during referee extraction: {e}")
        logger.info("Continuing with PDF downloads for any successful extractions...")
        
    # Step 2: Download PDFs (only new ones)
    logger.info("\nSTEP 2: Downloading PDFs...")
    logger.info("-" * 60)
    
    try:
        # Load the current download tracker
        download_tracker = system.load_download_tracker()
        
        # Download PDFs
        pdf_results = download_all_pdfs(
            system.week_dir,
            download_tracker,
            system.pdf_storage
        )
        
        # Save updated tracker
        system.save_download_tracker()
        
        logger.info("✅ PDF downloads completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during PDF downloads: {e}")
        
    # Step 3: Generate final summary
    logger.info("\nSTEP 3: Generating final summary...")
    logger.info("-" * 60)
    
    # Create final summary
    final_summary_path = system.week_dir / "final_summary.txt"
    with open(final_summary_path, 'w') as f:
        f.write("WEEKLY EXTRACTION FINAL SUMMARY\n")
        f.write(f"{'='*60}\n")
        f.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total time: {(time.time() - start_time) / 60:.1f} minutes\n")
        f.write(f"{'='*60}\n\n")
        
        # Summarize results for each journal
        total_manuscripts = 0
        total_active_referees = 0
        total_completed_referees = 0
        
        for journal in ['MF', 'MOR']:
            results_file = system.week_dir / journal.lower() / f"{journal.lower()}_referee_results.json"
            if results_file.exists():
                with open(results_file, 'r') as rf:
                    data = json.load(rf)
                    
                f.write(f"\n{journal} RESULTS\n")
                f.write("-" * 40 + "\n")
                
                manuscripts = data.get('manuscripts', [])
                total_manuscripts += len(manuscripts)
                
                for ms in manuscripts:
                    active = len(ms.get('referees', []))
                    completed = len(ms.get('completed_referees', []))
                    total_active_referees += active
                    total_completed_referees += completed
                    
                    f.write(f"\n{ms['manuscript_id']}: {ms.get('title', 'N/A')[:50]}...\n")
                    f.write(f"  Status: {ms.get('status', 'N/A')}\n")
                    f.write(f"  Due: {ms.get('due_date', 'N/A')}\n")
                    f.write(f"  Active referees: {active}\n")
                    f.write(f"  Completed referees: {completed}\n")
                    
                    # Check PDF status
                    ms_pdf = system.is_pdf_downloaded('manuscript', ms['manuscript_id'])
                    f.write(f"  Manuscript PDF: {'✅ Downloaded' if ms_pdf else '❌ Not available'}\n")
                    
        f.write(f"\n{'='*60}\n")
        f.write("TOTALS\n")
        f.write(f"Manuscripts processed: {total_manuscripts}\n")
        f.write(f"Active referees: {total_active_referees}\n")
        f.write(f"Completed referees: {total_completed_referees}\n")
        f.write(f"Total PDFs in storage: {len(list(system.pdf_storage.rglob('*.pdf')))}\n")
        
    logger.info(f"✅ Final summary saved to: {final_summary_path}")
    
    # Display key results
    logger.info(f"\n{'='*80}")
    logger.info("📊 EXTRACTION COMPLETE!")
    logger.info(f"{'='*80}")
    logger.info(f"✅ Results saved to: {system.week_dir}")
    logger.info(f"✅ PDFs saved to: {system.pdf_storage}")
    logger.info(f"✅ Email digest: {system.week_dir / 'email_digest.txt'}")
    logger.info(f"✅ Total time: {(time.time() - start_time) / 60:.1f} minutes")
    
    # Clean up old extractions (keep last 4 weeks)
    logger.info("\n🧹 Cleaning up old extractions...")
    system.cleanup_old_extractions(keep_weeks=4)
    
    logger.info("\n✨ Weekly extraction completed successfully!")
    
    # Return paths for use in automation
    return {
        'week_dir': system.week_dir,
        'email_digest': system.week_dir / 'email_digest.txt',
        'final_summary': final_summary_path,
        'pdf_storage': system.pdf_storage
    }


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run weekly referee extraction')
    parser.add_argument('--test', action='store_true', help='Test mode - only process first manuscript')
    parser.add_argument('--no-pdfs', action='store_true', help='Skip PDF downloads')
    parser.add_argument('--check-only', action='store_true', help='Only check current status')
    
    args = parser.parse_args()
    
    if args.check_only:
        # Just show current status
        system = WeeklyExtractionSystem()
        tracker = system.load_download_tracker()
        
        logger.info("📊 CURRENT STATUS")
        logger.info(f"Last extraction: {tracker.get('last_updated', 'Never')}")
        logger.info(f"Manuscript PDFs downloaded: {len(tracker.get('manuscripts', {}))}")
        logger.info(f"Referee reports downloaded: {len(tracker.get('referee_reports', {}))}")
        logger.info(f"PDF storage location: {system.pdf_storage}")
        logger.info(f"Total PDFs in storage: {len(list(system.pdf_storage.rglob('*.pdf')))}")
        
        # Show recent PDFs
        recent_pdfs = sorted(system.pdf_storage.rglob('*.pdf'), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        if recent_pdfs:
            logger.info("\nRecent PDFs:")
            for pdf in recent_pdfs:
                logger.info(f"  - {pdf.name} ({pdf.stat().st_size:,} bytes)")
    else:
        # Run full extraction
        main()