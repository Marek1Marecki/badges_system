# ==============================================================================
# Dockerfile — System Odznak Turystycznych PTTK
# Zgodny z ADR-020 (Deployment & DataOps) oraz 07-docker-contract.md / 08-base-image-policy.md
#
# Jeden plik, cztery targety: base -> builder -> {development, testing, production}
# Zakaz tworzenia osobnych Dockerfile.dev / Dockerfile.prod (ADR-020, Opcja B).
# ==============================================================================

ARG PYTHON_BASE=python:3.14-slim-bookworm
# Wersja uv przypięta jawnie — brak `latest` (08-base-image-policy.md)
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.5.11

# ==============================================================================
# 0. ETAP POMOCNICZY — źródło binarki `uv`
#
# WAŻNE: `COPY --from=${UV_IMAGE}` (odwołanie do wartości ARG bezpośrednio
# w --from) działa niedeterministycznie w BuildKit — bez cache trafienia
# kończy się błędem: "variable expansion is not supported for --from, define
# a new stage with FROM using ARG from global scope as a workaround". To
# jest dokładnie ten workaround: `FROM $ARG` (obsługiwane w pełni, także
# z cache miss) jest dozwolone, samo `COPY --from=$ARG` — nie zawsze.
# Wszystkie kolejne stage'e kopiują uv z NAZWY tego stage'u, nigdy ze zmiennej.
# ==============================================================================
FROM ${UV_IMAGE} AS uv_source


# ==============================================================================
# 1. ETAP BAZOWY — wspólne zmienne środowiskowe, brak instalacji pakietów
# ==============================================================================
FROM ${PYTHON_BASE} AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app


# ==============================================================================
# 2. ETAP BUILDER — kompilacja zależności (GDAL/PROJ/psycopg), instalacja uv
# ==============================================================================
FROM base AS builder

# Ciężki toolchain do kompilacji rozszerzeń C / bindingów GIS.
# Ten stage NIGDY nie trafia do obrazu production (tylko /opt/venv jest kopiowane).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libproj-dev \
        gdal-bin \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv_source /uv /usr/local/bin/uv

# Instalacja zależności BEZ instalowania samego projektu (uniknięcie
# editable-install przy braku jeszcze skopiowanego kodu źródłowego).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Kopiujemy kod i domykamy instalację (editable install projektu).
COPY . /app/
RUN uv sync --frozen --no-dev


# ==============================================================================
# 3. ETAP ROZWOJOWY (DEVELOPMENT) — pełne zależności dev, kod z volume mount
# ==============================================================================
FROM base AS development
# UID/GID dopasowane do hosta dewelopera (domyślnie 1000:1000 — typowy pierwszy
# użytkownik na Linuksie). Bez tego proces działałby jako root i pliki tworzone
# w zamontowanym wolumenie ./:/app miałyby właściciela root na hoście.
# Nadpisz przy buildzie, jeśli Twój UID/GID jest inny: `--build-arg USER_UID=$(id -u)`.
ARG USER_UID=1000
ARG USER_GID=1000

RUN apt-get update && apt-get install -y --no-install-recommends \
        libproj-dev \
        gdal-bin \
        gcc \
        g++ \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv_source /uv /usr/local/bin/uv
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml uv.lock README.md ./
# Jawnie grupa `dev` — patrz uzasadnienie przy stage'u `testing` niżej
# (zachowanie domyślnych grup uv nie powinno być domysłem Dockerfile'a).
RUN uv sync --frozen --group dev --no-install-project

# Tworzymy użytkownika deweloperskiego i przekazujemy mu własność /opt/venv
# oraz /app — bez tego `uv sync` (root) tworzy pliki niedostępne do zapisu
# dla późniejszego procesu działającego jako zwykły użytkownik.
RUN (getent group "${USER_GID}" || groupadd -g "${USER_GID}" devgroup) \
    && (id -u "${USER_UID}" >/dev/null 2>&1 || useradd -m -u "${USER_UID}" -g "${USER_GID}" -s /bin/bash devuser) \
    && chown -R "${USER_UID}:${USER_GID}" /opt/venv /app

USER ${USER_UID}:${USER_GID}

# Kod źródłowy przychodzi przez wolumen (compose.override.yml: ./:/app).
# `uv run` gwarantuje użycie interpretera z /opt/venv.
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8005"]


# ==============================================================================
# 4. ETAP TESTOWY (TESTING) — kod zamrożony w obrazie, pełne zależności dev
# ==============================================================================
FROM builder AS testing

ENV PATH="/opt/venv/bin:$PATH"
# UWAGA: `builder` zainstalował wyłącznie zależności produkcyjne
# (--no-dev). Samo `uv sync --frozen` bez dalszych flag NIE gwarantuje
# doinstalowania grupy `dev` — zależy to od tego, czy `dev` jest oznaczona
# jako domyślna grupa w `[tool.uv] default-groups` w pyproject.toml, co jest
# szczegółem konfiguracji projektu, nie czymś, na czym powinien polegać
# Dockerfile. Żądamy grupy `dev` jawnie, żeby zachowanie było deterministyczne
# niezależnie od konfiguracji domyślnych grup.
RUN uv sync --frozen --group dev

