"""
Real database tests with actual SQLite

Tests database operations with real data persistence
"""
import pytest
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from tests.real import TEST_CONFIG, real_test

if TEST_CONFIG['RUN_REAL_TESTS']:
    from database import RefereeDatabase, RefereeProfile, ReviewRecord

@real_test
class TestDatabaseReal:
    """Test real database operations"""
    
    @pytest.fixture
    def real_db(self):
        """Create a real test database"""
        db_path = TEST_CONFIG['TEST_DB_PATH']
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create database
        db = RefereeDatabase(db_path)
        
        yield db
        
        # Cleanup after tests (optional - might want to keep for inspection)
        # os.remove(db_path)
    
    def test_database_creation_real(self, real_db):
        """Test real database file creation and schema"""
        # Check file exists
        assert os.path.exists(real_db.db_path)
        
        # Check file size (should have tables)
        size = os.path.getsize(real_db.db_path)
        assert size > 0
        
        print(f"\n✓ Database created at: {real_db.db_path}")
        print(f"  Size: {size:,} bytes")
        
        # Verify schema
        with sqlite3.connect(real_db.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['referees', 'review_history', 'referee_metrics', 'referee_expertise']
            for table in expected_tables:
                assert table in tables
            
            print(f"  Tables: {', '.join(tables)}")
            
            # Check indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            print(f"  Indexes: {len(indexes)}")
    
    def test_referee_operations_real(self, real_db):
        """Test real referee CRUD operations"""
        # Create referee
        profile = RefereeProfile(
            name="Dr. Test Referee",
            email="test.referee@realuniversity.edu",
            institution="Real University",
            expertise=["optimization", "machine learning", "control theory"],
            relationship="colleague",
            notes="Excellent reviewer, very thorough",
            h_index=25
        )
        
        referee_id = real_db.add_or_update_referee(profile)
        assert referee_id > 0
        print(f"\n✓ Created referee with ID: {referee_id}")
        
        # Retrieve and verify
        stats = real_db.get_referee_stats("test.referee@realuniversity.edu")
        assert stats is not None
        assert stats['profile']['name'] == "Dr. Test Referee"
        assert stats['profile']['institution'] == "Real University"
        assert len(json.loads(stats['profile']['expertise'])) == 3
        
        # Update referee
        profile.h_index = 30
        profile.notes = "Updated notes - still excellent"
        referee_id2 = real_db.add_or_update_referee(profile)
        
        assert referee_id2 == referee_id  # Same ID
        
        # Verify update
        stats2 = real_db.get_referee_stats("test.referee@realuniversity.edu")
        assert stats2['profile']['h_index'] == 30
        assert "Updated notes" in stats2['profile']['notes']
        
        print("✓ Referee update successful")
    
    def test_review_history_real(self, real_db):
        """Test real review history tracking"""
        # First add a referee
        referee_email = "reviewer@realtest.edu"
        real_db.add_or_update_referee(RefereeProfile(
            name="Review Tester",
            email=referee_email
        ))
        
        # Add multiple reviews with realistic data
        reviews = []
        base_date = datetime.now() - timedelta(days=180)
        
        # Review 1: Completed on time
        review1 = ReviewRecord(
            referee_email=referee_email,
            manuscript_id="REAL-2024-001",
            journal="TEST",
            invited_date=base_date,
            responded_date=base_date + timedelta(days=3),
            decision="accepted",
            review_submitted_date=base_date + timedelta(days=21),
            report_quality_score=8.5,
            days_late=0,
            reminder_count=0
        )
        real_db.record_review(review1)
        
        # Review 2: Completed late
        review2 = ReviewRecord(
            referee_email=referee_email,
            manuscript_id="REAL-2024-002",
            journal="TEST",
            invited_date=base_date + timedelta(days=60),
            responded_date=base_date + timedelta(days=62),
            decision="accepted",
            review_submitted_date=base_date + timedelta(days=95),
            report_quality_score=7.0,
            days_late=5,
            reminder_count=2
        )
        real_db.record_review(review2)
        
        # Review 3: Declined
        review3 = ReviewRecord(
            referee_email=referee_email,
            manuscript_id="REAL-2024-003",
            journal="TEST",
            invited_date=base_date + timedelta(days=120),
            responded_date=base_date + timedelta(days=121),
            decision="declined"
        )
        real_db.record_review(review3)
        
        # Review 4: Currently active
        review4 = ReviewRecord(
            referee_email=referee_email,
            manuscript_id="REAL-2024-004",
            journal="TEST",
            invited_date=datetime.now() - timedelta(days=10),
            responded_date=datetime.now() - timedelta(days=8),
            decision="accepted"
        )
        real_db.record_review(review4)
        
        print(f"\n✓ Added {4} review records")
        
        # Check metrics calculation
        stats = real_db.get_referee_stats(referee_email)
        metrics = stats['metrics']
        
        print(f"\nReferee Metrics:")
        print(f"  Total invitations: {metrics['total_invitations']}")
        print(f"  Acceptance rate: {metrics['acceptance_rate']:.1%}")
        print(f"  Completion rate: {metrics['completion_rate']:.1%}")
        print(f"  Avg response time: {metrics['avg_response_time_days']:.1f} days")
        print(f"  Avg review time: {metrics['avg_review_time_days']:.1f} days")
        print(f"  On-time rate: {metrics['on_time_rate']:.1%}")
        
        assert metrics['total_invitations'] == 4
        assert metrics['total_accepted'] == 3
        assert metrics['total_declined'] == 1
        assert metrics['total_completed'] == 2
    
    def test_expertise_tracking_real(self, real_db):
        """Test real expertise tracking and updates"""
        referee_email = "expert@realtest.edu"
        
        # Initial expertise
        profile = RefereeProfile(
            name="Domain Expert",
            email=referee_email,
            expertise=["deep learning", "optimization", "NLP"]
        )
        real_db.add_or_update_referee(profile)
        
        # Check initial expertise
        with sqlite3.connect(real_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT expertise_area, confidence_score, evidence_count
                FROM referee_expertise
                WHERE referee_id = (SELECT id FROM referees WHERE email = ?)
                ORDER BY expertise_area
            """, (referee_email,))
            
            initial = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
            
        print(f"\n✓ Initial expertise recorded:")
        for area, (conf, count) in initial.items():
            print(f"  {area}: confidence={conf:.2f}, evidence={count}")
        
        # Update with overlapping expertise
        profile.expertise = ["deep learning", "computer vision", "optimization"]
        real_db.add_or_update_referee(profile)
        
        # Check updated expertise
        with sqlite3.connect(real_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT expertise_area, confidence_score, evidence_count
                FROM referee_expertise
                WHERE referee_id = (SELECT id FROM referees WHERE email = ?)
                ORDER BY expertise_area
            """, (referee_email,))
            
            updated = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        
        print(f"\n✓ Updated expertise:")
        for area, (conf, count) in updated.items():
            print(f"  {area}: confidence={conf:.2f}, evidence={count}")
        
        # Verify confidence increased for repeated areas
        assert updated['deep learning'][0] > initial['deep learning'][0]
        assert updated['optimization'][0] > initial['optimization'][0]
        assert updated['deep learning'][1] == 2  # Evidence count increased
    
    def test_workload_tracking_real(self, real_db):
        """Test real workload tracking"""
        referee_email = "busy@realtest.edu"
        real_db.add_or_update_referee(RefereeProfile(
            name="Busy Referee",
            email=referee_email
        ))
        
        # Add current workload
        now = datetime.now()
        
        # Active reviews
        for i in range(3):
            real_db.record_review(ReviewRecord(
                referee_email=referee_email,
                manuscript_id=f"ACTIVE-{i:03d}",
                journal="TEST",
                invited_date=now - timedelta(days=20-i*5),
                responded_date=now - timedelta(days=18-i*5),
                decision="accepted"
            ))
        
        # Completed reviews
        for i in range(2):
            real_db.record_review(ReviewRecord(
                referee_email=referee_email,
                manuscript_id=f"COMPLETE-{i:03d}",
                journal="TEST",
                invited_date=now - timedelta(days=60+i*20),
                responded_date=now - timedelta(days=58+i*20),
                decision="accepted",
                review_submitted_date=now - timedelta(days=40+i*20)
            ))
        
        workload = real_db.get_referee_workload(referee_email)
        
        print(f"\n✓ Referee Workload:")
        print(f"  Active reviews: {workload['active_reviews']}")
        print(f"  Recently completed: {workload['completed_recently']}")
        print(f"  Total recent load: {workload['total_recent']}")
        
        assert workload['active_reviews'] == 3
        assert workload['completed_recently'] == 2
    
    def test_performance_queries_real(self, real_db):
        """Test database performance with realistic data volume"""
        import time
        
        # Add multiple referees
        print("\n✓ Testing database performance...")
        
        start = time.time()
        for i in range(50):
            real_db.add_or_update_referee(RefereeProfile(
                name=f"Referee {i:03d}",
                email=f"referee{i:03d}@test.edu",
                expertise=["area1", "area2", "area3"]
            ))
        
        referee_time = time.time() - start
        print(f"  Added 50 referees in {referee_time:.2f}s")
        
        # Add reviews
        start = time.time()
        for i in range(200):
            real_db.record_review(ReviewRecord(
                referee_email=f"referee{i%50:03d}@test.edu",
                manuscript_id=f"PERF-{i:04d}",
                journal="TEST",
                invited_date=datetime.now() - timedelta(days=i),
                decision="accepted" if i % 3 != 0 else "declined"
            ))
        
        review_time = time.time() - start
        print(f"  Added 200 reviews in {review_time:.2f}s")
        
        # Test query performance
        start = time.time()
        experts = real_db.find_referees_by_expertise(["area1", "area2"])
        query_time = time.time() - start
        print(f"  Expertise query returned {len(experts)} referees in {query_time:.3f}s")
        
        assert referee_time < 5.0  # Should be fast
        assert review_time < 10.0
        assert query_time < 0.5
    
    def test_export_functionality_real(self, real_db):
        """Test exporting analytics to Excel"""
        # Add some data first
        for i in range(5):
            real_db.add_or_update_referee(RefereeProfile(
                name=f"Export Test {i}",
                email=f"export{i}@test.edu"
            ))
        
        # Export
        export_path = "test_referee_analytics.xlsx"
        real_db.export_analytics(export_path)
        
        assert os.path.exists(export_path)
        
        # Verify Excel file
        referees_df = pd.read_excel(export_path, sheet_name='Referees')
        reviews_df = pd.read_excel(export_path, sheet_name='Review History')
        
        print(f"\n✓ Exported analytics to {export_path}")
        print(f"  Referees sheet: {len(referees_df)} rows")
        print(f"  Reviews sheet: {len(reviews_df)} rows")
        
        # Cleanup
        os.remove(export_path)

@real_test 
class TestDatabaseIntegrity:
    """Test database integrity and constraints"""
    
    def test_unique_constraints_real(self, real_db):
        """Test unique constraints are enforced"""
        # Add referee
        real_db.add_or_update_referee(RefereeProfile(
            name="Unique Test",
            email="unique@test.edu"
        ))
        
        # Try to add duplicate email - should update, not create new
        id1 = real_db.add_or_update_referee(RefereeProfile(
            name="Different Name",
            email="unique@test.edu"
        ))
        
        # Count referees with this email
        with sqlite3.connect(real_db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM referees WHERE email = ?", ("unique@test.edu",))
            count = cursor.fetchone()[0]
        
        assert count == 1  # Should only have one entry
        print("\n✓ Unique email constraint enforced")
    
    def test_foreign_keys_real(self, real_db):
        """Test foreign key constraints"""
        # Try to add review for non-existent referee
        # Should auto-create referee
        review = ReviewRecord(
            referee_email="auto_created@test.edu",
            manuscript_id="FK-TEST-001",
            journal="TEST",
            invited_date=datetime.now()
        )
        
        real_db.record_review(review)
        
        # Verify referee was created
        stats = real_db.get_referee_stats("auto_created@test.edu")
        assert stats is not None
        
        print("\n✓ Foreign key constraints working (auto-creates referee)")

import json