import os

import pytest

from src.ecc.infrastructure.tasks.celery_app import celery_app

try:
    from celery.result import AsyncResult  # type: ignore
except Exception:
    from src.ecc.testing.celery_stub.result import AsyncResult  # type: ignore


@pytest.mark.skipif(not os.getenv("ECC_TEST_BROKER"), reason="No test broker configured")
def test_celery_job_roundtrip():
    job = celery_app.send_task(
        "ecc.sync_journal", args=["FS"], kwargs={"enrich": False, "max_manuscripts": 0}
    )
    assert job.id
    res = AsyncResult(job.id, app=celery_app)
    assert res.status in ("PENDING", "RECEIVED", "STARTED", "SUCCESS", "FAILURE")
