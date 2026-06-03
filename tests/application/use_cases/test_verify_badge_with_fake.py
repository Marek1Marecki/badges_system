"""Testy VerifyBadgeUseCase z FakeBadgeRepository.

Zgodnie z TEST_STRATEGY.md — testy jednostkowe bez bazy danych.
FakeBadgeRepository zastępuje DjangoBadgeRepository — zero I/O.

Protokół mutacyjny (TEST_STRATEGY.md):
- test_badge_not_found: obleje gdy use case nie sprawdza None z repozytorium
- test_verify_returns_false_when_validation_fails: obleje gdy ValidationError
  nie jest tłumaczony na wynik biznesowy
- test_verify_returns_true_when_all_peaks_visited: obleje gdy evaluate()
  nie akceptuje poprawnych wejść
"""

from datetime import date
from unittest.mock import MagicMock

import pytest

from application.dto.ascent_dto import AscentInputDTO, VerifyBadgeRequestDTO
from application.exceptions import UseCaseError
from application.use_cases.verify_badge import VerifyBadgeUseCase
from tests.fakes.badge_repository import FakeBadgeRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo() -> FakeBadgeRepository:
    """Świeże, puste repozytorium dla każdego testu."""
    return FakeBadgeRepository()


@pytest.fixture
def use_case(repo: FakeBadgeRepository) -> VerifyBadgeUseCase:
    """Use case z wstrzykniętym fake repozytorium."""
    return VerifyBadgeUseCase(repository=repo)


def _make_ascent_dto(peak_id: int, ascent_date: date | None = None) -> AscentInputDTO:
    """Fabryka AscentDTO z sensownymi wartościami domyślnymi."""
    return AscentInputDTO(
        peak_id=peak_id,
        ascent_date=ascent_date or date(2024, 7, 15),
        activity="HIKING",
    )


def _make_request(
    badge_code: str = "TEST",
    version_code: str = "2024",
    ascents: list[AscentInputDTO] | None = None,
) -> VerifyBadgeRequestDTO:
    """Fabryka VerifyBadgeRequestDTO."""
    return VerifyBadgeRequestDTO(
        badge_code=badge_code,
        version_code=version_code,
        ascents=ascents or [],
    )


# ---------------------------------------------------------------------------
# Testy: badge not found
# ---------------------------------------------------------------------------

class TestVerifyBadgeNotFound:
    """Use case rzuca UseCaseError gdy odznaka nie istnieje."""

    def test_raises_when_badge_code_not_in_repo(
        self, use_case: VerifyBadgeUseCase
    ) -> None:
        request = _make_request(badge_code="NIEISTNIEJACA", version_code="2024")
        with pytest.raises(UseCaseError, match="NIEISTNIEJACA"):
            use_case.execute(request)

    def test_raises_when_version_code_not_in_repo(
        self, use_case: VerifyBadgeUseCase, repo: FakeBadgeRepository
    ) -> None:
        badge_version = MagicMock()
        repo.add(badge_version, code="KGP", version="2024")

        request = _make_request(badge_code="KGP", version_code="INNA_WERSJA")
        with pytest.raises(UseCaseError, match="KGP"):
            use_case.execute(request)

    def test_error_message_contains_badge_code(
        self, use_case: VerifyBadgeUseCase
    ) -> None:
        request = _make_request(badge_code="KGP", version_code="2024")
        with pytest.raises(UseCaseError) as exc_info:
            use_case.execute(request)
        assert "KGP" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Testy: weryfikacja pozytywna
# ---------------------------------------------------------------------------

