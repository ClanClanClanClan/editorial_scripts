"""Platform-specific base extractors."""

from .scholarone import ScholarOneExtractor

# from .siam import SIAMExtractor
# from .editorial_manager import EditorialManagerExtractor
# from .email_based import EmailBasedExtractor

__all__ = [
    "ScholarOneExtractor",
    # 'SIAMExtractor',
    # 'EditorialManagerExtractor',
    # 'EmailBasedExtractor'
]
