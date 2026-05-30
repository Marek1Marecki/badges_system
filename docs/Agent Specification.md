# Agent Specification — specyfikacja agentów LLM

> **Wersja:** 1.1  
> **Data:** 2026-05-29  
> **Właściciel:** Dominik / AI Architect
>
> Ten dokument definiuje **instrukcje dla agentów LLM wspomagających development** —  
> nie opisuje wywołań LLM wewnątrz działającej aplikacji.  
> Agent LLM przed wykonaniem zadania powinien otrzymać odpowiednią sekcję tego dokumentu jako część kontekstu.

---

## Czym jest ten dokument

Każdy projekt ma obszary kodu, które wymagają specjalnej uwagi przy modyfikacji:
moduły z nieoczywistymi zależnościami, miejsca gdzie niezmienniki (invarianty) są szczególnie wrażliwe, wzorce, których agent nie powinien "ulepszać" według własnego uznania.

Ten dokument to zbiór **instrukcji briefingowych** — per obszar, per typ zadania. Zanim agent dotknie danego modułu, dostaje odpowiednią instrukcję.

---

## Typy agentów i ich role

| Typ agenta | Kiedy używany | Co dostaje jako kontekst |
|-----------|--------------|--------------------------|
| **Agent kodujący** | Implementacja funkcji, bugfix, refaktoryzacja | Ten plik (odp. sekcja) + `INVARIANTS.md` + model danych |
| **Agent architektoniczny** | Projektowanie nowego modułu, decyzje (Faza C) | `ARCHITECTURE.md` + `MODULES.md` + aktywne ADR-y |
| **Agent historyczny** | "Dlaczego tu jest tak napisane?" | `EDGE_CASES.md` + powiązane ADR-y + `CHANGELOG.md` |
| **Agent recenzujący** | Code review kodu przed komitem | `INVARIANTS.md` + `TEST_STRATEGY.md` + `AGENT-REVIEW` (sekcja) |
| **Agent dokumentujący** | Aktualizacja docs po zmianach | Ten plik + zmienione pliki kodu |

---

## Instrukcje dla Agenta Kodującego

### AGENT-DOMAIN-CODE — Implementacja Reguł Biznesowych i Czystej Domeny

**Obszar:** `domain/`  
**Typ:** kodujący

**Zasady obowiązujące w tym module:**
1. Każda nowa reguła weryfikacyjna musi dziedziczyć po `BadgeRule` i być zadeklarowana jako `@dataclass(frozen=True)`.
2. Ewaluacja postępu musi polegać na **Matematyce Zbiorów (Set Math)**. Do przecinania weryfikowanych szczytów używaj natywnych operacji Pythona (np. `climbed_ids.intersection(pool_ids)`).
3. **Czas i Kontekst:** Ponieważ reguły są odtwarzane z JSONB, NIE wstrzykuj do nich usług (np. `ClockPort`) przez konstruktor. Czas "teraz" lub daty z profilu przekazuj w metodzie `validate` przez dedykowany obiekt `VerificationContext`.

**Zakazane:**
- Importowanie jakichkolwiek paczek poza `stdlib` Pythona (szczególnie `django`, `pydantic`, `dateutil`).
- Używanie `datetime.now()` (T-02).
- Tworzenie zapytań GIS / PostGIS wewnątrz domeny (R-01).

**Wzorzec — poprawna reguła domenowa z kontekstem:**
```python
@dataclass(frozen=True)
class ExampleTimeRule(BadgeRule):
    required_id: int

    def validate(self, ascents: list[Ascent], context: VerificationContext) -> list[str]:
        # 'context.evaluation_time' pochodzi z Use Case'a (ClockPort), nie z datetime.now()!
        if context.evaluation_time.year < 2026:
            return ["Weryfikacja niedostępna w tym roku."]
            
        climbed_ids = {a.peak_id for a in ascents}
        if self.required_id not in climbed_ids:
            return [self._format_rejection(ascents[0], f"Brak szczytu o ID: {self.required_id}")]
        return []
```

---

### AGENT-USECASE-CODE — Implementacja Orkiestracji Aplikacji (Faza C)

**Obszar:** `application/use_cases/`, `application/dto/`  
**Typ:** kodujący

