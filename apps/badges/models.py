"""Modele Django (Active Record) dla infrastruktury odznak."""

from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Index
from django.utils.translation import gettext_lazy as _
from django_jsonform.models.fields import JSONField
from tinymce.models import HTMLField

from infrastructure.schemas.badge_rules_schema import RULES_SCHEMA


class RegionBaseModel(gis_models.Model):
    """Abstrakcyjny model bazowy dla wszystkich regionów geograficznych."""

    name = gis_models.CharField(max_length=100, verbose_name="Nazwa")
    translation = gis_models.CharField(max_length=100, verbose_name="Tłumaczenie")
    code = gis_models.CharField(max_length=10, verbose_name="Kod")
    link = gis_models.CharField(max_length=200, verbose_name="Link (Wiki)")
    shape = gis_models.MultiPolygonField(srid=4326, null=True, blank=True, verbose_name="Kształt")

    created_at = gis_models.DateTimeField(auto_now_add=True)
    updated_at = gis_models.DateTimeField(auto_now=True)

    class Meta:
        """Konfiguracja modelu RegionBaseModel."""

        abstract = True

    def __str__(self) -> str:
        """Reprezentacja tekstowa regionu: nazwa i kod."""
        return f"{self.name} ({self.code})"


class PhysicalRegionMixin(gis_models.Model):
    """Domieszka (Mixin) dodająca relacje sąsiedztwa dla fizycznych obiektów GIS."""

    neighbors = gis_models.ManyToManyField("self", blank=True, verbose_name="Sąsiedzi")

    class Meta:
        """Konfiguracja PhysicalRegionMixin."""

        abstract = True


class CountryModel(RegionBaseModel, PhysicalRegionMixin):
    """Model państwa."""

    order = gis_models.IntegerField(default=0)

    class Meta:
        """Konfiguracja modelu CountryModel."""

        db_table = "odznaki_country"
        verbose_name = "Państwo"
        verbose_name_plural = "Państwa"


class VoivodeshipModel(RegionBaseModel, PhysicalRegionMixin):
    """Model województwa (tylko dla Polski)."""

    country = gis_models.ForeignKey(CountryModel, on_delete=gis_models.CASCADE)

    class Meta:
        """Konfiguracja modelu VoivodeshipModel."""

        db_table = "odznaki_voivodeship"
        unique_together = [("country", "code"), ("country", "name")]
        verbose_name = "Województwo"
        verbose_name_plural = "Województwa"


class ProvinceModel(RegionBaseModel, PhysicalRegionMixin):
    """Model prowincji fizykogeograficznej."""

    country = gis_models.ForeignKey(CountryModel, on_delete=gis_models.CASCADE)

    class Meta:
        """Konfiguracja modelu ProvinceModel."""

        db_table = "odznaki_province"
        unique_together = [("country", "code")]
        verbose_name = "Prowincja"
        verbose_name_plural = "Prowincje"


class SubprovinceModel(RegionBaseModel, PhysicalRegionMixin):
    """Model podprowincji fizykogeograficznej."""

    province = gis_models.ForeignKey(ProvinceModel, on_delete=gis_models.CASCADE)

    class Meta:
        """Konfiguracja modelu SubprovinceModel."""

        db_table = "odznaki_subprovince"
        unique_together = [("province", "code")]
        verbose_name = "Podprowincja"
        verbose_name_plural = "Podprowincje"


class MacroregionModel(RegionBaseModel, PhysicalRegionMixin):
    """Model makroregionu."""

    subprovince = gis_models.ForeignKey(SubprovinceModel, on_delete=gis_models.CASCADE, null=True, blank=True)

    class Meta:
        """Konfiguracja modelu MacroregionModel."""

        db_table = "odznaki_macroregion"
        verbose_name = "Makroregion"
        verbose_name_plural = "Makroregiony"


