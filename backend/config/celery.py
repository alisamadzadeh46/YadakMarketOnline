"""Celery application definition.

RabbitMQ is the message broker (reliable task delivery); Redis stores results.
Periodic schedules are managed in the database via django-celery-beat so the
supplier can change SMS reminder timing from the admin without a redeploy.
"""

import os

from celery import Celery

# Point Celery at the same settings module Django uses.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("yadakmart")

# All Celery config lives in Django settings under the CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Discover tasks.py modules inside every installed app.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Trivial task used to confirm the worker is wired up correctly."""
    print(f"Request: {self.request!r}")
