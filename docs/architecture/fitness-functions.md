# Architecture Fitness Functions

> **Wersja:** 2.0  
> **Data:** 2026-08-27  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Każda reguła architektoniczna ma tu swój wpis jako Fitness Function (FF). FF odpowiada na pytanie „co chronimy?”, a tool/mechanizm odpowiada na „jak to sprawdzamy?”. Jeden FF może być realizowany przez wiele tooli, a jeden tool może realizować wiele FF.
> **Master index:** [`docs/architecture/governance.md`](governance.md) zawiera pełny przegląd toolingu, tier’ów, i mapowanie FF ↔ Tools.

---

## Format wpisu

| Pole | Opis |
|------|------|
| **ID** | Unikalny identyfikator: `FF-NNN` |
| **Nazwa** | Krótki opis fitness function |
| **Chroni** | Co się stanie, jeśli reguła zostanie złamana |
| **Powiązanie** | ADR lub inny kontekst decyzyjny |
| **Status** | Poziom zaufania: Gate / Diagnostic / Experimental |
| **Tool** | Narzędzie/tool realizujący tę FF |

---

## Mapowanie FF → Tools

| FF | Tool | Tier | Mode |
|----|------|------|------|
| FF-001 | Import Linter | Gate | blocking |
| FF-001 | pytest | Diagnostic | advisory |
| FF-002 | Import Linter | Gate | blocking |
| FF-002 | pytest | Gate | blocking |
| FF-003 | pytest | Gate | blocking |
| FF-004 | pytest | Gate | blocking |
| FF-005 | pytest | Gate | blocking |
| FF-006 | pytest | Diagnostic | advisory |
| FF-007 | pytest | Gate | blocking |
| FF-008 | pytest | Diagnostic | advisory |
| FF-009 | pytest | Diagnostic | advisory |
| FF-010 | pytest | Gate | blocking |
| FF-011 | Hadolint | Diagnostic | advisory |
| FF-012 | Checkov | Diagnostic | advisory |
| FF-013 | Trivy | Gate | blocking |
| FF-014 | Docker Bench | Diagnostic | advisory |
| FF-015 | pytest | Gate | blocking |
| FF-016 | pytest | Gate | blocking |
| FF-017 | pytest | Gate | blocking |
| FF-018 | pytest | Diagnostic | advisory |
| FF-019 | pytest | Gate | blocking |
| FF-020 | pytest | Gate | blocking |
| FF-021 | pytest | Gate | blocking |
| FF-022 | pytest | Diagnostic | advisory |
| FF-023 | pytest | Gate | blocking |

---

## Rejestr Fitness Functions

### FF-001: Dependency Direction

| Pole | Wartość |
|------|---------|
| **Nazwa** | Dependency Direction |
| **Tool** | Import Linter + `tests/architecture/test_dependency_direction.py` |
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
| **Tool** | `tests/architecture/test_domain_purity.py` |
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
| **Tool** | `tests/architecture/test_repository_contracts.py` |
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
| **Tool** | `tests/architecture/test_api_dto_gating.py` |
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
| **Tool** | `tests/architecture/test_di_container_completeness.py` |
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
| **Tool** | `tests/architecture/test_dto_naming_convention.py` |
| **Chroni** | Konwencja nazewnictwa DTO: nowe klasy kończą się na `InputDTO`, `RequestDTO` lub `ResponseDTO` |
| **Powiązanie** | — |
| **Status** | Diagnostic |

**Opis:**
Test akceptuje istniejące legacy DTO (np. `TouristProfileDTO`), ale wymusza konwencję na nowych klasach. Redukuje dług poznawczy przy onbordu.

> **Uwaga:** To jest reguła stylistyczna / konwencja, a nie invariant architektoniczny. Status: **Diagnostic**. Nie powinna blokować CI — służy spójności zespołu, a nie bezpieczeństwu systemu.

---

### FF-007: No Primitive Obsession

