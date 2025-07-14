"""
Unit tests for BaseExtractor
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import tempfile

from unified_system.core.base_extractor import BaseExtractor, Manuscript, Referee


class TestExtractor(BaseExtractor):
    """Test implementation of BaseExtractor"""
    journal_name = "TEST"
    base_url = "https://test.example.com"
    
    async def _authenticate_custom(self) -> bool:
        return True
    
    async def _navigate_to_manuscripts(self) -> bool:
        return True
    
    async def _extract_manuscripts(self):
        return [
            Manuscript(
                id="#TEST-001",
                title="Test Manuscript",
                authors=["Test Author"],
                status="Under Review",
                journal="TEST"
            )
        ]
    
    async def _extract_referee_details(self, manuscript):
        manuscript.referees = [
            Referee(
                name="Test Referee",
                email="referee@test.com",
                status="Accepted"
            )
        ]
    
    async def _extract_pdfs(self, manuscript):
        manuscript.pdf_urls["manuscript"] = "https://test.example.com/test.pdf"
    
    async def _extract_referee_reports(self, manuscript):
        manuscript.referee_reports["referee@test.com"] = "Test report content"


class TestBaseExtractor:
    """Test BaseExtractor functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def extractor(self, temp_dir):
        """Create test extractor instance"""
        return TestExtractor(
            cache_dir=temp_dir / "cache",
            output_dir=temp_dir / "output"
        )
    
    def test_initialization(self, extractor, temp_dir):
        """Test extractor initialization"""
        assert extractor.journal_name == "TEST"
        assert extractor.base_url == "https://test.example.com"
        assert extractor.cache_dir == temp_dir / "cache"
        assert extractor.output_dir == temp_dir / "output"
        assert extractor.cache_dir.exists()
        assert extractor.output_dir.exists()
    
    @pytest.mark.asyncio
    async def test_extract_flow(self, extractor):
        """Test basic extraction flow"""
        # Mock browser
        with patch('playwright.async_api.async_playwright') as mock_playwright:
            # Set up mocks
            mock_browser = AsyncMock()
            mock_page = AsyncMock()
            mock_context = AsyncMock()
            
            mock_playwright.return_value.start.return_value.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page
            
            # Mock page methods
            mock_page.goto = AsyncMock()
            mock_page.wait_for_load_state = AsyncMock()
            mock_page.content = AsyncMock(return_value="<html></html>")
            
            # Run extraction
            results = await extractor.extract(
                username="test_user",
                password="test_pass",
                headless=True
            )
            
            # Verify results
            assert results is not None
            assert results['journal'] == "TEST"
            assert results['total_manuscripts'] == 1
            assert len(results['manuscripts']) == 1
            
            # Check manuscript data
            ms = results['manuscripts'][0]
            assert ms['id'] == "#TEST-001"
            assert ms['title'] == "Test Manuscript"
            assert len(ms['referees']) == 1
            assert ms['referees'][0]['email'] == "referee@test.com"
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, extractor):
        """Test cache save and load"""
        test_data = {"test": "data", "count": 42}
        
        # Save to cache
        await extractor.save_to_cache("test_key", test_data)
        
        # Load from cache
        loaded_data = await extractor.load_from_cache("test_key")
        
        assert loaded_data == test_data
    
    @pytest.mark.asyncio
    async def test_pdf_download_direct(self, extractor):
        """Test direct PDF download"""
        # Mock aiohttp
        with patch('aiohttp.ClientSession') as mock_session:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read = AsyncMock(return_value=b'%PDF-1.4 test content')
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
            
            # Test download
            pdf_path = await extractor.download_pdf(
                "https://test.example.com/test.pdf",
                "test.pdf",
                use_browser=False
            )
            
            assert pdf_path is not None
            assert pdf_path.exists()
            assert pdf_path.name == "test.pdf"
            
            # Verify content
            with open(pdf_path, 'rb') as f:
                content = f.read()
                assert content.startswith(b'%PDF')
    
    def test_manuscript_dataclass(self):
        """Test Manuscript dataclass"""
        ms = Manuscript(
            id="#123",
            title="Test Title",
            authors=["Author 1", "Author 2"],
            status="Submitted"
        )
        
        assert ms.id == "#123"
        assert ms.title == "Test Title"
        assert len(ms.authors) == 2
        assert ms.status == "Submitted"
        assert ms.referees == []  # Default empty list
        assert ms.pdf_urls == {}  # Default empty dict
        assert ms.pdf_paths == {}  # Default empty dict
        assert ms.referee_reports == {}  # Default empty dict
    
    def test_referee_dataclass(self):
        """Test Referee dataclass"""
        ref = Referee(
            name="Dr. Reviewer",
            email="reviewer@university.edu",
            status="Accepted"
        )
        
        assert ref.name == "Dr. Reviewer"
        assert ref.email == "reviewer@university.edu"
        assert ref.status == "Accepted"
        assert ref.report_submitted is False  # Default
        assert ref.reminder_count == 0  # Default


if __name__ == "__main__":
    pytest.main([__file__, "-v"])