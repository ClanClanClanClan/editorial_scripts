#!/usr/bin/env /usr/bin/python3
"""
Debug top performers endpoint issue
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from src.api.main_simple import app

client = TestClient(app)

print("🧪 Testing Top Performers Endpoint")
print("=" * 50)

# Test different limits
for limit in [1, 10, 100]:
    try:
        response = client.get(
            f"/api/v1/referees/top-performers",
            params={"limit": limit}
        )
        print(f"Limit {limit}: Status {response.status_code}")
        
        if response.status_code == 200:
            results = response.json()
            print(f"  ✅ Got {len(results)} results")
        else:
            print(f"  ❌ Error: {response.text}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")

print("\n" + "=" * 50)
print("✅ Top performers test complete!")