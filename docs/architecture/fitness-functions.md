# Architecture Fitness Functions

> **Wersja:** 1.0  
> **Data:** 2026-08-26  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Każda reguła architektoniczna z `tests/architecture/` ma tu swój wpis. Test nie jest tylko testem — jest formalnie zidentyfikowaną fitness function.
> **Master index:** [`docs/architecture/governance.md`](governance.md) zawiera pełny przegląd wszystkich mechanizmów governance, ich charakteru blocking/advisory, i kolejności w CI.

---

## Format wpisu

| Pole | Opis |
|------|------|
| **ID** | Unikalny identyfikator: `FF-NNN` |
| **Nazwa** | Krótki opis fitness function |
| **Mechanizm** | Narzędzie egzekwujące regułę |
| **Chroni** | Co się stanie, jeśli reguła zostanie złamana |
| **Powiązanie** | ADR lub inny kontekst decyzyjny |
| **Status** | Poziom egzekwowania: Gate / Diagnostic / Advisory |

---

## Rejestr Fitness Functions

### FF-001: Dependency Direction

| Pole | Wartość |
|------|---------|
| **Nazwa** | Dependency Direction |
| **Mechanizm** | Import Linter + `tests/architecture/test_dependency_direction.py` |
| **Chroni** | Kierunek zależności między warstwami (domain ← application ← infrastructure ← apps) |
| **Powiązanie** | ADR-001 (Hexagonal Architecture) |
| **Status** | Diagnostic |

**Opis:**
Import Linter egzekwuje kierunek zależności na poziomie pakietów. Test w `tests/architecture/` daje dodatkowy, domenowy komunikat w standardowym `pytest`:

```
Domain purity violated:
domain/foo.py imports django.db.models
```

> **Uwaga:** Test `test_dependency_direction.py` jest komplementarny do Import Lintera. Import Linter jest źródłem prawdy dla kierunku zależności; test dostarcza diagnostykę w formacie pytest. Nie powinno się traktować ich jako niezależnych, równorzędnych mechanizmów. Status: **Diagnostic**.

---

### FF-002: Domain Purity

| Pole | Wartość |
|------|---------|
| **Nazwa** | Domain Purity |
| **Mechanizm** | `tests/architecture/test_domain_purity.py` |
| **Chroni** | Czystość warstwy domenowej — brak modeli Django ORM i zależności od frameworków |
| **Powiązanie** | ADR-001 (Hexagonal Architecture) |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że żaden plik w `domain/` nie dziedziczy po `django.db.models.Model`. Import Linter współpracuje z tym testem przez kontrakt `domain-purity`, który blokuje importy frameworków i innych warstw. Test koncentruje się na invariantie behawioralnym (brak Model w domenie), który Import Linter nie może wykryć.

> **Uwaga:** Test nie powtarza już sprawdzania importów — to jest obowiązek Import Lintera (`domain-purity`). Test chroni tylko invariant, który Import Linter nie obejmuje: brak dziedziczenia po `Model` w warstwie domenowej.

---

### FF-003: Repository Contracts

| Pole | Wartość |
|------|---------|
| **Nazwa** | Repository Contracts |
| **Mechanizm** | `tests/architecture/test_repository_contracts.py` |
| **Chroni** | Semantyczny kontrakt: każdy adapter implementuje wszystkie metody swojego portu |
| **Powiązanie** | ADR-001 (Hexagonal Architecture), ADR-002 (Ports & Adapters) |
| **Status** | Gate |

**Opis:**
Import Linter sprawdza, czy `application → infrastructure` jest dozwolone. Test sprawdza, czy `OsmRepository` implementuje `OsmRepositoryPort` i czy nie brakuje żadnych metod. To jest architektoniczny kontrakt behawioralno-strukturalny.

---

### FF-004: API DTO Gating

| Pole | Wartość |
|------|---------|
| **Nazwa** | API DTO Gating |
| **Mechanizm** | `tests/architecture/test_api_dto_gating.py` |
| **Chroni** | Wszystkie widoki modyfikujące stan (POST/PATCH) używają DTO Pydantic do walidacji |
| **Powiązanie** | ADR-016 (Rozdzielenie tożsamości od autoryzacji) |
| **Status** | Gate |

