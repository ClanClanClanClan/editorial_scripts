#!/usr/bin/env /usr/bin/python3
"""
Debug specific query issue
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.database.engine import get_session
from sqlalchemy import text
from uuid import UUID

async def debug_specific_query():
    print("🔍 Debug Specific Query Issue")
    print("=" * 50)
    
    # Use the first UUID from our database
    test_uuid = "efc16c05-0535-497f-b703-d72cfcef34d3"
    
    async with get_session() as session:
        print(f"Looking for UUID: {test_uuid}")
        
        # Try the exact query from the repository
        result = await session.execute(
            text("""
                SELECT r.*, c.metrics_json,
                       c.valid_until > NOW() as cache_valid
                FROM referees_analytics r
                LEFT JOIN referee_analytics_cache c ON r.id = c.referee_id
                WHERE r.id = :referee_id
            """),
            {"referee_id": test_uuid}
        )
        
        row = result.fetchone()
        if row:
            print("✅ Found referee:")
            print(f"  ID: {row.id}")
            print(f"  Name: {row.name}")
            print(f"  Has metrics_json: {row.metrics_json is not None}")
            print(f"  Cache valid: {row.cache_valid}")
        else:
            print("❌ No referee found")
            
        # Try with actual UUID object
        print(f"\nTrying with UUID object...")
        uuid_obj = UUID(test_uuid)
        result2 = await session.execute(
            text("""
                SELECT r.*, c.metrics_json,
                       c.valid_until > NOW() as cache_valid
                FROM referees_analytics r
                LEFT JOIN referee_analytics_cache c ON r.id = c.referee_id
                WHERE r.id = :referee_id
            """),
            {"referee_id": uuid_obj}
        )
        
        row2 = result2.fetchone()
        if row2:
            print("✅ Found with UUID object:")
            print(f"  ID: {row2.id}")
            print(f"  Name: {row2.name}")
        else:
            print("❌ No referee found with UUID object")

if __name__ == "__main__":
    asyncio.run(debug_specific_query())