"""Draft editorial decision letters via Claude API."""

import json
import os
from datetime import datetime

from pipeline import OUTPUTS_DIR
from pipeline.ae_report import assemble

VALID_DECISIONS = {"Accept", "Minor Revision", "Major Revision", "Reject"}


def draft_letters(journal, manuscript_id, decision, notes="", provider="claude"):
    if decision not in VALID_DECISIONS:
        raise ValueError(f"Invalid decision '{decision}'. Must be one of: {VALID_DECISIONS}")

    assembled = assemble(journal, manuscript_id)
    if not assembled:
        raise RuntimeError(
            f"Could not assemble data for {journal}/{manuscript_id}. "
            "Ensure at least 2 referee reports are complete."
        )

    eic_system, eic_user = _build_eic_prompt(assembled, decision, notes)
    author_system, author_user = _build_author_prompt(assembled, decision, notes)

    if provider == "claude":
        eic_letter = _call_claude(eic_system, eic_user)
        author_letter = _call_claude(author_system, author_user)
    elif provider == "clipboard":
        eic_letter = _clipboard_fallback(eic_system, eic_user, "EIC")
        author_letter = _clipboard_fallback(author_system, author_user, "Author")
    else:
        raise ValueError(f"Unknown provider '{provider}'. Use 'claude' or 'clipboard'.")

    letters = {
        "eic_letter": eic_letter,
        "author_letter": author_letter,
        "metadata": {
            "journal": journal.upper(),
            "manuscript_id": manuscript_id,
            "title": assembled.get("title", ""),
            "decision": decision,
            "notes": notes,
            "provider": provider,
            "referee_count": len(assembled.get("reports", [])),
            "revision_round": assembled.get("revision_round", 0),
            "generated_at": datetime.now().isoformat(),
        },
    }

    path = _save_decision(journal, manuscript_id, decision, letters)
    letters["metadata"]["saved_to"] = str(path)
    return letters


def _build_eic_prompt(assembled, decision, notes):
    ms_id = assembled["manuscript_id"]
    title = assembled.get("title", "")
    journal = assembled["journal"]
    revision_round = assembled.get("revision_round", 0)

    referee_summaries = []
    for r in assembled.get("reports", []):
        rec = r.get("recommendation", "Not stated")
        quality = r.get("quality_score")
        quality_str = f" (quality: {quality:.1f}/10)" if quality else ""
        text_preview = (r.get("text") or "")[:500]
        referee_summaries.append(
            f"- {r['name']}: Recommends {rec}{quality_str}\n  Report excerpt: {text_preview}"
        )

    consensus = assembled.get("consensus", {})
    consensus_str = ""
    if consensus:
        consensus_str = f"\nReferee consensus: {consensus.get('label', 'Mixed')}"

    system_prompt = (
        "You are drafting a letter from an Associate Editor to the Editor-in-Chief "
        f"of {journal}. The letter should be professional, concise, and provide a clear "
        "recommendation with supporting reasoning based on the referee reports."
    )

    user_prompt = (
        f"Manuscript: {ms_id}\n"
        f"Title: {title}\n"
        f"Revision Round: R{revision_round}\n"
        f"AE Decision: {decision}\n"
        f"{consensus_str}\n\n"
        f"Referee Reports:\n"
        + "\n".join(referee_summaries)
        + f"\n\nAdditional AE Notes: {notes}\n\n"
        "Draft a letter to the Editor-in-Chief explaining the AE recommendation. "
        "Include: (1) a brief summary of the manuscript, (2) key points from each referee, "
        "(3) the AE's assessment and recommendation, (4) any specific conditions or points "
        "for the authors to address if revision is recommended."
    )

    return system_prompt, user_prompt


