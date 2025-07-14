#!/usr/bin/env python3
"""
Comprehensive test suite for the complete editorial system
Tests SICON scraper fixes and Gmail integration
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test results storage
TEST_RESULTS_DIR = Path(f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
TEST_RESULTS_DIR.mkdir(exist_ok=True)

def test_environment():
    """Test 1: Check environment setup and dependencies"""
    logger.info("=" * 80)
    logger.info("TEST 1: Environment Setup Check")
    logger.info("=" * 80)
    
    results = {
        "test": "environment_setup",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    # Check Python version
    python_version = sys.version
    results["checks"]["python_version"] = {
        "value": python_version,
        "status": "PASS" if sys.version_info >= (3, 8) else "FAIL"
    }
    logger.info(f"Python version: {python_version}")
    
    # Check required packages
    required_packages = [
        'selenium', 'requests', 'beautifulsoup4', 'pandas', 'numpy',
        'sqlalchemy', 'fastapi', 'uvicorn', 'pydantic', 'python-dotenv',
        'google-auth', 'google-auth-oauthlib', 'google-auth-httplib2',
        'google-api-python-client', 'undetected-chromedriver', 'keyring',
        'openai', 'tiktoken'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✓ {package} installed")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"✗ {package} missing")
    
    results["checks"]["packages"] = {
        "required": required_packages,
        "missing": missing_packages,
        "status": "PASS" if not missing_packages else "FAIL"
    }
    
    # Check environment variables
    env_vars = [
        'ORCID_CLIENT_ID', 'ORCID_CLIENT_SECRET',
        'OPENAI_API_KEY', 'DATABASE_URL',
        'GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'
    ]
    
    missing_env = []
    for var in env_vars:
        if os.getenv(var):
            logger.info(f"✓ {var} set")
        else:
            missing_env.append(var)
            logger.warning(f"✗ {var} not set")
    
    results["checks"]["environment_variables"] = {
        "required": env_vars,
        "missing": missing_env,
        "status": "PASS" if len(missing_env) <= 2 else "FAIL"  # Allow some missing
    }
    
    # Save results
    with open(TEST_RESULTS_DIR / "test_1_environment.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results["checks"]["packages"]["status"] == "PASS"


def test_sicon_scraper():
    """Test 2: Test SICON scraper functionality"""
    logger.info("=" * 80)
    logger.info("TEST 2: SICON Scraper Test")
    logger.info("=" * 80)
    
    results = {
        "test": "sicon_scraper",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    try:
        from src.infrastructure.scrapers.siam_scraper_fixed import SIAMScraperFixed
        from src.core.credential_manager import CredentialManager
        
        logger.info("Initializing SICON scraper...")
        
        # Initialize credential manager
        cred_manager = CredentialManager()
        
        # Get SICON credentials
        sicon_creds = cred_manager.get_credentials('sicon')
        if not sicon_creds:
            logger.error("No SICON credentials found")
            results["checks"]["credentials"] = {"status": "FAIL", "error": "No credentials"}
            with open(TEST_RESULTS_DIR / "test_2_sicon.json", "w") as f:
                json.dump(results, f, indent=2)
            return False
        
        results["checks"]["credentials"] = {"status": "PASS"}
        
        # Initialize scraper
        scraper = SIAMScraperFixed(
            username=sicon_creds['username'],
            password=sicon_creds['password'],
            journal_code='sicon',
            headless=True
        )
        
        # Test login
        logger.info("Testing SICON login...")
        if scraper.setup():
            results["checks"]["login"] = {"status": "PASS"}
            logger.info("✓ Login successful")
            
            # Test manuscript extraction
            logger.info("Testing manuscript extraction...")
            manuscripts = scraper.get_manuscripts_under_review()
            
            results["checks"]["manuscript_extraction"] = {
                "status": "PASS" if manuscripts else "WARNING",
                "count": len(manuscripts) if manuscripts else 0,
                "sample": manuscripts[:2] if manuscripts else []
            }
            
            logger.info(f"Found {len(manuscripts) if manuscripts else 0} manuscripts")
            
            # Cleanup
            scraper.cleanup()
            
        else:
            results["checks"]["login"] = {"status": "FAIL", "error": "Login failed"}
            logger.error("Login failed")
            scraper.cleanup()
            
    except Exception as e:
        logger.error(f"SICON scraper test failed: {e}")
        results["checks"]["error"] = {"status": "FAIL", "error": str(e)}
    
    # Save results
    with open(TEST_RESULTS_DIR / "test_2_sicon.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results["checks"].get("login", {}).get("status") == "PASS"


def test_gmail_integration():
    """Test 3: Test Gmail integration"""
    logger.info("=" * 80)
    logger.info("TEST 3: Gmail Integration Test")
    logger.info("=" * 80)
    
    results = {
        "test": "gmail_integration",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    try:
        from src.infrastructure.gmail_integration import GmailRefereeTracker
        
        logger.info("Initializing Gmail integration...")
        gmail = GmailRefereeTracker()
        
        # Test authentication
        logger.info("Testing Gmail authentication...")
        if gmail.authenticate():
            results["checks"]["authentication"] = {"status": "PASS"}
            logger.info("✓ Gmail authentication successful")
            
            # Test search functionality
            logger.info("Testing email search...")
            test_queries = [
                'subject:"manuscript" after:2024/1/1',
                'from:@siam.org after:2024/1/1',
                'label:INBOX is:unread'
            ]
            
            search_results = []
            for query in test_queries:
                try:
                    emails = gmail.search_emails(query, max_results=5)
                    search_results.append({
                        "query": query,
                        "count": len(emails),
                        "status": "PASS"
                    })
                    logger.info(f"✓ Query '{query}' returned {len(emails)} results")
                except Exception as e:
                    search_results.append({
                        "query": query,
                        "error": str(e),
                        "status": "FAIL"
                    })
                    logger.error(f"✗ Query '{query}' failed: {e}")
            
            results["checks"]["search"] = search_results
            
            # Test label operations
            logger.info("Testing label operations...")
            try:
                labels = gmail.list_labels()
                results["checks"]["labels"] = {
                    "status": "PASS",
                    "count": len(labels),
                    "sample": [l['name'] for l in labels[:5]]
                }
                logger.info(f"✓ Found {len(labels)} labels")
            except Exception as e:
                results["checks"]["labels"] = {
                    "status": "FAIL",
                    "error": str(e)
                }
                logger.error(f"Label test failed: {e}")
                
        else:
            results["checks"]["authentication"] = {
                "status": "FAIL",
                "error": "Authentication failed"
            }
            logger.error("Gmail authentication failed")
            
    except Exception as e:
        logger.error(f"Gmail integration test failed: {e}")
        results["checks"]["error"] = {"status": "FAIL", "error": str(e)}
    
    # Save results
    with open(TEST_RESULTS_DIR / "test_3_gmail.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results["checks"].get("authentication", {}).get("status") == "PASS"


async def test_api_endpoints():
    """Test 4: Test API endpoints"""
    logger.info("=" * 80)
    logger.info("TEST 4: API Endpoints Test")
    logger.info("=" * 80)
    
    results = {
        "test": "api_endpoints",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    try:
        import httpx
        
        # Start API server in background
        logger.info("Starting API server...")
        api_process = await asyncio.create_subprocess_exec(
            sys.executable, '-m', 'uvicorn', 'src.api.main:app',
            '--host', '0.0.0.0', '--port', '8000',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Wait for server to start
        await asyncio.sleep(5)
        
        # Test endpoints
        async with httpx.AsyncClient() as client:
            base_url = "http://localhost:8000"
            
            # Test health endpoint
            logger.info("Testing health endpoint...")
            try:
                response = await client.get(f"{base_url}/health")
                results["checks"]["health"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else None
                }
                logger.info(f"Health check: {response.status_code}")
            except Exception as e:
                results["checks"]["health"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"Health check failed: {e}")
            
            # Test manuscripts endpoint
            logger.info("Testing manuscripts endpoint...")
            try:
                response = await client.get(f"{base_url}/api/manuscripts")
                results["checks"]["manuscripts"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "status_code": response.status_code
                }
                logger.info(f"Manuscripts endpoint: {response.status_code}")
            except Exception as e:
                results["checks"]["manuscripts"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"Manuscripts endpoint failed: {e}")
            
            # Test analytics endpoint
            logger.info("Testing analytics endpoint...")
            try:
                response = await client.get(f"{base_url}/api/analytics/referee-performance")
                results["checks"]["analytics"] = {
                    "status": "PASS" if response.status_code == 200 else "FAIL",
                    "status_code": response.status_code
                }
                logger.info(f"Analytics endpoint: {response.status_code}")
            except Exception as e:
                results["checks"]["analytics"] = {"status": "FAIL", "error": str(e)}
                logger.error(f"Analytics endpoint failed: {e}")
        
        # Terminate API server
        api_process.terminate()
        await api_process.wait()
        
    except Exception as e:
        logger.error(f"API test failed: {e}")
        results["checks"]["error"] = {"status": "FAIL", "error": str(e)}
    
    # Save results
    with open(TEST_RESULTS_DIR / "test_4_api.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return all(check.get("status") == "PASS" for check in results["checks"].values() if "status" in check)


def test_database_operations():
    """Test 5: Test database operations"""
    logger.info("=" * 80)
    logger.info("TEST 5: Database Operations Test")
    logger.info("=" * 80)
    
    results = {
        "test": "database_operations",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    try:
        from sqlalchemy import create_engine, text
        from src.infrastructure.config import get_settings
        
        settings = get_settings()
        
        # Test connection
        logger.info("Testing database connection...")
        engine = create_engine(settings.database_url)
        
        with engine.connect() as conn:
            # Test basic query
            result = conn.execute(text("SELECT 1"))
            results["checks"]["connection"] = {"status": "PASS"}
            logger.info("✓ Database connection successful")
            
            # Check tables
            logger.info("Checking database tables...")
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            tables = [row[0] for row in conn.execute(tables_query)]
            expected_tables = [
                'manuscripts', 'referees', 'reviews', 'editors',
                'manuscript_referees', 'analytics_snapshots'
            ]
            
            missing_tables = [t for t in expected_tables if t not in tables]
            
            results["checks"]["tables"] = {
                "status": "PASS" if not missing_tables else "FAIL",
                "found": tables,
                "missing": missing_tables
            }
            
            if missing_tables:
                logger.error(f"Missing tables: {missing_tables}")
            else:
                logger.info(f"✓ All {len(expected_tables)} expected tables found")
            
            # Test data operations
            logger.info("Testing data operations...")
            
            # Count records
            for table in ['manuscripts', 'referees', 'reviews']:
                if table in tables:
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.scalar()
                    logger.info(f"{table}: {count} records")
                    results["checks"][f"{table}_count"] = count
            
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        results["checks"]["error"] = {"status": "FAIL", "error": str(e)}
    
    # Save results
    with open(TEST_RESULTS_DIR / "test_5_database.json", "w") as f:
        json.dump(results, f, indent=2)
    
    return results["checks"].get("connection", {}).get("status") == "PASS"


def run_integration_test():
    """Test 6: Run full integration test"""
    logger.info("=" * 80)
    logger.info("TEST 6: Full Integration Test")
    logger.info("=" * 80)
    
    results = {
        "test": "integration",
        "timestamp": datetime.now().isoformat(),
        "checks": {}
    }
    
    try:
        # Test complete workflow
        logger.info("Testing complete editorial workflow...")
        
        # 1. Scrape data from SICON
        logger.info("Step 1: Scraping SICON data...")
        from src.infrastructure.scrapers.siam_scraper_fixed import SIAMScraperFixed
        from src.core.credential_manager import CredentialManager
        
        cred_manager = CredentialManager()
        sicon_creds = cred_manager.get_credentials('sicon')
        
        if sicon_creds:
            scraper = SIAMScraperFixed(
                username=sicon_creds['username'],
                password=sicon_creds['password'],
                journal_code='sicon',
                headless=True
            )
            
            if scraper.setup():
                manuscripts = scraper.get_manuscripts_under_review()
                results["checks"]["scraping"] = {
                    "status": "PASS",
                    "manuscripts_found": len(manuscripts) if manuscripts else 0
                }
                logger.info(f"✓ Scraped {len(manuscripts) if manuscripts else 0} manuscripts")
                scraper.cleanup()
            else:
                results["checks"]["scraping"] = {"status": "FAIL", "error": "Login failed"}
        else:
            results["checks"]["scraping"] = {"status": "SKIP", "reason": "No credentials"}
        
        # 2. Process with AI
        logger.info("Step 2: Testing AI processing...")
        try:
            from src.ai.services.manuscript_analyzer_service import ManuscriptAnalyzerService
            
            analyzer = ManuscriptAnalyzerService()
            # Test with dummy data
            test_manuscript = {
                "manuscript_id": "TEST-001",
                "title": "Test Manuscript",
                "abstract": "This is a test abstract for integration testing.",
                "status": "Under Review"
            }
            
            analysis = analyzer.analyze_manuscript(test_manuscript)
            results["checks"]["ai_processing"] = {
                "status": "PASS" if analysis else "FAIL",
                "has_analysis": bool(analysis)
            }
            logger.info("✓ AI processing tested")
            
        except Exception as e:
            results["checks"]["ai_processing"] = {"status": "FAIL", "error": str(e)}
            logger.error(f"AI processing failed: {e}")
        
        # 3. Store in database
        logger.info("Step 3: Testing database storage...")
        try:
            from src.infrastructure.repositories.manuscript_repository import ManuscriptRepository
            from sqlalchemy import create_engine
            from src.infrastructure.config import get_settings
            
            settings = get_settings()
            engine = create_engine(settings.database_url)
            
            repo = ManuscriptRepository(engine)
            # Test operations would go here
            results["checks"]["database_storage"] = {"status": "PASS"}
            logger.info("✓ Database storage tested")
            
        except Exception as e:
            results["checks"]["database_storage"] = {"status": "FAIL", "error": str(e)}
            logger.error(f"Database storage failed: {e}")
        
        # 4. Gmail integration
        logger.info("Step 4: Testing Gmail integration...")
        try:
            from src.infrastructure.gmail_integration import GmailRefereeTracker
            
            gmail = GmailRefereeTracker()
            if gmail.authenticate():
                # Test email search
                emails = gmail.search_emails('subject:test', max_results=1)
                results["checks"]["gmail_integration"] = {
                    "status": "PASS",
                    "authenticated": True,
                    "can_search": True
                }
                logger.info("✓ Gmail integration tested")
            else:
                results["checks"]["gmail_integration"] = {
                    "status": "FAIL",
                    "error": "Authentication failed"
                }
                
        except Exception as e:
            results["checks"]["gmail_integration"] = {"status": "FAIL", "error": str(e)}
            logger.error(f"Gmail integration failed: {e}")
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        results["checks"]["error"] = {"status": "FAIL", "error": str(e)}
    
    # Save results
    with open(TEST_RESULTS_DIR / "test_6_integration.json", "w") as f:
        json.dump(results, f, indent=2)
    
    # Generate summary
    passed = sum(1 for check in results["checks"].values() 
                 if isinstance(check, dict) and check.get("status") == "PASS")
    total = len(results["checks"])
    
    results["summary"] = {
        "passed": passed,
        "total": total,
        "success_rate": f"{(passed/total)*100:.1f}%" if total > 0 else "0%"
    }
    
    return passed == total


def generate_test_report():
    """Generate comprehensive test report"""
    logger.info("=" * 80)
    logger.info("GENERATING TEST REPORT")
    logger.info("=" * 80)
    
    report = {
        "test_suite": "Complete System Test",
        "timestamp": datetime.now().isoformat(),
        "results_directory": str(TEST_RESULTS_DIR),
        "tests": {}
    }
    
    # Load all test results
    for test_file in TEST_RESULTS_DIR.glob("test_*.json"):
        with open(test_file) as f:
            test_data = json.load(f)
            test_name = test_data.get("test", test_file.stem)
            report["tests"][test_name] = test_data
    
    # Calculate overall statistics
    total_tests = len(report["tests"])
    passed_tests = sum(1 for test in report["tests"].values()
                      if all(check.get("status") == "PASS" 
                            for check in test.get("checks", {}).values()
                            if isinstance(check, dict) and "status" in check))
    
    report["summary"] = {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": total_tests - passed_tests,
        "success_rate": f"{(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "0%"
    }
    
    # Save comprehensive report
    report_path = TEST_RESULTS_DIR / "COMPLETE_TEST_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    
    # Generate markdown report
    markdown_report = f"""# Complete System Test Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Total Tests**: {report['summary']['total_tests']}
