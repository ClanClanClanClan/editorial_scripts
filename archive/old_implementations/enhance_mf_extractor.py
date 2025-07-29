#!/usr/bin/env python3
"""
Enhance MF Extractor
====================

This script demonstrates how to enhance the MF extractor with:
1. Better referee affiliation extraction and cross-checking
2. Improved cover letter download handling

Run this after the main MF extraction to enhance the data.
"""

import json
import sys
from pathlib import Path

# Add current directory to path
sys.path.append('.')

from core.affiliation_crosscheck import affiliation_checker
from core.enhanced_cover_letter_downloader import EnhancedCoverLetterDownloader


def enhance_mf_results(results_file: str) -> str:
    """
    Enhance MF extraction results with cross-checked affiliations.
    
    Args:
        results_file: Path to the MF extraction JSON file
        
    Returns:
        Path to enhanced results file
    """
    print("🔧 Enhancing MF Extraction Results")
    print("=" * 60)
    
    # Load results
    with open(results_file) as f:
        data = json.load(f)
    
    print(f"📄 Loaded {len(data)} manuscripts")
    
    # Enhance each manuscript
    total_referees = 0
    enhanced_referees = 0
    
    for manuscript in data:
        print(f"\n📋 Processing {manuscript['id']}")
        
        # Enhance referee data
        for referee in manuscript.get('referees', []):
            total_referees += 1
            original_affiliation = referee.get('affiliation', '')
            
            # Apply cross-checking
            enhanced_referee = affiliation_checker.enhance_referee_data(referee)
            
            # Check if we added new data
            if enhanced_referee.get('institution') and (
                not original_affiliation or 
                original_affiliation == referee['name']
            ):
                enhanced_referees += 1
                print(f"   ✅ Enhanced {referee['name']}:")
                print(f"      Institution: {enhanced_referee.get('institution')}")
                print(f"      Source: {enhanced_referee.get('institution_source')}")
                if enhanced_referee.get('country'):
                    print(f"      Country: {enhanced_referee['country']}")
                if enhanced_referee.get('department'):
                    print(f"      Department: {enhanced_referee['department']}")
                    
        # Note about cover letters
        cover_letter_path = manuscript.get('documents', {}).get('cover_letter_path')
        if cover_letter_path and cover_letter_path.endswith('.txt'):
            print(f"   ℹ️ Cover letter saved as text: {cover_letter_path}")
            print(f"      (PDF/DOCX download may require manual intervention)")
    
    # Save enhanced results
    output_file = Path(results_file).stem + "_enhanced.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\n📊 Enhancement Summary:")
    print(f"   Total referees: {total_referees}")
    print(f"   Enhanced affiliations: {enhanced_referees}")
    print(f"   Enhancement rate: {enhanced_referees/total_referees*100:.1f}%")
    print(f"\n💾 Enhanced results saved to: {output_file}")
    
    return output_file


def demonstrate_cover_letter_fix():
    """
    Demonstrate how to integrate the enhanced cover letter downloader.
    
    This would be integrated into the MF extractor's download_cover_letter method.
    """
    print("\n📄 Enhanced Cover Letter Download Strategy")
    print("=" * 60)
    
    print("\nTo integrate into MF extractor, replace the download_cover_letter method:")
    print("""
    def download_cover_letter(self, cover_link, manuscript_id):
        '''Enhanced cover letter download.'''
        from core.enhanced_cover_letter_downloader import EnhancedCoverLetterDownloader
        
        downloader = EnhancedCoverLetterDownloader(self.driver)
        return downloader.download_cover_letter(cover_link, manuscript_id)
    """)
    
    print("\nThe enhanced downloader will:")
    print("1. ✅ Try multiple strategies to find download buttons")
    print("2. ✅ Handle embedded viewers and iframes")
    print("3. ✅ Download actual PDF/DOCX files when available")
    print("4. ✅ Fall back to text extraction only as last resort")


def main():
    """Main enhancement demonstration."""
    print("MF Extractor Enhancement Tool")
    print("=============================\n")
    
    # Check if filename provided as argument
    if len(sys.argv) > 1:
        results_file = sys.argv[1]
        if not Path(results_file).exists():
            print(f"❌ File not found: {results_file}")
            return
        latest_results = Path(results_file)
    else:
        # Find latest MF results
        results_files = list(Path(".").glob("mf_comprehensive_*.json"))
        
        if not results_files:
            print("❌ No MF extraction results found")
            print("   Run the MF extractor first: python3 run_production_mf_extractor.py")
            return
        
        # Use most recent file
        latest_results = max(results_files, key=lambda f: f.stat().st_mtime)
    
    print(f"📄 Using results file: {latest_results}")
    
    # Enhance the results
    enhanced_file = enhance_mf_results(str(latest_results))
    
    # Show cover letter fix
    demonstrate_cover_letter_fix()
    
    print("\n✅ Enhancement complete!")
    print("\nNext steps:")
    print("1. Review the enhanced data in:", enhanced_file)
    print("2. Consider integrating these enhancements into the main MF extractor")
    print("3. Test the enhanced cover letter downloader with live extraction")


if __name__ == "__main__":
    main()