#!/usr/bin/env python3
"""Referee candidate search: OpenAlex, Semantic Scholar, historical DB, author suggestions."""

import datetime
import json
import time

import requests
from core.academic_apis import AcademicProfileEnricher

from pipeline import H_INDEX_CAP, JOURNALS, OUTPUTS_DIR
from pipeline import normalize_name_orderless as normalize_name


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
    author_names = {normalize_name(a.get("name", "")) for a in authors if a.get("name")}

    rec = manuscript.get("referee_recommendations", {})
    if not rec:
        rec = (manuscript.get("platform_specific") or {}).get("referee_recommendations") or {}
    recommended = rec.get("recommended_referees", [])

    candidates = []
    seen_keys = set()
    api_calls = {"openalex": 0, "semantic_scholar": 0, "enrichment": 0}

    for ref in recommended:
        c = _make_candidate(ref, source="author_suggested")
        c["author_suggested"] = True
        if not _is_duplicate(c, seen_keys, author_names):
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
                if not _is_duplicate(c, seen_keys, author_names):
                    candidates.append(c)
        except (ValueError, RuntimeError) as e:
            print(f"   Warning: expertise_index search failed: {e}")

    oa_candidates = _search_openalex_works(keywords, title, session, author_names)
    if oa_candidates is not None:
        api_calls["openalex"] += 1
    for c in oa_candidates or []:
        if not _is_duplicate(c, seen_keys):
            candidates.append(c)

    s2_candidates = _search_semantic_scholar(keywords, title, session, author_names)
    if s2_candidates is not None:
        api_calls["semantic_scholar"] += 1
    for c in s2_candidates or []:
        if not _is_duplicate(c, seen_keys):
            candidates.append(c)

    hist_candidates = _search_historical(keywords, journal_code, author_names)
    for c in hist_candidates:
        if not _is_duplicate(c, seen_keys):
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
            except (requests.RequestException, ValueError, RuntimeError) as e:
                print(f"   Warning: enrichment failed for {c.get('name', 'unknown')}: {e}")

    for c in candidates:
        c["relevance_score"] = _compute_relevance(
            c, keywords, title, abstract, response_predictor, journal_code, manuscript
        )
        c["topic_overlap"] = _compute_topic_overlap(c, keywords)

    candidates.sort(key=lambda x: -x["relevance_score"])
    return candidates[:max_candidates], api_calls


def _dedup_keys(c: dict) -> list[str]:
    keys = []
    name = normalize_name(c.get("name", ""))
    if name:
        keys.append(name)
    email = (c.get("email") or "").lower().strip()
    if email:
        keys.append(email)
    return keys


def _is_duplicate(c: dict, seen_keys: set, excluded: set = None) -> bool:
    keys = _dedup_keys(c)
    if not keys:
        return True
    if any(k in seen_keys for k in keys):
        return True
    if excluded and any(k in excluded for k in keys):
        return True
    seen_keys.update(keys)
    return False


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
    keywords: list[str],
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
                if not name or normalize_name(name) in exclude_names:
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

    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"   [OpenAlex works] search error: {e}")

    return candidates


def _search_semantic_scholar(
    keywords: list[str],
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
                if not name or normalize_name(name) in exclude_names:
                    continue
                c = _make_candidate({"name": name}, source="semantic_scholar_search")
                candidates.append(c)

    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"   [S2 papers] search error: {e}")

    return candidates


def _search_historical(
    keywords: list[str],
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
                if not name or normalize_name(name) in exclude_names:
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
    seniority_score = min(1.0, h / H_INDEX_CAP)

    source_trust = {
        "author_suggested": 1.0,
        "cited_author": 0.6,
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
        current_year = datetime.datetime.now().year
        if max_year >= current_year - 2:
            recency_score = 1.0
        elif max_year >= current_year - 4:
            recency_score = 0.6
        elif max_year >= current_year - 6:
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
            candidate["_predicted_p_accept"] = p_accept
        except (ValueError, RuntimeError) as e:
            print(f"   Warning: response prediction failed: {e}")

    try:
        from pipeline.referee_db import RefereeDB

        db = RefereeDB()
        tr = db.get_track_record(candidate.get("name", ""))
        if tr and tr.get("invitations", 0) >= 2:
            candidate["referee_history"] = tr
            track_bonus = 0.0
            acc_rate = tr.get("acceptance_rate", 0)
            if acc_rate >= 0.7:
                track_bonus += 0.04
            elif acc_rate >= 0.5:
                track_bonus += 0.02
            elif acc_rate < 0.3:
                track_bonus -= 0.05
            avg_days = tr.get("avg_review_days")
            if avg_days and avg_days < 35:
                track_bonus += 0.03
            elif avg_days and avg_days > 90:
                track_bonus -= 0.03
            quality = tr.get("avg_quality")
            if quality and quality > 0.5:
                track_bonus += 0.03

            if journal_code:
                j_stats = db.get_journal_stats(candidate.get("name", ""), journal_code)
                if j_stats and j_stats.get("total_invitations", 0) >= 2:
                    j_acc = j_stats["total_accepted"] / j_stats["total_invitations"]
                    if j_acc >= 0.7:
                        track_bonus += 0.03

            overdue_rate = tr.get("overdue_rate")
            if overdue_rate and overdue_rate > 0.5:
                track_bonus -= 0.05

            qt = tr.get("quality_trend", [])
            if len(qt) >= 2 and qt[-1] > qt[0]:
                track_bonus += 0.02

            profile = db.get_profile(candidate.get("name", ""))
            if profile:
                pq = profile.get("percentile_quality")
                if pq is not None and pq >= 75:
                    track_bonus += 0.03

            if profile and profile.get("last_invited_date"):
                try:
                    last_inv = datetime.datetime.strptime(
                        profile["last_invited_date"][:10], "%Y-%m-%d"
                    ).date()
                    days_since = (datetime.datetime.now().date() - last_inv).days
                    if days_since < 60:
                        score -= 0.05
                        candidate["_cooling_off_days"] = days_since
                except (ValueError, TypeError):
                    pass

            score += track_bonus
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
