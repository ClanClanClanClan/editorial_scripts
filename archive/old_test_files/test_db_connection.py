#!/usr/bin/env python3
"""
Test database connection and basic operations
"""

import sys
import asyncio
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🧪 Testing database connection...")

async def test_db_connection():
    try:
        from src.infrastructure.config import get_settings
        settings = get_settings()
        print(f"✅ Config loaded - DB: {settings.db_name}@{settings.db_host}:{settings.db_port}")
        
        import asyncpg
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )
        
        # Test simple query
        result = await conn.fetchval("SELECT version()")
        print(f"✅ Database connected - PostgreSQL version: {result[:50]}...")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_db_connection())
    print(f"🎯 Database test: {'PASSED' if success else 'FAILED'}")