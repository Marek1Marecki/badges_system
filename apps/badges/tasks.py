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

from typing import Any

from celery import shared_task
from loguru import logger

from application.exceptions import TransientInfrastructureError, UseCaseError
from bootstrap.container import get_container


def _str(result: object) -> str:
    """Rzutuje wynik execute() na str — mypy nie zna typów z dict kontenera.

    Args:
      result: object:
      result: object:

    Returns:
    """
    return str(result)


@shared_task(bind=True, max_retries=15)
def fetch_osm_data_task(self, object_id: int) -> str:
    """Pobiera dane z OSM dla pojedynczego obiektu.

    Przy błędzie ponawia co 60s.
        Args:
          object_id: int:
          object_id: int:

        Returns:
    """
    from bootstrap import get_container

    try:
        use_case = get_container().fetch_osm_data
        result = _str(use_case.execute(object_id))
        calculate_object_regions_task.delay(object_id)
        return result
    except UseCaseError as e:
        return f"Błąd: {e}"
    except TransientInfrastructureError as e:
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


@shared_task(bind=True, max_retries=3)
def calculate_object_regions_task(self: Any, object_id: int) -> str:
    """Task asynchroniczny: Przelicza regiony i buduje płaską tabelę CQRS.

    Args:
      self: Any:
      object_id: int:
      self: Any:
      object_id: int:

    Returns:
    """
    try:
        use_case = get_container().calculate_object_regions
        use_case.execute(object_id=object_id)  # <--- BEZ PRZYPISANIA DO ZMIENNEJ
        return f"CQRS wyliczony dla obiektu: {object_id}"  # Zwracamy sztuczny string dla monitoringu Celery
    except Exception as exc:
        logger.error(f"CQRS Failed for {object_id}: {exc}")
        raise self.retry(exc=exc, countdown=10) from exc


@shared_task
def build_tourist_region_geometry_task(region_id: int) -> str:
    """Buduje geometrię Regionu Turystycznego i aktualizuje cache szczytów.

    Args:
      region_id: int:
      region_id: int:

    Returns:
    """
    from bootstrap import get_container

    try:
        use_case = get_container().build_tourist_region_geometry
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
        use_case = get_container().scan_proximity_candidates
        return _str(use_case.execute())
    except Exception as exc:
        logger.error(
            "Nieoczekiwany błąd w scan_proximity_candidates_task: {error}",
            error=str(exc),
        )
        raise


@shared_task
def run_osm_night_watchman_task(batch_size: int = 50) -> str:
    """Nocny skaner OSM — weryfikuje partię obiektów i zgłasza konflikty.

    Args:
      batch_size: int:  (Default value = 50)
      batch_size: int:  (Default value = 50)

    Returns:

    """
    from bootstrap import get_container

    try:
        use_case = get_container().run_osm_night_watchman
        return _str(use_case.execute(batch_size=batch_size))
    except Exception as exc:
        logger.error(
            "Nieoczekiwany błąd w run_osm_night_watchman_task: {error}",
            error=str(exc),
        )
        raise


@shared_task
def recalculate_poi_scores_task(profile_id: int) -> str:
    """Przelicza ranking szczytów (100/n) i inwaliduje cache Redis (ADR-015).

    Zadanie to jest wyzwalane asynchronicznie przez transakcje API,
    gwarantując niezaburzanie pracy wątku HTTP (Event-Driven Invalidation).

    Args:
      profile_id: int:
      profile_id: int:

    Returns:
    """
    from bootstrap import get_container

    try:
        service = get_container().poi_scoring_service
        service.recalculate_and_cache_for_profile(profile_id)
        return f"Sukces: Przeliczono punkty POI dla profilu (ID: {profile_id})."
    except Exception as exc:
        logger.error(f"Nieoczekiwany błąd w recalculate_poi_scores_task: {str(exc)}")
        raise


@shared_task
def fetch_badge_news_task() -> str:
    """Skanuje portale z newsami PTTK i wrzuca je do Admina (US-A01)."""
    from bootstrap import get_container

    try:
        use_case = get_container().fetch_badge_news
        return _str(use_case.execute())
    except Exception as exc:
        logger.error(f"Nieoczekiwany błąd w fetch_badge_news_task: {exc}")
        raise


@shared_task
def recalculate_object_regions_bulk_task(object_ids: list[int]) -> str:
    """Batch task: przelicza regiony dla wielu obiektów w jednej kolejce (AUDYT-073).

    Zmniejsza liczbę zadań Celery z N do 1 przy masowych akcjach admina.
    """
    from bootstrap import get_container

    use_case = get_container().calculate_object_regions
    for object_id in object_ids:
        try:
            use_case.execute(object_id=object_id)
        except Exception as exc:
            logger.error(f"CQRS Failed for object {object_id}: {exc}")
    return f"Sukces: Przeliczono regiony dla {len(object_ids)} obiektów."


@shared_task
def build_region_geometries_bulk_task(region_ids: list[int]) -> str:
    """Batch task: buduje geometrię dla wielu regionów w jednej kolejce (AUDYT-073)."""
    from bootstrap import get_container

    use_case = get_container().build_tourist_region_geometry
    for region_id in region_ids:
        try:
            use_case.execute(region_id)
        except Exception as exc:
            logger.error(f"Geometry build failed for region {region_id}: {exc}")
    return f"Sukces: Zbudowano geometrię dla {len(region_ids)} regionów."
