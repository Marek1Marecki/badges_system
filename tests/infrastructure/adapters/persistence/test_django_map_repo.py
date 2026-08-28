"""Testy integracyjne dla DjangoMapRepository — bez mocków ORM."""

from datetime import date

import pytest
from django.contrib.gis.geos import Point

from apps.badges.models import OrganizerModel
from infrastructure.adapters.persistence.django_map_repo import DjangoMapRepository


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.testcontainers
class TestDjangoMapRepository:
    """Testy oparte na prawdziwej bazie danych PostgreSQL z PostGIS."""

    def setup_method(self):
        self.repo = DjangoMapRepository()

    def test_get_objects_in_bbox_returns_objects(self):
        """Zwraca obiekty w podanym bbox."""
        from apps.badges.models import TouristObject

        obj = TouristObject.objects.create(
            name="Test Peak",
            type="Szczyt",
            geom=Point(20.0, 50.0, srid=4326),
            is_active=True,
            status="READY",
        )

        result = self.repo.get_objects_in_bbox(10, 40, 30, 60, None, None, None)

        assert len(result) == 1
        assert result[0].id == obj.id
        assert result[0].name == "Test Peak"

    def test_get_objects_in_bbox_limits_results(self):
        """Ogranicza liczbę wyników do 500."""
        from apps.badges.models import TouristObject

        for i in range(600):
            TouristObject.objects.create(
                name=f"Peak {i}",
                type="Szczyt",
                geom=Point(20.0 + i * 0.001, 50.0, srid=4326),
                is_active=True,
                status="READY",
            )

        result = self.repo.get_objects_in_bbox(10, 40, 30, 60, None, None, None)

        assert len(result) <= 500

    def test_get_objects_in_bbox_filters_by_badge(self):
        """Filtruje obiekty według kodu odznaki."""
        from apps.badges.models import BadgeModel, BadgeVersionModel, TouristObject

        badge = BadgeModel.objects.create(
            code="KGP", name="Korona Gór Polski", organizer=OrganizerModel.objects.create(name="PTTK")
        )
        version = BadgeVersionModel.objects.create(badge=badge, version_code="v2024", valid_from=date(2024, 1, 1))
        obj = TouristObject.objects.create(
            name="KGP Peak",
            type="Szczyt",
            geom=Point(20.0, 50.0, srid=4326),
            is_active=True,
            status="READY",
        )
        version.pool_peaks.add(obj)

        result = self.repo.get_objects_in_bbox(10, 40, 30, 60, "KGP", None, None)

        assert len(result) == 1
        assert result[0].id == obj.id

    def test_get_objects_along_line_returns_objects(self):
        """Zwraca obiekty wokół linii."""
        from apps.badges.models import TouristObject

        obj = TouristObject.objects.create(
            name="Line Peak",
            type="Szczyt",
            geom=Point(5.0, 5.0, srid=4326),
            altitude=1000,
            is_active=True,
            status="READY",
        )

        result = self.repo.get_objects_along_line("LINESTRING(0 0, 10 10)", 100000)

        assert len(result) == 1
        assert result[0]["id"] == obj.id
        assert result[0]["name"] == "Line Peak"
        assert result[0]["altitude"] == 1000

    def test_get_objects_along_line_returns_empty_on_invalid_wkt(self):
        """Zwraca pustą listę przy nieprawidłowym WKT."""
        result = self.repo.get_objects_along_line("invalid", 1000)
        assert result == []
