"""
Unified Authentication Architecture for Editorial Assistant

This module provides a single, consistent authentication interface
that supports all journal platforms while eliminating code duplication.
"""

from .base import AuthenticationProvider
from .editorial_manager_auth import EditorialManagerAuth
from .orcid_auth import ORCIDAuth
from .scholarone_auth import ScholarOneAuth

__all__ = ["AuthenticationProvider", "ORCIDAuth", "ScholarOneAuth", "EditorialManagerAuth"]
