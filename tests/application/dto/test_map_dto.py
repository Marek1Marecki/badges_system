"""Testy DTO dla żądań mapowych (AUDYT-049).

Czyste testy walidacji pydantic — nie wymagają DB ani Django settings.
Audyt-027: walidatory `Field(ge=, le=)` muszą odrzucać
fałszywe wektory bbox (np. ``-999,-999,999,999``) zanim trafią do PostGIS.
"""

from datetime import date

import pytest
from pydantic import ValidationError

from application.dto.map_dto import MapExploreRequestDTO


class TestBboxRangeValidation:
    """AUDYT-049: Bezwzględna walidacja zakresu geograficznego bbox."""

    def test_accepts_valid_bbox(self):
        """Poprawny bbox w granicach -180..180 / -90..90."""
        dto = MapExploreRequestDTO(
            profile_id=1,
            min_lon=10.0,
            min_lat=20.0,
            max_lon=30.0,
            max_lat=40.0,
        )
        assert dto.min_lon == 10.0

    @pytest.mark.parametrize(
        "min_lon,min_lat,max_lon,max_lat",
        [
            (-999, -999, 999, 999),  # AUDYT-049: klasyczny atak DoS
            (181, 0, 1, 1),  # lon > 180
            (0, 91, 1, 1),  # lat > 90
            (-181, 0, 1, 1),  # lon < -180
            (0, -91, 1, 1),  # lat < -90
        ],
    )
    def test_rejects_out_of_range_bbox(self, min_lon, min_lat, max_lon, max_lat):
        """Odrzuca bbox poza dopuszczalnym zakresem geograficznym (DoS protection)."""
        with pytest.raises(ValidationError):
            MapExploreRequestDTO(
                profile_id=1,
                min_lon=min_lon,
                min_lat=min_lat,
                max_lon=max_lon,
                max_lat=max_lat,
            )

    def test_rejects_extra_fields(self):
        """Brak tolerancji dla nieznanych pól (extra='forbid')."""
        with pytest.raises(ValidationError):
            MapExploreRequestDTO(
                profile_id=1,
                min_lon=0.0,
                min_lat=0.0,
                max_lon=1.0,
                max_lat=1.0,
                evil_param="drop table",
            )