| Pole | Wartość |
|------|---------|
| **Nazwa** | No Primitive Obsession |
| **Tool** | `tests/architecture/test_no_primitive_obsession.py` |
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
| **Tool** | `tests/architecture/test_migration_idempotency.py` |
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
| **Tool** | `tests/architecture/test_god_class_prevention.py` |
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
| **Tool** | `tests/architecture/test_badge_rule_immutability.py` |
| **Chroni** | Wszystkie reguły biznesowe dziedziczące po `BadgeRule` są `@dataclass(frozen=True)` |
| **Powiązanie** | ADR-003 (Silnik Reguł Biznesowych) |
| **Status** | Gate |

**Opis:**
Test gwarantuje brak zjawiska State Mutilation podczas współbieżnego oceniania wielu turystów. Wymusza deep immutability na wszystkich strategiach walidacyjnych.

---

## Podsumowanie

| ID | Fitness Function | Tool | Chroni | Powiązanie | Status |
|----|------------------|-----------|--------|------------|--------|
| FF-001 | Dependency Direction | Import Linter + pytest | kierunek zależności | ADR-001 | **Diagnostic** |
| FF-002 | Domain Purity | pytest | Clean Domain | ADR-001 | Blocking |
| FF-003 | Repository Contracts | pytest | Ports & Adapters | ADR-001, ADR-002 | Blocking |
| FF-004 | API DTO Gating | pytest | API boundary | ADR-016 | Blocking |
| FF-005 | DI Container Completeness | pytest | Composition Root | ADR-001 | Blocking |
| FF-006 | DTO Naming Convention | pytest | konwencja | — | Diagnostic |
| FF-007 | No Primitive Obsession | pytest | application boundary | AUDYT-124 | Blocking |
| FF-008 | Migration Idempotency | pytest | Expand & Contract | ADR-024 | **Diagnostic** |
| FF-009 | God Class Prevention | pytest | modularność | — | **Diagnostic** |
| FF-010 | Badge Rule Immutability | pytest | domain invariants | ADR-003 | Blocking |
| FF-011 | Dockerfile Hygiene | Hadolint | standard konstrukcji obrazu | ADR-020 | Diagnostic |
| FF-012 | Compose Security | Checkov | konfiguracja IaC | ADR-020 | Diagnostic |
| FF-013 | Image Vulnerability Scanning | Trivy | CVE w obrazie | ADR-020 | Blocking |
| FF-014 | Docker Bench Security | Docker Bench | konfiguracja hosta Docker | ADR-020 | Diagnostic |
| FF-015 | Compose Health Checks | pytest | healthcheck w Compose | ADR-020 | Blocking |
| FF-016 | API Exception Handling | pytest | obsługa ApplicationException | — | Blocking |
| FF-017 | Request ID Contract | pytest | korelacja żądań | — | Blocking |
| FF-018 | No Sensitive Data in Logs | pytest | brak wrażliwych danych w logach | — | Diagnostic |
| FF-019 | Structured Error Context | pytest | RFC 7807 + request_id | — | Blocking |
| FF-020 | Health Check Semantics | pytest | semantyka healthcheck | ADR-020 | Blocking |
| FF-021 | Lockfile Integrity | pytest | `uv.lock` jest committed i śledzony | — | Blocking |
| FF-022 | Dependency Groups Separation | pytest | narzędzia dev/test nie mieszają się z runtime | — | Diagnostic |
| FF-023 | Fitness Function Registry Completeness | pytest | wszystkie FF mają wpis w rejestrze i wymagane pola | — | Blocking |

---

## Grupa 8: Infrastructure / Runtime Architecture & Security Governance

Ta grupa pilnuje architektury poza kodem Pythona — kontenery, Compose, obrazy, sekrety, uprawnienia.

