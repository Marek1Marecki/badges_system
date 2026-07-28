"""Testy jednostkowe dla VerifyBadgeUseCase (z użyciem mocków)."""

from unittest.mock import MagicMock

import pytest

from application.dto.verify_badge_dto import VerifyBadgeRequestDTO
from application.exceptions import ResourceNotFoundError
from application.use_cases.verify_badge import VerifyBadgeUseCase
from domain.value_objects.verification_result import TierResult, VerificationResult
from tests.fakes.clock import FakeClock


def _dto() -> VerifyBadgeRequestDTO:
    return VerifyBadgeRequestDTO(profile_id=1, badge_code="KGP", cycle_number=1)


class TestVerifyBadgeUseCase:
    def test_init_with_repositories(self) -> None:
        uc = VerifyBadgeUseCase(MagicMock(), MagicMock(), MagicMock(), MagicMock(), FakeClock())
        assert uc._clock is not None

    def test_execute_raises_when_no_progress(self) -> None:
        progress_repo = MagicMock()
        progress_repo.get_progress.return_value = None
        uc = VerifyBadgeUseCase(progress_repo, MagicMock(), MagicMock(), MagicMock(), FakeClock())

        # ZMIANA: Zgodnie z nową logiką rzucamy 404 (ResourceNotFoundError), nie 400 (UseCaseError)
        with pytest.raises(ResourceNotFoundError, match="nie subskrybuje"):
            uc.execute(_dto())

    def test_execute_returns_not_started_when_no_version_anchored(self) -> None:
        """Kiedy turysta zaczął subskrypcję, ale nie ma logów, version_id jest puste."""
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
        badge_version.evaluate.return_value = VerificationResult(
            verified=True,
            status="COMPLETED",
            errors=[],
            valid_ascents_count=5,
            tiers=[TierResult(tier_id=1, name="Standard", status="COMPLETED", required_count=5)],
        )
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

    def test_execute_applies_cutoff_date_for_cycle_2(self) -> None:
        """Dla cyklu > 1, logi są odcinane po dacie zamknięcia poprzedniego cyklu."""
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = 99
        progress.progress_id = 123
        progress.domain_status = "IN_PROGRESS"
        progress_repo.get_progress.return_value = progress
        progress_repo.get_active_progresses.return_value = []

        prev_cycle = MagicMock()
        prev_cycle.logistic_status_date = "2023-01-01"
        progress_repo.get_progress.side_effect = [progress, prev_cycle]

        badge_repo = MagicMock()
        badge_version = MagicMock()
        badge_version.evaluate.return_value = VerificationResult(
            verified=False,
            status="IN_PROGRESS",
            errors=[],
            valid_ascents_count=3,
            tiers=[TierResult(tier_id=1, name="Standard", status="IN_PROGRESS", required_count=5)],
        )
        badge_repo.get_badge_version_by_id.return_value = badge_version

        ascent_repo = MagicMock()
        ascent_repo.get_unconsumed_ascents.return_value = []

        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = None

        dto = VerifyBadgeRequestDTO(profile_id=1, badge_code="KGP", cycle_number=2)
        uc = VerifyBadgeUseCase(progress_repo, ascent_repo, profile_repo, badge_repo, FakeClock())
        result = uc.execute(dto)

        ascent_repo.get_unconsumed_ascents.assert_called_once_with(
            profile_id=1, badge_code="KGP", cutoff_date="2023-01-01"
        )

    def test_execute_preserves_completed_status_from_history(self) -> None:
        """PRAWA NABYTE: Jeśli progress był COMPLETED, wymusza status COMPLETED nawet po zmianie profilu."""
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = 99
        progress.progress_id = 123
        progress.domain_status = "COMPLETED"
        progress_repo.get_progress.return_value = progress
        progress_repo.get_active_progresses.return_value = []

        badge_repo = MagicMock()
        badge_version = MagicMock()
        badge_version.evaluate.return_value = VerificationResult(
            verified=False,
            status="IN_PROGRESS",
            errors=["Wiek nie spełnia wymogów"],
            valid_ascents_count=5,
            tiers=[TierResult(tier_id=1, name="Standard", status="IN_PROGRESS", required_count=5)],
        )
        badge_repo.get_badge_version_by_id.return_value = badge_version

        ascent_repo = MagicMock()
        ascent_repo.get_unconsumed_ascents.return_value = []

        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = None

        uc = VerifyBadgeUseCase(progress_repo, ascent_repo, profile_repo, badge_repo, FakeClock())
        result = uc.execute(_dto())

        assert result["verified"] is True
        assert result["status"] == "COMPLETED"
        assert result["errors"] == ["Wiek nie spełnia wymogów"]
        assert result["tiers"][0]["status"] == "IN_PROGRESS"

    def test_execute_skips_update_when_status_unchanged(self) -> None:
        """Nie aktualizuje statusu w bazie, jeśli nie zmienił się."""
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = 99
        progress.progress_id = 123
        progress.domain_status = "IN_PROGRESS"
        progress_repo.get_progress.return_value = progress
        progress_repo.get_active_progresses.return_value = []

        badge_repo = MagicMock()
        badge_version = MagicMock()
        badge_version.evaluate.return_value = VerificationResult(
            verified=False,
            status="IN_PROGRESS",
            errors=[],
            valid_ascents_count=3,
            tiers=[TierResult(tier_id=1, name="Standard", status="IN_PROGRESS", required_count=5)],
        )
        badge_repo.get_badge_version_by_id.return_value = badge_version

        ascent_repo = MagicMock()
        ascent_repo.get_unconsumed_ascents.return_value = []

        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = None

        uc = VerifyBadgeUseCase(progress_repo, ascent_repo, profile_repo, badge_repo, FakeClock())
        result = uc.execute(_dto())

        assert result["status"] == "IN_PROGRESS"
        progress_repo.update_domain_status.assert_not_called()

    def test_get_completed_badges_filters_by_status(self) -> None:
        """Metoda pomocnicza zwraca tylko odznaki ze statusem COMPLETED."""
        progress_repo = MagicMock()
        progress1 = MagicMock()
        progress1.badge_code = "KGP"
        progress1.domain_status = "COMPLETED"
        progress2 = MagicMock()
        progress2.badge_code = "GOT"
        progress2.domain_status = "IN_PROGRESS"
        progress3 = MagicMock()
        progress3.badge_code = "KZG"
        progress3.domain_status = "COMPLETED"
        progress_repo.get_active_progresses.return_value = [progress1, progress2, progress3]

        uc = VerifyBadgeUseCase(progress_repo, MagicMock(), MagicMock(), MagicMock(), FakeClock())
        completed = uc._get_completed_badges(profile_id=1)

        assert completed == frozenset(["KGP", "KZG"])
