"""Modele obiektów turystycznych i integracji z OpenStreetMap.

Zawiera:
- ``TouristObject`` — główny model obiektu (Write Model & OSM Data Lake)
- ``OsmTypeMapping`` — słownik mapujący tagi OSM na typy obiektów
- ``TouristObjectStatus`` — enum statusów cyklu życia obiektu
- ``OsmSyncConflict`` — skrzynka odbiorcza propozycji zmian z OSM
- ``SyncConflictStatus`` — enum statusów konfliktów synchronizacji
"""

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.db.models import Index


class TouristObjectStatus(models.TextChoices):
    """Status cyklu życia obiektu w systemie zasilania."""

    DRAFT = "DRAFT", "Szkic"
    FETCHING_OSM = "FETCHING_OSM", "Pobieranie z OSM..."
    READY = "READY", "Gotowy (Przeliczony)"
    ERROR = "ERROR", "Błąd pobierania"


class TouristObject(gis_models.Model):
    """Złoty Standard dla punktu na mapie (Write Model & OSM Data Lake)."""

    # 1. Curated Fields (Teraz opcjonalne, bo czekają na hydrację z OSM)
    name = gis_models.CharField(
        max_length=200,
        null=True,
        blank=True,  # <--- ZMIANA
        verbose_name="Główna nazwa",
    )
    alt_name = gis_models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Alternatywna nazwa",
    )
    code = gis_models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
        verbose_name="Unikalny kod (Ewidencja)",
    )
    type = gis_models.CharField(
        max_length=100,
        default="Szczyt",
        verbose_name="Typ obiektu",
    )
    altitude = gis_models.IntegerField(
        null=True,
        blank=True,
        help_text="W m n.p.m. (Wymagane dla Szczytów)",
        verbose_name="Wysokość",
    )
    # Geometria też czeka na OSM
    geom = gis_models.PointField(
        srid=4326,
        null=True,
        blank=True,  # <--- ZMIANA
        verbose_name="Współrzędne (GPS)",
    )
    wikipedia_link = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        verbose_name="Link do Wikipedii",
        help_text=(
            "Opcjonalny. Jeśli nie podano, system spróbuje wyciągnąć go asynchronicznie z tagów OSM (np. wikipedia:pl)."
        ),
    )
    local_names = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Lokalne nazwy i graniczne",
    )
    # Miękkie usuwanie (Soft Delete) - np. spalona wieża
    is_active = models.BooleanField(
        default=True,
        verbose_name="Czy istnieje fizycznie?",
        help_text=(
            "Odznacz to (Soft Delete), jeśli wieża spłonęła lub schronisko zostało "
            "rozebrane. Nie usuwaj obiektu z bazy, by nie popsuć historii zdobytych "
            "odznak!"
        ),
    )
    existence_start = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data powstania/otwarcia",
        help_text=("Wypełnij np. dla nowo wybudowanych wież widokowych. Pusty = istniał 'od zawsze' (np. góry)."),
    )
    existence_end = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data zniszczenia/zamknięcia",
        help_text=("Wypełnij dla obiektów rozebranych lub zniszczonych. Pusty = istnieje do dziś."),
    )
    # Relacja rekurencyjna: Nadrzędność obiektów
    # (np. Schronisko przypięte do Szczytu)
    parent_object = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_objects",
        verbose_name="Obiekt nadrzędny",
        help_text="Np. Szczyt, na którym znajduje się to schronisko.",
    )
    # 2. Integracja z OpenStreetMap
    osm_id = gis_models.CharField(
        max_length=50,
        null=True,
        blank=True,
        unique=True,
        help_text="Format: node/123, way/456, relation/789",
        verbose_name="OSM ID",
    )
    # NOWE POLA: Fundament pod przyszły Re-hydrator (Background Sync)
    osm_version = models.IntegerField(
        null=True,
        blank=True,
        help_text="Wersja edycji w OSM",
    )
    osm_timestamp = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Data ostatniej edycji w OSM",
    )
    # Nasz Data Lake - ukryte przed zwykłym widokiem, bez schematu JSONForm
    osm_raw_tags = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Surowe tagi OSM",
        help_text="Wszystkie pobrane tagi z OSM (Data Lake).",
    )
    status = models.CharField(
        max_length=20,
        choices=TouristObjectStatus.choices,
        default=TouristObjectStatus.DRAFT,
        verbose_name="Status",
    )
    osm_error = models.TextField(
        null=True,
        blank=True,
        verbose_name="Błąd asynchronicznego pobierania",
        help_text=("Jeśli Celery napotka krytyczny błąd (np. obiekt nie istnieje), tu pojawi się przyczyna."),
    )
    last_sync_check = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Ostatnia weryfikacja w OSM",
        help_text="Data ostatniego sprawdzenia obiektu przez asynchronicznego stróża.",
    )

    # Metadane
    created_at = gis_models.DateTimeField(auto_now_add=True)
    updated_at = gis_models.DateTimeField(auto_now=True)

    class Meta:
        """Konfiguracja modelu TouristObject."""

        db_table = "odznaki_tourist_object"
        verbose_name = "Obiekt Turystyczny"
        verbose_name_plural = "Obiekty Turystyczne"
        ordering = ["name"]
        indexes = [
            Index(fields=["name"], name="tourist_object_name_idx"),
            Index(fields=["status"], name="tourist_object_status_idx"),
            Index(fields=["is_active"], name="tourist_object_is_active_idx"),
        ]

    def __str__(self) -> str:
        """Reprezentacja tekstowa obiektu turystycznego."""
        alt_str = f" ({self.altitude}m)" if self.altitude else ""
        status_str = "" if self.is_active else " [NIE ISTNIEJE]"
        return str(f"{self.name}{alt_str} [{self.type}]{status_str}")

    def clean(self) -> None:
        """Zabezpieczenie Invariantu C-01: Wymuszenie struktury Płaskiej Gwiazdy."""
        from django.core.exceptions import ValidationError

        super().clean()

        if self.parent_object_id is not None:
            # 1. Zabezpieczenie przed oczywistą pętlą: A -> A
            if self.id == self.parent_object_id:
                raise ValidationError({"parent_object": "Obiekt nie może być własnym rodzicem."})

            # 2. Zabezpieczenie: Rodzic nie może zostać Dzieckiem
            if self.id and self.child_objects.exists():
                raise ValidationError(
                    {
                        "parent_object": (
                            "Ten obiekt jest już Rodzicem dla innych obiektów. "
                            "Zgodnie z regułą Płaskiej Gwiazdy, nie możesz przypisać "
                            "mu obiektu nadrzędnego (nie twórz drzew wielopoziomowych)."
                        )
                    }
                )

            # 3. Zabezpieczenie: Dziecko nie może stać się nowym Rodzicem
            if (
                hasattr(self, "parent_object")
                and self.parent_object
                and self.parent_object.parent_object_id is not None
            ):
                raise ValidationError(
                    {
                        "parent_object": (
                            "Wybrany obiekt nadrzędny sam jest już przypisany do "
                            "innego Rodzica. Wybierz jako Rodzica główny obiekt "
                            "klastra (węzeł centralny)."
                        )
                    }
                )

    def save(self, *args, **kwargs) -> None:
        """Wymuszenie twardej walidacji przy każdym zapisie.

        Również z Akcji Admina i Celery.

        Args:
          *args:
          **kwargs:

        Returns:
        """
        self.clean()  # <--- To rozwiązuje problem omijania walidacji!
        super().save(*args, **kwargs)


