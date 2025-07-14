"""
Performance benchmarking for AI services
Measures throughput, latency, and resource usage of AI pipeline components
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import psutil
import gc

from src.ai.services.ai_orchestrator_service import AIOrchestrator
from src.ai.services.async_openai_client import AsyncOpenAIClient
from src.ai.services.pypdf_processor import PyPDFProcessor


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark"""
    test_name: str
    total_operations: int
    total_time_seconds: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p95_latency_ms: float
    operations_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    errors: int = 0


class AIPerformanceBenchmark:
    """Performance benchmarking suite for AI services"""
    
    def __init__(self):
        self.results: List[BenchmarkResult] = []
    
    async def measure_operation(self, operation, *args, **kwargs):
        """Measure the performance of a single operation"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        start_time = time.perf_counter()
        start_cpu = process.cpu_percent()
        
        try:
            result = await operation(*args, **kwargs)
            error = False
        except Exception as e:
            result = None
            error = True
        
        end_time = time.perf_counter()
        end_cpu = process.cpu_percent()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        return {
            'result': result,
            'latency_ms': (end_time - start_time) * 1000,
            'memory_delta_mb': final_memory - initial_memory,
            'cpu_usage': (start_cpu + end_cpu) / 2,
            'error': error
        }
    
    async def benchmark_operation(
        self, 
        test_name: str,
        operation,
        num_operations: int = 100,
        *args, 
        **kwargs
    ) -> BenchmarkResult:
        """Benchmark a specific operation multiple times"""
        print(f"🏃 Running benchmark: {test_name} ({num_operations} operations)")
        
        latencies = []
        memory_usages = []
        cpu_usages = []
        errors = 0
        
        # Warm up
        await self.measure_operation(operation, *args, **kwargs)
        gc.collect()
        
        start_time = time.perf_counter()
        
        # Run benchmark
        for i in range(num_operations):
            if i % 10 == 0:
                print(f"  Progress: {i}/{num_operations}")
            
            result = await self.measure_operation(operation, *args, **kwargs)
            
            latencies.append(result['latency_ms'])
            memory_usages.append(result['memory_delta_mb'])
            cpu_usages.append(result['cpu_usage'])
            
            if result['error']:
                errors += 1
        
        total_time = time.perf_counter() - start_time
        
        # Calculate statistics
        benchmark_result = BenchmarkResult(
            test_name=test_name,
            total_operations=num_operations,
            total_time_seconds=total_time,
            avg_latency_ms=statistics.mean(latencies),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            p95_latency_ms=statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else max(latencies),
            operations_per_second=num_operations / total_time,
            memory_usage_mb=statistics.mean(memory_usages),
            cpu_usage_percent=statistics.mean(cpu_usages),
            errors=errors
        )
        
        self.results.append(benchmark_result)
        print(f"✅ Completed: {test_name}")
        print(f"   Avg latency: {benchmark_result.avg_latency_ms:.1f}ms")
        print(f"   Throughput: {benchmark_result.operations_per_second:.1f} ops/sec")
        print(f"   Errors: {errors}")
        
        return benchmark_result
    
    def print_report(self):
        """Print comprehensive benchmark report"""
        print("\n" + "="*80)
        print("🚀 AI SERVICES PERFORMANCE BENCHMARK REPORT")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total tests: {len(self.results)}")
        print()
        
        for result in self.results:
            print(f"📊 {result.test_name}")
            print(f"   Operations: {result.total_operations}")
            print(f"   Total time: {result.total_time_seconds:.2f}s")
            print(f"   Avg latency: {result.avg_latency_ms:.1f}ms")
            print(f"   P95 latency: {result.p95_latency_ms:.1f}ms")
            print(f"   Throughput: {result.operations_per_second:.1f} ops/sec")
            print(f"   Memory usage: {result.memory_usage_mb:.1f}MB")
            print(f"   CPU usage: {result.cpu_usage_percent:.1f}%")
            print(f"   Error rate: {result.errors/result.total_operations*100:.1f}%")
            print()
    
    def save_report(self, filename: str):
        """Save benchmark results to file"""
        with open(filename, 'w') as f:
            f.write("AI Services Performance Benchmark Report\n")
            f.write("="*50 + "\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n\n")
            
            for result in self.results:
                f.write(f"Test: {result.test_name}\n")
                f.write(f"Operations: {result.total_operations}\n")
                f.write(f"Total time: {result.total_time_seconds:.2f}s\n")
                f.write(f"Avg latency: {result.avg_latency_ms:.1f}ms\n")
                f.write(f"P95 latency: {result.p95_latency_ms:.1f}ms\n")
                f.write(f"Throughput: {result.operations_per_second:.1f} ops/sec\n")
                f.write(f"Memory usage: {result.memory_usage_mb:.1f}MB\n")
                f.write(f"CPU usage: {result.cpu_usage_percent:.1f}%\n")
                f.write(f"Error rate: {result.errors/result.total_operations*100:.1f}%\n")
                f.write("-" * 30 + "\n")


# Mock implementations for benchmarking
class MockAIClient:
    """Mock AI client for performance testing"""
    
    async def analyze_desk_rejection(self, *args, **kwargs):
        # Simulate API latency
        await asyncio.sleep(0.1 + 0.05 * (hash(str(args)) % 10) / 10)
        from src.ai.models.manuscript_analysis import DeskRejectionAnalysis, AnalysisRecommendation
        return DeskRejectionAnalysis(
            recommendation=AnalysisRecommendation.ACCEPT_FOR_REVIEW,
            confidence=0.85,
            rejection_reasons=[],
            quality_issues=[],
            detailed_feedback="Mock analysis result"
        )
    
    async def recommend_referees(self, *args, **kwargs):
        # Simulate API latency
        await asyncio.sleep(0.15 + 0.05 * (hash(str(args)) % 10) / 10)
        from src.ai.models.manuscript_analysis import RefereeRecommendation
        return [
            RefereeRecommendation(
                referee_name=f"Mock Referee {i}",
                expertise_match=0.8 + 0.1 * i,
                availability_score=0.9,
                quality_score=0.85,
                workload_score=0.75,
                overall_score=0.82 + 0.05 * i,
                expertise_areas=["optimization", "analysis"],
                rationale=f"Mock rationale {i}"
            )
            for i in range(3)
        ]


class MockPDFProcessor:
    """Mock PDF processor for performance testing"""
    
    async def extract_text_content(self, *args, **kwargs):
        # Simulate processing time
        await asyncio.sleep(0.05)
        return {
            'title': 'Mock Title',
            'abstract': 'Mock abstract content',
            'full_text': 'Mock full text content',
            'sections': {'intro': 'Mock introduction'}
        }


@pytest.fixture
def benchmark_suite():
    """Create benchmark suite"""
    return AIPerformanceBenchmark()


@pytest.fixture
def mock_orchestrator():
    """Create AI orchestrator with mock dependencies"""
    return AIOrchestrator(
        ai_client=MockAIClient(),
        pdf_processor=MockPDFProcessor(),
        cache_enabled=False
    )


class TestAIPerformanceBenchmarks:
    """AI service performance benchmark tests"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_desk_rejection_analysis_performance(self, benchmark_suite, mock_orchestrator):
        """Benchmark desk rejection analysis performance"""
        await benchmark_suite.benchmark_operation(
            "Desk Rejection Analysis",
            mock_orchestrator.analyze_desk_rejection,
            50,  # Number of operations
            title="Test Manuscript",
            abstract="Test abstract for performance benchmarking",
            journal_code="SICON"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_referee_recommendation_performance(self, benchmark_suite, mock_orchestrator):
        """Benchmark referee recommendation performance"""
        await benchmark_suite.benchmark_operation(
            "Referee Recommendation",
            mock_orchestrator.recommend_referees,
            30,  # Number of operations
            title="Test Manuscript",
            abstract="Test abstract for performance benchmarking",
            journal_code="SICON",
            count=5
        )
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_comprehensive_analysis_performance(self, benchmark_suite, mock_orchestrator):
        """Benchmark full comprehensive analysis performance"""
        await benchmark_suite.benchmark_operation(
            "Comprehensive Analysis",
            mock_orchestrator.analyze_manuscript_comprehensive,
            20,  # Number of operations
            manuscript_id="PERF-TEST",
            journal_code="SICON",
            title="Performance Test Manuscript",
            abstract="This manuscript is being used for performance testing"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_load_performance(self, benchmark_suite, mock_orchestrator):
        """Test performance under concurrent load"""
        async def concurrent_analysis():
            tasks = []
            for i in range(10):  # 10 concurrent requests
                task = mock_orchestrator.analyze_desk_rejection(
                    title=f"Concurrent Test {i}",
                    abstract=f"Abstract {i}",
                    journal_code="SICON"
                )
                tasks.append(task)
            await asyncio.gather(*tasks)
        
        await benchmark_suite.benchmark_operation(
            "Concurrent Load (10 simultaneous)",
            concurrent_analysis,
            10  # 10 batches of concurrent requests
        )
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_caching_performance_impact(self, benchmark_suite):
        """Compare performance with and without caching"""
        # Without caching
        orchestrator_no_cache = AIOrchestrator(
            ai_client=MockAIClient(),
            pdf_processor=MockPDFProcessor(),
            cache_enabled=False
        )
        
        await benchmark_suite.benchmark_operation(
            "Analysis (No Cache)",
            orchestrator_no_cache.analyze_desk_rejection,
            20,
            title="Cache Test",
            abstract="Testing cache performance impact",
            journal_code="SICON"
        )
        
        # With caching
        orchestrator_with_cache = AIOrchestrator(
            ai_client=MockAIClient(),
            pdf_processor=MockPDFProcessor(),
            cache_enabled=True
        )
        
        await benchmark_suite.benchmark_operation(
            "Analysis (With Cache)",
            orchestrator_with_cache.analyze_desk_rejection,
            20,
            title="Cache Test",
            abstract="Testing cache performance impact",
            journal_code="SICON"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_memory_usage_over_time(self, benchmark_suite, mock_orchestrator):
        """Test memory usage patterns over extended operation"""
        print("🧠 Testing memory usage patterns...")
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # Run many operations to test for memory leaks
        for batch in range(5):
            print(f"  Memory test batch {batch + 1}/5")
            
            tasks = []
            for i in range(20):
                task = mock_orchestrator.analyze_desk_rejection(
                    title=f"Memory Test {batch}-{i}",
                    abstract=f"Memory test abstract {i}",
                    journal_code="SICON"
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Force garbage collection
            gc.collect()
            
            current_memory = process.memory_info().rss / 1024 / 1024
            print(f"    Memory usage: {current_memory:.1f}MB (delta: {current_memory - initial_memory:.1f}MB)")
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"🔍 Memory analysis:")
        print(f"   Initial: {initial_memory:.1f}MB")
        print(f"   Final: {final_memory:.1f}MB")
        print(f"   Increase: {memory_increase:.1f}MB")
        
        # Assert reasonable memory usage (< 100MB increase)
        assert memory_increase < 100, f"Memory increase too high: {memory_increase:.1f}MB"
    
    def test_benchmark_report_generation(self, benchmark_suite):
        """Test benchmark report generation"""
        # Add some mock results
        benchmark_suite.results.append(
            BenchmarkResult(
                test_name="Test Operation",
                total_operations=100,
                total_time_seconds=10.0,
                avg_latency_ms=100.0,
                min_latency_ms=50.0,
                max_latency_ms=200.0,
                p95_latency_ms=180.0,
                operations_per_second=10.0,
                memory_usage_mb=50.0,
                cpu_usage_percent=25.0
            )
        )
        
        # Test report generation
        benchmark_suite.print_report()
        
        # Test saving report
        benchmark_suite.save_report("/tmp/test_benchmark_report.txt")


# Performance thresholds for regression testing
PERFORMANCE_THRESHOLDS = {
    'desk_rejection_avg_latency_ms': 500,  # Max 500ms average
    'desk_rejection_p95_latency_ms': 1000,  # Max 1s P95
    'desk_rejection_min_throughput': 2,  # Min 2 ops/sec
    
    'referee_recommendation_avg_latency_ms': 750,  # Max 750ms average
    'referee_recommendation_p95_latency_ms': 1500,  # Max 1.5s P95
    'referee_recommendation_min_throughput': 1.5,  # Min 1.5 ops/sec
    
    'comprehensive_analysis_avg_latency_ms': 1200,  # Max 1.2s average
    'comprehensive_analysis_p95_latency_ms': 2000,  # Max 2s P95
    'comprehensive_analysis_min_throughput': 0.8,  # Min 0.8 ops/sec
}


def check_performance_regression(results: List[BenchmarkResult]):
    """Check if performance meets expected thresholds"""
    issues = []
    
    for result in results:
        test_name = result.test_name.lower().replace(" ", "_")
        
        # Check average latency
        threshold_key = f"{test_name}_avg_latency_ms"
        if threshold_key in PERFORMANCE_THRESHOLDS:
            if result.avg_latency_ms > PERFORMANCE_THRESHOLDS[threshold_key]:
                issues.append(f"{result.test_name}: Avg latency {result.avg_latency_ms:.1f}ms > {PERFORMANCE_THRESHOLDS[threshold_key]}ms")
        
        # Check P95 latency
        threshold_key = f"{test_name}_p95_latency_ms"
        if threshold_key in PERFORMANCE_THRESHOLDS:
            if result.p95_latency_ms > PERFORMANCE_THRESHOLDS[threshold_key]:
                issues.append(f"{result.test_name}: P95 latency {result.p95_latency_ms:.1f}ms > {PERFORMANCE_THRESHOLDS[threshold_key]}ms")
        
        # Check throughput
        threshold_key = f"{test_name}_min_throughput"
        if threshold_key in PERFORMANCE_THRESHOLDS:
            if result.operations_per_second < PERFORMANCE_THRESHOLDS[threshold_key]:
                issues.append(f"{result.test_name}: Throughput {result.operations_per_second:.1f} ops/sec < {PERFORMANCE_THRESHOLDS[threshold_key]} ops/sec")
    
    return issues


if __name__ == "__main__":
    # Run benchmarks directly
    async def run_benchmarks():
        benchmark = AIPerformanceBenchmark()
        orchestrator = AIOrchestrator(
            ai_client=MockAIClient(),
            pdf_processor=MockPDFProcessor(),
            cache_enabled=False
        )
        
        print("🚀 Starting AI Performance Benchmarks...")
        
        # Run core benchmarks
        await benchmark.benchmark_operation(
            "Desk Rejection Analysis",
            orchestrator.analyze_desk_rejection,
            50,
            title="Benchmark Test",
            abstract="Performance testing abstract",
            journal_code="SICON"
        )
        
        await benchmark.benchmark_operation(
            "Referee Recommendation",
            orchestrator.recommend_referees,
            30,
            title="Benchmark Test",
            abstract="Performance testing abstract",
            journal_code="SICON",
            count=5
        )
        
        benchmark.print_report()
        
        # Check for regressions
        issues = check_performance_regression(benchmark.results)
        if issues:
            print("\n⚠️ Performance Issues Detected:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ All performance benchmarks passed!")
    
    asyncio.run(run_benchmarks())