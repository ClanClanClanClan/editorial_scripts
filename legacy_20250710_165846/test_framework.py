#!/usr/bin/env python3
"""
Comprehensive Test Framework - Tests parsing logic with mock data
This validates the core logic without needing real account access
"""

import unittest
import re
from bs4 import BeautifulSoup
import json
from pathlib import Path

class MockHTMLGenerator:
    """Generates mock HTML for testing different scenarios"""
    
    @staticmethod
    def generate_ae_center_page(journal_name, categories_with_counts):
        """Generate mock AE Center page with categories"""
        
        category_html = ""
        for category, count in categories_with_counts.items():
            category_html += f'''
            <tr>
                <td><a href="#{category.replace(' ', '_')}">{category}</a></td>
                <td>{count}</td>
            </tr>
            '''
            
        return f'''
        <html>
        <head><title>{journal_name} Associate Editor Center</title></head>
        <body>
            <h1>Associate Editor Center</h1>
            <p>You may click on the manuscript list title to view a full listing of manuscripts in each status, 
               or click on the number next to the list to jump directly to the first manuscript in the list.</p>
            
            <table>
                {category_html}
            </table>
            
            <div class="category-text">
                {"".join([f"{count}{category}" for category, count in categories_with_counts.items()])}
            </div>
        </body>
        </html>
        '''
    
    @staticmethod
    def generate_manuscript_list_page(journal_name, manuscripts_data):
        """Generate mock manuscript list page with referee information"""
        
        manuscript_rows = ""
        for ms_data in manuscripts_data:
            ms_id = ms_data['id']
            title = ms_data['title']
            referee_text = ms_data['referee_text']
            
            manuscript_rows += f'''
            <tr>
                <td class="tablelightcolor">
                    <p class="listcontents">{ms_id}</p>
                    <p class="listcontents">(REX-PROD-1-12345)</p>
                </td>
                <td class="tablelightcolor">
                    <p class="listcontents">{title} [<a href="#">View Submission</a>]</p>
                </td>
                <td class="tablelightcolor">
                    <p class="listcontents">15-Jan-2025</p>
                </td>
                <td class="tablelightcolor">
                    <p class="listcontents">
                        AE: Test, Author<br>
                        {referee_text}
                    </p>
                </td>
                <td class="tablelightcolor">
                    <input type="checkbox" />
                </td>
            </tr>
            '''
            
        return f'''
        <html>
        <head><title>{journal_name} Manuscript List</title></head>
        <body>
            <h1>Manuscript List</h1>
            <a href="#ae_center">Associate Editor Center</a>
            
            <table>
                <tr>
                    <th>Manuscript ID</th>
                    <th>Title</th>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Take Action</th>
                </tr>
                {manuscript_rows}
            </table>
        </body>
        </html>
        '''

