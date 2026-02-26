import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
OUTPUTS_DIR = BASE_DIR / "production" / "outputs"
MODELS_DIR = BASE_DIR / "production" / "models"


class ExpertiseIndex:
    def __init__(self):
        self.referees = []
        self.index = None

    def build(self, journals: list = None):
        from pipeline.embeddings import get_engine

        engine = get_engine()
        self.referees = []
        texts = []

        if journals is None:
            journals = [d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir()]

        for journal in journals:
            journal_dir = OUTPUTS_DIR / journal
            if not journal_dir.exists():
                continue
            latest = _find_latest_json(journal_dir)
            if not latest:
                continue
            data = _load_json(latest)
            manuscripts = data.get("manuscripts", [])
            for ms in manuscripts:
                ms_keywords = ms.get("keywords", []) or []
                ms_title = ms.get("title", "")
                for ref in ms.get("referees", []):
                    profile = _build_referee_profile(ref, ms_keywords, ms_title, journal)
                    if profile["text"].strip():
                        self.referees.append(profile)
                        texts.append(profile["text"])

        if not texts:
            return 0

        self.referees = _deduplicate(self.referees)
        texts = [r["text"] for r in self.referees]
        self.index = engine.build_index(texts)
        return len(self.referees)

    def search(self, manuscript: dict, k: int = 30):
        if self.index is None or not self.referees:
            return []

        from pipeline.embeddings import get_engine

        engine = get_engine()
        query = _manuscript_text(manuscript)
        results = engine.search_index(query, self.index, k=k)

        candidates = []
        for idx, score in results:
            if 0 <= idx < len(self.referees):
                ref = dict(self.referees[idx])
                ref["semantic_similarity"] = score
                candidates.append(ref)
        return candidates

    def save(self, path: Path = None):
        if path is None:
            path = MODELS_DIR
        path.mkdir(parents=True, exist_ok=True)

        from pipeline.embeddings import get_engine

        engine = get_engine()
        if self.index is not None:
            engine.save_index(self.index, path / "referee_index.faiss")
        with open(path / "referee_metadata.json", "w") as f:
            json.dump(self.referees, f, default=str)

    def load(self, path: Path = None):
        if path is None:
            path = MODELS_DIR

        from pipeline.embeddings import get_engine

        engine = get_engine()
        index_path = path / "referee_index.faiss"
        meta_path = path / "referee_metadata.json"

        if index_path.exists() and meta_path.exists():
            self.index = engine.load_index(index_path)
            with open(meta_path) as f:
                self.referees = json.load(f)
            return True
        return False


def _build_referee_profile(ref: dict, ms_keywords: list, ms_title: str, journal: str) -> dict:
    wp = ref.get("web_profile") or {}
    topics = wp.get("research_topics", []) or []
    top_papers = []
    for src in ["semantic_scholar", "openalex"]:
        src_data = wp.get(src) or {}
        for p in src_data.get("top_papers", []) or []:
            top_papers.append(p.get("title", ""))

    text_parts = topics + top_papers[:5] + ms_keywords
    text = " ".join(str(t) for t in text_parts if t)

    return {
        "name": ref.get("name", ""),
        "email": ref.get("email", ""),
        "institution": ref.get("institution", ""),
        "h_index": wp.get("h_index") or wp.get("semantic_scholar", {}).get("h_index", 0) or 0,
        "journal": journal,
        "topics": topics,
        "text": text,
    }


def _manuscript_text(ms: dict) -> str:
    parts = [ms.get("title", ""), ms.get("abstract", "")]
    kw = ms.get("keywords", []) or []
    parts.extend(kw)
    return " ".join(str(p) for p in parts if p)


def _deduplicate(referees: list) -> list:
    seen = {}
    for ref in referees:
        key = ref.get("email", "").lower().strip() or ref.get("name", "").lower().strip()
        if not key:
            continue
        if key in seen:
            existing = seen[key]
            if ref.get("h_index", 0) > existing.get("h_index", 0):
                seen[key] = ref
        else:
            seen[key] = ref
    return list(seen.values())


def _find_latest_json(journal_dir: Path):
    jsons = sorted(
        journal_dir.glob("*_extraction_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return jsons[0] if jsons else None


def _load_json(path: Path) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