**Opis:**
Test wykrywa widoki, które parsują `request.body` lub JSON bez użycia DTO Pydantic. Zapobiega przetwarzaniu niezwalidowanego wejścia.

---

### FF-005: DI Container Completeness

| Pole | Wartość |
|------|---------|
| **Nazwa** | DI Container Completeness |
| **Mechanizm** | `tests/architecture/test_di_container_completeness.py` |
| **Chroni** | Wszystkie UseCase'y i Serwisy są zarejestrowane w `AppContainer` |
| **Powiązanie** | ADR-001 (Hexagonal Architecture) |
| **Status** | Gate |

**Opis:**
Test zabezpiecza przed sytuacją: dodano `NewBadgeUseCase`, zapomniano zarejestrować w `AppContainer`, aplikacja rzuca `AttributeError` w runtime.

---

### FF-006: DTO Naming Convention

| Pole | Wartość |
|------|---------|
| **Nazwa** | DTO Naming Convention |
| **Mechanizm** | `tests/architecture/test_dto_naming_convention.py` |
| **Chroni** | Konwencja nazewnictwa DTO: nowe klasy kończą się na `InputDTO`, `RequestDTO` lub `ResponseDTO` |
| **Powiązanie** | — |
| **Status** | Advisory |

**Opis:**
Test akceptuje istniejące legacy DTO (np. `TouristProfileDTO`), ale wymusza konwencję na nowych klasach. Redukuje dług poznawczy przy onbordu.

> **Uwaga:** To jest reguła stylistyczna / konwencja, a nie invariant architektoniczny. Status: **Advisory**. Nie powinna blokować CI — służy spójności zespołu, a nie bezpieczeństwu systemu.

---

### FF-007: No Primitive Obsession

| Pole | Wartość |
|------|---------|
| **Nazwa** | No Primitive Obsession |
| **Mechanizm** | `tests/architecture/test_no_primitive_obsession.py` |
| **Chroni** | Use Case'y nie zwracają surowych `dict` lub `Any` — wymagają dedykowanych DTO |
| **Powiązanie** | AUDYT-124 |
| **Status** | Gate |

**Opis:**
Test wybucha, jeśli use case deklaruje w typie zwracanym `dict`, `Any` lub `list[...]`. Wymusza użycie ResponseDTO do komunikacji z API i widokami.

---

### FF-008: Migration Idempotency

| Pole | Wartość |
|------|---------|
| **Nazwa** | Migration Idempotency (Expand & Contract) |
| **Mechanizm** | `tests/architecture/test_migration_idempotency.py` |
| **Chroni** | Migracje DDL nie mieszają operacji ekspansji i kontrakcji w jednym pliku |
| **Powiązanie** | ADR-024 (Lint Migracji) |
| **Status** | Diagnostic |

**Opis:**
Test egzekwuje zasadę Expand & Contract: migracja nie może zawierać zarówno `AddField` jak i `RemoveField`. Automatycznie zwalnia dewelopera z ręcznej weryfikacji kroków wdrożeniowych.

> **Uwaga:** Test jest heurystyką, a nie invariantem architektonicznym. Django migration może legalnie zawierać różne operacje DDL, jeśli jest to świadomie zaprojektowana migracja. Rzeczywisty kontrakt to: "deployment nie może powodować downtime / breaking schema change". Status: **Diagnostic**.

---

### FF-009: God Class Prevention

| Pole | Wartość |
|------|---------|
| **Nazwa** | God Class Prevention |
| **Mechanizm** | `tests/architecture/test_god_class_prevention.py` |
| **Chroni** | Żaden plik `models.py` nie przekracza progu 20 modeli Django |
| **Powiązanie** | — |
| **Status** | Diagnostic |

**Opis:**
Test wymusza dekompozycję modułów. Przeciwdziała powstawaniu plików takich jak `apps/badges/models.py` (obecnie 19 modeli, w tym klasy abstrakcyjne). Próg 20 gwarantuje, że obecny stan jest akceptowany, ale kolejne znacząco powiększające się moduły zostaną wykryte.

