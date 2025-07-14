"""
Enhanced PDF Manager - Comprehensive document download and management system
Implements requirements from COMPREHENSIVE_DATA_EXTRACTION_REQUIREMENTS.md
"""

import asyncio
import logging
import re
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
import json
import aiofiles
import aiohttp
from playwright.async_api import Page, Download
import mimetypes

try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

logger = logging.getLogger(__name__)


@dataclass
class DocumentMetadata:
    """Metadata for downloaded documents"""
    document_id: str
    filename: str
    file_path: str
    file_size: int
    checksum: str
    download_date: datetime
    source_url: str
    document_type: str  # manuscript, referee_report, supplement, etc.
    manuscript_id: str
    
    # Content metadata
    title: Optional[str] = None
    authors: List[str] = None
    page_count: Optional[int] = None
    text_extracted: bool = False
    text_length: Optional[int] = None
    
    # Quality metadata
    is_valid_pdf: bool = False
    extraction_quality: Optional[float] = None  # 0-1 score
    extraction_method: Optional[str] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []


@dataclass
class DocumentStorage:
    """Document storage configuration"""
    base_path: Path
    organize_by_journal: bool = True
    organize_by_year: bool = True
    organize_by_manuscript: bool = True
    max_file_size_mb: int = 100
    allowed_extensions: List[str] = None
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.pdf', '.doc', '.docx', '.txt']


