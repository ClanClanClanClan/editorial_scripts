"""AE recommendation report generator.

Assembles manuscript data + referee reports, generates draft AE reports
via Claude API or clipboard for ChatGPT Pro.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

from . import JOURNALS, OUTPUTS_DIR, _load_json
from .ae_prompt_template import build_prompt
from .report_quality import assess_report_quality


def _latest_extraction(journal: str) -> dict | None:
    journal_dir = OUTPUTS_DIR / journal
    files = sorted(journal_dir.glob(f"{journal}_extraction_*.json"))
    if not files:
        return None
    return _load_json(files[-1])


def _extract_pdf_text(path: str, max_chars: int = 15000) -> str:
    try:
        import fitz

        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
            if len(text) > max_chars:
                break
        doc.close()
        return text[:max_chars]
    except Exception:
        return ""


def _find_manuscript(data: dict, manuscript_id: str) -> dict | None:
    for ms in data.get("manuscripts", []):
        if ms.get("manuscript_id") == manuscript_id:
            return ms
    return None


def _detect_revision_round(manuscript: dict) -> int:
    status = (manuscript.get("status") or "").lower()
    ms_id = manuscript.get("manuscript_id", "")
    r_match = re.search(r"-R(\d+)", ms_id)
    if r_match:
        return int(r_match.group(1))
    if "r1" in status:
        return 1
    if "r2" in status:
        return 2
    if "revision" in status:
        return 1
    return 0


def _collect_report_text(referee: dict, manuscript: dict, journal: str) -> str:
    texts = []

    report = referee.get("report") or {}
    if report.get("comments_to_author"):
        texts.append(report["comments_to_author"])

    for rpt in referee.get("reports", []):
        analysis = rpt.get("analysis") or {}
        raw = analysis.get("raw_text", "")
        if raw:
            texts.append(raw)
        elif rpt.get("path") and os.path.exists(rpt["path"]):
            pdf_text = _extract_pdf_text(rpt["path"])
            if pdf_text:
                texts.append(pdf_text)

    ps = manuscript.get("platform_specific", {})
    ref_name_lower = referee.get("name", "").lower()
    for rpt in ps.get("referee_reports", []):
        if (rpt.get("referee") or "").lower() == ref_name_lower:
            analysis = rpt.get("analysis") or {}
            raw = analysis.get("raw_text", "")
            if raw and raw not in texts:
                texts.append(raw)
            elif rpt.get("path") and os.path.exists(rpt["path"]):
                pdf_text = _extract_pdf_text(rpt["path"])
                if pdf_text and pdf_text not in texts:
                    texts.append(pdf_text)

    docs = ps.get("documents", {}).get("files", [])
    for doc in docs:
        doc_type = doc.get("type", "")
        if doc_type.startswith("referee_report") and doc.get("local_path"):
            if os.path.exists(doc["local_path"]):
                pdf_text = _extract_pdf_text(doc["local_path"])
                if pdf_text and pdf_text not in texts:
                    texts.append(pdf_text)

    if not texts:
        rec = referee.get("recommendation", "")
        if rec:
            texts.append(f"(No report text available. Recommendation: {rec})")

    return "\n\n---\n\n".join(texts)


def _is_report_complete(referee: dict, journal: str) -> bool:
    status = (referee.get("status") or "").lower()
    if status in ("report submitted", "review complete", "completed"):
        return True
    sd = referee.get("status_details", {})
    if sd.get("review_received") or sd.get("review_complete"):
        return True
    report = referee.get("report") or {}
    if report.get("recommendation") or report.get("comments_to_author"):
        return True
    rec = referee.get("recommendation", "")
    if rec and rec.lower() not in ("unknown", "n/a", ""):
        reports = referee.get("reports", [])
        if reports:
            return True
    return False


def assemble(journal: str, manuscript_id: str) -> dict | None:
    data = _latest_extraction(journal)
    if not data:
        print(f"No extraction data for {journal}")
        return None

    manuscript = _find_manuscript(data, manuscript_id)
    if not manuscript:
        print(f"Manuscript {manuscript_id} not found in {journal} extraction")
        return None

    referees = manuscript.get("referees", [])
    completed_refs = [r for r in referees if _is_report_complete(r, journal)]

    if len(completed_refs) < 2:
        print(f"{manuscript_id}: only {len(completed_refs)} reports complete " f"(need at least 2)")
        return None

    reports = []
    for ref in completed_refs:
        text = _collect_report_text(ref, manuscript, journal)
        rec = (
            ref.get("recommendation")
            or (ref.get("report") or {}).get("recommendation")
            or "Not stated"
        )
        report_obj = ref.get("report") or {}
        quality_score = None
        rq = assess_report_quality(manuscript)
        for rq_report in rq.get("reports", []):
            if rq_report.get("reviewer", "").lower() == ref.get("name", "").lower():
                quality_score = rq_report.get("overall")
                break

        reports.append(
            {
                "name": ref.get("name", "Unknown"),
                "email": ref.get("email"),
                "recommendation": rec,
                "text": text,
                "quality_score": quality_score,
                "scores": report_obj.get("scores", {}),
            }
        )

    consensus = rq.get("consensus", {})
    revision_round = _detect_revision_round(manuscript)

    assembled = {
        "manuscript_id": manuscript_id,
        "journal": journal.upper(),
        "title": manuscript.get("title", ""),
        "abstract": manuscript.get("abstract", ""),
        "keywords": manuscript.get("keywords", []),
        "authors": manuscript.get("authors", []),
        "status": manuscript.get("status", ""),
        "revision_round": revision_round,
        "reports": reports,
        "consensus": consensus,
        "report_quality": rq,
    }

    return assembled


def generate(
    journal: str,
    manuscript_id: str,
    provider: str = "claude",
) -> dict | None:
    assembled = assemble(journal, manuscript_id)
    if not assembled:
        return None

    system_prompt, user_prompt = build_prompt(
        manuscript=assembled,
        reports=assembled["reports"],
        consensus=assembled["consensus"],
        journal_code=journal,
    )

    if provider == "clipboard":
        return _generate_clipboard(system_prompt, user_prompt, assembled)
    else:
        result = _generate_claude(system_prompt, user_prompt, assembled)
        if result is None:
            print("Claude API failed — falling back to clipboard mode")
            return _generate_clipboard(system_prompt, user_prompt, assembled)
        return result


def _generate_claude(system_prompt: str, user_prompt: str, assembled: dict) -> dict | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set")
        return None

    try:
        import anthropic
    except ImportError:
        print("anthropic package not installed")
        return None

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = {
                "recommendation": "See report",
                "confidence": 0.0,
                "summary": "",
                "report": text,
                "revision_points": [],
            }

        return _save_report(assembled, result, provider="claude")

    except Exception as e:
        print(f"Claude API error: {e}")
        return None


def _generate_clipboard(system_prompt: str, user_prompt: str, assembled: dict) -> dict:
    full_prompt = f"SYSTEM:\n{system_prompt}\n\n---\n\nUSER:\n{user_prompt}"

    try:
        subprocess.run(["pbcopy"], input=full_prompt.encode(), check=True)
        print(f"\n📋 Prompt copied to clipboard ({len(full_prompt)} chars)")
        print("   Paste into ChatGPT Pro and copy the JSON response back.")
    except Exception:
        prompt_path = (
            OUTPUTS_DIR
            / assembled["journal"].lower()
            / "ae_reports"
            / f"prompt_{assembled['manuscript_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(full_prompt)
        print(f"\n📄 Prompt saved to {prompt_path}")
        print("   Copy contents and paste into ChatGPT Pro.")

    return {
        "manuscript_id": assembled["manuscript_id"],
        "journal": assembled["journal"],
        "provider": "clipboard",
        "status": "awaiting_paste",
        "prompt_length": len(full_prompt),
    }


def _save_report(assembled: dict, llm_result: dict, provider: str) -> dict:
    journal = assembled["journal"].lower()
    ms_id = assembled["manuscript_id"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    out_dir = OUTPUTS_DIR / journal / "ae_reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "manuscript_id": ms_id,
        "journal": assembled["journal"],
        "title": assembled["title"],
        "revision_round": assembled["revision_round"],
        "generated_at": datetime.now().isoformat(),
        "provider": provider,
        "recommendation": llm_result.get("recommendation", ""),
        "confidence": llm_result.get("confidence", 0.0),
        "summary": llm_result.get("summary", ""),
        "report": llm_result.get("report", ""),
        "revision_points": llm_result.get("revision_points", []),
        "referee_count": len(assembled["reports"]),
        "referee_recommendations": [
            {"name": r["name"], "recommendation": r["recommendation"]} for r in assembled["reports"]
        ],
        "report_quality": assembled["report_quality"],
    }

    json_path = out_dir / f"ae_{ms_id}_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    md_path = out_dir / f"ae_{ms_id}_{timestamp}.md"
    md_content = f"""# AE Report: {ms_id}

