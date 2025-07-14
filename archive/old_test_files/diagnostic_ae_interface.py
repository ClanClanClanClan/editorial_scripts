#!/usr/bin/env python3
"""
Diagnostic script to understand what's currently available in MF and MOR Associate Editor interfaces.
This will help identify why manuscripts aren't being found.
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

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_driver():
    """Create Chrome driver"""
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    try:
        return uc.Chrome(options=options)
    except Exception as e:
        logger.warning(f"Undetected Chrome failed: {e}")
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        for arg in options.arguments:
            chrome_options.add_argument(arg)
        return webdriver.Chrome(options=chrome_options)


def save_diagnostic_info(driver, journal_name, stage):
    """Save diagnostic information"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path("diagnostic_output")
    output_dir.mkdir(exist_ok=True)
    
    # Save screenshot
    screenshot_path = output_dir / f"{journal_name}_{stage}_{timestamp}.png"
    driver.save_screenshot(str(screenshot_path))
    
    # Save HTML
    html_path = output_dir / f"{journal_name}_{stage}_{timestamp}.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)
    
    # Save URL and title
    info = {
        'url': driver.current_url,
        'title': driver.title,
        'timestamp': timestamp,
        'stage': stage
    }
    info_path = output_dir / f"{journal_name}_{stage}_{timestamp}_info.json"
    with open(info_path, 'w') as f:
        json.dump(info, f, indent=2)
    
    logger.info(f"📸 Saved diagnostic info: {screenshot_path}")
    return html_path


def analyze_page_content(html_content, journal_name):
    """Analyze page content to understand what's available"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    analysis = {
        'journal': journal_name,
        'analysis_time': datetime.now().isoformat(),
        'page_type': 'unknown',
        'links_found': [],
        'status_indicators': [],
        'manuscript_ids': [],
        'tables_with_manuscripts': 0,
        'navigation_options': []
    }
    
    # Detect page type
    page_text = soup.get_text().lower()
    if 'associate editor' in page_text:
        analysis['page_type'] = 'associate_editor'
    elif 'manuscript details' in page_text:
        analysis['page_type'] = 'manuscript_details'
    elif 'login' in page_text:
        analysis['page_type'] = 'login'
    elif 'home' in page_text:
        analysis['page_type'] = 'home'
    
    # Find all links
    for link in soup.find_all('a'):
        link_text = link.get_text(strip=True)
        href = link.get('href', '')
        if link_text:
            analysis['links_found'].append({
                'text': link_text,
                'href': href,
                'relevant': any(keyword in link_text.lower() for keyword in [
                    'manuscript', 'reviewer', 'awaiting', 'assignment', 'decision', 'editor'
                ])
            })
    
    # Find status indicators
    for element in soup.find_all(['td', 'span', 'div', 'p']):
        text = element.get_text(strip=True)
        if any(status in text for status in [
            'Awaiting', 'Under Review', 'Overdue', 'Ready for', 'New Submission'
        ]):
            analysis['status_indicators'].append(text)
    
    # Find manuscript IDs
    if journal_name == 'MF':
        pattern = r'MAFI-\d{4}-\d+'
    else:
        pattern = r'MOR-\d{4}-\d+'
    
    import re
    all_text = soup.get_text()
    manuscript_ids = list(set(re.findall(pattern, all_text)))
    analysis['manuscript_ids'] = manuscript_ids
    
    # Count tables with manuscripts
    tables = soup.find_all('table')
    for table in tables:
        table_text = table.get_text()
        if re.search(pattern, table_text):
            analysis['tables_with_manuscripts'] += 1
    
    # Find navigation options
    for element in soup.find_all(['li', 'div', 'span']):
        if element.find('a'):
            nav_text = element.get_text(strip=True)
            if any(keyword in nav_text.lower() for keyword in [
                'awaiting', 'under review', 'assignment', 'decision', 'manuscript'
            ]):
                analysis['navigation_options'].append(nav_text)
    
    return analysis


def diagnose_journal(journal_name):
    """Comprehensive diagnosis of a journal's AE interface"""
    logger.info(f"🔍 Starting diagnostic for {journal_name}")
    
    driver = create_driver()
    diagnosis = {
        'journal': journal_name,
        'start_time': datetime.now().isoformat(),
        'stages': {},
        'summary': {},
        'recommendations': []
    }
    
    try:
        # Login
        if journal_name == 'MF':
            from journals.mf import MFJournal
            url = 'https://mc.manuscriptcentral.com/mafi'
            journal = MFJournal(driver, debug=True)
        else:
            from journals.mor import MORJournal  
            url = 'https://mc.manuscriptcentral.com/mathor'
            journal = MORJournal(driver, debug=True)
        
        # Stage 1: Initial connection
        logger.info(f"🌐 Stage 1: Connecting to {journal_name}")
        driver.get(url)
        time.sleep(3)
        
        html_path = save_diagnostic_info(driver, journal_name, 'initial_connection')
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        diagnosis['stages']['initial_connection'] = analyze_page_content(html_content, journal_name)
        
        # Stage 2: After login
        logger.info(f"🔐 Stage 2: Logging in to {journal_name}")
        journal.login()
        time.sleep(3)
        
        html_path = save_diagnostic_info(driver, journal_name, 'after_login')
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        diagnosis['stages']['after_login'] = analyze_page_content(html_content, journal_name)
        
        # Stage 3: Try to find Associate Editor Center
        logger.info(f"📋 Stage 3: Looking for Associate Editor interface")
        
        # Try to find AE center
        ae_found = False
        for attempt in range(5):
            try:
                links = driver.find_elements(By.XPATH, "//a")
                for link in links:
                    link_text = link.text.strip().lower()
                    if any(phrase in link_text for phrase in [
                        "associate editor", "editor center", "assignment center"
                    ]):
                        logger.info(f"Found AE link: '{link.text.strip()}'")
                        driver.execute_script("arguments[0].scrollIntoView(true);", link)
                        link.click()
                        time.sleep(3)
                        ae_found = True
                        break
                
                if ae_found:
                    break
                    
            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} failed: {e}")
                time.sleep(1)
        
        if ae_found:
            html_path = save_diagnostic_info(driver, journal_name, 'ae_center')
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            diagnosis['stages']['ae_center'] = analyze_page_content(html_content, journal_name)
        else:
            logger.warning(f"Could not find AE center for {journal_name}")
            diagnosis['stages']['ae_center'] = {'error': 'AE center not found'}
        
        # Stage 4: Deep analysis of current page
        logger.info(f"🔬 Stage 4: Deep analysis of current state")
        
        # Get all links and their purposes
        all_links = driver.find_elements(By.XPATH, "//a")
        link_analysis = []
        for link in all_links:
            try:
                link_text = link.text.strip()
                href = link.get_attribute('href') or ''
                onclick = link.get_attribute('onclick') or ''
                
                if link_text:
                    link_analysis.append({
                        'text': link_text,
                        'href': href,
                        'onclick': onclick,
                        'relevant_score': sum([
                            'manuscript' in link_text.lower(),
                            'awaiting' in link_text.lower(),
                            'reviewer' in link_text.lower(),
                            'assignment' in link_text.lower(),
                            'decision' in link_text.lower(),
                            'under review' in link_text.lower()
                        ])
                    })
            except:
                continue
        
        # Sort by relevance
        link_analysis.sort(key=lambda x: x['relevant_score'], reverse=True)
        
        html_path = save_diagnostic_info(driver, journal_name, 'deep_analysis')
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        deep_analysis = analyze_page_content(html_content, journal_name)
        deep_analysis['detailed_links'] = link_analysis[:20]  # Top 20 most relevant links
        
        diagnosis['stages']['deep_analysis'] = deep_analysis
        
        # Generate summary and recommendations
        manuscript_count = len(deep_analysis.get('manuscript_ids', []))
        status_count = len(deep_analysis.get('status_indicators', []))
        relevant_links = len([l for l in link_analysis if l['relevant_score'] > 0])
        
        diagnosis['summary'] = {
            'manuscripts_found': manuscript_count,
            'status_indicators_found': status_count,
            'relevant_links_found': relevant_links,
            'ae_center_accessible': ae_found,
            'current_page_type': deep_analysis.get('page_type', 'unknown')
        }
        
        # Recommendations
        if manuscript_count == 0:
            diagnosis['recommendations'].append("❌ No manuscripts found - may indicate no current assignments or navigation issues")
        else:
            diagnosis['recommendations'].append(f"✅ Found {manuscript_count} manuscripts")
        
        if not ae_found:
            diagnosis['recommendations'].append("⚠️ AE center not accessible - may need different navigation approach")
        
        if relevant_links > 0:
            diagnosis['recommendations'].append(f"🔗 Found {relevant_links} potentially relevant navigation links")
        
        logger.info(f"✅ {journal_name} diagnosis complete")
        
    except Exception as e:
        diagnosis['error'] = str(e)
        logger.error(f"❌ {journal_name} diagnosis failed: {e}")
        
    finally:
        driver.quit()
    
    diagnosis['end_time'] = datetime.now().isoformat()
    return diagnosis


