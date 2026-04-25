"""Tests for journal grouping (MF + MF_WILEY -> single 'Mathematical Finance' group).

These tests ensure that the soft-merge layer in output_schema.py works
correctly across the dashboard, action items, and cross-journal report.
"""

from core.output_schema import (
    JOURNAL_GROUP_DISPLAY,
    JOURNAL_GROUP_MAP,
    journal_group,
    journal_group_display,
)
from reporting.cross_journal_report import aggregate_by_group


class TestJournalGroupMap:
    def test_mf_and_mf_wiley_share_group(self):
        assert journal_group("mf") == "MF"
        assert journal_group("mf_wiley") == "MF"
        assert journal_group("MF") == "MF"
        assert journal_group("MF_WILEY") == "MF"

    def test_self_mapping_for_other_journals(self):
        assert journal_group("sicon") == "SICON"
        assert journal_group("mor") == "MOR"
        assert journal_group("naco") == "NACO"

    def test_unknown_journal_self_maps(self):
        assert journal_group("unknown_journal") == "UNKNOWN_JOURNAL"

    def test_empty_returns_empty(self):
        assert journal_group("") == ""

    def test_display_name_for_mf_group(self):
        assert journal_group_display("mf_wiley") == "Mathematical Finance"
        assert journal_group_display("mf") == "Mathematical Finance"

    def test_display_name_for_self_mapped(self):
        assert journal_group_display("sicon") == "SIAM Journal on Control and Optimization"

    def test_group_map_contents(self):
        assert JOURNAL_GROUP_MAP["mf"] == "MF"
        assert JOURNAL_GROUP_MAP["mf_wiley"] == "MF"
        # JOURNAL_GROUP_DISPLAY covers all 8 logical journals
        assert "MF" in JOURNAL_GROUP_DISPLAY
        assert JOURNAL_GROUP_DISPLAY["MF"] == "Mathematical Finance"


class TestAggregateByGroup:
    def test_mf_and_mf_wiley_combined(self):
        all_stats = [
            {
                "journal": "MF",
                "journal_name": "Mathematical Finance",
                "platform": "ScholarOne",
                "manuscripts": 1,
                "referees": 1,
                "referees_all": 1,
                "authors": 2,
                "enriched": 1,
                "total_people": 3,
                "extraction_date": "2026-02-15",
            },
            {
                "journal": "MF_WILEY",
                "journal_name": "Mathematical Finance",
                "platform": "Wiley ScienceConnect",
                "manuscripts": 2,
                "referees": 9,
                "referees_all": 9,
                "authors": 4,
                "enriched": 5,
                "total_people": 13,
                "extraction_date": "2026-04-24",
            },
        ]
        groups = aggregate_by_group(all_stats)
        assert len(groups) == 1
        g = groups[0]
        assert g["group"] == "MF"
        assert g["group_name"] == "Mathematical Finance"
        assert g["manuscripts"] == 3
        assert g["referees"] == 10
        assert g["authors"] == 6
        assert "ScholarOne" in g["platforms"]
        assert "Wiley ScienceConnect" in g["platforms"]
        assert "MF" in g["journals_in_group"]
        assert "MF_WILEY" in g["journals_in_group"]
        assert g["latest_extraction"] == "2026-04-24"

    def test_separate_groups_kept_separate(self):
        all_stats = [
            {
                "journal": "SICON",
                "platform": "SIAM",
                "manuscripts": 5,
                "referees": 14,
                "authors": 10,
                "enriched": 8,
                "total_people": 24,
                "extraction_date": "2026-04-19",
            },
            {
                "journal": "SIFIN",
                "platform": "SIAM",
                "manuscripts": 2,
                "referees": 4,
                "authors": 3,
                "enriched": 4,
                "total_people": 7,
                "extraction_date": "2026-04-19",
            },
        ]
        groups = aggregate_by_group(all_stats)
        assert len(groups) == 2
        codes = {g["group"] for g in groups}
        assert "SICON" in codes
        assert "SIFIN" in codes

    def test_empty_input(self):
        assert aggregate_by_group([]) == []

    def test_skips_none_entries(self):
        all_stats = [None, {"journal": "MF", "manuscripts": 1, "platform": "ScholarOne"}]
        groups = aggregate_by_group(all_stats)
        assert len(groups) == 1
        assert groups[0]["group"] == "MF"

    def test_enrichment_pct_computed(self):
        all_stats = [
            {
                "journal": "MF",
                "platform": "ScholarOne",
                "manuscripts": 1,
                "enriched": 5,
                "total_people": 10,
            },
        ]
        groups = aggregate_by_group(all_stats)
        assert groups[0]["enrichment_pct"] == 50.0


class TestActionItemsCarryGroup:
    def test_action_item_has_group_field(self):
        from reporting.action_items import RefereeAction

        action = RefereeAction(
            priority="high",
            action_type="overdue_report",
            journal="MF_WILEY",
            manuscript_id="1384665",
            manuscript_title="Test",
        )
        # Default empty until compute_action_items populates it
        assert action.journal_group == ""
        # After manual set
        action.journal_group = journal_group(action.journal)
        assert action.journal_group == "MF"
