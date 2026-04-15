"""Zadania asynchroniczne (Celery) dla aplikacji odznak.

Zawiera m.in. logikę przeliczania relacji przestrzennych obiektów turystycznych,
odciążając główny wątek aplikacji webowej.
"""

from celery import shared_task
from django.contrib.gis.geos import GeometryCollection, MultiPolygon, Polygon
from django.db import transaction
from django.db.models import Q

from apps.badges.models import (
    CountryModel,
    MacroregionModel,
    MesoregionModel,
    ObjectRegionCache,
    ProvinceModel,
    RegionLevelType,
    SubprovinceModel,
    TouristObject,
    TouristRegionModel,
    VoivodeshipModel,
)


@shared_task
def calculate_object_regions_task(object_id: int) -> str:
    """Asynchronicznie oblicza i zapisuje przynależność geograficzną obiektu.

    Używa PostGIS (ST_DWithin) z rzutowaniem na EPSG:3857 (metry) i buforem 50m,
    aby znaleźć regiony, w których leży dany punkt (lub leży tuż za ich granicą).
    Zapisuje wyniki do płaskiej tabeli odczytu (ObjectRegionCache).

    Args:
        object_id: ID obiektu TouristObject do przeliczenia.

    Returns:
        Komunikat tekstowy o statusie wykonania (przydatny w logach Celery).
    """
    try:
        tourist_obj = TouristObject.objects.get(id=object_id)
    except TouristObject.DoesNotExist:
        return f"Błąd: Obiekt o ID {object_id} nie istnieje."

    if not tourist_obj.geom:
        return f"Pominięto: Obiekt {tourist_obj.name} (ID: {object_id}) nie ma geometrii."

    # 1. Definiujemy parametry wyszukiwania przestrzennego
    # Chcemy szukać w promieniu 50 metrów (bufor dla błędów GPS i granic)
    # Wymaga to rzutowania z WGS84 (stopnie) na Web Mercator (metry) w locie.
    SEARCH_RADIUS_METERS = 50
    # Tworzymy obiekt Point, mówiąc Django, by potraktował go jako geometrię
    # gotową do transformacji (jeśli używasz w locie w QuerySetach, Django robi to za Ciebie
    # przy użyciu lookupów typu `dwithin`, ale my zrobimy to jeszcze prościej!)
    target_point = tourist_obj.geom

    # 2. Definiujemy mapę modeli regionów i ich typów w naszym Cache
    region_models_map = [
        (CountryModel, RegionLevelType.COUNTRY),
        (VoivodeshipModel, RegionLevelType.VOIVODESHIP),
        (ProvinceModel, RegionLevelType.PROVINCE),
        (SubprovinceModel, RegionLevelType.SUBPROVINCE),
        (MacroregionModel, RegionLevelType.MACROREGION),
        (MesoregionModel, RegionLevelType.MESOREGION),
        (TouristRegionModel, RegionLevelType.TOURIST_REGION),
    ]

    new_cache_entries = []

    # 3. Wykonujemy zapytania przestrzenne dla każdego poziomu hierarchii
    # Pamiętaj: Używamy tu Django ORM GIS lookups.
    # W PostGIS pod spodem wykona to: ST_DWithin(shape, target_point, 50, true)
    # (Django wie, że WGS84 trzeba liczyć na sferze, jeśli podasz `D(m=50)`).
    from django.contrib.gis.measure import D

    for ModelClass, level_type in region_models_map:
        # Szukamy wszystkich regionów danego typu, które są w odległości <= 50m od punktu
        found_regions = ModelClass.objects.filter(shape__distance_lte=(target_point, D(m=SEARCH_RADIUS_METERS)))

        for region in found_regions:
            # Sprawdzenie "twardego" przecięcia (wewnątrz granicy)
            # Jeśli punkt leży dokładnie wewnątrz, distance_meters = 0.0
            # Jeśli punkt "złapał" się w bufor 50m (np. góra graniczna po stronie czeskiej),
            # oznaczamy go przybliżonym promieniem poszukiwań.
            is_inside = region.shape.intersects(target_point)
            final_distance = 0.0 if is_inside else float(SEARCH_RADIUS_METERS)

            new_cache_entries.append(
                ObjectRegionCache(
                    tourist_object=tourist_obj,
                    region_level=level_type,
                    region_id=region.id,
                    region_name=region.name,
                    distance_meters=final_distance,
                )
            )

    # 4. Atomowa aktualizacja Cache (CQRS Write)
    # Zamykamy w transakcji: usuwamy stare powiązania i ładujemy nowe.
    # Dzięki temu task może być odpalany wielokrotnie (Idempotentność!).
    with transaction.atomic():
        ObjectRegionCache.objects.filter(tourist_object=tourist_obj).delete()
        if new_cache_entries:
            ObjectRegionCache.objects.bulk_create(new_cache_entries)

    # ==========================================
    # 5. INTELIGENTNA EKSTRAKCJA JĘZYKOWA (Regional Whitelist)
    # ==========================================
    # Zamiast opierać się na granicach (gdzie bufor 50m może nie dotknąć
    # państwa sąsiedniego), definiujemy listę pożądanych języków w naszym regionie.
    # Ignorujemy śmieci z OSM (np. japoński, chiński, hiszpański).

    RELEVANT_LANGS = ["pl", "cs", "sk", "de", "uk", "be", "szl", "csb", "hu", "ru", "rue"]

    local_names_updated = False
    new_local_names = tourist_obj.local_names or {}
    raw_tags = tourist_obj.osm_raw_tags

    if raw_tags:
        for lang_code in RELEVANT_LANGS:
            tag_key = f"name:{lang_code}"

            if tag_key in raw_tags:
                val = raw_tags[tag_key]
                # Zapisujemy, o ile różni się od głównej nazwy
                if val != tourist_obj.name and new_local_names.get(lang_code) != val:
                    new_local_names[lang_code] = val
                    local_names_updated = True

    if local_names_updated:
        tourist_obj.local_names = new_local_names
        tourist_obj.save(update_fields=["local_names"])

    return f"Sukces: Przeliczono obiekt '{tourist_obj.name}'. Znaleziono {len(new_cache_entries)} regionów."


