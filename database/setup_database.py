#!/usr/bin/env python3
"""
Database setup script for Editorial Scripts
Creates database, user, and runs initial schema
"""

import asyncio
import asyncpg
import sys
import os
from pathlib import Path
from typing import Optional
import argparse

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.config import settings

class DatabaseSetup:
    """Database setup and migration utility"""
    
    def __init__(self, admin_user: str = "postgres", admin_password: str = None):
        self.admin_user = admin_user
        self.admin_password = admin_password or os.getenv("POSTGRES_ADMIN_PASSWORD", "postgres")
        self.host = settings.database.host
        self.port = settings.database.port
        self.target_db = settings.database.name
        self.target_user = settings.database.user
        self.target_password = settings.database.password
    
    async def create_database_and_user(self):
        """Create database and user if they don't exist"""
        print("🗄️ Setting up PostgreSQL database and user...")
        
        # Connect as admin to postgres db
        try:
            admin_conn = await asyncpg.connect(
                user=self.admin_user,
                password=self.admin_password,
                host=self.host,
                port=self.port,
                database="postgres"
            )
            
            # Check if database exists
            db_exists = await admin_conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", 
                self.target_db
            )
            
            if not db_exists:
                print(f"  Creating database '{self.target_db}'...")
                await admin_conn.execute(f'CREATE DATABASE "{self.target_db}"')
            else:
                print(f"  Database '{self.target_db}' already exists")
            
            # Check if user exists
            user_exists = await admin_conn.fetchval(
                "SELECT 1 FROM pg_user WHERE usename = $1",
                self.target_user
            )
            
            if not user_exists:
                print(f"  Creating user '{self.target_user}'...")
                await admin_conn.execute(
                    f"CREATE USER \"{self.target_user}\" WITH PASSWORD '{self.target_password}'"
                )
            else:
                print(f"  User '{self.target_user}' already exists")
            
            # Grant privileges
            print(f"  Granting privileges to '{self.target_user}'...")
            await admin_conn.execute(
                f'GRANT ALL PRIVILEGES ON DATABASE "{self.target_db}" TO "{self.target_user}"'
            )
            
            await admin_conn.close()
            print("✅ Database and user setup complete")
            
        except asyncpg.PostgresError as e:
            print(f"❌ Database setup failed: {e}")
            raise
    
    async def run_schema_migration(self):
        """Run the initial schema migration"""
        print("📋 Running initial schema migration...")
        
        try:
            # Connect to target database as target user
            conn = await asyncpg.connect(
                user=self.target_user,
                password=self.target_password,
                host=self.host,
                port=self.port,
                database=self.target_db
            )
            
            # Read and execute schema file
            schema_file = Path(__file__).parent / "schema.sql"
            if not schema_file.exists():
                raise FileNotFoundError(f"Schema file not found: {schema_file}")
            
            schema_sql = schema_file.read_text()
            
            print("  Executing schema creation...")
            await conn.execute(schema_sql)
            
            await conn.close()
            print("✅ Schema migration complete")
            
        except asyncpg.PostgresError as e:
            print(f"❌ Schema migration failed: {e}")
            raise
        except Exception as e:
            print(f"❌ Unexpected error during schema migration: {e}")
            raise
    
    async def verify_setup(self):
        """Verify database setup by checking tables"""
        print("🔍 Verifying database setup...")
        
        try:
            conn = await asyncpg.connect(
                user=self.target_user,
                password=self.target_password,
                host=self.host,
                port=self.port,
                database=self.target_db
            )
            
            # Check if main tables exist
            tables = await conn.fetch("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            table_names = [row['table_name'] for row in tables]
            expected_tables = [
                'manuscripts', 'referees', 'reviews', 'ai_analysis_cache',
                'referee_analytics', 'journal_analytics', 'system_metrics'
            ]
            
            print(f"  Found {len(table_names)} tables:")
            for table in table_names:
                print(f"    ✓ {table}")
            
            missing_tables = set(expected_tables) - set(table_names)
            if missing_tables:
                print(f"  ⚠️ Missing tables: {', '.join(missing_tables)}")
                return False
            
            # Test basic functionality
            test_query = "SELECT COUNT(*) FROM manuscripts"
            result = await conn.fetchval(test_query)
            print(f"  ✓ Test query successful: {result} manuscripts in database")
            
            await conn.close()
            print("✅ Database verification complete")
            return True
            
        except Exception as e:
            print(f"❌ Database verification failed: {e}")
            return False
    
    async def setup_complete(self):
        """Run complete database setup"""
        print("🚀 Starting Editorial Scripts database setup...")
        print(f"Target: {self.target_user}@{self.host}:{self.port}/{self.target_db}")
        print()
        
        try:
            await self.create_database_and_user()
            await self.run_schema_migration()
            
            if await self.verify_setup():
                print()
                print("🎉 Database setup completed successfully!")
                print()
                print("Next steps:")
                print("1. Copy .env.example to .env and update database credentials")
                print("2. Run the application: python -m src.api.main")
                print("3. Load sample data: python database/load_sample_data.py")
                return True
            else:
                print("❌ Database setup verification failed")
                return False
                
        except Exception as e:
            print(f"❌ Database setup failed: {e}")
            return False


async def main():
    """Main setup function"""
    parser = argparse.ArgumentParser(description="Setup Editorial Scripts database")
    parser.add_argument("--admin-user", default="postgres", help="PostgreSQL admin user")
    parser.add_argument("--admin-password", help="PostgreSQL admin password")
    parser.add_argument("--skip-verification", action="store_true", help="Skip verification step")
    
    args = parser.parse_args()
    
    setup = DatabaseSetup(
        admin_user=args.admin_user,
        admin_password=args.admin_password
    )
    
    success = await setup.setup_complete()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())