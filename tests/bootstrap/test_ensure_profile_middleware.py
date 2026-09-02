"""Testy dla EnsureTouristProfileMiddleware (AUDYT-126).

Weryfikuje, że proces tworzenia profilu został przeniesiony z widoków
do middleware — eliminując hidden write w funkcjach typu getter.

Strategia: RequestFactory + MagicMock user + mockowanie ``TouristProfile.objects``.
Testy są czystymi testami jednostkowymi (brak ``@pytest.mark.django_db``),
zgodnie z patternem w ``tests/apps/tourists/test_signals.py``.
"""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, PropertyMock, patch

from bootstrap.middleware import EnsureTouristProfileMiddleware


class TestEnsureTouristProfileMiddleware:
    """Testy zapewniające brak mutacji w getterze _get_active_profile_id."""

    @staticmethod
    @contextmanager
    def _noop_atomic():
        yield

    @staticmethod
    def _make_middleware() -> EnsureTouristProfileMiddleware:
        return EnsureTouristProfileMiddleware(get_response=lambda r: None)

    def test_anonymous_user_no_profile_created(self):
        """Dla nieautoryzowanego użytkownika nie tworzy profilu."""
        middleware = self._make_middleware()
        request = MagicMock()
        request.user = MagicMock()
        type(request.user).is_authenticated = PropertyMock(return_value=False)
        request.session = {}

        middleware.process_request(request)

        assert request.session.get("active_profile_id") is None

    @patch("bootstrap.middleware.transaction.atomic", _noop_atomic)
    @patch("bootstrap.middleware.TouristProfile")
    def test_authenticated_user_without_profile_creates_one(self, mock_profile_cls):
        """Dla autoryzowanego użytkownika bez profilu — tworzy go."""
        mock_profile = MagicMock()
        mock_profile.id = 42
        mock_profile_cls.objects.filter.return_value.first.return_value = None
        mock_profile_cls.objects.create.return_value = mock_profile

        middleware = self._make_middleware()
        user = MagicMock()
        type(user).is_authenticated = PropertyMock(return_value=True)
        user.email = "test@example.com"
        user.id = 1

        request = MagicMock()
        request.user = user
        request.session = {}

        middleware.process_request(request)

        mock_profile_cls.objects.create.assert_called_once()
        call_kwargs = mock_profile_cls.objects.create.call_args[1]
        assert call_kwargs["user"] == user
        assert call_kwargs["is_main_profile"] is True
        assert request.session["active_profile_id"] == 42

    @patch("bootstrap.middleware.transaction.atomic", _noop_atomic)
    @patch("bootstrap.middleware.TouristProfile")
    def test_authenticated_user_with_existing_session_no_creation(self, mock_profile_cls):
        """Jeśli sesja już ma active_profile_id — nie wywołuje filter ani create."""
        middleware = self._make_middleware()
        user = MagicMock()
        type(user).is_authenticated = PropertyMock(return_value=True)

        request = MagicMock()
        request.user = user
        request.session = {"active_profile_id": 99}

        middleware.process_request(request)

        mock_profile_cls.objects.filter.assert_not_called()
        mock_profile_cls.objects.create.assert_not_called()

    @patch("bootstrap.middleware.transaction.atomic", _noop_atomic)
    @patch("bootstrap.middleware.TouristProfile")
    def test_authenticated_user_with_existing_profile_no_duplication(self, mock_profile_cls):
        """Użytkownik z profilem — filter znajduje go, nie tworzy duplikatu."""
        mock_profile = MagicMock()
        mock_profile.id = 77
        mock_profile_cls.objects.filter.return_value.first.return_value = mock_profile

        middleware = self._make_middleware()
        user = MagicMock()
        type(user).is_authenticated = PropertyMock(return_value=True)
        user.email = "user@example.com"
        user.id = 3

        request = MagicMock()
        request.user = user
        request.session = {}

        middleware.process_request(request)

        mock_profile_cls.objects.filter.assert_called_once()
        mock_profile_cls.objects.create.assert_not_called()
        assert request.session["active_profile_id"] == 77

    @patch("bootstrap.middleware.transaction.atomic", _noop_atomic)
    @patch("bootstrap.middleware.TouristProfile")
    def test_filter_called_with_correct_user(self, mock_profile_cls):
        """Sprawdza, że filter używa request.user jako klucza."""
        mock_profile = MagicMock()
        mock_profile.id = 55
        mock_profile_cls.objects.filter.return_value.first.return_value = mock_profile

        middleware = self._make_middleware()
        user = MagicMock()
        type(user).is_authenticated = PropertyMock(return_value=True)
        user.email = "check@example.com"

        request = MagicMock()
        request.user = user
        request.session = {}

        middleware.process_request(request)

        call_kwargs = mock_profile_cls.objects.filter.call_args[1]
        assert call_kwargs["user"] == user

    @patch("bootstrap.middleware.transaction.atomic", _noop_atomic)
    @patch("bootstrap.middleware.TouristProfile")
    def test_no_profile_set_when_filter_returns_none_and_create_returns_none(self, mock_profile_cls):
        """Jeśli filter i create zwracają None — session nie jest modyfikowana."""
        mock_profile_cls.objects.filter.return_value.first.return_value = None
        mock_profile_cls.objects.create.return_value = None

        middleware = self._make_middleware()
        user = MagicMock()
        type(user).is_authenticated = PropertyMock(return_value=True)

        request = MagicMock()
        request.user = user
        request.session = {}

        middleware.process_request(request)

        assert request.session.get("active_profile_id") is None

    @patch("bootstrap.middleware.transaction.atomic", _noop_atomic)
    @patch("bootstrap.middleware.TouristProfile")
    def test_nickname_derived_from_email(self, mock_profile_cls):
        """nickname w create pochodzi od części przed @ w emailu."""
        mock_profile = MagicMock()
        mock_profile.id = 99
        mock_profile_cls.objects.filter.return_value.first.return_value = None
        mock_profile_cls.objects.create.return_value = mock_profile

        middleware = self._make_middleware()
        user = MagicMock()
        type(user).is_authenticated = PropertyMock(return_value=True)
        user.email = "jan.kowalski@example.com"

        request = MagicMock()
        request.user = user
        request.session = {}

        middleware.process_request(request)

        call_kwargs = mock_profile_cls.objects.create.call_args[1]
        assert call_kwargs["nickname"] == "jan.kowalski"

    @patch("bootstrap.middleware.transaction.atomic", _noop_atomic)
    @patch("bootstrap.middleware.TouristProfile")
    def test_nickname_uses_user_id_when_no_email(self, mock_profile_cls):
        """Gdy brak emaila, nickname = admin_{user.id}."""
        mock_profile = MagicMock()
        mock_profile.id = 88
        mock_profile_cls.objects.filter.return_value.first.return_value = None
        mock_profile_cls.objects.create.return_value = mock_profile

        middleware = self._make_middleware()
        user = MagicMock()
        type(user).is_authenticated = PropertyMock(return_value=True)
        user.email = None
        user.id = 42

        request = MagicMock()
        request.user = user
        request.session = {}

        middleware.process_request(request)

        call_kwargs = mock_profile_cls.objects.create.call_args[1]
        assert call_kwargs["nickname"] == "admin_42"
