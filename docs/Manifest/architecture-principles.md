# Architecture Principles

**Status:** Referencyjny (nadrzędny)
**Zakres:** Wszystkie projekty Python w architekturze heksagonalnej

---

## Cel tego dokumentu

Manifest składa się z 20+ kontraktów. Ten dokument zbiera fundamentalne zasady które je wszystkie przenikają — żeby nowy deweloper mógł zrozumieć *dlaczego*, zanim zacznie czytać *jak*.

Każda zasada jest odsyłaczem do konkretnego kontraktu który ją egzekwuje.

---

## Zasada 1: Reproducibility ponad wygodę

**Definicja:** Ten sam kod, ta sama maszyna, ten sam wynik — niezależnie od daty, środowiska i kolejności operacji.

**Konsekwencje:**
- Zależności są zamrożone w `uv.lock` — brak dynamicznego rozwiązywania przy buildzie
- Docker build używa `--frozen` i `--no-cache` — brak warstw z poprzednich buildów
- Akcje GitHub Actions są pinowane do konkretnych wersji (`@vX.Y.Z`)
- Testy używają `FakeClock` i `SequentialIdGenerator` — zero zależności od systemu

**Kontrakty:** `02-dependency-governance.md`, `07-docker-contract.md`, `09-ci-enforcement.md`, `17-determinism-contract.md`

---

## Zasada 2: Explicit Boundaries (jawne granice)

**Definicja:** Każda warstwa ma dokładnie zdefiniowane co może importować, co może rzucać i skąd dostaje swoje zależności. Naruszenie granicy jest błędem kompilacji — nie konwencją.

**Konsekwencje:**
- `domain/` zależy wyłącznie od biblioteki standardowej — żadnych frameworków
- `application/` nie importuje `infrastructure/` — zależność jest odwrócona przez porty
- Porty (`ClockPort`, `MeetingRepositoryPort`, `UnitOfWorkPort`) są własnością `application/ports/` — nie `domain/`
- Granica transakcji bazy danych jest definiowana w `application/` (Unit of Work Port), ale realizowana w `infrastructure/` — logika biznesowa nie zna ORM-a
- Wyjątki domenowe nie wychodzą poza `application/` — każda warstwa tłumaczy wyjątki z warstw niższych
- Konfiguracja jest wstrzykiwana przez `bootstrap` — domeny nie czytają `os.getenv`

**Kontrakty:** `14-domain-purity.md`, `16-error-boundary.md`, `20-configuration-contract.md`, `21-transaction-contract.md`, `22-ports-adapters-dto-contract.md`

---

## Zasada 3: Fail-Fast (błąd jak najwcześniej)

**Definicja:** Błąd wykryty wcześniej jest tańszy niż błąd wykryty później. Pipeline jest zorganizowany tak, żeby najtańsze sprawdzenia były pierwsze.

**Konsekwencje:**
- `make check` uruchamia narzędzia w kolejności: format → lint → types → tests → audit
- `quality-gate` blokuje `security-gate` — nie budujemy obrazu Dockera jeśli kod nie przeszedł
- DataFrame jest walidowany przez Panderę *natychmiast po wczytaniu* — przed jakimkolwiek użyciem
- Konfiguracja jest walidowana przez pydantic-settings przy starcie aplikacji — nie w trakcie działania
- `uv lock --check` jest pierwszym krokiem CI — nie instaluje nic, tylko weryfikuje kontrakt

**Kontrakty:** `01-makefile-contract.md`, `09-ci-enforcement.md`, `15-dataframe-contract.md`, `20-configuration-contract.md`

---

## Zasada 4: Determinism (przewidywalność)

**Definicja:** Kod który zależy od czasu, losowości lub środowiska nie jest w pełni testowalny. Wszelkie źródła niedeterminizmu są wstrzykiwane — nie wywoływane bezpośrednio.

**Konsekwencje:**
- `datetime.now()`, `uuid.uuid4()`, `random.*` są zakazane w `domain/` i `application/`
- Czas i ID są dostarczane przez `ClockPort` i `IdGeneratorPort` — wymienialne na `FakeClock` w testach
- `os.getenv` jest zakazany poza `bootstrap` — środowisko nie wpływa na logikę domenową
- Operacje zapisu są idempotentne — ID jest generowane i wstrzykiwane przed zapisem, dzięki czemu retry nie tworzy duplikatów
- Testy jednostkowe są deterministyczne: ten sam input → ten sam output zawsze

**Kontrakty:** `17-determinism-contract.md`, `20-configuration-contract.md`, `21-transaction-contract.md`

---

## Zasada 5: Contract over Convention (kontrakt ponad konwencję)

**Definicja:** Zasady które można zautomatyzować — są zautomatyzowane. Zasady które nie są egzekwowalne przez narzędzia — nie są kontraktami, tylko wytycznymi.