> **Uwaga:** Test korzysta z AST do wykrywania klas dziedziczących po typie kończącym się na `Model` (w tym `models.Model`, `gis_models.Model`, `RegionBaseModel`). Liczba modeli w pliku jest proxy metric, a nie rzeczywistym invariantem architektonicznym. 5 klas może tworzyć potężnego God Object, a 20 może być akceptowalnych. Test służy jako trend/smell detector, a nie blocking rule. Status: **Diagnostic**.

---

### FF-010: Badge Rule Immutability

| Pole | Wartość |
|------|---------|
| **Nazwa** | Badge Rule Immutability |
| **Mechanizm** | `tests/architecture/test_badge_rule_immutability.py` |
| **Chroni** | Wszystkie reguły biznesowe dziedziczące po `BadgeRule` są `@dataclass(frozen=True)` |
| **Powiązanie** | ADR-003 (Silnik Reguł Biznesowych) |
| **Status** | Gate |

**Opis:**
Test gwarantuje brak zjawiska State Mutilation podczas współbieżnego oceniania wielu turystów. Wymusza deep immutability na wszystkich strategiach walidacyjnych.

---

## Podsumowanie

| ID | Fitness Function | Mechanizm | Chroni | Powiązanie | Status |
|----|------------------|-----------|--------|------------|--------|
| FF-001 | Dependency Direction | Import Linter + pytest | kierunek zależności | ADR-001 | **Diagnostic** |
| FF-002 | Domain Purity | pytest | Clean Domain | ADR-001 | Blocking |
| FF-003 | Repository Contracts | pytest | Ports & Adapters | ADR-001, ADR-002 | Blocking |
| FF-004 | API DTO Gating | pytest | API boundary | ADR-016 | Blocking |
| FF-005 | DI Container Completeness | pytest | Composition Root | ADR-001 | Blocking |
| FF-006 | DTO Naming Convention | pytest | konwencja | — | Advisory |
| FF-007 | No Primitive Obsession | pytest | application boundary | AUDYT-124 | Blocking |
| FF-008 | Migration Idempotency | pytest | Expand & Contract | ADR-024 | **Diagnostic** |
| FF-009 | God Class Prevention | pytest | modularność | — | **Diagnostic** |
| FF-010 | Badge Rule Immutability | pytest | domain invariants | ADR-003 | Blocking |
| FF-011 | Dockerfile Hygiene | Hadolint | standard konstrukcji obrazu | ADR-020 | Advisory |
| FF-012 | Compose Security | Checkov | konfiguracja IaC | ADR-020 | Advisory |
| FF-013 | Image Vulnerability Scanning | Trivy | CVE w obrazie | ADR-020 | Blocking |
| FF-014 | Docker Bench Security | Docker Bench | konfiguracja hosta Docker | ADR-020 | Advisory |
| FF-015 | Compose Health Checks | pytest | healthcheck w Compose | ADR-020 | Blocking |
| FF-016 | API Exception Handling | pytest | obsługa ApplicationException | — | Blocking |
| FF-017 | Request ID Contract | pytest | korelacja żądań | — | Blocking |
| FF-018 | No Sensitive Data in Logs | pytest | brak wrażliwych danych w logach | — | Advisory |
| FF-019 | Structured Error Context | pytest | RFC 7807 + request_id | — | Blocking |
| FF-020 | Health Check Semantics | pytest | semantyka healthcheck | ADR-020 | Blocking |
| FF-021 | Lockfile Integrity | pytest | `uv.lock` jest committed i śledzony | — | Blocking |
| FF-022 | Dependency Groups Separation | pytest | narzędzia dev/test nie mieszają się z runtime | — | Advisory |
| FF-023 | Fitness Function Registry Completeness | pytest | wszystkie FF mają wpis w rejestrze i wymagane pola | — | Blocking |

---

## Grupa 8: Infrastructure / Runtime Architecture & Security Governance

Ta grupa pilnuje architektury poza kodem Pythona — kontenery, Compose, obrazy, sekrety, uprawnienia.

