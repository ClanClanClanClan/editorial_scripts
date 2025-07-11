#!/usr/bin/env python3
"""
Ultra-Enhanced PDF Metadata Parser – **REPOSITORY & JOURNAL SPECIALIST**
Handles SSRN, published papers, and complex academic document formats

MAJOR ULTRA-ENHANCEMENTS:
1. SSRN-specific parsing with header detection and cleanup
2. Published journal paper handling with multi-column support
3. Advanced text preprocessing with line reconstruction
4. Sophisticated author-affiliation separation
5. Multi-line title detection and reconstruction
6. Repository-specific metadata extraction
7. Journal format recognition and parsing
8. Robust fallback strategies for edge cases
"""

import regex as re
import os
import sys
from pathlib import Path
import unicodedata
from datetime import datetime
import yaml
import logging
import warnings
from typing import Optional, Tuple, List, Dict, Set, Any, Union
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from enum import Enum
import time
import hashlib
from functools import lru_cache

# Add current directory to path
current_dir = Path(__file__).parent.resolve()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Heavy PDF libraries
OFFLINE = bool(os.getenv("PDF_PARSER_OFFLINE")) or "PYTEST_CURRENT_TEST" in os.environ

if not OFFLINE:
    try:
        import fitz
    except ImportError:
        fitz = None
else:
    fitz = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

# Import sophisticated functions
try:
    from main import fix_author_block
    HAS_MAIN_FUNCTIONS = True
except ImportError:
    HAS_MAIN_FUNCTIONS = False

try:
    from filename_checker import to_sentence_case_academic
    HAS_FILENAME_CHECKER = True
except ImportError:
    HAS_FILENAME_CHECKER = False

# Setup logging
logger = logging.getLogger('ultra_pdf_parser')
warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────────────────────────────────────
# BASE CLASSES AND CONSTANTS
# ──────────────────────────────────────────────────────────────────────────────

class MetadataSource(Enum):
    """Source of extracted metadata"""
    UNKNOWN = "unknown"
    HEURISTIC = "heuristic"
    FILENAME = "filename"
    API = "api"
    REPOSITORY = "repository"

class PDFConstants:
    """Constants for PDF processing"""
    MAX_AUTHORS = 10
    MAX_FILENAME_LEN = 255
    MAX_TITLE_LEN = 200
    MAX_TEXT_LENGTH = 500000  # 500KB text limit
    DEFAULT_TIMEOUT = 30  # seconds

@dataclass
class PDFMetadata:
    """Metadata extracted from PDF"""
    title: str = "Unknown Title"
    authors: str = "Unknown"
    source: MetadataSource = MetadataSource.UNKNOWN
    confidence: float = 0.0
    filename: str = ""
    path: str = ""
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'title': self.title,
            'authors': self.authors,
            'source': self.source.value,
            'confidence': self.confidence,
            'filename': self.filename,
            'path': self.path,
            'error': self.error,
            'warnings': self.warnings,
            'processing_time': self.processing_time
        }

class LimitedCache:
    """Simple LRU cache with size limit"""
    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self.cache = {}
        self.access_order = []
    
    def __contains__(self, key):
        return key in self.cache
    
    def __getitem__(self, key):
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        raise KeyError(key)
    
    def __setitem__(self, key, value):
        if key in self.cache:
            # Update existing
            self.cache[key] = value
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new
            if len(self.cache) >= self.maxsize:
                # Remove least recently used
                oldest = self.access_order.pop(0)
                del self.cache[oldest]
            self.cache[key] = value
            self.access_order.append(key)

def clean_text(text: str) -> str:
    """Clean text for processing"""
    if not text:
        return ""
    
    # Normalize unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove null bytes and control characters
    text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\t')
    
    return text.strip()

# Mock api_session for compatibility
class MockAPISession:
    def get(self, *args, **kwargs):
        raise NotImplementedError("API session not available")

api_session = MockAPISession()

# ──────────────────────────────────────────────────────────────────────────────
# ENHANCED DATA STRUCTURES
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class TextBlock:
    """Represents a block of text with position and formatting info"""
    text: str
    x: float
    y: float
    width: float
    height: float
    font_size: float = 0.0
    font_name: str = ""
    is_bold: bool = False
    page_num: int = 0
    
    @property
    def center_x(self) -> float:
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

@dataclass
class DocumentStructure:
    """Represents the overall structure of a document"""
    title_candidates: List[Tuple[str, float, Dict[str, Any]]]  # (text, score, metadata)
    author_candidates: List[Tuple[str, float, Dict[str, Any]]]
    repository_type: Optional[str] = None
    is_published: bool = False
    is_multi_column: bool = False
    has_header_footer: bool = False
    language: str = "en"
    
@dataclass 
class ExtractionMetrics:
    """Metrics for extraction quality assessment"""
    confidence_title: float = 0.0
    confidence_authors: float = 0.0
    text_quality_score: float = 0.0
    structure_score: float = 0.0
    repository_match_score: float = 0.0

# ──────────────────────────────────────────────────────────────────────────────
# REPOSITORY-SPECIFIC PATTERNS
# ──────────────────────────────────────────────────────────────────────────────

class RepositoryPatterns:
    """Repository-specific patterns and extractors"""
    
    SSRN_PATTERNS = {
        'header_indicators': [
            r'electronic copy available at.*ssrn\.com',
            r'ssrn electronic library',
            r'social science research network',
            r'posted at the ssrn',
            r'ssrn\.com/abstract=\d+',
            r'available at ssrn:.*abstract.*=.*\d+',
        ],
        'title_markers': [
            r'(?:title|paper title)\s*:?\s*',
            r'(?:working )?paper\s*:?\s*',
        ],
        'author_markers': [
            r'(?:authors?|by)\s*:?\s*',
            r'(?:affiliations?)\s*:?\s*',
        ],
        'metadata_noise': [
            r'electronic copy available at.*',
            r'posted at.*ssrn.*',
            r'last revised.*\d{4}',
            r'this paper can be downloaded.*',
            r'abstract.*\d+.*http.*',
        ]
    }
    
    ARXIV_PATTERNS = {
        'header_indicators': [
            r'arxiv:\d{4}\.\d{4,5}',
            r'submitted to.*arxiv',
            r'preprint.*arxiv',
        ],
        'version_patterns': [
            r'v\d+\s+\d{1,2}\s+\w+\s+\d{4}',
            r'submitted on.*\d{4}',
            r'last revised.*\d{4}',
        ],
        'category_patterns': [
            r'\[[\w\-\.]+\]',  # [cs.LG], [math.PR], etc.
        ]
    }
    
    NBER_PATTERNS = {
        'header_indicators': [
            r'nber working paper',
            r'national bureau of economic research',
            r'working paper \d+',
            r'nber\.org',
        ],
        'series_patterns': [
            r'working paper no\.\s*\d+',
            r'nber working paper series',
        ]
    }
    
    JOURNAL_PATTERNS = {
        'publisher_indicators': [
            r'elsevier',
            r'springer',
            r'wiley',
            r'taylor.*francis',
            r'oxford.*press',
            r'cambridge.*press',
            r'ieee',
            r'acm',
            r'sage publications',
        ],
        'journal_markers': [
            r'journal of.*',
            r'proceedings of.*',
            r'transactions on.*',
            r'ieee transactions.*',
            r'acm transactions.*',
        ],
        'copyright_patterns': [
            r'©\s*\d{4}.*(?:elsevier|springer|wiley|ieee|acm)',
            r'copyright.*\d{4}',
            r'all rights reserved',
        ]
    }

# ──────────────────────────────────────────────────────────────────────────────
# ULTRA-ENHANCED PDF PARSER
# ──────────────────────────────────────────────────────────────────────────────

