"""Middleware wstrzykujący kontener DI (Composition Root) na obiekt request.

Architektura:
- ``bootstrap.container`` żyje jako Composition Root w pakiecie ``bootstrap``.
- Warstwa ``apps`` (Delivery) nie powinna importować ``bootstrap`` bezpośrednio,
  aby reguła ``importlinter`` (Delivery Layer must not depend on Infrastructure)
  nie była łamana przez zależności pośrednie.
- Ten middleware działa jako most: pośród żądań HTTP przypisuje kontener do
  ``request.app_container``, skąd widoki w ``apps`` mogą go pobrać.
"""

from typing import cast

from django.contrib.auth.models import AbstractUser
from django.db import transaction
from django.http import HttpRequest
from django.utils.deprecation import MiddlewareMixin

from apps.tourists.models import TouristProfile
from bootstrap.container import get_container


class ContainerMiddleware(MiddlewareMixin):
    """Dodaje ``request.app_container`` z konfigurowanym kontenerem DI."""

    def process_request(self, request: HttpRequest) -> None:
        """
        Args:
          request: HttpRequest:
          request: HttpRequest:

        Returns:

        """
        request.app_container = get_container()


class EnsureTouristProfileMiddleware(MiddlewareMixin):
    """Upewnia się, że zalogowany użytkownik posiada TouristProfile.

    W ramach jednego cyklu żądania-odpowiedzi:
    1. Sprawdza, czy w sesji jest ustawione ``active_profile_id``.
    2. Jeśli nie — szuka profilu dla ``request.user``.
    3. Jeśli brak profilu (np. stary użytkownik z dev-środowiska), tworzy go
       atomowo z ``get_or_create`` w ``transaction.atomic()``.

    Dzięki temu widoki w ``apps/tourists/views.py`` nie muszą wywoływać
    operacji zapisu w funkcjach nazwanych jak *gettery*. Głównym benefitem
    jest eliminacja stronego zapisu z widoków read-only (np. map).
    """

    def process_request(self, request: HttpRequest) -> None:
        """
        Args:
          request: HttpRequest:

        Returns:
        """
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return

        active_id = request.session.get("active_profile_id")
        if active_id:
            return

        profile = self._ensure_profile(request.user)
        if profile:
            request.session["active_profile_id"] = profile.id

    @staticmethod
    def _ensure_profile(user: AbstractUser) -> TouristProfile | None:
        """Tworzy profil turysty, jeśli nie istnieje.

        Używa ``filter().first()`` zamiast ``get_or_create(user=...)``
        ze względu na model Konto Rodzinne — użytkownik może mieć
        wiele profili (unique_together = user + nickname, nie na user).
        Wybiera profil główny (``is_main_profile=True``) lub dowolny
        pierwszy. Tworzy nowy, jeśli brak.
        """
        nickname = user.email.split("@")[0] if user.email else f"admin_{user.id}"

        with transaction.atomic():
            profile = TouristProfile.objects.filter(user=user).first()
            if profile is None:
                profile = TouristProfile.objects.create(
                    user=user,
                    nickname=nickname,
                    is_main_profile=True,
                    active_plan="FREE",
                    max_photos_per_ascent=1,
                    max_active_badges=3,
                )
        return cast("TouristProfile | None", profile)
