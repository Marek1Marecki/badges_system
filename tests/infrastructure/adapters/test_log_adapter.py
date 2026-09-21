"""Testy dla LoguruLoggingAdapter."""

from unittest.mock import MagicMock

import pytest

from infrastructure.adapters.log_adapter import LoguruLoggingAdapter


class TestLoguruLoggingAdapter:
    """Testy adaptera logowania Loguru."""

    @pytest.fixture
    def adapter(self):
        return LoguruLoggingAdapter()

    def test_info_without_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.info("test message")
            mock_logger.info.assert_called_once_with("test message")

    def test_info_with_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.info("test %s", "message")
            mock_logger.info.assert_called_once_with("test %s", "message")

    def test_warning_without_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.warning("test message")
            mock_logger.warning.assert_called_once_with("test message")

    def test_warning_with_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.warning("test %s", "message")
            mock_logger.warning.assert_called_once_with("test %s", "message")

    def test_error_without_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.error("test message")
            mock_logger.error.assert_called_once_with("test message")

    def test_error_with_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.error("test %s", "message")
            mock_logger.error.assert_called_once_with("test %s", "message")

    def test_debug_without_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.debug("test message")
            mock_logger.debug.assert_called_once_with("test message")

    def test_debug_with_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.debug("test %s", "message")
            mock_logger.debug.assert_called_once_with("test %s", "message")

    def test_exception_without_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.exception("test message")
            mock_logger.opt.assert_called_once_with(exception=True)
            mock_logger.opt.return_value.error.assert_called_once_with("test message")

    def test_exception_with_args(self, adapter):
        with pytest.MonkeyPatch.context() as m:
            mock_logger = MagicMock()
            m.setattr("infrastructure.adapters.log_adapter.logger", mock_logger)
            adapter.exception("test %s", "message")
            mock_logger.opt.assert_called_once_with(exception=True)
            mock_logger.opt.return_value.error.assert_called_once_with("test %s", "message")
