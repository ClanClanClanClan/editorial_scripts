"""
Unified Extraction Contract System

Defines standard interfaces and data models for all journal extractors,
ensuring consistent data extraction and quality validation.
"""

from .extraction_contract import ExtractionContract, ExtractionMetadata
from .models import DataQualityMetrics, ExtractionResult, ExtractionStatus, QualityScore
from .validation import QualityValidator, ValidationResult

__all__ = [
    "ExtractionContract",
    "ExtractionMetadata",
    "ValidationResult",
    "QualityValidator",
    "ExtractionResult",
    "QualityScore",
    "ExtractionStatus",
    "DataQualityMetrics",
]
