"""Modele narzędzi jakości danych (Radary i Klastry).

Zawiera modele wykrywania bliskich obiektów (proximity candidates)
dla klastrowania i analizy jakości danych.
Importuje ``TouristObject`` z ``apps.badges.models.osm``.
"""

from django.db import models

from apps.badges.models.osm import TouristObject


class ProximityStatus(models.TextChoices):
    """Status kandydata na bliski obiekt."""

    PENDING = "PENDING", "Oczekujące na decyzję"
    RESOLVED = "RESOLVED", "Rozwiązane (Połączone)"
    IGNORED = "IGNORED", "Ignorowane"


class ProximityCandidate(models.Model):
    """Skrzynka odbiorcza: Pary bliskich obiektów wykrytych przez Celery."""

    # Nazywamy je obj_a i obj_b (kolejność nie ma znaczenia,
    # skaner ustawi je alfabetycznie)
    obj_a = models.ForeignKey(TouristObject, on_delete=models.CASCADE, related_name="proximity_a")
    obj_b = models.ForeignKey(TouristObject, on_delete=models.CASCADE, related_name="proximity_b")

    distance_meters = models.FloatField(verbose_name="Odległość [m]")
    status = models.CharField(
        max_length=20,
        choices=ProximityStatus.choices,
        default=ProximityStatus.PENDING,
        verbose_name="Status",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Konfiguracja modelu ProximityCandidate."""

        db_table = "odznaki_proximity_candidate"
        verbose_name = "Kandydat do Klastrowania (Radar)"
        verbose_name_plural = "Radar Klastrowania"
        # Gwarantujemy, że ta sama para nie zostanie dodana dwa razy
        unique_together = ("obj_a", "obj_b")
        ordering = ["-created_at"]

    def __str__(self):
        """Reprezentacja tekstowa kandydata na bliski obiekt."""
        # Pobieramy również typ dla czytelności
        # (np. "Chryszczata [Szczyt] <-> Chryszczata [Wieża]")
        obj_a_type = self.obj_a.get_type_display() if hasattr(self.obj_a, "get_type_display") else self.obj_a.type
        obj_b_type = self.obj_b.get_type_display() if hasattr(self.obj_b, "get_type_display") else self.obj_b.type
        obj_a_display = f"{self.obj_a.name} [{obj_a_type}]"
        obj_b_display = f"{self.obj_b.name} [{obj_b_type}]"

        return f"{obj_a_display} <-> {obj_b_display} ({self.distance_meters:.0f}m)"
