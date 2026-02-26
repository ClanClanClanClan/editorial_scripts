#!/usr/bin/env python3
"""Referee candidate search: OpenAlex, Semantic Scholar, historical DB, author suggestions."""

import json
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

import requests

from core.academic_apis import AcademicProfileEnricher

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"
JOURNALS = ["mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco"]


def find_referees(
    manuscript: dict,
    journal_code: str,
    enricher: AcademicProfileEnricher,
    session: requests.Session,
    max_candidates: int = 15,
    expertise_index=None,
    response_predictor=None,
) -> tuple:
    keywords = manuscript.get("keywords", [])
    title = manuscript.get("title", "")
    abstract = manuscript.get("abstract", "")
    authors = manuscript.get("authors", [])
    editors = manuscript.get("editors", [])
    author_names = {_normalize(a.get("name", "")) for a in authors if a.get("name")}

    rec = manuscript.get("referee_recommendations", {})
    if not rec:
        rec = (manuscript.get("platform_specific") or {}).get("referee_recommendations") or {}
    recommended = rec.get("recommended_referees", [])
    opposed = rec.get("opposed_referees", [])

    candidates = []
    seen_keys = set()
    api_calls = {"openalex": 0, "semantic_scholar": 0, "enrichment": 0}

    for ref in recommended:
        c = _make_candidate(ref, source="author_suggested")
        c["author_suggested"] = True
        key = _dedup_key(c)
        if key and key not in seen_keys and key not in author_names:
            seen_keys.add(key)
            candidates.append(c)

    if expertise_index is not None:
        try:
            idx_results = expertise_index.search(manuscript, k=30)
            for ref in idx_results:
                c = _make_candidate(ref, source="expertise_index")
                c["semantic_similarity"] = ref.get("semantic_similarity", 0.0)
                if ref.get("h_index"):
                    c["h_index"] = ref["h_index"]
                if ref.get("topics"):
                    c["research_topics"] = ref["topics"]
                key = _dedup_key(c)
                if key and key not in seen_keys and key not in author_names:
                    seen_keys.add(key)
                    candidates.append(c)
        except Exception:
            pass

    oa_candidates = _search_openalex_works(keywords, title, session, author_names)
    if oa_candidates is not None:
        api_calls["openalex"] += 1
    for c in oa_candidates or []:
        key = _dedup_key(c)
        if key and key not in seen_keys:
            seen_keys.add(key)
            candidates.append(c)

    s2_candidates = _search_semantic_scholar(keywords, title, session, author_names)
    if s2_candidates is not None:
        api_calls["semantic_scholar"] += 1
    for c in s2_candidates or []:
        key = _dedup_key(c)
        if key and key not in seen_keys:
            seen_keys.add(key)
            candidates.append(c)

    hist_candidates = _search_historical(keywords, journal_code, author_names)
    for c in hist_candidates:
        key = _dedup_key(c)
        if key and key not in seen_keys:
            seen_keys.add(key)
            candidates.append(c)

    for c in candidates:
        if not c.get("web_profile") and (c.get("name") or c.get("orcid")):
            try:
                profile = enricher.enrich(
                    c["name"],
                    orcid_id=c.get("orcid"),
                    institution=c.get("institution"),
                )
                api_calls["enrichment"] += 1
                if profile:
                    c["web_profile"] = profile
                    c["h_index"] = profile.get("h_index")
                    c["citation_count"] = profile.get("citation_count")
                    c["research_topics"] = profile.get("research_topics", [])
                    s2 = profile.get("semantic_scholar", {})
                    c["relevant_papers"] = s2.get("top_papers", [])[:5]
            except Exception:
                pass

    for c in candidates:
        c["relevance_score"] = _compute_relevance(
            c, keywords, title, abstract, response_predictor, journal_code, manuscript
        )
        c["topic_overlap"] = _compute_topic_overlap(c, keywords)

    candidates.sort(key=lambda x: -x["relevance_score"])
    return candidates[: max_candidates * 2], api_calls


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def _dedup_key(c: dict) -> str:
    email = (c.get("email") or "").lower().strip()
    if email:
        return email
    return _normalize(c.get("name", ""))


