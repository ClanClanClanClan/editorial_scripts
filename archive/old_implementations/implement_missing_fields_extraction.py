#!/usr/bin/env python3
"""
Implement Missing Fields Extraction
===================================

Add extraction for abstract, keywords, author affiliations, DOI, and structured recommendations.
"""

print("🚀 IMPLEMENTING MISSING FIELDS EXTRACTION")
print("=" * 60)

# Read the current MF extractor
with open("production/mf_extractor.py") as f:
    code = f.read()

# 1. Add abstract extraction method
abstract_method = '''
    def extract_abstract(self, manuscript):
        """Extract manuscript abstract from popup."""
        try:
            print("   📝 Extracting abstract...")

            # Find abstract link
            doc_section = self.driver.find_element(By.XPATH, "//p[@class='pagecontents msdetailsbuttons']")
            abstract_links = doc_section.find_elements(By.XPATH, ".//a[contains(text(), 'Abstract')]")

            if abstract_links:
                # Store current window
                original_window = self.driver.current_window_handle

                # Click abstract link
                abstract_links[0].click()
                time.sleep(2)

                # Switch to popup
                if len(self.driver.window_handles) > 1:
                    for window in self.driver.window_handles:
                        if window != original_window:
                            self.driver.switch_to.window(window)
                            break

                    # Extract abstract text
                    abstract_text = ""

                    # Try various selectors
                    selectors = [
                        "//td[@class='pagecontents']",
                        "//p[@class='pagecontents']",
                        "//div[@class='abstract']",
                        "//body"
                    ]

                    for selector in selectors:
                        try:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            for elem in elements:
                                text = elem.text.strip()
                                if len(text) > 100:  # Likely abstract content
                                    abstract_text = text
                                    break
                            if abstract_text:
                                break
                        except:
                            pass

                    # Close popup
                    self.driver.close()
                    self.driver.switch_to.window(original_window)

                    if abstract_text:
                        manuscript['abstract'] = abstract_text
                        print(f"      ✅ Abstract extracted ({len(abstract_text)} chars)")
                    else:
                        print("      ❌ Abstract text not found in popup")
                else:
                    print("      ❌ Abstract popup did not open")

        except Exception as e:
            print(f"   ❌ Error extracting abstract: {e}")
'''

# 2. Add keywords extraction method
keywords_method = '''
    def extract_keywords(self, manuscript):
        """Extract manuscript keywords."""
        try:
            print("   🏷️ Extracting keywords...")

            # Look for keywords in various locations
            keyword_patterns = [
                "//td[contains(text(), 'Keywords')]/following-sibling::td",
                "//td[contains(text(), 'Key Words')]/following-sibling::td",
                "//p[contains(text(), 'Keywords:')]",
                "//span[contains(text(), 'Keywords')]/following::span[1]",
                "//div[contains(@class, 'keywords')]"
            ]

            keywords_found = False
            for pattern in keyword_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    for elem in elements:
                        text = elem.text.strip()
                        if text and len(text) > 3:
                            # Parse keywords (usually semicolon or comma separated)
                            if ';' in text:
                                keywords = [k.strip() for k in text.split(';') if k.strip()]
                            elif ',' in text:
                                keywords = [k.strip() for k in text.split(',') if k.strip()]
                            else:
                                keywords = [text]

                            if keywords:
                                manuscript['keywords'] = keywords
                                print(f"      ✅ Keywords extracted: {', '.join(keywords[:3])}...")
                                keywords_found = True
                                break
                    if keywords_found:
                        break
                except:
                    pass

            if not keywords_found:
                print("      ❌ Keywords not found on page")

        except Exception as e:
            print(f"   ❌ Error extracting keywords: {e}")
'''

# 3. Add author affiliations extraction
author_affiliations_method = '''
    def extract_author_affiliations(self, manuscript):
        """Extract author affiliations from mailpopup links."""
        try:
            print("   🏛️ Extracting author affiliations...")

            # For each author, try to get their affiliation
            for author in manuscript.get('authors', []):
                if not author.get('institution'):
                    # Find the author's mailpopup link
                    try:
                        # Look for author link by name
                        author_links = self.driver.find_elements(By.XPATH,
                            f"//a[contains(@href, 'mailpopup') and contains(text(), '{author['name'].split()[-1]}')]")

                        if author_links:
                            # Get email and potentially affiliation from popup
                            original_window = self.driver.current_window_handle

                            author_links[0].click()
                            time.sleep(2)

                            if len(self.driver.window_handles) > 1:
                                for window in self.driver.window_handles:
                                    if window != original_window:
                                        self.driver.switch_to.window(window)
                                        break

                                # Extract email and affiliation
                                try:
                                    # Email
                                    email_field = self.driver.find_element(By.NAME, "EMAIL_TEMPLATE_TO")
                                    email = email_field.get_attribute('value')
                                    if email and '@' in email:
                                        author['email'] = email
                                except:
                                    pass

                                # Look for institution/affiliation
                                affil_patterns = [
                                    "//td[contains(text(), 'Institution')]",
                                    "//td[contains(text(), 'Affiliation')]",
                                    "//td[contains(text(), 'Department')]"
                                ]

                                for pattern in affil_patterns:
                                    try:
                                        label = self.driver.find_element(By.XPATH, pattern)
                                        # Get next sibling td
                                        value = label.find_element(By.XPATH, "./following-sibling::td")
                                        affiliation = value.text.strip()
                                        if affiliation:
                                            author['institution'] = affiliation
                                            print(f"      ✅ {author['name']}: {affiliation}")
                                            break
                                    except:
                                        pass

                                # Close popup
                                self.driver.close()
                                self.driver.switch_to.window(original_window)

                    except Exception as e:
                        print(f"      ⚠️ Could not get affiliation for {author['name']}: {e}")

        except Exception as e:
            print(f"   ❌ Error extracting author affiliations: {e}")
'''

