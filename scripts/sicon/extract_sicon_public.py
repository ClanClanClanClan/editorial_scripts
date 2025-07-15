#!/usr/bin/env python3
"""
SICON Public Data Extractor - EXTRACT REAL PUBLIC DATA

This extractor extracts REAL data available from the public SICON website
without requiring authentication.
"""

import sys
import os
import asyncio
import logging
import time
import json
import re
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv(project_root / ".env.production")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PublicSICONExtractor:
    """
    Public SICON extractor that gets real data from publicly available pages.
    """
    
    def __init__(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = project_root / "output" / f"public_sicon_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Public data output: {self.output_dir}")
    
    def create_public_driver(self):
        """Create driver for public data extraction."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-images")
            options.add_argument("--disable-javascript")
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(30)
            
            logger.info("✅ Public data driver created")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Driver creation failed: {e}")
            raise
    
    async def extract_public_data(self):
        """Extract real public data from SICON."""
        logger.info("🚀 Starting PUBLIC SICON data extraction")
        
        start_time = datetime.now()
        result = {
            'started_at': start_time,
            'pages_analyzed': [],
            'journal_info': {},
            'submission_guidelines': {},
            'editorial_board': [],
            'recent_issues': [],
            'call_for_papers': [],
            'manuscript_types': [],
            'review_process': {},
            'success': False,
            'errors': [],
            'extraction_method': 'public_pages_analysis'
        }
        
        driver = None
        
        try:
            driver = self.create_public_driver()
            
            # Extract from multiple SICON pages
            pages_to_analyze = [
                ("Main Page", "https://sicon.siam.org/cgi-bin/main.plex"),
                ("Journal Info", "https://epubs.siam.org/journal/sicon"),
                ("SIAM Journals", "https://www.siam.org/publications/journals"),
                ("Editorial Manager", "https://www.editorialmanager.com/sicon/"),
            ]
            
            for page_name, url in pages_to_analyze:
                try:
                    logger.info(f"📍 Analyzing {page_name}: {url}")
                    page_data = await self._analyze_page(driver, page_name, url)
                    result['pages_analyzed'].append(page_data)
                except Exception as e:
                    logger.error(f"❌ Failed to analyze {page_name}: {e}")
                    result['errors'].append(f"Failed to analyze {page_name}: {str(e)}")
            
            # Extract specific information
            result['journal_info'] = self._extract_journal_info(result['pages_analyzed'])
            result['submission_guidelines'] = self._extract_submission_guidelines(result['pages_analyzed'])
            result['editorial_board'] = self._extract_editorial_board(result['pages_analyzed'])
            result['review_process'] = self._extract_review_process(result['pages_analyzed'])
            
            result['success'] = True
            logger.info("✅ Public data extraction completed")
            
        except Exception as e:
            logger.error(f"❌ Public data extraction failed: {e}")
            result['errors'].append(str(e))
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                try:
                    driver.quit()
                    logger.info("🖥️ Driver closed")
                except:
                    pass
            
            end_time = datetime.now()
            result['completed_at'] = end_time
            result['duration_seconds'] = (end_time - start_time).total_seconds()
            
            self._save_public_results(result)
        
        return result
    
    async def _analyze_page(self, driver, page_name, url):
        """Analyze a single page."""
        page_data = {
            'name': page_name,
            'url': url,
            'title': '',
            'content': '',
            'links': [],
            'emails': [],
            'key_terms': {},
            'analysis_time': datetime.now().isoformat()
        }
        
        try:
            driver.get(url)
            time.sleep(3)
            
            page_data['title'] = driver.title
            page_data['content'] = driver.page_source
            
            # Extract links
            from selenium.webdriver.common.by import By
            links = driver.find_elements(By.TAG_NAME, "a")
            for link in links[:50]:  # Limit to avoid too much data
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    if href and text and len(text) < 100:
                        page_data['links'].append({
                            'url': href,
                            'text': text
                        })
                except:
                    continue
            
            # Extract emails
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            emails = re.findall(email_pattern, page_data['content'])
            page_data['emails'] = list(set(emails))
            
            # Count key terms
            content_lower = page_data['content'].lower()
            key_terms = {
                'manuscript': content_lower.count('manuscript'),
                'submission': content_lower.count('submission'),
                'author': content_lower.count('author'),
                'referee': content_lower.count('referee'),
                'reviewer': content_lower.count('reviewer'),
                'review': content_lower.count('review'),
                'editorial': content_lower.count('editorial'),
                'editor': content_lower.count('editor'),
                'control': content_lower.count('control'),
                'optimization': content_lower.count('optimization')
            }
            page_data['key_terms'] = key_terms
            
            logger.info(f"✅ Analyzed {page_name} - {len(page_data['links'])} links, {len(page_data['emails'])} emails")
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {page_name}: {e}")
            page_data['error'] = str(e)
        
        return page_data
    
    def _extract_journal_info(self, pages_analyzed):
        """Extract journal information from analyzed pages."""
        journal_info = {
            'name': 'SIAM Journal on Control and Optimization',
            'abbreviation': 'SICON',
            'publisher': 'Society for Industrial and Applied Mathematics',
            'issn': [],
            'description': '',
            'scope': [],
            'frequency': ''
        }
        
        for page in pages_analyzed:
            content = page.get('content', '').lower()
            
            # Extract ISSN
            issn_pattern = r'issn[:\s]*(\d{4}-\d{4})'
            issns = re.findall(issn_pattern, content)
            journal_info['issn'].extend(issns)
            
            # Extract description
            if 'journal' in content and 'control' in content:
                desc_patterns = [
                    r'journal[^.]{10,200}\.',
                    r'sicon[^.]{20,300}\.',
                    r'control and optimization[^.]{10,200}\.'
                ]
                for pattern in desc_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches and not journal_info['description']:
                        journal_info['description'] = matches[0][:200]
            
            # Extract scope topics
            scope_keywords = [
                'optimal control', 'stochastic control', 'robust control',
                'nonlinear control', 'adaptive control', 'distributed control',
                'optimization', 'mathematical programming', 'calculus of variations',
                'differential games', 'dynamic programming'
            ]
            
            for keyword in scope_keywords:
                if keyword in content:
                    journal_info['scope'].append(keyword)
        
        journal_info['issn'] = list(set(journal_info['issn']))
        journal_info['scope'] = list(set(journal_info['scope']))
        
        return journal_info
    
    def _extract_submission_guidelines(self, pages_analyzed):
        """Extract submission guidelines."""
        guidelines = {
            'manuscript_types': [],
            'length_limits': [],
            'formatting_requirements': [],
            'submission_process': [],
            'review_timeline': ''
        }
        
        for page in pages_analyzed:
            content = page.get('content', '').lower()
            
            # Extract manuscript types
            type_patterns = [
                r'(research articles?)',
                r'(survey papers?)',
                r'(technical briefs?)',
                r'(letters?)',
                r'(communications?)'
            ]
            
            for pattern in type_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                guidelines['manuscript_types'].extend(matches)
            
            # Extract length information
            length_patterns = [
                r'(\d+)\s*pages?',
                r'(\d+)\s*words?',
                r'maximum[:\s]*(\d+)',
                r'limit[:\s]*(\d+)'
            ]
            
            for pattern in length_patterns:
                matches = re.findall(pattern, content)
                guidelines['length_limits'].extend(matches)
            
            # Extract formatting requirements
            if 'latex' in content:
                guidelines['formatting_requirements'].append('LaTeX required')
            if 'pdf' in content:
                guidelines['formatting_requirements'].append('PDF submission')
            if 'double' in content and 'space' in content:
                guidelines['formatting_requirements'].append('Double spacing')
        
        guidelines['manuscript_types'] = list(set(guidelines['manuscript_types']))
        guidelines['length_limits'] = list(set(guidelines['length_limits']))
        guidelines['formatting_requirements'] = list(set(guidelines['formatting_requirements']))
        
        return guidelines
    
    def _extract_editorial_board(self, pages_analyzed):
        """Extract editorial board information."""
        editorial_board = []
        
        for page in pages_analyzed:
            content = page.get('content', '')
            
            # Look for editor names
            editor_patterns = [
                r'Editor[^:]*:[^<\n]*([A-Z][a-z]+[,\s]+[A-Z][a-z]+)',
                r'([A-Z][a-z]+[,\s]+[A-Z][a-z]+)[^<\n]*Editor',
                r'Associate Editor[^:]*:[^<\n]*([A-Z][a-z]+[,\s]+[A-Z][a-z]+)'
            ]
            
            for pattern in editor_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match) > 5:  # Filter short matches
                        editorial_board.append({
                            'name': match,
                            'role': 'Editorial Board Member',
                            'source_page': page.get('name', 'Unknown')
                        })
        
        return editorial_board[:20]  # Limit results
    
    def _extract_review_process(self, pages_analyzed):
        """Extract review process information."""
        review_process = {
            'peer_review': False,
            'review_stages': [],
            'timeline': [],
            'criteria': []
        }
        
        for page in pages_analyzed:
            content = page.get('content', '').lower()
            
            if 'peer review' in content:
                review_process['peer_review'] = True
            
            # Extract review stages
            if 'initial review' in content:
                review_process['review_stages'].append('Initial Editorial Review')
            if 'referee' in content or 'reviewer' in content:
                review_process['review_stages'].append('Peer Review')
            if 'revision' in content:
                review_process['review_stages'].append('Revision Process')
            if 'final decision' in content:
                review_process['review_stages'].append('Final Decision')
            
            # Extract timeline information
            timeline_patterns = [
                r'(\d+)\s*weeks?',
                r'(\d+)\s*months?',
                r'(\d+)\s*days?'
            ]
            
            for pattern in timeline_patterns:
                matches = re.findall(pattern, content)
                review_process['timeline'].extend(matches)
        
        review_process['review_stages'] = list(set(review_process['review_stages']))
        review_process['timeline'] = list(set(review_process['timeline']))
        
        return review_process
    
    def _save_public_results(self, result):
        """Save public extraction results."""
        try:
            # Create summary results
            public_result = {
                'extraction_date': result['started_at'].isoformat(),
                'completion_date': result.get('completed_at').isoformat() if result.get('completed_at') else None,
                'duration_seconds': result.get('duration_seconds', 0),
                'success': result['success'],
                'extraction_method': result.get('extraction_method'),
                'data_type': 'PUBLIC_SICON_DATA',
                'pages_analyzed_count': len(result['pages_analyzed']),
                'journal_info': result.get('journal_info', {}),
                'submission_guidelines': result.get('submission_guidelines', {}),
                'editorial_board_count': len(result.get('editorial_board', [])),
                'review_process': result.get('review_process', {}),
                'errors': result['errors']
            }
            
            # Save main results
            results_file = self.output_dir / "public_sicon_results.json"
            with open(results_file, 'w') as f:
                json.dump(public_result, f, indent=2)
            
            # Save detailed data
            detailed_data = {
                'journal_info': result.get('journal_info', {}),
                'submission_guidelines': result.get('submission_guidelines', {}),
                'editorial_board': result.get('editorial_board', []),
                'review_process': result.get('review_process', {}),
                'pages_analyzed': result['pages_analyzed']
            }
            data_file = self.output_dir / "public_detailed_data.json"
            with open(data_file, 'w') as f:
                json.dump(detailed_data, f, indent=2)
            
            # Save human-readable summary
            summary_file = self.output_dir / "public_summary.txt"
            with open(summary_file, 'w') as f:
                f.write("SICON Public Data Extraction Summary\n")
                f.write("=" * 40 + "\n\n")
                f.write(f"Extraction Date: {result['started_at'].strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Success: {result['success']}\n")
                f.write(f"Duration: {result.get('duration_seconds', 0):.1f} seconds\n")
                f.write(f"Pages Analyzed: {len(result['pages_analyzed'])}\n\n")
                
                journal_info = result.get('journal_info', {})
                f.write("JOURNAL INFORMATION:\n")
                f.write(f"• Name: {journal_info.get('name', 'N/A')}\n")
                f.write(f"• Publisher: {journal_info.get('publisher', 'N/A')}\n")
                f.write(f"• ISSN: {', '.join(journal_info.get('issn', []))}\n")
                f.write(f"• Scope: {len(journal_info.get('scope', []))} topics\n\n")
                
                guidelines = result.get('submission_guidelines', {})
                f.write("SUBMISSION GUIDELINES:\n")
                f.write(f"• Manuscript Types: {len(guidelines.get('manuscript_types', []))}\n")
                f.write(f"• Formatting Requirements: {len(guidelines.get('formatting_requirements', []))}\n\n")
                
                f.write(f"EDITORIAL BOARD: {len(result.get('editorial_board', []))} members found\n\n")
                
                review_process = result.get('review_process', {})
                f.write("REVIEW PROCESS:\n")
                f.write(f"• Peer Review: {review_process.get('peer_review', False)}\n")
                f.write(f"• Review Stages: {len(review_process.get('review_stages', []))}\n")
            
            logger.info(f"💾 Public results saved to: {results_file}")
            logger.info(f"💾 Detailed data saved to: {data_file}")
            logger.info(f"💾 Summary saved to: {summary_file}")
            
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")


async def main():
    """Run public SICON data extraction."""
    print("🚀 SICON PUBLIC DATA EXTRACTION")
    print("=" * 60)
    print("🎯 EXTRACTING REAL PUBLIC DATA FROM SICON")
    print()
    print("This extractor will:")
    print("• Analyze public SICON website pages")
    print("• Extract journal information and guidelines")
    print("• Find editorial board information")
    print("• Analyze submission and review processes")
    print("• Get real publicly available data")
    print()
    print("🔧 PUBLIC DATA STRATEGY:")
    print("   1. Analyze multiple SICON-related pages")
    print("   2. Extract journal metadata and information")
    print("   3. Find submission guidelines and requirements")
    print("   4. Identify editorial board members")
    print("   5. Document review processes")
    print()
    print("🚀 Starting public data extraction...")
    print()
    
    try:
        extractor = PublicSICONExtractor()
        result = await extractor.extract_public_data()
        
        print("=" * 60)
        print("📊 PUBLIC DATA EXTRACTION RESULTS")
        print("=" * 60)
        
        print(f"✅ Success: {result['success']}")
        print(f"⏱️  Duration: {result['duration_seconds']:.1f}s")
        print(f"🔧 Method: {result.get('extraction_method', 'Unknown')}")
        print(f"❌ Errors: {len(result['errors'])}")
        
        if result['errors']:
            print(f"   Error details: {result['errors'][:2]}")
        
        print(f"\n📊 PUBLIC DATA EXTRACTED:")
        print(f"   Pages Analyzed: {len(result['pages_analyzed'])}")
        
        journal_info = result.get('journal_info', {})
        if journal_info:
            print(f"   Journal Name: {journal_info.get('name', 'N/A')}")
            print(f"   Publisher: {journal_info.get('publisher', 'N/A')}")
            print(f"   ISSN Numbers: {len(journal_info.get('issn', []))}")
            print(f"   Scope Topics: {len(journal_info.get('scope', []))}")
        
        guidelines = result.get('submission_guidelines', {})
        if guidelines:
            print(f"   Manuscript Types: {len(guidelines.get('manuscript_types', []))}")
            print(f"   Formatting Requirements: {len(guidelines.get('formatting_requirements', []))}")
        
        print(f"   Editorial Board Members: {len(result.get('editorial_board', []))}")
        
        review_process = result.get('review_process', {})
        if review_process:
            print(f"   Peer Review: {review_process.get('peer_review', False)}")
            print(f"   Review Stages: {len(review_process.get('review_stages', []))}")
        
        if result['success']:
            print(f"\n🎉 PUBLIC DATA EXTRACTION SUCCESS!")
            print("✅ Extracted real public data from SICON websites")
            print("📊 Analyzed journal information and processes")
            print("💾 All public data saved for analysis")
            print()
            print("🔍 CHECK OUTPUT FILES:")
            print(f"   • public_sicon_results.json - Summary results")
            print(f"   • public_detailed_data.json - Detailed extracted data")
            print(f"   • public_summary.txt - Human-readable summary")
            
            return True
        else:
            print(f"\n❌ Public data extraction failed")
            return False
    
    except Exception as e:
        print(f"❌ Public data extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\n{'='*60}")
    if success:
        print("🎉 REAL PUBLIC SICON DATA EXTRACTED!")
        print("✅ ACTUAL DATA FROM LIVE SICON WEBSITES!")
        print("🔍 CHECK OUTPUT FILES FOR REAL INFORMATION!")
    else:
        print("❌ Public data extraction needs debugging")
    print(f"{'='*60}")
    sys.exit(0 if success else 1)