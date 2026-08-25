"""Testy jednostkowe dla procesu subskrypcji i praw nabytych."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from application.exceptions import UseCaseError
from application.use_cases.start_badge_progress import StartBadgeProgressUseCase
from tests.fakes.clock import FakeClock
from tests.fakes.user_progress_repository import FakeTouristRepository


class MockUnitOfWork:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockEventPublisher:
    def publish(self, event):
        pass


class TestStartBadgeProgressUseCase:
    """Testuje logikę zakotwiczania regulaminu (US-C05) i limitów (US-C01c)."""

    def test_starts_progress_with_current_date_when_no_ascents(self) -> None:
        """Używa bieżącej daty gdy brak wcześniejszych wejść."""
        repo = FakeTouristRepository()
        # Zabezpieczenie przed limitem Freemium
        repo.profiles[1] = MagicMock(max_active_badges=10, active_plan="PRO")

        badge_repo = MagicMock()
        badge_repo.get_version_id_for_date.return_value = 42
        clock = FakeClock()
        uow = MockUnitOfWork()
        event_publisher = MockEventPublisher()

        uc = StartBadgeProgressUseCase(
            progress_repository=repo,
            ascent_repository=repo,
            profile_repository=repo,  # <--- DODANO WSTRZYKNIĘCIE PROFILU
            badge_repository=badge_repo,
            clock=clock,
            uow=uow,
            event_publisher=event_publisher,
        )

        progress_id = uc.execute(profile_id=1, badge_code="KGP")

        assert progress_id == 1
        assert repo.progresses[1].version_id == 42
        badge_repo.get_version_id_for_date.assert_called_once_with("KGP", clock.now().date())

    def test_starts_progress_with_oldest_ascent_date_grandfathering(self) -> None:
        """Używa daty najstarszego wejścia (grandfathering)."""
        repo = FakeTouristRepository()
        repo.profiles[1] = MagicMock(max_active_badges=10)
        repo.save_ascent(1, 10, date(2015, 6, 1))

        badge_repo = MagicMock()
        badge_repo.get_version_id_for_date.return_value = 10
        clock = FakeClock()
        uow = MockUnitOfWork()
        event_publisher = MockEventPublisher()

        uc = StartBadgeProgressUseCase(repo, repo, badge_repo, repo, clock, uow, event_publisher)  # 3x repo

        progress_id = uc.execute(profile_id=1, badge_code="KGP")

        badge_repo.get_version_id_for_date.assert_called_once_with("KGP", date(2015, 6, 1))
        assert repo.progresses[progress_id].version_id == 10

    def test_raises_error_when_no_version_exists(self) -> None:
        """Rzuca błąd gdy brak wersji regulaminu."""
        repo = FakeTouristRepository()
        repo.profiles[1] = MagicMock(max_active_badges=10)

        badge_repo = MagicMock()
        badge_repo.get_version_id_for_date.return_value = None

        uc = StartBadgeProgressUseCase(
            repo, repo, badge_repo, repo, FakeClock(), MockUnitOfWork(), MockEventPublisher()
        )

        with pytest.raises(UseCaseError, match="Brak opublikowanej wersji regulaminu"):
            uc.execute(profile_id=1, badge_code="KGP")

    def test_raises_error_when_freemium_limit_exceeded(self) -> None:
        """Rzuca błąd gdy przekroczono limit Freemium."""
        repo = FakeTouristRepository()
        # Turysta ma limit 1 odznaki
        repo.profiles[1] = MagicMock(max_active_badges=1, active_plan="FREE")
        # I symulujemy, że już zdobywa jedną odznakę
        repo.start_progress(profile_id=1, badge_code="INNA_ODZNAKA", version_id=99, cycle_number=1)

        badge_repo = MagicMock()
        badge_repo.get_version_id_for_date.return_value = 42

        uc = StartBadgeProgressUseCase(
            repo, repo, badge_repo, repo, FakeClock(), MockUnitOfWork(), MockEventPublisher()
        )

        with pytest.raises(UseCaseError, match="Przekroczono limit pakietu"):
            uc.execute(profile_id=1, badge_code="KGP")

    def test_raises_error_when_profile_not_found(self) -> None:
        """Rzuca błąd gdy profil nie istnieje."""
        repo = FakeTouristRepository()
        badge_repo = MagicMock()
        badge_repo.get_version_id_for_date.return_value = 42

        uc = StartBadgeProgressUseCase(
            repo, repo, badge_repo, repo, FakeClock(), MockUnitOfWork(), MockEventPublisher()
        )

        with pytest.raises(UseCaseError, match="Nie znaleziono profilu o ID 999"):
            uc.execute(profile_id=999, badge_code="KGP")
