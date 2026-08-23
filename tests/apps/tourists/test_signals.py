"""Testy dla sygnałów turystycznych."""

from unittest.mock import MagicMock, patch

from apps.tourists.signals import create_tourist_profile


class TestCreateTouristProfileSignal:
    """Testy sygnału create_tourist_profile."""

    @patch("apps.tourists.signals.TouristProfile.objects.create")
    def test_creates_profile_on_user_created(self, mock_create):
        """Tworzy profil po utworzeniu użytkownika."""
        user = MagicMock()
        user.email = "test@example.com"
        user.id = 1

        create_tourist_profile(MagicMock(), user, created=True)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["user"] == user
        assert call_kwargs["active_plan"] == "FREE"
        assert call_kwargs["max_active_badges"] == 3
        assert call_kwargs["nickname"] == "test_1"

    @patch("apps.tourists.signals.TouristProfile.objects.create")
    def test_creates_profile_with_none_email(self, mock_create):
        """Tworzy profil gdy użytkownik nie ma e-maila."""
        user = MagicMock()
        user.email = None
        user.id = 42

        create_tourist_profile(MagicMock(), user, created=True)

        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["nickname"] == "user_42_42"

    @patch("apps.tourists.signals.TouristProfile.objects.create")
    def test_does_not_create_on_update(self, mock_create):
        """Nie tworzy profilu przy aktualizacji użytkownika."""
        user = MagicMock()

        create_tourist_profile(MagicMock(), user, created=False)

        mock_create.assert_not_called()
