"""
Document storage service for manuscript documents
Handles secure storage and retrieval of PDFs and other documents
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime
import json


class DocumentStorage:
    """Service for storing and managing manuscript documents"""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize document storage"""
        self.base_path = Path(base_path) if base_path else Path.home() / '.editorial_scripts' / 'documents'
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.manuscripts_dir = self.base_path / 'manuscripts'
        self.metadata_dir = self.base_path / 'metadata'
        self.temp_dir = self.base_path / 'temp'
        
        for dir_path in [self.manuscripts_dir, self.metadata_dir, self.temp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def get_manuscript_dir(self, journal_code: str, manuscript_id: str) -> Path:
        """Get directory for a specific manuscript"""
        ms_dir = self.manuscripts_dir / journal_code / manuscript_id
        ms_dir.mkdir(parents=True, exist_ok=True)
        return ms_dir
    
    def store_document(self, 
                      content: bytes, 
                      journal_code: str, 
                      manuscript_id: str, 
                      document_type: str,
                      filename: Optional[str] = None) -> str:
        """Store a document and return its path"""
        ms_dir = self.get_manuscript_dir(journal_code, manuscript_id)
        
        # Generate filename if not provided
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{document_type}_{timestamp}.pdf"
        
        file_path = ms_dir / filename
        
        # Write content
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Store metadata
        self._store_document_metadata(journal_code, manuscript_id, document_type, filename, content)
        
        return str(file_path)
    
    def _store_document_metadata(self, 
                                journal_code: str, 
                                manuscript_id: str,
                                document_type: str,
                                filename: str,
                                content: bytes):
        """Store document metadata"""
        metadata = {
            'journal_code': journal_code,
            'manuscript_id': manuscript_id,
            'document_type': document_type,
            'filename': filename,
            'size_bytes': len(content),
            'md5_hash': hashlib.md5(content).hexdigest(),
            'stored_at': datetime.now().isoformat()
        }
        
        # Create metadata file
        metadata_file = self.metadata_dir / journal_code / manuscript_id / f"{filename}.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    def get_document(self, journal_code: str, manuscript_id: str, filename: str) -> Optional[bytes]:
        """Retrieve a document"""
        file_path = self.get_manuscript_dir(journal_code, manuscript_id) / filename
        
        if file_path.exists():
            with open(file_path, 'rb') as f:
                return f.read()
        
        return None
    
    def list_documents(self, journal_code: str, manuscript_id: str) -> List[Dict[str, Any]]:
        """List all documents for a manuscript"""
        ms_dir = self.get_manuscript_dir(journal_code, manuscript_id)
        documents = []
        
        for file_path in ms_dir.iterdir():
            if file_path.is_file():
                # Load metadata if available
                metadata_file = self.metadata_dir / journal_code / manuscript_id / f"{file_path.name}.json"
                metadata = {}
                
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                
                documents.append({
                    'filename': file_path.name,
                    'path': str(file_path),
                    'size_bytes': file_path.stat().st_size,
                    'modified_at': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    'metadata': metadata
                })
        
        return documents
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir()
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        total_size = 0
        file_count = 0
        journal_stats = {}
        
        for journal_dir in self.manuscripts_dir.iterdir():
            if journal_dir.is_dir():
                journal_size = 0
                journal_files = 0
                
                for ms_dir in journal_dir.iterdir():
                    if ms_dir.is_dir():
                        for file_path in ms_dir.iterdir():
                            if file_path.is_file():
                                size = file_path.stat().st_size
                                journal_size += size
                                total_size += size
                                journal_files += 1
                                file_count += 1
                
                journal_stats[journal_dir.name] = {
                    'files': journal_files,
                    'size_bytes': journal_size,
                    'size_mb': round(journal_size / 1024 / 1024, 2)
                }
        
        return {
            'total_files': file_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'journals': journal_stats,
            'storage_path': str(self.base_path)
        }