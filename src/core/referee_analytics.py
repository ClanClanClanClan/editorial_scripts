"""
Comprehensive Referee Analytics System
Extracts detailed referee timelines and cross-references with Gmail
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import re
from enum import Enum


class RefereeEventType(Enum):
    """Types of referee events"""
    INVITED = "invited"
    REMINDER_SENT = "reminder_sent"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    REPORT_SUBMITTED = "report_submitted"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


@dataclass
class RefereeEvent:
    """A single event in a referee's timeline"""
    event_type: RefereeEventType
    date: datetime
    details: Optional[str] = None
    email_subject: Optional[str] = None
    email_id: Optional[str] = None


@dataclass
class RefereeTimeline:
    """Complete timeline for a referee"""
    name: str
    email: str
    manuscript_id: str
    journal_code: str
    
    # Key dates
    invited_date: Optional[datetime] = None
    accepted_date: Optional[datetime] = None
    declined_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    submitted_date: Optional[datetime] = None
    
    # Email tracking
    invitation_emails_sent: int = 0
    reminder_emails_sent: int = 0
    total_emails_sent: int = 0
    
    # Report details
    report_pdf_path: Optional[str] = None
    report_quality: Optional[str] = None
    report_length: Optional[int] = None
    
    # Timeline events
    events: List[RefereeEvent] = None
    
    # Gmail cross-reference
    gmail_thread_ids: List[str] = None
    gmail_verified: bool = False
    
    def __post_init__(self):
        if self.events is None:
            self.events = []
        if self.gmail_thread_ids is None:
            self.gmail_thread_ids = []
    
    def add_event(self, event: RefereeEvent):
        """Add an event to the timeline"""
        self.events.append(event)
        self.events.sort(key=lambda e: e.date)
        
        # Update counts based on event type
        if event.event_type == RefereeEventType.INVITED:
            self.invitation_emails_sent += 1
            self.total_emails_sent += 1
            if not self.invited_date:
                self.invited_date = event.date
        elif event.event_type == RefereeEventType.REMINDER_SENT:
            self.reminder_emails_sent += 1
            self.total_emails_sent += 1
        elif event.event_type == RefereeEventType.ACCEPTED:
            if not self.accepted_date:
                self.accepted_date = event.date
        elif event.event_type == RefereeEventType.DECLINED:
            if not self.declined_date:
                self.declined_date = event.date
        elif event.event_type == RefereeEventType.REPORT_SUBMITTED:
            if not self.submitted_date:
                self.submitted_date = event.date
    
    def get_response_time_days(self) -> Optional[int]:
        """Calculate days from invitation to response"""
        if self.invited_date:
            if self.accepted_date:
                return (self.accepted_date - self.invited_date).days
            elif self.declined_date:
                return (self.declined_date - self.invited_date).days
        return None
    
    def get_review_time_days(self) -> Optional[int]:
        """Calculate days from acceptance to submission"""
        if self.accepted_date and self.submitted_date:
            return (self.submitted_date - self.accepted_date).days
        return None
    
    def is_overdue(self) -> bool:
        """Check if review is overdue"""
        if self.due_date and not self.submitted_date:
            return datetime.now() > self.due_date
        return False
    
    def get_status(self) -> str:
        """Get current referee status"""
        if self.declined_date:
            return "Declined"
        elif self.submitted_date:
            return "Completed"
        elif self.accepted_date:
            if self.is_overdue():
                return "Overdue"
            else:
                return "In Progress"
        elif self.invited_date:
            return "Invited"
        else:
            return "Unknown"
    
    def to_analytics_dict(self) -> Dict[str, Any]:
        """Convert to analytics dictionary"""
        return {
            'name': self.name,
            'email': self.email,
            'manuscript_id': self.manuscript_id,
            'journal_code': self.journal_code,
            'status': self.get_status(),
            'invited_date': self.invited_date.isoformat() if self.invited_date else None,
            'accepted_date': self.accepted_date.isoformat() if self.accepted_date else None,
            'declined_date': self.declined_date.isoformat() if self.declined_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'submitted_date': self.submitted_date.isoformat() if self.submitted_date else None,
            'response_time_days': self.get_response_time_days(),
            'review_time_days': self.get_review_time_days(),
            'is_overdue': self.is_overdue(),
            'invitation_emails_sent': self.invitation_emails_sent,
            'reminder_emails_sent': self.reminder_emails_sent,
            'total_emails_sent': self.total_emails_sent,
            'report_available': bool(self.report_pdf_path),
            'gmail_verified': self.gmail_verified,
            'events_count': len(self.events)
        }


