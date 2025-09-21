AI Governance – ECC Implementation
=================================

OpenAI Integration
- Client: src/ecc/adapters/ai/openai_client.py
- API endpoints: src/ecc/interfaces/api/ai_analysis.py
  - POST /api/ai/analyze: runs analysis and persists AIAnalysisModel
  - POST /api/ai/{analysis_id}/review: stores human review JSON and enables agreement calculation

Confidence Thresholds & HIL
- Endpoints accept `confidence_threshold`; set `human_review_required` if below threshold.
- Human review endpoint records reviewer decision and rationale.

Metrics & Audit
- AI analysis metrics recorded via telemetry.
- Store evidence and reasoning in DB; human review JSON captures decision and overrides.

Next Steps
- Improve prompt composition using real manuscript text & metadata.
- Add agreement metrics to /api/ai/stats endpoint; surface per-journal accuracy.

