# Infrastruktura — mapowanie na ADR-020 i ADR-024

Ten katalog zawiera artefakty Infrastructure as Code opisane w `ADR-020 —
Architektura Wdrożeń (Deployment & DataOps)` oraz `ADR-024 — Strategia
Migracji (Expand and Contract)`. Poniżej mapowanie: który plik realizuje
który zapis ADR, i jak się ze sobą łączą.

> **Historia zmian tego katalogu:**
> - Runda 1: audyt wykrył błędy P0 (m.in. `.dockerignore` blokujący testy
>   w obrazie `testing`, konflikt `image:`+`build:` w PRE-PROD łamiący Build
>   Once/Deploy Many, brak wolumenu na statyki pod `read_only: true`) —
>   wszystkie naprawione.

> - Runda 2: audyt nie znalazł już błędów blokujących (P0), wskazał kilka
>   P1/P2/P3 — również naprawione: jawna grupa `--group dev` w `uv sync`
>   (stage `development`/`testing`, zamiast polegania na domyślnej
>   konfiguracji grup), kolejność kroków w `release-application.sh` zmieniona
>   na "najpierw walidacja, potem zapis" (fail-fast-before-mutation), czytelny
>   komunikat błędu gdy `lint_migrations` jeszcze nie istnieje, limity pamięci
>   Redis (`--maxmemory`/`--maxmemory-policy noeviction`), jawne oznaczenie
>   HEALTHCHECK jako blokującego wymogu (nie opcjonalnego dopracowania) oraz
>   udokumentowanie świadomego wyjątku (Caddyfile jako bind mount, nie
>   wersjonowany obraz) i zawężenia `migrate` w `bootstrap.sh` wyłącznie do
>   nowych, pustych środowisk.

> - Runda 3: audyt infrastruktury (bez oceny kodu aplikacji) potwierdził
>   brak błędów klasy "automatyczne uszkodzenie danych" lub "niekontrolowane
>   wdrożenie", ale wykrył dwa ciche błędy funkcjonalne oraz kilka uwag
>   operacyjnych — wszystkie naprawione:
>   - **[błąd] `proxy` (Caddy) w PROD nie miał w ogóle bloku `environment:`**
>     — `DOMAIN_NAME` z `.env` nigdy nie trafiał do kontenera, więc Caddy
>     zawsze cicho używał domyślnego `localhost` z Caddyfile, niezależnie od
>     konfiguracji. Naprawione: `DOMAIN_NAME` wymagany (`:?`) w `proxy`,
>     usunięty domyślny fallback w samym Caddyfile.
>   - **[błąd] brak `REDIS_HOST`/`REDIS_PORT`** w środowisku jakiegokolwiek
>     serwisu (web/celery) we wszystkich plikach compose — dodane wszędzie
>     dla spójności z już istniejącym wzorcem `POSTGRES_HOST`/`POSTGRES_PORT`.
>   - **[błąd] `bootstrap.sh`** wywołuje `createsuperuser --noinput`, ale
>     `DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD` nie były przekazywane do
>     kontenera przez żaden blok `environment:` — dodane do `web` w DEV
>     i PRE-PROD, z `:?` (fail-fast zamiast niejasnego błędu Django).
>   - PRE-PROD oznaczony jawnym ostrzeżeniem przed pomyleniem z PROD (różna
>     warstwa ingress — bezpośredni port 8000 vs Caddy), sugestia
>     `COMPOSE_PROJECT_NAME` dla DEV, `IMAGE_TAG` w `.env.example` bez
>     mylącej wartości domyślnej `latest`, `deploy.resources` dla Celery
>     w PROD, doprecyzowanie opisu "runtime-equivalent poza warstwą ingress"
>     zamiast "architektoniczny klon" dla relacji PRE-PROD/PROD, dodatkowe
>     usunięcie plików infrastrukturalnych (compose*.yml, Dockerfile,
>     Caddyfile, .env.example) z obrazu `production` (Minimal Surface).

