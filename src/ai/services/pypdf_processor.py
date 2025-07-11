"""
PDF Processor Implementation using PyPDF2
Async implementation for PDF content extraction and processing
"""

import re
import hashlib
import logging
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ..ports.pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class PyPDFProcessor(PDFProcessor):
    """PDF processor using PyPDF2 for content extraction"""
    
    def __init__(self):
        self.logger = logger
        self._check_dependencies()
    
    def _check_dependencies(self):
        """Check if required dependencies are available"""
        try:
            import PyPDF2
            self.PyPDF2 = PyPDF2
            logger.info("✅ PyPDF2 available for PDF processing")
        except ImportError:
            logger.error("❌ PyPDF2 not installed - PDF processing will be limited")
            self.PyPDF2 = None
    
    async def extract_text_content(self, pdf_path: Path) -> Dict[str, str]:
        """Extract text content from PDF"""
        if not self.PyPDF2:
            return {'error': 'PyPDF2 not available'}
        
        try:
            # Run PDF processing in thread pool to avoid blocking
            return await asyncio.to_thread(self._extract_text_sync, pdf_path)
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            return {
                'title': '',
                'abstract': '',
                'full_text': '',
                'sections': '',
                'error': str(e)
            }
    
    def _extract_text_sync(self, pdf_path: Path) -> Dict[str, str]:
        """Synchronous text extraction for thread pool execution"""
        result = {
            'title': '',
            'abstract': '',
            'full_text': '',
            'sections': ''
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = self.PyPDF2.PdfReader(file)
                
                if len(pdf_reader.pages) == 0:
                    return result
                
                # Extract all text
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        full_text += f"\\n--- Page {page_num + 1} ---\\n{page_text}\\n"
                    except Exception as e:
                        logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                
                result['full_text'] = full_text
                
                # Extract title (usually on first page, often in larger font/caps)
                first_page_text = pdf_reader.pages[0].extract_text() if pdf_reader.pages else ""
                result['title'] = self._extract_title(first_page_text)
                
                # Extract abstract
                result['abstract'] = self._extract_abstract(full_text)
                
                # Extract sections
                result['sections'] = self._extract_sections(full_text)
                
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _extract_title(self, first_page_text: str) -> str:
        """Extract title from first page text using heuristics"""
        if not first_page_text:
            return ""
        
        lines = first_page_text.split('\\n')
        
        # Look for title patterns
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if not line:
                continue
                
            # Skip author/affiliation lines
            if '@' in line or 'university' in line.lower() or 'department' in line.lower():
                continue
            
            # Title is often the first substantial line
            if len(line) > 10 and len(line) < 200:
                # Clean up the title
                title = re.sub(r'[^a-zA-Z0-9\\s\\-\\:\\.\\,\\(\\)]', '', line)
                return title.strip()
        
        return ""
    
    def _extract_abstract(self, full_text: str) -> str:
        """Extract abstract from full text"""
        if not full_text:
            return ""
        
        # Look for abstract section
        abstract_patterns = [
            r'\\babstract\\b\\s*:?\\s*([^\\n]{50,1000})',
            r'\\babstract\\b\\s*([^\\n]{50,1000})',
            r'summary\\s*:?\\s*([^\\n]{50,1000})'
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up the abstract
                abstract = re.sub(r'\\s+', ' ', abstract)
                return abstract[:1000]  # Limit length
        
        # Fallback: try to find first substantial paragraph
        paragraphs = full_text.split('\\n\\n')
        for para in paragraphs:
            para = para.strip()
            if 50 <= len(para) <= 1000 and '.' in para:
                return para
        
        return ""
    
    def _extract_sections(self, full_text: str) -> str:
        """Extract section headers and structure"""
        if not full_text:
            return ""
        
        # Look for section headers
        section_patterns = [
            r'\\n\\s*(\\d+\\.\\s*[A-Z][A-Za-z\\s]{3,50})\\n',
            r'\\n\\s*([A-Z][A-Z\\s]{5,50})\\n',
            r'\\n\\s*(Introduction|Methodology|Results|Discussion|Conclusion)\\s*\\n'
        ]
        
        sections = []
        for pattern in section_patterns:
            matches = re.finditer(pattern, full_text, re.IGNORECASE)
            for match in matches:
                section = match.group(1).strip()
                if section and section not in sections:
                    sections.append(section)
        
        return '; '.join(sections[:10])  # Limit to first 10 sections
    
    async def extract_metadata(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract document metadata from PDF"""
        if not self.PyPDF2:
            return {'error': 'PyPDF2 not available'}
        
        try:
            return await asyncio.to_thread(self._extract_metadata_sync, pdf_path)
        except Exception as e:
            logger.error(f"Failed to extract metadata from {pdf_path}: {e}")
            return {'error': str(e)}
    
    def _extract_metadata_sync(self, pdf_path: Path) -> Dict[str, Any]:
        """Synchronous metadata extraction"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = self.PyPDF2.PdfReader(file)
                
                # Get basic file info
                file_stat = pdf_path.stat()
                
                # Extract PDF metadata
                metadata = {
                    'file_path': str(pdf_path),
                    'file_size': file_stat.st_size,
                    'page_count': len(pdf_reader.pages),
                    'creation_date': datetime.fromtimestamp(file_stat.st_ctime),
                    'modification_date': datetime.fromtimestamp(file_stat.st_mtime),
                    'title': '',
                    'authors': [],
                    'keywords': []
                }
                
                # Try to get PDF document info
                if pdf_reader.metadata:
                    doc_info = pdf_reader.metadata
                    metadata.update({
                        'pdf_title': doc_info.get('/Title', ''),
                        'pdf_author': doc_info.get('/Author', ''),
                        'pdf_subject': doc_info.get('/Subject', ''),
                        'pdf_creator': doc_info.get('/Creator', ''),
                        'pdf_producer': doc_info.get('/Producer', ''),
                        'pdf_creation_date': doc_info.get('/CreationDate', ''),
                        'pdf_modification_date': doc_info.get('/ModDate', '')
                    })
                
                return metadata
                
        except Exception as e:
            logger.error(f"Error extracting metadata from {pdf_path}: {e}")
            return {'error': str(e)}
    
    async def extract_figures_and_tables(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract figures and tables (basic implementation)"""
        # This is a placeholder for more advanced extraction
        # Would require libraries like pdfplumber or camelot for tables
        # and additional image processing for figures
        
        try:
            text_content = await self.extract_text_content(pdf_path)
            full_text = text_content.get('full_text', '')
            
            # Simple heuristic extraction
            figures = []
            tables = []
            equations = []
            
            # Look for figure references
            figure_refs = re.findall(r'Figure\\s+(\\d+)', full_text, re.IGNORECASE)
            for ref in figure_refs:
                figures.append(f"Figure {ref}")
            
            # Look for table references  
            table_refs = re.findall(r'Table\\s+(\\d+)', full_text, re.IGNORECASE)
            for ref in table_refs:
                tables.append(f"Table {ref}")
            
            # Look for equation patterns
            equation_patterns = re.findall(r'\\$[^\\$]+\\$|\\\\begin\\{equation\\}.*?\\\\end\\{equation\\}', full_text, re.DOTALL)
            equations = [eq[:100] for eq in equation_patterns[:10]]  # Limit and truncate
            
            return {
                'figures': figures,
                'tables': tables,
                'equations': equations,
                'extraction_method': 'basic_text_analysis'
            }
            
        except Exception as e:
            logger.error(f"Error extracting figures/tables from {pdf_path}: {e}")
            return {'error': str(e)}
    
    async def get_content_hash(self, pdf_path: Path) -> str:
        """Generate content hash for caching"""
        try:
            return await asyncio.to_thread(self._get_content_hash_sync, pdf_path)
        except Exception as e:
            logger.error(f"Failed to generate hash for {pdf_path}: {e}")
            return ""
    
    def _get_content_hash_sync(self, pdf_path: Path) -> str:
        """Synchronous hash generation"""
        try:
            hasher = hashlib.sha256()
            
            # Hash file content in chunks
            with open(pdf_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            logger.error(f"Error generating hash for {pdf_path}: {e}")
            return ""
    
    async def validate_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Validate PDF and assess extraction quality"""
        validation = {
            'is_valid': False,
            'is_readable': False,
            'quality_score': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        try:
            # Check if file exists and is readable
            if not pdf_path.exists():
                validation['issues'].append('File does not exist')
                return validation
            
            if not pdf_path.is_file():
                validation['issues'].append('Path is not a file')
                return validation
            
            # Try to open and validate PDF
            if self.PyPDF2:
                result = await asyncio.to_thread(self._validate_pdf_sync, pdf_path)
                validation.update(result)
            else:
                validation['issues'].append('PyPDF2 not available for validation')
            
        except Exception as e:
            validation['issues'].append(f"Validation error: {str(e)}")
        
        return validation
    
    def _validate_pdf_sync(self, pdf_path: Path) -> Dict[str, Any]:
        """Synchronous PDF validation"""
        validation = {
            'is_valid': False,
            'is_readable': False,
            'quality_score': 0.0,
            'issues': [],
            'recommendations': []
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = self.PyPDF2.PdfReader(file)
                
                # Basic validation
                page_count = len(pdf_reader.pages)
                validation['is_valid'] = page_count > 0
                
                if page_count == 0:
                    validation['issues'].append('PDF has no pages')
                    return validation
                
                # Test text extraction
                total_text = ""
                readable_pages = 0
                
                for page in pdf_reader.pages:
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            total_text += page_text
                            readable_pages += 1
                    except Exception:
                        pass
                
                validation['is_readable'] = readable_pages > 0
                
                if readable_pages == 0:
                    validation['issues'].append('No readable text found')
                    validation['recommendations'].append('PDF may be image-based - consider OCR')
                
                # Calculate quality score
                if readable_pages > 0:
                    text_density = len(total_text) / page_count
                    readability_ratio = readable_pages / page_count
                    
                    # Simple quality scoring
                    if text_density > 1000 and readability_ratio > 0.8:
                        validation['quality_score'] = 0.9
                    elif text_density > 500 and readability_ratio > 0.5:
                        validation['quality_score'] = 0.7
                    elif text_density > 100:
                        validation['quality_score'] = 0.5
                    else:
                        validation['quality_score'] = 0.3
                        validation['issues'].append('Low text density - may be image-heavy')
                
                # Additional checks
                if page_count > 50:
                    validation['recommendations'].append('Large document - consider processing in chunks')
                
                if readability_ratio < 0.5:
                    validation['recommendations'].append('Many pages unreadable - check for images or scanned content')
                
        except Exception as e:
            validation['issues'].append(f"PDF validation failed: {str(e)}")
        
        return validation