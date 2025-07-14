"""
Editorial Scripts Journal Implementations
Consolidated journal extractors with clean architecture
"""

from typing import Dict, Type
from abc import ABC

# Import journal implementations when ready
journal_registry: Dict[str, Type[ABC]] = {}

def register_journal(code: str, implementation: Type[ABC]):
    """Register a journal implementation"""
    journal_registry[code.upper()] = implementation

def get_journal(code: str) -> Type[ABC]:
    """Get journal implementation by code"""
    return journal_registry.get(code.upper())

__all__ = ['register_journal', 'get_journal', 'journal_registry']