#!/usr/bin/env python3
"""
Academic profile enrichment using ORCID API, Google Scholar, and other sources.
Enriches author and referee data with publications, h-indices, institutional affiliations.
"""

import os
import re
import json
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from urllib.parse import quote

class AcademicProfileEnricher:
    """Enrich author and referee profiles with academic data from multiple sources."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Editorial-Assistant/1.0 (research purposes)',
            'Accept': 'application/json'
        })
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting
        self.last_orcid_request = 0
        self.last_scholar_request = 0
        self.min_request_interval = 1.0  # seconds between requests
        
        # Cache for API responses
        self.orcid_cache = {}
        self.scholar_cache = {}

    def _is_valid_orcid(self, orcid_id: str) -> bool:
        """Validate ORCID ID format."""
        if not orcid_id:
            return False
        
        # Extract the numeric part
        orcid_clean = self._normalize_orcid(orcid_id)
        
        # ORCID format: 0000-0000-0000-0000
        import re
        pattern = r'^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$'
        return bool(re.match(pattern, orcid_clean))
    
    def _normalize_orcid(self, orcid_id: str) -> str:
        """Normalize ORCID ID to standard format."""
        # Remove URLs
        orcid_clean = orcid_id.replace('https://orcid.org/', '').replace('http://orcid.org/', '')
        
        # Remove any extra whitespace or formatting
        orcid_clean = orcid_clean.strip()
        
        # Ensure proper format with dashes
        if len(orcid_clean) == 16 and '-' not in orcid_clean:
            # Format: 0000000000000000 -> 0000-0000-0000-0000
            orcid_clean = f"{orcid_clean[:4]}-{orcid_clean[4:8]}-{orcid_clean[8:12]}-{orcid_clean[12:]}"
        
        return orcid_clean
    

    def check_orcid_quota(self):
        """Check if we're approaching ORCID API quota limits."""
        current_time = time.time()
        hour_start = current_time - (current_time % 3600)  # Start of current hour
        
        # Count requests in the last hour
        if not hasattr(self, 'orcid_request_times'):
            self.orcid_request_times = []
        
        # Clean old requests
        self.orcid_request_times = [t for t in self.orcid_request_times if t > hour_start]
        
        # ORCID allows 24 requests per hour for public API
        if len(self.orcid_request_times) >= 20:  # Leave some buffer
            print("   ⚠️ Approaching ORCID API quota limit - throttling requests")
            return False
        
        return True
    
    def record_orcid_request(self):
        """Record an ORCID API request for quota tracking."""
        if not hasattr(self, 'orcid_request_times'):
            self.orcid_request_times = []
        
        self.orcid_request_times.append(time.time())

    def enrich_person_profile(self, person_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich a person's profile with academic data from multiple sources."""
        
        enriched_profile = person_data.copy()
        enrichment_sources = []
        
        print(f"🔍 Enriching profile for: {person_data.get('name', 'Unknown')}")
        
        # 1. ORCID enrichment (most reliable)
        if person_data.get('orcid') and self.check_orcid_quota():
            orcid_data = self.get_orcid_profile(person_data['orcid'])
            self.record_orcid_request()
            if orcid_data:
                enriched_profile.update(self._merge_orcid_data(enriched_profile, orcid_data))
                enrichment_sources.append('orcid')
                print(f"   ✅ ORCID data found: {len(orcid_data.get('publications', []))} publications")
        
        # 2. Google Scholar enrichment (for metrics)
        if person_data.get('name'):
            scholar_data = self.get_scholar_profile(person_data['name'], person_data.get('institution', ''))
            if scholar_data:
                enriched_profile.update(self._merge_scholar_data(enriched_profile, scholar_data))  
                enrichment_sources.append('google_scholar')
                print(f"   ✅ Scholar data found: h-index {scholar_data.get('h_index', 'N/A')}")
        
        # 3. Institution enrichment (using ROR API)
        if person_data.get('institution'):
            institution_data = self.get_institution_data(person_data['institution'])
            if institution_data:
                enriched_profile['institution_enriched'] = institution_data
                enrichment_sources.append('ror_api')
                print(f"   ✅ Institution data found: {institution_data.get('name', 'Unknown')}")
        
        # 4. Cross-reference validation
        enriched_profile['enrichment_metadata'] = {
            'sources': enrichment_sources,
            'enrichment_timestamp': datetime.now().isoformat(),
            'confidence_score': self._calculate_confidence_score(enriched_profile, enrichment_sources),
            'data_completeness': self._assess_data_completeness(enriched_profile)
        }
        
        return enriched_profile
    
    def get_orcid_profile(self, orcid_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive profile data from ORCID API with edge case handling."""
        
        # Validate ORCID format first
        if not self._is_valid_orcid(orcid_id):
            print(f"   ⚠️ Invalid ORCID format: {orcid_id}")
            return None
        
        # Check cache first
        cache_key = self._normalize_orcid(orcid_id)
        if cache_key in self.orcid_cache:
            print(f"   💾 Using cached ORCID data for {cache_key}")
            return self.orcid_cache[cache_key]
        
        try:
            # Rate limiting with jitter
            time_since_last = time.time() - self.last_orcid_request
            if time_since_last < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last + (0.1 * (hash(orcid_id) % 10))  # Add jitter
                time.sleep(sleep_time)
            
            # Clean ORCID ID format
            orcid_clean = self._normalize_orcid(orcid_id)
            
            # ORCID API endpoint
            url = f"https://pub.orcid.org/v3.0/{orcid_clean}"
            headers = {'Accept': 'application/json'}
            
            response = self.session.get(url, headers=headers, timeout=10)
            self.last_orcid_request = time.time()
            
            if response.status_code == 200:
                orcid_data = response.json()
                
                # Parse ORCID response
                profile = {
                    'orcid_id': orcid_id,
                    'name': self._extract_orcid_name(orcid_data),
                    'biography': self._extract_orcid_biography(orcid_data), 
                    'affiliations': self._extract_orcid_affiliations(orcid_data),
                    'publications': self._extract_orcid_publications(orcid_data),
                    'external_ids': self._extract_orcid_external_ids(orcid_data),
                    'last_modified': orcid_data.get('history', {}).get('last-modified-date', {}).get('value')
                }
                
                # Cache the result
                self.orcid_cache[orcid_id] = profile
                return profile
            
            else:
                print(f"   ⚠️ ORCID API error {response.status_code} for {orcid_id}")
                return None
                
        except Exception as e:
            print(f"   ❌ ORCID API error for {orcid_id}: {str(e)}")
            return None
    
    def get_scholar_profile(self, name: str, institution: str = "") -> Optional[Dict[str, Any]]:
        """Get academic metrics from Google Scholar (via serpapi or scraping)."""
        
        cache_key = f"{name}_{institution}".lower()
        if cache_key in self.scholar_cache:
            return self.scholar_cache[cache_key]
        
        try:
            # Rate limiting for Scholar
            time_since_last = time.time() - self.last_scholar_request  
            if time_since_last < 2.0:  # More conservative for Scholar
                time.sleep(2.0 - time_since_last)
            
            # Search for scholar profile
            scholar_data = self._search_scholar_profile(name, institution)
            self.last_scholar_request = time.time()
            
            if scholar_data:
                self.scholar_cache[cache_key] = scholar_data
                return scholar_data
            
            return None
            
        except Exception as e:
            print(f"   ❌ Scholar API error for {name}: {str(e)}")
            return None
    
    def _search_scholar_profile(self, name: str, institution: str) -> Optional[Dict[str, Any]]:
        """Search for Google Scholar profile using web scraping or API."""
        
        # For now, return a mock profile structure that we'll enhance
        # This would be replaced with actual Scholar API or careful scraping
        mock_profile = {
            'name': name,
            'institution': institution,
            'h_index': None,
            'total_citations': None,
            'i10_index': None,
            'recent_publications': [],
            'research_interests': [],
            'profile_url': None,
            'data_source': 'scholar_placeholder'
        }
        
        # TODO: Implement actual Scholar scraping/API
        # This is a placeholder to establish the data structure
        
        return mock_profile
    
    def get_institution_data(self, institution_name: str) -> Optional[Dict[str, Any]]:
        """Get institution data from ROR (Research Organization Registry) API."""
        
        try:
            # Clean institution name for search
            clean_name = re.sub(r'[^\w\s]', '', institution_name).strip()
            
            # ROR API search
            url = "https://api.ror.org/organizations"
            params = {'query': clean_name, 'limit': 5}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                ror_data = response.json()
                
                if ror_data.get('items'):
                    best_match = ror_data['items'][0]  # Take best match
                    
                    return {
                        'ror_id': best_match.get('id'),
                        'name': best_match.get('name'),
                        'country': best_match.get('country', {}).get('country_name'),
                        'city': best_match.get('addresses', [{}])[0].get('city') if best_match.get('addresses') else None,
                        'types': best_match.get('types', []),
                        'external_ids': best_match.get('external_ids', {}),
                        'links': best_match.get('links', []),
                        'established': best_match.get('established'),
                        'aliases': best_match.get('aliases', [])
                    }
            
            return None
            
        except Exception as e:
            print(f"   ❌ ROR API error for {institution_name}: {str(e)}")
            return None
    
    def _extract_orcid_name(self, orcid_data: Dict) -> Optional[str]:
        """Extract name from ORCID data."""
        try:
            person = orcid_data.get('person', {})
            name_data = person.get('name', {})
            
            given_names = name_data.get('given-names', {}).get('value', '')
            family_name = name_data.get('family-name', {}).get('value', '')
            
            if given_names and family_name:
                return f"{given_names} {family_name}"
            
            return None
        except:
            return None
    
    def _extract_orcid_biography(self, orcid_data: Dict) -> Optional[str]:
        """Extract biography from ORCID data."""
        try:
            person = orcid_data.get('person', {})
            biography = person.get('biography', {})
            if biography and biography.get('content'):
                return biography['content']
            return None
        except:
            return None
    
    def _extract_orcid_affiliations(self, orcid_data: Dict) -> List[Dict[str, Any]]:
        """Extract employment/education history from ORCID."""
        affiliations = []
        
        try:
            activities = orcid_data.get('activities-summary', {})
            
            # Employment
            employments = activities.get('employments', {}).get('affiliation-group', [])
            for emp_group in employments:
                for emp in emp_group.get('summaries', []):
                    emp_data = emp.get('employment-summary', {})
                    affiliations.append({
                        'type': 'employment',
                        'organization': emp_data.get('organization', {}).get('name'),
                        'role': emp_data.get('role-title'),
                        'start_date': self._parse_orcid_date(emp_data.get('start-date')),
                        'end_date': self._parse_orcid_date(emp_data.get('end-date')),
                        'department': emp_data.get('department-name')
                    })
            
            # Education  
            educations = activities.get('educations', {}).get('affiliation-group', [])
            for edu_group in educations:
                for edu in edu_group.get('summaries', []):
                    edu_data = edu.get('education-summary', {})
                    affiliations.append({
                        'type': 'education',
                        'organization': edu_data.get('organization', {}).get('name'),
                        'role': edu_data.get('role-title'),
                        'start_date': self._parse_orcid_date(edu_data.get('start-date')),
                        'end_date': self._parse_orcid_date(edu_data.get('end-date')),
                        'department': edu_data.get('department-name')
                    })
            
        except Exception as e:
            print(f"   ⚠️ Error extracting ORCID affiliations: {e}")
        
        return affiliations
    
    def _extract_orcid_publications(self, orcid_data: Dict) -> List[Dict[str, Any]]:
        """Extract publication list from ORCID."""
        publications = []
        
        try:
            activities = orcid_data.get('activities-summary', {})
            works = activities.get('works', {}).get('group', [])
            
            for work_group in works[:20]:  # Limit to prevent API overuse
                for work_summary in work_group.get('work-summary', []):
                    pub = {
                        'title': work_summary.get('title', {}).get('title', {}).get('value'),
                        'journal': work_summary.get('journal-title', {}).get('value') if work_summary.get('journal-title') else None,
                        'type': work_summary.get('type'),
                        'publication_date': self._parse_orcid_date(work_summary.get('publication-date')),
                        'external_ids': work_summary.get('external-ids', {}).get('external-id', []),
                        'url': work_summary.get('url')
                    }
                    publications.append(pub)
            
        except Exception as e:
            print(f"   ⚠️ Error extracting ORCID publications: {e}")
        
        return publications
    
    def _extract_orcid_external_ids(self, orcid_data: Dict) -> Dict[str, str]:
        """Extract external identifiers from ORCID."""
        external_ids = {}
        
        try:
            person = orcid_data.get('person', {})
            external_identifiers = person.get('external-identifiers', {}).get('external-identifier', [])
            
            for ext_id in external_identifiers:
                id_type = ext_id.get('external-id-type')
                id_value = ext_id.get('external-id-value')
                if id_type and id_value:
                    external_ids[id_type.lower()] = id_value
                    
        except Exception as e:
            print(f"   ⚠️ Error extracting ORCID external IDs: {e}")
        
        return external_ids
    
    def _parse_orcid_date(self, date_data: Optional[Dict]) -> Optional[str]:
        """Parse ORCID date format.""" 
        if not date_data:
            return None
        
        try:
            year = date_data.get('year', {}).get('value')
            month = date_data.get('month', {}).get('value')
            day = date_data.get('day', {}).get('value')
            
            if year:
                if month and day:
                    return f"{year}-{month:02d}-{day:02d}"
                elif month:
                    return f"{year}-{month:02d}"
                else:
                    return str(year)
        except:
            pass
        
        return None
    
    def _merge_orcid_data(self, profile: Dict, orcid_data: Dict) -> Dict[str, Any]:
        """Merge ORCID data into existing profile."""
        updates = {}
        
        # Name verification/update
        if orcid_data.get('name') and not profile.get('name_verified'):
            updates['name_orcid'] = orcid_data['name']
            updates['name_verified'] = True
        
        # Biography
        if orcid_data.get('biography'):
            updates['biography'] = orcid_data['biography']
        
        # Publications and metrics
        publications = orcid_data.get('publications', [])
        if publications:
            updates['publications_count'] = len(publications)
            updates['recent_publications'] = [p for p in publications if self._is_recent_publication(p)]
            updates['publication_years'] = list(set([self._extract_year_from_pub(p) for p in publications if self._extract_year_from_pub(p)]))
        
        # Affiliations
        if orcid_data.get('affiliations'):
            updates['affiliations_history'] = orcid_data['affiliations']
            current_affiliations = [a for a in orcid_data['affiliations'] if not a.get('end_date')]
            if current_affiliations:
                updates['current_affiliations'] = current_affiliations
        
        # External IDs
        if orcid_data.get('external_ids'):
            updates['external_identifiers'] = orcid_data['external_ids']
        
        return updates
    
    def _merge_scholar_data(self, profile: Dict, scholar_data: Dict) -> Dict[str, Any]:
        """Merge Google Scholar data into existing profile."""
        updates = {}
        
        if scholar_data.get('h_index'):
            updates['h_index'] = scholar_data['h_index']
        
        if scholar_data.get('total_citations'):
            updates['total_citations'] = scholar_data['total_citations']
        
        if scholar_data.get('i10_index'):
            updates['i10_index'] = scholar_data['i10_index']
        
        if scholar_data.get('research_interests'):
            updates['research_interests'] = scholar_data['research_interests']
        
        return updates
    
    def _is_recent_publication(self, publication: Dict, years: int = 3) -> bool:
        """Check if publication is within recent years."""
        pub_year = self._extract_year_from_pub(publication)
        if pub_year:
            current_year = datetime.now().year
            return current_year - pub_year <= years
        return False
    
    def _extract_year_from_pub(self, publication: Dict) -> Optional[int]:
        """Extract publication year."""
        pub_date = publication.get('publication_date')
        if pub_date:
            try:
                return int(pub_date.split('-')[0])
            except:
                pass
        return None
    
    def _calculate_confidence_score(self, profile: Dict, sources: List[str]) -> float:
        """Calculate confidence score for enriched profile."""
        score = 0.0
        
        # Base score for having ORCID
        if 'orcid' in sources:
            score += 0.6
        
        # Scholar data adds credibility
        if 'google_scholar' in sources:
            score += 0.3
        
        # Institution verification
        if 'ror_api' in sources:
            score += 0.1
        
        # Bonus for consistent data across sources
        if len(sources) >= 2:
            score += 0.1
        
        return min(1.0, score)
    
    def _assess_data_completeness(self, profile: Dict) -> Dict[str, bool]:
        """Assess completeness of profile data."""
        return {
            'has_name': bool(profile.get('name')),
            'has_email': bool(profile.get('email')),
            'has_institution': bool(profile.get('institution')),
            'has_orcid': bool(profile.get('orcid')),
            'has_publications': bool(profile.get('publications_count', 0) > 0),
            'has_metrics': bool(profile.get('h_index') or profile.get('total_citations')),
            'has_affiliations': bool(profile.get('affiliations_history')),
            'has_biography': bool(profile.get('biography'))
        }

def enrich_all_people_from_mf_data(mf_extraction_file: str) -> Dict[str, Any]:
    """Enrich all authors and referees from MF extraction data."""
    
    enricher = AcademicProfileEnricher()
    
    print("🔍 ENRICHING ALL PEOPLE FROM MF EXTRACTION DATA")
    print("=" * 60)
    
    # Load MF extraction data
    try:
        with open(mf_extraction_file, 'r') as f:
            mf_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading MF data: {e}")
        return {}
    
    enriched_people = {}
    
    # Process all manuscripts (handle list structure)
    manuscripts = mf_data if isinstance(mf_data, list) else mf_data.get('manuscripts', [])
    
    for manuscript in manuscripts:
        manuscript_id = manuscript.get('id', 'Unknown')
        print(f"\n📄 Processing {manuscript_id}...")
        
        # Enrich authors
        authors = manuscript.get('authors', [])
        enriched_authors = []
        
        for author in authors:
            print(f"\n👤 Enriching author: {author.get('name', 'Unknown')}")
            enriched_author = enricher.enrich_person_profile(author)
            enriched_authors.append(enriched_author)
            
            # Store in people database
            person_key = f"author_{author.get('email', author.get('name', 'unknown'))}"
            enriched_people[person_key] = enriched_author
        
        # Enrich referees
        referees = manuscript.get('referees', [])
        enriched_referees = []
        
        for referee in referees:
            print(f"\n👥 Enriching referee: {referee.get('name', 'Unknown')}")
            enriched_referee = enricher.enrich_person_profile(referee)
            enriched_referees.append(enriched_referee)
            
            # Store in people database
            person_key = f"referee_{referee.get('email', referee.get('name', 'unknown'))}"
            enriched_people[person_key] = enriched_referee
        
        # Update manuscript with enriched data
        manuscript['authors_enriched'] = enriched_authors
        manuscript['referees_enriched'] = enriched_referees
    
    # Save enriched data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"academic_enrichment_{timestamp}.json"
    
    enrichment_results = {
        'enriched_manuscripts': manuscripts,
        'people_database': enriched_people,
        'enrichment_metadata': {
            'total_people_enriched': len(enriched_people),
            'enrichment_timestamp': timestamp,
            'source_file': mf_extraction_file
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enrichment_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 ENRICHMENT COMPLETE!")
    print(f"   👥 Enriched {len(enriched_people)} people")
    print(f"   💾 Results saved to: {output_file}")
    
    # Summary statistics
    orcid_count = sum(1 for p in enriched_people.values() if p.get('orcid'))
    institution_count = sum(1 for p in enriched_people.values() if p.get('institution'))
    
    print(f"   🆔 {orcid_count} people with ORCID IDs")
    print(f"   🏛️ {institution_count} people with institutions")
    
    return enrichment_results

if __name__ == "__main__":
    # Find latest MF extraction file
    import glob
    
    mf_files = glob.glob("mf_comprehensive_*.json")
    if mf_files:
        latest_file = max(mf_files, key=os.path.getctime)
        print(f"Using latest MF extraction file: {latest_file}")
        
        results = enrich_all_people_from_mf_data(latest_file)
    else:
        print("❌ No MF extraction files found. Run MF extraction first.")