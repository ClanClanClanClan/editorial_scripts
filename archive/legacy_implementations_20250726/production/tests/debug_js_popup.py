#!/usr/bin/env python3
"""
Debug the JavaScript popup execution issue
"""

import re

# Sample JavaScript from the error log
js_samples = [
    "popWindow('mafi?PARAMS=xik_VdRYEh3tCXkuC8gcSr2kmvo...",
    "popWindow('mafi?PARAMS=xik_6LU1RUkMMUhYx1MpqgVJGKR...",
]

print("🔍 Analyzing JavaScript popup calls...")
print("=" * 60)

for js in js_samples:
    print(f"\nOriginal: {js}")
    
    # The issue is likely that the JavaScript is truncated
    # The popWindow call needs proper quotes
    if js.endswith("..."):
        print("   ⚠️ JavaScript is truncated!")
        
    # Check for matching quotes
    single_quotes = js.count("'")
    double_quotes = js.count('"')
    parens = js.count("(") - js.count(")")
    
    print(f"   Single quotes: {single_quotes} (should be even)")
    print(f"   Double quotes: {double_quotes} (should be even)")
    print(f"   Unclosed parens: {parens}")
    
    if single_quotes % 2 != 0:
        print("   ❌ Unmatched single quotes!")
    if parens != 0:
        print("   ❌ Unmatched parentheses!")

print("\n📝 The problem:")
print("   The JavaScript code is being truncated when extracted from href")
print("   This creates invalid syntax when executed")
print("\n💡 Solution:")
print("   Don't truncate the JavaScript code, or handle it differently")