**Journal**: {assembled['journal']}
**Title**: {assembled['title']}
**Revision Round**: R{assembled['revision_round']} {'(Original)' if assembled['revision_round'] == 0 else ''}
**Generated**: {report['generated_at']}
**Provider**: {provider}

## Recommendation: {report['recommendation']}
**Confidence**: {report['confidence']}

## Summary
{report['summary']}

## Full Report
{report['report']}

## Revision Points
"""
    for i, point in enumerate(report.get("revision_points", []), 1):
        md_content += f"{i}. {point}\n"

    md_path.write_text(md_content)

    print("\n✅ AE report saved:")
    print(f"   JSON: {json_path}")
    print(f"   Markdown: {md_path}")
    print(f"   Recommendation: {report['recommendation']} (confidence: {report['confidence']})")

    return report


def find_manuscripts_needing_ae_report(journal: str = None) -> list[dict]:
    journals = [journal] if journal else JOURNALS
    results = []
    for j in journals:
        data = _latest_extraction(j)
        if not data:
            continue
        for ms in data.get("manuscripts", []):
            refs = ms.get("referees", [])
            completed = [r for r in refs if _is_report_complete(r, j)]
            active = [
                r
                for r in refs
                if not _is_report_complete(r, j)
                and (r.get("status") or "").lower()
                not in ("declined", "terminated", "reviewer declined")
            ]
            if len(completed) >= 2 and len(active) == 0:
                ae_dir = OUTPUTS_DIR / j / "ae_reports"
                existing = list(ae_dir.glob(f"ae_{ms['manuscript_id']}_*.json"))
                results.append(
                    {
                        "journal": j.upper(),
                        "manuscript_id": ms["manuscript_id"],
                        "title": ms.get("title", ""),
                        "completed_reports": len(completed),
                        "has_ae_report": len(existing) > 0,
                    }
                )
    return results


def auto_generate(provider: str = "claude") -> list[dict]:
    candidates = find_manuscripts_needing_ae_report()
    generated = []
    for c in candidates:
        if c["has_ae_report"]:
            print(f"⏭️  {c['journal']}/{c['manuscript_id']}: AE report already exists")
            continue
        print(f"\n🔄 Generating AE report for {c['journal']}/{c['manuscript_id']}...")
        result = generate(c["journal"].lower(), c["manuscript_id"], provider=provider)
        if result:
            generated.append(result)
    return generated


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate AE recommendation reports")
    parser.add_argument("-j", "--journal", help="Journal code")
    parser.add_argument("-m", "--manuscript", help="Manuscript ID")
    parser.add_argument(
        "--provider",
        choices=["claude", "clipboard"],
        default="claude",
        help="LLM provider (default: claude)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-generate for all manuscripts needing AE reports",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List manuscripts needing AE reports",
    )
    args = parser.parse_args()

    if args.list:
        candidates = find_manuscripts_needing_ae_report(args.journal)
        if not candidates:
            print("No manuscripts currently need AE reports.")
            return
        print(f"\n📋 Manuscripts needing AE reports ({len(candidates)}):\n")
        for c in candidates:
            flag = " ✅" if c["has_ae_report"] else ""
            print(
                f"  {c['journal']}/{c['manuscript_id']}: "
                f"{c['completed_reports']} reports — {c['title'][:60]}{flag}"
            )
        return

    if args.auto:
        results = auto_generate(provider=args.provider)
        print(f"\n📊 Generated {len(results)} AE report(s)")
        return

    if not args.journal or not args.manuscript:
        parser.error("--journal and --manuscript required (or use --auto/--list)")

    result = generate(args.journal, args.manuscript, provider=args.provider)
    if not result:
        sys.exit(1)


if __name__ == "__main__":
    main()
