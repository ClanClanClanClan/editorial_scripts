#!/usr/bin/env python3
"""
PDF Downloader - Downloads PDFs and gets full manuscript details
Works with existing extraction results to enhance them with PDFs
"""

import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import re
import requests
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from journals.mf import MFJournal
from journals.mor import MORJournal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PDF_DOWNLOADER")


class PDFDownloader:
    def __init__(self, journal_name):
        self.journal_name = journal_name
        self.driver = None
        self.journal = None
        self.output_dir = Path(f"{journal_name.lower()}_pdf_downloads")
        self.output_dir.mkdir(exist_ok=True)
        
    def create_driver(self, headless=False):
        """Create Chrome driver with download configuration"""
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        # Configure Chrome to download PDFs
        prefs = {
            "download.default_directory": str(self.output_dir.absolute()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        }
        options.add_experimental_option("prefs", prefs)
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
        
        try:
            self.driver = uc.Chrome(options=options)
        except:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            chrome_options = Options()
            for arg in options.arguments:
                chrome_options.add_argument(arg)
            chrome_options.add_experimental_option("prefs", prefs)
            self.driver = webdriver.Chrome(options=chrome_options)
            
    def download_pdfs_for_manuscript(self, manuscript_id, category="Awaiting Reviewer Reports"):
        """Download PDFs for a specific manuscript"""
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 Processing PDFs for: {manuscript_id}")
        
        result = {
            'manuscript_id': manuscript_id,
            'authors': [],
            'abstract': '',
            'keywords': [],
            'manuscript_pdf_url': '',
            'manuscript_pdf_path': '',
            'referee_reports': []
        }
        
        try:
            # Navigate to manuscript list
            logger.info(f"📂 Navigating to: {category}")
            ae_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Associate Editor Center"))
            )
            ae_link.click()
            time.sleep(2)
            
            category_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, category))
            )
            category_link.click()
            time.sleep(3)
            
            # Find and click View Submission link for this manuscript
            logger.info(f"🔍 Looking for View Submission link for {manuscript_id}")
            
            # Find the table containing manuscripts
            tables = self.driver.find_elements(By.TAG_NAME, "table")
            
            view_submission_found = False
            for table in tables:
                # Look for manuscript ID in table
                if manuscript_id in table.text:
                    # Find all cells with View Submission links
                    cells = table.find_elements(By.TAG_NAME, "td")
                    for cell in cells:
                        if manuscript_id in cell.text:
                            # The View Submission link should be in the same cell as the title
                            try:
                                view_link = cell.find_element(By.LINK_TEXT, "View Submission")
                                logger.info(f"✅ Found View Submission link for {manuscript_id}")
                                
                                # Scroll into view and click
                                self.driver.execute_script("arguments[0].scrollIntoView(true);", view_link)
                                time.sleep(0.5)
                                view_link.click()
                                time.sleep(3)
                                view_submission_found = True
                                break
                            except:
                                continue
                                
                if view_submission_found:
                    break
                    
            if not view_submission_found:
                logger.warning(f"⚠️  No View Submission link found for {manuscript_id}")
                return result
                
            # Extract submission details
            logger.info("📊 Extracting submission details...")
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Extract authors
            author_patterns = [
                (r'Authors?:\s*([^\n]+)', 1),  # Simple pattern
                (r'Author List.*?<table.*?>(.*?)</table>', 1),  # Table pattern
            ]
            
            for pattern, group in author_patterns:
                match = re.search(pattern, str(soup), re.IGNORECASE | re.DOTALL)
                if match:
                    author_text = match.group(group)
                    # Clean up author names
                    if '<' in author_text:  # HTML content
                        author_soup = BeautifulSoup(author_text, 'html.parser')
                        author_rows = author_soup.find_all('tr')[1:]  # Skip header
                        for row in author_rows:
                            cells = row.find_all('td')
                            if cells:
                                name = cells[0].get_text(strip=True)
                                email = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                                if name and not any(skip in name.lower() for skip in ['select', 'all', 'none']):
                                    result['authors'].append({'name': name, 'email': email})
                    else:  # Plain text
                        # Split by common delimiters
                        authors = re.split(r'[;,\n]', author_text)
                        for author in authors:
                            author = author.strip()
                            if author and len(author) > 3:
                                result['authors'].append({'name': author, 'email': ''})
                    break
                    
            logger.info(f"   👥 Found {len(result['authors'])} authors")
            
            # Extract abstract
            abstract_patterns = [
                (r'Abstract[:\s]*([^<]+)', 1),
                (r'<td[^>]*>Abstract</td>\s*<td[^>]*>(.*?)</td>', 1),
            ]
            
            for pattern, group in abstract_patterns:
                match = re.search(pattern, str(soup), re.IGNORECASE | re.DOTALL)
                if match:
                    abstract = match.group(group).strip()
                    # Clean HTML tags
                    abstract = re.sub('<.*?>', '', abstract)
                    abstract = abstract.strip()
                    if len(abstract) > 20:  # Reasonable abstract length
                        result['abstract'] = abstract
                        logger.info(f"   📝 Abstract: {abstract[:100]}...")
                        break
                        
            # Extract keywords
            keyword_patterns = [
                (r'Keywords?[:\s]*([^<\n]+)', 1),
                (r'<td[^>]*>Keywords?</td>\s*<td[^>]*>(.*?)</td>', 1),
            ]
            
            for pattern, group in keyword_patterns:
                match = re.search(pattern, str(soup), re.IGNORECASE | re.DOTALL)
                if match:
                    keyword_text = match.group(group).strip()
                    # Clean and split keywords
                    keyword_text = re.sub('<.*?>', '', keyword_text)
                    keywords = re.split(r'[;,\n]', keyword_text)
                    result['keywords'] = [k.strip() for k in keywords if k.strip() and len(k.strip()) > 2]
                    logger.info(f"   🏷️  Keywords: {', '.join(result['keywords'])}")
                    break
                    
            # Find manuscript PDF
            logger.info("🔍 Looking for manuscript PDF...")
            
            # First, try clicking the PDF tab if it exists
            try:
                pdf_tab = self.driver.find_element(By.LINK_TEXT, "PDF")
                logger.info("📄 Found PDF tab, clicking...")
                pdf_tab.click()
                time.sleep(2)
                
                # Now look for download link in the PDF view
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
            except:
                logger.info("ℹ️  No PDF tab found, looking for direct links...")
                
            # Look for PDF download links
            pdf_links = soup.find_all('a', href=True)
            for link in pdf_links:
                href = link.get('href', '')
                link_text = link.get_text(strip=True).lower()
                
                # Look for PDF indicators
                if any(indicator in href.lower() or indicator in link_text for indicator in ['pdf', 'download', 'manuscript', 'file']):
                    if 'pdf' in href or 'download' in href or 'file' in href:
                        # Construct full URL
                        if href.startswith('/'):
                            pdf_url = f"https://mc.manuscriptcentral.com{href}"
                        elif href.startswith('http'):
                            pdf_url = href
                        else:
                            pdf_url = f"https://mc.manuscriptcentral.com/{self.journal_name.lower()}/{href}"
                            
                        result['manuscript_pdf_url'] = pdf_url
                        logger.info(f"   ✅ Found manuscript PDF URL")
                        
                        # Download the PDF
                        pdf_path = self.download_pdf_with_session(pdf_url, f"{manuscript_id}_manuscript.pdf")
                        if pdf_path:
                            result['manuscript_pdf_path'] = pdf_path
                        break
                        
            # Also try Abstract tab for better abstract extraction
            try:
                abstract_tab = self.driver.find_element(By.LINK_TEXT, "Abstract")
                logger.info("📝 Found Abstract tab, clicking...")
                abstract_tab.click()
                time.sleep(1)
                
                # Extract abstract from dedicated tab
                soup_abstract = BeautifulSoup(self.driver.page_source, 'html.parser')
                abstract_content = soup_abstract.find('div', class_='abstract-content')
                if not abstract_content:
                    # Try other common abstract containers
                    abstract_content = soup_abstract.find('div', id=re.compile('abstract', re.I))
                    
                if abstract_content:
                    abstract_text = abstract_content.get_text(strip=True)
                    if len(abstract_text) > len(result.get('abstract', '')):
                        result['abstract'] = abstract_text
                        logger.info(f"   📝 Better abstract found: {abstract_text[:100]}...")
            except:
                pass
                        
            # Navigate back
            logger.info("🔄 Navigating back...")
            self.driver.back()
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"❌ Error processing {manuscript_id}: {e}")
            
        return result
        
    def download_pdf_with_session(self, pdf_url, filename):
        """Download PDF using current session cookies"""
        try:
            logger.info(f"   📥 Downloading: {filename}")
            
            # Get cookies from Selenium
            cookies = self.driver.get_cookies()
            
            # Create requests session with cookies
            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie['name'], cookie['value'])
                
            # Add headers
            headers = {
                'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                'Accept': 'application/pdf,*/*',
                'Referer': self.driver.current_url
            }
            
            # Download PDF
            response = session.get(pdf_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Check if response is actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and response.content[:4] != b'%PDF':
                logger.warning(f"   ⚠️  Response is not a PDF (Content-Type: {content_type})")
                return None
                
            # Save PDF
            pdf_path = self.output_dir / filename
            with open(pdf_path, 'wb') as f:
                shutil.copyfileobj(response.raw, f)
                
            file_size = pdf_path.stat().st_size
            logger.info(f"   ✅ PDF saved: {pdf_path} ({file_size:,} bytes)")
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"   ❌ Download failed: {e}")
            return None
            
    def download_all_pdfs(self, headless=True):
        """Download PDFs for all manuscripts"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🚀 PDF DOWNLOAD - {self.journal_name}")
        logger.info(f"{'='*80}")
        
        self.create_driver(headless=headless)
        
        try:
            # Setup journal and manuscripts
            if self.journal_name == "MF":
                self.journal = MFJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Scores"
                manuscripts = ["MAFI-2024-0167", "MAFI-2025-0166"]
            else:
                self.journal = MORJournal(self.driver, debug=True)
                category = "Awaiting Reviewer Reports"
                manuscripts = ["MOR-2025-1037", "MOR-2023-0376", "MOR-2023-0376.R1", "MOR-2024-0804"]
                
            # Login
            self.journal.login()
            
            # Process each manuscript
            all_results = []
            for manuscript_id in manuscripts:
                result = self.download_pdfs_for_manuscript(manuscript_id, category)
                all_results.append(result)
                
            # Save results
            results_file = self.output_dir / f"{self.journal_name.lower()}_pdf_results.json"
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False)
            logger.info(f"\n✅ Results saved to: {results_file}")
            
            # Generate summary
            summary_file = self.output_dir / f"{self.journal_name.lower()}_pdf_summary.txt"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"PDF DOWNLOAD SUMMARY - {self.journal_name}\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*60}\n\n")
                
                for result in all_results:
                    f.write(f"Manuscript: {result['manuscript_id']}\n")
                    f.write(f"Authors: {', '.join([a['name'] for a in result['authors']])}\n")
                    f.write(f"Keywords: {', '.join(result['keywords'])}\n")
                    f.write(f"PDF Downloaded: {'✅' if result['manuscript_pdf_path'] else '❌'}\n")
                    f.write(f"\n{'-'*60}\n\n")
                    
            logger.info(f"✅ Summary saved to: {summary_file}")
            
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            
        finally:
            self.driver.quit()


def main():
    """Main function"""
    import argparse
    parser = argparse.ArgumentParser(description='PDF Downloader')
    parser.add_argument('journal', choices=['MF', 'MOR'], help='Journal to process')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    downloader = PDFDownloader(args.journal)
    downloader.download_all_pdfs(headless=args.headless)


if __name__ == '__main__':
    main()