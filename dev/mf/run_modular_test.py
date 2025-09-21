#!/usr/bin/env python3
"""
Development runner for testing modular MF extractor
All outputs contained in dev/mf/outputs/
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from extractors.mf_modular import MFExtractor

def main():
    print("🧪 Testing Modular MF Extractor")
    print("=" * 50)
    
    # Ensure output directory exists
    output_dir = os.path.join(os.path.dirname(__file__), 'outputs')
    os.makedirs(output_dir, exist_ok=True)
    
    # Run extraction with limited manuscripts for testing
    with MFExtractor(headless=False, save_dir=output_dir) as extractor:
        try:
            result = extractor.extract_all(max_manuscripts=1)
            
            if result.success:
                filepath = extractor.save_results()
                summary = extractor.get_extraction_summary()
                
                print(f"\n🎉 Modular extraction test completed!")
                print(f"📄 Manuscripts: {summary['manuscripts']}")
                print(f"🧑‍⚖️ Referees: {summary['referees']['total']} ({summary['referees']['with_email']} emails)")
                print(f"✍️ Authors: {summary['authors']['total']} ({summary['authors']['with_email']} emails)")
                print(f"📧 Total emails: {summary['total_emails']}")
                print(f"💾 Results saved: {filepath}")
                
                # Show validation report
                from extractors.mf_modular.utils.data_models import validate_extracted_data
                validation = validate_extracted_data(extractor.manuscripts)
                print(f"\n📊 Validation Report:")
                print(f"  Valid manuscripts: {validation['valid_manuscripts']}/{validation['total_manuscripts']}")
                if validation['summary']['total_referees'] > 0:
                    print(f"  Referee email rate: {validation['summary'].get('referee_email_rate', 0):.1f}%")
                if validation['summary']['total_authors'] > 0:
                    print(f"  Author email rate: {validation['summary'].get('author_email_rate', 0):.1f}%")
            else:
                print(f"\n❌ Modular extraction test failed: {result.message}")
                if result.errors:
                    print("Errors:")
                    for error in result.errors:
                        print(f"  - {error}")
                        
        except Exception as e:
            print(f"\n💥 Test error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()