def main():
    print("🔬 MF and MOR Associate Editor Interface Diagnostic")
    print("=" * 60)
    print("This script analyzes what's currently available in your")
    print("Associate Editor interfaces to understand navigation issues.")
    print("=" * 60)
    
    # Load credentials
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    results = {}
    
    # Diagnose both journals
    for journal in ['MF', 'MOR']:
        print(f"\\n🔍 Diagnosing {journal}...")
        results[journal] = diagnose_journal(journal)
    
    # Save comprehensive results
    output_dir = Path("diagnostic_output")
    output_dir.mkdir(exist_ok=True)
    
    results_file = output_dir / f"comprehensive_diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Display summary
    print("\\n" + "=" * 60)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    
    for journal, data in results.items():
        print(f"\\n📋 {journal} Journal:")
        summary = data.get('summary', {})
        print(f"  Manuscripts Found: {summary.get('manuscripts_found', 0)}")
        print(f"  Status Indicators: {summary.get('status_indicators_found', 0)}")
        print(f"  Relevant Links: {summary.get('relevant_links_found', 0)}")
        print(f"  AE Center Access: {'✅' if summary.get('ae_center_accessible') else '❌'}")
        print(f"  Current Page Type: {summary.get('current_page_type', 'unknown')}")
        
        # Show recommendations
        recommendations = data.get('recommendations', [])
        if recommendations:
            print(f"  Recommendations:")
            for rec in recommendations:
                print(f"    • {rec}")
    
    print(f"\\n📁 Full diagnostic data saved to: {results_file}")
    print(f"📁 Debug files saved to: diagnostic_output/")
    
    # Determine if manuscripts are findable
    total_manuscripts = sum(r.get('summary', {}).get('manuscripts_found', 0) for r in results.values())
    
    if total_manuscripts > 0:
        print(f"\\n✅ SUCCESS: Found {total_manuscripts} total manuscripts across both journals!")
        print("The scrapers can be fixed to access these manuscripts.")
        return 0
    else:
        print(f"\\n⚠️ No manuscripts found in either journal.")
        print("This may indicate:")
        print("  1. No current manuscript assignments")
        print("  2. Navigation/access issues")
        print("  3. Different interface than expected")
        return 1


if __name__ == "__main__":
    exit(main())