| ID | Nazwa | Tool | Chroni | Powiązanie | Status |
|----|-------|------|--------|------------|--------|
| FF-011 | Dockerfile Hygiene | Hadolint | standard konstrukcji obrazu | ADR-020 | Diagnostic |
| FF-012 | Compose Security | Checkov | konfiguracja IaC | ADR-020 | Diagnostic |
| FF-013 | Image Vulnerability Scanning | Trivy | CVE w obrazie kontenerowym | ADR-020 | Blocking |
| FF-014 | Docker Bench Security | Docker Bench | konfiguracja hosta Docker | ADR-020 | Diagnostic |
| FF-015 | Compose Health Checks | pytest | healthcheck w Compose | ADR-020 | Gate |
| FF-016 | API Exception Handling | pytest | obsługa ApplicationException | — | Gate |

### FF-011: Dockerfile Hygiene

| Pole | Wartość |
|------|---------|
| **Nazwa** | Dockerfile Hygiene |
| **Chroni** | Standard konstrukcji obrazu, best practices Dockerfile |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Diagnostic |
| **Tool** | Hadolint (`make hadolint`) |

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
| **Chroni** | Konfigurację IaC — Compose files pod kątem bezpieczeństwa |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Diagnostic |
| **Tool** | Checkov (`make checkov`) |

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
| **Tool** | Trivy (`make security-audit`) |
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
| **Chroni** | Konfigurację środowiska Docker hosta — demon, sieć, uprawnienia, logging |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Diagnostic |
| **Tool** | Docker Bench (`make docker-bench`, na żądanie) |

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

| ID | Nazwa | Tool | Chroni | Powiązanie | Status |
|----|-------|-----------|--------|------------|--------|
| FF-015 | Compose Health Checks | pytest | Wszystkie services mają healthcheck | ADR-020 | Blocking |
| FF-016 | API Exception Handling | pytest | Widoki łapią ApplicationException | — | Blocking |

> **Uwaga FF-015:** Test weryfikuje obecność `healthcheck`, ale nie jego jakość. Healthcheck typu `curl localhost:8000` potwierdza tylko, że proces HTTP odpowiada, nie że aplikacja może obsługiwać ruch. Polityka: healthcheck musi sprawdzać rzeczywistą zdolność komponentu do pełnienia swojej funkcji (readiness/liveness), a nie wyłącznie istnienie procesu. Gdy projekt przejdzie do TEST/PROD, rozważyć rozszerzenie testu o weryfikację znaczenia healthcheck.

### FF-015: Compose Health Checks

| Pole | Wartość |
|------|---------|
| **Nazwa** | Compose Health Checks |
| **Tool** | `tests/architecture/test_health_checks.py` |
| **Chroni** | Wszystkie services mają `healthcheck` |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że każdy service w `compose*.yml` (poza `db` i `redis`) definiuje `healthcheck`. Gwarantuje to, że Docker może wykryć niezdrowe kontenery i zrestartować je automatycznie.

### FF-016: API Exception Handling

| Pole | Wartość |
|------|---------|
| **Nazwa** | API Exception Handling |
| **Tool** | `tests/architecture/test_exception_handling.py` |
| **Chroni** | Widoki łapią `ApplicationException` |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test sprawdza, że każda metoda `post`/`patch` w `apps/api/views.py` ma `except ApplicationException`. Zapewnia spójną obsługę błędów biznesowych i zapobiega wyciekowi stacktrace'ów do klienta.

---

## Grupa 10: Observability Governance

Ta grupa pilnuje gotowości aplikacji do przyszłego wdrożenia observability — request_id, strukturalne logowanie, semantyka health check. Nie instaluje narzędzi zewnętrznych; definiuje kontrakty, które później umożliwią integrację z Sentry, Prometheus, Loki lub OpenTelemetry bez przebudowy architektury.

| ID | Nazwa | Tool | Chroni | Powiązanie | Status |
|----|-------|------|--------|------------|--------|
| FF-017 | Request ID Contract | pytest | korelacja żądań | — | Gate |
| FF-018 | No Sensitive Data in Logs | pytest | brak wrażliwych danych w logach | — | Diagnostic |
| FF-019 | Structured Error Context | pytest | RFC 7807 + request_id | — | Gate |
| FF-020 | Health Check Semantics | pytest | semantyka healthcheck | ADR-020 | Gate |

### FF-017: Request ID Contract

