class AsyncResult:
    def __init__(self, task_id: str, app=None):
        self.id = task_id
        self.info = {}
        self._status = "PENDING"

    @property
    def status(self):
        return self._status
