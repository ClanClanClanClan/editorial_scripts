from src.ecc.infrastructure.tasks.celery_app import celery_app


def test_celery_broker_set():
    assert celery_app.conf.broker_url is not None
