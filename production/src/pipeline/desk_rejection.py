#!/usr/bin/env python3
"""Desk-rejection assessment: heuristic signals + optional LLM enhancement."""

import os
import re
from typing import Dict, List, Optional

JOURNAL_SCOPE_KEYWORDS = {
    "SICON": [
        "optimal control",
        "stochastic control",
        "differential games",
        "mean-field",
        "backward SDE",
        "BSDE",
        "Hamilton-Jacobi",
        "Bellman",
        "dynamic programming",
        "controllability",
        "observability",
        "stabilization",
        "feedback control",
        "viscosity solution",
        "stochastic differential equation",
        "Markov decision",
        "linear quadratic",
        "LQR",
        "Riccati",
        "robust control",
        "filtering",
    ],
    "SIFIN": [
        "financial mathematics",
        "option pricing",
        "risk management",
        "portfolio",
        "stochastic volatility",
        "derivative",
        "hedging",
        "Black-Scholes",
        "interest rate",
        "credit risk",
        "market microstructure",
        "algorithmic trading",
        "mean-variance",
        "utility maximization",
        "optimal stopping",
    ],
    "MOR": [
        "operations research",
        "optimization",
        "linear programming",
        "integer programming",
        "convex optimization",
        "stochastic programming",
        "combinatorial optimization",
        "game theory",
        "queueing",
        "Markov chain",
        "applied probability",
        "scheduling",
        "network optimization",
        "robust optimization",
    ],
    "MF": [
        "mathematical finance",
        "derivative pricing",
        "stochastic calculus",
        "risk measure",
        "portfolio optimization",
        "market microstructure",
        "volatility",
        "option",
        "hedging",
        "credit risk",
        "interest rate",
        "stochastic control",
        "mean-field game",
        "equilibrium",
    ],
    "FS": [
        "stochastic analysis",
        "finance",
        "probability",
        "stochastic processes",
        "stochastic differential equation",
        "Brownian motion",
        "martingale",
        "optimal stopping",
        "free boundary",
        "risk",
        "insurance",
    ],
    "JOTA": [
        "optimization",
        "variational inequality",
        "optimal control",
        "nonlinear programming",
        "convex analysis",
        "fixed point",
        "complementarity",
        "equilibrium",
        "saddle point",
        "minimax",
        "calculus of variations",
        "Lagrangian",
        "KKT",
        "duality",
    ],
    "MAFE": [
        "mathematical economics",
        "financial economics",
        "general equilibrium",
        "asset pricing",
        "mechanism design",
        "auction",
        "contract theory",
        "risk",
        "uncertainty",
        "decision theory",
        "game theory",
    ],
    "NACO": [
        "numerical algebra",
        "control",
        "optimization",
        "matrix computation",
        "eigenvalue",
        "iterative method",
        "numerical linear algebra",
        "optimal control",
        "feedback",
        "stabilization",
    ],
}

FREEMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "hotmail.com",
    "outlook.com",
    "aol.com",
    "mail.com",
    "protonmail.com",
    "icloud.com",
    "live.com",
    "msn.com",
    "ymail.com",
    "qq.com",
    "163.com",
    "126.com",
}

JOURNAL_SCOPES_LLM = {
    "SICON": (
        "SIAM Journal on Control and Optimization publishes research on the mathematics "
        "of control theory and its applications: optimal control, stochastic control, "
        "differential games, controllability, observability, stabilization, filtering, "
        "and related areas in optimization and applied probability."
    ),
    "SIFIN": (
        "SIAM Journal on Financial Mathematics publishes research on the mathematical "
        "and computational methods in financial mathematics: derivative pricing, risk "
        "management, portfolio optimization, market microstructure, and algorithmic trading."
    ),
    "MOR": (
        "Mathematics of Operations Research publishes research in all areas of "
        "operations research and management science: optimization, stochastic models, "
        "game theory, queueing, simulation, and applied probability."
    ),
    "MF": (
        "Mathematical Finance publishes original research in all areas of mathematical "
        "finance: derivative pricing, risk management, portfolio theory, market "
        "microstructure, and stochastic analysis applied to finance."
    ),
    "FS": (
        "Finance and Stochastics publishes research at the interface of finance and "
        "stochastic analysis: mathematical models for financial markets, risk measures, "
        "optimal investment, and insurance mathematics."
    ),
    "JOTA": (
        "Journal of Optimization Theory and Applications publishes research in "
        "optimization: continuous and discrete, deterministic and stochastic, with "
        "applications to engineering, economics, and operations research."
    ),
    "MAFE": (
        "Mathematical and Financial Economics publishes research at the intersection "
        "of mathematical economics and financial economics: general equilibrium, asset "
        "pricing, mechanism design, and decision theory."
    ),
    "NACO": (
        "Numerical Algebra, Control and Optimization publishes research in numerical "
        "algebra, control theory, and optimization, with emphasis on computational methods."
    ),
}


