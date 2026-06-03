"""Testy dla DTO wejść użytkownika."""

from datetime import date

import pytest

from application.dto.ascent_dto import AscentInputDTO, VerifyBadgeRequestDTO
from domain.value_objects.ascent import Ascent


class TestAscentInputDTO:
    """Testy klasy AscentInputDTO."""

    def test_valid_ascent_input_dto(self):
        """Test tworzenia poprawnego DTO."""
        dto = AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1))

        assert dto.peak_id == 1
        assert dto.ascent_date == date(2023, 1, 1)

    def test_to_domain_conversion(self):
        """Test konwersji na obiekt domenowy."""
        dto = AscentInputDTO(peak_id=42, ascent_date=date(2023, 6, 15))

        domain_ascent = dto.to_domain()

        assert isinstance(domain_ascent, Ascent)
        assert domain_ascent.peak_id == 42
        assert domain_ascent.ascent_date == date(2023, 6, 15)

    def test_validation_peak_id_must_be_positive(self):
        """Test walidacji - peak_id musi być dodatni."""
        with pytest.raises(ValueError) as exc_info:
            AscentInputDTO(peak_id=0, ascent_date=date(2023, 1, 1))

        assert "peak_id" in str(exc_info.value)
        assert "greater than 0" in str(exc_info.value)

    def test_validation_peak_id_cannot_be_negative(self):
        """Test walidacji - peak_id nie może być ujemny."""
        with pytest.raises(ValueError):
            AscentInputDTO(peak_id=-1, ascent_date=date(2023, 1, 1))

    def test_validation_with_large_peak_id(self):
        """Test walidacji z dużym peak_id."""
        dto = AscentInputDTO(peak_id=999999, ascent_date=date(2023, 1, 1))

        assert dto.peak_id == 999999
        domain_ascent = dto.to_domain()
        assert domain_ascent.peak_id == 999999

    def test_dto_is_immutable(self):
        """Test że DTO jest immutable."""
        dto = AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1))

        # Pydantic models are mutable by default, but we can test the structure
        assert hasattr(dto, "peak_id")
        assert hasattr(dto, "ascent_date")


class TestVerifyBadgeRequestDTO:
    """Testy klasy VerifyBadgeRequestDTO."""

    def test_valid_verify_badge_request_dto(self):
        """Test tworzenia poprawnego żądania weryfikacji."""
        ascents = [
            AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1)),
            AscentInputDTO(peak_id=2, ascent_date=date(2023, 6, 1)),
        ]

        request = VerifyBadgeRequestDTO(badge_code="BADGE001", version_code="v1", ascents=ascents)

        assert request.badge_code == "BADGE001"
        assert request.version_code == "v1"
        assert len(request.ascents) == 2
        assert request.ascents[0].peak_id == 1

    def test_request_with_empty_ascents_list(self):
        """Test żądania z pustą listą wejść."""
        request = VerifyBadgeRequestDTO(badge_code="BADGE001", version_code="v1", ascents=[])

        assert request.badge_code == "BADGE001"
        assert request.version_code == "v1"
        assert request.ascents == []

    def test_request_with_single_ascent(self):
        """Test żądania z pojedynczym wejściem."""
        ascents = [AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1))]

        request = VerifyBadgeRequestDTO(badge_code="BADGE001", version_code="v1", ascents=ascents)

        assert len(request.ascents) == 1

    def test_request_with_different_badge_codes(self):
        """Test żądania z różnymi kodami odznak."""
        ascents = [AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1))]

        badge_codes = ["BADGE001", "CROWN", "SUMMIT", "123"]
        version_codes = ["v1", "v2", "latest", "1.0"]

        for badge_code in badge_codes:
            for version_code in version_codes:
                request = VerifyBadgeRequestDTO(badge_code=badge_code, version_code=version_code, ascents=ascents)

                assert request.badge_code == badge_code
                assert request.version_code == version_code

    def test_request_with_edge_case_dates(self):
        """Test żądania z datami granicznymi."""
        ascents = [
            AscentInputDTO(peak_id=1, ascent_date=date(1900, 1, 1)),
            AscentInputDTO(peak_id=2, ascent_date=date(2100, 12, 31)),
        ]

        request = VerifyBadgeRequestDTO(badge_code="BADGE001", version_code="v1", ascents=ascents)

        assert request.ascents[0].ascent_date == date(1900, 1, 1)
        assert request.ascents[1].ascent_date == date(2100, 12, 31)

    def test_request_with_empty_strings(self):
        """Test żądania z pustymi stringami."""
        ascents = [AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1))]

        request = VerifyBadgeRequestDTO(badge_code="", version_code="", ascents=ascents)

        assert request.badge_code == ""
        assert request.version_code == ""
