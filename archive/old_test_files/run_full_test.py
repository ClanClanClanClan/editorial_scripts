#!/usr/bin/env /usr/bin/python3
"""
Run API server and tests together
"""

import subprocess
import sys
import os
import time
import signal
import asyncio
import threading

def run_server():
    """Run the API server in background"""
    print("🚀 Starting API server in background...")
    cmd = [
        sys.executable, "-m", "uvicorn", 
        "src.api.main_simple:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--log-level", "error"  # Reduce noise
    ]
    
    # Start server
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for it to start
    time.sleep(3)
    
    # Check if it's running
    try:
        import httpx
        response = httpx.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✅ Server is running!")
            return process
    except:
        pass
    
    print("❌ Server failed to start")
    process.kill()
    return None


def run_tests():
    """Run the paranoid tests"""
    print("\n🔥 Running paranoid API tests...")
    print("=" * 60)
    
    # Import and run the test suite
    from test_api_referee_paranoid import ParanoidAPITests
    
    suite = ParanoidAPITests()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    success = loop.run_until_complete(suite.run_all_tests())
    
    return success


def main():
    """Main test runner"""
    print("🎯 FULL API TEST SUITE")
    print("=" * 60)
    
    # Start server
    server_process = run_server()
    if not server_process:
        print("❌ Cannot start server!")
        return 1
    
    try:
        # Run tests
        success = run_tests()
        
        # Return appropriate exit code
        return 0 if success else 1
        
    finally:
        # Stop server
        print("\n🛑 Stopping server...")
        server_process.terminate()
        server_process.wait()
        print("✅ Server stopped")


if __name__ == "__main__":
    sys.exit(main())