"""
Fixed SICON Extractor - Addresses all data parsing issues
Implements comprehensive requirements from COMPREHENSIVE_DATA_EXTRACTION_REQUIREMENTS.md
"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup, Tag
from dataclasses import dataclass

from .base import SIAMBaseExtractor
from ...core.base_extractor import Manuscript, Referee

logger = logging.getLogger(__name__)


@dataclass
class ParsedManuscriptData:
    """Structured container for parsed manuscript data with validation"""
    title: Optional[str] = None
    authors: List[str] = None
    submission_date: Optional[str] = None
    corresponding_editor: Optional[str] = None
    associate_editor: Optional[str] = None
    status: Optional[str] = None
    abstract: Optional[str] = None
    keywords: List[str] = None
    validation_errors: List[str] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []
        if self.validation_errors is None:
            self.validation_errors = []


class SICONExtractorFixed(SIAMBaseExtractor):
    """Fixed SICON extractor with accurate data parsing"""
    
    journal_name = "SICON"
    base_url = "https://sicon.siam.org"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_validator = DataValidator()
    
    async def _extract_complete_manuscript_metadata(self, manuscript: Manuscript):
        """
        FIXED: Complete manuscript metadata extraction with proper table parsing
        Implements requirements from COMPREHENSIVE_DATA_EXTRACTION_REQUIREMENTS.md
        """
        try:
            logger.info(f"🔍 Extracting FIXED metadata for manuscript {manuscript.id}")
            
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Save debug content
            debug_file = f"debug_manuscript_{manuscript.id}_FIXED.html"
            with open(debug_file, 'w') as f:
                f.write(content)
            logger.info(f"💾 Debug content saved to {debug_file}")
            
            # Parse manuscript data using enhanced methods
            parsed_data = await self._parse_manuscript_data_comprehensive(soup, content)
            
            # Apply parsed data to manuscript object
            await self._apply_parsed_data_to_manuscript(manuscript, parsed_data)
            
            # Extract referee information with enhanced accuracy
            await self._extract_referee_information_enhanced(manuscript, soup, content)
            
            # Validate extracted data
            validation_result = self.data_validator.validate_manuscript_data(manuscript)
            if not validation_result.is_valid:
                logger.warning(f"⚠️ Validation issues for {manuscript.id}: {validation_result.warnings}")
            
            logger.info(f"✅ FIXED extraction complete for {manuscript.id}")
            
        except Exception as e:
            logger.error(f"❌ FIXED extraction failed for {manuscript.id}: {e}")
            raise
    
    async def _parse_manuscript_data_comprehensive(self, soup: BeautifulSoup, content: str) -> ParsedManuscriptData:
        """
        FIXED: Comprehensive manuscript data parsing with multiple extraction methods
        """
        parsed = ParsedManuscriptData()
        
        # Method 1: Extract from structured table (most reliable)
        parsed = await self._extract_from_table_structure(soup, parsed)
        
        # Method 2: Extract using regex patterns (fallback)
        parsed = await self._extract_using_regex_patterns(content, parsed)
        
        # Method 3: Extract from meta tags and headers (backup)
        parsed = await self._extract_from_meta_data(soup, parsed)
        
        # Method 4: Extract from form fields (additional sources)
        parsed = await self._extract_from_form_fields(soup, parsed)
        
        return parsed
    
    async def _extract_from_table_structure(self, soup: BeautifulSoup, parsed: ParsedManuscriptData) -> ParsedManuscriptData:
        """
        FIXED: Extract manuscript data from HTML table structure
        This method addresses the primary parsing issues
        """
        try:
            # Find the main manuscript details table
            # SIAM journals typically use tables with <th> and <td> structure
            
            # Extract Title
            title_patterns = [
                {'tag': 'th', 'text': re.compile(r'^Title$', re.IGNORECASE)},
                {'tag': 'td', 'text': re.compile(r'Title:', re.IGNORECASE)},
                {'tag': 'b', 'text': re.compile(r'Title:', re.IGNORECASE)}
            ]
            
            for pattern in title_patterns:
                title_element = soup.find(pattern['tag'], text=pattern['text'])
                if title_element:
                    # Get the next sibling or parent's next sibling
                    title_value = self._get_associated_value(title_element)
                    if title_value and len(title_value) > 10:
                        parsed.title = title_value.strip()
                        logger.info(f"📝 FIXED: Found title: {parsed.title[:60]}...")
                        break
            
            # Extract Authors
            author_patterns = [
                {'tag': 'th', 'text': re.compile(r'Author.*', re.IGNORECASE)},
                {'tag': 'td', 'text': re.compile(r'Author.*:', re.IGNORECASE)},
                {'tag': 'b', 'text': re.compile(r'Author.*:', re.IGNORECASE)}
            ]
            
            for pattern in author_patterns:
                author_element = soup.find(pattern['tag'], text=pattern['text'])
                if author_element:
                    authors_value = self._get_associated_value(author_element)
                    if authors_value:
                        # Parse multiple authors
                        authors = self._parse_author_list(authors_value, author_element.parent if author_element.parent else None)
                        if authors:
                            parsed.authors = authors
                            logger.info(f"👥 FIXED: Found authors: {authors}")
                            break
            
            # Extract Submission Date - FIXED LOGIC
            date_patterns = [
                {'tag': 'th', 'text': re.compile(r'Date.*Submitted', re.IGNORECASE)},
                {'tag': 'th', 'text': re.compile(r'Submission.*Date', re.IGNORECASE)},
                {'tag': 'th', 'text': re.compile(r'Submitted', re.IGNORECASE)},
                {'tag': 'td', 'text': re.compile(r'Submitted.*:', re.IGNORECASE)},
                {'tag': 'b', 'text': re.compile(r'Date.*Submitted:', re.IGNORECASE)}
            ]
            
            for pattern in date_patterns:
                date_element = soup.find(pattern['tag'], text=pattern['text'])
                if date_element:
                    date_value = self._get_associated_value(date_element)
                    if date_value:
                        # Clean and validate the date
                        cleaned_date = self._clean_submission_date(date_value)
                        if cleaned_date:
                            parsed.submission_date = cleaned_date
                            logger.info(f"📅 FIXED: Found submission date: {parsed.submission_date}")
                            break
            
            # Extract Corresponding Editor - FIXED LOGIC
            editor_patterns = [
                {'tag': 'th', 'text': re.compile(r'Corresponding.*Editor', re.IGNORECASE)},
                {'tag': 'th', 'text': re.compile(r'Editor.*in.*Chief', re.IGNORECASE)},
                {'tag': 'th', 'text': re.compile(r'Handling.*Editor', re.IGNORECASE)},
                {'tag': 'td', 'text': re.compile(r'Corresponding.*Editor.*:', re.IGNORECASE)},
                {'tag': 'b', 'text': re.compile(r'Editor.*:', re.IGNORECASE)}
            ]
            
            for pattern in editor_patterns:
                editor_element = soup.find(pattern['tag'], text=pattern['text'])
                if editor_element:
                    editor_value = self._get_associated_value(editor_element)
                    if editor_value and len(editor_value) > 2:
                        # Clean editor name
                        cleaned_editor = self._clean_editor_name(editor_value)
                        if cleaned_editor:
                            parsed.corresponding_editor = cleaned_editor
                            logger.info(f"📧 FIXED: Found corresponding editor: {parsed.corresponding_editor}")
                            break
            
            # Extract Associate Editor
            ae_patterns = [
                {'tag': 'th', 'text': re.compile(r'Associate.*Editor', re.IGNORECASE)},
                {'tag': 'th', 'text': re.compile(r'AE', re.IGNORECASE)},
                {'tag': 'td', 'text': re.compile(r'Associate.*Editor.*:', re.IGNORECASE)}
            ]
            
            for pattern in ae_patterns:
                ae_element = soup.find(pattern['tag'], text=pattern['text'])
                if ae_element:
                    ae_value = self._get_associated_value(ae_element)
                    if ae_value and len(ae_value) > 2:
                        cleaned_ae = self._clean_editor_name(ae_value)
                        if cleaned_ae:
                            parsed.associate_editor = cleaned_ae
                            logger.info(f"👤 FIXED: Found associate editor: {parsed.associate_editor}")
                            break
            
            return parsed
            
        except Exception as e:
            logger.error(f"❌ Table structure extraction failed: {e}")
            return parsed
    
    def _get_associated_value(self, element: Tag) -> Optional[str]:
        """
        Get the associated value for a table header or label element
        Handles multiple HTML structures used by SIAM journals
        """
        if not element:
            return None
        
        try:
            # Method 1: Next sibling (for <th><td> structure)
            next_sibling = element.find_next_sibling(['td', 'span', 'div'])
            if next_sibling:
                text = next_sibling.get_text(strip=True)
                if text and len(text) > 1:
                    return text
            
            # Method 2: Parent's next sibling (for nested structures)
            if element.parent:
                parent_next = element.parent.find_next_sibling(['td', 'tr'])
                if parent_next:
                    text = parent_next.get_text(strip=True)
                    if text and len(text) > 1:
                        return text
            
            # Method 3: Look within the same cell after the label
            parent = element.parent
            if parent:
                # Get all text after this element within the same container
                all_text = parent.get_text()
                element_text = element.get_text()
                if element_text in all_text:
                    after_text = all_text.split(element_text, 1)[-1].strip()
                    # Remove common separators
                    after_text = re.sub(r'^[:\-\s]+', '', after_text).strip()
                    if after_text and len(after_text) > 1:
                        return after_text
            
            # Method 4: Look for value in the same row
            row = element.find_parent('tr')
            if row:
                cells = row.find_all(['td', 'th'])
                for i, cell in enumerate(cells):
                    if element in cell.find_all():
                        # Get next cell in row
                        if i + 1 < len(cells):
                            next_cell_text = cells[i + 1].get_text(strip=True)
                            if next_cell_text and len(next_cell_text) > 1:
                                return next_cell_text
            
            return None
            
        except Exception as e:
            logger.debug(f"Error getting associated value: {e}")
            return None
    
    def _parse_author_list(self, authors_text: str, container_element: Optional[Tag] = None) -> List[str]:
        """
        Parse author list from text or HTML links
        Handles various author list formats used by SIAM journals
        """
        authors = []
        
        try:
            # Method 1: Extract from links (most accurate)
            if container_element:
                author_links = container_element.find_all('a')
                if author_links:
                    for link in author_links:
                        author_name = link.get_text(strip=True)
                        if author_name and len(author_name) > 2:
                            # Extract institution from link text or title
                            title = link.get('title', '')
                            if title and '(' in title:
                                author_with_institution = f"{author_name} ({title})"
                                authors.append(author_with_institution)
                            else:
                                authors.append(author_name)
                    
                    if authors:
                        return authors
            
            # Method 2: Parse from text using common delimiters
            if authors_text:
                # Common author separators
                separators = [';', ',', ' and ', ' & ']
                
                author_list = [authors_text]  # Start with full text
                
                # Split by each separator
                for sep in separators:
                    new_list = []
                    for item in author_list:
                        new_list.extend([part.strip() for part in item.split(sep) if part.strip()])
                    author_list = new_list
                
                # Clean and validate author names
                clean_authors = []
                for author in author_list:
                    author = author.strip()
                    # Basic validation: should contain letters and be reasonable length
                    if re.search(r'[a-zA-Z]', author) and 2 <= len(author) <= 200:
                        clean_authors.append(author)
                
                return clean_authors[:10]  # Limit to reasonable number
        
        except Exception as e:
            logger.debug(f"Error parsing author list: {e}")
        
        return []
    
    def _clean_submission_date(self, date_text: str) -> Optional[str]:
        """
        Clean and validate submission date
        Handles various date formats and removes HTML artifacts
        """
        if not date_text:
            return None
        
        try:
            # Remove HTML tags and artifacts
            clean_text = re.sub(r'<[^>]+>', '', date_text)
            clean_text = re.sub(r'&[a-zA-Z]+;', '', clean_text)  # HTML entities
            clean_text = clean_text.strip()
            
            # Skip clearly invalid dates (HTML fragments, etc.)
            invalid_patterns = [
                r'accepted.*published.*elsewhere',
                r'conference.*proceedings',
                r'supporting.*materials',
                r'submission.*guidelines',
                r'manuscript.*central'
            ]
            
            for pattern in invalid_patterns:
                if re.search(pattern, clean_text, re.IGNORECASE):
                    logger.debug(f"Skipping invalid date text: {clean_text[:50]}...")
                    return None
            
            # Extract date patterns
            date_patterns = [
                r'(\d{4}-\d{2}-\d{2})',  # 2024-01-15
                r'(\d{2}/\d{2}/\d{4})',  # 01/15/2024
                r'(\d{2}-\d{2}-\d{4})',  # 01-15-2024
                r'(\w+ \d{1,2}, \d{4})', # January 15, 2024
                r'(\d{1,2} \w+ \d{4})'   # 15 January 2024
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, clean_text)
                if match:
                    date_str = match.group(1)
                    # Validate the date makes sense
                    if self._validate_date_string(date_str):
                        return date_str
            
            # If no pattern matches but text looks like it might contain a date
            if re.search(r'\d{4}', clean_text) and len(clean_text) < 50:
                return clean_text  # Return as-is for manual review
            
            return None
            
        except Exception as e:
            logger.debug(f"Error cleaning submission date: {e}")
            return None
    
    def _validate_date_string(self, date_str: str) -> bool:
        """Validate that a date string represents a reasonable submission date"""
        try:
            # Try to parse with common formats
            date_formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%m-%d-%Y',
                '%B %d, %Y',
                '%d %B %Y'
            ]
            
            parsed_date = None
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if parsed_date:
                # Check if date is reasonable (not in future, not too old)
                now = datetime.now()
                if parsed_date <= now and parsed_date.year >= 2020:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _clean_editor_name(self, editor_text: str) -> Optional[str]:
        """
        Clean and validate editor name
        Removes HTML artifacts and invalid content
        """
        if not editor_text:
            return None
        
        try:
            # Remove HTML tags and entities
            clean_text = re.sub(r'<[^>]+>', '', editor_text)
            clean_text = re.sub(r'&[a-zA-Z]+;', '', clean_text)
            clean_text = clean_text.strip()
            
            # Remove common artifacts
            clean_text = re.sub(r'^[:\-\s;"\']+', '', clean_text)
            clean_text = re.sub(r'[:\-\s;"\']+$', '', clean_text)
            
            # Skip clearly invalid content
            invalid_patterns = [
                r'^["\';]+$',  # Just punctuation
                r'^\s*$',      # Just whitespace
                r'editor.*in.*chief.*not.*assigned',  # Not assigned messages
                r'to.*be.*determined',
                r'tbd',
                r'n/?a'
            ]
            
            for pattern in invalid_patterns:
                if re.match(pattern, clean_text, re.IGNORECASE):
                    return None
            
            # Basic validation: should be reasonable length and contain letters
            if 2 <= len(clean_text) <= 100 and re.search(r'[a-zA-Z]', clean_text):
                return clean_text
            
            return None
            
        except Exception as e:
            logger.debug(f"Error cleaning editor name: {e}")
            return None
    
    async def _extract_using_regex_patterns(self, content: str, parsed: ParsedManuscriptData) -> ParsedManuscriptData:
        """
        Fallback extraction using regex patterns
        Used when table structure extraction fails
        """
        try:
            # Only fill in missing data
            if not parsed.title:
                title_patterns = [
                    r'<title>([^<]+)</title>',
                    r'Title[:\s]*([^\n<]+)',
                    r'<h[12][^>]*>([^<]+)</h[12]>'
                ]
                
                for pattern in title_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        clean_title = match.strip()
                        if len(clean_title) > 20 and 'SIAM' not in clean_title:
                            parsed.title = clean_title
                            logger.info(f"📝 REGEX: Found title: {clean_title[:60]}...")
                            break
                    if parsed.title:
                        break
            
            if not parsed.submission_date:
                date_patterns = [
                    r'Submitted[:\s]*([^\n<]+)',
                    r'Date[:\s]*Submitted[:\s]*([^\n<]+)',
                    r'Submission[:\s]*Date[:\s]*([^\n<]+)'
                ]
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        cleaned_date = self._clean_submission_date(match)
                        if cleaned_date:
                            parsed.submission_date = cleaned_date
                            logger.info(f"📅 REGEX: Found submission date: {cleaned_date}")
                            break
                    if parsed.submission_date:
                        break
            
            if not parsed.corresponding_editor:
                editor_patterns = [
                    r'Corresponding[:\s]*Editor[:\s]*([^\n<]+)',
                    r'Editor[:\s]*in[:\s]*Chief[:\s]*([^\n<]+)',
                    r'Handling[:\s]*Editor[:\s]*([^\n<]+)'
                ]
                
                for pattern in editor_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        cleaned_editor = self._clean_editor_name(match)
                        if cleaned_editor:
                            parsed.corresponding_editor = cleaned_editor
                            logger.info(f"📧 REGEX: Found corresponding editor: {cleaned_editor}")
                            break
                    if parsed.corresponding_editor:
                        break
            
            return parsed
            
        except Exception as e:
            logger.error(f"❌ Regex extraction failed: {e}")
            return parsed
    
    async def _extract_from_meta_data(self, soup: BeautifulSoup, parsed: ParsedManuscriptData) -> ParsedManuscriptData:
        """Extract data from meta tags and structured data"""
        try:
            # Extract from meta tags
            meta_tags = soup.find_all('meta')
            for meta in meta_tags:
                name = meta.get('name', '').lower()
                content = meta.get('content', '')
                
                if 'title' in name and not parsed.title and len(content) > 10:
                    parsed.title = content.strip()
                elif 'author' in name and not parsed.authors and content:
                    authors = self._parse_author_list(content)
                    if authors:
                        parsed.authors = authors
                elif 'date' in name and not parsed.submission_date and content:
                    cleaned_date = self._clean_submission_date(content)
                    if cleaned_date:
                        parsed.submission_date = cleaned_date
            
            return parsed
            
        except Exception as e:
            logger.debug(f"Meta data extraction failed: {e}")
            return parsed
    
    async def _extract_from_form_fields(self, soup: BeautifulSoup, parsed: ParsedManuscriptData) -> ParsedManuscriptData:
        """Extract data from form fields and input elements"""
        try:
            # Look for hidden form fields or input elements with data
            inputs = soup.find_all(['input', 'textarea'])
            for input_elem in inputs:
                name = input_elem.get('name', '').lower()
                value = input_elem.get('value', '')
                
                if ('title' in name or 'subject' in name) and not parsed.title and len(value) > 10:
                    parsed.title = value.strip()
                elif 'author' in name and not parsed.authors and value:
                    authors = self._parse_author_list(value)
                    if authors:
                        parsed.authors = authors
                elif ('date' in name or 'submit' in name) and not parsed.submission_date and value:
                    cleaned_date = self._clean_submission_date(value)
                    if cleaned_date:
                        parsed.submission_date = cleaned_date
            
            return parsed
            
        except Exception as e:
            logger.debug(f"Form field extraction failed: {e}")
            return parsed
    
    async def _apply_parsed_data_to_manuscript(self, manuscript: Manuscript, parsed: ParsedManuscriptData):
        """Apply parsed data to manuscript object with validation"""
        try:
            if parsed.title:
                manuscript.title = parsed.title
            
            if parsed.authors:
                manuscript.authors = parsed.authors
            
            if parsed.submission_date:
                manuscript.submission_date = parsed.submission_date
            
            if parsed.corresponding_editor:
                manuscript.corresponding_editor = parsed.corresponding_editor
            
            if parsed.associate_editor:
                manuscript.associate_editor = parsed.associate_editor
            
            # Log what was successfully extracted
            logger.info(f"✅ Applied parsed data to {manuscript.id}:")
            logger.info(f"   📝 Title: {manuscript.title[:60] if manuscript.title else 'NOT FOUND'}...")
            logger.info(f"   👥 Authors: {len(manuscript.authors) if manuscript.authors else 0} found")
            logger.info(f"   📅 Submission: {manuscript.submission_date if manuscript.submission_date else 'NOT FOUND'}")
            logger.info(f"   📧 CE: {manuscript.corresponding_editor if manuscript.corresponding_editor else 'NOT FOUND'}")
            
        except Exception as e:
            logger.error(f"❌ Failed to apply parsed data: {e}")
    
    async def _extract_referee_information_enhanced(self, manuscript: Manuscript, soup: BeautifulSoup, content: str):
        """
        ENHANCED: Extract referee information with improved accuracy
        Addresses issues with missing emails and institution data
        """
        try:
            logger.info(f"🔍 ENHANCED referee extraction for {manuscript.id}")
            
            referees = []
            
            # Method 1: Extract from detailed referee sections with status parsing
            referees.extend(await self._extract_active_referees_enhanced(soup, content))
            
            # Method 2: Extract declined/inactive referees
            referees.extend(await self._extract_inactive_referees_enhanced(soup, content))
            
            # Method 3: Extract referee suggestions (potential future referees)
            referees.extend(await self._extract_referee_suggestions_enhanced(soup, content))
            
            # Apply to manuscript
            if referees:
                manuscript.referees = referees
                logger.info(f"✅ ENHANCED: Found {len(referees)} total referees for {manuscript.id}")
                
                # Log referee summary
                for referee in referees:
                    logger.info(f"   👤 {referee.name} ({referee.status}) - {referee.email or 'No email'}")
            else:
                logger.warning(f"⚠️ No referees found for {manuscript.id}")
            
        except Exception as e:
            logger.error(f"❌ Enhanced referee extraction failed: {e}")
    
    async def _extract_active_referees_enhanced(self, soup: BeautifulSoup, content: str) -> List[Referee]:
        """Extract active referees with enhanced email and institution detection"""
        referees = []
        
        try:
            # Look for referee sections in the content
            referee_section_patterns = [
                r'Current.*Referees[^<]*</[^>]+>.*?(?=<(?:h\d|div|table))',
                r'Referees[^<]*</[^>]+>.*?(?=<(?:h\d|div|table))',
                r'Under.*Review.*Referees[^<]*</[^>]+>.*?(?=<(?:h\d|div|table))'
            ]
            
            for pattern in referee_section_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    section_html = match.group(0)
                    section_soup = BeautifulSoup(section_html, 'html.parser')
                    
                    # Extract referee links from this section
                    referee_links = section_soup.find_all('a', href=re.compile(r'biblio_dump'))
                    for link in referee_links:
                        referee_data = await self._parse_referee_link_enhanced(link, section_html)
                        if referee_data:
                            referees.append(referee_data)
            
            # If no referees found in sections, look for individual referee mentions
            if not referees:
                all_referee_links = soup.find_all('a', href=re.compile(r'biblio_dump'))
                for link in all_referee_links:
                    referee_data = await self._parse_referee_link_enhanced(link, content)
                    if referee_data:
                        referees.append(referee_data)
            
            return referees
            
        except Exception as e:
            logger.error(f"❌ Active referee extraction failed: {e}")
            return []
    
    async def _parse_referee_link_enhanced(self, link: Tag, context_html: str) -> Optional[Referee]:
        """Parse individual referee link with enhanced data extraction"""
        try:
            referee_name = link.get_text(strip=True)
            if not referee_name or len(referee_name) < 2:
                return None
            
            # Extract biblio URL for detailed information
            biblio_href = link.get('href', '')
            biblio_url = f"{self.base_url}/{biblio_href}" if biblio_href and not biblio_href.startswith('http') else biblio_href
            
            # Parse status and dates from surrounding context
            parent_text = link.parent.get_text() if link.parent else ""
            status, dates = self._parse_referee_status_and_dates(parent_text, context_html)
            
            # Create referee object
            referee = Referee(
                name=referee_name,
                email="",  # Will be filled by biblio extraction
                status=status,
                institution=None,  # Will be filled by biblio extraction
                report_submitted=(status == "Report submitted"),
                **dates
            )
            
            # Extract detailed information from biblio page
            if biblio_url:
                try:
                    await self._extract_referee_details_from_biblio_enhanced(referee, biblio_url)
                except Exception as e:
                    logger.warning(f"Failed to extract biblio details for {referee_name}: {e}")
            
            return referee
            
        except Exception as e:
            logger.error(f"❌ Referee link parsing failed: {e}")
            return None
    
    def _parse_referee_status_and_dates(self, text: str, context: str) -> tuple[str, dict]:
        """Parse referee status and associated dates from text context"""
        status = "Review pending"  # Default
        dates = {}
        
        try:
            # Status patterns
            if re.search(r'Rcvd:|received|submitted', text, re.IGNORECASE):
                status = "Report submitted"
            elif re.search(r'declined|refuse', text, re.IGNORECASE):
                status = "Declined"
            elif re.search(r'accept|agree', text, re.IGNORECASE):
                status = "Accepted"
            elif re.search(r'due:|pending', text, re.IGNORECASE):
                status = "Review pending"
            
            # Date patterns
            date_patterns = {
                'report_date': r'Rcvd:\s*(\d{4}-\d{2}-\d{2})',
                'due_date': r'Due:\s*(\d{4}-\d{2}-\d{2})',
                'contact_date': r'Contact.*Date:\s*(\d{4}-\d{2}-\d{2})',
                'last_contact': r'Last.*Contact.*Date:\s*(\d{4}-\d{2}-\d{2})'
            }
            
            for key, pattern in date_patterns.items():
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    dates[key] = match.group(1)
            
            return status, dates
            
        except Exception as e:
            logger.debug(f"Status parsing error: {e}")
            return status, dates
    
    async def _extract_referee_details_from_biblio_enhanced(self, referee: Referee, biblio_url: str):
        """Enhanced extraction of referee details from biblio page"""
        try:
            logger.info(f"🔗 ENHANCED: Extracting biblio details for {referee.name}")
            
            # Navigate to biblio page
            await self.page.goto(biblio_url, timeout=30000)
            await asyncio.sleep(2)
            
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Save debug content
            debug_file = f"debug_referee_{referee.name.replace(' ', '_')}_ENHANCED.html"
            with open(debug_file, 'w') as f:
                f.write(content)
            
            # Extract email with multiple methods
            email = self._extract_email_enhanced(soup, content)
            if email:
                referee.email = email.upper()  # SIAM emails are typically uppercase
                logger.info(f"📧 ENHANCED: Found email: {referee.email}")
            
            # Extract institution with multiple methods
            institution = self._extract_institution_enhanced(soup, content)
            if institution:
                referee.institution = institution
                logger.info(f"🏛️ ENHANCED: Found institution: {referee.institution}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Enhanced biblio extraction failed for {referee.name}: {e}")
            return False
    
    def _extract_email_enhanced(self, soup: BeautifulSoup, content: str) -> Optional[str]:
        """Enhanced email extraction with multiple methods"""
        
        # Method 1: Direct email pattern matching
        email_patterns = [
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'Email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
            r'E-mail[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        ]
        
        for pattern in email_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Validate and return first valid email
                for email in matches:
                    if self._validate_email(email):
                        return email
        
        # Method 2: Look in specific HTML elements
        email_elements = soup.find_all(['td', 'div', 'span'], text=re.compile(r'@'))
        for elem in email_elements:
            text = elem.get_text(strip=True)
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', text)
            if email_match and self._validate_email(email_match.group(1)):
                return email_match.group(1)
        
        return None
    
    def _extract_institution_enhanced(self, soup: BeautifulSoup, content: str) -> Optional[str]:
        """Enhanced institution extraction"""
        
        # Method 1: Look for institution patterns
        institution_patterns = [
            r'Institution[:\s]*([^\n<]+)',
            r'Affiliation[:\s]*([^\n<]+)',
            r'University[:\s]*([^\n<]+)',
            r'College[:\s]*([^\n<]+)'
        ]
        
        for pattern in institution_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                institution = matches[0].strip()
                if len(institution) > 3 and len(institution) < 200:
                    return institution
        
        # Method 2: Infer from email domain
        email_match = re.search(r'@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', content)
        if email_match:
            domain = email_match.group(1).lower()
            institution = self._infer_institution_from_domain(domain)
            if institution:
                return institution
        
        return None
    
    def _infer_institution_from_domain(self, domain: str) -> Optional[str]:
        """Infer institution name from email domain"""
        domain_mapping = {
            'mit.edu': 'Massachusetts Institute of Technology',
            'harvard.edu': 'Harvard University',
            'stanford.edu': 'Stanford University',
            'berkeley.edu': 'UC Berkeley',
            'cambridge.ac.uk': 'University of Cambridge',
            'ox.ac.uk': 'University of Oxford',
            'polytechnique.edu': 'École Polytechnique',
            'ens.fr': 'École Normale Supérieure',
            'sorbonne-universite.fr': 'Sorbonne Université',
            'u-paris.fr': 'Université Paris',
            'inria.fr': 'INRIA',
            'kth.se': 'KTH Royal Institute of Technology',
            'uchicago.edu': 'University of Chicago',
            'hu-berlin.de': 'Humboldt University Berlin'
        }
        
        # Direct mapping
        if domain in domain_mapping:
            return domain_mapping[domain]
        
        # Fuzzy matching for common patterns
        if 'univ' in domain or 'university' in domain:
            # Extract university name from domain
            parts = domain.split('.')
            for part in parts:
                if 'univ' in part and len(part) > 4:
                    return f"{part.title()} University"
        
        return None
    
    def _validate_email(self, email: str) -> bool:
        """Validate email address format"""
        if not email or len(email) < 5:
            return False
        
        # Basic email validation
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    async def _extract_inactive_referees_enhanced(self, soup: BeautifulSoup, content: str) -> List[Referee]:
        """Extract declined/inactive referees"""
        referees = []
        
        try:
            # Look for potential/declined referee sections
            declined_patterns = [
                r'Potential.*Referees[^<]*</[^>]+>.*?(?=<(?:h\d|div|table))',
                r'Declined.*Referees[^<]*</[^>]+>.*?(?=<(?:h\d|div|table))',
                r'Previous.*Referees[^<]*</[^>]+>.*?(?=<(?:h\d|div|table))'
            ]
            
            for pattern in declined_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    section_html = match.group(0)
                    section_soup = BeautifulSoup(section_html, 'html.parser')
                    
                    # Extract referee links from declined section
                    referee_links = section_soup.find_all('a', href=re.compile(r'biblio_dump'))
                    for link in referee_links:
                        referee_data = await self._parse_referee_link_enhanced(link, section_html)
                        if referee_data:
                            # Override status for declined section
                            referee_data.status = "Declined"
                            referees.append(referee_data)
            
            return referees
            
        except Exception as e:
            logger.error(f"❌ Inactive referee extraction failed: {e}")
            return []
    
    async def _extract_referee_suggestions_enhanced(self, soup: BeautifulSoup, content: str) -> List[Referee]:
        """Extract referee suggestions (potential future referees)"""
        referees = []
        
        try:
            # Look for referee suggestions with emails
            suggestions_pattern = r'Referee.*Suggestions[^<]*</[^>]+>.*?(\d+\.\s*[^<]*@[^<]*)'
            matches = re.finditer(suggestions_pattern, content, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                suggestions_text = match.group(1)
                
                # Parse individual suggestions
                suggestion_pattern = r'(\d+)\.\s*([^,]+),\s*Email:\s*([^\s]+)'
                suggestions = re.findall(suggestion_pattern, suggestions_text, re.IGNORECASE)
                
                for num, name, email in suggestions:
                    if self._validate_email(email):
                        referee = Referee(
                            name=name.strip(),
                            email=email.strip(),
                            status="Suggested (not contacted)",
                            institution=self._infer_institution_from_domain(email.split('@')[1].lower())
                        )
                        referees.append(referee)
                        logger.info(f"💡 SUGGESTION: {name.strip()} ({email.strip()})")
            
            return referees
            
        except Exception as e:
            logger.error(f"❌ Referee suggestions extraction failed: {e}")
            return []


class DataValidator:
    """Data validation class for manuscript and referee data"""
    
    def validate_manuscript_data(self, manuscript: Manuscript) -> 'ValidationResult':
        """Validate extracted manuscript data"""
        errors = []
        warnings = []
        
        # Required field validation
        if not manuscript.id:
            errors.append("Missing manuscript ID")
        
        if not manuscript.title or len(manuscript.title) < 10:
            warnings.append("Title missing or too short")
        
        if not manuscript.authors:
            warnings.append("No authors found")
        
        if not manuscript.submission_date:
            warnings.append("Submission date missing")
        elif not self._validate_submission_date(manuscript.submission_date):
            warnings.append(f"Suspicious submission date: {manuscript.submission_date}")
        
        if not manuscript.corresponding_editor:
            warnings.append("Corresponding editor missing")
        
        # Referee validation
        if manuscript.referees:
            for referee in manuscript.referees:
                if not referee.email and referee.status not in ["Suggested (not contacted)", "Not contacted"]:
                    warnings.append(f"Missing email for referee {referee.name}")
        else:
            warnings.append("No referees found")
        
        return ValidationResult(
            is_valid=(len(errors) == 0),
            errors=errors,
            warnings=warnings
        )
    
    def _validate_submission_date(self, date_str: str) -> bool:
        """Validate submission date format and reasonableness"""
        try:
            # Check for common invalid patterns
            invalid_patterns = [
                r'accepted.*published',
                r'conference.*proceedings',
                r'supporting.*materials'
            ]
            
            for pattern in invalid_patterns:
                if re.search(pattern, date_str, re.IGNORECASE):
                    return False
            
            # Check for reasonable date patterns
            if re.search(r'\d{4}', date_str):
                return True
            
            return False
            
        except Exception:
            return False


@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


# Usage example
if __name__ == "__main__":
    async def test_fixed_sicon():
        extractor = SICONExtractorFixed()
        results = await extractor.extract(
            username="your_username",
            password="your_password",
            headless=False
        )
        
        print(f"\n✅ FIXED Extraction Results:")
        print(f"📄 Manuscripts: {results['total_manuscripts']}")
        print(f"👥 Total referees: {results['statistics']['total_referees']}")
        print(f"📧 Referees with emails: {results['statistics']['referees_with_emails']}")
        print(f"🏛️ Referees with institutions: {results['statistics']['referees_with_institutions']}")
    
    asyncio.run(test_fixed_sicon())