class MesoregionModel(RegionBaseModel, PhysicalRegionMixin):
    """Model mezoregionu."""

    macroregion = gis_models.ForeignKey(MacroregionModel, on_delete=gis_models.CASCADE, null=True, blank=True)

    class Meta:
        """Konfiguracja modelu MesoregionModel."""

        db_table = "odznaki_mesoregion"
        verbose_name = "Mezoregion"
        verbose_name_plural = "Mezoregiony"


class TouristRegionModel(RegionBaseModel):
    """Region turystyczny budowany agregacyjnie z mniejszych jednostek (Write Model)."""

    provinces = models.ManyToManyField(ProvinceModel, blank=True, verbose_name="Prowincje")
    subprovinces = models.ManyToManyField(SubprovinceModel, blank=True, verbose_name="Podprowincje")
    macroregions = models.ManyToManyField(MacroregionModel, blank=True, verbose_name="Makroregiony")
    mesoregions = models.ManyToManyField(MesoregionModel, blank=True, verbose_name="Mezoregiony")

    class Meta:
        """Konfiguracja modelu TouristRegionModel."""

        db_table = "odznaki_tourist_region"
        verbose_name = "Region Turystyczny"
        verbose_name_plural = "Regiony Turystyczne"


# ==========================================================
# ORGANIZATORZY (Nowy byt biznesowy)
# ==========================================================


class OrganizerModel(models.Model):
    """Reprezentuje organizatora odznaki (np.

    Oddział PTTK, Klub).
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Nazwa organizatora",
    )
    contact_info = models.TextField(
        blank=True,
        verbose_name="Dane kontaktowe",
    )
    club_rules_link = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="Regulamin klubu (Link)",
    )
    # Pliki wizualne (Opcjonalne)
    club_badge_image = models.ImageField(
        upload_to="organizers/badges/",
        blank=True,
        null=True,
        verbose_name="Odznaka klubowa",
    )
    is_booklet_required = models.BooleanField(
        default=False,
        verbose_name="Wymagana książeczka klubowa",
        help_text=(
            "Zaznacz, jeśli organizator bezwzględnie wymaga posiadania swojej książeczki do zdobywania jego odznak."
        ),
    )
    booklet_template_pdf = models.FileField(
        upload_to="organizers/booklets/",
        blank=True,
        null=True,
        verbose_name="Wzór książeczki (PDF)",
    )
    has_publication_consent = models.BooleanField(
        default=False,
        verbose_name="Zgoda na publikację",
        help_text=(
            "Zaznacz, jeśli masz zgodę organizatora na publikację wizerunku odznak, książeczek i treści regulaminów."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Konfiguracja modelu OrganizerModel."""

        db_table = "odznaki_organizer"
        verbose_name = "Organizator"
        verbose_name_plural = "Organizatorzy"
        ordering = ["name"]

    def __str__(self) -> str:
        """Reprezentacja tekstowa organizatora."""
        return str(self.name)


# ==========================================================
# SŁOWNIKI I MAPOWANIA OSM
# ==========================================================


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
        help_text="Zaznacz, jeśli ten tag to śmieć (np. tablica informacyjna) i system ma go nigdy nie używać.",
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