**Zasady:**
1. `UseCase` to jedyne miejsce, w którym można orkiestrować przepływ: DTO -> Domena -> Porty -> Wynik.
2. Zależności zewnętrzne (np. repozytoria bazy danych, `ClockPort`) są wstrzykiwane wyłącznie przez konstruktor (`__init__`).
3. Wyłapuj `DomainException` i pozwól im propagować (lub transformuj) do warstwy prezentacji, gdzie zajmie się nimi globalny middleware (Zasada z `ERROR_HANDLING.md`).

**Zakazane:**
- Bezpośredni import i wywołanie `apps.badges.models` (ORM) lub zadań z `tasks.py`.
- Zwracanie obiektów bazy danych na zewnątrz Use Case'a. Zwracaj DTO.

**Wzorzec — poprawna orkiestracja w Use Case:**
```python
class StartBadgeProgressUseCase:
    def __init__(self, repository: BadgeRepositoryPort, clock: ClockPort) -> None:
        self._repo = repository
        self._clock = clock

    def execute(self, dto: StartBadgeRequestDTO) -> StartBadgeResponseDTO:
        # 1. Pobierz przez port (nie przez ORM Django bezpośrednio)
        badge_version = self._repo.get_badge_version(dto.badge_code, dto.version_code)
        if not badge_version:
            raise BadgeNotFoundException(f"Odznaka {dto.badge_code} nie istnieje.")
            
        # 2. Logika domenowa (np. zbudowanie kontekstu z czasem)
        context = VerificationContext(evaluation_time=self._clock.now())
        
        # 3. Wywołaj operację na porcie (zapisz stan)
        self._repo.save_user_progress(dto.user_id, badge_version.version_id, context.evaluation_time)
        
        # 4. Zwróć DTO
        return StartBadgeResponseDTO(status="STARTED", current_date=context.evaluation_time)
```

---

### AGENT-API-CONTRACT — Implementacja REST API dla Klientów (Faza C)

**Obszar:** `apps/api/`, `apps/badges/views.py`  
**Typ:** kodujący

**Zasady:**
1. Każdy endpoint przyjmuje wyłącznie surowy format HTTP, który natychmiast musi być zwalidowany do obiektu Pydantic DTO (np. `VerifyBadgeRequestDTO.model_validate(request.body)`).
2. Endpoint wywołuje przygotowany Use Case pobrany z Kontenera DI (`bootstrap.get_container()`).
3. Endpointy zwracają `JsonResponse` lub `HttpResponse`. 

**Zakazane:**
- Obsługa wyjątków typu `try/except DomainValidationError: return JsonResponse({"error": "..."})` na poziomie każdego widoku. Zgodnie z `ERROR_HANDLING.md` polegamy na centralnym `RFC7807ErrorMiddleware`.
- Zwracanie modeli ORM (np. `JsonResponse(model.values())`). Zawsze używaj metody `model_dump()` na obiekcie DTO zwróconym z Use Case'a.

---

### AGENT-FRONTEND-CODE — Implementacja Widoków i Map (HTMX + MapLibre)

**Obszar:** `apps/templates/`, `apps/static/`  
**Typ:** kodujący

**Zasady:**
1. Aplikacja webowa opiera się na Server-Side Rendering (SSR) z użyciem **Django Templates**.
2. Dynamika UI realizowana jest wyłącznie przez **HTMX** (np. `hx-get`, `hx-target`).
3. Wyświetlanie map realizowane jest w **MapLibre GL JS** poprzez czysty JavaScript osadzony w dedykowanych plikach statycznych. Warstwy zasilane są z endpointów GeoJSON lub MVT wystawianych przez Django.

**Zakazane:**
- Tworzenie komponentów React / Vue. System nie używa Node.js/NPM do budowania frontendu.
- Pisanie rozbudowanego, zagnieżdżonego kodu JavaScript wewnątrz plików HTML (Inline JS). Logika inicjalizacji mapy musi być zhermetyzowana i czytelna.
- Używanie biblioteki Leaflet (poza już istniejącymi, odizolowanymi formularzami w Django Admin). Warstwa użytkownika opiera się na wektorach i WebGL w MapLibre.

---

### AGENT-INFRA-CODE — Adaptery, Repozytoria i Celery

**Obszar:** `infrastructure/adapters/`, `apps/badges/tasks.py`  
**Typ:** kodujący

