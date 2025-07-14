#!/usr/bin/env python3
"""
Real Integration Test Runner

This script runs the complete suite of real integration tests for the editorial system.
It includes safety checks, credential validation, and comprehensive reporting.

Usage:
    python run_real_tests.py [options]
    
Options:
    --all                   Run all real tests
    --gmail                 Run Gmail API tests only
    --credentials          Run credential tests only
    --database             Run database tests only
    --scraping             Run journal scraping tests only
    --email-sending        Run email sending tests only
    --smoke                Run smoke tests only
    --dry-run              Run in dry-run mode (default)
    --live                 Run live tests (use with extreme caution)
    --verbose              Verbose output
    --report               Generate test report
    --setup-check          Check test environment setup
"""

import os
import sys
import argparse
import subprocess
import json
from datetime import datetime
from pathlib import Path
import warnings

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """Check if the environment is set up for real tests"""
    print("🔍 Checking test environment setup...")
    
    issues = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        issues.append("Python 3.8+ required")
    
    # Check required files
    required_files = [
        'requirements.txt',
        'core/credential_manager.py',
        'core/email_utils.py',
        'database/referee_db.py',
        'tests/real/test_config.py'
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            issues.append(f"Missing required file: {file}")
    
    # Check credentials
    cred_sources = []
    if os.path.exists('credentials.json'):
        cred_sources.append("Gmail credentials.json")
    if os.path.exists('token.json'):
        cred_sources.append("Gmail token.json")
    if subprocess.run(['which', 'op'], capture_output=True).returncode == 0:
        cred_sources.append("1Password CLI")
    
    if not cred_sources:
        issues.append("No credential sources found (Gmail OAuth or 1Password CLI)")
    
    # Check Chrome/Selenium
    chrome_paths = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium-browser'
    ]
    
    chrome_found = any(os.path.exists(path) for path in chrome_paths)
    if not chrome_found:
        issues.append("Chrome/Chromium not found for Selenium tests")
    
    # Report results
    if issues:
        print("❌ Environment issues found:")
        for issue in issues:
            print(f"   • {issue}")
        print("\n💡 Fix these issues before running real tests")
        return False
    else:
        print("✅ Environment setup looks good!")
        if cred_sources:
            print(f"   📋 Credential sources: {', '.join(cred_sources)}")
        return True

