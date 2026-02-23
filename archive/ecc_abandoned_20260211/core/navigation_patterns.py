"""Navigation patterns for journal platforms.

Provides reusable navigation components for moving through
manuscript systems, handling tabs, pagination, and complex
navigation flows.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

from selenium.common.exceptions import (
    NoSuchElementException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .browser_manager import BrowserManager
from .error_handling import SafeExecutor
from .logging_system import ExtractorLogger, LogCategory
from .retry_strategies import RetryConfigs, retry


class NavigationTarget(Enum):
    """Common navigation targets in manuscript systems."""

    DASHBOARD = "dashboard"
    MANUSCRIPT_LIST = "manuscript_list"
    MANUSCRIPT_DETAILS = "manuscript_details"
    REFEREE_CENTER = "referee_center"
    AUTHOR_CENTER = "author_center"
    EDITOR_CENTER = "editor_center"
    REVIEW_DETAILS = "review_details"
    AUDIT_TRAIL = "audit_trail"
    DOCUMENTS = "documents"
    CORRESPONDENCE = "correspondence"


@dataclass
class NavigationContext:
    """Context for navigation operations."""

    current_page: str
    target_page: str
    manuscript_id: str | None = None
    category: str | None = None
    page_number: int = 1
    total_pages: int | None = None
    breadcrumbs: list[str] = None

    def __post_init__(self):
        if self.breadcrumbs is None:
            self.breadcrumbs = []


class NavigationStrategy(ABC):
    """Abstract base for navigation strategies."""

    @abstractmethod
    def navigate(self, browser: BrowserManager, context: NavigationContext) -> bool:
        """Execute navigation strategy."""
        pass


class TabNavigationStrategy(NavigationStrategy):
    """Navigation using tabs."""

    def navigate(self, browser: BrowserManager, context: NavigationContext) -> bool:
        """
        Navigate using tab interface.

        Args:
            browser: Browser manager instance
            context: Navigation context

        Returns:
            True if navigation successful
        """
        try:
            # Common tab selectors
            tab_selectors = [
                f"//a[contains(@class, 'tab') and contains(text(), '{context.target_page}')]",
                f"//li[@class='tab']//a[contains(text(), '{context.target_page}')]",
                f"//div[@class='tabs']//a[contains(text(), '{context.target_page}')]",
                f"//ul[@class='nav-tabs']//a[contains(text(), '{context.target_page}')]",
            ]

            for selector in tab_selectors:
                try:
                    tab_element = browser.driver.find_element(By.XPATH, selector)
                    browser.safe_click(tab_element)
                    time.sleep(1)
                    return True
                except NoSuchElementException:
                    continue

            return False

        except Exception:
            return False


class LinkNavigationStrategy(NavigationStrategy):
    """Navigation using direct links."""

    def navigate(self, browser: BrowserManager, context: NavigationContext) -> bool:
        """
        Navigate using direct link.

        Args:
            browser: Browser manager instance
            context: Navigation context

        Returns:
            True if navigation successful
        """
        try:
            # Try to find link by text
            link = browser.driver.find_element(By.LINK_TEXT, context.target_page)
            browser.safe_click(link)
            return True

        except NoSuchElementException:
            # Try partial link text
            try:
                link = browser.driver.find_element(By.PARTIAL_LINK_TEXT, context.target_page)
                browser.safe_click(link)
                return True
            except Exception:
                return False


class Navigator:
    """Main navigation handler for manuscript systems."""

    def __init__(
        self,
        browser: BrowserManager,
        logger: ExtractorLogger | None = None,
        safe_executor: SafeExecutor | None = None,
    ):
        """
        Initialize navigator.

        Args:
            browser: Browser manager instance
            logger: Logger instance
            safe_executor: Safe executor for error handling
        """
        self.browser = browser
        self.logger = logger or ExtractorLogger("navigator")
        self.safe_executor = safe_executor or SafeExecutor(self.logger.logger)
        self.context = NavigationContext("home", "home")
        self.navigation_history: list[NavigationContext] = []

    @retry(config=RetryConfigs.NAVIGATION)
    def navigate_to_section(
        self, target: NavigationTarget, manuscript_id: str | None = None
    ) -> bool:
        """
        Navigate to a specific section.

        Args:
            target: Target section
            manuscript_id: Optional manuscript ID for context

        Returns:
            True if navigation successful
        """
        self.logger.enter_context(f"navigate_{target.value}")

        try:
            # Store current context
            self.navigation_history.append(self.context)

            # Create new context
            new_context = NavigationContext(
                current_page=self.context.target_page,
                target_page=target.value,
                manuscript_id=manuscript_id,
            )

            # Execute navigation based on target
            success = self._execute_navigation(target, new_context)

            if success:
                self.context = new_context
                self.logger.success(f"Navigated to {target.value}", LogCategory.NAVIGATION)

            return success

        finally:
            self.logger.exit_context(success=True)

    def _execute_navigation(self, target: NavigationTarget, context: NavigationContext) -> bool:
        """
        Execute navigation based on target type.

        Args:
            target: Navigation target
            context: Navigation context

        Returns:
            True if successful
        """
        navigation_map = {
            NavigationTarget.DASHBOARD: self._navigate_dashboard,
            NavigationTarget.MANUSCRIPT_LIST: self._navigate_manuscript_list,
            NavigationTarget.MANUSCRIPT_DETAILS: self._navigate_manuscript_details,
            NavigationTarget.REFEREE_CENTER: self._navigate_referee_center,
            NavigationTarget.EDITOR_CENTER: self._navigate_editor_center,
            NavigationTarget.AUDIT_TRAIL: self._navigate_audit_trail,
            NavigationTarget.DOCUMENTS: self._navigate_documents,
        }

        nav_func = navigation_map.get(target)
        if nav_func:
            return nav_func(context)

        # Fallback to generic navigation
        return self._generic_navigation(context)

    def _navigate_dashboard(self, context: NavigationContext) -> bool:
        """Navigate to dashboard."""
        try:
            # Look for dashboard links
            dashboard_links = [
                "//a[contains(text(), 'Dashboard')]",
                "//a[contains(text(), 'Home')]",
                "//a[contains(@href, 'dashboard')]",
                "//a[contains(@href, 'HOME')]",
            ]

            for xpath in dashboard_links:
                try:
                    link = self.browser.driver.find_element(By.XPATH, xpath)
                    self.browser.safe_click(link)
                    time.sleep(2)
                    return True
                except NoSuchElementException:
                    continue

            return False

        except Exception as e:
            self.logger.error(f"Dashboard navigation failed: {e}")
            return False

    def _navigate_manuscript_list(self, context: NavigationContext) -> bool:
        """Navigate to manuscript list."""
        try:
            # Look for manuscript list links
            list_links = [
                "//a[contains(text(), 'Manuscripts')]",
                "//a[contains(text(), 'View Submissions')]",
                "//a[contains(@href, 'MANUSCRIPTS')]",
                "//a[contains(@href, 'submissions')]",
            ]

            for xpath in list_links:
                try:
                    link = self.browser.driver.find_element(By.XPATH, xpath)
                    self.browser.safe_click(link)
                    time.sleep(2)
                    return True
                except NoSuchElementException:
                    continue

            return False

        except Exception:
            return False

    def _navigate_manuscript_details(self, context: NavigationContext) -> bool:
        """Navigate to manuscript details page."""
        if not context.manuscript_id:
            self.logger.error("Manuscript ID required for details navigation")
            return False

        try:
            # Find manuscript link
            manuscript_link = self.browser.driver.find_element(
                By.XPATH, f"//a[contains(text(), '{context.manuscript_id}')]"
            )
            self.browser.safe_click(manuscript_link)
            time.sleep(2)
            return True

        except NoSuchElementException:
            self.logger.error(f"Manuscript link not found: {context.manuscript_id}")
            return False

    def _navigate_referee_center(self, context: NavigationContext) -> bool:
        """Navigate to referee/reviewer center."""
        try:
            referee_links = [
                "//a[contains(text(), 'Associate Editor Center')]",
                "//a[contains(text(), 'Referee Center')]",
                "//a[contains(text(), 'Reviewer Center')]",
                "//a[contains(@href, 'ASSOCIATE_EDITOR')]",
                "//a[contains(@href, 'REFEREE')]",
            ]

            for xpath in referee_links:
                try:
                    link = self.browser.driver.find_element(By.XPATH, xpath)
                    self.browser.safe_click(link)
                    time.sleep(2)
                    return True
                except NoSuchElementException:
                    continue

            return False

        except Exception:
            return False

    def _navigate_editor_center(self, context: NavigationContext) -> bool:
        """Navigate to editor center."""
        try:
            editor_links = [
                "//a[contains(text(), 'Editor Center')]",
                "//a[contains(text(), 'Editorial Center')]",
                "//a[contains(@href, 'EDITOR')]",
            ]

            for xpath in editor_links:
                try:
                    link = self.browser.driver.find_element(By.XPATH, xpath)
                    self.browser.safe_click(link)
                    time.sleep(2)
                    return True
                except NoSuchElementException:
                    continue

            return False

        except Exception:
            return False

    def _navigate_audit_trail(self, context: NavigationContext) -> bool:
        """Navigate to audit trail/history."""
        try:
            # Try tab navigation first
            tab_strategy = TabNavigationStrategy()
            context.target_page = "Audit Trail"
            if tab_strategy.navigate(self.browser, context):
                return True

            # Try direct link
            audit_links = [
                "//a[contains(text(), 'Audit Trail')]",
                "//a[contains(text(), 'History')]",
                "//a[contains(text(), 'Timeline')]",
                "//a[contains(@href, 'AUDIT')]",
                "//a[contains(@href, 'HISTORY')]",
            ]

            for xpath in audit_links:
                try:
                    link = self.browser.driver.find_element(By.XPATH, xpath)
                    self.browser.safe_click(link)
                    time.sleep(2)
                    return True
                except NoSuchElementException:
                    continue

            return False

        except Exception:
            return False

    def _navigate_documents(self, context: NavigationContext) -> bool:
        """Navigate to documents section."""
        try:
            # Try tab navigation
            tab_strategy = TabNavigationStrategy()
            context.target_page = "Documents"
            if tab_strategy.navigate(self.browser, context):
                return True

            # Try direct link
            doc_links = [
                "//a[contains(text(), 'Documents')]",
                "//a[contains(text(), 'Files')]",
                "//a[contains(@href, 'DOCUMENTS')]",
            ]

            for xpath in doc_links:
                try:
                    link = self.browser.driver.find_element(By.XPATH, xpath)
                    self.browser.safe_click(link)
                    time.sleep(2)
                    return True
                except NoSuchElementException:
                    continue

            return False

        except Exception:
            return False

    def _generic_navigation(self, context: NavigationContext) -> bool:
        """Generic navigation fallback."""
        # Try tab strategy
        tab_strategy = TabNavigationStrategy()
        if tab_strategy.navigate(self.browser, context):
            return True

        # Try link strategy
        link_strategy = LinkNavigationStrategy()
        if link_strategy.navigate(self.browser, context):
            return True

        self.logger.warning(f"Failed to navigate to {context.target_page}")
        return False

    def navigate_pagination(self, page_number: int) -> bool:
        """
        Navigate to specific page in paginated content.

        Args:
            page_number: Target page number

        Returns:
            True if navigation successful
        """
        try:
            # Look for page number link
            page_link = self.browser.driver.find_element(By.XPATH, f"//a[text()='{page_number}']")
            self.browser.safe_click(page_link)
            time.sleep(1)
            return True

        except NoSuchElementException:
            # Try input field approach
            try:
                page_input = self.browser.driver.find_element(
                    By.XPATH, "//input[@type='text' and contains(@name, 'page')]"
                )
                page_input.clear()
                page_input.send_keys(str(page_number))
                page_input.send_keys(Keys.RETURN)
                time.sleep(1)
                return True
            except Exception:
                return False

    def navigate_next(self) -> bool:
        """Navigate to next item/page."""
        try:
            next_buttons = [
                "//a[contains(text(), 'Next')]",
                "//button[contains(text(), 'Next')]",
                "//a[contains(@class, 'next')]",
                "//a[text()='>']",
            ]

            for xpath in next_buttons:
                try:
                    button = self.browser.driver.find_element(By.XPATH, xpath)
                    if button.is_enabled():
                        self.browser.safe_click(button)
                        time.sleep(1)
                        return True
                except NoSuchElementException:
                    continue

            return False

        except Exception:
            return False

    def navigate_previous(self) -> bool:
        """Navigate to previous item/page."""
        try:
            prev_buttons = [
                "//a[contains(text(), 'Previous')]",
                "//button[contains(text(), 'Previous')]",
                "//a[contains(@class, 'prev')]",
                "//a[text()='<']",
            ]

            for xpath in prev_buttons:
                try:
                    button = self.browser.driver.find_element(By.XPATH, xpath)
                    if button.is_enabled():
                        self.browser.safe_click(button)
                        time.sleep(1)
                        return True
                except NoSuchElementException:
                    continue

            return False

        except Exception:
            return False

    def navigate_back(self) -> bool:
        """Navigate back to previous page."""
        if self.navigation_history:
            previous_context = self.navigation_history.pop()
            self.context = previous_context
            self.browser.driver.back()
            time.sleep(1)
            return True
        return False

    def get_current_location(self) -> str:
        """
        Get current navigation location.

        Returns:
            Current page identifier
        """
        return self.context.current_page
