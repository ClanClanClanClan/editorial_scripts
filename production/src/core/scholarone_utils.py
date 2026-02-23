#!/usr/bin/env python3
"""
Shared utilities for ScholarOne extractors (MF, MOR).
"""

import time
import random
import re
from datetime import datetime
from pathlib import Path
from functools import wraps
from typing import Callable, Optional

from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By


def with_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (
                    TimeoutException,
                    NoSuchElementException,
                    WebDriverException,
                    StaleElementReferenceException,
                ) as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = delay * (backoff**attempt)
                        print(f"   ⚠️ {func.__name__} attempt {attempt + 1} failed: {str(e)[:50]}")
                        print(f"      Retrying in {wait_time:.1f} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"   ❌ {func.__name__} failed after {max_attempts} attempts")
                except Exception as e:
                    print(f"   ❌ {func.__name__} failed with unrecoverable error: {str(e)[:100]}")
                    raise

            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator


def safe_click(driver, element) -> bool:
    if not element:
        return False
    try:
        element.click()
        return True
    except Exception:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", element)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            return False


def safe_get_text(element) -> str:
    if not element:
        return ""
    try:
        return element.text.strip()
    except Exception:
        try:
            return element.get_attribute("textContent").strip()
        except Exception:
            return ""


def safe_array_access(array: list, index: int, default=None):
    try:
        if array and 0 <= index < len(array):
            return array[index]
    except Exception:
        pass
    return default


def safe_int(value, default=0):
    try:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return int(value)
        value = str(value).strip().replace(",", "")
        if not value:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default


def smart_wait(seconds: float = 1.0):
    wait_time = seconds + random.uniform(-0.2, 0.5)
    time.sleep(max(0.5, wait_time))


def parse_date(d_str: str) -> Optional[datetime]:
    if not d_str:
        return None
    for fmt in ("%d-%b-%Y", "%d %b %Y", "%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(d_str.strip(), fmt)
        except ValueError:
            continue
    return None


def parse_ev_date(ds: str) -> Optional[datetime]:
    if not ds:
        return None
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(ds[:11].strip(), fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(ds.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def capture_page(
    driver, journal_code: str, page_type: str, manuscript_id: str = "", is_popup: bool = False
):
    try:
        debug_dir = Path(__file__).parent.parent.parent.parent / "dev" / "html_captures"
        debug_dir.mkdir(parents=True, exist_ok=True)
        suffix = f"_{manuscript_id}" if manuscript_id else ""
        filename = f"{journal_code.lower()}_{page_type}{suffix}.html"
        with open(debug_dir / filename, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"      💾 Captured: {filename}")
        if is_popup:
            frames = driver.find_elements(By.TAG_NAME, "frame")
            for i, frame in enumerate(frames):
                try:
                    frame_name = frame.get_attribute("name") or f"frame{i}"
                    driver.switch_to.frame(frame)
                    frame_filename = f"{journal_code.lower()}_{page_type}{suffix}_{frame_name}.html"
                    with open(debug_dir / frame_filename, "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    driver.switch_to.default_content()
                except Exception:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
    except Exception:
        pass
