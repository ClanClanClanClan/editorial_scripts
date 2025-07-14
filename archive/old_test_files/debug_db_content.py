#!/usr/bin/env /usr/bin/python3
"""
Debug database content to see what's actually stored
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.infrastructure.database.engine import get_session
from sqlalchemy import text

async def debug_db():
    print("🔍 Debug Database Content")
    print("=" * 50)
    
    async with get_session() as session:
        # Check what's in the referees table
        result = await session.execute(
            text("SELECT id, name, email FROM referees_analytics LIMIT 5")
        )
        
        print("📊 Recent referees in database:")
        for row in result:
            print(f"  ID: {row.id}")
            print(f"  Name: {row.name}")
            print(f"  Email: {row.email}")
            print("  ---")
        
        # Check cache table
        cache_result = await session.execute(
            text("SELECT referee_id, SUBSTR(metrics_json::text, 1, 100) as preview FROM referee_analytics_cache LIMIT 3")
        )
        
        print("\n📊 Cache entries:")
        for row in cache_result:
            print(f"  Referee ID: {row.referee_id}")
            print(f"  JSON preview: {row.preview}...")
            print("  ---")

if __name__ == "__main__":
    asyncio.run(debug_db())