| ID | Nazwa | Mechanizm | Chroni | Powiązanie | Status |
|----|-------|-----------|--------|------------|--------|
| FF-011 | Dockerfile Hygiene | Hadolint | standard konstrukcji obrazu | ADR-020 | Advisory |
| FF-012 | Compose Security | Checkov | konfiguracja IaC | ADR-020 | Advisory |
| FF-013 | Image Vulnerability Scanning | Trivy | CVE w obrazie kontenerowym | ADR-020 | Blocking |
| FF-014 | Docker Bench Security | Docker Bench | konfiguracja hosta Docker | ADR-020 | Advisory |
| FF-015 | Compose Health Checks | pytest | healthcheck w Compose | ADR-020 |
| FF-016 | API Exception Handling | pytest | obsługa ApplicationException | — |

### FF-011: Dockerfile Hygiene

| Pole | Wartość |
|------|---------|
| **Nazwa** | Dockerfile Hygiene |
| **Mechanizm** | Hadolint (`make hadolint`) |
| **Chroni** | Standard konstrukcji obrazu, best practices Dockerfile |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Advisory |

**Opis:**
Hadolint sprawdza Dockerfile pod kątem:
- Pinowania wersji obrazów bazowych
- Pinowania wersji pakietów APT
- Poprawnej konstrukcji warstw
- Ustawień użytkownika

### FF-012: Compose Security

| Pole | Wartość |
|------|---------|
| **Nazwa** | Compose Security |
| **Mechanizm** | Checkov (`make checkov`) |
| **Chroni** | Konfigurację IaC — Compose files pod kątem bezpieczeństwa |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Advisory |

**Opis:**
Checkov skanuje compose.yml i środowiskowe override'y pod kątem:
- Uruchamiania kontenerów jako root
- Braku ograniczeń capabilities
- Niebezpiecznych ustawień sieci
- Braku healthcheck

### FF-013: Image Vulnerability Scanning

| Pole | Wartość |
|------|---------|
| **Nazwa** | Image Vulnerability Scanning |
| **Mechanizm** | Trivy (`make security-audit`) |
| **Chroni** | CVE w obrazie kontenerowym, zależnościach OS i Python |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Gate |

**Opis:**
Trivy skanuje obraz kontenerowy pod kątem:
- Podatności w pakietach OS
- Podatności w zależnościach Python
- Sekretów w obrazie
- SBOM (Software Bill of Materials)

---

### FF-014: Docker Bench Security

| Pole | Wartość |
|------|---------|
| **Nazwa** | Docker Bench Security |
| **Mechanizm** | Docker Bench (`make docker-bench`, na żądanie) |
| **Chroni** | Konfigurację środowiska Docker hosta — demon, sieć, uprawnienia, logging |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Advisory |

**Opis:**
Docker Bench to audyt oparty na CIS Docker Benchmark. W przeciwieństwie do Hadolint/Checkov (analizują IaC w repo), Docker Bench sprawdza rzeczywistą konfigurację demona Dockera na hoście.

> **Uwaga:** Projekt upstream `docker/docker-bench` został zarchiwizowany. Target `make docker-bench` pozostawiono jako placeholder na przyszły audyt hosta Docker — jeśli pojawi się aktywny successor, zaktualizuj komendę w Makefile.

Używa się go **na żądanie**, w zaufanych środowiskach (lokalnie), nigdy automatycznie w CI:

```bash
make docker-bench
```

Wymaga dostępu do `/var/run/docker.sock` hosta.

---

## Grupa 9: Operational / Runtime Governance

Ta grupa pilnuje architektury runtime — health checks, error handling, observability.

| ID | Nazwa | Mechanizm | Chroni | Powiązanie | Status |
|----|-------|-----------|--------|------------|--------|
| FF-015 | Compose Health Checks | pytest | Wszystkie services mają healthcheck | ADR-020 | Blocking |
| FF-016 | API Exception Handling | pytest | Widoki łapią ApplicationException | — | Blocking |

