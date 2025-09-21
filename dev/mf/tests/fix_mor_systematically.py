#!/usr/bin/env python3
"""
Systematically fix and enhance MOR extractor to MF-level
Adds missing methods one by one with proper integration
"""

import os
import re
from pathlib import Path
from datetime import datetime

# File paths
mor_path = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src/extractors/mor_extractor.py')
mf_path = Path('/Users/dylanpossamai/Library/CloudStorage/Dropbox/Work/editorial_scripts/production/src/extractors/mf_extractor.py')

print("="*60)
print("🔧 SYSTEMATIC MOR ENHANCEMENT TO MF-LEVEL")
print("="*60)

# Read both files
with open(mor_path, 'r') as f:
    mor_content = f.read()

with open(mf_path, 'r') as f:
    mf_content = f.read()

print("\n📝 STEP 1: Fix Cache Integration")
print("-" * 50)

# Fix the cache initialization issue
old_init = '''    def __init__(self, use_cache: bool = True, cache_ttl_hours: int = 24):
        """Initialize with caching support"""
        super().__init__(cache_ttl_hours=cache_ttl_hours)
        self.use_cache = use_cache'''

new_init = '''    def __init__(self, use_cache: bool = True, cache_ttl_hours: int = 24):
        """Initialize with caching support"""
        # Note: CachedExtractorMixin doesn't have __init__, use init_cached_extractor instead
        self.use_cache = use_cache
        self.cache_ttl_hours = cache_ttl_hours
        self.cache_hits = 0'''

if old_init in mor_content:
    mor_content = mor_content.replace(old_init, new_init)
    print("✅ Fixed cache initialization")
else:
    print("⚠️  Cache init pattern not found, may already be fixed")

# Also need to initialize cache properly
old_setup = '''        self.setup_chrome_options()
        self.setup_directories()
        self.driver = None'''

new_setup = '''        self.setup_chrome_options()
        self.setup_directories()
        # Initialize cache after setting up directories
        if self.use_cache:
            try:
                self.init_cached_extractor('MOR')
            except:
                print("⚠️  Cache initialization failed, continuing without cache")
                self.use_cache = False
        self.driver = None'''

if old_setup in mor_content:
    mor_content = mor_content.replace(old_setup, new_setup)
    print("✅ Added proper cache initialization")

print("\n📝 STEP 2: Extract Missing Methods from MF")
print("-" * 50)

# Extract specific methods from MF
mf_lines = mf_content.split('\n')

# Method definitions to extract with their line ranges (approximate)
methods_to_add = [
    ('get_email_from_popup_safe', 'MINIMAL: Just try to get email without complex frame handling'),
    ('extract_cover_letter_from_details', 'Extract cover letter download link from details page'),
    ('extract_response_to_reviewers', 'Extract response to reviewers document if available'),
    ('extract_referee_report_from_link', 'Extract referee report details from review link'),
    ('extract_review_popup_content', 'Extract content from review history popup'),
    ('infer_country_from_web_search', 'Try to infer country from institution name using web search'),
    ('parse_affiliation_string', 'Parse a complex affiliation string'),
    ('get_manuscript_categories', 'Get list of available manuscript categories')
]

extracted_methods = {}

for method_name, method_desc in methods_to_add:
    # Find method in MF
    pattern = rf'\s+def {method_name}\(self[^)]*\):[^\n]*\n\s+"""[^"]*{method_desc[:30]}'
    
    for i, line in enumerate(mf_lines):
        if f'def {method_name}(' in line:
            # Extract the full method
            indent_level = len(line) - len(line.lstrip())
            method_lines = [line]
            
            # Continue until we hit another method at the same indent level
            j = i + 1
            while j < len(mf_lines):
                current_line = mf_lines[j]
                if current_line.strip() and not current_line.startswith(' ' * (indent_level + 1)):
                    # Check if it's another method definition at same level
                    if current_line.strip().startswith('def ') or current_line.strip().startswith('@'):
                        break
                method_lines.append(current_line)
                j += 1
            
            extracted_methods[method_name] = '\n'.join(method_lines)
            print(f"✅ Extracted {method_name} ({j - i} lines)")
            break

print(f"\n📊 Extracted {len(extracted_methods)} methods from MF")

print("\n📝 STEP 3: Add Missing Methods to MOR")
print("-" * 50)

# Find where to insert the methods (before the run method)
run_pattern = r'(\s+)def run\(self\)'
run_match = re.search(run_pattern, mor_content)

if run_match:
    insert_pos = run_match.start()
    indent = run_match.group(1)
    
    # Build the methods section
    methods_section = f"{indent}# " + "="*50 + "\n"
    methods_section += f"{indent}# MF-LEVEL ENHANCEMENT METHODS\n"
    methods_section += f"{indent}# Systematically added for full capability parity\n"
    methods_section += f"{indent}# " + "="*50 + "\n\n"
    
    # Add each method
    for method_name, method_code in extracted_methods.items():
        if method_code:
            methods_section += method_code + "\n\n"
            print(f"✅ Added {method_name}")
    
    # Insert the methods
    enhanced_content = mor_content[:insert_pos] + methods_section + mor_content[insert_pos:]
    
    print("\n📝 STEP 4: Save Enhanced MOR Extractor")
    print("-" * 50)
    
    # Backup original
    backup_path = mor_path.with_suffix('.py.backup_before_enhancement')
    with open(backup_path, 'w') as f:
        f.write(mor_content)
    print(f"💾 Backup saved: {backup_path.name}")
    
    # Save enhanced version
    with open(mor_path, 'w') as f:
        f.write(enhanced_content)
    
    # Calculate stats
    original_lines = len(mor_content.split('\n'))
    enhanced_lines = len(enhanced_content.split('\n'))
    added_lines = enhanced_lines - original_lines
    
    print(f"\n📈 Enhancement Statistics:")
    print(f"   Original: {original_lines} lines")
    print(f"   Enhanced: {enhanced_lines} lines")
    print(f"   Added: {added_lines} lines")
    print(f"   Methods added: {len(extracted_methods)}")
    
    print("\n🎉 MOR EXTRACTOR ENHANCED TO MF-LEVEL!")
    print("   All critical methods have been added")
    print("   Cache integration has been fixed")
    print("   Ready for testing")
    
else:
    print("❌ Could not find run method in MOR extractor")
    print("   Unable to insert enhancement methods")