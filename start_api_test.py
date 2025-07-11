#!/usr/bin/env /usr/bin/python3
"""
Start the API server for testing
"""

import subprocess
import sys
import os
import signal
import time

# Set environment variables
os.environ['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))

print("🚀 Starting API server...")
print("=" * 50)

# Start the server
cmd = [
    sys.executable, "-m", "uvicorn", 
    "src.api.main_simple:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload"
]

print(f"Running: {' '.join(cmd)}")
print("\nPress Ctrl+C to stop the server")
print("=" * 50)

try:
    # Start the process
    process = subprocess.Popen(cmd)
    
    # Wait for it to start
    time.sleep(3)
    
    print("\n✅ Server should be running at http://localhost:8000")
    print("📚 API docs at http://localhost:8000/docs")
    
    # Wait for interrupt
    process.wait()
    
except KeyboardInterrupt:
    print("\n\n🛑 Stopping server...")
    process.send_signal(signal.SIGTERM)
    process.wait()
    print("✅ Server stopped")