class UltraEnhancedPDFParser:
    """Ultra-enhanced PDF parser specialized for repositories and journals"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with enhanced capabilities"""
        self.config = self._load_config(config_path)
        self._init_patterns()
        self._init_caches()
        self._init_extractors()
        
        # Statistics
        self.stats = {
            "processed": 0, "errors": 0, "total_time": 0,
            "ssrn_detected": 0, "arxiv_detected": 0, "journal_detected": 0,
            "multi_column_detected": 0, "title_reconstructed": 0
        }
        
        logger.info("Ultra-Enhanced PDF Parser initialized with repository & journal support")
    
    def _load_config(self, path: str) -> dict:
        """Load configuration with enhanced defaults"""
        defaults = {
            "extraction": {
                "max_pages": 5,
                "enable_position_analysis": True,
                "enable_font_analysis": True,
                "multi_column_threshold": 0.6,
                "title_max_lines": 4,
                "author_max_lines": 3,
            },
            "repositories": {
                "enable_ssrn_parser": True,
                "enable_arxiv_parser": True,
                "enable_nber_parser": True,
                "enable_journal_parser": True,
            },
            "scoring": {
                "position_weight": 0.3,
                "font_weight": 0.2,
                "length_weight": 0.2,
                "content_weight": 0.3,
            }
        }
        
        try:
            if Path(path).exists():
                with open(path, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                # Merge configs
                return self._deep_merge(defaults, user_config)
        except Exception as e:
            logger.warning(f"Config load error: {e}")
        
        return defaults
    
    def _deep_merge(self, base: dict, update: dict) -> dict:
        """Deep merge dictionaries"""
        result = base.copy()
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _init_patterns(self):
        """Initialize enhanced pattern matching"""
        self.patterns = {
            # Enhanced title patterns
            'title_indicators': re.compile(
                r'^\s*(?:'
                r'title\s*:?\s*|'
                r'paper\s+title\s*:?\s*|'
                r'working\s+paper\s*:?\s*'
                r')', re.I
            ),
            
            # Enhanced author patterns
            'author_indicators': re.compile(
                r'^\s*(?:'
                r'authors?\s*:?\s*|'
                r'by\s*:?\s*|'
                r'written\s+by\s*:?\s*'
                r')', re.I
            ),
            
            # Affiliation patterns
            'affiliation_indicators': re.compile(
                r'(?:'
                r'university|college|institute|school|'
                r'department|faculty|division|center|centre|'
                r'laboratory|lab|research|'
                r'federal\s+reserve|bank\s+of|'
                r'ministry|government|bureau|'
                r'corporation|company|inc\.|ltd\.|llc'
                r')', re.I
            ),
            
            # Email and URL patterns
            'email_pattern': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'url_pattern': re.compile(r'https?://[^\s]+'),
            
            # Footnote and reference markers
            'footnote_markers': re.compile(r'[\*\†\‡\§\¶\#\¹\²\³\⁴\⁵\⁶\⁷\⁸\⁹\⁰]+'),
            'reference_pattern': re.compile(r'^\s*references?\s*$', re.I),
            
            # Date patterns
            'date_pattern': re.compile(
                r'\b(?:'
                r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}|'
                r'\d{1,2}[/-]\d{1,2}[/-]\d{4}|'
                r'\d{4}[/-]\d{1,2}[/-]\d{1,2}'
                r')\b', re.I
            ),
            
            # Page number patterns
            'page_number': re.compile(r'^\s*\d{1,4}\s*$'),
            
            # Section headers
            'section_header': re.compile(
                r'^\s*(?:\d+\.?\s*)?(?:'
                r'abstract|introduction|methodology|methods|results|discussion|'
                r'conclusion|references|appendix|acknowledgments|'
                r'literature\s+review|data|empirical\s+analysis'
                r')\s*$', re.I
            ),
        }
    
    def _init_caches(self):
        """Initialize caches"""
        self.text_cache = LimitedCache(maxsize=500)
        self.structure_cache = LimitedCache(maxsize=200)
        self.extraction_cache = LimitedCache(maxsize=1000)
    
    def _init_extractors(self):
        """Initialize specialized extractors"""
        self.repository_extractors = {
            'ssrn': SSRNExtractor(),
            'arxiv': ArxivExtractor(), 
            'nber': NBERExtractor(),
            'journal': JournalExtractor(),
        }
    
    # ────────────────────────────────────────────────────────────────────
    # ENHANCED TEXT EXTRACTION WITH POSITION DATA
    # ────────────────────────────────────────────────────────────────────
    
    def extract_enhanced_text(self, pdf_path: str) -> Tuple[str, List[TextBlock], DocumentStructure]:
        """Extract text with position and formatting information"""
        cache_key = f"enhanced_text_{hashlib.md5(pdf_path.encode()).hexdigest()}"
        if cache_key in self.text_cache:
            return self.text_cache[cache_key]
        
        text_blocks = []
        full_text_lines = []
        
        # Try PyMuPDF for enhanced extraction if available
        if fitz and not OFFLINE:
            try:
                text_blocks, full_text_lines = self._extract_with_pymupdf(pdf_path)
            except Exception as e:
                logger.debug(f"PyMuPDF extraction failed: {e}")
        
        # Fallback to pdfplumber
        if not text_blocks and pdfplumber:
            try:
                text_blocks, full_text_lines = self._extract_with_pdfplumber(pdf_path)
            except Exception as e:
                logger.debug(f"pdfplumber extraction failed: {e}")
        
        # Basic text extraction fallback
        if not full_text_lines:
            full_text_lines = ["Failed to extract text"]
        
        full_text = "\n".join(full_text_lines)
        document_structure = self._analyze_document_structure(text_blocks, full_text)
        
        result = (full_text, text_blocks, document_structure)
        self.text_cache[cache_key] = result
        return result
    
    def _extract_with_pymupdf(self, pdf_path: str) -> Tuple[List[TextBlock], List[str]]:
        """Extract with PyMuPDF including position data"""
        doc = fitz.open(pdf_path)
        text_blocks = []
        text_lines = []
        
        max_pages = min(self.config["extraction"]["max_pages"], len(doc))
        
        for page_num in range(max_pages):
            page = doc.load_page(page_num)
            
            # Get text with position information
            if hasattr(page, 'get_text') and hasattr(page, 'get_textpage'):
                try:
                    # Get detailed text information
                    text_dict = page.get_text("dict")
                    page_blocks = self._process_pymupdf_blocks(text_dict, page_num)
                    text_blocks.extend(page_blocks)
                except:
                    # Fallback to simple text extraction
                    page_text = page.get_text()
                    text_lines.extend(page_text.split('\n'))
            else:
                # Basic extraction
                page_text = page.get_text()
                text_lines.extend(page_text.split('\n'))
        
        doc.close()
        
        # Convert text blocks to lines if we have blocks
        if text_blocks:
            # Sort by position and create lines
            sorted_blocks = sorted(text_blocks, key=lambda b: (b.page_num, b.y, b.x))
            text_lines = [block.text for block in sorted_blocks if block.text.strip()]
        
        return text_blocks, text_lines
    
    def _process_pymupdf_blocks(self, text_dict: dict, page_num: int) -> List[TextBlock]:
        """Process PyMuPDF text dictionary into TextBlock objects"""
        blocks = []
        
        for block in text_dict.get("blocks", []):
            if "lines" in block:  # Text block
                for line in block["lines"]:
                    line_text_parts = []
                    total_bbox = line.get("bbox", [0, 0, 0, 0])
                    max_font_size = 0
                    font_names = []
                    is_bold = False
                    
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            line_text_parts.append(text)
                            # Track font information
                            font_size = span.get("size", 0)
                            if font_size > max_font_size:
                                max_font_size = font_size
                            
                            font_name = span.get("font", "")
                            if font_name:
                                font_names.append(font_name)
                                # Check for bold indicators in font name
                                if any(indicator in font_name.lower() for indicator in ['bold', 'heavy', 'black']):
                                    is_bold = True
                    
                    if line_text_parts:
                        full_text = " ".join(line_text_parts)
                        if len(full_text.strip()) > 0:
                            blocks.append(TextBlock(
                                text=full_text,
                                x=total_bbox[0],
                                y=total_bbox[1], 
                                width=total_bbox[2] - total_bbox[0],
                                height=total_bbox[3] - total_bbox[1],
                                font_size=max_font_size if max_font_size > 0 else 12.0,
                                font_name=font_names[0] if font_names else "",
                                is_bold=is_bold,
                                page_num=page_num
                            ))
        
        return blocks
    
    def _extract_with_pdfplumber(self, pdf_path: str) -> Tuple[List[TextBlock], List[str]]:
        """Extract with pdfplumber including basic position data"""
        text_blocks = []
        text_lines = []
        
        with pdfplumber.open(pdf_path) as pdf:
            max_pages = min(self.config["extraction"]["max_pages"], len(pdf.pages))
            
            for page_num in range(max_pages):
                page = pdf.pages[page_num]
                
                # Try to get character-level data
                try:
                    chars = page.chars
                    if chars:
                        # Group characters into lines
                        line_groups = self._group_chars_into_lines(chars)
                        for line_text, bbox in line_groups:
                            if line_text.strip():
                                text_blocks.append(TextBlock(
                                    text=line_text,
                                    x=bbox[0],
                                    y=bbox[1],
                                    width=bbox[2] - bbox[0],
                                    height=bbox[3] - bbox[1],
                                    page_num=page_num
                                ))
                                text_lines.append(line_text)
                except:
                    # Fallback to simple text extraction
                    page_text = page.extract_text()
                    if page_text:
                        lines = page_text.split('\n')
                        text_lines.extend(lines)
                        # Create dummy text blocks
                        for i, line in enumerate(lines):
                            if line.strip():
                                text_blocks.append(TextBlock(
                                    text=line,
                                    x=0, y=i*20, width=500, height=15,
                                    page_num=page_num
                                ))
        
        return text_blocks, text_lines
    
    def _group_chars_into_lines(self, chars: List[dict]) -> List[Tuple[str, Tuple[float, float, float, float]]]:
        """Group character data into lines with bounding boxes"""
        if not chars:
            return []
        
        # Sort characters by position
        sorted_chars = sorted(chars, key=lambda c: (-c.get('y0', 0), c.get('x0', 0)))
        
        lines = []
        current_line_chars = []
        current_y = None
        y_tolerance = 5  # Tolerance for considering chars on same line
        
        for char in sorted_chars:
            char_y = char.get('y0', 0)
            
            if current_y is None or abs(char_y - current_y) <= y_tolerance:
                # Same line
                current_line_chars.append(char)
                current_y = char_y
            else:
                # New line
                if current_line_chars:
                    line_text, bbox = self._chars_to_line(current_line_chars)
                    if line_text.strip():
                        lines.append((line_text, bbox))
                
                current_line_chars = [char]
                current_y = char_y
        
        # Process last line
        if current_line_chars:
            line_text, bbox = self._chars_to_line(current_line_chars)
            if line_text.strip():
                lines.append((line_text, bbox))
        
        return lines
    
    def _chars_to_line(self, chars: List[dict]) -> Tuple[str, Tuple[float, float, float, float]]:
        """Convert character list to line text and bounding box"""
        if not chars:
            return "", (0, 0, 0, 0)
        
        # Sort by x position
        sorted_chars = sorted(chars, key=lambda c: c.get('x0', 0))
        
        # Extract text
        text = "".join(c.get('text', '') for c in sorted_chars)
        
        # Calculate bounding box
        x_coords = [c.get('x0', 0) for c in chars] + [c.get('x1', 0) for c in chars]
        y_coords = [c.get('y0', 0) for c in chars] + [c.get('y1', 0) for c in chars]
        
        bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
        
        return text, bbox
    
    # ────────────────────────────────────────────────────────────────────
    # DOCUMENT STRUCTURE ANALYSIS
    # ────────────────────────────────────────────────────────────────────
    
    def _analyze_document_structure(self, text_blocks: List[TextBlock], full_text: str) -> DocumentStructure:
        """Analyze document structure and characteristics"""
        structure = DocumentStructure(title_candidates=[], author_candidates=[])
        
        # Detect repository type
        structure.repository_type = self._detect_repository_type(full_text)
        
        # Detect if published paper
        structure.is_published = self._detect_published_paper(full_text)
        
        # Detect multi-column layout
        structure.is_multi_column = self._detect_multi_column_layout(text_blocks)
        
        # Detect header/footer
        structure.has_header_footer = self._detect_header_footer(text_blocks)
        
        # Detect language
        structure.language = self._detect_language(full_text)
        
        return structure
    
    def _detect_repository_type(self, text: str) -> Optional[str]:
        """Detect the type of repository or publisher"""
        text_lower = text.lower()
        
        # Check SSRN
        ssrn_indicators = [
            'ssrn', 'social science research network', 'ssrn.com',
            'electronic copy available at', 'posted at the ssrn'
        ]
        if any(indicator in text_lower for indicator in ssrn_indicators):
            return 'ssrn'
        
        # Check arXiv
        if re.search(r'arxiv:\d{4}\.\d{4,5}', text_lower) or 'arxiv.org' in text_lower:
            return 'arxiv'
        
        # Check NBER
        nber_indicators = ['nber', 'national bureau of economic research']
        if any(indicator in text_lower for indicator in nber_indicators):
            return 'nber'
        
        # Check if it's a published journal
        journal_indicators = [
            'elsevier', 'springer', 'wiley', 'ieee', 'acm',
            'journal of', 'proceedings of', 'transactions on'
        ]
        if any(indicator in text_lower for indicator in journal_indicators):
            return 'journal'
        
        return None
    
    def _detect_published_paper(self, text: str) -> bool:
        """Detect if this is a published paper vs working paper"""
        text_lower = text.lower()
        
        published_indicators = [
            'journal of', 'proceedings of', 'transactions on',
            'published in', 'appears in', 'copyright',
            'all rights reserved', 'doi:', '© 20'
        ]
        
        working_indicators = [
            'working paper', 'discussion paper', 'draft',
            'preliminary', 'work in progress', 'comments welcome'
        ]
        
        published_score = sum(1 for indicator in published_indicators if indicator in text_lower)
        working_score = sum(1 for indicator in working_indicators if indicator in text_lower)
        
        return published_score > working_score
    
    def _detect_multi_column_layout(self, text_blocks: List[TextBlock]) -> bool:
        """Detect if document has multi-column layout"""
        if len(text_blocks) < 10:
            return False
        
        # Group blocks by page
        pages = defaultdict(list)
        for block in text_blocks:
            pages[block.page_num].append(block)
        
        multi_column_pages = 0
        
        for page_blocks in pages.values():
            if len(page_blocks) < 5:
                continue
            
            # Check x-position distribution
            x_positions = [block.center_x for block in page_blocks]
            x_positions.sort()
            
            # Look for gaps that might indicate columns
            gaps = []
            for i in range(1, len(x_positions)):
                gap = x_positions[i] - x_positions[i-1]
                if gap > 50:  # Significant gap
                    gaps.append(gap)
            
            # If we have significant gaps, likely multi-column
            if len(gaps) >= 2 and max(gaps) > 100:
                multi_column_pages += 1
        
        return multi_column_pages > 0
    
    def _detect_header_footer(self, text_blocks: List[TextBlock]) -> bool:
        """Detect presence of headers/footers"""
        if len(text_blocks) < 5:
            return False
        
        # Group by page and find repeated elements at top/bottom
        pages = defaultdict(list)
        for block in text_blocks:
            pages[block.page_num].append(block)
        
        if len(pages) < 2:
            return False
        
        # Check for repeated content at similar positions across pages
        top_content = {}
        bottom_content = {}
        
        for page_num, blocks in pages.items():
            if not blocks:
                continue
                
            sorted_blocks = sorted(blocks, key=lambda b: b.y)
            
            # Top elements
            if sorted_blocks:
                top_y = max(b.y for b in sorted_blocks)
                top_blocks = [b for b in sorted_blocks if abs(b.y - top_y) < 20]
                for block in top_blocks[:2]:  # Top 2 blocks
                    content = block.text.strip()
                    if len(content) > 5 and len(content) < 100:
                        top_content[content] = top_content.get(content, 0) + 1
            
            # Bottom elements  
            if sorted_blocks:
                bottom_y = min(b.y for b in sorted_blocks)
                bottom_blocks = [b for b in sorted_blocks if abs(b.y - bottom_y) < 20]
                for block in bottom_blocks[:2]:  # Bottom 2 blocks
                    content = block.text.strip()
                    if len(content) > 2 and len(content) < 50:
                        bottom_content[content] = bottom_content.get(content, 0) + 1
        
        # Check for repeated content
        repeated_top = any(count > 1 for count in top_content.values())
        repeated_bottom = any(count > 1 for count in bottom_content.values())
        
        return repeated_top or repeated_bottom
    
    def _detect_language(self, text: str) -> str:
        """Detect document language"""
        # Simple language detection based on common words
        text_sample = text[:2000].lower()
        
        # English indicators
        english_words = ['the', 'and', 'of', 'to', 'in', 'for', 'with', 'on', 'by', 'this', 'that', 'we', 'our', 'analysis']
        english_score = sum(1 for word in english_words if word in text_sample)
        
        # French indicators
        french_words = ['le', 'la', 'les', 'de', 'du', 'des', 'et', 'une', 'dans', 'pour', 'avec', 'sur', 'analyse']
        french_score = sum(1 for word in french_words if word in text_sample)
        
        # German indicators
        german_words = ['der', 'die', 'das', 'und', 'für', 'von', 'mit', 'zu', 'auf', 'über', 'durch', 'analyse']
        german_score = sum(1 for word in german_words if word in text_sample)
        
        scores = {'en': english_score, 'fr': french_score, 'de': german_score}
        return max(scores, key=scores.get) if max(scores.values()) > 3 else 'en'
    
    # ────────────────────────────────────────────────────────────────────
    # ENHANCED TITLE EXTRACTION
    # ────────────────────────────────────────────────────────────────────
    
    def extract_title_enhanced(self, text_blocks: List[TextBlock], full_text: str, 
                              document_structure: DocumentStructure) -> Tuple[str, float]:
        """Enhanced title extraction with multi-line support and repository awareness"""
        
        # Use repository-specific extractor if available
        if document_structure.repository_type in self.repository_extractors:
            extractor = self.repository_extractors[document_structure.repository_type]
            repo_title = extractor.extract_title(full_text, text_blocks)
            if repo_title:
                return repo_title, 0.9
        
        title_candidates = []
        
        # Method 1: Position-based extraction with text blocks
        if text_blocks:
            position_candidates = self._extract_title_by_position(text_blocks, document_structure)
            title_candidates.extend(position_candidates)
        
        # Method 2: Pattern-based extraction from full text
        pattern_candidates = self._extract_title_by_patterns(full_text, document_structure)
        title_candidates.extend(pattern_candidates)
        
        # Method 3: Multi-line title reconstruction
        multiline_candidates = self._extract_multiline_titles(text_blocks, full_text)
        title_candidates.extend(multiline_candidates)
        
        # Score and select best candidate
        if title_candidates:
            scored_candidates = []
            for title, base_score, metadata in title_candidates:
                enhanced_score = self._score_title_candidate_enhanced(
                    title, base_score, metadata, document_structure, full_text
                )
                scored_candidates.append((title, enhanced_score, metadata))
            
            # Sort by score and return best
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            best_title, best_score, _ = scored_candidates[0]
            
            # Clean and format the title
            cleaned_title = self._clean_and_format_title(best_title)
            return cleaned_title, best_score
        
        return "Unknown Title", 0.0
    
    def _extract_title_by_position(self, text_blocks: List[TextBlock], 
                                  document_structure: DocumentStructure) -> List[Tuple[str, float, Dict]]:
        """Extract title candidates based on position analysis"""
        candidates = []
        
        if not text_blocks:
            return candidates
        
        # Group blocks by page (focus on first page)
        first_page_blocks = [block for block in text_blocks if block.page_num == 0]
        if not first_page_blocks:
            return candidates
        
        # Sort by position (top to bottom, left to right)
        # Note: PDF coordinates have Y=0 at bottom, so smaller Y values are at top
        sorted_blocks = sorted(first_page_blocks, key=lambda b: (b.y, b.x))
        
        # Calculate average font size to identify larger fonts
        font_sizes = [b.font_size for b in sorted_blocks if b.font_size > 0]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 12
        
        # Find the main content area (skip headers/footers)
        content_start_idx = 0
        for idx, block in enumerate(sorted_blocks[:10]):
            if self._is_repository_header(block.text) or self._is_date_or_metadata(block.text):
                content_start_idx = idx + 1
            else:
                break
        
        # Skip obvious headers and repository info
        filtered_blocks = []
        for idx, block in enumerate(sorted_blocks[content_start_idx:30]):  # Consider more blocks
            text = block.text.strip()
            
            # More strict filtering
            if len(text) < 10 or len(text) > 300:
                continue
            if self._is_repository_header(text):
                continue
            if self._is_date_or_metadata(text):
                continue
            if self.patterns['email_pattern'].search(text):
                continue
            if self.patterns['url_pattern'].search(text):
                continue
            if self._looks_like_author_name(text):
                continue  # Skip author names
            if text.lower().startswith(('abstract', 'keywords', 'jel')):
                break  # Stop at abstract section
            
            # Check if this could be a title based on content
            if self._has_title_characteristics(text, block, avg_font_size):
                filtered_blocks.append(block)
        
        # Analyze top candidates
        for i, block in enumerate(filtered_blocks[:5]):  # Reduce to top 5
            text = block.text.strip()
            
            # Enhanced scoring based on title characteristics
            position_score = max(0, (5 - i) / 5) * 0.4
            
            # Strong font size bonus
            font_bonus = 0
            if block.font_size > 0 and avg_font_size > 0:
                if block.font_size > avg_font_size * 1.2:  # 20% larger than average
                    font_bonus = 0.4
                elif block.font_size > avg_font_size:
                    font_bonus = 0.2
            
            # Content quality score
            content_score = self._score_title_quality(text, sorted_blocks) * 0.4
            
            total_score = position_score + font_bonus + content_score
            
            metadata = {
                'position_rank': i,
                'y_position': block.y,
                'font_size': block.font_size,
                'avg_font_size': avg_font_size,
                'content_start': content_start_idx,
                'extraction_method': 'position'
            }
            
            candidates.append((text, total_score, metadata))
        
        return candidates
    
    def _extract_title_by_patterns(self, text: str, 
                                  document_structure: DocumentStructure) -> List[Tuple[str, float, Dict]]:
        """Extract title candidates using pattern matching"""
        candidates = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines[:30]):  # Only check first 30 lines
            line = line.strip()
            if len(line) < 10 or len(line) > 300:
                continue
            
            score = 0
            metadata = {'line_number': i, 'extraction_method': 'pattern'}
            
            # Check for explicit title markers
            if self.patterns['title_indicators'].match(line):
                # Extract title after marker
                title_match = self.patterns['title_indicators'].sub('', line).strip()
                if title_match:
                    score = 0.8
                    candidates.append((title_match, score, metadata))
                continue
            
            # Score based on position
            position_score = max(0, (30 - i) / 30) * 0.5
            
            # Score based on content characteristics
            content_score = self._score_title_content(line)
            
            total_score = position_score + content_score
            
            if total_score > 0.3:  # Minimum threshold
                candidates.append((line, total_score, metadata))
        
        return candidates
    
    def _extract_multiline_titles(self, text_blocks: List[TextBlock], full_text: str) -> List[Tuple[str, float, Dict]]:
        """Extract multi-line title candidates"""
        candidates = []
        
        if not text_blocks:
            return candidates
        
        # Group consecutive blocks that might form a multi-line title
        first_page_blocks = sorted([b for b in text_blocks if b.page_num == 0], key=lambda b: (b.y, b.x))
        
        max_lines = self.config["extraction"]["title_max_lines"]
        
        for start_idx in range(min(10, len(first_page_blocks))):  # Start from top 10 blocks
            for length in range(2, min(max_lines + 1, len(first_page_blocks) - start_idx + 1)):
                # Get consecutive blocks
                block_group = first_page_blocks[start_idx:start_idx + length]
                
                # Check if blocks are reasonably aligned and close together
                if self._blocks_form_title_group(block_group):
                    combined_text = ' '.join(block.text.strip() for block in block_group)
                    combined_text = re.sub(r'\s+', ' ', combined_text).strip()
                    
                    if 20 <= len(combined_text) <= 300:
                        # Score based on multi-line characteristics
                        score = self._score_multiline_title(block_group, combined_text)
                        
                        metadata = {
                            'line_count': length,
                            'start_position': start_idx,
                            'extraction_method': 'multiline'
                        }
                        
                        candidates.append((combined_text, score, metadata))
        
        return candidates
    
    def _blocks_form_title_group(self, blocks: List[TextBlock]) -> bool:
        """Check if blocks could form a coherent title group"""
        if len(blocks) < 2:
            return False
        
        # Check vertical alignment (similar X positions)
        x_positions = [block.x for block in blocks]
        x_variance = max(x_positions) - min(x_positions)
        if x_variance > 100:  # Too much horizontal variation
            return False
        
        # Check vertical spacing (blocks should be close together)
        for i in range(1, len(blocks)):
            y_gap = abs(blocks[i-1].y - blocks[i].y)
            # Adjust gap tolerance based on font size
            avg_height = (blocks[i-1].height + blocks[i].height) / 2
            max_gap = max(50, avg_height * 2)  # Allow gap up to 2x line height
            if y_gap > max_gap:
                return False
        
        # Check that each block has substantial text
        for block in blocks:
            if len(block.text.strip()) < 3:
                return False
        
        # Check font consistency (if available)
        font_sizes = [b.font_size for b in blocks if b.font_size > 0]
        if len(font_sizes) > 1:
            # Font sizes should be similar within a title
            min_size, max_size = min(font_sizes), max(font_sizes)
            if max_size > min_size * 1.5:  # More than 50% difference
                return False
        
        # Check that blocks don't contain obvious non-title content
        for block in blocks:
            text = block.text.strip().lower()
            if any(marker in text for marker in ['@', 'university', 'department', 'abstract']):
                return False
        
        return True
    
    def _score_title_content(self, text: str) -> float:
        """Score text based on title-like characteristics"""
        score = 0
        
        # Length score (titles are usually 20-200 characters)
        length = len(text)
        if 30 <= length <= 120:
            score += 0.4
        elif 120 <= length <= 200:
            score += 0.2
        elif length < 20 or length > 300:
            score -= 0.3
        
        # Capitalization score
        words = text.split()
        if words:
            # Check if it starts with capital
            if words[0][0].isupper():
                score += 0.1
            
            # Check for title case indicators
            capital_words = sum(1 for word in words if len(word) > 3 and word[0].isupper())
            if len(words) > 3 and capital_words / len(words) > 0.3:
                score += 0.1
        
        # Strong title indicators
        strong_title_keywords = [
            'effect', 'impact', 'analysis', 'study', 'investigation', 'approach',
            'method', 'model', 'theory', 'framework', 'evidence', 'empirical',
            'experimental', 'theoretical', 'computational', 'novel', 'new',
            'improved', 'efficient', 'optimal', 'comparative', 'comprehensive'
        ]
        keyword_count = sum(1 for keyword in strong_title_keywords if keyword in text.lower())
        score += min(0.3, keyword_count * 0.1)
        
        # Check for common title patterns
        title_patterns = [
            r'^(?:A |An |The )?[A-Z]\w+(?:\s+\w+)*:',  # "Something: subtitle"
            r'^\w+ing\s+',  # Starts with gerund (Investigating, Analyzing, etc.)
            r'\b(?:of|for|in|on|with|using|via|through|by)\b',  # Prepositions common in titles
        ]
        if any(re.search(pattern, text) for pattern in title_patterns):
            score += 0.2
        
        # Negative indicators - stronger penalties
        if self.patterns['email_pattern'].search(text):
            score -= 0.8
        if self.patterns['url_pattern'].search(text):
            score -= 0.6
        if self.patterns['reference_pattern'].match(text):
            score -= 0.8
        if self._is_repository_header(text):
            score -= 0.8
        if re.search(r'^\d+\.\s*', text):  # Starts with number (like "1. Introduction")
            score -= 0.5
        if text.lower().startswith(('see ', 'been ', 'has been', 'have been', 'is ', 'are ')):
            score -= 0.7  # Likely body text
        
        # Check for citation patterns (like [1], [2])
        if re.search(r'\[\d+\]|\(\d{4}\)', text):
            score -= 0.5
        
        return max(0, score)
    
    def _score_multiline_title(self, blocks: List[TextBlock], combined_text: str) -> float:
        """Score a multi-line title candidate"""
        base_score = self._score_title_content(combined_text)
        
        # Bonus for good multi-line characteristics
        if len(blocks) == 2:
            base_score += 0.1  # Two-line titles are common
        elif len(blocks) == 3:
            base_score += 0.05
        else:
            base_score -= 0.1  # Very long titles are less likely
        
        # Check for good line breaks (avoid breaking mid-word)
        for i in range(len(blocks) - 1):
            line1 = blocks[i].text.strip()
            line2 = blocks[i + 1].text.strip()
            
            if line1.endswith((':', 'of', 'in', 'and', 'the', 'a', 'an')):
                base_score += 0.05  # Good break point
            elif line1.endswith('-'):
                base_score -= 0.1  # Hyphenated break (less ideal)
        
        return base_score
    
    def _score_title_candidate_enhanced(self, title: str, base_score: float, metadata: Dict,
                                       document_structure: DocumentStructure, full_text: str) -> float:
        """Enhanced scoring for title candidates"""
        score = base_score
        
        # Repository-specific adjustments
        if document_structure.repository_type == 'ssrn':
            # SSRN papers often have titles early but after repository header
            if metadata.get('line_number', 0) > 5:
                score += 0.1
        elif document_structure.repository_type == 'arxiv':
            # arXiv papers usually have clean title positioning
            if metadata.get('position_rank', 10) < 5:
                score += 0.1
        
        # Multi-column layout adjustments
        if document_structure.is_multi_column:
            # In multi-column, title is usually single-column at top
            if metadata.get('extraction_method') == 'position':
                score += 0.1
        
        # Published paper adjustments
        if document_structure.is_published:
            # Published papers may have journal name before title
            if metadata.get('line_number', 0) > 3:
                score += 0.05
        
        # Font size bonus (if available)
        if metadata.get('font_size', 0) > 14:
            score += 0.1
        
        # Check against common false positives
        if self._is_likely_false_positive_title(title, full_text):
            score -= 0.3
        
        return max(0, min(1, score))
    
    def _is_repository_header(self, text: str) -> bool:
        """Check if text is a repository header"""
        text_lower = text.lower()
        
        repository_headers = [
            'electronic copy available', 'posted at', 'available at ssrn',
            'working paper no', 'nber working paper', 'discussion paper',
            'arxiv:', 'submitted to arxiv', 'last revised'
        ]
        
        return any(header in text_lower for header in repository_headers)
    
    def _is_date_or_metadata(self, text: str) -> bool:
        """Check if text is date or metadata"""
        return bool(self.patterns['date_pattern'].search(text) or 
                   self.patterns['page_number'].match(text) or
                   len(text.split()) == 1 and text.isdigit())
    
    def _is_likely_false_positive_title(self, title: str, full_text: str) -> bool:
        """Check if title is likely a false positive"""
        title_lower = title.lower()
        
        # Check if it's an author name that got picked up as title
        if self._looks_like_author_name(title):
            return True
        
        # Check if it's institutional affiliation
        if self.patterns['affiliation_indicators'].search(title_lower):
            return True
        
        # Check if it's a section header
        if self.patterns['section_header'].match(title):
            return True
        
        # Check if it appears multiple times (likely header/footer)
        title_count = full_text.lower().count(title_lower)
        if title_count > 2:
            return True
        
        # Check if it's likely from the paper body
        body_text_indicators = [
            r'^(?:been|has been|have been|is|are|was|were)\s+',  # Passive voice starts
            r'^(?:this|these|that|those|it|they)\s+',  # Pronoun starts
            r'^(?:however|therefore|thus|hence|moreover|furthermore)',  # Transitional starts
            r'^(?:in|on|at|by|for|with|from)\s+(?:the|this|that)',  # Prepositional phrase starts
            r'\[\d+\]',  # Citations
            r'\bet\s+al\.?',  # et al. references
            r'\(\d{4}[a-z]?\)',  # Year citations like (2023) or (2023a)
        ]
        if any(re.search(pattern, title_lower) for pattern in body_text_indicators):
            return True
        
        # Check if it contains incomplete sentences (likely pulled from paragraph)
        if title.endswith((',', ';', 'and', 'or', 'the', 'in', 'of')):
            return True
        
        return False
    
    def _looks_like_author_name(self, text: str) -> bool:
        """Check if text looks like an author name"""
        words = text.split()
        if len(words) < 2 or len(words) > 5:
            return False
        
        # Check for name patterns
        name_patterns = [
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+$',  # First Last
            r'^[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+$',  # A. B. Last
            r'^[A-Z][a-z]+,\s*[A-Z]\.$',  # Last, F.
        ]
        
        return any(re.match(pattern, text) for pattern in name_patterns)
    
    def _has_title_characteristics(self, text: str, block: TextBlock, avg_font_size: float) -> bool:
        """Check if a text block has characteristics of a title"""
        # Length check
        if len(text) < 20 or len(text) > 250:
            return False
        
        # Font size check (if available)
        if block.font_size > 0 and avg_font_size > 0:
            if block.font_size < avg_font_size * 0.9:  # Smaller than average
                return False
        
        # Should not be all caps (often headers/footers)
        if text.isupper() and len(text) > 10:
            return False
        
        # Should have substantial content
        word_count = len(text.split())
        if word_count < 3:
            return False
        
        # Should not start with common body text patterns
        body_starts = [
            'been', 'has been', 'have been', 'is', 'are', 'was', 'were',
            'this', 'these', 'that', 'those', 'it', 'they',
            'however', 'therefore', 'thus', 'hence', 'moreover',
            'see', 'cf.', 'e.g.', 'i.e.', 'viz.',
        ]
        first_word = text.split()[0].lower().rstrip('.,;:')
        if first_word in body_starts:
            return False
        
        return True
    
    def _score_title_quality(self, text: str, all_blocks: List[TextBlock]) -> float:
        """Score title quality based on document context"""
        score = 0.5  # Base score
        
        # Check if it's unique in the document (titles usually appear once)
        text_lower = text.lower()
        occurrences = sum(1 for block in all_blocks if text_lower in block.text.lower())
        if occurrences == 1:
            score += 0.3
        elif occurrences > 2:
            score -= 0.3
        
        # Check for good title structure
        if ':' in text and len(text.split(':')[0]) > 10:
            score += 0.2  # Subtitle structure
        
        # Penalty for question marks (less common in titles)
        if '?' in text:
            score -= 0.1
        
        # Bonus for balanced parentheses/brackets
        if text.count('(') == text.count(')') and text.count('[') == text.count(']'):
            score += 0.1
        else:
            score -= 0.2
        
        return max(0, min(1, score))
    
    def _clean_and_format_title(self, title: str) -> str:
        """Clean and format extracted title"""
        if not title:
            return "Unknown Title"
        
        # Remove footnote markers
        title = self.patterns['footnote_markers'].sub('', title)
        
        # Clean whitespace
        title = re.sub(r'\s+', ' ', title).strip()
        
        # Remove leading/trailing punctuation
        title = title.strip('.,;:-')
        
        # Use integrated title formatting if available
        if HAS_FILENAME_CHECKER:
            try:
                formatted, _ = to_sentence_case_academic(title, set(), set())
                return formatted
            except:
                pass
        
        # Basic sentence case
        words = title.split()
        if words:
            words[0] = words[0].capitalize()
            title = ' '.join(words)
        
        return title
    
    # ────────────────────────────────────────────────────────────────────
    # ENHANCED AUTHOR EXTRACTION  
    # ────────────────────────────────────────────────────────────────────
    
    def extract_authors_enhanced(self, text_blocks: List[TextBlock], full_text: str,
                                document_structure: DocumentStructure) -> Tuple[str, float]:
        """Enhanced author extraction with affiliation separation"""
        
        # Use repository-specific extractor if available
        if document_structure.repository_type in self.repository_extractors:
            extractor = self.repository_extractors[document_structure.repository_type]
            repo_authors = extractor.extract_authors(full_text, text_blocks)
            if repo_authors:
                return repo_authors, 0.9
        
        author_candidates = []
        
        # Method 1: Position-based extraction (after title area)
        if text_blocks:
            position_candidates = self._extract_authors_by_position(text_blocks, document_structure)
            author_candidates.extend(position_candidates)
        
        # Method 2: Pattern-based extraction
        pattern_candidates = self._extract_authors_by_patterns(full_text)
        author_candidates.extend(pattern_candidates)
        
        # Method 3: Heuristic extraction (look for name-like patterns)
        heuristic_candidates = self._extract_authors_heuristic(full_text)
        author_candidates.extend(heuristic_candidates)
        
        # Score and select best candidate
        if author_candidates:
            scored_candidates = []
            for authors, base_score, metadata in author_candidates:
                enhanced_score = self._score_author_candidate_enhanced(
                    authors, base_score, metadata, document_structure, full_text
                )
                scored_candidates.append((authors, enhanced_score, metadata))
            
            # Sort by score and return best
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            best_authors, best_score, _ = scored_candidates[0]
            
            # Clean and format authors
            cleaned_authors = self._clean_and_format_authors(best_authors)
            return cleaned_authors, best_score
        
        return "Unknown", 0.0
    
    def _extract_authors_by_position(self, text_blocks: List[TextBlock],
                                    document_structure: DocumentStructure) -> List[Tuple[str, float, Dict]]:
        """Extract author candidates based on position (typically after title)"""
        candidates = []
        
        if not text_blocks:
            return candidates
        
        # Focus on first page
        first_page_blocks = [block for block in text_blocks if block.page_num == 0]
        sorted_blocks = sorted(first_page_blocks, key=lambda b: (b.y, b.x))
        
        # Find where the title likely ends
        title_end_idx = 0
        for i, block in enumerate(sorted_blocks[:10]):
            text = block.text.strip().lower()
            # Skip headers and find substantial text
            if (len(text) > 20 and 
                not self._is_repository_header(text) and
                not self._is_date_or_metadata(text)):
                title_end_idx = i + 1
                break
        
        # Look for author blocks after the title area
        author_region_start = max(title_end_idx, 2)
        author_region_end = min(author_region_start + 10, len(sorted_blocks))
        
        for i in range(author_region_start, author_region_end):
            block = sorted_blocks[i]
            text = block.text.strip()
            
            # Skip if too short/long or is clearly not authors
            if len(text) < 5 or len(text) > 300:
                continue
            if text.lower().startswith(('abstract', 'keywords', 'jel', 'introduction')):
                break  # Stop at paper sections
            
            # Strong negative: if it's ONLY an institution name
            if self._is_pure_affiliation(text):
                continue
            
            # Check if it looks like authors
            if self._looks_like_author_block(text):
                # Separate authors from affiliations
                clean_authors = self._separate_authors_from_affiliations(text)
                
                if clean_authors and len(clean_authors) > 5:
                    # Successfully extracted authors
                    score = 0.8 - (i - author_region_start) * 0.05  # Position penalty
                    
                    # Bonus if it's a clean extraction
                    if not self.patterns['affiliation_indicators'].search(clean_authors):
                        score += 0.1
                    
                    metadata = {
                        'position_rank': i,
                        'y_position': block.y,
                        'extraction_method': 'position',
                        'had_affiliations': clean_authors != text
                    }
                    candidates.append((clean_authors, score, metadata))
                    
            elif self._is_pure_author_block(text):
                # Already clean author block
                score = 0.7 - (i - author_region_start) * 0.05
                metadata = {
                    'position_rank': i,
                    'y_position': block.y,
                    'extraction_method': 'position',
                    'had_affiliations': False
                }
                candidates.append((text, score, metadata))
        
        return candidates
    
    def _extract_authors_by_patterns(self, text: str) -> List[Tuple[str, float, Dict]]:
        """Extract authors using explicit author markers"""
        candidates = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines[:30]):
            line = line.strip()
            
            # Check for explicit author markers
            if self.patterns['author_indicators'].match(line):
                # Extract authors after marker
                authors_match = self.patterns['author_indicators'].sub('', line).strip()
                if authors_match and len(authors_match) > 5:
                    # Clean up affiliations
                    clean_authors = self._separate_authors_from_affiliations(authors_match)
                    
                    score = 0.8  # High score for explicit markers
                    metadata = {
                        'line_number': i,
                        'extraction_method': 'pattern',
                        'marker_type': 'explicit'
                    }
                    candidates.append((clean_authors or authors_match, score, metadata))
        
        return candidates
    
    def _extract_authors_heuristic(self, text: str) -> List[Tuple[str, float, Dict]]:
        """Extract authors using heuristic name detection"""
        candidates = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines[:25]):
            line = line.strip()
            if len(line) < 10 or len(line) > 300:
                continue
            
            # Score based on name-like characteristics
            name_score = self._score_author_line(line)
            
            if name_score > 0.4:  # Threshold for potential author line
                clean_authors = self._separate_authors_from_affiliations(line)
                
                metadata = {
                    'line_number': i,
                    'extraction_method': 'heuristic',
                    'name_score': name_score
                }
                
                candidates.append((clean_authors or line, name_score, metadata))
        
        return candidates
    
    def _looks_like_author_block(self, text: str) -> bool:
        """Check if text block looks like it contains authors"""
        # Check for name patterns (handle both mixed case and uppercase)
        name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+\b',  # A. B. Last
            r'\b[A-Z][a-z]+,\s*[A-Z]\.\b',  # Last, F.
            r'\b[A-Z]{2,}\s+[A-Z]{2,}\b',  # FIRST LAST (all caps)
            r'\b[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}\b',  # FIRST MIDDLE LAST
        ]
        
        name_matches = sum(len(re.findall(pattern, text)) for pattern in name_patterns)
        
        # Check for separators
        has_separators = ' and ' in text or ' & ' in text or ',' in text
        
        # Check for email (authors often have emails)
        has_email = bool(self.patterns['email_pattern'].search(text))
        
        # Check for affiliations (mixed with authors)
        has_affiliations = bool(self.patterns['affiliation_indicators'].search(text))
        
        return name_matches >= 1 and (has_separators or has_email or has_affiliations)
    
    def _is_pure_author_block(self, text: str) -> bool:
        """Check if text is a pure author block (no affiliations)"""
        # Should have name patterns
        name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+\b',  # A. B. Last
            r'\b[A-Z][a-z]+,\s*[A-Z]\.\b',  # Last, F.
        ]
        
        name_matches = sum(len(re.findall(pattern, text)) for pattern in name_patterns)
        
        # Should NOT have institutional indicators
        has_institutions = bool(self.patterns['affiliation_indicators'].search(text))
        
        # Should have author separators
        has_separators = ' and ' in text or ' & ' in text or ',' in text
        
        return name_matches >= 1 and not has_institutions and (has_separators or name_matches > 1)
    
    def _separate_authors_from_affiliations(self, text: str) -> str:
        """Separate author names from institutional affiliations"""
        if not text:
            return text
        
        # First try to split by line breaks (common in PDFs)
        lines = text.split('\n')
        author_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # If the line is purely institutional, skip it
            if self._is_pure_affiliation(line):
                continue
            
            # If it contains author names, process it
            if self._contains_author_name(line):
                # Extract names from this line
                names = self._extract_names_from_line(line)
                if names:
                    author_lines.extend(names)
        
        if author_lines:
            return ', '.join(author_lines)
        
        # Fallback: Split on common separators and analyze each part
        parts = re.split(r'[;,]\s*', text)
        author_parts = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check if this part is an author name vs institution
            if self._is_author_name_part(part):
                author_parts.append(part)
            elif self._contains_author_name(part) and not self._is_pure_affiliation(part):
                # Extract just the name part
                extracted_name = self._extract_name_from_mixed_part(part)
                if extracted_name:
                    author_parts.append(extracted_name)
        
        if author_parts:
            return ', '.join(author_parts)
        
        # Last resort: try to extract names from the whole text
        return self._extract_names_fallback(text)
    
    def _is_author_name_part(self, part: str) -> bool:
        """Check if a part is likely just an author name"""
        # Should look like a name
        name_patterns = [
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+$',  # First Last
            r'^[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+$',  # A. B. Last
            r'^[A-Z][a-z]+,?\s*[A-Z]\.?$',  # Last, F. or Last F.
            r'^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+$',  # First A. Last
        ]
        
        matches_pattern = any(re.match(pattern, part) for pattern in name_patterns)
        
        # Should NOT contain institutional words
        has_institution = bool(self.patterns['affiliation_indicators'].search(part))
        
        # Should be reasonable length for a name
        word_count = len(part.split())
        
        return matches_pattern and not has_institution and 2 <= word_count <= 4
    
    def _contains_author_name(self, part: str) -> bool:
        """Check if part contains an author name mixed with other info"""
        # Look for name patterns within the part
        name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+\b',  # A. B. Last
            r'\b[A-Z][a-z]+,\s*[A-Z]\.\b',  # Last, F.
            r'\b[A-Z]{2,}\s+[A-Z]{2,}\b',  # FIRST LAST (all caps)
            r'\b[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}\b',  # FIRST MIDDLE LAST
        ]
        
        return any(re.search(pattern, part) for pattern in name_patterns)
    
    def _extract_name_from_mixed_part(self, part: str) -> Optional[str]:
        """Extract author name from text mixed with affiliations"""
        # Try to find name patterns and extract them
        name_patterns = [
            r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b',  # First Last
            r'\b([A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+)\b',  # A. B. Last
            r'\b([A-Z][a-z]+,\s*[A-Z]\.)\b',  # Last, F.
            r'\b([A-Z]{2,}\s+[A-Z]{2,})\b',  # FIRST LAST (all caps)
            r'\b([A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,})\b',  # FIRST MIDDLE LAST
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, part)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_names_fallback(self, text: str) -> str:
        """Fallback method to extract names from messy text"""
        # Find all potential name matches
        name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+\b',  # A. B. Last
            r'\b[A-Z][a-z]+,\s*[A-Z]\.\b',  # Last, F.
        ]
        
        found_names = []
        for pattern in name_patterns:
            matches = re.findall(pattern, text)
            found_names.extend(matches)
        
        if found_names:
            # Remove duplicates while preserving order
            unique_names = []
            for name in found_names:
                if name not in unique_names:
                    unique_names.append(name)
            return ', '.join(unique_names)
        
        return text  # Return original if no extraction possible
    
    def _score_author_line(self, line: str) -> float:
        """Score a line based on author-like characteristics"""
        score = 0
        
        # Name pattern score
        name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+\b',  # A. B. Last
            r'\b[A-Z][a-z]+,\s*[A-Z]\.\b',  # Last, F.
            r'\b[A-Z]{2,}\s+[A-Z]{2,}\b',  # FIRST LAST (all caps)
            r'\b[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}\b',  # FIRST MIDDLE LAST
        ]
        
        name_count = sum(len(re.findall(pattern, line)) for pattern in name_patterns)
        score += name_count * 0.3
        
        # Require at least one name match
        if name_count == 0:
            return 0
        
        # Separator bonus
        if ' and ' in line or ' & ' in line:
            score += 0.2
        
        # Multiple comma-separated items
        comma_parts = line.split(',')
        if len(comma_parts) > 1:
            score += min(0.2, len(comma_parts) * 0.05)
        
        # Email bonus
        if self.patterns['email_pattern'].search(line):
            score += 0.1
        
        # Penalty for institutional words
        if self.patterns['affiliation_indicators'].search(line):
            score -= 0.2
        
        # Strong penalty for body text indicators
        body_indicators = [
            r'\b(after|before|since|during|while|when|where|because|although|however|therefore|thus|hence)\b',
            r'\b(the|this|that|these|those|a|an)\b.*\b(is|are|was|were|has|have|had)\b',
            r'\b(in|on|at|by|for|with|from|to|of)\b.*\b(the|this|that)\b',
        ]
        if any(re.search(pattern, line.lower()) for pattern in body_indicators):
            score -= 0.5
        
        # Length penalty
        if len(line) > 200:
            score -= 0.3
        
        return max(0, score)
    
    def _score_author_candidate_enhanced(self, authors: str, base_score: float, metadata: Dict,
                                        document_structure: DocumentStructure, full_text: str) -> float:
        """Enhanced scoring for author candidates"""
        score = base_score
        
        # Check if authors look realistic
        if self._authors_look_realistic(authors):
            score += 0.2
        else:
            score -= 0.3
        
        # Repository-specific adjustments
        if document_structure.repository_type == 'ssrn':
            # SSRN often has authors after title
            if metadata.get('line_number', 0) > 5:
                score += 0.1
        
        # Position bonus (authors usually come after title)
        position = metadata.get('position_rank', 20)
        if 3 <= position <= 10:
            score += 0.1
        
        # Check for excessive affiliations still present
        if self.patterns['affiliation_indicators'].search(authors):
            score -= 0.2
        
        return max(0, min(1, score))
    
    def _authors_look_realistic(self, authors: str) -> bool:
        """Check if extracted authors look realistic"""
        if not authors or len(authors) < 5:
            return False
        
        # Split into individual authors
        author_parts = re.split(r',\s*(?=[A-Z])|and|&', authors)
        author_parts = [part.strip() for part in author_parts if part.strip()]
        
        if not author_parts:
            return False
        
        # Check each author part
        realistic_count = 0
        for part in author_parts[:5]:  # Check up to 5 authors
            if self._single_author_looks_realistic(part):
                realistic_count += 1
        
        # At least 50% should look realistic
        return realistic_count / len(author_parts[:5]) >= 0.5
    
    def _single_author_looks_realistic(self, author: str) -> bool:
        """Check if a single author name looks realistic"""
        if not author or len(author) < 2:
            return False
        
        # Should have reasonable length
        if len(author) > 50:
            return False
        
        # Should match common name patterns
        name_patterns = [
            r'^[A-Z][a-z]+\s+[A-Z][a-z]+$',  # First Last
            r'^[A-Z]\.\s*[A-Z]\.\s*[A-Z][a-z]+$',  # A. B. Last
            r'^[A-Z][a-z]+,\s*[A-Z]\.?$',  # Last, F.
            r'^[A-Z][a-z]+\s+[A-Z]\.\s*[A-Z][a-z]+$',  # First A. Last
            r'^[A-Z]{2,}\s+[A-Z]{2,}$',  # FIRST LAST (all caps)
            r'^[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}$',  # FIRST MIDDLE LAST
        ]
        
        matches_pattern = any(re.match(pattern, author) for pattern in name_patterns)
        
        # Should not contain institutional words
        has_institution = bool(self.patterns['affiliation_indicators'].search(author))
        
        return matches_pattern and not has_institution
    
    def _clean_and_format_authors(self, authors: str) -> str:
        """Clean and format extracted authors"""
        if not authors:
            return "Unknown"
        
        # Use integrated author formatting if available
        if HAS_MAIN_FUNCTIONS:
            try:
                formatted = fix_author_block(authors)
                if formatted and formatted.strip() and formatted != authors:
                    return formatted
            except:
                pass
        
        # Basic formatting
        # Remove footnote markers
        authors = self.patterns['footnote_markers'].sub('', authors)
        
        # Clean whitespace
        authors = re.sub(r'\s+', ' ', authors).strip()
        
        # Basic author formatting
        return self._basic_author_formatting(authors)
    
    def _is_pure_affiliation(self, text: str) -> bool:
        """Check if text is purely an institutional affiliation without author names"""
        text_lower = text.lower()
        
        # List of pure institutional indicators
        pure_institution_patterns = [
            r'^(?:the\s+)?university(?:\s+of)?(?:\s+\w+)*$',
            r'^(?:department|dept\.?)(?:\s+of)?(?:\s+\w+)*$',
            r'^(?:school|college|institute|center|centre)(?:\s+of)?(?:\s+\w+)*$',
            r'^\w+\s+(?:university|college|institute)$',
            r'^(?:harvard|stanford|mit|yale|princeton|oxford|cambridge)(?:\s+university)?$',
        ]
        
        # Check if it matches pure institution patterns
        for pattern in pure_institution_patterns:
            if re.match(pattern, text_lower):
                # Make sure there's no author name in it
                if not self._contains_author_name(text):
                    return True
        
        # Check word composition
        words = text.split()
        if len(words) <= 3:
            # Short phrases that are all institutional words
            inst_words = {'university', 'college', 'institute', 'department', 'school',
                         'center', 'centre', 'faculty', 'division'}
            if all(word.lower() in inst_words or word[0].isupper() for word in words):
                return True
        
        return False
    
    def _extract_names_from_line(self, line: str) -> List[str]:
        """Extract individual author names from a line of text"""
        names = []
        
        # Remove institutional suffixes and numbers
        line = re.sub(r'\s*(?:,|;|\()?\s*(?:university|college|institute|department).*$', '', line, flags=re.I)
        line = re.sub(r'\s*\d+\s*', ' ', line)  # Remove numbers like "1 AND 2"
        
        # Split by common author separators (case-insensitive)
        potential_names = re.split(r'\s+and\s+|\s*[,;]\s*|\s+&\s+', line, flags=re.IGNORECASE)
        
        for name in potential_names:
            name = name.strip()
            # Remove trailing numbers and punctuation
            name = re.sub(r'\s*[,;\d]+\s*$', '', name)
            if name and self._is_valid_author_name(name):
                names.append(name)
        
        return names
    
    def _is_valid_author_name(self, text: str) -> bool:
        """Check if text is a valid author name"""
        if not text or len(text) < 3 or len(text) > 50:
            return False
        
        # Should match name patterns
        name_patterns = [
            r'^[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+$',  # First (M.) Last
            r'^[A-Z]\.(?:\s*[A-Z]\.)*\s+[A-Z][a-z]+$',  # F. M. Last
            r'^[A-Z][a-z]+(?:\s+[a-z]+)?\s+[A-Z][a-z]+$',  # First van Last
            r'^[A-Z][a-z]+,\s*[A-Z]\.?$',  # Last, F.
            r'^[A-Z]{2,}\s+[A-Z]{2,}$',  # FIRST LAST (all caps)
            r'^[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}$',  # FIRST MIDDLE LAST
        ]
        
        if not any(re.match(pattern, text) for pattern in name_patterns):
            return False
        
        # Should not contain institutional words
        inst_words = ['university', 'college', 'institute', 'department', 'school']
        if any(word in text.lower() for word in inst_words):
            return False
        
        return True
    
    def _basic_author_formatting(self, authors: str) -> str:
        """Basic author formatting as fallback"""
        if not authors:
            return "Unknown"
        
        # Split on common separators
        parts = re.split(r'\s+and\s+|\s+&\s+|,\s*(?=[A-Z])', authors)
        formatted_authors = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Basic name formatting
            if ',' in part:
                # Already in "Last, First" format
                formatted_authors.append(part)
            else:
                # Convert "First Last" to "Last, F."
                words = part.split()
                if len(words) >= 2:
                    last = words[-1]
                    first_initials = [w[0].upper() + '.' for w in words[:-1] if w and w[0].isalpha()]
                    if first_initials:
                        formatted_authors.append(f"{last}, {' '.join(first_initials)}")
                    else:
                        formatted_authors.append(last)
                else:
                    formatted_authors.append(part)
        
        # Apply et al. limit
        if len(formatted_authors) > PDFConstants.MAX_AUTHORS:
            formatted_authors = formatted_authors[:PDFConstants.MAX_AUTHORS] + ["et al."]
        
        return ", ".join(formatted_authors) if formatted_authors else "Unknown"
    
    # ────────────────────────────────────────────────────────────────────
    # MAIN EXTRACTION METHOD
    # ────────────────────────────────────────────────────────────────────
    
    def extract_metadata(self, pdf_path: str, **kwargs) -> PDFMetadata:
        """Main metadata extraction with ultra-enhanced capabilities"""
        start_time = time.time()
        pdf_file = Path(pdf_path)
        
        logger.info(f"→ Ultra-enhanced extraction: {pdf_file.name}")
        
        # Validate file
        try:
            if not pdf_file.exists():
                raise FileNotFoundError(f"PDF not found: {pdf_path}")
            if pdf_file.stat().st_size > 100 * 1024 * 1024:  # 100MB limit
                raise ValueError("PDF file too large")
        except Exception as e:
            return PDFMetadata(
                title="Error",
                authors="Error", 
                source=MetadataSource.UNKNOWN,
                error=str(e),
                filename=pdf_file.name,
                path=str(pdf_file),
                processing_time=time.time() - start_time,
            )
        
        # Check cache
        file_hash = hashlib.md5(str(pdf_file).encode()).hexdigest()
        if file_hash in self.extraction_cache:
            cached = self.extraction_cache[file_hash]
            cached.processing_time = time.time() - start_time
            return cached
        
        # Initialize metadata
        metadata = PDFMetadata(
            title="Unknown Title",
            authors="Unknown",
            source=MetadataSource.UNKNOWN,
            filename=pdf_file.name,
            path=str(pdf_file),
        )
        
        try:
            # Enhanced text extraction with position data
            full_text, text_blocks, document_structure = self.extract_enhanced_text(str(pdf_file))
            
            # Update stats
            if document_structure.repository_type == 'ssrn':
                self.stats['ssrn_detected'] += 1
            elif document_structure.repository_type == 'arxiv':
                self.stats['arxiv_detected'] += 1
            elif document_structure.is_published:
                self.stats['journal_detected'] += 1
            
            if document_structure.is_multi_column:
                self.stats['multi_column_detected'] += 1
            
            # Enhanced title extraction
            title, title_confidence = self.extract_title_enhanced(text_blocks, full_text, document_structure)
            if title != "Unknown Title":
                metadata.title = title
                metadata.source = MetadataSource.HEURISTIC
                metadata.confidence = title_confidence
                
                # Check if this was a multi-line reconstruction
                if any('multiline' in str(block) for block in text_blocks):
                    self.stats['title_reconstructed'] += 1
            
            # Enhanced author extraction 
            authors, author_confidence = self.extract_authors_enhanced(text_blocks, full_text, document_structure)
            if authors != "Unknown":
                metadata.authors = authors
                if metadata.source == MetadataSource.UNKNOWN:
                    metadata.source = MetadataSource.HEURISTIC
                metadata.confidence = max(metadata.confidence, author_confidence)
            
            # Repository-specific metadata
            if document_structure.repository_type:
                metadata.warnings.append(f"Detected as {document_structure.repository_type} paper")
            
            if document_structure.is_multi_column:
                metadata.warnings.append("Multi-column layout detected")
            
            # Set final confidence
            if metadata.confidence == 0:
                metadata.confidence = 0.5 if metadata.title != "Unknown Title" or metadata.authors != "Unknown" else 0.3
            
        except Exception as e:
            logger.exception("Ultra-enhanced extraction error")
            metadata.error = str(e)
            metadata.title = "Error"
            metadata.authors = "Error"
        
        # Finalize
        metadata.processing_time = time.time() - start_time
        self.extraction_cache[file_hash] = metadata
        
        self.stats["processed"] += 1
        self.stats["total_time"] += metadata.processing_time
        if metadata.error:
            self.stats["errors"] += 1
        
        logger.info(f"← {pdf_file.name}: {metadata.source.name} "
                   f"(conf {metadata.confidence:.2f}, {metadata.processing_time:.2f}s)")
        
        return metadata


