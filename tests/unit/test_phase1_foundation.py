"""
Comprehensive Test Suite for Phase 1 Foundation

Tests the unified authentication, browser management, and extraction contract
systems implemented in Phase 1 of the refactoring plan.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import Phase 1 components
from editorial_assistant.core.authentication import (
    AuthenticationProvider, ORCIDAuth, ScholarOneAuth, EditorialManagerAuth,
    AuthStatus, AuthenticationResult
)
from editorial_assistant.core.browser import (
    BrowserSession, BrowserPool, BrowserConfig, BrowserType
)
from editorial_assistant.core.extraction import (
    ExtractionContract, ExtractionResult, QualityValidator,
    ExtractionStatus, QualityScore, DataQualityMetrics
)
from editorial_assistant.core.data_models import Manuscript, Referee


class TestUnifiedAuthentication:
    """Test unified authentication architecture."""
    
    def test_orcid_auth_initialization(self):
        """Test ORCID authentication provider initialization."""
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        auth = ORCIDAuth('SICON', credentials)
        
        assert auth.journal_code == 'SICON'
        assert auth.get_login_url() == 'https://www.editorialmanager.com/siamjco/'
        assert auth.get_required_credentials() == ['username', 'password']
        assert auth.validate_credentials() == True
    
    def test_scholarone_auth_initialization(self):
        """Test ScholarOne authentication provider initialization."""
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        auth = ScholarOneAuth('MF', credentials)
        
        assert auth.journal_code == 'MF'
        assert auth.get_login_url() == 'https://mc.manuscriptcentral.com/mafi'
        assert auth.get_required_credentials() == ['username', 'password']
        assert auth.validate_credentials() == True
    
    def test_editorial_manager_auth_initialization(self):
        """Test Editorial Manager authentication provider initialization."""
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        auth = EditorialManagerAuth('FS', credentials)
        
        assert auth.journal_code == 'FS'
        assert auth.get_login_url() == 'https://www.editorialmanager.com/finsto/'
        assert auth.get_required_credentials() == ['username', 'password']
        assert auth.validate_credentials() == True
    
    def test_invalid_credentials_validation(self):
        """Test credential validation with missing credentials."""
        credentials = {'username': 'test@example.com'}  # Missing password
        auth = ORCIDAuth('SICON', credentials)
        
        assert auth.validate_credentials() == False
    
    def test_authentication_result_creation(self):
        """Test authentication result creation."""
        result = AuthenticationResult(
            status=AuthStatus.SUCCESS,
            message="Authentication successful",
            requires_2fa=False
        )
        
        assert result.status == AuthStatus.SUCCESS
        assert result.message == "Authentication successful"
        assert result.requires_2fa == False
        assert result.session_data is None


class TestBrowserManagement:
    """Test standardized browser management."""
    
    def test_browser_config_defaults(self):
        """Test browser configuration defaults."""
        config = BrowserConfig()
        
        assert config.browser_type == BrowserType.UNDETECTED_CHROME
        assert config.headless == True
        assert config.window_size == (1920, 1080)
        assert config.page_load_timeout == 30
    
    def test_browser_config_stealth_mode(self):
        """Test stealth mode configuration."""
        config = BrowserConfig.for_stealth_mode()
        
        assert config.browser_type == BrowserType.UNDETECTED_CHROME
        chrome_options = config.get_chrome_options()
        assert "--disable-blink-features=AutomationControlled" in chrome_options
    
    def test_browser_config_performance_mode(self):
        """Test performance mode configuration."""
        config = BrowserConfig.for_performance()
        
        assert config.disable_images == True
        assert config.disable_gpu == True
        chrome_options = config.get_chrome_options()
        assert "--disable-background-timer-throttling" in chrome_options
    
    def test_browser_session_initialization(self):
        """Test browser session initialization."""
        config = BrowserConfig()
        session = BrowserSession(config)
        
        assert session.config == config
        assert session.driver is None
        assert session._is_initialized == False
    
    @pytest.mark.asyncio
    async def test_browser_session_context_manager(self):
        """Test browser session async context manager."""
        config = BrowserConfig()
        
        # Mock the browser initialization to avoid actual browser startup
        with patch.object(BrowserSession, '_create_undetected_chrome') as mock_create:
            mock_driver = Mock()
            mock_driver.session_id = "test-session-123"
            mock_create.return_value = mock_driver
            
            async with BrowserSession(config) as session:
                assert session._is_initialized == True
                assert session.driver == mock_driver
    
    def test_browser_pool_initialization(self):
        """Test browser pool initialization."""
        config = BrowserConfig()
        pool = BrowserPool(pool_size=2, config=config)
        
        assert pool.pool_size == 2
        assert pool.config == config
        assert pool._is_initialized == False
    
    @pytest.mark.asyncio
    async def test_browser_pool_health_check(self):
        """Test browser pool health check."""
        config = BrowserConfig()
        pool = BrowserPool(pool_size=2, config=config)
        
        health = await pool.health_check()
        
        assert 'pool_size' in health
        assert 'total_sessions' in health
        assert 'is_healthy' in health
        assert health['pool_size'] == 2


class TestExtractionContract:
    """Test extraction contract and validation system."""
    
    def test_extraction_contract_initialization(self):
        """Test extraction contract initialization."""
        contract = ExtractionContract('SICON', 'SIAM Journal on Control and Optimization')
        
        assert contract.journal_code == 'SICON'
        assert contract.journal_name == 'SIAM Journal on Control and Optimization'
        assert contract.minimum_quality_threshold == 0.7
        assert contract._extraction_started == False
    
    def test_extraction_contract_lifecycle(self):
        """Test extraction contract begin/complete lifecycle."""
        contract = ExtractionContract('SICON', 'SIAM Journal on Control and Optimization')
        
        # Begin extraction
        contract.begin_extraction({'headless': True})
        assert contract._extraction_started == True
        assert contract.metadata.extraction_config == {'headless': True}
        
        # Complete extraction
        contract.complete_extraction()
        assert contract._extraction_completed == True
        assert contract.metadata.completed_at is not None
        assert contract.metadata.duration_seconds > 0
    
    def test_quality_score_calculation(self):
        """Test quality score calculation."""
        score = QualityScore()
        score.manuscript_completeness = 0.8
        score.referee_completeness = 0.6
        score.pdf_success_rate = 0.7
        score.data_integrity = 0.9
        score.has_referee_emails = True
        score.has_manuscript_pdfs = True
        
        overall = score.calculate_overall_score()
        
        assert 0.0 <= overall <= 1.0
        assert overall > 0.7  # Should be good with these scores
    
    def test_data_quality_metrics(self):
        """Test data quality metrics calculation."""
        metrics = DataQualityMetrics()
        metrics.total_manuscripts_found = 10
        metrics.total_manuscripts_processed = 9
        metrics.total_referees_found = 25
        metrics.total_referees_with_emails = 20
        metrics.total_pdfs_attempted = 10
        metrics.total_pdfs_downloaded = 8
        
        rates = metrics.calculate_success_rates()
        
        assert rates['manuscript_processing_rate'] == 0.9
        assert rates['email_extraction_rate'] == 0.8
        assert rates['pdf_download_rate'] == 0.8
    
    def test_extraction_result_creation(self):
        """Test extraction result creation."""
        # Create test data
        manuscripts = [
            Manuscript(manuscript_id="TEST-2025-001", title="Test Paper 1"),
            Manuscript(manuscript_id="TEST-2025-002", title="Test Paper 2")
        ]
        
        referees = [
            Referee(name="Dr. Test Reviewer", email="test@example.com")
        ]
        
        pdfs = [Path("/tmp/test1.pdf"), Path("/tmp/test2.pdf")]
        
        # Create contract and result
        contract = ExtractionContract('TEST', 'Test Journal')
        result = contract.create_result(manuscripts, referees, pdfs)
        
        assert len(result.manuscripts) == 2
        assert len(result.referees) == 1
        assert len(result.pdfs) == 2
        assert result.metadata is not None
        assert result.quality_score is not None
        assert result.metrics is not None
    
    def test_quality_validator_initialization(self):
        """Test quality validator initialization."""
        validator = QualityValidator()
        
        assert validator.strict_mode == False
        assert validator.thresholds['minimum_overall_score'] == 0.6
        
        # Test strict mode
        strict_validator = QualityValidator(strict_mode=True)
        assert strict_validator.thresholds['minimum_overall_score'] == 0.8
    
    def test_extraction_result_validation(self):
        """Test extraction result validation."""
        # Create test result with good data
        manuscripts = [
            Manuscript(manuscript_id="TEST-2025-001", title="Test Paper 1")
        ]
        
        contract = ExtractionContract('TEST', 'Test Journal')
        result = contract.create_result(manuscripts)
        
        # Validate
        validator = QualityValidator()
        validation = validator.validate_extraction_result(result)
        
        assert isinstance(validation.is_valid, bool)
        assert 'total_issues' in validation.summary
        assert isinstance(validation.recommendations, list)
    
    def test_extraction_status_determination(self):
        """Test extraction status determination logic."""
        contract = ExtractionContract('TEST', 'Test Journal')
        
        # Test successful extraction
        manuscripts = [
            Manuscript(manuscript_id="TEST-2025-001", title="Test Paper 1")
        ]
        result = contract.create_result(manuscripts)
        
        # Status should be determined based on quality
        assert result.status in [
            ExtractionStatus.SUCCESS, 
            ExtractionStatus.PARTIAL_SUCCESS,
            ExtractionStatus.FAILED
        ]


class TestIntegration:
    """Integration tests for Phase 1 components."""
    
    def test_authentication_browser_integration(self):
        """Test authentication provider with browser session."""
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        auth = ORCIDAuth('SICON', credentials)
        config = BrowserConfig()
        
        # Both components should be compatible
        assert auth.validate_credentials() == True
        assert config.browser_type == BrowserType.UNDETECTED_CHROME
    
    def test_browser_extraction_integration(self):
        """Test browser session with extraction contract."""
        config = BrowserConfig()
        session = BrowserSession(config)
        contract = ExtractionContract('TEST', 'Test Journal')
        
        # Components should be compatible
        assert session.config is not None
        assert contract.journal_code == 'TEST'
    
    def test_full_pipeline_mock(self):
        """Test complete extraction pipeline with mocked browser."""
        # 1. Authentication
        credentials = {'username': 'test@example.com', 'password': 'test123'}
        auth = ORCIDAuth('SICON', credentials)
        assert auth.validate_credentials()
        
        # 2. Browser session
        config = BrowserConfig()
        session = BrowserSession(config)
        
        # 3. Extraction contract
        contract = ExtractionContract('SICON', 'SIAM Journal on Control and Optimization')
        contract.begin_extraction()
        
        # 4. Mock extraction results
        manuscripts = [
            Manuscript(manuscript_id="SICON-2025-001", title="Control Theory Paper")
        ]
        
        result = contract.create_result(manuscripts)
        
        # 5. Verify pipeline
        assert result.status in [ExtractionStatus.SUCCESS, ExtractionStatus.PARTIAL_SUCCESS]
        assert len(result.manuscripts) == 1
        assert result.quality_score.overall_score >= 0.0


@pytest.mark.asyncio
async def test_concurrent_browser_sessions():
    """Test concurrent browser session management."""
    config = BrowserConfig()
    
    # Mock browser creation to avoid actual browser startup
    with patch.object(BrowserSession, '_create_undetected_chrome') as mock_create:
        mock_driver = Mock()
        mock_driver.session_id = "test-session"
        mock_create.return_value = mock_driver
        
        # Test concurrent sessions
        sessions = []
        for i in range(3):
            session = BrowserSession(config)
            await session.initialize()
            sessions.append(session)
        
        # All sessions should be initialized
        assert all(s._is_initialized for s in sessions)
        assert len(sessions) == 3
        
        # Cleanup
        for session in sessions:
            await session.cleanup()


def test_error_handling():
    """Test error handling in Phase 1 components."""
    # Test authentication with invalid credentials
    auth = ORCIDAuth('INVALID', {})
    assert auth.validate_credentials() == False
    
    # Test extraction with no data
    contract = ExtractionContract('TEST', 'Test Journal')
    result = contract.create_result([])  # Empty manuscripts
    
    assert result.status == ExtractionStatus.FAILED
    assert len(result.errors) > 0 or result.quality_score.overall_score < 0.3


def test_quality_thresholds():
    """Test quality threshold enforcement."""
    contract = ExtractionContract('TEST', 'Test Journal', minimum_quality_threshold=0.9)
    
    # Create low-quality result
    manuscripts = [Manuscript(manuscript_id="")]  # No ID
    result = contract.create_result(manuscripts)
    
    # Should fail quality check
    assert result.quality_score.overall_score < 0.9
    validator = QualityValidator()
    validation = validator.validate_extraction_result(result, 0.9)
    assert validation.has_errors()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])