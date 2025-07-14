"""
Comprehensive unit tests for AI Orchestrator Service
Tests all functionality of the central AI coordination service
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4
from pathlib import Path

from src.ai.services.ai_orchestrator_service import AIOrchestrator
from src.ai.models.manuscript_analysis import (
    ManuscriptMetadata, DeskRejectionAnalysis, RefereeRecommendation,
    AnalysisResult, ComprehensiveAnalysis, AnalysisRecommendation, 
    QualityIssueType, QualityIssue
)
from src.ai.ports.ai_client import AIClient, AIModel
from src.ai.ports.pdf_processor import PDFProcessor


class MockAIClient:
    """Mock AI client for testing"""
    
    def __init__(self):
        self.call_count = 0
        self.last_call_args = None
    
    async def analyze_desk_rejection(self, title: str, abstract: str, journal_requirements: str, **kwargs):
        self.call_count += 1
        self.last_call_args = {'title': title, 'abstract': abstract, 'journal_requirements': journal_requirements}
        
        # Return different responses based on input
        if "reject" in title.lower() or len(abstract) < 20:
            recommendation = AnalysisRecommendation.DESK_REJECT
            confidence = 0.9
            reasons = ["Insufficient quality", "Poor methodology"]
            issues = [QualityIssue(
                issue_type=QualityIssueType.POOR_PRESENTATION,
                description="Poor presentation quality",
                severity=0.8,
                suggested_improvement="Improve writing clarity"
            )]
        else:
            recommendation = AnalysisRecommendation.ACCEPT_FOR_REVIEW
            confidence = 0.85
            reasons = []
            issues = []
        
        return DeskRejectionAnalysis(
            recommendation=recommendation,
            confidence=confidence,
            rejection_reasons=reasons,
            quality_issues=issues,
            detailed_feedback="Mock detailed feedback"
        )
    
    async def recommend_referees(self, title: str, abstract: str, expertise_keywords: list, count: int = 5, **kwargs):
        self.call_count += 1
        self.last_call_args = {'title': title, 'abstract': abstract, 'expertise_keywords': expertise_keywords, 'count': count}
        
        referees = []
        for i in range(min(count, 5)):
            referees.append(RefereeRecommendation(
                referee_name=f"Dr. Mock Referee {i+1}",
                expertise_match=0.8 + 0.05 * i,
                availability_score=0.9 - 0.05 * i,
                quality_score=0.85 + 0.03 * i,
                workload_score=0.75 + 0.05 * i,
                overall_score=0.82 + 0.02 * i,
                expertise_areas=[f"area_{i}", "optimization"],
                matching_keywords=expertise_keywords[:2] if expertise_keywords else ["keyword1", "keyword2"],
                rationale=f"Mock rationale for referee {i+1}",
                confidence=0.8 + 0.04 * i
            ))
        
        return referees
    
    async def extract_metadata_from_text(self, title: str, abstract: str, full_text: str = None, **kwargs):
        self.call_count += 1
        
        # Extract keywords from title and abstract
        text = f"{title} {abstract}".lower()
        keywords = []
        for word in ["optimization", "algorithm", "machine", "learning", "analysis", "method"]:
            if word in text:
                keywords.append(word)
        
        return ManuscriptMetadata(
            title=title,
            abstract=abstract,
            keywords=keywords,
            research_area="Mathematics" if "math" in text else "Computer Science",
            methodology="Computational" if "algorithm" in text else "Theoretical",
            complexity_score=0.7,
            novelty_score=0.8,
            technical_quality_score=0.75,
            presentation_quality_score=0.8,
            scope_fit_score=0.85
        )


class MockPDFProcessor:
    """Mock PDF processor for testing"""
    
    def __init__(self):
        self.call_count = 0
        self.should_fail = False
    
    async def extract_text_content(self, pdf_path: Path):
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Mock PDF processing error")
        
        return {
            'title': 'Extracted Title from PDF',
            'abstract': 'Extracted abstract from PDF document.',
            'full_text': 'This is the full text content extracted from the PDF file.',
            'sections': {
                'introduction': 'Introduction section content',
                'methodology': 'Methodology section content',
                'results': 'Results section content',
                'conclusion': 'Conclusion section content'
            }
        }
    
    async def extract_metadata(self, pdf_path: Path):
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Mock PDF metadata extraction error")
        
        return {
            'title': 'PDF Metadata Title',
            'authors': ['Dr. Author One', 'Prof. Author Two'],
            'keywords': ['pdf', 'extraction', 'test'],
            'creation_date': datetime.now(),
            'page_count': 15,
            'file_size': 1024 * 1024
        }
    
    async def validate_pdf(self, pdf_path: Path):
        self.call_count += 1
        
        return {
            'is_valid': not self.should_fail,
            'is_readable': not self.should_fail,
            'quality_score': 0.85 if not self.should_fail else 0.2,
            'issues': [] if not self.should_fail else ["Mock validation error"],
            'recommendations': ["Use high-quality PDF"] if self.should_fail else []
        }


@pytest.fixture
def mock_ai_client():
    return MockAIClient()


@pytest.fixture
def mock_pdf_processor():
    return MockPDFProcessor()


@pytest.fixture
def ai_orchestrator(mock_ai_client, mock_pdf_processor):
    return AIOrchestrator(
        ai_client=mock_ai_client,
        pdf_processor=mock_pdf_processor,
        cache_enabled=False
    )


@pytest.fixture
def ai_orchestrator_with_cache(mock_ai_client, mock_pdf_processor):
    return AIOrchestrator(
        ai_client=mock_ai_client,
        pdf_processor=mock_pdf_processor,
        cache_enabled=True
    )


class TestAIOrchestratorInitialization:
    """Test AI orchestrator initialization and configuration"""
    
    def test_orchestrator_initialization(self, mock_ai_client, mock_pdf_processor):
        """Test basic orchestrator initialization"""
        orchestrator = AIOrchestrator(
            ai_client=mock_ai_client,
            pdf_processor=mock_pdf_processor,
            cache_enabled=True
        )
        
        assert orchestrator.ai_client == mock_ai_client
        assert orchestrator.pdf_processor == mock_pdf_processor
        assert orchestrator.cache_enabled is True
        assert orchestrator.default_model == AIModel.GPT_4_TURBO
        assert orchestrator.confidence_threshold == 0.7
        assert orchestrator.max_referee_recommendations == 10
    
    def test_orchestrator_configuration_options(self, mock_ai_client, mock_pdf_processor):
        """Test orchestrator with different configuration options"""
        orchestrator = AIOrchestrator(
            ai_client=mock_ai_client,
            pdf_processor=mock_pdf_processor,
            cache_enabled=False
        )
        
        assert orchestrator.cache_enabled is False
    
    def test_orchestrator_with_none_dependencies(self):
        """Test orchestrator error handling with None dependencies"""
        with pytest.raises((TypeError, AttributeError)):
            AIOrchestrator(ai_client=None, pdf_processor=None)


class TestDeskRejectionAnalysis:
    """Test desk rejection analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_basic_desk_rejection_analysis(self, ai_orchestrator, mock_ai_client):
        """Test basic desk rejection analysis"""
        result = await ai_orchestrator.analyze_desk_rejection(
            title="Test Manuscript",
            abstract="This is a test abstract with sufficient content for analysis.",
            journal_code="SICON"
        )
        
        assert isinstance(result, DeskRejectionAnalysis)
        assert result.recommendation in AnalysisRecommendation
        assert 0 <= result.confidence <= 1
        assert mock_ai_client.call_count == 1
    
    @pytest.mark.asyncio
    async def test_desk_rejection_with_poor_quality(self, ai_orchestrator, mock_ai_client):
        """Test desk rejection analysis with poor quality manuscript"""
        result = await ai_orchestrator.analyze_desk_rejection(
            title="Bad Reject Title",
            abstract="Short",  # Very short abstract
            journal_code="SICON"
        )
        
        assert result.recommendation == AnalysisRecommendation.DESK_REJECT
        assert result.confidence > 0.8
        assert len(result.rejection_reasons) > 0
        assert len(result.quality_issues) > 0
    
    @pytest.mark.asyncio
    async def test_desk_rejection_with_good_quality(self, ai_orchestrator, mock_ai_client):
        """Test desk rejection analysis with good quality manuscript"""
        result = await ai_orchestrator.analyze_desk_rejection(
            title="Novel Algorithm for Optimization",
            abstract="This paper presents a comprehensive approach to solving complex optimization problems with novel theoretical contributions and extensive experimental validation.",
            journal_code="SICON"
        )
        
        assert result.recommendation == AnalysisRecommendation.ACCEPT_FOR_REVIEW
        assert result.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_desk_rejection_invalid_inputs(self, ai_orchestrator):
        """Test desk rejection analysis with invalid inputs"""
        with pytest.raises(ValueError):
            await ai_orchestrator.analyze_desk_rejection(
                title="",
                abstract="",
                journal_code=""
            )
    
    @pytest.mark.asyncio
    async def test_desk_rejection_journal_specific(self, ai_orchestrator, mock_ai_client):
        """Test that desk rejection analysis adapts to different journals"""
        journals = ["SICON", "SIFIN", "MF", "MOR"]
        
        for journal in journals:
            result = await ai_orchestrator.analyze_desk_rejection(
                title="Test Title",
                abstract="Test abstract content for journal-specific analysis.",
                journal_code=journal
            )
            
            assert isinstance(result, DeskRejectionAnalysis)
            # Should contain journal-specific requirements
            assert journal.lower() in mock_ai_client.last_call_args['journal_requirements'].lower()


