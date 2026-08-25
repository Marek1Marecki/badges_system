"""Wstrzykiwanie kontekstu turysty do szablonów HTML.

Umożliwia dostęp do aktywnego profilu i listy sub-profili (Konta Rodzinne) we wszystkich widokach (np. na pasku
nawigacyjnym base.html).
"""

import json

from django.conf import settings

from apps.tourists.models import TouristProfile
from infrastructure.config.map_layers import AVAILABLE_MAP_LAYERS


def tourist_profiles(request):
    """Zwraca aktywny profil i konfigurację Freemium (Premium Maps).

    Args:
      request:

    Returns:
    """
    if not request.user.is_authenticated:
        return {}

    profiles = list(TouristProfile.objects.filter(user=request.user).order_by("-is_main_profile", "nickname"))

    active_id = request.session.get("active_profile_id")
    active_profile = next((p for p in profiles if p.id == active_id), None)

    if not active_profile and profiles:
        active_profile = profiles[0]
        request.session["active_profile_id"] = active_profile.id

    is_premium = False
    mapy_key = getattr(settings, "MAPY_CZ_API_KEY", "")
    preferred_map = "cartodb_positron"

    if active_profile:
        if active_profile.active_plan.upper() != "FREE":
            is_premium = True
            preferred_map = active_profile.preferred_base_map
        else:
            # Fallback dla użytkowników, którym wygasł abonament
            preferred_map = active_profile.preferred_base_map
            # Jeśli wybrali płatną mapę, zmuszamy do powrotu na darmową
            if any(layer["id"] == preferred_map and layer["is_paid"] for layer in AVAILABLE_MAP_LAYERS):
                preferred_map = "cartodb_positron"

    # Budujemy dynamiczną listę map dla frontendu
    processed_layers = []
    for layer in AVAILABLE_MAP_LAYERS:
        l_data = layer.copy()
        if l_data["is_paid"]:
            if is_premium:
                l_data["locked"] = False
                l_data["tiles"] = l_data["tiles"].replace("{api_key}", mapy_key)
            else:
                l_data["locked"] = True
                l_data["tiles"] = ""  # OCHRONA: Brak klucza dla darmowych kont!
        else:
            l_data["locked"] = False

        processed_layers.append(l_data)

    return {
        "user_profiles": profiles,
        "active_profile": active_profile,
        "map_premium_unlocked": is_premium,
        "preferred_base_map": preferred_map,
        "map_layers": processed_layers,
        "map_layers_json": json.dumps(processed_layers),
    }
