from unittest.mock import MagicMock

from pipeline.conflict_checker import check_conflicts
from pipeline.desk_rejection import JOURNAL_SCOPE_KEYWORDS, assess_desk_rejection
from pipeline.referee_finder import _compute_relevance, _compute_topic_overlap
from pipeline.referee_pipeline import is_awaiting_referee


class TestIsAwaitingReferee:
    def test_siam_stage(self):
        ms = {
            "status": "Waiting for Potential Referee Assignment",
            "platform_specific": {
                "metadata": {"current_stage": "Waiting for Potential Referee Assignment"}
            },
        }
        assert is_awaiting_referee(ms, "SIAM") is True

    def test_siam_not_awaiting(self):
        ms = {
            "status": "All Referees Assigned",
            "platform_specific": {"metadata": {"current_stage": "All Referees Assigned"}},
        }
        assert is_awaiting_referee(ms, "SIAM") is False

    def test_scholarone_category(self):
        ms = {
            "status": "",
            "category": "Submitted Manuscripts Requiring Assignment to a Reviewer",
            "platform_specific": {},
        }
        assert is_awaiting_referee(ms, "ScholarOne") is True

    def test_scholarone_revised(self):
        ms = {
            "status": "",
            "category": "",
            "platform_specific": {
                "category_name": "Revised Manuscripts Requiring Assignment to a Reviewer"
            },
        }
        assert is_awaiting_referee(ms, "ScholarOne") is True

    def test_scholarone_not_awaiting(self):
        ms = {
            "status": "Under Review",
            "category": "",
            "platform_specific": {"category_name": "Manuscripts Under Review"},
        }
        assert is_awaiting_referee(ms, "ScholarOne") is False

    def test_em_under_review_no_referees(self):
        ms = {
            "status": "Under Review",
            "referees": [],
            "platform_specific": {},
        }
        assert is_awaiting_referee(ms, "Editorial Manager") is True

    def test_em_under_review_with_referees(self):
        ms = {
            "status": "Under Review",
            "referees": [{"name": "Smith", "status": "Awaiting Report"}],
            "platform_specific": {},
        }
        assert is_awaiting_referee(ms, "Editorial Manager") is False

    def test_editflow_under_review_no_refs(self):
        ms = {"status": "Under Review", "referees": [], "platform_specific": {}}
        assert is_awaiting_referee(ms, "EditFlow (MSP)") is True

    def test_gmail_new_submission(self):
        ms = {"status": "New Submission", "platform_specific": {}}
        assert is_awaiting_referee(ms, "Email (Gmail)") is True


class TestDeskRejection:
    def test_missing_abstract(self):
        ms = {"abstract": "", "keywords": ["control"], "authors": [], "title": "Test"}
        result = assess_desk_rejection(ms, "SICON")
        names = [s["signal_name"] for s in result["signals"]]
        assert "missing_abstract" in names

    def test_missing_keywords(self):
        ms = {"abstract": "A" * 100, "keywords": [], "authors": [], "title": "Test"}
        result = assess_desk_rejection(ms, "SICON")
        names = [s["signal_name"] for s in result["signals"]]
        assert "missing_keywords" in names

    def test_scope_match(self):
        ms = {
            "abstract": "We study optimal control of stochastic differential equations using dynamic programming.",
            "keywords": [
                "optimal control",
                "stochastic differential equation",
                "dynamic programming",
            ],
            "authors": [],
            "title": "Optimal Control of SDEs",
        }
        result = assess_desk_rejection(ms, "SICON")
        names = [s["signal_name"] for s in result["signals"]]
        assert "scope_match" in names
        assert result["should_desk_reject"] is False

    def test_scope_mismatch(self):
        ms = {
            "abstract": "We study the phylogenetic relationships among amphibian species in tropical ecosystems.",
            "keywords": ["phylogenetics", "amphibians", "biodiversity", "ecology"],
            "authors": [],
            "title": "Phylogenetics of Tropical Amphibians",
        }
        result = assess_desk_rejection(ms, "SICON")
        names = [s["signal_name"] for s in result["signals"]]
        assert "scope_mismatch" in names
        assert result["should_desk_reject"] is True

    def test_normal_paper_passes(self):
        ms = {
            "abstract": "We prove existence and uniqueness of solutions to a backward stochastic differential equation with Lipschitz coefficients.",
            "keywords": ["backward SDE", "BSDE", "stochastic control"],
            "authors": [
                {"name": "Smith", "web_profile": {"h_index": 10, "citation_count": 500}},
            ],
            "title": "BSDEs with Lipschitz Coefficients",
        }
        result = assess_desk_rejection(ms, "SICON")
        assert result["should_desk_reject"] is False

    def test_duplicate_submission(self):
        ms = {
            "abstract": "A" * 100,
            "keywords": ["control"],
            "authors": [],
            "title": "A Novel Approach to Stochastic Control",
            "manuscript_id": "M999",
        }
        other = {
            "manuscripts": [
                {
                    "title": "A Novel Approach to Stochastic Control",
                    "manuscript_id": "MOR-2025-001",
                }
            ]
        }
        result = assess_desk_rejection(ms, "SICON", all_journals_data={"mor": other})
        names = [s["signal_name"] for s in result["signals"]]
        assert "duplicate_submission" in names

    def test_freemail_signal(self):
        ms = {
            "abstract": "A" * 100,
            "keywords": ["control"],
            "title": "Test",
            "authors": [
                {
                    "name": "Smith",
                    "email": "smith@gmail.com",
                    "is_corresponding": True,
                    "web_profile": {},
                },
            ],
        }
        result = assess_desk_rejection(ms, "SICON")
        names = [s["signal_name"] for s in result["signals"]]
        assert "freemail_corresponding" in names


