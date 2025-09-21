import asyncio
from types import SimpleNamespace

from src.ecc.infrastructure.cli.commands import ECCCLIApp


class StubAdapter:
    def __init__(self, **kwargs):
        self.manuscripts = []
        self.config = SimpleNamespace(journal_id="TEST")
        self.page = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def authenticate(self):
        return True

    async def fetch_all_manuscripts(self):
        # Return one manuscript shell
        from src.ecc.core.domain.models import Manuscript

        return [
            Manuscript(
                journal_id="TEST",
                external_id="TEST-2025-0001",
                title="T",
            )
        ]

    async def extract_manuscript_details(self, mid):
        from src.ecc.core.domain.models import Manuscript

        m = Manuscript(journal_id="TEST", external_id=mid, title="T")
        m.metadata["audit_trail"] = [
            {"datetime": "01-Jan-2025 10:00", "event": "Invitation sent", "status": "Completed"},
            {"datetime": "02-Jan-2025", "event": "Reminder", "status": "Queued"},
        ]
        return m


def test_cli_normalize_audit(monkeypatch, capsys):
    app = ECCCLIApp()
    # Monkeypatch adapter factory
    from src.ecc.adapters.journals import factory

    monkeypatch.setattr(factory, "get_adapter", lambda *a, **k: StubAdapter())
    # Run internal method to avoid Click plumbing
    asyncio.run(
        app._extract_manuscripts(
            ctx_obj={},
            journal="TEST",
            max_manuscripts=0,
            output_dir=None,
            headless=True,
            dry_run=True,
            persist=False,
            trace=False,
            debug_snapshots=False,
            enrich=False,
            download=False,
            normalize_audit=True,
        )
    )
    out = capsys.readouterr().out
    assert "🧾" in out or "events" in out.lower()
