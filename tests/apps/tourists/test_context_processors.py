"""Testy dla context processors turysty."""

from unittest.mock import MagicMock, patch

import pytest

from apps.tourists.context_processors import tourist_profiles
from infrastructure.config.map_layers import AVAILABLE_MAP_LAYERS


def test_returns_empty_dict_for_unauthenticated_user():
    """Zwraca pusty słownik dla nieuwierzytelnionego użytkownika."""
    request = MagicMock()
    request.user.is_authenticated = False

    result = tourist_profiles(request)

    assert result == {}


@patch("apps.tourists.context_processors.TouristProfile")
def test_returns_profiles_for_authenticated_user(mock_profile_model):
    """Zwraca profile dla uwierzytelnionego użytkownika."""
    request = MagicMock()
    request.user.is_authenticated = True
    request.session = {}

    profile1 = MagicMock()
    profile1.id = 1
    profile1.is_main_profile = True
    profile1.nickname = "Test"
    profile1.active_plan = "FREE"
    profile1.preferred_base_map = "carto"

    mock_qs = MagicMock()
    mock_qs.order_by.return_value = [profile1]
    mock_profile_model.objects.filter.return_value = mock_qs

    result = tourist_profiles(request)

    assert result["user_profiles"] == [profile1]
    assert result["active_profile"] == profile1
    mock_profile_model.objects.filter.assert_called_once_with(user=request.user)


@patch("apps.tourists.context_processors.TouristProfile")
def test_sets_active_profile_from_session(mock_profile_model):
    """Ustawia aktywny profil z sesji."""
    request = MagicMock()
    request.user.is_authenticated = True
    request.session = {"active_profile_id": 2}

    profile1 = MagicMock()
    profile1.id = 1
    profile2 = MagicMock()
    profile2.id = 2
    profile2.is_main_profile = True
    profile2.active_plan = "FREE"
    profile2.preferred_base_map = "carto"

    mock_qs = MagicMock()
    mock_qs.order_by.return_value = [profile1, profile2]
    mock_profile_model.objects.filter.return_value = mock_qs

    result = tourist_profiles(request)

    assert result["active_profile"] == profile2


@patch("apps.tourists.context_processors.TouristProfile")
def test_falls_back_to_first_profile_when_no_active(mock_profile_model):
    """Falls back to first profile when no active profile in session."""
    request = MagicMock()
    request.user.is_authenticated = True
    request.session = {}

    profile1 = MagicMock()
    profile1.id = 1
    profile1.is_main_profile = False
    profile1.active_plan = "FREE"
    profile1.preferred_base_map = "carto"

    mock_qs = MagicMock()
    mock_qs.order_by.return_value = [profile1]
    mock_profile_model.objects.filter.return_value = mock_qs

    result = tourist_profiles(request)

    assert result["active_profile"] == profile1
    assert request.session["active_profile_id"] == 1


@patch("apps.tourists.context_processors.TouristProfile")
def test_premium_user_gets_paid_maps(mock_profile_model):
    """Użytkownik Premium dostaje płatne mapy."""
    request = MagicMock()
    request.user.is_authenticated = True
    request.session = {}

    profile = MagicMock()
    profile.id = 1
    profile.is_main_profile = True
    profile.active_plan = "PREMIUM"
    profile.preferred_base_map = "mapycz_outdoor"

    mock_qs = MagicMock()
    mock_qs.order_by.return_value = [profile]
    mock_profile_model.objects.filter.return_value = mock_qs

    with patch("apps.tourists.context_processors.settings") as mock_settings:
        mock_settings.MAPY_CZ_API_KEY = "test-api-key"
        result = tourist_profiles(request)

    assert result["map_premium_unlocked"] is True
    assert result["preferred_base_map"] == "mapycz_outdoor"
    paid_layer = next(l for l in result["map_layers"] if l["id"] == "mapycz_outdoor")
    assert paid_layer["locked"] is False
    assert "{api_key}" not in paid_layer["tiles"]


@patch("apps.tourists.context_processors.TouristProfile")
def test_free_user_cannot_access_paid_maps(mock_profile_model):
    """Użytkownik Free nie dostaje płatnych map."""
    request = MagicMock()
    request.user.is_authenticated = True
    request.session = {}

    profile = MagicMock()
    profile.id = 1
    profile.is_main_profile = True
    profile.active_plan = "FREE"
    profile.preferred_base_map = "mapycz_outdoor"

    mock_qs = MagicMock()
    mock_qs.order_by.return_value = [profile]
    mock_profile_model.objects.filter.return_value = mock_qs

    result = tourist_profiles(request)

    assert result["map_premium_unlocked"] is False
    assert result["preferred_base_map"] == "cartodb_positron"
    paid_layer = next(l for l in result["map_layers"] if l["id"] == "mapycz_outdoor")
    assert paid_layer["locked"] is True
    assert paid_layer["tiles"] == ""


@patch("apps.tourists.context_processors.TouristProfile")
def test_free_user_keeps_free_map_preference(mock_profile_model):
    """Użytkownik Free z darmową mapą zachowuje preferencję."""
    request = MagicMock()
    request.user.is_authenticated = True
    request.session = {}

    profile = MagicMock()
    profile.id = 1
    profile.is_main_profile = True
    profile.active_plan = "FREE"
    profile.preferred_base_map = "osm_standard"

    mock_qs = MagicMock()
    mock_qs.order_by.return_value = [profile]
    mock_profile_model.objects.filter.return_value = mock_qs

    result = tourist_profiles(request)

    assert result["preferred_base_map"] == "osm_standard"
