"""Popup window handling extracted from legacy code."""

import time
import re
from typing import Optional, Dict, Any, List
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchWindowException, TimeoutException


class PopupHandler:
    """
    Handles popup windows for data extraction.
    
    Common pattern in ScholarOne: JavaScript popups for emails, reviews, etc.
    """
    
    def __init__(self, browser_manager):
        """
        Initialize popup handler.
        
        Args:
            browser_manager: SeleniumBrowserManager instance
        """
        self.browser = browser_manager
        self.driver = browser_manager.driver
        
    def extract_from_javascript_popup(self, popup_url: str) -> Optional[str]:
        """
        Extract content from JavaScript popup URL.
        
        Pattern: javascript:popWindow('url', 'window_name', width, height)
        
        Args:
            popup_url: JavaScript popup URL
            
        Returns:
            Extracted content or None
        """
        if not popup_url or 'javascript:' not in popup_url:
            return None
            
        try:
            # Store current window
            main_window = self.driver.current_window_handle
            
            # Execute JavaScript to open popup
            self.driver.execute_script(popup_url.replace('javascript:', ''))
            
            # Wait for popup
            time.sleep(2)
            
            # Switch to popup
            popup_content = None
            for window_handle in self.driver.window_handles:
                if window_handle != main_window:
                    self.driver.switch_to.window(window_handle)
                    
                    # Extract content
                    popup_content = self._extract_popup_content()
                    
                    # Close popup
                    self.driver.close()
                    break
                    
            # Return to main window
            self.driver.switch_to.window(main_window)
            
            return popup_content
            
        except Exception as e:
            print(f"Popup extraction failed: {e}")
            # Ensure we're back in main window
            try:
                self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return None
    
    def _extract_popup_content(self) -> Optional[str]:
        """
        Extract content from current popup window.
        
        Returns:
            Extracted content based on popup type
        """
        try:
            # Wait for content to load
            time.sleep(1)
            
            # Try different extraction patterns
            
            # 1. Email popup pattern
            email = self._extract_email_from_popup()
            if email:
                return email
                
            # 2. Review content pattern
            review = self._extract_review_content()
            if review:
                return review
                
            # 3. Abstract popup pattern
            abstract = self._extract_abstract_content()
            if abstract:
                return abstract
                
            # 4. Generic text extraction
            return self._extract_generic_text()
            
        except Exception as e:
            print(f"Content extraction failed: {e}")
            return None
    
    def _extract_email_from_popup(self) -> Optional[str]:
        """
        Extract email from popup window.
        
        Common pattern: Email displayed in popup for referees/authors
        
        Returns:
            Email address or None
        """
        email_patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]
        
        try:
            # Look for email in various locations
            
            # Check for mailto links
            mailto_links = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'mailto:')]")
            for link in mailto_links:
                href = link.get_attribute('href')
                if href:
                    email = href.replace('mailto:', '').split('?')[0]
                    if '@' in email:
                        return email.strip()
            
            # Check text content
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            for pattern in email_patterns:
                matches = re.findall(pattern, page_text)
                if matches:
                    # Return first valid email, filtering out system emails
                    for match in matches:
                        if '@' in match and '.' in match:
                            # Filter out system emails
                            if not any(skip in match.lower() for skip in ['noreply', 'donotreply', 'manuscriptcentral']):
                                return match.strip()
                            
        except:
            pass
            
        return None
    
    def _extract_review_content(self) -> Optional[Dict[str, Any]]:
        """
        Extract review/recommendation content from popup.
        
        Returns:
            Dictionary with review data or None
        """
        try:
            review_data = {}
            
            # Look for recommendation
            recommendation_patterns = [
                "Recommendation:",
                "Editorial Recommendation:",
                "Reviewer Recommendation:",
                "Decision:"
            ]
            
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            for pattern in recommendation_patterns:
                if pattern in page_text:
                    lines = page_text.split('\n')
                    for i, line in enumerate(lines):
                        if pattern in line:
                            # Get recommendation from same line or next line
                            if ':' in line:
                                review_data['recommendation'] = line.split(':', 1)[1].strip()
                            elif i + 1 < len(lines):
                                review_data['recommendation'] = lines[i + 1].strip()
                            break
            
            # Look for scores
            score_patterns = [
                r'Overall Rating:\s*(\d+)',
                r'Technical Quality:\s*(\d+)',
                r'Clarity:\s*(\d+)',
                r'Significance:\s*(\d+)',
                r'Originality:\s*(\d+)'
            ]
            
            for pattern in score_patterns:
                match = re.search(pattern, page_text)
                if match:
                    field_name = pattern.split(':')[0].lower().replace('\\s*', '').replace('(\\d+)', '')
                    review_data[field_name] = int(match.group(1))
            
            # Look for review text
            review_sections = [
                "Comments to Author:",
                "Review:",
                "Reviewer Comments:",
                "Detailed Comments:"
            ]
            
            for section in review_sections:
                if section in page_text:
                    # Extract text after section header
                    parts = page_text.split(section, 1)
                    if len(parts) > 1:
                        # Take text until next section or end
                        review_text = parts[1].strip()
                        # Truncate at next section if present
                        for other_section in review_sections:
                            if other_section in review_text and other_section != section:
                                review_text = review_text.split(other_section)[0].strip()
                        review_data['review_text'] = review_text[:2000]  # Limit length
                    break
            
            return review_data if review_data else None
            
        except:
            return None
    
    def _extract_abstract_content(self) -> Optional[str]:
        """
        Extract abstract from popup window.
        
        Returns:
            Abstract text or None
        """
        try:
            # Look for abstract markers
            abstract_markers = [
                "Abstract:",
                "ABSTRACT",
                "Summary:",
                "SUMMARY"
            ]
            
            page_text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            for marker in abstract_markers:
                if marker in page_text:
                    # Extract text after marker
                    parts = page_text.split(marker, 1)
                    if len(parts) > 1:
                        abstract = parts[1].strip()
                        
                        # Clean up - remove everything after common end markers
                        end_markers = [
                            "Keywords:",
                            "Key Words:",
                            "JEL Classification:",
                            "MSC Classification:",
                            "Mathematics Subject Classification:"
                        ]
                        
                        for end_marker in end_markers:
                            if end_marker in abstract:
                                abstract = abstract.split(end_marker)[0].strip()
                        
                        return abstract
                        
            # If no markers, but popup contains substantial text, might be abstract
            if len(page_text) > 200 and len(page_text) < 5000:
                # Check if it looks like abstract (has sentences)
                if '.' in page_text and len(page_text.split('.')) > 3:
                    return page_text.strip()
                    
        except:
            pass
            
        return None
    
    def _extract_generic_text(self) -> Optional[str]:
        """
        Generic text extraction from popup.
        
        Returns:
            Text content or None
        """
        try:
            # Get all text from body
            body_element = self.driver.find_element(By.TAG_NAME, 'body')
            text = body_element.text.strip()
            
            # Return if meaningful content
            if text and len(text) > 10:
                return text
                
        except:
            pass
            
        return None
    
    def extract_referee_history_popup(self, popup_url: str) -> Optional[List[Dict[str, Any]]]:
        """
        Extract referee history from popup.
        
        Args:
            popup_url: JavaScript popup URL for referee history
            
        Returns:
            List of history events or None
        """
        content = self.extract_from_javascript_popup(popup_url)
        if not content:
            return None
            
        history = []
        
        try:
            # Parse history events (common pattern: date - event)
            lines = content.split('\n')
            
            date_pattern = r'(\d{1,2}-\w{3}-\d{4})'
            
            for line in lines:
                match = re.search(date_pattern, line)
                if match:
                    date = match.group(1)
                    event = line.replace(date, '').strip(' -:')
                    
                    history.append({
                        'date': date,
                        'event': event
                    })
                    
        except:
            pass
            
        return history if history else None
    
    def extract_author_details_popup(self, popup_url: str) -> Optional[Dict[str, Any]]:
        """
        Extract author details from popup.
        
        Args:
            popup_url: JavaScript popup URL for author details
            
        Returns:
            Author details dictionary or None
        """
        content = self.extract_from_javascript_popup(popup_url)
        if not content:
            return None
            
        author_data = {}
        
        try:
            # Extract email
            email = self._extract_email_from_popup()
            if email:
                author_data['email'] = email
                
            # Extract affiliation
            if 'Affiliation:' in content:
                parts = content.split('Affiliation:', 1)
                if len(parts) > 1:
                    affiliation = parts[1].split('\n')[0].strip()
                    author_data['affiliation'] = affiliation
                    
            # Extract ORCID
            orcid_pattern = r'(?:orcid.org/)?(\d{4}-\d{4}-\d{4}-\d{3}[0-9X])'
            orcid_match = re.search(orcid_pattern, content)
            if orcid_match:
                author_data['orcid'] = orcid_match.group(1)
                
        except:
            pass
            
        return author_data if author_data else None