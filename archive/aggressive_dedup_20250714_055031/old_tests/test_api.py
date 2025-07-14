#!/usr/bin/env python3
"""
API Endpoints Test
"""

import os
import sys
import time
import logging
import asyncio
import signal
import subprocess
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start_api_server() -> Optional[subprocess.Popen]:
    """Start the API server in background"""
    try:
        # Start API server
        process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'uvicorn', 'src.api.main:app',
            '--host', '0.0.0.0', '--port', '8000',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for server to start
        await asyncio.sleep(5)
        
        return process
        
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        return None

async def test_api_endpoints():
    """Test API endpoints"""
    logger.info("Testing API endpoints...")
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            base_url = "http://localhost:8000"
            
            # Test health endpoint
            logger.info("Testing health endpoint...")
            try:
                response = await client.get(f"{base_url}/health", timeout=10.0)
                if response.status_code == 200:
                    logger.info("✓ Health endpoint working")
                    health_pass = True
                else:
                    logger.error(f"Health endpoint returned {response.status_code}")
                    health_pass = False
            except Exception as e:
                logger.error(f"Health endpoint failed: {e}")
                health_pass = False
            
            # Test docs endpoint
            logger.info("Testing docs endpoint...")
            try:
                response = await client.get(f"{base_url}/docs", timeout=10.0)
                if response.status_code == 200:
                    logger.info("✓ Docs endpoint working")
                    docs_pass = True
                else:
                    logger.error(f"Docs endpoint returned {response.status_code}")
                    docs_pass = False
            except Exception as e:
                logger.error(f"Docs endpoint failed: {e}")
                docs_pass = False
            
            # Test API root
            logger.info("Testing API root...")
            try:
                response = await client.get(f"{base_url}/", timeout=10.0)
                if response.status_code == 200:
                    logger.info("✓ API root working")
                    root_pass = True
                else:
                    logger.error(f"API root returned {response.status_code}")
                    root_pass = False
            except Exception as e:
                logger.error(f"API root failed: {e}")
                root_pass = False
            
            return health_pass and docs_pass and root_pass
            
    except ImportError:
        logger.error("httpx not available for API testing")
        return False
    except Exception as e:
        logger.error(f"API test failed: {e}")
        return False

def test_api_import():
    """Test API module import"""
    logger.info("Testing API module import...")
    
    try:
        from src.api.main import app
        logger.info("✓ API main module imported successfully")
        
        # Test FastAPI app
        if hasattr(app, 'routes'):
            route_count = len(app.routes)
            logger.info(f"✓ FastAPI app has {route_count} routes")
        
        return True
        
    except Exception as e:
        logger.error(f"API import failed: {e}")
        return False

async def main():
    """Run API tests"""
    logger.info("Starting API Test Suite")
    
    # Test 1: Import
    logger.info(f"\n{'='*60}")
    logger.info("TEST: API Import")
    logger.info('='*60)
    
    import_result = test_api_import()
    if import_result:
        logger.info("✅ API Import: PASS")
    else:
        logger.info("❌ API Import: FAIL")
        return False
    
    # Test 2: Server startup and endpoints
    logger.info(f"\n{'='*60}")
    logger.info("TEST: API Server and Endpoints")
    logger.info('='*60)
    
    # Start server
    api_process = await start_api_server()
    
    if api_process is None:
        logger.error("❌ Failed to start API server")
        return False
    
    try:
        # Test endpoints
        endpoint_result = await test_api_endpoints()
        
        if endpoint_result:
            logger.info("✅ API Endpoints: PASS")
            result = True
        else:
            logger.info("❌ API Endpoints: FAIL")
            result = False
    
    finally:
        # Cleanup: terminate server
        if api_process:
            api_process.terminate()
            await api_process.wait()
            logger.info("API server terminated")
    
    logger.info(f"\n{'='*60}")
    logger.info("API TEST SUMMARY")
    logger.info('='*60)
    
    if import_result and endpoint_result:
        logger.info("✅ All API tests passed!")
        return True
    else:
        logger.info("❌ Some API tests failed")
        return False

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # Run async main
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        sys.exit(1)