def assess_desk_rejection(
    manuscript: dict,
    journal_code: str,
    all_journals_data: Optional[Dict[str, dict]] = None,
    use_llm: bool = False,
    outcome_predictor=None,
    report_quality: dict = None,
) -> dict:
    signals = _heuristic_signals(manuscript, journal_code, all_journals_data)

    high_signals = [s for s in signals if s["severity"] == "high"]
    should_reject = len(high_signals) > 0
    confidence = min(0.9, 0.3 * len(high_signals) + 0.1 * len(signals))
    if not signals:
        confidence = 0.05
    method = "heuristic"

    if outcome_predictor is not None:
        try:
            p_accept = outcome_predictor.predict(manuscript, journal_code)
            signals.append(
                {
                    "signal_name": "model_prediction",
                    "severity": "high"
                    if p_accept < 0.2
                    else ("medium" if p_accept < 0.4 else "low"),
                    "description": f"Trained model: P(accept)={p_accept:.2f}",
                    "confidence": 0.7,
                }
            )
            confidence = round(1.0 - p_accept, 2) if should_reject else round(p_accept, 2)
            method = "heuristic+model"
        except Exception:
            pass

    summary = _build_summary(signals, should_reject)

    if use_llm:
        llm_result = _llm_assessment(manuscript, journal_code, signals, report_quality)
        if llm_result:
            method = "heuristic+llm"
            if llm_result.get("should_desk_reject") is not None:
                should_reject = llm_result["should_desk_reject"]
                confidence = llm_result.get("confidence", confidence)
                summary = llm_result.get("summary", summary)
                signals.append(
                    {
                        "signal_name": "llm_assessment",
                        "severity": "high" if should_reject else "low",
                        "description": llm_result.get("reasoning", ""),
                        "confidence": confidence,
                    }
                )

    return {
        "should_desk_reject": should_reject,
        "confidence": round(confidence, 2),
        "method": method,
        "signals": signals,
        "summary": summary,
    }


def _heuristic_signals(
    manuscript: dict,
    journal_code: str,
    all_journals_data: Optional[Dict[str, dict]],
) -> list:
    signals = []

    abstract = (manuscript.get("abstract") or "").strip()
    if not abstract or len(abstract) < 50:
        signals.append(
            {
                "signal_name": "missing_abstract",
                "severity": "medium",
                "description": f"Abstract is {'missing' if not abstract else 'very short'} ({len(abstract)} chars)",
                "confidence": 0.9,
            }
        )

    keywords = manuscript.get("keywords", [])
    if not keywords:
        signals.append(
            {
                "signal_name": "missing_keywords",
                "severity": "low",
                "description": "No keywords provided",
                "confidence": 0.8,
            }
        )

    scope_kws = JOURNAL_SCOPE_KEYWORDS.get(journal_code.upper(), [])
    if scope_kws and keywords:
        ms_words = set()
        for kw in keywords:
            ms_words.update(kw.lower().split())
        scope_words = set()
        for kw in scope_kws:
            scope_words.update(kw.lower().split())
        intersection = ms_words & scope_words
        union = ms_words | scope_words
        jaccard = len(intersection) / len(union) if union else 0.0
        if jaccard < 0.1 and abstract:
            signals.append(
                {
                    "signal_name": "scope_mismatch",
                    "severity": "high",
                    "description": f"Keyword-scope Jaccard similarity={jaccard:.2f} (threshold 0.1)",
                    "confidence": 0.6,
                }
            )
        elif jaccard >= 0.15:
            signals.append(
                {
                    "signal_name": "scope_match",
                    "severity": "low",
                    "description": f"Good keyword-scope overlap (Jaccard={jaccard:.2f})",
                    "confidence": 0.8,
                }
            )

    scope_desc = JOURNAL_SCOPES_LLM.get(journal_code.upper(), "")
    if scope_desc and abstract:
        try:
            from pipeline.embeddings import get_engine

            engine = get_engine()
            scope_sim = engine.similarity(abstract[:2000], scope_desc)
            if scope_sim < 0.2:
                signals.append(
                    {
                        "signal_name": "scope_embedding_mismatch",
                        "severity": "high",
                        "description": f"Semantic scope similarity very low ({scope_sim:.2f})",
                        "confidence": 0.7,
                    }
                )
            elif scope_sim >= 0.5:
                signals.append(
                    {
                        "signal_name": "scope_embedding_match",
                        "severity": "low",
                        "description": f"Strong semantic scope match ({scope_sim:.2f})",
                        "confidence": 0.8,
                    }
                )
        except Exception:
            pass

    authors = manuscript.get("authors", [])
    if authors:
        has_profile = any(
            a.get("web_profile", {}).get("h_index")
            or a.get("web_profile", {}).get("citation_count")
            for a in authors
        )
        if not has_profile:
            signals.append(
                {
                    "signal_name": "weak_author_profiles",
                    "severity": "low",
                    "description": "No author has a detectable publication record (h-index or citations)",
                    "confidence": 0.4,
                }
            )

        corresponding = None
        for a in authors:
            if (
                a.get("is_corresponding")
                or a.get("platform_specific", {}).get("role") == "corresponding"
            ):
                corresponding = a
                break
        if not corresponding:
            corresponding = authors[0] if authors else None

        if corresponding:
            email = (corresponding.get("email") or "").lower()
            domain = email.split("@")[-1] if "@" in email else ""
            if domain in FREEMAIL_DOMAINS:
                signals.append(
                    {
                        "signal_name": "freemail_corresponding",
                        "severity": "low",
                        "description": f"Corresponding author uses freemail domain: {domain}",
                        "confidence": 0.5,
                    }
                )

    if all_journals_data:
        title = (manuscript.get("title") or "").strip().lower()
        ms_id = manuscript.get("manuscript_id", "")
        if title and len(title) > 20:
            for jcode, jdata in all_journals_data.items():
                if jcode.upper() == journal_code.upper():
                    continue
                for ms in jdata.get("manuscripts", []):
                    other_title = (ms.get("title") or "").strip().lower()
                    if other_title == title and ms.get("manuscript_id") != ms_id:
                        signals.append(
                            {
                                "signal_name": "duplicate_submission",
                                "severity": "high",
                                "description": (
                                    f"Same title found in {jcode.upper()}: "
                                    f"{ms.get('manuscript_id', '?')}"
                                ),
                                "confidence": 0.85,
                            }
                        )

    return signals