# ──────────────────────────────────────────────────────────────────────────────
# REPOSITORY-SPECIFIC EXTRACTORS
# ──────────────────────────────────────────────────────────────────────────────

class SSRNExtractor:
    """SSRN-specific metadata extractor"""
    
    def extract_title(self, text: str, text_blocks: List[TextBlock]) -> Optional[str]:
        """Extract title from SSRN paper"""
        lines = text.split('\n')
        
        # Look for title after SSRN header but before abstract
        in_title_section = False
        title_lines = []
        
        for i, line in enumerate(lines[:40]):
            line = line.strip()
            
            # Skip SSRN headers
            if any(marker in line.lower() for marker in [
                'electronic copy available', 'posted at', 'ssrn',
                'last revised', 'download date'
            ]):
                continue
            
            # Start collecting after headers
            if not in_title_section and len(line) > 10 and not self._is_metadata_line(line):
                in_title_section = True
            
            # Stop at abstract or author section
            if line.lower() in ['abstract', 'authors:', 'by:'] or line.startswith('JEL'):
                break
            
            if in_title_section and len(line) > 5:
                title_lines.append(line)
            
            # Limit title to reasonable length
            if len(title_lines) > 3:
                break
        
        if title_lines:
            title = ' '.join(title_lines)
            # Clean up common SSRN artifacts
            title = re.sub(r'^(working paper|paper title):\s*', '', title, flags=re.I)
            return title.strip()
        
        return None
    
    def extract_authors(self, text: str, text_blocks: List[TextBlock]) -> Optional[str]:
        """Extract authors from SSRN paper"""
        lines = text.split('\n')
        
        # Look for explicit author markers
        for i, line in enumerate(lines[:30]):
            if re.match(r'^\s*(?:authors?|by):\s*', line, re.I):
                author_line = re.sub(r'^\s*(?:authors?|by):\s*', '', line, flags=re.I)
                if author_line:
                    return self._clean_ssrn_authors(author_line)
        
        # Look for author-like lines after title area
        for i, line in enumerate(lines[5:25], 5):
            line = line.strip()
            if self._looks_like_ssrn_authors(line):
                return self._clean_ssrn_authors(line)
        
        return None
    
    def _is_metadata_line(self, line: str) -> bool:
        """Check if line is SSRN metadata"""
        metadata_indicators = [
            'electronic copy', 'posted at', 'last revised', 'download date',
            'ssrn.com', 'abstract=', 'available at'
        ]
        return any(indicator in line.lower() for indicator in metadata_indicators)
    
    def _looks_like_ssrn_authors(self, line: str) -> bool:
        """Check if line looks like SSRN authors"""
        # Common SSRN author patterns
        if len(line) < 10 or len(line) > 200:
            return False
        
        # Check for name patterns
        name_patterns = [
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # First Last
            r'\b[A-Z]{2,}\s+[A-Z]{2,}\b',  # FIRST LAST (all caps)
            r'\b[A-Z]{2,}\s+[A-Z]{2,}\s+[A-Z]{2,}\b',  # FIRST MIDDLE LAST
        ]
        name_count = sum(len(re.findall(pattern, line)) for pattern in name_patterns)
        
        # Check for email (SSRN often includes emails)
        has_email = '@' in line
        
        # Check for institutional markers (to exclude pure affiliations)
        institutional_words = ['university', 'college', 'institute', 'school', 'department']
        institution_count = sum(1 for word in institutional_words if word in line.lower())
        
        return name_count >= 1 and (has_email or institution_count < 2)
    
    def _clean_ssrn_authors(self, authors_text: str) -> str:
        """Clean SSRN author text"""
        # Remove email addresses for cleaner author list
        authors_text = re.sub(r'\s*\([^)]*@[^)]*\)', '', authors_text)
        authors_text = re.sub(r'\s*<[^>]*@[^>]*>', '', authors_text)
        
        # Remove institutional affiliations in parentheses
        authors_text = re.sub(r'\s*\([^)]*(?:university|college|institute)[^)]*\)', '', authors_text, flags=re.I)
        
        return authors_text.strip()