class OsmTypeMapping(models.Model):
    """Dynamiczny słownik (Skrzynka odbiorcza) mapujący tagi OSM na nasze typy obiektów."""

    osm_key = models.CharField(max_length=100, verbose_name="Klucz OSM (np. natural)")
    osm_value = models.CharField(max_length=100, verbose_name="Wartość OSM (np. peak)")

    target_type = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Typ docelowy",
        help_text="Wpisz np. 'Szczyt', 'Wodospad'. Zostaw puste, jeśli oczekuje na decyzję.",
    )

    is_ignored = models.BooleanField(
        default=False,
        verbose_name="Ignoruj",
        help_text=("Zaznacz, jeśli ten tag to śmieć (np. tablica informacyjna) i system ma go nigdy nie używać."),
    )

    class Meta:
        """Konfiguracja modelu OsmTypeMapping."""

        db_table = "odznaki_osm_type_mapping"
        verbose_name = "Mapowanie Typu OSM"
        verbose_name_plural = "Słownik Mapowań OSM"
        unique_together = ("osm_key", "osm_value")
        ordering = ["is_ignored", "target_type", "osm_key"]

    def __str__(self) -> str:
        """Reprezentacja tekstowa mapowania OSM."""
        status = " (Ignorowany)" if self.is_ignored else ""
        return str(f"{self.osm_key}={self.osm_value} -> {self.target_type or '?'}{status}")


class SyncConflictStatus(models.TextChoices):
    """Status konfliktu synchronizacji OSM."""

    PENDING = "PENDING", "Oczekujące na decyzję"
    ACCEPTED = "ACCEPTED", "Zaakceptowane (Nadpisane)"
    REJECTED = "REJECTED", "Odrzucone (Zachowano stare)"


class OsmSyncConflict(models.Model):
    """Skrzynka odbiorcza: Propozycje zmian z nocnego skanera OSM."""

    tourist_object = models.ForeignKey(
        TouristObject,
        on_delete=models.CASCADE,
        related_name="sync_conflicts",
        verbose_name="Obiekt",
    )
    field_name = models.CharField(max_length=50, verbose_name="Zmienione pole")
    old_value = models.CharField(max_length=500, null=True, blank=True, verbose_name="Wartość w bazie")
    new_value = models.CharField(max_length=500, null=True, blank=True, verbose_name="Propozycja z OSM")

    status = models.CharField(
        max_length=20,
        choices=SyncConflictStatus.choices,
        default=SyncConflictStatus.PENDING,
        verbose_name="Status",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Konfiguracja modelu OsmSyncConflict."""

        db_table = "odznaki_osm_sync_conflict"
        verbose_name = "Konflikt Danych OSM"
        verbose_name_plural = "Konflikty Danych OSM"
        ordering = ["-created_at"]

    def __str__(self):
        """Reprezentacja tekstowa konfliktu synchronizacji."""
        return f"{self.tourist_object.name}: {self.field_name} ({self.old_value} -> {self.new_value})"
