"""Testy dla context processors turysty."""

from unittest.mock import MagicMock


class TestTouristProfilesContextProcessor:
    def test_returns_empty_dict_for_unauthenticated_user(self):
        """Zwraca pusty słownik dla nieuwierzytelnionego użytkownika."""
        from apps.tourists.context_processors import tourist_profiles

        request = MagicMock()
        request.user.is_authenticated = False

        result = tourist_profiles(request)

        assert result == {}
