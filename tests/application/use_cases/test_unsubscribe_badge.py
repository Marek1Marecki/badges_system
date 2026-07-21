"""Testy jednostkowe dla procesu rezygnacji z odznaki (Unsubscribe)."""

import pytest

from application.exceptions import ConflictError, UseCaseError
from application.use_cases.unsubscribe_badge import UnsubscribeBadgeUseCase
from tests.fakes.user_progress_repository import FakeTouristRepository


class MockUnitOfWork:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockEventPublisher:
    def publish(self, event):
        pass


class TestUnsubscribeBadgeUseCase:
    """Testuje logikę usuwania subskrypcji i zwolnienia limitu Freemium."""

    def test_deletes_progress_when_subscribed(self) -> None:
        """Turysta może porzucić odznakę, jeśli nie jest jeszcze ukończona."""
        repo = FakeTouristRepository()
        repo.start_progress(profile_id=1, badge_code="KGP", version_id=42, cycle_number=1)

        uc = UnsubscribeBadgeUseCase(
            progress_repository=repo, uow=MockUnitOfWork(), event_publisher=MockEventPublisher()
        )
        uc.execute(profile_id=1, badge_code="KGP")

        assert repo.progresses.get((1, "KGP", 1)) is None

    def test_raises_error_when_not_subscribed(self) -> None:
        """Turysta nie może porzucić odznaki, której nie subskrybuje."""
        repo = FakeTouristRepository()

        uc = UnsubscribeBadgeUseCase(
            progress_repository=repo, uow=MockUnitOfWork(), event_publisher=MockEventPublisher()
        )

        with pytest.raises(UseCaseError, match="Nie subskrybujesz odznaki KGP"):
            uc.execute(profile_id=1, badge_code="KGP")

    def test_raises_error_when_already_completed(self) -> None:
        """Turysta nie może porzucić odznaki, która została już ukończona."""
        repo = FakeTouristRepository()
        progress_id = repo.start_progress(profile_id=1, badge_code="KGP", version_id=42, cycle_number=1)
        repo.update_domain_status(progress_id, "COMPLETED")

        uc = UnsubscribeBadgeUseCase(
            progress_repository=repo, uow=MockUnitOfWork(), event_publisher=MockEventPublisher()
        )

        with pytest.raises(ConflictError, match="Nie można porzucić odznaki, która została ukończona"):
            uc.execute(profile_id=1, badge_code="KGP")

    def test_deletes_progress_for_different_cycles(self) -> None:
        """Turysta może porzucić odznakę w konkretnym cyklu."""
        repo = FakeTouristRepository()
        repo.start_progress(profile_id=1, badge_code="KGP", version_id=42, cycle_number=1)
        repo.start_progress(profile_id=1, badge_code="KGP", version_id=43, cycle_number=2)

        uc = UnsubscribeBadgeUseCase(
            progress_repository=repo, uow=MockUnitOfWork(), event_publisher=MockEventPublisher()
        )
        uc.execute(profile_id=1, badge_code="KGP")

        # Oba postępy powinny zostać usunięte (unsubscribe usuwa po badge_code, nie po cycle)
        assert repo.progresses.get((1, "KGP", 1)) is None
        assert repo.progresses.get((1, "KGP", 2)) is None
