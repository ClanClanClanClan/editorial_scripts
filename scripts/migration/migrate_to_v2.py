#!/usr/bin/env python3
"""
Migration script from v1 to v2 architecture
Helps transition from Selenium to Playwright and SQLite to PostgreSQL
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from datetime import datetime
import logging
from typing import Dict, List, Any

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine

# Add parent directory to path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.infrastructure.config import get_settings
from src.infrastructure.database.engine import init_db
from src.core.domain.models import ManuscriptStatus, RefereeStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages migration from v1 to v2"""
    
    def __init__(self):
        self.settings = get_settings()
        self.old_db_path = Path("data/referees.db")
        self.progress = {
            "manuscripts": 0,
            "referees": 0,
            "reviews": 0,
            "errors": []
        }
        
    async def run(self):
        """Run complete migration"""
        logger.info("Starting migration from v1 to v2")
        
        # Check prerequisites
        if not self.check_prerequisites():
            return
            
        # Initialize new database
        await self.init_new_database()
        
        # Migrate data
        await self.migrate_referees()
        await self.migrate_manuscripts()
        await self.migrate_reviews()
        
        # Migrate configurations
        await self.migrate_configurations()
        
        # Generate report
        self.generate_report()
        
        logger.info("Migration completed successfully")
        
    def check_prerequisites(self) -> bool:
        """Check if migration can proceed"""
        # Check old database exists
        if not self.old_db_path.exists():
            logger.error(f"Old database not found at {self.old_db_path}")
            return False
            
        # Check PostgreSQL connection
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                dbname=self.settings.database.name,
                user=self.settings.database.user,
                password=self.settings.database.password
            )
            conn.close()
            logger.info("PostgreSQL connection successful")
        except Exception as e:
            logger.error(f"Cannot connect to PostgreSQL: {e}")
            logger.error("Please ensure PostgreSQL is running and credentials are correct")
            return False
            
        return True
        
    async def init_new_database(self):
        """Initialize new database schema"""
        logger.info("Initializing new database schema")
        await init_db()
        
    async def migrate_referees(self):
        """Migrate referee data"""
        logger.info("Migrating referee data")
        
        # Connect to old SQLite database
        old_conn = sqlite3.connect(self.old_db_path)
        old_conn.row_factory = sqlite3.Row
        cursor = old_conn.cursor()
        
        # Get all referees
        cursor.execute("""
            SELECT DISTINCT 
                email, name, institution
            FROM review_history
            WHERE email IS NOT NULL
        """)
        
        referees = cursor.fetchall()
        
        # Connect to new PostgreSQL database
        pg_conn = await asyncpg.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password
        )
        
        try:
            for referee in referees:
                try:
                    await pg_conn.execute("""
                        INSERT INTO referees (id, name, email, institution, created_at, updated_at)
                        VALUES (gen_random_uuid(), $1, $2, $3, $4, $4)
                        ON CONFLICT (email) DO UPDATE
                        SET name = EXCLUDED.name,
                            institution = EXCLUDED.institution,
                            updated_at = EXCLUDED.updated_at
                    """, 
                    referee['name'], 
                    referee['email'], 
                    referee['institution'],
                    datetime.utcnow()
                    )
                    self.progress['referees'] += 1
                except Exception as e:
                    self.progress['errors'].append(f"Referee {referee['email']}: {e}")
                    
        finally:
            await pg_conn.close()
            old_conn.close()
            
        logger.info(f"Migrated {self.progress['referees']} referees")
        
    async def migrate_manuscripts(self):
        """Migrate manuscript data"""
        logger.info("Migrating manuscript data")
        
        # For v1, manuscripts might be in JSON files
        manuscripts_dir = Path("data/extractions")
        
        if not manuscripts_dir.exists():
            logger.warning("No manuscript data found to migrate")
            return
            
        pg_conn = await asyncpg.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password
        )
        
        try:
            for json_file in manuscripts_dir.glob("**/*.json"):
                try:
                    with open(json_file) as f:
                        data = json.load(f)
                        
                    # Process each manuscript in the file
                    manuscripts = data.get('manuscripts', [])
                    journal_code = data.get('journal', {}).get('code', 'UNKNOWN')
                    
                    for ms in manuscripts:
                        await pg_conn.execute("""
                            INSERT INTO manuscripts (
                                id, journal_code, external_id, title, 
                                authors, status, submission_date,
                                created_at, updated_at, metadata
                            )
                            VALUES (
                                gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $7, $8
                            )
                            ON CONFLICT (journal_code, external_id) DO UPDATE
                            SET title = EXCLUDED.title,
                                updated_at = EXCLUDED.updated_at
                        """,
                        journal_code,
                        ms.get('manuscript_id', ''),
                        ms.get('title', ''),
                        json.dumps(ms.get('authors', [])),
                        'under_review',  # Default status
                        datetime.utcnow(),  # Use current time if not available
                        datetime.utcnow(),
                        json.dumps(ms)
                        )
                        self.progress['manuscripts'] += 1
                        
                except Exception as e:
                    self.progress['errors'].append(f"File {json_file}: {e}")
                    
        finally:
            await pg_conn.close()
            
        logger.info(f"Migrated {self.progress['manuscripts']} manuscripts")
        
    async def migrate_reviews(self):
        """Migrate review/referee assignment data"""
        logger.info("Migrating review data")
        
        # Connect to old SQLite database
        old_conn = sqlite3.connect(self.old_db_path)
        old_conn.row_factory = sqlite3.Row
        cursor = old_conn.cursor()
        
        # Get all reviews
        cursor.execute("""
            SELECT * FROM review_history
            ORDER BY invited_date DESC
        """)
        
        reviews = cursor.fetchall()
        
        pg_conn = await asyncpg.connect(
            host=self.settings.database.host,
            port=self.settings.database.port,
            database=self.settings.database.name,
            user=self.settings.database.user,
            password=self.settings.database.password
        )
        
        try:
            for review in reviews:
                try:
                    # Get referee ID by email
                    referee_id = await pg_conn.fetchval(
                        "SELECT id FROM referees WHERE email = $1",
                        review['email']
                    )
                    
                    if not referee_id:
                        continue
                        
                    # Get manuscript ID
                    manuscript_id = await pg_conn.fetchval(
                        "SELECT id FROM manuscripts WHERE external_id = $1",
                        review['manuscript_id']
                    )
                    
                    if not manuscript_id:
                        continue
                        
                    # Map old status to new
                    status_map = {
                        'invited': 'invited',
                        'accepted': 'accepted',
                        'declined': 'declined',
                        'submitted': 'completed',
                        'no_response': 'no_response'
                    }
                    
                    status = status_map.get(review['decision'], 'invited')
                    
                    await pg_conn.execute("""
                        INSERT INTO reviews (
                            id, referee_id, manuscript_id, status,
                            invited_date, responded_date, due_date, submitted_date,
                            created_at, updated_at
                        )
                        VALUES (
                            gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, $8
                        )
                    """,
                    referee_id,
                    manuscript_id,
                    status,
                    review['invited_date'],
                    review['responded_date'],
                    review['due_date'],
                    review['submitted_date'],
                    datetime.utcnow()
                    )
                    self.progress['reviews'] += 1
                    
                except Exception as e:
                    self.progress['errors'].append(f"Review {review['id']}: {e}")
                    
        finally:
            await pg_conn.close()
            old_conn.close()
            
        logger.info(f"Migrated {self.progress['reviews']} reviews")
        
    async def migrate_configurations(self):
        """Migrate journal configurations and credentials"""
        logger.info("Migrating configurations")
        
        # Check for old config files
        old_config_files = [
            Path("config/credentials.yaml"),
            Path("config/journals.yaml"),
            Path("credentials.json"),
            Path("token.json")
        ]
        
        new_config_dir = Path("config_backup_v1")
        new_config_dir.mkdir(exist_ok=True)
        
        for config_file in old_config_files:
            if config_file.exists():
                # Copy to backup
                import shutil
                shutil.copy2(config_file, new_config_dir / config_file.name)
                logger.info(f"Backed up {config_file} to {new_config_dir}")
                
        # Create migration instructions
        instructions = """
# Configuration Migration Instructions

1. Environment Variables (.env file):
   - Copy your ORCID credentials to the new .env file
   - Copy your ScholarOne credentials to the new .env file
   - Set up PostgreSQL credentials
   - Configure Redis if using caching
   - Set your OpenAI API key for AI features

2. Gmail API Credentials:
   - Copy credentials.json and token.json to the new location
   - Update paths in .env file

3. Journal-specific settings:
   - Review src/infrastructure/config.py for new configuration options
   - Update journal URLs if needed

4. Update your deployment scripts to use:
   - uvicorn src.api.main:app (instead of python main.py)
   - python -m src.cli.main (for CLI operations)

5. Database migrations:
   - Run: alembic upgrade head
   - To create new migrations: alembic revision --autogenerate -m "description"

Your old configuration files have been backed up to: {backup_dir}
""".format(backup_dir=new_config_dir)
        
        with open("MIGRATION_INSTRUCTIONS.md", "w") as f:
            f.write(instructions)
            
        logger.info("Configuration migration instructions written to MIGRATION_INSTRUCTIONS.md")
        
    def generate_report(self):
        """Generate migration report"""
        report = f"""
# Migration Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary
- Referees migrated: {self.progress['referees']}
- Manuscripts migrated: {self.progress['manuscripts']}
- Reviews migrated: {self.progress['reviews']}
- Errors encountered: {len(self.progress['errors'])}

## Next Steps
1. Review MIGRATION_INSTRUCTIONS.md for configuration steps
2. Test the new API: uvicorn src.api.main:app --reload
3. Run a test extraction to verify everything works
4. Review error log below if any issues occurred

## Errors
"""
        
        if self.progress['errors']:
            for error in self.progress['errors']:
                report += f"- {error}\n"
        else:
            report += "No errors encountered during migration.\n"
            
        with open("MIGRATION_REPORT.md", "w") as f:
            f.write(report)
            
        logger.info("Migration report written to MIGRATION_REPORT.md")
        print(report)


async def main():
    """Run migration"""
    migration = MigrationManager()
    await migration.run()


if __name__ == "__main__":
    asyncio.run(main())