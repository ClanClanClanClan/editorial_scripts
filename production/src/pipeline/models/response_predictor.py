import json
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
OUTPUTS_DIR = BASE_DIR / "production" / "outputs"
MODELS_DIR = BASE_DIR / "production" / "models"


class RefereeResponsePredictor:
    def __init__(self):
        self.model = None
        self.feature_names = [
            "h_index",
            "acceptance_rate",
            "n_past_reviews",
            "journal_match",
            "expertise_similarity",
        ]

    def train(self, journals: list = None) -> dict:
        X, y = self._build_training_data(journals)
        if len(X) < 10:
            return {"status": "insufficient_data", "n_samples": len(X)}

        from sklearn.model_selection import cross_val_score

        try:
            from xgboost import XGBClassifier

            self.model = XGBClassifier(
                n_estimators=50,
                max_depth=3,
                min_child_weight=5,
                learning_rate=0.1,
                random_state=42,
                eval_metric="logloss",
            )
        except ImportError:
            from sklearn.ensemble import GradientBoostingClassifier

            self.model = GradientBoostingClassifier(
                n_estimators=50, max_depth=3, min_samples_leaf=5, random_state=42
            )

        scores = cross_val_score(self.model, X, y, cv=min(5, len(X)), scoring="accuracy")
        self.model.fit(X, y)

        return {
            "status": "trained",
            "n_samples": len(X),
            "cv_accuracy": round(float(np.mean(scores)), 3),
            "cv_std": round(float(np.std(scores)), 3),
            "positive_rate": round(float(np.mean(y)), 3),
        }

    def predict(self, features: dict) -> float:
        if self.model is None:
            return 0.5
        X = np.array([[features.get(f, 0.0) for f in self.feature_names]])
        proba = self.model.predict_proba(X)
        pos_idx = list(self.model.classes_).index(1) if 1 in self.model.classes_ else 0
        return float(proba[0][pos_idx])

    def predict_for_candidate(self, candidate: dict, manuscript: dict, journal: str) -> float:
        wp = candidate.get("web_profile") or {}
        h_index = wp.get("h_index") or 0
        stats = self._get_referee_stats(candidate)

        features = {
            "h_index": min(h_index / 30.0, 1.0),
            "acceptance_rate": stats.get("acceptance_rate", 0.5),
            "n_past_reviews": min(stats.get("n_reviews", 0) / 10.0, 1.0),
            "journal_match": 1.0 if stats.get("journals", {}).get(journal, 0) > 0 else 0.0,
            "expertise_similarity": candidate.get("semantic_similarity", 0.5),
        }
        return self.predict(features)

    def save(self, path: Path = None):
        if path is None:
            path = MODELS_DIR
        path.mkdir(parents=True, exist_ok=True)
        if self.model is not None:
            import joblib

            joblib.dump(self.model, path / "response_predictor.joblib")

    def load(self, path: Path = None) -> bool:
        if path is None:
            path = MODELS_DIR
        model_path = path / "response_predictor.joblib"
        if model_path.exists():
            import joblib

            self.model = joblib.load(model_path)
            return True
        return False

    def _build_training_data(self, journals: list = None) -> tuple:
        if journals is None:
            journals = [d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir()]

        referee_history = {}
        samples_X = []
        samples_y = []

        all_referees = []
        for journal in journals:
            journal_dir = OUTPUTS_DIR / journal
            if not journal_dir.exists():
                continue
            for json_path in sorted(journal_dir.glob("*_extraction_*.json")):
                data = _load_json(json_path)
                for ms in data.get("manuscripts", []):
                    for ref in ms.get("referees", []):
                        all_referees.append((ref, journal))

        for ref, journal in all_referees:
            key = ref.get("email", "").lower().strip() or ref.get("name", "").lower().strip()
            if not key:
                continue
            if key not in referee_history:
                referee_history[key] = {
                    "n_invited": 0,
                    "n_agreed": 0,
                    "n_completed": 0,
                    "journals": {},
                }

            status = (ref.get("status") or "").lower()
            referee_history[key]["n_invited"] += 1
            referee_history[key]["journals"][journal] = (
                referee_history[key]["journals"].get(journal, 0) + 1
            )

            if any(s in status for s in ["agreed", "complete", "submitted", "overdue"]):
                referee_history[key]["n_agreed"] += 1
            if any(s in status for s in ["complete", "submitted"]):
                referee_history[key]["n_completed"] += 1

        for ref, journal in all_referees:
            status = (ref.get("status") or "").lower()
            if not status:
                continue

            agreed = any(s in status for s in ["agreed", "complete", "submitted", "overdue"])
            declined = any(s in status for s in ["declined", "uninvited", "no response"])
            if not agreed and not declined:
                continue

            key = ref.get("email", "").lower().strip() or ref.get("name", "").lower().strip()
            stats = referee_history.get(key, {})
            wp = ref.get("web_profile") or {}
            h_index = wp.get("h_index") or 0

            n_inv = stats.get("n_invited", 1)
            acceptance_rate = stats.get("n_agreed", 0) / max(n_inv, 1)

            features = [
                min(h_index / 30.0, 1.0),
                acceptance_rate,
                min(n_inv / 10.0, 1.0),
                1.0 if stats.get("journals", {}).get(journal, 0) > 1 else 0.0,
                0.5,
            ]
            samples_X.append(features)
            samples_y.append(1 if agreed else 0)

        return np.array(samples_X) if samples_X else np.array([]).reshape(0, 5), np.array(samples_y)

    def _get_referee_stats(self, candidate: dict) -> dict:
        return candidate.get(
            "_referee_stats", {"acceptance_rate": 0.5, "n_reviews": 0, "journals": {}}
        )


def _load_json(path: Path) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}
