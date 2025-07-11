#!/usr/bin/env /usr/bin/python3
"""
Quick API test script - For manual testing
"""

import httpx
import asyncio
import json
from datetime import datetime
import sys


async def test_api():
    """Quick test of referee API endpoints"""
    base_url = "http://localhost:8000"
    
    print("🔍 Quick API Test")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        # 1. Health check
        print("\n1. Testing health endpoint...")
        try:
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print("   Make sure the API is running: uvicorn src.api.main:app")
            return
        
        # 2. Create a referee
        print("\n2. Creating a test referee...")
        referee_data = {
            "name": "Dr. Quick Test",
            "email": f"quicktest_{datetime.now().timestamp()}@example.com",
            "institution": "Quick Test University",
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
                "expertise_areas": ["machine learning", "optimization", "statistics"],
                "h_index": 30,
                "recent_publications": 10,
                "citation_count": 1500,
                "years_experience": 12,
                "expertise_score": 0.75
            }
        }
        
        try:
            response = await client.post(
                f"{base_url}/api/v1/referees/",
                json=referee_data
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 201:
                referee_id = response.json()
                print(f"   Created referee ID: {referee_id}")
            else:
                print(f"   Error: {response.text}")
                return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        # 3. Get referee by ID
        print(f"\n3. Getting referee by ID: {referee_id}")
        try:
            response = await client.get(f"{base_url}/api/v1/referees/{referee_id}")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Name: {data['name']}")
                print(f"   Email: {data['email']}")
                print(f"   Overall Score: {data['overall_score']:.2f}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 4. Get referee by email
        print(f"\n4. Getting referee by email...")
        try:
            response = await client.get(
                f"{base_url}/api/v1/referees/by-email/{referee_data['email']}"
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Found referee by email")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 5. Get top performers
        print("\n5. Getting top performers...")
        try:
            response = await client.get(
                f"{base_url}/api/v1/referees/top-performers",
                params={"limit": 5}
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                performers = response.json()
                print(f"   Found {len(performers)} top performers")
                for i, p in enumerate(performers[:3]):
                    print(f"   {i+1}. {p['name']} - Score: {p['overall_score']:.2f}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 6. Get performance stats
        print("\n6. Getting performance statistics...")
        try:
            response = await client.get(f"{base_url}/api/v1/referees/stats")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                stats = response.json()
                print(f"   Total referees: {stats['total_referees']}")
                print(f"   Average score: {stats['average_score']:.2f}")
                print(f"   Scored referees: {stats['scored_referees']}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # 7. Test error handling
        print("\n7. Testing error handling...")
        try:
            response = await client.get(
                f"{base_url}/api/v1/referees/00000000-0000-0000-0000-000000000000"
            )
            print(f"   Non-existent referee status: {response.status_code}")
            if response.status_code == 404:
                print("   ✅ Correctly returns 404 for non-existent referee")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Quick API test complete!")


if __name__ == "__main__":
    asyncio.run(test_api())