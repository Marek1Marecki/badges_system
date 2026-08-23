"""Testy dla DjangoUnitOfWork."""

from unittest.mock import MagicMock, patch

from infrastructure.adapters.django_uow import DjangoUnitOfWork


class TestDjangoUnitOfWork:
    """Testy DjangoUnitOfWork."""

    def test_enter_returns_uow_instance(self):
        """__enter__ zwraca instancję UoW."""
        uow = DjangoUnitOfWork()
        with patch("django.db.transaction.atomic") as mock_atomic:
            mock_atomic.return_value = MagicMock()
            result = uow.__enter__()

        assert result is uow

    def test_exit_without_exception_commits(self):
        """__exit__ bez wyjątku commituje transakcję."""
        uow = DjangoUnitOfWork()
        mock_atomic = MagicMock()
        uow._atomic = mock_atomic

        uow.__exit__(None, None, None)

        mock_atomic.__exit__.assert_called_once_with(None, None, None)

    def test_exit_with_exception_propagates(self):
        """__exit__ z wyjątkiem propaguje rollback."""
        uow = DjangoUnitOfWork()
        mock_atomic = MagicMock()
        uow._atomic = mock_atomic

        exc_type = ValueError
        exc_val = ValueError("test error")
        exc_tb = MagicMock()

        uow.__exit__(exc_type, exc_val, exc_tb)

        mock_atomic.__exit__.assert_called_once_with(exc_type, exc_val, exc_tb)
