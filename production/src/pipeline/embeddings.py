import numpy as np
from pathlib import Path

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = EmbeddingEngine()
    return _engine


class EmbeddingEngine:
    MODEL_NAME = "allenai/specter2_base"
    FALLBACK_MODEL = "all-MiniLM-L6-v2"

    def __init__(self):
        self.model = None
        self.dim = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer

            try:
                self.model = SentenceTransformer(self.MODEL_NAME)
            except Exception:
                print(f"  SPECTER unavailable, falling back to {self.FALLBACK_MODEL}")
                self.model = SentenceTransformer(self.FALLBACK_MODEL)
            test = self.model.encode(["test"])
            self.dim = test.shape[1]
        except ImportError:
            print("  sentence-transformers not installed — using TF-IDF fallback")
            self.model = None
            self.dim = None

    def embed(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            return np.zeros(self.dim or 768)
        if self.model is not None:
            return self.model.encode(text, normalize_embeddings=True)
        return self._tfidf_embed(text)

    def batch_embed(self, texts: list) -> np.ndarray:
        texts = [t if t and t.strip() else "empty" for t in texts]
        if self.model is not None:
            return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.array([self._tfidf_embed(t) for t in texts])

    def similarity(self, text_a: str, text_b: str) -> float:
        va = self.embed(text_a)
        vb = self.embed(text_b)
        return float(np.dot(va, vb))

    def build_index(self, texts: list):
        try:
            import faiss
        except ImportError:
            return None
        if not texts:
            return None
        vecs = self.batch_embed(texts)
        vecs = vecs.astype(np.float32)
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs)
        return index

    def search_index(self, query: str, index, k: int = 10):
        if index is None:
            return []
        vec = self.embed(query).astype(np.float32).reshape(1, -1)
        scores, indices = index.search(vec, min(k, index.ntotal))
        results = []
        for i, (idx, score) in enumerate(zip(indices[0], scores[0])):
            if idx >= 0:
                results.append((int(idx), float(score)))
        return results

    def save_index(self, index, path: Path):
        try:
            import faiss

            faiss.write_index(index, str(path))
        except Exception:
            pass

    def load_index(self, path: Path):
        try:
            import faiss

            if path.exists():
                return faiss.read_index(str(path))
        except Exception:
            pass
        return None

    def _tfidf_embed(self, text: str) -> np.ndarray:
        from sklearn.feature_extraction.text import TfidfVectorizer

        if not hasattr(self, "_tfidf"):
            self._tfidf = TfidfVectorizer(max_features=768)
            self._tfidf_fitted = False
        if not self._tfidf_fitted:
            self._tfidf.fit([text])
            self._tfidf_fitted = True
            self.dim = len(self._tfidf.vocabulary_)
        vec = self._tfidf.transform([text]).toarray()[0]
        if len(vec) < 768:
            vec = np.pad(vec, (0, 768 - len(vec)))
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec
