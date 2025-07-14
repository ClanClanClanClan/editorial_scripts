#!/usr/bin/env python3
"""
Test API startup without actually running the server
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("🚀 Testing API Startup")
print("=" * 50)

try:
    # Test importing the app
    from src.api.main import app
    print("✅ API app imported successfully")
    
    # Check app attributes
    print(f"✅ App title: {app.title}")
    print(f"✅ App version: {app.version}")
    
    # Check routes
    routes = [route.path for route in app.routes]
    print(f"✅ Number of routes: {len(routes)}")
    
    # Check key routes exist
    key_routes = ['/health', '/api/v1/manuscripts', '/api/v1/referees', '/api/v1/ai']
    for route in key_routes:
        matching = [r for r in routes if route in r]
        if matching:
            print(f"✅ Route {route} exists")
        else:
            print(f"❌ Route {route} not found")
    
    print("\n✨ API startup test passed!")
    
except Exception as e:
    print(f"❌ API startup failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)