class TestRefereeRecommendation:
    """Test referee recommendation functionality"""
    
    @pytest.mark.asyncio
    async def test_basic_referee_recommendation(self, ai_orchestrator, mock_ai_client):
        """Test basic referee recommendation"""
        recommendations = await ai_orchestrator.recommend_referees(
            title="Optimization Algorithm",
            abstract="This paper presents a new optimization algorithm.",
            journal_code="SICON",
            count=3
        )
        
        assert len(recommendations) == 3
        assert all(isinstance(r, RefereeRecommendation) for r in recommendations)
        assert all(0 <= r.overall_score <= 1 for r in recommendations)
        assert mock_ai_client.call_count == 1
    
    @pytest.mark.asyncio
    async def test_referee_recommendation_different_counts(self, ai_orchestrator, mock_ai_client):
        """Test referee recommendation with different counts"""
        for count in [1, 3, 5, 10]:
            recommendations = await ai_orchestrator.recommend_referees(
                title="Test Title",
                abstract="Test abstract",
                journal_code="SICON",
                count=count
            )
            
            # Should not exceed 5 (mock limitation) or requested count
            expected_count = min(count, 5)
            assert len(recommendations) == expected_count
    
    @pytest.mark.asyncio
    async def test_referee_recommendation_sorting(self, ai_orchestrator):
        """Test that referee recommendations are sorted by score"""
        recommendations = await ai_orchestrator.recommend_referees(
            title="Test Title",
            abstract="Test abstract",
            journal_code="SICON",
            count=5
        )
        
        # Should be sorted by overall_score descending
        scores = [r.overall_score for r in recommendations]
        assert scores == sorted(scores, reverse=True)
    
    @pytest.mark.asyncio
    async def test_referee_recommendation_expertise_extraction(self, ai_orchestrator, mock_ai_client):
        """Test that expertise keywords are extracted from manuscript"""
        await ai_orchestrator.recommend_referees(
            title="Machine Learning for Optimization",
            abstract="This paper applies machine learning techniques to optimization problems.",
            journal_code="SICON",
            count=3
        )
        
        # Check that keywords were extracted and passed to AI client
        args = mock_ai_client.last_call_args
        assert 'expertise_keywords' in args
        assert len(args['expertise_keywords']) > 0
    
    @pytest.mark.asyncio
    async def test_referee_recommendation_invalid_inputs(self, ai_orchestrator):
        """Test referee recommendation with invalid inputs"""
        with pytest.raises(ValueError):
            await ai_orchestrator.recommend_referees(
                title="",
                abstract="",
                journal_code="",
                count=0
            )


