"""Celery application configuration for ECC background tasks.

Graceful degradation: when Celery or Prometheus are not installed, this module
falls back to local stubs so API code remains importable.
"""

import os
import time
from typing import Any

from src.ecc.infrastructure.runtime_flags import use_real_deps

try:  # Celery may be unavailable in lightweight test envs
    from celery import Celery, signals
except Exception as _e:  # pragma: no cover
    if use_real_deps():
        raise
    # Fallback to internal stub (does not shadow real celery package)
    from src.ecc.testing.celery_stub import Celery, signals

try:  # Prometheus may be unavailable in test envs
    from prometheus_client import (  # type: ignore[import-not-found]
        Counter,
        Histogram,
        start_http_server,
    )
except Exception:  # pragma: no cover

    class _Metric:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def labels(self, *a: Any, **k: Any) -> "_Metric":
            return self

        def inc(self, *a: Any, **k: Any) -> None:
            return None

        def observe(self, *a: Any, **k: Any) -> None:
            return None

    # Fallback metric types
    Counter = Histogram = _Metric  # type: ignore[assignment]

    def start_http_server(*a: Any, **k: Any) -> None:  # type: ignore[no-redef]
        return None


# Prometheus metrics (declared early so setup can reference them)
tasks_received: Any = Counter("celery_tasks_received_total", "Celery tasks received", ["task"])  # type: ignore[call-arg]
tasks_started: Any = Counter("celery_tasks_started_total", "Celery tasks started", ["task"])  # type: ignore[call-arg]
tasks_succeeded: Any = Counter("celery_tasks_succeeded_total", "Celery tasks succeeded", ["task"])  # type: ignore[call-arg]
tasks_failed: Any = Counter("celery_tasks_failed_total", "Celery tasks failed", ["task"])  # type: ignore[call-arg]
task_duration: Any = Histogram("celery_task_duration_seconds", "Celery task runtime", ["task"])  # type: ignore[call-arg]

_task_starts: dict[str, float] = {}


def _task_name(sender: Any, kwargs: dict[str, Any]) -> str:
    try:
        return getattr(sender, "name", None) or kwargs.get("task", {}).name
    except Exception:
        return "unknown"


def _setup_metrics(app: Celery) -> None:
    @signals.task_received.connect
    def _on_task_received(sender: Any = None, request: Any = None, **kwargs: Any) -> None:
        name = getattr(request, "name", None) or _task_name(sender, kwargs) or "unknown"
        tasks_received.labels(task=name).inc()

    @signals.task_prerun.connect
    def _on_task_prerun(sender: Any = None, task_id: str | None = None, **kwargs: Any) -> None:
        name = _task_name(sender, kwargs) or "unknown"
        tasks_started.labels(task=name).inc()
        if task_id:
            _task_starts[task_id] = time.time()

    @signals.task_postrun.connect
    def _on_task_postrun(sender: Any = None, task_id: str | None = None, **kwargs: Any) -> None:
        name = _task_name(sender, kwargs) or "unknown"
        try:
            start = _task_starts.pop(task_id, None)
            if start:
                task_duration.labels(task=name).observe(time.time() - start)
        except Exception:
            pass

    @signals.task_success.connect
    def _on_task_success(sender: Any = None, result: Any = None, **kwargs: Any) -> None:
        name = _task_name(sender, kwargs) or "unknown"
        tasks_succeeded.labels(task=name).inc()

    @signals.task_failure.connect
    def _on_task_failure(sender: Any = None, **kwargs: Any) -> None:
        name = _task_name(sender, kwargs) or "unknown"
        tasks_failed.labels(task=name).inc()


def _maybe_start_metrics_http() -> None:
    try:
        port = int(os.getenv("ECC_CELERY_METRICS_PORT", "0"))
        if port > 0:
            start_http_server(port)
    except Exception:
        pass


def create_celery_app() -> Celery:
    broker_url = os.getenv("ECC_BROKER_URL", "redis://localhost:6380/0")
    backend_url = os.getenv("ECC_RESULT_BACKEND", broker_url)
    app = Celery("ecc", broker=broker_url, backend=backend_url)
    # basic conf on stub as well
    try:
        app.conf.task_track_started = True  # type: ignore[attr-defined]
        app.conf.result_expires = int(os.getenv("ECC_TASK_RESULT_EXPIRES", "86400"))  # 1 day
        app.conf.worker_hijack_root_logger = False
    except Exception:
        pass
    return app


celery_app = create_celery_app()
_setup_metrics(celery_app)
_maybe_start_metrics_http()
