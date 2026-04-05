"""Extract references from manuscript PDFs for referee finding."""

import re


def extract_references(pdf_path, max_refs=50):
    try:
        import fitz
    except ImportError:
        return []

    pdf_path = str(pdf_path)
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return []

    try:
        full_text = ""
        for page in doc:
            full_text += page.get_text()
    finally:
        doc.close()

    section = _find_references_section(full_text)
    if not section:
        return []

    raw_entries = _split_entries(section)
    results = []
    for entry in raw_entries[:max_refs]:
        parsed = _parse_reference_entry(entry)
        if parsed:
            results.append(parsed)
    return results


def _find_references_section(text):
    patterns = [
        r"\n\s*(?:References|REFERENCES|Bibliography|BIBLIOGRAPHY|Literature Cited)\s*\n",
        r"\n\s*(?:References|REFERENCES|Bibliography)\s*$",
    ]
    best_pos = -1
    for pat in patterns:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            pos = m.end()
            if best_pos < 0 or pos > best_pos:
                best_pos = pos

    if best_pos < 0:
        return None

    section = text[best_pos:]

    end_patterns = [
        r"\n\s*(?:Appendix|APPENDIX|Supplementary|SUPPLEMENTARY|Acknowledgment|Acknowledgement)\s*\n",
    ]
    for pat in end_patterns:
        m = re.search(pat, section)
        if m:
            section = section[: m.start()]
            break

    return section.strip() if section.strip() else None


def _split_entries(section_text):
    numbered = re.split(r"\n\s*\[\d+\]\s*", section_text)
    if len(numbered) > 2:
        return [e.strip() for e in numbered if e.strip()]

    dot_numbered = re.split(r"\n\s*\d+\.\s+", section_text)
    if len(dot_numbered) > 2:
        return [e.strip() for e in dot_numbered if e.strip()]

    lines = section_text.split("\n")
    entries = []
    current = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                entries.append(" ".join(current))
                current = []
        else:
            current.append(stripped)
    if current:
        entries.append(" ".join(current))

    return entries


def _parse_reference_entry(entry):
    entry = entry.strip()
    if not entry or len(entry) < 10:
        return None

    year = None
    year_match = re.search(r"\((\d{4})\)|,\s*(\d{4})[.,\s]|\b((?:19|20)\d{2})\b", entry)
    if year_match:
        year = int(next(g for g in year_match.groups() if g))

    title = _extract_title(entry)
    authors = _extract_author_names(entry)

    return {
        "raw": entry,
        "authors": authors,
        "title": title,
        "year": year,
    }


def _extract_title(entry):
    patterns = [
        r'[""](.*?)["""]',
        r"\.\s+([A-Z][^.]{15,}?)\.\s",
        r",\s*(\d{4})\)?\s*[.,]?\s*([A-Z][^.]{15,}?)\.",
    ]
    for pat in patterns:
        m = re.search(pat, entry)
        if m:
            return m.group(m.lastindex).strip()

    parts = re.split(r"\.\s+", entry)
    if len(parts) >= 2:
        candidate = parts[1].strip()
        if len(candidate) > 15:
            return candidate

    return ""


def _extract_author_names(entry):
    author_section = entry
    for sep in [r"\(\d{4}\)", r",\s*\d{4}[.,]", r"\.\s+[A-Z]"]:
        m = re.search(sep, entry)
        if m:
            author_section = entry[: m.start()].strip()
            break

    author_section = re.sub(r"^\[\d+\]\s*", "", author_section)
    author_section = re.sub(r"^\d+\.\s+", "", author_section)
    author_section = author_section.rstrip(".,;:")

    if not author_section or len(author_section) < 3:
        return []

    if " and " in author_section:
        parts = re.split(r",\s*(?:and\s+)?|\s+and\s+", author_section)
    else:
        parts = re.split(r";\s*|,\s*(?=[A-Z])", author_section)

    names = []
    for part in parts:
        part = part.strip().rstrip(".,")
        if not part or len(part) < 2:
            continue
        if re.match(r"^[A-Z]\.$", part) or re.match(r"^[A-Z]\.\s*[A-Z]\.$", part):
            continue
        part = re.sub(r"\s+", " ", part)
        if any(c.isalpha() for c in part):
            names.append(part)

    return names


def get_cited_author_candidates(pdf_path, exclude_names=None, session=None):
    from pipeline import normalize_name_orderless as normalize_name

    refs = extract_references(pdf_path)
    if not refs:
        return []

    exclude_normalized = set()
    if exclude_names:
        exclude_normalized = {normalize_name(n) for n in exclude_names}

    author_papers: dict[str, list[str]] = {}
    for ref in refs:
        title = ref.get("title", "")
        for author in ref.get("authors", []):
            norm = normalize_name(author)
            if not norm or norm in exclude_normalized:
                continue
            author_papers.setdefault(norm, {"name": author, "papers": []})
            if title:
                author_papers[norm]["papers"].append(title)

    candidates = []
    for _norm_key, info in sorted(author_papers.items(), key=lambda x: -len(x[1]["papers"])):
        candidates.append(
            {
                "name": info["name"],
                "source": "cited_author",
                "relevant_papers": info["papers"],
                "citation_count": len(info["papers"]),
            }
        )

    return candidates