> - Runda 4: incydent operacyjny (świeży wolumen po `docker compose down` →
>   `celery_beat` pada na nieistniejących tabelach, bo nikt jeszcze nie
>   wykonał migracji) doprowadził do nazwania i sformalizowania zasady
>   **Declarative Infrastructure, Imperative Operations** — `compose*.yml`
>   opisuje wyłącznie stan docelowy, cała orkiestracja (kolejność, warunki)
>   żyje w `scripts/`. Odrzucona alternatywa: serwis `migrate` w Compose
>   z `depends_on: condition: service_completed_successfully` — techniczne
>   poprawne, ale sprzeczne z ADR-024 (migracje jako świadomy, oddzielny krok
>   release'u, nie automat uruchamiany przy każdym `up`). Dodano
>   `scripts/dev-{up,down,reset,status,logs}.sh` oraz `Makefile.dev-snippet.mk`
>   jako cienkie aliasy — jeden punkt wejścia używany identycznie lokalnie
>   i w CI.

> - Runda 5: **incydent utraty danych** w DEV — `dev-reset` usunął wolumeny
>   bez wykonanego wcześniej backupu (1163 obiekty turystyczne, konta
>   użytkowników; odzyskane z ręcznie posiadanego dumpa). Przyczyna główna:
>   niedopasowanie mountu wolumenu PostgreSQL do wersji obrazu (PG 18 zmienił
>   domyślny `PGDATA` na `/var/lib/postgresql/<major>/docker` — stary mount
>   `.../data` powodował cichy, PUSTY klaster zamiast błędu). Naprawy:
>   `compose.yml` montuje teraz `/var/lib/postgresql` (rodzica, patrz
>   **ADR-025**), dodano `scripts/dev-backup.sh`/`scripts/dev-restore.sh`
>   (zawsze przez kontener, nigdy lokalny `pg_dump`/`pg_restore` — różnica
>   wersji klient/serwer psuje odtwarzanie), `dev-reset.sh` domyślnie
>   proponuje backup przed usunięciem i przypomina o ponownym
>   `bootstrap.sh` po odbudowie, `dev-status.sh` weryfikuje poprawność
>   mountu przez `docker inspect`. Odrzucona propozycja: przemianowanie
>   `dev-up`/`dev-down` na `dev-start`/`dev-stop` — utrzymano istniejące
>   nazwy (spójne ze słownictwem samego `docker compose up`/`down`), zamiast
>   wprowadzać churn bez wyraźnej korzyści.

## Pliki i ich rola

| Plik | Rola | Środowisko |
|---|---|---|
| `Dockerfile` | Multi-stage: `base → builder → {development, testing, production}`. Dev/testing instalują zależności jawnie przez `--group dev` (nie polegają na domyślnej konfiguracji grup w `pyproject.toml`). Dev działa jako nieuprzywilejowany user (build args `USER_UID`/`USER_GID`), production usuwa `tests/`/`docs/` po `COPY --from=builder`. | wszystkie |
| `.dockerignore` | Wyklucza sekrety i venv; **zachowuje** `data/reference/` (Golden Set) **i `tests/`** (potrzebne w obrazie `testing` — patrz niżej). | wszystkie |
| `Caddyfile` | Reverse proxy z automatycznym HTTPS (Let's Encrypt), serwuje statyki i przekazuje ruch do Gunicorna. | PROD |
| `compose.yml` | Wspólna baza: `db` (PostgreSQL 18, wolumen pod `/var/lib/postgresql` — patrz ADR-025), `redis`. Docker nie zna konfiguracji Django. | wszystkie |
| `compose.override.yml` | Ładowany automatycznie przez `docker compose up`. Volume mount kodu, nieuprzywilejowany user dev, Flower (profil `monitoring`). | DEV |
| `compose.test.yml` | Efemeryczne CI — izolacja przez unikalną nazwę projektu + `down -v`, nie przez tmpfs. | TEST |
| `compose.preprod.yml` | Wyłącznie `image:` (bez `build:`) — pobiera już zbudowany obraz z rejestru. Wolumen na statyki pod `read_only`. | PRE-PROD |
| `compose.prod.yml` | Jak PRE-PROD + pełny hardening runtime + serwis `proxy` (Caddy) jako jedyny punkt wejścia z internetu. | PROD |
| `ADR-025-postgresql-volume-layout.md` | Uzasadnienie mountu `/var/lib/postgresql` (nie `.../data`) dla PostgreSQL 18+ — reakcja na realny incydent utraty dostępu do danych opisany w historii zmian niżej. | wszystkie (dokumentacja) |
| `.env.example` | Zmienne czytane przez **sam Docker Compose** (POSTGRES_*, IMAGE_TAG, DOMAIN_NAME, DEV_UID/GID, sekrety wstrzykiwane do PRE-PROD/PROD). | wszystkie (szablon) |
| `.env.shared` | Zmienne nie-poufne czytane przez **AppSettings/Pydantic** wewnątrz kontenera (LANGUAGE_CODE, feature flags). Commitowany do repo. | wszystkie |
| `scripts/entrypoint.sh` | WYŁĄCZNIE start procesu. `wait_for_postgres` wykonuje realną próbę połączenia (psycopg), nie tylko sprawdzenie otwartego portu TCP. Zero migracji, zero side-effectów. | TEST / PRE-PROD / PROD |
| `scripts/release-database.sh` | **Database Release** — linter migracji (ADR-024) + `showmigrations --plan` + `migrate`. | wszystkie (poza DEV) |
| `scripts/release-application.sh` | **Application Release** — `migrate --check` jako gating (wbudowana flaga Django, nie parsowanie tekstu) ➔ `collectstatic` ➔ `check --deploy`. Kolejność celowa: walidacja przed zapisem (fail-fast-before-mutation). | wszystkie (poza DEV) |
| `scripts/release-reference-data.sh` | **Reference Data Release** — walidacja manifestu (checksum + `compatible_schema`) + `restore_reference_data` (idempotentne) + `calculate_neighbors`. Wymaga `<snapshot_id>`. Rollback = ponowne wywołanie z poprzednim `<snapshot_id>`. | wszystkie (poza DEV) |
| `scripts/bootstrap.sh` | Jednorazowa, **ręczna** inicjalizacja nowego środowiska. Sprawdza istnienie superusera jawnie zamiast maskować błędy przez `\|\| true`. | DEV / TEST / PRE-PROD (pierwsze uruchomienie) |
| `scripts/dev-up.sh` | Jedyne źródło prawdy dla startu DEV: Database Release ➔ start reszty usług. `make dev-up` to tylko alias. | DEV |
| `scripts/dev-down.sh` | Zatrzymanie DEV bez usuwania wolumenów (`docker compose down`, nigdy `-v`). | DEV |
| `scripts/dev-reset.sh` | Jedyne miejsce w projekcie z `docker compose down -v` — **domyślnie proponuje backup** przed usunięciem, wymaga wpisania `usun-dane-dev`, po odbudowie przypomina o `bootstrap.sh` dla danych referencyjnych. | DEV |
| `scripts/dev-backup.sh` | Backup bazy do `./backups/` (katalog projektu, poza Dockerem) — zawsze przez `docker compose exec db pg_dump`, format `-Fc`. | DEV |
| `scripts/dev-restore.sh` | Odtworzenie backupu — zawsze przez `docker compose exec db pg_restore` (nigdy lokalny binarny `pg_restore` — niedopasowanie wersji klient/serwer psuje odtwarzanie). Wymaga wpisania `odtworz-baze-dev`. | DEV |
| `scripts/dev-status.sh` | Diagnostyka: kontenery, PostgreSQL, Redis, migracje, Celery worker, **poprawność mountu wolumenu Postgresa (ADR-025)**. Raportuje wszystkie problemy naraz (bez `set -e`). | DEV |
| `scripts/dev-logs.sh` | Cienki wrapper na `docker compose logs -f --tail=N`. | DEV |
| `Makefile.dev-snippet.mk` | Blok do wklejenia do głównego `Makefile` projektu — cienkie aliasy `dev-up`/`dev-down`/`dev-reset`/`dev-status`/`dev-logs`/`dev-backup`/`dev-restore` wywołujące powyższe skrypty. Logika żyje w skryptach, nie w Makefile. | DEV |

## Zasada: Declarative Infrastructure, Imperative Operations

Fundamentalna zasada tego katalogu, nadrzędna wobec pojedynczych plików:

> Pliki `compose*.yml` opisują **wyłącznie docelowy stan** infrastruktury
> (kontenery, sieci, wolumeny, healthchecki). **Nie zawierają** logiki
> wdrożeniowej ani orkiestracyjnej (kolejności akcji, warunków, kroków
> migracyjnych). Wszystkie operacje **zmieniające stan** systemu (start
> w określonej kolejności, bootstrap, migracje, import danych, backup,
> restore, reset środowiska) są wykonywane wyłącznie przez dedykowane
> skrypty (`scripts/*.sh`) lub cienkie aliasy Makefile do tych skryptów.

Konsekwencja praktyczna: `docker compose` (samo w sobie) nigdy nie jest
narzędziem deploymentowym w tym projekcie — jest wyłącznie silnikiem
wykonującym to, co opisano deklaratywnie. Orkiestracją (co, kiedy, w jakiej
kolejności) zajmują się zawsze skrypty. To rozstrzyga np. dlaczego migracje
NIE są zaimplementowane jako `depends_on: condition: service_completed_successfully`
w `compose.override.yml` (rozwiązanie techniczne popularne w mniejszych
projektach Django) — taki zapis wciskałby orkiestrację do warstwy
deklaratywnej i byłby sprzeczny z ADR-024 (migracje jako świadomy, oddzielny
krok, nie automat uruchamiany przy każdym `docker compose up`).

## Świadomie zaakceptowana asymetria: `dev-down` vs `dev-reset`

To rozróżnienie jest celowe, nie przypadkowe nazewnictwo:

- **`dev-down`** = koniec pracy na dziś. Zawsze bezpieczne — nigdy nie usuwa
  wolumenów, nie przyjmuje żadnej flagi zwiększającej destrukcyjność.
- **`dev-reset`** = jedyne miejsce w całym projekcie z `docker compose down -v`.
  Wymaga wpisania z klawiatury dokładnego słowa `usun-dane-dev` — zwykłe
  `[y/N]` jest zbyt łatwe do przypadkowego przeklikania (Enter w pośpiechu,
  domyślnie zaznaczona opcja w skrypcie). Ten sam wzorzec guard już
  stosujecie w `restore_reference_data --force` i w `${VAR:?}` w Compose —
  to jest to samo zabezpieczenie, konsekwentnie zastosowane.

## Dwie odrębne warstwy zmiennych — nie mylić

1. **`.env`** (katalog główny) — czytany automatycznie przez `docker compose`.
   Zawiera to, czego potrzebują same obrazy `postgis/postgis` i `redis`
   (`POSTGRES_USER/PASSWORD/DB`), identyfikatory obrazu (`IMAGE_NAME`,
   `IMAGE_TAG`), domenę dla Caddy (`DOMAIN_NAME`) oraz opcjonalny
   `DEV_UID`/`DEV_GID`. Ten plik **nie jest** czytany przez Pydantic.

2. **`.env.shared` + `.env.dev` / `.env.test` / `.env.preprod` / `.env.prod`**
   — czytane przez `AppSettings` (Pydantic) wewnątrz kontenera, na podstawie
   zmiennej `ENV_FILE`. Dla DEV plik `.env.dev` jest fizycznie obecny w
   kontenerze dzięki volume mount. Dla PRE-PROD/PROD plik **nie istnieje**
   na dysku — `ENV_FILE=.env.preprod`/`.env.prod` pełni tam wyłącznie funkcję
   **identyfikatora profilu konfiguracji** odczytywanego przez `AppSettings`,
   nie gwarancji fizycznej obecności pliku. Realne wartości pochodzą z
   `environment:` w `compose.preprod.yml`/`compose.prod.yml`, wstrzykiwanych
   przez pipeline CI/CD lub menedżer sekretów. `AppSettings` ma ustawione
   `env_file_required=False` właśnie z tego powodu.

## Dlaczego `.dockerignore` NIE wyklucza `tests/`

Pierwsza wersja tego pliku wykluczała `tests/` globalnie — co po cichu
uniemożliwiało uruchomienie `pytest` w obrazie `testing`, bo `.dockerignore`
filtruje build context dla **wszystkich** etapów Dockerfile naraz, nie da się
tym plikiem wykluczyć katalogu tylko z jednego stage'u. Rozwiązanie: `tests/`
trafia do build contextu (i do obrazów `builder`/`testing`), a obraz
`production` usuwa je jawnie przez `RUN rm -rf /app/tests /app/docs` — dzięki
temu Minimal Surface na produkcji jest zachowane bez blokowania CI.

## Typowe komendy

```bash
# DEV — pierwsze uruchomienie (Linux: ustaw DEV_UID/DEV_GID w .env)
echo "DEV_UID=$(id -u)" >> .env
echo "DEV_GID=$(id -g)" >> .env
docker compose build
make dev-up      # = ./scripts/dev-up.sh: Database Release ➔ start usług
make dev-status  # weryfikacja: kontenery / DB / Redis / migracje / Celery
docker compose exec web ./scripts/bootstrap.sh 2026.07.09   # tylko raz, na nowym wolumenie — dane referencyjne

# DEV — codzienna praca
make dev-up      # bezpieczne na świeżym i istniejącym wolumenie
make dev-logs    # podgląd logów (Ctrl+C aby wyjść)
make dev-down    # koniec pracy — NIE usuwa wolumenów
make dev-reset   # DESTRUKCYJNE: pyta o backup, wymaga potwierdzenia, usuwa wolumeny i odbudowuje od zera

# DEV — backup / restore (ZAWSZE przez kontener, nigdy lokalny pg_dump/pg_restore)
make dev-backup                              # -> ./backups/badges_system_<timestamp>.dump
make dev-restore FILE=./backups/nazwa.dump   # wymaga wpisania potwierdzenia — nadpisuje bieżącą bazę

# ⚠️ OBOWIĄZKOWO przed KAŻDĄ zmianą wersji obrazu PostgreSQL (np. 18 -> 19):
make dev-backup
# dopiero potem zmieniaj `image:` w compose.yml — patrz ADR-025

# DEV — Flower na żądanie
docker compose --profile monitoring up -d flower

# TEST — pojedynczy przebieg CI (przykład)
export CI_RUN_ID=$(date +%s)
docker compose -p ci-${CI_RUN_ID} -f compose.yml -f compose.test.yml up -d --wait db redis
docker compose -p ci-${CI_RUN_ID} -f compose.yml -f compose.test.yml run --rm web
docker compose -p ci-${CI_RUN_ID} -f compose.yml -f compose.test.yml down -v --remove-orphans

# PRE-PROD / PROD — kolejność Release'ów (ADR-020, Zasada Kolejności Wdrożeń)
# Obraz musi być WCZEŚNIEJ zbudowany i wypchnięty do rejestru w osobnym kroku CI
# (compose.preprod.yml / compose.prod.yml celowo nie mają `build:`).
docker compose -f compose.yml -f compose.prod.yml run --rm web ./scripts/release-database.sh
docker compose -f compose.yml -f compose.prod.yml run --rm web ./scripts/release-application.sh
docker compose -f compose.yml -f compose.prod.yml up -d
docker compose -f compose.yml -f compose.prod.yml run --rm web \
    ./scripts/release-reference-data.sh 2026.07.09   # osobno, tylko gdy Golden Set się zmienił
```

### Backupy — `./backups/` musi być w `.gitignore`

`dev-backup.sh` tworzy pliki w `./backups/` w katalogu projektu (celowo poza
Dockerem — patrz Runda 5 w historii zmian). To są **dane**, nie kod — upewnij
się, że masz w swoim `.gitignore`:
```
backups/
```
W przeciwnym razie ryzykujesz zacommitowanie zrzutu bazy (potencjalnie
z danymi osobowymi użytkowników) do repozytorium Git.

### Integracja z istniejącym Makefile

`Makefile.dev-snippet.mk` nie jest samodzielnym plikiem wykonywalnym — to
blok do wklejenia do już istniejącego `Makefile` projektu (ten katalog nie
zna pełnej zawartości Waszego `Makefile`, więc nie nadpisuje go automatycznie).
Dwa sposoby użycia:

```bash
# Wariant A — wklej zawartość ręcznie do sekcji INFRA swojego Makefile

# Wariant B — dołącz jako include (wymaga GNU Make)
echo "include Makefile.dev-snippet.mk" >> Makefile
```

## Świadomie zaakceptowane kompromisy (nie błędy — decyzje z uzasadnieniem)

- **`Caddyfile` jako bind mount w PROD** (`./Caddyfile:/etc/caddy/Caddyfile:ro`),
  nie jako część wersjonowanego obrazu. Odstępstwo od pełnej Immutable
  Infrastructure — akceptowalne dla wdrożenia tej skali, dopóki konfiguracja
  proxy zmienia się rzadko i ręcznie. Jeśli zacznie się zmieniać równolegle
  z Release'ami aplikacji, rozważcie przeniesienie do osobnego, wersjonowanego
  obrazu budowanego w tym samym pipeline CI.
- **Tagi obrazów bazowych (`postgis/postgis:15-3.3`, `redis:7.4-alpine`)**
  pinowane do minor+patch, nie do pełnego digestu SHA. Spójne z filozofią
  już przyjętą w tym projekcie dla obrazu Pythona (`08-base-image-policy.md`):
  pinujemy minor w pliku, dokładny digest logujemy w CI jako ślad audytowy,
  zamiast ręcznie utrzymywać SHA w każdym pliku compose.

## Znane luki / do uzupełnienia w kodzie aplikacji (BLOKUJĄCE przed pierwszym wdrożeniem)

Poniższe elementy są zakładane przez skrypty i pliki compose, ale ich
implementacja leży po stronie kodu Django, nie infrastruktury:

- **[BLOKUJĄCE] Widok `/health/`** zwracający `200 OK` bez wymogu
  uwierzytelnienia (`ALLOWED_HOSTS` musi zawierać `localhost`/`127.0.0.1` dla
  Docker `HEALTHCHECK`). Bez tego widoku obraz `production` wchodzi w pętlę
  restartów (`Running → unhealthy → restart → ...`) od pierwszego uruchomienia.
  Traktujcie to jako część Definition of Done tego Dockerfile'a, nie opcjonalne
  dopracowanie na później. Docelowo rozważcie rozdzielenie na `/health/live`
  (proces żyje) i `/health/ready` (DB/Redis/migracje gotowe), zgodnie
  z konwencją Kubernetes.
- Komenda zarządzająca `validate_reference_manifest` (walidacja `sha256`
  zawartości snapshotu — nie manifestu — oraz pola `compatible_schema`).
- Komenda zarządzająca `lint_migrations` (ADR-024, pkt 6) — statyczna
  introspekcja `Migration.operations` względem whitelisty dozwolonych
  operacji. Wywoływana w `release-database.sh` jako druga linia obrony;
  podstawowe egzekwowanie powinno i tak odbywać się w CI na etapie PR.
- Test regresyjny potwierdzający idempotentność `restore_reference_data`
  (dwukrotne uruchomienie na tym samym snapshocie bez zmiany stanu bazy) —
  wymagany przez ADR-020 jako obowiązkowa część potoku CI.
- Rejestr Version Matrix (artefakt audytowy) — format i miejsce
  przechowywania świadomie pozostawione poza zakresem ADR-020 i tych plików.
- `STATIC_ROOT` w `settings.py` musi wskazywać na `/app/staticfiles` —
  zgodnie z wolumenem zamontowanym w `compose.preprod.yml`/`compose.prod.yml`.
- Dla `compose.test.yml`: migracje test-database są aplikowane automatycznie
  przez `pytest-django` przy tworzeniu bazy testowej (zachowanie domyślne,
  o ile nie użyto `--no-migrations`) — nie wymaga osobnego kroku `migrate`
  w tym pliku compose. Jeśli testy integracyjne korzystają z fixture'ów
  danych referencyjnych, wczytanie ich jest odpowiedzialnością samych testów
  (np. fixture pytest), nie tego pliku infrastruktury.
- `[tool.uv] default-groups` w `pyproject.toml` — Dockerfile jawnie żąda
  `--group dev` w stage'ach `development`/`testing`, więc nie jest to już
  luka blokująca, ale warto zweryfikować, że grupa nazywa się faktycznie
  `dev` w Waszym `pyproject.toml` (jeśli nazwa jest inna, np. `development`,
  trzeba to dopasować w Dockerfile).