def run_safety_checks():
    """Run safety checks before executing real tests"""
    print("\n🛡️  Running safety checks...")
    
    safety_issues = []
    
    # Check for production database
    if os.path.exists('data/referees.db'):
        safety_issues.append("Production database found - tests might modify real data")
    
    # Check for .env file with real credentials
    if os.path.exists('.env'):
        safety_issues.append("Production .env file found - might use real credentials")
    
    # Check test configuration
    try:
        from tests.real.test_config import TEST_CONFIG
        if not TEST_CONFIG['DRY_RUN_ONLY']:
            safety_issues.append("DRY_RUN_ONLY is disabled - tests might send real emails")
        
        if TEST_CONFIG['MAX_EMAILS_TO_FETCH'] > 100:
            safety_issues.append("MAX_EMAILS_TO_FETCH too high - might hit rate limits")
    except ImportError:
        safety_issues.append("Cannot import test configuration")
    
    if safety_issues:
        print("⚠️  Safety warnings:")
        for issue in safety_issues:
            print(f"   • {issue}")
        
        response = input("\n❓ Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("🛑 Stopped by user")
            return False
    
    print("✅ Safety checks passed")
    return True

def run_pytest_command(test_path, markers=None, verbose=False):
    """Run pytest with appropriate flags"""
    cmd = ['python', '-m', 'pytest', test_path]
    
    # Add markers
    if markers:
        cmd.extend(['-m', markers])
    
    # Add verbose flag
    if verbose:
        cmd.append('-v')
    
    # Set environment for real tests
    env = os.environ.copy()
    env['RUN_REAL_TESTS'] = 'true'
    
    # Run command
    print(f"\n🚀 Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    
    return result

def generate_test_report(results):
    """Generate a test report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'results': results,
        'summary': {
            'total_tests': len(results),
            'passed': sum(1 for r in results if r['passed']),
            'failed': sum(1 for r in results if not r['passed']),
            'skipped': sum(1 for r in results if r['skipped'])
        }
    }
    
    # Write report
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📊 Test report saved to: {report_file}")
    return report

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description='Run real integration tests')
    parser.add_argument('--all', action='store_true', help='Run all real tests')
    parser.add_argument('--gmail', action='store_true', help='Run Gmail API tests only')
    parser.add_argument('--credentials', action='store_true', help='Run credential tests only')
    parser.add_argument('--database', action='store_true', help='Run database tests only')
    parser.add_argument('--scraping', action='store_true', help='Run journal scraping tests only')
    parser.add_argument('--email-sending', action='store_true', help='Run email sending tests only')
    parser.add_argument('--smoke', action='store_true', help='Run smoke tests only')
    parser.add_argument('--live', action='store_true', help='Run live tests (DANGEROUS)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--report', action='store_true', help='Generate test report')
    parser.add_argument('--setup-check', action='store_true', help='Check test environment only')
    
    args = parser.parse_args()
    
    # Handle setup check
    if args.setup_check:
        check_environment()
        return
    
    # Default to all tests if no specific test specified
    if not any([args.gmail, args.credentials, args.database, args.scraping, args.email_sending, args.smoke]):
        args.all = True
    
    print("🧪 Editorial Scripts - Real Integration Test Runner")
    print("=" * 50)
    
    # Environment check
    if not check_environment():
        sys.exit(1)
    
    # Safety checks
    if not run_safety_checks():
        sys.exit(1)
    
    # Warn about live mode
    if args.live:
        print("\n⚠️  LIVE MODE ENABLED - TESTS MAY AFFECT REAL SYSTEMS")
        response = input("Are you absolutely sure? Type 'LIVE' to continue: ")
        if response != 'LIVE':
            print("🛑 Stopped by user")
            sys.exit(1)
    
    # Test execution plan
    test_plan = []
    
    if args.all or args.gmail:
        test_plan.append(('Gmail API', 'tests/real/test_gmail_real.py', 'gmail'))
    
    if args.all or args.credentials:
        test_plan.append(('Credentials', 'tests/real/test_credentials_real.py', 'credential'))
    
    if args.all or args.database:
        test_plan.append(('Database', 'tests/real/test_database_real.py', None))
    
    if args.all or args.scraping:
        test_plan.append(('Journal Scraping', 'tests/real/test_journal_scraping_real.py', 'selenium'))
    
    if args.all or args.email_sending:
        test_plan.append(('Email Sending', 'tests/real/test_email_sending_real.py', 'gmail'))
    
    if args.all or args.smoke:
        test_plan.append(('Smoke Tests', 'tests/real/test_journal_scraping_real.py::TestSmokeIntegration', None))
    
    # Execute tests
    results = []
    
    for name, test_path, markers in test_plan:
        print(f"\n🔬 Testing {name}...")
        print("-" * 30)
        
        result = run_pytest_command(test_path, markers, args.verbose)
        
        # Parse results
        passed = result.returncode == 0
        skipped = 'SKIPPED' in result.stdout
        
        results.append({
            'name': name,
            'path': test_path,
            'passed': passed,
            'skipped': skipped,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
        
        # Show immediate results
        if passed:
            print(f"✅ {name} tests passed")
        elif skipped:
            print(f"⏭️  {name} tests skipped")
        else:
            print(f"❌ {name} tests failed")
            if not args.verbose:
                print("Run with --verbose for details")
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    failed = sum(1 for r in results if not r['passed'] and not r['skipped'])
    skipped = sum(1 for r in results if r['skipped'])
    
    print(f"Total tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⏭️  Skipped: {skipped}")
    
    if failed > 0:
        print("\n❌ FAILED TESTS:")
        for result in results:
            if not result['passed'] and not result['skipped']:
                print(f"   • {result['name']}")
    
    # Generate report
    if args.report:
        generate_test_report(results)
    
    # Exit with appropriate code
    if failed > 0:
        sys.exit(1)
    else:
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)

if __name__ == '__main__':
    main()