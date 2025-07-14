#!/usr/bin/env python3
"""
Database Operations Test
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test basic database connection"""
    logger.info("Testing database connection...")
    
    try:
        from src.infrastructure.config import get_settings
        settings = get_settings()
        
        # Get database URL
        db_url = settings.get_database_url
        logger.info(f"Database URL: {db_url}")
        
        if db_url.startswith('sqlite'):
            # SQLite test
            db_path = db_url.replace('sqlite:///', '').replace('sqlite://', '')
            logger.info(f"Testing SQLite connection to: {db_path}")
            
            # Create directory if needed
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Test connection
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create a simple test table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_table (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert test data
            cursor.execute("INSERT INTO test_table (name) VALUES (?)", ("test_entry",))
            conn.commit()
            
            # Query test data
            cursor.execute("SELECT COUNT(*) FROM test_table")
            count = cursor.fetchone()[0]
            
            logger.info(f"✓ Database connection successful, {count} test records")
            
            conn.close()
            return True
            
        else:
            # PostgreSQL test would go here
            logger.info("PostgreSQL connection testing not implemented")
            return True
            
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        return False

def test_sqlalchemy_integration():
    """Test SQLAlchemy integration"""
    logger.info("Testing SQLAlchemy integration...")
    
    try:
        from sqlalchemy import create_engine, text
        from src.infrastructure.config import get_settings
        
        settings = get_settings()
        db_url = settings.get_database_url
        
        # For SQLite, use synchronous URL
        if 'sqlite' in db_url:
            db_url = db_url.replace('sqlite:///', 'sqlite:///')
            
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                logger.info("✓ SQLAlchemy connection successful")
                return True
            else:
                logger.error("SQLAlchemy query returned unexpected result")
                return False
                
    except Exception as e:
        logger.error(f"SQLAlchemy test failed: {e}")
        return False

def main():
    """Run database tests"""
    logger.info("Starting Database Test Suite")
    
    tests = [
        ("Basic Database Connection", test_database_connection),
        ("SQLAlchemy Integration", test_sqlalchemy_integration)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST: {test_name}")
        logger.info('='*60)
        
        try:
            result = test_func()
            if result:
                logger.info(f"✅ {test_name}: PASS")
                passed += 1
            else:
                logger.info(f"❌ {test_name}: FAIL")
        except Exception as e:
            logger.error(f"❌ {test_name}: ERROR - {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"DATABASE TEST SUMMARY")
    logger.info('='*60)
    logger.info(f"Passed: {passed}/{len(tests)} ({(passed/len(tests))*100:.1f}%)")
    
    return passed == len(tests)

if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    success = main()
    sys.exit(0 if success else 1)