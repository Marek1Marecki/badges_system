"""Komenda pomocnicza dla testów E2E. Generuje ważne ciastko sesji dla wskazanego użytkownika."""

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Generuje token sesji (sessionid) dla zadanego użytkownika."

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Nazwa użytkownika (username)")

    def handle(self, *args, **options):
        username = options["username"]
        User = get_user_model()

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Użytkownik {username} nie istnieje."))
            return

        # Upewniamy się, że użytkownik ma TouristProfile (Lazy init omijamy tworząc to jawnie)
        from apps.tourists.models import TouristProfile

        profile, _ = TouristProfile.objects.get_or_create(
            user=user, defaults={"nickname": f"{username}_e2e", "is_main_profile": True, "active_plan": "PRO"}
        )

        # Tworzymy fałszywą sesję i przypisujemy do niej użytkownika oraz jego profil
        session = SessionStore()
        session["_auth_user_id"] = str(user.pk)
        session["_auth_user_backend"] = "django.contrib.auth.backends.ModelBackend"
        session["_auth_user_hash"] = user.get_session_auth_hash()
        session["active_profile_id"] = profile.id
        session.set_expiry(timezone.now() + timezone.timedelta(days=1))
        session.save()

        # Wypluwamy tylko wygenerowany klucz sesji, by bash mógł go przechwycić
        self.stdout.write(session.session_key)
