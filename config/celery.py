import os
import asyncio
import logging

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_shutdown


logger = logging.getLogger(__name__)

_ = os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


app = Celery("config")


celery_settings = app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.beat_schedule = {
    "daily-check-clean-two-week-cancelled-transactions": {
        "task": "core.tasks.periodic.transactions.cleanup_two_week_cancelled_transactions_task",
        "schedule": crontab(hour=2, minute=0),  # Каждый день в 02:00
    },
    "daily-check-deactivate-unused-promo-codes": {
        "task": "core.tasks.periodic.promo_codes.deactivate_unused_promo_codes_task",
        "schedule": crontab(hour=2, minute=30),  # Каждый день в 02:30
    }
}


app.autodiscover_tasks()


# Этот сигнал срабатывает при выключении каждого отдельного процесса-воркера
@worker_process_shutdown.connect
def shutdown_worker(**_: object):
    logger.info("Celery worker shutting down...")
    from general.resource_management import close_resources, Where
    asyncio.run(close_resources(Where("in Celery")))
