"""Testy LogAscentUseCase dla US-C03 i Invariantów T-01, T-03, D-04."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from application.dto.ascent_dto import AscentInputDTO
from application.exceptions import BitemporalTimeError, ConflictError, UseCaseError
from application.use_cases.log_ascent import LogAscentUseCase
from tests.fakes.clock import FakeClock


def _dto(ascent_date: date) -> AscentInputDTO:
    """Buduje DTO logu wejścia."""
    return AscentInputDTO(peak_id=42, ascent_date=ascent_date)


def _use_case(
    *,
    lifespan: tuple[date | None, date | None] | None = (None, None),
) -> tuple[LogAscentUseCase, MagicMock, FakeClock]:
    """Buduje use case z mockowanym portem bazy i deterministycznym FakeClock."""
    ascent_repo = MagicMock()
    ascent_repo.get_object_lifespan.return_value = lifespan
    ascent_repo.ascent_exists.return_value = False  # Domyślnie brak duplikatu
    ascent_repo.save_ascent.return_value = 123

    # FakeClock domyślnie zatrzymuje czas na dacie 2024-06-15
    clock = FakeClock()

    return LogAscentUseCase(ascent_repo, clock), ascent_repo, clock


class TestLogAscentUseCase:
    """Testy logowania wejścia z walidacją bitemporalną i chronologiczną."""

    def test_saves_ascent_when_lifespan_allows_it(self) -> None:
        """Test poprawnego zapisu - data mieści się w życiu obiektu."""
        use_case, ascent_repo, clock = _use_case(
            lifespan=(date(2020, 1, 1), date(2030, 12, 31)),
        )

        ascent_id = use_case.execute(
            profile_id=1,
            dto=_dto(date(2024, 6, 1)),
        )

        assert ascent_id == 123
        ascent_repo.get_object_lifespan.assert_called_once_with(42)
        ascent_repo.save_ascent.assert_called_once_with(
            profile_id=1,
            peak_id=42,
            ascent_date=date(2024, 6, 1),
        )

    def test_raises_when_peak_does_not_exist(self) -> None:
        """Test braku obiektu w bazie danych."""
        use_case, ascent_repo, clock = _use_case(lifespan=None)

        with pytest.raises(UseCaseError, match="nie istnieje"):
            use_case.execute(profile_id=1, dto=_dto(date(2024, 6, 1)))

        ascent_repo.save_ascent.assert_not_called()

    def test_T01_rejects_ascent_before_object_existed(self) -> None:
        """Invariant T-01: Wejście przed zbudowaniem obiektu."""
        use_case, ascent_repo, clock = _use_case(
            lifespan=(date(2020, 1, 1), None),
        )

        with pytest.raises(BitemporalTimeError, match="Obiekt powstał 2020-01-01"):
            use_case.execute(profile_id=1, dto=_dto(date(2019, 12, 31)))

        ascent_repo.save_ascent.assert_not_called()

    def test_T01_rejects_ascent_after_object_stopped_existing(self) -> None:
        """Invariant T-01: Wejście po zniszczeniu obiektu."""
        use_case, ascent_repo, clock = _use_case(
            lifespan=(None, date(2023, 12, 31)),
        )

        with pytest.raises(BitemporalTimeError, match="przestał istnieć 2023-12-31"):
            use_case.execute(profile_id=1, dto=_dto(date(2024, 1, 1)))

        ascent_repo.save_ascent.assert_not_called()

    def test_allows_ascent_exactly_on_lifespan_boundaries(self) -> None:
        """Test wejścia dokładnie w dniu granicy bitemporalnej."""
        use_case, ascent_repo, clock = _use_case(
            lifespan=(date(2020, 1, 1), date(2020, 1, 1)),
        )

        # Odwiedziny w dzień otwarcia i zniszczenia jednocześnie
        ascent_id = use_case.execute(profile_id=1, dto=_dto(date(2020, 1, 1)))

        assert ascent_id == 123
        ascent_repo.save_ascent.assert_called_once()

    def test_T03_rejects_ascent_from_the_future(self) -> None:
        """Invariant T-03: Blokada wejść z przyszłości."""
        use_case, ascent_repo, clock = _use_case()

        # FakeClock domyślnie symuluje datę 2024-06-15.
        # Próbujemy zalogować wejście na dzień później (2024-06-16)
        with pytest.raises(UseCaseError, match="nie może być z przyszłości"):
            use_case.execute(profile_id=1, dto=_dto(date(2024, 6, 16)))

        ascent_repo.save_ascent.assert_not_called()

    def test_D04_rejects_duplicate_ascent(self) -> None:
        """Invariant D-04: Idempotentność zapisu (blokada dubli)."""
        use_case, ascent_repo, clock = _use_case()

        # Symulujemy, że baza danych potwierdza istnienie logu
        ascent_repo.ascent_exists.return_value = True

        with pytest.raises(ConflictError, match="zostało już wcześniej zalogowane"):
            use_case.execute(profile_id=1, dto=_dto(date(2024, 6, 1)))

        ascent_repo.save_ascent.assert_not_called()
