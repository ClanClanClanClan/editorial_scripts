"""Tests for SIAM base _backfill_referee_dates_from_trail method."""

import pytest


class FakeSIAM:
    """Minimal stub to test _backfill_referee_dates_from_trail in isolation."""

    def _backfill_referee_dates_from_trail(self, manuscript):
        from core.siam_base import SIAMExtractor

        SIAMExtractor._backfill_referee_dates_from_trail(self, manuscript)

    def _normalize_referee_dates(self, referees):
        from core.siam_base import SIAMExtractor

        SIAMExtractor._normalize_referee_dates(self, referees)


@pytest.fixture
def siam():
    return FakeSIAM()


def _inv(to, date):
    return {
        "type": "reviewer_invitation",
        "event_type": "email",
        "to": to,
        "from": "editor@siam.org",
        "date": date,
    }


def _acc(from_field, date):
    return {
        "type": "reviewer_accepted",
        "event_type": "email",
        "to": "editor@siam.org",
        "from": from_field,
        "date": date,
    }


class TestBackfillByInvitationChain:
    def test_basic_invitation_acceptance_pairing(self, siam):
        ms = {
            "referees": [
                {"name": "Smith", "email": "smith@uni.edu", "section": "active"},
            ],
            "audit_trail": [
                _inv("smith@uni.edu", "2026-01-10"),
                _acc("system", "2026-01-15"),
            ],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["acceptance_date"] == "2026-01-15"
        assert ms["referees"][0]["contact_date"] == "2026-01-10"
        assert ms["referees"][0]["dates"]["agreed"] == "2026-01-15"
        assert ms["referees"][0]["dates"]["invited"] == "2026-01-10"


class TestBackfillByFromField:
    def test_match_by_exact_name(self, siam):
        ms = {
            "referees": [
                {"name": "Yang Shen", "email": "shen@test.edu", "section": "active"},
            ],
            "audit_trail": [
                _acc("Yang Shen", "2026-02-01"),
            ],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["acceptance_date"] == "2026-02-01"

    def test_match_by_surname(self, siam):
        ms = {
            "referees": [
                {"name": "Christoph Belak", "email": "belak@tum.de", "section": "active"},
            ],
            "audit_trail": [
                _acc("C. Belak", "2026-02-05"),
            ],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["acceptance_date"] == "2026-02-05"

    def test_match_by_email(self, siam):
        ms = {
            "referees": [
                {"name": "J. Doe", "email": "jdoe@uni.edu", "section": "active"},
            ],
            "audit_trail": [
                _acc("jdoe@uni.edu", "2026-03-01"),
            ],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["acceptance_date"] == "2026-03-01"

    def test_declined_not_matched(self, siam):
        ms = {
            "referees": [
                {
                    "name": "Declined Ref",
                    "email": "dec@uni.edu",
                    "section": "active",
                    "status": "Declined",
                },
            ],
            "audit_trail": [
                _acc("Declined Ref", "2026-02-01"),
            ],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert not ms["referees"][0].get("acceptance_date")

    def test_already_has_acceptance_not_overwritten(self, siam):
        ms = {
            "referees": [
                {
                    "name": "Existing",
                    "email": "ex@uni.edu",
                    "section": "active",
                    "acceptance_date": "2026-01-01",
                },
            ],
            "audit_trail": [
                _acc("Existing", "2026-02-01"),
            ],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["acceptance_date"] == "2026-01-01"


class TestDateNormalization:
    def test_contact_date_to_invited(self, siam):
        ms = {
            "referees": [
                {
                    "name": "A",
                    "email": "a@x.com",
                    "section": "active",
                    "contact_date": "2026-01-10",
                },
            ],
            "audit_trail": [],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["dates"]["invited"] == "2026-01-10"

    def test_acceptance_date_to_agreed(self, siam):
        ms = {
            "referees": [
                {
                    "name": "B",
                    "email": "b@x.com",
                    "section": "active",
                    "acceptance_date": "2026-01-15",
                },
            ],
            "audit_trail": [],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["dates"]["agreed"] == "2026-01-15"

    def test_due_date_to_due(self, siam):
        ms = {
            "referees": [
                {"name": "C", "email": "c@x.com", "section": "active", "due_date": "2026-03-01"},
            ],
            "audit_trail": [],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["dates"]["due"] == "2026-03-01"

    def test_received_date_to_returned(self, siam):
        ms = {
            "referees": [
                {
                    "name": "D",
                    "email": "d@x.com",
                    "section": "active",
                    "received_date": "2026-02-28",
                },
            ],
            "audit_trail": [],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["dates"]["returned"] == "2026-02-28"

    def test_existing_dates_not_overwritten(self, siam):
        ms = {
            "referees": [
                {
                    "name": "E",
                    "email": "e@x.com",
                    "section": "active",
                    "contact_date": "2026-01-10",
                    "dates": {"invited": "2026-01-05"},
                },
            ],
            "audit_trail": [],
        }
        siam._backfill_referee_dates_from_trail(ms)
        assert ms["referees"][0]["dates"]["invited"] == "2026-01-05"

    def test_all_four_fields_normalized(self, siam):
        ms = {
            "referees": [
                {
                    "name": "F",
                    "email": "f@x.com",
                    "section": "active",
                    "contact_date": "2026-01-10",
                    "acceptance_date": "2026-01-15",
                    "due_date": "2026-03-01",
                    "received_date": "2026-02-28",
                },
            ],
            "audit_trail": [],
        }
        siam._backfill_referee_dates_from_trail(ms)
        d = ms["referees"][0]["dates"]
        assert d["invited"] == "2026-01-10"
        assert d["agreed"] == "2026-01-15"
        assert d["due"] == "2026-03-01"
        assert d["returned"] == "2026-02-28"
