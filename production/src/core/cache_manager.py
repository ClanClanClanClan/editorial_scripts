#!/usr/bin/env python3
"""
COMPREHENSIVE CACHING SYSTEM FOR EDITORIAL EXTRACTORS
=====================================================

This module provides a foolproof caching system that:
1. Works across all journal extractors (MF, MOR, SICON, etc.)
2. Persists data between runs
3. Intelligently detects changes
4. Manages referee profiles globally
5. Provides incremental extraction capabilities
"""

import hashlib
import json
import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


@dataclass
class CachedReferee:
    """Global referee profile that persists across journals."""

    email: str
    name: str
    institution: str
    department: str = ""
    country: str = ""
    orcid: str = ""
    last_seen: str = ""  # ISO format datetime
    last_updated: str = ""  # ISO format datetime
    journals_seen: list[str] = None  # List of journals where this referee appears
    affiliations_history: list[dict[str, str]] = None  # Track affiliation changes

    def __post_init__(self):
        if self.journals_seen is None:
            self.journals_seen = []
        if self.affiliations_history is None:
            self.affiliations_history = []
        if not self.last_updated:
            self.last_updated = datetime.now().isoformat()


@dataclass
class CachedManuscript:
    """Cached manuscript data with change tracking."""

    manuscript_id: str
    journal: str
    title: str
    status: str
    authors: list[str]
    submission_date: str
    last_updated: str
    extraction_date: str
    data_hash: str  # Hash of key fields to detect changes
    referee_count: int
    has_version_history: bool
    full_data: dict[str, Any]  # Complete manuscript data


