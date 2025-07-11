#!/usr/bin/env python3
"""
Test database integration functionality
"""

import sys
import os
from datetime import datetime, timedelta
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import get_db, ReviewRecord

def test_database():
    """Test database functionality"""
    print("Testing database integration...")
    
    try:
        # Test database initialization
        db = get_db()
        print(f"✅ Database initialized: {type(db).__name__}")
        
        # Test creating a review record
        test_record = ReviewRecord(
            referee_email="test@example.com",
            manuscript_id="TEST-001",
            journal="TEST",
            invited_date=datetime.now(),
            responded_date=datetime.now() + timedelta(days=1),
            decision="accepted"
        )
        
        # Test recording review
        db.record_review(test_record)
        print(f"✅ Review record created and stored")
        
        # Test retrieving referee stats
        stats = db.get_referee_stats("test@example.com")
        print(f"✅ Referee stats retrieved: {stats}")
        
        # Test getting referee workload
        workload = db.get_referee_workload("test@example.com")
        print(f"✅ Referee workload retrieved: {workload}")
        
        # Test expertise search
        expertise_results = db.find_referees_by_expertise(["finance", "optimization"])
        print(f"✅ Expertise search: {len(expertise_results)} referees found")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_database()
    if success:
        print("\n✅ Database tests completed")
    else:
        print("\n❌ Database tests failed")
        sys.exit(1)