class ArxivExtractor:
    """arXiv-specific metadata extractor"""
    
    def extract_title(self, text: str, text_blocks: List[TextBlock]) -> Optional[str]:
        """Extract title from arXiv paper"""
        lines = text.split('\n')
        
        # Skip arXiv header lines
        start_idx = 0
        for i, line in enumerate(lines[:10]):
            if re.search(r'arxiv:\d{4}\.\d{4,5}', line.lower()) or '[' in line and ']' in line:
                start_idx = i + 1
                continue
            break
        
        # Look for title in next few lines
        title_lines = []
        for i in range(start_idx, min(start_idx + 5, len(lines))):
            line = lines[i].strip()
            if len(line) > 10 and not self._is_arxiv_metadata(line):
                title_lines.append(line)
            elif title_lines:  # Stop after collecting title
                break
        
        if title_lines:
            return ' '.join(title_lines)
        
        return None
    
    def extract_authors(self, text: str, text_blocks: List[TextBlock]) -> Optional[str]:
        """Extract authors from arXiv paper"""
        lines = text.split('\n')
        
        # In arXiv papers, authors usually come after title
        # Look for lines with multiple names
        for i, line in enumerate(lines[3:15], 3):
            line = line.strip()
            if self._looks_like_arxiv_authors(line):
                return line
        
        return None
    
    def _is_arxiv_metadata(self, line: str) -> bool:
        """Check if line is arXiv metadata"""
        return bool(re.search(r'arxiv:\d{4}\.\d{4,5}|submitted|revised|\[\w+\.\w+\]', line, re.I))
    
    def _looks_like_arxiv_authors(self, line: str) -> bool:
        """Check if line looks like arXiv authors"""
        if len(line) < 10 or len(line) > 300:
            return False
        
        # Count name patterns
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        
        # Check for separators
        has_separators = ' and ' in line or ',' in line
        
        # Should not be institutional
        institutional_words = ['university', 'institute', 'department']
        is_institutional = any(word in line.lower() for word in institutional_words)
        
        return name_count >= 1 and has_separators and not is_institutional


