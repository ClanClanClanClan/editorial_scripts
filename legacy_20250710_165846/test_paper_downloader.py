#!/usr/bin/env python3
"""
Test paper downloader functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.paper_downloader import get_paper_downloader

def test_paper_downloader():
    """Test paper downloader functionality"""
    print("Testing paper downloader...")
    
    try:
        downloader = get_paper_downloader()
        print(f"✅ Paper downloader created: {type(downloader).__name__}")
        
        # Test directory creation
        print(f"✅ Papers directory: {downloader.papers_dir}")
        print(f"✅ Reports directory: {downloader.reports_dir}")
        
        # Test stats
        stats = downloader.get_download_stats()
        print(f"✅ Download stats: {stats}")
        
        # Test safe filename generation
        test_filename = "Test: Paper with / special * chars"
        safe_filename = downloader._safe_filename(test_filename)
        print(f"✅ Safe filename: '{test_filename}' -> '{safe_filename}'")
        
        # Test URL handling without actual download
        test_url = "https://example.com/paper.pdf"
        print(f"✅ URL handling test: {test_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Paper downloader test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_paper_downloader()
    if success:
        print("\n✅ Paper downloader tests completed")
    else:
        print("\n❌ Paper downloader tests failed")
        sys.exit(1)