"""Testy jednostkowe dla VerifyBadgeUseCase (z użyciem mocków)."""

from unittest.mock import MagicMock

import pytest

from application.dto.verify_badge_dto import VerifyBadgeRequestDTO
from application.exceptions import UseCaseError
from application.use_cases.verify_badge import VerifyBadgeUseCase
from tests.fakes.clock import FakeClock


def _dto() -> VerifyBadgeRequestDTO:
    return VerifyBadgeRequestDTO(user_id=1, badge_code="KGP", cycle_number=1)


class TestVerifyBadgeUseCase:
    def test_init_with_repositories(self) -> None:
        uc = VerifyBadgeUseCase(MagicMock(), MagicMock(), MagicMock(), MagicMock(), FakeClock())
        assert uc._clock is not None

    def test_execute_raises_when_no_progress(self) -> None:
        progress_repo = MagicMock()
        progress_repo.get_progress.return_value = None
        uc = VerifyBadgeUseCase(progress_repo, MagicMock(), MagicMock(), MagicMock(), FakeClock())

        with pytest.raises(UseCaseError, match="nie subskrybuje"):
            uc.execute(_dto())

    def test_execute_returns_not_started_when_no_version_anchored(self) -> None:
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = None
        progress_repo.get_progress.return_value = progress

        uc = VerifyBadgeUseCase(progress_repo, MagicMock(), MagicMock(), MagicMock(), FakeClock())
        result = uc.execute(_dto())

        assert result["status"] == "NOT_STARTED"
        assert result["verified"] is False

    def test_execute_evaluates_domain_successfully(self) -> None:
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = 99
        progress.progress_id = 123
        progress.domain_status = "IN_PROGRESS"
        progress_repo.get_progress.return_value = progress
        progress_repo.get_active_progresses.return_value = []

        badge_repo = MagicMock()
        badge_version = MagicMock()
        badge_version.evaluate.return_value = {
            "verified": True,
            "status": "COMPLETED",
            "errors": [],
            "valid_ascents_count": 5,
        }
        badge_repo.get_badge_version_by_id.return_value = badge_version

        ascent_repo = MagicMock()
        ascent_repo.get_unconsumed_ascents.return_value = []

        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = None

        uc = VerifyBadgeUseCase(progress_repo, ascent_repo, profile_repo, badge_repo, FakeClock())
        result = uc.execute(_dto())

        assert result["verified"] is True
        assert result["status"] == "COMPLETED"
        progress_repo.update_domain_status.assert_called_once_with(123, "COMPLETED")
