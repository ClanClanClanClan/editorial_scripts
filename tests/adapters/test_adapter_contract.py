import asyncio
import inspect


def _is_async_callable(obj, name):
    fn = getattr(obj, name, None)
    return inspect.iscoroutinefunction(fn)


def test_mf_mor_adapters_conform_contract():
    from src.ecc.adapters.journals.base import AsyncJournalAdapter
    from src.ecc.adapters.journals.mf import MFAdapter
    from src.ecc.adapters.journals.mor import MORAdapter

    for Adapter in (MFAdapter, MORAdapter):
        adapter = Adapter(headless=True)
        # Inherit from AsyncJournalAdapter
        assert isinstance(adapter, AsyncJournalAdapter)
        # Required async methods
        assert _is_async_callable(adapter, "authenticate")
        assert _is_async_callable(adapter, "fetch_all_manuscripts")
        assert _is_async_callable(adapter, "fetch_manuscripts")
        assert _is_async_callable(adapter, "extract_manuscript_details")
        assert _is_async_callable(adapter, "download_manuscript_files")


def test_fs_adapter_conforms_min_contract():
    # FS is email based and not a Playwright adapter but must provide async workflow methods
    from src.ecc.adapters.journals.fs import FSAdapter

    adapter = FSAdapter()
    assert _is_async_callable(adapter, "authenticate")
    assert _is_async_callable(adapter, "fetch_all_manuscripts")
    assert _is_async_callable(adapter, "extract_manuscript_details")


async def _call_if_exists(obj, name, *args, **kwargs):
    fn = getattr(obj, name, None)
    if inspect.iscoroutinefunction(fn):
        return await fn(*args, **kwargs)
    return None


def test_adapter_context_manager_protocol_smoke():
    # Ensure async context manager protocol exists for MF/MOR and FS
    from src.ecc.adapters.journals.fs import FSAdapter
    from src.ecc.adapters.journals.mf import MFAdapter
    from src.ecc.adapters.journals.mor import MORAdapter

    async def _smoke(Adapter):
        # Do not actually launch Playwright or Gmail; just verify __aenter__/__aexit__ presence
        adapter = Adapter(headless=True) if Adapter is not FSAdapter else Adapter()
        assert hasattr(adapter, "__aenter__") and hasattr(adapter, "__aexit__")
        # We avoid entering context to prevent network/browser usage in unit tests

    asyncio.run(_smoke(MFAdapter))
    asyncio.run(_smoke(MORAdapter))
    asyncio.run(_smoke(FSAdapter))


def test_other_adapters_conform_contract():
    # Ensure new adapters conform to AsyncJournalAdapter contract
    from src.ecc.adapters.journals.base import AsyncJournalAdapter
    from src.ecc.adapters.journals.jota import JOTAAdapter
    from src.ecc.adapters.journals.mafe import MAFEAdapter
    from src.ecc.adapters.journals.naco import NACOAdapter
    from src.ecc.adapters.journals.sicon import SICONAdapter
    from src.ecc.adapters.journals.sifin import SIFINAdapter

    for Adapter in (SICONAdapter, SIFINAdapter, JOTAAdapter, MAFEAdapter, NACOAdapter):
        adapter = Adapter(headless=True)
        assert isinstance(adapter, AsyncJournalAdapter)
        assert _is_async_callable(adapter, "authenticate")
        assert _is_async_callable(adapter, "fetch_all_manuscripts")
        assert _is_async_callable(adapter, "fetch_manuscripts")
        assert _is_async_callable(adapter, "extract_manuscript_details")
        assert _is_async_callable(adapter, "download_manuscript_files")