| Pole | Wartość |
|------|---------|
| **Nazwa** | Request ID Contract |
| **Tool** | `tests/architecture/test_request_id_contract.py` |
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
| **Tool** | `tests/architecture/test_no_sensitive_data_in_logs.py` |
| **Chroni** | Brak wrażliwych danych w logach |
| **Powiązanie** | — |
| **Status** | Diagnostic |

**Opis:**
Test skanuje komunikaty logów w `application/`, `infrastructure/` i `apps/` pod kątem słów kluczowych: `password`, `passwd`, `secret`, `token`, `api_key`, `apikey`, `authorization`, `credentials`, `private_key`, `session_id`, `session_token`, `session_key`. Tryb: advisory — automatyczne wykrywanie może generować false positives.

> **Polityka:** Dane wrażliwe nigdy nie trafiają do logów. Jeśli potrzebujesz zapisać kontekst zdarzenia, używaj anonimizowanych identyfikatorów (np. `user_id`, `profile_id`). Słowo `session` zostało zastąpione konkretnymi `session_id`/`session_token`/`session_key`, aby uniknąć false positives z logami typu "user session expired".

### FF-019: Structured Error Context

| Pole | Wartość |
|------|---------|
| **Nazwa** | Structured Error Context |
| **Tool** | `tests/architecture/test_structured_error_context.py` |
| **Chroni** | RFC 7807 + request_id |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że każda metoda `post`/`patch` w `apps/api/views.py`, która łapie `ApplicationException`, używa `_handle_application_exception` lub `_problem_detail`. Oba helpery wstrzykują `request_id` do odpowiedzi RFC 7807, co pozwala na korelację między logami a odpowiedziami API.

### FF-020: Health Check Semantics

| Pole | Wartość |
|------|---------|
| **Nazwa** | Health Check Semantics |
| **Tool** | `tests/architecture/test_health_checks.py` |
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

| ID | Nazwa | Tool | Chroni | Powiązanie | Status |
|----|-------|-----------|--------|------------|--------|
| FF-021 | Lockfile Integrity | pytest | `uv.lock` jest committed i śledzony | — | Blocking |
| FF-022 | Dependency Groups Separation | pytest | narzędzia dev/test nie mieszają się z runtime | — | Diagnostic |

### FF-021: Lockfile Integrity

| Pole | Wartość |
|------|---------|
| **Nazwa** | Lockfile Integrity |
| **Tool** | `tests/architecture/test_lockfile_integrity.py` + pre-commit `uv lock --check` |
| **Chroni** | `uv.lock` jest committed i śledzony |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że `uv.lock` istnieje i jest śledzony przez Git. Pre-commit hook `uv lock --check` gwarantuje, że lockfile jest zsynchronizowany z `pyproject.toml`.

### FF-022: Dependency Groups Separation

| Pole | Wartość |
|------|---------|
| **Nazwa** | Dependency Groups Separation |
| **Tool** | `tests/architecture/test_dependency_groups_separation.py` |
| **Chroni** | Narzędzia dev/test nie mieszają się z runtime |
| **Powiązanie** | — |
| **Status** | Diagnostic |

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
| **Blocking / Advisory** | Czy łamanie reguły blokuje CI? (blocking / advisory) |
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
| Liczba FF bez false-negative analysis | 0 (Diagnostic/Experimental mogą mieć opisane ryzyko) |
| Liczba FF bez testu negatywnego | 0 dla Blocking FF |

#### FF-023: Fitness Function Registry Completeness

| Pole | Wartość |
|------|---------|
| **Nazwa** | Fitness Function Registry Completeness |
| **Tool** | `tests/architecture/test_fitness_function_registry.py` |
| **Chroni** | Wszystkie FF mają wpis w rejestrze i wymagane pola |
| **Powiązanie** | — |
| **Status** | Gate |

**Opis:**
Test weryfikuje, że każda FF wymieniona w `governance.md` ma odpowiadający wpis w `fitness-functions.md` z wymaganymi polami: Nazwa, Tool, Chroni, Powiązanie, Opis. Gwarantuje, że rejestr FF nie ulega rozjeźdzeniu z rzeczywistym stanem governance.

