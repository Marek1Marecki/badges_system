"""Testy dla ustawień Django."""

from config.settings import (
    ALLOWED_HOSTS,
    AUTH_PASSWORD_VALIDATORS,
    BASE_DIR,
    DATABASES,
    DEBUG,
    INSTALLED_APPS,
    LANGUAGE_CODE,
    MIDDLEWARE,
    ROOT_URLCONF,
    SECRET_KEY,
    STATIC_URL,
    TEMPLATES,
    TIME_ZONE,
    USE_I18N,
    USE_TZ,
    WSGI_APPLICATION,
)


class TestBasicSettings:
    """Testy podstawowych ustawień."""

    def test_base_dir_exists(self):
        """Test że BASE_DIR jest zdefiniowany."""
        assert BASE_DIR is not None
        assert BASE_DIR.exists()
        assert BASE_DIR.is_dir()

    def test_secret_key_is_defined(self):
        """Test że SECRET_KEY jest zdefiniowany."""
        assert SECRET_KEY is not None
        assert isinstance(SECRET_KEY, str)
        assert len(SECRET_KEY) > 0

    def test_debug_setting(self):
        """Test ustawienia DEBUG."""
        assert isinstance(DEBUG, bool)

    def test_allowed_hosts(self):
        """Test ustawienia ALLOWED_HOSTS."""
        assert isinstance(ALLOWED_HOSTS, list)


class TestInstalledApps:
    """Testy zainstalowanych aplikacji."""

    def test_installed_apps_is_list(self):
        """Test że INSTALLED_APPS jest listą."""
        assert isinstance(INSTALLED_APPS, list)
        assert len(INSTALLED_APPS) > 0

    def test_core_django_apps_are_installed(self):
        """Test że podstawowe aplikacje Django są zainstalowane."""
        core_apps = [
            "django.contrib.admin",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "django.contrib.staticfiles",
        ]

        for app in core_apps:
            assert app in INSTALLED_APPS

    def test_gis_and_custom_apps_are_installed(self):
        """Test że aplikacje GIS i własne są zainstalowane."""
        expected_apps = [
            "django.contrib.gis",
            "django_jsonform",
            "apps.badges",
        ]

        for app in expected_apps:
            assert app in INSTALLED_APPS


class TestMiddleware:
    """Testy middleware."""

    def test_middleware_is_list(self):
        """Test że MIDDLEWARE jest listą."""
        assert isinstance(MIDDLEWARE, list)
        assert len(MIDDLEWARE) > 0

    def test_core_middleware_are_present(self):
        """Test że podstawowe middleware są obecne."""
        core_middleware = [
            "django.middleware.security.SecurityMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
            "django.middleware.clickjacking.XFrameOptionsMiddleware",
        ]

        for middleware in core_middleware:
            assert middleware in MIDDLEWARE

    def test_ensure_profile_middleware_present(self):
        assert "bootstrap.middleware.EnsureTouristProfileMiddleware" in MIDDLEWARE


class TestDatabaseSettings:
    """Testy ustawień bazy danych."""

    def test_databases_is_dict(self):
        """Test że DATABASES jest słownikiem."""
        assert isinstance(DATABASES, dict)
        assert "default" in DATABASES

    def test_default_database_config(self):
        """Test konfiguracji domyślnej bazy danych."""
        default_db = DATABASES["default"]

        assert "ENGINE" in default_db
        assert "NAME" in default_db
        assert "USER" in default_db
        assert "PASSWORD" in default_db
        assert "HOST" in default_db
        assert "PORT" in default_db

    def test_database_engine_is_postgis(self):
        """Test że silnikiem bazy danych jest PostGIS."""
        assert DATABASES["default"]["ENGINE"] == "django.contrib.gis.db.backends.postgis"


class TestTemplatesSettings:
    """Testy ustawień szablonów."""

    def test_templates_is_list(self):
        """Test że TEMPLATES jest listą."""
        assert isinstance(TEMPLATES, list)
        assert len(TEMPLATES) > 0

    def test_template_backend(self):
        """Test backendu szablonów."""
        template_config = TEMPLATES[0]
        assert template_config["BACKEND"] == "django.template.backends.django.DjangoTemplates"

    def test_template_options(self):
        """Test opcji szablonów."""
        template_config = TEMPLATES[0]

        assert "OPTIONS" in template_config
        assert "context_processors" in template_config["OPTIONS"]

        context_processors = template_config["OPTIONS"]["context_processors"]
        expected_processors = [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ]

        for processor in expected_processors:
            assert processor in context_processors


class TestAuthPasswordValidators:
    """Testy walidatorów haseł."""

    def test_auth_password_validators_is_list(self):
        """Test że AUTH_PASSWORD_VALIDATORS jest listą."""
        assert isinstance(AUTH_PASSWORD_VALIDATORS, list)
        assert len(AUTH_PASSWORD_VALIDATORS) > 0

    def test_password_validators_structure(self):
        """Test struktury walidatorów haseł."""
        for validator in AUTH_PASSWORD_VALIDATORS:
            assert isinstance(validator, dict)
            assert "NAME" in validator

    def test_default_password_validators_are_present(self):
        """Test że domyślne walidatory haseł są obecne."""
        expected_validators = [
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
            "django.contrib.auth.password_validation.MinimumLengthValidator",
            "django.contrib.auth.password_validation.CommonPasswordValidator",
            "django.contrib.auth.password_validation.NumericPasswordValidator",
        ]

        validator_names = [v["NAME"] for v in AUTH_PASSWORD_VALIDATORS]

        for validator in expected_validators:
            assert validator in validator_names


class TestInternationalizationSettings:
    """Testy ustawień internacjonalizacji."""

    def test_language_code(self):
        """Test ustawienia LANGUAGE_CODE."""
        assert isinstance(LANGUAGE_CODE, str)
        assert len(LANGUAGE_CODE) > 0

    def test_time_zone(self):
        """Test ustawienia TIME_ZONE."""
        assert isinstance(TIME_ZONE, str)
        assert len(TIME_ZONE) > 0

    def test_use_i18n(self):
        """Test ustawienia USE_I18N."""
        assert isinstance(USE_I18N, bool)

    def test_use_tz(self):
        """Test ustawienia USE_TZ."""
        assert isinstance(USE_TZ, bool)


class TestStaticFilesSettings:
    """Testy ustawień plików statycznych."""

    def test_static_url(self):
        """Test ustawienia STATIC_URL."""
        assert isinstance(STATIC_URL, str)
        assert len(STATIC_URL) > 0
        assert STATIC_URL.endswith("/")


class TestUrlAndWsgiSettings:
    """Testy ustawień URL i WSGI."""

    def test_root_urlconf(self):
        """Test ustawienia ROOT_URLCONF."""
        assert isinstance(ROOT_URLCONF, str)
        assert len(ROOT_URLCONF) > 0

    def test_wsgi_application(self):
        """Test ustawienia WSGI_APPLICATION."""
        assert isinstance(WSGI_APPLICATION, str)
        assert len(WSGI_APPLICATION) > 0
