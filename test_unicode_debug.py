#!/usr/bin/env /usr/bin/python3
"""
Debug Unicode issues in API
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from src.api.main_simple import app

client = TestClient(app)

def generate_valid_metrics():
    return {
        "name": "José García-López",
        "email": "jose@example.com",
        "institution": "Test University",
        "time_metrics": {
            "avg_response_time": 3.0,
            "avg_review_time": 21.0,
            "fastest_review": 7.0,
            "slowest_review": 35.0,
            "response_time_std": 1.0,
            "review_time_std": 5.0,
            "on_time_rate": 0.9,
            "consistency_score": 0.85
        },
        "quality_metrics": {
            "avg_quality_score": 8.0,
            "quality_consistency": 0.85,
            "report_thoroughness": 0.9,
            "constructiveness_score": 8.5,
            "technical_accuracy": 8.2,
            "clarity_score": 8.0,
            "actionability_score": 7.8,
            "overall_quality": 8.1
        },
        "workload_metrics": {
            "current_reviews": 2,
            "completed_reviews_30d": 3,
            "completed_reviews_90d": 8,
            "completed_reviews_365d": 30,
            "monthly_average": 2.5,
            "peak_capacity": 5,
            "availability_score": 0.6,
            "burnout_risk_score": 0.3,
            "capacity_utilization": 0.4
        },
        "reliability_metrics": {
            "acceptance_rate": 0.8,
            "completion_rate": 0.95,
            "ghost_rate": 0.05,
            "decline_after_accept_rate": 0.02,
            "reminder_effectiveness": 0.9,
            "communication_score": 0.85,
            "excuse_frequency": 0.1,
            "reliability_score": 0.82
        },
        "expertise_metrics": {
            "expertise_areas": ["machine learning", "optimization"],
            "h_index": 30,
            "recent_publications": 10,
            "citation_count": 1500,
            "years_experience": 12,
            "expertise_score": 0.75
        }
    }

print("🧪 Testing Unicode name support")
print("=" * 50)

data = generate_valid_metrics()
print(f"Creating referee: {data['name']}")

try:
    response = client.post("/api/v1/referees/", json=data)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        referee_id = response.json()
        print(f"✅ Created: {referee_id}")
        
        # Try to retrieve
        get_response = client.get(f"/api/v1/referees/{referee_id}")
        print(f"Get status: {get_response.status_code}")
        
        if get_response.status_code == 200:
            retrieved = get_response.json()
            print(f"✅ Retrieved name: {retrieved['name']}")
            print(f"Names match: {retrieved['name'] == data['name']}")
        else:
            print(f"❌ Failed to retrieve: {get_response.text}")
    else:
        print(f"❌ Failed to create: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")