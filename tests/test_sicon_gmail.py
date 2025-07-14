#!/usr/bin/env python3
"""
Focused test for SICON scraper and Gmail integration
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_sicon_scraper():
    """Test SICON scraper with real credentials if available"""
    logger.info("=" * 80)
    logger.info("Testing SICON Scraper")
    logger.info("=" * 80)
    
    try:
        from src.infrastructure.scrapers.siam_scraper_fixed import SIAMScraperFixed
        from src.core.credential_manager import CredentialManager
        
        # Initialize credential manager
        cred_manager = CredentialManager()
        
        # Check for SICON credentials
        sicon_creds = cred_manager.get_credentials('sicon')
        
        if not sicon_creds:
            logger.warning("No SICON credentials found in credential manager")
            logger.info("Checking environment variables...")
            
            # Try environment variables
            orcid_email = os.getenv('ORCID_EMAIL')
            orcid_password = os.getenv('ORCID_PASSWORD')
            
            if orcid_email and orcid_password and orcid_email != 'test@example.com':
                logger.info("Found ORCID credentials in environment")
                sicon_creds = {
                    'username': orcid_email,
                    'password': orcid_password
                }
            else:
                logger.warning("No real credentials found. Skipping SICON test.")
                return False
        
        # Initialize scraper
        logger.info("Initializing SICON scraper...")
        scraper = SIAMScraperFixed(journal_code='SICON')
        
        # Test login
        logger.info("Attempting SICON login...")
        if scraper.setup():
            logger.info("✓ Login successful!")
            
            # Test manuscript extraction
            logger.info("Extracting manuscripts under review...")
            manuscripts = scraper.get_manuscripts_under_review()
            
            if manuscripts:
                logger.info(f"✓ Found {len(manuscripts)} manuscripts")
                
                # Show sample data
                for i, ms in enumerate(manuscripts[:3]):
                    logger.info(f"\nManuscript {i+1}:")
                    logger.info(f"  ID: {ms.get('manuscript_id', 'N/A')}")
                    logger.info(f"  Title: {ms.get('title', 'N/A')[:60]}...")
                    logger.info(f"  Status: {ms.get('status', 'N/A')}")
            else:
                logger.warning("No manuscripts found (this might be normal)")
            
            # Cleanup
            scraper.cleanup()
            return True
            
        else:
            logger.error("✗ Login failed")
            scraper.cleanup()
            return False
            
    except Exception as e:
        logger.error(f"SICON test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gmail_integration():
    """Test Gmail integration"""
    logger.info("=" * 80)
    logger.info("Testing Gmail Integration")
    logger.info("=" * 80)
    
    try:
        from src.infrastructure.gmail_integration import GmailRefereeTracker
        
        # Initialize Gmail tracker
        logger.info("Initializing Gmail referee tracker...")
        gmail = GmailRefereeTracker()
        
        # Test authentication
        logger.info("Testing Gmail authentication...")
        if gmail.authenticate():
            logger.info("✓ Gmail authentication successful!")
            
            # Test search functionality
            logger.info("\nTesting email search functionality...")
            test_queries = [
                {
                    'query': 'subject:"referee" after:2024/1/1',
                    'description': 'Referee-related emails from 2024'
                },
                {
                    'query': 'from:@siam.org after:2024/1/1',
                    'description': 'Emails from SIAM'
                },
                {
                    'query': 'subject:"manuscript" after:2024/1/1',
                    'description': 'Manuscript-related emails'
                }
            ]
            
            for test in test_queries:
                logger.info(f"\nSearching: {test['description']}")
                logger.info(f"Query: {test['query']}")
                
                try:
                    emails = gmail.search_emails(test['query'], max_results=3)
                    logger.info(f"✓ Found {len(emails)} emails")
                    
                    # Show sample results
                    for i, email in enumerate(emails):
                        logger.info(f"  Email {i+1}:")
                        logger.info(f"    Subject: {email.get('subject', 'N/A')}")
                        logger.info(f"    From: {email.get('from', 'N/A')}")
                        logger.info(f"    Date: {email.get('date', 'N/A')}")
                        
                except Exception as e:
                    logger.error(f"✗ Search failed: {e}")
            
            # Test label operations
            logger.info("\nTesting label operations...")
            try:
                labels = gmail.list_labels()
                logger.info(f"✓ Found {len(labels)} labels")
                
                # Show some labels
                logger.info("Sample labels:")
                for label in labels[:5]:
                    logger.info(f"  - {label.get('name', 'N/A')}")
                    
            except Exception as e:
                logger.error(f"✗ Label listing failed: {e}")
            
            return True
            
        else:
            logger.error("✗ Gmail authentication failed")
            logger.info("\nTo set up Gmail integration:")
            logger.info("1. Create OAuth2 credentials in Google Cloud Console")
            logger.info("2. Download credentials.json to the project directory")
            logger.info("3. Run the authentication flow to generate token.json")
            return False
            
    except Exception as e:
        logger.error(f"Gmail test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test SICON + Gmail integration"""
    logger.info("=" * 80)
    logger.info("Testing SICON + Gmail Integration")
    logger.info("=" * 80)
    
    try:
        # First check if we can import both
        from src.infrastructure.scrapers.siam_scraper_fixed import SIAMScraperFixed
        from src.infrastructure.gmail_integration import GmailRefereeTracker
        from src.core.credential_manager import CredentialManager
        
        logger.info("✓ All required modules imported successfully")
        
        # Test credential manager
        cred_manager = CredentialManager()
        logger.info("\nChecking available credentials:")
        
        for journal in ['sicon', 'sifin', 'mf', 'mor']:
            creds = cred_manager.get_credentials(journal)
            if creds:
                logger.info(f"  ✓ {journal.upper()} credentials available")
            else:
                logger.info(f"  ✗ {journal.upper()} credentials not found")
        
        # Test AI configuration
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and openai_key != 'test-api-key':
            logger.info("\n✓ OpenAI API key configured")
        else:
            logger.info("\n✗ OpenAI API key not configured (using test key)")
        
        return True
        
    except Exception as e:
        logger.error(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    logger.info("Starting SICON + Gmail Test Suite")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Store results
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {}
    }
    
    # Run tests
    test_functions = [
        ("SICON Scraper", test_sicon_scraper),
        ("Gmail Integration", test_gmail_integration),
        ("System Integration", test_integration)
    ]
    
    passed = 0
    total = len(test_functions)
    
    for test_name, test_func in test_functions:
        logger.info("")  # Empty line for readability
        try:
            result = test_func()
            results["tests"][test_name] = {
                "status": "PASS" if result else "FAIL",
                "timestamp": datetime.now().isoformat()
            }
            if result:
                passed += 1
        except Exception as e:
            results["tests"][test_name] = {
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Test {test_name} encountered an error: {e}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    for test_name, test_result in results["tests"].items():
        status = test_result["status"]
        icon = "✅" if status == "PASS" else "❌"
        logger.info(f"{icon} {test_name}: {status}")
    
    logger.info("-" * 80)
    logger.info(f"Passed: {passed}/{total} ({(passed/total)*100:.1f}%)")
    
    # Save results
    results["summary"] = {
        "passed": passed,
        "total": total,
        "success_rate": f"{(passed/total)*100:.1f}%"
    }
    
    results_file = f"test_results_sicon_gmail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nResults saved to: {results_file}")


if __name__ == "__main__":
    main()