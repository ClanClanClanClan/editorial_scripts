#!/usr/bin/env python3
"""
Test script for the connection debugger.
This script runs comprehensive debugging tests on all journal connections.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.connection_debugger import ConnectionDebugger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Test the connection debugger"""
    print("🔍 Editorial Scripts Connection Debugger Test")
    print("=" * 50)
    
    try:
        # Initialize the connection debugger
        logger.info("Initializing connection debugger...")
        debugger = ConnectionDebugger(debug=True)
        
        # Run comprehensive debugging
        logger.info("Starting comprehensive debugging of all journal connections...")
        results = debugger.comprehensive_debug_all_journals()
        
        # Display results
        print("\n📊 DEBUGGING RESULTS")
        print("=" * 50)
        
        for journal_name, journal_results in results.items():
            print(f"\n🔬 {journal_name}")
            print("-" * 20)
            
            if 'error' in journal_results:
                print(f"❌ Error: {journal_results['error']}")
                continue
            
            # Connection test results
            if 'connection_test' in journal_results:
                conn_test = journal_results['connection_test']
                print(f"🌐 Network: {'✅' if conn_test.get('network_accessible') else '❌'}")
                print(f"📄 Page Load: {'✅' if conn_test.get('page_loads') else '❌'}")
                print(f"🔑 Auth Elements: {'✅' if conn_test.get('auth_elements_found') else '❌'}")
                print(f"🏠 Dashboard: {'✅' if conn_test.get('dashboard_accessible') else '❌'}")
                print(f"📋 Documents: {'✅' if conn_test.get('documents_accessible') else '❌'}")
            
            # Issues found
            if 'issues_found' in journal_results:
                issues = journal_results['issues_found']
                if issues:
                    print(f"⚠️  Issues Found: {len(issues)}")
                    for issue in issues[:3]:  # Show top 3 issues
                        print(f"   • {issue}")
                else:
                    print("✅ No issues found")
            
            # Fixes applied
            if 'fixes_applied' in journal_results:
                fixes = journal_results['fixes_applied']
                if fixes.get('fixes_applied'):
                    print(f"🔧 Fixes Applied: {len(fixes['fixes_applied'])}")
                    for fix in fixes['fixes_applied'][:3]:
                        print(f"   • {fix}")
                
                if fixes.get('recommendations'):
                    print(f"💡 Recommendations: {len(fixes['recommendations'])}")
                    for rec in fixes['recommendations'][:2]:
                        print(f"   • {rec}")
        
        print("\n✅ Connection debugging completed successfully!")
        
        # Summary
        total_journals = len(results)
        successful_journals = sum(1 for r in results.values() if 'error' not in r)
        
        print(f"\n📈 SUMMARY")
        print(f"Total Journals Tested: {total_journals}")
        print(f"Successful Tests: {successful_journals}")
        print(f"Failed Tests: {total_journals - successful_journals}")
        print(f"Success Rate: {successful_journals/total_journals*100:.1f}%")
        
    except Exception as e:
        logger.error(f"❌ Connection debugging failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())