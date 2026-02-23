from unittest.mock import MagicMock, patch

from core.web_enrichment import enrich_people_from_web


class TestOrcidIdExtraction:
    def test_url_to_bare_id(self):
        person = {"name": "Smith", "orcid": "https://orcid.org/0000-0001-2345-6789"}
        data = {"referees": [person]}
        enrich_people_from_web(data, lambda *a: None, lambda *a: None)
        assert person["orcid"] == "0000-0001-2345-6789"

    def test_bare_id_passthrough(self):
        person = {"name": "Smith", "orcid": "0000-0001-2345-6789"}
        data = {"referees": [person]}
        enrich_people_from_web(data, lambda *a: None, lambda *a: None)
        assert person["orcid"] == "0000-0001-2345-6789"

    def test_invalid_orcid_not_written(self):
        person = {"name": "Smith", "orcid": "invalid"}
        data = {"referees": [person]}
        enrich_people_from_web(data, lambda *a: None, lambda *a: None)
        assert person["orcid"] == "invalid"


class TestCacheHit:
    def test_cache_hit_skips_network(self):
        cached = {"recent_publications": [{"title": "Cached Paper"}]}
        get_cache = MagicMock(return_value=cached)
        save_cache = MagicMock()
        person = {"name": "Smith"}
        data = {"referees": [person]}

        with patch("core.web_enrichment.requests") as _mock_requests:  # noqa: F841
            result = enrich_people_from_web(data, get_cache, save_cache)

        assert person["web_profile"] == cached
        assert person["web_profile_source"] == "cache"
        save_cache.assert_not_called()
        assert result == 1

    def test_empty_people_returns_zero(self):
        result = enrich_people_from_web(
            {"referees": [], "authors": []}, lambda *a: None, lambda *a: None
        )
        assert result == 0


class TestNameParsing:
    def test_comma_format(self):
        person = {"name": "Smith, John", "institution": "MIT"}
        data = {"authors": [person]}
        get_cache = MagicMock(return_value=None)
        save_cache = MagicMock()
        with patch("core.web_enrichment.requests"):
            enrich_people_from_web(data, get_cache, save_cache)
        get_cache.assert_called_once_with("Smith, John", "MIT", "")


class TestAuthorFallbackProfile:
    def test_author_gets_meta_profile(self):
        person = {
            "name": "Smith",
            "institution": "MIT",
            "department": "Math",
            "country": "US",
            "email": "smith@mit.edu",
        }
        data = {"authors": [person]}
        get_cache = MagicMock(return_value=None)
        save_cache = MagicMock()

        with patch("core.web_enrichment.requests") as mock_req:
            mock_session = MagicMock()
            mock_session.get.return_value = MagicMock(status_code=404)
            mock_req.Session.return_value = mock_session
            enrich_people_from_web(data, get_cache, save_cache, platform_label="test_meta")

        profile = person["web_profile"]
        assert profile["source"] == "test_meta"
        assert profile["institution"] == "MIT"
        assert profile["department"] == "Math"
        assert profile["country"] == "US"
        assert profile["email_domain"] == "mit.edu"

    def test_referee_no_fallback(self):
        person = {"name": "Smith", "institution": "MIT"}
        data = {"referees": [person]}
        get_cache = MagicMock(return_value=None)
        save_cache = MagicMock()

        with patch("core.web_enrichment.requests") as mock_req:
            mock_session = MagicMock()
            mock_session.get.return_value = MagicMock(status_code=404)
            mock_req.Session.return_value = mock_session
            enrich_people_from_web(data, get_cache, save_cache)

        assert "web_profile" not in person
