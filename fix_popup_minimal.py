#!/usr/bin/env python3
"""Minimal popup fix - just make it not hang."""

import sys
import os

# Read the MF extractor
with open('production/src/extractors/mf_extractor.py', 'r') as f:
    content = f.read()

# Find the problematic popup method and replace with a MINIMAL version
# that just opens, tries to get email, and closes without getting stuck

minimal_popup_method = '''    def get_email_from_popup_safe(self, popup_url_or_element):
        """MINIMAL: Just try to get email without complex frame handling."""
        if not popup_url_or_element:
            return ""

        original_window = self.driver.current_window_handle
        email = ""

        try:
            # Open popup
            if hasattr(popup_url_or_element, 'click'):
                try:
                    popup_url_or_element.click()
                    time.sleep(1)
                except:
                    return ""
            else:
                return ""

            # Check if popup opened
            if len(self.driver.window_handles) > 1:
                popup_window = self.driver.window_handles[-1]

                try:
                    # Switch to popup
                    self.driver.switch_to.window(popup_window)
                    time.sleep(1)

                    # Just check URL for email - don't mess with frames
                    current_url = self.driver.current_url
                    if '@' in current_url:
                        import re
                        emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})', current_url)
                        for e in emails:
                            if 'dylan' not in e.lower():
                                email = e
                                break

                    # Quick check of page source (no frames!)
                    if not email:
                        try:
                            # Just first 3000 chars
                            text = self.driver.page_source[:3000]
                            if '@' in text:
                                import re
                                emails = re.findall(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})', text)
                                for e in emails:
                                    if 'dylan' not in e.lower() and 'manuscript' not in e.lower():
                                        email = e
                                        break
                        except:
                            pass

                    # Close popup
                    self.driver.close()

                except Exception as e:
                    print(f"         ⚠️ Popup error: {e}")
                    # Try to close popup anyway
                    try:
                        self.driver.close()
                    except:
                        pass

                # Return to main window
                self.driver.switch_to.window(original_window)

                # Reset frame context just in case
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass

            return email

        except Exception as e:
            print(f"         ❌ Popup failed: {e}")

            # Emergency cleanup
            try:
                for w in self.driver.window_handles:
                    if w != original_window:
                        try:
                            self.driver.switch_to.window(w)
                            self.driver.close()
                        except:
                            pass
                self.driver.switch_to.window(original_window)
                self.driver.switch_to.default_content()
            except:
                pass

            return ""
'''

# Find and replace the method
import re

# Find the start of the method
pattern = r'(    def get_email_from_popup_safe\(self.*?\n)(.*?)(\n    def [a-zA-Z_])'

# Use regex with DOTALL flag to match across lines
match = re.search(pattern, content, re.DOTALL)

if match:
    # Replace just this method
    new_content = content[:match.start()] + minimal_popup_method + match.group(3) + content[match.end():]

    # Save the fixed version
    with open('production/src/extractors/mf_extractor.py', 'w') as f:
        f.write(new_content)

    print("✅ Applied minimal popup fix")
    print("   - Simplified popup handling")
    print("   - No complex frame switching")
    print("   - Quick email check only")
    print("   - Guaranteed cleanup")
else:
    print("❌ Could not find method to replace")
    print("   Trying alternative approach...")

    # Alternative: just replace the whole method by finding it differently
    start_marker = "    def get_email_from_popup_safe(self, popup_url_or_element):"

    if start_marker in content:
        start_idx = content.index(start_marker)

        # Find the next method (starts with "    def ")
        remaining = content[start_idx + len(start_marker):]
        next_method_match = re.search(r'\n    def [a-zA-Z_]', remaining)

        if next_method_match:
            end_idx = start_idx + len(start_marker) + next_method_match.start()

            # Replace the method
            new_content = content[:start_idx] + minimal_popup_method + content[end_idx:]

            with open('production/src/extractors/mf_extractor.py', 'w') as f:
                f.write(new_content)

            print("✅ Applied minimal popup fix (alternative method)")
        else:
            print("❌ Could not find end of method")