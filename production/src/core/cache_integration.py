#!/usr/bin/env python3
"""
CACHE INTEGRATION MODULE FOR EXTRACTORS
=======================================

Provides easy integration of the comprehensive cache system into extractors.
Handles both test and production modes automatically.
"""

import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Import cache components
from .cache_manager import ExtractorCacheMixin


class CachedExtractorMixin(ExtractorCacheMixin):
    """
    Enhanced mixin that integrates comprehensive caching into any extractor.

    Features:
    - Automatic test/production mode detection
    - Safe download directory management
    - Global referee database
    - Institution and country caching
    - Manuscript change detection
    """

    def init_cached_extractor(self, journal_name: str):
        """Initialize the extractor with comprehensive caching."""
        # Initialize cache (auto-detects test mode)
        self.init_cache(journal_name)

        # Store journal name for later use
        self.journal_name = journal_name

        print(f"✅ Initialized {journal_name} with comprehensive caching")
        print(f"   Mode: {'🧪 TEST' if self.cache_manager.test_mode else '🚨 PRODUCTION'}")
        print(f"   Cache: {self.cache_manager.cache_dir}")

    def get_safe_download_dir(self, subdir=""):
        """Get download directory that respects test/production mode."""
        journal_name = getattr(self, "journal_name", "UNKNOWN")
        date_str = datetime.now().strftime("%Y%m%d")

        if self.cache_manager.test_mode:
            # In test mode, use cache directory for downloads
            download_path = (
                self.cache_manager.cache_dir / "downloads" / journal_name / date_str / subdir
            )
        else:
            # In production, use standard location
            project_root = getattr(self, "project_root", Path.cwd())
            download_path = project_root / "data" / journal_name / date_str / subdir

        download_path.mkdir(parents=True, exist_ok=True)
        return download_path

    def infer_institution_from_email_cached(self, email_domain):
        """
        Get institution from email domain using cache.
        Replaces _domain_institution_cache with persistent storage.
        """
        # Check cache first
        cached_result = self.cache_manager.get_institution_from_domain(email_domain)
        if cached_result:
            institution, country = cached_result
            print(f"         📚 Cache hit: {email_domain} → {institution}")
            return institution

        # If not in cache, use existing inference logic
        # This should call the original infer_institution_from_email_domain
        if hasattr(self, "infer_institution_from_email_domain"):
            inferred = self.infer_institution_from_email_domain(email_domain)

            # Cache the result
            if inferred and inferred != "Unknown Institution":
                # Try to get country too if we have the method
                country = ""
                if hasattr(self, "infer_country_from_web_search"):
                    country = self.infer_country_from_web_search(inferred) or ""

                self.cache_manager.cache_institution(email_domain, inferred, country)
                print(f"         💾 Cached: {email_domain} → {inferred}")

            return inferred

        return "Unknown Institution"

    def get_cached_referee_info(self, email):
        """Get referee info from cache or create new entry."""
        return self.get_cached_referee_data(email)

    def update_referee_cache(self, referee_data):
        """Update referee information in cache."""
        return self.cache_manager.update_referee(referee_data, self.journal_name)

    def should_process_manuscript(self, manuscript_id, status=None, last_updated=None):
        """Check if manuscript needs processing based on cache."""
        return self.should_extract_manuscript(manuscript_id, status, last_updated)

    def cache_manuscript(self, manuscript_data):
        """Cache manuscript data after extraction."""
        self.cache_manuscript_data(manuscript_data)

    def _check_existing_download(
        self, manuscript_id: str, doc_type: str, download_dir: str
    ) -> Optional[str]:
        pattern = os.path.join(download_dir, f"{manuscript_id}*{doc_type}*")
        matches = glob.glob(pattern)
        if not matches:
            pattern_alt = os.path.join(download_dir, f"*{manuscript_id}*")
            matches = [
                m for m in glob.glob(pattern_alt) if doc_type.lower() in os.path.basename(m).lower()
            ]
        if not matches:
            safe_id = manuscript_id.replace("-", "_").replace(".", "_")
            pattern_safe = os.path.join(download_dir, f"*{safe_id}*")
            matches = [
                m
                for m in glob.glob(pattern_safe)
                if doc_type.lower() in os.path.basename(m).lower()
            ]
        if matches:
            newest = max(matches, key=os.path.getmtime)
            if os.path.getsize(newest) > 0:
                return newest
        return None

    def get_cached_web_profile(
        self, name: str, institution: str = "", orcid_id: str = ""
    ) -> Optional[Dict]:
        if not hasattr(self, "cache_manager"):
            return None
        if orcid_id:
            result = self.cache_manager.get_web_profile(orcid_id)
            if result:
                return result
        name_key = f"{name.strip().lower()}|{institution.strip().lower()}"
        return self.cache_manager.get_web_profile(name_key)

    def save_web_profile(
        self,
        name: str,
        institution: str,
        orcid_id: str,
        profile_data: Dict,
        source: str = "orcid+crossref",
    ):
        if not hasattr(self, "cache_manager"):
            return
        key = orcid_id if orcid_id else f"{name.strip().lower()}|{institution.strip().lower()}"
        if orcid_id:
            name_key = f"{name.strip().lower()}|{institution.strip().lower()}"
            try:
                import sqlite3

                with sqlite3.connect(self.cache_manager.db_path) as conn:
                    conn.execute("DELETE FROM web_profiles WHERE person_key = ?", (name_key,))
                    conn.commit()
            except Exception:
                pass
        self.cache_manager.update_web_profile(key, name, orcid_id, profile_data, source)

    def finish_extraction_with_stats(self):
        """Finish extraction and show comprehensive statistics."""
        self.finish_extraction()
