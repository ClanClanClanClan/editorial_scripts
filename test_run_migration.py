#!/usr/bin/env python3
"""
Test running the referee analytics migration
"""

import sys
import asyncio
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'src'))

print("🧪 Testing migration...")

async def run_migration():
    try:
        from src.infrastructure.config import get_settings
        settings = get_settings()
        
        import asyncpg
        conn = await asyncpg.connect(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name
        )
        
        print("🗄️ Creating referee analytics tables...")
        
        # Create referees_analytics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS referees_analytics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(200) NOT NULL,
                email VARCHAR(200) NOT NULL UNIQUE,
                institution VARCHAR(300),
                h_index INTEGER,
                years_experience INTEGER,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                active BOOLEAN NOT NULL DEFAULT TRUE
            );
            CREATE INDEX IF NOT EXISTS idx_referee_analytics_email ON referees_analytics(email);
            CREATE INDEX IF NOT EXISTS idx_referee_analytics_name ON referees_analytics(name);
        """)
        print("✅ Created referees_analytics table")
        
        # Create manuscripts_analytics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS manuscripts_analytics (
                id VARCHAR(100) PRIMARY KEY,
                journal_code VARCHAR(10) NOT NULL,
                title VARCHAR(500),
                abstract TEXT,
                keywords VARCHAR[],
                research_area VARCHAR(200),
                submission_date TIMESTAMP,
                decision_date TIMESTAMP,
                final_decision VARCHAR(50),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_manuscript_analytics_journal ON manuscripts_analytics(journal_code);
        """)
        print("✅ Created manuscripts_analytics table")
        
        # Create referee_analytics_cache table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS referee_analytics_cache (
                referee_id UUID PRIMARY KEY REFERENCES referees_analytics(id) ON DELETE CASCADE,
                metrics_json JSONB NOT NULL,
                calculated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                valid_until TIMESTAMP NOT NULL,
                data_version INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_analytics_cache_valid ON referee_analytics_cache(valid_until);
        """)
        print("✅ Created referee_analytics_cache table")
        
        # Test inserting sample data
        print("📝 Testing sample data insertion...")
        await conn.execute("""
            INSERT INTO referees_analytics (name, email, institution, h_index, years_experience)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (email) DO NOTHING
        """, "Dr. Test Referee", "test@university.edu", "Test University", 25, 10)
        
        # Test querying
        result = await conn.fetchrow("SELECT * FROM referees_analytics WHERE email = $1", "test@university.edu")
        if result:
            print(f"✅ Sample data inserted and retrieved: {result['name']}")
        else:
            print("ℹ️ Sample data already exists or insertion failed")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(run_migration())
    print(f"🎯 Migration test: {'PASSED' if success else 'FAILED'}")