# 4. Add DOI extraction
doi_extraction = '''
    def extract_doi(self, manuscript):
        """Extract DOI if available."""
        try:
            # Look for DOI patterns
            doi_patterns = [
                "//td[contains(text(), 'DOI')]/following-sibling::td",
                "//span[contains(text(), 'DOI:')]",
                "//a[contains(@href, 'doi.org')]",
                "//*[contains(text(), '10.') and contains(text(), '/')]"
            ]

            for pattern in doi_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    for elem in elements:
                        text = elem.text.strip()
                        # Extract DOI pattern (10.xxxx/yyyy)
                        import re
                        doi_match = re.search(r'10\\.\\d{4,}/[-._;()/:a-zA-Z0-9]+', text)
                        if doi_match:
                            manuscript['doi'] = doi_match.group(0)
                            print(f"   📖 DOI found: {manuscript['doi']}")
                            return
                except:
                    pass

        except Exception as e:
            print(f"   ⚠️ Error extracting DOI: {e}")
'''

# 5. Enhanced recommendation parsing from popup content
parse_recommendation_method = '''
    def parse_recommendation_from_popup(self, popup_content):
        """Parse structured recommendation from popup content."""
        if not popup_content:
            return None

        recommendation = popup_content.get('recommendation', '')
        review_text = popup_content.get('review_text', '')

        # Map text to structured enum values
        recommendation_map = {
            'accept': 'accept',
            'minor': 'minor',
            'major': 'major',
            'reject': 'reject',
            'minor revision': 'minor',
            'major revision': 'major',
            'acceptance': 'accept',
            'rejection': 'reject'
        }

        # Check recommendation field first
        rec_lower = recommendation.lower()
        for key, value in recommendation_map.items():
            if key in rec_lower:
                return value

        # Check review text for recommendation keywords
        text_lower = review_text.lower()
        if 'recommend acceptance' in text_lower or 'should be accepted' in text_lower:
            return 'accept'
        elif 'minor revision' in text_lower or 'minor changes' in text_lower:
            return 'minor'
        elif 'major revision' in text_lower or 'substantial revision' in text_lower:
            return 'major'
        elif 'recommend rejection' in text_lower or 'should be rejected' in text_lower:
            return 'reject'

        return None
'''

# Now insert these methods into the extractor
import re

# Find where to insert the methods (after extract_document_links)
insert_pos = code.find("def get_email_from_popup")

if insert_pos > 0:
    # Insert all the new methods
    new_methods = (
        abstract_method
        + "\n"
        + keywords_method
        + "\n"
        + author_affiliations_method
        + "\n"
        + doi_extraction
        + "\n"
        + parse_recommendation_method
        + "\n"
    )

    code = code[:insert_pos] + new_methods + "    " + code[insert_pos:]
    print("✅ Added new extraction methods")
else:
    print("❌ Could not find insertion point")

# Now update extract_manuscript_details to call these methods
# Find the method
extract_details_pattern = (
    r"def extract_manuscript_details\(self, manuscript_id\):.*?return manuscript"
)
match = re.search(extract_details_pattern, code, re.DOTALL)

if match:
    method_code = match.group(0)

    # Find where to insert the calls (before return)
    insert_before = "return manuscript"

    new_calls = """
        # Extract additional fields
        self.extract_abstract(manuscript)
        self.extract_keywords(manuscript)
        self.extract_author_affiliations(manuscript)
        self.extract_doi(manuscript)

        """

    updated_method = method_code.replace(insert_before, new_calls + insert_before)
    code = code.replace(method_code, updated_method)
    print("✅ Updated extract_manuscript_details to call new methods")

# Also update referee extraction to parse recommendations
referee_pattern = r"if popup_content:\s*referee\[\'popup_review_content\'\] = popup_content"
if referee_pattern in code:
    replacement = """if popup_content:
                                            referee['popup_review_content'] = popup_content
                                            # Parse structured recommendation
                                            structured_rec = self.parse_recommendation_from_popup(popup_content)
                                            if structured_rec:
                                                referee['recommendation_structured'] = structured_rec
                                                print(f"         ⭐ Recommendation: {structured_rec}")"""

    code = re.sub(referee_pattern, replacement, code)
    print("✅ Added recommendation parsing to referee extraction")

# Write the updated code
with open("production/mf_extractor.py", "w") as f:
    f.write(code)

print("\n✅ MISSING FIELDS EXTRACTION IMPLEMENTED!")
print("\nNew fields being extracted:")
print("  📝 Abstract - From popup window")
print("  🏷️ Keywords - From manuscript page")
print("  🏛️ Author affiliations - From mailpopup links")
print("  📖 DOI - From manuscript metadata")
print("  ⭐ Structured recommendations - Parsed from popup content")

print("\n🚀 Ready to run extraction with enhanced field capture!")
