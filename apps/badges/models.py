"""Modele Django (Active Record) dla infrastruktury odznak."""

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_jsonform.models.fields import JSONField
from tinymce.models import HTMLField


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
        abstract = True
        managed = False

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class CountryModel(RegionBaseModel):
    """Model państwa."""

    order = gis_models.IntegerField(default=0)

    class Meta:
        db_table = "odznaki_country"
        managed = False
        verbose_name = "Państwo"
        verbose_name_plural = "Państwa"


class VoivodeshipModel(RegionBaseModel):
    """Model województwa (tylko dla Polski)."""

    country = gis_models.ForeignKey(CountryModel, on_delete=gis_models.CASCADE)

    class Meta:
        db_table = "odznaki_voivodeship"
        managed = False
        unique_together = [("country", "code"), ("country", "name")]
        verbose_name = "Województwo"
        verbose_name_plural = "Województwa"


class ProvinceModel(RegionBaseModel):
    """Model prowincji fizykogeograficznej."""

    country = gis_models.ForeignKey(CountryModel, on_delete=gis_models.CASCADE)

    class Meta:
        db_table = "odznaki_province"
        managed = False
        unique_together = [("country", "code")]
        verbose_name = "Prowincja"
        verbose_name_plural = "Prowincje"


class SubprovinceModel(RegionBaseModel):
    """Model podprowincji fizykogeograficznej."""

    province = gis_models.ForeignKey(ProvinceModel, on_delete=gis_models.CASCADE)

    class Meta:
        db_table = "odznaki_subprovince"
        managed = False
        unique_together = [("province", "code")]
        verbose_name = "Podprowincja"
        verbose_name_plural = "Podprowincje"


