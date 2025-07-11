"""
Unit tests for referee database
"""
import pytest
from datetime import datetime, timedelta
import json
import sqlite3

from database import (
    RefereeDatabase,
    RefereeProfile,
    ReviewRecord,
    get_db
)

class TestRefereeProfile:
    """Test RefereeProfile dataclass"""
    
    def test_default_values(self):
        """Test default values are set correctly"""
        profile = RefereeProfile(
            name="John Doe",
            email="john@university.edu"
        )
        
        assert profile.name == "John Doe"
        assert profile.email == "john@university.edu"
        assert profile.institution == ""
        assert profile.expertise == []
        assert profile.relationship == "standard"
        assert profile.notes == ""
        assert profile.h_index is None
        assert profile.last_contact is None
        assert isinstance(profile.created_at, datetime)
    
    def test_custom_values(self):
        """Test custom values"""
        expertise = ["machine learning", "optimization"]
        last_contact = datetime.now()
        
        profile = RefereeProfile(
            name="Jane Smith",
            email="jane@college.edu",
            institution="Top College",
            expertise=expertise,
            relationship="friend",
            notes="Very reliable",
            h_index=25,
            last_contact=last_contact
        )
        
        assert profile.institution == "Top College"
        assert profile.expertise == expertise
        assert profile.relationship == "friend"
        assert profile.notes == "Very reliable"
        assert profile.h_index == 25
        assert profile.last_contact == last_contact

class TestReviewRecord:
    """Test ReviewRecord dataclass"""
    
    def test_review_record_creation(self):
        """Test creating a review record"""
        invited = datetime.now()
        
        record = ReviewRecord(
            referee_email="referee@test.com",
            manuscript_id="TEST-2024-001",
            journal="SICON",
            invited_date=invited
        )
        
        assert record.referee_email == "referee@test.com"
        assert record.manuscript_id == "TEST-2024-001"
        assert record.journal == "SICON"
        assert record.invited_date == invited
        assert record.responded_date is None
        assert record.decision is None
        assert record.review_submitted_date is None
        assert record.report_quality_score is None
        assert record.days_late == 0
        assert record.reminder_count == 0

