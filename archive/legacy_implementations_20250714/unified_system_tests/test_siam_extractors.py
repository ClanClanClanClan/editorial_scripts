"""
Unit tests for SIAM extractors (SICON/SIFIN)
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import tempfile

from unified_system.extractors.siam import SICONExtractor, SIFINExtractor, SIAMBaseExtractor


class TestSIAMExtractors:
    """Test SIAM extractor functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def mock_page_content(self):
        """Mock SIAM page HTML content"""
        return """
        <html>
        <body>
            <tbody role="assoc_ed">
                <tr class="ndt_task">
                    <td><a class="ndt_task_link" href="/view_ms?id=123">#SICON-2024-001</a></td>
                    <td>Optimal Control of Quantum Systems</td>
                </tr>
                <tr class="ndt_task">
                    <td><a class="ndt_task_link" href="/view_ms?id=124">#SICON-2024-002</a></td>
                    <td>Stochastic Differential Equations</td>
                </tr>
            </tbody>
        </body>
        </html>
        """
    
    @pytest.fixture
    def mock_manuscript_content(self):
        """Mock manuscript details page"""
        return """
        <html>
        <body>
            <table id="ms_details_expanded">
                <tr>
                    <th>Title</th>
                    <td>Optimal Control of Quantum Systems with Applications</td>
                </tr>
                <tr>
                    <th>Submission Date</th>
                    <td>2024-01-15</td>
                </tr>
                <tr>
                    <th>Current Stage</th>
                    <td>Under Review</td>
                </tr>
                <tr>
                    <th>Referees</th>
                    <td>
                        <a href="/referee/123">Dr. John Smith</a>
                        <font color="red">Due: 2024-02-15</font>
                        <br>
                        <a href="/referee/124">Prof. Jane Doe</a>
                        <font color="red">Due: 2024-02-20</font>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    @pytest.fixture
    def mock_referee_content(self):
        """Mock referee profile page"""
        return """
        <html>
        <body>
            <table>
                <tr>
                    <td>Email:</td>
                    <td><a href="mailto:john.smith@university.edu">john.smith@university.edu</a></td>
                </tr>
            </table>
        </body>
        </html>
        """
    
    def test_sicon_initialization(self, temp_dir):
        """Test SICON extractor initialization"""
        extractor = SICONExtractor(output_dir=temp_dir)
        assert extractor.journal_name == "SICON"
        assert extractor.base_url == "https://sicon.siam.org/"
        assert extractor.login_type == "orcid"
        assert extractor.requires_cloudflare_wait is True
    
    def test_sifin_initialization(self, temp_dir):
        """Test SIFIN extractor initialization"""
        extractor = SIFINExtractor(output_dir=temp_dir)
        assert extractor.journal_name == "SIFIN"
        assert extractor.base_url == "https://sifin.siam.org/"
        assert extractor.login_type == "orcid"
        assert extractor.requires_cloudflare_wait is True
    
    @pytest.mark.asyncio
    async def test_manuscript_extraction(self, temp_dir, mock_page_content):
        """Test manuscript list extraction"""
        extractor = SICONExtractor(output_dir=temp_dir)
        
        # Mock page
        mock_page = AsyncMock()
        mock_page.content.return_value = mock_page_content
        mock_page.query_selector_all.return_value = []
        
        extractor.page = mock_page
        
        # Extract manuscripts
        manuscripts = await extractor._extract_manuscripts()
        
        assert len(manuscripts) == 2
        assert manuscripts[0].id == "#SICON-2024-001"
        assert manuscripts[0].title == "Optimal Control of Quantum Systems"
        assert manuscripts[1].id == "#SICON-2024-002"
        assert manuscripts[1].title == "Stochastic Differential Equations"
    
    @pytest.mark.asyncio
    async def test_referee_extraction(self, temp_dir, mock_manuscript_content, mock_referee_content):
        """Test referee details extraction"""
        extractor = SICONExtractor(output_dir=temp_dir)
        
        # Create test manuscript
        from unified_system.core.base_extractor import Manuscript
        manuscript = Manuscript(
            id="#SICON-2024-001",
            title="Test",
            authors=[],
            status="Under Review"
        )
        
        # Mock page navigation
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock()
        mock_page.content.side_effect = [mock_manuscript_content, mock_referee_content, mock_referee_content]
        
        extractor.page = mock_page
        extractor._manuscript_urls = [(manuscript, "https://sicon.siam.org/view_ms?id=123")]
        
        # Extract referee details
        await extractor._extract_referee_details(manuscript)
        
        assert len(manuscript.referees) == 2
        assert manuscript.referees[0].name == "Dr. John Smith"
        assert manuscript.referees[0].status == "Accepted"
        assert manuscript.referees[0].report_date == "2024-02-15"
    
    @pytest.mark.asyncio
    async def test_pdf_extraction(self, temp_dir):
        """Test PDF URL extraction"""
        extractor = SICONExtractor(output_dir=temp_dir)
        
        # Create test manuscript
        from unified_system.core.base_extractor import Manuscript
        manuscript = Manuscript(
            id="#SICON-2024-001",
            title="Test",
            authors=[],
            status="Under Review"
        )
        
        # Mock page with PDF links
        mock_page = AsyncMock()
        mock_link1 = AsyncMock()
        mock_link1.get_attribute.return_value = "https://sicon.siam.org/manuscript.pdf"
        mock_link1.text_content.return_value = "Download Manuscript"
        
        mock_link2 = AsyncMock()
        mock_link2.get_attribute.return_value = "https://sicon.siam.org/supplement.pdf"
        mock_link2.text_content.return_value = "Supplementary Material"
        
        mock_page.query_selector_all.return_value = [mock_link1, mock_link2]
        
        extractor.page = mock_page
        extractor._manuscript_urls = [(manuscript, "https://sicon.siam.org/view_ms?id=123")]
        
        # Mock download_pdf to avoid actual downloads
        extractor.download_pdf = AsyncMock(return_value=Path("/tmp/test.pdf"))
        
        # Extract PDFs
        await extractor._extract_pdfs(manuscript)
        
        assert "manuscript" in manuscript.pdf_urls
        assert "supplement" in manuscript.pdf_urls
        assert manuscript.pdf_urls["manuscript"] == "https://sicon.siam.org/manuscript.pdf"
        assert manuscript.pdf_urls["supplement"] == "https://sicon.siam.org/supplement.pdf"
    
    def test_referee_email_regex(self):
        """Test email extraction regex"""
        from unified_system.extractors.siam.base import SIAMBaseExtractor
        
        # Test various email formats
        test_cases = [
            ("Email: john.doe@university.edu", "john.doe@university.edu"),
            ("Contact: jane.smith@dept.uni.ac.uk", "jane.smith@dept.uni.ac.uk"),
            ("No email here", None),
            ("Multiple emails: a@b.com and c@d.org", "a@b.com"),  # Should find first
        ]
        
        import re
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        
        for text, expected in test_cases:
            match = re.search(email_pattern, text)
            if expected:
                assert match is not None
                assert match.group(0) == expected
            else:
                assert match is None
    
    @pytest.mark.asyncio
    async def test_orcid_authentication(self, temp_dir):
        """Test ORCID authentication flow"""
        extractor = SICONExtractor(output_dir=temp_dir)
        
        # Mock browser and page
        mock_page = AsyncMock()
        mock_page.wait_for_selector.return_value = AsyncMock()  # ORCID button
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.url = "https://sicon.siam.org/dashboard"
        
        extractor.page = mock_page
        
        # Test authentication
        result = await extractor._authenticate_orcid()
        
        assert result is True
        # Verify ORCID flow was followed
        mock_page.wait_for_selector.assert_called()
        assert mock_page.fill.call_count >= 2  # Username and password
        mock_page.click.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])