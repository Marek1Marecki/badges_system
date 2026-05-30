"""Konfiguracja aplikacji Celery dla projektu badges_system."""

import os

from celery import Celery

# Ustawiamy domyślny moduł ustawień Django dla Celery
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Inicjalizujemy instancję aplikacji Celery (nazwa projektu)
app = Celery("badges_system")

# Mówimy Celery, by czytało konfigurację z pliku settings.py (zmienne z prefiksem CELERY_)
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover automatycznie znajdzie pliki `tasks.py` w Twoich aplikacjach Django
app.autodiscover_tasks()
