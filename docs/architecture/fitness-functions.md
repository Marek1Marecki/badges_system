# Architecture Fitness Functions

> **Wersja:** 1.0  
> **Data:** 2026-08-26  
> **Właściciel:** Dominik / AI Architect  
> **Zasada:** Każda reguła architektoniczna z `tests/architecture/` ma tu swój wpis. Test nie jest tylko testem — jest formalnie zidentyfikowaną fitness function.

---

## Format wpisu

| Pole | Opis |
|------|------|
| **ID** | Unikalny identyfikator: `FF-NNN` |
| **Nazwa** | Krótki opis fitness function |
| **Mechanizm** | Narzędzie egzekwujące regułę |
| **Chroni** | Co się stanie, jeśli reguła zostanie złamana |
| **Powiązanie** | ADR lub inny kontekst decyzyjny |

---

## Rejestr Fitness Functions

### FF-001: Dependency Direction

| Pole | Wartość |
|------|---------|
| **Nazwa** | Dependency Direction |
| **Mechanizm** | Import Linter + `tests/architecture/test_dependency_direction.py` |
| **Chroni** | Kierunek zależności między warstwami (domain ← application ← infrastructure ← apps) |
| **Powiązanie** | ADR-001 (Hexagonal Architecture) |

**Opis:**
Import Linter egzekwuje kierunek zależności na poziomie pakietów. Test w `tests/architecture/` daje dodatkowy, domenowy komunikat w standardowym `pytest`:

```
Domain purity violated:
domain/foo.py imports django.db.models
```

---

### FF-002: Domain Purity

| Pole | Wartość |
|------|---------|
| **Nazwa** | Domain Purity |
| **Mechanizm** | `tests/architecture/test_domain_purity.py` |
| **Chroni** | Czystość warstwy domenowej — brak importów z application, infrastructure, apps, Django ORM, env |
| **Powiązanie** | ADR-001 (Hexagonal Architecture) |

**Opis:**
Test weryfikuje, że żaden plik w `domain/` nie importuje z zewnętrznych warstw ani frameworków. Import Linter współpracuje z tym testem, ale test daje lepszą diagnostykę w `pytest`.

---

### FF-003: Repository Contracts

| Pole | Wartość |
|------|---------|
| **Nazwa** | Repository Contracts |
| **Mechanizm** | `tests/architecture/test_repository_contracts.py` |
| **Chroni** | Semantyczny kontrakt: każdy adapter implementuje wszystkie metody swojego portu |
| **Powiązanie** | ADR-001 (Hexagonal Architecture), ADR-002 (Ports & Adapters) |

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

**Opis:**
Test akceptuje istniejące legacy DTO (np. `TouristProfileDTO`), ale wymusza konwencję na nowych klasach. Redukuje dług poznawczy przy onbordu.

---

### FF-007: No Primitive Obsession

| Pole | Wartość |
|------|---------|
| **Nazwa** | No Primitive Obsession |
| **Mechanizm** | `tests/architecture/test_no_primitive_obsession.py` |
| **Chroni** | Use Case'y nie zwracają surowych `dict` lub `Any` — wymagają dedykowanych DTO |
| **Powiązanie** | AUDYT-124 |

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

**Opis:**
Test egzekwuje zasadę Expand & Contract: migracja nie może zawierać zarówno `AddField` jak i `RemoveField`. Automatycznie zwalnia dewelopera z ręcznej weryfikacji kroków wdrożeniowych.

---

### FF-009: God Class Prevention

| Pole | Wartość |
|------|---------|
| **Nazwa** | God Class Prevention |
| **Mechanizm** | `tests/architecture/test_god_class_prevention.py` |
| **Chroni** | Żaden plik `models.py` nie przekracza progu 8 modeli Django |
| **Powiązanie** | — |

**Opis:**
Test wymusza dekompozycję modułów. Przeciwdziała powstawaniu plików takich jak `apps/badges/models.py` (700 linijek, 8+ modeli).

---

### FF-010: Badge Rule Immutability

| Pole | Wartość |
|------|---------|
| **Nazwa** | Badge Rule Immutability |
| **Mechanizm** | `tests/architecture/test_badge_rule_immutability.py` |
| **Chroni** | Wszystkie reguły biznesowe dziedziczące po `BadgeRule` są `@dataclass(frozen=True)` |
| **Powiązanie** | ADR-003 (Silnik Reguł Biznesowych) |

**Opis:**
Test gwarantuje brak zjawiska State Mutilation podczas współbieżnego oceniania wielu turystów. Wymusza deep immutability na wszystkich strategiach walidacyjnych.

---

## Podsumowanie

| ID | Fitness Function | Mechanizm | Chroni | Powiązanie |
|----|------------------|-----------|--------|------------|
| FF-001 | Dependency Direction | Import Linter + pytest | kierunek zależności | ADR-001 |
| FF-002 | Domain Purity | pytest | Clean Domain | ADR-001 |
| FF-003 | Repository Contracts | pytest | Ports & Adapters | ADR-001, ADR-002 |
| FF-004 | API DTO Gating | pytest | API boundary | ADR-016 |
| FF-005 | DI Container Completeness | pytest | Composition Root | ADR-001 |
| FF-006 | DTO Naming Convention | pytest | konwencja | — |
| FF-007 | No Primitive Obsession | pytest | application boundary | AUDYT-124 |
| FF-008 | Migration Idempotency | pytest | Expand & Contract | ADR-024 |
| FF-009 | God Class Prevention | pytest | modularność | — |
| FF-010 | Badge Rule Immutability | pytest | domain invariants | ADR-003 |

---

## Grupa 8: Infrastructure / Runtime Architecture & Security Governance

Ta grupa pilnuje architektury poza kodem Pythona — kontenery, Compose, obrazy, sekrety, uprawnienia.

| ID | Nazwa | Mechanizm | Chroni | Powiązanie |
|----|-------|-----------|--------|------------|
| FF-011 | Dockerfile Hygiene | Hadolint | standard konstrukcji obrazu | ADR-020 |
| FF-012 | Compose Security | Checkov | konfiguracja IaC | ADR-020 |
| FF-013 | Image Vulnerability Scanning | Trivy | CVE w obrazie | ADR-020 |

### FF-011: Dockerfile Hygiene

| Pole | Wartość |
|------|---------|
| **Nazwa** | Dockerfile Hygiene |
| **Mechanizm** | Hadolint (`make hadolint`) |
| **Chroni** | Standard konstrukcji obrazu, best practices Dockerfile |
| **Powiązanie** | ADR-020 (Deployment & DataOps) |

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

**Opis:**
Trivy skanuje obraz kontenerowy pod kątem:
- Podatności w pakietach OS
- Podatności w zależnościach Python
- Sekretów w obrazie
- SBOM (Software Bill of Materials)

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
```

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-08-26 | Dominik / AI Architect | Utworzenie rejestru fitness functions (FF-001..FF-010) |
