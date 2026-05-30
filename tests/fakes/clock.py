"""FakeClock — kontrolowany dostawca czasu do testów jednostkowych.

Zgodnie z 17-determinism-contract.md:
- Testy jednostkowe nie zależą od zegara systemowego
- Ten sam input zawsze daje ten sam output
- FakeClock może być przestawiony na dowolny moment w czasie

Użycie:
    clock = FakeClock(datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc))
    use_case = SomeUseCase(clock=clock)
    result = use_case.execute(...)
    assert result.timestamp == datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc)
"""

from datetime import UTC, datetime


class FakeClock:
    """Deterministyczny dostawca czasu do testów.

    Zwraca stały, z góry ustalony czas — niezależnie od tego kiedy
    test jest uruchamiany (pora dnia, strefa czasowa, CI vs lokalnie).
    """

    DEFAULT_TIME = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)

    def __init__(self, fixed_time: datetime | None = None) -> None:
        """Inicjalizuje FakeClock z podanym lub domyślnym czasem.

        Args:
            fixed_time: Czas który clock będzie zawsze zwracał.
                        Musi mieć tzinfo. Jeśli None — używa DEFAULT_TIME.
        """
        self._time = fixed_time or self.DEFAULT_TIME

    def now(self) -> datetime:
        """Zwraca ustalony czas — zawsze ten sam."""
        return self._time

    def advance(self, **kwargs) -> None:
        """Przesuwa zegar do przodu o podany czas.

        Args:
            **kwargs: Argumenty przekazywane do timedelta (seconds, minutes,
                      hours, days itp.)

        Przykład:
            clock = FakeClock()
            clock.advance(hours=2)
            assert clock.now() == FakeClock.DEFAULT_TIME + timedelta(hours=2)
        """
        from datetime import timedelta

        self._time = self._time + timedelta(**kwargs)
