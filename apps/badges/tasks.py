"""Zadania asynchroniczne (Celery) dla aplikacji odznak.

Zawiera m.in. logikę przeliczania relacji przestrzennych obiektów turystycznych,
odciążając główny wątek aplikacji webowej.
"""

from celery import shared_task
from django.contrib.gis.geos import GeometryCollection, MultiPolygon, Point, Polygon
from django.db import transaction
from django.db.models import F, Q
from django.utils.timezone import now

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
from infrastructure.adapters.osm_adapter import OsmAdapterError, OsmDataExtractor, OverpassClient


@shared_task(bind=True, max_retries=15)
def fetch_osm_data_task(self, object_id: int) -> str:
    """Pobiera dane z OSM. Przy błędzie ponawia próbę równo co 60 sekund."""
    try:
        obj = TouristObject.objects.get(id=object_id)
    except TouristObject.DoesNotExist:
        return f"Błąd: Obiekt {object_id} nie istnieje."

    if not obj.osm_id:
        return "Pominięto: Brak OSM ID."

    client = OverpassClient()
    try:
        osm_node = client.fetch_object(obj.osm_id)
    except OsmAdapterError as e:
        # LINIOWY RETRY (60 sekund), dopóki nie wyczerpiemy prób (max_retries=10)
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60) from e
        else:
            # Wyczerpano próby! Oznaczamy na czerwono w panelu Admina.
            obj.status = "ERROR"
            obj.osm_error = f"Ostateczny błąd po 15 próbach: {str(e)}"
            obj.save(update_fields=["status", "osm_error"])
            return f"BŁĄD KRYTYCZNY: Nie udało się pobrać {obj.osm_id}."

    # Mamy dane! Inteligentna ekstrakcja (Data Override chroni ręczne wpisy)
    obj.osm_raw_tags = osm_node.tags

    ext_name = OsmDataExtractor.extract_name(osm_node.tags)
    if not obj.name and ext_name:
        obj.name = ext_name

    ext_alt = OsmDataExtractor.extract_alt_name(osm_node.tags, obj.name)
    if not obj.alt_name and ext_alt:
        obj.alt_name = ext_alt

    ext_altit = OsmDataExtractor.extract_altitude(osm_node.tags)
    if not obj.altitude and ext_altit is not None:
        obj.altitude = ext_altit

    ext_wiki = OsmDataExtractor.extract_wikipedia_link(osm_node.tags)
    if not obj.wikipedia_link and ext_wiki:
        obj.wikipedia_link = ext_wiki

    if osm_node.version:
        obj.osm_version = osm_node.version
    if osm_node.timestamp:
        obj.osm_timestamp = osm_node.timestamp

    if not obj.geom:
        obj.geom = Point(osm_node.longitude, osm_node.latitude, srid=4326)

    determined_type, _ = OsmDataExtractor.determine_type(osm_node.tags)
    if determined_type:
        obj.type = determined_type
    elif not obj.type:
        obj.type = "Inny punkt"

    # Aktualizujemy status i zdejmujemy flagę błędu
    obj.status = "READY"
    obj.osm_error = None
    obj.save()

    # MAGIA ŁAŃCUCHA: Teraz wyzwalamy przeliczanie geografii CQRS dla tego obiektu!
    calculate_object_regions_task.delay(obj.id)

    return f"Sukces: Pobrano z OSM {obj.osm_id}. Wyzwolono przeliczanie regionów."


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


@shared_task
def scan_proximity_candidates_task() -> str:
    """Skanuje całą bazę szukając niepowiązanych obiektów blisko siebie (Radar 150m)."""

    # Importujemy lokalnie, by uniknąć problemów cyrkularnych
    from django.contrib.gis.measure import D

    from apps.badges.models import ProximityCandidate, ProximityStatus, TouristObject

    SEARCH_RADIUS = 150.0  # 150 metrów

    # Szukamy tylko wśród obiektów, które fizycznie istnieją, mają geometrię
    # i nie są "podrzędne" (nie mają jeszcze rodzica)
    base_qs = TouristObject.objects.filter(geom__isnull=False, is_active=True, parent_object__isnull=True)

    created_count = 0

    # Pętla po wszystkich obiektach. To zadanie może zająć chwilę w dużej bazie,
    # ale działa w tle, więc nie ma to znaczenia.
    for obj in base_qs:
        # Szukamy sąsiadów w promieniu 150m (używając lookupu D)
        neighbors = base_qs.exclude(id=obj.id).filter(geom__distance_lte=(obj.geom, D(m=SEARCH_RADIUS)))

        for neighbor in neighbors:
            # Uporządkowanie alfabetyczne (lub po ID), by uniknąć zapisu pary (A,B) i (B,A)
            if obj.id >= neighbor.id:
                continue

            # Liczymy dokładny dystans w metrach dla panelu informacyjnego
            # dla bazy używamy ST_Distance, ale w pythonie wystarczy mnożnik
            # dokładniej: obj.geom.transform(3857, clone=True).distance(neighbor.geom.transform(3857, clone=True))

            try:
                # PostGIS transform daje dokładne metry
                exact_dist = obj.geom.transform(3857, clone=True).distance(neighbor.geom.transform(3857, clone=True))
            except Exception:
                exact_dist = 0.0

            # Próba zapisu do Skrzynki. Jeśli już tam są, get_or_create zignoruje.
            candidate, created = ProximityCandidate.objects.get_or_create(
                obj_a=obj, obj_b=neighbor, defaults={"distance_meters": exact_dist, "status": ProximityStatus.PENDING}
            )

            if created:
                created_count += 1

    return f"Skanowanie zakończone. Utworzono {created_count} nowych kandydujących par."


