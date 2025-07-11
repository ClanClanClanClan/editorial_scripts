"""
Mock data generators for testing
"""
from datetime import datetime, timedelta
import random
import base64
from typing import Dict, List, Optional

class MockDataGenerator:
    """Generate realistic mock data for testing"""
    
    # Sample data pools
    FIRST_NAMES = ["John", "Jane", "Robert", "Maria", "David", "Sarah", "Michael", "Emma", "James", "Lisa"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
    UNIVERSITIES = ["University", "College", "Institute", "Academy", "School"]
    DEPARTMENTS = ["Mathematics", "Computer Science", "Physics", "Engineering", "Statistics", "Operations Research"]
    DOMAINS = ["edu", "ac.uk", "edu.au", "uni.de", "fr", "ch"]
    
    PAPER_TITLES = [
        "Optimal Control of Stochastic Systems with Applications",
        "Machine Learning Approaches to Combinatorial Optimization",
        "Novel Algorithms for Large-Scale Linear Programming",
        "Convergence Analysis of Gradient Descent Methods",
        "Portfolio Optimization under Uncertainty",
        "Deep Learning for Scientific Computing",
        "Efficient Methods for Convex Optimization",
        "Stability Analysis of Dynamical Systems"
    ]
    
    JOURNAL_PREFIXES = {
        "SICON": "SICON-",
        "SIFIN": "SIFIN-",
        "MOR": "MOR-",
        "MF": "MAFI-",
        "JOTA": "JOTA-D-",
        "MAFE": "MAFE-D-",
        "NACO": "NACO-",
        "FS": "FS-"
    }
    
    @classmethod
    def generate_referee_name(cls) -> str:
        """Generate a random referee name"""
        return f"{random.choice(cls.FIRST_NAMES)} {random.choice(cls.LAST_NAMES)}"
    
    @classmethod
    def generate_email(cls, name: Optional[str] = None) -> str:
        """Generate email address from name"""
        if not name:
            name = cls.generate_referee_name()
        
        parts = name.lower().split()
        username = f"{parts[0][0]}{parts[-1]}"
        
        institution = random.choice(cls.UNIVERSITIES).lower()
        domain = random.choice(cls.DOMAINS)
        
        return f"{username}@{institution}.{domain}"
    
    @classmethod
    def generate_manuscript_id(cls, journal: str = "SICON") -> str:
        """Generate manuscript ID"""
        prefix = cls.JOURNAL_PREFIXES.get(journal, "TEST-")
        year = random.randint(23, 25)
        number = random.randint(1, 999)
        revision = random.choice(["", "R1", "R2"])
        
        return f"{prefix}{year:02d}-{number:05d}{revision}"
    
    @classmethod
    def generate_manuscript(cls, journal: str = "SICON", 
                           num_referees: int = 2,
                           base_date: Optional[datetime] = None) -> Dict:
        """Generate a complete manuscript record"""
        if not base_date:
            base_date = datetime.now() - timedelta(days=30)
        
        manuscript = {
            "Manuscript #": cls.generate_manuscript_id(journal),
            "Title": random.choice(cls.PAPER_TITLES),
            "Contact Author": cls.generate_referee_name(),
            "Current Stage": random.choice(["Under Review", "Pending Referee Assignment", "All Referees Assigned"]),
            "Submission Date": base_date.isoformat(),
            "Referees": []
        }
        
        # Generate referees
        for i in range(num_referees):
            referee = cls.generate_referee(
                base_date=base_date + timedelta(days=i*5)
            )
            manuscript["Referees"].append(referee)
        
        return manuscript
    
    @classmethod
    def generate_referee(cls, status: Optional[str] = None,
                        base_date: Optional[datetime] = None) -> Dict:
        """Generate a referee record"""
        if not base_date:
            base_date = datetime.now() - timedelta(days=20)
        
        if not status:
            status = random.choice(["Accepted", "Contacted", "Declined"])
        
        name = cls.generate_referee_name()
        referee = {
            "Referee Name": name,
            "Status": status,
            "Referee Email": cls.generate_email(name),
            "Contacted Date": base_date.isoformat()
        }
        
        if status == "Accepted":
            accepted_date = base_date + timedelta(days=random.randint(1, 5))
            referee["Accepted Date"] = accepted_date.isoformat()
            referee["Due Date"] = (accepted_date + timedelta(days=28)).isoformat()
        elif status == "Declined":
            referee["Declined Date"] = (base_date + timedelta(days=1)).isoformat()
        
        return referee
    
    @classmethod
    def generate_email_message(cls, message_type: str = "acceptance",
                              journal: str = "SICON") -> Dict:
        """Generate mock email message"""
        if message_type == "acceptance":
            return cls._generate_acceptance_email(journal)
        elif message_type == "invitation":
            return cls._generate_invitation_email(journal)
        elif message_type == "weekly":
            return cls._generate_weekly_overview(journal)
        else:
            return cls._generate_status_email(journal)
    
    @classmethod
    def _generate_acceptance_email(cls, journal: str) -> Dict:
        """Generate acceptance email"""
        referee_name = cls.generate_referee_name()
        ms_id = cls.generate_manuscript_id(journal)
        
        subject_templates = {
            "JOTA": f"JOTA - Reviewer has agreed to review {ms_id}",
            "MAFE": f"MAFE - Reviewer has agreed to review {ms_id}",
            "MOR": f"Mathematics of Operations Research - {referee_name} agreed to review {ms_id}",
            "MF": f"Mathematical Finance - Thank you for agreeing to review {ms_id}",
            "DEFAULT": f"{journal} manuscript #{ms_id} - Referee agreed"
        }
        
        subject = subject_templates.get(journal, subject_templates["DEFAULT"])
        
        body = f"""
        Dear Editor,
        
        {referee_name} has agreed to review manuscript {ms_id}.
        
        Title: {random.choice(cls.PAPER_TITLES)}
        
        The reviewer has been given until {(datetime.now() + timedelta(days=28)).strftime('%B %d, %Y')} to complete the review.
        
        Best regards,
        Editorial Manager
        """
        
        return {
            'id': f'msg_{random.randint(1000, 9999)}',
            'subject': subject,
            'from': 'em@editorialmanager.com',
            'to': f'editor@{journal.lower()}.org',
            'date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'),
            'body': body
        }
    
    @classmethod
    def _generate_invitation_email(cls, journal: str) -> Dict:
        """Generate invitation email"""
        referee_name = cls.generate_referee_name()
        ms_id = cls.generate_manuscript_id(journal)
        title = random.choice(cls.PAPER_TITLES)
        
        body = f"""
        Dear Dr. {referee_name},
        
        I would like to invite you to review the following manuscript:
        
        Manuscript ID: {ms_id}
        Title: "{title}"
        
        Authors: {cls.generate_referee_name()}, {cls.generate_referee_name()}
        
        Please log in to the editorial system to accept or decline this invitation.
        
        Best regards,
        Associate Editor
        """
        
        return {
            'id': f'msg_{random.randint(1000, 9999)}',
            'subject': f"{journal} - Invitation to review {ms_id}",
            'from': f'editor@{journal.lower()}.org',
            'to': cls.generate_email(referee_name),
            'date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'),
            'body': body
        }
    
    @classmethod
    def _generate_weekly_overview(cls, journal: str) -> Dict:
        """Generate weekly overview email"""
        manuscripts = []
        
        for i in range(random.randint(2, 5)):
            ms_id = cls.generate_manuscript_id(journal)
            days_ago = random.randint(10, 90)
            status_days = random.randint(5, 30)
            agreed = random.randint(0, 3)
            
            ms_text = f"""
{ms_id}  submitted {days_ago} days ago  Under Review ({status_days} days) {agreed} Agreed
Title: {random.choice(cls.PAPER_TITLES)}
Authors: {cls.generate_referee_name()}, {random.choice(cls.UNIVERSITIES)}; {cls.generate_referee_name()}, {random.choice(cls.UNIVERSITIES)}
"""
            manuscripts.append(ms_text)
        
        body = f"""
Weekly Overview of Your Assignments

{''.join(manuscripts)}

Best regards,
Editorial System
"""
        
        return {
            'id': f'msg_{random.randint(1000, 9999)}',
            'subject': f"{journal} - Weekly Overview Of Your Assignments",
            'from': 'em@editorialmanager.com',
            'to': f'editor@{journal.lower()}.org',
            'date': datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000'),
            'body': body
        }
    
    @classmethod
    def generate_gmail_message(cls, email_dict: Dict) -> Dict:
        """Convert email dict to Gmail API format"""
        body_data = base64.urlsafe_b64encode(email_dict['body'].encode()).decode()
        
        return {
            'id': email_dict['id'],
            'payload': {
                'headers': [
                    {'name': 'Subject', 'value': email_dict['subject']},
                    {'name': 'From', 'value': email_dict['from']},
                    {'name': 'To', 'value': email_dict['to']},
                    {'name': 'Date', 'value': email_dict['date']}
                ],
                'body': {
                    'data': body_data
                }
            }
        }
    
    @classmethod
    def generate_review_history(cls, referee_email: str,
                               num_reviews: int = 5,
                               journal: str = "SICON") -> List[Dict]:
        """Generate review history for a referee"""
        reviews = []
        base_date = datetime.now() - timedelta(days=365)
        
        for i in range(num_reviews):
            invited_date = base_date + timedelta(days=i * 60)
            
            # Vary the outcomes
            if i % 4 == 0:
                # Declined
                review = {
                    'referee_email': referee_email,
                    'manuscript_id': cls.generate_manuscript_id(journal),
                    'journal': journal,
                    'invited_date': invited_date,
                    'responded_date': invited_date + timedelta(days=2),
                    'decision': 'declined'
                }
            elif i % 3 == 0:
                # No response
                review = {
                    'referee_email': referee_email,
                    'manuscript_id': cls.generate_manuscript_id(journal),
                    'journal': journal,
                    'invited_date': invited_date,
                    'decision': 'no_response'
                }
            else:
                # Accepted and completed
                responded = invited_date + timedelta(days=random.randint(1, 7))
                submitted = responded + timedelta(days=random.randint(14, 35))
                
                review = {
                    'referee_email': referee_email,
                    'manuscript_id': cls.generate_manuscript_id(journal),
                    'journal': journal,
                    'invited_date': invited_date,
                    'responded_date': responded,
                    'decision': 'accepted',
                    'review_submitted_date': submitted,
                    'report_quality_score': random.uniform(6.0, 9.5),
                    'days_late': max(0, (submitted - responded - timedelta(days=28)).days)
                }
            
            reviews.append(review)
        
        return reviews