# ==========================================================
# 1. OBIEKT TURYSTYCZNY (SZCZYT, SCHRONISKO, ZAMEK)
# ==========================================================


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
            "Odznacz to (Soft Delete), jeśli wieża spłonęła lub schronisko zostało rozebrane. "
            "Nie usuwaj obiektu z bazy, by nie popsuć historii zdobytych odznak!"
        ),
    )
    existence_start = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data powstania/otwarcia",
        help_text="Wypełnij np. dla nowo wybudowanych wież widokowych. Puste = istniał 'od zawsze' (np. góry).",
    )
    existence_end = models.DateField(
        null=True,
        blank=True,
        verbose_name="Data zniszczenia/zamknięcia",
        help_text="Wypełnij dla obiektów rozebranych lub zniszczonych. Puste = istnieje do dziś.",
    )
    # Relacja rekurencyjna: Nadrzędność obiektów (np. Schronisko przypięte do Szczytu)
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
    # Nasz Data Lake - ukryte przed zwykłym widokiem, bez schematu JSONForm (wolna amerykanka)
    osm_raw_tags = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Surowe tagi OSM",
        help_text="Wszystkie pobrane tagi z OSM (Data Lake).",
    )
    status = models.CharField(
        max_length=20, choices=TouristObjectStatus.choices, default=TouristObjectStatus.DRAFT, verbose_name="Status"
    )
    osm_error = models.TextField(
        null=True,
        blank=True,
        verbose_name="Błąd asynchronicznego pobierania",
        help_text="Jeśli Celery napotka krytyczny błąd (np. obiekt nie istnieje), tu pojawi się przyczyna.",
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
                            "Zgodnie z regułą Płaskiej Gwiazdy, nie możesz przypisać mu "
                            "obiektu nadrzędnego (nie twórz drzew wielopoziomowych)."
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
                            "Wybrany obiekt nadrzędny sam jest już przypisany do innego Rodzica. "
                            "Wybierz jako Rodzica główny obiekt klastra (węzeł centralny)."
                        )
                    }
                )

    def save(self, *args, **kwargs) -> None:
        """Wymuszenie twardej walidacji przy każdym zapisie (również z Akcji Admina i Celery).

        Args:
          *args:
          **kwargs:

        Returns:
        """
        self.clean()  # <--- To rozwiązuje problem omijania walidacji!
        super().save(*args, **kwargs)


# ==========================================================
# 2. UNIFIED READ MODEL (ZDENORMALIZOWANE RELACJE PRZESTRZENNE)
# ==========================================================


class RegionLevelType(models.TextChoices):
    """Poziomy słownika geograficznego do filtrowania w CQRS."""

    COUNTRY = "COUNTRY", _("Państwo")
    VOIVODESHIP = "VOIVODESHIP", _("Województwo")
    PROVINCE = "PROVINCE", _("Prowincja")
    SUBPROVINCE = "SUBPROVINCE", _("Podprowincja")
    MACROREGION = "MACROREGION", _("Makroregion")
    MESOREGION = "MESOREGION", _("Mezoregion")
    TOURIST_REGION = "TOURIST_REGION", _("Region Turystyczny")


class ObjectRegionCache(models.Model):
    """Płaska tabela odczytu (CQRS Read Model) wypełniana asynchronicznie przez Celery.

    Łączy punkt (TouristObject) z dowolnym z 6 typów regionów na podstawie ST_DWithin.
    Zamiast 6 tabel M2M, mamy jedną, błyskawiczną w odpytywaniu.

    Args:

    Returns:
    """

    tourist_object = models.ForeignKey(TouristObject, on_delete=models.CASCADE, related_name="cached_regions")

    # Przechowujemy typ poziomu (np. COUNTRY) i fizyczne ID wiersza z odpowiedniej tabeli
    # (np. ID Polski z CountryModel)
    region_level = models.CharField(max_length=20, choices=RegionLevelType.choices)
    region_id = models.BigIntegerField(help_text="ID wiersza z tabeli odpowiadającej poziomowi region_level.")
    region_name = models.CharField(
        max_length=100, help_text="Zdenormalizowana nazwa regionu do błyskawicznego wyświetlania (np. w panelu)."
    )

    # 0.0 oznacza, że obiekt leży ściśle wewnątrz poligonu (ST_Intersects)
    # Wartość > 0.0 oznacza bufor przygraniczny (ST_DWithin)
    distance_meters = models.FloatField(
        default=0.0, help_text="Odległość od krawędzi regionu w metrach (0.0 = wewnątrz)."
    )

    class Meta:
        """Konfiguracja modelu ObjectRegionCache."""

        db_table = "odznaki_object_region_cache"
        # Uniemożliwiamy zduplikowanie przypisania tego samego regionu do obiektu
        unique_together = ("tourist_object", "region_level", "region_id")
        # Indeksy potężnie przyspieszające odczyt CQRS dla paneli analitycznych
        indexes = [
            models.Index(fields=["tourist_object", "region_level"]),
            models.Index(fields=["region_level", "region_id"]),
        ]

    def __str__(self) -> str:
        """Reprezentacja tekstowa cache regionu."""
        dist_str = f" (Bufor {self.distance_meters}m)" if self.distance_meters > 0 else ""
        return f"{self.tourist_object.name} -> {self.region_name} [{self.get_region_level_display()}]{dist_str}"


