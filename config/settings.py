"""Django settings for config project."""

from pathlib import Path

from infrastructure.config.app_settings import AppSettings

# --- JEDNO ŹRÓDŁO PRAWDY DLA KONFIGURACJI ---
# Pydantic wczytuje zmienne z odpowiednich plików .env od razu przy imporcie tego pliku.
app_settings_config = AppSettings()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ==========================================
# CORE SETTINGS (Czytane z .env / AppSettings)
# ==========================================
SECRET_KEY = app_settings_config.secret_key
DEBUG = app_settings_config.debug

# Twarde hosty potrzebne do działania Dockera (Healthcheck i ruch lokalny wewnątrz kontenera)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Doklejenie prawdziwych domen z Twoich plików `.env` z chronionej instancji Pydantic (bez białych znaków)
if app_settings_config.allowed_hosts_str:
    env_hosts = [h.strip() for h in app_settings_config.allowed_hosts_str.split(",") if h.strip()]
    ALLOWED_HOSTS.extend(env_hosts)

# ==========================================
# DATABASE (Parsowanie z DATABASE_URL)
# ==========================================
# db_url = urlparse(app_settings_config.database_url)
#
# DATABASES = {
#    "default": {
#        "ENGINE": "django.contrib.gis.db.backends.postgis",
#        "NAME": db_url.path.lstrip("/"),
#        "USER": db_url.username,
#        "PASSWORD": db_url.password,
#        "HOST": db_url.hostname,
#        "PORT": str(db_url.port or 5432),
#    }
# }

import dj_database_url

DATABASES = {
    "default": dj_database_url.config(
        default=app_settings_config.database_url,  # To musi wskazywać na Pydantic, nie os.environ!
        conn_max_age=600,
        conn_health_checks=True,
    )
}
# Upewnijmy się, że używamy silnika PostGIS
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"

# ===============================
# CELERY & REDIS CONFIGURATION
# ===============================
# Adres brokera (kolejki zadań), do którego Django wysyła polecenia
CELERY_BROKER_URL = app_settings_config.celery_broker_url
# Adres, pod którym Celery zapisuje wyniki zadań (opcjonalnie, ale przydatne)
CELERY_RESULT_BACKEND = app_settings_config.celery_result_backend
# Format serializacji danych (JSON jest bezpieczny i uniwersalny)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
# Strefa czasowa dla zadań opóźnionych
CELERY_TIMEZONE = "Europe/Warsaw"
# Mówimy Celery, by harmonogramy brało z bazy danych (Django Admin), a nie z kodu!
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# --- Wspólny "Mózg" dla całej aplikacji ---
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": app_settings_config.celery_broker_url,
    }
}


# ==========================================
# APLIKACJE I MIDDLEWARE
# ==========================================
INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "django_jsonform",
    "django_celery_beat",
    "leaflet",
    "tinymce",
    "apps.badges",
    "apps.tourists",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "infrastructure.middleware.error_handling.RFC7807ErrorMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "apps" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.tourists.context_processors.tourist_profiles",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "apps" / "static"]
SITE_ID = 1

# Ustawienie wymagane przez serwery OpenStreetMap (Tile Usage Policy)
# Pozwala przeglądarce wysłać nagłówek Referer do obcych serwerów (jak OSM),
# co odblokowuje kafelki map w Django Adminie.
SECURE_REFERRER_POLICY = "origin-when-cross-origin"

# ==========================================
# TINYMCE CONFIGURATION
# ==========================================
TINYMCE_DEFAULT_CONFIG = {
    "height": "500px",
    "width": "100%",
    "menubar": True,
    "plugins": "advlist autolink lists link image charmap print preview anchor searchreplace visualblocks code fullscreen insertdatetime media table paste code help wordcount",
    "toolbar": "undo redo | formatselect | bold italic backcolor | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent | removeformat | help",
}


# ==========================================
# DJANGO UNFOLD (Modern Admin Theme)
# ==========================================
UNFOLD = {
    "SITE_TITLE": "Badges Admin",
    "SITE_HEADER": "System Odznak Turystycznych",
    "SITE_URL": "/",
    "COLORS": {
        "primary": {
            "50": "#f0f9ff",
            "100": "#e0f2fe",
            "200": "#bae6fd",
            "300": "#7dd3fc",
            "400": "#38bdf8",
            "500": "#0ea5e9",
            "600": "#0284c7",
            "700": "#0369a1",
            "800": "#075985",
            "900": "#0c4a6e",
        },
    },
}


# ==========================================
# AUTHENTICATION & ALLAUTH (Google OAuth)
# ==========================================
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",  # Domyślny (np. logowanie Admina)
    "allauth.account.auth_backends.AuthenticationBackend",  # Logowanie przez Google
]

# Nowoczesna konfiguracja Allauth
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
# ACCOUNT_EMAIL_VERIFICATION = "none"  # Google już zweryfikowało ten e-mail

# Przekierowania po zalogowaniu/wylogowaniu
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

# Zabezpieczenie danych Google (idą z .env na produkcji, lokalnie ustawisz je w panelu Admina)
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        # Dodanie bloku 'APP' omija konieczność dodawania kluczy w bazie danych w Django Adminie!
        "APP": {
            "client_id": app_settings_config.google_oauth_client_id,
            "secret": app_settings_config.google_oauth_client_secret,
            "key": "",
        },
        "SCOPE": [
            "profile",
            "email",
        ],
        "AUTH_PARAMS": {
            "access_type": "online",
        },
    }
}
