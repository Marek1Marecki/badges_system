"""Testy jednostkowe dla FakeClock.

FakeClock jest używany we wszystkich testach use case'ów wymagających czasu.
Te testy weryfikują że sam FakeClock działa poprawnie jako narzędzie testowe.
"""

from datetime import UTC, datetime, timedelta

from tests.fakes.clock import FakeClock


class TestFakeClock:
    """Testy FakeClock — deterministycznego dostawcy czasu."""

    def test_returns_default_time_when_no_time_given(self) -> None:
        """Zwraca domyślny czas gdy nie podano czasu."""
        clock = FakeClock()
        assert clock.now() == FakeClock.DEFAULT_TIME

    def test_returns_fixed_time_when_given(self) -> None:
        """Zwraca podany stały czas."""
        fixed = datetime(2025, 1, 15, 8, 30, 0, tzinfo=UTC)
        clock = FakeClock(fixed_time=fixed)
        assert clock.now() == fixed

    def test_now_is_deterministic(self) -> None:
        """Wielokrotne wywołania zwracają ten sam czas."""
        clock = FakeClock()
        first = clock.now()
        second = clock.now()
        assert first == second

    def test_returned_datetime_has_timezone(self) -> None:
        """Zwrócony datetime ma strefę czasową."""
        clock = FakeClock()
        result = clock.now()
        assert result.tzinfo is not None

    def test_advance_moves_clock_forward(self) -> None:
        """advance przesuwa zegar do przodu."""
        clock = FakeClock()
        original = clock.now()
        clock.advance(hours=2)
        assert clock.now() == original + timedelta(hours=2)

    def test_advance_with_days(self) -> None:
        """advance działa z parametrem days."""
        clock = FakeClock()
        original = clock.now()
        clock.advance(days=7)
        assert clock.now() == original + timedelta(days=7)

    def test_advance_accumulates(self) -> None:
        """Kolejne wywołania advance sumują się."""
        clock = FakeClock()
        original = clock.now()
        clock.advance(hours=1)
        clock.advance(hours=1)
        assert clock.now() == original + timedelta(hours=2)

    def test_default_time_is_utc(self) -> None:
        """Domyślny czas jest w strefie UTC."""
        assert FakeClock.DEFAULT_TIME.tzinfo == UTC
