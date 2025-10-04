#!/usr/bin/env python3
"""Skip popup email extraction to prevent hanging."""

import sys
import os

# Read the current MF extractor
with open("production/src/extractors/mf_extractor.py", "r") as f:
    content = f.read()

# Fix: Skip popup extraction entirely in referee extraction
fix_old = """                                            # CLICK THE POPUP TO EXTRACT EMAIL
                                            try:
                                                # Add timeout protection
                                                email = self.get_email_from_popup_safe(link)
                                                if email:
                                                    print(f"         📧 Email from popup click: {email}")
                                                    break
                                            except Exception as popup_error:
                                                print(f"         ⚠️ Popup extraction failed: {popup_error}")
                                                # Continue without email rather than getting stuck
                                                email = ""
                                                break"""

fix_new = """                                            # SKIP POPUP TO PREVENT HANGING
                                            print(f"         ⚠️ Skipping popup extraction to prevent hanging")
                                            email = ""  # Will get emails from Gmail cross-check later
                                            break"""

if fix_old in content:
    content = content.replace(fix_old, fix_new)
    print("✅ Applied skip popup fix")
else:
    # Try without the try-except wrapper
    alt_old = """                                            # CLICK THE POPUP TO EXTRACT EMAIL
                                            email = self.get_email_from_popup_safe(link)
                                            if email:
                                                print(f"         📧 Email from popup click: {email}")
                                                break"""

    alt_new = """                                            # SKIP POPUP TO PREVENT HANGING
                                            print(f"         ⚠️ Skipping popup extraction to prevent hanging")
                                            email = ""  # Will get emails from Gmail cross-check later
                                            break"""

    if alt_old in content:
        content = content.replace(alt_old, alt_new)
        print("✅ Applied alternate skip popup fix")
    else:
        print("⚠️ Could not find popup extraction code")

# Also skip popup in author extraction
author_popup_old = """                            email = self.get_email_from_popup_safe(link)"""
author_popup_new = """                            email = ""  # Skip popup to prevent hanging"""

if author_popup_old in content:
    content = content.replace(author_popup_old, author_popup_new)
    print("✅ Also skipped popup in author extraction")

# Save the fixed version
output_file = "production/src/extractors/mf_extractor_nopopup.py"
with open(output_file, "w") as f:
    f.write(content)

print(f"\n💾 Fixed version saved to: {output_file}")
print("\n📝 To apply the fix:")
print(f"   cp {output_file} production/src/extractors/mf_extractor.py")