def _build_summary(signals: list, should_reject: bool) -> str:
    if not signals:
        return "No significant signals detected. Paper appears suitable for review."

    if should_reject:
        high = [s for s in signals if s["severity"] == "high"]
        reasons = "; ".join(s["description"] for s in high)
        return f"Desk rejection recommended: {reasons}"

    names = [s["signal_name"] for s in signals if s["severity"] != "low"]
    if names:
        return f"Minor concerns ({', '.join(names)}) but paper appears suitable for review."
    return "Paper appears in scope and suitable for review."


def _llm_assessment(
    manuscript: dict,
    journal_code: str,
    heuristic_signals: list,
    report_quality: dict = None,
) -> Optional[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    scope = JOURNAL_SCOPES_LLM.get(journal_code.upper(), "")
    title = manuscript.get("title", "")
    abstract = manuscript.get("abstract", "")
    keywords = manuscript.get("keywords", [])

    authors_summary = []
    for a in manuscript.get("authors", [])[:5]:
        wp = a.get("web_profile", {})
        h = wp.get("h_index") or "unknown"
        topics = wp.get("research_topics", [])[:5]
        authors_summary.append(
            f"- {a.get('name', '?')} ({a.get('institution', '?')}): "
            f"h-index={h}, topics={topics}"
        )

    signals_text = "\n".join(
        f"- [{s['severity']}] {s['signal_name']}: {s['description']}" for s in heuristic_signals
    )

    rq_text = ""
    if report_quality and report_quality.get("n_reports", 0) > 0:
        rq_lines = [
            f"\n\nExisting referee reports ({report_quality['n_reports']} total, "
            f"overall quality={report_quality.get('overall_quality', 'N/A')}):"
        ]
        for rpt in report_quality.get("reports", []):
            rq_lines.append(
                f"  - {rpt.get('reviewer', '?')}: rec={rpt.get('recommendation', '?')}, "
                f"words={rpt.get('word_count', 0)}, thoroughness={rpt.get('thoroughness_score', 'N/A')}, "
                f"timeliness={rpt.get('timeliness_score', 'N/A')}"
            )
        if report_quality.get("consensus"):
            cons = report_quality["consensus"]
            rq_lines.append(
                f"  Consensus: agreement={cons.get('recommendation_agreement', 'N/A')}, "
                f"sentiment={cons.get('sentiment_agreement', 'N/A')}"
            )
        rq_text = "\n".join(rq_lines)

    prompt = f"""You are an associate editor for {journal_code.upper()}.

Journal scope: {scope}

A manuscript has been submitted. Based on the information below, should it be desk-rejected?

Title: {title}
Keywords: {', '.join(keywords)}
Abstract: {abstract[:1500]}

Authors:
{chr(10).join(authors_summary) if authors_summary else '(no author data)'}

Heuristic signals:
{signals_text if signals_text else '(none)'}{rq_text}

Respond in JSON format:
{{"should_desk_reject": true/false, "confidence": 0.0-1.0, "reasoning": "brief explanation", "summary": "one sentence recommendation"}}

Be conservative: only recommend desk rejection for clear scope mismatches or serious quality issues. When in doubt, send to referees."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        import json

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"   LLM assessment error: {e}")

    return None
