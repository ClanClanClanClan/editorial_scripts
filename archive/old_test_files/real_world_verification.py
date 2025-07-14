#!/usr/bin/env python3
"""
Real-world verification test for all 4 journals
This script actually extracts data and provides detailed referee information
"""

import sys
import json
import time
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RealWorldVerifier:
    """Real-world verification of all journal capabilities"""
    
    def __init__(self):
        self.results = {
            'SIFIN': {'manuscripts': [], 'errors': [], 'summary': {}},
            'SICON': {'manuscripts': [], 'errors': [], 'summary': {}},
            'MOR': {'manuscripts': [], 'errors': [], 'summary': {}},
            'MF': {'manuscripts': [], 'errors': [], 'summary': {}}
        }
        
        # Create output directory
        self.output_dir = Path("verification_results")
        self.output_dir.mkdir(exist_ok=True)
        
        # Email cross-check data
        self.email_data = {}
        
    def test_journal_real_extraction(self, journal_name: str) -> Dict[str, Any]:
        """Test actual extraction from a journal"""
        print(f"\n{'='*80}")
        print(f"REAL-WORLD EXTRACTION TEST: {journal_name}")
        print(f"{'='*80}")
        
        try:
            if journal_name == 'SIFIN':
                return self._test_sifin_extraction()
            elif journal_name == 'SICON':
                return self._test_sicon_extraction()
            elif journal_name == 'MOR':
                return self._test_mor_extraction()
            elif journal_name == 'MF':
                return self._test_mf_extraction()
            else:
                raise ValueError(f"Unknown journal: {journal_name}")
                
        except Exception as e:
            logger.error(f"Real extraction test failed for {journal_name}: {e}")
            return {
                'status': 'FAILED',
                'error': str(e),
                'manuscripts': [],
                'referee_count': 0,
                'email_count': 0
            }
    
    def _test_sifin_extraction(self) -> Dict[str, Any]:
        """Test SIFIN real extraction"""
        print("🔍 Testing SIFIN actual extraction...")
        
        try:
            from journals.sifin import SIFIN
            
            sifin = SIFIN()
            sifin.setup_driver(headless=True)
            
            print("📋 Authenticating...")
            if not sifin.authenticate():
                return {
                    'status': 'FAILED',
                    'error': 'Authentication failed',
                    'manuscripts': [],
                    'referee_count': 0,
                    'email_count': 0
                }
            
            print("📋 Extracting manuscripts...")
            manuscripts = sifin.extract_manuscripts()
            
            if not manuscripts:
                return {
                    'status': 'FAILED',
                    'error': 'No manuscripts found',
                    'manuscripts': [],
                    'referee_count': 0,
                    'email_count': 0
                }
            
            print(f"📋 Found {len(manuscripts)} manuscripts")
            
            # Process each manuscript for detailed information
            detailed_manuscripts = []
            total_referees = 0
            total_emails = 0
            total_cover_letters = 0
            total_referee_reports = 0
            
            for manuscript in manuscripts:
                ms_data = {
                    'manuscript_id': manuscript.get('id', 'Unknown'),
                    'title': manuscript.get('title', 'Unknown'),
                    'submission_date': manuscript.get('submission_date', 'Unknown'),
                    'referees': [],
                    'documents': {
                        'pdf': manuscript.get('pdf_url', None),
                        'cover_letter': manuscript.get('cover_letter_url', None),
                        'referee_reports': manuscript.get('documents', {}).get('referee_reports', [])
                    }
                }
                
                # Process referees
                referees = manuscript.get('referees', [])
                for referee in referees:
                    referee_data = {
                        'name': referee.get('name', 'Unknown'),
                        'institution': referee.get('institution', 'Unknown'),
                        'email': referee.get('email', 'NOT FOUND'),
                        'status': referee.get('status', 'Unknown'),
                        'contact_date': referee.get('invited_date', 'Unknown'),
                        'acceptance_date': referee.get('accepted_date', 'Unknown'),
                        'due_date': referee.get('due_date', 'Unknown'),
                        'report_received_date': referee.get('report_submitted_date', 'Unknown'),
                        'decline_date': referee.get('declined_date', 'Unknown')
                    }
                    
                    ms_data['referees'].append(referee_data)
                    total_referees += 1
                    
                    if referee_data['email'] != 'NOT FOUND':
                        total_emails += 1
                
                # Count documents
                if ms_data['documents']['pdf']:
                    # PDFs are always found for SIFIN
                    pass
                if ms_data['documents']['cover_letter']:
                    total_cover_letters += 1
                total_referee_reports += len(ms_data['documents']['referee_reports'])
                
                detailed_manuscripts.append(ms_data)
            
            sifin.driver.quit()
            
            return {
                'status': 'SUCCESS',
                'manuscripts': detailed_manuscripts,
                'summary': {
                    'total_manuscripts': len(manuscripts),
                    'total_referees': total_referees,
                    'total_emails_found': total_emails,
                    'email_success_rate': f"{total_emails}/{total_referees} ({total_emails/total_referees*100:.1f}%)" if total_referees > 0 else "0/0 (0%)",
                    'total_cover_letters': total_cover_letters,
                    'total_referee_reports': total_referee_reports
                }
            }
            
        except Exception as e:
            logger.error(f"SIFIN extraction failed: {e}")
            return {
                'status': 'FAILED',
                'error': str(e),
                'manuscripts': [],
                'referee_count': 0,
                'email_count': 0
            }
    
    def _test_sicon_extraction(self) -> Dict[str, Any]:
        """Test SICON real extraction"""
        print("🔍 Testing SICON actual extraction...")
        
        try:
            from journals.sicon import SICON
            
            sicon = SICON()
            sicon.setup_driver(headless=True)
            
            print("📋 Authenticating...")
            if not sicon.authenticate():
                return {
                    'status': 'FAILED',
                    'error': 'Authentication failed',
                    'manuscripts': [],
                    'referee_count': 0,
                    'email_count': 0
                }
            
            print("📋 Extracting manuscripts...")
            manuscripts = sicon.extract_manuscripts()
            
            if not manuscripts:
                return {
                    'status': 'FAILED',
                    'error': 'No manuscripts found',
                    'manuscripts': [],
                    'referee_count': 0,
                    'email_count': 0
                }
            
            print(f"📋 Found {len(manuscripts)} manuscripts")
            
            # Process each manuscript for detailed information
            detailed_manuscripts = []
            total_referees = 0
            total_emails = 0
            total_cover_letters = 0
            total_referee_reports = 0
            
            for manuscript in manuscripts:
                ms_data = {
                    'manuscript_id': manuscript.get('id', 'Unknown'),
                    'title': manuscript.get('title', 'Unknown'),
                    'submission_date': manuscript.get('submission_date', 'Unknown'),
                    'referees': [],
                    'documents': {
                        'pdf': manuscript.get('pdf_url', None),
                        'cover_letter': manuscript.get('cover_letter_url', None),
                        'referee_reports': manuscript.get('documents', {}).get('referee_reports', [])
                    }
                }
                
                # Process referees
                referees = manuscript.get('referees', [])
                for referee in referees:
                    referee_data = {
                        'name': referee.get('name', 'Unknown'),
                        'institution': referee.get('institution', 'Unknown'),
                        'email': referee.get('email', 'NOT FOUND'),
                        'status': referee.get('status', 'Unknown'),
                        'contact_date': referee.get('invited_date', 'Unknown'),
                        'acceptance_date': referee.get('accepted_date', 'Unknown'),
                        'due_date': referee.get('due_date', 'Unknown'),
                        'report_received_date': referee.get('report_submitted_date', 'Unknown'),
                        'decline_date': referee.get('declined_date', 'Unknown')
                    }
                    
                    ms_data['referees'].append(referee_data)
                    total_referees += 1
                    
                    if referee_data['email'] != 'NOT FOUND':
                        total_emails += 1
                
                # Count documents
                if ms_data['documents']['cover_letter']:
                    total_cover_letters += 1
                total_referee_reports += len(ms_data['documents']['referee_reports'])
                
                detailed_manuscripts.append(ms_data)
            
            sicon.driver.quit()
            
            return {
                'status': 'SUCCESS',
                'manuscripts': detailed_manuscripts,
                'summary': {
                    'total_manuscripts': len(manuscripts),
                    'total_referees': total_referees,
                    'total_emails_found': total_emails,
                    'email_success_rate': f"{total_emails}/{total_referees} ({total_emails/total_referees*100:.1f}%)" if total_referees > 0 else "0/0 (0%)",
                    'total_cover_letters': total_cover_letters,
                    'total_referee_reports': total_referee_reports
                }
            }
            
        except Exception as e:
            logger.error(f"SICON extraction failed: {e}")
            return {
                'status': 'FAILED',
                'error': str(e),
                'manuscripts': [],
                'referee_count': 0,
                'email_count': 0
            }
    
    def _test_mor_extraction(self) -> Dict[str, Any]:
        """Test MOR real extraction"""
        print("🔍 Testing MOR actual extraction...")
        
        try:
            from journals.mor import MORJournal
            from selenium import webdriver
            
            # Initialize Chrome driver
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(options=options)
            
            mor = MORJournal(driver, debug=False)
            
            print("📋 Extracting manuscripts and emails...")
            manuscripts = mor.scrape_manuscripts_and_emails()
            
            if not manuscripts:
                return {
                    'status': 'FAILED',
                    'error': 'No manuscripts found',
                    'manuscripts': [],
                    'referee_count': 0,
                    'email_count': 0
                }
            
            print(f"📋 Found {len(manuscripts)} manuscripts")
            
            # Process each manuscript for detailed information
            detailed_manuscripts = []
            total_referees = 0
            total_emails = 0
            total_cover_letters = 0
            total_referee_reports = 0
            
            for manuscript in manuscripts:
                ms_data = {
                    'manuscript_id': manuscript.get('Manuscript #', 'Unknown'),
                    'title': manuscript.get('Title', 'Unknown'),
                    'submission_date': manuscript.get('Submission Date', 'Unknown'),
                    'contact_author': manuscript.get('Contact Author', 'Unknown'),
                    'referees': [],
                    'documents': {
                        'cover_letters': manuscript.get('Cover Letters', []),
                        'referee_reports': manuscript.get('Referee Reports', [])
                    }
                }
                
                # Process referees
                referees = manuscript.get('Referees', [])
                for referee in referees:
                    referee_data = {
                        'name': referee.get('Referee Name', 'Unknown'),
                        'institution': 'Unknown',  # MOR doesn't extract institution
                        'email': referee.get('Email', 'NOT FOUND'),
                        'status': referee.get('Status', 'Unknown'),
                        'contact_date': referee.get('Contacted Date', 'Unknown'),
                        'acceptance_date': referee.get('Accepted Date', 'Unknown'),
                        'due_date': referee.get('Due Date', 'Unknown'),
                        'report_received_date': 'Unknown',  # MOR doesn't track this specifically
                        'decline_date': 'Unknown',  # MOR doesn't track this specifically
                        'lateness': referee.get('Lateness', '')
                    }
                    
                    ms_data['referees'].append(referee_data)
                    total_referees += 1
                    
                    if referee_data['email'] != 'NOT FOUND':
                        total_emails += 1
                
                # Count documents
                total_cover_letters += len(ms_data['documents']['cover_letters'])
                total_referee_reports += len(ms_data['documents']['referee_reports'])
                
                detailed_manuscripts.append(ms_data)
            
            driver.quit()
            
            return {
                'status': 'SUCCESS',
                'manuscripts': detailed_manuscripts,
                'summary': {
                    'total_manuscripts': len(manuscripts),
                    'total_referees': total_referees,
                    'total_emails_found': total_emails,
                    'email_success_rate': f"{total_emails}/{total_referees} ({total_emails/total_referees*100:.1f}%)" if total_referees > 0 else "0/0 (0%)",
                    'total_cover_letters': total_cover_letters,
                    'total_referee_reports': total_referee_reports
                }
            }
            
        except Exception as e:
            logger.error(f"MOR extraction failed: {e}")
            return {
                'status': 'FAILED',
                'error': str(e),
                'manuscripts': [],
                'referee_count': 0,
                'email_count': 0
            }
    
    def _test_mf_extraction(self) -> Dict[str, Any]:
        """Test MF real extraction"""
        print("🔍 Testing MF actual extraction...")
        
        try:
            from journals.mf import MFJournal
            from selenium import webdriver
            
            # Initialize Chrome driver
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            driver = webdriver.Chrome(options=options)
            
            mf = MFJournal(driver, debug=False)
            
            print("📋 Extracting manuscripts and emails...")
            manuscripts = mf.scrape_manuscripts_and_emails()
            
            if not manuscripts:
                return {
                    'status': 'FAILED',
                    'error': 'No manuscripts found',
                    'manuscripts': [],
                    'referee_count': 0,
                    'email_count': 0
                }
            
            print(f"📋 Found {len(manuscripts)} manuscripts")
            
            # Process each manuscript for detailed information
            detailed_manuscripts = []
            total_referees = 0
            total_emails = 0
            total_cover_letters = 0
            total_referee_reports = 0
            
            for manuscript in manuscripts:
                ms_data = {
                    'manuscript_id': manuscript.get('Manuscript #', 'Unknown'),
                    'title': manuscript.get('Title', 'Unknown'),
                    'submission_date': manuscript.get('Submission Date', 'Unknown'),
                    'contact_author': manuscript.get('Contact Author', 'Unknown'),
                    'referees': [],
                    'documents': {
                        'cover_letters': manuscript.get('Cover Letters', []),
                        'referee_reports': manuscript.get('Referee Reports', [])
                    }
                }
                
                # Process referees
                referees = manuscript.get('Referees', [])
                for referee in referees:
                    referee_data = {
                        'name': referee.get('Referee Name', 'Unknown'),
                        'institution': 'Unknown',  # MF doesn't extract institution
                        'email': referee.get('Email', 'NOT FOUND'),
                        'status': referee.get('Status', 'Unknown'),
                        'contact_date': referee.get('Contacted Date', 'Unknown'),
                        'acceptance_date': referee.get('Accepted Date', 'Unknown'),
                        'due_date': referee.get('Due Date', 'Unknown'),
                        'report_received_date': 'Unknown',  # MF doesn't track this specifically
                        'decline_date': 'Unknown',  # MF doesn't track this specifically
                        'lateness': referee.get('Lateness', '')
                    }
                    
                    ms_data['referees'].append(referee_data)
                    total_referees += 1
                    
                    if referee_data['email'] != 'NOT FOUND':
                        total_emails += 1
                
                # Count documents
                total_cover_letters += len(ms_data['documents']['cover_letters'])
                total_referee_reports += len(ms_data['documents']['referee_reports'])
                
                detailed_manuscripts.append(ms_data)
            
            driver.quit()
            
            return {
                'status': 'SUCCESS',
                'manuscripts': detailed_manuscripts,
                'summary': {
                    'total_manuscripts': len(manuscripts),
                    'total_referees': total_referees,
                    'total_emails_found': total_emails,
                    'email_success_rate': f"{total_emails}/{total_referees} ({total_emails/total_referees*100:.1f}%)" if total_referees > 0 else "0/0 (0%)",
                    'total_cover_letters': total_cover_letters,
                    'total_referee_reports': total_referee_reports
                }
            }
            
        except Exception as e:
            logger.error(f"MF extraction failed: {e}")
            return {
                'status': 'FAILED',
                'error': str(e),
                'manuscripts': [],
                'referee_count': 0,
                'email_count': 0
            }
    
    def cross_check_with_emails(self):
        """Cross-check extracted data with email records"""
        print(f"\n{'='*80}")
        print("CROSS-CHECKING WITH EMAIL RECORDS")
        print(f"{'='*80}")
        
        try:
            # Try to fetch email data for cross-checking
            print("📧 Fetching email data for cross-checking...")
            
            # This would use the same email utilities as the journals
            from core.email_utils import fetch_starred_emails
            
            email_checks = {}
            
            for journal in ['SIFIN', 'SICON', 'MOR', 'MF']:
                try:
                    print(f"📧 Fetching {journal} emails...")
                    emails = fetch_starred_emails(journal)
                    email_checks[journal] = {
                        'total_emails': len(emails),
                        'emails': emails
                    }
                    print(f"   Found {len(emails)} starred emails for {journal}")
                except Exception as e:
                    print(f"   ⚠️ Could not fetch emails for {journal}: {e}")
                    email_checks[journal] = {
                        'total_emails': 0,
                        'emails': [],
                        'error': str(e)
                    }
            
            self.email_data = email_checks
            
        except Exception as e:
            logger.error(f"Email cross-check failed: {e}")
            self.email_data = {'error': str(e)}
    
    def generate_detailed_report(self):
        """Generate detailed verification report"""
        print(f"\n{'='*80}")
        print("GENERATING DETAILED VERIFICATION REPORT")
        print(f"{'='*80}")
        
        # Create CSV files for each journal
        for journal_name, journal_data in self.results.items():
            if journal_data['manuscripts']:
                self._create_csv_report(journal_name, journal_data)
        
        # Create summary report
        self._create_summary_report()
        
        # Create email cross-check report
        self._create_email_crosscheck_report()
        
        print(f"\n📄 All reports saved to: {self.output_dir}")
    
    def _create_csv_report(self, journal_name: str, journal_data: Dict):
        """Create CSV report for a journal"""
        csv_file = self.output_dir / f"{journal_name}_referee_details.csv"
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Headers
            writer.writerow([
                'Manuscript ID', 'Title', 'Submission Date', 'Contact Author',
                'Referee Name', 'Institution', 'Email', 'Status',
                'Contact Date', 'Acceptance Date', 'Due Date',
                'Report Received Date', 'Decline Date', 'Lateness'
            ])
            
            # Data rows
            for manuscript in journal_data['manuscripts']:
                ms_id = manuscript['manuscript_id']
                title = manuscript['title']
                submission_date = manuscript['submission_date']
                contact_author = manuscript.get('contact_author', 'Unknown')
                
                for referee in manuscript['referees']:
                    writer.writerow([
                        ms_id, title, submission_date, contact_author,
                        referee['name'], referee['institution'], referee['email'],
                        referee['status'], referee['contact_date'],
                        referee['acceptance_date'], referee['due_date'],
                        referee['report_received_date'], referee['decline_date'],
                        referee.get('lateness', '')
                    ])
        
        print(f"📄 Created CSV report: {csv_file}")
    
    def _create_summary_report(self):
        """Create summary report"""
        summary_file = self.output_dir / "summary_report.txt"
        
        with open(summary_file, 'w') as f:
            f.write("REAL-WORLD VERIFICATION SUMMARY REPORT\n")
            f.write("="*60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for journal_name, journal_data in self.results.items():
                f.write(f"{journal_name} RESULTS:\n")
                f.write("-"*40 + "\n")
                
                if journal_data.get('summary'):
                    summary = journal_data['summary']
                    f.write(f"Status: {journal_data.get('status', 'Unknown')}\n")
                    f.write(f"Total Manuscripts: {summary.get('total_manuscripts', 0)}\n")
                    f.write(f"Total Referees: {summary.get('total_referees', 0)}\n")
                    f.write(f"Email Success Rate: {summary.get('email_success_rate', '0/0 (0%)')}\n")
                    f.write(f"Cover Letters Found: {summary.get('total_cover_letters', 0)}\n")
                    f.write(f"Referee Reports Found: {summary.get('total_referee_reports', 0)}\n")
                else:
                    f.write(f"Status: {journal_data.get('status', 'Unknown')}\n")
                    if journal_data.get('error'):
                        f.write(f"Error: {journal_data['error']}\n")
                
                f.write("\n")
        
        print(f"📄 Created summary report: {summary_file}")
    
    def _create_email_crosscheck_report(self):
        """Create email cross-check report"""
        email_file = self.output_dir / "email_crosscheck_report.txt"
        
        with open(email_file, 'w') as f:
            f.write("EMAIL CROSS-CHECK REPORT\n")
            f.write("="*60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if self.email_data:
                for journal_name, email_info in self.email_data.items():
                    f.write(f"{journal_name} EMAIL DATA:\n")
                    f.write("-"*40 + "\n")
                    
                    if 'error' in email_info:
                        f.write(f"Error: {email_info['error']}\n")
                    else:
                        f.write(f"Total Starred Emails: {email_info.get('total_emails', 0)}\n")
                        
                        # Cross-check with extracted referees
                        if journal_name in self.results and self.results[journal_name]['manuscripts']:
                            extracted_emails = []
                            for manuscript in self.results[journal_name]['manuscripts']:
                                for referee in manuscript['referees']:
                                    if referee['email'] != 'NOT FOUND':
                                        extracted_emails.append(referee['email'])
                            
                            f.write(f"Extracted Referee Emails: {len(extracted_emails)}\n")
                            f.write(f"Unique Extracted Emails: {len(set(extracted_emails))}\n")
                    
                    f.write("\n")
            else:
                f.write("No email data available for cross-checking\n")
        
        print(f"📄 Created email cross-check report: {email_file}")
    
    def run_full_verification(self):
        """Run complete real-world verification"""
        print("🔍 STARTING REAL-WORLD VERIFICATION OF ALL JOURNALS")
        print("This will actually extract data from all journals and provide detailed information")
        
        journals = ['SIFIN', 'SICON', 'MOR', 'MF']
        
        for journal in journals:
            print(f"\n🔄 Processing {journal}...")
            try:
                result = self.test_journal_real_extraction(journal)
                self.results[journal] = result
                
                if result['status'] == 'SUCCESS':
                    print(f"✅ {journal} extraction successful")
                    print(f"   Manuscripts: {result['summary']['total_manuscripts']}")
                    print(f"   Referees: {result['summary']['total_referees']}")
                    print(f"   Email Success: {result['summary']['email_success_rate']}")
                else:
                    print(f"❌ {journal} extraction failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Verification failed for {journal}: {e}")
                self.results[journal] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'manuscripts': [],
                    'summary': {}
                }
        
        # Cross-check with emails
        self.cross_check_with_emails()
        
        # Generate reports
        self.generate_detailed_report()
        
        # Final summary
        self._print_final_summary()
    
    def _print_final_summary(self):
        """Print final verification summary"""
        print(f"\n{'='*80}")
        print("FINAL REAL-WORLD VERIFICATION SUMMARY")
        print(f"{'='*80}")
        
        for journal_name, journal_data in self.results.items():
            print(f"\n📊 {journal_name} RESULTS:")
            
            if journal_data['status'] == 'SUCCESS':
                summary = journal_data['summary']
                print(f"   ✅ Status: SUCCESS")
                print(f"   📄 Manuscripts: {summary['total_manuscripts']}")
                print(f"   👥 Referees: {summary['total_referees']}")
                print(f"   📧 Email Success: {summary['email_success_rate']}")
                print(f"   📝 Cover Letters: {summary['total_cover_letters']}")
                print(f"   📋 Referee Reports: {summary['total_referee_reports']}")
            else:
                print(f"   ❌ Status: FAILED")
                print(f"   Error: {journal_data.get('error', 'Unknown error')}")
        
        print(f"\n📄 Detailed results saved to: {self.output_dir}")
        print(f"{'='*80}")

def main():
    """Main verification function"""
    verifier = RealWorldVerifier()
    verifier.run_full_verification()

if __name__ == "__main__":
    main()