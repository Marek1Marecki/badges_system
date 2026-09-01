"""Shared mock objects for unit tests.

These lightweight fakes replace database-backed or infrastructure components
when testing Use Cases in complete isolation.  Centralising them here (per
AUDYT-063) avoids the "shotgun copy-paste" of identical definitions across
multiple test modules.
"""


class MockUnitOfWork:
    """Minimal Unit of Work mock — acts as a no-op context manager."""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockEventPublisher:
    """Null object for event publishing; events are silently swallowed."""

    def publish(self, event):
        pass