---

### FF-024: Architecture Health Score

| Pole | Wartość |
|------|---------|
| **Nazwa** | Architecture Health Score |
| **Tool** | `scripts/architecture-scorecard.py` + `tests/architecture/test_scorecard_metrics.py` |
| **Chroni** | Stopień zgodności architektury ze stylem — complexity, maintainability, layer purity, TDD ratio, security, import linter, type safety |
| **Powiązanie** | AUDYT-058 |
| **Status** | Diagnostic |

**Opis:**
Skrypt uruchamia `radon cc`/`radon mi`/`radon raw`, `audit_contracts.py`, `lint-imports`, `mypy`, i `ruff check`, agregując wyniki w `architecture_scorecard.json` z `health_score` (0-100). Test fitness function weryfikuje strukturę JSON, obecność wszystkich grup metryk, zakładanie pól `status`, oraz poprawność progów (np. `max_complexity` powyżej progu → `status: fail`).

---

## FF Inventory Review

Audyt wszystkich 24 FF według sześciu pytań:

| FF | Co chroni? | Dlaczego? | Jak? (mechanizm) | Czym? (tool) | Tier | Co powoduje zmianę tieru? |
|----|-----------|-----------|------------------|--------------|------|---------------------------|
| FF-001 | Kierunek zależności: domain ← application ← infrastructure ← apps | Bez kontroli: warstwy wyższe importują z niższych, pęcherzyk zależności, trudny do testowania kod | Import Linter + AST w pytest | Import Linter + `test_dependency_direction.py` | Gate (IL) / Diagnostic (pytest) | Import Linter jest źródłem prawdy; pytest to tylko dodatkowa diagnostyka |
| FF-002 | Brak Django Model w warstwie domenowej | Bez kontroli: domena zależy od frameworka, trudny do testowania unit | AST w pytest + Import Linter `domain-purity` | pytest + Import Linter | Gate | Import Linter blokuje importy frameworków; test chroni invariant behawioralny (dziedziczenie po Model) |
| FF-003 | Każdy adapter implementuje wszystkie metody swojego portu | Bez kontroli: dodanie metody do portu bez implementacji → `AttributeError` w runtime | AST w pytest | pytest | Gate | Brak implementacji portu = runtime failure; jasne remediation |
| FF-004 | Wszystkie widoki POST/PATCH używają DTO Pydantic | Bez kontroli: niezwalidowane dane wejściowe → błędy biznesowe, injection | AST w pytest | pytest | Gate | Bez DTO = brak walidacji; jasne remediation (dodaj DTO) |
| FF-005 | Wszystkie UseCase’y zarejestrowane w AppContainer | Bez kontroli: dodanie UseCase’u bez rejestracji → `AttributeError` w DI | AST w pytest | pytest | Gate | Brak rejestracji = runtime failure; jasne remediation |
| FF-006 | Konwencja nazewnictwa DTO: `*InputDTO`, `*RequestDTO`, `*ResponseDTO` | Bez kontroli: niespójne nazwy → wysoki dług poznawczy, trudny onboarding | AST w pytest | pytest | Diagnostic | Konwencja, nie invariant; nie blokuje bezpieczeństwa systemu |
| FF-007 | UseCase’y nie zwracają `dict`/`Any`/`list[...]` | Bez kontroli: surowe typy → niejawny kontrakt API, trudna walidacja | AST w pytest | pytest | Gate | Łamanie = brak ResponseDTO; jasne remediation |
| FF-008 | Migracje DDL nie mieszają AddField/RemoveField w jednym pliku | Bez kontroli: breaking schema change w jednym deployment’ie | AST w pytest | pytest | Diagnostic | Heurystyka, nie invariant; świadome migracje mogą łamać regułę |
| FF-009 | Żaden `models.py` nie przekracza 20 modeli Django | Bez kontroli: God Object → trudny do utrzymania, wysoka coupling | AST w pytest | pytest | Diagnostic | Proxy metric, nie invariant; 5 modeli może być God Object, 20 może być OK |
| FF-010 | Wszystkie strategie walidacyjne dziedziczą `BadgeRule` i są `frozen=True` | Bez kontroli: State Mutilation przy współbieżnym ocenianiu turystów | AST w pytest | pytest | Gate | Łamanie = race condition; krytyczne dla poprawności biznesowej |
| FF-011 | Dockerfile zgodny z best practices (pin wersji, warstwy, user) | Bez kontroli: nieprzewidywalne obrazy, security vulnerabilities, duży rozmiar | Hadolint | Hadolint | Diagnostic | Heurystyka jakości; nie blokuje bezpieczeństwa systemu |
| FF-012 | Compose files nie uruchamiają kontenerów jako root, mają capabilities | Bez kontroli: kontener z uprawnieniami root → security risk | Checkov | Checkov | Diagnostic | Advisory dla current baseline; może awansować jeśli Checkov dostatecznie dojrzeje |
| FF-013 | Obraz kontenerowy nie ma CVE HIGH/CRITICAL | Bez kontroli: znane exploit’y w produkcji → compromise | Trivy | Trivy | Gate | HIGH/CRITICAL CVE = realne ryzyko; jasne remediation (aktualizacja) |
| FF-014 | Host Docker spełnia CIS Docker Benchmark | Bez kontroli: nieprawidłowa konfiguracja demona → security risk | Docker Bench | Docker Bench | Diagnostic | Placeholder (upstream zarchiwizowany); może awansować gdy pojawi się aktywny successor |
| FF-015 | Wszystkie services w compose mają `healthcheck` | Bez kontroli: Docker nie wykrywa niezdrowych kontenerów → downtime | YAML parsing + pytest | pytest | Gate | Brak healthcheck = nieautomatyczny restart; jasne remediation |
| FF-016 | Wszystkie widoki POST/PATCH łapią `ApplicationException` | Bez kontroli: nieobsłużony wyjątek → 500 z traceback → stack trace exposure | AST w pytest | pytest | Gate | Łamanie = RFC 7807 violation; CodeQL alert #1 uzasadniony |
| FF-017 | Middleware generuje/honoruje `request_id`, wstrzykuje do request i logów | Bez kontroli: brak korelacji żądań → trudne debugowanie produkcji | AST + runtime w pytest | pytest | Gate | Brak request_id = tracenie śladów żądań; krytyczne dla observability |
| FF-018 | Logi nie zawierają haseł, tokenów, sekretów | Bez kontroli: wyciek danych wrażliwych w logach → compliance violation | Keyword scanning w pytest | pytest | Diagnostic | Heurystyka z FP; detect-secrets jest lepszym mechanizmem |
| FF-019 | Wszystkie `except ApplicationException` używają `_handle_application_exception` lub `_problem_detail` | Bez kontroli: niespójne formaty błędów → klient nie może obsłużyć API | AST w pytest | pytest | Gate | Łamanie = RFC 7807 violation; jasne remediation |
| FF-020 | Endpoint `/health/` sprawdza DB i Redis, zwraca 503 jeśli niedostępne | Bez kontroli: healthcheck zwraca 200 chociaż aplikacja nie działa → load balancer wysyła ruch do broken instance | pytest + urllib | pytest | Gate | Łamanie = downtime bez wykrycia; krytyczne dla readiness |
| FF-021 | `uv.lock` istnieje, jest śledzony przez Git, zsynchronizowany z pyproject.toml | Bez kontroli: brak reproducible builds → "u mnie działa" problem | pytest + pre-commit hook | pytest + `uv lock --check` | Gate | Łamanie = niespójne wersje zależności; jasne remediation |
| FF-022 | Zależności dev/test nie mieszają się z runtime `dependencies` | Bez kontroli: narzędzia deweloperskie w obrazie PROD → większy attack surface | AST w pytest | pytest | Diagnostic | Advisory: nie blokuje bezpieczeństwa, ale zwiększa risk profile |
| FF-023 | Wszystkie FF w governance.md mają wpis w rejestre fitness-functions.md | Bez kontroli: rejestr rozjeżdża się z rzeczywistością → fałszywe poczucie bezpieczeństwa | Markdown parsing w pytest | pytest | Gate | Łamanie = governance drift; FF-023 jest meta-governance |
| FF-024 | Architecture Health Score utrzymany powyżej progu | Bez kontroli: stopniowa degradacja jakości kodu → technical debt spiral | Skrypt scorecard + pytest | `scripts/architecture-scorecard.py` + `test_scorecard_metrics.py` | Diagnostic | Advisory: trend health_score > 90 to zdrowie, < 70 to alarm krytyczny |
| FF-024 | Architecture Health Score utrzymany powyżej progu | Bez kontroli: stopniowa degradacja jakości kodu → technical debt spiral | Skrypt scorecard + pytest | `scripts/architecture-scorecard.py` + `test_scorecard_metrics.py` | Diagnostic | Advisory: trend health_score > 90 to zdrowie, < 70 to alarm krytyczny |

