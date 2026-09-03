"""Testy jednostkowe dla EvaluateBadgeProgressQuery (z użyciem mocków)."""

from unittest.mock import MagicMock

import pytest

from application.exceptions import ResourceNotFoundError
from application.use_cases.verify_badge import (
    EvaluateBadgeProgressQuery,
    UpdateBadgeProgressCommand,
)
from domain.services.badge_awarding_domain_service import BadgeAwardingDomainService
from domain.value_objects.verification_result import TierResult, VerificationResult
from tests.fakes.clock import FakeClock

AWARDING_SERVICE = BadgeAwardingDomainService()


class TestEvaluateBadgeProgressQuery:
    def test_init_with_repositories(self) -> None:
        """Test inicjalizacji EvaluateBadgeProgressQuery z repozytoriami."""
        uc = EvaluateBadgeProgressQuery(
            MagicMock(), MagicMock(), MagicMock(), MagicMock(), FakeClock(), AWARDING_SERVICE
        )
        assert uc._clock is not None

    def test_execute_raises_when_no_progress(self) -> None:
        """Test podniesienia błędu przy braku postępu."""
        progress_repo = MagicMock()
        progress_repo.get_progress.return_value = None
        uc = EvaluateBadgeProgressQuery(
            progress_repo, MagicMock(), MagicMock(), MagicMock(), FakeClock(), AWARDING_SERVICE
        )

        with pytest.raises(ResourceNotFoundError, match="nie subskrybuje"):
            # Zmiana: podajemy płaskie parametry, bo DTO zostało odchudzone!
            result = uc.execute(profile_id=1, badge_code="KGP", cycle_number=1)

    def test_execute_returns_not_started_when_no_version_anchored(self) -> None:
        """Kiedy turysta zaczął subskrypcję, ale nie ma logów, a w bazie nie ma nowej wersji odznaki."""
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = None
        progress_repo.get_progress.return_value = progress

        badge_repo = MagicMock()
        badge_repo.get_latest_badge_version.return_value = None

        uc = EvaluateBadgeProgressQuery(
            progress_repo, MagicMock(), MagicMock(), badge_repo, FakeClock(), AWARDING_SERVICE
        )

        with pytest.raises(ResourceNotFoundError, match="Brak zdefiniowanego regulaminu"):
            result = uc.execute(profile_id=1, badge_code="KGP", cycle_number=1)

    def test_execute_evaluates_domain_successfully(self) -> None:
        """Test pomyślnej ewaluacji domenowej postępu odznaki."""
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = 99
        progress.progress_id = 123
        progress.domain_status = "IN_PROGRESS"
        progress_repo.get_progress.return_value = progress
        progress_repo.get_completed_badge_codes.return_value = frozenset()

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

        uc = EvaluateBadgeProgressQuery(
            progress_repo, ascent_repo, profile_repo, badge_repo, FakeClock(), AWARDING_SERVICE
        )
        result = uc.execute(profile_id=1, badge_code="KGP", cycle_number=1)

        assert result["verified"] is True
        assert result["status"] == "COMPLETED"
        # Ochrona CQS: Query absolutnie NICZEGO nie zapisuje! Aktualizuje stan UpdateBadgeProgressCommand.
        progress_repo.update_domain_status.assert_not_called()

    def test_execute_applies_cutoff_date_for_cycle_2(self) -> None:
        """Dla cyklu > 1, logi są odcinane po dacie zamknięcia poprzedniego cyklu (logistic_status_date)."""
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = 99
        progress.progress_id = 123
        progress.domain_status = "IN_PROGRESS"
        progress_repo.get_completed_badge_codes.return_value = frozenset()

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

        uc = EvaluateBadgeProgressQuery(
            progress_repo, ascent_repo, profile_repo, badge_repo, FakeClock(), AWARDING_SERVICE
        )
        uc.execute(profile_id=1, badge_code="KGP", cycle_number=2)

        ascent_repo.get_unconsumed_ascents.assert_called_once_with(1, "KGP", cutoff_date="2023-01-01")

    def test_execute_preserves_completed_status_from_history(self) -> None:
        """PRAWA NABYTE: Jeśli progress był COMPLETED, wymusza status COMPLETED nawet po zmianie profilu."""
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = 99
        progress.progress_id = 123
        progress.domain_status = "COMPLETED"
        progress_repo.get_progress.return_value = progress
        progress_repo.get_completed_badge_codes.return_value = frozenset()

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

        uc = EvaluateBadgeProgressQuery(
            progress_repo, ascent_repo, profile_repo, badge_repo, FakeClock(), AWARDING_SERVICE
        )
        result = uc.execute(profile_id=1, badge_code="KGP", cycle_number=1)

        assert result["verified"] is True
        assert result["status"] == "COMPLETED"
        assert result["errors"] == ["Wiek nie spełnia wymogów"]
        assert result["tiers"][0]["status"] == "IN_PROGRESS"