@shared_task
def run_osm_night_watchman_task(batch_size: int = 50) -> str:
    """Nocny Skaner (Re-hydrator). Pobiera partię obiektów, by uaktualnić ich tagi
    i ewentualnie zgłosić konflikty do Panelu Admina.
    """
    from apps.badges.models import OsmSyncConflict, TouristObject
    from infrastructure.adapters.osm_adapter import OsmDataExtractor, OverpassClient

    # 1. Pobieramy 'batch_size' obiektów, zaczynając od tych najdawniej sprawdzanych.
    # Wymagają one posiadania osm_id (bo ręcznych i tak nie sprawdzimy).
    # order_by('last_sync_check') sortuje NULLe najpierw, potem najstarsze daty.
    objects_to_check = list(
        TouristObject.objects.exclude(osm_id__isnull=True)
        .exclude(osm_id="")
        .order_by(F("last_sync_check").asc(nulls_first=True))[:batch_size]
    )

    if not objects_to_check:
        return "Brak obiektów do synchronizacji."

    osm_ids = [obj.osm_id for obj in objects_to_check]
    client = OverpassClient()

    # 2. Strzał masowy z obsługą twardych błędów API
    from infrastructure.adapters.osm_adapter import OsmAdapterError

    try:
        osm_data_map = client.fetch_multiple_objects(osm_ids)
    except OsmAdapterError as e:
        # Serwer leży. Przerywamy całe zadanie. Nie aktualizujemy daty last_sync_check,
        # żeby te same obiekty mogły spróbować jutro.
        return f"PRZERWANO: Błąd połączenia z API OSM -> {str(e)}"

    conflicts_created = 0
    updated_silently = 0
    current_time = now()

    # 3. Analiza każdego obiektu z osobna
    for obj in objects_to_check:
        # Znaczymy, że go dzisiaj sprawdzaliśmy, by jutro wziął się za kolejne na liście!
        obj.last_sync_check = current_time

        osm_node = osm_data_map.get(obj.osm_id)

        # PRZYPADEK A: DUCH (Obiekt zniknął z mapy!)
        if not osm_node:
            OsmSyncConflict.objects.get_or_create(
                tourist_object=obj,
                field_name="is_active",
                defaults={
                    "old_value": str(obj.is_active),
                    "new_value": "False",  # Proponujemy miękkie usunięcie!
                },
            )
            conflicts_created += 1
            obj.save(update_fields=["last_sync_check"])
            continue

        # PRZYPADEK B: Analiza danych (The Smart Extractor)
        # Zawsze i bez pytania aktualizujemy Data Lake (bo to brudnopis)
        obj.osm_raw_tags = osm_node.tags
        obj.osm_version = osm_node.version
        obj.osm_timestamp = osm_node.timestamp

        # Sprawdzamy Wysokość
        ext_alt = OsmDataExtractor.extract_altitude(osm_node.tags)
        if ext_alt is not None and ext_alt != obj.altitude:
            # Wystąpił konflikt! Odkładamy do skrzynki.
            OsmSyncConflict.objects.get_or_create(
                tourist_object=obj,
                field_name="altitude",
                defaults={"old_value": str(obj.altitude), "new_value": str(ext_alt)},
            )
            conflicts_created += 1

        # Sprawdzamy Link do Wikipedii
        ext_wiki = OsmDataExtractor.extract_wikipedia_link(osm_node.tags)
        if ext_wiki and ext_wiki != obj.wikipedia_link:
            OsmSyncConflict.objects.get_or_create(
                tourist_object=obj,
                field_name="wikipedia_link",
                defaults={"old_value": obj.wikipedia_link or "Brak", "new_value": ext_wiki},
            )
            conflicts_created += 1

        # Zapisujemy zmiany ciche (Data Lake i Data Sprawdzenia)
        obj.save(update_fields=["osm_raw_tags", "osm_version", "osm_timestamp", "last_sync_check"])
        updated_silently += 1

    return (
        f"Stróż skończył. Obiekty: {len(objects_to_check)}. "
        f"Konflikty: {conflicts_created}. Zaktualizowano cicho: {updated_silently}."
    )
