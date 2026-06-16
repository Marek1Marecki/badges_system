"""Tests for ASGI configuration."""

import os


class TestASGIConfig:
    """Test suite for ASGI configuration."""

    def test_asgi_application_exists(self):
        """Test that ASGI application can be imported."""
        from config.asgi import application

        assert application is not None

    def test_django_settings_module_set(self):
        """Test that DJANGO_SETTINGS_MODULE is set correctly."""

        assert os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings"