> **Uwaga FF-015:** Test weryfikuje obecność `healthcheck`, ale nie jego jakość. Healthcheck typu `curl localhost:8000` potwierdza tylko, że proces HTTP odpowiada, nie że aplikacja może obsługiwać ruch. Polityka: healthcheck musi sprawdzać rzeczywistą zdolność komponentu do pełnienia swojej funkcji (readiness/liveness), a nie wyłącznie istnienie procesu. Gdy projekt przejdzie do TEST/PROD, rozważyć rozszerzenie testu o weryfikację znaczenia healthcheck.

### FF-015: Compose Health Checks

| Pole | Wartość |
|------|---------|
| **Nazwa** | Compose Health Checks |
| **Mechanizm** | `tests/architecture/test_health_checks.py` |
| **Chroni** | Wszystkie services mają `healthcheck` |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że każdy service w `compose*.yml` (poza `db` i `redis`) definiuje `healthcheck`. Gwarantuje to, że Docker może wykryć niezdrowe kontenery i zrestartować je automatycznie.

### FF-016: API Exception Handling

| Pole | Wartość |
|------|---------|
| **Nazwa** | API Exception Handling |
| **Mechanizm** | `tests/architecture/test_exception_handling.py` |
| **Chroni** | Widoki łapią `ApplicationException` |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test sprawdza, że każda metoda `post`/`patch` w `apps/api/views.py` ma `except ApplicationException`. Zapewnia spójną obsługę błędów biznesowych i zapobiega wyciekowi stacktrace'ów do klienta.

---

## Grupa 10: Observability Governance

Ta grupa pilnuje gotowości aplikacji do przyszłego wdrożenia observability — request_id, strukturalne logowanie, semantyka health check. Nie instaluje narzędzi zewnętrznych; definiuje kontrakty, które później umożliwią integrację z Sentry, Prometheus, Loki lub OpenTelemetry bez przebudowy architektury.

| ID | Nazwa | Mechanizm | Chroni | Powiązanie | Status |
|----|-------|-----------|--------|------------|--------|
| FF-017 | Request ID Contract | pytest | korelacja żądań | — | Blocking |
| FF-018 | No Sensitive Data in Logs | pytest | brak wrażliwych danych w logach | — | Advisory |
| FF-019 | Structured Error Context | pytest | RFC 7807 + request_id | — | Blocking |
| FF-020 | Health Check Semantics | pytest | semantyka healthcheck | ADR-020 | Blocking |

### FF-017: Request ID Contract

| Pole | Wartość |
|------|---------|
| **Nazwa** | Request ID Contract |
| **Mechanizm** | `tests/architecture/test_request_id_contract.py` |
| **Chroni** | Korelacja żądań |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że middleware `RFC7807ErrorMiddleware` generuje `request_id` jeśli brak nagłówka `X-Request-ID`, a jeśli nagłówek jest obecny — honoruje go (korelacja między systemami). `request_id` jest wstrzykiwany do obiektu `request` i do kontekstu Loguru, więc wszystkie logi podczas żądania automatycznie go dziedziczą.

> **Polityka:** W produkcji `X-Request-ID` powinien być ustawiany przez reverse proxy (Caddy/Nginx). Jeśli nagłówek jest brakujący lub fałszywy, middleware generuje własny identyfikator. Nigdy nie zwracamy `request_id` z zewnątrz bez walidacji.

### FF-018: No Sensitive Data in Logs

| Pole | Wartość |
|------|---------|
| **Nazwa** | No Sensitive Data in Logs |
| **Mechanizm** | `tests/architecture/test_no_sensitive_data_in_logs.py` |
| **Chroni** | Brak wrażliwych danych w logach |
| **Powiązanie** | — |
| **Status** | Advisory |

**Opis:**
Test skanuje komunikaty logów w `application/`, `infrastructure/` i `apps/` pod kątem słów kluczowych: `password`, `passwd`, `secret`, `token`, `api_key`, `apikey`, `authorization`, `credentials`, `private_key`, `session_id`, `session_token`, `session_key`. Ma charakter Advisory — automatyczne wykrywanie może generować false positives.

> **Polityka:** Dane wrażliwe nigdy nie trafiają do logów. Jeśli potrzebujesz zapisać kontekst zdarzenia, używaj anonimizowanych identyfikatorów (np. `user_id`, `profile_id`). Słowo `session` zostało zastąpione konkretnymi `session_id`/`session_token`/`session_key`, aby uniknąć false positives z logami typu "user session expired".

