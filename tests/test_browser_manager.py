"""Tests for Selenium browser management."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from selenium.common.exceptions import (
    TimeoutException, 
    WebDriverException,
    StaleElementReferenceException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from src.ecc.browser.selenium_manager import SeleniumBrowserManager


class TestSeleniumBrowserManager:
    """Test browser management functionality."""
    
    @pytest.fixture
    def browser_manager(self):
        """Create browser manager instance."""
        return SeleniumBrowserManager(headless=True, window_size=(1200, 800))
    
    @pytest.fixture
    def mock_driver(self):
        """Create mock WebDriver."""
        driver = MagicMock()
        driver.current_window_handle = "main_window"
        driver.window_handles = ["main_window"]
        return driver
    
    def test_initialization(self, browser_manager):
        """Test browser manager initialization."""
        assert browser_manager.headless == True
        assert browser_manager.window_size == (1200, 800)
        assert browser_manager.driver is None
        assert browser_manager.wait_timeout == 10
        assert browser_manager.retry_attempts == 3
    
    @patch('src.ecc.browser.selenium_manager.webdriver.Chrome')
    def test_setup_driver(self, mock_chrome, browser_manager):
        """Test driver setup with correct options."""
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        driver = browser_manager.setup_driver()
        
        # Verify Chrome was called with options
        assert mock_chrome.called
        chrome_options = mock_chrome.call_args[1]['options']
        
        # Check window size was set
        mock_driver.set_window_size.assert_called_with(1200, 800)
        
        # Check timeouts were set
        mock_driver.implicitly_wait.assert_called_with(5)
        mock_driver.set_page_load_timeout.assert_called_with(30)
        
        assert driver == mock_driver
        assert browser_manager.driver == mock_driver
    
    def test_wait_for_element_success(self, browser_manager, mock_driver):
        """Test successful element wait."""
        browser_manager.driver = mock_driver
        mock_element = MagicMock()
        
        with patch('src.ecc.browser.selenium_manager.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.return_value = mock_element
            mock_wait.return_value = mock_wait_instance
            
            result = browser_manager.wait_for_element(By.ID, "test_id", timeout=5)
            
            mock_wait.assert_called_with(mock_driver, 5)
            assert result == mock_element
    
    def test_wait_for_element_timeout(self, browser_manager, mock_driver):
        """Test element wait timeout."""
        browser_manager.driver = mock_driver
        
        with patch('src.ecc.browser.selenium_manager.WebDriverWait') as mock_wait:
            mock_wait_instance = MagicMock()
            mock_wait_instance.until.side_effect = TimeoutException()
            mock_wait.return_value = mock_wait_instance
            
            result = browser_manager.wait_for_element(By.ID, "test_id")
            
            assert result is None
    
    def test_wait_for_element_no_driver(self, browser_manager):
        """Test wait_for_element without driver initialized."""
        with pytest.raises(RuntimeError, match="Driver not initialized"):
            browser_manager.wait_for_element(By.ID, "test_id")
    
    def test_safe_click_success(self, browser_manager, mock_driver):
        """Test successful element click."""
        browser_manager.driver = mock_driver
        mock_element = MagicMock()
        
        result = browser_manager.safe_click(mock_element)
        
        # Verify scroll and click
        mock_driver.execute_script.assert_called_with(
            "arguments[0].scrollIntoView(true);", 
            mock_element
        )
        mock_element.click.assert_called_once()
        assert result == True
    
    def test_safe_click_with_retry(self, browser_manager, mock_driver):
        """Test click with retry on failure."""
        browser_manager.driver = mock_driver
        mock_element = MagicMock()
        
        # First attempt fails, second succeeds
        mock_element.click.side_effect = [
            StaleElementReferenceException(),
            None
        ]
        
        result = browser_manager.safe_click(mock_element, retry_attempts=2)
        
        assert mock_element.click.call_count == 2
        assert result == True
    
    def test_safe_click_javascript_fallback(self, browser_manager, mock_driver):
        """Test JavaScript click fallback."""
        browser_manager.driver = mock_driver
        mock_element = MagicMock()
        
        # Regular click fails
        mock_element.click.side_effect = WebDriverException()
        
        result = browser_manager.safe_click(mock_element, retry_attempts=1)
        
        # Should try JavaScript click
        expected_call = call("arguments[0].click();", mock_element)
        assert expected_call in mock_driver.execute_script.call_args_list
        assert result == True
    
    def test_safe_send_keys_success(self, browser_manager, mock_driver):
        """Test successful key sending."""
        browser_manager.driver = mock_driver
        mock_element = MagicMock()
        
        result = browser_manager.safe_send_keys(mock_element, "test text")
        
        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called()
        assert result == True
    
    def test_safe_send_keys_no_clear(self, browser_manager, mock_driver):
        """Test sending keys without clearing first."""
        browser_manager.driver = mock_driver
        mock_element = MagicMock()
        
        result = browser_manager.safe_send_keys(
            mock_element, 
            "test text", 
            clear_first=False
        )
        
        mock_element.clear.assert_not_called()
        # Should only have one send_keys call (the text)
        assert mock_element.send_keys.call_count == 1
        mock_element.send_keys.assert_called_with("test text")
        assert result == True
    
    def test_navigate_with_retry_success(self, browser_manager, mock_driver):
        """Test successful navigation."""
        browser_manager.driver = mock_driver
        mock_driver.current_url = "https://example.com"
        
        result = browser_manager.navigate_with_retry("https://example.com")
        
        mock_driver.get.assert_called_with("https://example.com")
        assert result == True
    
    def test_navigate_with_retry_failure(self, browser_manager, mock_driver):
        """Test navigation with retries on failure."""
        browser_manager.driver = mock_driver
        mock_driver.get.side_effect = WebDriverException()
        mock_driver.current_url = None
        
        result = browser_manager.navigate_with_retry(
            "https://example.com", 
            retry_attempts=2
        )
        
        assert mock_driver.get.call_count == 2
        assert result == False
    
    def test_dismiss_cookie_banner_found(self, browser_manager, mock_driver):
        """Test dismissing cookie banner when found."""
        browser_manager.driver = mock_driver
        mock_element = MagicMock()
        mock_element.is_displayed.return_value = True
        mock_driver.find_element.return_value = mock_element
        
        result = browser_manager.dismiss_cookie_banner()
        
        assert browser_manager.safe_click(mock_element)
        assert result == True
    
    def test_dismiss_cookie_banner_not_found(self, browser_manager, mock_driver):
        """Test when no cookie banner found."""
        browser_manager.driver = mock_driver
        mock_driver.find_element.side_effect = Exception()
        
        result = browser_manager.dismiss_cookie_banner()
        
        assert result == False
    
    def test_switch_to_popup_window(self, browser_manager, mock_driver):
        """Test switching to popup window."""
        browser_manager.driver = mock_driver
        mock_driver.window_handles = ["main_window", "popup_window"]
        
        with patch('src.ecc.browser.selenium_manager.WebDriverWait'):
            result = browser_manager.switch_to_popup_window()
            
            mock_driver.switch_to.window.assert_called_with("popup_window")
            assert result == True
    
    def test_close_popup_and_return(self, browser_manager, mock_driver):
        """Test closing popup and returning to main."""
        browser_manager.driver = mock_driver
        
        result = browser_manager.close_popup_and_return()
        
        mock_driver.close.assert_called_once()
        mock_driver.switch_to.window.assert_called_with("main_window")
        assert result == True
    
    def test_execute_script_safe_success(self, browser_manager, mock_driver):
        """Test safe script execution."""
        browser_manager.driver = mock_driver
        mock_driver.execute_script.return_value = "result"
        
        result = browser_manager.execute_script_safe("return 1;")
        
        mock_driver.execute_script.assert_called_with("return 1;")
        assert result == "result"
    
    def test_execute_script_safe_failure(self, browser_manager, mock_driver):
        """Test script execution failure handling."""
        browser_manager.driver = mock_driver
        mock_driver.execute_script.side_effect = Exception("Script error")
        
        result = browser_manager.execute_script_safe("bad script")
        
        assert result is None
    
    def test_take_screenshot_success(self, browser_manager, mock_driver):
        """Test taking screenshot."""
        browser_manager.driver = mock_driver
        
        result = browser_manager.take_screenshot("test.png")
        
        mock_driver.save_screenshot.assert_called_with("test.png")
        assert result == True
    
    def test_cleanup(self, browser_manager, mock_driver):
        """Test cleanup of browser resources."""
        browser_manager.driver = mock_driver
        
        browser_manager.cleanup()
        
        mock_driver.quit.assert_called_once()
        assert browser_manager.driver is None
    
    def test_context_manager(self):
        """Test context manager usage."""
        with patch('src.ecc.browser.selenium_manager.webdriver.Chrome'):
            with SeleniumBrowserManager() as browser:
                assert browser.driver is not None
            
            # After context exit, driver should be cleaned up
            assert browser.driver is None
    
    def test_with_retry_success(self, browser_manager):
        """Test retry wrapper with successful operation."""
        mock_operation = MagicMock(return_value="success")
        
        result = browser_manager.with_retry(mock_operation, max_attempts=3)
        
        mock_operation.assert_called_once()
        assert result == "success"
    
    def test_with_retry_eventual_success(self, browser_manager):
        """Test retry wrapper with eventual success."""
        mock_operation = MagicMock(side_effect=[None, None, "success"])
        
        result = browser_manager.with_retry(mock_operation, max_attempts=3, delay=0.1)
        
        assert mock_operation.call_count == 3
        assert result == "success"
    
    def test_with_retry_all_failures(self, browser_manager):
        """Test retry wrapper when all attempts fail."""
        mock_operation = MagicMock(side_effect=Exception("Error"))
        
        result = browser_manager.with_retry(mock_operation, max_attempts=2, delay=0.1)
        
        assert mock_operation.call_count == 2
        assert result is None