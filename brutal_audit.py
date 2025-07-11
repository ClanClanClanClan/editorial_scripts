#!/usr/bin/env /usr/bin/python3
"""
BRUTAL HONEST AUDIT - No lies, no bullshit
"""

import asyncio
import asyncpg
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'src'))
sys.path.append(str(Path(__file__).parent / 'analytics'))

print("🔍 BRUTAL HONEST AUDIT OF REFEREE ANALYTICS")
print("=" * 70)


async def brutal_audit():
    audit_results = {
        'database': {'status': '❌', 'details': []},
        'repository': {'status': '❌', 'details': []},
        'functionality': {'status': '❌', 'details': []},
        'lies_found': []
    }
    
    # AUDIT 1: Database Connection
    print("\n📊 AUDIT 1: Database Reality Check")
    print("-" * 40)
    try:
        conn = await asyncpg.connect(
            host='localhost',
            port=5432,
            user='dylanpossamai',
            password='',
            database='editorial_scripts'
        )
        print("✅ Database connection successful")
        audit_results['database']['status'] = '✅'
        
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name LIKE '%referee%' OR table_name LIKE '%analytics%')
            ORDER BY table_name
        """)
        
        table_names = [t['table_name'] for t in tables]
        print(f"\nFound {len(table_names)} related tables:")
        for table in table_names:
            print(f"  - {table}")
        
        # Verify critical tables
        required_tables = ['referees_analytics', 'referee_analytics_cache', 'referee_metrics_history']
        missing_tables = [t for t in required_tables if t not in table_names]
        
        if missing_tables:
            print(f"\n❌ MISSING CRITICAL TABLES: {missing_tables}")
            audit_results['lies_found'].append(f"Claimed tables exist but missing: {missing_tables}")
        else:
            print("\n✅ All critical tables exist")
            audit_results['database']['details'].append("All required tables present")
        
        # Count actual data
        referee_count = await conn.fetchval('SELECT COUNT(*) FROM referees_analytics')
        cache_count = await conn.fetchval('SELECT COUNT(*) FROM referee_analytics_cache')
        history_count = await conn.fetchval('SELECT COUNT(*) FROM referee_metrics_history')
        
        print(f"\nData counts:")
        print(f"  Referees: {referee_count}")
        print(f"  Cached metrics: {cache_count}")
        print(f"  History records: {history_count}")
        
        audit_results['database']['details'].append(f"Referees: {referee_count}, Cache: {cache_count}, History: {history_count}")
        
    except Exception as e:
        print(f"❌ DATABASE CONNECTION FAILED: {e}")
        audit_results['lies_found'].append(f"Database connection failed: {e}")
        conn = None
    
    # AUDIT 2: Repository Code
    print("\n📁 AUDIT 2: Repository Implementation Check")
    print("-" * 40)
    
    try:
        # Check if files actually exist
        repo_path = Path('src/infrastructure/repositories/referee_repository_fixed.py')
        models_path = Path('src/infrastructure/database/referee_models_fixed.py')
        domain_path = Path('analytics/models/referee_metrics.py')
        
        files_exist = {
            'Repository': repo_path.exists(),
            'DB Models': models_path.exists(),
            'Domain Models': domain_path.exists()
        }
        
        for name, exists in files_exist.items():
            status = "✅" if exists else "❌"
            print(f"{status} {name}: {exists}")
            if not exists:
                audit_results['lies_found'].append(f"{name} file doesn't exist")
        
        # Try to import
        if all(files_exist.values()):
            try:
                from src.infrastructure.repositories.referee_repository_fixed import RefereeRepositoryFixed
                print("\n✅ Repository imports successfully")
                audit_results['repository']['status'] = '✅'
                
                # Check methods exist
                repo = RefereeRepositoryFixed()
                methods = ['save_referee_metrics', 'get_referee_metrics', 'get_referee_by_email', 
                          'get_performance_stats', 'get_top_performers', 'record_review_activity']
                
                for method in methods:
                    if hasattr(repo, method):
                        print(f"  ✅ {method} exists")
                    else:
                        print(f"  ❌ {method} MISSING")
                        audit_results['lies_found'].append(f"Method {method} doesn't exist")
                        
            except Exception as e:
                print(f"\n❌ Repository import failed: {e}")
                audit_results['lies_found'].append(f"Repository import failed: {e}")
        
    except Exception as e:
        print(f"❌ Repository check failed: {e}")
    
    # AUDIT 3: Actual Functionality Test
    print("\n⚡ AUDIT 3: Real Functionality Test")
    print("-" * 40)
    
    if conn and audit_results['repository']['status'] == '✅':
        try:
            from models.referee_metrics import (
                RefereeMetrics, TimeMetrics, QualityMetrics, WorkloadMetrics,
                ReliabilityMetrics, ExpertiseMetrics
            )
            
            # Test 1: Can we actually retrieve data?
            print("\nTest 1: Retrieve existing referee")
            test_id = await conn.fetchval('SELECT id FROM referees_analytics LIMIT 1')
            if test_id:
                retrieved = await repo.get_referee_metrics(test_id)
                if retrieved:
                    print(f"  ✅ Retrieved: {retrieved.name} (Score: {retrieved.get_overall_score():.2f})")
                    audit_results['functionality']['details'].append("Retrieval works")
                else:
                    print(f"  ❌ Retrieval returned None for ID {test_id}")
                    audit_results['lies_found'].append("get_referee_metrics returns None")
            
            # Test 2: Performance stats
            print("\nTest 2: Performance statistics")
            stats = await repo.get_performance_stats()
            if stats and 'total_referees' in stats:
                print(f"  ✅ Stats work: {stats['total_referees']} referees, avg score: {stats.get('avg_overall_score', 0):.2f}")
                audit_results['functionality']['details'].append("Stats calculation works")
            else:
                print(f"  ❌ Stats failed or incomplete: {stats}")
                audit_results['lies_found'].append("Performance stats don't work properly")
            
            # Test 3: Top performers
            print("\nTest 3: Top performers ranking")
            top = await repo.get_top_performers(limit=3)
            if top:
                print(f"  ✅ Found {len(top)} top performers")
                for i, p in enumerate(top, 1):
                    print(f"     {i}. {p['name']} - Score: {p['overall_score']:.2f}")
                audit_results['functionality']['details'].append("Ranking works")
            else:
                print(f"  ❌ Top performers failed")
                audit_results['lies_found'].append("Top performers doesn't work")
            
            audit_results['functionality']['status'] = '✅'
            
        except Exception as e:
            print(f"\n❌ Functionality test failed: {e}")
            audit_results['lies_found'].append(f"Functionality test crashed: {e}")
            import traceback
            traceback.print_exc()
    
    if conn:
        await conn.close()
    
    # FINAL VERDICT
    print("\n" + "=" * 70)
    print("🎯 BRUTAL AUDIT VERDICT")
    print("=" * 70)
    
    print(f"\nDatabase: {audit_results['database']['status']}")
    for detail in audit_results['database']['details']:
        print(f"  - {detail}")
    
    print(f"\nRepository: {audit_results['repository']['status']}")
    for detail in audit_results['repository']['details']:
        print(f"  - {detail}")
    
    print(f"\nFunctionality: {audit_results['functionality']['status']}")
    for detail in audit_results['functionality']['details']:
        print(f"  - {detail}")
    
    if audit_results['lies_found']:
        print(f"\n❌ LIES/ISSUES FOUND ({len(audit_results['lies_found'])}):")
        for lie in audit_results['lies_found']:
            print(f"  ⚠️  {lie}")
    else:
        print(f"\n✅ NO LIES FOUND - Everything actually works as claimed!")
    
    # Overall assessment
    all_pass = all(r['status'] == '✅' for r in [audit_results['database'], 
                                                   audit_results['repository'], 
                                                   audit_results['functionality']])
    
    if all_pass and not audit_results['lies_found']:
        print("\n🎉 VERDICT: SYSTEM IS ACTUALLY WORKING")
        print("The referee analytics system is genuinely functional.")
    else:
        print("\n⚠️  VERDICT: SYSTEM HAS ISSUES")
        print("Not everything works as claimed.")
    
    return audit_results


if __name__ == "__main__":
    results = asyncio.run(brutal_audit())
    
    # Exit with error if lies found
    sys.exit(0 if not results['lies_found'] else 1)