### FF-019: Structured Error Context

| Pole | Wartość |
|------|---------|
| **Nazwa** | Structured Error Context |
| **Mechanizm** | `tests/architecture/test_structured_error_context.py` |
| **Chroni** | RFC 7807 + request_id |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że każda metoda `post`/`patch` w `apps/api/views.py`, która łapie `ApplicationException`, używa `_handle_application_exception` lub `_problem_detail`. Oba helpery wstrzykują `request_id` do odpowiedzi RFC 7807, co pozwala na korelację między logami a odpowiedziami API.

### FF-020: Health Check Semantics

| Pole | Wartość |
|------|---------|
| **Nazwa** | Health Check Semantics |
| **Mechanizm** | `tests/architecture/test_health_checks.py` |
| **Chroni** | Semantyka healthcheck |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Gate |

**Opis:**
FF-015 weryfikuje obecność `healthcheck`. FF-020 weryfikuje jego semantykę: endpoint `/health/` sprawdza połączenie z bazą danych (`SELECT 1`) i Redisem (`cache.set`/`cache.get`). Jeśli któraś zależność jest niedostępna, endpoint zwraca `503 Service Unavailable`. W środowisku testowym (`APP_ENV=test`) healthcheck pomija sprawdzanie zależności, aby nie wymagać uruchomionego PostgreSQL/Redis dla testów jednostkowych.

> **Uwaga:** W produkcji `APP_ENV=production` healthcheck jest pełny. W testach jednostkowych (`SimpleTestCase`) nie ma dostępu do DB, więc pomijane są sprawdzania — to nie jest luką, a świadomym wyjątkiem umożliwiającym uruchamianie testów bez infrastruktury.

---

## Cykl Governance

```
                    ┌───────────────┐
                    │     ADR       │
                    │    DECIDE     │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │      C4       │
                    │  DOCUMENT     │
                    └───────┬───────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
       Import Linter              Architecture Tests
       ENFORCEMENT                FITNESS FUNCTIONS
              │                           │
              └─────────────┬─────────────┘
                            ▼
                    ┌───────────────┐
                    │ Radon/Xenon   │
                    │   MEASURE      │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │     wily      │
                    │    EVOLVE     │
                    └───────────────┘

                 DISCOVER
                    ↑
              pydeps/pyreverse

                  INFRASTRUCTURE GOVERNANCE
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
       Checkov           Hadolint          Trivy
           │                │                │
           ▼                ▼                ▼
        Compose         Dockerfile       Image/SBOM
       / IaC                              / CVE
           │                │                │
           └────────────────┼────────────────┘
                            │
                            ▼
                     CI SECURITY GATE

                  OPERATIONAL GOVERNANCE
                            │
           ┌────────────────┼────────────────┐
           │                │                │
           ▼                ▼                ▼
       Health Checks   Error Handling   Observability
           │                │                │
           ▼                ▼                ▼
         Compose           API Views       Logging / Metrics
        healthcheck       Exception        (future)
```

---

## Grupa 11: Supply Chain & Dependency Governance

Ta grupa pilnuje kontroli nad łańcuchem dostaw oprogramowania — od lockfile po przyszłe SBOM i provenance. Nie dodaje nowych narzędzi; definiuje kontrakty, które wykorzystują już istniejące mechanizmy (`uv.lock`, `pyproject.toml`, Trivy, OSV-Scanner).

| ID | Nazwa | Mechanizm | Chroni | Powiązanie | Status |
|----|-------|-----------|--------|------------|--------|
| FF-021 | Lockfile Integrity | pytest | `uv.lock` jest committed i śledzony | — | Blocking |
| FF-022 | Dependency Groups Separation | pytest | narzędzia dev/test nie mieszają się z runtime | — | Advisory |

### FF-021: Lockfile Integrity

| Pole | Wartość |
|------|---------|
| **Nazwa** | Lockfile Integrity |
| **Mechanizm** | `tests/architecture/test_lockfile_integrity.py` + pre-commit `uv lock --check` |
| **Chroni** | `uv.lock` jest committed i śledzony |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że `uv.lock` istnieje i jest śledzony przez Git. Pre-commit hook `uv lock --check` gwarantuje, że lockfile jest zsynchronizowany z `pyproject.toml`.

