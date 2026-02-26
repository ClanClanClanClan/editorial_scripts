import json
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[4]
OUTPUTS_DIR = BASE_DIR / "production" / "outputs"
MODELS_DIR = BASE_DIR / "production" / "models"


class RefereeResponsePredictor:
    def __init__(self):
        self.model = None
        self.completion_model = None
        self.feature_names = [
            "h_index",
            "acceptance_rate",
            "n_past_reviews",
            "journal_match",
            "expertise_similarity",
            "avg_turnaround",
            "active_load",
            "institution_distance",
        ]

    def train(self, journals: list = None) -> dict:
        X, y_agree, y_complete = self._build_training_data(journals)
        if len(X) < 10:
            return {"status": "insufficient_data", "n_samples": len(X)}

        from sklearn.model_selection import cross_val_score, StratifiedKFold

        n_splits = min(5, min(int(np.sum(y_agree)), int(np.sum(1 - y_agree))))
        if n_splits < 2:
            n_splits = 2
        cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

        self.model = _make_model()
        scores = cross_val_score(self.model, X, y_agree, cv=cv, scoring="accuracy")
        mean_cv = float(np.mean(scores))
        positive_rate = float(np.mean(y_agree))
        baseline = max(positive_rate, 1.0 - positive_rate)

        if mean_cv < baseline + 0.05:
            self.model = None
            return {
                "status": "model_not_useful",
                "n_samples": len(X),
                "cv_accuracy": round(mean_cv, 3),
                "baseline_accuracy": round(baseline, 3),
                "positive_rate": round(positive_rate, 3),
            }

        self.model.fit(X, y_agree)

        result = {
            "status": "trained",
            "n_samples": len(X),
            "cv_accuracy": round(mean_cv, 3),
            "cv_std": round(float(np.std(scores)), 3),
            "positive_rate": round(positive_rate, 3),
        }

        agreed_mask = y_agree == 1
        if np.sum(agreed_mask) >= 10:
            X_agreed = X[agreed_mask]
            y_comp = y_complete[agreed_mask]
            if len(set(y_comp)) >= 2:
                n_comp = min(5, min(int(np.sum(y_comp)), int(np.sum(1 - y_comp))))
                if n_comp >= 2:
                    cv_comp = StratifiedKFold(n_splits=n_comp, shuffle=True, random_state=42)
                    self.completion_model = _make_model()
                    comp_scores = cross_val_score(
                        self.completion_model, X_agreed, y_comp, cv=cv_comp, scoring="accuracy"
                    )
                    self.completion_model.fit(X_agreed, y_comp)
                    result["completion_cv_accuracy"] = round(float(np.mean(comp_scores)), 3)
                    result["completion_n_samples"] = int(np.sum(agreed_mask))

        return result

    def predict(self, features: dict) -> float:
        if self.model is None:
            return 0.5
        X = np.array([[features.get(f, 0.0) for f in self.feature_names]])
        proba = self.model.predict_proba(X)
        pos_idx = list(self.model.classes_).index(1) if 1 in self.model.classes_ else 0
        return float(proba[0][pos_idx])

    def predict_completion(self, features: dict) -> float:
        if self.completion_model is None:
            return 0.5
        X = np.array([[features.get(f, 0.0) for f in self.feature_names]])
        proba = self.completion_model.predict_proba(X)
        pos_idx = (
            list(self.completion_model.classes_).index(1)
            if 1 in self.completion_model.classes_
            else 0
        )
        return float(proba[0][pos_idx])

    def predict_for_candidate(self, candidate: dict, manuscript: dict, journal: str) -> float:
        wp = candidate.get("web_profile") or {}
        h_index = wp.get("h_index") or candidate.get("h_index") or 0
        stats = self._get_referee_stats(candidate)

        ms_authors = manuscript.get("authors", [])
        cand_inst = (candidate.get("institution") or "").lower()
        inst_distance = 1.0
        if cand_inst:
            for a in ms_authors:
                a_inst = (a.get("institution") or "").lower()
                if a_inst and (cand_inst in a_inst or a_inst in cand_inst):
                    inst_distance = 0.0
                    break

        features = {
            "h_index": min(h_index / 30.0, 1.0),
            "acceptance_rate": stats.get("acceptance_rate", 0.5),
            "n_past_reviews": min(stats.get("n_reviews", 0) / 10.0, 1.0),
            "journal_match": 1.0 if stats.get("journals", {}).get(journal, 0) > 0 else 0.0,
            "expertise_similarity": candidate.get("semantic_similarity", 0.5),
            "avg_turnaround": min(stats.get("avg_turnaround_days", 30) / 60.0, 1.0),
            "active_load": min(stats.get("active_reviews", 0) / 5.0, 1.0),
            "institution_distance": inst_distance,
        }
        return self.predict(features)

    def save(self, path: Path = None):
        if path is None:
            path = MODELS_DIR
        path.mkdir(parents=True, exist_ok=True)
        if self.model is not None:
            import joblib

            data = {"model": self.model, "completion_model": self.completion_model}
            joblib.dump(data, path / "response_predictor.joblib")

    def load(self, path: Path = None) -> bool:
        if path is None:
            path = MODELS_DIR
        model_path = path / "response_predictor.joblib"
        if model_path.exists():
            import joblib

            data = joblib.load(model_path)
            if isinstance(data, dict):
                self.model = data.get("model")
                self.completion_model = data.get("completion_model")
            else:
                self.model = data
            return self.model is not None
        return False

    def _build_training_data(self, journals: list = None) -> tuple:
        if journals is None:
            journals = [d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir()]

        referee_history = {}
        all_referees = []

        for journal in journals:
            journal_dir = OUTPUTS_DIR / journal
            if not journal_dir.exists():
                continue
            for json_path in sorted(journal_dir.glob("*_extraction_*.json")):
                data = _load_json(json_path)
                for ms in data.get("manuscripts", []):
                    ms_keywords = ms.get("keywords", []) or []
                    for ref in ms.get("referees", []):
                        all_referees.append((ref, journal, ms_keywords))

        for ref, journal, _ in all_referees:
            key = ref.get("email", "").lower().strip() or ref.get("name", "").lower().strip()
            if not key:
                continue
            if key not in referee_history:
                referee_history[key] = {
                    "n_invited": 0,
                    "n_agreed": 0,
                    "n_completed": 0,
                    "journals": {},
                    "turnaround_days": [],
                    "active_count": 0,
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

            days = _extract_turnaround_days(ref)
            if days is not None:
                referee_history[key]["turnaround_days"].append(days)

            if any(s in status for s in ["agreed", "awaiting", "in progress", "overdue"]):
                referee_history[key]["active_count"] += 1

        samples_X = []
        samples_y_agree = []
        samples_y_complete = []

        for ref, journal, ms_keywords in all_referees:
            status = (ref.get("status") or "").lower()
            if not status:
                continue

            agreed = any(s in status for s in ["agreed", "complete", "submitted", "overdue"])
            declined = any(s in status for s in ["declined", "uninvited", "no response"])
            if not agreed and not declined:
                continue

            completed = any(s in status for s in ["complete", "submitted"])

            key = ref.get("email", "").lower().strip() or ref.get("name", "").lower().strip()
            stats = referee_history.get(key, {})
            wp = ref.get("web_profile") or {}
            h_index = wp.get("h_index") or 0

            n_inv = stats.get("n_invited", 1)
            acceptance_rate = stats.get("n_agreed", 0) / max(n_inv, 1)
            turnaround_days = stats.get("turnaround_days", [])
            avg_turnaround = sum(turnaround_days) / len(turnaround_days) if turnaround_days else 30

            ref_topics = wp.get("research_topics") or []
            expertise_sim = _keyword_overlap(ref_topics, ms_keywords)

            inst = (ref.get("institution") or "").lower()
            inst_distance = 1.0 if inst else 0.5

            journal_count = stats.get("journals", {}).get(journal, 0)
            prior_journal_reviews = max(0, journal_count - 1)
            features = [
                min(h_index / 30.0, 1.0),
                acceptance_rate,
                min(n_inv / 10.0, 1.0),
                1.0 if prior_journal_reviews > 0 else 0.0,
                expertise_sim,
                min(avg_turnaround / 60.0, 1.0),
                min(stats.get("active_count", 0) / 5.0, 1.0),
                inst_distance,
            ]
            samples_X.append(features)
            samples_y_agree.append(1 if agreed else 0)
            samples_y_complete.append(1 if completed else 0)

        n_features = len(self.feature_names)
        X = np.array(samples_X) if samples_X else np.array([]).reshape(0, n_features)
        return X, np.array(samples_y_agree), np.array(samples_y_complete)

    def _get_referee_stats(self, candidate: dict) -> dict:
        return candidate.get(
            "_referee_stats",
            {
                "acceptance_rate": 0.5,
                "n_reviews": 0,
                "journals": {},
                "avg_turnaround_days": 30,
                "active_reviews": 0,
            },
        )


def _make_model():
    try:
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=50,
            max_depth=3,
            min_child_weight=5,
            learning_rate=0.1,
            random_state=42,
            eval_metric="logloss",
        )
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier

        return GradientBoostingClassifier(
            n_estimators=50, max_depth=3, min_samples_leaf=5, random_state=42
        )


def _extract_turnaround_days(ref: dict) -> int | None:
    invited = ref.get("date_invited") or ref.get("invitation_date")
    completed = ref.get("date_completed") or ref.get("report_date")
    if not invited or not completed:
        return None
    try:
        from datetime import datetime

        for fmt in ["%Y-%m-%d", "%d %b %Y", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"]:
            try:
                d1 = datetime.strptime(str(invited).strip()[:19], fmt)
                d2 = datetime.strptime(str(completed).strip()[:19], fmt)
                days = (d2 - d1).days
                return max(0, days) if days < 365 else None
            except ValueError:
                continue
    except Exception:
        pass
    return None


def _keyword_overlap(topics: list, keywords: list) -> float:
    if not topics or not keywords:
        return 0.5
    topic_words = set()
    for t in topics:
        topic_words.update(str(t).lower().split())
    kw_words = set()
    for k in keywords:
        kw_words.update(str(k).lower().split())
    if not topic_words or not kw_words:
        return 0.5
    common = topic_words & kw_words
    union = topic_words | kw_words
    return len(common) / len(union) if union else 0.5


def _load_json(path: Path) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}
