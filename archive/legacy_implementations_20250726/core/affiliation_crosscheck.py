"""
Affiliation Cross-checking Module
=================================

Provides multiple strategies to find referee affiliations when missing from platform data.
"""

import re
import time
import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AffiliationCrossChecker:
    """Cross-check referee affiliations using multiple sources."""
    
    def __init__(self):
        self.cache = {}
        self.email_domain_map = self._load_domain_mappings()
        
    def _load_domain_mappings(self) -> Dict[str, str]:
        """Load known email domain to institution mappings."""
        return {
            # UK Universities
            'warwick.ac.uk': 'University of Warwick',
            'wbs.ac.uk': 'Warwick Business School',
            'ed.ac.uk': 'University of Edinburgh',
            'cam.ac.uk': 'University of Cambridge',
            'ox.ac.uk': 'University of Oxford',
            'imperial.ac.uk': 'Imperial College London',
            'ucl.ac.uk': 'University College London',
            'lse.ac.uk': 'London School of Economics',
            
            # US Universities
            'berkeley.edu': 'University of California, Berkeley',
            'stanford.edu': 'Stanford University',
            'mit.edu': 'Massachusetts Institute of Technology',
            'harvard.edu': 'Harvard University',
            'princeton.edu': 'Princeton University',
            'yale.edu': 'Yale University',
            'columbia.edu': 'Columbia University',
            'nyu.edu': 'New York University',
            
            # European Universities
            'math.ethz.ch': 'ETH Zurich',
            'ethz.ch': 'ETH Zurich',
            'epfl.ch': 'École Polytechnique Fédérale de Lausanne',
            'univ-lemans.fr': 'Le Mans University',
            'sorbonne-universite.fr': 'Sorbonne University',
            'polytechnique.edu': 'École Polytechnique',
            'ens.fr': 'École Normale Supérieure',
            
            # Other institutions
            'gmail.com': None,  # Personal email, no institution
            'yahoo.com': None,
            'hotmail.com': None,
        }
    
    def enhance_referee_data(self, referee: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance referee data with cross-checked affiliation info."""
        name = referee.get('name', '')
        email = referee.get('email', '')
        orcid = referee.get('orcid', '')
        current_affiliation = referee.get('affiliation', '')
        
        # Skip if we already have a good affiliation (not just the name)
        # Check various name formats to detect name-only affiliations
        name_variations = [name]
        
        # Handle "First Last" format
        if ',' not in name:
            parts = name.split()
            if len(parts) >= 2:
                # Add "Last, First" variation
                name_variations.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
        else:
            # Handle "Last, First" format
            parts = name.split(',', 1)
            if len(parts) == 2:
                # Add "First Last" variation
                name_variations.append(f"{parts[1].strip()} {parts[0].strip()}")
                
        # Check if current affiliation is just a name variation
        is_name_only = current_affiliation in name_variations
        
        if current_affiliation and not is_name_only:
            return referee
            
        # Check cache first
        cache_key = f"{name}:{email}"
        if cache_key in self.cache:
            referee.update(self.cache[cache_key])
            return referee
            
        enhanced_data = {}
        
        # 1. Try ORCID API
        if orcid:
            orcid_data = self.get_affiliation_from_orcid(orcid)
            if orcid_data:
                enhanced_data.update(orcid_data)
                
        # 2. Try email domain inference
        if not enhanced_data.get('institution') and email:
            institution = self.infer_institution_from_email(email)
            if institution:
                enhanced_data['institution'] = institution
                enhanced_data['institution_source'] = 'email_domain'
                
        # 3. Try Semantic Scholar API
        if not enhanced_data.get('institution'):
            semantic_data = self.search_semantic_scholar(name, email)
            if semantic_data:
                enhanced_data.update(semantic_data)
                
        # Update referee data
        if enhanced_data:
            referee.update(enhanced_data)
            self.cache[cache_key] = enhanced_data
            
        return referee
    
    def get_affiliation_from_orcid(self, orcid_url: str) -> Optional[Dict[str, Any]]:
        """Fetch affiliation from ORCID public API."""
        try:
            # Extract ORCID ID from URL
            orcid_id = orcid_url.rstrip('/').split('/')[-1]
            
            # ORCID public API endpoint
            api_url = f"https://pub.orcid.org/v3.0/{orcid_id}/employments"
            headers = {'Accept': 'application/json'}
            
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Get current employment (first one is usually current)
                for group in data.get('employment-summary', []):
                    summaries = group.get('summaries', [])
                    if summaries:
                        employment = summaries[0]
                        org = employment.get('employment-summary', {}).get('organization', {})
                        
                        result = {
                            'institution': org.get('name'),
                            'institution_source': 'orcid',
                        }
                        
                        # Get country if available
                        address = org.get('address', {})
                        if address.get('country'):
                            result['country'] = address['country']
                            
                        # Get department if available
                        dept = employment.get('employment-summary', {}).get('department-name')
                        if dept:
                            result['department'] = dept
                            
                        # Try to get ROR ID from disambiguated org ID
                        disambiguated = org.get('disambiguated-organization', {})
                        if disambiguated.get('disambiguated-organization-identifier'):
                            result['external_id'] = disambiguated['disambiguated-organization-identifier']
                            result['external_id_type'] = disambiguated.get('disambiguation-source')
                            
                        return result
                        
            elif response.status_code == 404:
                logger.warning(f"ORCID {orcid_id} not found")
            else:
                logger.warning(f"ORCID API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching ORCID data: {e}")
            
        return None
    
    def infer_institution_from_email(self, email: str) -> Optional[str]:
        """Infer institution from email domain."""
        if not email or '@' not in email:
            return None
            
        domain = email.split('@')[-1].lower()
        
        # Check exact matches first
        if domain in self.email_domain_map:
            return self.email_domain_map[domain]
            
        # Try subdomain matching (e.g., cs.stanford.edu -> stanford.edu)
        parts = domain.split('.')
        if len(parts) > 2:
            parent_domain = '.'.join(parts[-2:])
            if parent_domain in self.email_domain_map:
                return self.email_domain_map[parent_domain]
                
        # Generic patterns
        if domain.endswith('.edu'):
            # US educational institution
            institution_part = parts[0] if len(parts) > 2 else domain.split('.')[0]
            return f"{institution_part.upper()} University"
            
        elif domain.endswith('.ac.uk'):
            # UK academic institution
            institution_part = parts[0] if len(parts) > 2 else domain.split('.')[0]
            return f"University of {institution_part.title()}"
            
        elif domain.endswith('.edu.au'):
            # Australian university
            institution_part = parts[0] if len(parts) > 2 else domain.split('.')[0]
            return f"{institution_part.upper()} University"
            
        elif any(domain.endswith(suffix) for suffix in ['.fr', '.de', '.ch', '.nl', '.be']):
            # European institution - harder to infer
            if 'univ' in domain:
                return f"University ({domain})"
                
        return None
    
    def search_semantic_scholar(self, name: str, email: str = None) -> Optional[Dict[str, Any]]:
        """Search for researcher using Semantic Scholar API."""
        try:
            # Clean name for search
            search_name = name.strip()
            if ',' in search_name:
                # Convert "Last, First" to "First Last"
                parts = search_name.split(',', 1)
                search_name = f"{parts[1].strip()} {parts[0].strip()}"
                
            # Search for author
            search_url = "https://api.semanticscholar.org/graph/v1/author/search"
            params = {'query': search_name, 'limit': 5}
            
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                authors = data.get('data', [])
                
                # Try to find best match
                for author in authors:
                    author_id = author.get('authorId')
                    author_name = author.get('name', '')
                    
                    # Check name similarity
                    if self._names_match(search_name, author_name):
                        # Get detailed author info
                        detail_url = f"https://api.semanticscholar.org/graph/v1/author/{author_id}"
                        params = {'fields': 'affiliations,homepage,paperCount'}
                        
                        detail_response = requests.get(detail_url, params=params, timeout=10)
                        
                        if detail_response.status_code == 200:
                            author_data = detail_response.json()
                            
                            affiliations = author_data.get('affiliations', [])
                            if affiliations:
                                return {
                                    'institution': affiliations[0],
                                    'institution_source': 'semantic_scholar',
                                    'paper_count': author_data.get('paperCount', 0)
                                }
                                
        except Exception as e:
            logger.error(f"Error searching Semantic Scholar: {e}")
            
        return None
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two names likely refer to the same person."""
        # Simple implementation - could be enhanced with fuzzy matching
        name1_parts = set(name1.lower().split())
        name2_parts = set(name2.lower().split())
        
        # At least last name should match
        return len(name1_parts.intersection(name2_parts)) >= 1
    
    def get_ror_id(self, institution_name: str) -> Optional[str]:
        """Get ROR (Research Organization Registry) ID for institution."""
        if not institution_name:
            return None
            
        try:
            # ROR API endpoint
            api_url = "https://api.ror.org/organizations"
            params = {'query': institution_name}
            
            response = requests.get(api_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get('items', [])
                
                if items:
                    # Take the first match (highest score)
                    best_match = items[0]
                    return best_match.get('id')  # ROR ID like https://ror.org/xxxxx
                    
        except Exception as e:
            logger.error(f"Error fetching ROR ID: {e}")
            
        return None


# Singleton instance
affiliation_checker = AffiliationCrossChecker()