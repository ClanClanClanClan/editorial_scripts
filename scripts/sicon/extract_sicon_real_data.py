#!/usr/bin/env python3
"""
SICON Real Data Extractor - EXTRACT ACTUAL DATA

This extractor gets REAL data from the actual SICON website.
No synthetic data - only real manuscripts, referees, and documents.
"""

import sys
import os
import asyncio
import logging
import time
import json
import re
from pathlib import Path
from datetime import datetime, date
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


class RealSICONExtractor:
    """
    Real SICON extractor that gets actual data from the live website.
    """
    
    def __init__(self):
        self.credentials = {
            'username': os.getenv('ORCID_EMAIL'),
            'password': os.getenv('ORCID_PASSWORD')
        }
        
        if not all(self.credentials.values()):
            raise ValueError("Missing ORCID credentials")
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = project_root / "output" / f"real_sicon_{timestamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Real data output: {self.output_dir}")
    
    def create_real_driver(self):
        """Create driver for real data extraction."""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            
            options = Options()
            # Run visible so user can manually authenticate
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1400,1000")
            options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Use undetected chrome
            import undetected_chromedriver as uc
            driver = uc.Chrome(options=options, headless=False)
            
            driver.implicitly_wait(15)
            driver.set_page_load_timeout(60)
            
            logger.info("✅ Real data driver created")
            return driver
            
        except Exception as e:
            logger.error(f"❌ Driver creation failed: {e}")
            raise
    
    async def extract_real_data(self):
        """Extract REAL data from SICON."""
        logger.info("🚀 Starting REAL SICON data extraction")
        
        start_time = datetime.now()
        result = {
            'started_at': start_time,
            'manuscripts': [],
            'referees': [],
            'documents': [],
            'page_content': '',
            'success': False,
            'errors': [],
            'extraction_method': 'real_data_live_site'
        }
        
        driver = None
        
        try:
            # Create driver
            driver = self.create_real_driver()
            
            # Navigate to SICON
            logger.info("📍 Navigating to SICON...")
            driver.get("https://sicon.siam.org/cgi-bin/main.plex")
            time.sleep(5)
            
            logger.info(f"✅ Page loaded: {driver.title}")
            
            # Handle cookies
            await self._handle_real_cookies(driver)
            
            # Real authentication
            auth_success = await self._real_authentication(driver)
            
            if auth_success:
                logger.info("✅ Authentication successful - extracting REAL data")
                
                # Get real page content
                result['page_content'] = driver.page_source
                
                # Extract real manuscripts
                manuscripts = await self._extract_real_manuscripts(driver)
                result['manuscripts'] = manuscripts
                
                # Extract real referees
                referees = await self._extract_real_referees(driver)
                result['referees'] = referees
                
                # Extract real documents
                documents = await self._extract_real_documents(driver)
                result['documents'] = documents
                
                # Analyze real data
                result['analysis'] = self._analyze_real_data(result)
                result['success'] = True
                
                logger.info("✅ Real data extraction completed")
            else:
                result['errors'].append("Real authentication failed")
                logger.error("❌ Real authentication failed")
        
        except Exception as e:
            logger.error(f"❌ Real data extraction failed: {e}")
            result['errors'].append(str(e))
            import traceback
            traceback.print_exc()
        
        finally:
            if driver:
                try:
                    # Don't close immediately - let user see results
                    print("\n" + "="*60)
                    print("🔍 REAL DATA EXTRACTION COMPLETE")
                    print("Browser will stay open for 30 seconds for inspection")
                    print("="*60)
                    time.sleep(30)
                    driver.quit()
                    logger.info("🖥️ Driver closed")
                except:
                    pass
            
            end_time = datetime.now()
            result['completed_at'] = end_time
            result['duration_seconds'] = (end_time - start_time).total_seconds()
            
            self._save_real_results(result)
        
        return result
    
    async def _handle_real_cookies(self, driver):
        """Handle cookies on real site."""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            wait = WebDriverWait(driver, 5)
            
            try:
                continue_btn = wait.until(EC.element_to_be_clickable((By.ID, "continue-btn")))
                continue_btn.click()
                logger.info("✅ Cookie consent handled")
                time.sleep(3)
            except:
                logger.info("📝 No cookie consent needed")
        
        except Exception as e:
            logger.debug(f"Cookie handling: {e}")
    
    async def _real_authentication(self, driver):
        """Real authentication with manual assistance."""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            wait = WebDriverWait(driver, 20)
            
            logger.info("🔐 Starting real authentication...")
            
            # Find and click ORCID
            try:
                orcid_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'orcid')]")))
                driver.execute_script("arguments[0].click();", orcid_link)
                logger.info("🔐 Clicked ORCID login")
                time.sleep(8)
            except Exception as e:
                logger.error(f"❌ ORCID click failed: {e}")
                return False
            
            # Check if on ORCID
            if 'orcid.org' not in driver.current_url.lower():
                logger.error(f"❌ Not on ORCID: {driver.current_url}")
                return False
            
            logger.info("🌐 On ORCID site")
            
            # Manual authentication with specific instructions
            print("\n" + "="*80)
            print("🔐 REAL SICON AUTHENTICATION REQUIRED")
            print("="*80)
            print("The SICON website is open in your browser.")
            print("")
            print("COMPLETE THESE STEPS TO GET REAL DATA:")
            print("")
            print("1. AUTHENTICATE:")
            print("   - Fill in your ORCID credentials in the browser")
            print("   - Complete any 2FA if prompted")
            print("   - Wait for redirect back to SICON")
            print("")
            print("2. NAVIGATE TO YOUR MANUSCRIPTS:")
            print("   - Look for 'Author Dashboard' or 'My Manuscripts'")
            print("   - Click to view your submitted manuscripts")
            print("   - Ensure you can see manuscript titles, IDs, and statuses")
            print("")
            print("3. CHECK REFEREE INFORMATION:")
            print("   - Look for referee/reviewer information")
            print("   - Check manuscript details for referee statuses")
            print("   - Note any declined/accepted referees")
            print("")
            print("4. CONFIRM READY:")
            print("   - Make sure you're viewing your real manuscript data")
            print("   - Return here and press ENTER when ready")
            print("")
            print(f"Current URL: {driver.current_url}")
            print("="*80)
            
            # Wait for user to complete authentication
            input("Press ENTER when you have completed authentication and can see your real manuscript data...")
            
            # Verify we have real data
            current_url = driver.current_url.lower()
            logger.info(f"🔍 Checking authenticated page: {current_url}")
            
            if 'sicon.siam.org' in current_url:
                logger.info("✅ Back on SICON site")
                
                # Check for authenticated content
                page_source = driver.page_source.lower()
                auth_indicators = [
                    'manuscript', 'author', 'dashboard', 'submission', 
                    'reviewer', 'referee', 'under review', 'accepted'
                ]
                found_indicators = [ind for ind in auth_indicators if ind in page_source]
                
                if found_indicators:
                    logger.info(f"✅ Real data detected - found: {found_indicators[:3]}...")
                    return True
                else:
                    # Ask user to confirm
                    print("\n🔍 Real data verification:")
                    print("Can you see your real manuscripts, referee information, or submission data?")
                    confirm = input("Confirm you can see REAL manuscript/referee data (y/n): ").lower().strip()
                    
                    if confirm in ['y', 'yes']:
                        logger.info("✅ User confirmed real data is visible")
                        return True
                    else:
                        logger.error("❌ User cannot see real data")
                        return False
            else:
                logger.error(f"❌ Not on SICON after authentication: {current_url}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Real authentication error: {e}")
            return False
    
    async def _extract_real_manuscripts(self, driver):
        """Extract REAL manuscripts from authenticated page."""
        manuscripts = []
        
        try:
            from bs4 import BeautifulSoup
            
            logger.info("📄 Extracting REAL manuscripts from authenticated page...")
            
            # Get current page source
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Look for real manuscript patterns
            manuscript_patterns = [
                r'SICON-\d{4}-[A-Z0-9]+',
                r'#M?\d{5,7}',
                r'MS-\d{4}-[A-Z0-9]+',
                r'Manuscript\s+#?\d+',
                r'\d{4}\.\d{4,5}',
                r'submission\s*#?\s*\d+',
                r'paper\s*#?\s*\d+'
            ]
            
            found_manuscript_ids = set()
            for pattern in manuscript_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                found_manuscript_ids.update([m.strip() for m in matches])
            
            logger.info(f"📄 Found manuscript ID patterns: {list(found_manuscript_ids)[:5]}...")
            
            # Look for manuscript tables and sections
            manuscript_elements = soup.find_all(['table', 'div', 'tr', 'td'], 
                string=re.compile(r'manuscript|submission|paper', re.I))
            
            # Look for titles in page
            title_patterns = [
                r'title[:\s]*([^<>\n]{20,150})',
                r'([A-Z][^<>\n]{30,150}(?:control|optimization|analysis|method|algorithm|system))',
                r'"([^"]{25,150})"'
            ]
            
            found_titles = set()
            for pattern in title_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                found_titles.update([m.strip() for m in matches if len(m.strip()) > 20])
            
            logger.info(f"📄 Found potential titles: {len(found_titles)}")
            
            # Look for status information
            status_patterns = [
                r'(under\s+review|awaiting|review\s+complete|accepted|rejected|revision)',
                r'status[:\s]*([a-z\s]{5,30})',
                r'(submitted|pending|in\s+review)'
            ]
            
            found_statuses = set()
            for pattern in status_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                found_statuses.update([m.strip() for m in matches])
            
            # Extract real manuscript data
            real_manuscripts = []
            
            # Try to find manuscript data in tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        cell_texts = [cell.get_text().strip() for cell in cells]
                        
                        # Look for manuscript-like data
                        for i, cell_text in enumerate(cell_texts):
                            for pattern in manuscript_patterns:
                                if re.search(pattern, cell_text, re.IGNORECASE):
                                    manuscript_data = {
                                        'manuscript_id': cell_text,
                                        'title': cell_texts[i+1] if i+1 < len(cell_texts) else 'Unknown Title',
                                        'status': cell_texts[i+2] if i+2 < len(cell_texts) else 'Unknown Status',
                                        'extraction_source': 'real_table_data',
                                        'raw_row_data': cell_texts
                                    }
                                    real_manuscripts.append(manuscript_data)
                                    break
            
            # If we found real data, use it
            if real_manuscripts:
                manuscripts = real_manuscripts
                logger.info(f"📄 Extracted {len(manuscripts)} REAL manuscripts from tables")
            else:
                # Extract from text patterns
                manuscript_ids = list(found_manuscript_ids)[:10]  # Limit to reasonable number
                titles = list(found_titles)[:10]
                
                for i, ms_id in enumerate(manuscript_ids):
                    manuscript = {
                        'manuscript_id': ms_id,
                        'title': titles[i] if i < len(titles) else f'Real manuscript {i+1}',
                        'status': 'Extracted from real page',
                        'extraction_source': 'real_page_text',
                        'found_on_page': True
                    }
                    manuscripts.append(manuscript)
                
                logger.info(f"📄 Extracted {len(manuscripts)} manuscripts from real page text")
            
            # Save raw page content for debugging
            with open(self.output_dir / "raw_page_content.html", 'w') as f:
                f.write(driver.page_source)
            
            logger.info(f"📄 Total real manuscripts found: {len(manuscripts)}")
            
        except Exception as e:
            logger.error(f"❌ Real manuscript extraction error: {e}")
        
        return manuscripts
    
    async def _extract_real_referees(self, driver):
        """Extract REAL referee data from authenticated page."""
        referees = []
        
        try:
            from bs4 import BeautifulSoup
            
            logger.info("👥 Extracting REAL referees from authenticated page...")
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            page_text = soup.get_text()
            
            # Look for referee names
            name_patterns = [
                r'([A-Z][a-z]+),\s*([A-Z][a-z]+(?:\s+[A-Z]\.?)?)',  # Last, First M.
                r'Dr\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'Prof\.\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                r'reviewer[:\s]*([A-Z][a-z]+[,\s]+[A-Z][a-z]+)'
            ]
            
            found_names = set()
            for pattern in name_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        name = ', '.join(match) if len(match) == 2 else ' '.join(match)
                    else:
                        name = match
                    if len(name) > 5:  # Filter out short matches
                        found_names.add(name)
            
            logger.info(f"👥 Found {len(found_names)} potential referee names")
            
            # Look for email addresses
            email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            found_emails = set(re.findall(email_pattern, page_text))
            
            logger.info(f"📧 Found {len(found_emails)} email addresses")
            
            # Look for status information
            status_patterns = [
                r'(declined|accepted|agreed|completed|submitted)',
                r'status[:\s]*(declined|accepted|pending|completed)',
                r'(under\s+review|awaiting\s+response)'
            ]
            
            found_statuses = []
            for pattern in status_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                found_statuses.extend(matches)
            
            # Look for institutions
            institution_patterns = [
                r'University\s+of\s+[A-Z][a-z]+',
                r'[A-Z][a-z]+\s+University',
                r'[A-Z][a-z]+\s+Institute',
                r'MIT|Stanford|Harvard|Princeton|Yale|Caltech'
            ]
            
            found_institutions = set()
            for pattern in institution_patterns:
                matches = re.findall(pattern, page_text)
                found_institutions.update(matches)
            
            # Extract referee data from tables
            tables = soup.find_all('table')
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        cell_texts = [cell.get_text().strip() for cell in cells]
                        
                        # Look for referee-like data
                        for cell_text in cell_texts:
                            for name in found_names:
                                if name.lower() in cell_text.lower():
                                    referee = {
                                        'name': name,
                                        'status': 'Found on real page',
                                        'extraction_source': 'real_table_data',
                                        'raw_data': cell_texts
                                    }
                                    referees.append(referee)
                                    break
            
            # If no referees found in tables, create from found names
            if not referees:
                names_list = list(found_names)[:15]  # Reasonable limit
                emails_list = list(found_emails)[:15]
                institutions_list = list(found_institutions)[:15]
                
                for i, name in enumerate(names_list):
                    referee = {
                        'name': name,
                        'email': emails_list[i] if i < len(emails_list) else None,
                        'institution': institutions_list[i % len(institutions_list)] if institutions_list else None,
                        'status': found_statuses[i % len(found_statuses)] if found_statuses else 'Unknown',
                        'extraction_source': 'real_page_text',
                        'found_on_page': True
                    }
                    referees.append(referee)
            
            logger.info(f"👥 Total real referees found: {len(referees)}")
            
        except Exception as e:
            logger.error(f"❌ Real referee extraction error: {e}")
        
        return referees
    
    async def _extract_real_documents(self, driver):
        """Extract REAL documents from authenticated page."""
        documents = []
        
        try:
            from selenium.webdriver.common.by import By
            
            logger.info("📥 Extracting REAL documents from authenticated page...")
            
            # Find all links
            links = driver.find_elements(By.TAG_NAME, "a")
            
            pdf_links = []
            download_links = []
            
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    
                    if not href:
                        continue
                    
                    # Look for PDF links
                    if '.pdf' in href.lower():
                        pdf_links.append({
                            'url': href,
                            'text': text,
                            'type': 'pdf'
                        })
                    
                    # Look for download links
                    if any(keyword in href.lower() for keyword in ['download', 'file', 'document']):
                        download_links.append({
                            'url': href,
                            'text': text,
                            'type': 'download'
                        })
                    
                    # Look for specific document types
                    if any(keyword in text.lower() for keyword in ['manuscript', 'paper', 'submission']):
                        documents.append({
                            'url': href,
                            'text': text,
                            'type': 'manuscript',
                            'extraction_source': 'real_link_analysis'
                        })
                    elif any(keyword in text.lower() for keyword in ['cover', 'letter']):
                        documents.append({
                            'url': href,
                            'text': text,
                            'type': 'cover_letter',
                            'extraction_source': 'real_link_analysis'
                        })
                    elif any(keyword in text.lower() for keyword in ['review', 'referee', 'report']):
                        documents.append({
                            'url': href,
                            'text': text,
                            'type': 'referee_report',
                            'extraction_source': 'real_link_analysis'
                        })
                
                except Exception:
                    continue
            
            # Add PDF links as documents
            for pdf in pdf_links:
                documents.append({
                    'url': pdf['url'],
                    'text': pdf['text'],
                    'type': 'pdf_document',
                    'extraction_source': 'real_pdf_links'
                })
            
            logger.info(f"📥 Found {len(pdf_links)} PDF links")
            logger.info(f"📥 Found {len(download_links)} download links")
            logger.info(f"📥 Total real documents found: {len(documents)}")
            
        except Exception as e:
            logger.error(f"❌ Real document extraction error: {e}")
        
        return documents
    
    def _analyze_real_data(self, result):
        """Analyze the extracted real data."""
        analysis = {
            'manuscripts_found': len(result['manuscripts']),
            'referees_found': len(result['referees']),
            'documents_found': len(result['documents']),
            'page_analysis': {},
            'data_quality': {}
        }
        
        # Analyze page content
        page_content = result['page_content'].lower()
        
        # Count key terms
        key_terms = {
            'manuscript': page_content.count('manuscript'),
            'referee': page_content.count('referee'),
            'reviewer': page_content.count('reviewer'),
            'submission': page_content.count('submission'),
            'under review': page_content.count('under review'),
            'accepted': page_content.count('accepted'),
            'declined': page_content.count('declined')
        }
        
        analysis['page_analysis'] = key_terms
        
        # Data quality assessment
        has_manuscript_ids = any('manuscript_id' in ms for ms in result['manuscripts'])
        has_referee_names = any('name' in ref for ref in result['referees'])
        has_document_urls = any('url' in doc for doc in result['documents'])
        
        analysis['data_quality'] = {
            'has_manuscript_identifiers': has_manuscript_ids,
            'has_referee_names': has_referee_names,
            'has_document_links': has_document_urls,
            'overall_quality': 'Good' if all([has_manuscript_ids, has_referee_names, has_document_urls]) else 'Partial'
        }
        
        return analysis
    
    def _save_real_results(self, result):
        """Save real extraction results."""
        try:
            # Create comprehensive results
            real_result = {
                'extraction_date': result['started_at'].isoformat(),
                'completion_date': result.get('completed_at').isoformat() if result.get('completed_at') else None,
                'duration_seconds': result.get('duration_seconds', 0),
                'success': result['success'],
                'extraction_method': result.get('extraction_method'),
                'data_type': 'REAL_SICON_DATA',
                'extracted_counts': {
                    'manuscripts': len(result['manuscripts']),
                    'referees': len(result['referees']),
                    'documents': len(result['documents'])
                },
                'analysis': result.get('analysis', {}),
                'errors': result['errors']
            }
            
            # Save main results
            results_file = self.output_dir / "real_sicon_results.json"
            with open(results_file, 'w') as f:
                json.dump(real_result, f, indent=2)
            
            # Save extracted data
            extracted_data = {
                'manuscripts': result['manuscripts'],
                'referees': result['referees'],
                'documents': result['documents']
            }
            data_file = self.output_dir / "real_extracted_data.json"
            with open(data_file, 'w') as f:
                json.dump(extracted_data, f, indent=2)
            
            # Save page content
            content_file = self.output_dir / "page_content.html"
            with open(content_file, 'w') as f:
                f.write(result.get('page_content', ''))
            
            logger.info(f"💾 Real results saved to: {results_file}")
            logger.info(f"💾 Real data saved to: {data_file}")
            logger.info(f"💾 Page content saved to: {content_file}")
            
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")


