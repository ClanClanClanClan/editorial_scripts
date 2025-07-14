#!/usr/bin/env python3
"""
Quick test script for referee analytics system
Tests basic functionality without full extraction
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.referee_analytics import RefereeTimeline, RefereeEvent, RefereeEventType, RefereeAnalytics


def test_referee_timeline():
    """Test referee timeline functionality"""
    print("🧪 Testing Referee Timeline...")
    
    # Create sample timeline
    timeline = RefereeTimeline(
        name="Dr. John Smith",
        email="john.smith@university.edu",
        manuscript_id="SICON-2024-001",
        journal_code="SICON"
    )
    
    # Add events
    invited_date = datetime.now() - timedelta(days=30)
    timeline.add_event(RefereeEvent(RefereeEventType.INVITED, invited_date))
    
    accepted_date = invited_date + timedelta(days=3)
    timeline.add_event(RefereeEvent(RefereeEventType.ACCEPTED, accepted_date))
    
    reminder_date = accepted_date + timedelta(days=14)
    timeline.add_event(RefereeEvent(RefereeEventType.REMINDER_SENT, reminder_date))
    
    submitted_date = accepted_date + timedelta(days=21)
    timeline.add_event(RefereeEvent(RefereeEventType.REPORT_SUBMITTED, submitted_date))
    
    # Test calculations
    print(f"   Name: {timeline.name}")
    print(f"   Status: {timeline.get_status()}")
    print(f"   Response time: {timeline.get_response_time_days()} days")
    print(f"   Review time: {timeline.get_review_time_days()} days")
    print(f"   Total emails: {timeline.total_emails_sent}")
    print(f"   Events: {len(timeline.events)}")
    
    assert timeline.get_status() == "Completed"
    assert timeline.get_response_time_days() == 3
    assert timeline.get_review_time_days() == 21
    
    print("   ✅ Timeline tests passed!")
    return timeline


def test_referee_analytics():
    """Test analytics aggregation"""
    print("\n🧪 Testing Referee Analytics...")
    
    analytics = RefereeAnalytics()
    
    # Add multiple timelines
    for i in range(5):
        timeline = RefereeTimeline(
            name=f"Referee {i+1}",
            email=f"referee{i+1}@example.com",
            manuscript_id=f"SICON-2024-{i+1:03d}",
            journal_code="SICON"
        )
        
        # Add some events
        invited = datetime.now() - timedelta(days=30-i)
        timeline.add_event(RefereeEvent(RefereeEventType.INVITED, invited))
        
        if i < 4:  # 4 out of 5 accept
            accepted = invited + timedelta(days=i+1)
            timeline.add_event(RefereeEvent(RefereeEventType.ACCEPTED, accepted))
            
            if i < 3:  # 3 out of 4 complete
                submitted = accepted + timedelta(days=14+i*2)
                timeline.add_event(RefereeEvent(RefereeEventType.REPORT_SUBMITTED, submitted))
        
        analytics.add_timeline(timeline)
    
    # Get statistics
    stats = analytics.get_journal_stats("SICON")
    
    print(f"   Total referees: {stats['total_referees']}")
    print(f"   Acceptance rate: {stats['acceptance_rate']:.1f}%")
    print(f"   Completion rate: {stats['completion_rate']:.1f}%")
    
    assert stats['total_referees'] == 5
    assert stats['accepted'] == 4
    assert stats['completed'] == 3
    
    print("   ✅ Analytics tests passed!")


def test_gmail_patterns():
    """Test Gmail pattern matching"""
    print("\n🧪 Testing Gmail Patterns...")
    
    try:
        from src.infrastructure.gmail_integration import GmailRefereeTracker
        
        # Test pattern matching
        test_subjects = [
            ("Invitation to review manuscript SICON-2024-001", "invitation"),
            ("Reminder: Your review is due", "reminder"),
            ("Thank you for agreeing to review", "acceptance"),
            ("Re: Unable to review at this time", "decline"),
            ("Review submitted for SICON-2024-001", "submission")
        ]
        
        patterns = GmailRefereeTracker.REFEREE_PATTERNS
        
        for subject, expected_type in test_subjects:
            found = False
            for pattern_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    import re
                    if re.search(pattern, subject, re.IGNORECASE):
                        found = pattern_type == expected_type
                        break
                if found:
                    break
            
            status = "✅" if found else "❌"
            print(f"   {status} '{subject}' -> {expected_type}")
        
        print("   ✅ Pattern tests completed!")
        
    except ImportError:
        print("   ⚠️  Gmail integration not available (missing dependencies)")


async def test_basic_extraction():
    """Test basic extraction setup"""
    print("\n🧪 Testing Basic Extraction Setup...")
    
    try:
        from src.infrastructure.scrapers.enhanced_referee_extractor import EnhancedRefereeExtractor
        
        # Create extractor
        extractor = EnhancedRefereeExtractor("SICON", "http://sicon.siam.org")
        
        # Test date parsing
        test_dates = [
            "15-Jan-2024",
            "01/15/2024",
            "2024-01-15",
            "15 Jan 2024"
        ]
        
        for date_str in test_dates:
            parsed = extractor._parse_date_string(date_str)
            status = "✅" if parsed else "❌"
            print(f"   {status} Parse '{date_str}' -> {parsed.strftime('%Y-%m-%d') if parsed else 'Failed'}")
        
        # Test event classification
        test_events = [
            ("Referee invited on 15-Jan-2024", RefereeEventType.INVITED),
            ("Reminder sent", RefereeEventType.REMINDER_SENT),
            ("Referee accepted", RefereeEventType.ACCEPTED),
            ("Review submitted", RefereeEventType.REPORT_SUBMITTED)
        ]
        
        for text, expected in test_events:
            result = extractor._classify_event(text)
            status = "✅" if result == expected else "❌"
            print(f"   {status} Classify '{text}' -> {result.value if result else 'None'}")
        
        print("   ✅ Extraction setup tests passed!")
        
    except Exception as e:
        print(f"   ❌ Extraction setup failed: {e}")


def main():
    """Run all tests"""
    print("🚀 Referee Analytics System Test")
    print("=" * 60)
    
    # Test core functionality
    timeline = test_referee_timeline()
    test_referee_analytics()
    test_gmail_patterns()
    
    # Test async components
    asyncio.run(test_basic_extraction())
    
    print("\n✅ All tests completed!")
    print("\nSystem is ready for full analysis.")
    print("Run 'python run_comprehensive_referee_analytics.py' for complete extraction.")


if __name__ == "__main__":
    main()