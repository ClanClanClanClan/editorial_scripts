"""Manuscript similarity detection using FAISS embeddings."""

import json

from pipeline import JOURNALS, MODELS_DIR, OUTPUTS_DIR, _load_json

INDEX_PATH = MODELS_DIR / "manuscript_index.faiss"
META_PATH = MODELS_DIR / "manuscript_metadata.json"


class ManuscriptIndex:
    def __init__(self):
        self.manuscripts = []
        self.index = None

    def build(self, journals=None):
        from pipeline.embeddings import get_engine

        engine = get_engine()
        self.manuscripts = []
        texts = []

        if journals is None:
            journals = list(JOURNALS)

        for journal in journals:
            journal_dir = OUTPUTS_DIR / journal
            if not journal_dir.exists():
                continue
            extraction_files = sorted(journal_dir.glob("*_extraction_*.json"))
            if not extraction_files:
                continue
            latest = extraction_files[-1]
            data = _load_json(latest)
            for ms in data.get("manuscripts", []):
                title = ms.get("title", "")
                abstract = ms.get("abstract", "")
                ms_id = ms.get("manuscript_id", "")
                if not title and not abstract:
                    continue
                self.manuscripts.append(
                    {
                        "journal": journal,
                        "manuscript_id": ms_id,
                        "title": title,
                        "abstract": abstract,
                        "status": ms.get("status", ""),
                        "keywords": ms.get("keywords", []) or [],
                    }
                )
                text = _manuscript_text(title, abstract, ms.get("keywords"))
                texts.append(text)

        if not texts:
            return 0

        self.index = engine.build_index(texts)
        return len(self.manuscripts)

    def search(self, title, abstract, top_k=5):
        if self.index is None or not self.manuscripts:
            return []

        from pipeline.embeddings import get_engine

        engine = get_engine()
        query = _manuscript_text(title, abstract)
        results = engine.search_index(query, self.index, k=top_k + 5)

        matches = []
        for idx, score in results:
            if 0 <= idx < len(self.manuscripts):
                ms = dict(self.manuscripts[idx])
                if ms["title"] == title:
                    continue
                ms["similarity"] = round(score, 4)
                matches.append(ms)
                if len(matches) >= top_k:
                    break
        return matches

    def save(self, path=None):
        save_dir = path or MODELS_DIR
        save_dir.mkdir(parents=True, exist_ok=True)

        from pipeline.embeddings import get_engine

        engine = get_engine()
        if self.index is not None:
            engine.save_index(self.index, save_dir / "manuscript_index.faiss")

        meta = []
        for ms in self.manuscripts:
            meta.append(
                {
                    "journal": ms["journal"],
                    "manuscript_id": ms["manuscript_id"],
                    "title": ms["title"],
                    "abstract": ms.get("abstract", ""),
                    "status": ms.get("status", ""),
                    "keywords": ms.get("keywords", []),
                }
            )
        with open(save_dir / "manuscript_metadata.json", "w") as f:
            json.dump(meta, f, default=str)

    def load(self, path=None):
        load_dir = path or MODELS_DIR

        from pipeline.embeddings import get_engine

        engine = get_engine()
        index_path = load_dir / "manuscript_index.faiss"
        meta_path = load_dir / "manuscript_metadata.json"

        if index_path.exists() and meta_path.exists():
            self.index = engine.load_index(index_path)
            with open(meta_path) as f:
                self.manuscripts = json.load(f)
            return True
        return False


def _manuscript_text(title, abstract, keywords=None):
    parts = [title or "", abstract or ""]
    if keywords:
        parts.extend(str(k) for k in keywords if k)
    return " ".join(p for p in parts if p)


def find_similar_manuscripts(title, abstract, top_k=5):
    idx = ManuscriptIndex()
    if not idx.load():
        count = idx.build()
        if count > 0:
            idx.save()
    return idx.search(title, abstract, top_k=top_k)
