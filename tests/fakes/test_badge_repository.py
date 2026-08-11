"""Testy jednostkowe dla FakeBadgeRepository."""

from datetime import date

from domain.entities.badge_version import BadgeVersionDomain
from tests.fakes.badge_repository import FakeBadgeRepository


def test_fake_badge_repository_adds_and_gets_badge() -> None:
    """Sprawdza, czy fake repozytorium poprawnie zapisuje i zwraca wersje."""
    repo = FakeBadgeRepository()

    # Repozytorium jest na starcie puste
    assert repo.get_badge_version("KGP", "v1") is None

    # Dodajemy odznakę na sztywno
    repo.add(code="KGP", version="v1")

    badge = repo.get_badge_version("KGP", "v1")
    assert isinstance(badge, BadgeVersionDomain)
    assert badge.tiers[0].required_count == 1  # Domyślny wymóg z Fake'a

    # Wyszukiwanie po id wygenerowanym z automatu (id = 1)
    badge_by_id = repo.get_badge_version_by_id(1)
    assert badge_by_id is not None
    assert badge_by_id.version_id == 1


def test_fake_badge_repository_gets_version_for_date() -> None:
    """Sprawdza, czy wyszukiwanie wersji po dacie zawraca pierwsze pasujące ID."""
    repo = FakeBadgeRepository()
    repo.add(code="KGP", version="v1")

    version_id = repo.get_version_id_for_date("KGP", date(2025, 1, 1))
    assert version_id == 1

    # Dla nieznanej odznaki
    assert repo.get_version_id_for_date("INNA", date(2025, 1, 1)) is None


def test_fake_badge_repository_handles_string_version_id() -> None:
    """Sprawdza, czy fake obsługuje nie-intowe version_id."""
    repo = FakeBadgeRepository()
    badge = BadgeVersionDomain(
        version_id="v-string",
        rules=[],
        pool_peak_ids=frozenset(),
        tiers=[],
    )
    repo.add(code="KGP", version="v1", badge=badge)

    badge_by_id = repo.get_badge_version_by_id(1)
    assert badge_by_id is not None
    assert badge_by_id.version_id == "v-string"


def test_fake_badge_repository_clear_and_len() -> None:
    """Sprawdza, czy clear i __len__ działają poprawnie."""
    repo = FakeBadgeRepository()
    repo.add(code="KGP", version="v1")
    repo.add(code="KGP", version="v2")

    assert len(repo) == 2

    repo.clear()
    assert len(repo) == 0
    assert repo.get_badge_version("KGP", "v1") is None
