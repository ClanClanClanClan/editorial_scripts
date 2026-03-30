import json
import subprocess
import time

from pipeline import MODELS_DIR

FEEDBACK_DIR = MODELS_DIR / "feedback"


class ModelTrainer:
    def __init__(self):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)

    def train_all(self, journals: list = None) -> dict:
        results = {}
        print("\n=== Model Training ===\n")

        print("1. Building expertise index...")
        t0 = time.time()
        results["expertise_index"] = self._train_expertise_index(journals)
        print(
            f"   {results['expertise_index'].get('n_referees', 0)} referees indexed ({time.time()-t0:.1f}s)"
        )

        print("2. Training response predictor...")
        t0 = time.time()
        results["response_predictor"] = self._train_response_predictor(journals)
        rp = results["response_predictor"]
        print(
            f"   {rp.get('status', 'unknown')} — {rp.get('n_samples', 0)} samples, CV={rp.get('cv_accuracy', 'N/A')} ({time.time()-t0:.1f}s)"
        )

        print("3. Training outcome predictor...")
        t0 = time.time()
        results["outcome_predictor"] = self._train_outcome_predictor(journals)
        op = results["outcome_predictor"]
        print(
            f"   {op.get('status', 'unknown')} — {op.get('n_samples', 0)} samples, CV={op.get('cv_accuracy', 'N/A')} ({time.time()-t0:.1f}s)"
        )

        print("4. Validating against resolved predictions...")
        try:
            from pipeline.referee_db import RefereeDB

            db = RefereeDB()
            cal = db.prediction_calibration()
            results["calibration"] = cal
            if cal.get("n_resolved", 0) > 0:
                print(
                    f"   {cal['n_resolved']} resolved — Brier={cal['brier_score']}, skill={cal['brier_skill']}"
                )
            else:
                print("   No resolved predictions yet")
        except Exception as e:
            results["calibration"] = {"status": "error", "message": str(e)}

        results_path = MODELS_DIR / "training_results.json"
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {results_path}")

        marker = MODELS_DIR / ".last_trained"
        marker.write_text(time.strftime("%Y-%m-%dT%H:%M:%S"))

        self._write_training_metadata(results)

        return results

    def _write_training_metadata(self, results: dict):
        commit = "unknown"
        try:
            out = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if out.returncode == 0:
                commit = out.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass

        metadata = {
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "commit": commit,
            "expertise_index": results.get("expertise_index", {}),
            "response_predictor": results.get("response_predictor", {}),
            "outcome_predictor": results.get("outcome_predictor", {}),
            "calibration": results.get("calibration", {}),
        }
        metadata_path = MODELS_DIR / "training_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        print(f"Training metadata saved to {metadata_path}")

    def _train_expertise_index(self, journals: list = None) -> dict:
        from pipeline.models.expertise_index import ExpertiseIndex

        idx = ExpertiseIndex()
        n = idx.build(journals)
        if n > 0:
            idx.save()
        return {"n_referees": n, "status": "built" if n > 0 else "empty"}

    def _train_response_predictor(self, journals: list = None) -> dict:
        from pipeline.models.response_predictor import RefereeResponsePredictor

        predictor = RefereeResponsePredictor()
        result = predictor.train(journals)
        if result.get("status") == "trained":
            predictor.save()
        return result

    def _train_outcome_predictor(self, journals: list = None) -> dict:
        from pipeline.models.outcome_predictor import ManuscriptOutcomePredictor

        predictor = ManuscriptOutcomePredictor()
        result = predictor.train(journals)
        if result.get("status") == "trained":
            predictor.save()
        return result

    def record_outcome(self, journal: str, manuscript_id: str, decision: str):
        record = {
            "journal": journal,
            "manuscript_id": manuscript_id,
            "decision": decision,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        feedback_file = FEEDBACK_DIR / f"{journal}_outcomes.jsonl"
        with open(feedback_file, "a") as f:
            f.write(json.dumps(record) + "\n")
        print(f"Recorded: {journal} {manuscript_id} → {decision}")

    def get_feedback_stats(self) -> dict:
        stats = {}
        for f in FEEDBACK_DIR.glob("*_outcomes.jsonl"):
            journal = f.stem.replace("_outcomes", "")
            with open(f) as fh:
                lines = fh.readlines()
            decisions = {}
            for line in lines:
                try:
                    rec = json.loads(line)
                    d = rec.get("decision", "unknown")
                    decisions[d] = decisions.get(d, 0) + 1
                except (json.JSONDecodeError, KeyError):
                    pass
            stats[journal] = {"total": len(lines), "decisions": decisions}
        return stats