**Zasady:**
1. Zapytania GIS (`ST_DWithin`, `ST_Union`) wykonuj tylko w adapterach/repozytoriach.
2. Jeśli tworzysz nową fabrykę reguły (`_build_...`), w przypadku braku wymaganego atrybutu bezwzględnie rzucaj `ValueError` (Fail-Fast, R-02).
3. Taski Celery w `tasks.py` są cienkimi wrapperami. Muszą wyciągać Use Case z `bootstrap.get_container()` i tylko zarządzać ewentualnym mechanizmem Retry.

**Zakazane:**
- Ciche łapanie wyjątków (`except Exception: pass`) w warstwie GIS i hydracji.
- Metody `POST` i twardy `Accept: application/json` w zapytaniach do Overpass API.

---

### AGENT-DB-MIGRATIONS — Migracje i Modele Danych

**Obszar:** `apps/[app_name]/models.py`, `migrations/`  
**Typ:** kodujący

**Zasady:**
1. Modele w Django są tylko "workami na dane" dla infrastruktury.
2. Migracje generowane przez `manage.py makemigrations` są wyłączone ze sprawdzania Mypy i długości linii (E501 w ruff). Nie formatuj ich ręcznie.
3. Klastrowanie obiektów (`parent_object`) nie posiada zabezpieczenia przed cyklem bezpośrednio w bazie. Zawsze zabezpieczaj to w metodzie `clean()` formularza.

**Zakazane:**
- `DROP COLUMN` lub cofanie migracji PostGIS bez jawnej autoryzacji człowieka.
- Wykorzystywanie Django Signals (np. `post_save`) do odpalania zapytań GIS. Używamy `transaction.on_commit()`.

---

## Instrukcje dla Agenta Architektonicznego i Recenzującego

### AGENT-BLAST-RADIUS — Modyfikacje wspólnych Portów

Zanim zmienisz interfejs w `application/ports/` lub sygnaturę metody domenowej:
1. Przeszukaj całe repozytorium pod kątem wywołań.
2. Zaktualizuj **WSZYSTKIE** Adaptery (w tym `tests/fakes/`), które implementują dany Port w tym samym commicie. (Niezgodność Fake'a z Portem złamie `make check`).

### AGENT-REVIEW — Code Review Pull Requesta

Przed zatwierdzeniem kodu agent musi sprawdzić poniższą checklistę:
```text
INVARIANTY
[ ] Czy żadna zmiana nie narusza INVARIANTS.md (np. czy Czysta Domena nie używa GIS)?
[ ] Czy zmiana w regułach biznesowych posiada test mutacyjny weryfikujący krawędzie błędu?
[ ] Czy użyto ClockPort dla pojęcia czasu?

BEZPIECZEŃSTWO
[ ] Czy nowy endpoint zwraca błędy zgodne ze standardem RFC 7807 (ERROR_HANDLING.md)?
[ ] Czy w kodzie nie ma hardkodowanych haseł i URL-i omijających AppSettings?

ARCHITEKTURA
[ ] Czy zachowano jednokierunkowość importów (w dół do domain/)?
[ ] Czy Task Celery nie zawiera logiki, a jedynie wrapper Use Case'a?
[ ] Czy pliki HTML w warstwie Frontendu nie używają nieuzasadnionego Inline JS?
```

---

## Instrukcja obowiązkowa przed każdym zadaniem z kodowaniem

Przed wygenerowaniem pierwszego bloku kodu, agent musi odpowiedzieć na 5 pytań w formie listy punktowanej:

```markdown
**Analiza przed implementacją:**
1. Invarianty zagrożone przez zmianę: [wymień ID z INVARIANTS.md]
2. Zabezpieczenie: [jak kod egzekwuje invariant]
3. Zmiany w publicznym API warstwy: [Tak/Nie]
4. Czy istnieje powiązany Edge Case: [np. EC-001 - jak omijamy blokady]
5. Blast Radius: [Jeśli zmieniłem Port/UseCase, jakie Adaptery i Fakes muszę zaktualizować w tym samym commicie?]
```

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-29 | Dominik / AI Architect | Pierwsza wersja, dostosowana do Faz A/B. |
| 1.1 | 2026-05-29 | AI Architect | Uzupełniono specyfikację pod Fazę C (Frontend: HTMX/MapLibre, API Contract, wzorzec wstrzykiwania ClockPort do weryfikacji domenowej oraz Checklista Review). |