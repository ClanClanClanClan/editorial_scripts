#!/usr/bin/env python3
"""
Debug the analytics functionality to see why it's returning null values
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from enhanced_referee_analytics_system import RefereeReport, EnhancedRefereeAnalytics
from pathlib import Path


async def debug_analytics():
    """Debug the analytics function"""
    
    # Create a test report
    test_report = RefereeReport(
        manuscript_id="TEST123",
        journal="TEST",
        referee_email="test@test.com",
        report_text="""This paper presents a novel approach to stochastic control theory with interesting applications. 

The methodology is sound and the mathematical framework is well-developed. The authors have provided rigorous proofs for the main theorems and the experimental validation supports their theoretical claims.

However, I have several suggestions for improvement:
1. The literature review could be more comprehensive, particularly regarding recent work by Johnson et al. (2024)
2. The computational complexity analysis needs more detail
3. Some notation could be clarified in Section 3.2

Overall, this is solid work that makes meaningful contributions to the field. I recommend acceptance with minor revisions to address the points above.""",
        recommendation="minor_revision"
    )
    
    print(f"Original report:")
    print(f"  Text length: {len(test_report.report_text)}")
    print(f"  Word count: {test_report.word_count}")
    print(f"  Recommendation: {test_report.recommendation}")
    print(f"  Quality score: {test_report.review_quality_score}")
    print(f"  Technical depth: {test_report.technical_depth}")
    print(f"  Constructiveness: {test_report.constructiveness}")
    print(f"  Topics: {test_report.key_topics}")
    
    # Create analytics instance
    debug_dir = Path("debug_test")
    debug_dir.mkdir(exist_ok=True)
    analytics = EnhancedRefereeAnalytics(debug_dir)
    
    print("\nRunning analytics...")
    await analytics._analyze_report_content(test_report)
    
    print(f"\nAfter analytics:")
    print(f"  Quality score: {test_report.review_quality_score}")
    print(f"  Technical depth: {test_report.technical_depth}")
    print(f"  Constructiveness: {test_report.constructiveness}")
    print(f"  Topics: {test_report.key_topics}")
    
    # Debug the analysis step by step
    text = test_report.report_text.lower()
    print(f"\nDebug analysis:")
    
    # Technical depth
    technical_indicators = {
        'deep': ['methodology', 'algorithm', 'proof', 'theorem', 'mathematical', 'statistical', 'experimental design'],
        'moderate': ['method', 'approach', 'analysis', 'results', 'conclusion', 'literature'],
        'shallow': ['overall', 'general', 'seems', 'appears', 'good', 'bad']
    }
    
    depth_scores = {}
    for depth, indicators in technical_indicators.items():
        score = sum(1 for indicator in indicators if indicator in text)
        depth_scores[depth] = score
        print(f"  {depth}: {score} (found: {[ind for ind in indicators if ind in text]})")
    
    print(f"  Technical depth chosen: {max(depth_scores, key=depth_scores.get)}")
    
    # Constructiveness
    constructive_words = ['suggest', 'recommend', 'improve', 'consider', 'perhaps', 'could', 'might']
    destructive_words = ['terrible', 'awful', 'completely wrong', 'useless', 'nonsense']
    
    constructive_count = sum(1 for word in constructive_words if word in text)
    destructive_count = sum(1 for word in destructive_words if word in text)
    
    print(f"  Constructive words found: {constructive_count} ({[w for w in constructive_words if w in text]})")
    print(f"  Destructive words found: {destructive_count} ({[w for w in destructive_words if w in text]})")
    
    # Quality calculation
    quality_factors = [
        min(test_report.word_count / 100, 10),
        constructive_count * 2,
        depth_scores.get('deep', 0) * 3,
        5 if test_report.recommendation else 0,
    ]
    print(f"  Quality factors: {quality_factors}")
    print(f"  Total quality: {sum(quality_factors)}")


if __name__ == "__main__":
    asyncio.run(debug_analytics())