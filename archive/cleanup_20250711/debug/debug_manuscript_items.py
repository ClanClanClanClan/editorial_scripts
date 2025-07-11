#!/usr/bin/env python3
"""
Debug manuscript items section structure
"""

from bs4 import BeautifulSoup
import re

def debug_manuscript_items():
    """Debug the manuscript items section structure"""
    print("=== DEBUGGING MANUSCRIPT ITEMS SECTION ===")
    
    # Read the saved HTML file
    with open('sifin_manuscript_detail.html', 'r') as f:
        html_content = f.read()
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the manuscript details table
    details_table = soup.find('table', {'id': 'ms_details_expanded'})
    if not details_table:
        print("No ms_details_expanded table found")
        return
    
    print("Found ms_details_expanded table")
    
    # Look for all sections in the table
    for i, row in enumerate(details_table.find_all('tr')):
        th = row.find('th')
        td = row.find('td')
        if th and td:
            label = th.get_text(strip=True)
            content = td.get_text(strip=True)
            
            print(f"\nRow {i+1}: {label}")
            print(f"  Content: {content[:100]}..." if len(content) > 100 else f"  Content: {content}")
            
            # Look for any sections that might contain documents
            if any(keyword in label.lower() for keyword in ['item', 'document', 'file', 'manuscript', 'attach']):
                print(f"  🔍 POTENTIAL DOCUMENT SECTION: {label}")
                
                # Look for links in this section
                links = td.find_all('a')
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    if href:
                        print(f"    Link: {text} -> {href}")
                        if '.pdf' in href.lower():
                            print(f"      📄 PDF LINK FOUND!")
                            
                            # Check if it's a cover letter
                            if 'cover' in text.lower() or 'cover' in href.lower():
                                print(f"      ✉️  COVER LETTER DETECTED!")
                            
                            # Check if it's an article file
                            if 'article' in text.lower() or 'article' in href.lower():
                                print(f"      📋 ARTICLE FILE DETECTED!")
    
    print("\n=== SEARCHING FOR SPECIFIC PATTERNS ===")
    
    # Look for specific patterns the user mentioned
    patterns = [
        r'Author Cover Letter',
        r'Article File',
        r'Source File',
        r'Save File As',
        r'Manuscript Items?',
        r'PDF.*\(\d+KB\)',
        r'cover.*letter',
        r'article.*file'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            print(f"Found pattern '{pattern}': {matches}")
            
            # Find the context around these matches
            for match in matches:
                start = html_content.lower().find(match.lower())
                if start != -1:
                    context_start = max(0, start - 200)
                    context_end = min(len(html_content), start + len(match) + 200)
                    context = html_content[context_start:context_end]
                    print(f"  Context: ...{context}...")
                    break
    
    print("\n=== ALL PDF LINKS IN THE PAGE ===")
    
    # Find all PDF links
    pdf_links = soup.find_all('a', href=lambda x: x and '.pdf' in x.lower())
    print(f"Found {len(pdf_links)} PDF links total:")
    
    for i, link in enumerate(pdf_links):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        print(f"  {i+1}: {text} -> {href}")
        
        # Classify the link
        if 'cover' in text.lower() or 'cover' in href.lower():
            print(f"       Type: COVER LETTER")
        elif 'article' in text.lower() or 'article' in href.lower():
            print(f"       Type: ARTICLE FILE")
        elif 'source' in text.lower() or 'source' in href.lower():
            print(f"       Type: SOURCE FILE")
        else:
            print(f"       Type: UNKNOWN")

if __name__ == "__main__":
    debug_manuscript_items()