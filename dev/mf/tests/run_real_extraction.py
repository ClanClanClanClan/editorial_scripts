#!/usr/bin/env python3
"""
RUN REAL EXTRACTION - Actually extract manuscripts from MF
=========================================================

This script will:
1. Login to MF
2. Get real manuscript categories
3. Extract actual manuscripts
4. Save results to JSON
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add the production path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'production' / 'src' / 'extractors'))

def run_real_extraction():
    """Run actual MF extraction and save results."""

    from mf_extractor import ComprehensiveMFExtractor

    print("🚀 RUNNING REAL MF EXTRACTION")
    print("=" * 70)

    # Create output directory
    output_dir = Path(__file__).parent.parent / 'outputs'
    output_dir.mkdir(exist_ok=True)

    extraction_results = {
        'timestamp': datetime.now().isoformat(),
        'extractor': 'MF',
        'categories': [],
        'manuscripts': [],
        'errors': []
    }

    try:
        print("📝 Creating MF extractor...")
        mf = ComprehensiveMFExtractor()

        print("🔐 Logging in to MF platform...")
        if not mf.login():
            print("❌ Login failed!")
            extraction_results['errors'].append("Login failed")
            return extraction_results

        print("✅ Login successful!")
        print("\n" + "=" * 70)

        # Get manuscript categories
        print("\n📊 GETTING MANUSCRIPT CATEGORIES...")
        try:
            categories = mf.get_manuscript_categories()
            print(f"✅ Found {len(categories)} categories:\n")

            for i, cat in enumerate(categories, 1):
                cat_info = {
                    'index': i,
                    'name': cat.get('name', 'Unknown'),
                    'count': cat.get('count', 0)
                }
                extraction_results['categories'].append(cat_info)
                print(f"   {i}. {cat_info['name']} ({cat_info['count']} manuscripts)")

            # Extract manuscripts from first few categories with manuscripts
            print("\n" + "=" * 70)
            print("\n📄 EXTRACTING MANUSCRIPTS...")

            manuscripts_extracted = 0
            max_manuscripts = 5  # Limit for demonstration

            for category in categories:
                if manuscripts_extracted >= max_manuscripts:
                    break

                if category.get('count', 0) > 0:
                    print(f"\n📁 Extracting from category: {category['name']}")

                    try:
                        # Navigate to category and get manuscript list
                        manuscripts = mf.get_manuscripts_from_category(category['name'])

                        if manuscripts:
                            print(f"   Found {len(manuscripts)} manuscripts in this category")

                            # Extract details for each manuscript (limit to 2 per category)
                            for ms in manuscripts[:2]:
                                if manuscripts_extracted >= max_manuscripts:
                                    break

                                ms_id = ms.get('id', 'Unknown')
                                print(f"\n   📋 Extracting manuscript: {ms_id}")

                                try:
                                    # Extract full details
                                    details = mf.extract_manuscript_details(ms_id)

                                    # Store results
                                    manuscript_data = {
                                        'id': details.get('id'),
                                        'title': details.get('title'),
                                        'status': details.get('status'),
                                        'category': category['name'],
                                        'submission_date': details.get('submission_date'),
                                        'authors': details.get('authors', []),
                                        'author_count': len(details.get('authors', [])),
                                        'referees': [],
                                        'referee_count': len(details.get('referees', [])),
                                        'timeline_events': len(details.get('timeline', [])),
                                        'documents': len(details.get('documents', [])),
                                        'abstract': details.get('abstract', '')[:200] + '...' if details.get('abstract') else None
                                    }

                                    # Process referee data (anonymize emails)
                                    for ref in details.get('referees', []):
                                        referee_info = {
                                            'name': ref.get('name'),
                                            'email': ref.get('email', '').replace('@', '[at]') if ref.get('email') else None,
                                            'status': ref.get('status'),
                                            'recommendation': ref.get('recommendation'),
                                            'affiliation': ref.get('affiliation')
                                        }
                                        manuscript_data['referees'].append(referee_info)

                                    extraction_results['manuscripts'].append(manuscript_data)
                                    manuscripts_extracted += 1

                                    # Display summary
                                    print(f"      ✅ Title: {manuscript_data['title'][:50]}...")
                                    print(f"      ✅ Status: {manuscript_data['status']}")
                                    print(f"      ✅ Authors: {manuscript_data['author_count']}")
                                    print(f"      ✅ Referees: {manuscript_data['referee_count']}")
                                    print(f"      ✅ Timeline events: {manuscript_data['timeline_events']}")

                                except Exception as e:
                                    print(f"      ❌ Error extracting {ms_id}: {str(e)}")
                                    extraction_results['errors'].append(f"Failed to extract {ms_id}: {str(e)}")

                    except Exception as e:
                        print(f"   ❌ Error with category {category['name']}: {str(e)}")
                        extraction_results['errors'].append(f"Category error {category['name']}: {str(e)}")

        except Exception as e:
            print(f"❌ Error getting categories: {str(e)}")
            extraction_results['errors'].append(f"Category retrieval failed: {str(e)}")

        # Cleanup
        print("\n🧹 Cleaning up...")
        mf.cleanup()

    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        extraction_results['errors'].append(f"Fatal error: {str(e)}")

    # Save results
    output_file = output_dir / f"real_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(extraction_results, f, indent=2)

    print("\n" + "=" * 70)
    print(f"\n💾 Results saved to: {output_file}")
    print(f"✅ Extracted {len(extraction_results['manuscripts'])} manuscripts")
    print(f"✅ Found {len(extraction_results['categories'])} categories")

    if extraction_results['errors']:
        print(f"⚠️ {len(extraction_results['errors'])} errors occurred")

    return extraction_results

if __name__ == "__main__":
    results = run_real_extraction()

    print("\n" + "=" * 70)
    print("📊 EXTRACTION SUMMARY")
    print("=" * 70)

    if results['manuscripts']:
        print("\n🔍 SAMPLE MANUSCRIPT DATA:")
        for i, ms in enumerate(results['manuscripts'][:2], 1):
            print(f"\n📄 Manuscript {i}:")
            print(f"   ID: {ms['id']}")
            print(f"   Title: {ms['title'][:60]}...")
            print(f"   Status: {ms['status']}")
            print(f"   Authors: {ms['author_count']}")
            print(f"   Referees: {ms['referee_count']}")

            if ms['referees']:
                print("   Referee Details:")
                for ref in ms['referees'][:2]:
                    print(f"      - {ref['name']} ({ref['status']})")
    else:
        print("\n❌ No manuscripts were extracted")

    print("\n🏁 EXTRACTION COMPLETE")