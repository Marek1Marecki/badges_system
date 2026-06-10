"""Testy dla DTO wejść (AscentDTO i AscentInputDTO)."""

from datetime import date

import pytest
from pydantic import ValidationError

from application.dto.ascent_dto import AscentDTO, AscentInputDTO


def test_ascent_dto_to_domain() -> None:
    dto = AscentDTO(peak_id=1, ascent_date=date(2024, 1, 1), region_ids=frozenset([10, 20]))
    domain_obj = dto.to_domain()
    assert domain_obj.peak_id == 1
    assert domain_obj.ascent_date == date(2024, 1, 1)
    assert domain_obj.region_ids == frozenset([10, 20])


def test_ascent_input_dto_to_domain() -> None:
    dto = AscentInputDTO(peak_id=1, ascent_date=date(2024, 1, 1))
    domain_obj = dto.to_domain()
    assert domain_obj.peak_id == 1
    assert domain_obj.ascent_date == date(2024, 1, 1)


def test_invalid_peak_id() -> None:
    with pytest.raises(ValidationError):
        AscentInputDTO(peak_id=0, ascent_date=date(2024, 1, 1))
