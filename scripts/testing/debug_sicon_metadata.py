#!/usr/bin/env python3
"""
Debug SICON metadata parsing to understand why titles/authors are empty
"""

import asyncio
import logging
from bs4 import BeautifulSoup
from pathlib import Path
import sys
sys.path.append('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts')

from src.infrastructure.scrapers.siam.sicon_scraper import SICONRealExtractor
from src.core.credential_manager import CredentialManager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_metadata_parsing():
    """Debug the metadata parsing by inspecting the HTML structure"""
    
    print("🔍 Debugging SICON metadata parsing...")
    
    # Get credentials
    cred_manager = CredentialManager()
    creds = cred_manager.get_credentials('SICON')
    
    if not creds:
        print("❌ No credentials found")
        return
    
    # Create extractor
    extractor = SICONRealExtractor()
    
    try:
        # Initialize browser
        await extractor._init_browser(headless=True)
        
        # Authenticate
        print("🔐 Authenticating...")
        authenticated = await extractor._authenticate(creds['username'], creds['password'])
        
        if not authenticated:
            print("❌ Authentication failed")
            return
        
        # Navigate to manuscripts
        print("📋 Navigating to manuscripts...")
        await extractor._navigate_to_manuscripts()
        
        # Get manuscript list
        print("📄 Getting manuscript list...")
        manuscripts = await extractor._get_manuscripts()
        
        if not manuscripts:
            print("❌ No manuscripts found")
            return
        
        # Take the first manuscript for debugging
        first_ms = manuscripts[0]
        print(f"🔍 Debugging manuscript: {first_ms.id}")
        
        # Navigate to manuscript detail page
        await extractor.page.goto(f"{extractor.base_url}/cgi-bin/main.plex?form_type=display_auth_page&j_id=8&ms_id={first_ms.id}&ms_rev_no=0")
        await extractor.page.wait_for_load_state("networkidle")
        
        # Get page content
        content = await extractor.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Debug the table structure
        print("\n📊 Analyzing table structure...")
        tables = soup.find_all('table')
        print(f"Found {len(tables)} tables")
        
        for i, table in enumerate(tables):
            print(f"\n--- Table {i+1} ---")
            rows = table.find_all('tr')
            print(f"  Has {len(rows)} rows")
            
            for j, row in enumerate(rows[:5]):  # Show first 5 rows
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    print(f"    Row {j+1}: '{label}' = '{value[:50]}...'")
        
        # Also check for form elements
        print("\n📝 Checking form elements...")
        forms = soup.find_all('form')
        print(f"Found {len(forms)} forms")
        
        for i, form in enumerate(forms):
            inputs = form.find_all('input')
            print(f"  Form {i+1}: {len(inputs)} inputs")
            for inp in inputs[:3]:  # Show first 3 inputs
                name = inp.get('name', '')
                value = inp.get('value', '')
                input_type = inp.get('type', '')
                print(f"    Input: name='{name}', value='{value[:30]}...', type='{input_type}'")
        
        # Save the HTML for manual inspection
        debug_file = Path("debug_sicon_page.html")
        debug_file.write_text(content)
        print(f"\n💾 Saved page HTML to: {debug_file}")
        
        # Try to manually parse key fields
        print("\n🔍 Manual parsing attempt...")
        
        # Look for title patterns
        title_patterns = ['Title', 'Article Title', 'Manuscript Title']
        for pattern in title_patterns:
            elements = soup.find_all(string=lambda text: text and pattern in text)
            if elements:
                print(f"  Found '{pattern}' in {len(elements)} elements")
                for elem in elements[:2]:
                    parent = elem.parent
                    if parent:
                        print(f"    Context: {parent.name} - {str(parent)[:100]}...")
        
        # Look for author patterns
        author_patterns = ['Author', 'Corresponding Author', 'Contact Author']
        for pattern in author_patterns:
            elements = soup.find_all(string=lambda text: text and pattern in text)
            if elements:
                print(f"  Found '{pattern}' in {len(elements)} elements")
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        if extractor.page:
            await extractor.page.close()
        if extractor.browser:
            await extractor.browser.close()

if __name__ == "__main__":
    asyncio.run(debug_metadata_parsing())