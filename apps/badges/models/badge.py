"""Modele hierarchii odznak (Badge -> Version -> Tier).

Zawiera modele odznak, ich wersji regulaminów oraz stopni (tierów).
Importuje ``OrganizerModel`` z ``apps.badges.models.organizer`` oraz
``TouristObject`` z ``apps.badges.models.osm`` dla kluczy obcych.
"""

from django.db import models
from django_jsonform.models.fields import JSONField
from tinymce.models import HTMLField

from apps.badges.models.organizer import OrganizerModel
from apps.badges.models.osm import TouristObject
from apps.badges.rules_schema import RULES_SCHEMA


class BadgeModel(models.Model):
    """Główna tożsamość odznaki (Trwa wiecznie)."""

    code = models.CharField(max_length=50, unique=True, verbose_name="Kod")
    name = models.CharField(max_length=255, verbose_name="Nazwa Odznaki")

    # Nowe relacje i metadane
    organizer = models.ForeignKey(
        OrganizerModel,
        on_delete=models.CASCADE,
        related_name="badges",
        verbose_name="Organizator",
    )
    established_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data ustanowienia",
    )
    is_booklet_required = models.BooleanField(
        default=False,
        verbose_name="Wymagana książeczka odznaki",
        help_text=("Zaznacz, jeśli ta konkretna odznaka wymaga posiadania dedykowanej książeczki do odznaki."),
    )

    class Meta:
        """Konfiguracja modelu BadgeModel."""

        db_table = "odznaki_badge"
        verbose_name = "Odznaka"
        verbose_name_plural = "Odznaki"

    def __str__(self) -> str:
        """Reprezentacja tekstowa odznaki."""
        return str(self.name)


class BadgeVersionModel(models.Model):
    """Konkretny regulamin i lista szczytów w czasie i reguły JSON."""

    badge = models.ForeignKey(
        BadgeModel,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name="Odznaka",
    )
    version_code = models.CharField(
        max_length=50,
        verbose_name="Wersja (np. v2024)",
    )
    valid_from = models.DateField(verbose_name="Obowiązuje od")
    # Zarządzanie linkami (Wzorzec Archiwum)
    official_link = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Oficjalny link (Źródło organizatora)",
    )
    rules_link = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Link do archiwum regulaminu",
    )
    system_entry_date = models.DateField(
        auto_now_add=True,
        verbose_name="Data wprowadzenia archiwum do systemu",
    )
    booklet_template_image = models.ImageField(
        upload_to="badges/versions/booklets/",
        blank=True,
        null=True,
        verbose_name="Wzór książeczki",
    )
    rules_text = HTMLField(
        blank=True,
        null=True,
        verbose_name="Treść regulaminu",
        help_text="Wklej tutaj oryginalną treść regulaminu PTTK dla zachowania historii.",
    )
    # Elastyczne reguły w postaci weryfikowanego JSON-a
    rules = JSONField(
        schema=RULES_SCHEMA,
        default=list,
        blank=True,
        null=True,
        verbose_name="Reguły biznesowe",
    )
    # Nowe: Prosta, klasyczna relacja M2M wspierana przez 'filter_horizontal'
    pool_peaks = models.ManyToManyField(
        TouristObject,
        verbose_name="Pula Obiektów",
        blank=True,
    )

    class Meta:
        """Konfiguracja modelu BadgeVersionModel."""

        db_table = "odznaki_badge_version"
        verbose_name = "Wersja Regulaminu"
        verbose_name_plural = "Wersje Regulaminów"

    def __str__(self) -> str:
        """Reprezentacja tekstowa wersji odznaki."""
        return f"{self.badge.name} ({self.version_code})"


class LevelType(models.TextChoices):
    """Słownik stopni odznak turystycznych."""

    JEDNOSTOPNIOWA = "jednostopniowa", "Jednostopniowa"
    POPULARNA = "popularna", "Popularna"
    BRAZOWA = "brazowa", "Brązowa"
    SREBRNA = "srebrna", "Srebrna"
    ZLOTA = "zlota", "Złota"
    PLATYNOWA = "platynowa", "Platynowa"
    DIAMENTOWA = "diamentowa", "Diamentowa"
    BRYLANTOWA = "brylantowa", "Brylantowa"
    MALA = "mala", "Mała"
    DUZA = "duza", "Duża"
    WIELKA = "wielka", "Wielka"
    PODSTAWOWA = "podstawowa", "Podstawowa"
    GLOWNA = "glowna", "Główna"
    MALA_POPULARNA = "mala_popularna", "Mała popularna"
    MALA_BRAZOWA = "mala_brazowa", "Mała brązowa"
    ZA_WYTRWALOSC = "za_wytrwalosc", "Za Wytrwałość"


class BadgeTierModel(models.Model):
    """Stopień odznaki (Obserwator postępu.

    To tutaj weryfikujemy wymaganą ilość szczytów z puli.
    """

    version = models.ForeignKey(
        BadgeVersionModel,
        on_delete=models.CASCADE,
        related_name="tiers",
        verbose_name="Wersja odznaki",
    )
    name = models.CharField(
        max_length=50,
        choices=LevelType.choices,
        null=True,
        blank=False,
        verbose_name="Stopień",
    )
    order = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Kolejność zdobywania (1=najniższy)",
        help_text="Kolejność zdobywania (1=najniższy)",
    )
    # Fizyczna blacha reprezentująca ten stopień
    badge_image = models.ImageField(
        upload_to="badges/tiers/",
        blank=True,
        null=True,
        verbose_name="Zdjęcie blachy (Odznaki)",
    )
    required_peaks_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Puste = wymaga zdobycia WSZYSTKIECH szczytów z puli tej wersji.",
    )

    class Meta:
        """Konfiguracja modelu BadgeTierModel."""

        db_table = "odznaki_badge_tier"
        unique_together = ("version", "name")
        ordering = ["version", "order"]
        verbose_name = "Stopień Odznaki"
        verbose_name_plural = "Stopnie Odznak"
        constraints = [
            models.UniqueConstraint(fields=["version", "name"], name="unique_tier_name_per_version"),
            models.UniqueConstraint(fields=["version", "order"], name="unique_tier_order_per_version"),
        ]

    def __str__(self) -> str:
        """Reprezentacja tekstowa stopnia odznaki."""
        return f"{self.version} - {self.get_name_display()}"