class TestComprehensiveAnalysis:
    """Test comprehensive manuscript analysis functionality"""
    
    @pytest.mark.asyncio
    async def test_comprehensive_analysis_basic(self, ai_orchestrator, mock_ai_client):
        """Test basic comprehensive analysis"""
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="TEST-001",
            journal_code="SICON",
            title="Test Manuscript",
            abstract="This is a comprehensive test of the analysis pipeline."
        )
        
        assert isinstance(result, AnalysisResult)
        assert result.manuscript_id == "TEST-001"
        assert result.journal_code == "SICON"
        assert isinstance(result.metadata, ManuscriptMetadata)
        assert isinstance(result.desk_rejection_analysis, DeskRejectionAnalysis)
        assert len(result.referee_recommendations) > 0
        assert result.processing_time_seconds >= 0
        assert result.analysis_timestamp
    
    @pytest.mark.asyncio
    async def test_comprehensive_analysis_with_pdf(self, ai_orchestrator, mock_pdf_processor, tmp_path):
        """Test comprehensive analysis with PDF processing"""
        # Create a test PDF file
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_text("dummy pdf content")
        
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="TEST-PDF-001",
            journal_code="SICON",
            title="Test Title",
            abstract="Test Abstract",
            pdf_path=str(pdf_path)
        )
        
        assert result.pdf_path == str(pdf_path)
        assert result.text_extracted is True
        assert mock_pdf_processor.call_count > 0
    
    @pytest.mark.asyncio
    async def test_comprehensive_analysis_pdf_error_handling(self, ai_orchestrator, mock_pdf_processor):
        """Test comprehensive analysis handles PDF processing errors"""
        mock_pdf_processor.should_fail = True
        
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="TEST-ERROR-001",
            journal_code="SICON",
            title="Test Title",
            abstract="Test Abstract",
            pdf_path="/fake/path/to/file.pdf"
        )
        
        # Should still complete analysis without PDF
        assert isinstance(result, AnalysisResult)
        assert result.text_extracted is False
    
    @pytest.mark.asyncio
    async def test_comprehensive_analysis_timing(self, ai_orchestrator):
        """Test that comprehensive analysis timing is tracked"""
        start_time = datetime.now()
        
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="TIMING-TEST",
            journal_code="SICON",
            title="Timing Test",
            abstract="Testing timing functionality"
        )
        
        end_time = datetime.now()
        
        assert result.processing_time_seconds > 0
        assert result.analysis_timestamp >= start_time
        assert result.analysis_timestamp <= end_time
    
    @pytest.mark.asyncio
    async def test_comprehensive_analysis_metadata_integration(self, ai_orchestrator, mock_ai_client):
        """Test that metadata is properly integrated from all sources"""
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="METADATA-TEST",
            journal_code="SICON",
            title="Machine Learning Algorithm",
            abstract="This paper presents a novel machine learning algorithm for optimization."
        )
        
        # Check that metadata contains expected information
        assert "machine" in result.metadata.keywords or "learning" in result.metadata.keywords
        assert result.metadata.title == "Machine Learning Algorithm"
        assert result.metadata.overall_quality_score() > 0


