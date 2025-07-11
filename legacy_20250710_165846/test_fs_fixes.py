#!/usr/bin/env python3
"""
Test script to verify FS journal fixes for PDF parsing and referee detection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from journals.fs import improve_sentence_case, parse_pdf_title_author_fallback

def test_sentence_case():
    """Test sentence case conversion"""
    print("Testing sentence case conversion...")
    
    test_cases = [
        ("ENTROPY-REGULARIZED MEAN-VARIANCE PORTFOLIO OPTIMIZATION WITH JUMPS", 
         "Entropy-regularized Mean-variance Portfolio Optimization with Jumps"),
        ("A STUDY OF MACHINE LEARNING AND ARTIFICIAL INTELLIGENCE", 
         "A Study of Machine Learning and Artificial Intelligence"),
        ("THE IMPACT OF COVID-19 ON FINANCIAL MARKETS", 
         "The Impact of Covid-19 on Financial Markets"),
        ("PORTFOLIO OPTIMIZATION WITH TRANSACTION COSTS", 
         "Portfolio Optimization with Transaction Costs")
    ]
    
    for input_title, expected in test_cases:
        result = improve_sentence_case(input_title)
        print(f"Input:    {input_title}")
        print(f"Expected: {expected}")
        print(f"Got:      {result}")
        print(f"Match:    {'✅' if result == expected else '❌'}")
        print()

def test_report_detection():
    """Test report submission detection patterns"""
    print("Testing report submission detection...")
    
    # Test email body samples
    test_bodies = [
        "Dear Dylan, I have completed my review and my report is attached. Best regards, Xuefeng",
        "Hi Dylan, Please find my report attached. The paper has been reviewed thoroughly.",
        "Dear Editor, I am submitting my report for the manuscript. Thank you.",
        "Hello, I finished my review and the report is complete. Attached is my assessment.",
        "Dear Dylan, I accept the invitation to review this paper and will complete it soon.",
        "Hi, I am happy to review this manuscript. I will get back to you within 6 weeks."
    ]
    
    report_completion_phrases = [
        "report submitted", "report completed", "review submitted", "review completed",
        "my report", "attached report", "report attached", "submitted my report",
        "completed my review", "finished my review", "review is complete",
        "report is complete", "please find my report", "here is my report",
        "my review is attached", "report is attached", "sending my report",
        "submitting my report", "final report", "review report", "referee report"
    ]
    
    acceptance_phrases = [
        "i accept", "i am happy to", "i will review", "i agree to",
        "i would be happy to", "i can review", "i'll review",
        "yes, i will", "yes i will", "happy to review",
        "agree to review", "willing to review", "pleased to review",
        "i am willing", "i'd be happy", "count me in",
        "i accept the invitation", "accept your invitation",
        "yes i can", "sure i will", "i'll be happy", "i'm happy to"
    ]
    
    for i, body in enumerate(test_bodies, 1):
        print(f"Test Body {i}: {body}")
        
        # Check for report completion
        report_found = False
        for phrase in report_completion_phrases:
            if phrase in body.lower():
                print(f"  ✅ Found report completion phrase: '{phrase}'")
                report_found = True
                break
        
        if not report_found:
            # Check for acceptance
            for phrase in acceptance_phrases:
                if phrase in body.lower():
                    print(f"  📝 Found acceptance phrase: '{phrase}'")
                    break
            else:
                print(f"  ❌ No relevant phrases found")
        
        print()

def test_title_extraction():
    """Test title extraction improvements"""
    print("Testing title extraction improvements...")
    
    # Simulate PDF lines that would be processed
    sample_lines = [
        "ENTROPY-REGULARIZED MEAN-VARIANCE PORTFOLIO",
        "OPTIMIZATION WITH JUMPS",
        "",
        "Xuefeng Gao",
        "Department of Finance",
        "Chinese University of Hong Kong"
    ]
    
    print("Sample PDF lines:")
    for i, line in enumerate(sample_lines):
        print(f"  {i}: {line}")
    
    # Import the plausible_human_name function for testing
    from journals.fs import plausible_human_name
    
    # Simulate the improved title extraction logic
    title_lines = []
    for idx, line in enumerate(sample_lines):
        line_clean = line.strip()
        if not line_clean:
            continue
        
        # Check if this looks like a title line (uppercase or title case, not author-like)
        if (line_clean.isupper() or (line_clean and line_clean[0].isupper() and not any(c.isdigit() or c == '@' for c in line_clean) and len(line_clean) > 10)):
            # Don't include lines that look like author names
            if not plausible_human_name(line_clean):
                if len(title_lines) < 5:  # Allow up to 5 lines for title
                    title_lines.append(line_clean)
                continue
            else:
                # If we encounter an author name, stop collecting title lines
                break
        else:
            break
    
    title = " ".join(title_lines).replace("  ", " ").strip(" :;")
    if title.isupper():
        title = title.title()
    title = improve_sentence_case(title)
    
    print(f"\nExtracted title: {title}")
    print(f"Expected: Entropy-regularized Mean-variance Portfolio Optimization with Jumps")
    print(f"Match: {'✅' if 'Optimization with Jumps' in title else '❌'}")

def main():
    """Run all tests"""
    print("🔍 Testing FS Journal Fixes")
    print("=" * 50)
    
    test_sentence_case()
    test_report_detection()
    test_title_extraction()
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    main()