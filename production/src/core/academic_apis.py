import time
import unicodedata

import requests

SURNAME_PARTICLES = {
    "van",
    "von",
    "de",
    "del",
    "della",
    "di",
    "la",
    "le",
    "den",
    "der",
    "ten",
    "ter",
    "das",
    "dos",
    "du",
    "el",
    "al",
    "bin",
}


class AcademicProfileEnricher:
    S2_BASE = "https://api.semanticscholar.org/graph/v1"
    OA_BASE = "https://api.openalex.org"
    S2_FIELDS = "name,citationCount,paperCount,hIndex,papers.title,papers.year,papers.citationCount,papers.venue"
    RATE_LIMIT = 0.6

    def __init__(self, session: requests.Session):
        self.session = session
        self._last_request = 0
        self._inst_cache = {}

    def enrich(self, name, orcid_id=None, institution=None):
        result = {}

        s2 = self._semantic_scholar(name, orcid_id, institution)
        if s2:
            result["semantic_scholar"] = s2

        oa, oa_from_name = self._openalex(name, orcid_id, institution)
        if oa:
            result["openalex"] = oa

        if oa_from_name and institution and oa and not oa.pop("_confident", False):
            oa_inst = (oa.get("last_institution") or {}).get("name", "")
            if oa_inst and not self._institution_match(institution, oa_inst):
                oa = None
                result.pop("openalex", None)
                if s2:
                    s2 = None
                    result.pop("semantic_scholar", None)

        if s2 or oa:
            result["citation_count"] = (s2 or {}).get("citation_count") or (oa or {}).get(
                "cited_by_count"
            )
            result["h_index"] = (oa or {}).get("h_index") or (s2 or {}).get("h_index")
            result["research_topics"] = (oa or {}).get("topics", [])

        return result if (s2 or oa) else {}

    def _rate_limit(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self._last_request = time.time()

    def _normalize(self, s):
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()

    def _semantic_scholar(self, name, orcid_id=None, institution=None):
        try:
            if orcid_id:
                self._rate_limit()
                resp = self.session.get(
                    f"{self.S2_BASE}/author/ORCID:{orcid_id}",
                    params={"fields": self.S2_FIELDS},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return self._parse_s2(resp.json())
                if not institution:
                    return None

            self._rate_limit()
            resp = self.session.get(
                f"{self.S2_BASE}/author/search",
                params={"query": name, "fields": self.S2_FIELDS, "limit": 10},
                timeout=10,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                match = self._disambiguate_s2(data, name)
                if match:
                    return self._parse_s2(match)
        except Exception as e:
            print(f"      [S2] {name}: {type(e).__name__}: {e}")
        return None

    def _parse_s2(self, author):
        papers = author.get("papers", [])
        top_papers = sorted(papers, key=lambda p: p.get("citationCount") or 0, reverse=True)[:5]
        return {
            "author_id": author.get("authorId"),
            "citation_count": author.get("citationCount"),
            "paper_count": author.get("paperCount"),
            "h_index": author.get("hIndex"),
            "top_papers": [
                {
                    "title": p.get("title"),
                    "year": p.get("year"),
                    "citations": p.get("citationCount"),
                    "venue": p.get("venue") or None,
                }
                for p in top_papers
                if p.get("title")
            ],
        }

    def _disambiguate_s2(self, candidates, target_name):
        if not candidates:
            return None
        matches = [c for c in candidates if self._name_match(c.get("name", ""), target_name)]
        if not matches:
            return None
        if len(matches) == 1:
            return matches[0]
        target_norm = self._normalize(target_name.replace(",", " ").replace(".", " "))
        target_parts = set(target_norm.split())
        exact = [
            m
            for m in matches
            if set(self._normalize(m.get("name", "").replace(",", " ").replace(".", " ")).split())
            == target_parts
        ]
        pool = exact if exact else matches
        if len(pool) == 1:
            return pool[0]
        return sorted(pool, key=lambda x: x.get("citationCount") or 0, reverse=True)[0]

    def _openalex(self, name, orcid_id=None, institution=None):
        try:
            if orcid_id:
                self._rate_limit()
                resp = self.session.get(
                    f"{self.OA_BASE}/authors/orcid:{orcid_id}",
                    timeout=10,
                )
                if resp.status_code == 200:
                    return self._parse_oa(resp.json()), False
                if not institution:
                    return None, False

            self._rate_limit()
            resp = self.session.get(
                f"{self.OA_BASE}/authors",
                params={"search": name, "per_page": 50},
                timeout=10,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                match, confident = self._disambiguate_oa(results, name, institution)
                if match:
                    parsed = self._parse_oa(match)
                    parsed["_confident"] = confident
                    return parsed, True

            if institution:
                inst_id = self._resolve_oa_institution(institution)
                if inst_id:
                    self._rate_limit()
                    resp2 = self.session.get(
                        f"{self.OA_BASE}/authors",
                        params={
                            "search": name,
                            "filter": f"affiliations.institution.id:{inst_id}",
                            "per_page": 10,
                        },
                        timeout=10,
                    )
                    if resp2.status_code == 200:
                        results2 = resp2.json().get("results", [])
                        match2, _ = self._disambiguate_oa(results2, name, institution)
                        if match2:
                            parsed = self._parse_oa(match2)
                            parsed["_confident"] = True
                            return parsed, True
        except Exception as e:
            print(f"      [OA] {name}: {type(e).__name__}: {e}")
        return None, False

    def _resolve_oa_institution(self, name):
        if name in self._inst_cache:
            return self._inst_cache[name]
        try:
            self._rate_limit()
            resp = self.session.get(
                f"{self.OA_BASE}/institutions",
                params={"search": name, "per_page": 1},
                timeout=10,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    inst_id = results[0].get("id", "")
                    self._inst_cache[name] = inst_id
                    return inst_id
        except Exception as e:
            print(f"      [OA inst] {name}: {type(e).__name__}: {e}")
        self._inst_cache[name] = None
        return None

    def _parse_oa(self, author):
        stats = author.get("summary_stats", {})
        institutions = author.get("last_known_institutions") or []
        topics = author.get("topics", [])
        return {
            "author_id": author.get("id"),
            "display_name": author.get("display_name"),
            "cited_by_count": author.get("cited_by_count"),
            "works_count": author.get("works_count"),
            "h_index": stats.get("h_index"),
            "topics": [t.get("display_name") for t in topics[:10] if t.get("display_name")],
            "last_institution": (
                {
                    "name": institutions[0].get("display_name"),
                    "country": institutions[0].get("country_code"),
                }
                if institutions
                else None
            ),
        }

    def _disambiguate_oa(self, candidates, target_name, institution=None):
        if not candidates:
            return None, False
        matches = [
            c for c in candidates if self._name_match(c.get("display_name", ""), target_name)
        ]
        if not matches:
            return None, False
        if len(matches) == 1:
            return matches[0], True
        target_norm = self._normalize(target_name.replace(",", " ").replace(".", " "))
        target_parts = set(target_norm.split())
        exact = [
            m
            for m in matches
            if set(
                self._normalize(
                    m.get("display_name", "").replace(",", " ").replace(".", " ")
                ).split()
            )
            == target_parts
        ]
        if institution:
            for m in exact:
                for inst in m.get("last_known_institutions") or []:
                    inst_name = inst.get("display_name", "")
                    if inst_name and self._institution_match(institution, inst_name):
                        return m, True
            for m in matches:
                if m in exact:
                    continue
                for inst in m.get("last_known_institutions") or []:
                    inst_name = inst.get("display_name", "")
                    if inst_name and self._institution_match(institution, inst_name):
                        return m, True
        pool = exact if exact else matches
        if len(pool) == 1:
            return pool[0], True
        return sorted(pool, key=lambda x: x.get("cited_by_count") or 0, reverse=True)[0], False

    def _institution_match(self, known, api_inst):
        stop = {
            "university",
            "universite",
            "universidad",
            "universitat",
            "universiteit",
            "of",
            "the",
            "and",
            "for",
            "at",
            "in",
            "d",
            "de",
            "des",
            "du",
            "la",
            "le",
            "les",
            "del",
            "di",
            "institute",
            "institut",
            "school",
            "college",
            "center",
            "centre",
            "department",
            "faculty",
            "national",
            "polytechnic",
            "technical",
            "technology",
            "science",
            "sciences",
            "research",
            "state",
        }
        clean = (
            lambda s: self._normalize(s)
            .replace(",", " ")
            .replace("-", " ")
            .replace("\u2013", " ")
            .replace("\u2014", " ")
            .replace("(", " ")
            .replace(")", " ")
            .replace("'", " ")
            .replace("\u2019", " ")
        )
        known_words = set(clean(known).split()) - stop
        api_words = set(clean(api_inst).split()) - stop
        if not known_words or not api_words:
            return False
        overlap = len(known_words & api_words)
        needed = 2 if len(known_words) >= 3 else 1
        return overlap >= needed

    def _extract_surname(self, parts, original_name):
        if "," in original_name:
            raw = self._normalize(original_name.split(",")[0].strip())
            surname_parts = [p for p in raw.split() if p]
            core = [p for p in surname_parts if p not in SURNAME_PARTICLES]
            return core[-1] if core else surname_parts[-1] if surname_parts else ""
        core = [p for p in parts if p not in SURNAME_PARTICLES]
        return core[-1] if core else parts[-1] if parts else ""

    def _name_match(self, api_name, target_name):
        api_norm = self._normalize(api_name.replace(",", " ").replace(".", " "))
        target_norm = self._normalize(target_name.replace(",", " ").replace(".", " "))
        api_parts = [p for p in api_norm.split() if p]
        target_parts = [p for p in target_norm.split() if p]
        if not api_parts or not target_parts:
            return False

        api_surname = self._extract_surname(api_parts, api_name)
        target_surname = self._extract_surname(target_parts, target_name)

        if api_surname != target_surname:
            return False

        api_given = [p for p in api_parts if p != api_surname and p not in SURNAME_PARTICLES]
        target_given = [
            p for p in target_parts if p != target_surname and p not in SURNAME_PARTICLES
        ]

        if not api_given or not target_given:
            return len(api_parts) == 1 and len(target_parts) == 1

        for ag in api_given:
            for tg in target_given:
                if ag == tg:
                    return True
                if len(ag) == 1 and tg.startswith(ag):
                    return True
                if len(tg) == 1 and ag.startswith(tg):
                    return True

        return False