def _build_author_prompt(assembled, decision, notes):
    ms_id = assembled["manuscript_id"]
    title = assembled.get("title", "")
    journal = assembled["journal"]

    referee_summaries = []
    for i, r in enumerate(assembled.get("reports", []), 1):
        rec = r.get("recommendation", "Not stated")
        text_preview = (r.get("text") or "")[:800]
        referee_summaries.append(f"Referee {i} ({rec}):\n{text_preview}")

        scores = r.get("scores", {})
        if scores:
            score_str = ", ".join(f"{k}: {v}" for k, v in scores.items())
            referee_summaries.append(f"  Scores: {score_str}")

    system_prompt = (
        f"You are drafting a decision letter to the authors of a manuscript submitted to {journal}. "
        "The letter should be professional, constructive, and clearly communicate the editorial decision."
    )

    decision_guidance = {
        "Accept": (
            "Congratulate the authors on their accepted manuscript. "
            "Mention any minor suggestions from referees that could improve the final version."
        ),
        "Minor Revision": (
            "Inform the authors that minor revision is required. "
            "List the specific points each referee raised that must be addressed. "
            "Set a clear expectation for the revision."
        ),
        "Major Revision": (
            "Inform the authors that major revision is required. "
            "Clearly outline the substantial concerns raised by referees. "
            "Emphasize that a thorough revision addressing all points is expected."
        ),
        "Reject": (
            "Inform the authors of the rejection decision with empathy. "
            "Provide clear explanation of the key reasons based on referee feedback. "
            "Offer constructive suggestions for improving the work."
        ),
    }

    user_prompt = (
        f"Manuscript: {ms_id}\n"
        f"Title: {title}\n"
        f"Decision: {decision}\n\n"
        f"Referee Reports:\n"
        + "\n\n".join(referee_summaries)
        + f"\n\nAdditional Notes: {notes}\n\n"
        f"Instructions: {decision_guidance[decision]}\n\n"
        "Draft the decision letter addressed to 'Dear Authors'. "
        "Do not include the referee reports verbatim; instead, summarize key points."
    )

    return system_prompt, user_prompt


def _call_claude(system_prompt, user_prompt):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    try:
        import anthropic
    except ImportError as err:
        raise RuntimeError("anthropic package not installed: pip install anthropic") from err

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    if not response.content:
        raise RuntimeError("Claude API returned empty content")
    return response.content[0].text


def _clipboard_fallback(system_prompt, user_prompt, label):
    import subprocess

    full_prompt = f"SYSTEM:\n{system_prompt}\n\n---\n\nUSER:\n{user_prompt}"
    try:
        subprocess.run(["pbcopy"], input=full_prompt.encode(), check=True)
        print(f"\n[{label}] Prompt copied to clipboard ({len(full_prompt)} chars)")
    except Exception:
        print(f"\n[{label}] Could not copy to clipboard")
    return f"[Prompt for {label} letter copied to clipboard — paste into LLM]"


def _save_decision(journal, manuscript_id, decision, letters):
    out_dir = OUTPUTS_DIR / journal.lower() / "decisions"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = out_dir / f"decision_{manuscript_id}_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(letters, f, indent=2, default=str)

    md_path = out_dir / f"decision_{manuscript_id}_{timestamp}.md"
    meta = letters["metadata"]
    md_content = (
        f"# Decision: {manuscript_id}\n\n"
        f"**Journal**: {meta['journal']}\n"
        f"**Title**: {meta['title']}\n"
        f"**Decision**: {meta['decision']}\n"
        f"**Generated**: {meta['generated_at']}\n"
        f"**Provider**: {meta['provider']}\n\n"
        f"---\n\n"
        f"## Letter to Editor-in-Chief\n\n"
        f"{letters['eic_letter']}\n\n"
        f"---\n\n"
        f"## Letter to Authors\n\n"
        f"{letters['author_letter']}\n"
    )
    md_path.write_text(md_content)

    print("\nDecision letters saved:")
    print(f"  JSON: {json_path}")
    print(f"  Markdown: {md_path}")

    return json_path
