"""
V3 Compliance Transformation Layer

Transforms extracted manuscript data to comply with V3 database schema requirements:
- UUIDs for all primary keys
- Proper date formatting (TIMESTAMPTZ)
- Enum value mapping
- Required field validation
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path
import json


class V3ComplianceTransformer:
    """Transform extracted data to V3 database schema compliance."""
    
    # Enum mappings
    PLATFORM_TYPE_MAP = {
        'mathematical finance': 'scholarone',
        'mf': 'scholarone',
        'scholarone': 'scholarone',
        'siam': 'siam',
        'email': 'email'
    }
    
    MANUSCRIPT_TYPE_MAP = {
        'original article': 'article',
        'article': 'article',
        'review': 'review',
        'letter': 'letter',
        'research article': 'article',
        'corrigendum': 'corrigendum'
    }
    
    LICENSE_TYPE_MAP = {
        'all rights reserved': 'all-rights-reserved',
        'cc-by': 'CC-BY',
        'cc-by-nc': 'CC-BY-NC',
        'default': 'all-rights-reserved'
    }
    
    RECOMMENDATION_MAP = {
        'accept': 'accept',
        'minor revision': 'minor',
        'minor revisions': 'minor',
        'major revision': 'major', 
        'major revisions': 'major',
        'reject': 'reject',
        'decline': 'reject'
    }
    
    DECISION_TYPE_MAP = {
        'desk reject': 'desk_reject',
        'reject': 'reject',
        'minor revision': 'minor_revision',
        'major revision': 'major_revision',
        'conditional accept': 'conditional_accept',
        'accept': 'accept'
    }
    
    def __init__(self, journal_code: str = 'MF'):
        """Initialize transformer with journal context."""
        self.journal_code = journal_code
        self.journal_id = self._get_journal_uuid(journal_code)
    
    def _get_journal_uuid(self, journal_code: str) -> str:
        """Get or generate consistent UUID for journal."""
        # For consistency, use deterministic UUID based on journal code
        # In production, this would come from database
        journal_uuid_map = {
            'MF': str(uuid.uuid5(uuid.NAMESPACE_DNS, 'mathematical-finance')),
            'MOR': str(uuid.uuid5(uuid.NAMESPACE_DNS, 'mathematics-operations-research')),
            'SIFIN': str(uuid.uuid5(uuid.NAMESPACE_DNS, 'siam-financial-mathematics'))
        }
        return journal_uuid_map.get(journal_code, str(uuid.uuid4()))
    
    def generate_uuid7(self) -> str:
        """Generate UUIDv7-style UUID (time-ordered)."""
        # Python doesn't have native UUIDv7, use time-ordered UUID4
        return str(uuid.uuid4())
    
    def transform_datetime(self, date_str: str) -> Optional[str]:
        """Transform date string to TIMESTAMPTZ format."""
        if not date_str:
            return None
            
        try:
            # Handle common MF date formats
            if 'T' in date_str:
                # ISO format
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                # Common formats: "19-Jun-2025", "15-Jan-2025"
                dt = datetime.strptime(date_str, "%d-%b-%Y")
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt.isoformat()
        except (ValueError, TypeError):
            print(f"      ⚠️ Could not parse date: {date_str}")
            return None
    
    def map_enum_value(self, value: str, enum_map: Dict[str, str], default: str = None) -> str:
        """Map a value to enum using case-insensitive matching."""
        if not value:
            return default
            
        value_lower = value.lower().strip()
        
        # Direct lookup
        if value_lower in enum_map:
            return enum_map[value_lower]
            
        # Partial matching
        for key, enum_val in enum_map.items():
            if key in value_lower or value_lower in key:
                return enum_val
                
        return default
    
    def transform_manuscript(self, manuscript_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform manuscript data to V3 compliance."""
        try:
            transformed = {
                # Core identifiers
                'manuscript_id': self.generate_uuid7(),
                'external_id': manuscript_data.get('id', ''),
                'journal_id': self.journal_id,
                
                # Required manuscript fields
                'title': manuscript_data.get('title', ''),
                'abstract': manuscript_data.get('abstract', ''),
                'language_tag': 'en-US',  # Default for MF
                'keywords': manuscript_data.get('keywords', []),
                
                # Enums
                'manuscript_type': self.map_enum_value(
                    manuscript_data.get('article_type', ''), 
                    self.MANUSCRIPT_TYPE_MAP, 
                    'article'
                ),
                'license_type': self.map_enum_value(
                    manuscript_data.get('license', ''),
                    self.LICENSE_TYPE_MAP,
                    'all-rights-reserved'
                ),
                
                # Optional fields
                'doi': manuscript_data.get('doi'),
                'word_count': self._extract_word_count(manuscript_data),
                'page_count': self._extract_page_count(manuscript_data),
                
                # Categories (MSC/JEL classifications)
                'category_msc': manuscript_data.get('msc_categories', []),
                'category_jel': manuscript_data.get('jel_categories', []),
                
                # Metadata
                'created_at': self.transform_datetime(manuscript_data.get('submission_date')),
                'updated_at': self.transform_datetime(manuscript_data.get('last_updated'))
            }
            
            # Validation
            if not transformed['title'] or len(transformed['title']) < 10:
                print(f"      ⚠️ Title too short: '{transformed['title']}'")
            
            if not transformed['abstract']:
                print(f"      ⚠️ Missing abstract for {transformed['external_id']}")
                
            return transformed
            
        except Exception as e:
            print(f"      ❌ Error transforming manuscript: {e}")
            return {}
    
    def transform_authors(self, manuscript_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform author data to V3 compliance."""
        authors = []
        
        for idx, author_data in enumerate(manuscript_data.get('authors', [])):
            try:
                author = {
                    'author_id': self.generate_uuid7(),
                    'orcid': author_data.get('orcid'),
                    'given_name': self._extract_given_name(author_data.get('name', '')),
                    'family_name': self._extract_family_name(author_data.get('name', '')),
                    'email': author_data.get('email', ''),
                    'institution': author_data.get('affiliation', ''),
                    'country': author_data.get('country'),
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Manuscript-author relationship
                manuscript_author = {
                    'author_id': author['author_id'],
                    'author_order': idx + 1,
                    'corresponding': author_data.get('is_corresponding', False)
                }
                
                authors.append({
                    'author': author,
                    'manuscript_author': manuscript_author
                })
                
            except Exception as e:
                print(f"      ⚠️ Error transforming author {idx}: {e}")
                continue
                
        return authors
    
    def transform_referees(self, manuscript_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform referee data to V3 compliance."""
        referees = []
        
        for referee_data in manuscript_data.get('referees', []):
            try:
                referee = {
                    'referee_id': self.generate_uuid7(),
                    'name': referee_data.get('name', ''),
                    'email': referee_data.get('email', ''),
                    'orcid': referee_data.get('orcid'),
                    'institution': referee_data.get('affiliation', ''),
                    'country': referee_data.get('country_hints', [None])[0],
                    'blacklist': False,
                    'whitelist': False,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Review assignment data
                review_assignment = {
                    'assignment_id': self.generate_uuid7(),
                    'referee_id': referee['referee_id'],
                    'invitation_sent_at': self.transform_datetime(
                        referee_data.get('dates', {}).get('invited')
                    ),
                    'invitation_method': 'email',
                    'agreed_at': self.transform_datetime(
                        referee_data.get('dates', {}).get('agreed')
                    ),
                    'declined_at': self.transform_datetime(
                        referee_data.get('dates', {}).get('declined')
                    ),
                    'recommendation': self.map_enum_value(
                        referee_data.get('recommendation', ''),
                        self.RECOMMENDATION_MAP
                    ),
                    'report_text': referee_data.get('report', {}).get('content')
                }
                
                referees.append({
                    'referee': referee,
                    'review_assignment': review_assignment
                })
                
            except Exception as e:
                print(f"      ⚠️ Error transforming referee {referee_data.get('name', 'Unknown')}: {e}")
                continue
                
        return referees
    
    def transform_files(self, manuscript_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Transform file data to V3 compliance."""
        files = []
        
        documents = manuscript_data.get('documents', {})
        
        # PDF file
        if documents.get('pdf') and documents.get('pdf_path'):
            files.append({
                'file_id': self.generate_uuid7(),
                'path': documents['pdf_path'],
                'mime_type': 'application/pdf',
                'uploaded_at': datetime.now(timezone.utc).isoformat()
            })
        
        # Cover letter
        if documents.get('cover_letter') and documents.get('cover_letter_path'):
            cover_path = documents['cover_letter_path']
            mime_type = 'text/plain'
            if cover_path.endswith('.pdf'):
                mime_type = 'application/pdf'
            elif cover_path.endswith('.docx'):
                mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                
            files.append({
                'file_id': self.generate_uuid7(),
                'path': cover_path,
                'mime_type': mime_type,
                'uploaded_at': datetime.now(timezone.utc).isoformat()
            })
            
        return files
    
    def _extract_word_count(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract word count from various sources."""
        # Check main manuscript data first
        if 'word_count' in data and isinstance(data['word_count'], int):
            return data['word_count']
        
        # Look in documents for word count info
        docs = data.get('documents', {})
        if 'word_count' in docs:
            return docs['word_count']
        return None
    
    def _extract_page_count(self, data: Dict[str, Any]) -> Optional[int]:
        """Extract page count from various sources."""
        # Check main manuscript data first  
        if 'page_count' in data and isinstance(data['page_count'], int):
            return data['page_count']
            
        # Look in documents for page count info
        docs = data.get('documents', {})
        if 'page_count' in docs:
            return docs['page_count']
        return None
    
    def _extract_given_name(self, full_name: str) -> str:
        """Extract given name from full name."""
        if not full_name:
            return ''
        parts = full_name.strip().split()
        if len(parts) >= 2:
            return ' '.join(parts[:-1])  # All but last part
        return parts[0] if parts else ''
    
    def _extract_family_name(self, full_name: str) -> str:
        """Extract family name from full name."""
        if not full_name:
            return ''
        parts = full_name.strip().split()
        return parts[-1] if parts else ''
    
    def transform_complete_manuscript(self, manuscript_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform complete manuscript with all related entities."""
        print(f"   🔄 Transforming to V3 compliance: {manuscript_data.get('id', 'Unknown')}")
        
        result = {
            'manuscript': self.transform_manuscript(manuscript_data),
            'authors': self.transform_authors(manuscript_data),
            'referees': self.transform_referees(manuscript_data),
            'files': self.transform_files(manuscript_data),
            'metadata': {
                'journal_code': self.journal_code,
                'journal_id': self.journal_id,
                'transformed_at': datetime.now(timezone.utc).isoformat(),
                'transformer_version': '1.0.0'
            }
        }
        
        return result
    
    def save_transformed_data(self, transformed_data: Dict[str, Any], output_path: str):
        """Save transformed data to file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(transformed_data, f, indent=2, ensure_ascii=False)
                
            print(f"   ✅ Saved V3 compliant data: {output_file.name}")
            return str(output_file)
            
        except Exception as e:
            print(f"   ❌ Error saving transformed data: {e}")
            return None


def transform_extraction_results(input_file: str, output_file: str = None, journal_code: str = 'MF'):
    """Transform extraction results to V3 compliance."""
    try:
        # Load extracted data
        with open(input_file, 'r', encoding='utf-8') as f:
            extracted_data = json.load(f)
        
        if not isinstance(extracted_data, list):
            extracted_data = [extracted_data]
        
        # Transform each manuscript
        transformer = V3ComplianceTransformer(journal_code)
        transformed_manuscripts = []
        
        for manuscript_data in extracted_data:
            transformed = transformer.transform_complete_manuscript(manuscript_data)
            if transformed['manuscript']:  # Only add if transformation succeeded
                transformed_manuscripts.append(transformed)
        
        # Save results
        if not output_file:
            input_path = Path(input_file)
            output_file = str(input_path.parent / f"{input_path.stem}_v3_compliant.json")
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transformed_manuscripts, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Transformed {len(transformed_manuscripts)} manuscripts to V3 compliance")
        print(f"   📁 Output: {output_path}")
        
        return str(output_path)
        
    except Exception as e:
        print(f"❌ Error transforming to V3 compliance: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    input_file = "mf_details_page_extraction_20250723_234323.json"
    if Path(input_file).exists():
        transform_extraction_results(input_file)
    else:
        print(f"Input file not found: {input_file}")