"""Shared pytest fixtures and test configuration.

Per AUDYT-063: centralises common mock objects so individual test modules
do not need to redefine (or import-copy) them.
"""

import pytest

from tests.fakes.clock import FakeClock
from tests.fakes.mocks import MockEventPublisher, MockUnitOfWork


@pytest.fixture
def fake_clock() -> FakeClock:
    """Deterministic clock aligned with FakeClock.DEFAULT_TIME."""
    return FakeClock()


@pytest.fixture
def mock_uow() -> MockUnitOfWork:
    """No-op Unit of Work mock for Use Case tests that don't need persistence."""
    return MockUnitOfWork()


@pytest.fixture
def mock_event_publisher() -> MockEventPublisher:
    """Null object event publisher that silently swallows events."""
    return MockEventPublisher()
