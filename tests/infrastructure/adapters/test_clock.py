"""Tests for SystemClock adapter."""

from datetime import UTC, datetime

from infrastructure.adapters.clock import SystemClock


class TestSystemClock:
    """Test suite for SystemClock."""

    def test_now_returns_datetime(self):
        """Test that now() returns a datetime object."""
        clock = SystemClock()
        result = clock.now()
        assert isinstance(result, datetime)

    def test_now_returns_utc_time(self):
        """Test that now() returns time in UTC timezone."""
        clock = SystemClock()
        result = clock.now()
        assert result.tzinfo == UTC

    def test_now_is_recent(self):
        """Test that now() returns current time (within 5s tolerance for CI load)."""
        clock = SystemClock()
        result = clock.now()
        now = datetime.now(UTC)
        difference = abs((result - now).total_seconds())
        assert difference < 5.0