---

## Uwagi szczególne

**FF-001: Dependency Direction**

Import Linter jest źródłem prawdy dla kierunku zależności. Test `test_dependency_direction.py` dostarcza dodatkową diagnostykę w formacie pytest, ale nie powinien być traktowany jako niezależny mechanizm. Tier dla tego FF zależy od toola:
- Import Linter → Gate × blocking
- pytest → Diagnostic × advisory

**FF-002: Domain Purity**

Import Linter egzekwuje `domain-purity` contract (brak importów frameworków). Test chroni invariant behawioralny, który Import Linter nie może wykryć: brak dziedziczenia po `Model` w warstwie domenowej.

**FF-006: DTO Naming Convention**

Konwencja stylistyczna, nie invariant architektoniczny. Status: Diagnostic. Nie powinna blokować CI — służy spójności zespołu, a nie bezpieczeństwu systemu.

**FF-008: Migration Idempotency**

Heurystyka, nie invariant. Django migration może legalnie zawierać różne operacje DDL, jeśli jest to świadomie zaprojektowana migracja. Rzeczywisty kontrakt to: "deployment nie może powodować downtime / breaking schema change".

**FF-009: God Class Prevention**

Proxy metric, nie invariant. Liczba modeli w pliku nie gwarantuje jakości architektury. 5 klas może tworzyć God Object, a 20 może być akceptowalnych. Test służy jako trend/smell detector.

