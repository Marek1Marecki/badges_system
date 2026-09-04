"""Testy dla DTO wejść (AscentDTO i AscentRequestDTO)."""

from datetime import date

import pytest
from pydantic import ValidationError

from application.dto.ascent_dto import AscentDTO, AscentRequestDTO


def test_ascent_dto_to_domain() -> None:
    """Test konwersji AscentDTO na obiekt domenowy."""
    dto = AscentDTO(peak_id=1, ascent_date=date(2024, 1, 1), region_ids=frozenset([10, 20]))
    domain_obj = dto.to_domain()
    assert domain_obj.peak_id == 1
    assert domain_obj.ascent_date == date(2024, 1, 1)
    assert domain_obj.region_ids == frozenset([10, 20])


def test_ascent_input_dto_to_domain() -> None:
    """Test konwersji AscentRequestDTO na obiekt domenowy."""
    dto = AscentRequestDTO(peak_id=1, ascent_date=date(2024, 1, 1))
    domain_obj = dto.to_domain()
    assert domain_obj.peak_id == 1
    assert domain_obj.ascent_date == date(2024, 1, 1)


def test_invalid_peak_id() -> None:
    """Test odrzucenia nieprawidłowego peak_id."""
    with pytest.raises(ValidationError):
        AscentRequestDTO(peak_id=0, ascent_date=date(2024, 1, 1))
