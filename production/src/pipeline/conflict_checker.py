#!/usr/bin/env python3
"""Conflict-of-interest detection for referee candidates."""

from core.academic_apis import AcademicProfileEnricher


def check_conflicts(
    candidate: dict,
    manuscript_authors: list[dict],
    opposed_referees: list[dict],
    manuscript_editors: list[dict],
    enricher: AcademicProfileEnricher,
) -> list[str]:
    conflicts = []

    cand_name = candidate.get("name", "")
    cand_email = (candidate.get("email") or "").lower()
    cand_inst = candidate.get("institution") or ""

    for author in manuscript_authors:
        author_name = author.get("name", "")
        if enricher.name_match(cand_name, author_name):
            conflicts.append(f"Is manuscript author: {author_name}")
            break

    if not any("Is manuscript author" in c for c in conflicts):
        for author in manuscript_authors:
            author_inst = author.get("institution") or ""
            if author_inst and cand_inst and enricher.institution_match(cand_inst, author_inst):
                conflicts.append(
                    f"Same institution as author {author.get('name', '?')}: "
                    f"{cand_inst} / {author_inst}"
                )
                break

    for opp in opposed_referees:
        opp_name = opp.get("name", "")
        opp_email = (opp.get("email") or "").lower()
        if opp_email and cand_email and opp_email == cand_email:
            conflicts.append("Author-opposed referee (email match)")
            break
        if opp_name and enricher.name_match(cand_name, opp_name):
            conflicts.append("Author-opposed referee (name match)")
            break

    for editor in manuscript_editors:
        editor_name = editor.get("name", "")
        if editor_name and enricher.name_match(cand_name, editor_name):
            conflicts.append(f"Is manuscript editor: {editor_name}")
            break

    coauthor_conflict = _check_coauthorship(candidate, manuscript_authors)
    if coauthor_conflict:
        conflicts.append(coauthor_conflict)

    inst_conflict = _check_institution_history(candidate, manuscript_authors)
    if inst_conflict:
        conflicts.append(inst_conflict)

    return conflicts


def _check_institution_history(
    candidate: dict,
    manuscript_authors: list[dict],
) -> str | None:
    cand_wp = candidate.get("web_profile") or {}
    cand_oa = cand_wp.get("openalex") or {}
    cand_affiliations = set()
    for aff in (cand_oa.get("affiliations") or [])[:5]:
        inst_name = (aff.get("institution") or aff.get("display_name") or "").strip().lower()
        if inst_name:
            cand_affiliations.add(inst_name)
    if not cand_affiliations:
        cand_inst = (candidate.get("institution") or "").strip().lower()
        if cand_inst:
            cand_affiliations.add(cand_inst)

    if not cand_affiliations:
        return None

    for author in manuscript_authors:
        author_wp = author.get("web_profile") or {}
        author_oa = author_wp.get("openalex") or {}
        author_affiliations = set()
        for aff in (author_oa.get("affiliations") or [])[:5]:
            inst_name = (aff.get("institution") or aff.get("display_name") or "").strip().lower()
            if inst_name:
                author_affiliations.add(inst_name)
        if not author_affiliations:
            author_inst = (author.get("institution") or "").strip().lower()
            if author_inst:
                author_affiliations.add(author_inst)

        shared = cand_affiliations & author_affiliations
        if shared:
            inst = next(iter(shared))
            return f"Shared institution history with {author.get('name', '?')}: {inst}"

    return None


def _check_coauthorship(
    candidate: dict,
    manuscript_authors: list[dict],
) -> str | None:
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
