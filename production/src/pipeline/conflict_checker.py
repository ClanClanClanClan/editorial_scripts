#!/usr/bin/env python3
"""Conflict-of-interest detection for referee candidates."""

from typing import Dict, List, Optional

from core.academic_apis import AcademicProfileEnricher


def check_conflicts(
    candidate: dict,
    manuscript_authors: List[dict],
    opposed_referees: List[dict],
    manuscript_editors: List[dict],
    enricher: AcademicProfileEnricher,
) -> List[str]:
    conflicts = []

    cand_name = candidate.get("name", "")
    cand_email = (candidate.get("email") or "").lower()
    cand_inst = candidate.get("institution") or ""

    for author in manuscript_authors:
        author_name = author.get("name", "")
        if enricher._name_match(cand_name, author_name):
            conflicts.append(f"Is manuscript author: {author_name}")
            break

    if not any("Is manuscript author" in c for c in conflicts):
        for author in manuscript_authors:
            author_inst = author.get("institution") or ""
            if author_inst and cand_inst and enricher._institution_match(cand_inst, author_inst):
                conflicts.append(
                    f"Same institution as author {author.get('name', '?')}: "
                    f"{cand_inst} / {author_inst}"
                )
                break

    for opp in opposed_referees:
        opp_name = opp.get("name", "")
        opp_email = (opp.get("email") or "").lower()
        if opp_email and cand_email and opp_email == cand_email:
            conflicts.append(f"Author-opposed referee (email match)")
            break
        if opp_name and enricher._name_match(cand_name, opp_name):
            conflicts.append(f"Author-opposed referee (name match)")
            break

    for editor in manuscript_editors:
        editor_name = editor.get("name", "")
        if editor_name and enricher._name_match(cand_name, editor_name):
            conflicts.append(f"Is manuscript editor: {editor_name}")
            break

    coauthor_conflict = _check_coauthorship(candidate, manuscript_authors, enricher)
    if coauthor_conflict:
        conflicts.append(coauthor_conflict)

    return conflicts


def _check_coauthorship(
    candidate: dict,
    manuscript_authors: List[dict],
    enricher: AcademicProfileEnricher,
) -> Optional[str]:
    cand_name = candidate.get("name", "")

    for author in manuscript_authors:
        wp = author.get("web_profile") or {}
        s2 = wp.get("semantic_scholar") or {}
        for paper in s2.get("top_papers") or []:
            title = paper.get("title", "")
            if not title:
                continue
            cand_papers = candidate.get("relevant_papers", [])
            for cp in cand_papers:
                if cp.get("title", "").lower() == title.lower():
                    return (
                        f"Possible co-author with {author.get('name', '?')}: "
                        f'shared paper "{title[:80]}"'
                    )

    cand_wp = candidate.get("web_profile") or {}
    cand_s2 = cand_wp.get("semantic_scholar") or {}
    cand_papers = cand_s2.get("top_papers", [])
    for author in manuscript_authors:
        author_wp = author.get("web_profile") or {}
        author_s2 = author_wp.get("semantic_scholar") or {}
        author_papers = author_s2.get("top_papers", [])
        cand_titles = {p.get("title", "").lower() for p in cand_papers if p.get("title")}
        author_titles = {p.get("title", "").lower() for p in author_papers if p.get("title")}
        shared = cand_titles & author_titles
        if shared:
            title = next(iter(shared))
            return f"Co-author with {author.get('name', '?')}: " f'shared paper "{title[:80]}"'

    return None