class MacroregionModel(RegionBaseModel):
    """Model makroregionu."""

    subprovince = gis_models.ForeignKey(SubprovinceModel, on_delete=gis_models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = "odznaki_macroregion"
        managed = False
        verbose_name = "Makroregion"
        verbose_name_plural = "Makroregiony"


class MesoregionModel(RegionBaseModel):
    """Model mezoregionu."""

    macroregion = gis_models.ForeignKey(MacroregionModel, on_delete=gis_models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = "odznaki_mesoregion"
        managed = False
        verbose_name = "Mezoregion"
        verbose_name_plural = "Mezoregiony"


class TouristRegionModel(RegionBaseModel):
    """Region turystyczny budowany agregacyjnie z mniejszych jednostek (Write Model)."""

    provinces = models.ManyToManyField(ProvinceModel, blank=True, verbose_name="Prowincje")
    subprovinces = models.ManyToManyField(SubprovinceModel, blank=True, verbose_name="Podprowincje")
    macroregions = models.ManyToManyField(MacroregionModel, blank=True, verbose_name="Makroregiony")
    mesoregions = models.ManyToManyField(MesoregionModel, blank=True, verbose_name="Mezoregiony")

    class Meta:
        db_table = "odznaki_tourist_region"
        verbose_name = "Region Turystyczny"
        verbose_name_plural = "Regiony Turystyczne"


# ==========================================================
# ORGANIZATORZY (Nowy byt biznesowy)
# ==========================================================


class OrganizerModel(models.Model):
    """Reprezentuje organizatora odznaki (np. Oddział PTTK, Klub)."""

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
            "Zaznacz, jeśli masz zgodę organizatora na publikację wizerunku odznak, książeczek i treści regulaminów.",
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "odznaki_organizer"
        verbose_name = "Organizator"
        verbose_name_plural = "Organizatorzy"
        ordering = ["name"]

    def __str__(self) -> str:
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
        db_table = "odznaki_osm_type_mapping"
        verbose_name = "Mapowanie Typu OSM"
        verbose_name_plural = "Słownik Mapowań OSM"
        unique_together = ("osm_key", "osm_value")
        ordering = ["is_ignored", "target_type", "osm_key"]

    def __str__(self) -> str:
        status = " (Ignorowany)" if self.is_ignored else ""
        return str(f"{self.osm_key}={self.osm_value} -> {self.target_type or '?'}{status}")


# ==========================================================
# 1. OBIEKT TURYSTYCZNY (SZCZYT, SCHRONISKO, ZAMEK)
# ==========================================================


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

    # Metadane
    created_at = gis_models.DateTimeField(auto_now_add=True)
    updated_at = gis_models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "odznaki_tourist_object"
        verbose_name = "Obiekt Turystyczny"
        verbose_name_plural = "Obiekty Turystyczne"
        ordering = ["name"]

    def __str__(self) -> str:
        alt_str = f" ({self.altitude}m)" if self.altitude else ""
        status_str = "" if self.is_active else " [NIE ISTNIEJE]"
        return str(f"{self.name}{alt_str} [{self.type}]{status_str}")


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
    """
    Płaska tabela odczytu (CQRS Read Model) wypełniana asynchronicznie przez Celery.
    Łączy punkt (TouristObject) z dowolnym z 6 typów regionów na podstawie ST_DWithin.
    Zamiast 6 tabel M2M, mamy jedną, błyskawiczną w odpytywaniu.
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
        db_table = "odznaki_object_region_cache"
        # Uniemożliwiamy zduplikowanie przypisania tego samego regionu do obiektu
        unique_together = ("tourist_object", "region_level", "region_id")
        # Indeksy potężnie przyspieszające odczyt CQRS dla paneli analitycznych
        indexes = [
            models.Index(fields=["tourist_object", "region_level"]),
            models.Index(fields=["region_level", "region_id"]),
        ]

    def __str__(self) -> str:
        dist_str = f" (Bufor {self.distance_meters}m)" if self.distance_meters > 0 else ""
        return f"{self.tourist_object.name} -> {self.region_name} [{self.get_region_level_display()}]{dist_str}"


# ==========================================================
# HIERARCHIA ODZNAK (Badge -> Tier -> Version)
# ==========================================================

# Definicja schematu JSON Schema dla panelu Django Admin
RULES_SCHEMA = {
    "type": "list",
    "title": "Reguły Biznesowe",
    "items": {
        "type": "dict",
        "keys": {
            "type": {
                "type": "string",
                "title": "Typ Reguły",
                "choices": [
                    {"value": "ActivityRule", "title": "Ograniczenie Aktywności"},
                    {"value": "TimeLimitRule", "title": "Limit Czasowy w latach"},
                    {"value": "RequiresClubJoinDateRule", "title": "Wymaga zapisu do Klubu (tylko nowe wejścia)"},
                    {"value": "MinAgeRule", "title": "Minimalny Wiek (w latach)"},
                    {"value": "StartDateRule", "title": "Szczyty zaliczane od konkretnej daty"},
                    {"value": "MandatoryObjectsRule", "title": "Obowiązkowe konkretne obiekty"},
                    {"value": "GroupedAlternativesRule", "title": "Wymagane obiekty w różnych grupach/pasmach"},
                ],
            },
            "allowed_activities": {
                "type": "array",
                "title": "Dozwolone aktywności (tylko dla ActivityRule)",
                "items": {"type": "string", "choices": ["HIKING", "CYCLING", "SKIING"]},
                "required": False,
            },
            "limit_in_years": {
                "type": "integer",
                "title": "Limit w latach (tylko dla TimeLimitRule)",
                "required": False,
            },
            "min_age": {
                "type": "integer",
                "title": "Minimalny Wiek (tylko dla MinAgeRule)",
                "required": False,
            },
            "start_date": {
                "type": "string",
                "format": "date",  # To wymusi pojawienie się widgetu kalendarza!
                "title": "Zalicza wejścia od daty (tylko dla StartDateRule)",
                "required": False,
            },
            "mandatory_peak_ids": {
                "type": "array",
                "title": "ID obowiązkowych obiektów (Wpisz liczby, np. ID Babiej Góry)",
                "items": {"type": "integer"},
                "required": False,
            },
            "min_groups_required": {
                "type": "integer",
                "title": "Ile RÓŻNYCH grup/pasm turysta musi zaliczyć? (tylko dla GroupedAlternativesRule)",
                "required": False,
            },
            "groups": {
                "type": "array",
                "title": "Grupy / Pasma / Wiaderka",
                "items": {
                    "type": "dict",
                    "title": "Pojedyncza Grupa",
                    "keys": {
                        "group_name": {
                            "type": "string",
                            "title": "Nazwa grupy dla Twojej wygody (np. 'Tatry')",
                            "required": False,
                        },
                        "peak_ids": {
                            "type": "array",
                            "title": "ID obiektów należących do tej grupy",
                            "items": {"type": "integer"},
                        },
                    },
                },
                "required": False,
            },
        },
    },
}


class PeakModel(models.Model):
    """Model szczytu."""

    name = models.CharField(max_length=100, verbose_name="Nazwa szczytu")
    altitude = models.IntegerField(verbose_name="Wysokość (m n.p.m.)")
    mesoregion = models.ForeignKey(
        "MesoregionModel",
        on_delete=models.CASCADE,
        related_name="peaks",
        verbose_name="Mezoregion",
    )
    link = models.URLField(max_length=255, blank=True, null=True, verbose_name="Link do opisu")
    shape = models.CharField(max_length=255, blank=True, null=True, verbose_name="Kształt szczytu")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Utworzono")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Zaktualizowano")

    class Meta:
        """Meta klasy PeakModel."""

        db_table = "odznaki_peak"
        verbose_name = "Szczyt"
        verbose_name_plural = "Szczyty"

    def __str__(self) -> str:
        """Zwraca reprezentację tekstową szczytu."""
        return f"{self.name} ({self.altitude} m n.p.m.)"


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

    class Meta:
        db_table = "odznaki_badge"
        verbose_name = "Odznaka"
        verbose_name_plural = "Odznaki"

    def __str__(self) -> str:
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
        verbose_name="Reguły biznesowe",
    )
    # Nowe: Prosta, klasyczna relacja M2M wspierana przez 'filter_horizontal'
    pool_peaks = models.ManyToManyField(
        TouristObject,
        verbose_name="Pula Obiektów",
        blank=True,
    )

    class Meta:
        db_table = "odznaki_badge_version"
        verbose_name = "Wersja Regulaminu"
        verbose_name_plural = "Wersje Regulaminów"

    def __str__(self) -> str:
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
    """Stopień odznaki (Obserwator postępu). To tutaj weryfikujemy wymaganą ilość szczytów z puli."""

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
        db_table = "odznaki_badge_tier"
        unique_together = ("version", "name")
        ordering = ["version", "order"]
        verbose_name = "Stopień Odznaki"
        verbose_name_plural = "Stopnie Odznak"

    def __str__(self) -> str:
        return f"{self.version} - {self.get_name_display()}"
