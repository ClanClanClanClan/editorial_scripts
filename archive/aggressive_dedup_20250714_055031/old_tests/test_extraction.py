#!/usr/bin/env python3
"""
Quick test script to verify the updated SIAM extraction logic
"""

import sys
import os
from bs4 import BeautifulSoup

def test_siam_extraction():
    """Test the new SIAM extraction methods with debug HTML"""
    
    # Read the debug HTML file
    debug_file = "/Users/dylanpossamai/.editorial_scripts/analytics/debug_M174160_page.html"
    
    print(f"📋 Testing SIAM extraction with {debug_file}")
    
    with open(debug_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    print(f"✅ Loaded HTML: {len(html_content)} characters")
    
    # Test 1: Find manuscript details table
    details_table = soup.find('table', class_='dump_ms_details')
    if details_table:
        print(f"✅ Found manuscript details table")
        
        # Test extracting specific fields
        for row in details_table.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            
            if th and td:
                label = th.get_text().strip().lower()
                value = td.get_text().strip()
                
                if 'title' in label and 'running' not in label:
                    print(f"📄 Title: {value}")
                elif 'referees' in label and 'potential' not in label:
                    print(f"👥 Referees section found")
                    # Test referee parsing
                    referee_links = td.find_all('a', target='bio')
                    for link in referee_links:
                        referee_name = link.get_text().strip()
                        print(f"   👤 Referee: {referee_name}")
                        
                        # Look for dates in the context
                        referee_text = td.get_text()
                        if 'Due:' in referee_text:
                            import re
                            due_match = re.search(r'Due:\s*(\d{4}-\d{2}-\d{2})', referee_text)
                            if due_match:
                                print(f"      📅 Due: {due_match.group(1)}")
                        if 'Rcvd:' in referee_text:
                            rcvd_match = re.search(r'Rcvd:\s*(\d{4}-\d{2}-\d{2})', referee_text)
                            if rcvd_match:
                                print(f"      📥 Received: {rcvd_match.group(1)}")
                        
                elif 'corresponding author' in label:
                    author_link = td.find('a')
                    if author_link:
                        author_text = author_link.get_text().strip()
                        if '(' in author_text:
                            author_name = author_text.split('(')[0].strip()
                            print(f"👤 Corresponding Author: {author_name}")
                        
    else:
        print(f"❌ No manuscript details table found")
        
    # Test 2: Find PDF links
    items_sections = soup.find_all(text=lambda t: t and 'manuscript items' in t.lower())
    print(f"📄 Found {len(items_sections)} manuscript items sections")
    
    for section in items_sections:
        parent = section.parent
        if parent:
            ol = parent.find_next('ol')
            if ol:
                for li in ol.find_all('li'):
                    pdf_links = li.find_all('a', href=lambda h: h and '.pdf' in h.lower())
                    for link in pdf_links:
                        pdf_url = link.get('href', '')
                        pdf_text = li.get_text()
                        print(f"📄 PDF found: {pdf_url}")
                        print(f"   Description: {pdf_text.strip()[:100]}...")

if __name__ == "__main__":
    test_siam_extraction()