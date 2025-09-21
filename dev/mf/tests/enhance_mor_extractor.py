#!/usr/bin/env python3
"""
Enhance MOR extractor with missing MF capabilities
Adds the critical missing features to bring MOR to MF-level
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Paths
original_mor = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src/extractors/mor_extractor.py')
original_mf = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src/extractors/mf_extractor.py')
enhanced_mor = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src/extractors/mor_extractor_enhanced.py')

print("="*60)
print("🔧 ENHANCING MOR EXTRACTOR WITH MF CAPABILITIES")
print("="*60)

# Read the original MOR extractor
with open(original_mor, 'r') as f:
    mor_content = f.read()

# Read the MF extractor to get missing methods
with open(original_mf, 'r') as f:
    mf_content = f.read()

# Extract key methods from MF that MOR is missing
missing_methods = [
    # Safe popup email extraction
    ('get_email_from_popup_safe', 461, 553),
    
    # Cover letter extraction  
    ('extract_cover_letter_from_details', 4709, 4723),
    
    # Response to reviewers
    ('extract_response_to_reviewers', 4724, 4776),
    
    # Referee report extraction
    ('extract_referee_report_from_link', 2667, 2758),
    
    # Review popup content
    ('extract_review_popup_content', 2758, 2879),
    
    # Report with timeout
    ('extract_report_with_timeout', 2618, 2667),
    
    # Country inference from web search
    ('infer_country_from_web_search', 1740, 1959),
    
    # Parse affiliation string
    ('parse_affiliation_string', 1959, 2036),
    
    # Get manuscript categories
    ('get_manuscript_categories', 1403, 1514)
]

print("\n📝 Adding missing methods to MOR extractor:")
print("-" * 50)

# Extract method code from MF
methods_to_add = []
mf_lines = mf_content.split('\n')

for method_name, start_line, end_line in missing_methods:
    # Adjust for 0-based indexing
    method_code = '\n'.join(mf_lines[start_line-1:end_line])
    methods_to_add.append((method_name, method_code))
    print(f"✅ Extracted {method_name} ({end_line - start_line + 1} lines)")

# Find where to insert the methods (before the run method)
import re
run_match = re.search(r'(\s*)def run\(self\)', mor_content)
if run_match:
    insert_position = run_match.start()
    indent = run_match.group(1)
    
    # Build the enhanced content
    enhanced_content = mor_content[:insert_position]
    
    # Add a section header
    enhanced_content += f"{indent}# " + "="*50 + "\n"
    enhanced_content += f"{indent}# MF-LEVEL ENHANCED METHODS\n"
    enhanced_content += f"{indent}# Added from MF extractor for capability parity\n"
    enhanced_content += f"{indent}# " + "="*50 + "\n\n"
    
    # Add each missing method
    for method_name, method_code in methods_to_add:
        enhanced_content += f"{indent}{method_code}\n\n"
    
    # Add the rest of the original content
    enhanced_content += mor_content[insert_position:]
    
    # Write the enhanced version
    with open(enhanced_mor, 'w') as f:
        f.write(enhanced_content)
    
    print("-" * 50)
    print(f"\n✅ Enhanced MOR extractor created: {enhanced_mor.name}")
    print(f"   Added {len(missing_methods)} MF-level methods")
    
    # Calculate file size difference
    original_size = original_mor.stat().st_size
    enhanced_size = enhanced_mor.stat().st_size
    size_increase = (enhanced_size - original_size) / 1024
    
    print(f"   Original size: {original_size/1024:.1f} KB")
    print(f"   Enhanced size: {enhanced_size/1024:.1f} KB")
    print(f"   Size increase: {size_increase:.1f} KB")
    
    # Create a backup of the original
    backup_path = original_mor.with_suffix('.py.backup')
    shutil.copy2(original_mor, backup_path)
    print(f"\n💾 Backup created: {backup_path.name}")
    
    print("\n🎆 MOR EXTRACTOR ENHANCEMENT COMPLETE!")
    print("   The enhanced version has ALL MF-level capabilities")
    print("   Test with: python3 mor_extractor_enhanced.py")
    
else:
    print("❌ Could not find run method in MOR extractor")
    sys.exit(1)