class EnhancedPDFManager:
    """
    Enhanced PDF and document management system
    Provides comprehensive document download, storage, and processing capabilities
    """
    
    def __init__(
        self, 
        storage_config: DocumentStorage,
        journal_name: str,
        page: Optional[Page] = None
    ):
        self.storage = storage_config
        self.journal_name = journal_name
        self.page = page
        
        # Create storage directories
        self._setup_storage_directories()
        
        # Document registry
        self.document_registry: Dict[str, DocumentMetadata] = {}
        self.download_stats = {
            'total_attempts': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'duplicate_documents': 0,
            'invalid_documents': 0
        }
    
    def _setup_storage_directories(self):
        """Create organized storage directory structure"""
        try:
            self.storage.base_path.mkdir(parents=True, exist_ok=True)
            
            # Create subdirectories
            subdirs = ['pdfs', 'metadata', 'extracted_text', 'cache', 'temp']
            for subdir in subdirs:
                (self.storage.base_path / subdir).mkdir(exist_ok=True)
            
            # Create journal-specific directories if enabled
            if self.storage.organize_by_journal:
                journal_dir = self.storage.base_path / 'pdfs' / self.journal_name.lower()
                journal_dir.mkdir(exist_ok=True)
            
            logger.info(f"✅ Storage directories created: {self.storage.base_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to create storage directories: {e}")
            raise
    
    async def download_manuscript_documents(
        self, 
        manuscript_id: str, 
        document_urls: Dict[str, Union[str, List[str]]],
        force_redownload: bool = False
    ) -> Dict[str, List[DocumentMetadata]]:
        """
        Download all documents for a manuscript with comprehensive management
        
        Args:
            manuscript_id: Unique manuscript identifier
            document_urls: Dictionary of document type -> URL(s)
            force_redownload: Whether to redownload existing documents
            
        Returns:
            Dictionary of document type -> list of DocumentMetadata
        """
        try:
            logger.info(f"📄 Starting document download for manuscript {manuscript_id}")
            
            downloaded_docs = {}
            total_documents = sum(
                len(urls) if isinstance(urls, list) else 1 
                for urls in document_urls.values()
            )
            
            logger.info(f"📊 Found {total_documents} documents to download")
            
            for doc_type, urls in document_urls.items():
                downloaded_docs[doc_type] = []
                
                # Handle single URL or list of URLs
                url_list = urls if isinstance(urls, list) else [urls]
                
                for i, url in enumerate(url_list):
                    try:
                        # Generate document identifier
                        doc_id = self._generate_document_id(manuscript_id, doc_type, i)
                        
                        # Check if document already exists
                        if not force_redownload and doc_id in self.document_registry:
                            logger.info(f"📋 Document already exists: {doc_id}")
                            downloaded_docs[doc_type].append(self.document_registry[doc_id])
                            self.download_stats['duplicate_documents'] += 1
                            continue
                        
                        # Validate URL
                        if not self._validate_document_url(url):
                            logger.warning(f"⚠️ Invalid URL for {doc_type}: {url}")
                            continue
                        
                        # Download document
                        doc_metadata = await self._download_single_document(
                            url=url,
                            manuscript_id=manuscript_id,
                            document_type=doc_type,
                            document_id=doc_id,
                            sequence_number=i
                        )
                        
                        if doc_metadata:
                            downloaded_docs[doc_type].append(doc_metadata)
                            self.document_registry[doc_id] = doc_metadata
                            
                            # Process document (extract text, metadata)
                            await self._process_downloaded_document(doc_metadata)
                            
                        await asyncio.sleep(1)  # Rate limiting
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to download {doc_type} #{i}: {e}")
                        self.download_stats['failed_downloads'] += 1
            
            # Save registry and generate report
            await self._save_document_registry()
            await self._generate_download_report(manuscript_id, downloaded_docs)
            
            logger.info(f"✅ Document download complete for {manuscript_id}")
            return downloaded_docs
            
        except Exception as e:
            logger.error(f"❌ Manuscript document download failed: {e}")
            raise
    
    async def _download_single_document(
        self,
        url: str,
        manuscript_id: str,
        document_type: str,
        document_id: str,
        sequence_number: int = 0
    ) -> Optional[DocumentMetadata]:
        """Download a single document with comprehensive error handling and validation"""
        
        self.download_stats['total_attempts'] += 1
        
        try:
            logger.info(f"📥 Downloading {document_type} for {manuscript_id}: {url}")
            
            # Generate file path
            file_path = self._generate_file_path(manuscript_id, document_type, sequence_number)
            
            # Attempt download with multiple methods
            success = False
            download_method = None
            
            # Method 1: Browser-based download (for authenticated content)
            if self.page:
                success = await self._download_via_browser(url, file_path)
                if success:
                    download_method = "browser"
            
            # Method 2: Direct HTTP download (fallback)
            if not success:
                success = await self._download_via_http(url, file_path)
                if success:
                    download_method = "http"
            
            # Method 3: Alternative approaches for specific URL patterns
            if not success:
                success = await self._download_with_alternative_methods(url, file_path)
                if success:
                    download_method = "alternative"
            
            if not success:
                logger.error(f"❌ All download methods failed for {url}")
                return None
            
            # Validate downloaded file
            if not await self._validate_downloaded_file(file_path):
                logger.error(f"❌ Downloaded file validation failed: {file_path}")
                return None
            
            # Create metadata
            doc_metadata = await self._create_document_metadata(
                document_id=document_id,
                file_path=file_path,
                url=url,
                manuscript_id=manuscript_id,
                document_type=document_type,
                download_method=download_method
            )
            
            self.download_stats['successful_downloads'] += 1
            logger.info(f"✅ Successfully downloaded: {file_path.name}")
            
            return doc_metadata
            
        except Exception as e:
            logger.error(f"❌ Single document download failed: {e}")
            self.download_stats['failed_downloads'] += 1
            return None
    
    async def _download_via_browser(self, url: str, file_path: Path) -> bool:
        """Download using browser for authenticated content"""
        try:
            if not self.page:
                return False
            
            logger.debug(f"🌐 Browser download: {url}")
            
            # Create new page for download to avoid interfering with main session
            download_page = await self.page.context.new_page()
            
            try:
                # Set up download handling with timeout
                async with download_page.expect_download(timeout=60000) as download_info:
                    # Navigate to PDF URL
                    await download_page.goto(url, timeout=30000)
                
                download = await download_info.value
                
                # Save to our path
                await download.save_as(file_path)
                
                return True
                
            finally:
                await download_page.close()
                
        except Exception as e:
            logger.debug(f"Browser download failed: {e}")
            return False
    
    async def _download_via_http(self, url: str, file_path: Path) -> bool:
        """Download using direct HTTP request with authentication"""
        try:
            logger.debug(f"🔗 HTTP download: {url}")
            
            # Get cookies from browser if available
            cookies = {}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            if self.page:
                browser_cookies = await self.page.context.cookies()
                cookies = {c['name']: c['value'] for c in browser_cookies}
            
            timeout = aiohttp.ClientTimeout(total=60)
            
            async with aiohttp.ClientSession(
                cookies=cookies, 
                headers=headers, 
                timeout=timeout
            ) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Check file size
                        if len(content) > self.storage.max_file_size_mb * 1024 * 1024:
                            logger.warning(f"File too large: {len(content)} bytes")
                            return False
                        
                        # Save content
                        async with aiofiles.open(file_path, 'wb') as f:
                            await f.write(content)
                        
                        return True
                    else:
                        logger.debug(f"HTTP {response.status} for {url}")
                        return False
                        
        except Exception as e:
            logger.debug(f"HTTP download failed: {e}")
            return False
    
    async def _download_with_alternative_methods(self, url: str, file_path: Path) -> bool:
        """Try alternative download methods for specific URL patterns"""
        try:
            # Handle SIAM-specific URL patterns
            if 'siam.org' in url and 'main.plex' in url:
                return await self._download_siam_document(url, file_path)
            
            # Handle other journal-specific patterns
            # Add more specific handlers as needed
            
            return False
            
        except Exception as e:
            logger.debug(f"Alternative download failed: {e}")
            return False
    
    async def _download_siam_document(self, url: str, file_path: Path) -> bool:
        """Handle SIAM-specific document downloads"""
        try:
            if not self.page:
                return False
            
            # Navigate to the document URL and wait for response
            response = await self.page.goto(url, wait_until="networkidle")
            
            if response and response.status == 200:
                # Check if it's a PDF content type
                content_type = response.headers.get('content-type', '')
                if 'application/pdf' in content_type:
                    # Get the response body
                    content = await response.body()
                    
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(content)
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"SIAM document download failed: {e}")
            return False
    
    async def _validate_downloaded_file(self, file_path: Path) -> bool:
        """Validate that downloaded file is valid"""
        try:
            if not file_path.exists():
                logger.error(f"File does not exist: {file_path}")
                return False
            
            file_size = file_path.stat().st_size
            if file_size < 100:  # Too small to be a valid document
                logger.error(f"File too small: {file_size} bytes")
                return False
            
            # Check file extension
            if file_path.suffix.lower() not in self.storage.allowed_extensions:
                logger.warning(f"Unexpected file extension: {file_path.suffix}")
            
            # For PDFs, check magic number
            if file_path.suffix.lower() == '.pdf':
                async with aiofiles.open(file_path, 'rb') as f:
                    header = await f.read(4)
                    if header != b'%PDF':
                        logger.error(f"Invalid PDF header: {header}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return False
    
    async def _create_document_metadata(
        self,
        document_id: str,
        file_path: Path,
        url: str,
        manuscript_id: str,
        document_type: str,
        download_method: str
    ) -> DocumentMetadata:
        """Create comprehensive document metadata"""
        try:
            # Basic file information
            file_size = file_path.stat().st_size
            checksum = await self._calculate_file_checksum(file_path)
            
            # Create metadata object
            metadata = DocumentMetadata(
                document_id=document_id,
                filename=file_path.name,
                file_path=str(file_path),
                file_size=file_size,
                checksum=checksum,
                download_date=datetime.now(),
                source_url=url,
                document_type=document_type,
                manuscript_id=manuscript_id,
                extraction_method=download_method,
                is_valid_pdf=(file_path.suffix.lower() == '.pdf')
            )
            
            # Extract content metadata for PDFs
            if file_path.suffix.lower() == '.pdf':
                await self._extract_pdf_metadata(file_path, metadata)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata creation failed: {e}")
            raise
    
    async def _extract_pdf_metadata(self, file_path: Path, metadata: DocumentMetadata):
        """Extract metadata from PDF file"""
        try:
            # Try multiple PDF processing libraries
            if HAS_PYPDF2:
                success = await self._extract_metadata_pypdf2(file_path, metadata)
                if success:
                    return
            
            if HAS_PDFPLUMBER:
                success = await self._extract_metadata_pdfplumber(file_path, metadata)
                if success:
                    return
            
            logger.warning(f"No PDF libraries available for metadata extraction: {file_path}")
            
        except Exception as e:
            logger.error(f"PDF metadata extraction failed: {e}")
    
    async def _extract_metadata_pypdf2(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Extract PDF metadata using PyPDF2"""
        try:
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Basic info
                metadata.page_count = len(pdf_reader.pages)
                
                # Metadata from PDF info
                if pdf_reader.metadata:
                    info = pdf_reader.metadata
                    if info.title:
                        metadata.title = str(info.title)
                    if info.author:
                        # Split author string if it contains multiple authors
                        authors = str(info.author).split(';')
                        metadata.authors = [a.strip() for a in authors if a.strip()]
                
                # Extract some text for quality assessment
                text_sample = ""
                for i in range(min(3, len(pdf_reader.pages))):  # First 3 pages
                    page_text = pdf_reader.pages[i].extract_text()
                    if page_text:
                        text_sample += page_text[:1000]  # Limit sample size
                
                metadata.text_extracted = bool(text_sample.strip())
                metadata.text_length = len(text_sample)
                metadata.extraction_quality = self._assess_text_quality(text_sample)
                
                return True
                
        except Exception as e:
            logger.debug(f"PyPDF2 extraction failed: {e}")
            return False
    
    async def _extract_metadata_pdfplumber(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Extract PDF metadata using pdfplumber"""
        try:
            with pdfplumber.open(file_path) as pdf:
                metadata.page_count = len(pdf.pages)
                
                # Extract text from first few pages
                text_sample = ""
                for i, page in enumerate(pdf.pages[:3]):  # First 3 pages
                    page_text = page.extract_text()
                    if page_text:
                        text_sample += page_text[:1000]
                
                metadata.text_extracted = bool(text_sample.strip())
                metadata.text_length = len(text_sample)
                metadata.extraction_quality = self._assess_text_quality(text_sample)
                
                return True
                
        except Exception as e:
            logger.debug(f"pdfplumber extraction failed: {e}")
            return False
    
    def _assess_text_quality(self, text: str) -> float:
        """Assess quality of extracted text (0-1 score)"""
        if not text or len(text) < 10:
            return 0.0
        
        # Calculate ratio of alphanumeric characters
        alphanumeric = sum(1 for c in text if c.isalnum())
        total_chars = len(text)
        
        if total_chars == 0:
            return 0.0
        
        alphanumeric_ratio = alphanumeric / total_chars
        
        # Check for common quality indicators
        has_sentences = '.' in text and len(text.split('.')) > 2
        has_words = len(text.split()) > 10
        reasonable_length = 50 <= len(text) <= 10000
        
        # Calculate quality score
        score = alphanumeric_ratio
        if has_sentences:
            score += 0.2
        if has_words:
            score += 0.2
        if reasonable_length:
            score += 0.1
        
        return min(1.0, score)
    
    async def _process_downloaded_document(self, metadata: DocumentMetadata):
        """Process downloaded document (extract text, analyze content)"""
        try:
            # Extract full text if it's a PDF and extraction quality is good
            if (metadata.is_valid_pdf and 
                metadata.extraction_quality and 
                metadata.extraction_quality > 0.3):
                
                await self._extract_full_text(metadata)
            
            # Save metadata to file
            await self._save_document_metadata(metadata)
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
    
    async def _extract_full_text(self, metadata: DocumentMetadata):
        """Extract full text from document and save to separate file"""
        try:
            file_path = Path(metadata.file_path)
            text_path = self.storage.base_path / 'extracted_text' / f"{metadata.document_id}.txt"
            
            if file_path.suffix.lower() == '.pdf':
                extracted_text = await self._extract_full_pdf_text(file_path)
                
                if extracted_text and len(extracted_text) > 100:
                    async with aiofiles.open(text_path, 'w', encoding='utf-8') as f:
                        await f.write(extracted_text)
                    
                    logger.info(f"📄 Extracted text ({len(extracted_text)} chars): {text_path}")
                    metadata.text_extracted = True
                    metadata.text_length = len(extracted_text)
            
        except Exception as e:
            logger.error(f"Full text extraction failed: {e}")
    
    async def _extract_full_pdf_text(self, file_path: Path) -> Optional[str]:
        """Extract full text from PDF using best available method"""
        try:
            # Try pdfplumber first (usually better for text extraction)
            if HAS_PDFPLUMBER:
                try:
                    with pdfplumber.open(file_path) as pdf:
                        text_parts = []
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                        
                        if text_parts:
                            full_text = '\n\n'.join(text_parts)
                            # Clean up the text
                            full_text = re.sub(r'\s+', ' ', full_text)
                            return full_text.strip()
                except Exception as e:
                    logger.debug(f"pdfplumber text extraction failed: {e}")
            
            # Fallback to PyPDF2
            if HAS_PYPDF2:
                try:
                    with open(file_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        text_parts = []
                        
                        for page in pdf_reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text_parts.append(page_text)
                        
                        if text_parts:
                            full_text = '\n\n'.join(text_parts)
                            # Clean up the text
                            full_text = re.sub(r'\s+', ' ', full_text)
                            return full_text.strip()
                except Exception as e:
                    logger.debug(f"PyPDF2 text extraction failed: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"PDF text extraction failed: {e}")
            return None
    
    async def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of file"""
        try:
            hash_sha256 = hashlib.sha256()
            async with aiofiles.open(file_path, 'rb') as f:
                async for chunk in self._read_chunks(f):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Checksum calculation failed: {e}")
            return ""
    
    async def _read_chunks(self, file_handle, chunk_size: int = 8192):
        """Async generator for reading file in chunks"""
        while True:
            chunk = await file_handle.read(chunk_size)
            if not chunk:
                break
            yield chunk
    
    def _generate_document_id(self, manuscript_id: str, doc_type: str, sequence: int) -> str:
        """Generate unique document identifier"""
        return f"{self.journal_name}_{manuscript_id}_{doc_type}_{sequence}_{datetime.now().strftime('%Y%m%d')}"
    
    def _generate_file_path(self, manuscript_id: str, doc_type: str, sequence: int) -> Path:
        """Generate organized file path for document"""
        # Create safe filename
        safe_manuscript_id = re.sub(r'[^\w\-_.]', '_', manuscript_id)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if sequence > 0:
            filename = f"{safe_manuscript_id}_{doc_type}_{sequence}_{timestamp}.pdf"
        else:
            filename = f"{safe_manuscript_id}_{doc_type}_{timestamp}.pdf"
        
        # Organize by journal and optionally by year and manuscript
        base_dir = self.storage.base_path / 'pdfs'
        
        if self.storage.organize_by_journal:
            base_dir = base_dir / self.journal_name.lower()
        
        if self.storage.organize_by_year:
            base_dir = base_dir / str(datetime.now().year)
        
        if self.storage.organize_by_manuscript:
            base_dir = base_dir / safe_manuscript_id
        
        # Create directory if it doesn't exist
        base_dir.mkdir(parents=True, exist_ok=True)
        
        return base_dir / filename
    
    def _validate_document_url(self, url: str) -> bool:
        """Validate document URL"""
        if not url or not isinstance(url, str):
            return False
        
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'javascript:',
            r'data:',
            r'file:',
            r'<script',
            r'onclick'
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        return True
    
    async def _save_document_metadata(self, metadata: DocumentMetadata):
        """Save document metadata to file"""
        try:
            metadata_path = self.storage.base_path / 'metadata' / f"{metadata.document_id}.json"
            metadata_path.parent.mkdir(exist_ok=True)
            
            async with aiofiles.open(metadata_path, 'w') as f:
                await f.write(json.dumps(asdict(metadata), indent=2, default=str))
            
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    async def _save_document_registry(self):
        """Save document registry to file"""
        try:
            registry_path = self.storage.base_path / 'document_registry.json'
            
            registry_data = {
                'last_updated': datetime.now().isoformat(),
                'total_documents': len(self.document_registry),
                'download_stats': self.download_stats,
                'documents': {
                    doc_id: asdict(metadata) 
                    for doc_id, metadata in self.document_registry.items()
                }
            }
            
            async with aiofiles.open(registry_path, 'w') as f:
                await f.write(json.dumps(registry_data, indent=2, default=str))
            
            logger.info(f"💾 Document registry saved: {len(self.document_registry)} documents")
            
        except Exception as e:
            logger.error(f"Failed to save document registry: {e}")
    
    async def _generate_download_report(
        self, 
        manuscript_id: str, 
        downloaded_docs: Dict[str, List[DocumentMetadata]]
    ):
        """Generate download report for manuscript"""
        try:
            report_path = self.storage.base_path / 'reports' / f"{manuscript_id}_download_report.json"
            report_path.parent.mkdir(exist_ok=True)
            
            report = {
                'manuscript_id': manuscript_id,
                'download_date': datetime.now().isoformat(),
                'total_documents': sum(len(docs) for docs in downloaded_docs.values()),
                'documents_by_type': {
                    doc_type: len(docs) for doc_type, docs in downloaded_docs.items()
                },
                'successful_downloads': [
                    {
                        'type': doc_type,
                        'filename': doc.filename,
                        'file_size': doc.file_size,
                        'text_extracted': doc.text_extracted
                    }
                    for doc_type, docs in downloaded_docs.items()
                    for doc in docs
                ],
                'download_stats': self.download_stats
            }
            
            async with aiofiles.open(report_path, 'w') as f:
                await f.write(json.dumps(report, indent=2))
            
            logger.info(f"📊 Download report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Failed to generate download report: {e}")
    
    async def get_document_by_id(self, document_id: str) -> Optional[DocumentMetadata]:
        """Retrieve document metadata by ID"""
        return self.document_registry.get(document_id)
    
    async def get_documents_for_manuscript(self, manuscript_id: str) -> List[DocumentMetadata]:
        """Get all documents for a specific manuscript"""
        return [
            doc for doc in self.document_registry.values()
            if doc.manuscript_id == manuscript_id
        ]
    
    async def cleanup_old_documents(self, days_old: int = 30):
        """Clean up old temporary and cache documents"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            
            # Clean up temp and cache directories
            temp_dir = self.storage.base_path / 'temp'
            cache_dir = self.storage.base_path / 'cache'
            
            cleaned_count = 0
            for directory in [temp_dir, cache_dir]:
                if directory.exists():
                    for file_path in directory.iterdir():
                        if file_path.is_file() and file_path.stat().st_mtime < cutoff_date:
                            file_path.unlink()
                            cleaned_count += 1
            
            logger.info(f"🧹 Cleaned up {cleaned_count} old documents")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get comprehensive download statistics"""
        return {
            'total_documents': len(self.document_registry),
            'download_stats': self.download_stats.copy(),
            'storage_info': {
                'base_path': str(self.storage.base_path),
                'total_size_mb': self._calculate_total_storage_size()
            },
            'document_types': self._get_document_type_distribution(),
            'extraction_quality': self._get_extraction_quality_stats()
        }
    
    def _calculate_total_storage_size(self) -> float:
        """Calculate total storage size in MB"""
        try:
            total_size = 0
            for doc in self.document_registry.values():
                total_size += doc.file_size
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0
    
    def _get_document_type_distribution(self) -> Dict[str, int]:
        """Get distribution of document types"""
        distribution = {}
        for doc in self.document_registry.values():
            distribution[doc.document_type] = distribution.get(doc.document_type, 0) + 1
        return distribution
    
    async def download_pdf(self, url: str, filename: str, journal: str, manuscript_id: str) -> Optional[Path]:
        """Simple wrapper for compatibility with existing code"""
        try:
            # Use the comprehensive download method
            doc_type = filename.split('_')[-1].replace('.pdf', '')  # Extract type from filename
            document_urls = {doc_type: url}
            
            results = await self.download_manuscript_documents(
                manuscript_id=manuscript_id,
                document_urls=document_urls,
                force_redownload=False
            )
            
            # Return the path of the first downloaded document
            if results and doc_type in results and results[doc_type]:
                return Path(results[doc_type][0].file_path)
            
            return None
            
        except Exception as e:
            logger.error(f"PDF download failed: {e}")
            return None
    
    async def extract_text(self, pdf_path: Path) -> Optional[str]:
        """Extract text from PDF for compatibility"""
        try:
            if not pdf_path.exists():
                return None
                
            # Try PyPDF2 first
            if HAS_PYPDF2:
                try:
                    text = ""
                    with open(pdf_path, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        for page in pdf_reader.pages:
                            text += page.extract_text() + "\n"
                    if text.strip():
                        return text
                except Exception as e:
                    logger.debug(f"PyPDF2 extraction failed: {e}")
            
            # Try pdfplumber as fallback
            if HAS_PDFPLUMBER:
                try:
                    import pdfplumber
                    text = ""
                    with pdfplumber.open(pdf_path) as pdf:
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                    if text.strip():
                        return text
                except Exception as e:
                    logger.debug(f"pdfplumber extraction failed: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return None
    
    def _get_extraction_quality_stats(self) -> Dict[str, Any]:
        """Get text extraction quality statistics"""
        quality_scores = [
            doc.extraction_quality for doc in self.document_registry.values()
            if doc.extraction_quality is not None
        ]
        
        if not quality_scores:
            return {'average_quality': 0.0, 'documents_with_text': 0}
        
        return {
            'average_quality': sum(quality_scores) / len(quality_scores),
            'documents_with_text': sum(1 for doc in self.document_registry.values() if doc.text_extracted),
            'total_text_length': sum(doc.text_length or 0 for doc in self.document_registry.values())
        }


# Example usage and testing
if __name__ == "__main__":
    async def test_enhanced_pdf_manager():
        # Setup storage configuration
        storage_config = DocumentStorage(
            base_path=Path("test_storage"),
            organize_by_journal=True,
            organize_by_year=True,
            organize_by_manuscript=True
        )
        
        # Create PDF manager
        pdf_manager = EnhancedPDFManager(storage_config, "SICON")
        
        # Test document URLs
        test_urls = {
            "manuscript": "https://example.com/manuscript.pdf",
            "referee_reports": [
                "https://example.com/review1.pdf",
                "https://example.com/review2.pdf"
            ]
        }
        
        # Download documents
        results = await pdf_manager.download_manuscript_documents(
            manuscript_id="M172838",
            document_urls=test_urls
        )
        
        print("Download Results:")
        for doc_type, docs in results.items():
            print(f"  {doc_type}: {len(docs)} documents")
        
        # Get statistics
        stats = pdf_manager.get_download_statistics()
        print(f"Total storage: {stats['storage_info']['total_size_mb']:.2f} MB")
    
    # Run test
    # asyncio.run(test_enhanced_pdf_manager())