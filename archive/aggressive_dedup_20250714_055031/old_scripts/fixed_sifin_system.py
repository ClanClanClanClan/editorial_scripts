#!/usr/bin/env python3
"""
Fixed SIFIN Scraper with Persistent Cache System and Referee Analytics Preservation
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
import hashlib
import aiofiles
import aiohttp
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PersistentManuscriptCache:
    """Persistent cache system that preserves referee analytics forever"""
    
    def __init__(self, base_dir: Path):
        self.cache_dir = base_dir / "persistent_cache"
        self.manuscripts_dir = self.cache_dir / "manuscripts"
        self.referees_dir = self.cache_dir / "referees" 
        self.analytics_dir = self.cache_dir / "analytics"
        
        # Create directories
        for directory in [self.cache_dir, self.manuscripts_dir, self.referees_dir, self.analytics_dir]:
            directory.mkdir(exist_ok=True)
        
        self.active_manuscripts: Set[str] = set()
        self.archived_manuscripts: Set[str] = set()
    
    def get_manuscript_file(self, journal: str, manuscript_id: str) -> Path:
        """Get manuscript cache file path"""
        return self.manuscripts_dir / f"{journal.lower()}_{manuscript_id}.json"
    
    def get_referee_file(self, referee_email: str) -> Path:
        """Get referee analytics file path"""
        email_hash = hashlib.md5(referee_email.encode()).hexdigest()
        return self.referees_dir / f"referee_{email_hash}.json"
    
    def get_analytics_file(self, journal: str, date: str) -> Path:
        """Get analytics summary file path"""
        return self.analytics_dir / f"{journal.lower()}_analytics_{date}.json"
    
    async def load_manuscript(self, journal: str, manuscript_id: str) -> Optional[Dict[str, Any]]:
        """Load manuscript from persistent cache"""
        cache_file = self.get_manuscript_file(journal, manuscript_id)
        
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    logger.info(f"📁 Loaded cached manuscript {manuscript_id}")
                    return data
            except Exception as e:
                logger.warning(f"Failed to load manuscript cache {cache_file}: {e}")
        
        return None
    
    async def save_manuscript(self, journal: str, manuscript_id: str, data: Dict[str, Any]):
        """Save manuscript to persistent cache"""
        cache_file = self.get_manuscript_file(journal, manuscript_id)
        
        # Add cache metadata
        data['cache_metadata'] = {
            'last_updated': datetime.now().isoformat(),
            'journal': journal,
            'manuscript_id': manuscript_id,
            'status': 'active'
        }
        
        try:
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps(data, indent=2, default=str))
            
            self.active_manuscripts.add(f"{journal}_{manuscript_id}")
            logger.info(f"💾 Saved manuscript {manuscript_id} to persistent cache")
        except Exception as e:
            logger.error(f"Failed to save manuscript cache {cache_file}: {e}")
    
    async def save_referee_analytics(self, referee_email: str, analytics_data: Dict[str, Any]):
        """Save referee analytics (preserved forever)"""
        cache_file = self.get_referee_file(referee_email)
        
        # Load existing analytics if present
        existing_data = {}
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    content = await f.read()
                    existing_data = json.loads(content)
            except:
                pass
        
        # Merge with existing data (preserve history)
        if 'review_history' not in existing_data:
            existing_data['review_history'] = []
        
        # Add new analytics entry
        new_entry = {
            'timestamp': datetime.now().isoformat(),
            'manuscript_data': analytics_data,
            'extraction_session': analytics_data.get('extraction_session', 'unknown')
        }
        
        existing_data['review_history'].append(new_entry)
        existing_data['referee_email'] = referee_email
        existing_data['last_activity'] = datetime.now().isoformat()
        existing_data['total_manuscripts_reviewed'] = len(existing_data['review_history'])
        
        try:
            async with aiofiles.open(cache_file, 'w') as f:
                await f.write(json.dumps(existing_data, indent=2, default=str))
            
            logger.info(f"📊 Preserved referee analytics for {referee_email}")
        except Exception as e:
            logger.error(f"Failed to save referee analytics {cache_file}: {e}")
    
    async def mark_manuscript_archived(self, journal: str, manuscript_id: str):
        """Mark manuscript as archived (removed from active website)"""
        cache_file = self.get_manuscript_file(journal, manuscript_id)
        
        if cache_file.exists():
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                
                # Update status to archived
                if 'cache_metadata' not in data:
                    data['cache_metadata'] = {}
                
                data['cache_metadata']['status'] = 'archived'
                data['cache_metadata']['archived_date'] = datetime.now().isoformat()
                
                async with aiofiles.open(cache_file, 'w') as f:
                    await f.write(json.dumps(data, indent=2, default=str))
                
                # Move to archived set
                active_key = f"{journal}_{manuscript_id}"
                if active_key in self.active_manuscripts:
                    self.active_manuscripts.remove(active_key)
                self.archived_manuscripts.add(active_key)
                
                logger.info(f"📦 Archived manuscript {manuscript_id}")
            except Exception as e:
                logger.error(f"Failed to archive manuscript {manuscript_id}: {e}")
    
    async def get_active_manuscripts(self, journal: str) -> List[str]:
        """Get list of currently active manuscript IDs for a journal"""
        active_ids = []
        
        pattern = f"{journal.lower()}_*.json"
        for cache_file in self.manuscripts_dir.glob(pattern):
            try:
                async with aiofiles.open(cache_file, 'r') as f:
                    content = await f.read()
                    data = json.loads(content)
                    
                    status = data.get('cache_metadata', {}).get('status', 'active')
                    if status == 'active':
                        manuscript_id = data.get('cache_metadata', {}).get('manuscript_id')
                        if manuscript_id:
                            active_ids.append(manuscript_id)
            except:
                continue
        
        return active_ids
    
    async def update_manuscript_lifecycle(self, journal: str, current_manuscript_ids: List[str]):
        """Update manuscript lifecycle - archive manuscripts no longer on website"""
        cached_active = await self.get_active_manuscripts(journal)
        current_ids_set = set(current_manuscript_ids)
        cached_ids_set = set(cached_active)
        
        # Archive manuscripts that are no longer on the website
        to_archive = cached_ids_set - current_ids_set
        
        for manuscript_id in to_archive:
            await self.mark_manuscript_archived(journal, manuscript_id)
            logger.info(f"🗄️ Archived {manuscript_id} - no longer on {journal} website")
        
        # Report new manuscripts
        new_manuscripts = current_ids_set - cached_ids_set
        if new_manuscripts:
            logger.info(f"🆕 New manuscripts in {journal}: {', '.join(new_manuscripts)}")
        
        return {
            'archived_count': len(to_archive),
            'new_count': len(new_manuscripts),
            'archived_manuscripts': list(to_archive),
            'new_manuscripts': list(new_manuscripts)
        }


class FixedSIFINScraper:
    """Fixed SIFIN scraper with improved authentication and navigation"""
    
    def __init__(self):
        self.base_url = "http://sifin.siam.org"
        self.folder_id = "1800"  # Try SICON's working folder ID first
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Load credentials
        self.username = os.getenv('ORCID_USERNAME')
        self.password = os.getenv('ORCID_PASSWORD')
        
        if not self.username or not self.password:
            raise ValueError("ORCID credentials not found in environment")
    
    async def authenticate_and_navigate(self, page):
        """Improved SIFIN authentication with better modal handling"""
        logger.info("🔐 Starting improved SIFIN authentication")
        
        # Navigate to SIFIN
        await page.goto(self.base_url, wait_until="networkidle")
        
        # Wait and handle any initial modals
        await asyncio.sleep(3)
        
        # Handle cookie consent modal (common issue)
        try:
            cookie_accept = page.locator("button:has-text('Accept')")
            if await cookie_accept.is_visible(timeout=2000):
                await cookie_accept.click()
                await page.wait_for_load_state("networkidle")
                logger.info("✓ Accepted cookie consent")
        except:
            pass
        
        # Look for ORCID login link
        orcid_selectors = [
            "a:has-text('ORCID')",
            "a[href*='orcid']",
            "button:has-text('ORCID')",
            ".orcid-login",
            "#orcid-login"
        ]
        
        orcid_clicked = False
        for selector in orcid_selectors:
            try:
                orcid_link = page.locator(selector).first
                if await orcid_link.is_visible(timeout=2000):
                    await orcid_link.click()
                    await page.wait_for_load_state("networkidle")
                    logger.info(f"🔗 Clicked ORCID login using selector: {selector}")
                    orcid_clicked = True
                    break
            except:
                continue
        
        if not orcid_clicked:
            logger.error("❌ Could not find ORCID login link")
            return False
        
        # Wait for ORCID page
        await asyncio.sleep(3)
        
        # Handle privacy notification modal (SIFIN-specific)
        try:
            continue_button = page.locator("button:has-text('Continue')").first
            if await continue_button.is_visible(timeout=5000):
                await continue_button.click()
                await page.wait_for_load_state("networkidle")
                logger.info("✓ Handled privacy notification modal")
        except:
            logger.info("No privacy notification modal found")
        
        # Fill ORCID credentials
        try:
            username_field = page.locator("input[name='userId'], input[type='email'], #username")
            password_field = page.locator("input[name='password'], input[type='password'], #password")
            
            await username_field.fill(self.username)
            await password_field.fill(self.password)
            
            # Submit form
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:has-text('Sign in')",
                "#signin-button"
            ]
            
            for selector in submit_selectors:
                try:
                    submit_btn = page.locator(selector).first
                    if await submit_btn.is_visible(timeout=2000):
                        await submit_btn.click()
                        logger.info("🔑 Submitted ORCID credentials")
                        break
                except:
                    continue
            
            # Wait for authentication
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"❌ ORCID authentication failed: {e}")
            return False
        
        # Verify we're back on SIFIN site
        current_url = page.url
        if "sifin.siam.org" in current_url:
            logger.info("✅ Successfully authenticated with SIFIN")
            return True
        else:
            logger.error(f"❌ Authentication failed - still on: {current_url}")
            return False
    
    async def navigate_to_manuscripts(self, page):
        """Navigate to manuscripts folder with multiple folder ID attempts"""
        logger.info("📂 Navigating to manuscripts folder")
        
        # Try multiple folder IDs
        folder_ids_to_try = ["1800", "1802", "1804", "1806"]  # Common SIAM folder IDs
        
        for folder_id in folder_ids_to_try:
            try:
                folder_url = f"{self.base_url}/PeerReview/folders/{folder_id}"
                logger.info(f"🔍 Trying folder ID: {folder_id}")
                
                await page.goto(folder_url, wait_until="networkidle")
                await asyncio.sleep(3)
                
                # Check if we found manuscripts
                manuscript_selectors = [
                    "a[href*='/PeerReview/view/']",
                    ".manuscript-link",
                    "a:has-text('M')",
                    "tr td a"
                ]
                
                manuscripts_found = False
                for selector in manuscript_selectors:
                    manuscript_links = page.locator(selector)
                    count = await manuscript_links.count()
                    if count > 0:
                        logger.info(f"✅ Found {count} manuscripts in folder {folder_id}")
                        manuscripts_found = True
                        self.folder_id = folder_id  # Update working folder ID
                        break
                
                if manuscripts_found:
                    return True
                    
            except Exception as e:
                logger.warning(f"Folder {folder_id} failed: {e}")
                continue
        
        logger.error("❌ Could not find manuscripts in any folder")
        return False
    
    async def extract_manuscripts(self, page):
        """Extract manuscript data from SIFIN"""
        logger.info("📄 Extracting manuscript data")
        
        manuscripts = []
        
        # Get all manuscript links
        manuscript_selectors = [
            "a[href*='/PeerReview/view/']",
            "a:has-text('M')"
        ]
        
        manuscript_links = []
        for selector in manuscript_selectors:
            links = await page.locator(selector).all()
            manuscript_links.extend(links)
        
        if not manuscript_links:
            logger.error("No manuscript links found")
            return []
        
        logger.info(f"Found {len(manuscript_links)} manuscript links")
        
        for i, link in enumerate(manuscript_links[:10]):  # Limit to 10 for testing
            try:
                # Get manuscript ID from link text or href
                link_text = await link.text_content()
                href = await link.get_attribute('href')
                
                # Extract manuscript ID
                manuscript_id = None
                if link_text and link_text.startswith('M'):
                    manuscript_id = link_text.split()[0]
                elif href:
                    import re
                    match = re.search(r'M\d+', href)
                    if match:
                        manuscript_id = match.group()
                
                if not manuscript_id:
                    continue
                
                logger.info(f"📋 Processing manuscript {i+1}: {manuscript_id}")
                
                # Click on manuscript link
                await link.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                
                # Extract manuscript details
                manuscript_data = await self.extract_manuscript_details(page, manuscript_id)
                if manuscript_data:
                    manuscripts.append(manuscript_data)
                
                # Go back to manuscript list
                await page.go_back()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Failed to process manuscript {i+1}: {e}")
                continue
        
        logger.info(f"✅ Successfully extracted {len(manuscripts)} manuscripts")
        return manuscripts
    
    async def extract_manuscript_details(self, page, manuscript_id: str):
        """Extract detailed manuscript information"""
        try:
            # Get title
            title_selectors = ["h1", ".title", ".manuscript-title"]
            title = "Unknown Title"
            for selector in title_selectors:
                try:
                    title_elem = page.locator(selector).first
                    if await title_elem.is_visible(timeout=1000):
                        title = await title_elem.text_content()
                        break
                except:
                    continue
            
            # Extract referees
            referees = await self.extract_referees(page)
            
            manuscript_data = {
                'manuscript_id': manuscript_id,
                'title': title.strip() if title else "Unknown Title",
                'journal': 'SIFIN',
                'status': 'Under Review',
                'extraction_timestamp': datetime.now().isoformat(),
                'extraction_session': self.session_id,
                'referees': referees,
                'referee_count': len(referees),
                'files_downloaded': False  # Will be updated if PDFs are downloaded
            }
            
            logger.info(f"✅ Extracted {manuscript_id}: {len(referees)} referees")
            return manuscript_data
            
        except Exception as e:
            logger.error(f"Failed to extract details for {manuscript_id}: {e}")
            return None
    
    async def extract_referees(self, page):
        """Extract referee information from manuscript page"""
        referees = []
        
        # Look for referee sections
        referee_selectors = [
            ".referee", ".reviewer", ".peer-reviewer",
            "tr:has-text('Referee')", "tr:has-text('Reviewer')"
        ]
        
        for selector in referee_selectors:
            try:
                referee_elements = await page.locator(selector).all()
                
                for elem in referee_elements:
                    try:
                        text_content = await elem.text_content()
                        
                        # Extract email addresses
                        import re
                        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                        emails = re.findall(email_pattern, text_content)
                        
                        for email in emails:
                            # Extract name (text before email)
                            name_match = re.search(r'([A-Za-z\s]+)\s*' + re.escape(email), text_content)
                            name = name_match.group(1).strip() if name_match else email.split('@')[0]
                            
                            referee_data = {
                                'name': name,
                                'full_name': name,
                                'email': email.lower(),
                                'status': 'Extracted',
                                'extraction_success': True,
                                'source': 'sifin_scraper_fixed'
                            }
                            
                            # Avoid duplicates
                            if not any(r['email'] == email.lower() for r in referees):
                                referees.append(referee_data)
                    
                    except Exception as e:
                        continue
            
            except Exception as e:
                continue
        
        return referees
    
    async def run_extraction(self):
        """Run complete SIFIN extraction"""
        logger.info("🚀 Starting fixed SIFIN extraction")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)  # Visible for debugging
            page = await browser.new_page()
            
            try:
                # Authenticate
                if not await self.authenticate_and_navigate(page):
                    logger.error("❌ Authentication failed")
                    return None
                
                # Navigate to manuscripts
                if not await self.navigate_to_manuscripts(page):
                    logger.error("❌ Could not access manuscripts")
                    return None
                
                # Extract manuscripts
                manuscripts = await self.extract_manuscripts(page)
                
                if manuscripts:
                    results = {
                        'journal': 'SIFIN',
                        'extraction_time': datetime.now().isoformat(),
                        'session_id': self.session_id,
                        'folder_id_used': self.folder_id,
                        'manuscripts_found': len(manuscripts),
                        'manuscripts': manuscripts,
                        'success': True
                    }
                    
                    logger.info(f"🎉 SIFIN extraction successful: {len(manuscripts)} manuscripts")
                    return results
                else:
                    logger.error("❌ No manuscripts extracted from SIFIN")
                    return None
                
            except Exception as e:
                logger.error(f"❌ SIFIN extraction failed: {e}")
                return None
            finally:
                await browser.close()


class FixedSIAMSystem:
    """Enhanced SIAM system with fixed SIFIN and persistent caching"""
    
    def __init__(self):
        self.base_dir = Path(".")
        self.system_dir = self.base_dir / "fixed_siam_system"
        self.system_dir.mkdir(exist_ok=True)
        
        self.cache = PersistentManuscriptCache(self.system_dir)
        self.gmail_tracker = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize components"""
        try:
            from src.infrastructure.gmail_integration import GmailRefereeTracker
            self.gmail_tracker = GmailRefereeTracker()
            logger.info("✓ Components initialized")
        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise
    
    async def run_sifin_extraction_with_cache(self):
        """Run SIFIN extraction with persistent caching"""
        logger.info("🔄 Starting SIFIN extraction with persistent cache")
        
        # Extract fresh data from SIFIN
        scraper = FixedSIFINScraper()
        extraction_result = await scraper.run_extraction()
        
        if not extraction_result:
            logger.error("❌ SIFIN extraction failed")
            return None
        
        manuscripts = extraction_result.get('manuscripts', [])
        current_manuscript_ids = [ms['manuscript_id'] for ms in manuscripts]
        
        # Update manuscript lifecycle (archive removed manuscripts)
        lifecycle_update = await self.cache.update_manuscript_lifecycle('SIFIN', current_manuscript_ids)
        
        logger.info(f"📊 Lifecycle update: {lifecycle_update['new_count']} new, {lifecycle_update['archived_count']} archived")
        
        # Process each manuscript
        enhanced_manuscripts = []
        for manuscript in manuscripts:
            manuscript_id = manuscript['manuscript_id']
            
            # Check if we have cached data
            cached_data = await self.cache.load_manuscript('SIFIN', manuscript_id)
            
            if cached_data:
                # Merge new data with cached data (preserve referee analytics)
                logger.info(f"📁 Found cached data for {manuscript_id}")
                
                # Update status and timestamp but preserve referee analytics
                cached_data['current_status'] = manuscript['status']
                cached_data['last_seen_active'] = datetime.now().isoformat()
                
                # Add any new referees but preserve existing analytics
                existing_referee_emails = {r['email'] for r in cached_data.get('referees', [])}
                new_referees = [r for r in manuscript['referees'] if r['email'] not in existing_referee_emails]
                
                if new_referees:
                    cached_data['referees'].extend(new_referees)
                    logger.info(f"➕ Added {len(new_referees)} new referees to {manuscript_id}")
                
                enhanced_manuscript = cached_data
            else:
                # New manuscript - enhance with email analysis
                logger.info(f"🆕 New manuscript {manuscript_id} - performing full analysis")
                enhanced_manuscript = await self.enhance_manuscript_with_emails(manuscript)
            
            # Save/update persistent cache
            await self.cache.save_manuscript('SIFIN', manuscript_id, enhanced_manuscript)
            
            # Save referee analytics (preserved forever)
            for referee in enhanced_manuscript.get('referees', []):
                if referee.get('email'):
                    analytics_data = {
                        'manuscript_id': manuscript_id,
                        'journal': 'SIFIN',
                        'role': 'reviewer',
                        'extraction_session': self.session_id,
                        'referee_data': referee
                    }
                    await self.cache.save_referee_analytics(referee['email'], analytics_data)
            
            enhanced_manuscripts.append(enhanced_manuscript)
        
        # Generate results
        results = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'journal': 'SIFIN',
            'extraction_type': 'fixed_sifin_with_persistent_cache',
            'manuscripts': enhanced_manuscripts,
            'lifecycle_update': lifecycle_update,
            'summary': {
                'total_manuscripts': len(enhanced_manuscripts),
                'new_manuscripts': lifecycle_update['new_count'],
                'archived_manuscripts': lifecycle_update['archived_count'],
                'total_referees': sum(len(ms.get('referees', [])) for ms in enhanced_manuscripts)
            }
        }
        
        # Save results
        results_file = self.system_dir / f"sifin_extraction_results_{self.session_id}.json"
        async with aiofiles.open(results_file, 'w') as f:
            await f.write(json.dumps(results, indent=2, default=str))
        
        logger.info(f"💾 Results saved: {results_file}")
        return results
    
    async def enhance_manuscript_with_emails(self, manuscript: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance manuscript with Gmail analysis"""
        manuscript_id = manuscript.get('manuscript_id', '')
        
        # Search for related emails
        search_queries = [
            f'"{manuscript_id}"',
            f'subject:"{manuscript_id}"',
            f'from:sifin@siam.org',
            f'{manuscript_id} AND (referee OR review OR manuscript)'
        ]
        
        all_emails = []
        
        for query in search_queries:
            try:
                emails = self.gmail_tracker.search_emails(query, max_results=5)
                if emails:
                    all_emails.extend(emails)
            except Exception as e:
                logger.warning(f"Email search failed for '{query}': {e}")
        
        # Remove duplicates
        unique_emails = {}
        for email in all_emails:
            email_id = email.get('id') or email.get('message_id')
            if email_id and email_id not in unique_emails:
                unique_emails[email_id] = email
        
        final_emails = list(unique_emails.values())
        
        # Add email enhancement
        manuscript['email_enhancement'] = {
            'related_emails_count': len(final_emails),
            'related_emails': final_emails[:5],  # Keep top 5
            'email_analysis_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"📧 Enhanced {manuscript_id} with {len(final_emails)} related emails")
        return manuscript


async def main():
    """Run fixed SIFIN system"""
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        # Initialize system
        system = FixedSIAMSystem()
        
        # Run SIFIN extraction with persistent caching
        results = await system.run_sifin_extraction_with_cache()
        
        if results:
            summary = results['summary']
            logger.info(f"\\n{'='*60}")
            logger.info("FIXED SIFIN EXTRACTION COMPLETE")
            logger.info('='*60)
            logger.info(f"📊 Total manuscripts: {summary['total_manuscripts']}")
            logger.info(f"🆕 New manuscripts: {summary['new_manuscripts']}")
            logger.info(f"🗄️ Archived manuscripts: {summary['archived_manuscripts']}")
            logger.info(f"👥 Total referees: {summary['total_referees']}")
            logger.info(f"💾 Persistent cache updated with referee analytics")
            
            return True
        else:
            logger.error("❌ SIFIN extraction failed")
            return False
        
    except Exception as e:
        logger.error(f"System failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)