class CacheManager:
    """Comprehensive cache manager for editorial extractors."""

    def __init__(self, cache_dir: Path = None, test_mode: bool = None):
        """Initialize cache manager with persistent storage."""
        # Auto-detect test mode if not specified
        if test_mode is None:
            test_mode = self._is_test_environment()

        # SAFETY CHECK: If we detect ANY test indicators, force test mode
        # This prevents production pollution even if test_mode=False is explicitly passed
        detected_test_env = self._is_test_environment()
        if detected_test_env and not test_mode:
            print(
                "🛡️ SAFETY OVERRIDE: Test environment detected, forcing test mode to prevent production pollution"
            )
            test_mode = True

        self.test_mode = test_mode

        if test_mode:
            # Use temporary directory for tests
            import tempfile

            self.cache_dir = Path(tempfile.mkdtemp(prefix="editorial_test_cache_"))
            print(f"🧪 TEST MODE: Using temporary cache at: {self.cache_dir}")
        else:
            if cache_dir is None:
                # Default to project root cache directory
                self.cache_dir = Path(__file__).parent.parent.parent / "cache"
            else:
                self.cache_dir = Path(cache_dir)
            print(f"✅ PRODUCTION MODE: Cache initialized at: {self.cache_dir}")

        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # SQLite database for structured data
        db_name = "editorial_cache_test.db" if test_mode else "editorial_cache.db"
        self.db_path = self.cache_dir / db_name
        self._init_database()

        # Thread lock for database access
        self.lock = threading.Lock()

        # Track database connections for cleanup
        self._db_connections = []

        # In-memory cache for current session
        self.session_cache = {
            "referees": {},
            "manuscripts": {},
            "institutions": {},
            "countries": {},
        }

    def _is_test_environment(self) -> bool:
        """Auto-detect if running in test environment."""
        import os
        import sys

        try:
            # Check common test indicators
            test_indicators = [
                "pytest" in sys.modules,
                "unittest" in sys.modules,
                os.environ.get("TESTING") == "1",
                os.environ.get("PYTEST_CURRENT_TEST") is not None,
            ]

            # Check script name safely
            if len(sys.argv) > 0 and sys.argv[0]:
                script_name = str(sys.argv[0]).lower()
                test_indicators.append("test" in script_name)

            # Check arguments safely
            test_indicators.append(any("test" in str(arg).lower() for arg in sys.argv if arg))

            # Check if we're in dev/ directory (development isolation)
            current_path = str(Path.cwd())
            file_path = str(Path(__file__))
            test_indicators.extend(
                ["/dev/" in current_path, current_path.endswith("/dev"), "/dev/" in file_path]
            )

            # Additional safety: Check the call stack for test-related code
            import inspect

            try:
                frame = inspect.currentframe()
                while frame:
                    frame_filename = frame.f_code.co_filename
                    if frame_filename != __file__:  # Skip our own file
                        # Check if called from dev/ directory or test files
                        if (
                            "/dev/" in frame_filename
                            or "test" in frame_filename.lower()
                            or "editorial_scripts" in frame_filename
                        ):
                            test_indicators.append(True)
                            break
                    frame = frame.f_back
            except:
                pass  # Ignore errors in stack inspection

            # CRITICAL SAFETY: Check if we're in editorial_scripts project directory
            # This prevents ANY cache creation within the project during development
            project_indicators = [
                "editorial_scripts" in str(Path(__file__).resolve()),
                "editorial_scripts" in current_path,
                str(Path(__file__).resolve()).endswith(
                    "editorial_scripts/production/src/core/cache_manager.py"
                ),
            ]

            # If we're in the editorial_scripts project, default to test mode for safety
            # unless explicitly overridden with a special environment variable
            if any(project_indicators) and not os.environ.get("EDITORIAL_FORCE_PRODUCTION_MODE"):
                test_indicators.append(True)

            return any(test_indicators)
        except Exception:
            # If detection fails, default to False (production mode)
            return False

    def cleanup_test_cache(self):
        """Clean up test cache directory (only in test mode)."""
        if not self.test_mode:
            return

        try:
            # Close any open database connections first
            if hasattr(self, "_db_connections"):
                for conn in self._db_connections:
                    try:
                        conn.close()
                    except:
                        pass

            # Wait a moment for any pending operations
            import time

            time.sleep(0.1)

            # Remove the cache directory
            if self.cache_dir.exists():
                import shutil

                # Use error handler to deal with permission issues
                def handle_remove_readonly(func, path, exc):
                    import os
                    import stat

                    if os.path.exists(path):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)

                shutil.rmtree(self.cache_dir, onerror=handle_remove_readonly)
                print(f"🧹 Cleaned up test cache: {self.cache_dir}")
        except Exception as e:
            print(f"⚠️ Warning: Could not fully cleanup test cache: {e}")

    def __del__(self):
        """Automatic cleanup when object is destroyed."""
        try:
            self.cleanup_test_cache()
        except:
            pass  # Ignore errors during destruction

    def _init_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Referee profiles table (global across journals)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS referees (
                    email TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    institution TEXT,
                    department TEXT,
                    country TEXT,
                    orcid TEXT,
                    last_seen TEXT,
                    last_updated TEXT,
                    journals_seen TEXT,  -- JSON array
                    affiliations_history TEXT,  -- JSON array
                    data_hash TEXT
                )
            """
            )

            # Manuscript cache table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS manuscripts (
                    manuscript_id TEXT,
                    journal TEXT,
                    title TEXT,
                    status TEXT,
                    authors TEXT,  -- JSON array
                    submission_date TEXT,
                    last_updated TEXT,
                    extraction_date TEXT,
                    data_hash TEXT,
                    referee_count INTEGER,
                    has_version_history BOOLEAN,
                    full_data TEXT,  -- JSON object
                    PRIMARY KEY (manuscript_id, journal)
                )
            """
            )

            # Institution lookups
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS institutions (
                    domain TEXT PRIMARY KEY,
                    institution_name TEXT,
                    country TEXT,
                    last_updated TEXT
                )
            """
            )

            # Referee performance cache (v1.0 spec compliance)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS referee_performance_cache (
                    referee_email TEXT PRIMARY KEY,
                    metrics TEXT NOT NULL,  -- JSON in SQLite, JSONB in PostgreSQL
                    calculated_at TEXT NOT NULL,
                    valid_until TEXT NOT NULL
                )
            """
            )

            # Journal statistics (v1.0 spec compliance)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS journal_statistics (
                    journal_id TEXT,
                    period_start TEXT,  -- DATE in SQLite as TEXT
                    period_end TEXT,
                    total_submissions INTEGER,
                    average_review_time REAL,
                    acceptance_rate REAL,
                    desk_rejection_rate REAL,
                    PRIMARY KEY (journal_id, period_start, period_end)
                )
            """
            )

            # Extraction runs metadata
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS extraction_runs (
                    run_id TEXT PRIMARY KEY,
                    journal TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    manuscripts_extracted INTEGER,
                    new_manuscripts INTEGER,
                    updated_manuscripts INTEGER,
                    new_referees INTEGER,
                    errors INTEGER,
                    metadata TEXT  -- JSON object
                )
            """
            )

            conn.commit()

    def _compute_data_hash(self, data: dict[str, Any], fields: list[str]) -> str:
        """Compute hash of specific fields to detect changes."""
        hash_data = {k: data.get(k, "") for k in fields}
        hash_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.md5(hash_string.encode(), usedforsecurity=False).hexdigest()

    # REFEREE CACHING METHODS

    def get_referee(self, email: str) -> CachedReferee | None:
        """Get cached referee profile."""
        with self.lock:
            # Check session cache first
            if email in self.session_cache["referees"]:
                return self.session_cache["referees"][email]

            # Check database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM referees WHERE email = ?", (email,))
                row = cursor.fetchone()

                if row:
                    referee = CachedReferee(
                        email=row[0],
                        name=row[1],
                        institution=row[2] or "",
                        department=row[3] or "",
                        country=row[4] or "",
                        orcid=row[5] or "",
                        last_seen=row[6] or "",
                        last_updated=row[7] or "",
                        journals_seen=json.loads(row[8] or "[]"),
                        affiliations_history=json.loads(row[9] or "[]"),
                    )
                    self.session_cache["referees"][email] = referee
                    return referee

                return None

    def update_referee(self, referee_data: dict[str, Any], journal: str) -> CachedReferee:
        """Update or create referee profile with intelligent merging."""
        email = referee_data.get("email", "").lower().strip()
        if not email:
            return None

        with self.lock:
            # Get existing referee or create new
            existing = self.get_referee(email)

            if existing:
                # Check for changes in key fields
                changed = False

                # Update name if provided and different
                new_name = referee_data.get("name", "").strip()
                if new_name and new_name != existing.name:
                    existing.name = new_name
                    changed = True

                # Track affiliation changes
                new_institution = referee_data.get("institution", "").strip()
                if new_institution and new_institution != existing.institution:
                    # Add to history
                    existing.affiliations_history.append(
                        {
                            "institution": existing.institution,
                            "department": existing.department,
                            "date": existing.last_updated,
                            "journal": journal,
                        }
                    )
                    existing.institution = new_institution
                    existing.department = referee_data.get("department", "")
                    changed = True

                # Update country if provided
                new_country = referee_data.get("country", "").strip()
                if new_country and new_country != existing.country:
                    existing.country = new_country
                    changed = True

                # Update ORCID if provided
                new_orcid = referee_data.get("orcid", "").strip()
                if new_orcid and new_orcid != existing.orcid:
                    existing.orcid = new_orcid
                    changed = True

                # Update journals seen
                if journal not in existing.journals_seen:
                    existing.journals_seen.append(journal)
                    changed = True

                # Update timestamps
                existing.last_seen = datetime.now().isoformat()
                if changed:
                    existing.last_updated = datetime.now().isoformat()

                referee = existing
            else:
                # Create new referee
                referee = CachedReferee(
                    email=email,
                    name=referee_data.get("name", ""),
                    institution=referee_data.get("institution", ""),
                    department=referee_data.get("department", ""),
                    country=referee_data.get("country", ""),
                    orcid=referee_data.get("orcid", ""),
                    last_seen=datetime.now().isoformat(),
                    last_updated=datetime.now().isoformat(),
                    journals_seen=[journal],
                    affiliations_history=[],
                )

            # Save to database
            self._save_referee(referee)

            # Update session cache
            self.session_cache["referees"][email] = referee

            return referee

    def _save_referee(self, referee: CachedReferee):
        """Save referee to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Compute data hash for change detection
            data_hash = self._compute_data_hash(
                asdict(referee), ["name", "institution", "department", "country", "orcid"]
            )

            cursor.execute(
                """
                INSERT OR REPLACE INTO referees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    referee.email,
                    referee.name,
                    referee.institution,
                    referee.department,
                    referee.country,
                    referee.orcid,
                    referee.last_seen,
                    referee.last_updated,
                    json.dumps(referee.journals_seen),
                    json.dumps(referee.affiliations_history),
                    data_hash,
                ),
            )
            conn.commit()

    # MANUSCRIPT CACHING METHODS

    def get_manuscript(self, manuscript_id: str, journal: str) -> CachedManuscript | None:
        """Get cached manuscript data."""
        with self.lock:
            cache_key = f"{journal}:{manuscript_id}"

            # Check session cache
            if cache_key in self.session_cache["manuscripts"]:
                return self.session_cache["manuscripts"][cache_key]

            # Check database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM manuscripts WHERE manuscript_id = ? AND journal = ?",
                    (manuscript_id, journal),
                )
                row = cursor.fetchone()

                if row:
                    manuscript = CachedManuscript(
                        manuscript_id=row[0],
                        journal=row[1],
                        title=row[2],
                        status=row[3],
                        authors=json.loads(row[4] or "[]"),
                        submission_date=row[5],
                        last_updated=row[6],
                        extraction_date=row[7],
                        data_hash=row[8],
                        referee_count=row[9],
                        has_version_history=bool(row[10]),
                        full_data=json.loads(row[11] or "{}"),
                    )
                    self.session_cache["manuscripts"][cache_key] = manuscript
                    return manuscript

                return None

    def should_update_manuscript(
        self, manuscript_id: str, journal: str, status: str = None, last_updated: str = None
    ) -> bool:
        """Determine if manuscript needs updating based on cached data."""
        cached = self.get_manuscript(manuscript_id, journal)

        if not cached:
            return True  # Not in cache, needs extraction

        # Check if status changed
        if status and status != cached.status:
            print(f"   📝 Status changed: {cached.status} → {status}")
            return True

        # Check if last_updated changed
        if last_updated and last_updated != cached.last_updated:
            print(f"   📝 Updated date changed: {cached.last_updated} → {last_updated}")
            return True

        # Check cache age (configurable, default 7 days for completed, 1 day for active)
        cache_age = datetime.now() - datetime.fromisoformat(cached.extraction_date)

        if status and "complete" in status.lower():
            max_age = timedelta(days=30)  # Completed manuscripts rarely change
        else:
            max_age = timedelta(days=1)  # Active manuscripts need frequent updates

        if cache_age > max_age:
            print(f"   📝 Cache expired: {cache_age.days} days old")
            return True

        print(f"   ✅ Using cached data (age: {cache_age.days} days)")
        return False

    def update_manuscript(self, manuscript_data: dict[str, Any], journal: str) -> CachedManuscript:
        """Update or create manuscript cache entry."""
        manuscript_id = manuscript_data.get("id", "")
        if not manuscript_id:
            return None

        with self.lock:
            # Compute data hash for change detection
            key_fields = ["title", "status", "authors", "referees"]
            data_hash = self._compute_data_hash(manuscript_data, key_fields)

            # Create cached manuscript
            manuscript = CachedManuscript(
                manuscript_id=manuscript_id,
                journal=journal,
                title=manuscript_data.get("title", ""),
                status=manuscript_data.get("status", ""),
                authors=manuscript_data.get("authors", []),
                submission_date=manuscript_data.get("submission_date", ""),
                last_updated=manuscript_data.get("last_updated", ""),
                extraction_date=datetime.now().isoformat(),
                data_hash=data_hash,
                referee_count=len(manuscript_data.get("referees", [])),
                has_version_history=manuscript_data.get("has_version_history", False),
                full_data=manuscript_data,
            )

            # Save to database
            self._save_manuscript(manuscript)

            # Update session cache
            cache_key = f"{journal}:{manuscript_id}"
            self.session_cache["manuscripts"][cache_key] = manuscript

            return manuscript

    def _save_manuscript(self, manuscript: CachedManuscript):
        """Save manuscript to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO manuscripts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    manuscript.manuscript_id,
                    manuscript.journal,
                    manuscript.title,
                    manuscript.status,
                    json.dumps(manuscript.authors),
                    manuscript.submission_date,
                    manuscript.last_updated,
                    manuscript.extraction_date,
                    manuscript.data_hash,
                    manuscript.referee_count,
                    manuscript.has_version_history,
                    json.dumps(manuscript.full_data),
                ),
            )
            conn.commit()

    # INSTITUTION CACHING

    def get_institution_from_domain(self, domain: str) -> tuple[str, str] | None:
        """Get cached institution name and country from email domain."""
        with self.lock:
            # Check session cache
            if domain in self.session_cache["institutions"]:
                return self.session_cache["institutions"][domain]

            # Check database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT institution_name, country FROM institutions WHERE domain = ?", (domain,)
                )
                row = cursor.fetchone()

                if row:
                    result = (row[0], row[1])
                    self.session_cache["institutions"][domain] = result
                    return result

                return None

    def cache_institution(self, domain: str, institution_name: str, country: str = ""):
        """Cache institution lookup result."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO institutions VALUES (?, ?, ?, ?)
                """,
                    (domain, institution_name, country, datetime.now().isoformat()),
                )
                conn.commit()

            # Update session cache
            self.session_cache["institutions"][domain] = (institution_name, country)

    # REFEREE PERFORMANCE CACHING (V1.0 SPEC COMPLIANCE)

    def cache_referee_performance(
        self, referee_email: str, metrics: dict[str, Any], validity_hours: int = 24
    ):
        """Cache referee performance metrics as per v1.0 specifications."""
        with self.lock:
            valid_until = (datetime.now() + timedelta(hours=validity_hours)).isoformat()

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO referee_performance_cache
                    VALUES (?, ?, ?, ?)
                """,
                    (referee_email, json.dumps(metrics), datetime.now().isoformat(), valid_until),
                )
                conn.commit()

    def get_referee_performance(self, referee_email: str) -> dict[str, Any] | None:
        """Get cached referee performance metrics."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT metrics, calculated_at, valid_until
                    FROM referee_performance_cache
                    WHERE referee_email = ?
                """,
                    (referee_email,),
                )
                row = cursor.fetchone()

                if row:
                    metrics_json, calculated_at, valid_until = row

                    # Check if still valid
                    if datetime.now() < datetime.fromisoformat(valid_until):
                        return {
                            "metrics": json.loads(metrics_json),
                            "calculated_at": calculated_at,
                            "valid_until": valid_until,
                        }
                    else:
                        # Remove expired entry
                        cursor.execute(
                            """
                            DELETE FROM referee_performance_cache
                            WHERE referee_email = ?
                        """,
                            (referee_email,),
                        )
                        conn.commit()

                return None

    # JOURNAL STATISTICS CACHING (V1.0 SPEC COMPLIANCE)

    def cache_journal_statistics(
        self, journal_id: str, period_start: str, period_end: str, stats: dict[str, Any]
    ):
        """Cache journal statistics as per v1.0 specifications."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO journal_statistics
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        journal_id,
                        period_start,
                        period_end,
                        stats.get("total_submissions", 0),
                        stats.get("average_review_time", 0.0),
                        stats.get("acceptance_rate", 0.0),
                        stats.get("desk_rejection_rate", 0.0),
                    ),
                )
                conn.commit()

    def get_journal_statistics(
        self, journal_id: str, period_start: str = None, period_end: str = None
    ) -> list[dict[str, Any]]:
        """Get cached journal statistics."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                if period_start and period_end:
                    cursor.execute(
                        """
                        SELECT * FROM journal_statistics
                        WHERE journal_id = ? AND period_start = ? AND period_end = ?
                    """,
                        (journal_id, period_start, period_end),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT * FROM journal_statistics
                        WHERE journal_id = ?
                        ORDER BY period_start DESC
                    """,
                        (journal_id,),
                    )

                rows = cursor.fetchall()

                return [
                    {
                        "journal_id": row[0],
                        "period_start": row[1],
                        "period_end": row[2],
                        "total_submissions": row[3],
                        "average_review_time": row[4],
                        "acceptance_rate": row[5],
                        "desk_rejection_rate": row[6],
                    }
                    for row in rows
                ]

    # EXTRACTION RUN TRACKING

    def start_extraction_run(self, journal: str) -> str:
        """Start a new extraction run and return run ID."""
        run_id = f"{journal}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO extraction_runs
                (run_id, journal, start_time, manuscripts_extracted, new_manuscripts,
                 updated_manuscripts, new_referees, errors)
                VALUES (?, ?, ?, 0, 0, 0, 0, 0)
            """,
                (run_id, journal, datetime.now().isoformat()),
            )
            conn.commit()

        return run_id

    def update_extraction_stats(self, run_id: str, stats: dict[str, int]):
        """Update extraction run statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE extraction_runs
                SET manuscripts_extracted = ?,
                    new_manuscripts = ?,
                    updated_manuscripts = ?,
                    new_referees = ?,
                    errors = ?
                WHERE run_id = ?
            """,
                (
                    stats.get("manuscripts_extracted", 0),
                    stats.get("new_manuscripts", 0),
                    stats.get("updated_manuscripts", 0),
                    stats.get("new_referees", 0),
                    stats.get("errors", 0),
                    run_id,
                ),
            )
            conn.commit()

    def finish_extraction_run(self, run_id: str, metadata: dict[str, Any] = None):
        """Finish extraction run and save metadata."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE extraction_runs
                SET end_time = ?, metadata = ?
                WHERE run_id = ?
            """,
                (datetime.now().isoformat(), json.dumps(metadata or {}), run_id),
            )
            conn.commit()

    # CACHE ANALYSIS METHODS

    def get_cache_statistics(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # Referee statistics
            cursor.execute("SELECT COUNT(*) FROM referees")
            stats["total_referees"] = cursor.fetchone()[0]

            cursor.execute(
                'SELECT COUNT(DISTINCT institution) FROM referees WHERE institution != ""'
            )
            stats["unique_institutions"] = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(DISTINCT country) FROM referees WHERE country != ""')
            stats["unique_countries"] = cursor.fetchone()[0]

            # Manuscript statistics
            cursor.execute("SELECT COUNT(*) FROM manuscripts")
            stats["total_manuscripts"] = cursor.fetchone()[0]

            cursor.execute("SELECT journal, COUNT(*) FROM manuscripts GROUP BY journal")
            stats["manuscripts_by_journal"] = dict(cursor.fetchall())

            # Recent extractions
            cursor.execute(
                """
                SELECT journal, start_time, manuscripts_extracted
                FROM extraction_runs
                ORDER BY start_time DESC
                LIMIT 10
            """
            )
            stats["recent_extractions"] = [
                {"journal": row[0], "date": row[1], "count": row[2]} for row in cursor.fetchall()
            ]

            # Cache size
            stats["cache_size_mb"] = self.db_path.stat().st_size / (1024 * 1024)

            return stats

    # SPECIFICATION-COMPLIANT METHODS (v1.0)

    def update_referee_performance_metrics(
        self, referee_email: str, metrics: dict[str, Any], valid_hours: int = 24
    ):
        """Update referee performance metrics cache (spec lines 589-594)."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                now = datetime.now()
                valid_until = now + timedelta(hours=valid_hours)

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO referee_performance_cache
                    (referee_email, metrics, calculated_at, valid_until)
                    VALUES (?, ?, ?, ?)
                """,
                    (referee_email, json.dumps(metrics), now.isoformat(), valid_until.isoformat()),
                )
                conn.commit()

    def get_referee_performance_metrics(self, referee_email: str) -> dict[str, Any] | None:
        """Get cached referee performance metrics if still valid."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT metrics, valid_until
                FROM referee_performance_cache
                WHERE referee_email = ? AND valid_until > ?
            """,
                (referee_email, datetime.now().isoformat()),
            )

            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None

    def update_journal_statistics(
        self,
        journal_id: str,
        period_start: date,
        period_end: date,
        total_submissions: int,
        average_review_time: float,
        acceptance_rate: float,
        desk_rejection_rate: float,
    ):
        """Update journal statistics (spec lines 596-606)."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    INSERT OR REPLACE INTO journal_statistics
                    (journal_id, period_start, period_end, total_submissions,
                     average_review_time, acceptance_rate, desk_rejection_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        journal_id,
                        period_start.isoformat(),
                        period_end.isoformat(),
                        total_submissions,
                        average_review_time,
                        acceptance_rate,
                        desk_rejection_rate,
                    ),
                )
                conn.commit()

    def get_journal_statistics(
        self, journal_id: str, period_start: date, period_end: date
    ) -> dict[str, Any] | None:
        """Get journal statistics for a specific period."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT total_submissions, average_review_time,
                       acceptance_rate, desk_rejection_rate
                FROM journal_statistics
                WHERE journal_id = ? AND period_start = ? AND period_end = ?
            """,
                (journal_id, period_start.isoformat(), period_end.isoformat()),
            )

            result = cursor.fetchone()
            if result:
                return {
                    "total_submissions": result[0],
                    "average_review_time": result[1],
                    "acceptance_rate": result[2],
                    "desk_rejection_rate": result[3],
                }
            return None

    def populate_sample_statistics(self):
        """Populate sample statistics for testing."""
        # Sample referee performance metrics
        sample_metrics = {
            "test@example.com": {
                "average_response_time": 15.5,
                "acceptance_rate": 0.65,
                "quality_score": 8.5,
                "reliability_score": 0.95,
                "total_reviews": 25,
            }
        }

        for email, metrics in sample_metrics.items():
            self.update_referee_performance_metrics(email, metrics)

        # Sample journal statistics
        from datetime import date

        today = date.today()
        start_date = date(today.year, today.month, 1)
        end_date = date(today.year, today.month, 28)

        self.update_journal_statistics(
            "MF",
            start_date,
            end_date,
            total_submissions=45,
            average_review_time=28.5,
            acceptance_rate=0.35,
            desk_rejection_rate=0.15,
        )

        self.update_journal_statistics(
            "MOR",
            start_date,
            end_date,
            total_submissions=38,
            average_review_time=32.0,
            acceptance_rate=0.30,
            desk_rejection_rate=0.20,
        )

    def clear_old_cache(self, days: int = 90):
        """Clear cache entries older than specified days."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Clear old manuscripts
            cursor.execute(
                """
                DELETE FROM manuscripts
                WHERE extraction_date < ?
            """,
                (cutoff_date,),
            )

            deleted_manuscripts = cursor.rowcount

            # Clear old extraction runs
            cursor.execute(
                """
                DELETE FROM extraction_runs
                WHERE start_time < ?
            """,
                (cutoff_date,),
            )

            deleted_runs = cursor.rowcount

            conn.commit()

        print(f"🧹 Cleared {deleted_manuscripts} old manuscripts and {deleted_runs} old runs")

        return deleted_manuscripts, deleted_runs


