# Docker Contract

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty aplikacyjne

---

## Filozofia

Hierarchia zasad (niezmienna): Reproducibility → Jawność → Deterministyczność → Prostota → Wygoda.

Bezpieczeństwo jest elementem definicji poprawnego środowiska produkcyjnego — nie osobnym priorytetem.

---

## Multi-stage build (obowiązkowe)

Oddzielamy warstwę budowania zależności od warstwy runtime. Brak build toolchain w runtime.

### Dlaczego /opt/venv zamiast /app/.venv

Mount `./:/app` w trybie dev nadpisuje cały katalog `/app`, niszcząc `.venv` z obrazu. Przeniesienie venv do `/opt/venv` rozwiązuje problem strukturalnie — bez anonimowych wolumenów.

```dockerfile
# Builder instaluje do /opt/venv
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --no-dev --frozen

# Runtime kopiuje gotowy venv
COPY --from=builder /opt/venv /opt/venv
```

**Zakaz:** montowania `/opt/venv` jako named volume — prowadzi do "zamrożonego venv" (nowe paczki nie pojawiają się po `docker compose build`).

### Instalacja zależności

```dockerfile
COPY pyproject.toml uv.lock ./
RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --no-dev --frozen
```

`--frozen` odmawia buildu jeśli `uv.lock` jest niezsynchronizowany z `pyproject.toml`. Brak dynamicznego rozwiązywania zależności — pełna deterministyczność.

---

## Hardening Stage 2

Obrazy bazowe `python:3.x-slim-bookworm` zawierają systemowy `pip`, `setuptools` i `wheel` z vendored dependencies w starszych wersjach. Trivy wykrywa je jako CVE mimo że projekt używa wyłącznie `/opt/venv`.

**Rozwiązanie — usunięcie w Stage 2:**

```dockerfile
# Stage 2: runtime
RUN pip uninstall -y pip setuptools wheel || true
```

`|| true` — idempotentne, nie psuje buildu jeśli pakiety już nie istnieją. Usuwa vendored copies które byłyby wykryte przez Trivy. Nie wpływa na `/opt/venv` — aplikacja używa venv, nie systemowego pip.

---

## Runtime Security (obowiązkowe)

### Non-root user

```dockerfile
RUN useradd --create-home --uid 10001 appuser
USER appuser
```

UID jest jawny i stały — unika konfliktów z mounted volumes.

### Read-only filesystem

```yaml
read_only: true
```

### tmpfs dla /tmp

```yaml
tmpfs:
  - /tmp
```

Umożliwia operacje tymczasowe, nie łamie modelu read-only, czyści się przy restarcie.

### Drop wszystkich capabilities

```yaml
cap_drop:
  - ALL
```

Każde odstępstwo wymaga jawnego uzasadnienia i dokumentacji w repozytorium.

### No new privileges

```yaml
security_opt:
  - no-new-privileges:true
```

### Limity zasobów

```yaml
deploy:
  resources:
    limits:
      cpus: "1.0"
      memory: 512M
```

---

## Healthcheck

```dockerfile
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/health')"
```

**Zakaz:** instalowania `curl` wyłącznie do healthchecka — rozszerza powierzchnię ataku.

---

## Kanoniczny Dockerfile

```dockerfile
# ===============================
# Stage 1: builder
# ===============================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

RUN UV_PROJECT_ENVIRONMENT=/opt/venv uv sync --no-dev --frozen

# ===============================
# Stage 2: runtime
# ===============================
FROM python:3.12-slim-bookworm

WORKDIR /app

# Hardening: usuń systemowy pip/setuptools/wheel
# Trivy wykrywa vendored copies jako CVE mimo że używamy /opt/venv
RUN pip uninstall -y pip setuptools wheel || true

RUN useradd --create-home --uid 10001 appuser

COPY --from=builder /opt/venv /opt/venv
COPY . .

ENV VIRTUAL_ENV="/opt/venv"
ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8050

HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8050/health')"

USER appuser

CMD ["python", "app.py"]
```

---

## docker-compose — wariant DEV

`docker-compose.dev.yml` służy wyłącznie do uruchamiania aplikacji w trybie developerskim z live reload. Narzędzia developerskie działają lokalnie przez `uv` — nie wewnątrz kontenera.

```yaml
services:
  app:
    build: .
    container_name: app_dev
    ports:
      - "8050:8050"
    volumes:
      - .:/app
    env_file:
      - .env.dev
    environment:
      DASH_DEBUG: "1"
    restart: unless-stopped
```

**Uwaga:** W trybie dev z `/opt/venv` nie potrzebujemy anonimowego volumenu dla venv — venv jest poza `/app` i nie zostanie nadpisany przez mount `./:/app`.

---

## docker-compose — wariant PROD

```yaml
services:
  app:
    build: .
    container_name: app_prod
    ports:
      - "8050:8050"
    env_file:
      - .env.prod
    environment:
      DASH_DEBUG: "0"
    restart: unless-stopped
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
```

---

## Wyjątek: projekty GIS (GDAL, PostGIS, GeoDjango)

