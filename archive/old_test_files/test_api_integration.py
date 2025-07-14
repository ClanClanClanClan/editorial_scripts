#!/usr/bin/env /usr/bin/python3
"""
API Integration Tests - Tests API with real database
"""

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.api.main import app
from src.infrastructure.database.engine import engine, Base
from src.infrastructure.config import get_settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session():
    """Create test database session"""
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Clean up tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    """Create test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestRefereeAPI:
    """Test referee API endpoints with real database"""
    
    async def test_create_referee(self, client: AsyncClient, db_session):
        """Test creating a new referee"""
        referee_data = {
            "name": "Dr. Test User",
            "email": "test@example.com",
            "institution": "Test University",
            "time_metrics": {
                "avg_response_time": 3.0,
                "avg_review_time": 21.0,
                "fastest_review": 7.0,
                "slowest_review": 35.0,
                "response_time_std": 1.0,
                "review_time_std": 5.0,
                "on_time_rate": 0.9
            },
            "quality_metrics": {
                "avg_quality_score": 8.0,
                "quality_consistency": 0.85,
                "report_thoroughness": 0.9,
                "constructiveness_score": 8.5,
                "technical_accuracy": 8.2,
                "clarity_score": 8.0,
                "actionability_score": 7.8
            },
            "workload_metrics": {
                "current_reviews": 2,
                "completed_reviews_30d": 3,
                "completed_reviews_90d": 8,
                "completed_reviews_365d": 30,
                "monthly_average": 2.5,
                "peak_capacity": 5,
                "availability_score": 0.6,
                "burnout_risk_score": 0.3
            },
            "reliability_metrics": {
                "acceptance_rate": 0.8,
                "completion_rate": 0.95,
                "ghost_rate": 0.05,
                "decline_after_accept_rate": 0.02,
                "reminder_effectiveness": 0.9,
                "communication_score": 0.85,
                "excuse_frequency": 0.1
            },
            "expertise_metrics": {
                "expertise_areas": ["machine learning", "optimization"],
                "h_index": 30,
                "recent_publications": 10,
                "citation_count": 1500,
                "years_experience": 12
            }
        }
        
        response = await client.post("/api/v1/referees/", json=referee_data)
        
        assert response.status_code == 201
        referee_id = response.json()
        assert UUID(referee_id)  # Valid UUID
    
    async def test_get_referee_by_id(self, client: AsyncClient, db_session):
        """Test retrieving referee by ID"""
        # First create a referee
        referee_data = {
            "name": "Dr. Get Test",
            "email": "gettest@example.com",
            "institution": "Get University",
            "time_metrics": {
                "avg_response_time": 3.0,
                "avg_review_time": 21.0,
                "fastest_review": 7.0,
                "slowest_review": 35.0,
                "response_time_std": 1.0,
                "review_time_std": 5.0,
                "on_time_rate": 0.9
            },
            "quality_metrics": {
                "avg_quality_score": 8.0,
                "quality_consistency": 0.85,
                "report_thoroughness": 0.9,
                "constructiveness_score": 8.5,
                "technical_accuracy": 8.2,
                "clarity_score": 8.0,
                "actionability_score": 7.8
            },
            "workload_metrics": {
                "current_reviews": 1,
                "completed_reviews_30d": 2,
                "completed_reviews_90d": 5,
                "completed_reviews_365d": 20,
                "monthly_average": 1.7,
                "peak_capacity": 4,
                "availability_score": 0.75,
                "burnout_risk_score": 0.2
            },
            "reliability_metrics": {
                "acceptance_rate": 0.85,
                "completion_rate": 0.98,
                "ghost_rate": 0.02,
                "decline_after_accept_rate": 0.01,
                "reminder_effectiveness": 0.95,
                "communication_score": 0.9,
                "excuse_frequency": 0.05
            },
            "expertise_metrics": {
                "expertise_areas": ["statistics", "data science"],
                "h_index": 25,
                "recent_publications": 8,
                "citation_count": 1200,
                "years_experience": 10
            }
        }
        
        create_response = await client.post("/api/v1/referees/", json=referee_data)
        assert create_response.status_code == 201
        referee_id = create_response.json()
        
        # Now get the referee
        get_response = await client.get(f"/api/v1/referees/{referee_id}")
        assert get_response.status_code == 200
        
        referee = get_response.json()
        assert referee["name"] == "Dr. Get Test"
        assert referee["email"] == "gettest@example.com"
        assert referee["overall_score"] > 0
        assert referee["time_metrics"]["avg_response_time"] == 3.0
    
    async def test_get_referee_by_email(self, client: AsyncClient, db_session):
        """Test retrieving referee by email"""
        # Create referee
        referee_data = {
            "name": "Dr. Email Test",
            "email": "emailtest@example.com",
            "institution": "Email University",
            "time_metrics": {
                "avg_response_time": 4.0,
                "avg_review_time": 20.0,
                "fastest_review": 10.0,
                "slowest_review": 30.0,
                "response_time_std": 2.0,
                "review_time_std": 4.0,
                "on_time_rate": 0.85
            },
            "quality_metrics": {
                "avg_quality_score": 7.5,
                "quality_consistency": 0.8,
                "report_thoroughness": 0.85,
                "constructiveness_score": 8.0,
                "technical_accuracy": 7.8,
                "clarity_score": 7.5,
                "actionability_score": 7.2
            },
            "workload_metrics": {
                "current_reviews": 3,
                "completed_reviews_30d": 4,
                "completed_reviews_90d": 10,
                "completed_reviews_365d": 35,
                "monthly_average": 3.0,
                "peak_capacity": 6,
                "availability_score": 0.5,
                "burnout_risk_score": 0.4
            },
            "reliability_metrics": {
                "acceptance_rate": 0.75,
                "completion_rate": 0.92,
                "ghost_rate": 0.08,
                "decline_after_accept_rate": 0.03,
                "reminder_effectiveness": 0.88,
                "communication_score": 0.82,
                "excuse_frequency": 0.12
            },
            "expertise_metrics": {
                "expertise_areas": ["computer vision", "deep learning"],
                "h_index": 35,
                "recent_publications": 12,
                "citation_count": 2000,
                "years_experience": 15
            }
        }
        
        create_response = await client.post("/api/v1/referees/", json=referee_data)
        assert create_response.status_code == 201
        
        # Get by email
        get_response = await client.get("/api/v1/referees/by-email/emailtest@example.com")
        assert get_response.status_code == 200
        
        referee = get_response.json()
        assert referee["name"] == "Dr. Email Test"
        assert referee["email"] == "emailtest@example.com"
    
    async def test_get_top_performers(self, client: AsyncClient, db_session):
        """Test getting top performers"""
        # Create multiple referees with different scores
        referees = [
            ("High Performer", 9.0, 0.9),
            ("Good Performer", 7.5, 0.8),
            ("Average Performer", 6.0, 0.7),
            ("Low Performer", 4.5, 0.6),
        ]
        
        for name, quality_score, on_time_rate in referees:
            referee_data = {
                "name": name,
                "email": f"{name.lower().replace(' ', '')}@example.com",
                "institution": "Performance University",
                "time_metrics": {
                    "avg_response_time": 3.0,
                    "avg_review_time": 21.0,
                    "fastest_review": 7.0,
                    "slowest_review": 35.0,
                    "response_time_std": 1.0,
                    "review_time_std": 5.0,
                    "on_time_rate": on_time_rate
                },
                "quality_metrics": {
                    "avg_quality_score": quality_score,
                    "quality_consistency": 0.85,
                    "report_thoroughness": 0.9,
                    "constructiveness_score": quality_score,
                    "technical_accuracy": quality_score,
                    "clarity_score": quality_score,
                    "actionability_score": quality_score - 0.5
                },
                "workload_metrics": {
                    "current_reviews": 2,
                    "completed_reviews_30d": 3,
                    "completed_reviews_90d": 8,
                    "completed_reviews_365d": 30,
                    "monthly_average": 2.5,
                    "peak_capacity": 5,
                    "availability_score": 0.6,
                    "burnout_risk_score": 0.3
                },
                "reliability_metrics": {
                    "acceptance_rate": 0.8,
                    "completion_rate": 0.95,
                    "ghost_rate": 0.05,
                    "decline_after_accept_rate": 0.02,
                    "reminder_effectiveness": 0.9,
                    "communication_score": 0.85,
                    "excuse_frequency": 0.1
                },
                "expertise_metrics": {
                    "expertise_areas": ["test area"],
                    "h_index": 30,
                    "recent_publications": 10,
                    "citation_count": 1500,
                    "years_experience": 12
                }
            }
            
            response = await client.post("/api/v1/referees/", json=referee_data)
            assert response.status_code == 201
        
        # Get top performers
        response = await client.get("/api/v1/referees/top-performers", params={"limit": 3})
        assert response.status_code == 200
        
        top_performers = response.json()
        assert len(top_performers) == 3
        assert top_performers[0]["name"] == "High Performer"
        assert top_performers[0]["overall_score"] > top_performers[1]["overall_score"]
    
    async def test_get_performance_stats(self, client: AsyncClient, db_session):
        """Test getting overall performance statistics"""
        # Create some referees first
        for i in range(5):
            referee_data = {
                "name": f"Stats Test {i}",
                "email": f"stats{i}@example.com",
                "institution": "Stats University",
                "time_metrics": {
                    "avg_response_time": 3.0 + i,
                    "avg_review_time": 20.0 + i,
                    "fastest_review": 7.0,
                    "slowest_review": 35.0,
                    "response_time_std": 1.0,
                    "review_time_std": 5.0,
                    "on_time_rate": 0.8
                },
                "quality_metrics": {
                    "avg_quality_score": 7.0 + i * 0.3,
                    "quality_consistency": 0.8,
                    "report_thoroughness": 0.85,
                    "constructiveness_score": 7.5,
                    "technical_accuracy": 7.8,
                    "clarity_score": 7.5,
                    "actionability_score": 7.2
                },
                "workload_metrics": {
                    "current_reviews": i,
                    "completed_reviews_30d": i + 2,
                    "completed_reviews_90d": i + 5,
                    "completed_reviews_365d": i + 20,
                    "monthly_average": 2.0,
                    "peak_capacity": 5,
                    "availability_score": 0.6,
                    "burnout_risk_score": 0.3
                },
                "reliability_metrics": {
                    "acceptance_rate": 0.8,
                    "completion_rate": 0.95,
                    "ghost_rate": 0.05,
                    "decline_after_accept_rate": 0.02,
                    "reminder_effectiveness": 0.9,
                    "communication_score": 0.85,
                    "excuse_frequency": 0.1
                },
                "expertise_metrics": {
                    "expertise_areas": ["test"],
                    "h_index": 20 + i * 5,
                    "recent_publications": 5 + i,
                    "citation_count": 1000 + i * 100,
                    "years_experience": 10 + i
                }
            }
            
            response = await client.post("/api/v1/referees/", json=referee_data)
            assert response.status_code == 201
        
        # Get stats
        response = await client.get("/api/v1/referees/stats")
        assert response.status_code == 200
        
        stats = response.json()
        assert stats["total_referees"] == 5
        assert stats["average_score"] > 0
        assert stats["scored_referees"] == 5
    
    async def test_invalid_referee_id(self, client: AsyncClient, db_session):
        """Test error handling for invalid referee ID"""
        # Non-existent UUID
        response = await client.get("/api/v1/referees/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
        
        # Invalid UUID format
        response = await client.get("/api/v1/referees/not-a-uuid")
        assert response.status_code == 422
    
    async def test_validation_errors(self, client: AsyncClient, db_session):
        """Test validation of input data"""
        # Missing required fields
        invalid_data = {
            "name": "Test",
            # Missing email and other required fields
        }
        
        response = await client.post("/api/v1/referees/", json=invalid_data)
        assert response.status_code == 422
        
        # Invalid email format
        invalid_email_data = {
            "name": "Test User",
            "email": "not-an-email",
            "institution": "Test",
            # ... rest of required fields
        }
        
        response = await client.post("/api/v1/referees/", json=invalid_email_data)
        assert response.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])