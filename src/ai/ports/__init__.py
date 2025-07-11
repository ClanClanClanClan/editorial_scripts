"""
AI Service Ports (Interfaces)
Define contracts for AI-powered analysis services
"""

from .manuscript_analyzer import ManuscriptAnalyzer
from .pdf_processor import PDFProcessor
from .ai_client import AIClient

__all__ = [
    'ManuscriptAnalyzer',
    'PDFProcessor', 
    'AIClient'
]