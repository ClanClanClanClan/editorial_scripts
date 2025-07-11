#!/usr/bin/env python3
"""
Test connection pool optimization under stress
"""

import sys
import time
import logging
import uuid
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import psutil

sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from src.api.main_simple import app

# Disable verbose logging
logging.getLogger('sqlalchemy').setLevel(logging.WARNING)

def generate_test_data():
    """Generate test data"""
    return {
        "name": f"Pool Test {uuid.uuid4().hex[:8]}",
        "email": f"pool_{uuid.uuid4().hex[:8]}@test.com",
        "institution": "Pool University",
        "time_metrics": {
            "avg_response_time": 3.5,
            "avg_review_time": 21.0,
            "fastest_review": 7.0,
            "slowest_review": 45.0,
            "response_time_std": 1.2,
            "review_time_std": 5.5,
            "on_time_rate": 0.85,
            "consistency_score": 0.8
        },
        "quality_metrics": {
            "avg_quality_score": 7.5,
            "quality_consistency": 0.8,
            "report_thoroughness": 0.85,
            "constructiveness_score": 8.0,
            "technical_accuracy": 7.8,
            "clarity_score": 8.2,
            "actionability_score": 7.6,
            "overall_quality": 7.8
        },
        "workload_metrics": {
            "current_reviews": 2,
            "completed_reviews_30d": 3,
            "completed_reviews_90d": 8,
            "completed_reviews_365d": 25,
            "monthly_average": 2.1,
            "peak_capacity": 5,
            "availability_score": 0.6,
            "burnout_risk_score": 0.3,
            "capacity_utilization": 0.4
        },
        "reliability_metrics": {
            "acceptance_rate": 0.75,
            "completion_rate": 0.92,
            "ghost_rate": 0.08,
            "decline_after_accept_rate": 0.03,
            "reminder_effectiveness": 0.85,
            "communication_score": 0.88,
            "excuse_frequency": 0.15,
            "reliability_score": 0.82
        },
        "expertise_metrics": {
            "expertise_areas": ["machine learning", "optimization"],
            "h_index": 25,
            "recent_publications": 5,
            "citation_count": 1200,
            "years_experience": 10,
            "expertise_score": 0.75
        }
    }

def stress_worker(worker_id, num_operations):
    """Worker for stress testing"""
    client = TestClient(app)
    results = {'success': 0, 'failures': 0, 'start_time': time.time()}
    
    for i in range(num_operations):
        try:
            if i % 3 == 0:
                # Create operation
                data = generate_test_data()
                response = client.post("/api/v1/referees/", json=data)
                if response.status_code == 201:
                    results['success'] += 1
                else:
                    results['failures'] += 1
            elif i % 3 == 1:
                # Stats operation
                response = client.get("/api/v1/referees/stats")
                if response.status_code == 200:
                    results['success'] += 1
                else:
                    results['failures'] += 1
            else:
                # Top performers
                response = client.get("/api/v1/referees/top-performers?limit=3")
                if response.status_code == 200:
                    results['success'] += 1
                else:
                    results['failures'] += 1
        except Exception:
            results['failures'] += 1
    
    results['end_time'] = time.time()
    results['duration'] = results['end_time'] - results['start_time']
    
    return results

def get_system_connections():
    """Get system connection count"""
    try:
        process = psutil.Process()
        return len(process.net_connections())
    except:
        return 0

def test_connection_pool():
    """Test optimized connection pool"""
    print("🔧 CONNECTION POOL OPTIMIZATION TEST")
    print("=" * 50)
    
    initial_connections = get_system_connections()
    print(f"📊 Initial connections: {initial_connections}")
    
    # Progressive load testing
    test_configs = [
        (2, 10),   # 2 workers, 10 ops each = 20 total ops
        (4, 15),   # 4 workers, 15 ops each = 60 total ops  
        (8, 20),   # 8 workers, 20 ops each = 160 total ops
    ]
    
    for num_workers, ops_per_worker in test_configs:
        total_ops = num_workers * ops_per_worker
        
        print(f"\n🚀 Testing {num_workers} workers × {ops_per_worker} ops = {total_ops} operations")
        
        start_time = time.time()
        start_connections = get_system_connections()
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [
                executor.submit(stress_worker, i, ops_per_worker)
                for i in range(num_workers)
            ]
            
            results = []
            for future in futures:
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    print(f"   ❌ Worker failed: {e}")
                    results.append({'success': 0, 'failures': 1, 'duration': 60})
        
        end_time = time.time()
        end_connections = get_system_connections()
        
        # Analyze results
        total_success = sum(r['success'] for r in results)
        total_failures = sum(r['failures'] for r in results)
        total_duration = end_time - start_time
        success_rate = total_success / (total_success + total_failures) if (total_success + total_failures) > 0 else 0
        throughput = (total_success + total_failures) / total_duration if total_duration > 0 else 0
        connection_growth = end_connections - start_connections
        
        print(f"   📈 Results:")
        print(f"      Success: {total_success}/{total_success + total_failures} ({success_rate*100:.1f}%)")
        print(f"      Throughput: {throughput:.1f} ops/sec")
        print(f"      Duration: {total_duration:.2f}s")
        print(f"      Connections: {start_connections} → {end_connections} (Δ{connection_growth:+d})")
        
        # Check if this configuration meets our criteria
        meets_criteria = (
            success_rate >= 0.95 and
            throughput >= 5.0 and
            end_connections <= 20  # Much stricter limit
        )
        
        status = "✅ PASS" if meets_criteria else "❌ FAIL"
        print(f"   {status}")
        
        if not meets_criteria:
            if success_rate < 0.95:
                print(f"      ❌ Success rate too low: {success_rate*100:.1f}% < 95%")
            if throughput < 5.0:
                print(f"      ❌ Throughput too low: {throughput:.1f} < 5.0 ops/sec")
            if end_connections > 20:
                print(f"      ❌ Too many connections: {end_connections} > 20")
        
        # Wait for connections to potentially close
        time.sleep(2)
        final_connections = get_system_connections()
        if final_connections < end_connections:
            print(f"      🔄 Connections cleaned up: {end_connections} → {final_connections}")
    
    final_connections = get_system_connections()
    total_connection_growth = final_connections - initial_connections
    
    print(f"\n🎯 FINAL ASSESSMENT:")
    print(f"   Initial connections: {initial_connections}")
    print(f"   Final connections: {final_connections}")
    print(f"   Net growth: {total_connection_growth:+d}")
    
    # Overall success criteria
    overall_success = total_connection_growth <= 15  # Allow some reasonable growth
    
    if overall_success:
        print(f"\n🎉 CONNECTION POOL OPTIMIZATION SUCCESSFUL!")
        print(f"✅ Connection growth controlled: {total_connection_growth:+d} ≤ 15")
    else:
        print(f"\n💥 CONNECTION POOL OPTIMIZATION FAILED!")
        print(f"❌ Too many connections created: {total_connection_growth:+d} > 15")
    
    return overall_success

def main():
    try:
        return test_connection_pool()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)