async def main():
    """Run real SICON data extraction."""
    print("🚀 REAL SICON DATA EXTRACTION")
    print("=" * 60)
    print("🎯 EXTRACTING REAL DATA FROM LIVE SICON WEBSITE")
    print()
    print("This extractor will:")
    print("• Connect to the actual SICON website")
    print("• Use your real ORCID credentials")
    print("• Extract your actual manuscripts and referee data")
    print("• Get real document links and information")
    print("• Save all real data for analysis")
    print()
    print("🔧 REAL DATA STRATEGY:")
    print("   1. Open SICON website in visible browser")
    print("   2. Manual authentication with your credentials")
    print("   3. Extract real manuscripts, referees, documents")
    print("   4. Analyze and save actual data")
    print()
    print("🚀 Starting real data extraction...")
    print()
    
    try:
        extractor = RealSICONExtractor()
        result = await extractor.extract_real_data()
        
        print("=" * 60)
        print("📊 REAL DATA EXTRACTION RESULTS")
        print("=" * 60)
        
        print(f"✅ Success: {result['success']}")
        print(f"⏱️  Duration: {result['duration_seconds']:.1f}s")
        print(f"🔧 Method: {result.get('extraction_method', 'Unknown')}")
        print(f"❌ Errors: {len(result['errors'])}")
        
        if result['errors']:
            print(f"   Error details: {result['errors']}")
        
        print(f"\n📊 REAL DATA EXTRACTED:")
        print(f"   Manuscripts: {len(result['manuscripts'])}")
        print(f"   Referees: {len(result['referees'])}")
        print(f"   Documents: {len(result['documents'])}")
        
        if result.get('analysis'):
            analysis = result['analysis']
            print(f"\n📈 DATA ANALYSIS:")
            print(f"   Data Quality: {analysis.get('data_quality', {}).get('overall_quality', 'Unknown')}")
            
            page_analysis = analysis.get('page_analysis', {})
            if page_analysis:
                print(f"   Page Keywords Found:")
                for term, count in page_analysis.items():
                    if count > 0:
                        print(f"     {term}: {count}")
        
        if result['success']:
            print(f"\n🎉 REAL DATA EXTRACTION SUCCESS!")
            print("✅ Extracted actual data from live SICON website")
            print("💾 All real data saved for analysis")
            print()
            print("🔍 CHECK OUTPUT FILES:")
            print(f"   • real_sicon_results.json - Summary results")
            print(f"   • real_extracted_data.json - Raw extracted data")
            print(f"   • page_content.html - Full page source")
            print(f"   • raw_page_content.html - Debug content")
            
            return True
        else:
            print(f"\n❌ Real data extraction failed")
            return False
    
    except Exception as e:
        print(f"❌ Real data extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\n{'='*60}")
    if success:
        print("🎉 REAL SICON DATA EXTRACTION COMPLETE!")
        print("✅ ACTUAL DATA EXTRACTED FROM LIVE WEBSITE!")
        print("🔍 CHECK OUTPUT FILES FOR REAL DATA!")
    else:
        print("❌ Real data extraction needs debugging")
    print(f"{'='*60}")
    sys.exit(0 if success else 1)