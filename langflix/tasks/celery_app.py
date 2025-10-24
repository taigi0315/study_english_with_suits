"""
Celery application configuration for background task processing
"""
from celery import Celery
from langflix import settings

# Create Celery app
celery_app = Celery('langflix')

# Configure Celery
celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Import tasks
from . import tasks  # noqa

if __name__ == '__main__':
    celery_app.start()
