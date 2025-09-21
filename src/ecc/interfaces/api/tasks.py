"""Task streaming via SSE-like endpoint (basic implementation)."""

import asyncio

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.ecc.infrastructure.tasks.celery_app import celery_app

# Celery AsyncResult may be unavailable in lightweight envs; provide stub fallback
try:
    from celery.result import AsyncResult
except Exception:  # pragma: no cover
    from src.ecc.testing.celery_stub.result import AsyncResult

router = APIRouter()


@router.get("/stream/{task_id}")
async def stream_task(task_id: str) -> StreamingResponse:
    async def event_generator():
        # Basic polling loop
        while True:
            res = AsyncResult(task_id, app=celery_app)
            payload = {
                "task_id": task_id,
                "status": res.status,
                "info": res.info if isinstance(res.info, dict) else {},
            }
            yield f"data: {payload}\n\n"
            if res.status in ("SUCCESS", "FAILURE", "REVOKED"):
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