@shared_task
def build_tourist_region_geometry_task(region_id: int) -> str:
    """Buduje geometrię Regionu Turystycznego i aktualizuje cache szczytów (CQRS)."""
    try:
        t_region = TouristRegionModel.objects.get(id=region_id)
    except TouristRegionModel.DoesNotExist:
        return f"Błąd: Region turystyczny o ID {region_id} nie istnieje."

    # ==========================================
    # 1. SCALANIE GEOMETRII (ST_Union)
    # ==========================================
    geoms = []

    # Wyciągamy z relacji M2M kształty wszystkich przypiętych klocków
    for qs in [
        t_region.provinces.all(),
        t_region.subprovinces.all(),
        t_region.macroregions.all(),
        t_region.mesoregions.all(),
    ]:
        for item in qs:
            if item.shape:
                geoms.append(item.shape)

    if geoms:
        # Złączamy wszystko biblioteką GEOS (Odpowiednik ST_UnaryUnion)
        combined = GeometryCollection(geoms).unary_union

        # Baza wymaga MultiPolygon. Jeśli złączenie dało jeden zwarty poligon, rzutujemy:
        if isinstance(combined, Polygon):
            t_region.shape = MultiPolygon(combined)
        elif isinstance(combined, MultiPolygon):
            t_region.shape = combined

        t_region.save(update_fields=["shape"])

    # ==========================================
    # 2. LOGICZNE ZASILENIE CQRS (Dziedziczenie)
    # ==========================================
    # Zbieramy ID składowych klocków
    prov_ids = t_region.provinces.values_list("id", flat=True)
    subprov_ids = t_region.subprovinces.values_list("id", flat=True)
    macro_ids = t_region.macroregions.values_list("id", flat=True)
    meso_ids = t_region.mesoregions.values_list("id", flat=True)

    # Budujemy zapytanie logiczne OR:
    # "Znajdź wpisy z Cache, które wskazują na którykolwiek z naszych klocków"
    query = (
        Q(region_level=RegionLevelType.PROVINCE, region_id__in=prov_ids)
        | Q(region_level=RegionLevelType.SUBPROVINCE, region_id__in=subprov_ids)
        | Q(region_level=RegionLevelType.MACROREGION, region_id__in=macro_ids)
        | Q(region_level=RegionLevelType.MESOREGION, region_id__in=meso_ids)
    )

    # Wyciągamy unikalne ID obiektów turystycznych (szczytów) z tych klocków
    matching_object_ids = ObjectRegionCache.objects.filter(query).values_list("tourist_object_id", flat=True).distinct()

    new_entries = []
    for obj_id in matching_object_ids:
        new_entries.append(
            ObjectRegionCache(
                tourist_object_id=obj_id,
                region_level=RegionLevelType.TOURIST_REGION,
                region_id=t_region.id,
                region_name=t_region.name,
                distance_meters=0.0,  # Z logicznego dziedziczenia przyjmujemy bazowy bufor
            )
        )

    with transaction.atomic():
        # Najpierw czyścimy stare wpisy, żeby uniknąć duplikatów przy re-edycji regionu
        ObjectRegionCache.objects.filter(region_level=RegionLevelType.TOURIST_REGION, region_id=t_region.id).delete()

        if new_entries:
            ObjectRegionCache.objects.bulk_create(new_entries, ignore_conflicts=True)

    return f"Sukces: Przypisano {len(new_entries)} obiektów do {t_region.name}."
