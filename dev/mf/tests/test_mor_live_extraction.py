#!/usr/bin/env python3
"""
Live test of enhanced MOR extractor with real extraction
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add production path
sys.path.insert(0, '/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src')

from extractors.mor_extractor import MORExtractor

print("="*60)
print("🚀 LIVE TEST: ENHANCED MOR EXTRACTOR")
print("="*60)

print("\n⚠️  This will perform a REAL extraction from MOR")
print("   - Requires valid credentials")
print("   - Will login with 2FA")
print("   - Will extract manuscripts")
print("   - Will test all enhanced features")

try:
    # Initialize extractor
    print("\n🔧 Initializing enhanced MOR extractor...")
    extractor = MORExtractor(use_cache=False)  # Disable cache for fresh test
    
    print("✅ Extractor initialized")
    
    # Run extraction
    print("\n🚀 Starting extraction...")
    results = extractor.run()
    
    # Analyze results
    print("\n📊 EXTRACTION RESULTS:")
    print("-" * 50)
    
    if results and 'manuscripts' in results:
        num_manuscripts = len(results['manuscripts'])
        print(f"📝 Manuscripts extracted: {num_manuscripts}")
        
        # Check enhanced features usage
        features_used = {
            'referee_emails': 0,
            'orcid_enrichment': 0,
            'documents_downloaded': 0,
            'audit_trail_events': 0,
            'version_history': 0,
            'cover_letters': 0,
            'response_docs': 0,
            'referee_reports': 0,
            'enhanced_status': 0,
            'web_enrichment': 0
        }
        
        for manuscript in results['manuscripts']:
            # Check referee emails
            if 'referees' in manuscript:
                for ref in manuscript['referees']:
                    if ref.get('email'):
                        features_used['referee_emails'] += 1
                    if ref.get('orcid'):
                        features_used['orcid_enrichment'] += 1
            
            # Check documents
            if 'documents' in manuscript:
                docs = manuscript['documents']
                if docs:
                    features_used['documents_downloaded'] += len(docs)
                if 'cover_letter' in docs:
                    features_used['cover_letters'] += 1
                if 'response_to_reviewers' in docs:
                    features_used['response_docs'] += 1
            
            # Check audit trail
            if 'audit_trail' in manuscript and manuscript['audit_trail']:
                features_used['audit_trail_events'] += len(manuscript['audit_trail'])
            
            # Check version history
            if 'version_history' in manuscript and manuscript['version_history']:
                features_used['version_history'] += len(manuscript['version_history'])
            
            # Check referee reports (NEW feature)
            if 'referee_reports' in manuscript:
                features_used['referee_reports'] += len(manuscript.get('referee_reports', []))
            
            # Check enhanced status (NEW feature)
            if 'status_details' in manuscript and manuscript['status_details']:
                features_used['enhanced_status'] += 1
            
            # Check web enrichment (NEW feature)
            if 'authors' in manuscript:
                for author in manuscript['authors']:
                    if author.get('country') and author.get('country') != '':
                        features_used['web_enrichment'] += 1
                        break
        
        print("\n🎯 ENHANCED FEATURES USAGE:")
        print("-" * 50)
        
        for feature, count in features_used.items():
            icon = "✅" if count > 0 else "⚠️"
            feature_name = feature.replace('_', ' ').title()
            print(f"{icon} {feature_name:25} {count}")
        
        # Calculate MF-level score
        features_active = sum(1 for v in features_used.values() if v > 0)
        total_features = len(features_used)
        feature_score = (features_active / total_features) * 100
        
        print("-" * 50)
        print(f"\n🎯 MF-LEVEL FEATURE USAGE: {feature_score:.1f}% ({features_active}/{total_features})")
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/dev/mf/outputs') / f"mor_enhanced_live_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Full results saved to: {output_file.name}")
        
        # Summary assessment
        print("\n" + "="*60)
        print("📢 LIVE TEST ASSESSMENT")
        print("="*60)
        
        if feature_score >= 80:
            print("🎉 EXCELLENT! Enhanced MOR extractor is working with MF-level features!")
        elif feature_score >= 60:
            print("✅ GOOD: Most enhanced features are working")
        elif feature_score >= 40:
            print("⚠️  PARTIAL: Some enhanced features working")
        else:
            print("❌ LIMITED: Few enhanced features detected")
            print("   Note: This may be due to manuscript data availability")
        
        # Check specific enhancements
        print("\n🔍 NEW MF-LEVEL FEATURES VERIFICATION:")
        new_features = [
            ('Cover letter extraction', features_used['cover_letters'] > 0),
            ('Response to reviewers', features_used['response_docs'] > 0),
            ('Referee reports', features_used['referee_reports'] > 0),
            ('Enhanced status parsing', features_used['enhanced_status'] > 0),
            ('Web enrichment', features_used['web_enrichment'] > 0)
        ]
        
        for feature, active in new_features:
            icon = "✅" if active else "⚠️"
            status = "Active" if active else "Not detected"
            print(f"{icon} {feature:25} {status}")
        
        if results.get('summary'):
            summary = results['summary']
            print(f"\n📈 EXTRACTION SUMMARY:")
            print(f"   Total manuscripts: {summary.get('total_manuscripts', 0)}")
            print(f"   Referee emails: {summary.get('referee_emails_extracted', 0)}")
            print(f"   Documents: {summary.get('documents_downloaded', 0)}")
            print(f"   Audit events: {summary.get('total_audit_events', 0)}")
        
        print("\n🎆 ENHANCED MOR EXTRACTOR TEST COMPLETE!")
        
    else:
        print("❌ No manuscripts found in results")
        
except Exception as e:
    print(f"\n❌ Error during live test: {e}")
    import traceback
    traceback.print_exc()