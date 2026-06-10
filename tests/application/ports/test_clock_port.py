"""Testy dla ClockPort."""

from datetime import datetime

from application.ports.clock_port import ClockPort


def test_clock_port_is_protocol():
    """Test że ClockPort jest protokołem."""
    # ClockPort to Protocol, więc testujemy tylko że interfejs istnieje
    assert hasattr(ClockPort, "now")
    assert callable(ClockPort.now)


def test_clock_port_now_returns_datetime():
    """Test że metoda now zwraca datetime."""
    # Testujemy tylko sygnaturę - implementacja w FakeClock
    assert ClockPort.now.__annotations__.get("return") == datetime
