#!/usr/bin/env python3
"""Direct SIFIN test to check document extraction"""

import asyncio
import os
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def test_sifin_documents():
    print("🧪 DIRECT SIFIN DOCUMENT EXTRACTION TEST")
    print("=" * 60)
    
    email = "dylan.possamai@polytechnique.org"
    password = "Hioupy0042%"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        try:
            # Navigate to SIFIN
            print("📍 Navigating to SIFIN...")
            await page.goto("http://sifin.siam.org/cgi-bin/main.plex", timeout=30000)
            await page.wait_for_timeout(5000)
            
            # Dismiss modals
            await page.evaluate("if(document.getElementById('cookie-policy-layer-bg')) document.getElementById('cookie-policy-layer-bg').style.display = 'none';")
            
            # Click ORCID
            print("🔗 Clicking ORCID...")
            orcid_img = page.locator("img[src*='orcid']").first
            if await orcid_img.is_visible():
                parent_link = orcid_img.locator("..")
                await parent_link.click()
                await page.wait_for_timeout(5000)
            
            # Handle ORCID authentication
            if "orcid.org" in page.url:
                print("🔐 On ORCID page...")
                
                # Accept cookies
                accept_btn = page.locator("button:has-text('Accept All Cookies')").first
                if await accept_btn.is_visible():
                    await accept_btn.click()
                    await page.wait_for_timeout(3000)
                
                # Click Sign in
                signin_btn = page.get_by_role("button", name="Sign in to ORCID")
                if await signin_btn.is_visible():
                    await signin_btn.click()
                    await page.wait_for_timeout(5000)
                
                # Enter credentials
                await page.fill("input[placeholder*='Email or']", email)
                await page.fill("input[placeholder*='password']", password)
                
                # Submit
                submit_btn = page.locator("button:has-text('Sign in to ORCID')").last
                await submit_btn.click()
                
                print("⏳ Waiting for authentication...")
                await page.wait_for_timeout(10000)
            
            # Check if back on SIFIN
            if "sifin.siam.org" in page.url:
                print("✅ Back on SIFIN - authenticated!")
                
                # Get page content
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                # Find manuscripts
                print("\n🔍 Looking for manuscripts...")
                ms_links = soup.find_all('a', {'class': 'ndt_task_link'})
                
                if ms_links:
                    print(f"✅ Found {len(ms_links)} manuscript links")
                    
                    # Show all links to find manuscripts
                    print("\n📋 All manuscript links:")
                    manuscripts = []
                    for i, ms in enumerate(ms_links[:10]):
                        text = ms.text.strip()
                        print(f"   {i+1}. {text[:80]}...")
                        if 'M1' in text and ' - ' in text:  # Likely a manuscript
                            manuscripts.append(ms)
                    
                    if not manuscripts:
                        print("❌ No actual manuscripts found - using first non-instruction link")
                        # Skip Author Instructions
                        for ms in ms_links:
                            if 'Author Instructions' not in ms.text:
                                actual_manuscript = ms
                                break
                    else:
                        actual_manuscript = manuscripts[0]
                    
                    if not actual_manuscript:
                        print("❌ No suitable manuscript found")
                        return
                    
                    ms_text = actual_manuscript.text.strip()
                    ms_id = ms_text.split(' - ')[0].replace('#', '')
                    print(f"\n📄 Checking manuscript: {ms_id}")
                    
                    # Dismiss all modals
                    await page.evaluate("""
                        // Dismiss cookie modal background
                        if(document.getElementById('cookie-policy-layer-bg')) 
                            document.getElementById('cookie-policy-layer-bg').style.display = 'none';
                        
                        // Dismiss privacy notification modal
                        if(document.getElementById('cookie-policy-layer')) 
                            document.getElementById('cookie-policy-layer').style.display = 'none';
                    """)
                    await page.wait_for_timeout(1000)
                    
                    # Click manuscript link
                    ms_selector = f"a:has-text('{ms_id}')"
                    await page.click(ms_selector)
                    await page.wait_for_timeout(5000)
                    
                    # Get manuscript details page
                    ms_content = await page.content()
                    ms_soup = BeautifulSoup(ms_content, 'html.parser')
                    
                    print("\n📎 Document Analysis:")
                    
                    # Look for PDF links
                    pdf_links = ms_soup.find_all('a', href=lambda x: x and '.pdf' in x.lower())
                    print(f"   PDF links found: {len(pdf_links)}")
                    
                    for link in pdf_links[:5]:
                        href = link.get('href')
                        text = link.get_text(strip=True)
                        print(f"   - {text}: {href}")
                    
                    # Look for download links
                    download_links = ms_soup.find_all('a', href=lambda x: x and 'download' in str(x).lower())
                    print(f"\n   Download links found: {len(download_links)}")
                    
                    for link in download_links[:5]:
                        href = link.get('href')
                        text = link.get_text(strip=True)
                        print(f"   - {text}: {href}")
                    
                    # Look for specific document sections
                    print("\n   Document sections:")
                    
                    # Check for manuscript files
                    if "manuscript" in ms_content.lower() and "pdf" in ms_content.lower():
                        print("   ✅ Manuscript PDF section found")
                    
                    # Check for cover letter
                    if "cover letter" in ms_content.lower():
                        print("   ✅ Cover letter section found")
                    
                    # Check for referee reports
                    if "referee" in ms_content.lower() and "report" in ms_content.lower():
                        print("   ✅ Referee reports section found")
                    
                    # Save page for analysis
                    await page.screenshot(path="sifin_manuscript_detail.png")
                    print("\n📸 Screenshot saved: sifin_manuscript_detail.png")
                    
                    # Save HTML for deeper analysis
                    with open('sifin_manuscript_page.html', 'w') as f:
                        f.write(ms_content)
                    print("📄 HTML saved: sifin_manuscript_page.html")
                    
                else:
                    print("❌ No manuscript links found")
            
            print("\n⏸️ Browser open for 15 seconds...")
            await page.wait_for_timeout(15000)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(test_sifin_documents())