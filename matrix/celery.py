import os
from celery import Celery
from celery.signals import task_postrun, task_prerun

from matrix.core.config_version import fermer_contexte, ouvrir_contexte

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix.settings")

app = Celery("matrix")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@task_prerun.connect
def ouvrir_contexte_configuration(**kwargs):
    ouvrir_contexte()


@task_postrun.connect
def fermer_contexte_configuration(**kwargs):
    fermer_contexte()
