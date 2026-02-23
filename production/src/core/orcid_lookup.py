#!/usr/bin/env python3
import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List
import urllib.request
import urllib.parse
import urllib.error


class ORCIDLookup:
    API_BASE = "https://pub.orcid.org/v3.0"
    SEARCH_URL = f"{API_BASE}/search/"
    TIMEOUT = 5
    RATE_LIMIT_DELAY = 0.5

    def __init__(self, cache_dir: Path = None, cache_ttl_days: int = 30):
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "orcid_cache.db"
        self.cache_ttl_days = cache_ttl_days
        self._init_db()
        self._last_request_time = 0

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orcid_cache (
                    lookup_key TEXT PRIMARY KEY,
                    orcid_id TEXT,
                    full_name TEXT,
                    affiliations TEXT,
                    lookup_date TEXT,
                    raw_response TEXT
                )
            """
            )
            conn.commit()

    def _get_cached(self, key: str) -> Optional[Dict]:
        with sqlite3.connect(str(self.db_path)) as conn:
            row = conn.execute(
                "SELECT orcid_id, full_name, affiliations, lookup_date, raw_response FROM orcid_cache WHERE lookup_key = ?",
                (key,),
            ).fetchone()
        if row:
            lookup_date = datetime.fromisoformat(row[3])
            if datetime.now() - lookup_date < timedelta(days=self.cache_ttl_days):
                return {
                    "orcid_id": row[0],
                    "full_name": row[1],
                    "affiliations": json.loads(row[2]) if row[2] else [],
                    "lookup_date": row[3],
                    "cached": True,
                }
        return None

    def _set_cached(
        self, key: str, orcid_id: str, full_name: str, affiliations: List, raw: str = ""
    ):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO orcid_cache
                   (lookup_key, orcid_id, full_name, affiliations, lookup_date, raw_response)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    key,
                    orcid_id,
                    full_name,
                    json.dumps(affiliations),
                    datetime.now().isoformat(),
                    raw,
                ),
            )
            conn.commit()

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def search_by_name(self, first_name: str, last_name: str, email: str = "") -> Optional[Dict]:
        if not first_name or not last_name:
            return None

        first_clean = first_name.strip().split()[0]
        last_clean = last_name.strip()
        cache_key = f"{first_clean.lower()}_{last_clean.lower()}_{email.lower() if email else ''}"

        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            self._rate_limit()

            if email:
                query = f"email:{email}"
            else:
                query = f"family-name:{last_clean}+AND+given-names:{first_clean}"

            url = f"{self.SEARCH_URL}?q={urllib.parse.quote(query, safe=':+')}&rows=5"

            req = urllib.request.Request(url)
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", "EditorialScripts/1.0 (mailto:dylansmb@gmail.com)")

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))

            results = data.get("result", [])
            if not results:
                self._set_cached(cache_key, "", "", [])
                return None

            best_match = None
            for result in results:
                orcid_id = result.get("orcid-identifier", {}).get("path", "")
                if orcid_id:
                    if email:
                        best_match = orcid_id
                        break
                    record = self._fetch_record(orcid_id)
                    if record:
                        rec_first = (record.get("given_names", "") or "").lower()
                        rec_last = (record.get("family_name", "") or "").lower()
                        if rec_last == last_clean.lower() and (
                            rec_first.startswith(first_clean.lower()[:3])
                            or first_clean.lower().startswith(rec_first[:3])
                        ):
                            best_match = orcid_id
                            full_name = (
                                f"{record.get('given_names', '')} {record.get('family_name', '')}"
                            )
                            affiliations = record.get("affiliations", [])
                            self._set_cached(
                                cache_key, orcid_id, full_name, affiliations, json.dumps(record)
                            )
                            return {
                                "orcid_id": orcid_id,
                                "full_name": full_name,
                                "affiliations": affiliations,
                                "cached": False,
                            }

            if best_match:
                record = self._fetch_record(best_match)
                full_name = ""
                affiliations = []
                if record:
                    full_name = f"{record.get('given_names', '')} {record.get('family_name', '')}"
                    affiliations = record.get("affiliations", [])
                self._set_cached(cache_key, best_match, full_name, affiliations)
                return {
                    "orcid_id": best_match,
                    "full_name": full_name,
                    "affiliations": affiliations,
                    "cached": False,
                }

            self._set_cached(cache_key, "", "", [])
            return None

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"         ⚠️ ORCID API error: {str(e)[:50]}")
            return None
        except Exception as e:
            print(f"         ⚠️ ORCID lookup error: {str(e)[:50]}")
            return None

    def _fetch_record(self, orcid_id: str) -> Optional[Dict]:
        try:
            self._rate_limit()
            url = f"{self.API_BASE}/{orcid_id}/person"
            req = urllib.request.Request(url)
            req.add_header("Accept", "application/json")
            req.add_header("User-Agent", "EditorialScripts/1.0 (mailto:dylansmb@gmail.com)")

            with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:  # nosec B310
                data = json.loads(resp.read().decode("utf-8"))

            name_data = data.get("name", {}) or {}
            given = (name_data.get("given-names", {}) or {}).get("value", "")
            family = (name_data.get("family-name", {}) or {}).get("value", "")

            affiliations = []
            try:
                emp_url = f"{self.API_BASE}/{orcid_id}/employments"
                req2 = urllib.request.Request(emp_url)
                req2.add_header("Accept", "application/json")
                req2.add_header("User-Agent", "EditorialScripts/1.0 (mailto:dylansmb@gmail.com)")
                with urllib.request.urlopen(req2, timeout=self.TIMEOUT) as resp2:  # nosec B310
                    emp_data = json.loads(resp2.read().decode("utf-8"))

                groups = emp_data.get("affiliation-group", []) or []
                for group in groups[:5]:
                    summaries = group.get("summaries", []) or []
                    for summary in summaries:
                        emp = summary.get("employment-summary", {}) or {}
                        org = emp.get("organization", {}) or {}
                        org_name = org.get("name", "")
                        dept = emp.get("department-name", "")
                        role = emp.get("role-title", "")
                        if org_name:
                            affiliations.append(
                                {
                                    "organization": org_name,
                                    "department": dept or "",
                                    "role": role or "",
                                }
                            )
            except Exception:
                pass

            return {
                "given_names": given,
                "family_name": family,
                "affiliations": affiliations,
            }

        except Exception:
            return None

    def lookup_person(self, name: str, email: str = "") -> Optional[Dict]:
        if not name:
            return None

        name = name.strip()
        if ", " in name:
            parts = name.split(", ", 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip()
        else:
            parts = name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = parts[-1]
            elif len(parts) == 1:
                first_name = ""
                last_name = parts[0]
            else:
                return None

        return self.search_by_name(first_name, last_name, email)

    def enrich_referees(self, referees: List[Dict], verbose: bool = True) -> int:
        enriched = 0
        for ref in referees:
            if ref.get("orcid"):
                continue
            name = ref.get("name", "")
            email = ref.get("email", "")
            if not name:
                continue

            result = self.lookup_person(name, email)
            if result and result.get("orcid_id"):
                ref["orcid"] = result["orcid_id"]
                if result.get("affiliations") and not ref.get("institution"):
                    ref["institution"] = result["affiliations"][0].get("organization", "")
                    if result["affiliations"][0].get("department"):
                        ref["department"] = result["affiliations"][0]["department"]
                enriched += 1
                if verbose:
                    src = "cached" if result.get("cached") else "API"
                    print(f"         🔗 ORCID [{src}]: {name} → {result['orcid_id']}")

        return enriched

    def enrich_authors(self, authors: List[Dict], verbose: bool = True) -> int:
        enriched = 0
        for author in authors:
            if author.get("orcid"):
                continue
            name = author.get("name", "")
            email = author.get("email", "")
            if not name:
                continue

            result = self.lookup_person(name, email)
            if result and result.get("orcid_id"):
                author["orcid"] = result["orcid_id"]
                if result.get("affiliations") and not author.get("institution"):
                    author["institution"] = result["affiliations"][0].get("organization", "")
                enriched += 1
                if verbose:
                    src = "cached" if result.get("cached") else "API"
                    print(f"         🔗 ORCID [{src}]: {name} → {result['orcid_id']}")

        return enriched
