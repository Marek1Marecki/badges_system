"""Tests for log_config."""

from infrastructure.logging.log_config import configure_logging


class TestConfigureLogging:
    """Test configure_logging function."""

    def test_configure_logging_with_json_mode(self):
        """Test configure_logging with json_mode=True."""
        # This should not raise an exception
        configure_logging(json_mode=True, level="INFO")

    def test_configure_logging_with_development_mode(self):
        """Test configure_logging with json_mode=False."""
        # This should not raise an exception
        configure_logging(json_mode=False, level="INFO")

    def test_configure_logging_with_different_levels(self):
        """Test configure_logging with different log levels."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        for level in levels:
            configure_logging(json_mode=False, level=level)

    def test_configure_logging_default_parameters(self):
        """Test configure_logging with default parameters."""
        # This should not raise an exception
        configure_logging()

    def test_configure_logging_overwrites_previous_config(self):
        """Test that configure_logging overwrites previous configuration."""
        # First configuration
        configure_logging(json_mode=False, level="INFO")
        # Second configuration should overwrite
        configure_logging(json_mode=True, level="DEBUG")