class NBERExtractor:
    """NBER-specific metadata extractor"""
    
    def extract_title(self, text: str, text_blocks: List[TextBlock]) -> Optional[str]:
        """Extract title from NBER working paper"""
        lines = text.split('\n')
        
        # Skip NBER header
        title_start = 0
        for i, line in enumerate(lines[:15]):
            if 'nber' in line.lower() or 'working paper' in line.lower():
                title_start = i + 1
                continue
            break
        
        # Get title lines
        title_lines = []
        for i in range(title_start, min(title_start + 4, len(lines))):
            line = lines[i].strip()
            if len(line) > 10 and not self._is_nber_metadata(line):
                title_lines.append(line)
            elif title_lines:
                break
        
        return ' '.join(title_lines) if title_lines else None
    
    def extract_authors(self, text: str, text_blocks: List[TextBlock]) -> Optional[str]:
        """Extract authors from NBER paper"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[5:20], 5):
            line = line.strip()
            if self._looks_like_nber_authors(line):
                return line
        
        return None
    
    def _is_nber_metadata(self, line: str) -> bool:
        """Check if line is NBER metadata"""
        return 'nber' in line.lower() or 'working paper' in line.lower()
    
    def _looks_like_nber_authors(self, line: str) -> bool:
        """Check if line looks like NBER authors"""
        if len(line) < 15 or len(line) > 200:
            return False
        
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        has_separators = ' and ' in line or ',' in line
        
        return name_count >= 2 and has_separators


class JournalExtractor:
    """Published journal paper extractor"""
    
    def extract_title(self, text: str, text_blocks: List[TextBlock]) -> Optional[str]:
        """Extract title from published journal paper"""
        lines = text.split('\n')
        
        # Skip journal headers
        title_start = 0
        for i, line in enumerate(lines[:10]):
            if any(pub in line.lower() for pub in ['journal', 'proceedings', 'elsevier', 'springer']):
                title_start = i + 1
                continue
            break
        
        # Look for substantial title
        for i in range(title_start, min(title_start + 6, len(lines))):
            line = lines[i].strip()
            if 30 <= len(line) <= 200 and not self._is_journal_metadata(line):
                return line
        
        return None
    
    def extract_authors(self, text: str, text_blocks: List[TextBlock]) -> Optional[str]:
        """Extract authors from journal paper"""
        lines = text.split('\n')
        
        for i, line in enumerate(lines[3:15], 3):
            line = line.strip()
            if self._looks_like_journal_authors(line):
                return line
        
        return None
    
    def _is_journal_metadata(self, line: str) -> bool:
        """Check if line is journal metadata"""
        metadata_indicators = ['journal', 'vol.', 'pp.', 'doi:', '©', 'copyright']
        return any(indicator in line.lower() for indicator in metadata_indicators)
    
    def _looks_like_journal_authors(self, line: str) -> bool:
        """Check if line looks like journal authors"""
        if len(line) < 10 or len(line) > 150:
            return False
        
        name_count = len(re.findall(r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b', line))
        has_separators = ' and ' in line or ',' in line
        not_affiliation = not any(word in line.lower() for word in ['university', 'institute', 'department'])
        
        return name_count >= 1 and has_separators and not_affiliation


# ──────────────────────────────────────────────────────────────────────────────
# MAIN FUNCTION FOR TESTING
# ──────────────────────────────────────────────────────────────────────────────

def main():
    """Test the ultra-enhanced parser"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ultra-Enhanced PDF Parser")
    parser.add_argument("pdf_files", nargs="*", help="PDF files to process")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # Initialize parser
    ultra_parser = UltraEnhancedPDFParser()
    
    # Process files
    pdf_files = args.pdf_files or list(Path(".").glob("*.pdf"))
    
    for pdf_file in pdf_files:
        print(f"\n{'='*60}")
        print(f"Processing: {pdf_file}")
        print('='*60)
        
        try:
            metadata = ultra_parser.extract_metadata(str(pdf_file))
            
            print(f"Title: {metadata.title}")
            print(f"Authors: {metadata.authors}")
            print(f"Source: {metadata.source.name}")
            print(f"Confidence: {metadata.confidence:.3f}")
            print(f"Processing time: {metadata.processing_time:.3f}s")
            
            if metadata.warnings:
                print(f"Warnings: {'; '.join(metadata.warnings)}")
            
            if metadata.error:
                print(f"Error: {metadata.error}")
                
        except Exception as e:
            print(f"Failed to process {pdf_file}: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
    
    # Print stats
    stats = ultra_parser.stats
    print(f"\n{'='*60}")
    print("PROCESSING STATISTICS")
    print('='*60)
    print(f"Total processed: {stats['processed']}")
    print(f"Errors: {stats['errors']}")
    print(f"SSRN papers detected: {stats['ssrn_detected']}")
    print(f"arXiv papers detected: {stats['arxiv_detected']}")
    print(f"Journal papers detected: {stats['journal_detected']}")
    print(f"Multi-column layouts: {stats['multi_column_detected']}")
    print(f"Titles reconstructed: {stats['title_reconstructed']}")
    
    if stats['processed'] > 0:
        avg_time = stats['total_time'] / stats['processed']
        print(f"Average processing time: {avg_time:.3f}s")


if __name__ == "__main__":
    main()