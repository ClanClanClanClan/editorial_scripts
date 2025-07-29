#!/usr/bin/env python3
"""
Google Scholar metrics extraction for academic profile enrichment.
Extracts h-index, citation counts, i10-index, and publication data.
"""

import os
import re
import json
import time
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from urllib.parse import quote, urlencode
from bs4 import BeautifulSoup
import random

class GoogleScholarScraper:
    """Extract academic metrics from Google Scholar profiles."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.logger = logging.getLogger(__name__)
        
        # Rate limiting to avoid blocking
        self.last_request_time = 0
        self.min_delay = 3.0  # seconds between requests
        self.max_delay = 8.0
        
        # Cache for profiles
        self.profile_cache = {}
    
    def search_scholar_profile(self, name: str, institution: str = "", affiliation_keywords: List[str] = None) -> Optional[Dict[str, Any]]:
        """Search for a scholar's Google Scholar profile."""
        
        cache_key = f"{name.lower()}_{institution.lower()}"
        if cache_key in self.profile_cache:
            return self.profile_cache[cache_key]
        
        try:
            print(f"   🔍 Searching Scholar for: {name} ({institution})")
            
            # Apply rate limiting
            self._apply_rate_limit()
            
            # Search for the scholar using name and institution
            search_results = self._search_scholar_profiles(name, institution)
            
            if not search_results:
                print(f"   ❌ No Scholar profiles found for {name}")
                return None
            
            # Find the best matching profile
            best_profile = self._select_best_profile(search_results, name, institution, affiliation_keywords)
            
            if best_profile:
                # Get detailed profile data
                profile_data = self._extract_profile_details(best_profile['profile_url'], name)
                
                if profile_data:
                    self.profile_cache[cache_key] = profile_data
                    print(f"   ✅ Scholar profile found: h-index {profile_data.get('h_index', 'N/A')}, {profile_data.get('total_citations', 0)} citations")
                    return profile_data
            
            print(f"   ⚠️ No suitable Scholar profile found for {name}")
            return None
            
        except Exception as e:
            print(f"   ❌ Scholar search error for {name}: {str(e)}")
            return None
    
    def _apply_rate_limit(self):
        """Apply rate limiting to avoid being blocked."""
        elapsed = time.time() - self.last_request_time
        delay = random.uniform(self.min_delay, self.max_delay)
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            print(f"   ⏳ Rate limiting: sleeping {sleep_time:.1f}s")
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _search_scholar_profiles(self, name: str, institution: str = "") -> List[Dict[str, str]]:
        """Search for scholar profiles matching the given name and institution."""
        
        # Construct search query
        query_parts = [name]
        if institution:
            # Extract key institutional terms
            inst_keywords = self._extract_institution_keywords(institution)
            query_parts.extend(inst_keywords[:2])  # Add top 2 keywords
        
        query = ' '.join(query_parts)
        
        # Google Scholar search URL
        search_url = "https://scholar.google.com/citations"
        params = {
            'view_op': 'search_authors',
            'mauthors': query,
            'hl': 'en'
        }
        
        try:
            response = self.session.get(search_url, params=params, timeout=15)
            
            if response.status_code == 200:
                return self._parse_search_results(response.text, name)
            else:
                print(f"   ⚠️ Scholar search returned status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"   ❌ Scholar search request failed: {e}")
            return []
    
    def _parse_search_results(self, html: str, target_name: str) -> List[Dict[str, str]]:
        """Parse Google Scholar search results to extract profile candidates."""
        
        try:
            soup = BeautifulSoup(html, 'html.parser')
            profiles = []
            
            # Find profile containers
            profile_divs = soup.find_all('div', class_='gs_ai_chpr')
            
            for div in profile_divs[:5]:  # Limit to top 5 results
                try:
                    # Extract profile link
                    link_elem = div.find('a', href=True)
                    if not link_elem:
                        continue
                    
                    profile_url = "https://scholar.google.com" + link_elem['href']
                    
                    # Extract name
                    name_elem = div.find('h3', class_='gs_ai_name')
                    name = name_elem.get_text().strip() if name_elem else ""
                    
                    # Extract affiliation
                    affil_elem = div.find('div', class_='gs_ai_aff')
                    affiliation = affil_elem.get_text().strip() if affil_elem else ""
                    
                    # Extract field/interests
                    interests_elem = div.find('div', class_='gs_ai_int')
                    interests = interests_elem.get_text().strip() if interests_elem else ""
                    
                    # Extract citation info if available
                    cited_elem = div.find('div', class_='gs_ai_cby')
                    citations_text = cited_elem.get_text().strip() if cited_elem else ""
                    
                    profiles.append({
                        'name': name,
                        'profile_url': profile_url,
                        'affiliation': affiliation,
                        'interests': interests,
                        'citations_text': citations_text,
                        'name_similarity': self._calculate_name_similarity(name, target_name)
                    })
                    
                except Exception as e:
                    print(f"   ⚠️ Error parsing profile result: {e}")
                    continue
            
            return profiles
            
        except Exception as e:
            print(f"   ❌ Error parsing Scholar search results: {e}")
            return []
    
    def _select_best_profile(self, profiles: List[Dict[str, str]], target_name: str, 
                           target_institution: str, affiliation_keywords: List[str] = None) -> Optional[Dict[str, str]]:
        """Select the best matching profile from search results."""
        
        if not profiles:
            return None
        
        # Score each profile
        scored_profiles = []
        
        for profile in profiles:
            score = 0.0
            
            # Name similarity (most important)
            name_sim = profile.get('name_similarity', 0.0)
            score += name_sim * 0.6
            
            # Institution/affiliation match
            if target_institution:
                affil_sim = self._calculate_affiliation_similarity(
                    profile.get('affiliation', ''), target_institution
                )
                score += affil_sim * 0.3
            
            # Additional affiliation keywords match
            if affiliation_keywords:
                for keyword in affiliation_keywords:
                    if keyword.lower() in profile.get('affiliation', '').lower():
                        score += 0.05
            
            # Prefer profiles with citations (indicates active researcher)
            if profile.get('citations_text'):
                score += 0.05
            
            scored_profiles.append((score, profile))
        
        # Sort by score and return best match if score is reasonable
        scored_profiles.sort(key=lambda x: x[0], reverse=True)
        best_score, best_profile = scored_profiles[0]
        
        if best_score >= 0.3:  # Minimum threshold for reasonable match
            return best_profile
        
        return None
    
    def _extract_profile_details(self, profile_url: str, name: str) -> Optional[Dict[str, Any]]:
        """Extract detailed metrics from a Google Scholar profile page."""
        
        try:
            self._apply_rate_limit()
            
            response = self.session.get(profile_url, timeout=15)
            
            if response.status_code != 200:
                print(f"   ⚠️ Profile page returned status {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract profile information
            profile_data = {
                'name': self._extract_profile_name(soup),
                'profile_url': profile_url,
                'affiliation': self._extract_profile_affiliation(soup),
                'interests': self._extract_research_interests(soup),
                'h_index': self._extract_h_index(soup),
                'total_citations': self._extract_total_citations(soup),
                'i10_index': self._extract_i10_index(soup),
                'recent_publications': self._extract_recent_publications(soup),
                'citation_years': self._extract_citation_by_year(soup),
                'verified_email': self._extract_verified_email(soup),
                'extraction_timestamp': datetime.now().isoformat(),
                'confidence_score': self._calculate_profile_confidence(soup, name)
            }
            
            return profile_data
            
        except Exception as e:
            print(f"   ❌ Error extracting profile details: {e}")
            return None
    
    def _extract_profile_name(self, soup: BeautifulSoup) -> str:
        """Extract the scholar's name from profile page."""
        try:
            name_elem = soup.find('div', id='gsc_prf_in')
            if name_elem:
                return name_elem.get_text().strip()
        except:
            pass
        return ""
    
    def _extract_profile_affiliation(self, soup: BeautifulSoup) -> str:
        """Extract affiliation from profile page."""
        try:
            affil_elem = soup.find('div', class_='gsc_prf_il')
            if affil_elem:
                return affil_elem.get_text().strip()
        except:
            pass
        return ""
    
    def _extract_research_interests(self, soup: BeautifulSoup) -> List[str]:
        """Extract research interests/fields."""
        try:
            interests = []
            interest_elems = soup.find_all('a', class_='gsc_prf_inta')
            for elem in interest_elems:
                interests.append(elem.get_text().strip())
            return interests
        except:
            return []
    
    def _extract_h_index(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract h-index from citation metrics."""
        try:
            # Find the citation table
            table = soup.find('table', id='gsc_rsb_st')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2 and 'h-index' in cells[0].get_text():
                        h_index_text = cells[1].get_text().strip()
                        return int(h_index_text)
        except:
            pass
        return None
    
    def _extract_total_citations(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract total citation count."""
        try:
            table = soup.find('table', id='gsc_rsb_st')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2 and 'Citations' in cells[0].get_text():
                        citations_text = cells[1].get_text().strip()
                        return int(citations_text)
        except:
            pass
        return None
    
    def _extract_i10_index(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract i10-index from citation metrics."""
        try:
            table = soup.find('table', id='gsc_rsb_st')
            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2 and 'i10-index' in cells[0].get_text():
                        i10_text = cells[1].get_text().strip()
                        return int(i10_text)
        except:
            pass
        return None
    
    def _extract_recent_publications(self, soup: BeautifulSoup, limit: int = 10) -> List[Dict[str, Any]]:
        """Extract recent publications list."""
        publications = []
        
        try:
            pub_rows = soup.find_all('tr', class_='gsc_a_tr')
            
            for row in pub_rows[:limit]:
                try:
                    # Extract title
                    title_elem = row.find('a', class_='gsc_a_at')
                    title = title_elem.get_text().strip() if title_elem else ""
                    
                    # Extract authors
                    author_elem = row.find('div', class_='gs_gray')
                    authors = author_elem.get_text().strip() if author_elem else ""
                    
                    # Extract year
                    year_elem = row.find('span', class_='gsc_a_y')
                    year = year_elem.get_text().strip() if year_elem else ""
                    
                    # Extract citation count
                    cite_elem = row.find('a', class_='gsc_a_ac')
                    citations = cite_elem.get_text().strip() if cite_elem else "0"
                    citations = int(citations) if citations.isdigit() else 0
                    
                    publications.append({
                        'title': title,
                        'authors': authors,
                        'year': int(year) if year.isdigit() else None,
                        'citations': citations
                    })
                    
                except Exception as e:
                    print(f"   ⚠️ Error parsing publication: {e}")
                    continue
        
        except Exception as e:
            print(f"   ⚠️ Error extracting publications: {e}")
        
        return publications
    
    def _extract_citation_by_year(self, soup: BeautifulSoup) -> Dict[int, int]:
        """Extract citation counts by year."""
        citation_years = {}
        
        try:
            # Look for citation graph data (if available)
            # This is more complex to parse and may not always be present
            pass
        except:
            pass
        
        return citation_years
    
    def _extract_verified_email(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract verified email domain if available."""
        try:
            email_elem = soup.find('div', id='gsc_prf_ivh')
            if email_elem:
                email_text = email_elem.get_text().strip()
                if '@' in email_text:
                    return email_text
        except:
            pass
        return None
    
    def _calculate_profile_confidence(self, soup: BeautifulSoup, target_name: str) -> float:
        """Calculate confidence score for profile match."""
        score = 0.0
        
        try:
            # Check if name matches well
            profile_name = self._extract_profile_name(soup)
            if profile_name:
                name_sim = self._calculate_name_similarity(profile_name, target_name)
                score += name_sim * 0.5
            
            # Check if has verified email
            if self._extract_verified_email(soup):
                score += 0.2
            
            # Check if has reasonable number of citations/publications
            citations = self._extract_total_citations(soup)
            if citations and citations > 0:
                score += 0.2
            
            # Check if has h-index
            h_index = self._extract_h_index(soup)
            if h_index and h_index > 0:
                score += 0.1
                
        except:
            pass
        
        return min(1.0, score)
    
    def _extract_institution_keywords(self, institution: str) -> List[str]:
        """Extract key terms from institution name for searching."""
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'of', 'and', 'for', 'in', 'at', 'university', 'college', 'institute', 'school'}
        
        words = re.findall(r'\b[A-Za-z]{3,}\b', institution.lower())
        keywords = [w for w in words if w not in stop_words]
        
        return keywords[:3]  # Return top 3 keywords
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        try:
            # Simple name similarity based on common words
            words1 = set(re.findall(r'\b[A-Za-z]+\b', name1.lower()))
            words2 = set(re.findall(r'\b[A-Za-z]+\b', name2.lower()))
            
            if not words1 or not words2:
                return 0.0
            
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            return intersection / union if union > 0 else 0.0
            
        except:
            return 0.0
    
    def _calculate_affiliation_similarity(self, affil1: str, affil2: str) -> float:
        """Calculate similarity between affiliations."""
        try:
            # Extract key terms from both affiliations
            terms1 = set(self._extract_institution_keywords(affil1))
            terms2 = set(self._extract_institution_keywords(affil2))
            
            if not terms1 or not terms2:
                return 0.0
            
            intersection = len(terms1.intersection(terms2))
            union = len(terms1.union(terms2))
            
            return intersection / union if union > 0 else 0.0
            
        except:
            return 0.0

def enrich_with_scholar_metrics(enrichment_file: str) -> Dict[str, Any]:
    """Enrich existing academic profiles with Google Scholar metrics."""
    
    scraper = GoogleScholarScraper()
    
    print("🔍 ENRICHING PROFILES WITH GOOGLE SCHOLAR METRICS")
    print("=" * 60)
    
    # Load existing enrichment data
    try:
        with open(enrichment_file, 'r') as f:
            enrichment_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading enrichment data: {e}")
        return {}
    
    people_db = enrichment_data.get('people_database', {})
    
    print(f"Found {len(people_db)} people to enrich with Scholar metrics")
    
    enriched_count = 0
    
    for person_id, person_data in people_db.items():
        name = person_data.get('name', '')
        institution = person_data.get('institution', '')
        
        if not name:
            continue
        
        print(f"\n👤 Enriching {person_id}: {name}")
        
        # Search for Scholar profile
        scholar_data = scraper.search_scholar_profile(
            name, 
            institution,
            affiliation_keywords=person_data.get('affiliations_history', [])
        )
        
        if scholar_data:
            # Merge Scholar data into person profile
            person_data['scholar_metrics'] = scholar_data
            person_data['h_index'] = scholar_data.get('h_index')
            person_data['total_citations'] = scholar_data.get('total_citations')
            person_data['i10_index'] = scholar_data.get('i10_index')
            person_data['research_interests'] = scholar_data.get('interests', [])
            person_data['recent_publications_scholar'] = scholar_data.get('recent_publications', [])
            
            enriched_count += 1
        
        # Be respectful with rate limiting
        if enriched_count % 3 == 0:
            print("   💤 Taking a longer break to avoid rate limiting...")
            time.sleep(random.uniform(10, 20))
    
    # Save enriched data
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"scholar_enriched_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(enrichment_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 SCHOLAR ENRICHMENT COMPLETE!")
    print(f"   📊 Enriched {enriched_count}/{len(people_db)} people with Scholar metrics")
    print(f"   💾 Results saved to: {output_file}")
    
    # Summary statistics
    h_index_count = sum(1 for p in people_db.values() if p.get('h_index'))
    citation_count = sum(1 for p in people_db.values() if p.get('total_citations'))
    
    print(f"   📈 {h_index_count} people with h-index")
    print(f"   📚 {citation_count} people with citation counts")
    
    return enrichment_data

if __name__ == "__main__":
    # Find latest academic enrichment file
    import glob
    
    enrichment_files = glob.glob("academic_enrichment_*.json")
    if enrichment_files:
        latest_file = max(enrichment_files, key=os.path.getctime)
        print(f"Using latest enrichment file: {latest_file}")
        
        results = enrich_with_scholar_metrics(latest_file)
    else:
        print("❌ No academic enrichment files found. Run academic enrichment first.")