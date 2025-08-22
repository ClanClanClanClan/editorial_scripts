"""Tests for popup window handling."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from selenium.webdriver.common.by import By

from src.ecc.browser.popup_handler import PopupHandler


class TestPopupHandler:
    """Test popup handling functionality."""
    
    @pytest.fixture
    def mock_browser_manager(self):
        """Create mock browser manager."""
        browser = MagicMock()
        browser.driver = MagicMock()
        browser.driver.current_window_handle = "main_window"
        browser.driver.window_handles = ["main_window"]
        return browser
    
    @pytest.fixture
    def popup_handler(self, mock_browser_manager):
        """Create popup handler instance."""
        return PopupHandler(mock_browser_manager)
    
    def test_initialization(self, popup_handler, mock_browser_manager):
        """Test popup handler initialization."""
        assert popup_handler.browser == mock_browser_manager
        assert popup_handler.driver == mock_browser_manager.driver
    
    def test_extract_from_javascript_popup_invalid_url(self, popup_handler):
        """Test extraction with invalid popup URL."""
        assert popup_handler.extract_from_javascript_popup(None) is None
        assert popup_handler.extract_from_javascript_popup("") is None
        assert popup_handler.extract_from_javascript_popup("http://example.com") is None
    
    def test_extract_from_javascript_popup_success(self, popup_handler):
        """Test successful popup extraction."""
        popup_url = "javascript:popWindow('test.html', 'popup', 800, 600)"
        
        # Setup mock popup window
        popup_handler.driver.window_handles = ["main_window", "popup_window"]
        
        # Mock content extraction
        with patch.object(popup_handler, '_extract_popup_content', return_value="test@example.com"):
            result = popup_handler.extract_from_javascript_popup(popup_url)
        
        # Verify JavaScript execution
        popup_handler.driver.execute_script.assert_called_with(
            "popWindow('test.html', 'popup', 800, 600)"
        )
        
        # Verify window switching
        popup_handler.driver.switch_to.window.assert_called()
        
        # Verify popup was closed
        popup_handler.driver.close.assert_called()
        
        assert result == "test@example.com"
    
    def test_extract_from_javascript_popup_exception(self, popup_handler):
        """Test popup extraction with exception."""
        popup_url = "javascript:test()"
        
        # Make execute_script fail
        popup_handler.driver.execute_script.side_effect = Exception("Script error")
        
        result = popup_handler.extract_from_javascript_popup(popup_url)
        
        assert result is None
    
    def test_extract_email_from_popup_mailto_link(self, popup_handler):
        """Test email extraction from mailto link."""
        # Mock mailto link
        mock_link = MagicMock()
        mock_link.get_attribute.return_value = "mailto:john@example.com?subject=Test"
        popup_handler.driver.find_elements.return_value = [mock_link]
        
        result = popup_handler._extract_email_from_popup()
        
        assert result == "john@example.com"
    
    def test_extract_email_from_popup_text_pattern(self, popup_handler):
        """Test email extraction from text using regex."""
        # No mailto links
        popup_handler.driver.find_elements.return_value = []
        
        # Mock page text with email
        mock_body = MagicMock()
        mock_body.text = "Contact: john.doe@university.edu for more info"
        popup_handler.driver.find_element.return_value = mock_body
        
        result = popup_handler._extract_email_from_popup()
        
        assert result == "john.doe@university.edu"
    
    def test_extract_email_filters_system_emails(self, popup_handler):
        """Test that system emails are filtered out."""
        # Mock page text with system email
        popup_handler.driver.find_elements.return_value = []
        mock_body = MagicMock()
        mock_body.text = "noreply@manuscriptcentral.com and real@example.com"
        popup_handler.driver.find_element.return_value = mock_body
        
        result = popup_handler._extract_email_from_popup()
        
        assert result == "real@example.com"
    
    def test_extract_review_content_with_recommendation(self, popup_handler):
        """Test review content extraction with recommendation."""
        mock_body = MagicMock()
        mock_body.text = """
        Recommendation: Accept
        
        Overall Rating: 8
        Technical Quality: 9
        
        Comments to Author:
        This is a well-written paper.
        """
        popup_handler.driver.find_element.return_value = mock_body
        
        result = popup_handler._extract_review_content()
        
        assert result is not None
        assert result['recommendation'] == "Accept"
        assert 'overall rating' in result
        assert result['overall rating'] == 8
        assert 'technical quality' in result
        assert result['technical quality'] == 9
        assert 'review_text' in result
        assert "well-written paper" in result['review_text']
    
    def test_extract_review_content_no_data(self, popup_handler):
        """Test review extraction with no review data."""
        mock_body = MagicMock()
        mock_body.text = "This page has no review content"
        popup_handler.driver.find_element.return_value = mock_body
        
        result = popup_handler._extract_review_content()
        
        assert result is None
    
    def test_extract_abstract_with_marker(self, popup_handler):
        """Test abstract extraction with marker."""
        mock_body = MagicMock()
        mock_body.text = """
        Title: Test Paper
        
        Abstract:
        This paper presents a novel approach to solving complex problems.
        We demonstrate the effectiveness of our method through experiments.
        
        Keywords: optimization, algorithms
        """
        popup_handler.driver.find_element.return_value = mock_body
        
        result = popup_handler._extract_abstract_content()
        
        assert result is not None
        assert "novel approach" in result
        assert "Keywords:" not in result  # Should be truncated
    
    def test_extract_abstract_without_marker(self, popup_handler):
        """Test abstract extraction without explicit marker."""
        mock_body = MagicMock()
        # Text that looks like an abstract (200-5000 chars with sentences)
        mock_body.text = """
        This comprehensive study examines the fundamental principles of quantum computing.
        We analyze various quantum algorithms and their applications.
        The results show significant improvements over classical methods.
        Our findings have important implications for future research.
        """
        popup_handler.driver.find_element.return_value = mock_body
        
        result = popup_handler._extract_abstract_content()
        
        assert result is not None
        assert "quantum computing" in result
    
    def test_extract_generic_text(self, popup_handler):
        """Test generic text extraction."""
        mock_body = MagicMock()
        mock_body.text = "Some generic popup content here"
        popup_handler.driver.find_element.return_value = mock_body
        
        result = popup_handler._extract_generic_text()
        
        assert result == "Some generic popup content here"
    
    def test_extract_generic_text_too_short(self, popup_handler):
        """Test generic text extraction with short content."""
        mock_body = MagicMock()
        mock_body.text = "Short"
        popup_handler.driver.find_element.return_value = mock_body
        
        result = popup_handler._extract_generic_text()
        
        assert result is None
    
    def test_extract_referee_history_popup(self, popup_handler):
        """Test referee history extraction."""
        popup_url = "javascript:showHistory()"
        
        # Mock popup content extraction
        mock_content = """
        15-Jan-2024 - Invitation sent
        20-Jan-2024 - Invitation accepted
        01-Feb-2024 - Review submitted
        """
        
        with patch.object(popup_handler, 'extract_from_javascript_popup', return_value=mock_content):
            result = popup_handler.extract_referee_history_popup(popup_url)
        
        assert result is not None
        assert len(result) == 3
        assert result[0]['date'] == "15-Jan-2024"
        assert result[0]['event'] == "Invitation sent"
        assert result[2]['date'] == "01-Feb-2024"
        assert result[2]['event'] == "Review submitted"
    
    def test_extract_referee_history_no_content(self, popup_handler):
        """Test referee history with no content."""
        popup_url = "javascript:showHistory()"
        
        with patch.object(popup_handler, 'extract_from_javascript_popup', return_value=None):
            result = popup_handler.extract_referee_history_popup(popup_url)
        
        assert result is None
    
    def test_extract_author_details_popup(self, popup_handler):
        """Test author details extraction."""
        popup_url = "javascript:showAuthor()"
        
        # Mock email extraction
        with patch.object(popup_handler, 'extract_from_javascript_popup') as mock_extract:
            mock_extract.return_value = """
            Email: author@university.edu
            Affiliation: University of Example
            ORCID: 0000-0002-1234-5678
            """
            
            with patch.object(popup_handler, '_extract_email_from_popup', return_value="author@university.edu"):
                result = popup_handler.extract_author_details_popup(popup_url)
        
        assert result is not None
        assert result['email'] == "author@university.edu"
        assert 'affiliation' in result
        assert 'orcid' in result
        assert result['orcid'] == "0000-0002-1234-5678"
    
    def test_extract_author_details_no_data(self, popup_handler):
        """Test author details with no extractable data."""
        popup_url = "javascript:showAuthor()"
        
        with patch.object(popup_handler, 'extract_from_javascript_popup', return_value="No data"):
            with patch.object(popup_handler, '_extract_email_from_popup', return_value=None):
                result = popup_handler.extract_author_details_popup(popup_url)
        
        assert result is None