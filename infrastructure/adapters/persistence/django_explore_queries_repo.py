"""Adapter odczytu dla zapytań eksploracji i rankingów."""

from typing import Any

from application.ports.explore_queries_port import ExploreQueriesRepositoryPort
from apps.badges.models import (
    MacroregionModel,
    MesoregionModel,
    ObjectRegionCache,
    TouristObject,
    VoivodeshipModel,
)


class DjangoExploreQueriesRepository(ExploreQueriesRepositoryPort):
    """Implementuje zoptymalizowane pod odczyt zapytania do bazy PTTK."""

    def get_points_of_interest_with_relations(self) -> Any:
        """Pobiera szczyty z relacjami prefetch (Ochrona N+1)."""
        # Pobiera całe rodziny, jeśli ktokolwiek ma punkty (w logice użyjemy filtrowania z serwisu)
        # Optymalizacja: Prefetch odznak by szybko złożyć je w słowniki w serwisie
        return (
            TouristObject.objects.filter(status="READY", is_active=True)
            .select_related("parent_object")
            .prefetch_related("badges")
        )

    def get_regions_by_level(self, level: str) -> Any:
        """Zwraca wszystkie regiony z danego poziomu."""
        if level == "VOIVODESHIP":
            return VoivodeshipModel.objects.all()
        elif level == "MACROREGION":
            return MacroregionModel.objects.all()
        elif level == "MESOREGION":
            return MesoregionModel.objects.all()
        return []

    def get_object_region_cache_for_level(self, level: str) -> Any:
        """Pobiera powiązania CQRS z płaskiej tabeli."""
        return ObjectRegionCache.objects.filter(region_level=level)