class RefereeAnalytics:
    """Analytics aggregator for referee data"""
    
    def __init__(self):
        self.timelines: Dict[str, RefereeTimeline] = {}
    
    def add_timeline(self, timeline: RefereeTimeline):
        """Add a referee timeline"""
        key = f"{timeline.journal_code}_{timeline.manuscript_id}_{timeline.email}"
        self.timelines[key] = timeline
    
    def get_journal_stats(self, journal_code: str) -> Dict[str, Any]:
        """Get statistics for a specific journal"""
        journal_timelines = [t for t in self.timelines.values() if t.journal_code == journal_code]
        
        if not journal_timelines:
            return {}
        
        # Calculate statistics
        total_referees = len(journal_timelines)
        accepted = sum(1 for t in journal_timelines if t.accepted_date)
        declined = sum(1 for t in journal_timelines if t.declined_date)
        completed = sum(1 for t in journal_timelines if t.submitted_date)
        overdue = sum(1 for t in journal_timelines if t.is_overdue())
        
        # Response times
        response_times = [t.get_response_time_days() for t in journal_timelines if t.get_response_time_days()]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Review times
        review_times = [t.get_review_time_days() for t in journal_timelines if t.get_review_time_days()]
        avg_review_time = sum(review_times) / len(review_times) if review_times else 0
        
        # Email statistics
        avg_invitations = sum(t.invitation_emails_sent for t in journal_timelines) / total_referees
        avg_reminders = sum(t.reminder_emails_sent for t in journal_timelines) / total_referees
        
        return {
            'journal_code': journal_code,
            'total_referees': total_referees,
            'accepted': accepted,
            'declined': declined,
            'completed': completed,
            'overdue': overdue,
            'acceptance_rate': accepted / total_referees * 100 if total_referees > 0 else 0,
            'completion_rate': completed / accepted * 100 if accepted > 0 else 0,
            'avg_response_time_days': round(avg_response_time, 1),
            'avg_review_time_days': round(avg_review_time, 1),
            'avg_invitation_emails': round(avg_invitations, 1),
            'avg_reminder_emails': round(avg_reminders, 1)
        }
    
    def get_referee_performance(self, email: str) -> Dict[str, Any]:
        """Get performance metrics for a specific referee across all journals"""
        referee_timelines = [t for t in self.timelines.values() if t.email == email]
        
        if not referee_timelines:
            return {}
        
        total_invitations = len(referee_timelines)
        accepted = sum(1 for t in referee_timelines if t.accepted_date)
        declined = sum(1 for t in referee_timelines if t.declined_date)
        completed = sum(1 for t in referee_timelines if t.submitted_date)
        
        # Average times
        response_times = [t.get_response_time_days() for t in referee_timelines if t.get_response_time_days()]
        review_times = [t.get_review_time_days() for t in referee_timelines if t.get_review_time_days()]
        
        return {
            'email': email,
            'name': referee_timelines[0].name if referee_timelines else '',
            'total_invitations': total_invitations,
            'accepted': accepted,
            'declined': declined,
            'completed': completed,
            'acceptance_rate': accepted / total_invitations * 100 if total_invitations > 0 else 0,
            'completion_rate': completed / accepted * 100 if accepted > 0 else 0,
            'avg_response_time_days': round(sum(response_times) / len(response_times), 1) if response_times else 0,
            'avg_review_time_days': round(sum(review_times) / len(review_times), 1) if review_times else 0,
            'journals': list(set(t.journal_code for t in referee_timelines))
        }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """Get overall statistics across all journals"""
        stats = {}
        for journal in ['SICON', 'SIFIN', 'MF', 'MOR']:
            journal_stats = self.get_journal_stats(journal)
            if journal_stats:
                stats[journal] = journal_stats
        
        # Overall totals
        all_timelines = list(self.timelines.values())
        stats['overall'] = {
            'total_referees': len(all_timelines),
            'unique_referees': len(set(t.email for t in all_timelines)),
            'total_reports': sum(1 for t in all_timelines if t.submitted_date),
            'gmail_verified': sum(1 for t in all_timelines if t.gmail_verified),
            'reports_with_pdf': sum(1 for t in all_timelines if t.report_pdf_path)
        }
        
        return stats