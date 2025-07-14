#!/usr/bin/env python3
"""
Test simple referee analytics operations without relationships
"""

import sys
import asyncio
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🧪 Testing simple referee operations...")

async def test_simple_operations():
    try:
        from src.infrastructure.config import get_settings
        import asyncpg
        
        settings = get_settings()
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )
        
        print("✅ Database connected")
        
        # Test simple insertion
        import uuid
        referee_uuid = uuid.uuid4()
        referee_id = str(referee_uuid)
        result = await conn.fetchrow("""
            INSERT INTO referees_analytics (id, name, email, institution, h_index, years_experience)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (email) DO UPDATE SET 
                name = EXCLUDED.name,
                institution = EXCLUDED.institution,
                h_index = EXCLUDED.h_index
            RETURNING id
        """, referee_uuid, "Dr. Test Analytics", "test.analytics@university.edu", "Analytics University", 30, 15)
        
        actual_id = result['id']
        
        print("✅ Referee data inserted")
        
        # Test cache insertion
        cache_data = {
            "referee_id": referee_id,
            "name": "Dr. Test Analytics",
            "email": "test.analytics@university.edu",
            "overall_score": 8.5,
            "time_metrics": {"avg_review_time": 18.5},
            "quality_metrics": {"avg_quality_score": 8.2}
        }
        
        import json
        await conn.execute("""
            INSERT INTO referee_analytics_cache (referee_id, metrics_json, calculated_at, valid_until)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (referee_id) DO UPDATE SET metrics_json = EXCLUDED.metrics_json
        """, actual_id, json.dumps(cache_data), datetime.now(), datetime.now().replace(hour=23, minute=59))
        
        print("✅ Cache data inserted")
        
        # Test retrieval
        result = await conn.fetchrow("""
            SELECT r.*, c.metrics_json 
            FROM referees_analytics r
            LEFT JOIN referee_analytics_cache c ON r.id = c.referee_id
            WHERE r.email = $1
        """, "test.analytics@university.edu")
        
        if result:
            print(f"✅ Retrieved data: {result['name']} (H-index: {result['h_index']})")
            print(f"   Cached metrics available: {bool(result['metrics_json'])}")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Simple operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_operations())
    print(f"🎯 Simple operations test: {'PASSED' if success else 'FAILED'}")