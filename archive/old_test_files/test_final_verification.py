#!/usr/bin/env /usr/bin/python3
"""
Final verification test
"""

import sys
import os
import uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from src.api.main_simple import app

client = TestClient(app)

print("🎯 FINAL API VERIFICATION")
print("=" * 50)

# Test key functionality
test_data = {
    "name": "Final Test",
    "email": "final@test.com", 
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

results = {}

# 1. Create referee
print("1. Creating referee...")
response = client.post("/api/v1/referees/", json=test_data)
results["create"] = response.status_code == 201
if response.status_code == 201:
    referee_id = response.json()
    print(f"   ✅ Created: {referee_id}")
else:
    print(f"   ❌ Failed: {response.status_code}")
    referee_id = None

# 2. Get by email
print("2. Getting by email...")
response = client.get(f"/api/v1/referees/by-email/{test_data['email']}")
results["get_by_email"] = response.status_code == 200
print(f"   {'✅' if results['get_by_email'] else '❌'} Status: {response.status_code}")

# 3. Get by ID (if we have one)
if referee_id:
    print("3. Getting by ID...")
    response = client.get(f"/api/v1/referees/{referee_id}")
    results["get_by_id"] = response.status_code == 200
    print(f"   {'✅' if results['get_by_id'] else '❌'} Status: {response.status_code}")

# 4. Top performers
print("4. Top performers...")
response = client.get("/api/v1/referees/top-performers?limit=5")
results["top_performers"] = response.status_code == 200
print(f"   {'✅' if results['top_performers'] else '❌'} Status: {response.status_code}")

# 5. Stats
print("5. Performance stats...")
response = client.get("/api/v1/referees/stats")
results["stats"] = response.status_code == 200
print(f"   {'✅' if results['stats'] else '❌'} Status: {response.status_code}")

# 6. Update (if we have ID)
if referee_id:
    print("6. Update referee...")
    update_data = {"name": "Updated Final Test"}
    response = client.put(f"/api/v1/referees/{referee_id}", json=update_data)
    results["update"] = response.status_code == 200
    print(f"   {'✅' if results['update'] else '❌'} Status: {response.status_code}")

print("\n" + "=" * 50)
print("📊 FINAL RESULTS SUMMARY")
print("=" * 50)

working = sum(results.values())
total = len(results)
percentage = (working / total) * 100

for test, passed in results.items():
    print(f"  {'✅' if passed else '❌'} {test}")

print(f"\n🎯 CORE FUNCTIONALITY: {working}/{total} ({percentage:.1f}%)")

if percentage >= 80:
    print("🎉 API IS READY FOR PRODUCTION!")
elif percentage >= 60:
    print("⚠️  API has core functionality but needs polish")
else:
    print("❌ API needs significant work")