Projekty GIS wymagają systemowych bibliotek GDAL/GEOS/PROJ w kontenerze. Nie instalujemy ich lokalnie na hoście — tylko w Dockerfile.

Konsekwencja: `mypy` z pluginem `django-stubs` nie może działać lokalnie bez GDAL.

Rozwiązanie zgodne z kontraktem:
- Wykluczyć warstwy Django z mypy (`exclude = ["^apps/"]`)
- Usunąć `mypy_django_plugin` z konfiguracji mypy
- Udokumentować wyjątek w `pyproject.toml`

---

## Definicja poprawnego środowiska

Środowisko jest zgodne z kontraktem tylko gdy:

- Build jest deterministyczny
- Zależności są zamrożone (`--frozen`)
- Runtime jest minimalny (brak build toolchain)
- Kontener działa jako non-root
- System plików jest read-only
- Capabilities są usunięte
- `no-new-privileges` jest aktywne
- Zasoby są ograniczone
- Healthcheck nie rozszerza powierzchni ataku

Brak któregokolwiek → środowisko nie jest production-ready.

---

## Kontrakt migracji bazy danych

Migracje bazy danych są operacją administracyjną — nie częścią startu kontenera aplikacji.

**Zakaz: migracje jako `CMD` przy starcie kontenera**

```dockerfile
# Zakaz — race condition przy wielu instancjach, brak izolacji błędów
CMD ["sh", "-c", "python manage.py migrate && python app.py"]
```

Przy skalowaniu poziomym (wiele instancji) każda próbuje wykonać migrację równocześnie. Przy błędzie migracji kontener nie startuje — brak możliwości rollbacku bez ingerencji w infrastrukturę.

**Nakaz: migracje jako osobny krok przed przepięciem ruchu**

```makefile
# Makefile — jawny krok migracji przed deploymentem
db-migrate:
    docker compose run --rm web python manage.py migrate
```

W środowisku K8s: dedykowany `Job` który kończy się przed aktualizacją `Deployment`. W środowisku Compose: `docker compose run --rm web python manage.py migrate` wywołany ręcznie lub przez pipeline CD przed `docker compose up -d`.

**Dlaczego `run --rm` a nie `exec`:** `docker compose exec` wymaga działającego kontenera `web`. Jeśli aplikacja nie startuje bez migracji — `exec` tworzy deadlock. `run --rm` tworzy jednorazowy kontener niezależnie od stanu aplikacji.

**Kolejność w pipeline CD:**

```
docker build → trivy → migrate (jednorazowy kontener) → docker compose up -d (nowy obraz)
```

Migracja uruchamiana po zbudowaniu nowego obrazu, przed przepięciem ruchu — gwarantuje że schemat bazy jest aktualny przed startem nowej wersji aplikacji.

---

## Kontrakt `.dockerignore` (obowiązkowy)

`COPY . .` bez rygorystycznego `.dockerignore` to cichy zabójca buildu — kopiuje do obrazu pliki których tam nie powinno być i blokuje Docker Daemon na przesyłaniu gigabajtów build contextu.

**Dwa problemy:**

- **Wydajność:** lokalny `.venv` z Torchem waży 2–3 GB. Docker Daemon wysyła cały katalog roboczy do build context zanim zacznie build — stąd "wiszące" `Sending build context to Docker daemon`.
- **Bezpieczeństwo:** `.git/` ujawnia pełną historię repozytorium, `.env` trafia do warstwy obrazu, `tests/` i `Makefile` rozszerzają powierzchnię ataku w runtime.

**Kanoniczny `.dockerignore`:**

```dockerignore
# Środowisko wirtualne — lokalny .venv może ważyć 2-3 GB (Torch)
.venv/

# Repozytorium git — nie ujawniamy historii w obrazie produkcyjnym
.git/
.gitignore

# Sekrety — nigdy nie kopiujemy do obrazu
.env
.env.*
!.env.example

# Narzędzia developerskie — nie należą do runtime
tests/
Makefile
.pre-commit-config.yaml

# Cache i artefakty — nie wpływają na działanie aplikacji
__pycache__/
*.pyc
.mypy_cache/
.ruff_cache/
.pytest_cache/
htmlcov/
*.egg-info/

# CI i konfiguracja IDE
.github/
.vscode/
.idea/
```

**Zasada:** każdy plik który nie jest potrzebny do działania aplikacji w runtime — wyklucz. Wątpliwość = wykluczyć.

**Weryfikacja:** `docker build` powinien raportować build context poniżej 1 MB dla typowego projektu bez danych ML. Jeśli context przekracza 10 MB — `.dockerignore` wymaga przeglądu.

---

## Zakazane praktyki

- `COPY pyproject.toml uv.lock* ./` (gwiazdka — lockfile opcjonalny)
- `COPY . .` bez `.dockerignore` — kopiuje `.venv`, `.git`, `.env` do obrazu
- `pip install` w runtime
- Brak `uv.lock` w repo
- Wspólny compose dla wielu środowisk
- `ENV SECRET=value` w Dockerfile
- Wykonywanie migracji przy starcie kontenera
- Montowanie całego `/` lub `/opt/venv` jako named volume
