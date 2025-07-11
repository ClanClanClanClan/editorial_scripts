"""Finance and Stochastics (FS) journal extractor - Email-based."""

from typing import List, Dict, Any, Optional
import logging
import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

from editorial_assistant.core.data_models import JournalConfig, Manuscript, Referee, ManuscriptStatus
from editorial_assistant.extractors.base_platform_extractors import EmailBasedExtractor


class FSExtractor(EmailBasedExtractor):
    """Finance and Stochastics journal extractor using email-based approach."""
    
    def __init__(self, journal: JournalConfig):
        super().__init__(journal)
        self.journal_name = "Finance and Stochastics"
        
    def extract_from_emails(self) -> List[Dict[str, Any]]:
        """Extract manuscript data from FS email communications."""
        try:
            # Get email search patterns from journal config
            email_subjects = self.journal.patterns.get('email_subjects', ['Finance and Stochastics', 'FS manuscript'])
            lookback_days = self.journal.settings.get('email_lookback_days', 30)
            
            # Search for FS-related emails
            manuscripts = []
            
            # Search starred emails
            starred_emails = self._search_starred_emails()
            manuscripts.extend(self._parse_starred_emails(starred_emails))
            
            # Search editor communications
            editor_emails = self._search_editor_communications(email_subjects, lookback_days)
            manuscripts.extend(self._parse_editor_emails(editor_emails))
            
            # Remove duplicates and merge data
            merged_manuscripts = self._merge_manuscript_data(manuscripts)
            
            logging.info(f"[FS] Extracted {len(merged_manuscripts)} manuscripts from emails")
            return merged_manuscripts
            
        except Exception as e:
            logging.error(f"[FS] Email extraction failed: {e}")
            return []
    
    def _search_starred_emails(self) -> List[Dict[str, Any]]:
        """Search for starred emails related to FS."""
        try:
            # Use Gmail API to search for starred emails
            query = f'is:starred ("{self.journal_name}" OR "FS manuscript" OR "FS-20")'
            
            emails = self.email_manager.search_emails(query)
            
            parsed_emails = []
            for email in emails:
                try:
                    parsed_email = self._parse_email_content(email)
                    if parsed_email:
                        parsed_emails.append(parsed_email)
                except Exception as e:
                    logging.warning(f"[FS] Failed to parse starred email: {e}")
                    continue
            
            return parsed_emails
            
        except Exception as e:
            logging.error(f"[FS] Failed to search starred emails: {e}")
            return []
    
    def _search_editor_communications(self, subjects: List[str], lookback_days: int) -> List[Dict[str, Any]]:
        """Search for editor communications within lookback period."""
        try:
            # Build search query for editor communications
            subject_queries = [f'subject:"{subject}"' for subject in subjects]
            query = f'({" OR ".join(subject_queries)}) newer_than:{lookback_days}d'
            
            emails = self.email_manager.search_emails(query)
            
            parsed_emails = []
            for email in emails:
                try:
                    parsed_email = self._parse_email_content(email)
                    if parsed_email:
                        parsed_emails.append(parsed_email)
                except Exception as e:
                    logging.warning(f"[FS] Failed to parse editor email: {e}")
                    continue
            
            return parsed_emails
            
        except Exception as e:
            logging.error(f"[FS] Failed to search editor communications: {e}")
            return []
    
    def _parse_email_content(self, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse email content to extract manuscript information."""
        try:
            subject = email.get('subject', '')
            body = email.get('body', '')
            date = email.get('date')
            
            # Extract manuscript ID using FS pattern
            manuscript_id = self._extract_manuscript_id(subject, body)
            if not manuscript_id:
                return None
            
            # Parse different types of emails
            if "referee" in subject.lower() or "reviewer" in subject.lower():
                return self._parse_referee_email(manuscript_id, subject, body, date)
            elif "submission" in subject.lower() or "manuscript" in subject.lower():
                return self._parse_submission_email(manuscript_id, subject, body, date)
            elif "decision" in subject.lower() or "accept" in subject.lower():
                return self._parse_decision_email(manuscript_id, subject, body, date)
            else:
                return self._parse_general_email(manuscript_id, subject, body, date)
            
        except Exception as e:
            logging.error(f"[FS] Failed to parse email content: {e}")
            return None
    
    def _extract_manuscript_id(self, subject: str, body: str) -> Optional[str]:
        """Extract manuscript ID from email subject or body."""
        # Try FS pattern from journal config
        pattern = self.journal.patterns.get('manuscript_id', 'FS-\\d{4}-\\d{4}')
        
        # Search in subject first
        match = re.search(pattern, subject)
        if match:
            return match.group(0)
        
        # Search in body
        match = re.search(pattern, body)
        if match:
            return match.group(0)
        
        # Try alternative patterns
        alt_patterns = [
            r'FS-\d{2}-\d{4}',
            r'FS\s*\d{4}-\d{4}',
            r'manuscript\s*#?\s*(FS-?\d{2,4}-\d{4})',
        ]
        
        for pattern in alt_patterns:
            match = re.search(pattern, subject + ' ' + body, re.IGNORECASE)
            if match:
                return match.group(1) if match.groups() else match.group(0)
        
        return None
    
    def _parse_referee_email(self, manuscript_id: str, subject: str, body: str, date: datetime) -> Dict[str, Any]:
        """Parse referee-related email."""
        # Extract referee information
        referee_name = self._extract_referee_name(subject, body)
        referee_email = self._extract_referee_email(body)
        
        # Determine referee status
        status = "Contacted"
        if any(word in subject.lower() for word in ['accepted', 'agreed', 'confirmed']):
            status = "Accepted"
        elif any(word in subject.lower() for word in ['declined', 'rejected']):
            status = "Declined"
        
        referee_data = {
            "name": referee_name,
            "email": referee_email,
            "status": status,
            "contacted_date": date.isoformat() if date else None,
            "due_date": self._extract_due_date(body)
        }
        
        return {
            "manuscript_id": manuscript_id,
            "type": "referee_communication",
            "subject": subject,
            "date": date.isoformat() if date else None,
            "referees": [referee_data],
            "title": self._extract_title(subject, body),
            "status": self._infer_manuscript_status(subject, body)
        }
    
    def _parse_submission_email(self, manuscript_id: str, subject: str, body: str, date: datetime) -> Dict[str, Any]:
        """Parse submission-related email."""
        return {
            "manuscript_id": manuscript_id,
            "type": "submission",
            "subject": subject,
            "date": date.isoformat() if date else None,
            "title": self._extract_title(subject, body),
            "author": self._extract_author(body),
            "submission_date": date.isoformat() if date else None,
            "status": "Submitted"
        }
    
    def _parse_decision_email(self, manuscript_id: str, subject: str, body: str, date: datetime) -> Dict[str, Any]:
        """Parse decision-related email."""
        decision = "Unknown"
        if any(word in subject.lower() for word in ['accept', 'accepted']):
            decision = "Accepted"
        elif any(word in subject.lower() for word in ['reject', 'rejected']):
            decision = "Rejected"
        elif any(word in subject.lower() for word in ['revision', 'revise']):
            decision = "Revision Required"
        
        return {
            "manuscript_id": manuscript_id,
            "type": "decision",
            "subject": subject,
            "date": date.isoformat() if date else None,
            "title": self._extract_title(subject, body),
            "decision": decision,
            "status": decision
        }
    
    def _parse_general_email(self, manuscript_id: str, subject: str, body: str, date: datetime) -> Dict[str, Any]:
        """Parse general email communication."""
        return {
            "manuscript_id": manuscript_id,
            "type": "general",
            "subject": subject,
            "date": date.isoformat() if date else None,
            "title": self._extract_title(subject, body),
            "status": self._infer_manuscript_status(subject, body)
        }
    
    def _extract_referee_name(self, subject: str, body: str) -> str:
        """Extract referee name from email content."""
        # Common patterns for referee names
        patterns = [
            r'Dear\s+(?:Prof\.?|Dr\.?|Mr\.?|Ms\.?)\s+([A-Z][a-zA-Z\s\-\']{2,})',
            r'([A-Z][a-zA-Z\s\-\']{2,})\s+has\s+(?:accepted|agreed|declined)',
            r'Reviewer:\s+([A-Z][a-zA-Z\s\-\']{2,})',
            r'Prof\.?\s+([A-Z][a-zA-Z\s\-\']{2,})',
            r'Dr\.?\s+([A-Z][a-zA-Z\s\-\']{2,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 2:
                    return name
        
        return ""
    
    def _extract_referee_email(self, body: str) -> str:
        """Extract referee email from email body."""
        # Standard email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        emails = re.findall(email_pattern, body)
        
        # Filter out common system emails
        system_emails = ['noreply', 'admin', 'support', 'system']
        for email in emails:
            if not any(sys_email in email.lower() for sys_email in system_emails):
                return email
        
        return ""
    
    def _extract_title(self, subject: str, body: str) -> str:
        """Extract manuscript title from email content."""
        # Common patterns for title extraction
        patterns = [
            r'Title:\s*([^\n\r]+)',
            r'titled\s*["\']([^"\'\n\r]+)["\']',
            r'paper\s*["\']([^"\'\n\r]+)["\']',
            r'manuscript\s*["\']([^"\'\n\r]+)["\']',
            r'article\s*["\']([^"\'\n\r]+)["\']',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                if len(title) > 10:
                    return title
        
        return ""
    
    def _extract_author(self, body: str) -> str:
        """Extract author name from email body."""
        # Common patterns for author extraction
        patterns = [
            r'Author:\s*([^\n\r]+)',
            r'by\s+([A-Z][a-zA-Z\s\-\']{2,})',
            r'From:\s*([A-Z][a-zA-Z\s\-\']{2,})',
            r'Submitted\s+by\s+([A-Z][a-zA-Z\s\-\']{2,})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                author = match.group(1).strip()
                if len(author) > 2:
                    return author
        
        return ""
    
    def _extract_due_date(self, body: str) -> Optional[str]:
        """Extract due date from email body."""
        # Common patterns for due dates
        patterns = [
            r'due\s+(?:on\s+)?([\d\-/]+)',
            r'deadline\s+(?:is\s+)?([\d\-/]+)',
            r'by\s+([\d\-/]+)',
            r'before\s+([\d\-/]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Try to parse and format the date
                try:
                    if '/' in date_str:
                        date_obj = datetime.strptime(date_str, '%m/%d/%Y')
                    elif '-' in date_str:
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    else:
                        continue
                    return date_obj.isoformat()
                except ValueError:
                    continue
        
        return None
    
    def _infer_manuscript_status(self, subject: str, body: str) -> str:
        """Infer manuscript status from email content."""
        content = (subject + ' ' + body).lower()
        
        if any(word in content for word in ['accepted', 'accept']):
            return "Accepted"
        elif any(word in content for word in ['rejected', 'reject']):
            return "Rejected"
        elif any(word in content for word in ['revision', 'revise']):
            return "Revision Required"
        elif any(word in content for word in ['under review', 'reviewing']):
            return "Under Review"
        elif any(word in content for word in ['submitted', 'submission']):
            return "Submitted"
        else:
            return "Unknown"
    
    def _merge_manuscript_data(self, manuscripts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge manuscript data from multiple emails."""
        merged = {}
        
        for manuscript in manuscripts:
            manuscript_id = manuscript.get('manuscript_id')
            if not manuscript_id:
                continue
            
            if manuscript_id not in merged:
                merged[manuscript_id] = {
                    "Manuscript #": manuscript_id,
                    "Title": manuscript.get('title', ''),
                    "Contact Author": manuscript.get('author', ''),
                    "Current Stage": manuscript.get('status', 'Unknown'),
                    "Submission Date": manuscript.get('submission_date', ''),
                    "Referees": [],
                    "Communications": []
                }
            
            # Update with non-empty values
            if manuscript.get('title'):
                merged[manuscript_id]["Title"] = manuscript['title']
            if manuscript.get('author'):
                merged[manuscript_id]["Contact Author"] = manuscript['author']
            if manuscript.get('status'):
                merged[manuscript_id]["Current Stage"] = manuscript['status']
            if manuscript.get('submission_date'):
                merged[manuscript_id]["Submission Date"] = manuscript['submission_date']
            
            # Add referees
            if manuscript.get('referees'):
                for referee in manuscript['referees']:
                    # Check if referee already exists
                    existing_referee = None
                    for existing in merged[manuscript_id]["Referees"]:
                        if (existing.get('Referee Name') == referee.get('name') or
                            existing.get('Referee Email') == referee.get('email')):
                            existing_referee = existing
                            break
                    
                    if existing_referee:
                        # Update existing referee
                        if referee.get('status'):
                            existing_referee['Status'] = referee['status']
                        if referee.get('due_date'):
                            existing_referee['Due Date'] = referee['due_date']
                    else:
                        # Add new referee
                        merged[manuscript_id]["Referees"].append({
                            "Referee Name": referee.get('name', ''),
                            "Referee Email": referee.get('email', ''),
                            "Status": referee.get('status', 'Contacted'),
                            "Contacted Date": referee.get('contacted_date', ''),
                            "Due Date": referee.get('due_date', '')
                        })
            
            # Add communication record
            merged[manuscript_id]["Communications"].append({
                "date": manuscript.get('date', ''),
                "subject": manuscript.get('subject', ''),
                "type": manuscript.get('type', 'general')
            })
        
        return list(merged.values())
