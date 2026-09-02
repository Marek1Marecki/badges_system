"""Modele newsów i aktualności odznak.

Zawiera model skrzynki odbiorczej dla radaru aktualności
z zewnętrznych portali oraz enum typów zmian.
"""

from django.db import models


class NewsChangeType(models.TextChoices):
    """Typ zmiany w newsie odznaki."""

    ADDITION = "ADDITION", "Nowa odznaka"
    CHANGE = "CHANGE", "Zmiana regulaminu"


class BadgeNewsItem(models.Model):
    """Skrzynka odbiorcza: Radar aktualności z zewnętrznych portali."""

    change_date_str = models.CharField(max_length=50, verbose_name="Data z portalu")
    change_type = models.CharField(max_length=20, choices=NewsChangeType.choices, verbose_name="Typ zmiany")
    badge_name = models.CharField(max_length=255, verbose_name="Nazwa odznaki")
    source_url = models.URLField(max_length=500, verbose_name="Źródło (Link)")

    is_read = models.BooleanField(default=False, verbose_name="Przeczytane")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Konfiguracja modelu BadgeNewsItem."""

        db_table = "odznaki_badge_news_item"
        verbose_name = "Aktualność Odznaki"
        verbose_name_plural = "Radar Aktualności"
        # Deduplikacja (US-A01)
        unique_together = ("change_date_str", "change_type", "badge_name")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Reprezentacja tekstowa wiadomości odznaki."""
        return f"[{self.get_change_type_display()}] {self.badge_name}"
