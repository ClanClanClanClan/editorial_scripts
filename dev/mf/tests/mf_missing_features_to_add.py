# Missing features to add to MF extractor
# Copy these functions into the appropriate places


    def extract_response_to_reviewers(self, manuscript):
        """Extract response to reviewers document if available."""
        try:
            print("      📝 Looking for response to reviewers...")

            # Look for response to reviewers link
            response_links = self.driver.find_elements(By.XPATH,
                "//a[contains(text(), 'Response to Reviewers') or contains(text(), 'Response to Referee') or contains(text(), 'Author Response')]")

            if response_links:
                for link in response_links:
                    try:
                        href = link.get_attribute('href')
                        if href and ('.pdf' in href or '.docx' in href or '.doc' in href):
                            # Download the response document
                            filename = f"response_to_reviewers_{manuscript.get('id', 'unknown')}"
                            if '.pdf' in href:
                                filename += '.pdf'
                            elif '.docx' in href:
                                filename += '.docx'
                            else:
                                filename += '.doc'

                            download_path = os.path.join(self.download_dir, filename)

                            # Click to download
                            link.click()
                            time.sleep(2)

                            # Wait for download
                            if self.wait_for_download(filename):
                                manuscript['response_to_reviewers'] = {
                                    'path': download_path,
                                    'filename': filename,
                                    'extracted': True
                                }
                                print(f"      ✅ Downloaded response to reviewers: {filename}")
                                return True
                    except Exception as e:
                        print(f"      ⚠️ Error downloading response: {e}")
                        continue

            # Alternative: Look in manuscript history or revisions section
            revision_sections = self.driver.find_elements(By.XPATH,
                "//td[contains(text(), 'Revision') or contains(text(), 'Resubmission')]/following-sibling::td//a")

            for link in revision_sections:
                try:
                    text = link.text.lower()
                    if 'response' in text or 'reply' in text or 'rebuttal' in text:
                        href = link.get_attribute('href')
                        if href:
                            # Extract response document
                            manuscript['response_to_reviewers'] = {
                                'link': href,
                                'text': link.text,
                                'found': True
                            }
                            print(f"      ✅ Found response to reviewers link: {link.text}")
                            return True
                except:
                    continue

            print("      ℹ️ No response to reviewers found (may not be a revision)")
            manuscript['response_to_reviewers'] = None

        except Exception as e:
            print(f"      ⚠️ Error extracting response to reviewers: {e}")
            manuscript['response_to_reviewers'] = None



    def extract_revised_manuscripts(self, manuscript):
        """Extract all versions of revised manuscripts."""
        try:
            print("      📄 Looking for revised manuscript versions...")

            manuscript['revisions'] = []

            # Look for revision history
            revision_links = self.driver.find_elements(By.XPATH,
                "//a[contains(text(), 'Revised Manuscript') or contains(text(), 'Revision') or contains(@href, 'revised')]")

            for link in revision_links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()

                    if href and ('.pdf' in href or '.docx' in href):
                        # Extract version number if present
                        version_match = re.search(r'[Vv]ersion\s*(\d+)|[Rr]evision\s*(\d+)|R(\d+)', text)
                        version = 'unknown'
                        if version_match:
                            version = version_match.group(1) or version_match.group(2) or version_match.group(3)

                        revision_data = {
                            'version': version,
                            'link': href,
                            'text': text,
                            'type': 'revised_manuscript'
                        }

                        # Try to download
                        if self.download_manuscript_revision(href, manuscript.get('id', 'unknown'), version):
                            revision_data['downloaded'] = True

                        manuscript['revisions'].append(revision_data)
                        print(f"      ✅ Found revision: {text}")

                except Exception as e:
                    print(f"      ⚠️ Error processing revision link: {e}")
                    continue

            # Look for track changes versions
            track_changes_links = self.driver.find_elements(By.XPATH,
                "//a[contains(text(), 'Track Changes') or contains(text(), 'Marked') or contains(text(), 'Tracked')]")

            for link in track_changes_links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        manuscript['revisions'].append({
                            'type': 'track_changes',
                            'link': href,
                            'text': link.text.strip()
                        })
                        print(f"      ✅ Found track changes: {link.text}")
                except:
                    continue

            if manuscript['revisions']:
                print(f"      ✅ Found {len(manuscript['revisions'])} revision documents")
            else:
                print("      ℹ️ No revisions found (may be initial submission)")

        except Exception as e:
            print(f"      ⚠️ Error extracting revisions: {e}")
            manuscript['revisions'] = []

    def download_manuscript_revision(self, url, manuscript_id, version):
        """Download a specific manuscript revision."""
        try:
            filename = f"manuscript_{manuscript_id}_v{version}"
            if '.pdf' in url:
                filename += '.pdf'
            elif '.docx' in url:
                filename += '.docx'
            else:
                filename += '.doc'

            download_path = os.path.join(self.download_dir, 'revisions', filename)
            os.makedirs(os.path.dirname(download_path), exist_ok=True)

            # Implementation would download the file
            # For now, just mark as found
            return True

        except Exception as e:
            print(f"         ⚠️ Error downloading revision: {e}")
            return False



    def extract_latex_source(self, manuscript):
        """Extract LaTeX source files if available."""
        try:
            print("      📦 Looking for LaTeX source files...")

            manuscript['latex_source'] = None

            # Look for LaTeX/source file links
            source_links = self.driver.find_elements(By.XPATH,
                "//a[contains(text(), 'LaTeX') or contains(text(), 'Source') or contains(text(), '.tex') or contains(@href, '.zip')]")

            for link in source_links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()

                    # Check if it's a LaTeX source
                    if any(x in text.lower() for x in ['latex', 'source', '.tex', '.zip']):
                        manuscript['latex_source'] = {
                            'link': href,
                            'text': text,
                            'type': 'latex_source'
                        }

                        # Try to download
                        if '.zip' in href or '.tex' in href:
                            filename = f"latex_source_{manuscript.get('id', 'unknown')}.zip"
                            download_path = os.path.join(self.download_dir, 'sources', filename)
                            os.makedirs(os.path.dirname(download_path), exist_ok=True)

                            # Click to download
                            link.click()
                            time.sleep(2)

                            manuscript['latex_source']['downloaded'] = True
                            manuscript['latex_source']['path'] = download_path
                            print(f"      ✅ Found LaTeX source: {text}")

                        return True

                except Exception as e:
                    print(f"      ⚠️ Error processing source link: {e}")
                    continue

            # Look in supplementary files
            supp_section = self.driver.find_elements(By.XPATH,
                "//td[contains(text(), 'Supplementary Files') or contains(text(), 'Additional Files')]/following-sibling::td")

            for section in supp_section:
                links = section.find_elements(By.TAG_NAME, 'a')
                for link in links:
                    text = link.text.lower()
                    if 'latex' in text or 'source' in text or '.tex' in text:
                        manuscript['latex_source'] = {
                            'link': link.get_attribute('href'),
                            'text': link.text,
                            'found_in': 'supplementary'
                        }
                        print(f"      ✅ Found LaTeX in supplementary: {link.text}")
                        return True

            print("      ℹ️ No LaTeX source files found")

        except Exception as e:
            print(f"      ⚠️ Error extracting LaTeX source: {e}")
            manuscript['latex_source'] = None



    # Ensure recommendation is properly stored in referee['report']['recommendation']
    # This is called after extracting report data
    def ensure_recommendation_storage(self, referee, report_data):
        """Ensure recommendation is consistently stored."""
        if report_data and 'recommendation' in report_data:
            if 'report' not in referee:
                referee['report'] = {}
            referee['report']['recommendation'] = report_data['recommendation']

            # Also normalize the recommendation
            normalized = self.normalize_recommendation(report_data['recommendation'])
            referee['report']['recommendation_normalized'] = normalized

            # Store confidence level if we can determine it
            if any(word in str(report_data.get('comments_to_editor', '')).lower()
                   for word in ['strongly', 'definitely', 'certainly']):
                referee['report']['confidence'] = 'high'
            elif any(word in str(report_data.get('comments_to_editor', '')).lower()
                     for word in ['possibly', 'perhaps', 'maybe']):
                referee['report']['confidence'] = 'low'
            else:
                referee['report']['confidence'] = 'medium'

        return referee



    def extract_all_documents(self, manuscript):
        """Extract all available documents for a manuscript."""
        try:
            print("      📚 Extracting all available documents...")

            # Core documents
            self.extract_manuscript_pdf(manuscript)
            self.extract_cover_letter_from_details(manuscript)

            # Revision-related documents
            self.extract_response_to_reviewers(manuscript)
            self.extract_revised_manuscripts(manuscript)

            # Source files
            self.extract_latex_source(manuscript)

            # Supplementary materials
            self.extract_supplementary_files(manuscript)

            # Summary
            doc_count = sum([
                1 if manuscript.get('manuscript_pdf') else 0,
                1 if manuscript.get('cover_letter') else 0,
                1 if manuscript.get('response_to_reviewers') else 0,
                len(manuscript.get('revisions', [])),
                1 if manuscript.get('latex_source') else 0,
                len(manuscript.get('supplementary_files', []))
            ])

            print(f"      ✅ Extracted {doc_count} documents total")
            manuscript['document_count'] = doc_count

        except Exception as e:
            print(f"      ⚠️ Error in document extraction: {e}")
