"""Konfiguracja testcontainers dla sesji testowej."""

from __future__ import annotations

import os

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connections
from pytest_django.plugin import blocking_manager_key
from testcontainers.community.postgres import PostgresContainer


_testcontainers_container = None


def _start_postgres_container():
    """Uruchamia kontener PostgreSQL/PostGIS."""
    global _testcontainers_container
    if _testcontainers_container is None:
        _testcontainers_container = PostgresContainer("postgis/postgis:18-3.6-alpine")
        _testcontainers_container.start()
    return _testcontainers_container


def _stop_postgres_container():
    """Zatrzymuje kontener PostgreSQL/PostGIS."""
    global _testcontainers_container
    if _testcontainers_container is not None:
        _testcontainers_container.stop()
        _testcontainers_container = None


def _configure_django_for_testcontainers(container):
    """Konfiguruje Django do używania bazy z testcontainers."""
    db_url = (
        f"postgresql://{container.username}:{container.password}"
        f"@{container.get_container_host_ip()}:{container.get_exposed_port(5432)}"
        f"/{container.dbname}"
    )
    os.environ["DATABASE_URL"] = db_url

    db_config = {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": container.dbname,
        "USER": container.username,
        "PASSWORD": container.password,
        "HOST": container.get_container_host_ip(),
        "PORT": str(container.get_exposed_port(5432)),
    }
    settings.DATABASES["default"].update(db_config)
    if "default" in connections:
        connections["default"].settings_dict.update(db_config)


@pytest.fixture(scope="session")
def postgres_container():
    """Udostępnia kontener PostgreSQL/PostGIS dla testów z markerem ``testcontainers``."""
    global _testcontainers_container
    _testcontainers_container = _start_postgres_container()
    _configure_django_for_testcontainers(_testcontainers_container)
    call_command("migrate", "--run-syncdb", verbosity=0)
    try:
        yield _testcontainers_container
    finally:
        _stop_postgres_container()


@pytest.fixture(scope="session")
def django_db_setup(postgres_container):
    """Nadpisuje domyślne django_db_setup, używając testcontainers.

    Ten fixture jest wywoływany tylko gdy test wymaga bazy danych Django
    (przez ``@pytest.mark.django_db``). Dla testów z markerem ``testcontainers``,
    ``postgres_container`` uruchamia rzeczywisty kontener PostGIS.
    """
    _configure_django_for_testcontainers(postgres_container)
    call_command("migrate", "--run-syncdb", verbosity=0)
    yield {
        "default": {
            "ENGINE": "django.contrib.gis.db.backends.postgis",
            "NAME": postgres_container.dbname,
            "USER": postgres_container.username,
            "PASSWORD": postgres_container.password,
            "HOST": postgres_container.get_container_host_ip(),
            "PORT": str(postgres_container.get_exposed_port(5432)),
        }
    }


@pytest.fixture(scope="session", autouse=True)
def _unblock_database(request):
    """Odblokuje dostęp do bazy danych po tym, jak pytest-django zablokuje go."""
    blocking_manager = request.config.stash[blocking_manager_key]
    blocking_manager.unblock()
