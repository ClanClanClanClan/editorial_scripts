"""Prompt templates for AE recommendation report generation."""

from .desk_rejection import JOURNAL_SCOPES_LLM

SYSTEM_PROMPT = """You are an experienced Associate Editor for {journal_name}.

Journal scope: {journal_scope}

You are writing an AE recommendation report for the Editor-in-Chief. Your report should be concise, professional, and actionable. Base your assessment on the referee reports provided — do not speculate beyond what the referees have evaluated."""

USER_PROMPT = """Write an AE recommendation report for the following manuscript.

## Manuscript

**ID**: {manuscript_id}
**Title**: {title}
**Revision round**: {revision_round}

**Abstract**:
{abstract}

**Keywords**: {keywords}

**Authors**:
{authors_text}

## Referee Reports

{reports_text}

## Referee Consensus

{consensus_text}

## Instructions

Write a structured AE report with these sections:

1. **Summary**: One paragraph summarizing the paper's contribution and methodology.
2. **Assessment of Referee Reports**: For each referee, briefly summarize their main points and evaluate whether their concerns are substantive. Note agreements and disagreements between referees.
3. **Key Issues**: Bullet list of the most important issues that must be addressed (if any).
4. **Recommendation**: One of: Accept, Minor Revision, Major Revision, or Reject. Justify briefly.
5. **Revision Points** (if not Accept/Reject): Numbered list of specific changes the authors should make.

Respond in JSON format:
{{"recommendation": "Accept|Minor Revision|Major Revision|Reject", "confidence": 0.0-1.0, "summary": "one paragraph paper summary", "report": "the full AE report in markdown", "revision_points": ["point 1", "point 2", ...]}}"""


def build_prompt(
    manuscript: dict,
    reports: list[dict],
    consensus: dict,
    journal_code: str,
) -> tuple[str, str]:
    journal_scope = JOURNAL_SCOPES_LLM.get(journal_code.upper(), "")

    authors_text = ""
    for a in manuscript.get("authors", [])[:10]:
        wp = a.get("web_profile") or {}
        h = wp.get("h_index") or "unknown"
        inst = a.get("institution", "unknown")
        authors_text += f"- {a.get('name', '?')} ({inst}), h-index={h}\n"
    if not authors_text:
        authors_text = "(no author data)"

    reports_text = ""
    for i, rpt in enumerate(reports, 1):
        reports_text += f"### Referee {i}: {rpt['name']}\n"
        reports_text += f"**Recommendation**: {rpt.get('recommendation', 'Not stated')}\n"
        if rpt.get("quality_score") is not None:
            reports_text += f"**Report quality score**: {rpt['quality_score']:.2f}\n"
        reports_text += f"\n{rpt.get('text', '(no report text available)')}\n\n"

    consensus_text = ""
    if consensus:
        agreement = consensus.get("recommendation_agreement")
        if agreement is not None:
            consensus_text += f"- Recommendation agreement: {'Yes' if agreement else 'No'}\n"
        sentiment = consensus.get("sentiment_agreement")
        if sentiment is not None:
            consensus_text += f"- Sentiment spread: {sentiment:.2f} (0=divergent, 1=aligned)\n"
    if not consensus_text:
        consensus_text = "(insufficient data for consensus analysis)"

    revision_round = manuscript.get("revision_round", 0)
    round_label = f"R{revision_round}" if revision_round > 0 else "Original submission"

    keywords = manuscript.get("keywords", [])
    keywords_str = ", ".join(keywords) if keywords else "(none)"

    # Use human-readable journal name when available (e.g. MF_WILEY -> "Mathematical Finance")
    from core.output_schema import JOURNAL_NAME_MAP

    journal_name = JOURNAL_NAME_MAP.get(journal_code.upper(), journal_code.upper())

    system = SYSTEM_PROMPT.format(
        journal_name=journal_name,
        journal_scope=journal_scope,
    )
    user = USER_PROMPT.format(
        manuscript_id=manuscript.get("manuscript_id", "?"),
        title=manuscript.get("title", "?"),
        revision_round=round_label,
        abstract=manuscript.get("abstract", "(no abstract)")[:3000],
        keywords=keywords_str,
        authors_text=authors_text,
        reports_text=reports_text,
        consensus_text=consensus_text,
    )
    return system, user
