"""Category selection helpers and config-driven selectors per journal.

These selectors are heuristic; they can be refined as real HTML samples are collected.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path


def get_category_selector_patterns(journal_id: str, category: str) -> list[str]:
    jid = journal_id.upper()
    # Journal-specific patterns first, then generic fallbacks
    specific = {
        # SIAM journals
        "SICON": [
            f"a:has-text('{category}')",
            f"td:has-text('{category}')",
        ],
        "SIFIN": [
            f"a:has-text('{category}')",
            f"td:has-text('{category}')",
        ],
        # Springer journals
        "JOTA": [
            f"nav a:has-text('{category}')",
            f"a:has-text('{category}')",
            f"td:has-text('{category}')",
            f"text={category}",
        ],
        "MAFE": [
            f"nav a:has-text('{category}')",
            f"a:has-text('{category}')",
            f"td:has-text('{category}')",
            f"text={category}",
        ],
        "NACO": [
            f"nav a:has-text('{category}')",
            f"a:has-text('{category}')",
            f"td:has-text('{category}')",
            f"text={category}",
        ],
        # ScholarOne fallback (kept generic)
        "MF": [f"text={category}", f"a:has-text('{category}')"],
        "MOR": [f"text={category}", f"a:has-text('{category}')"],
        # FS email adapter does not use page category selection
        "FS": [],
    }
    patterns = specific.get(jid, [])
    # Load overrides from env JSON if present: ECC_CATEGORY_SELECTORS='{"JOTA": ["nav a:has-text('{category}')"]}'
    try:
        raw = os.getenv("ECC_CATEGORY_SELECTORS", "").strip()
        if raw:
            data = json.loads(raw)
            extra = data.get(jid)
            if isinstance(extra, list):
                for p in extra:
                    if isinstance(p, str):
                        patterns.append(p.format(category=category))
    except Exception:
        pass
    # Load selectors from config/selectors/<JOURNAL>.json and default.json
    try:
        base = Path.cwd() / "config" / "selectors"
        journal_file = base / f"{jid}.json"
        default_file = base / "default.json"
        for fp in (journal_file, default_file):
            if fp.exists():
                try:
                    data = json.loads(fp.read_text())
                    if isinstance(data, list):
                        for p in data:
                            if isinstance(p, str):
                                patterns.append(p.format(category=category))
                except Exception:
                    continue
    except Exception:
        pass
    # Generic fallbacks
    patterns += [
        f"text={category}",
        f"a:has-text('{category}')",
        f"td:has-text('{category}')",
    ]
    return patterns


async def select_category(page, journal_id: str, category: str) -> bool:
    """Try multiple selector patterns to click a category; return True if clicked."""
    logger = logging.getLogger("category_selectors")
    patterns = get_category_selector_patterns(journal_id, category)
    for sel in patterns:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                await page.wait_for_load_state("networkidle")
                logger.debug(
                    "Category clicked",
                    extra={"journal": journal_id, "category": category, "selector": sel},
                )
                return True
        except Exception:
            continue
    return False
