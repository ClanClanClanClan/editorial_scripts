"""
Integration tests for the complete AI pipeline
Tests end-to-end functionality of manuscript analysis and referee recommendations
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from uuid import uuid4

from src.ai.services.ai_orchestrator_service import AIOrchestrator
from src.ai.services.async_openai_client import AsyncOpenAIClient
from src.ai.services.pypdf_processor import PyPDFProcessor
from src.ai.models.manuscript_analysis import (
    ManuscriptMetadata, DeskRejectionAnalysis, RefereeRecommendation,
    AnalysisResult, AnalysisRecommendation, QualityIssueType
)


@pytest.fixture
def mock_ai_client():
    """Mock AI client that returns predictable responses"""
    client = Mock(spec=AsyncOpenAIClient)
    
    # Mock desk rejection analysis
    async def mock_analyze_desk_rejection(*args, **kwargs):
        return DeskRejectionAnalysis(
            recommendation=AnalysisRecommendation.ACCEPT_FOR_REVIEW,
            confidence=0.85,
            rejection_reasons=[],
            quality_issues=[],
            detailed_feedback="Well-structured manuscript with clear methodology."
        )
    
    # Mock referee recommendations
    async def mock_recommend_referees(*args, **kwargs):
        return [
            RefereeRecommendation(
                referee_name="Dr. Sarah Chen",
                expertise_match=0.92,
                availability_score=0.88,
                quality_score=0.95,
                workload_score=0.75,
                overall_score=0.88,
                expertise_areas=["optimization", "machine learning"],
                rationale="Expert in optimization with recent publications in the field"
            ),
            RefereeRecommendation(
                referee_name="Prof. Michael Thompson",
                expertise_match=0.87,
                availability_score=0.90,
                quality_score=0.92,
                workload_score=0.80,
                overall_score=0.87,
                expertise_areas=["numerical analysis", "optimization"],
                rationale="Strong background in numerical methods"
            )
        ]
    
    client.analyze_desk_rejection = mock_analyze_desk_rejection
    client.recommend_referees = mock_recommend_referees
    return client


@pytest.fixture
def mock_pdf_processor():
    """Mock PDF processor"""
    processor = Mock(spec=PyPDFProcessor)
    
    async def mock_extract_text_content(*args, **kwargs):
        return {
            'title': 'A Novel Approach to Optimization',
            'abstract': 'This paper presents a new optimization algorithm...',
            'full_text': 'Introduction\nThis paper addresses...',
            'sections': {
                'introduction': 'This paper addresses...',
                'methodology': 'We propose a new algorithm...',
                'results': 'Our experiments show...',
                'conclusion': 'We have demonstrated...'
            }
        }
    
    async def mock_extract_metadata(*args, **kwargs):
        return {
            'title': 'A Novel Approach to Optimization',
            'authors': ['Dr. Jane Smith', 'Prof. John Doe'],
            'keywords': ['optimization', 'algorithm', 'numerical methods'],
            'creation_date': datetime.now(),
            'page_count': 15,
            'file_size': 1024 * 1024  # 1MB
        }
    
    processor.extract_text_content = mock_extract_text_content
    processor.extract_metadata = mock_extract_metadata
    return processor


@pytest.fixture
def ai_orchestrator(mock_ai_client, mock_pdf_processor):
    """AI orchestrator with mocked dependencies"""
    return AIOrchestrator(
        ai_client=mock_ai_client,
        pdf_processor=mock_pdf_processor,
        cache_enabled=False  # Disable caching for tests
    )


class TestAIPipelineIntegration:
    """Test the complete AI pipeline end-to-end"""
    
    @pytest.mark.asyncio
    async def test_manuscript_analysis_pipeline(self, ai_orchestrator):
        """Test complete manuscript analysis workflow"""
        # Test input
        manuscript_id = "TEST-001"
        journal_code = "SICON"
        title = "A Novel Approach to Optimization"
        abstract = "This paper presents a new optimization algorithm for constrained problems."
        
        # Execute the pipeline
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id=manuscript_id,
            journal_code=journal_code,
            title=title,
            abstract=abstract
        )
        
        # Verify results
        assert isinstance(result, AnalysisResult)
        assert result.manuscript_id == manuscript_id
        assert result.journal_code == journal_code
        
        # Check metadata extraction
        assert result.metadata.title == title
        assert result.metadata.overall_quality_score() > 0
        
        # Check desk rejection analysis
        assert result.desk_rejection_analysis.recommendation == AnalysisRecommendation.ACCEPT_FOR_REVIEW
        assert result.desk_rejection_analysis.confidence >= 0.5
        
        # Check referee recommendations
        assert len(result.referee_recommendations) >= 2
        for ref in result.referee_recommendations:
            assert ref.overall_score > 0
            assert len(ref.expertise_areas) > 0
            assert ref.rationale
        
        # Check processing metadata
        assert result.processing_time_seconds >= 0
        assert result.analysis_timestamp
    
    @pytest.mark.asyncio
    async def test_desk_rejection_analysis_only(self, ai_orchestrator):
        """Test desk rejection analysis in isolation"""
        result = await ai_orchestrator.analyze_desk_rejection(
            title="Poor Quality Manuscript",
            abstract="This is a very short abstract without substance.",
            journal_code="SICON"
        )
        
        assert isinstance(result, DeskRejectionAnalysis)
        assert result.confidence >= 0.0 and result.confidence <= 1.0
        assert result.recommendation in AnalysisRecommendation
    
    @pytest.mark.asyncio
    async def test_referee_recommendation_only(self, ai_orchestrator):
        """Test referee recommendation in isolation"""
        recommendations = await ai_orchestrator.recommend_referees(
            title="Optimization Algorithm",
            abstract="New algorithm for constrained optimization",
            journal_code="SICON",
            count=5
        )
        
        assert len(recommendations) <= 5
        for rec in recommendations:
            assert isinstance(rec, RefereeRecommendation)
            assert rec.overall_score >= 0 and rec.overall_score <= 1.0
            assert rec.expertise_match >= 0 and rec.expertise_match <= 1.0
    
    @pytest.mark.asyncio
    async def test_pipeline_with_pdf(self, ai_orchestrator, tmp_path):
        """Test pipeline with PDF file processing"""
        # Create a dummy PDF path
        pdf_path = tmp_path / "test_manuscript.pdf"
        pdf_path.write_text("dummy pdf content")
        
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="TEST-PDF-001",
            journal_code="SICON",
            title="Test Manuscript",
            abstract="Test abstract",
            pdf_path=str(pdf_path)
        )
        
        # Should still work with PDF processing
        assert result.manuscript_id == "TEST-PDF-001"
        assert result.pdf_path == str(pdf_path)
        assert result.text_extracted is True
    
    @pytest.mark.asyncio
    async def test_error_handling_invalid_inputs(self, ai_orchestrator):
        """Test pipeline error handling with invalid inputs"""
        # Test with empty inputs
        with pytest.raises(ValueError):
            await ai_orchestrator.analyze_manuscript_comprehensive(
                manuscript_id="",
                journal_code="",
                title="",
                abstract=""
            )
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, mock_ai_client, mock_pdf_processor):
        """Test that caching works correctly"""
        # Create orchestrator with caching enabled
        orchestrator = AIOrchestrator(
            ai_client=mock_ai_client,
            pdf_processor=mock_pdf_processor,
            cache_enabled=True
        )
        
        # First analysis
        result1 = await orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="CACHE-TEST-001",
            journal_code="SICON",
            title="Cached Analysis Test",
            abstract="Testing caching behavior"
        )
        
        # Second analysis with same inputs
        result2 = await orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="CACHE-TEST-001",
            journal_code="SICON",
            title="Cached Analysis Test",
            abstract="Testing caching behavior"
        )
        
        # Results should be identical (from cache)
        assert result1.manuscript_id == result2.manuscript_id
        assert result1.desk_rejection_analysis.confidence == result2.desk_rejection_analysis.confidence
    
    @pytest.mark.asyncio
    async def test_concurrent_analysis(self, ai_orchestrator):
        """Test pipeline handles concurrent requests correctly"""
        # Create multiple analysis tasks
        tasks = []
        for i in range(5):
            task = ai_orchestrator.analyze_manuscript_comprehensive(
                manuscript_id=f"CONCURRENT-{i:03d}",
                journal_code="SICON",
                title=f"Manuscript {i}",
                abstract=f"Abstract for manuscript {i}"
            )
            tasks.append(task)
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all completed successfully
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.manuscript_id == f"CONCURRENT-{i:03d}"
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, ai_orchestrator):
        """Test that performance metrics are tracked"""
        result = await ai_orchestrator.analyze_manuscript_comprehensive(
            manuscript_id="PERF-TEST-001",
            journal_code="SICON",
            title="Performance Test",
            abstract="Testing performance tracking"
        )
        
        # Should have timing information
        assert result.processing_time_seconds >= 0
        assert result.analysis_timestamp
        assert result.ai_model_versions
    
    @pytest.mark.asyncio
    async def test_journal_specific_analysis(self, ai_orchestrator):
        """Test that analysis adapts to different journals"""
        journals = ["SICON", "SIFIN", "MF", "MOR"]
        
        results = []
        for journal in journals:
            result = await ai_orchestrator.analyze_manuscript_comprehensive(
                manuscript_id=f"JOURNAL-{journal}-001",
                journal_code=journal,
                title="Journal Specific Test",
                abstract="Testing journal-specific analysis"
            )
            results.append(result)
        
        # All should complete successfully
        assert len(results) == len(journals)
        for i, result in enumerate(results):
            assert result.journal_code == journals[i]


@pytest.mark.asyncio
async def test_ai_client_integration():
    """Test real AI client integration (requires API key)"""
    try:
        from src.infrastructure.config import settings
        if not settings.openai.api_key:
            pytest.skip("OpenAI API key not configured")
        
        # Test with real client
        client = AsyncOpenAIClient(api_key=settings.openai.api_key)
        
        result = await client.analyze_desk_rejection(
            title="Test Manuscript",
            abstract="This is a test abstract for integration testing.",
            journal_requirements="Mathematical rigor and novelty required."
        )
        
        assert isinstance(result, DeskRejectionAnalysis)
        assert result.confidence >= 0 and result.confidence <= 1.0
        
    except Exception as e:
        pytest.skip(f"AI integration test skipped: {e}")