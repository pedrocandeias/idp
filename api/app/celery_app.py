from __future__ import annotations

import os
from celery import Celery


broker_url = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://redis:6379/0"))
backend_url = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/0"))

celery_app = Celery("idp", broker=broker_url, backend=backend_url, include=["app.tasks"])
celery_app.conf.update(task_track_started=True, task_serializer="json", result_serializer="json", accept_content=["json"]) 

