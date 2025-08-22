"""Tests for text processing utilities."""

import pytest
from src.ecc.utils.text_processing import (
    normalize_name,
    is_same_person_name,
    parse_affiliation_string,
    extract_email_domain,
    infer_institution_from_email,
    clean_text,
    similarity_score
)


class TestNormalizeName:
    """Test name normalization."""
    
    def test_last_first_format(self):
        """Test converting Last, First to First Last."""
        assert normalize_name("Smith, John") == "John Smith"
        assert normalize_name("Doe, Jane Mary") == "Jane Mary Doe"
    
    def test_already_normalized(self):
        """Test names already in correct format."""
        assert normalize_name("John Smith") == "John Smith"
        assert normalize_name("Jane Mary Doe") == "Jane Mary Doe"
    
    def test_whitespace_handling(self):
        """Test handling of extra whitespace."""
        assert normalize_name("  Smith , John  ") == "John Smith"
        assert normalize_name("  John   Smith  ") == "John   Smith"  # Preserves internal spacing
    
    def test_edge_cases(self):
        """Test edge cases."""
        assert normalize_name("") == ""
        assert normalize_name(None) == ""
        assert normalize_name("Smith") == "Smith"


class TestIsSamePersonName:
    """Test name matching."""
    
    def test_exact_match(self):
        """Test exact name matches."""
        assert is_same_person_name("John Smith", "John Smith") == True
        assert is_same_person_name("Jane Doe", "Jane Doe") == True
    
    def test_format_variations(self):
        """Test different name formats."""
        assert is_same_person_name("John Smith", "Smith, John") == True
        assert is_same_person_name("Smith, John", "John Smith") == True
    
    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert is_same_person_name("John Smith", "john smith") == True
        assert is_same_person_name("JOHN SMITH", "John Smith") == True
    
    def test_initials(self):
        """Test handling of initials."""
        assert is_same_person_name("J. Smith", "John Smith") == True
        assert is_same_person_name("John Smith", "J. Smith") == True
        assert is_same_person_name("J Smith", "John Smith") == True
    
    def test_middle_names(self):
        """Test middle names and initials."""
        assert is_same_person_name("John A. Smith", "John Smith") == True
        assert is_same_person_name("John Smith", "John A. Smith") == True
    
    def test_different_people(self):
        """Test names that don't match."""
        assert is_same_person_name("John Smith", "Jane Smith") == False
        assert is_same_person_name("John Smith", "John Doe") == False
        assert is_same_person_name("J. Smith", "K. Smith") == False
    
    def test_edge_cases(self):
        """Test edge cases."""
        assert is_same_person_name("", "John Smith") == False
        assert is_same_person_name("John Smith", "") == False
        assert is_same_person_name(None, "John Smith") == False


class TestParseAffiliationString:
    """Test affiliation parsing."""
    
    def test_simple_institution(self):
        """Test simple institution name."""
        result = parse_affiliation_string("MIT")
        assert result['institution'] == "MIT"
    
    def test_full_affiliation(self):
        """Test complete affiliation string."""
        result = parse_affiliation_string("MIT, Department of Mathematics, Cambridge, MA, USA")
        assert result['institution'] == "MIT"
        assert result['department'] == "Department of Mathematics"
        assert result['country'] == "USA"
    
    def test_country_detection(self):
        """Test country extraction."""
        assert parse_affiliation_string("Oxford, UK")['country'] == "UK"
        assert parse_affiliation_string("ETH Zurich, Switzerland")['country'] == "Switzerland"
        assert parse_affiliation_string("Sorbonne, Paris, France")['country'] == "France"
    
    def test_department_detection(self):
        """Test department extraction."""
        result = parse_affiliation_string("Stanford, School of Engineering")
        assert result['department'] == "School of Engineering"
        
        result = parse_affiliation_string("Harvard, Dept of Economics")
        assert result['department'] == "Dept of Economics"
    
    def test_edge_cases(self):
        """Test edge cases."""
        assert parse_affiliation_string("") == {}
        assert parse_affiliation_string(None) == {}


class TestEmailProcessing:
    """Test email-related functions."""
    
    def test_extract_domain(self):
        """Test domain extraction."""
        assert extract_email_domain("john@mit.edu") == "mit.edu"
        assert extract_email_domain("jane.doe@stanford.edu") == "stanford.edu"
        assert extract_email_domain("user@sub.domain.com") == "sub.domain.com"
    
    def test_extract_domain_invalid(self):
        """Test invalid email handling."""
        assert extract_email_domain("not-an-email") == None
        assert extract_email_domain("") == None
        assert extract_email_domain(None) == None
    
    def test_infer_institution(self):
        """Test institution inference from email."""
        assert infer_institution_from_email("john@mit.edu") == "Massachusetts Institute of Technology"
        assert infer_institution_from_email("jane@stanford.edu") == "Stanford University"
        assert infer_institution_from_email("prof@cam.ac.uk") == "University of Cambridge"
        assert infer_institution_from_email("student@ethz.ch") == "ETH Zurich"
    
    def test_infer_unknown_institution(self):
        """Test inference for unknown domains."""
        # Should try to guess from domain
        result = infer_institution_from_email("user@northwestern.edu")
        assert result == "Northwestern University"
        
        result = infer_institution_from_email("admin@unknown.edu")
        assert result == "Unknown University"


class TestTextCleaning:
    """Test text cleaning utilities."""
    
    def test_clean_text(self):
        """Test text cleaning."""
        assert clean_text("  Multiple   spaces  ") == "Multiple spaces"
        assert clean_text("Line\nbreaks\r\nand\ttabs") == "Line breaks and tabs"
        assert clean_text("   ") == ""
    
    def test_clean_text_edge_cases(self):
        """Test edge cases."""
        assert clean_text("") == ""
        assert clean_text(None) == ""
        assert clean_text("Normal text") == "Normal text"


class TestSimilarityScore:
    """Test string similarity calculation."""
    
    def test_exact_match(self):
        """Test exact matches."""
        assert similarity_score("John Smith", "John Smith") == 1.0
        assert similarity_score("test", "test") == 1.0
    
    def test_similar_strings(self):
        """Test similar strings."""
        assert similarity_score("John Smith", "Jon Smith") > 0.8
        assert similarity_score("MIT", "M.I.T.") > 0.5
    
    def test_different_strings(self):
        """Test different strings."""
        assert similarity_score("John", "Jane") <= 0.5
        assert similarity_score("MIT", "Stanford") < 0.3
    
    def test_case_insensitive(self):
        """Test case insensitivity."""
        assert similarity_score("john smith", "JOHN SMITH") == 1.0
    
    def test_edge_cases(self):
        """Test edge cases."""
        assert similarity_score("", "test") == 0.0
        assert similarity_score("test", "") == 0.0
        assert similarity_score(None, "test") == 0.0