**FF-014: Docker Bench Security**

Placeholder — upstream `docker/docker-bench` został zarchiwizowany. Target pozostawiono na przyszły audyt hosta Docker. Tier: Diagnostic, aż do znalezienia successor'a.

**FF-018: No Sensitive Data in Logs**

Heurystyka z potencjalnymi false positives. Keyword scanning nie jest wystarczająco precyzyjny. detect-secrets jest lepszym mechanizmem do wykrywania sekretów.

---

## Kryteria zmiany tieru

### Awans Experimental → Diagnostic
- Narzędzie przeżyło co najmniej 1 kwartał w użyciu
- Wygenerowało wartość (wykryło coś, co inaczej by przegapiono)
- Ma clear exit criteria i maintenance plan

### Awans Diagnostic → Gate
- Invariant jest obiektywnie weryfikowalny (nie subiektywny)
- Ma niski poziom false positives i false negatives
- Remediation jest jasne i jednoznaczne
- Łamanie invariant'a oznacza realne ryzyko dla systemu

### Degradacja Gate → Diagnostic
- Narzędzie generuje częste false positives
- Invariant jest słaby lub subiektywny
- Maintenance overhead przekracza wartość
- Istnieje lepszy sposób wykrywania tego samego problemu

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 2.0 | 2026-08-27 | Dominik / AI Architect | FF Inventory Review: dodano audyt 23 FF według 6 pytań; konsolidacja tier’ów; rozdzielenie FF od Tools |
| 1.0 | 2026-08-26 | Dominik / AI Architect | Utworzenie rejestru fitness functions (FF-001..FF-010) |
