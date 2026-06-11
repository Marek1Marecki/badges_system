"""Zadania asynchroniczne (Celery) — cienkie wrappery delegujące do use case'ów.

Zgodnie z architekturą heksagonalną:
- Tasks NIE zawierają logiki biznesowej
- Tasks odpowiadają za: obsługę retry, logowanie błędów Celery, wywołanie use case'u
- Cała logika żyje w application/use_cases/

Wzorzec:
    1. Pobierz use case z kontenera DI
    2. Wywołaj execute()
    3. Obsłuż wyjątki infrastrukturalne (retry, logowanie)
    4. Zwróć komunikat tekstowy do logów Celery
"""

from celery import shared_task
from loguru import logger

from application.exceptions import UseCaseError


def _str(result: object) -> str:
    """Rzutuje wynik execute() na str — mypy nie zna typów z dict kontenera."""
    return str(result)


@shared_task(bind=True, max_retries=15)
def fetch_osm_data_task(self, object_id: int) -> str:
    """Pobiera dane z OSM dla pojedynczego obiektu. Przy błędzie ponawia co 60s."""
    from bootstrap import get_container
    from infrastructure.adapters.osm_adapter import OsmAdapterError

    try:
        use_case = get_container()["fetch_osm_data"]
        result = _str(use_case.execute(object_id))
        calculate_object_regions_task.delay(object_id)
        return result
    except UseCaseError as e:
        return f"Błąd: {e}"
    except OsmAdapterError as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60) from e
        from apps.badges.models import TouristObject

        try:
            obj = TouristObject.objects.get(id=object_id)
            obj.status = "ERROR"
            obj.osm_error = f"Ostateczny błąd po 15 próbach: {e}"
            obj.save(update_fields=["status", "osm_error"])
        except TouristObject.DoesNotExist:
            pass
        return f"BŁĄD KRYTYCZNY: Nie udało się pobrać danych dla obiektu {object_id}."


@shared_task
def calculate_object_regions_task(object_id: int) -> str:
    """Oblicza przynależność geograficzną obiektu (PostGIS ST_DWithin)."""
    from bootstrap import get_container

    try:
        use_case = get_container()["calculate_object_regions"]
        return _str(use_case.execute(object_id))
    except UseCaseError as e:
        return f"Błąd: {e}"
    except Exception as exc:
        logger.error(
            "Nieoczekiwany błąd w calculate_object_regions_task dla obiektu {object_id}: {error}",
            object_id=object_id,
            error=str(exc),
        )
        raise


@shared_task
def build_tourist_region_geometry_task(region_id: int) -> str:
    """Buduje geometrię Regionu Turystycznego i aktualizuje cache szczytów."""
    from bootstrap import get_container

    try:
        use_case = get_container()["build_tourist_region_geometry"]
        return _str(use_case.execute(region_id))
    except UseCaseError as e:
        return f"Błąd: {e}"
    except Exception as exc:
        logger.error(
            "Nieoczekiwany błąd w build_tourist_region_geometry_task dla regionu {region_id}: {error}",
            region_id=region_id,
            error=str(exc),
        )
        raise


@shared_task
def scan_proximity_candidates_task() -> str:
    """Skanuje bazę szukając niepowiązanych obiektów bliskich sobie (Radar 150m)."""
    from bootstrap import get_container

    try:
        use_case = get_container()["scan_proximity_candidates"]
        return _str(use_case.execute())
    except Exception as exc:
        logger.error(
            "Nieoczekiwany błąd w scan_proximity_candidates_task: {error}",
            error=str(exc),
        )
        raise


@shared_task
def run_osm_night_watchman_task(batch_size: int = 50) -> str:
    """Nocny skaner OSM — weryfikuje partię obiektów i zgłasza konflikty."""
    from bootstrap import get_container

    try:
        use_case = get_container()["run_osm_night_watchman"]
        return _str(use_case.execute(batch_size=batch_size))
    except Exception as exc:
        logger.error(
            "Nieoczekiwany błąd w run_osm_night_watchman_task: {error}",
            error=str(exc),
        )
        raise


@shared_task
def recalculate_poi_scores_task(user_id: int) -> str:
    """Przelicza ranking szczytów (100/n) i inwaliduje cache Redis (ADR-015).

    Zadanie to jest wyzwalane asynchronicznie przez transakcje API,
    gwarantując niezaburzanie pracy wątku HTTP (Event-Driven Invalidation).
    """
    # TODO: Zaimplementować logikę w następnym US-C16!
    return f"Zadanie przeliczenia 100/n dla usera (ID: {user_id}) umieszczone w kolejce."