# ==========================================================
# HIERARCHIA ODZNAK (Badge -> Tier -> Version)
# ==========================================================


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
        help_text="Zaznacz, jeśli ta konkretna odznaka wymaga posiadania dedykowanej książeczki do odznaki.",
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


# ==========================================================
# NARZĘDZIA JAKOŚCI DANYCH (Radary i Klastry)
# ==========================================================


class ProximityStatus(models.TextChoices):
    """Status kandydata na bliski obiekt."""

    PENDING = "PENDING", "Oczekujące na decyzję"
    RESOLVED = "RESOLVED", "Rozwiązane (Połączone)"
    IGNORED = "IGNORED", "Ignorowane"


class ProximityCandidate(models.Model):
    """Skrzynka odbiorcza: Pary bliskich obiektów wykrytych przez Celery."""

    # Nazywamy je obj_a i obj_b (kolejność nie ma znaczenia, skaner ustawi je alfabetycznie)
    obj_a = models.ForeignKey(TouristObject, on_delete=models.CASCADE, related_name="proximity_a")
    obj_b = models.ForeignKey(TouristObject, on_delete=models.CASCADE, related_name="proximity_b")

    distance_meters = models.FloatField(verbose_name="Odległość [m]")
    status = models.CharField(
        max_length=20, choices=ProximityStatus.choices, default=ProximityStatus.PENDING, verbose_name="Status"
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
        # Pobieramy również typ dla czytelności (np. "Chryszczata [Szczyt] <-> Chryszczata [Wieża]")
        obj_a_type = self.obj_a.get_type_display() if hasattr(self.obj_a, "get_type_display") else self.obj_a.type
        obj_b_type = self.obj_b.get_type_display() if hasattr(self.obj_b, "get_type_display") else self.obj_b.type
        obj_a_display = f"{self.obj_a.name} [{obj_a_type}]"
        obj_b_display = f"{self.obj_b.name} [{obj_b_type}]"

        return f"{obj_a_display} <-> {obj_b_display} ({self.distance_meters:.0f}m)"


class SyncConflictStatus(models.TextChoices):
    """Status konfliktu synchronizacji OSM."""

    PENDING = "PENDING", "Oczekujące na decyzję"
    ACCEPTED = "ACCEPTED", "Zaakceptowane (Nadpisane)"
    REJECTED = "REJECTED", "Odrzucone (Zachowano stare)"


class OsmSyncConflict(models.Model):
    """Skrzynka odbiorcza: Propozycje zmian z nocnego skanera OSM."""

    tourist_object = models.ForeignKey(
        TouristObject, on_delete=models.CASCADE, related_name="sync_conflicts", verbose_name="Obiekt"
    )
    field_name = models.CharField(max_length=50, verbose_name="Zmienione pole")
    old_value = models.CharField(max_length=500, null=True, blank=True, verbose_name="Wartość w bazie")
    new_value = models.CharField(max_length=500, null=True, blank=True, verbose_name="Propozycja z OSM")

    status = models.CharField(
        max_length=20, choices=SyncConflictStatus.choices, default=SyncConflictStatus.PENDING, verbose_name="Status"
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