class TestRefereeExtraction(unittest.TestCase):
    """Test referee information extraction logic"""
    
    def setUp(self):
        """Set up test cases"""
        self.mf_test_data = [
            {
                'id': 'MAFI-2024-0001',
                'title': 'Test Paper on Financial Mathematics',
                'referee_text': '2 active selections; 2 invited; 2 agreed; 1 declined; 0 returned'
            },
            {
                'id': 'MAFI-2025-0002', 
                'title': 'Another Financial Paper',
                'referee_text': '3 active selections; 3 invited; 1 agreed; 2 declined; 1 returned'
            }
        ]
        
        self.mor_test_data = [
            {
                'id': 'MOR-2023-0001',
                'title': 'Operations Research Study',
                'referee_text': '2 active selections; 2 invited; 2 agreed; 0 declined; 0 returned'
            },
            {
                'id': 'MOR-2024-0002',
                'title': 'Mathematical Operations Paper', 
                'referee_text': '1 active selections; 3 invited; 1 agreed; 2 declined; 1 returned'
            },
            {
                'id': 'MOR-2025-0003',
                'title': 'Advanced OR Methods',
                'referee_text': '2 active selections; 2 invited; 2 agreed; 1 declined; 0 returned'
            }
        ]
        
    def extract_referee_counts(self, referee_text):
        """Extract referee counts from text (mimics real extraction logic)"""
        active_match = re.search(r'(\d+)\s+active\s+selections', referee_text)
        invited_match = re.search(r'(\d+)\s+invited', referee_text)
        agreed_match = re.search(r'(\d+)\s+agreed', referee_text)
        declined_match = re.search(r'(\d+)\s+declined', referee_text)
        returned_match = re.search(r'(\d+)\s+returned', referee_text)
        
        return {
            'active_selections': int(active_match.group(1)) if active_match else 0,
            'invited': int(invited_match.group(1)) if invited_match else 0,
            'agreed': int(agreed_match.group(1)) if agreed_match else 0,
            'declined': int(declined_match.group(1)) if declined_match else 0,
            'returned': int(returned_match.group(1)) if returned_match else 0
        }
        
    def discover_categories_from_html(self, html_content):
        """Test category discovery logic"""
        soup = BeautifulSoup(html_content, 'html.parser')
        page_text = soup.get_text()
        
        categories_with_counts = []
        
        # Test the regex patterns used in real scraper
        category_patterns = [
            r'(\d+)\s*([A-Z][A-Za-z\s]+(?:Reviewer|Review|Awaiting|Overdue)[A-Za-z\s]*)',
            r'(\d+)\s*(Awaiting[A-Za-z\s]+)',
            r'(\d+)\s*(Overdue[A-Za-z\s]+)'
        ]
        
        for pattern in category_patterns:
            matches = re.findall(pattern, page_text)
            for count, category_name in matches:
                count = int(count)
                category_name = category_name.strip()
                
                if (count > 0 and 
                    len(category_name) > 5 and 
                    any(word in category_name.lower() for word in ['awaiting', 'overdue', 'reviewer', 'review'])):
                    
                    categories_with_counts.append({
                        'name': category_name,
                        'count': count
                    })
                    
        return categories_with_counts
        
    def test_mf_referee_extraction(self):
        """Test MF referee extraction"""
        print("\\n🧪 Testing MF referee extraction...")
        
        total_agreed = 0
        for ms_data in self.mf_test_data:
            counts = self.extract_referee_counts(ms_data['referee_text'])
            total_agreed += counts['agreed']
            print(f"  📄 {ms_data['id']}: {counts['agreed']} agreed referees")
            
        print(f"  📊 Total MF active referees: {total_agreed}")
        self.assertEqual(total_agreed, 3, "MF should have 3 total agreed referees")
        
    def test_mor_referee_extraction(self):
        """Test MOR referee extraction"""
        print("\\n🧪 Testing MOR referee extraction...")
        
        total_agreed = 0
        for ms_data in self.mor_test_data:
            counts = self.extract_referee_counts(ms_data['referee_text'])
            total_agreed += counts['agreed']
            print(f"  📄 {ms_data['id']}: {counts['agreed']} agreed referees")
            
        print(f"  📊 Total MOR active referees: {total_agreed}")
        self.assertEqual(total_agreed, 5, "MOR should have 5 total agreed referees")
        
    def test_category_discovery_mf(self):
        """Test category discovery for MF"""
        print("\\n🧪 Testing MF category discovery...")
        
        categories = {
            "Awaiting Reviewer Selection": 0,
            "Awaiting Reviewer Invitation": 0,
            "Awaiting Reviewer Scores": 2,
            "Overdue Reviewer Scores": 0,
            "Awaiting AE Recommendation": 0
        }
        
        html = MockHTMLGenerator.generate_ae_center_page("MF", categories)
        discovered = self.discover_categories_from_html(html)
        
        # Should only find categories with count > 0
        self.assertEqual(len(discovered), 1, "Should find only 1 category with manuscripts")
        self.assertEqual(discovered[0]['name'], "Awaiting Reviewer Scores")
        self.assertEqual(discovered[0]['count'], 2)
        
        print(f"  ✅ Discovered: {discovered}")
        
    def test_category_discovery_mor(self):
        """Test category discovery for MOR"""
        print("\\n🧪 Testing MOR category discovery...")
        
        categories = {
            "Awaiting Reviewer Selection": 0,
            "Awaiting Reviewer Invitation": 0,
            "Awaiting Reviewer Reports": 3,
            "Overdue Reviewer Reports": 0,
            "Awaiting AE Recommendation": 0
        }
        
        html = MockHTMLGenerator.generate_ae_center_page("MOR", categories)
        discovered = self.discover_categories_from_html(html)
        
        # Should only find categories with count > 0
        self.assertEqual(len(discovered), 1, "Should find only 1 category with manuscripts")
        self.assertEqual(discovered[0]['name'], "Awaiting Reviewer Reports")
        self.assertEqual(discovered[0]['count'], 3)
        
        print(f"  ✅ Discovered: {discovered}")
        
    def test_manuscript_parsing_mf(self):
        """Test manuscript parsing for MF"""
        print("\\n🧪 Testing MF manuscript parsing...")
        
        html = MockHTMLGenerator.generate_manuscript_list_page("MF", self.mf_test_data)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find manuscript IDs
        ms_ids = re.findall(r'MAFI-\d{4}-\d+', soup.get_text())
        self.assertEqual(len(ms_ids), 2, "Should find 2 MF manuscripts")
        
        print(f"  ✅ Found manuscripts: {ms_ids}")
        
    def test_manuscript_parsing_mor(self):
        """Test manuscript parsing for MOR"""
        print("\\n🧪 Testing MOR manuscript parsing...")
        
        html = MockHTMLGenerator.generate_manuscript_list_page("MOR", self.mor_test_data)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find manuscript IDs
        ms_ids = re.findall(r'MOR-\d{4}-\d+', soup.get_text())
        self.assertEqual(len(ms_ids), 3, "Should find 3 MOR manuscripts")
        
        print(f"  ✅ Found manuscripts: {ms_ids}")
        
    def test_edge_cases(self):
        """Test edge cases and robustness"""
        print("\\n🧪 Testing edge cases...")
        
        # Test empty referee text
        empty_counts = self.extract_referee_counts("")
        self.assertEqual(sum(empty_counts.values()), 0, "Empty text should give zero counts")
        
        # Test malformed referee text
        malformed_counts = self.extract_referee_counts("Some random text without patterns")
        self.assertEqual(sum(malformed_counts.values()), 0, "Malformed text should give zero counts")
        
        # Test unusual spacing
        spaced_text = "   2   active   selections  ;  2   invited  ;  1   agreed  "
        spaced_counts = self.extract_referee_counts(spaced_text)
        self.assertEqual(spaced_counts['agreed'], 1, "Should handle unusual spacing")
        
        print("  ✅ Edge cases handled correctly")

