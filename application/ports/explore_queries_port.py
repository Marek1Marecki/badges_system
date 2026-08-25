"""Port dla usług odczytu zoptymalizowanych pod widoki (Query Layer)."""

from typing import Any, Protocol


class ExploreQueriesRepositoryPort(Protocol):
    """Zoptymalizowany adapter bazy danych tylko do odczytu złożonych widoków."""

    def get_points_of_interest_with_relations(self) -> Any:
        """Pobiera wszystkie szczyty wraz z relacjami (rodzice, odznaki) unikając N+1."""
        ...

    def get_regions_by_level(self, level: str) -> Any:
        """Pobiera wszystkie regiony z danego poziomu geograficznego (np.

        'MESOREGION').
                Args:
                  level: str:
                  level: str:

                Returns:
        """
        ...

    def get_object_region_cache_for_level(self, level: str) -> Any:
        """Pobiera płaską relację CQRS dla obiektów na zadanym poziomie.

        Args:
          level: str:
          level: str:

        Returns:
        """
        ...
