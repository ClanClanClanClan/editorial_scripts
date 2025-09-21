#!/usr/bin/env python3
"""
Run MOR extractor to test all capabilities
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add production path
sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

# Import MOR extractor
from extractors.mor_extractor import MORExtractor

def test_mor_extraction():
    """Test MOR extraction with all capabilities"""
    print("\n" + "="*60)
    print("TESTING MOR EXTRACTOR WITH ALL CAPABILITIES")
    print("="*60)
    
    extractor = None
    try:
        # Initialize extractor
        print("\n🚀 Initializing MOR extractor...")
        extractor = MORExtractor(
            use_cache=True,
            cache_ttl_hours=24
        )
        
        # Test login
        print("\n🔐 Testing login with 2FA...")
        if extractor.login():
            print("✅ Login successful!")
            
            # Run extraction
            print("\n📊 Extracting all manuscripts...")
            results = extractor.extract_all_manuscripts()
            
            # Analyze results
            if results and 'manuscripts' in results:
                num_manuscripts = len(results['manuscripts'])
                print(f"\n📝 Found {num_manuscripts} manuscript(s)")
                
                # Check capabilities used
                capabilities_found = {
                    "referees_with_emails": False,
                    "authors_with_orcid": False,
                    "documents_downloaded": False,
                    "audit_trail_extracted": False,
                    "version_history": False,
                    "enhanced_status": False
                }
                
                for manuscript in results['manuscripts']:
                    # Check referee emails
                    if 'referees' in manuscript:
                        for ref in manuscript['referees']:
                            if ref.get('email'):
                                capabilities_found["referees_with_emails"] = True
                            if ref.get('orcid'):
                                capabilities_found["authors_with_orcid"] = True
                    
                    # Check author ORCIDs
                    if 'authors' in manuscript:
                        for author in manuscript['authors']:
                            if author.get('orcid'):
                                capabilities_found["authors_with_orcid"] = True
                    
                    # Check documents
                    if 'documents' in manuscript and manuscript['documents']:
                        capabilities_found["documents_downloaded"] = True
                    
                    # Check audit trail
                    if 'audit_trail' in manuscript and manuscript['audit_trail']:
                        capabilities_found["audit_trail_extracted"] = True
                    
                    # Check version history
                    if 'version_history' in manuscript and manuscript['version_history']:
                        capabilities_found["version_history"] = True
                    
                    # Check enhanced status
                    if 'metadata' in manuscript:
                        meta = manuscript['metadata']
                        if any(key in meta for key in ['review_round', 'days_in_review', 'referee_stats']):
                            capabilities_found["enhanced_status"] = True
                
                # Print capability usage
                print("\n📊 CAPABILITIES USED:")
                print("-" * 40)
                for cap, found in capabilities_found.items():
                    icon = "✅" if found else "⚠️"
                    print(f"{icon} {cap.replace('_', ' ').title()}: {found}")
                
                # Save results
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_file = Path(f"/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs/mor_test_{timestamp}.json")
                
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2, default=str)
                
                print(f"\n📄 Results saved to: {output_file.name}")
                
                # Summary
                capabilities_used = sum(capabilities_found.values())
                total_capabilities = len(capabilities_found)
                score = (capabilities_used / total_capabilities) * 100
                
                print(f"\n🎯 MF-LEVEL CAPABILITY SCORE: {score:.1f}% ({capabilities_used}/{total_capabilities})")
                
                if score == 100:
                    print("\n🎉 SUCCESS: MOR extractor demonstrates ALL MF-level capabilities!")
                elif score >= 80:
                    print("\n⚠️  GOOD: Most capabilities working")
                else:
                    print("\n❌ NEEDS WORK: Some capabilities missing")
            else:
                print("\n❌ No manuscripts found")
        else:
            print("\n❌ Login failed")
            
    except Exception as e:
        print(f"\n❌ Error during extraction: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if extractor and hasattr(extractor, 'driver'):
            try:
                extractor.driver.quit()
            except:
                pass

if __name__ == "__main__":
    test_mor_extraction()