class TestVerifyBadgeSuccess:
    """Use case zwraca verified=True gdy reguły są spełnione."""

    def test_returns_verified_true_when_evaluate_passes(
        self, use_case: VerifyBadgeUseCase, repo: FakeBadgeRepository
    ) -> None:
        badge_version = MagicMock()
        badge_version.evaluate.return_value = None  # brak wyjątku = sukces
        repo.add(badge_version, code="TEST", version="2024")

        request = _make_request(ascents=[_make_ascent_dto(peak_id=1)])
        result = use_case.execute(request)

        assert result["verified"] is True
        assert "Gratulacje" in str(result["message"])

    def test_evaluate_called_with_domain_ascents(
        self, use_case: VerifyBadgeUseCase, repo: FakeBadgeRepository
    ) -> None:
        """Use case konwertuje DTO na obiekty domenowe przed przekazaniem do evaluate."""
        badge_version = MagicMock()
        repo.add(badge_version, code="TEST", version="2024")

        ascents = [_make_ascent_dto(peak_id=1), _make_ascent_dto(peak_id=2)]
        request = _make_request(ascents=ascents)
        use_case.execute(request)

        badge_version.evaluate.assert_called_once()
        domain_ascents = badge_version.evaluate.call_args[0][0]
        assert len(domain_ascents) == 2
        # Sprawdzamy że to obiekty domenowe, nie DTO
        assert hasattr(domain_ascents[0], "peak_id")
        assert hasattr(domain_ascents[0], "ascent_date")

    def test_empty_ascents_list_is_passed_to_evaluate(
        self, use_case: VerifyBadgeUseCase, repo: FakeBadgeRepository
    ) -> None:
        badge_version = MagicMock()
        repo.add(badge_version, code="TEST", version="2024")

        request = _make_request(ascents=[])
        use_case.execute(request)

        badge_version.evaluate.assert_called_once_with([])


# ---------------------------------------------------------------------------
# Testy: weryfikacja negatywna
# ---------------------------------------------------------------------------

class TestVerifyBadgeFailure:
    """Use case zwraca verified=False gdy reguły nie są spełnione."""

    def test_returns_verified_false_when_validation_error(
        self, use_case: VerifyBadgeUseCase, repo: FakeBadgeRepository
    ) -> None:
        from domain.exceptions import ValidationError

        badge_version = MagicMock()
        badge_version.evaluate.side_effect = ValidationError("Za mało szczytów")
        repo.add(badge_version, code="TEST", version="2024")

        request = _make_request(ascents=[_make_ascent_dto(peak_id=1)])
        result = use_case.execute(request)

        assert result["verified"] is False
        assert "Za mało szczytów" in str(result["message"])

    def test_validation_error_message_is_preserved(
        self, use_case: VerifyBadgeUseCase, repo: FakeBadgeRepository
    ) -> None:
        from domain.exceptions import ValidationError

        badge_version = MagicMock()
        badge_version.evaluate.side_effect = ValidationError("Wymagana aktywność: HIKING")
        repo.add(badge_version, code="TEST", version="2024")

        result = use_case.execute(_make_request())

        assert "Wymagana aktywność: HIKING" in str(result["message"])


# ---------------------------------------------------------------------------
# Testy: FakeBadgeRepository
# ---------------------------------------------------------------------------

class TestFakeBadgeRepository:
    """Testy samego FakeBadgeRepository — weryfikacja narzędzia testowego."""

    def test_returns_none_for_unknown_badge(self) -> None:
        repo = FakeBadgeRepository()
        assert repo.get_badge_version("BRAK", "2024") is None

    def test_returns_added_badge_version(self) -> None:
        repo = FakeBadgeRepository()
        badge_version = MagicMock()
        repo.add(badge_version, code="KGP", version="2024")
        assert repo.get_badge_version("KGP", "2024") is badge_version

    def test_different_versions_are_independent(self) -> None:
        repo = FakeBadgeRepository()
        v2024 = MagicMock()
        v2025 = MagicMock()
        repo.add(v2024, code="KGP", version="2024")
        repo.add(v2025, code="KGP", version="2025")

        assert repo.get_badge_version("KGP", "2024") is v2024
        assert repo.get_badge_version("KGP", "2025") is v2025

    def test_clear_removes_all_entries(self) -> None:
        repo = FakeBadgeRepository()
        repo.add(MagicMock(), code="KGP", version="2024")
        repo.clear()
        assert repo.get_badge_version("KGP", "2024") is None

    def test_len_returns_number_of_stored_versions(self) -> None:
        repo = FakeBadgeRepository()
        assert len(repo) == 0
        repo.add(MagicMock(), code="KGP", version="2024")
        repo.add(MagicMock(), code="DPG", version="2024")
        assert len(repo) == 2