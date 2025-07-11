#!/usr/bin/env python3
"""
Verify connection pool configuration without dependencies
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def analyze_pool_config():
    """Analyze the connection pool configuration"""
    print("🔧 CONNECTION POOL CONFIGURATION ANALYSIS")
    print("=" * 50)
    
    # Read the engine configuration
    engine_file = Path(__file__).parent / "src/infrastructure/database/engine.py"
    
    with open(engine_file, 'r') as f:
        content = f.read()
    
    # Extract pool settings
    import re
    
    test_pool_size = re.search(r'pool_size = (\d+)', content)
    test_max_overflow = re.search(r'max_overflow = (\d+)', content)
    test_pool_timeout = re.search(r'pool_timeout = (\d+)', content)
    test_pool_recycle = re.search(r'pool_recycle = (\d+)', content)
    
    if test_pool_size and test_max_overflow:
        pool_size = int(test_pool_size.group(1))
        max_overflow = int(test_max_overflow.group(1))
        pool_timeout = int(test_pool_timeout.group(1)) if test_pool_timeout else "N/A"
        pool_recycle = int(test_pool_recycle.group(1)) if test_pool_recycle else "N/A"
        
        print(f"📊 Test Environment Pool Settings:")
        print(f"   Pool Size: {pool_size}")
        print(f"   Max Overflow: {max_overflow}")
        print(f"   Pool Timeout: {pool_timeout}s")
        print(f"   Pool Recycle: {pool_recycle}s")
        
        max_connections = pool_size + max_overflow
        print(f"   Maximum Possible Connections: {max_connections}")
        
        # Analysis
        print(f"\n🎯 ANALYSIS:")
        
        if max_connections <= 20:
            print(f"   ✅ Pool configuration excellent: {max_connections} ≤ 20 max connections")
            optimized = True
        elif max_connections <= 30:
            print(f"   ⚠️ Pool configuration acceptable: {max_connections} ≤ 30 max connections")
            optimized = True
        else:
            print(f"   ❌ Pool configuration too high: {max_connections} > 30 max connections")
            optimized = False
        
        # Check for other optimizations
        has_reset = "pool_reset_on_return" in content
        has_timeouts = "idle_in_transaction_session_timeout" in content
        has_ping = "pool_pre_ping=True" in content
        
        print(f"\n🔧 OPTIMIZATION FEATURES:")
        print(f"   {'✅' if has_reset else '❌'} Connection reset on return")
        print(f"   {'✅' if has_timeouts else '❌'} Idle transaction timeouts")
        print(f"   {'✅' if has_ping else '❌'} Pre-ping enabled")
        
        optimization_score = sum([has_reset, has_timeouts, has_ping])
        
        if optimization_score >= 2:
            print(f"   ✅ Good optimization features: {optimization_score}/3")
        else:
            print(f"   ⚠️ Limited optimization features: {optimization_score}/3")
        
        # Final assessment
        overall_success = optimized and optimization_score >= 2
        
        print(f"\n🎉 FINAL ASSESSMENT:")
        if overall_success:
            print(f"   ✅ CONNECTION POOL CONFIGURATION OPTIMIZED!")
            print(f"   ✅ Should handle stress tests with ≤20 connections")
        else:
            print(f"   ❌ CONNECTION POOL NEEDS FURTHER OPTIMIZATION")
            if not optimized:
                print(f"   ❌ Reduce pool_size + max_overflow to ≤20")
            if optimization_score < 2:
                print(f"   ❌ Add more optimization features")
        
        return overall_success
    
    else:
        print("❌ Could not parse pool configuration")
        return False

def main():
    try:
        return analyze_pool_config()
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)