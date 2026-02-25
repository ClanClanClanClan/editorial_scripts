import re

CONSTRUCTIVE_WORDS = {
    "suggest",
    "consider",
    "recommend",
    "improve",
    "clarify",
    "strengthen",
    "expand",
    "elaborate",
    "revise",
    "address",
    "could",
    "might",
    "alternative",
    "opportunity",
    "enhance",
    "would benefit",
}
NEGATIVE_ONLY_WORDS = {
    "wrong",
    "poor",
    "inadequate",
    "fails",
    "unacceptable",
    "reject",
    "flawed",
    "trivial",
    "superficial",
    "meaningless",
}
SPECIFIC_PATTERNS = [
    r"(?:equation|eq\.?\s*)\(?(\d+)\)?",
    r"(?:figure|fig\.?\s*)\(?(\d+)\)?",
    r"(?:table)\s*(\d+)",
    r"(?:theorem|lemma|proposition|corollary)\s*(\d+)",
    r"(?:page|p\.?\s*)\s*(\d+)",
    r"\[[\d,\s\-]+\]",
    r"(?:section|sec\.?\s*)\s*(\d+)",
]
RECOMMENDATION_SENTIMENT = {
    "accept": 1.0,
    "minor revision": 0.7,
    "minor revisions": 0.7,
    "major revision": 0.3,
    "major revisions": 0.3,
    "reject": 0.0,
}


def assess_report_quality(manuscript: dict) -> dict:
    referees = manuscript.get("referees", []) or []
    reports = []

    for ref in referees:
        ref_reports = ref.get("reports", []) or []
        for report in ref_reports:
            score = _score_single_report(report, manuscript, ref)
            reports.append(score)

        if not ref_reports and ref.get("recommendation"):
            score = _score_from_recommendation_only(ref)
            reports.append(score)

    consensus = _compute_consensus(reports) if len(reports) >= 2 else {}
    overall = sum(r.get("overall", 0) for r in reports) / max(len(reports), 1)

    return {
        "reports": reports,
        "consensus": consensus,
        "overall_quality": round(overall, 3),
        "n_reports": len(reports),
    }


def _score_single_report(report: dict, manuscript: dict, referee: dict) -> dict:
    text = (
        (report.get("comments_to_author", "") or "") + " " + (report.get("raw_text", "") or "")
    ).strip()
    recommendation = report.get("recommendation", "") or referee.get("recommendation", "") or ""

    word_count = len(text.split()) if text else 0
    length_score = min(word_count / 200.0, 1.0)

    specificity_score = 0.0
    if text:
        specific_count = sum(len(re.findall(p, text, re.IGNORECASE)) for p in SPECIFIC_PATTERNS)
        specificity_score = min(specific_count / 5.0, 1.0)

    constructiveness_score = _constructiveness(text)

    engagement_score = 0.0
    if text and manuscript.get("abstract"):
        try:
            from pipeline.embeddings import get_engine

            engine = get_engine()
            engagement_score = max(
                0.0, engine.similarity(text[:2000], manuscript["abstract"][:2000])
            )
        except Exception:
            pass

    consistency_score = _recommendation_consistency(text, recommendation)

    overall = (
        0.25 * length_score
        + 0.20 * specificity_score
        + 0.20 * constructiveness_score
        + 0.20 * engagement_score
        + 0.15 * consistency_score
    )

    return {
        "reviewer": referee.get("name", "Unknown"),
        "recommendation": recommendation,
        "word_count": word_count,
        "length_score": round(length_score, 3),
        "specificity_score": round(specificity_score, 3),
        "constructiveness_score": round(constructiveness_score, 3),
        "engagement_score": round(engagement_score, 3),
        "consistency_score": round(consistency_score, 3),
        "overall": round(overall, 3),
    }


def _score_from_recommendation_only(referee: dict) -> dict:
    return {
        "reviewer": referee.get("name", "Unknown"),
        "recommendation": referee.get("recommendation", ""),
        "word_count": 0,
        "length_score": 0.0,
        "specificity_score": 0.0,
        "constructiveness_score": 0.0,
        "engagement_score": 0.0,
        "consistency_score": 0.0,
        "overall": 0.0,
    }


def _constructiveness(text: str) -> float:
    if not text:
        return 0.0
    lower = text.lower()
    constructive = sum(1 for w in CONSTRUCTIVE_WORDS if w in lower)
    negative = sum(1 for w in NEGATIVE_ONLY_WORDS if w in lower)
    total = constructive + negative
    if total == 0:
        return 0.5
    return constructive / total


def _recommendation_consistency(text: str, recommendation: str) -> float:
    if not text or not recommendation:
        return 0.5
    rec_lower = recommendation.lower().strip()
    rec_sentiment = None
    for key, val in RECOMMENDATION_SENTIMENT.items():
        if key in rec_lower:
            rec_sentiment = val
            break
    if rec_sentiment is None:
        return 0.5

    lower = text.lower()
    positive_words = sum(
        1
        for w in ["excellent", "well-written", "strong", "novel", "important", "interesting"]
        if w in lower
    )
    negative_words = sum(
        1 for w in ["weak", "unclear", "missing", "error", "incorrect", "confusing"] if w in lower
    )
    total = positive_words + negative_words
    if total == 0:
        return 0.5
    text_sentiment = positive_words / total
    return 1.0 - abs(rec_sentiment - text_sentiment)


def _compute_consensus(reports: list) -> dict:
    recommendations = [
        r["recommendation"].lower().strip() for r in reports if r.get("recommendation")
    ]
    if len(recommendations) < 2:
        return {}

    sentiments = []
    for rec in recommendations:
        for key, val in RECOMMENDATION_SENTIMENT.items():
            if key in rec:
                sentiments.append(val)
                break

    recommendation_agreement = 1.0 if len(set(recommendations)) == 1 else 0.0
    sentiment_spread = max(sentiments) - min(sentiments) if len(sentiments) >= 2 else 0.0
    sentiment_agreement = 1.0 - sentiment_spread

    texts = [
        (r.get("word_count", 0), r.get("reviewer", ""))
        for r in reports
        if r.get("word_count", 0) > 50
    ]

    return {
        "n_reviewers": len(reports),
        "recommendation_agreement": round(recommendation_agreement, 3),
        "sentiment_agreement": round(sentiment_agreement, 3),
        "recommendations": recommendations,
    }
