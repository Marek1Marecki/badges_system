"""Wstrzykiwanie kontekstu turysty do szablonów HTML.

Umożliwia dostęp do aktywnego profilu i listy sub-profili (Konta Rodzinne)
we wszystkich widokach (np. na pasku nawigacyjnym base.html).
"""

from apps.tourists.models import TouristProfile


def tourist_profiles(request):
    """Zwraca aktywny profil i wszystkie profile powiązane z kontem."""
    if request.user.is_authenticated:
        profiles = list(TouristProfile.objects.filter(user=request.user).order_by("-is_main_profile", "nickname"))

        active_id = request.session.get("active_profile_id")
        active_profile = next((p for p in profiles if p.id == active_id), None)

        # Fallback: Jeśli brak aktywnego ID, bierzemy główny profil
        if not active_profile and profiles:
            active_profile = profiles[0]
            request.session["active_profile_id"] = active_profile.id

        return {
            "user_profiles": profiles,
            "active_profile": active_profile,
        }
    return {}
