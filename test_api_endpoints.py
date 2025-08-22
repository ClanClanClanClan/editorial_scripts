"""Test API endpoints with proper database initialization."""

import asyncio
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from src.ecc.infrastructure.database.connection import initialize_database, close_database
from src.ecc.main import app


async def test_api_with_database():
    """Test API endpoints with proper database setup."""
    print("🧪 TESTING API ENDPOINTS WITH DATABASE")
    print("=" * 60)
    
    # Initialize database first
    database_url = "postgresql+asyncpg://ecc_user:ecc_password@localhost:5433/ecc_db"
    await initialize_database(database_url, echo=False)
    print("✅ Database initialized for testing")
    
    try:
        # Create test client
        client = TestClient(app, raise_server_exceptions=True)
        
        # Test health endpoint
        health_response = client.get("/health")
        print(f"✅ Health endpoint: {health_response.status_code}")
        if health_response.status_code == 200:
            data = health_response.json()
            print(f"   Status: {data['status']}")
        
        # Test journals endpoint  
        journals_response = client.get("/api/journals/")
        print(f"✅ Journals endpoint: {journals_response.status_code}")
        if journals_response.status_code == 200:
            data = journals_response.json()
            print(f"   Found {data['total_journals']} journals, {data['total_supported']} supported")
        
        # Test specific journal
        mf_response = client.get("/api/journals/MF")
        print(f"✅ MF journal endpoint: {mf_response.status_code}")
        if mf_response.status_code == 200:
            data = mf_response.json()
            print(f"   Journal: {data['name']}")
        
        # Test manuscripts endpoint (should work now)
        manuscripts_response = client.get("/api/manuscripts/")
        print(f"✅ Manuscripts endpoint: {manuscripts_response.status_code}")
        if manuscripts_response.status_code == 200:
            data = manuscripts_response.json()
            print(f"   Found {data['total']} manuscripts")
        else:
            print(f"   Error: {manuscripts_response.json()}")
        
        # Test authentication endpoints
        auth_response = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin"
        })
        print(f"✅ Auth login endpoint: {auth_response.status_code}")
        if auth_response.status_code == 200:
            data = auth_response.json()
            print(f"   Logged in as: {data['username']}")
        
        print("\n📊 API TESTING RESULTS:")
        all_working = all([
            health_response.status_code == 200,
            journals_response.status_code == 200,
            mf_response.status_code == 200,
            manuscripts_response.status_code == 200,
            auth_response.status_code == 200,
        ])
        
        if all_working:
            print("✅ ALL ENDPOINTS WORKING")
            print("✅ Database integration: COMPLETE")
            print("✅ API framework: FULLY FUNCTIONAL")
        else:
            print("❌ Some endpoints failing")
            
        return all_working
        
    except Exception as e:
        print(f"❌ API testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        await close_database()
        print("✅ Database connections closed")


if __name__ == "__main__":
    result = asyncio.run(test_api_with_database())
    print(f"\n🎯 PHASE 1 API TEST: {'SUCCESS' if result else 'FAILED'}")