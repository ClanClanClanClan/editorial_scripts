#!/usr/bin/env python3
"""Proper fix for MF popup handling."""

import sys
import os

# Read the current MF extractor
with open('production/src/extractors/mf_extractor.py', 'r') as f:
    lines = f.readlines()

# Find and replace the problematic get_email_from_popup_safe method
new_method = '''    def get_email_from_popup_safe(self, popup_url_or_element):
        """FIXED: Simplified popup handling that doesn't get stuck."""
        if not popup_url_or_element:
            return ""

        original_window = self.driver.current_window_handle
        email = ""

        try:
            # Step 1: Open the popup
            if hasattr(popup_url_or_element, 'click'):
                popup_url_or_element.click()
            else:
                return ""  # Skip non-clickable elements

            # Step 2: Wait briefly for popup
            time.sleep(2)

            # Step 3: Check if popup opened
            windows = self.driver.window_handles
            if len(windows) <= 1:
                print("         ⚠️ No popup opened")
                return ""

            # Step 4: Switch to popup
            popup_window = windows[-1]
            self.driver.switch_to.window(popup_window)

            # Step 5: Quick email extraction - just check URL and basic page
            try:
                current_url = self.driver.current_url

                # Check URL for email
                if 'EMAIL_TO=' in current_url or '@' in current_url:
                    import re
                    from urllib.parse import unquote

                    # Look for email pattern in URL
                    email_pattern = r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,})'
                    matches = re.findall(email_pattern, unquote(current_url))

                    for match in matches:
                        if 'dylan.possamai' not in match.lower():
                            email = match
                            print(f"         ✅ Email from URL: {email}")
                            break

                # If no email in URL, do a VERY quick check of page
                if not email:
                    # Just grab first 5000 chars of page source
                    try:
                        page_text = self.driver.page_source[:5000]

                        # Quick email pattern search
                        import re
                        email_pattern = r'([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,})'
                        matches = re.findall(email_pattern, page_text)

                        for match in matches:
                            if 'dylan.possamai' not in match.lower() and 'manuscript' not in match.lower():
                                email = match
                                print(f"         ✅ Email from page: {email}")
                                break
                    except:
                        pass

            except Exception as e:
                print(f"         ⚠️ Email extraction error: {e}")

        except Exception as e:
            print(f"         ❌ Popup handling error: {e}")

        finally:
            # CRITICAL: Clean return to original window
            try:
                # Close all popups
                for window in self.driver.window_handles:
                    if window != original_window:
                        try:
                            self.driver.switch_to.window(window)
                            self.driver.close()
                        except:
                            pass

                # Return to original
                self.driver.switch_to.window(original_window)

                # IMPORTANT: Reset any frame context
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass

            except:
                # Emergency recovery
                try:
                    if self.driver.window_handles:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        self.driver.switch_to.default_content()
                except:
                    pass

        return email

'''

# Find the start and end of the current method
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'def get_email_from_popup_safe' in line:
        start_idx = i
    elif start_idx is not None and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
        end_idx = i
        break

if start_idx is not None:
    # If we didn't find the end, look for the next method definition
    if end_idx is None:
        for i in range(start_idx + 1, len(lines)):
            if lines[i].strip().startswith('def ') and not lines[i].strip().startswith('def '):
                end_idx = i
                break

    # If still no end, use a reasonable limit
    if end_idx is None:
        end_idx = start_idx + 300  # Reasonable max for a method

    # Replace the method
    new_lines = lines[:start_idx] + [new_method + '\n'] + lines[end_idx:]

    # Write the fixed version
    with open('production/src/extractors/mf_extractor_fixed.py', 'w') as f:
        f.writelines(new_lines)

    print("✅ Applied proper popup fix")
    print(f"   Replaced lines {start_idx+1} to {end_idx}")
    print("\n💾 Fixed version saved to: production/src/extractors/mf_extractor_fixed.py")
    print("\n📝 To apply the fix:")
    print("   cp production/src/extractors/mf_extractor_fixed.py production/src/extractors/mf_extractor.py")
else:
    print("❌ Could not find get_email_from_popup_safe method")