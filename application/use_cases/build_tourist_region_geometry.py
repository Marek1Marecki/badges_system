"""Przypadek użycia: Budowanie geometrii Regionu Turystycznego.

Zgodnie z 14-domain-purity.md — zero importów apps/, django/, infrastructure/.
"""

from typing import Any

from application.exceptions import UseCaseError


class BuildTouristRegionGeometryUseCase:
    """Buduje geometrię Regionu Turystycznego i aktualizuje CQRS cache."""

    def __init__(self, region_cache_repository: Any) -> None:
        """Inicjalizuje use case.

        Args:
            region_cache_repository: Adapter wykonujący operacje PostGIS.
        """
        self._repo = region_cache_repository

    def execute(self, region_id: int) -> str:
        """Scala geometrię i aktualizuje cache obiektów turystycznych.

        Args:
            region_id: ID TouristRegionModel do przeliczenia.

        Returns:
            Komunikat tekstowy o statusie.

        Raises:
            UseCaseError: Gdy region nie istnieje.
        """
        region = self._repo.get_tourist_region(region_id)

        if region is None:
            raise UseCaseError(f"Region turystyczny o ID {region_id} nie istnieje.")

        combined_geometry = self._repo.build_union_geometry(region_id)

        if combined_geometry is not None:
            self._repo.save_region_geometry(region_id, combined_geometry)

        object_ids = self._repo.find_object_ids_in_sub_regions(region_id)

        self._repo.replace_tourist_region_entries(
            region_id=region_id,
            region_name=region.name,
            object_ids=object_ids,
        )

        return f"Sukces: Przypisano {len(object_ids)} obiektów do '{region.name}'."
