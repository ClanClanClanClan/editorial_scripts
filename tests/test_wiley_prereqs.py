"""Tests for the MF_WILEY attach-mode pre-flight check helpers.

Tests the pure-logic helpers (_classify_title) without invoking osascript.
Integration testing of the full script lives in the manual workflow.
"""

import importlib.util
import sys
from pathlib import Path

# Load scripts/check_wiley_prereqs.py as a module
SCRIPT_PATH = Path(__file__).parent.parent / "scripts" / "check_wiley_prereqs.py"
spec = importlib.util.spec_from_file_location("check_wiley_prereqs", SCRIPT_PATH)
preflight = importlib.util.module_from_spec(spec)
sys.modules["check_wiley_prereqs"] = preflight
spec.loader.exec_module(preflight)


class TestClassifyTitle:
    def test_dashboard_logged_in(self):
        assert preflight._classify_title("Dashboard | Wiley") == "logged_in"

    def test_manuscript_details_logged_in(self):
        assert preflight._classify_title("1384665 - Manuscript Details | Wiley") == "logged_in"

    def test_login_page(self):
        assert preflight._classify_title("Connexion - CONNECT") == "logged_out"
        assert preflight._classify_title("Connect - Sign in") == "logged_out"

    def test_login_page_non_english(self):
        # German, Spanish, Italian, Portuguese login flows
        assert preflight._classify_title("Anmelden - Wiley") == "logged_out"
        assert preflight._classify_title("Iniciar sesión") == "logged_out"
        assert preflight._classify_title("Conectar - Wiley") == "logged_out"
        assert preflight._classify_title("Accedi") == "logged_out"
        assert preflight._classify_title("Entrar") == "logged_out"

    def test_cloudflare_challenge(self):
        assert preflight._classify_title("Just a moment...") == "cloudflare"
        assert preflight._classify_title("Un instant...") == "cloudflare"
        # Cloudflare challenge takes precedence over login-marker words
        # ("connect" appears nowhere here, but verify the marker order is sane)
        assert preflight._classify_title("Verifying you are human") == "cloudflare"

    def test_logged_in_extra_pages(self):
        # Profile, Manuscripts list, Settings — all logged-in states
        assert preflight._classify_title("Profile | Wiley") == "logged_in"
        assert preflight._classify_title("Manuscripts | Wiley") == "logged_in"
        assert preflight._classify_title("Settings | Wiley") == "logged_in"
        assert preflight._classify_title("Research Exchange Review | Wiley") == "logged_in"

    def test_empty_title(self):
        assert preflight._classify_title("") == "empty"
        assert preflight._classify_title("   ") == "empty"
        assert preflight._classify_title(None) == "empty"

    def test_unknown_state(self):
        assert preflight._classify_title("Random Page") == "unknown"


class TestScriptIsExecutable:
    def test_script_exists(self):
        assert SCRIPT_PATH.exists()

    def test_script_has_main(self):
        assert hasattr(preflight, "main")

    def test_script_has_classify(self):
        assert hasattr(preflight, "_classify_title")
