"""
Journal Extractor Port (Interface)
Defines the contract for journal data extraction
"""

from abc import ABC, abstractmethod
from typing import List

from ..domain.models import Manuscript


class JournalExtractor(ABC):
    """Abstract interface for journal manuscript extraction"""
    
    @abstractmethod
    async def extract_manuscripts(self) -> List[Manuscript]:
        """Extract manuscripts and referee data from journal platform"""
        pass