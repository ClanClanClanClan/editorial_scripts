#!/usr/bin/env python3
"""
AI Integration Test
Test the new AI manuscript analysis system with the clean architecture
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.infrastructure.config import get_settings
from src.ai.services.pypdf_processor import PyPDFProcessor
from src.ai.services.openai_client import OpenAIClient
from src.ai.services.openai_manuscript_analyzer import OpenAIManuscriptAnalyzer
from src.ai.models.manuscript_analysis import AnalysisRecommendation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_ai_components():
    """Test individual AI components"""
    logger.info("Testing AI Components")
    logger.info("=" * 50)
    
    # Test configuration
    logger.info("🔧 Testing configuration...")
    settings = get_settings()
    
    if settings.openai_api_key:
        logger.info("✅ OpenAI API key configured")
    else:
        logger.warning("⚠️ OpenAI API key not configured - using fallback mode")
    
    # Test PDF processor
    logger.info("📄 Testing PDF processor...")
    pdf_processor = PyPDFProcessor()
    
    # Test AI client
    logger.info("🤖 Testing AI client...")
    ai_client = OpenAIClient()
    
    # Test model availability if API key is configured
    if settings.openai_api_key:
        from src.ai.ports.ai_client import AIModel
        model_available = await ai_client.check_model_availability(AIModel.GPT_4_TURBO)
        if model_available:
            logger.info("✅ GPT-4 Turbo model available")
        else:
            logger.warning("⚠️ GPT-4 Turbo model not available - may hit rate limits")
    
    # Test manuscript analyzer
    logger.info("📊 Testing manuscript analyzer...")
    analyzer = OpenAIManuscriptAnalyzer(
        pdf_processor=pdf_processor,
        ai_client=ai_client,
        cache=None  # Skip Redis cache for this test
    )
    
    logger.info("✅ All AI components initialized successfully")
    return analyzer


async def test_with_sample_data():
    """Test AI analysis with sample data (without requiring real PDF)"""
    logger.info("\nTesting AI Analysis Pipeline")
    logger.info("=" * 50)
    
    analyzer = await test_ai_components()
    ai_client = analyzer.ai_client
    
    # Test metadata extraction
    logger.info("🔍 Testing metadata extraction...")
    
    sample_title = "Optimal Control of Nonlinear Dynamical Systems with Applications to Finance"
    sample_abstract = """
    This paper presents a novel approach to optimal control of nonlinear dynamical systems 
    with applications in financial mathematics. We develop a new theoretical framework 
    combining stochastic differential equations with advanced optimization techniques.
    Our method shows significant improvements in computational efficiency and solution accuracy
    compared to existing approaches. We demonstrate the effectiveness through numerical 
    experiments on portfolio optimization and risk management problems.
    """
    sample_text = f"{sample_title}\n\n{sample_abstract}\n\n1. Introduction\nThe problem of optimal control..."
    
    try:
        # Test metadata extraction
        metadata = await ai_client.extract_research_metadata(
            title=sample_title,
            abstract=sample_abstract,
            full_text_sample=sample_text
        )
        
        logger.info(f"✅ Metadata extracted:")
        logger.info(f"   Research Area: {metadata.get('research_area', 'Unknown')}")
        logger.info(f"   Keywords: {metadata.get('keywords', [])}")
        logger.info(f"   Novelty Score: {metadata.get('novelty_score', 0.0):.2f}")
        
        # Test desk rejection analysis
        logger.info("📝 Testing desk rejection analysis...")
        
        desk_analysis = await ai_client.analyze_for_desk_rejection(
            title=sample_title,
            abstract=sample_abstract,
            full_text_sample=sample_text,
            journal_code="SICON"
        )
        
        logger.info(f"✅ Desk rejection analysis completed:")
        logger.info(f"   Recommendation: {desk_analysis.recommendation.value}")
        logger.info(f"   Confidence: {desk_analysis.confidence:.2f}")
        logger.info(f"   Overall Score: {desk_analysis.overall_score:.2f}")
        logger.info(f"   Summary: {desk_analysis.recommendation_summary}")
        
        if desk_analysis.quality_issues:
            logger.info(f"   Quality Issues: {len(desk_analysis.quality_issues)}")
            for issue in desk_analysis.quality_issues[:3]:  # Show first 3
                logger.info(f"     - {issue.issue_type.value}: {issue.description[:100]}...")
        
        # Test quality assessment
        logger.info("🎯 Testing quality assessment...")
        
        quality_scores = await ai_client.assess_quality(
            title=sample_title,
            abstract=sample_abstract,
            full_text_sample=sample_text
        )
        
        logger.info(f"✅ Quality assessment completed:")
        for metric, score in quality_scores.items():
            logger.info(f"   {metric}: {score:.2f}")
        
        # Test explanation generation
        logger.info("💬 Testing decision explanation...")
        
        explanation = await ai_client.explain_decision(desk_analysis)
        logger.info(f"✅ Explanation generated:")
        logger.info(f"   {explanation[:200]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ AI analysis failed: {e}")
        return False


async def test_error_handling():
    """Test error handling and fallback mechanisms"""
    logger.info("\nTesting Error Handling")
    logger.info("=" * 50)
    
    analyzer = await test_ai_components()
    
    # Test with empty inputs
    logger.info("🚫 Testing with empty inputs...")
    
    try:
        desk_analysis = await analyzer.ai_client.analyze_for_desk_rejection(
            title="",
            abstract="",
            full_text_sample="",
            journal_code="SICON"
        )
        
        logger.info(f"✅ Handled empty input gracefully:")
        logger.info(f"   Recommendation: {desk_analysis.recommendation.value}")
        logger.info(f"   Confidence: {desk_analysis.confidence:.2f}")
        
    except Exception as e:
        logger.error(f"❌ Error handling failed: {e}")
        return False
    
    return True


async def run_all_tests():
    """Run comprehensive AI system tests"""
    logger.info("🚀 Starting AI System Integration Tests")
    logger.info("=" * 60)
    
    tests = [
        ("Component Initialization", test_ai_components()),
        ("Sample Data Analysis", test_with_sample_data()),
        ("Error Handling", test_error_handling())
    ]
    
    results = []
    for test_name, test_coro in tests:
        logger.info(f"\n🧪 Running {test_name}...")
        try:
            result = await test_coro
            if isinstance(result, bool):
                results.append((test_name, result))
            else:
                results.append((test_name, True))  # Component test returns analyzer object
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\nAI Integration Test Results")
    logger.info("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name:<25} {status}")
        if result:
            passed += 1
    
    total = len(results)
    logger.info(f"\nSummary: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL AI TESTS PASSED - AI system is working correctly!")
        logger.info("\n📋 Next Steps:")
        logger.info("   1. Integration with manuscript extraction pipeline")
        logger.info("   2. Database storage of AI analysis results")
        logger.info("   3. Web dashboard for AI insights")
        logger.info("   4. Real PDF testing with downloaded manuscripts")
        return True
    else:
        logger.error(f"❌ {total - passed} tests failed - AI system needs fixes")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)