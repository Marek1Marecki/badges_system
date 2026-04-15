"""Testy dla przypadku użycia weryfikacji odznaki."""

from datetime import date
from unittest.mock import Mock

import pytest

from application.dto.ascent_dto import AscentInputDTO, VerifyBadgeRequestDTO
from application.exceptions import UseCaseError
from application.use_cases.verify_badge import VerifyBadgeUseCase
from domain.exceptions import ValidationError
from domain.value_objects.ascent import ActivityType


class TestVerifyBadgeUseCase:
    """Testy klasy VerifyBadgeUseCase."""

    def test_init_with_repository(self):
        """Test inicjalizacji z repozytorium."""
        mock_repository = Mock()
        use_case = VerifyBadgeUseCase(mock_repository)
        assert use_case._repository == mock_repository

    def test_execute_successful_verification(self):
        """Test pomyślnej weryfikacji."""
        mock_repository = Mock()
        mock_badge_version = Mock()
        mock_badge_version.evaluate.return_value = None
        mock_repository.get_badge_version.return_value = mock_badge_version
        
        use_case = VerifyBadgeUseCase(mock_repository)
        
        request = VerifyBadgeRequestDTO(
            badge_code="BADGE001",
            version_code="v1",
            ascents=[
                AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1), activity="HIKING"),
                AscentInputDTO(peak_id=2, ascent_date=date(2023, 6, 1), activity="HIKING"),
            ]
        )
        
        result = use_case.execute(request)
        
        assert result["verified"] is True
        assert result["message"] == "Gratulacje! Odznaka przyznana."
        mock_repository.get_badge_version.assert_called_once_with("BADGE001", "v1")
        mock_badge_version.evaluate.assert_called_once()

    def test_execute_with_validation_error(self):
        """Test weryfikacji z błędem walidacji."""
        mock_repository = Mock()
        mock_badge_version = Mock()
        mock_badge_version.evaluate.side_effect = ValidationError("Insufficient peaks")
        mock_repository.get_badge_version.return_value = mock_badge_version
        
        use_case = VerifyBadgeUseCase(mock_repository)
        
        request = VerifyBadgeRequestDTO(
            badge_code="BADGE001",
            version_code="v1",
            ascents=[
                AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1), activity="HIKING"),
            ]
        )
        
        result = use_case.execute(request)
        
        assert result["verified"] is False
        assert result["message"] == "Insufficient peaks"
        mock_repository.get_badge_version.assert_called_once_with("BADGE001", "v1")
        mock_badge_version.evaluate.assert_called_once()

    def test_execute_with_badge_not_found(self):
        """Test weryfikacji gdy odznaka nie zostanie znaleziona."""
        mock_repository = Mock()
        mock_repository.get_badge_version.return_value = None
        
        use_case = VerifyBadgeUseCase(mock_repository)
        
        request = VerifyBadgeRequestDTO(
            badge_code="NONEXISTENT",
            version_code="v1",
            ascents=[]
        )
        
        with pytest.raises(UseCaseError, match="Nie znaleziono odznaki: NONEXISTENT \\(v1\\)"):
            use_case.execute(request)
        
        mock_repository.get_badge_version.assert_called_once_with("NONEXISTENT", "v1")

    def test_execute_with_empty_ascents_list(self):
        """Test weryfikacji z pustą listą wejść."""
        mock_repository = Mock()
        mock_badge_version = Mock()
        mock_badge_version.evaluate.side_effect = ValidationError("Wymagano 1 szczytów, masz 0")
        mock_repository.get_badge_version.return_value = mock_badge_version
        
        use_case = VerifyBadgeUseCase(mock_repository)
        
        request = VerifyBadgeRequestDTO(
            badge_code="BADGE001",
            version_code="v1",
            ascents=[]
        )
        
        result = use_case.execute(request)
        
        assert result["verified"] is False
        assert "Wymagano 1 szczytów, masz 0" in result["message"]

    def test_execute_with_multiple_validation_errors(self):
        """Test weryfikacji z wieloma błędami walidacji."""
        mock_repository = Mock()
        mock_badge_version = Mock()
        mock_badge_version.evaluate.side_effect = ValidationError("Error 1 | Error 2")
        mock_repository.get_badge_version.return_value = mock_badge_version
        
        use_case = VerifyBadgeUseCase(mock_repository)
        
        request = VerifyBadgeRequestDTO(
            badge_code="BADGE001",
            version_code="v1",
            ascents=[
                AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1), activity="CYCLING"),
            ]
        )
        
        result = use_case.execute(request)
        
        assert result["verified"] is False
        assert result["message"] == "Error 1 | Error 2"

    def test_execute_dto_to_domain_conversion(self):
        """Test konwersji DTO na obiekty domenowe."""
        mock_repository = Mock()
        mock_badge_version = Mock()
        mock_badge_version.evaluate.return_value = None
        mock_repository.get_badge_version.return_value = mock_badge_version
        
        use_case = VerifyBadgeUseCase(mock_repository)
        
        request = VerifyBadgeRequestDTO(
            badge_code="BADGE001",
            version_code="v1",
            ascents=[
                AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1), activity="HIKING"),
                AscentInputDTO(peak_id=2, ascent_date=date(2023, 6, 1), activity="CYCLING"),
            ]
        )
        
        use_case.execute(request)
        
        # Verify that evaluate was called with domain objects
        call_args = mock_badge_version.evaluate.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0].peak_id == 1
        assert call_args[0].activity == ActivityType.HIKING
        assert call_args[1].peak_id == 2
        assert call_args[1].activity == ActivityType.CYCLING

    def test_execute_with_different_activity_types(self):
        """Test weryfikacji z różnymi typami aktywności."""
        mock_repository = Mock()
        mock_badge_version = Mock()
        mock_badge_version.evaluate.return_value = None
        mock_repository.get_badge_version.return_value = mock_badge_version
        
        use_case = VerifyBadgeUseCase(mock_repository)
        
        request = VerifyBadgeRequestDTO(
            badge_code="BADGE001",
            version_code="v1",
            ascents=[
                AscentInputDTO(peak_id=1, ascent_date=date(2023, 1, 1), activity="SKIING"),
                AscentInputDTO(peak_id=2, ascent_date=date(2023, 6, 1), activity="CYCLING"),
                AscentInputDTO(peak_id=3, ascent_date=date(2023, 9, 1), activity="HIKING"),
            ]
        )
        
        result = use_case.execute(request)
        
        assert result["verified"] is True
        
        # Verify all activity types were converted correctly
        call_args = mock_badge_version.evaluate.call_args[0][0]
        activities = [ascent.activity for ascent in call_args]
        assert ActivityType.SKIING in activities
        assert ActivityType.CYCLING in activities
        assert ActivityType.HIKING in activities
