"""Konfiguracja aplikacji Django dla systemu odznak."""

from django.apps import AppConfig


class BadgesConfig(AppConfig):
    """Konfiguracja aplikacji odznak."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.badges"