#ENTRYPOINT ["uv", "run", "pytest"]
CMD ["uv", "run", "pytest", "-m", "not integration"]


# ==============================================================================
# 5. ETAP PRODUKCYJNY / PRE-PROD (RUNTIME)
# ==============================================================================
FROM base AS production

ENV PATH="/opt/venv/bin:$PATH"

# Wyłącznie biblioteki współdzielone (bez -dev, bez kompilatorów, bez curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdal32 \
        libproj25 \
    && rm -rf /var/lib/apt/lists/*

# Binarka `uv` — WYMAGANA, bo scripts/release-*.sh i bootstrap.sh wołają
# `uv run python manage.py ...`. Bez tego kopiowania te skrypty działałyby
# w DEV/TEST (mają swój własny `uv` z etapu development/builder), ale
# kończyłyby się błędem "uv: command not found" dopiero przy pierwszym
# uruchomieniu na PRE-PROD/PROD — dokładnie ten rodzaj błędu, który ujawnia
# się późno, bo wcześniejsze środowiska go maskują.
COPY --from=uv_source /uv /usr/local/bin/uv

# Hardening: usunięcie narzędzi paczkujących (vendored CVE w obrazie bazowym).
# `|| true` jest tu ŚWIADOMYM wyjątkiem od zasady "nie maskuj błędów" —
# celowo ignorujemy sytuację, w której pip/setuptools/wheel już nie istnieją
# w obrazie bazowym (np. po jego aktualizacji), bo cel (ich brak) jest wtedy
# już osiągnięty. Nie maskujemy tym innych, niezwiązanych błędów tej komendy.
RUN pip uninstall -y pip setuptools wheel || true

# Zbudowane środowisko wirtualne z etapu builder (zawiera już zainstalowany projekt)
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app

# Usunięcie kodu testowego, dokumentacji i plików infrastrukturalnych z obrazu
# produkcyjnego (Minimal Surface). .dockerignore NIE wyklucza już tests/ (musi
# trafić do etapu 'testing' — patrz ten plik, komentarz przy .dockerignore),
# więc czyścimy to jawnie tutaj, tylko dla warstwy production/pre-prod.
#
# Poniższe pliki repo-root (compose*.yml, Dockerfile, Caddyfile, .env.example,
# README-infra.md) trafiają do /app przez `COPY . /app/` w builderze (nic w
# .dockerignore ich nie wyklucza — są potrzebne w repo, nie w obrazie
# runtime). Same w sobie nie są sekretami, ale zgodnie z Minimal Surface
# (architecture-principles.md) nie powinny zaśmiecać obrazu produkcyjnego.
#
# scripts/dev-*.sh usuwamy z tego samego powodu — to orkiestracja WYŁĄCZNIE
# na hosta (wywołują `docker compose`), wewnątrz uruchomionego już kontenera
# nie mają jak zadziałać (brak dostępu do demona Dockera) i tylko zaśmiecałyby
# obraz produkcyjny.
RUN rm -rf /app/tests /app/docs /app/docs_sphinx \
    && rm -f /app/compose*.yml /app/Dockerfile /app/Caddyfile \
             /app/.env.example /app/README-infra.md /app/.dockerignore \
             /app/.pre-commit-config.yaml /app/scripts/dev-*.sh

# Glob po rozszerzeniu (`*.sh`), NIE `chmod +x /app/scripts` (to ustawiłoby
# uprawnienie na samym KATALOGU, nie na plikach w środku) i NIE `chmod -R`
# (uczyniłoby wykonywalnym też np. przypadkowy plik .md w tym katalogu).
# Ten wariant skaluje się automatycznie — nowy skrypt *.sh w tym katalogu
# nie wymaga już ręcznej edycji tej listy.
RUN chmod +x /app/scripts/*.sh

# Stały, jawny UID (zgodnie z kontraktem bezpieczeństwa)
RUN useradd -m -d /app -s /bin/bash --uid 10001 django_user \
    && mkdir -p /app/staticfiles \
    && chown -R django_user:django_user /app

# ==============================================================================
# UWAGA — BLOKUJĄCY WYMÓG PRZED PIERWSZYM URUCHOMIENIEM TEGO OBRAZU:
# Poniższy HEALTHCHECK zakłada istnienie widoku `/health/` zwracającego 200 OK
# BEZ wymogu uwierzytelnienia. Jeśli ten widok nie istnieje jeszcze w kodzie
# Django, kontener wejdzie w nieskończoną pętlę: Running -> unhealthy ->
# restart -> Running -> unhealthy... Traktuj implementację `/health/` (oraz
# obecność `localhost`/`127.0.0.1` w ALLOWED_HOSTS) jako część Definition of
# Done TEGO Dockerfile'a, nie opcjonalne dopracowanie na później.
# Patrz README-infra.md, sekcja "Znane luki".
# ==============================================================================
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, http.client; \
conn = http.client.HTTPConnection('localhost:8000'); \
conn.request('GET', '/health/'); \
res = conn.getresponse(); \
sys.exit(0) if res.status == 200 else sys.exit(1)"

USER 10001
EXPOSE 8000

# entrypoint jest CELOWO pozbawiony efektów ubocznych (brak migrate/collectstatic —
# patrz ADR-020, Zasada Akceptacji Release'u oraz 07-docker-contract.md).
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
