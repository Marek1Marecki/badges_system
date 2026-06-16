"""Tests for WSGI configuration."""

import os


class TestWSGIConfig:
    """Test suite for WSGI configuration."""

    def test_wsgi_application_exists(self):
        """Test that WSGI application can be imported."""
        from config.wsgi import application

        assert application is not None

    def test_django_settings_module_set(self):
        """Test that DJANGO_SETTINGS_MODULE is set correctly."""

        assert os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings"
