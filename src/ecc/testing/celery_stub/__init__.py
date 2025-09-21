"""Lightweight Celery stub for test environments without celery installed.

Only implements the minimal surface used by our tests.
"""

import uuid


class _Sig:
    def connect(self, func):
        return func


class signals:  # noqa: N801 - mimic celery.signals
    task_received = _Sig()
    task_prerun = _Sig()
    task_postrun = _Sig()
    task_success = _Sig()
    task_failure = _Sig()


class Celery:
    def __init__(self, name: str, broker: str = "", backend: str = ""):
        class _Conf:
            broker_url = broker
            result_expires = 0
            worker_hijack_root_logger = False

        self.conf = _Conf()

    def send_task(self, name: str, args=None, kwargs=None):
        class _Res:
            def __init__(self):
                self.id = str(uuid.uuid4())

        return _Res()


class AsyncResult:
    def __init__(self, task_id: str, app=None):
        self.id = task_id

    @property
    def status(self):
        return "PENDING"