# Integration helper for extractors
class ExtractorCacheMixin:
    """Mixin class to add caching capabilities to extractors."""

    def init_cache(self, journal_name: str, test_mode: bool = None):
        """Initialize cache for the extractor."""
        self.cache_manager = CacheManager(test_mode=test_mode)
        self.journal_name = journal_name
        self.run_id = self.cache_manager.start_extraction_run(journal_name)
        self.extraction_stats = {
            "manuscripts_extracted": 0,
            "new_manuscripts": 0,
            "updated_manuscripts": 0,
            "new_referees": 0,
            "errors": 0,
        }

    def should_extract_manuscript(
        self, manuscript_id: str, status: str = None, last_updated: str = None
    ) -> bool:
        """Check if manuscript needs extraction."""
        return self.cache_manager.should_update_manuscript(
            manuscript_id, self.journal_name, status, last_updated
        )

    def cache_manuscript_data(self, manuscript_data: dict[str, Any]):
        """Cache manuscript data after extraction."""
        cached = self.cache_manager.get_manuscript(manuscript_data["id"], self.journal_name)

        if cached:
            self.extraction_stats["updated_manuscripts"] += 1
        else:
            self.extraction_stats["new_manuscripts"] += 1

        self.extraction_stats["manuscripts_extracted"] += 1

        # Cache the manuscript
        self.cache_manager.update_manuscript(manuscript_data, self.journal_name)

        # Cache all referees
        for referee in manuscript_data.get("referees", []):
            if referee.get("email"):
                existing = self.cache_manager.get_referee(referee["email"])
                if not existing:
                    self.extraction_stats["new_referees"] += 1

                self.cache_manager.update_referee(referee, self.journal_name)

    def get_cached_referee_data(self, email: str) -> dict[str, Any] | None:
        """Get cached referee data to pre-populate fields."""
        cached = self.cache_manager.get_referee(email)
        if cached:
            return {
                "name": cached.name,
                "institution": cached.institution,
                "department": cached.department,
                "country": cached.country,
                "orcid": cached.orcid,
                "cached": True,
                "last_updated": cached.last_updated,
            }
        return None

    def finish_extraction(self, metadata: dict[str, Any] = None):
        """Finish extraction and save statistics."""
        self.cache_manager.update_extraction_stats(self.run_id, self.extraction_stats)
        self.cache_manager.finish_extraction_run(self.run_id, metadata)

        # Print summary
        print("\n📊 CACHE STATISTICS:")
        print(f"   📄 Total Manuscripts: {self.extraction_stats['manuscripts_extracted']}")
        print(f"   🆕 New Manuscripts: {self.extraction_stats['new_manuscripts']}")
        print(f"   🔄 Updated Manuscripts: {self.extraction_stats['updated_manuscripts']}")
        print(f"   👤 New Referees: {self.extraction_stats['new_referees']}")

        # Get overall cache stats
        stats = self.cache_manager.get_cache_statistics()
        print("\n📈 OVERALL CACHE:")
        print(f"   👥 Total Referees: {stats['total_referees']}")
        print(f"   🏢 Unique Institutions: {stats['unique_institutions']}")
        print(f"   🌍 Unique Countries: {stats['unique_countries']}")
        print(f"   💾 Cache Size: {stats['cache_size_mb']:.1f} MB")

        # Cleanup test cache if in test mode
        if hasattr(self, "cache_manager"):
            self.cache_manager.cleanup_test_cache()


# Usage example for MOR extractor:
"""
class ComprehensiveMORExtractor(ExtractorCacheMixin):
    def __init__(self):
        # ... existing init code ...
        self.init_cache('MOR')

    def extract_manuscript_details(self, manuscript_id):
        # Check if we need to extract
        if not self.should_extract_manuscript(manuscript_id, status, last_updated):
            # Use cached data
            cached = self.cache_manager.get_manuscript(manuscript_id, 'MOR')
            return cached.full_data

        # ... perform extraction ...

        # Cache the results
        self.cache_manuscript_data(manuscript)

        return manuscript

    def extract_referee_data(self, referee_info):
        # Check for cached data
        if referee_info.get('email'):
            cached_data = self.get_cached_referee_data(referee_info['email'])
            if cached_data:
                # Pre-populate with cached data
                referee_info.update(cached_data)

        # ... continue extraction ...

        return referee_info

    def run(self):
        try:
            self.extract_all()
        finally:
            self.finish_extraction()
            self.cleanup()
"""
