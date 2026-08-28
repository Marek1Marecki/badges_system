"""Proof-of-concept testcontainers dla PostgreSQL/PostGIS.

Uruchamia prawdziwą bazę danych w kontenerze Docker, uruchamia migracje
i wykonuje prosty test integracyjny przeciwko rzeczywistemu PostGIS.

Uruchomienie:
    make experimental-testcontainers
"""

from __future__ import annotations

import pytest
from django.db import connection


@pytest.mark.integration
@pytest.mark.django_db
@pytest.mark.testcontainers
class TestRealPostGISWithTestcontainers:
    """Integracyjne testy przeciwko prawdziwej PostGIS uruchomionej przez testcontainers."""

    def test_database_connection_works(self):
        """Weryfikuje, że łączność z PostGIS działa."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        assert result[0] == 1

    def test_postgis_extension_available(self):
        """Weryfikuje, że rozszerzenie PostGIS jest dostępne."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT PostGIS_Version()")
            result = cursor.fetchone()
        assert result[0] is not None

    def test_migrations_ran_successfully(self):
        """Weryfikuje, że migracje zostały uruchomione (tabele istnieją)."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'odznaki_badge'"
            )
            result = cursor.fetchone()
        assert result is not None, "Migracje nie zostały uruchomione — brak tabeli odznaki_badge"

    def test_can_create_and_query_badge(self):
        """Weryfikuje podstawowe CRUD na modelu Badge."""
        from apps.badges.models import BadgeModel, OrganizerModel

        organizer = OrganizerModel.objects.create(name="Test Organizer")
        badge = BadgeModel.objects.create(
            code="TEST",
            name="Test Badge",
            organizer=organizer,
        )
        assert badge.code == "TEST"

        retrieved = BadgeModel.objects.get(code="TEST")
        assert retrieved.name == "Test Badge"
