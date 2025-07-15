"""
Unified Extraction Contract System

Defines standard interfaces and data models for all journal extractors,
ensuring consistent data extraction and quality validation.
"""

from .extraction_contract import ExtractionContract, ExtractionMetadata
from .validation import ValidationResult, QualityValidator
from .models import (
    ExtractionResult, 
    QualityScore,
    ExtractionStatus,
    DataQualityMetrics
)

__all__ = [
    'ExtractionContract',
    'ExtractionMetadata', 
    'ValidationResult',
    'QualityValidator',
    'ExtractionResult',
    'QualityScore',
    'ExtractionStatus',
    'DataQualityMetrics'
]