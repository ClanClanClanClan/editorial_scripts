import os
import time
import logging
from abc import ABC, abstractmethod
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class JournalBase(ABC):
    """
    Abstract base class for all journal scrapers.
    """

    def __init__(self, driver):
        if driver is None:
            raise ValueError("A Selenium driver must be provided to JournalBase.")
        self.driver = driver
        # Default to ORCID login; subclasses may add more.
        self.ORCID_EMAIL = os.environ.get("ORCID_EMAIL")
        self.ORCID_PASSWORD = os.environ.get("ORCID_PASSWORD")
        if not (self.ORCID_EMAIL and self.ORCID_PASSWORD):
            logging.warning("ORCID credentials not set. If this journal doesn't use ORCID, this is safe to ignore.")

    @abstractmethod
    def get_url(self):
        """
        Return the main dashboard or login URL for the journal.
        """
        pass

    def login(self):
        """
        Default login: ORCID workflow with consent/cookie banner removal.
        Only allowed for SICON/SIFIN journals! All others must override.
        """
        if self.__class__.__name__ not in ("SICONJournal", "SIFINJournal"):
            raise NotImplementedError(
                f"Base ORCID login should NOT be called by {self.__class__.__name__}! "
                "Override login() in your subclass."
            )
        driver = self.driver
        logging.info("Using default ORCID login flow.")
        try:
            orcid_btn = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'orcid')]"))
            )
            orcid_btn.click()
            WebDriverWait(driver, 15).until(
                lambda d: "orcid.org" in d.current_url or d.find_elements(By.ID, "username-input")
            )
            self.remove_orcid_cookie_banner(max_wait=18)

            email_input = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.ID, "username-input"))
            )
            password_input = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.ID, "password"))
            )
            email_input.clear()
            email_input.send_keys(self.ORCID_EMAIL)
            password_input.clear()
            password_input.send_keys(self.ORCID_PASSWORD)

            btn_xpath = "//button[.//span[contains(text(), 'Sign in to ORCID')]]"
            conn_btn = WebDriverWait(driver, 12).until(
                EC.element_to_be_clickable((By.XPATH, btn_xpath))
            )
            conn_btn.click()
            self.remove_orcid_cookie_banner(max_wait=7)

            try:
                authorize_btn = WebDriverWait(driver, 7).until(
                    EC.element_to_be_clickable((By.ID, "authorize"))
                )
                authorize_btn.click()
            except Exception:
                pass

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'logout')]"))
            )
            logging.info("ORCID login successful.")
        except Exception as e:
            logging.error(f"ORCID login failed: {e}")
            raise

    def remove_cookie_banner(self):
        """
        Remove standard site cookie banners by element ID.
        """
        driver = self.driver
        for el_id in ["cookie-policy-layer", "cookie-policy-layer-bg"]:
            try:
                driver.execute_script(
                    f"var el = document.getElementById('{el_id}'); if (el) el.remove();"
                )
            except Exception:
                pass

    def remove_orcid_cookie_banner(self, max_wait=18):
        """
        Remove ORCID cookie/consent overlays if present.
        """
        driver = self.driver
        cookie_selectors = [
            '//button[contains(translate(., "ACEPTTURL", "aceptturl"), "accept all cookies")]',
            '//button[contains(text(), "Reject Unnecessary Cookies")]',
            '//button[contains(text(), "Reject all")]',
            '//button[contains(text(), "Reject")]',
            '//button[contains(text(), "OK")]',
            '//button[contains(text(), "Continue")]',
            '//button[contains(@id, "onetrust-reject-all-handler")]',
            '//button[contains(@id, "onetrust-accept-btn-handler")]',
        ]
        deadline = time.time() + max_wait
        while time.time() < deadline:
            for sel in cookie_selectors:
                try:
                    btns = driver.find_elements(By.XPATH, sel)
                    for btn in btns:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                except Exception:
                    continue
            overlays = driver.find_elements(
                By.CSS_SELECTOR,
                '#onetrust-banner-sdk, #onetrust-pc-sdk, #cookie-policy-layer, #cookie-policy-layer-bg'
            )
            if not any(ov.is_displayed() for ov in overlays):
                break

    @abstractmethod
    def scrape_manuscripts_and_emails(self):
        """
        Must be implemented by each journal subclass.
        Should return a list of manuscript dicts, each with all necessary referee data.
        """
        pass