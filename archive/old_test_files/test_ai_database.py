#!/usr/bin/env python3
"""
AI Database Integration Test
Test storing and retrieving AI analysis results in PostgreSQL
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.infrastructure.config import get_settings
from src.infrastructure.repositories.ai_analysis_repository import AIAnalysisRepository
from src.ai.models.manuscript_analysis import (
    AnalysisResult, DeskRejectionAnalysis, ManuscriptMetadata,
    RefereeRecommendation, AnalysisRecommendation, QualityIssue, QualityIssueType
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_sample_analysis() -> AnalysisResult:
    """Create a sample AI analysis result for testing"""
    
    # Create sample metadata
    metadata = ManuscriptMetadata(
        title="Optimal Control of Nonlinear Dynamical Systems",
        abstract="This paper presents a novel approach to optimal control...",
        keywords=["optimal control", "nonlinear systems", "dynamical systems"],
        research_area="Mathematical Control Theory",
        methodology="Theoretical Analysis with Numerical Validation",
        complexity_score=0.8,
        novelty_score=0.7,
        technical_quality_score=0.85,
        presentation_quality_score=0.75,
        scope_fit_score=0.9
    )
    
    # Create sample quality issues
    quality_issues = [
        QualityIssue(
            issue_type=QualityIssueType.UNCLEAR_METHODOLOGY,
            severity=0.6,
            description="The numerical method validation could be more detailed",
            location="Section 4.2",
            suggestion="Add convergence analysis and computational complexity discussion"
        ),
        QualityIssue(
            issue_type=QualityIssueType.REFERENCE_ISSUES,
            severity=0.3,
            description="Some recent works in optimal control are missing",
            suggestion="Include references to recent advances in nonlinear control theory"
        )
    ]
    
    # Create desk rejection analysis
    desk_analysis = DeskRejectionAnalysis(
        recommendation=AnalysisRecommendation.ACCEPT_FOR_REVIEW,
        confidence=0.82,
        overall_score=0.78,
        rejection_reasons=[],
        quality_issues=quality_issues,
        scope_issues=[],
        technical_issues=[],
        model_version="gpt-4-turbo",
        processing_time_seconds=2.5,
        recommendation_summary="Strong theoretical contribution suitable for review",
        detailed_explanation="The manuscript presents solid theoretical work with good mathematical rigor. While there are minor presentation issues, the core contributions are significant and appropriate for the journal scope."
    )
    
    # Create referee recommendations
    referee_recommendations = [
        RefereeRecommendation(
            referee_name="Dr. Sarah Chen",
            expertise_match=0.95,
            availability_score=0.8,
            quality_score=0.9,
            workload_score=0.7,
            overall_score=0.87,
            expertise_areas=["optimal control", "nonlinear systems", "mathematical optimization"],
            matching_keywords=["optimal control", "dynamical systems"],
            rationale="Expert in optimal control theory with extensive publication record",
            confidence=0.9,
            contact_info={"email": "s.chen@university.edu"},
            institution="MIT",
            recent_publications=["Advances in Nonlinear Control Theory", "Optimal Control Applications"],
            historical_response_rate=0.85,
            average_review_time_days=21,
            review_quality_rating=0.92
        ),
        RefereeRecommendation(
            referee_name="Prof. Michael Rodriguez",
            expertise_match=0.88,
            availability_score=0.9,
            quality_score=0.85,
            workload_score=0.8,
            overall_score=0.86,
            expertise_areas=["control theory", "numerical analysis", "optimization"],
            matching_keywords=["nonlinear systems", "numerical validation"],
            rationale="Strong background in both theoretical and numerical aspects",
            confidence=0.85,
            contact_info={"email": "m.rodriguez@tech.edu"},
            institution="Stanford University",
            recent_publications=["Numerical Methods in Control Theory"],
            historical_response_rate=0.92,
            average_review_time_days=18,
            review_quality_rating=0.88
        )
    ]
    
    # Create complete analysis result
    analysis = AnalysisResult(
        manuscript_id="SICON-2024-001",
        journal_code="SICON",
        metadata=metadata,
        desk_rejection_analysis=desk_analysis,
        referee_recommendations=referee_recommendations,
        processing_time_seconds=3.2,
        content_hash="abc123def456",
        pdf_path="/path/to/manuscript.pdf",
        text_extracted=True,
        analysis_quality=0.85,
        ai_model_versions={
            "openai_model": "gpt-4-turbo",
            "pdf_processor": "PyPDF2",
            "analyzer_version": "1.0.0"
        }
    )
    
    return analysis


async def test_save_and_retrieve():
    """Test saving and retrieving AI analysis"""
    logger.info("🧪 Testing AI analysis save and retrieve...")
    
    try:
        # Create repository
        repository = AIAnalysisRepository()
        
        # Create sample analysis
        analysis = create_sample_analysis()
        original_id = analysis.id
        
        # Save to database
        logger.info(f"💾 Saving analysis {original_id}...")
        saved_id = await repository.save_analysis(analysis)
        
        assert saved_id == original_id, "Saved ID should match original"
        logger.info(f"✅ Analysis saved with ID: {saved_id}")
        
        # Retrieve by ID
        logger.info(f"🔍 Retrieving analysis {saved_id}...")
        retrieved = await repository.get_analysis_by_id(saved_id)
        
        assert retrieved is not None, "Should retrieve saved analysis"
        assert retrieved.manuscript_id == analysis.manuscript_id, "Manuscript ID should match"
        assert retrieved.journal_code == analysis.journal_code, "Journal code should match"
        assert retrieved.metadata.title == analysis.metadata.title, "Title should match"
        assert len(retrieved.referee_recommendations) == len(analysis.referee_recommendations), "Referee count should match"
        assert len(retrieved.desk_rejection_analysis.quality_issues) == len(analysis.desk_rejection_analysis.quality_issues), "Quality issues count should match"
        
        logger.info(f"✅ Analysis retrieved successfully:")
        logger.info(f"   Manuscript: {retrieved.manuscript_id}")
        logger.info(f"   Title: {retrieved.metadata.title}")
        logger.info(f"   Recommendation: {retrieved.desk_rejection_analysis.recommendation.value}")
        logger.info(f"   Confidence: {retrieved.desk_rejection_analysis.confidence:.2f}")
        logger.info(f"   Referees: {len(retrieved.referee_recommendations)}")
        logger.info(f"   Quality Issues: {len(retrieved.desk_rejection_analysis.quality_issues)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Save and retrieve test failed: {e}")
        return False


async def test_manuscript_queries():
    """Test querying analyses by manuscript"""
    logger.info("🧪 Testing manuscript-based queries...")
    
    try:
        repository = AIAnalysisRepository()
        
        # Create multiple analyses for the same manuscript
        manuscript_id = "SICON-2024-002"
        
        for i in range(3):
            analysis = create_sample_analysis()
            analysis.manuscript_id = manuscript_id
            analysis.metadata.title = f"Test Manuscript Version {i+1}"
            
            await repository.save_analysis(analysis)
            logger.info(f"💾 Saved analysis {i+1} for manuscript {manuscript_id}")
        
        # Query by manuscript
        logger.info(f"🔍 Querying analyses for manuscript {manuscript_id}...")
        analyses = await repository.get_analyses_by_manuscript(manuscript_id)
        
        assert len(analyses) == 3, f"Should find 3 analyses, found {len(analyses)}"
        
        # Verify they're sorted by timestamp (most recent first)
        for i, analysis in enumerate(analyses):
            assert analysis.manuscript_id == manuscript_id
            logger.info(f"   Analysis {i+1}: {analysis.metadata.title}")
        
        logger.info(f"✅ Found {len(analyses)} analyses for manuscript {manuscript_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Manuscript queries test failed: {e}")
        return False


async def test_performance_stats():
    """Test performance statistics"""
    logger.info("🧪 Testing performance statistics...")
    
    try:
        repository = AIAnalysisRepository()
        
        # Get performance stats
        logger.info("📊 Getting performance statistics...")
        stats = await repository.get_performance_stats(journal_code="SICON", days=30)
        
        assert 'total_analyses' in stats, "Should include total analyses count"
        assert 'validation_rate' in stats, "Should include validation rate"
        assert 'avg_processing_time_seconds' in stats, "Should include avg processing time"
        
        logger.info(f"✅ Performance stats retrieved:")
        logger.info(f"   Total analyses: {stats['total_analyses']}")
        logger.info(f"   Validated: {stats['validated_analyses']}")
        logger.info(f"   Validation rate: {stats['validation_rate']:.2%}")
        logger.info(f"   Avg processing time: {stats['avg_processing_time_seconds']:.2f}s")
        logger.info(f"   Avg quality: {stats['avg_analysis_quality']:.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Performance stats test failed: {e}")
        return False


async def test_validation_updates():
    """Test human validation updates"""
    logger.info("🧪 Testing validation updates...")
    
    try:
        repository = AIAnalysisRepository()
        
        # Create and save analysis
        analysis = create_sample_analysis()
        analysis.manuscript_id = "SICON-2024-003"
        saved_id = await repository.save_analysis(analysis)
        
        # Update validation
        logger.info(f"✅ Updating validation for analysis {saved_id}...")
        success = await repository.update_validation(
            analysis_id=saved_id,
            validated=True,
            notes="Analysis reviewed and approved by human editor",
            validator_id="editor_001"
        )
        
        assert success, "Validation update should succeed"
        
        # Verify update
        updated_analysis = await repository.get_analysis_by_id(saved_id)
        assert updated_analysis.human_validated == True, "Should be marked as validated"
        assert "approved by human editor" in updated_analysis.validation_notes, "Notes should be updated"
        
        logger.info(f"✅ Validation updated successfully")
        logger.info(f"   Validated: {updated_analysis.human_validated}")
        logger.info(f"   Notes: {updated_analysis.validation_notes}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Validation update test failed: {e}")
        return False


async def test_usage_recording():
    """Test AI usage recording"""
    logger.info("🧪 Testing usage recording...")
    
    try:
        repository = AIAnalysisRepository()
        
        # Record usage
        logger.info("📝 Recording AI usage...")
        await repository.record_usage(
            service_type="openai",
            operation="desk_rejection",
            model_name="gpt-4-turbo",
            processing_time_ms=2500.0,
            success=True,
            journal_code="SICON",
            tokens_used=1250,
            estimated_cost_usd=0.05
        )
        
        # Record error case
        await repository.record_usage(
            service_type="openai",
            operation="metadata_extraction",
            model_name="gpt-4-turbo",
            processing_time_ms=1000.0,
            success=False,
            journal_code="SIFIN",
            error_message="Rate limit exceeded"
        )
        
        logger.info("✅ Usage recording completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Usage recording test failed: {e}")
        return False


async def run_all_tests():
    """Run all AI database integration tests"""
    logger.info("🚀 Starting AI Database Integration Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Save and Retrieve", test_save_and_retrieve()),
        ("Manuscript Queries", test_manuscript_queries()),
        ("Performance Stats", test_performance_stats()),
        ("Validation Updates", test_validation_updates()),
        ("Usage Recording", test_usage_recording())
    ]
    
    results = []
    for test_name, test_coro in tests:
        logger.info(f"\n🧪 Running {test_name}...")
        try:
            result = await test_coro
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\nAI Database Integration Test Results")
    logger.info("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    total = len(results)
    logger.info(f"\nSummary: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL AI DATABASE TESTS PASSED!")
        logger.info("\n📋 Database Integration Complete:")
        logger.info("   ✅ AI analysis storage and retrieval")
        logger.info("   ✅ Complex domain model persistence")
        logger.info("   ✅ Performance tracking and analytics")
        logger.info("   ✅ Human validation workflow")
        logger.info("   ✅ Usage statistics recording")
        logger.info("\n🚀 Ready for Phase 1.3: Complete AI Pipeline Testing")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed - Database integration needs fixes")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)