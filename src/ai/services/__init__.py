"""
AI Services Layer - Dependency injection and service configuration
"""

from .async_openai_client import AsyncOpenAIClient
from .ai_orchestrator_service import AIOrchestrator
from .openai_manuscript_analyzer import OpenAIManuscriptAnalyzer
from .pypdf_processor import PyPDFProcessor
from .openai_client import OpenAIClient
from ..ports.ai_client import AIClient, AIModel
from ..ports.pdf_processor import PDFProcessor

__all__ = [
    'AsyncOpenAIClient',
    'AIOrchestrator', 
    'AIClient',
    'AIModel',
    'PDFProcessor',
    'OpenAIManuscriptAnalyzer',
    'PyPDFProcessor',
    'OpenAIClient',
    'create_ai_client',
    'create_ai_orchestrator'
]


def create_ai_client(
    openai_api_key: str = None,
    model: str = "gpt-4-turbo"
) -> AIClient:
    """
    Factory function to create AI client
    """
    return AsyncOpenAIClient(api_key=openai_api_key, model=model)


def create_pdf_processor() -> PDFProcessor:
    """
    Factory function to create PDF processor
    """
    return PyPDFProcessor()


def create_ai_orchestrator(
    openai_api_key: str = None,
    cache_enabled: bool = True
) -> AIOrchestrator:
    """
    Factory function to create AI orchestrator with all dependencies
    """
    ai_client = create_ai_client(openai_api_key)
    pdf_processor = create_pdf_processor()
    
    return AIOrchestrator(
        ai_client=ai_client,
        pdf_processor=pdf_processor,
        cache_enabled=cache_enabled
    )