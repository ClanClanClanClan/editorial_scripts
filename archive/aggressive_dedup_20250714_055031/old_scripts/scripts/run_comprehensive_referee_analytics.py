#!/usr/bin/env python3
"""
Comprehensive Referee Analytics Runner
Extracts all referee data, cross-checks with Gmail, and generates analytics
"""

import asyncio
import os
import sys
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.referee_analytics import RefereeAnalytics, RefereeTimeline
from src.infrastructure.gmail_integration import GmailRefereeTracker
from src.infrastructure.scrapers.enhanced_referee_extractor import EnhancedRefereeExtractor
from src.infrastructure.scrapers.siam_scraper import SIAMScraper
from src.infrastructure.scrapers.mf_scraper_fixed import MFScraperFixed
from src.infrastructure.scrapers.mor_scraper_fixed import MORScraperFixed

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveRefereeAnalyzer:
    """Main analyzer that orchestrates everything"""
    
    def __init__(self):
        self.analytics = RefereeAnalytics()
        self.gmail_tracker = None
        self.results_dir = Path.home() / '.editorial_scripts' / 'analytics'
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    async def run_complete_analysis(self):
        """Run complete referee analysis for all journals"""
        logger.info("🚀 Starting Comprehensive Referee Analytics")
        logger.info("=" * 60)
        
        # Set credentials
        os.environ['ORCID_EMAIL'] = 'dylan.possamai@polytechnique.org'
        os.environ['ORCID_PASSWORD'] = 'Hioupy0042%'
        
        # Initialize Gmail if credentials exist
        if os.path.exists('credentials.json'):
            try:
                self.gmail_tracker = GmailRefereeTracker()
                logger.info("✅ Gmail integration initialized")
            except Exception as e:
                logger.warning(f"⚠️ Gmail integration failed: {e}")
        
        # Process each journal
        all_manuscripts = {}
        
        # SIAM Journals (SICON, SIFIN)
        for journal_code in ['SIFIN', 'SICON']:
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 Processing {journal_code}")
            logger.info(f"{'='*60}")
            
            manuscripts = await self.process_siam_journal(journal_code)
            all_manuscripts[journal_code] = manuscripts
        
        # ScholarOne Journals (MF, MOR) - if credentials available
        if os.environ.get('MF_USER') or os.environ.get('SCHOLARONE_USER'):
            for journal_code, scraper_class in [('MF', MFScraperFixed), ('MOR', MORScraperFixed)]:
                logger.info(f"\n{'='*60}")
                logger.info(f"📊 Processing {journal_code}")
                logger.info(f"{'='*60}")
                
                manuscripts = await self.process_scholarone_journal(journal_code, scraper_class)
                all_manuscripts[journal_code] = manuscripts
        
        # Cross-check with Gmail
        if self.gmail_tracker:
            logger.info("\n📧 Cross-checking with Gmail...")
            await self.cross_check_with_gmail(all_manuscripts)
        
        # Generate analytics
        logger.info("\n📊 Generating Analytics...")
        self.generate_comprehensive_report(all_manuscripts)
        
        logger.info("\n✅ Analysis Complete!")
        logger.info(f"📁 Results saved to: {self.results_dir}")
    
    async def process_siam_journal(self, journal_code: str) -> List[Dict]:
        """Process a SIAM journal"""
        manuscripts = []
        
        try:
            # Create scraper
            scraper = SIAMScraper(journal_code)
            
            # Create browser
            browser = await scraper.create_browser()
            context = await scraper.setup_browser_context(browser)
            page = await context.new_page()
            
            # Authenticate
            if await scraper.authenticate(page):
                logger.info(f"✅ Authenticated to {journal_code}")
                
                # Extract manuscripts
                result = await scraper.extract_manuscripts(page)
                
                # Create referee extractor
                extractor = EnhancedRefereeExtractor(
                    journal_code,
                    scraper.config.base_url
                )
                
                # Process each manuscript
                for ms in result:
                    logger.info(f"\n📄 Processing manuscript: {ms.id}")
                    
                    # Extract referee timelines
                    timelines = await extractor.extract_referee_timeline_siam(page, ms.id)
                    
                    # Download all documents
                    documents = await extractor.download_all_manuscript_documents(page, ms.id)
                    
                    # Add to analytics
                    for timeline in timelines:
                        self.analytics.add_timeline(timeline)
                    
                    manuscripts.append({
                        'id': ms.id,
                        'title': ms.title,
                        'referee_count': len(timelines),
                        'documents': documents,
                        'timelines': timelines
                    })
                    
                    logger.info(f"   ✅ Found {len(timelines)} referees")
                    logger.info(f"   📎 Downloaded: {len(documents['manuscript_pdfs'])} manuscripts, "
                              f"{len(documents['cover_letters'])} covers, "
                              f"{len(documents['referee_reports'])} reports")
            
            await context.close()
            await browser.close()
            
        except Exception as e:
            logger.error(f"Error processing {journal_code}: {e}")
        
        return manuscripts
    
    async def process_scholarone_journal(self, journal_code: str, scraper_class) -> List[Dict]:
        """Process a ScholarOne journal"""
        manuscripts = []
        
        try:
            # Create scraper
            scraper = scraper_class()
            
            # Create browser
            browser = await scraper.create_browser()
            context = await scraper.setup_browser_context(browser)
            page = await context.new_page()
            
            # Authenticate
            if await scraper.authenticate(page):
                logger.info(f"✅ Authenticated to {journal_code}")
                
                # Extract manuscripts
                result = await scraper.extract_manuscripts(page)
                
                # Create referee extractor
                extractor = EnhancedRefereeExtractor(
                    journal_code,
                    scraper.base_url
                )
                
                # Process each manuscript
                for ms in result:
                    logger.info(f"\n📄 Processing manuscript: {ms.id}")
                    
                    # Extract referee timelines
                    timelines = await extractor.extract_referee_timeline_scholarone(page, ms.id)
                    
                    # Download all documents
                    documents = await extractor.download_all_manuscript_documents(page, ms.id)
                    
                    # Add to analytics
                    for timeline in timelines:
                        self.analytics.add_timeline(timeline)
                    
                    manuscripts.append({
                        'id': ms.id,
                        'title': ms.title,
                        'referee_count': len(timelines),
                        'documents': documents,
                        'timelines': timelines
                    })
                    
                    logger.info(f"   ✅ Found {len(timelines)} referees")
                    logger.info(f"   📎 Downloaded: {len(documents['manuscript_pdfs'])} manuscripts, "
                              f"{len(documents['cover_letters'])} covers, "
                              f"{len(documents['referee_reports'])} reports")
            
            await context.close()
            await browser.close()
            
        except Exception as e:
            logger.error(f"Error processing {journal_code}: {e}")
        
        return manuscripts
    
    async def cross_check_with_gmail(self, all_manuscripts: Dict[str, List]):
        """Cross-check referee data with Gmail"""
        # Get date range (last 6 months)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        date_range = (start_date, end_date)
        
        # Process each referee
        for journal_code, manuscripts in all_manuscripts.items():
            for ms in manuscripts:
                for timeline in ms.get('timelines', []):
                    # Search for emails
                    emails = self.gmail_tracker.search_referee_emails(
                        timeline.email,
                        ms['id'],
                        journal_code,
                        date_range
                    )
                    
                    if emails:
                        logger.info(f"   📧 Found {len(emails)} emails for {timeline.name}")
                        
                        # Analyze emails
                        gmail_timeline = self.gmail_tracker.analyze_referee_timeline(
                            emails,
                            timeline.email,
                            ms['id']
                        )
                        
                        # Merge Gmail data
                        self._merge_gmail_data(timeline, gmail_timeline)
        
        # Find missing referees
        all_referees = []
        for manuscripts in all_manuscripts.values():
            for ms in manuscripts:
                for timeline in ms.get('timelines', []):
                    all_referees.append({
                        'email': timeline.email,
                        'name': timeline.name
                    })
        
        missing = self.gmail_tracker.find_missing_referee_emails(all_referees, date_range)
        if missing:
            logger.warning(f"⚠️ Found {len(missing)} referees in Gmail not in scraped data")
            self._save_missing_referees(missing)
    
    def _merge_gmail_data(self, timeline: RefereeTimeline, gmail_timeline: RefereeTimeline):
        """Merge Gmail data into referee timeline"""
        # Update event counts from Gmail
        if gmail_timeline.invitation_emails_sent > timeline.invitation_emails_sent:
            timeline.invitation_emails_sent = gmail_timeline.invitation_emails_sent
        
        if gmail_timeline.reminder_emails_sent > timeline.reminder_emails_sent:
            timeline.reminder_emails_sent = gmail_timeline.reminder_emails_sent
        
        # Add Gmail events
        for event in gmail_timeline.events:
            # Check if we already have this event
            existing = any(e.date == event.date and e.event_type == event.event_type 
                          for e in timeline.events)
            if not existing:
                timeline.add_event(event)
        
        # Add Gmail thread IDs
        timeline.gmail_thread_ids.extend(gmail_timeline.gmail_thread_ids)
        timeline.gmail_verified = True
    
    def generate_comprehensive_report(self, all_manuscripts: Dict[str, List]):
        """Generate comprehensive analytics report"""
        # Overall statistics
        overall_stats = self.analytics.get_overall_stats()
        
        # Save overall report
        report = {
            'generated_at': datetime.now().isoformat(),
            'overall_statistics': overall_stats,
            'journal_statistics': {},
            'top_referees': self._get_top_referees(),
            'problem_referees': self._get_problem_referees(),
            'document_statistics': self._get_document_stats(all_manuscripts)
        }
        
        # Add journal-specific stats
        for journal_code in ['SICON', 'SIFIN', 'MF', 'MOR']:
            journal_stats = self.analytics.get_journal_stats(journal_code)
            if journal_stats:
                report['journal_statistics'][journal_code] = journal_stats
        
        # Save main report
        report_file = self.results_dir / f"referee_analytics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Save detailed referee data
        self._save_referee_details()
        
        # Generate summary
        self._print_summary(report)
    
    def _get_top_referees(self, limit: int = 10) -> List[Dict]:
        """Get top performing referees"""
        referee_emails = set(t.email for t in self.analytics.timelines.values())
        performances = []
        
        for email in referee_emails:
            perf = self.analytics.get_referee_performance(email)
            if perf and perf['completed'] > 0:
                performances.append(perf)
        
        # Sort by completion rate and number of reviews
        performances.sort(key=lambda p: (p['completion_rate'], p['completed']), reverse=True)
        
        return performances[:limit]
    
    def _get_problem_referees(self) -> List[Dict]:
        """Get referees with issues"""
        problems = []
        
        for timeline in self.analytics.timelines.values():
            issues = []
            
            # Check for overdue
            if timeline.is_overdue():
                issues.append('overdue')
            
            # Check for slow response
            response_time = timeline.get_response_time_days()
            if response_time and response_time > 14:
                issues.append(f'slow_response ({response_time} days)')
            
            # Check for many reminders
            if timeline.reminder_emails_sent > 3:
                issues.append(f'many_reminders ({timeline.reminder_emails_sent})')
            
            if issues:
                problems.append({
                    'name': timeline.name,
                    'email': timeline.email,
                    'manuscript': timeline.manuscript_id,
                    'journal': timeline.journal_code,
                    'issues': issues
                })
        
        return problems
    
    def _get_document_stats(self, all_manuscripts: Dict[str, List]) -> Dict:
        """Get document download statistics"""
        stats = {
            'total_manuscripts': 0,
            'total_cover_letters': 0,
            'total_referee_reports': 0,
            'by_journal': {}
        }
        
        for journal_code, manuscripts in all_manuscripts.items():
            journal_stats = {
                'manuscripts': 0,
                'cover_letters': 0,
                'referee_reports': 0
            }
            
            for ms in manuscripts:
                docs = ms.get('documents', {})
                journal_stats['manuscripts'] += len(docs.get('manuscript_pdfs', []))
                journal_stats['cover_letters'] += len(docs.get('cover_letters', []))
                journal_stats['referee_reports'] += len(docs.get('referee_reports', []))
            
            stats['by_journal'][journal_code] = journal_stats
            stats['total_manuscripts'] += journal_stats['manuscripts']
            stats['total_cover_letters'] += journal_stats['cover_letters']
            stats['total_referee_reports'] += journal_stats['referee_reports']
        
        return stats
    
    def _save_referee_details(self):
        """Save detailed referee information"""
        # Convert all timelines to dictionaries
        details = []
        
        for timeline in self.analytics.timelines.values():
            detail = timeline.to_analytics_dict()
            detail['events'] = [
                {
                    'type': e.event_type.value,
                    'date': e.date.isoformat() if e.date else None,
                    'details': e.details
                }
                for e in timeline.events
            ]
            details.append(detail)
        
        # Save to file
        details_file = self.results_dir / f"referee_details_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(details_file, 'w') as f:
            json.dump(details, f, indent=2)
    
    def _save_missing_referees(self, missing: List[Dict]):
        """Save missing referees found in Gmail"""
        file_path = self.results_dir / "missing_referees_from_gmail.json"
        with open(file_path, 'w') as f:
            json.dump({
                'found_at': datetime.now().isoformat(),
                'count': len(missing),
                'referees': missing
            }, f, indent=2)
    
    def _print_summary(self, report: Dict):
        """Print summary to console"""
        print("\n" + "="*60)
        print("📊 REFEREE ANALYTICS SUMMARY")
        print("="*60)
        
        overall = report['overall_statistics']['overall']
        print(f"\n📈 Overall Statistics:")
        print(f"   Total Referees: {overall['total_referees']}")
        print(f"   Unique Referees: {overall['unique_referees']}")
        print(f"   Total Reports: {overall['total_reports']}")
        print(f"   Gmail Verified: {overall['gmail_verified']}")
        
        print(f"\n📎 Document Statistics:")
        docs = report['document_statistics']
        print(f"   Manuscripts: {docs['total_manuscripts']}")
        print(f"   Cover Letters: {docs['total_cover_letters']}")
        print(f"   Referee Reports: {docs['total_referee_reports']}")
        
        print(f"\n📊 By Journal:")
        for journal, stats in report['journal_statistics'].items():
            print(f"\n   {journal}:")
            print(f"      Referees: {stats['total_referees']}")
            print(f"      Acceptance Rate: {stats['acceptance_rate']:.1f}%")
            print(f"      Completion Rate: {stats['completion_rate']:.1f}%")
            print(f"      Avg Response Time: {stats['avg_response_time_days']} days")
            print(f"      Avg Review Time: {stats['avg_review_time_days']} days")
        
        if report.get('top_referees'):
            print(f"\n🌟 Top Referees:")
            for i, ref in enumerate(report['top_referees'][:5], 1):
                print(f"   {i}. {ref['name']} - {ref['completed']} reviews, "
                      f"{ref['completion_rate']:.0f}% completion rate")
        
        problems = report.get('problem_referees', [])
        if problems:
            print(f"\n⚠️ Problem Referees: {len(problems)}")


async def main():
    """Main entry point"""
    analyzer = ComprehensiveRefereeAnalyzer()
    await analyzer.run_complete_analysis()


if __name__ == "__main__":
    asyncio.run(main())