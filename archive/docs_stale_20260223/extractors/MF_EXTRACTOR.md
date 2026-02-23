MF Extractor (ScholarOne) – Design, Flow, and Debug Guide
=========================================================

Overview
- Platform: ScholarOne (Manuscript Central)
- Adapter: `src/ecc/adapters/journals/mf.py` (inherits from `ScholarOneAdapter`)
- Production reference: `production/src/extractors/mf_extractor.py`

Highlights
- Categories and list parsing identical in spirit to MOR (ScholarOne family)
- Reviewer emails via popup extraction – known working in production
- Abstract/Proof/Original files popups handled by common popup logic

Flow (new adapter)
1) Authenticate to `https://mc.manuscriptcentral.com/mafi` (MF)
2) Fetch default categories (Awaiting Reviewer Reports / AE Recommendation / Under Review / …)
3) Parse manuscript lists (MF ID pattern: `MAFI-\d{4}-\d{4}`)
4) Extract details per manuscript:
   - Title/Keywords/Abstract
   - Authors: name and email from popup if available
   - Referees: Reviewer List (same parsing strategy as MOR with hidden `XIK_RP_ID*` rows)
   - Metadata and resources (PDF/Original Files)
   - Audit Trail (tab + paginated events)
5) Persist (optional via repository upsert)

Selectors
- ID pattern: `MAFI-\d{4}-\d{4}`
- Reviewer rows: same as MOR; status at `td:nth-child(3)`
- Abstract/PDF/Original Files: `a.msdetailsbuttons:has-text('…')`
- Audit Trail: same as MOR

Debugging
- Tracing/snapshots like MOR with `ECC_DEBUG_TRACING` and `ECC_DEBUG_SNAPSHOTS`
- Use CLI dry‑run to validate authentication and listing before persisting

Audit Summary (MF)
- Reviewer emails extraction: confirmed working in production (`docs/CRITICAL_FINDING.md`)
- New adapter mirrors that behavior via popup extraction and regex
- Audit Trail captured similarly to MOR

Known Differences vs MOR
- Category labels can differ slightly; adapter uses default MF set in `MFAdapter.get_default_categories`
- Minor DOM differences tolerated by the flexible selectors
