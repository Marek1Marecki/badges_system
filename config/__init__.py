"""Konfiguracja pakietu Django oraz integracji z Celery."""

# To gwarantuje, że Celery zostanie zaimportowane, gdy Django startuje.
from .celery import app as celery_app

__all__ = ("celery_app",)