class TestScenarios(unittest.TestCase):
    """Test different scenarios that might occur"""
    
    def test_scenario_manuscripts_in_multiple_categories(self):
        """Test scenario where manuscripts exist in multiple categories"""
        print("\\n🧪 Testing multiple categories with manuscripts...")
        
        categories = {
            "Awaiting Reviewer Scores": 1,
            "Awaiting Reviewer Reports": 2,
            "Overdue Reviewer Scores": 1
        }
        
        html = MockHTMLGenerator.generate_ae_center_page("MF", categories)
        soup = BeautifulSoup(html, 'html.parser')
        
        # Simulate discovery
        tester = TestRefereeExtraction()
        discovered = tester.discover_categories_from_html(html)
        
        # Should find all categories with count > 0
        self.assertEqual(len(discovered), 3, "Should find 3 categories with manuscripts")
        
        total_manuscripts = sum(cat['count'] for cat in discovered)
        self.assertEqual(total_manuscripts, 4, "Should have 4 total manuscripts")
        
        print(f"  ✅ Would process {len(discovered)} categories with {total_manuscripts} manuscripts")
        
    def test_scenario_no_manuscripts(self):
        """Test scenario where no categories have manuscripts"""
        print("\\n🧪 Testing scenario with no manuscripts...")
        
        categories = {
            "Awaiting Reviewer Selection": 0,
            "Awaiting Reviewer Invitation": 0,
            "Awaiting Reviewer Scores": 0
        }
        
        html = MockHTMLGenerator.generate_ae_center_page("MF", categories)
        
        tester = TestRefereeExtraction()
        discovered = tester.discover_categories_from_html(html)
        
        self.assertEqual(len(discovered), 0, "Should find no categories with manuscripts")
        print("  ✅ Correctly handles empty state")

def run_comprehensive_tests():
    """Run all tests and generate report"""
    print("🚀 Running Comprehensive Test Framework")
    print("="*80)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add all test methods
    test_suite.addTest(TestRefereeExtraction('test_mf_referee_extraction'))
    test_suite.addTest(TestRefereeExtraction('test_mor_referee_extraction'))
    test_suite.addTest(TestRefereeExtraction('test_category_discovery_mf'))
    test_suite.addTest(TestRefereeExtraction('test_category_discovery_mor'))
    test_suite.addTest(TestRefereeExtraction('test_manuscript_parsing_mf'))
    test_suite.addTest(TestRefereeExtraction('test_manuscript_parsing_mor'))
    test_suite.addTest(TestRefereeExtraction('test_edge_cases'))
    test_suite.addTest(TestScenarios('test_scenario_manuscripts_in_multiple_categories'))
    test_suite.addTest(TestScenarios('test_scenario_no_manuscripts'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Generate summary
    print("\\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\\n❌ FAILURES:")
        for test, traceback in result.failures:
            print(f"  • {test}: {traceback}")
            
    if result.errors:
        print("\\n💥 ERRORS:")
        for test, traceback in result.errors:
            print(f"  • {test}: {traceback}")
            
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\\n📈 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 100:
        print("✅ ALL TESTS PASSED - Logic is robust!")
    elif success_rate >= 80:
        print("⚠️ MOSTLY PASSING - Some issues to address")
    else:
        print("❌ SIGNIFICANT ISSUES - Logic needs work")
        
    return result

if __name__ == "__main__":
    run_comprehensive_tests()