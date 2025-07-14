"""
Domain models for manuscript and referee management
Core business entities for the editorial system
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4


class ManuscriptStatus(Enum):
    """Manuscript status enumeration"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    DESK_REJECTED = "desk_rejected"
    REVISION_REQUESTED = "revision_requested"


class RefereeStatus(Enum):
    """Referee status enumeration"""
    INVITED = "invited"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    WITHDRAWN = "withdrawn"


@dataclass
class RefereeInfo:
    """Referee information for a manuscript"""
    name: str
    email: str = ""
    status: RefereeStatus = RefereeStatus.INVITED
    invited_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    response_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    expertise_areas: List[str] = field(default_factory=list)
    institution: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_overdue(self) -> bool:
        """Check if referee is overdue"""
        if not self.due_date or self.status in [RefereeStatus.COMPLETED, RefereeStatus.DECLINED]:
            return False
        return datetime.now() > self.due_date
    
    def days_since_invitation(self) -> Optional[int]:
        """Calculate days since invitation"""
        if not self.invited_date:
            return None
        return (datetime.now() - self.invited_date).days


@dataclass
class DocumentInfo:
    """Document information for a manuscript"""
    document_type: str  # 'manuscript', 'cover_letter', 'referee_report', 'supplement'
    url: str
    filename: str = ""
    file_size: Optional[int] = None
    download_date: Optional[datetime] = None
    local_path: Optional[str] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Manuscript:
    """Core manuscript domain object"""
    id: str
    title: str
    journal_code: str
    status: ManuscriptStatus = ManuscriptStatus.SUBMITTED
    submission_date: Optional[datetime] = None
    corresponding_editor: str = ""
    associate_editor: str = ""
    abstract: str = ""
    keywords: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    referees: List[RefereeInfo] = field(default_factory=list)
    documents: List[DocumentInfo] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization processing"""
        if not self.id:
            self.id = str(uuid4())
        self.updated_at = datetime.now()
    
    def add_referee(self, referee: RefereeInfo):
        """Add a referee to the manuscript"""
        # Check for duplicates
        existing_names = [r.name for r in self.referees]
        if referee.name not in existing_names:
            self.referees.append(referee)
            self.updated_at = datetime.now()
    
    def update_referee_status(self, referee_name: str, status: RefereeStatus, completion_date: Optional[datetime] = None):
        """Update referee status"""
        for referee in self.referees:
            if referee.name == referee_name:
                referee.status = status
                if completion_date:
                    referee.completion_date = completion_date
                self.updated_at = datetime.now()
                break
    
    def add_document(self, document: DocumentInfo):
        """Add a document to the manuscript"""
        self.documents.append(document)
        self.updated_at = datetime.now()
    
    def get_referees_by_status(self, status: RefereeStatus) -> List[RefereeInfo]:
        """Get referees by status"""
        return [r for r in self.referees if r.status == status]
    
    def get_overdue_referees(self) -> List[RefereeInfo]:
        """Get overdue referees"""
        return [r for r in self.referees if r.is_overdue()]
    
    def get_documents_by_type(self, document_type: str) -> List[DocumentInfo]:
        """Get documents by type"""
        return [d for d in self.documents if d.document_type == document_type]
    
    def days_in_system(self) -> Optional[int]:
        """Calculate days manuscript has been in system"""
        if not self.submission_date:
            return None
        return (datetime.now() - self.submission_date).days
    
    def is_stale(self, days_threshold: int = 90) -> bool:
        """Check if manuscript is stale (in system too long)"""
        days = self.days_in_system()
        return days is not None and days > days_threshold
    
    def referee_completion_rate(self) -> float:
        """Calculate referee completion rate"""
        if not self.referees:
            return 0.0
        
        completed = len(self.get_referees_by_status(RefereeStatus.COMPLETED))
        return completed / len(self.referees)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'title': self.title,
            'journal_code': self.journal_code,
            'status': self.status.value,
            'submission_date': self.submission_date.isoformat() if self.submission_date else None,
            'corresponding_editor': self.corresponding_editor,
            'associate_editor': self.associate_editor,
            'abstract': self.abstract,
            'keywords': self.keywords,
            'authors': self.authors,
            'referees': [
                {
                    'name': r.name,
                    'email': r.email,
                    'status': r.status.value,
                    'invited_date': r.invited_date.isoformat() if r.invited_date else None,
                    'due_date': r.due_date.isoformat() if r.due_date else None,
                    'expertise_areas': r.expertise_areas,
                    'institution': r.institution,
                    'metadata': r.metadata
                }
                for r in self.referees
            ],
            'documents': [
                {
                    'document_type': d.document_type,
                    'url': d.url,
                    'filename': d.filename,
                    'file_size': d.file_size,
                    'download_date': d.download_date.isoformat() if d.download_date else None,
                    'local_path': d.local_path,
                    'metadata': d.metadata
                }
                for d in self.documents
            ],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Manuscript':
        """Create from dictionary"""
        # Parse referees
        referees = []
        for ref_data in data.get('referees', []):
            referee = RefereeInfo(
                name=ref_data['name'],
                email=ref_data.get('email', ''),
                status=RefereeStatus(ref_data.get('status', 'invited')),
                invited_date=datetime.fromisoformat(ref_data['invited_date']) if ref_data.get('invited_date') else None,
                due_date=datetime.fromisoformat(ref_data['due_date']) if ref_data.get('due_date') else None,
                expertise_areas=ref_data.get('expertise_areas', []),
                institution=ref_data.get('institution', ''),
                metadata=ref_data.get('metadata', {})
            )
            referees.append(referee)
        
        # Parse documents
        documents = []
        for doc_data in data.get('documents', []):
            document = DocumentInfo(
                document_type=doc_data['document_type'],
                url=doc_data['url'],
                filename=doc_data.get('filename', ''),
                file_size=doc_data.get('file_size'),
                download_date=datetime.fromisoformat(doc_data['download_date']) if doc_data.get('download_date') else None,
                local_path=doc_data.get('local_path'),
                metadata=doc_data.get('metadata', {})
            )
            documents.append(document)
        
        # Create manuscript
        manuscript = cls(
            id=data['id'],
            title=data['title'],
            journal_code=data['journal_code'],
            status=ManuscriptStatus(data.get('status', 'submitted')),
            submission_date=datetime.fromisoformat(data['submission_date']) if data.get('submission_date') else None,
            corresponding_editor=data.get('corresponding_editor', ''),
            associate_editor=data.get('associate_editor', ''),
            abstract=data.get('abstract', ''),
            keywords=data.get('keywords', []),
            authors=data.get('authors', []),
            referees=referees,
            documents=documents,
            created_at=datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else datetime.now(),
            metadata=data.get('metadata', {})
        )
        
        return manuscript


@dataclass
class Journal:
    """Journal domain object"""
    code: str
    name: str
    platform: str
    base_url: str
    active: bool = True
    credentials_required: bool = True
    last_extraction: Optional[datetime] = None
    total_manuscripts: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'code': self.code,
            'name': self.name,
            'platform': self.platform,
            'base_url': self.base_url,
            'active': self.active,
            'credentials_required': self.credentials_required,
            'last_extraction': self.last_extraction.isoformat() if self.last_extraction else None,
            'total_manuscripts': self.total_manuscripts,
            'metadata': self.metadata
        }