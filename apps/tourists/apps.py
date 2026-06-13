from django.apps import AppConfig


class TouristsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.tourists"
    verbose_name = "Turyści i Postępy"

    def ready(self) -> None:
        """Inicjalizacja aplikacji (np. podpięcie sygnałów Django)."""
        import apps.tourists.signals  # noqa: F401
