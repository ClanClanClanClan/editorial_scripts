"""
Domain ports (interfaces) for Editorial Scripts system
These define the contracts that infrastructure must implement
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from .models import (
    Manuscript, Referee, Review, ExtractionResult,
    JournalConfiguration, RefereeStatistics
)


class JournalExtractor(ABC):
    """Port for journal data extraction"""
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Authenticate with the journal platform"""
        pass
    
    @abstractmethod
    async def extract_manuscripts(self) -> List[Manuscript]:
        """Extract all manuscripts under review"""
        pass
    
    @abstractmethod
    async def extract_referee_details(self, manuscript: Manuscript) -> List[Review]:
        """Extract referee details for a specific manuscript"""
        pass
    
    @abstractmethod
    async def download_manuscript_pdf(self, manuscript: Manuscript) -> Optional[str]:
        """Download manuscript PDF and return file path"""
        pass
    
    @abstractmethod
    async def download_review_pdf(self, review: Review) -> Optional[str]:
        """Download review report PDF and return file path"""
        pass


class ManuscriptRepository(ABC):
    """Port for manuscript persistence"""
    
    @abstractmethod
    async def save(self, manuscript: Manuscript) -> None:
        """Save or update a manuscript"""
        pass
    
    @abstractmethod
    async def get(self, manuscript_id: UUID) -> Optional[Manuscript]:
        """Get manuscript by ID"""
        pass
    
    @abstractmethod
    async def get_by_external_id(self, journal_code: str, external_id: str) -> Optional[Manuscript]:
        """Get manuscript by journal and external ID"""
        pass
    
    @abstractmethod
    async def find_by_journal(self, journal_code: str) -> List[Manuscript]:
        """Find all manuscripts for a journal"""
        pass
    
    @abstractmethod
    async def find_active(self, journal_code: Optional[str] = None) -> List[Manuscript]:
        """Find all active manuscripts"""
        pass


class RefereeRepository(ABC):
    """Port for referee persistence"""
    
    @abstractmethod
    async def save(self, referee: Referee) -> None:
        """Save or update a referee"""
        pass
    
    @abstractmethod
    async def get(self, referee_id: UUID) -> Optional[Referee]:
        """Get referee by ID"""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[Referee]:
        """Get referee by email address"""
        pass
    
    @abstractmethod
    async def find_by_expertise(self, expertise_areas: List[str]) -> List[Referee]:
        """Find referees by expertise areas"""
        pass
    
    @abstractmethod
    async def get_statistics(self, referee_id: UUID) -> RefereeStatistics:
        """Get aggregated statistics for a referee"""
        pass


class ReviewRepository(ABC):
    """Port for review persistence"""
    
    @abstractmethod
    async def save(self, review: Review) -> None:
        """Save or update a review"""
        pass
    
    @abstractmethod
    async def get(self, review_id: UUID) -> Optional[Review]:
        """Get review by ID"""
        pass
    
    @abstractmethod
    async def find_by_manuscript(self, manuscript_id: UUID) -> List[Review]:
        """Find all reviews for a manuscript"""
        pass
    
    @abstractmethod
    async def find_by_referee(self, referee_id: UUID) -> List[Review]:
        """Find all reviews by a referee"""
        pass
    
    @abstractmethod
    async def find_pending(self, journal_code: Optional[str] = None) -> List[Review]:
        """Find all pending reviews"""
        pass


class NotificationService(ABC):
    """Port for sending notifications"""
    
    @abstractmethod
    async def send_referee_invitation(self, referee: Referee, manuscript: Manuscript) -> bool:
        """Send referee invitation email"""
        pass
    
    @abstractmethod
    async def send_reminder(self, review: Review) -> bool:
        """Send review reminder"""
        pass
    
    @abstractmethod
    async def send_digest(self, recipient: str, digest_data: Dict[str, Any]) -> bool:
        """Send weekly digest email"""
        pass


class AIAnalysisService(ABC):
    """Port for AI-powered analysis"""
    
    @abstractmethod
    async def analyze_manuscript_quality(self, manuscript: Manuscript) -> Dict[str, Any]:
        """Analyze manuscript quality and provide recommendations"""
        pass
    
    @abstractmethod
    async def suggest_referees(self, manuscript: Manuscript, pool: List[Referee]) -> List[tuple[Referee, float]]:
        """Suggest best referee matches with confidence scores"""
        pass
    
    @abstractmethod
    async def predict_review_timeline(self, referee: Referee, workload: int) -> Dict[str, Any]:
        """Predict review completion timeline"""
        pass
    
    @abstractmethod
    async def analyze_review_quality(self, review: Review) -> Dict[str, Any]:
        """Analyze review report quality"""
        pass


class CacheService(ABC):
    """Port for caching"""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL"""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache"""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern, return count deleted"""
        pass


class MetricsService(ABC):
    """Port for metrics collection"""
    
    @abstractmethod
    async def record_extraction(self, result: ExtractionResult) -> None:
        """Record extraction metrics"""
        pass
    
    @abstractmethod
    async def record_api_call(self, endpoint: str, duration_ms: float, status_code: int) -> None:
        """Record API call metrics"""
        pass
    
    @abstractmethod
    async def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric"""
        pass
    
    @abstractmethod
    async def record_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric"""
        pass