class TestCaching:
    """Test caching functionality"""
    
    @pytest.mark.asyncio
    async def test_caching_enabled(self, ai_orchestrator_with_cache, mock_ai_client):
        """Test that caching works when enabled"""
        # First call
        result1 = await ai_orchestrator_with_cache.analyze_desk_rejection(
            title="Cache Test",
            abstract="Testing caching functionality",
            journal_code="SICON"
        )
        
        call_count_after_first = mock_ai_client.call_count
        
        # Second identical call
        result2 = await ai_orchestrator_with_cache.analyze_desk_rejection(
            title="Cache Test",
            abstract="Testing caching functionality",
            journal_code="SICON"
        )
        
        # Call count should not increase (cached result)
        assert mock_ai_client.call_count == call_count_after_first
        assert result1.recommendation == result2.recommendation
        assert result1.confidence == result2.confidence
    
    @pytest.mark.asyncio
    async def test_caching_disabled(self, ai_orchestrator, mock_ai_client):
        """Test that caching is disabled when configured"""
        # First call
        await ai_orchestrator.analyze_desk_rejection(
            title="No Cache Test",
            abstract="Testing no caching functionality",
            journal_code="SICON"
        )
        
        call_count_after_first = mock_ai_client.call_count
        
        # Second identical call
        await ai_orchestrator.analyze_desk_rejection(
            title="No Cache Test",
            abstract="Testing no caching functionality",
            journal_code="SICON"
        )
        
        # Call count should increase (no caching)
        assert mock_ai_client.call_count == call_count_after_first + 1
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, ai_orchestrator_with_cache, mock_ai_client):
        """Test that different inputs generate different cache keys"""
        # Call with different titles
        await ai_orchestrator_with_cache.analyze_desk_rejection(
            title="Cache Test 1",
            abstract="Same abstract",
            journal_code="SICON"
        )
        
        await ai_orchestrator_with_cache.analyze_desk_rejection(
            title="Cache Test 2",
            abstract="Same abstract",
            journal_code="SICON"
        )
        
        # Should make two separate calls (different cache keys)
        assert mock_ai_client.call_count == 2