def _make_candidate(data: dict, source: str) -> dict:
    return {
        "name": data.get("name", ""),
        "email": data.get("email"),
        "institution": data.get("institution"),
        "country": data.get("country"),
        "orcid": data.get("orcid"),
        "source": source,
        "relevance_score": 0.0,
        "topic_overlap": [],
        "h_index": data.get("h_index"),
        "citation_count": data.get("citation_count"),
        "relevant_papers": [],
        "research_topics": data.get("research_topics", []),
        "conflicts": [],
        "is_conflicted": False,
        "author_suggested": False,
        "author_opposed": False,
        "web_profile": data.get("web_profile"),
    }


def _search_openalex_works(
    keywords: List[str],
    title: str,
    session: requests.Session,
    exclude_names: set,
) -> list:
    query = " ".join(keywords[:5]) if keywords else title[:100]
    if not query.strip():
        return []

    candidates = []
    try:
        time.sleep(0.3)
        resp = session.get(
            "https://api.openalex.org/works",
            params={
                "search": query,
                "filter": "type:journal-article,publication_year:>2019",
                "per_page": 25,
                "sort": "relevance_score:desc",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        for work in resp.json().get("results", []):
            for authorship in work.get("authorships", []):
                author = authorship.get("author", {})
                name = author.get("display_name", "")
                if not name or _normalize(name) in exclude_names:
                    continue

                orcid_url = author.get("orcid")
                orcid = None
                if orcid_url and "orcid.org/" in str(orcid_url):
                    orcid = orcid_url.split("orcid.org/")[-1]

                c = _make_candidate(
                    {
                        "name": name,
                        "orcid": orcid,
                    },
                    source="openalex_search",
                )

                insts = authorship.get("institutions", [])
                if insts:
                    c["institution"] = insts[0].get("display_name")
                    c["country"] = insts[0].get("country_code")

                candidates.append(c)

    except Exception as e:
        print(f"   [OpenAlex works] search error: {e}")

    return candidates


def _search_semantic_scholar(
    keywords: List[str],
    title: str,
    session: requests.Session,
    exclude_names: set,
) -> list:
    query = title[:200] if title else " ".join(keywords[:5])
    if not query.strip():
        return []

    candidates = []
    try:
        time.sleep(0.6)
        resp = session.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params={
                "query": query,
                "fields": "title,authors",
                "limit": 10,
            },
            timeout=15,
        )
        if resp.status_code != 200:
            return []

        for paper in resp.json().get("data", []):
            for author in paper.get("authors", []):
                name = author.get("name", "")
                if not name or _normalize(name) in exclude_names:
                    continue
                c = _make_candidate({"name": name}, source="semantic_scholar_search")
                candidates.append(c)

    except Exception as e:
        print(f"   [S2 papers] search error: {e}")

    return candidates


def _search_historical(
    keywords: List[str],
    current_journal: str,
    exclude_names: set,
) -> list:
    if not keywords:
        return []

    kw_lower = {k.lower() for k in keywords}
    candidates = []

    for journal in JOURNALS:
        journal_dir = OUTPUTS_DIR / journal
        if not journal_dir.exists():
            continue

        files = sorted(journal_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
        latest = None
        for f in files:
            if (
                "BASELINE" not in f.name
                and "debug" not in str(f)
                and "recommendation" not in str(f)
            ):
                latest = f
                break
        if not latest:
            continue

        try:
            with open(latest) as _f:
                data = json.load(_f)
        except (json.JSONDecodeError, OSError):
            continue

        for ms in data.get("manuscripts", []):
            ms_kws = {k.lower() for k in ms.get("keywords", [])}
            overlap = kw_lower & ms_kws
            if not overlap:
                continue

            for ref in ms.get("referees", []):
                name = ref.get("name", "")
                if not name or _normalize(name) in exclude_names:
                    continue

                c = _make_candidate(
                    {
                        "name": name,
                        "email": ref.get("email"),
                        "institution": ref.get("institution"),
                        "orcid": ref.get("orcid"),
                        "web_profile": ref.get("web_profile"),
                        "h_index": (ref.get("web_profile") or {}).get("h_index"),
                        "citation_count": (ref.get("web_profile") or {}).get("citation_count"),
                        "research_topics": (ref.get("web_profile") or {}).get(
                            "research_topics", []
                        ),
                    },
                    source="historical_referee",
                )
                c["_hist_journal"] = journal.upper()
                c["_hist_ms"] = ms.get("manuscript_id", "")
                c["_hist_overlap"] = list(overlap)
                candidates.append(c)

    return candidates


def _compute_relevance(
    candidate: dict,
    keywords: list,
    title: str,
    abstract: str,
    response_predictor=None,
    journal_code: str = None,
    manuscript: dict = None,
) -> float:
    # Spec weights: 30% topic, 25% publication, 15% seniority, 15% source trust, 15% recency
    topic_score = 0.0
    semantic_sim = candidate.get("semantic_similarity")
    if semantic_sim is not None:
        topic_score = min(1.0, max(0.0, semantic_sim))
    else:
        topics = candidate.get("research_topics", [])
        if topics and keywords:
            kw_words = set()
            for k in keywords:
                kw_words.update(k.lower().split())
            topic_words = set()
            for t in topics:
                topic_words.update(t.lower().split())
            common = kw_words & topic_words
            union = kw_words | topic_words
            if union:
                topic_score = min(1.0, len(common) / len(union) * 3)

    pub_score = 0.0
    papers = candidate.get("relevant_papers", [])
    if papers and title:
        title_words = set(title.lower().split())
        best = 0.0
        for p in papers:
            ptitle = (p.get("title") or "").lower()
            if not ptitle:
                continue
            p_words = set(ptitle.split())
            common = title_words & p_words
            union = title_words | p_words
            if union:
                best = max(best, len(common) / len(union))
        pub_score = min(1.0, best * 3)

    h = candidate.get("h_index") or 0
    seniority_score = min(1.0, h / 30)

    source_trust = {
        "author_suggested": 1.0,
        "expertise_index": 0.85,
        "historical_referee": 0.7,
        "openalex_search": 0.4,
        "semantic_scholar_search": 0.4,
    }
    trust_score = source_trust.get(candidate.get("source", ""), 0.3)

    recency_score = 0.0
    if papers:
        years = [p.get("year") or 0 for p in papers]
        max_year = max(years) if years else 0
        if max_year >= 2024:
            recency_score = 1.0
        elif max_year >= 2022:
            recency_score = 0.6
        elif max_year >= 2020:
            recency_score = 0.3

    score = (
        0.30 * topic_score
        + 0.25 * pub_score
        + 0.15 * seniority_score
        + 0.15 * trust_score
        + 0.15 * recency_score
    )

    if response_predictor is not None and manuscript is not None:
        try:
            p_accept = response_predictor.predict_for_candidate(
                candidate, manuscript, journal_code or ""
            )
            score += 0.05 * p_accept
        except Exception:
            pass

    return round(min(1.0, score), 3)


def _compute_topic_overlap(candidate: dict, keywords: list) -> list:
    if not keywords:
        return []
    topics = candidate.get("research_topics", [])
    if not topics:
        return []

    kw_lower = {k.lower() for k in keywords}
    overlaps = []
    for kw in kw_lower:
        kw_parts = set(kw.split())
        for t in topics:
            t_parts = set(t.lower().split())
            if kw_parts & t_parts:
                overlaps.append(kw)
                break
    return overlaps
