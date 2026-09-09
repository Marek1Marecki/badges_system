"""Konfiguracja aplikacji Celery dla projektu badges_system."""

import os
from typing import TYPE_CHECKING, Any

from celery import Celery
from celery.signals import task_prerun

if TYPE_CHECKING:
    from celery import Task

# Ustawiamy domyślny moduł ustawień Django dla Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Inicjalizujemy instancję aplikacji Celery (nazwa projektu)
app = Celery("badges_system")

# Mówimy Celery, by czytało konfigurację z pliku settings.py (zmienne z prefiksem CELERY_)
app.config_from_object("django.conf:settings", namespace="CELERY")


@task_prerun.connect
def _propagate_request_id_to_context(sender: "Task", signal: Any = None, **kwargs: Any) -> None:
    """AUDYT-117: Propagowanie request_id z nagłówków Celery do ContextVar.

    `CeleryEventPublisher` przekazuje request_id jako `headers={"request_id": ...}`.
    Celery propguje headers do workera — w `task_prerun` odczytujemy je z
    `sender.request.headers` (Task.request ContextProxy jest już zainicjalizowany).
    Ustawiamy ContextVar, aby `recalculate_poi_scores_task` mógł go odczytać
    bez dostępu do `self.request` (łatwiejsze do zamockowania w testach).
    """
    from infrastructure.request_context import set_request_id

    # sender = Task instance; sender.request.headers dostępne w task_prerun
    # (Celery pushuje request_stack przed wywołaniem hooka).
    request = getattr(sender, "request", None)
    headers = getattr(request, "headers", {}) or {}
    request_id = headers.get("request_id")
    set_request_id(request_id)


# Autodiscover automatycznie znajdzie pliki `tasks.py` w Twoich aplikacjach Django
app.autodiscover_tasks()
