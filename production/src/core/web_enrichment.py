#!/usr/bin/env python3
import re
import time
import requests
from typing import Dict, Callable, Optional
from urllib.parse import quote_plus

try:
    from core.academic_apis import AcademicProfileEnricher
except ImportError:
    AcademicProfileEnricher = None


def enrich_people_from_web(
    manuscript_data: Dict,
    get_cached_web_profile: Callable,
    save_web_profile: Callable,
    platform_label: str = "platform_metadata",
) -> int:
    people = []
    for ref in manuscript_data.get("referees", []):
        if ref.get("name"):
            people.append(("referee", ref))
    for auth in manuscript_data.get("authors", []):
        if auth.get("name"):
            people.append(("author", auth))

    if not people:
        return 0

    enriched = 0
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Editorial-Scripts/1.0 (mailto:dylansmb@gmail.com)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    academic = None
    if AcademicProfileEnricher is not None:
        try:
            academic = AcademicProfileEnricher(session)
        except Exception:
            pass

    cache_hits = 0
    for role, person in people:
        name = person.get("name", "")
        institution = (
            person.get("institution", "")
            or person.get("affiliation", "")
            or person.get("institution_parsed", "")
        )
        orcid = person.get("orcid", "")
        if person.get("web_profile"):
            continue

        if orcid and orcid.startswith("http"):
            orcid_id = orcid.rstrip("/").split("/")[-1]
        elif orcid and re.match(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", orcid):
            orcid_id = orcid
        else:
            orcid_id = None

        if orcid_id:
            person["orcid"] = orcid_id

        cached_profile = get_cached_web_profile(name, institution, orcid_id or "")
        if cached_profile:
            person["web_profile"] = cached_profile
            person["web_profile_source"] = "cache"
            cache_hits += 1
            enriched += 1
            continue

        profile = {}

        if orcid_id:
            try:
                resp = session.get(
                    f"https://pub.orcid.org/v3.0/{orcid_id}/works",
                    headers={"Accept": "application/json"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    works = resp.json().get("group", [])
                    recent = []
                    for w in works[:5]:
                        ws = w.get("work-summary", [{}])[0]
                        title_obj = ws.get("title", {}).get("title", {})
                        title = title_obj.get("value", "") if title_obj else ""
                        year = (
                            ws.get("publication-date", {}).get("year", {}).get("value", "")
                            if ws.get("publication-date")
                            else ""
                        )
                        journal = (
                            ws.get("journal-title", {}).get("value", "")
                            if ws.get("journal-title")
                            else ""
                        )
                        if title:
                            paper = {"title": title}
                            if year:
                                paper["year"] = year
                            if journal:
                                paper["journal"] = journal
                            recent.append(paper)
                    if recent:
                        profile["recent_publications"] = recent
                        profile["publication_count"] = len(works)

                person_resp = session.get(
                    f"https://pub.orcid.org/v3.0/{orcid_id}/person",
                    headers={"Accept": "application/json"},
                    timeout=10,
                )
                if person_resp.status_code == 200:
                    person_data = person_resp.json()
                    bio_obj = person_data.get("biography", {})
                    if bio_obj and bio_obj.get("content"):
                        profile["biography"] = bio_obj["content"][:500]
                    urls_obj = person_data.get("researcher-urls", {})
                    if urls_obj:
                        ext_urls = []
                        for url_item in urls_obj.get("researcher-url", [])[:5]:
                            url_name = url_item.get("url-name", "")
                            url_value = (url_item.get("url", {}) or {}).get("value", "")
                            if url_value:
                                ext_urls.append({"name": url_name, "url": url_value})
                        if ext_urls:
                            profile["external_urls"] = ext_urls
                    kw_obj = person_data.get("keywords", {})
                    if kw_obj:
                        keywords = []
                        for kw_item in kw_obj.get("keyword", [])[:10]:
                            kw_content = kw_item.get("content", "")
                            if kw_content:
                                keywords.append(kw_content)
                        if keywords:
                            profile["research_keywords"] = keywords
            except Exception:
                pass

        if not profile.get("recent_publications"):
            search_name = name.replace(",", "").strip()
            name_parts = search_name.split()
            target_surname = name_parts[-1].lower() if name_parts else ""
            target_given = name_parts[0].lower() if len(name_parts) >= 2 else ""
            if "," in name:
                comma_parts = name.split(",")
                target_surname = (
                    comma_parts[0].strip().split()[-1].lower() if comma_parts[0].strip() else ""
                )
                target_given = (
                    comma_parts[1].strip().split()[0].lower()
                    if len(comma_parts) > 1 and comma_parts[1].strip()
                    else ""
                )
            if institution:
                search_name += f" {institution}"
            try:
                resp = session.get(
                    f"https://api.crossref.org/works?query.author={quote_plus(search_name)}&rows=10&sort=published&order=desc",
                    timeout=15,
                )
                if resp.status_code == 200:
                    items = resp.json().get("message", {}).get("items", [])
                    crossref_papers = []
                    for item in items[:10]:
                        cr_authors = item.get("author", [])
                        author_match = False
                        if target_surname and cr_authors:
                            for cr_auth in cr_authors:
                                cr_family = (cr_auth.get("family") or "").lower()
                                cr_given = (cr_auth.get("given") or "").lower()
                                if cr_family == target_surname:
                                    if not target_given or not cr_given:
                                        author_match = True
                                    elif (
                                        cr_given == target_given
                                        or cr_given.startswith(target_given[:2])
                                        or target_given.startswith(cr_given[:2])
                                    ):
                                        author_match = True
                                    if orcid_id and cr_auth.get("ORCID"):
                                        cr_orcid = cr_auth["ORCID"].rstrip("/").split("/")[-1]
                                        if cr_orcid == orcid_id:
                                            author_match = True
                                    if author_match:
                                        break
                        if not author_match:
                            continue
                        title = " ".join(item.get("title", []))
                        year_parts = item.get("published-print", {}).get("date-parts", [[]])
                        if not year_parts[0]:
                            year_parts = item.get("published-online", {}).get("date-parts", [[]])
                        year = str(year_parts[0][0]) if year_parts and year_parts[0] else ""
                        journal_name = " ".join(item.get("container-title", []))
                        doi = item.get("DOI", "")
                        if title:
                            paper = {"title": title}
                            if year:
                                paper["year"] = year
                            if journal_name:
                                paper["journal"] = journal_name
                            if doi:
                                paper["doi"] = doi
                            crossref_papers.append(paper)
                        if len(crossref_papers) >= 5:
                            break
                    if crossref_papers:
                        profile["recent_publications"] = crossref_papers
                        profile["source"] = "crossref"
            except Exception:
                pass

        if academic:
            try:
                academic_data = academic.enrich(name, orcid_id, institution)
                if academic_data:
                    profile.update(academic_data)
            except Exception:
                pass

        if profile:
            person["web_profile"] = profile
            enriched += 1
            source = "orcid+crossref"
            if profile.get("semantic_scholar") or profile.get("openalex"):
                source += "+academic"
            save_web_profile(name, institution, orcid_id or "", profile, source)
        elif role == "author":
            meta_profile = {"source": platform_label}
            if institution:
                meta_profile["institution"] = institution
            dept = person.get("department", "")
            if dept:
                meta_profile["department"] = dept
            country = person.get("country", "")
            if country:
                meta_profile["country"] = country
            email = person.get("email", "")
            if email and "@" in email:
                meta_profile["email_domain"] = email.split("@")[-1]
            person["web_profile"] = meta_profile
            enriched += 1

    if enriched:
        cache_msg = f" ({cache_hits} from cache)" if cache_hits else ""
        print(
            f"      🌐 Web enriched: {enriched}/{len(people)} people via ORCID/CrossRef/S2/OpenAlex{cache_msg}"
        )

    return enriched