**Konsekwencje:**
- Każdy kontrakt ma przypisane narzędzie egzekwujące: ruff, mypy, import-linter, trivy, audit_contracts.py
- `make check = CI quality-gate` — nie ma dwóch zestawów zasad: jednego lokalnego i jednego w CI
- Naruszenie kontraktu → pipeline FAIL → merge zablokowany — nie ma "wyjątków na raz"
- `audit_contracts.py` weryfikuje naruszenia których żadne inne narzędzie nie wykryje (TYPE_CHECKING, determinizm przez AST)

**Kontrakty:** `01-makefile-contract.md`, `05-test-coverage.md`, `09-ci-enforcement.md`, `14-domain-purity.md`

---

## Zasada 6: Minimal Surface (minimalna powierzchnia)

**Definicja:** Każdy komponent ma dostęp tylko do tego czego potrzebuje. Każdy obraz zawiera tylko to co musi działać. Każda biblioteka jest uzasadniona.

**Konsekwencje:**
- Obraz runtime nie zawiera build toolchain (`pip`, `setuptools`, `wheel` usuwane w Stage 2)
- Kontener działa jako non-root z read-only filesystem i zrzuconymi capabilities
- `curl` nie jest instalowany do healthchecka — używamy `urllib` z biblioteki standardowej
- Sekrety nie trafiają do warstw obrazu Docker ani do `bash_history`
- Każdy adapter ma osobny klucz API — nie ma "god client" z dostępem do wszystkiego

**Kontrakty:** `07-docker-contract.md`, `10-secrets-management.md`

---

## Architektura heksagonalna — schemat

```
                    ┌─────────────────────────────┐
                    │         domain/             │
                    │   (entities, value objects, │
                    │    exceptions, services)    │
                    │   tylko stdlib Pythona      │
                    └─────────────────────────────┘
                               ▲
                               │ importuje
                    ┌──────────┴──────────────────┐
                    │       application/          │
                    │   (use cases, DTOs,         │
                    │    port interfaces)         │
                    │   stdlib + domain/          │
                    └─────────────────────────────┘
                               ▲
                               │ importuje / implementuje porty
          ┌────────────────────┴────────────────────────┐
          │              infrastructure/                │
          │   (adapters, repositories, config,          │
          │    logging, zewnętrzne API)                 │
          │   może importować wszystko                  │
          └─────────────────────────────────────────────┘
                               ▲
                               │ wstrzykuje przez porty
                    ┌──────────┴──────────────────┐
                    │        bootstrap/           │
                    │   (DI container, AppSettings│
                    │    — jedyne miejsce os.getenv│
                    └─────────────────────────────┘
```

Kierunek importów jest **jednostronny** — zawsze do wewnątrz. Nigdy na zewnątrz.
`application/` nie importuje `infrastructure/` — zależność jest odwrócona przez porty (Ports & Adapters).

---

## Zasada 7: Dev/Prod Parity & Shift-Left (symetria środowisk)

**Definicja:** Środowisko lokalne dewelopera jest lustrzanym odbiciem CI i produkcji. Błędy łapiemy na najwcześniejszym możliwym etapie — na klawiaturze dewelopera, nie w pipeline ani na produkcji.

**Konsekwencje:**
- `make check` uruchamia dokładnie ten sam zestaw walidacji co CI `quality-gate` — zero rozbieżności
- Pre-commit uruchamia `make check` lub jego szybki podzbiór — nigdy nic spoza `make check`
- Docker definiuje zachowanie aplikacji w runtime, izolując je od systemu hosta
- `uv.lock` gwarantuje że deweloper lokalnie ma te same wersje co CI i produkcja

**Kontrakty:** `01-makefile-contract.md`, `09-ci-enforcement.md`, `02-dependency-governance.md`

---

## Zasada 8: Security by Default & Defense in Depth (bezpieczeństwo wbudowane)

**Definicja:** Bezpieczeństwo nie jest osobnym krokiem ani checklistą przed wydaniem. Jest wbudowane w konfigurację frameworków, obrazów i warstw — przy założeniu że każda linia obrony może zawieść.

**Konsekwencje:**
- Aplikacja nigdy nie działa jako root, ma read-only filesystem i zrzucone capabilities
- Sekrety nie trafiają do kodu, warstw obrazu Docker ani `bash_history` — są wstrzykiwane przez środowisko
- Dane wejściowe (w tym DataFrames) są traktowane jako nieufne i walidowane przez Pydantic/Pandera na granicach systemu
- Zależności są skanowane przez Trivy przy każdym buildzie — CVE CRITICAL/HIGH blokuje merge

**Kontrakty:** `07-docker-contract.md`, `10-secrets-management.md`, `15-dataframe-contract.md`

---

## Zasada 9: Observability & Traceability (obserwowalność i identyfikowalność)

**Definicja:** Zbudowanie aplikacji to połowa sukcesu — druga połowa to wiedza o tym co się w niej dzieje na produkcji, bez konieczności zgadywania. Każdy błąd pozostawia ślad. Każdy artefakt ma tożsamość.