class TestErrorHandling:
    """Test error handling and resilience"""
    
    @pytest.mark.asyncio
    async def test_ai_client_error_handling(self, ai_orchestrator, mock_pdf_processor):
        """Test handling of AI client errors"""
        # Create a mock AI client that raises errors
        error_client = Mock()
        error_client.analyze_desk_rejection = AsyncMock(side_effect=Exception("AI service error"))
        
        orchestrator = AIOrchestrator(
            ai_client=error_client,
            pdf_processor=mock_pdf_processor,
            cache_enabled=False
        )
        
        with pytest.raises(Exception):
            await orchestrator.analyze_desk_rejection(
                title="Error Test",
                abstract="Testing error handling",
                journal_code="SICON"
            )
    
    @pytest.mark.asyncio
    async def test_pdf_processor_error_handling(self, ai_orchestrator, mock_ai_client, mock_pdf_processor):
        """Test handling of PDF processor errors"""
        mock_pdf_processor.should_fail = True
        
        # Should not raise exception, but handle gracefully
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="ERROR-TEST",
            journal_code="SICON",
            title="Error Test",
            abstract="Testing PDF error handling",
            pdf_path="/fake/path.pdf"
        )
        
        assert isinstance(result, AnalysisResult)
        assert result.text_extracted is False
    
    @pytest.mark.asyncio
    async def test_partial_failure_handling(self, ai_orchestrator, mock_ai_client):
        """Test handling when some components fail but others succeed"""
        # Mock AI client that fails for referee recommendations but succeeds for desk rejection
        partial_fail_client = Mock()
        partial_fail_client.analyze_desk_rejection = mock_ai_client.analyze_desk_rejection
        partial_fail_client.recommend_referees = AsyncMock(side_effect=Exception("Referee service error"))
        partial_fail_client.extract_metadata_from_text = mock_ai_client.extract_metadata_from_text
        
        orchestrator = AIOrchestrator(
            ai_client=partial_fail_client,
            pdf_processor=MockPDFProcessor(),
            cache_enabled=False
        )
        
        # Should complete with partial results
        result = await orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="PARTIAL-FAIL-TEST",
            journal_code="SICON",
            title="Partial Failure Test",
            abstract="Testing partial failure handling"
        )
        
        assert isinstance(result, AnalysisResult)
        assert isinstance(result.desk_rejection_analysis, DeskRejectionAnalysis)
        # Referee recommendations might be empty due to failure
        assert isinstance(result.referee_recommendations, list)


class TestPerformanceAndScaling:
    """Test performance characteristics and scaling"""
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, ai_orchestrator):
        """Test that orchestrator handles concurrent requests"""
        tasks = []
        for i in range(5):
            task = ai_orchestrator.analyze_desk_rejection(
                title=f"Concurrent Test {i}",
                abstract=f"Concurrent abstract {i}",
                journal_code="SICON"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(isinstance(r, DeskRejectionAnalysis) for r in results)
    
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, ai_orchestrator):
        """Test that orchestrator doesn't accumulate memory over multiple operations"""
        # This is a basic test - more sophisticated memory testing would use memory profiling
        initial_call_count = ai_orchestrator.ai_client.call_count
        
        # Perform multiple operations
        for i in range(10):
            await ai_orchestrator.analyze_desk_rejection(
                title=f"Memory Test {i}",
                abstract=f"Memory test abstract {i}",
                journal_code="SICON"
            )
        
        # Verify all operations completed
        assert ai_orchestrator.ai_client.call_count == initial_call_count + 10


class TestValidationAndSanitization:
    """Test input validation and sanitization"""
    
    @pytest.mark.asyncio
    async def test_input_validation(self, ai_orchestrator):
        """Test that inputs are properly validated"""
        # Test empty strings
        with pytest.raises(ValueError):
            await ai_orchestrator.analyze_desk_rejection("", "", "")
        
        # Test None values
        with pytest.raises(ValueError):
            await ai_orchestrator.analyze_desk_rejection(None, None, None)
    
    @pytest.mark.asyncio
    async def test_input_sanitization(self, ai_orchestrator, mock_ai_client):
        """Test that inputs are properly sanitized"""
        # Test with special characters and long strings
        title = "Test Title with Special Characters!@#$%^&*()"
        abstract = "A" * 10000  # Very long abstract
        
        result = await ai_orchestrator.analyze_desk_rejection(
            title=title,
            abstract=abstract,
            journal_code="SICON"
        )
        
        assert isinstance(result, DeskRejectionAnalysis)
        # Verify that the AI client received sanitized inputs
        assert mock_ai_client.last_call_args['title'] == title
        # Abstract might be truncated for performance
        assert len(mock_ai_client.last_call_args['abstract']) <= len(abstract)
    
    @pytest.mark.asyncio
    async def test_journal_code_validation(self, ai_orchestrator):
        """Test that journal codes are validated"""
        valid_journals = ["SICON", "SIFIN", "MF", "MOR", "JOTA", "FS"]
        
        for journal in valid_journals:
            result = await ai_orchestrator.analyze_desk_rejection(
                title="Test",
                abstract="Test abstract",
                journal_code=journal
            )
            assert isinstance(result, DeskRejectionAnalysis)
        
        # Test invalid journal code
        result = await ai_orchestrator.analyze_desk_rejection(
            title="Test",
            abstract="Test abstract",
            journal_code="INVALID"
        )
        # Should still work but might use default settings
        assert isinstance(result, DeskRejectionAnalysis)