"""Testy dla zadań Celery.

Po refaktoryzacji tasks.py jest cienkim wrapperem — mockujemy metody
repozytoriów i use case'ów, nie ORM bezpośrednio.

Wzorzec testowania:
- patch na metodach repozytorium (infrastructure/adapters/)
- weryfikacja że task wywołuje use case z poprawnymi argumentami
- weryfikacja komunikatów zwrotnych
"""

from unittest.mock import MagicMock, patch

from apps.badges.tasks import build_tourist_region_geometry_task, calculate_object_regions_task
from infrastructure.adapters.persistence.region_cache_repo import RegionMatch, TouristObjectData, TouristRegionData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tourist_object_data(**kwargs) -> TouristObjectData:
    """Fabryka TouristObjectData z sensownymi domyślnymi wartościami."""
    defaults = {
        "id": 1,
        "name": "Test Peak",
        "has_geom": True,
        "geom": MagicMock(),
        "osm_id": "123456",
        "osm_raw_tags": {},
        "local_names": {},
        "alt_name": None,
        "altitude": 1000.0,
        "wikipedia_link": None,
    }
    defaults.update(kwargs)
    return TouristObjectData(**defaults)


def _make_tourist_region_data(**kwargs) -> TouristRegionData:
    """Fabryka TouristRegionData z sensownymi domyślnymi wartościami."""
    defaults = {"id": 1, "name": "Sudety"}
    defaults.update(kwargs)
    return TouristRegionData(**defaults)


# ---------------------------------------------------------------------------
# TestCalculateObjectRegionsTask
# ---------------------------------------------------------------------------

class TestCalculateObjectRegionsTask:
    """Testy zadania calculate_object_regions_task."""

    def test_object_not_exists(self) -> None:
        """Task zwraca komunikat błędu gdy obiekt nie istnieje."""
        with patch(
            "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.get_tourist_object",
            return_value=None,
        ):
            result = calculate_object_regions_task(999)

        assert result == "Błąd: Obiekt o ID 999 nie istnieje."

    def test_object_without_geometry(self) -> None:
        """Task pomija obiekty bez geometrii."""
        obj = _make_tourist_object_data(id=1, name="Test Object", has_geom=False)

        with patch(
            "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.get_tourist_object",
            return_value=obj,
        ):
            result = calculate_object_regions_task(1)

        assert "Pominięto" in result
        assert "Test Object" in result

    def test_successful_calculation_with_regions(self) -> None:
        """Task przelicza regiony i zapisuje cache."""
        obj = _make_tourist_object_data(id=1, name="Test Peak", has_geom=True)
        matches = [
            RegionMatch(region_level="country", region_id=1, region_name="Polska", distance_meters=0.0),
            RegionMatch(region_level="voivodeship", region_id=2, region_name="Małopolska", distance_meters=0.0),
        ]

        with (
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.get_tourist_object",
                return_value=obj,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.find_regions_for_point",
                return_value=matches,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.replace_cache_for_object",
            ) as mock_replace,
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.save_local_names",
            ),
        ):
            result = calculate_object_regions_task(1)

        assert "Sukces" in result
        assert "Test Peak" in result
        assert "2" in result
        mock_replace.assert_called_once_with(1, matches)

    def test_local_names_extraction(self) -> None:
        """Task wyodrębnia lokalne nazwy z tagów OSM i zapisuje je."""
        obj = _make_tourist_object_data(
            id=1,
            name="Rysy",
            has_geom=True,
            local_names={"de": "Rysberg"},
            osm_raw_tags={
                "name:pl": "Rysy",
                "name:cs": "Rysí hora",
                "name:sk": "Rysy vrch",
                "name:de": "Rysberg",
                "name:fr": "Mont Rysy",  # fr nie jest w RELEVANT_LANGS
            },
        )

        with (
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.get_tourist_object",
                return_value=obj,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.find_regions_for_point",
                return_value=[],
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.replace_cache_for_object",
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.save_local_names",
            ) as mock_save_names,
        ):
            calculate_object_regions_task(1)

        # cs i sk są nowe — powinny być zapisane
        # de już istnieje z tą samą wartością — nie powinno być zapisywane ponownie
        # fr nie jest w RELEVANT_LANGS — ignorowane
        mock_save_names.assert_called_once()
        saved_names = mock_save_names.call_args[0][1]
        assert saved_names["cs"] == "Rysí hora"
        assert saved_names["sk"] == "Rysy vrch"
        assert saved_names["de"] == "Rysberg"
        assert "fr" not in saved_names


# ---------------------------------------------------------------------------
# TestBuildTouristRegionGeometryTask
# ---------------------------------------------------------------------------

class TestBuildTouristRegionGeometryTask:
    """Testy zadania build_tourist_region_geometry_task."""

    def test_region_not_exists(self) -> None:
        """Task zwraca komunikat błędu gdy region nie istnieje."""
        with patch(
            "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.get_tourist_region",
            return_value=None,
        ):
            result = build_tourist_region_geometry_task(999)

        assert result == "Błąd: Region turystyczny o ID 999 nie istnieje."

    def test_successful_geometry_building(self) -> None:
        """Task buduje geometrię i przypisuje obiekty do regionu."""
        region = _make_tourist_region_data(id=1, name="Sudety")
        object_ids = [1, 2, 3]

        with (
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.get_tourist_region",
                return_value=region,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.build_union_geometry",
                return_value=None,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.find_object_ids_in_sub_regions",
                return_value=object_ids,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.replace_tourist_region_entries",
            ) as mock_replace,
        ):
            result = build_tourist_region_geometry_task(1)

        assert "Sukces" in result
        assert "3" in result
        assert "Sudety" in result
        mock_replace.assert_called_once_with(
            region_id=1,
            region_name="Sudety",
            object_ids=object_ids,
        )

    def test_geometry_building_saves_when_geometry_exists(self) -> None:
        """Task zapisuje geometrię gdy adapter ją zwraca."""
        region = _make_tourist_region_data(id=1, name="Test Region")
        mock_geometry = MagicMock()

        with (
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.get_tourist_region",
                return_value=region,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.build_union_geometry",
                return_value=mock_geometry,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.save_region_geometry",
            ) as mock_save_geom,
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.find_object_ids_in_sub_regions",
                return_value=[],
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.replace_tourist_region_entries",
            ),
        ):
            build_tourist_region_geometry_task(1)

        mock_save_geom.assert_called_once_with(1, mock_geometry)

    def test_geometry_building_skips_save_when_no_geometry(self) -> None:
        """Task nie wywołuje save_region_geometry gdy brak składowych."""
        region = _make_tourist_region_data(id=1, name="Test Region")

        with (
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.get_tourist_region",
                return_value=region,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.build_union_geometry",
                return_value=None,
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.save_region_geometry",
            ) as mock_save_geom,
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.find_object_ids_in_sub_regions",
                return_value=[],
            ),
            patch(
                "infrastructure.adapters.persistence.region_cache_repo.RegionCacheRepository.replace_tourist_region_entries",
            ),
        ):
            build_tourist_region_geometry_task(1)

        mock_save_geom.assert_not_called()