### FF-022: Dependency Groups Separation

| Pole | Wartość |
|------|---------|
| **Nazwa** | Dependency Groups Separation |
| **Mechanizm** | `tests/architecture/test_dependency_groups_separation.py` |
| **Chroni** | Narzędzia dev/test nie mieszają się z runtime |
| **Powiązanie** | — |
| **Status** | Advisory |

**Opis:**
Test weryfikuje, że zależności z `[dependency-groups.dev]` i `[dependency-groups.test]` nie pojawiają się w głównej liście `dependencies` w `pyproject.toml`. Zapewnia, że narzędzia deweloperskie (ruff, mypy, semgrep, radon, xenon) nie trafiają do obrazu produkcyjnego.

> **Polityka:** CI używa `uv sync --group test --no-dev` dla testów i `uv sync --no-dev` dla PROD. Narzędzia analizy bezpieczeństwa (Semgrep, Radon, Xenon) są w `dev`, ale CI instaluje je jawnie w osobnym stage'ie.

---

## Fitness Function Quality Policy

Każda nowa lub modyfikowana fitness function musi przejść kontrolę jakości, aby uniknąć fałszywego poczucia bezpieczeństwa.

### Wymagania minimalne

Każda FF w rejestrze musi mieć zdefiniowane:

| Pole | Opis |
|------|------|
| **Invariant** | Co dokładnie chroni — sformułowanie behawioralne, nie techniczne. |
| **Detection mechanism** | AST / runtime / static analysis / filesystem / composite. |
| **False-positive analysis** | Jakie legalne przypadki mogą być błędnie wykryte? |
| **False-negative analysis** | Jakie naruszenia mogą zostać przeoczone? |
| **Blocking / Advisory** | Czy łamanie reguły blokuje CI? |
| **Owner** | Osoba/moduł odpowiedzialny za utrzymanie FF. |
| **Rationale** | Dlaczego ta reguła istnieje — powiązanie z ADR, AUDYT lub doświadczeniem. |

### Zasady projektowania FF

1. **Preferuj semantykę nad tekstem** — zamiast `grep "session"` używaj AST do wykrywania `session_id`/`session_token`/`session_key`.
2. **Preferuj strukturę kodu nad ciągiem znaków** — zamiast dopasowania `(Model)` używaj AST do wykrywania dziedziczenia po typie kończącym się na `Model`.
3. **Ratchet, nie target** — próg FF powinien gwarantować, że sytuacja nie się pogarsza, nawet jeśli obecny stan nie jest idealny.
4. **Testuj mechanizm, nie tylko kod** — dla złożonych FF dodaj przynajmniej jedną kontrolę, że test wykrywa naruszenie (przypadek negatywny).
5. **Dokumentuj wyjątki** — jeśli FF ma wyjątki, wymień je explicite z uzasadnieniem.

### Metryki governance

| Metryka | Cel |
|---------|-----|
| Liczba FF bez dokumentacji | 0 |
| Liczba FF bez false-positive analysis | 0 |
| Liczba FF bez false-negative analysis | 0 (Advisory mogą mieć opisane ryzyko) |
| Liczba FF bez testu negatywnego | 0 dla Blocking FF |

#### FF-023: Fitness Function Registry Completeness

| Pole | Wartość |
|------|---------|
| **Nazwa** | Fitness Function Registry Completeness |
| **Mechanizm** | `tests/architecture/test_fitness_function_registry.py` |
| **Chroni** | Wszystkie FF mają wpis w rejestrze i wymagane pola |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że każda FF wymieniona w `governance.md` ma odpowiadający wpis w `fitness-functions.md` z wymaganymi polami: Nazwa, Mechanizm, Chroni, Powiązanie, Opis. Gwarantuje, że rejestr FF nie ulega rozjeźdzeniu z rzeczywistym stanem governance.

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-08-26 | Dominik / AI Architect | Utworzenie rejestru fitness functions (FF-001..FF-010) |
