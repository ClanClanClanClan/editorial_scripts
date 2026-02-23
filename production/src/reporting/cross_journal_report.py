#!/usr/bin/env python3
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

OUTPUTS_DIR = Path(__file__).parent.parent.parent / "outputs"

JOURNALS = ["mf", "mor", "fs", "jota", "mafe", "sicon", "sifin", "naco"]

JOURNAL_NAMES = {
    "mf": "Mathematical Finance",
    "mor": "Math. Operations Research",
    "fs": "Finance & Stochastics",
    "jota": "JOTA",
    "mafe": "MAFE",
    "sicon": "SICON",
    "sifin": "SIFIN",
    "naco": "NACO",
}

PLATFORMS = {
    "mf": "ScholarOne",
    "mor": "ScholarOne",
    "fs": "Gmail",
    "jota": "Editorial Mgr",
    "mafe": "Editorial Mgr",
    "sicon": "SIAM",
    "sifin": "SIAM",
    "naco": "EditFlow",
}


def find_latest_output(journal: str) -> Optional[Path]:
    journal_dir = OUTPUTS_DIR / journal
    if not journal_dir.exists():
        return None
    files = sorted(journal_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in files:
        if "BASELINE" in f.name or "debug" in str(f):
            continue
        return f
    return None


def load_journal_data(journal: str) -> Optional[Dict]:
    path = find_latest_output(journal)
    if not path:
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        data["_source_file"] = path.name
        data["_source_path"] = str(path)
        return data
    except (json.JSONDecodeError, OSError):
        return None


def compute_journal_stats(journal: str, data: Dict) -> Dict:
    manuscripts = data.get("manuscripts", [])
    ms_count = len(manuscripts)

    total_refs = sum(len(m.get("referees", [])) for m in manuscripts)
    total_authors = sum(len(m.get("authors", [])) for m in manuscripts)

    enriched = sum(
        1
        for m in manuscripts
        for p in m.get("referees", []) + m.get("authors", [])
        if p.get("web_profile")
    )
    total_people = total_refs + total_authors

    span_days = []
    response_days = []
    for m in manuscripts:
        ta = m.get("timeline_analytics", {})
        if ta.get("communication_span_days"):
            span_days.append(ta["communication_span_days"])
        rta = ta.get("response_time_analysis", {})
        if rta.get("average_response_days"):
            response_days.append(rta["average_response_days"])

    avg_span = round(sum(span_days) / len(span_days), 1) if span_days else None
    avg_response = round(sum(response_days) / len(response_days), 1) if response_days else None

    ts = data.get("extraction_timestamp", "")
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            age_days = (
                (datetime.now(dt.tzinfo) - dt).days if dt.tzinfo else (datetime.now() - dt).days
            )
        except Exception:
            age_days = None
    else:
        age_days = None

    return {
        "journal": journal.upper(),
        "journal_name": JOURNAL_NAMES.get(journal, journal),
        "platform": PLATFORMS.get(journal, ""),
        "manuscripts": ms_count,
        "referees": total_refs,
        "authors": total_authors,
        "enriched": enriched,
        "total_people": total_people,
        "enrichment_pct": round(100 * enriched / total_people, 1) if total_people > 0 else 0,
        "avg_span_days": avg_span,
        "avg_response_days": avg_response,
        "extraction_date": ts[:10] if len(ts) >= 10 else "",
        "age_days": age_days,
        "source_file": data.get("_source_file", ""),
        "schema_version": data.get("schema_version", ""),
    }


def print_terminal_report(all_stats: List[Dict]):
    print()
    print("╔══════════════════════════════════════════════════════════════════════════════════╗")
    print("║                       CROSS-JOURNAL EXTRACTION REPORT                          ║")
    print(
        f"║  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}                                                  ║"
    )
    print("╚══════════════════════════════════════════════════════════════════════════════════╝")
    print()

    header = f"{'Journal':<8} {'Platform':<14} {'MSS':>4} {'Refs':>5} {'Auth':>5} {'Enrich':>7} {'Span':>6} {'Resp':>6} {'Extracted':>11}"
    print(header)
    print("─" * len(header))

    tot_ms = tot_refs = tot_auth = tot_enriched = 0
    active_journals = 0

    for s in all_stats:
        if s is None:
            continue

        ms_str = str(s["manuscripts"]) if s["manuscripts"] > 0 else "—"
        refs_str = str(s["referees"]) if s["referees"] > 0 else "—"
        auth_str = str(s["authors"]) if s["authors"] > 0 else "—"
        enrich_str = f"{s['enrichment_pct']:.0f}%" if s["total_people"] > 0 else "—"
        span_str = f"{s['avg_span_days']:.0f}d" if s["avg_span_days"] else "—"
        resp_str = f"{s['avg_response_days']:.0f}d" if s["avg_response_days"] else "—"
        date_str = s["extraction_date"] if s["extraction_date"] else "—"

        print(
            f"{s['journal']:<8} {s['platform']:<14} {ms_str:>4} {refs_str:>5} {auth_str:>5} {enrich_str:>7} {span_str:>6} {resp_str:>6} {date_str:>11}"
        )

        tot_ms += s["manuscripts"]
        tot_refs += s["referees"]
        tot_auth += s["authors"]
        tot_enriched += s["enriched"]
        if s["manuscripts"] > 0:
            active_journals += 1

    print("─" * len(header))
    tot_people = tot_refs + tot_auth
    enrich_pct = f"{100 * tot_enriched / tot_people:.0f}%" if tot_people > 0 else "—"
    print(
        f"{'TOTAL':<8} {'':<14} {tot_ms:>4} {tot_refs:>5} {tot_auth:>5} {enrich_pct:>7} {'':>6} {'':>6} {'':>11}"
    )

    print()
    print(f"  📊 {active_journals}/{len(all_stats)} journals active, {tot_ms} manuscripts tracked")
    print(f"  👥 {tot_refs} referees, {tot_auth} authors ({tot_enriched}/{tot_people} enriched)")
    stale = [s for s in all_stats if s and s.get("age_days") and s["age_days"] > 7]
    if stale:
        stale_names = ", ".join(s["journal"] for s in stale)
        print(f"  ⚠️  Stale data (>7 days): {stale_names}")
    print()


def generate_json_report(all_stats: List[Dict]) -> Dict:
    return {
        "report_type": "cross_journal",
        "generated_at": datetime.now().isoformat(),
        "schema_version": "1.0.0",
        "journals": all_stats,
        "totals": {
            "journals_active": sum(1 for s in all_stats if s and s["manuscripts"] > 0),
            "journals_total": len(all_stats),
            "manuscripts": sum(s["manuscripts"] for s in all_stats if s),
            "referees": sum(s["referees"] for s in all_stats if s),
            "authors": sum(s["authors"] for s in all_stats if s),
            "enriched_people": sum(s["enriched"] for s in all_stats if s),
        },
    }


def run_report(save_json: bool = False, output_dir: Optional[Path] = None) -> Dict:
    all_stats = []
    for journal in JOURNALS:
        data = load_journal_data(journal)
        if data:
            stats = compute_journal_stats(journal, data)
            all_stats.append(stats)
        else:
            all_stats.append(
                {
                    "journal": journal.upper(),
                    "journal_name": JOURNAL_NAMES.get(journal, journal),
                    "platform": PLATFORMS.get(journal, ""),
                    "manuscripts": 0,
                    "referees": 0,
                    "authors": 0,
                    "enriched": 0,
                    "total_people": 0,
                    "enrichment_pct": 0,
                    "avg_span_days": None,
                    "avg_response_days": None,
                    "extraction_date": "",
                    "age_days": None,
                    "source_file": "",
                    "schema_version": "",
                }
            )

    print_terminal_report(all_stats)

    report = generate_json_report(all_stats)

    if save_json:
        out_dir = output_dir or OUTPUTS_DIR
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = out_dir / f"cross_journal_report_{timestamp}.json"
        with open(out_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"  💾 JSON report saved: {out_file}")

    return report


if __name__ == "__main__":
    save = "--json" in sys.argv
    run_report(save_json=save)