**Konsekwencje:**
- Twarda hierarchia wyjątków (`16-error-boundary.md`) — błędy infrastrukturalne nie maskują błędów domenowych
- Globalny exception handler gwarantuje że proces który "umiera" zostawia zrozumiały log JSON i `exit(1)`
- Correlation ID (`request_id`) w logach łączy wszystkie wpisy jednego żądania HTTP
- Każdy wydany artefakt ma ślad audytowy: `commit SHA → Docker image SHA → tag vX.Y.Z`
- Logi na stdout/stderr w formacie JSON — gotowe pod ElasticSearch/Loki bez dodatkowej konfiguracji

**Kontrakty:** `16-error-boundary.md`, `18-logging-monitoring.md`

---

## Narzędzia egzekwowania — mapa

| Zasada | Narzędzie | Co wykrywa |
|--------|-----------|-----------|
| Reproducibility | `uv lock --check` | Brak synchronizacji lockfile |
| Explicit Boundaries | `import-linter` | Naruszenia kierunku importów między warstwami |
| Explicit Boundaries | `ruff TID251` | Bezpośrednie importy zakazanych bibliotek w domain/ |
| Explicit Boundaries | `audit_contracts.py` | Importy w bloku TYPE_CHECKING, os.getenv w application/ |
| Fail-Fast | `mypy strict` | Błędy typów w domain/ i application/ |
| Determinism | `audit_contracts.py` | datetime.now(), uuid4(), random.* w domain/ i application/ |
| Contract over Convention | `trivy` | CVE CRITICAL/HIGH w obrazie Docker |
| Contract over Convention | `ruff S` | eval(), exec(), assert w kodzie produkcyjnym |
| Minimal Surface | `audit_contracts.py` | Brak .dockerignore lub brakujące krytyczne wpisy |
| Minimal Surface | `make secrets-check` | Brakujące zmienne środowiskowe wymagane przez `.env.example` |
| Security by Default | `docker run` (Runtime Integrity Tests) | Próby zapisu do `/app` lub uruchomienia jako root |

---

## Architecture Decision Records (ADR)

Kontrakty w tym manifeście mówią **co** jest prawdą i **jak** jest egzekwowane. ADR mówią **dlaczego** — dokumentują decyzje architektoniczne z kontekstem, rozważanymi alternatywami i konsekwencjami.

**Zasada:** Każda nieoczywista decyzja architektoniczna musi być udokumentowana jako ADR w repozytorium projektu.

### Struktura

```
docs/
└── adr/
    ├── ADR-001-hexagonal-architecture.md
    ├── ADR-002-uv-as-package-manager.md
    └── ADR-003-unit-of-work-pattern.md
```

### Format (obowiązkowy)

```markdown
# ADR-NNN: Tytuł decyzji

**Data:** YYYY-MM-DD
**Status:** Accepted | Deprecated | Superseded by ADR-NNN

## Kontekst

Opis problemu który wymaga decyzji. Co się dzieje? Dlaczego musimy podjąć decyzję?

## Rozważane opcje

1. Opcja A — opis + wady/zalety
2. Opcja B — opis + wady/zalety
3. Opcja C — opis + wady/zalety

## Decyzja

Wybraliśmy opcję X, ponieważ...

## Konsekwencje

Co ta decyzja oznacza w praktyce? Jakie nowe ograniczenia wprowadza? Co staje się łatwiejsze, co trudniejsze?
```

### Kiedy pisać ADR

ADR jest wymagany gdy:
- Wybieramy pattern architektoniczny (np. Unit of Work zamiast bezpośredniego ORM)
- Rezygnujemy ze standardowego podejścia (np. brak `pytest-django` na rzecz `FakeRepository`)
- Wprowadzamy wyjątek od kontraktu z uzasadnieniem
- Decyzja będzie zadziwiać nowego dewelopera za 6 miesięcy

ADR nie jest potrzebny dla decyzji oczywistych w kontekście manifestu (np. "używamy ruff" — to wynika z kontraktu).

### Relacja do manifestu

Manifest definiuje **kontrakt obowiązujący wszystkie projekty**. ADR dokumentuje **decyzje specyficzne dla konkretnego projektu** — w tym odstępstwa od kontraktu z uzasadnieniem. Każde odstępstwo od manifestu wymaga ADR.

Dla nowego dewelopera dołączającego do projektu:

1. Ten dokument — fundamenty i mapa
2. `01-makefile-contract.md` — jak pracować lokalnie
3. `14-domain-purity.md` — gdzie co należy
4. `22-ports-adapters-dto-contract.md` — jak warstwy rozmawiają ze sobą
5. `09-ci-enforcement.md` — jak działa pipeline
6. `17-determinism-contract.md` + `20-configuration-contract.md` — dwa najczęściej naruszane kontrakty
7. Pozostałe dokumenty — w razie potrzeby
