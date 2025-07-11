"""
PDF Processor Port (Interface)
Defines the contract for PDF content extraction and processing
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class PDFProcessor(ABC):
    """Abstract interface for PDF content extraction"""
    
    @abstractmethod
    async def extract_text_content(self, pdf_path: Path) -> Dict[str, str]:
        """
        Extract text content from PDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted content:
            - 'title': Document title
            - 'abstract': Abstract or summary
            - 'full_text': Complete text content
            - 'sections': Section-wise content
        """
        pass
    
    @abstractmethod
    async def extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract document metadata from PDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with document metadata:
            - 'title': Document title
            - 'authors': List of authors
            - 'keywords': List of keywords
            - 'creation_date': Document creation date
            - 'page_count': Number of pages
            - 'file_size': File size in bytes
        """
        pass
    
    @abstractmethod
    async def extract_figures_and_tables(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract figures and tables from PDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with extracted visual elements:
            - 'figures': List of figure descriptions/captions
            - 'tables': List of table data
            - 'equations': List of mathematical equations
        """
        pass
    
    @abstractmethod
    async def get_content_hash(self, pdf_path: Path) -> str:
        """
        Generate content hash for caching and duplicate detection
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            SHA-256 hash of the document content
        """
        pass
    
    @abstractmethod
    async def validate_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Validate PDF file and assess extraction quality
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dictionary with validation results:
            - 'is_valid': Boolean indicating if PDF is valid
            - 'is_readable': Boolean indicating if text can be extracted
            - 'quality_score': Float 0-1 indicating extraction quality
            - 'issues': List of any issues found
            - 'recommendations': List of recommendations for better processing
        """
        pass