#!/usr/bin/env python3
"""
ORCID API Client for Academic Profile Enrichment
================================================

Provides comprehensive ORCID integration for finding researcher IDs
and enriching profiles with publications, affiliations, and more.
"""

import logging
import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote

import requests

from src.ecc.infrastructure.secrets.provider import get_secret_with_vault


class ORCIDClient:
    """Client for ORCID API v3.0 with full enrichment capabilities."""

    def __init__(self, client_id: str = None, client_secret: str = None):
        """Initialize ORCID client with API credentials."""
        # Read from env or secret manager; do not ship defaults
        self.client_id = client_id or get_secret_with_vault("ORCID_CLIENT_ID")
        self.client_secret = client_secret or get_secret_with_vault("ORCID_CLIENT_SECRET")

        # API endpoints
        self.base_url = "https://pub.orcid.org/v3.0"
        self.search_url = "https://pub.orcid.org/v3.0/search"
        self.token_url = "https://orcid.org/oauth/token"

        # Cache for API responses
        self.cache = {}
        self.cache_duration = timedelta(hours=24)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 10 requests per second max

        # Logger (PII-redacting)
        self.logger = logging.getLogger("orcid_client")

        # Get access token
        self.access_token = None
        self.token_expiry = None
        if self.client_id and self.client_secret:
            self._get_access_token()
        else:
            self.logger.warning("ORCID credentials not set; enrichment limited")

    def _get_access_token(self):
        """Get OAuth access token for public API access."""
        try:
            headers = {"Accept": "application/json"}
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
                "scope": "/read-public",
            }

            response = requests.post(self.token_url, headers=headers, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                # Token expires in seconds, convert to timestamp
                expires_in = token_data.get("expires_in", 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                self.logger.info("ORCID API authenticated", extra={"expires_in": expires_in})
            else:
                self.logger.warning(
                    "ORCID authentication failed", extra={"status": response.status_code}
                )
        except Exception as e:
            self.logger.error("ORCID authentication error", extra={"error": str(e)[:200]})

    def _ensure_rate_limit(self):
        """Ensure we don't exceed rate limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def _make_request(self, url: str, headers: dict = None) -> dict | None:
        """Make API request with rate limiting and error handling."""
        self._ensure_rate_limit()

        # Check token expiry
        if self.token_expiry and datetime.now() >= self.token_expiry:
            self._get_access_token()

        # Default headers
        default_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        if headers:
            default_headers.update(headers)

        try:
            response = requests.get(url, headers=default_headers, timeout=10)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            elif response.status_code == 401:
                self.logger.warning("ORCID API auth error - refreshing token")
                self.access_token = None
                self._get_access_token()
                # Retry once with new token
                if self.access_token:
                    default_headers["Authorization"] = f"Bearer {self.access_token}"
                    response = requests.get(url, headers=default_headers, timeout=10)
                    if response.status_code == 200:
                        return response.json()
                return None
            else:
                # Silently handle other errors to avoid breaking extraction
                return None
        except requests.exceptions.Timeout:
            self.logger.warning("ORCID API timeout - skipping")
            return None
        except Exception:
            # Silently handle other exceptions to avoid breaking extraction
            return None

    def search_by_name_and_affiliation(
        self, name: str, affiliation: str = None, email: str = None
    ) -> list[dict]:
        """
        Search for ORCID profiles by name and optionally affiliation/email.

        Returns list of potential matches with scores.
        """
        self.logger.debug("ORCID search", extra={"name": self._redact_name(name)})

        # Build search query
        query_parts = []

        # Parse name (handle "Last, First" and "First Last" formats)
        if "," in name:
            last_name, first_name = name.split(",", 1)
            last_name = last_name.strip()
            first_name = first_name.strip()
        else:
            name_parts = name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                first_name = ""
                last_name = name

        # Add name to query
        if first_name and last_name:
            query_parts.append(f'given-names:"{first_name}"')
            query_parts.append(f'family-name:"{last_name}"')
        elif last_name:
            query_parts.append(f'family-name:"{last_name}"')

        # First try with just name
        name_query = " AND ".join(query_parts)

        # Add email if provided (more specific)
        if email:
            query_parts.append(f"email:{email}")

        # Combine query parts
        query = " AND ".join(query_parts)
        self.logger.debug("ORCID query", extra={"query": query})

        # Make search request
        search_url = f"{self.search_url}?q={quote(query)}"
        results = self._make_request(search_url)

        # If no results, try with just the name
        if (not results or results.get("num-found", 0) == 0) and affiliation:
            print("      📝 Trying broader search with just name...")
            query = name_query
            search_url = f"{self.search_url}?q={quote(query)}"
            results = self._make_request(search_url)

        if results is None:
            self.logger.info("No ORCID results (None)", extra={"name": self._redact_name(name)})
            return []

        if not isinstance(results, dict) or "result" not in results:
            self.logger.info("No ORCID results (format)", extra={"name": self._redact_name(name)})
            return []

        # Process results
        matches = []
        result_list = results.get("result") or []
        self.logger.debug("ORCID candidates", extra={"count": len(result_list)})
        for result in result_list[:10]:
            orcid_id = result.get("orcid-identifier", {}).get("path")
            if not orcid_id:
                continue

            # Get full profile to verify match
            profile = self.get_full_profile(orcid_id)
            if not profile:
                continue

            # Calculate match score
            score = self._calculate_match_score(profile, name, affiliation, email)

            if score > 0.3:  # Lower threshold for better matching
                matches.append(
                    {
                        "orcid": orcid_id,
                        "score": score,
                        "name": self._extract_name_from_profile(profile),
                        "affiliations": self._extract_affiliations_from_profile(profile),
                    }
                )

        # Sort by score
        matches.sort(key=lambda x: x["score"], reverse=True)

        if matches:
            best_match = matches[0]
            self.logger.info(
                "ORCID match",
                extra={"orcid": best_match["orcid"], "score": round(best_match["score"], 3)},
            )

        return matches

    def get_full_profile(self, orcid_id: str) -> dict | None:
        """Get complete ORCID profile including all sections."""
        # Clean ORCID ID (remove URL prefix if present)
        if orcid_id and orcid_id.startswith("http"):
            orcid_id = orcid_id.split("/")[-1]

        # Check cache
        cache_key = f"profile_{orcid_id}"
        if cache_key in self.cache:
            cached_data, cached_time = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                return cached_data

        # Fetch profile
        profile_url = f"{self.base_url}/{orcid_id}"
        profile = self._make_request(profile_url)

        if profile:
            # Cache result
            self.cache[cache_key] = (profile, datetime.now())

        return profile

    def get_works(self, orcid_id: str) -> list[dict]:
        """Get all works (publications) for an ORCID ID."""
        # Clean ORCID ID (remove URL prefix if present)
        if orcid_id and orcid_id.startswith("http"):
            orcid_id = orcid_id.split("/")[-1]

        works_url = f"{self.base_url}/{orcid_id}/works"
        works_summary = self._make_request(works_url)

        if not works_summary or "group" not in works_summary:
            return []

        publications = []

        # Get detailed info for each work
        for group in works_summary.get("group", [])[:50]:  # Limit to 50 most recent
            work_summary = group.get("work-summary", [])
            if not work_summary:
                continue

            # Use first work summary (they're duplicates)
            work = work_summary[0]
            put_code = work.get("put-code")

            if put_code:
                # Get full work details
                work_detail_url = f"{self.base_url}/{orcid_id}/work/{put_code}"
                work_detail = self._make_request(work_detail_url)

                if work_detail:
                    pub = self._parse_work_detail(work_detail)
                    if pub:
                        publications.append(pub)

        return publications

    def _parse_work_detail(self, work: dict) -> dict | None:
        """Parse work detail into structured publication data."""
        try:
            title = work.get("title", {}).get("title", {}).get("value", "")

            # Get publication year
            pub_date = work.get("publication-date")
            year = None
            if pub_date:
                year = pub_date.get("year", {}).get("value")

            # Get journal
            journal = work.get("journal-title", {}).get("value", "")

            # Get DOI
            doi = None
            external_ids = work.get("external-ids", {}).get("external-id", [])
            for ext_id in external_ids:
                if ext_id.get("external-id-type") == "doi":
                    doi = ext_id.get("external-id-value")
                    break

            # Get type
            work_type = work.get("type", "")

            # Get contributors (co-authors)
            contributors = []
            for contributor in work.get("contributors", {}).get("contributor", []):
                credit_name = contributor.get("credit-name")
                if credit_name:
                    contributors.append(credit_name.get("value", ""))

            return {
                "title": title,
                "year": year,
                "journal": journal,
                "doi": doi,
                "type": work_type,
                "authors": contributors,
                "source": "ORCID",
            }
        except Exception as e:
            print(f"         ⚠️ Error parsing work: {e}")
            return None

    def get_affiliations(self, orcid_id: str) -> list[dict]:
        """Get employment and education history."""
        # Clean ORCID ID (remove URL prefix if present)
        if orcid_id and orcid_id.startswith("http"):
            orcid_id = orcid_id.split("/")[-1]

        affiliations = []

        # Get employment - handle affiliation-group structure
        employment_url = f"{self.base_url}/{orcid_id}/employments"
        employments = self._make_request(employment_url)

        if employments:
            # Handle v3.0 API structure with affiliation-group
            if "affiliation-group" in employments:
                for group in employments["affiliation-group"]:
                    summaries = group.get("summaries", [])
                    for summary in summaries:
                        emp = summary.get("employment-summary", {})
                        org = emp.get("organization", {})
                        affiliations.append(
                            {
                                "type": "employment",
                                "organization": org.get("name", "").strip(),
                                "department": (
                                    emp.get("department-name", "").strip()
                                    if emp.get("department-name")
                                    else ""
                                ),
                                "role": (
                                    emp.get("role-title", "").strip()
                                    if emp.get("role-title")
                                    else ""
                                ),
                                "start_date": self._parse_date(emp.get("start-date")),
                                "end_date": self._parse_date(emp.get("end-date")),
                                "current": emp.get("end-date") is None,
                                "city": org.get("address", {}).get("city", ""),
                                "country": org.get("address", {}).get("country", ""),
                            }
                        )
            # Fallback to old structure if needed
            elif "employment-summary" in employments:
                for emp in employments["employment-summary"]:
                    org = emp.get("organization", {})
                    affiliations.append(
                        {
                            "type": "employment",
                            "organization": org.get("name", "").strip(),
                            "department": (
                                emp.get("department-name", "").strip()
                                if emp.get("department-name")
                                else ""
                            ),
                            "role": (
                                emp.get("role-title", "").strip() if emp.get("role-title") else ""
                            ),
                            "start_date": self._parse_date(emp.get("start-date")),
                            "end_date": self._parse_date(emp.get("end-date")),
                            "current": emp.get("end-date") is None,
                            "city": org.get("address", {}).get("city", ""),
                            "country": org.get("address", {}).get("country", ""),
                        }
                    )

        # Get education - handle affiliation-group structure
        education_url = f"{self.base_url}/{orcid_id}/educations"
        educations = self._make_request(education_url)

        if educations:
            # Handle v3.0 API structure with affiliation-group
            if "affiliation-group" in educations:
                for group in educations["affiliation-group"]:
                    summaries = group.get("summaries", [])
                    for summary in summaries:
                        edu = summary.get("education-summary", {})
                        org = edu.get("organization", {})
                        affiliations.append(
                            {
                                "type": "education",
                                "organization": org.get("name", "").strip(),
                                "department": (
                                    edu.get("department-name", "").strip()
                                    if edu.get("department-name")
                                    else ""
                                ),
                                "role": (
                                    edu.get("role-title", "").strip()
                                    if edu.get("role-title")
                                    else ""
                                ),
                                "degree": (
                                    edu.get("role-title", "").strip()
                                    if edu.get("role-title")
                                    else ""
                                ),
                                "start_date": self._parse_date(edu.get("start-date")),
                                "end_date": self._parse_date(edu.get("end-date")),
                                "city": org.get("address", {}).get("city", ""),
                                "country": org.get("address", {}).get("country", ""),
                            }
                        )
            # Fallback to old structure if needed
            elif "education-summary" in educations:
                for edu in educations["education-summary"]:
                    org = edu.get("organization", {})
                    affiliations.append(
                        {
                            "type": "education",
                            "organization": org.get("name", "").strip(),
                            "department": (
                                edu.get("department-name", "").strip()
                                if edu.get("department-name")
                                else ""
                            ),
                            "role": (
                                edu.get("role-title", "").strip() if edu.get("role-title") else ""
                            ),
                            "degree": (
                                edu.get("role-title", "").strip() if edu.get("role-title") else ""
                            ),
                            "start_date": self._parse_date(edu.get("start-date")),
                            "end_date": self._parse_date(edu.get("end-date")),
                            "city": org.get("address", {}).get("city", ""),
                            "country": org.get("address", {}).get("country", ""),
                        }
                    )

        return affiliations

    def enrich_person_profile(self, person_data: dict) -> dict:
        """
        Enrich a person's profile with ORCID data.

        Input should have: name, orcid (optional), institution (optional), email (optional)
        """
        name = person_data.get("name", "")
        orcid_id = person_data.get("orcid", "")
        institution = person_data.get("institution", "")
        email = person_data.get("email", "")

        enriched = person_data.copy()

        # If no ORCID ID, try to find one
        if not orcid_id:
            matches = self.search_by_name_and_affiliation(name, institution, email)
            if matches and matches[0]["score"] > 0.5:  # Moderate confidence threshold
                orcid_id = matches[0]["orcid"]
                enriched["orcid"] = orcid_id
                enriched["orcid_confidence"] = matches[0]["score"]
                print(f"      🎯 Discovered ORCID: {orcid_id}")

        # If we have ORCID ID, enrich profile
        if orcid_id:
            # Clean ORCID ID (remove URL prefix if present)
            if orcid_id.startswith("http"):
                orcid_id = orcid_id.split("/")[-1]

            # Get full profile
            profile = self.get_full_profile(orcid_id)

            if profile:
                try:
                    # Extract verified email
                    emails = profile.get("emails", {}).get("email", [])
                    for email_obj in emails:
                        if email_obj.get("verified", False):
                            enriched["email_verified"] = email_obj.get("email", "")
                            break
                except Exception:
                    pass

                try:
                    # Get biography
                    bio = profile.get("biography")
                    if bio:
                        enriched["biography"] = bio.get("content", "")
                except Exception:
                    pass

                try:
                    # Get keywords (research interests) - nested under person
                    person = profile.get("person", {})
                    keywords = person.get("keywords", {}).get("keyword", [])
                    if keywords:
                        enriched["research_interests"] = [
                            kw.get("content", "") for kw in keywords if kw.get("content")
                        ]
                except Exception:
                    pass

                # Research interests will be extracted after publications are fetched

                try:
                    # Get other identifiers
                    external_ids = profile.get("external-identifiers", {}).get(
                        "external-identifier", []
                    )
                except Exception:
                    external_ids = []
                if external_ids:
                    enriched["other_ids"] = {}
                    for ext_id in external_ids:
                        id_type = ext_id.get("external-id-type", "")
                        id_value = ext_id.get("external-id-value", "")
                        enriched["other_ids"][id_type] = id_value

            try:
                # Get publications
                publications = self.get_works(orcid_id)
                if publications:
                    enriched["publications"] = publications
                    enriched["publication_count"] = len(publications)

                    # Extract research interests from publication titles if no keywords were found
                    current_interests = enriched.get("research_interests", [])
                    if not current_interests or len(current_interests) == 0:
                        try:
                            interests = self._extract_research_interests_from_publications(
                                publications
                            )
                            if interests:
                                enriched["research_interests"] = interests
                                pass  # Successfully extracted research interests
                        except Exception as e:
                            self.logger.debug(
                                "Interests extraction exception", extra={"error": str(e)[:200]}
                            )

                    # Calculate h-index estimate (simplified)
                    try:
                        enriched["metrics"] = self._calculate_publication_metrics(publications)
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                # Get affiliations
                affiliations = self.get_affiliations(orcid_id)
                if affiliations:
                    enriched["affiliation_history"] = affiliations

                    # Find current affiliation and extract details
                    current = [a for a in affiliations if a.get("current", False)]
                    if current:
                        enriched["current_affiliation"] = current[0]
                        # Add top-level fields for easy access
                        if current[0].get("organization"):
                            enriched["institution"] = current[0]["organization"]
                        if current[0].get("department"):
                            enriched["department"] = current[0]["department"]
                        if current[0].get("role"):
                            enriched["role"] = current[0]["role"]
            except Exception:
                pass

            # Extract country from profile if we have one
            try:
                if profile:
                    country = self._extract_country_from_profile(profile)
                    if country:
                        enriched["country"] = country
            except Exception:
                pass

        # Add enrichment metadata
        enriched["enrichment_date"] = datetime.now().isoformat()
        enriched["enrichment_source"] = "ORCID"

        return enriched

    @staticmethod
    def _redact_name(name: str) -> str:
        try:
            n = (name or "").strip()
            # Redact emails within name if present
            n = re.sub(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+)\.[A-Za-z]{2,}", r"***@\2", n)
            parts = n.split()
            if len(parts) >= 2:
                return parts[0] + " ***"
            return n[:1] + "***" if n else n
        except Exception:
            return "***"

        # If name cannot be processed, return masked fallback above

    def _extract_institution_name(self, affiliation: str) -> str:
        """Extract clean institution name from affiliation string."""
        # Remove department info
        institution = re.sub(r",.*Department.*", "", affiliation)
        institution = re.sub(r",.*School.*", "", institution)

        # Clean up
        institution = institution.split(",")[0].strip()

        return institution

    def _extract_name_from_profile(self, profile: dict) -> str:
        """Extract full name from ORCID profile."""
        # Name is nested under 'person' -> 'name'
        person = profile.get("person", {})
        name_obj = person.get("name", {})
        given = name_obj.get("given-names", {}).get("value", "").strip()
        family = name_obj.get("family-name", {}).get("value", "").strip()

        if given and family:
            return f"{given} {family}"
        elif family:
            return family
        else:
            return ""

    def _extract_affiliations_from_profile(self, profile: dict) -> list[str]:
        """Extract affiliation names from profile."""
        affiliations = []

        # Get from employment - structure is different in v3.0 API
        activities = profile.get("activities-summary", {})
        employments = activities.get("employments", {})

        # Check for affiliation-group structure
        affiliation_groups = employments.get("affiliation-group", [])
        for group in affiliation_groups:
            summaries = group.get("summaries", [])
            for summary in summaries:
                # The organization is nested under employment-summary
                emp_summary = summary.get("employment-summary", {})
                org = emp_summary.get("organization", {}).get("name", "")
                if org:
                    affiliations.append(org.strip())

        return affiliations

    def _extract_country_from_profile(self, profile: dict) -> str | None:
        """Extract country from ORCID profile affiliations."""
        # Country code to name mapping
        country_map = {
            "GB": "United Kingdom",
            "US": "United States",
            "USA": "United States",
            "UK": "United Kingdom",
            "CN": "China",
            "DE": "Germany",
            "FR": "France",
            "JP": "Japan",
            "CA": "Canada",
            "AU": "Australia",
            "NZ": "New Zealand",
            "IT": "Italy",
            "ES": "Spain",
            "NL": "Netherlands",
            "CH": "Switzerland",
            "SE": "Sweden",
            "NO": "Norway",
            "DK": "Denmark",
            "BE": "Belgium",
            "AT": "Austria",
            "IN": "India",
            "BR": "Brazil",
            "SG": "Singapore",
            "HK": "Hong Kong",
            "KR": "South Korea",
            "TW": "Taiwan",
            "IL": "Israel",
            "ZA": "South Africa",
            "MX": "Mexico",
            "AR": "Argentina",
        }

        # Try to get country from current employment
        activities = profile.get("activities-summary", {})
        employments = activities.get("employments", {})
        affiliation_groups = employments.get("affiliation-group", [])

        for group in affiliation_groups:
            summaries = group.get("summaries", [])
            for summary in summaries:
                emp_summary = summary.get("employment-summary", {})
                address = emp_summary.get("organization", {}).get("address", {})
                country_code = address.get("country")
                if country_code:
                    return country_map.get(country_code, country_code)

        # Try person address as fallback
        person = profile.get("person", {})
        addresses = person.get("addresses", {}).get("address", [])
        if addresses:
            country_val = addresses[0].get("country", {}).get("value")
            if country_val:
                return country_map.get(country_val, country_val)

        return None

    def _calculate_match_score(
        self, profile: dict, name: str, affiliation: str, email: str
    ) -> float:
        """Calculate how well a profile matches search criteria."""
        score = 0.0

        # Name matching (50% weight)
        profile_name = self._extract_name_from_profile(profile)
        if profile_name:
            name_similarity = self._string_similarity(name.lower(), profile_name.lower())
            score += name_similarity * 0.5

        # Affiliation matching (30% weight)
        if affiliation:
            profile_affiliations = self._extract_affiliations_from_profile(profile)
            if profile_affiliations:
                best_affil_match = max(
                    self._string_similarity(affiliation.lower(), pa.lower())
                    for pa in profile_affiliations
                )
                score += best_affil_match * 0.3

        # Email matching (20% weight)
        if email:
            profile_emails = profile.get("emails", {}).get("email", [])
            for email_obj in profile_emails:
                if email_obj.get("email", "").lower() == email.lower():
                    score += 0.2
                    break

        return score

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate similarity between two strings (0-1)."""
        # Simple token-based similarity
        tokens1 = set(s1.split())
        tokens2 = set(s2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)

        return len(intersection) / len(union)

    def _parse_date(self, date_obj: dict | None) -> str | None:
        """Parse ORCID date object to string."""
        if not date_obj:
            return None

        year_obj = date_obj.get("year", {})
        month_obj = date_obj.get("month", {})
        day_obj = date_obj.get("day", {})

        year = year_obj.get("value") if year_obj else None
        month = month_obj.get("value") if month_obj else None
        day = day_obj.get("value") if day_obj else None

        if year:
            if month and day:
                return f"{year}-{int(month):02d}-{int(day):02d}"
            elif month:
                return f"{year}-{int(month):02d}"
            else:
                return str(year)

        return None

    def _extract_research_interests_from_publications(self, publications: list[dict]) -> list[str]:
        """Extract research interests from publication titles using keyword analysis."""
        if not publications:
            return []

        # Common academic keywords to look for in titles
        keyword_map = {
            "optimization": ["optimization", "optimal", "optimize", "optimality"],
            "stochastic": ["stochastic", "random", "probabilistic", "uncertainty"],
            "control": ["control", "controller", "controlled"],
            "finance": ["finance", "financial", "portfolio", "investment", "trading", "market"],
            "machine learning": [
                "machine learning",
                "neural",
                "deep learning",
                "ai",
                "artificial intelligence",
            ],
            "statistics": ["statistical", "statistics", "estimation", "inference"],
            "differential equations": [
                "differential equation",
                "pde",
                "ode",
                "partial differential",
            ],
            "game theory": ["game theory", "nash", "equilibrium", "strategic"],
            "networks": ["network", "graph", "topology", "connectivity"],
            "algorithms": ["algorithm", "computational", "complexity"],
            "risk": ["risk", "risk management", "risk measure"],
            "derivatives": ["derivative", "option", "futures", "swap"],
            "credit": ["credit", "default", "cds", "bond"],
            "volatility": ["volatility", "variance", "vix"],
            "pricing": ["pricing", "valuation", "price"],
            "hedging": ["hedging", "hedge", "replication"],
            "monte carlo": ["monte carlo", "simulation", "sampling"],
            "time series": ["time series", "forecasting", "arima", "garch"],
            "bayesian": ["bayesian", "bayes", "posterior", "prior"],
            "markov": ["markov", "markovian", "chain"],
            "martingale": ["martingale", "stopping", "optional"],
            "mean field": ["mean field", "mean-field", "mckean"],
            "reinforcement learning": ["reinforcement learning", "q-learning", "policy"],
            "numerical methods": ["numerical", "finite difference", "finite element"],
            "analysis": ["analysis", "analytical", "theory"],
            "modeling": ["model", "modeling", "modelling"],
            "dynamics": ["dynamic", "dynamics", "dynamical"],
            "nonlinear": ["nonlinear", "non-linear", "chaos"],
            "quantum": ["quantum", "quantum computing"],
            "blockchain": ["blockchain", "cryptocurrency", "bitcoin", "defi"],
        }

        # Count keyword occurrences across all publication titles
        keyword_counts = {}

        for pub in publications[:50]:  # Analyze up to 50 most recent publications
            title = pub.get("title", "").lower()
            if not title:
                continue

            for interest, keywords in keyword_map.items():
                for keyword in keywords:
                    if keyword in title:
                        keyword_counts[interest] = keyword_counts.get(interest, 0) + 1
                        break

        # Sort by frequency and return top interests
        sorted_interests = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)

        # Return top 5 research interests
        return [interest.title() for interest, _ in sorted_interests[:5]]

    def _calculate_publication_metrics(self, publications: list[dict]) -> dict:
        """Calculate publication metrics like h-index estimate."""
        metrics = {
            "total_publications": len(publications),
            "years_active": 0,
            "journals": set(),
            "publication_years": [],
        }

        years = []
        for pub in publications:
            if pub.get("year"):
                years.append(int(pub["year"]))
            if pub.get("journal"):
                metrics["journals"].add(pub["journal"])

        if years:
            metrics["first_publication"] = min(years)
            metrics["latest_publication"] = max(years)
            metrics["years_active"] = max(years) - min(years) + 1
            metrics["publication_years"] = sorted(set(years))

        metrics["unique_journals"] = len(metrics["journals"])
        metrics["journals"] = list(metrics["journals"])[:10]  # Top 10 journals

        return metrics


# Test function
if __name__ == "__main__":
    print("🧪 Testing ORCID Client")
    print("=" * 60)

    client = ORCIDClient()

    # Test search
    test_person = {"name": "Dylan Possamai", "institution": "ETH Zurich", "email": ""}

    print(f"\n🔍 Testing search for: {test_person['name']}")
    enriched = client.enrich_person_profile(test_person)

    print("\n📊 Enrichment Results:")
    print(f"   ORCID: {enriched.get('orcid', 'Not found')}")
    print(f"   Publications: {enriched.get('publication_count', 0)}")
    print(
        f"   Current affiliation: {enriched.get('current_affiliation', {}).get('organization', 'Unknown')}"
    )

    if enriched.get("publications"):
        print("\n📚 Recent Publications:")
        for pub in enriched["publications"][:3]:
            print(f"   - {pub['year']}: {pub['title'][:60]}...")
            if pub.get("journal"):
                print(f"     Journal: {pub['journal']}")