class TestConflictChecker:
    def _enricher(self):
        import requests
        from core.academic_apis import AcademicProfileEnricher

        return AcademicProfileEnricher(requests.Session())

    def test_is_author(self):
        enricher = self._enricher()
        candidate = {"name": "John Smith"}
        authors = [{"name": "John Smith", "institution": "MIT"}]
        conflicts = check_conflicts(candidate, authors, [], [], enricher)
        assert any("manuscript author" in c for c in conflicts)

    def test_same_institution(self):
        enricher = self._enricher()
        candidate = {"name": "Jane Doe", "institution": "ETH Zurich"}
        authors = [{"name": "John Smith", "institution": "ETH Zurich, Switzerland"}]
        conflicts = check_conflicts(candidate, authors, [], [], enricher)
        assert any("institution" in c.lower() for c in conflicts)

    def test_author_opposed(self):
        enricher = self._enricher()
        candidate = {"name": "Bob Jones", "email": "bob@example.com"}
        opposed = [{"name": "Bob Jones", "email": "bob@example.com"}]
        conflicts = check_conflicts(candidate, [], opposed, [], enricher)
        assert any("opposed" in c.lower() for c in conflicts)

    def test_no_conflicts(self):
        enricher = self._enricher()
        candidate = {"name": "Alice Brown", "institution": "Stanford"}
        authors = [{"name": "John Smith", "institution": "MIT"}]
        conflicts = check_conflicts(candidate, authors, [], [], enricher)
        assert len(conflicts) == 0

    def test_editor_conflict(self):
        enricher = self._enricher()
        candidate = {"name": "Jane Editor"}
        editors = [{"name": "Jane Editor"}]
        conflicts = check_conflicts(candidate, [], [], editors, enricher)
        assert any("editor" in c.lower() for c in conflicts)


class TestRelevanceScoring:
    def test_keyword_overlap_boosts_score(self):
        c1 = {
            "research_topics": ["stochastic control", "optimal stopping"],
            "source": "openalex_search",
            "relevant_papers": [],
        }
        c2 = {
            "research_topics": ["marine biology", "ecology"],
            "source": "openalex_search",
            "relevant_papers": [],
        }
        kw = ["stochastic control", "dynamic programming"]
        s1 = _compute_relevance(c1, kw, "Stochastic Control", "")
        s2 = _compute_relevance(c2, kw, "Stochastic Control", "")
        assert s1 > s2

    def test_author_suggested_bonus(self):
        c1 = {"research_topics": [], "source": "author_suggested", "relevant_papers": []}
        c2 = {"research_topics": [], "source": "openalex_search", "relevant_papers": []}
        s1 = _compute_relevance(c1, [], "Test", "")
        s2 = _compute_relevance(c2, [], "Test", "")
        assert s1 > s2

    def test_h_index_contributes(self):
        c1 = {
            "research_topics": [],
            "source": "openalex_search",
            "relevant_papers": [],
            "h_index": 25,
        }
        c2 = {
            "research_topics": [],
            "source": "openalex_search",
            "relevant_papers": [],
            "h_index": 0,
        }
        s1 = _compute_relevance(c1, [], "Test", "")
        s2 = _compute_relevance(c2, [], "Test", "")
        assert s1 > s2


class TestTopicOverlap:
    def test_matching_keywords(self):
        c = {"research_topics": ["Stochastic Control Theory", "Optimal Stopping Problems"]}
        kw = ["stochastic control", "dynamic programming"]
        overlap = _compute_topic_overlap(c, kw)
        assert "stochastic control" in overlap

    def test_no_match(self):
        c = {"research_topics": ["Marine Biology"]}
        kw = ["stochastic control"]
        overlap = _compute_topic_overlap(c, kw)
        assert len(overlap) == 0
