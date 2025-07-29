#!/usr/bin/env python3
"""
Test complete extraction showing ALL data in detail
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from src.extractors.mf_extractor import ComprehensiveMFExtractor
import time
from selenium.webdriver.common.by import By
import json

def test_complete_extraction():
    extractor = ComprehensiveMFExtractor()
    
    try:
        # Quick login and navigation
        login_success = extractor.login()
        if not login_success:
            return
        
        max_wait = 30
        wait_count = 0
        while wait_count < max_wait:
            current_url = extractor.driver.current_url
            if "page=LOGIN" not in current_url and "login" not in current_url.lower():
                break
            time.sleep(2)
            wait_count += 1
        
        time.sleep(3)
        ae_link = extractor.driver.find_element(By.LINK_TEXT, "Associate Editor Center")
        ae_link.click()
        time.sleep(5)
        
        categories = extractor.get_manuscript_categories()
        if categories:
            for category in categories:
                if category['count'] > 0:
                    category['link'].click()
                    time.sleep(3)
                    
                    take_action_links = extractor.driver.find_elements(By.XPATH, 
                        "//a[contains(@href,'ASSOCIATE_EDITOR_MANUSCRIPT_DETAILS')]")
                    
                    if take_action_links:
                        take_action_links[0].click()
                        time.sleep(5)
                        
                        manuscript_id = extractor.get_current_manuscript_id()
                        
                        manuscript = {
                            'id': manuscript_id,
                            'title': '',
                            'authors': [],
                            'submission_date': '',
                            'last_updated': '',
                            'status': '',
                            'referees': [],
                            'documents': {},
                            'abstract': '',
                            'keywords': []
                        }
                        
                        print(f"🔍 COMPLETE EXTRACTION FOR {manuscript_id}")
                        print("="*80)
                        
                        # Extract manuscript details
                        print("\n📄 EXTRACTING MANUSCRIPT DETAILS...")
                        print("-"*60)
                        
                        # Get title
                        try:
                            title_elem = extractor.driver.find_element(By.XPATH, 
                                "//td[@class='headerbg2']//td[@colspan='2']//p[@class='pagecontents']")
                            manuscript['title'] = title_elem.text.strip()
                            print(f"✅ Title: {manuscript['title']}")
                        except:
                            print("❌ Could not extract title")
                        
                        # Get dates and status
                        try:
                            header_text = extractor.driver.find_element(By.XPATH, 
                                "//td[@class='headerbg2']").text
                            if 'Submitted:' in header_text:
                                import re
                                submitted_match = re.search(r'Submitted:\s*(\d{1,2}-\w{3}-\d{4})', header_text)
                                if submitted_match:
                                    manuscript['submission_date'] = submitted_match.group(1)
                                    print(f"✅ Submission Date: {manuscript['submission_date']}")
                                
                                updated_match = re.search(r'Last Updated:\s*(\d{1,2}-\w{3}-\d{4})', header_text)
                                if updated_match:
                                    manuscript['last_updated'] = updated_match.group(1)
                                    print(f"✅ Last Updated: {manuscript['last_updated']}")
                                
                                # Extract status
                                status_match = re.search(r'(Awaiting Reviewer Scores|Under Review|Completed)', header_text)
                                if status_match:
                                    manuscript['status'] = status_match.group(1)
                                    print(f"✅ Status: {manuscript['status']}")
                        except:
                            print("❌ Could not extract dates/status")
                        
                        # Get authors
                        try:
                            # Look for author info in header
                            author_line_elem = extractor.driver.find_element(By.XPATH, 
                                "//p[@class='pagecontents'][contains(text(), ';') and not(contains(text(), 'special issue'))]")
                            author_text = author_line_elem.text.strip()
                            authors = [a.strip() for a in author_text.split(';')]
                            manuscript['authors'] = authors
                            print(f"✅ Authors: {', '.join(authors)}")
                        except:
                            print("❌ Could not extract authors")
                        
                        # Extract referees with all details
                        print("\n👥 EXTRACTING REFEREES...")
                        print("-"*60)
                        extractor.extract_referees_comprehensive(manuscript)
                        
                        # Extract documents
                        print("\n📂 EXTRACTING DOCUMENTS...")
                        print("-"*60)
                        extractor.extract_document_links(manuscript)
                        
                        # Extract abstract
                        print("\n📝 EXTRACTING ABSTRACT...")
                        print("-"*60)
                        extractor.extract_abstract(manuscript)
                        
                        # DETAILED OUTPUT
                        print("\n" + "="*80)
                        print("📊 COMPLETE EXTRACTION RESULTS - ALL DATA")
                        print("="*80)
                        
                        print(f"\n🆔 MANUSCRIPT ID: {manuscript['id']}")
                        print(f"📚 TITLE: {manuscript['title']}")
                        print(f"👤 AUTHORS: {', '.join(manuscript['authors'])}")
                        print(f"📅 SUBMISSION DATE: {manuscript['submission_date']}")
                        print(f"🔄 LAST UPDATED: {manuscript['last_updated']}")
                        print(f"📊 STATUS: {manuscript['status']}")
                        
                        print(f"\n📝 ABSTRACT:")
                        print("-"*60)
                        abstract_text = manuscript.get('abstract', '')
                        if abstract_text:
                            # Print first 300 chars of abstract
                            print(f"{abstract_text[:300]}..." if len(abstract_text) > 300 else abstract_text)
                        else:
                            print("No abstract found")
                        
                        print(f"\n📂 DOCUMENTS:")
                        print("-"*60)
                        docs = manuscript.get('documents', {})
                        for doc_type, doc_info in docs.items():
                            if isinstance(doc_info, bool) and doc_info:
                                print(f"✅ {doc_type}: Available")
                            elif isinstance(doc_info, str):
                                print(f"✅ {doc_type}: {doc_info}")
                                # Check file extension for cover letter
                                if 'cover_letter' in doc_type and 'path' in doc_type:
                                    path = Path(doc_info)
                                    print(f"   📄 Extension: {path.suffix}")
                                    print(f"   📄 Full path: {doc_info}")
                        
                        # Check actual cover letter files
                        print(f"\n📋 COVER LETTER FILE CHECK:")
                        print("-"*60)
                        cover_letter_dirs = [
                            Path("downloads"),
                            Path("downloads/cover_letters"),
                            Path("src/downloads"),
                            Path("src/downloads/cover_letters")
                        ]
                        
                        found_cover_letters = []
                        for dir_path in cover_letter_dirs:
                            if dir_path.exists():
                                # Look for cover letter files
                                patterns = [
                                    f"{manuscript_id}_cover_letter.*",
                                    f"*cover_letter*{manuscript_id}*",
                                    f"{manuscript_id}*cover*"
                                ]
                                for pattern in patterns:
                                    files = list(dir_path.glob(pattern))
                                    found_cover_letters.extend(files)
                        
                        if found_cover_letters:
                            print(f"✅ Found {len(found_cover_letters)} cover letter file(s):")
                            for file_path in found_cover_letters:
                                print(f"   📄 {file_path}")
                                print(f"      Extension: {file_path.suffix}")
                                print(f"      Size: {file_path.stat().st_size} bytes")
                        else:
                            print("❌ No cover letter files found on disk")
                        
                        print(f"\n👥 REFEREES: {len(manuscript['referees'])} total")
                        print("-"*60)
                        
                        for i, referee in enumerate(manuscript['referees'], 1):
                            print(f"\n🔸 REFEREE {i}:")
                            print(f"   👤 Name: {referee['name']}")
                            print(f"   📧 Email: {referee['email']}")
                            print(f"   🏢 Affiliation: {referee['affiliation'] or 'Not found'}")
                            print(f"   🌍 Country: {referee['country'] or 'Not found'}")
                            print(f"   📊 Status: {referee['status'] or 'Not found'}")
                            print(f"   🆔 ORCID: {referee['orcid'] or 'Not found'}")
                            
                            # Dates details
                            dates = referee.get('dates', {})
                            if dates:
                                print(f"   📅 Dates:")
                                for date_type, date_value in dates.items():
                                    print(f"      - {date_type}: {date_value}")
                            else:
                                print(f"   📅 Dates: None found")
                            
                            # Review links
                            review_links = referee.get('review_links', [])
                            if review_links:
                                print(f"   🔗 Review Links: {len(review_links)}")
                                for link in review_links:
                                    print(f"      - {link['text']}")
                            else:
                                print(f"   🔗 Review Links: None")
                        
                        # Pretty print JSON for easy copying
                        print(f"\n📋 JSON DATA (for easy copying):")
                        print("-"*60)
                        print(json.dumps(manuscript, indent=2))
                        
                        break
                    break
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n⏸️ Closing browser in 20 seconds...")
        time.sleep(20)
        extractor.driver.quit()

if __name__ == "__main__":
    test_complete_extraction()