class TestRefereeDatabase:
    """Test referee database operations"""
    
    def test_database_initialization(self, temp_db_path):
        """Test database is initialized with correct schema"""
        db = RefereeDatabase(temp_db_path)
        
        # Check tables exist
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            
            expected_tables = {
                'referees', 'review_history', 'referee_metrics', 
                'referee_expertise', 'sqlite_sequence'
            }
            assert expected_tables.issubset(tables)
    
    def test_add_new_referee(self, temp_db_path):
        """Test adding a new referee"""
        db = RefereeDatabase(temp_db_path)
        
        profile = RefereeProfile(
            name="Test Referee",
            email="test@university.edu",
            institution="Test University",
            expertise=["mathematics", "statistics"],
            relationship="colleague"
        )
        
        referee_id = db.add_or_update_referee(profile)
        
        assert referee_id > 0
        
        # Verify in database
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM referees WHERE id = ?", (referee_id,))
            row = cursor.fetchone()
            
            assert row[1] == "Test Referee"  # name
            assert row[2] == "test@university.edu"  # email
            assert row[3] == "Test University"  # institution
            assert json.loads(row[4]) == ["mathematics", "statistics"]  # expertise
            assert row[5] == "colleague"  # relationship
    
    def test_update_existing_referee(self, temp_db_path):
        """Test updating an existing referee"""
        db = RefereeDatabase(temp_db_path)
        
        # Add initial referee
        profile1 = RefereeProfile(
            name="Initial Name",
            email="test@university.edu",
            institution="Old University"
        )
        referee_id1 = db.add_or_update_referee(profile1)
        
        # Update referee
        profile2 = RefereeProfile(
            name="Updated Name",
            email="test@university.edu",  # Same email
            institution="New University",
            h_index=30
        )
        referee_id2 = db.add_or_update_referee(profile2)
        
        assert referee_id1 == referee_id2  # Should be same ID
        
        # Verify update
        stats = db.get_referee_stats("test@university.edu")
        assert stats['profile']['name'] == "Updated Name"
        assert stats['profile']['institution'] == "New University"
        assert stats['profile']['h_index'] == 30
    
    def test_record_review(self, temp_db_path):
        """Test recording a review"""
        db = RefereeDatabase(temp_db_path)
        
        invited = datetime.now() - timedelta(days=5)
        responded = invited + timedelta(days=2)
        
        record = ReviewRecord(
            referee_email="reviewer@test.com",
            manuscript_id="SICON-2024-001",
            journal="SICON",
            invited_date=invited,
            responded_date=responded,
            decision="accepted"
        )
        
        review_id = db.record_review(record)
        assert review_id > 0
        
        # Check calculated fields
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT days_to_respond FROM review_history WHERE id = ?", (review_id,))
            days_to_respond = cursor.fetchone()[0]
            assert days_to_respond == 2
    
    def test_referee_stats(self, temp_db_path):
        """Test getting referee statistics"""
        db = RefereeDatabase(temp_db_path)
        
        # Add referee
        profile = RefereeProfile(
            name="Stats Referee",
            email="stats@test.com"
        )
        db.add_or_update_referee(profile)
        
        # Add multiple reviews
        base_date = datetime.now() - timedelta(days=100)
        
        for i in range(5):
            record = ReviewRecord(
                referee_email="stats@test.com",
                manuscript_id=f"TEST-2024-{i:03d}",
                journal="TEST",
                invited_date=base_date + timedelta(days=i*10),
                responded_date=base_date + timedelta(days=i*10 + 2),
                decision="accepted" if i < 4 else "declined",
                review_submitted_date=base_date + timedelta(days=i*10 + 20) if i < 3 else None,
                report_quality_score=8.5 if i < 3 else None,
                days_late=0 if i < 2 else 5
            )
            db.record_review(record)
        
        # Get stats
        stats = db.get_referee_stats("stats@test.com")
        
        assert stats is not None
        assert stats['profile']['email'] == "stats@test.com"
        assert len(stats['recent_reviews']) == 5
        
        metrics = stats['metrics']
        assert metrics['total_invitations'] == 5
        assert metrics['total_accepted'] == 4
        assert metrics['total_declined'] == 1
        assert metrics['total_completed'] == 3
        assert metrics['acceptance_rate'] == 0.8  # 4/5
        assert metrics['avg_response_time_days'] == 2.0
    
    def test_find_referees_by_expertise(self, temp_db_path):
        """Test finding referees by expertise"""
        db = RefereeDatabase(temp_db_path)
        
        # Add referees with different expertise
        referees = [
            RefereeProfile(
                name="ML Expert",
                email="ml@test.com",
                expertise=["machine learning", "deep learning", "AI"]
            ),
            RefereeProfile(
                name="Stats Expert",
                email="stats@test.com",
                expertise=["statistics", "probability", "bayesian"]
            ),
            RefereeProfile(
                name="Optimization Expert",
                email="opt@test.com",
                expertise=["optimization", "linear programming", "convex"]
            ),
            RefereeProfile(
                name="Multi Expert",
                email="multi@test.com",
                expertise=["machine learning", "optimization", "statistics"]
            )
        ]
        
        for ref in referees:
            db.add_or_update_referee(ref)
        
        # Search for ML experts
        ml_experts = db.find_referees_by_expertise(
            ["machine learning", "deep learning"],
            min_score=0.3
        )
        
        assert len(ml_experts) == 2
        emails = {expert['email'] for expert in ml_experts}
        assert emails == {"ml@test.com", "multi@test.com"}
        
        # Search with exclusion
        other_ml_experts = db.find_referees_by_expertise(
            ["machine learning"],
            exclude_emails=["ml@test.com"],
            min_score=0.3
        )
        
        assert len(other_ml_experts) == 1
        assert other_ml_experts[0]['email'] == "multi@test.com"
    
    def test_referee_workload(self, temp_db_path):
        """Test checking referee workload"""
        db = RefereeDatabase(temp_db_path)
        
        # Add referee
        db.add_or_update_referee(RefereeProfile(
            name="Busy Referee",
            email="busy@test.com"
        ))
        
        # Add recent reviews
        now = datetime.now()
        
        # Active review (invited, not completed)
        db.record_review(ReviewRecord(
            referee_email="busy@test.com",
            manuscript_id="ACTIVE-001",
            journal="TEST",
            invited_date=now - timedelta(days=10),
            responded_date=now - timedelta(days=8),
            decision="accepted"
        ))
        
        # Completed review
        db.record_review(ReviewRecord(
            referee_email="busy@test.com",
            manuscript_id="COMPLETE-001",
            journal="TEST",
            invited_date=now - timedelta(days=50),
            responded_date=now - timedelta(days=48),
            decision="accepted",
            review_submitted_date=now - timedelta(days=30)
        ))
        
        # Old review (outside window)
        db.record_review(ReviewRecord(
            referee_email="busy@test.com",
            manuscript_id="OLD-001",
            journal="TEST",
            invited_date=now - timedelta(days=200),
            responded_date=now - timedelta(days=198),
            decision="accepted",
            review_submitted_date=now - timedelta(days=180)
        ))
        
        workload = db.get_referee_workload("busy@test.com", months_back=6)
        
        assert workload['active_reviews'] == 1
        assert workload['completed_recently'] == 1
        assert workload['total_recent'] == 2
    
    def test_mark_as_friend(self, temp_db_path):
        """Test marking referee as friend"""
        db = RefereeDatabase(temp_db_path)
        
        # Add referee
        db.add_or_update_referee(RefereeProfile(
            name="Future Friend",
            email="friend@test.com"
        ))
        
        # Initially not a friend
        stats = db.get_referee_stats("friend@test.com")
        assert stats['profile']['relationship'] == "standard"
        
        # Mark as friend
        success = db.mark_as_friend("friend@test.com")
        assert success
        
        # Verify changed
        stats = db.get_referee_stats("friend@test.com")
        assert stats['profile']['relationship'] == "friend"
        
        # Non-existent referee
        success = db.mark_as_friend("nonexistent@test.com")
        assert not success
    
    def test_expertise_tracking(self, temp_db_path):
        """Test expertise confidence updates"""
        db = RefereeDatabase(temp_db_path)
        
        # Add referee with initial expertise
        profile = RefereeProfile(
            name="Expert",
            email="expert@test.com",
            expertise=["topic1", "topic2"]
        )
        referee_id = db.add_or_update_referee(profile)
        
        # Check initial confidence
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT expertise_area, confidence_score, evidence_count "
                "FROM referee_expertise WHERE referee_id = ?",
                (referee_id,)
            )
            initial_expertise = {row[0]: (row[1], row[2]) for row in cursor.fetchall()}
        
        assert initial_expertise['topic1'][0] == 0.5  # Initial confidence
        assert initial_expertise['topic1'][1] == 1     # Evidence count
        
        # Update with same expertise (should increase confidence)
        profile.expertise = ["topic1", "topic3"]  # topic1 repeated, topic3 new
        db.add_or_update_referee(profile)
        
        # Check updated confidence
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT expertise_area, confidence_score, evidence_count "
                "FROM referee_expertise WHERE referee_id = ? AND expertise_area = 'topic1'",
                (referee_id,)
            )
            row = cursor.fetchone()
        
        # Confidence should increase: 0.5 * 0.9 + 0.1 = 0.55
        assert row[1] == pytest.approx(0.55, rel=1e-3)
        assert row[2] == 2  # Evidence count increased
    
    def test_metrics_calculation(self, temp_db_path):
        """Test referee metrics calculation accuracy"""
        db = RefereeDatabase(temp_db_path)
        
        # Add referee
        db.add_or_update_referee(RefereeProfile(
            name="Metrics Test",
            email="metrics@test.com"
        ))
        
        # Add specific reviews to test calculations
        base_date = datetime.now() - timedelta(days=60)
        
        # Review 1: Accepted, completed on time
        db.record_review(ReviewRecord(
            referee_email="metrics@test.com",
            manuscript_id="M001",
            journal="TEST",
            invited_date=base_date,
            responded_date=base_date + timedelta(days=3),
            decision="accepted",
            review_submitted_date=base_date + timedelta(days=20),
            report_quality_score=9.0,
            days_late=0
        ))
        
        # Review 2: Accepted, completed late
        db.record_review(ReviewRecord(
            referee_email="metrics@test.com",
            manuscript_id="M002",
            journal="TEST",
            invited_date=base_date + timedelta(days=10),
            responded_date=base_date + timedelta(days=11),
            decision="accepted",
            review_submitted_date=base_date + timedelta(days=35),
            report_quality_score=7.5,
            days_late=5
        ))
        
        # Review 3: Declined
        db.record_review(ReviewRecord(
            referee_email="metrics@test.com",
            manuscript_id="M003",
            journal="TEST",
            invited_date=base_date + timedelta(days=20),
            responded_date=base_date + timedelta(days=22),
            decision="declined"
        ))
        
        stats = db.get_referee_stats("metrics@test.com")
        metrics = stats['metrics']
        
        # Verify calculations
        assert metrics['total_invitations'] == 3
        assert metrics['total_accepted'] == 2
        assert metrics['total_declined'] == 1
        assert metrics['total_completed'] == 2
        assert metrics['acceptance_rate'] == pytest.approx(2/3, rel=1e-3)
        assert metrics['completion_rate'] == 1.0  # 2/2 accepted were completed
        assert metrics['avg_response_time_days'] == 2.0  # (3+1+2)/3
        assert metrics['avg_review_time_days'] == pytest.approx((17+24)/2, rel=1e-3)
        assert metrics['avg_quality_score'] == pytest.approx((9.0+7.5)/2, rel=1e-3)
        assert metrics['on_time_rate'] == 0.5  # 1 on time out of 2 completed