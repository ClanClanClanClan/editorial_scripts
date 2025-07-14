#!/usr/bin/env python3
"""
Simple database setup script for Editorial Scripts
Creates database, user, and runs initial schema without complex dependencies
"""

import asyncio
import asyncpg
import sys
import os
from pathlib import Path
import argparse

class SimpleDatabaseSetup:
    """Simple database setup utility"""
    
    def __init__(self, admin_user: str = "postgres", admin_password: str = None):
        self.admin_user = admin_user
        self.admin_password = admin_password or os.getenv("POSTGRES_ADMIN_PASSWORD", "postgres")
        
        # Use environment variables or defaults
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.target_db = os.getenv("DB_NAME", "editorial_scripts")
        self.target_user = os.getenv("DB_USER", "editorial")
        self.target_password = os.getenv("DB_PASSWORD", "editorial_password")
    
    async def create_database_and_user(self):
        """Create database and user if they don't exist"""
        print("🗄️ Setting up PostgreSQL database and user...")
        print(f"   Target: {self.target_user}@{self.host}:{self.port}/{self.target_db}")
        
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
                print("Database connection details:")
                print(f"  Host: {self.host}")
                print(f"  Port: {self.port}")
                print(f"  Database: {self.target_db}")
                print(f"  Username: {self.target_user}")
                print(f"  Password: {self.target_password}")
                print()
                print("Next steps:")
                print("1. Copy .env.example to .env and update database credentials")
                print("2. Load sample data: python database/load_sample_data.py")
                print("3. Run the application: python -m src.api.main")
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
    parser.add_argument("--host", default="localhost", help="PostgreSQL host")
    parser.add_argument("--port", default="5432", help="PostgreSQL port")
    parser.add_argument("--db-name", default="editorial_scripts", help="Target database name")
    parser.add_argument("--db-user", default="editorial", help="Target database user")
    parser.add_argument("--db-password", default="editorial_password", help="Target database password")
    
    args = parser.parse_args()
    
    setup = SimpleDatabaseSetup(
        admin_user=args.admin_user,
        admin_password=args.admin_password
    )
    
    # Override defaults with command line args
    setup.host = args.host
    setup.port = int(args.port)
    setup.target_db = args.db_name
    setup.target_user = args.db_user
    setup.target_password = args.db_password
    
    success = await setup.setup_complete()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())