class TestEvaluateBadgeProgressQueryNoVersion:
    """Testy EvaluateBadgeProgressQuery gdy brakuje wersji odznaki."""

    def test_execute_raises_when_badge_version_not_found(self) -> None:
        """Podnosi ResourceNotFoundError gdy get_badge_version_by_id zwróci None."""
        progress_repo = MagicMock()
        progress = MagicMock()
        progress.version_id = 99
        progress_repo.get_progress.return_value = progress

        badge_repo = MagicMock()
        badge_repo.get_version_id_for_date.return_value = 99
        badge_repo.get_badge_version_by_id.return_value = None

        ascent_repo = MagicMock()
        profile_repo = MagicMock()

        uc = EvaluateBadgeProgressQuery(
            progress_repo, ascent_repo, profile_repo, badge_repo, FakeClock(), AWARDING_SERVICE
        )

        with pytest.raises(ResourceNotFoundError, match="Nie udało się odtworzyć struktury odznaki"):
            result = uc.execute(profile_id=1, badge_code="KGP", cycle_number=1)


class TestUpdateBadgeProgressCommand:
    """Testy UpdateBadgeProgressCommand."""

    def test_execute_returns_early_when_no_progress(self) -> None:
        """Zwraca None gdy nie istnieje postęp."""
        progress_repo = MagicMock()
        progress_repo.get_progress.return_value = None

        query_service = MagicMock()
        cmd = UpdateBadgeProgressCommand(query_service, progress_repo)

        result = cmd.execute(profile_id=1, badge_code="KGP", cycle_number=1)

        assert result is None
        query_service.execute.assert_not_called()
        progress_repo.update_domain_status.assert_not_called()

    def test_execute_updates_status_when_changed(self) -> None:
        """Aktualizuje status gdy się zmienił."""
        progress = MagicMock()
        progress.progress_id = 10
        progress.domain_status = "IN_PROGRESS"

        progress_repo = MagicMock()
        progress_repo.get_progress.return_value = progress

        query_service = MagicMock()
        query_service.execute.return_value = {"status": "COMPLETED"}

        cmd = UpdateBadgeProgressCommand(query_service, progress_repo)
        cmd.execute(profile_id=1, badge_code="KGP", cycle_number=1)

        progress_repo.update_domain_status.assert_called_once_with(10, "COMPLETED")

    def test_execute_does_not_update_when_status_unchanged(self) -> None:
        """Nie aktualizuje statusu gdy się nie zmienił."""
        progress = MagicMock()
        progress.progress_id = 10
        progress.domain_status = "IN_PROGRESS"

        progress_repo = MagicMock()
        progress_repo.get_progress.return_value = progress

        query_service = MagicMock()
        query_service.execute.return_value = {"status": "IN_PROGRESS"}

        cmd = UpdateBadgeProgressCommand(query_service, progress_repo)
        cmd.execute(profile_id=1, badge_code="KGP", cycle_number=1)

        progress_repo.update_domain_status.assert_not_called()
