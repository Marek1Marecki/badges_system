"""Tworzy sesję testową dla podanego użytkownika E2E."""

from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY, get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """Komenda do tworzenia sesji testowej."""

    help = "Tworzy sesję testową dla podanego użytkownika i zwraca session ID."

    def add_arguments(self, parser):
        """

        Args:
          parser:

        Returns:

        """
        parser.add_argument("username", type=str, help="Nazwa użytkownika, dla którego tworzymy sesję.")

    def handle(self, *args, **options):
        """

        Args:
          *args:
          **options:

        Returns:

        """
        username = options["username"]
        User = get_user_model()
        user, _ = User.objects.get_or_create(username=username, defaults={"is_active": True})
        session = SessionStore()
        session[SESSION_KEY] = str(user.id)
        session[BACKEND_SESSION_KEY] = "django.contrib.auth.backends.ModelBackend"
        session[HASH_SESSION_KEY] = user.get_session_auth_hash()
        session.save()
        self.stdout.write(session.session_key)
