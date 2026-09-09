"""Shared pytest fixtures and test configuration.

Per AUDYT-063: centralises common mock objects so individual test modules
do not need to redefine (or import-copy) them.
"""

import pytest

from tests.fakes.clock import FakeClock
from tests.fakes.mocks import MockEventPublisher, MockUnitOfWork


@pytest.fixture(autouse=True)
def _reset_request_context():
    """AUDYT-117: Reset ContextVar (request_id) między testami.

    pytest-randomly może przypadkowo wykonać test ustawiający ContextVar
    przed testem, który zakłada czysty stan. Ten fixture gwarantuje,
    że każdy test zaczyna z `request_id=None`.
    """
    from infrastructure.request_context import set_request_id

    set_request_id(None)
    yield
    set_request_id(None)


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
