"""
SICON Extractor - REAL FIX based on actual workflow
"""

import asyncio
import logging
import re
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from bs4 import BeautifulSoup
from pathlib import Path

from .base import SIAMBaseExtractor
from ...core.base_extractor import Manuscript, Referee

logger = logging.getLogger(__name__)


class SICONRealExtractor(SIAMBaseExtractor):
    """
    REAL SICON extractor that actually works
    Features:
    - Smart caching with checksum-based change detection
    - Complete PDF extraction (manuscripts, reports, cover letters)
    - Email crosschecking with Gmail integration
    - Proper name formatting and status parsing
    """
    
    journal_name = "SICON"
    base_url = "https://sicon.siam.org"
    
    def __init__(self, cache_dir: Optional[Path] = None, output_dir: Optional[Path] = None):
        super().__init__(cache_dir, output_dir)
        # Use existing enhanced systems
        from ...core.smart_cache_manager import SmartCacheManager
        from ...core.enhanced_pdf_manager import EnhancedPDFManager
        
        self.cache_manager = SmartCacheManager(cache_dir=self.cache_dir)
        
        # Setup PDF manager with storage config
        from ...core.enhanced_pdf_manager import EnhancedPDFManager, DocumentStorage
        storage_config = DocumentStorage(
            base_path=self.output_dir / "pdfs",
            organize_by_journal=True,
            organize_by_year=True,
            organize_by_manuscript=True
        )
        self.pdf_manager = EnhancedPDFManager(
            storage_config=storage_config,
            journal_name=self.journal_name
        )
    
    def _get_content_hash(self, content: str) -> str:
        """Generate hash for content-based caching"""
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cache_path(self, ms_id: str, cache_type: str = "manuscript") -> Path:
        """Get cache file path for manuscript"""
        return self.cache_dir / f"{ms_id}_{cache_type}.json"
    
    def _load_cached_manuscript(self, ms_id: str, content_hash: str) -> Optional[Manuscript]:
        """Load manuscript from cache if content unchanged"""
        try:
            cache_path = self._get_cache_path(ms_id)
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    cached_data = json.load(f)
                
                # Check if content hash matches (no changes)
                if cached_data.get('content_hash') == content_hash:
                    logger.info(f"   💾 Using cached data for {ms_id} (no changes)")
                    return self._deserialize_manuscript(cached_data['manuscript'])
                else:
                    logger.info(f"   🔄 Content changed for {ms_id}, updating cache")
        except Exception as e:
            logger.warning(f"Cache load failed for {ms_id}: {e}")
        
        return None
    
    def _save_manuscript_to_cache(self, manuscript: Manuscript, content_hash: str):
        """Save manuscript to cache with content hash"""
        try:
            cache_path = self._get_cache_path(manuscript.id)
            cache_data = {
                'content_hash': content_hash,
                'timestamp': datetime.now().isoformat(),
                'manuscript': self._serialize_manuscript(manuscript)
            }
            
            with open(cache_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"   💾 Saved {manuscript.id} to cache")
        except Exception as e:
            logger.error(f"Cache save failed for {manuscript.id}: {e}")
    
    def _serialize_manuscript(self, manuscript: Manuscript) -> dict:
        """Convert manuscript to serializable dict"""
        return {
            'id': manuscript.id,
            'title': manuscript.title,
            'authors': manuscript.authors,
            'status': manuscript.status,
            'submission_date': getattr(manuscript, 'submission_date', None),
            'journal': manuscript.journal,
            'corresponding_editor': getattr(manuscript, 'corresponding_editor', None),
            'associate_editor': getattr(manuscript, 'associate_editor', None),
            'referees': [self._serialize_referee(ref) for ref in manuscript.referees],
            'pdf_urls': manuscript.pdf_urls or {},
            'pdf_paths': manuscript.pdf_paths or {},
            'referee_reports': manuscript.referee_reports or {}
        }
    
    def _serialize_referee(self, referee: Referee) -> dict:
        """Convert referee to serializable dict"""
        return {
            'name': referee.name,
            'email': referee.email,
            'status': referee.status,
            'institution': getattr(referee, 'institution', None),
            'report_submitted': getattr(referee, 'report_submitted', False),
            'report_date': getattr(referee, 'report_date', None),
            'contact_date': getattr(referee, 'contact_date', None),
            'due_date': getattr(referee, 'due_date', None),
            'declined': getattr(referee, 'declined', False),
            'reminder_count': referee.reminder_count,
            'days_since_invited': referee.days_since_invited
        }
    
    def _deserialize_manuscript(self, data: dict) -> Manuscript:
        """Convert dict back to Manuscript object"""
        manuscript = Manuscript(
            id=data['id'],
            title=data['title'],
            authors=data['authors'],
            status=data['status'],
            journal=data['journal']
        )
        
        # Set optional attributes
        manuscript.submission_date = data.get('submission_date')
        manuscript.corresponding_editor = data.get('corresponding_editor')
        manuscript.associate_editor = data.get('associate_editor')
        manuscript.pdf_urls = data.get('pdf_urls', {})
        manuscript.pdf_paths = data.get('pdf_paths', {})
        manuscript.referee_reports = data.get('referee_reports', {})
        
        # Deserialize referees
        manuscript.referees = [self._deserialize_referee(ref_data) for ref_data in data.get('referees', [])]
        
        return manuscript
    
    def _deserialize_referee(self, data: dict) -> Referee:
        """Convert dict back to Referee object"""
        referee = Referee(
            name=data['name'],
            email=data['email'],
            status=data['status'],
            institution=data.get('institution'),
            report_submitted=data.get('report_submitted', False),
            report_date=data.get('report_date'),
            reminder_count=data.get('reminder_count', 0),
            days_since_invited=data.get('days_since_invited')
        )
        
        # Set additional attributes
        referee.contact_date = data.get('contact_date')
        referee.due_date = data.get('due_date')
        referee.declined = data.get('declined', False)
        
        return referee
    
    async def _crosscheck_emails(self, manuscript: Manuscript):
        """COMPREHENSIVE email crosschecking with detailed communication timeline analysis"""
        try:
            logger.info(f"   📧 Building comprehensive communication timeline for {manuscript.id}...")
            
            # Use the EXISTING Gmail integration
            try:
                from ....src.infrastructure.gmail_integration import GmailRefereeTracker
                from ....unified_system.core.enhanced_email_tracker import EnhancedEmailTracker
                
                gmail_tracker = GmailRefereeTracker()
                email_tracker = EnhancedEmailTracker()
                
                for referee in manuscript.referees:
                    if referee.email:
                        try:
                            logger.info(f"     📊 Analyzing communication timeline for {referee.name}...")
                            
                            # Build comprehensive communication story
                            communication_story = await self._build_communication_story(
                                referee, manuscript.id, gmail_tracker, email_tracker
                            )
                            
                            # Update referee with detailed timeline data
                            self._update_referee_timeline(referee, communication_story)
                            
                            # Log the communication story
                            self._log_communication_summary(referee, communication_story)
                            
                        except Exception as e:
                            logger.warning(f"     ⚠️ Email analysis failed for {referee.name}: {e}")
                
            except ImportError:
                logger.warning("📧 Gmail integration not available - using scraped data only")
                
        except Exception as e:
            logger.error(f"Email crosschecking failed: {e}")
    
    async def _build_communication_story(self, referee, manuscript_id, gmail_tracker, email_tracker):
        """Build comprehensive communication story for a referee"""
        story = {
            # Basic timeline
            'invitation_date': None,
            'first_response_date': None,
            'acceptance_date': None,
            'report_submission_date': None,
            'decline_date': None,
            
            # Communication metrics
            'invitation_emails_sent': 0,
            'reminder_emails_sent': 0,
            'response_emails_received': 0,
            'total_emails_exchanged': 0,
            
            # Timeline analysis
            'days_to_first_response': None,
            'days_to_acceptance': None,
            'days_to_decline': None,
            'days_from_acceptance_to_report': None,
            'reminders_needed_for_response': 0,
            'reminders_needed_for_report': 0,
            
            # Communication behavior
            'responded_to_first_invitation': False,
            'needed_follow_up_for_response': False,
            'accepted_immediately': False,
            'needed_reminders_for_report': False,
            'communication_quality': 'unknown',
            
            # Email thread details
            'email_threads': [],
            'last_email_date': None,
            'communication_gaps': []
        }
        
        try:
            # Search for all emails related to this referee and manuscript
            email_query = f"(from:{referee.email} OR to:{referee.email}) AND {manuscript_id}"
            emails = await gmail_tracker.search_emails(email_query, max_results=50)
            
            if not emails:
                logger.info(f"       📭 No emails found for {referee.name}")
                return story
            
            # Sort emails by date
            emails.sort(key=lambda x: x.get('date', ''))
            story['total_emails_exchanged'] = len(emails)
            
            # Analyze each email to build timeline
            invitation_count = 0
            reminder_count = 0
            response_count = 0
            
            for email in emails:
                subject = email.get('subject', '').lower()
                date = email.get('date')
                sender = email.get('sender', '').lower()
                body_snippet = email.get('body_snippet', '').lower()
                
                # Determine email type and direction
                email_type = self._classify_email_type(subject, body_snippet)
                is_from_referee = referee.email.lower() in sender
                
                # Track different types of emails
                if email_type == 'invitation' and not is_from_referee:
                    invitation_count += 1
                    if not story['invitation_date']:
                        story['invitation_date'] = date
                        
                elif email_type == 'reminder' and not is_from_referee:
                    reminder_count += 1
                    
                elif is_from_referee:
                    response_count += 1
                    if not story['first_response_date']:
                        story['first_response_date'] = date
                    
                    # Check if this is acceptance/decline
                    if email_type == 'acceptance':
                        story['acceptance_date'] = date
                        story['accepted_immediately'] = (invitation_count == 1)
                    elif email_type == 'decline':
                        story['decline_date'] = date
                    elif email_type == 'report_submission':
                        story['report_submission_date'] = date
                
                story['last_email_date'] = date
            
            # Calculate metrics
            story['invitation_emails_sent'] = invitation_count
            story['reminder_emails_sent'] = reminder_count
            story['response_emails_received'] = response_count
            
            # Calculate timeline metrics
            if story['invitation_date'] and story['first_response_date']:
                story['days_to_first_response'] = self._calculate_days_between(
                    story['invitation_date'], story['first_response_date']
                )
                story['responded_to_first_invitation'] = story['days_to_first_response'] <= 7
                
            if story['invitation_date'] and story['acceptance_date']:
                story['days_to_acceptance'] = self._calculate_days_between(
                    story['invitation_date'], story['acceptance_date']
                )
                
            if story['invitation_date'] and story['decline_date']:
                story['days_to_decline'] = self._calculate_days_between(
                    story['invitation_date'], story['decline_date']
                )
                
            if story['acceptance_date'] and story['report_submission_date']:
                story['days_from_acceptance_to_report'] = self._calculate_days_between(
                    story['acceptance_date'], story['report_submission_date']
                )
            
            # Analyze communication patterns
            story['needed_follow_up_for_response'] = invitation_count > 1 and not story['first_response_date']
            story['reminders_needed_for_response'] = max(0, invitation_count - 1)
            story['needed_reminders_for_report'] = reminder_count > 0 and story['acceptance_date']
            story['reminders_needed_for_report'] = reminder_count if story['acceptance_date'] else 0
            
            # Assess communication quality
            story['communication_quality'] = self._assess_communication_quality(story)
            
        except Exception as e:
            logger.error(f"Failed to build communication story: {e}")
            
        return story
    
    def _classify_email_type(self, subject, body_snippet):
        """Classify email type based on subject and content"""
        subject_body = f"{subject} {body_snippet}".lower()
        
        # Invitation patterns
        if any(word in subject_body for word in ['invitation', 'invited to review', 'review invitation', 'referee invitation']):
            return 'invitation'
        
        # Reminder patterns  
        if any(word in subject_body for word in ['reminder', 'follow up', 'overdue', 'pending review']):
            return 'reminder'
            
        # Acceptance patterns
        if any(word in subject_body for word in ['accept', 'agreed to review', 'will review', 'happy to review']):
            return 'acceptance'
            
        # Decline patterns
        if any(word in subject_body for word in ['decline', 'unable to review', 'cannot review', 'regret']):
            return 'decline'
            
        # Report submission patterns
        if any(word in subject_body for word in ['review completed', 'report attached', 'my review', 'review of']):
            return 'report_submission'
            
        return 'other'
    
    def _calculate_days_between(self, date1, date2):
        """Calculate days between two date strings"""
        try:
            from datetime import datetime
            d1 = datetime.fromisoformat(date1.replace('Z', '+00:00'))
            d2 = datetime.fromisoformat(date2.replace('Z', '+00:00'))
            return abs((d2 - d1).days)
        except:
            return None
    
    def _assess_communication_quality(self, story):
        """Assess overall communication quality based on timeline metrics"""
        score = 0
        
        # Positive factors
        if story['responded_to_first_invitation']:
            score += 2
        if story['days_to_first_response'] and story['days_to_first_response'] <= 3:
            score += 2
        if story['response_emails_received'] > 0:
            score += 1
        if story['reminders_needed_for_response'] == 0:
            score += 1
        if story['days_from_acceptance_to_report'] and story['days_from_acceptance_to_report'] <= 30:
            score += 1
            
        # Negative factors
        if story['reminders_needed_for_response'] > 2:
            score -= 2
        if story['days_to_first_response'] and story['days_to_first_response'] > 14:
            score -= 1
        if story['reminders_needed_for_report'] > 3:
            score -= 2
            
        if score >= 4:
            return 'excellent'
        elif score >= 2:
            return 'good'
        elif score >= 0:
            return 'average'
        else:
            return 'poor'
    
    def _update_referee_timeline(self, referee, story):
        """Update referee object with comprehensive timeline data"""
        # Basic timeline
        referee.contact_date = story.get('invitation_date')
        referee.first_response_date = story.get('first_response_date')
        referee.acceptance_date = story.get('acceptance_date')
        referee.decline_date = story.get('decline_date')
        referee.report_date = story.get('report_submission_date')
        referee.last_email_date = story.get('last_email_date')
        
        # Communication metrics
        referee.invitation_emails_sent = story.get('invitation_emails_sent', 0)
        referee.reminder_count = story.get('reminder_emails_sent', 0)
        referee.response_emails_received = story.get('response_emails_received', 0)
        referee.total_emails_exchanged = story.get('total_emails_exchanged', 0)
        
        # Timeline analysis
        referee.days_to_first_response = story.get('days_to_first_response')
        referee.days_to_acceptance = story.get('days_to_acceptance')
        referee.days_to_decline = story.get('days_to_decline')
        referee.days_from_acceptance_to_report = story.get('days_from_acceptance_to_report')
        referee.reminders_needed_for_response = story.get('reminders_needed_for_response', 0)
        referee.reminders_needed_for_report = story.get('reminders_needed_for_report', 0)
        
        # Communication behavior
        referee.responded_to_first_invitation = story.get('responded_to_first_invitation', False)
        referee.needed_follow_up_for_response = story.get('needed_follow_up_for_response', False)
        referee.accepted_immediately = story.get('accepted_immediately', False)
        referee.needed_reminders_for_report = story.get('needed_reminders_for_report', False)
        referee.communication_quality = story.get('communication_quality', 'unknown')
        
        # Update status based on comprehensive analysis
        if story.get('decline_date'):
            referee.status = "Declined"
            referee.declined = True
        elif story.get('report_submission_date'):
            referee.status = "Report submitted"
            referee.report_submitted = True
        elif story.get('acceptance_date'):
            referee.status = "Accepted, awaiting report"
            
        # Calculate days since invited for current context
        if referee.contact_date:
            from datetime import datetime
            try:
                contact_dt = datetime.fromisoformat(referee.contact_date.replace('Z', '+00:00'))
                referee.days_since_invited = (datetime.now() - contact_dt).days
            except:
                pass
    
    def _log_communication_summary(self, referee, story):
        """Log detailed communication summary"""
        logger.info(f"       📊 Communication Summary for {referee.name}:")
        logger.info(f"         📧 Total emails: {story.get('total_emails_exchanged', 0)}")
        logger.info(f"         📤 Invitations sent: {story.get('invitation_emails_sent', 0)}")
        logger.info(f"         🔔 Reminders sent: {story.get('reminder_emails_sent', 0)}")
        logger.info(f"         📥 Responses received: {story.get('response_emails_received', 0)}")
        
        if story.get('days_to_first_response'):
            logger.info(f"         ⏱️ Days to first response: {story['days_to_first_response']}")
        if story.get('days_to_acceptance'):
            logger.info(f"         ✅ Days to acceptance: {story['days_to_acceptance']}")
        if story.get('days_to_decline'):
            logger.info(f"         ❌ Days to decline: {story['days_to_decline']}")
        if story.get('days_from_acceptance_to_report'):
            logger.info(f"         📝 Days from acceptance to report: {story['days_from_acceptance_to_report']}")
            
        logger.info(f"         🏆 Communication quality: {story.get('communication_quality', 'unknown')}")
        
        # Behavioral insights
        behavior = []
        if story.get('responded_to_first_invitation'):
            behavior.append("responded to first invitation")
        if story.get('accepted_immediately'):
            behavior.append("accepted immediately")
        if story.get('needed_follow_up_for_response'):
            behavior.append("needed follow-up for response")
        if story.get('needed_reminders_for_report'):
            behavior.append("needed reminders for report")
            
        if behavior:
            logger.info(f"         🔍 Behavior: {', '.join(behavior)}")
    
    async def _navigate_to_manuscripts(self) -> bool:
        """Navigate to manuscripts - REAL implementation"""
        try:
            logger.info("🔍 Navigating to manuscripts...")
            
            # After login, we should be on main.plex
            # Look for the AE task links
            await asyncio.sleep(3)
            
            # Find all AE task links
            content = await self.page.content()
            
            # Look for any links with "AE" that have counts > 0
            # Pattern: any text followed by a number > 0 and "AE"
            ae_links = re.findall(r'<a[^>]*>([^<]*?(\d+)\s+AE[^<]*)</a>', content)
            
            found_any = False
            for link_text, count in ae_links:
                if int(count) > 0:
                    logger.info(f"Found AE link with {count} manuscripts: {link_text.strip()}")
                    found_any = True
            
            return found_any
            
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    async def _extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts - REAL implementation"""
        manuscripts = []
        
        try:
            # Find and click on all AE links with count > 0
            content = await self.page.content()
            ae_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*?(\d+)\s+AE[^<]*)</a>', content)
            
            manuscript_urls = {}  # {ms_id: url}
            
            for href, link_text, count in ae_links:
                try:
                    if int(count) > 0:
                        logger.info(f"📂 Clicking '{link_text.strip()}' ({count} manuscripts)...")
                        
                        # Click the link
                        full_url = href if href.startswith('http') else f"{self.base_url}/{href}"
                        await self.page.goto(full_url, wait_until="networkidle")
                        await asyncio.sleep(2)
                        
                        # Extract manuscript IDs and their URLs from this page
                        category_content = await self.page.content()
                        
                        # Find all manuscript links
                        ms_links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>[^<]*(M\d{6})[^<]*</a>', category_content)
                        
                        for ms_href, ms_id in ms_links:
                            clean_href = ms_href.replace('&amp;', '&')
                            full_ms_url = f"{self.base_url}/{clean_href}" if not clean_href.startswith('http') else clean_href
                            manuscript_urls[ms_id] = full_ms_url
                        
                        logger.info(f"   Found {len(ms_links)} manuscript URLs")
                        
                        # Go back to main page
                        await self.page.go_back()
                        await asyncio.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error processing link '{link_text}': {e}")
            
            # Now process each manuscript
            for ms_id, url in manuscript_urls.items():
                try:
                    logger.info(f"📄 Processing manuscript {ms_id}...")
                    await self.page.goto(url, wait_until="networkidle")
                    await asyncio.sleep(2)
                    
                    content = await self.page.content()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Parse manuscript
                    manuscript = await self._parse_manuscript_page(ms_id, soup, content)
                    if manuscript:
                        manuscripts.append(manuscript)
                        
                except Exception as e:
                    logger.error(f"Error processing {ms_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Manuscript extraction failed: {e}")
            
        return manuscripts
    
    async def _parse_manuscript_page(self, ms_id: str, soup: BeautifulSoup, content: str) -> Optional[Manuscript]:
        """Parse a manuscript detail page - REAL implementation with smart caching"""
        try:
            # Check cache first
            content_hash = self._get_content_hash(content)
            cached_manuscript = self._load_cached_manuscript(ms_id, content_hash)
            if cached_manuscript:
                return cached_manuscript
            manuscript = Manuscript(
                id=ms_id,
                title="",
                authors=[],
                status="Under Review",
                journal="SICON"
            )
            
            # Extract fields from table rows
            for row in soup.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    
                    if 'Title' in label:
                        manuscript.title = value
                    elif 'Submission Date' in label:
                        manuscript.submission_date = value
                    elif 'Associate Editor' in label:
                        manuscript.associate_editor = value
                    elif 'Corresponding Editor' in label:
                        manuscript.corresponding_editor = value
                    elif 'Corresponding Author' in label:
                        # Extract author name without affiliation
                        author_name = re.sub(r'\([^)]*\)', '', value).strip()
                        if author_name:
                            manuscript.authors.append(author_name)
            
            # CRITICAL: Parse referees correctly
            referees = []
            
            # 1. Parse Potential Referees section
            potential_referees = await self._parse_potential_referees(soup, content)
            referees.extend(potential_referees)
            
            # 2. Parse Referees section (accepted only)
            active_referees = await self._parse_referees_section(soup, content)
            referees.extend(active_referees)
            
            # Remove duplicates
            unique_referees = {}
            for ref in referees:
                key = ref.email if ref.email else ref.name
                if key not in unique_referees:
                    unique_referees[key] = ref
            
            manuscript.referees = list(unique_referees.values())
            
            # Extract PDF URLs
            manuscript.pdf_urls = self._extract_pdf_urls(soup)
            
            # Extract referee comments from AE recommendation page
            await self._extract_referee_comments(manuscript)
            
            logger.info(f"✅ Parsed {ms_id}: {len(manuscript.referees)} referees")
            
            # Save to cache
            self._save_manuscript_to_cache(manuscript, content_hash)
            
            return manuscript
            
        except Exception as e:
            logger.error(f"Failed to parse manuscript {ms_id}: {e}")
            return None
    
    async def _parse_potential_referees(self, soup: BeautifulSoup, content: str) -> List[Referee]:
        """Parse Potential Referees section - these can have various statuses"""
        referees = []
        
        try:
            # Find the Potential Referees row
            for row in soup.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td and 'Potential Referees' in th.get_text():
                    # Parse the content cell - it contains <a> links and text
                    # Get all referee links
                    referee_links = td.find_all('a', href=re.compile(r'biblio_dump'))
                    
                    # Also need the full HTML to extract dates/status
                    td_html = str(td)
                    
                    for link in referee_links:
                        name = link.get_text(strip=True)
                        href = link.get('href', '')
                        
                        # Extract referee number from name
                        name_match = re.match(r'(.+?)\s*#(\d+)', name)
                        if name_match:
                            clean_name = name_match.group(1).strip()
                            ref_num = name_match.group(2)
                        else:
                            clean_name = name
                            ref_num = ""
                        
                        # Look for pattern after this referee's link
                        # Pattern: (Last Contact Date: YYYY-MM-DD) (Status: XXX)
                        escaped_name = re.escape(name)
                        pattern = escaped_name + r'</a>\s*\(Last Contact Date:\s*(\d{4}-\d{2}-\d{2})\)\s*(?:\(Status:\s*([^)]+)\))?'
                        match = re.search(pattern, td_html)
                        
                        if match:
                            contact_date = match.group(1)
                            status_text = match.group(2) if match.group(2) else "Contacted, awaiting response"
                            
                            # Determine status
                            if "Declined" in status_text:
                                status = "Declined"
                                is_declined = True
                            elif "No Response" in status_text:
                                status = "No Response"
                                is_declined = False
                            else:
                                status = status_text
                                is_declined = False
                            
                            referee = Referee(
                                name=clean_name,
                                email="",  # Will be filled by clicking link
                                status=status
                            )
                            
                            # Set dates
                            referee.contact_date = contact_date
                            if is_declined:
                                referee.declined = True
                                referee.declined_date = contact_date
                            
                            # Store the biblio URL for later fetching
                            referee.biblio_url = f"{self.base_url}/{href}" if not href.startswith('http') else href
                            
                            referees.append(referee)
                            logger.info(f"   Potential: {clean_name} - {status} (contacted {contact_date})")
                    
                    break
                    
        except Exception as e:
            logger.error(f"Failed to parse potential referees: {e}")
            
        return referees
    
    async def _parse_referees_section(self, soup: BeautifulSoup, content: str) -> List[Referee]:
        """Parse Referees section - these are all ACCEPTED"""
        referees = []
        
        try:
            # Find the Referees row (not Potential Referees)
            for row in soup.find_all('tr'):
                th = row.find('th')
                td = row.find('td')
                if th and td:
                    th_text = th.get_text(strip=True)
                    # Make sure it's "Referees" not "Potential Referees"
                    if th_text == 'Referees' or (th_text.startswith('Referees') and 'Potential' not in th_text):
                        # Parse the TD content which has links and font tags
                        # Get all referee links
                        referee_links = td.find_all('a', href=re.compile(r'biblio_dump'))
                        
                        # Get the full HTML to parse dates
                        td_html = str(td)
                        
                        for link in referee_links:
                            name = link.get_text(strip=True)
                            href = link.get('href', '')
                            
                            # Extract referee number from name
                            name_match = re.match(r'(.+?)\s*#(\d+)', name)
                            if name_match:
                                clean_name = name_match.group(1).strip()
                                ref_num = name_match.group(2)
                            else:
                                clean_name = name
                                ref_num = ""
                            
                            # Look for dates after this referee
                            # Pattern 1: <font size="-1">(Rcvd: YYYY-MM-DD)</font>
                            # Pattern 2: <font size="-1">(Due: YYYY-MM-DD)</font>
                            escaped_name = re.escape(name)
                            
                            # Check for received date
                            rcvd_pattern = escaped_name + r'</a>\s*<font[^>]*>\(Rcvd:\s*(\d{4}-\d{2}-\d{2})\)</font>'
                            rcvd_match = re.search(rcvd_pattern, td_html)
                            
                            if rcvd_match:
                                report_date = rcvd_match.group(1)
                                referee = Referee(
                                    name=clean_name,
                                    email="",  # Will be filled by clicking link
                                    status="Report submitted",
                                    report_submitted=True,
                                    report_date=report_date
                                )
                                # Store the biblio URL
                                referee.biblio_url = f"{self.base_url}/{href}" if not href.startswith('http') else href
                                referees.append(referee)
                                logger.info(f"   Active: {clean_name} - Report submitted {report_date}")
                            else:
                                # Check for due date
                                due_pattern = escaped_name + r'</a>\s*<font[^>]*>\(Due:\s*(\d{4}-\d{2}-\d{2})\)</font>'
                                due_match = re.search(due_pattern, td_html)
                                
                                if due_match:
                                    due_date = due_match.group(1)
                                    referee = Referee(
                                        name=clean_name,
                                        email="",  # Will be filled by clicking link
                                        status="Accepted, awaiting report",
                                        report_submitted=False
                                    )
                                    referee.due_date = due_date
                                    # Store the biblio URL
                                    referee.biblio_url = f"{self.base_url}/{href}" if not href.startswith('http') else href
                                    referees.append(referee)
                                    logger.info(f"   Active: {clean_name} - Due {due_date}")
                        
                        break
                        
        except Exception as e:
            logger.error(f"Failed to parse referees section: {e}")
            
        return referees
    
    def _extract_pdf_urls(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract PDF URLs from manuscript page - COMPREHENSIVE"""
        pdf_urls = {}
        
        try:
            # Look for all PDF links in the page
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                text = link.get_text().strip()
                
                # Skip empty links
                if not href or not text:
                    continue
                
                # Build full URL
                full_url = href if href.startswith('http') else f"{self.base_url}/{href}"
                
                # Categorize different types of PDFs
                if 'PDF' in text.upper() or '/GetDoc/' in href or '.pdf' in href.lower():
                    
                    # Manuscript PDF
                    if any(word in text.upper() for word in ['ARTICLE', 'MANUSCRIPT', 'PAPER', 'SUBMISSION']):
                        pdf_urls['manuscript'] = full_url
                        logger.info(f"     📄 Found manuscript PDF: {text}")
                    
                    # Cover letter
                    elif any(word in text.upper() for word in ['COVER', 'LETTER']):
                        pdf_urls['cover_letter'] = full_url
                        logger.info(f"     📄 Found cover letter: {text}")
                    
                    # Supplementary materials
                    elif any(word in text.upper() for word in ['SUPPLEMENT', 'APPENDIX', 'ADDITIONAL']):
                        pdf_urls['supplement'] = full_url
                        logger.info(f"     📄 Found supplement: {text}")
                    
                    # Referee reports
                    elif any(word in text.upper() for word in ['REFEREE', 'REVIEW', 'REPORT']):
                        # Try to extract referee number
                        num_match = re.search(r'#?(\d+)', text)
                        if num_match:
                            num = num_match.group(1)
                            pdf_urls[f'referee_report_{num}'] = full_url
                            logger.info(f"     📄 Found referee report #{num}: {text}")
                        else:
                            # Generic referee report
                            report_count = len([k for k in pdf_urls.keys() if k.startswith('referee_report')])
                            pdf_urls[f'referee_report_{report_count + 1}'] = full_url
                            logger.info(f"     📄 Found referee report: {text}")
                    
                    # Any other PDF
                    elif 'PDF' in text.upper():
                        # Generic PDF document
                        pdf_key = re.sub(r'[^a-zA-Z0-9_]', '_', text.lower())[:20]
                        pdf_urls[pdf_key] = full_url
                        logger.info(f"     📄 Found PDF: {text}")
                        
            # SPECIAL: Look for Associate Editor Recommendation links (Daudin's comments)
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                text = link.get_text().strip()
                if 'display_me_review' in href or 'Associate Editor Recommendation' in text:
                    full_url = href if href.startswith('http') else f"{self.base_url}/{href}"
                    pdf_urls['ae_recommendation'] = full_url
                    logger.info(f"     📝 Found AE Recommendation (comments): {text}")
                    break
            
            logger.info(f"   📁 Total documents found: {len(pdf_urls)}")
                            
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            
        return pdf_urls
    
    async def _extract_referee_comments(self, manuscript: Manuscript):
        """Extract referee comments from AE recommendation page"""
        try:
            # Look for AE recommendation URL
            ae_url = manuscript.pdf_urls.get('ae_recommendation')
            if not ae_url:
                return
            
            logger.info(f"   📝 Extracting referee comments from AE recommendation...")
            
            # Navigate to the AE recommendation page
            await self.page.goto(ae_url, wait_until="networkidle")
            await asyncio.sleep(2)
            
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for referee comments table
            for table in soup.find_all('table', border="1"):
                # Check if this is the referee comments table
                headers = table.find_all('th')
                if len(headers) >= 3:
                    header_texts = [th.get_text().strip() for th in headers]
                    if 'Referee' in header_texts and 'Comment' in header_texts:
                        logger.info(f"     📋 Found referee comments table")
                        
                        # Extract comments from table rows
                        rows = table.find_all('tr')[1:]  # Skip header row
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 3:
                                referee_cell = cells[0].get_text().strip()
                                note_type = cells[1].get_text().strip()
                                comment = cells[2].get_text().strip()
                                
                                # Extract referee name
                                referee_name_match = re.search(r'([^\n]+)', referee_cell)
                                if referee_name_match:
                                    referee_name = referee_name_match.group(1).strip()
                                    
                                    # Find the corresponding referee object
                                    for referee in manuscript.referees:
                                        if referee.name.lower() in referee_name.lower():
                                            # Store the comment
                                            if not hasattr(referee, 'comments'):
                                                referee.comments = {}
                                            referee.comments[note_type] = comment
                                            
                                            logger.info(f"     💬 Added comment for {referee.name}: {note_type}")
                                            
                                            # Update report status if this is a review
                                            if 'Author' in note_type:
                                                referee.report_submitted = True
                                                referee.status = "Report submitted"
                                            break
                        
                        break
            
        except Exception as e:
            logger.error(f"Failed to extract referee comments: {e}")
    
    async def _extract_referee_details(self, manuscript: Manuscript):
        """Click on referee names to get emails, full names, and affiliations"""
        try:
            for referee in manuscript.referees:
                if hasattr(referee, 'biblio_url') and referee.biblio_url:
                    try:
                        logger.info(f"   🔍 Fetching details for {referee.name}...")
                        
                        # Navigate to biblio_dump URL in current page
                        await self.page.goto(referee.biblio_url, wait_until="networkidle")
                        await asyncio.sleep(2)
                        
                        content = await self.page.content()
                        
                        # Extract full name from table structure
                        # Pattern: FIRSTNAME followed by "First Name", LASTNAME followed by "Last Name"
                        table_cells = re.findall(r'<td[^>]*>([^<]+)</td>', content)
                        
                        first_name = None
                        last_name = None
                        
                        # Look for the pattern: FIRSTNAME, "First Name", LASTNAME, "Last Name"
                        for i, cell in enumerate(table_cells):
                            if cell == "First Name" and i > 0:
                                first_name = table_cells[i-1].strip()
                            elif cell == "Last Name" and i > 0:
                                last_name = table_cells[i-1].strip()
                        
                        full_name = None
                        if first_name and last_name:
                            full_name = f"{first_name} {last_name}"
                        
                        if full_name:
                            # Format name properly: "First Last" with proper capitalization
                            if ',' in full_name:
                                # Handle "Last, First" format
                                last, first = [n.strip() for n in full_name.split(',', 1)]
                                formatted_name = f"{first.title()} {last.title()}"
                            else:
                                # Handle "First Last" format
                                formatted_name = ' '.join(word.title() for word in full_name.split())
                            
                            referee.name = formatted_name
                            logger.info(f"     ✓ Updated name: {formatted_name}")
                        
                        # Extract email
                        email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
                        if email_match:
                            referee.email = email_match.group(1).lower()
                            logger.info(f"     ✓ Found email: {referee.email}")
                        
                        # Extract institution/affiliation
                        inst_patterns = [
                            r'<b>Institution:</b>\s*([^<]+)',
                            r'<b>Affiliation:</b>\s*([^<]+)',
                            r'<b>Department:</b>\s*([^<]+)',
                            r'Department[^<]*<[^>]*>([^<]+)',
                            r'University[^<]*<[^>]*>([^<]+)',
                            r'<td[^>]*>\s*([^<]*(?:University|Institute|College|Department)[^<]*)\s*</td>'
                        ]
                        
                        for pattern in inst_patterns:
                            inst_match = re.search(pattern, content, re.IGNORECASE)
                            if inst_match:
                                institution = inst_match.group(1).strip()
                                if institution and len(institution) > 3:  # Avoid empty or very short matches
                                    referee.institution = institution
                                    logger.info(f"     ✓ Found institution: {institution}")
                                    break
                        
                        # If no specific institution found, look for any text that might be affiliation
                        if not referee.institution:
                            # Look for lines with organization-like words
                            org_match = re.search(r'<td[^>]*>\s*([^<]*(?:Univ|Tech|Inst|Corp|Lab|Center)[^<]*)\s*</td>', content, re.IGNORECASE)
                            if org_match:
                                referee.institution = org_match.group(1).strip()
                                logger.info(f"     ✓ Found affiliation: {referee.institution}")
                        
                    except Exception as e:
                        logger.error(f"Failed to get details for {referee.name}: {e}")
                        
        except Exception as e:
            logger.error(f"Referee detail extraction failed: {e}")
        
        # After getting basic details, crosscheck with emails
        await self._crosscheck_emails(manuscript)
    
    async def _extract_pdfs(self, manuscript: Manuscript):
        """Download all PDFs using enhanced PDF manager"""
        try:
            logger.info(f"   📥 Downloading documents for {manuscript.id}...")
            
            for pdf_type, url in manuscript.pdf_urls.items():
                try:
                    filename = f"{manuscript.id}_{pdf_type}.pdf"
                    
                    # Use existing enhanced PDF manager
                    pdf_path = await self.pdf_manager.download_pdf(
                        url=url,
                        filename=filename,
                        journal="SICON",
                        manuscript_id=manuscript.id
                    )
                    
                    if pdf_path:
                        manuscript.pdf_paths[pdf_type] = str(pdf_path)
                        logger.info(f"     ✅ Downloaded {pdf_type}: {filename}")
                        
                        # Extract text content for reports
                        if 'report' in pdf_type or 'recommendation' in pdf_type:
                            text_content = await self.pdf_manager.extract_text(pdf_path)
                            if text_content:
                                if not manuscript.referee_reports:
                                    manuscript.referee_reports = {}
                                manuscript.referee_reports[pdf_type] = text_content
                                logger.info(f"     📄 Extracted text from {pdf_type}")
                    else:
                        logger.warning(f"     ❌ Failed to download {pdf_type}")
                        
                except Exception as e:
                    logger.error(f"Failed to download {pdf_type}: {e}")
                    
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
    
    async def _extract_referee_reports(self, manuscript: Manuscript):
        """Reports are in PDFs"""
        pass