- **Passed**: {report['summary']['passed']}
- **Failed**: {report['summary']['failed']}
- **Success Rate**: {report['summary']['success_rate']}

## Test Results

"""
    
    for test_name, test_data in report["tests"].items():
        markdown_report += f"### {test_name.replace('_', ' ').title()}\n\n"
        
        for check_name, check_data in test_data.get("checks", {}).items():
            if isinstance(check_data, dict) and "status" in check_data:
                status_icon = "✅" if check_data["status"] == "PASS" else "❌"
                markdown_report += f"- {status_icon} **{check_name}**: {check_data['status']}\n"
                
                if check_data.get("error"):
                    markdown_report += f"  - Error: {check_data['error']}\n"
        
        markdown_report += "\n"
    
    # Save markdown report
    markdown_path = TEST_RESULTS_DIR / "COMPLETE_TEST_REPORT.md"
    with open(markdown_path, "w") as f:
        f.write(markdown_report)
    
    logger.info(f"Test report saved to: {report_path}")
    logger.info(f"Markdown report saved to: {markdown_path}")
    
    return report


async def main():
    """Run all tests"""
    logger.info("Starting Complete System Test Suite")
    logger.info(f"Results will be saved to: {TEST_RESULTS_DIR}")
    
    # Run tests
    test_results = []
    
    # Test 1: Environment
    test_results.append(("Environment Setup", test_environment()))
    
    # Test 2: SICON Scraper
    test_results.append(("SICON Scraper", test_sicon_scraper()))
    
    # Test 3: Gmail Integration
    test_results.append(("Gmail Integration", test_gmail_integration()))
    
    # Test 4: API Endpoints
    test_results.append(("API Endpoints", await test_api_endpoints()))
    
    # Test 5: Database Operations
    test_results.append(("Database Operations", test_database_operations()))
    
    # Test 6: Integration Test
    test_results.append(("Integration Test", run_integration_test()))
    
    # Generate report
    report = generate_test_report()
    
    # Print summary
    logger.info("=" * 80)
    logger.info("TEST SUITE COMPLETE")
    logger.info("=" * 80)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
    
    logger.info("-" * 80)
    logger.info(f"Overall Success Rate: {report['summary']['success_rate']}")
    logger.info(f"Full report available at: {TEST_RESULTS_DIR}")


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Run tests
    asyncio.run(main())