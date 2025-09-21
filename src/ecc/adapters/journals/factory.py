"""Adapter factory for journals.

Creates the proper AsyncJournalAdapter based on journal_id.
"""


def get_adapter(journal_id: str, *, headless: bool = True):
    jid = journal_id.upper()
    if jid == "MF":
        from .mf import MFAdapter

        return MFAdapter(headless=headless)
    if jid == "MOR":
        from .mor import MORAdapter

        return MORAdapter(headless=headless)
    if jid == "FS":
        from .fs import FSAdapter

        return FSAdapter()
    if jid == "SICON":
        from .sicon import SICONAdapter

        return SICONAdapter(headless=headless)
    if jid == "SIFIN":
        from .sifin import SIFINAdapter

        return SIFINAdapter(headless=headless)
    if jid == "JOTA":
        from .jota import JOTAAdapter

        return JOTAAdapter(headless=headless)
    if jid == "MAFE":
        from .mafe import MAFEAdapter

        return MAFEAdapter(headless=headless)
    if jid == "NACO":
        from .naco import NACOAdapter

        return NACOAdapter(headless=headless)
    raise ValueError(f"Unsupported journal_id: {journal_id}")
