"""Port dla usług odczytu zoptymalizowanych pod widoki (Query Layer)."""

from collections.abc import Sequence
from typing import Any, Protocol

from application.dto.tourist_views_dto import BadgeCatalogEntryResponseDTO


class ExploreQueriesRepositoryPort(Protocol):
    """Zoptymalizowany adapter bazodanowy tylko do odczytu złożonych widoków."""

    def get_points_of_interest_with_relations(self) -> Any:
        """Pobiera wszystkie szczyty wraz z relacjami (rodzice, odznaki) unikając N+1."""
        ...

    def get_regions_by_level(self, level: str) -> Any:
        """Pobiera wszystkie regiony z danego poziomu geograficznego (np.

        'MESOREGION').
        """
        ...

    def get_object_region_cache_for_level(self, level: str) -> Any:
        """Pobiera płaską relację CQRS dla obiektów na zadanym poziomie."""
        ...

    def get_catalog_badges(self, profile_id: int) -> Sequence[BadgeCatalogEntryResponseDTO]:
        """Pobiera katalog odznak z danymi subskrypcji i statusu dla profilu.

        Args:
          profile_id: int:

        Returns:
          Sequence[BadgeCatalogEntryResponseDTO]: Lista wpisów katalogu odznak.
        """
        ...

    def get_badge_detail_data(self, badge_code: str, profile_id: int) -> Any:
        """Pobiera surowe dane odznaki dla widoku badge_detail (z prefetchami N+1)."""
        ...

    def get_object_detail_data(self, object_id: int, profile_id: int) -> Any:
        """Pobiera surowe dane obiektu turystycznego dla widoku object_detail."""
        ...

    def get_region_context_data(self, region_level: str, region_id: int, profile_id: int) -> Any:
        """Pobiera surowe dane kontekstu regionu dla widoku region_detail."""
        ...

    def get_organizer_detail(self, organizer_id: int) -> Any:
        """Pobiera organizatora z jego odznakami dla widoku organizer_detail."""
        ...

    def get_subscribed_badge_ids(self, profile_id: int) -> list[int]:
        """Pobiera ID odznak subskrybowanych przez profil (dla organizer_detail)."""
        ...
