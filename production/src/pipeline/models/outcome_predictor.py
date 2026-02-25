import json
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
OUTPUTS_DIR = BASE_DIR / "production" / "outputs"
MODELS_DIR = BASE_DIR / "production" / "models"

FINAL_STATUSES = {
    "accept": ["completed accept", "accept", "accepted"],
    "reject": ["completed reject", "reject", "rejected", "desk reject"],
}


class ManuscriptOutcomePredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = [
            "scope_similarity",
            "abstract_length",
            "n_keywords",
            "n_authors",
            "author_h_index_max",
            "author_h_index_mean",
            "author_citation_max",
            "has_freemail",
            "keyword_scope_overlap",
        ]

    def train(self, journals: list = None) -> dict:
        X, y = self._build_training_data(journals)
        if len(X) < 5:
            return {"status": "insufficient_data", "n_samples": len(X)}

        from sklearn.preprocessing import StandardScaler
        from sklearn.model_selection import cross_val_score, LeaveOneOut

        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        n = len(X)
        best_model = None
        best_score = -1.0
        best_name = ""

        candidates = self._get_model_candidates(n)
        cv = LeaveOneOut() if n < 20 else 5

        for name, model in candidates:
            try:
                scores = cross_val_score(model, X_scaled, y, cv=cv, scoring="accuracy")
                mean_score = float(np.mean(scores))
                if mean_score > best_score:
                    best_score = mean_score
                    best_model = model
                    best_name = name
            except Exception:
                continue

        if best_model is None:
            return {"status": "training_failed", "n_samples": n}

        best_model.fit(X_scaled, y)
        self.model = best_model

        return {
            "status": "trained",
            "n_samples": n,
            "model_type": best_name,
            "cv_accuracy": round(best_score, 3),
            "positive_rate": round(float(np.mean(y)), 3),
        }

    def predict(self, manuscript: dict, journal_code: str = None) -> float:
        if self.model is None or self.scaler is None:
            return 0.5
        features = self._extract_features(manuscript, journal_code)
        X = np.array([[features.get(f, 0.0) for f in self.feature_names]])
        X_scaled = self.scaler.transform(X)
        proba = self.model.predict_proba(X_scaled)
        pos_idx = list(self.model.classes_).index(1) if 1 in self.model.classes_ else 0
        return float(proba[0][pos_idx])

    def save(self, path: Path = None):
        if path is None:
            path = MODELS_DIR
        path.mkdir(parents=True, exist_ok=True)
        if self.model is not None:
            import joblib

            joblib.dump(
                {"model": self.model, "scaler": self.scaler}, path / "outcome_predictor.joblib"
            )

    def load(self, path: Path = None) -> bool:
        if path is None:
            path = MODELS_DIR
        model_path = path / "outcome_predictor.joblib"
        if model_path.exists():
            import joblib

            data = joblib.load(model_path)
            self.model = data["model"]
            self.scaler = data["scaler"]
            return True
        return False

    def _get_model_candidates(self, n: int) -> list:
        from sklearn.linear_model import LogisticRegression

        models = [
            ("logistic_regression", LogisticRegression(C=0.1, random_state=42, max_iter=1000))
        ]

        if n >= 20:
            from sklearn.ensemble import GradientBoostingClassifier

            models.append(
                (
                    "gradient_boosting",
                    GradientBoostingClassifier(
                        n_estimators=30, max_depth=2, min_samples_leaf=3, random_state=42
                    ),
                )
            )

        if n >= 30:
            from sklearn.ensemble import RandomForestClassifier

            models.append(
                (
                    "random_forest",
                    RandomForestClassifier(
                        n_estimators=50, max_depth=3, min_samples_leaf=3, random_state=42
                    ),
                )
            )

        return models

    def _build_training_data(self, journals: list = None) -> tuple:
        if journals is None:
            journals = [d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir()]

        samples_X = []
        samples_y = []

        for journal in journals:
            journal_dir = OUTPUTS_DIR / journal
            if not journal_dir.exists():
                continue
            latest = _find_latest_json(journal_dir)
            if not latest:
                continue
            data = _load_json(latest)
            for ms in data.get("manuscripts", []):
                label = _classify_outcome(ms)
                if label is None:
                    continue
                features = self._extract_features(ms, journal)
                row = [features.get(f, 0.0) for f in self.feature_names]
                samples_X.append(row)
                samples_y.append(label)

        return np.array(samples_X) if samples_X else np.array([]).reshape(
            0, len(self.feature_names)
        ), np.array(samples_y)

    def _extract_features(self, ms: dict, journal_code: str = None) -> dict:
        abstract = ms.get("abstract", "") or ""
        keywords = ms.get("keywords", []) or []
        authors = ms.get("authors", []) or []

        h_indices = []
        citation_counts = []
        has_freemail = False
        freemail_domains = {
            "gmail.com",
            "yahoo.com",
            "hotmail.com",
            "outlook.com",
            "qq.com",
            "163.com",
        }

        for author in authors:
            wp = author.get("web_profile") or {}
            h = wp.get("h_index") or 0
            c = wp.get("citation_count") or 0
            if h:
                h_indices.append(h)
            if c:
                citation_counts.append(c)
            email = (author.get("email") or "").lower()
            if any(d in email for d in freemail_domains):
                has_freemail = True

        scope_sim = 0.5
        if journal_code and abstract:
            try:
                from pipeline.embeddings import get_engine
                from pipeline.desk_rejection import JOURNAL_SCOPES_LLM

                scope_desc = JOURNAL_SCOPES_LLM.get(journal_code.upper(), "")
                if scope_desc:
                    engine = get_engine()
                    scope_sim = max(0.0, engine.similarity(abstract[:2000], scope_desc))
            except Exception:
                pass

        keyword_overlap = 0.0
        if journal_code and keywords:
            try:
                from pipeline.desk_rejection import JOURNAL_SCOPE_KEYWORDS

                scope_kw = set(JOURNAL_SCOPE_KEYWORDS.get(journal_code.upper(), []))
                ms_words = set()
                for kw in keywords:
                    ms_words.update(kw.lower().split())
                if scope_kw and ms_words:
                    keyword_overlap = len(ms_words & scope_kw) / max(len(ms_words), 1)
            except Exception:
                pass

        return {
            "scope_similarity": scope_sim,
            "abstract_length": min(len(abstract.split()) / 300.0, 1.0),
            "n_keywords": min(len(keywords) / 8.0, 1.0),
            "n_authors": min(len(authors) / 6.0, 1.0),
            "author_h_index_max": min(max(h_indices) / 40.0, 1.0) if h_indices else 0.0,
            "author_h_index_mean": min((sum(h_indices) / len(h_indices)) / 20.0, 1.0)
            if h_indices
            else 0.0,
            "author_citation_max": min(max(citation_counts) / 5000.0, 1.0)
            if citation_counts
            else 0.0,
            "has_freemail": 1.0 if has_freemail else 0.0,
            "keyword_scope_overlap": keyword_overlap,
        }


def _classify_outcome(ms: dict) -> int | None:
    status = (ms.get("status") or ms.get("final_status") or "").lower().strip()
    category = (ms.get("category") or "").lower().strip()
    combined = f"{status} {category}"

    for s in FINAL_STATUSES["accept"]:
        if s in combined:
            return 1
    for s in FINAL_STATUSES["reject"]:
        if s in combined:
            return 0
    return None


def _find_latest_json(journal_dir: Path):
    jsons = sorted(
        journal_dir.glob("*_extraction_*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return jsons[0] if jsons else None


def _load_json(path: Path) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}
