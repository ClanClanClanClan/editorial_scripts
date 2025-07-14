#!/usr/bin/env python3
"""
Simple connection pool test without FastAPI dependencies
"""

import asyncio
import sys
import time
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.database.engine import get_session, get_connection_info
from src.infrastructure.repositories.referee_repository_fixed import RefereeRepositoryFixed

async def test_connection_usage():
    """Test connection usage with optimized settings"""
    print("🔧 SIMPLE CONNECTION POOL TEST")
    print("=" * 40)
    
    # Get initial connection count
    process = psutil.Process()
    initial_connections = len(process.net_connections())
    print(f"📊 Initial connections: {initial_connections}")
    
    # Test async operations
    repository = RefereeRepositoryFixed()
    
    start_time = time.time()
    operations = 0
    
    try:
        # Perform multiple operations
        for i in range(20):
            async with get_session() as session:
                # Simple query to test connection
                result = await session.execute("SELECT 1 as test")
                operations += 1
                
                if i % 5 == 0:
                    current_connections = len(process.net_connections())
                    pool_info = await get_connection_info()
                    print(f"   Operation {i+1}: {current_connections} connections, Pool: {pool_info}")
    
    except Exception as e:
        print(f"❌ Error during operations: {e}")
        return False
    
    end_time = time.time()
    final_connections = len(process.net_connections())
    duration = end_time - start_time
    
    # Results
    connection_growth = final_connections - initial_connections
    throughput = operations / duration if duration > 0 else 0
    
    print(f"\n📈 Results:")
    print(f"   Operations: {operations}")
    print(f"   Duration: {duration:.2f}s")
    print(f"   Throughput: {throughput:.1f} ops/sec")
    print(f"   Connections: {initial_connections} → {final_connections} (Δ{connection_growth:+d})")
    
    # Check criteria
    success = connection_growth <= 10 and operations == 20
    
    if success:
        print(f"✅ CONNECTION POOL OPTIMIZATION SUCCESSFUL!")
        print(f"   ✅ Connection growth controlled: {connection_growth:+d} ≤ 10")
    else:
        print(f"❌ CONNECTION POOL OPTIMIZATION FAILED!")
        if connection_growth > 10:
            print(f"   ❌ Too many connections: {connection_growth:+d} > 10")
        if operations != 20:
            print(f"   ❌ Operations failed: {operations} < 20")
    
    return success

async def main():
    try:
        return await test_connection_usage()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)