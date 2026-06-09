# Agent Specification — specyfikacja agentów LLM

> **Wersja:** 1.3  
> **Data:** 2026-05-31  
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
1. **Głęboka Niemutowalność (Deep Immutability):** Każda nowa reguła weryfikacyjna musi dziedziczyć po `BadgeRule` i być zadeklarowana jako `@dataclass(frozen=True)`. Co więcej, wszystkie pola kolekcji wewnątrz reguł muszą używać niemutowalnych typów natywnych: zawsze używaj `tuple` zamiast `list`, oraz `frozenset` zamiast `set`.
2. Ewaluacja postępu musi polegać na **Matematyce Zbiorów (Set Math)**. Do przecinania weryfikowanych szczytów używaj natywnych operacji Pythona (np. `climbed_ids.intersection(pool_ids)`).
3. **Czas i Kontekst:** Ponieważ reguły są odtwarzane z JSONB, NIE wstrzykuj do nich usług (np. `ClockPort`) przez konstruktor. Czas "teraz" lub daty z profilu przekazuj w metodzie `validate` przez dedykowany obiekt `VerificationContext`.

**Zakazane:**
- Importowanie jakichkolwiek paczek poza `stdlib` Pythona (szczególnie `django`, `pydantic`, `dateutil`).
- Używanie `datetime.now()` (T-02).
- Tworzenie zapytań GIS / PostGIS wewnątrz domeny (R-01).
- Używanie mutowalnych kolekcji (`list`, `set`, `dict`) jako definicji typów dla atrybutów wewnątrz klas reguł domenowych.

---

### AGENT-USECASE-CODE — Implementacja Orkiestracji Aplikacji

**Obszar:** `application/use_cases/`, `application/dto/`  
**Typ:** kodujący

**Zasady:**
1. `UseCase` to jedyne miejsce, w którym można orkiestrować przepływ: DTO -> Domena -> Porty -> Wynik.
2. Zależności zewnętrzne (np. repozytoria bazy danych, `ClockPort`) są wstrzykiwane wyłącznie przez konstruktor (`__init__`).
3. Wyłapuj `DomainException` i pozwól im propagować (lub transformuj) do warstwy prezentacji, gdzie zajmie się nimi globalny middleware.
4. **Weryfikacja Bitemporalna (Invariant T-01):** Każdy Use Case odpowiedzialny za zapis logu wejścia (`AscentLog`) lub weryfikację musi przed przekazaniem wejścia do Domeny przeprowadzić twardą walidację czasową obiektu. Algorytm: Jeśli data wejścia jest mniejsza niż `existence_start` (o ile nie NULL) LUB większa niż `existence_end` (o ile nie NULL), Use Case musi rzucić wyjątek typu `BitemporalTimeError` i zablokować zapis/weryfikację.

**Zakazane:**
- Bezpośredni import i wywołanie `apps.badges.models` (ORM) lub zadań z `tasks.py`.
- Zwracanie obiektów bazy danych na zewnątrz Use Case'a. Zwracaj DTO.
- **Dynamiczne walidatory czasu w Pydantic DTO.** Zakazuje się używania `@field_validator` w Pydantic do oceny reguł zależnych od czasu "teraz" (np. walidacja czy data z requestu nie jest z przyszłości). Data w walidatorze modelu Pydantic staje się "zamrożona" podczas uruchomienia procesu lub prowadzi do naruszenia Invariantu T-02. Logika uwarunkowana czasem "dzisiaj" należy wyłącznie do Use Case'a w oparciu o wstrzyknięty `ClockPort`.

---

### AGENT-API-CONTRACT — Implementacja REST API dla Klientów

**Obszar:** `apps/api/`, `apps/badges/views.py`  
**Typ:** kodujący

**Zasady:**
1. Każdy endpoint przyjmuje wyłącznie surowy format HTTP, który natychmiast musi być zwalidowany do obiektu Pydantic DTO.
2. Endpoint wywołuje przygotowany Use Case pobrany z Kontenera DI (`bootstrap.get_container()`).
3. Endpointy zwracają `JsonResponse` lub `HttpResponse`. 
4. Zwracany dynamiczny stan turysty musi być transportowany **wyłącznie** w formacie `GeoJSON` dla limitowanej liczby punktów (BBox). 
5. Endpointy MVT (`.pbf`) służą wyłącznie do pobierania statycznej topografii i nigdy nie mogą zawierać logiki zależnej od zalogowanego użytkownika (User-Agnostic).

**Zakazane:**
- Obsługa wyjątków typu `try/except DomainValidationError: return JsonResponse(...)` na poziomie każdego widoku. Polegamy na centralnym `RFC7807ErrorMiddleware`.
- Zwracanie modeli ORM. Zawsze używaj metody `model_dump()` na obiekcie DTO zwróconym z Use Case'a.

---

### AGENT-DJANGO-ADMIN — Konfiguracja Panelu Administracyjnego

**Obszar:** `apps/badges/admin.py`  
**Typ:** kodujący

**Zasady:**
1. **Ochrona zasobów przeglądarki (Read-Only GIS):** Poligony, linie i skomplikowane kształty GIS (np. granice państw, regionów turystycznych) muszą być ZAWSZE renderowane w trybie "Tylko do odczytu" (`modifiable = False` w klasach dziedziczących po `LeafletGeoAdmin`).
2. **Edycja Geometrii:** Aktywna edycja i dodawanie na mapie (`modifiable = True`) dozwolone są WYŁĄCZNIE dla modeli punktowych (`PointField`), takich jak `TouristObject`.
3. **Dynamiczne QuerySety:** Nigdy nie przypisuj `.objects.all()` bezpośrednio do pól formularza na poziomie definicji klasy (ryzyko Stale Data). QuerySety dla pól `ModelChoiceField` i podobnych ZAWSZE inicjalizuj wewnątrz metody `__init__` formularza (`self.fields['moje_pole'].queryset = ...`).
4. **Otwarty Słownik Typów:** Pole type w modelu TouristObject jest celowo zdefiniowane jako czysty CharField (bez nałożonego wymogu choices na poziomie bazy). Gwarantuje to elastyczność przy asymilacji nowych typów z OSM. Nie konwertuj tego pola na zablokowany Enum w modelu. Ułatwienia UX realizowane są wyłącznie w warstwie formularzy (np. <datalist>).
5. **Bezpieczeństwo HTML (XSS Prevention i Mypy):** Podczas tworzenia niestandardowych widżetów formularzy lub kolumn z linkami (`@admin.display`) **bezwzględnie zakazuje się**:
   - Używania funkcji `mark_safe()` do omijania ostrzeżeń Bandit (S308). Używaj wyłącznie `format_html` oraz `format_html_join`.
   - Rzutowania wyniku `format_html()` na zwykły string (tj. `str(format_html(...))`) w celu uspokojenia lintera Mypy. Rzutowanie takie niszczy właściwość `SafeString`, psując renderowanie w przeglądarce (Edge Case EC-029). Zawsze używaj: `# type: ignore[no-any-return]`.
6. **Akcje masowe zdejmujące obciążenie (Celery Actions):** Jeśli piszesz niestandardową akcję w panelu (`@admin.action`), która aktualizuje statusy i wysyła zadania do Celery, **bezwzględnie** filtruj QuerySet przed przetworzeniem (np. odrzucając obiekty niekwalifikujące się do akcji) oraz używaj `.save(update_fields=[...])`. Zapisywanie całych obiektów (`obj.save()`) w pętli wyzwalającej taski prowadzi do zjawiska *Race Condition* i nadpisywania pól zmienionych w międzyczasie przez workery w tle.
7. **Nowoczesny Interfejs (Django Unfold):** Projekt korzysta z biblioteki `django-unfold` jako nakładki na interfejs administracyjny. 
   - Konfiguracja globalna interfejsu (np. niestandardowe ikony, nawigacja) znajduje się w słowniku `UNFOLD` w `config/settings.py`.
   - Wszystkie klasy `ModelAdmin` w systemie **MUSZĄ** dziedziczyć po klasach dostarczanych przez `unfold` (np. `from unfold.admin import ModelAdmin`), jeśli nie wchodzą w konflikt z zewnętrznymi pakietami takimi jak `django-leaflet`.
   - Rejestracja i unifikacja narzędzi (np. odpięcie i podpięcie standardowego admina na rzecz klasy `UnfoldAdminSite`) następuje wyłącznie poprzez metodę `ready()` wewnątrz konfiguracji w `apps.py` głównej aplikacji, unikając zaśmiecania globalnego pliku `urls.py`.

**Zakazane:**
- Ręczne tworzenie formularzy HTML dla map. Zawsze korzystaj z integracji biblioteki `django-leaflet`.

---

### AGENT-FRONTEND-CODE — Implementacja Widoków i Map (HTMX + MapLibre)

**Obszar:** `apps/templates/`, `apps/static/`  
**Typ:** kodujący

**Zasady:**
1. Aplikacja webowa opiera się na Server-Side Rendering (SSR) z użyciem **Django Templates**.
2. Dynamika UI realizowana jest wyłącznie przez **HTMX** (np. `hx-get`, `hx-target`).
3. Wyświetlanie map realizowane jest w **MapLibre GL JS** poprzez czysty JavaScript osadzony w dedykowanych plikach statycznych. Warstwy zasilane są z endpointów GeoJSON lub MVT wystawianych przez Django.
4. **Zasada Map Spamming Defense (Debounce):** Każda akcja przesuwania mapy przez użytkownika (eventy `moveend`, `zoomend`), która odpytuje backend o nowe obiekty, **musi** posiadać opóźnienie (Debounce) na poziomie minimum **300ms**.

**Zakazane:**
- Tworzenie komponentów React / Vue. System nie używa Node.js/NPM do budowania frontendu.

---

### AGENT-INFRA-CODE — Adaptery, Repozytoria i Celery

**Obszar:** `infrastructure/adapters/`, `apps/badges/tasks.py`  
**Typ:** kodujący

**Zasady:**
1. Zapytania GIS (`ST_DWithin`, `ST_Union`) wykonuj tylko w adapterach/repozytoriach.
2. Jeśli tworzysz nową fabrykę reguły (`_build_...`), w przypadku braku wymaganego atrybutu bezwzględnie rzucaj `ValueError` (Fail-Fast, R-02).
3. Taski Celery w `tasks.py` są cienkimi wrapperami. Muszą wyciągać Use Case z `bootstrap.get_container()`.
4. **Wydajność zapytań przestrzennych:** Nigdy nie używaj w zapytaniach precyzyjnych i zasobożernych funkcji obliczających dokładną odległość (np. `ST_DistanceSpheroid` czy `distance()`) w pętlach po wszystkich obiektach. Do weryfikacji przynależności terytorialnej używaj wyłącznie szybkich operatorów opartych na indeksach GiST (np. `geom__distance_lte` z wykorzystaniem `D(m=...)` oraz metody `.intersects()`). Szybkość wykonania asynchronicznego Taska ma zawsze wyższy priorytet niż milimetrowa dokładność matematyczna.
5. **Skrypty diagnostyczne i analityczne (Bypass domyślnego sortowania):** Każdy skrypt, który wyszukuje anomalie, braki danych (np. brakujący link Wiki) lub zduplikowane obiekty, **musi** jawnie nadpisywać domyślne sortowanie modelu (zdefiniowane w klasie `Meta`) za pomocą `.order_by('id')` lub `.order_by('created_at')`. Gwarantuje to chronologiczny i metodyczny przegląd danych dla administratora naprawiającego bazę.
6. **Timeout Budgeting (Budżetowanie czasu):** Każde synchroniczne zapytanie HTTP do zewnętrznego API (o ile nie zostało oddelegowane do Celery) musi mieć bezwzględnie określony parametr `timeout`. Suma maksymalnego czasu oczekiwania włączając ponowienia (Retry) musi zamknąć się w okienku **< 15 sekund**, aby nie doprowadzić do zabicia głównego wątku żądania HTTP (Gunicorn/WSGI timeout) przed zwróceniem sformatowanej odpowiedzi RFC 7807 do klienta.
7. **Zasada Uprzejmego Pełzacza (Bulk API Fetching):** Jeśli system musi zaktualizować lub pobrać dane dla wielu obiektów z zewnętrznego API, bezwzględnie używaj zapytań grupowych (Bulk Query / Batching) w jednym żądaniu HTTP. Wysyłanie zapytań HTTP w pętli `for` dla wielu obiektów zagraża stabilności serwera i naraża system na błędy 429 (Too Many Requests).

**Zakazane:**
- Ciche łapanie wyjątków (`except Exception: pass`) w warstwie GIS i hydracji.
- Metody `POST` i twardy `Accept: application/json` w zapytaniach do Overpass API.
- Poleganie na alfabetycznym `Meta.ordering` z modeli w skryptach audytujących, co gubi kontekst chronologiczny błędów.
- **Hardkodowanie harmonogramów Celery Beat:** Zakazuje się modyfikowania pliku `config/celery.py` w celu dodania słownika `app.conf.beat_schedule`. Harmonogramy są zarządzane operacyjnie wyłącznie przez interfejs graficzny bazy danych (`django-celery-beat`), zgodnie z zasadą Operational Excellence.

---

### AGENT-DB-MIGRATIONS — Migracje i Modele Danych

**Obszar:** `apps/[app_name]/models.py`, `migrations/`  
**Typ:** kodujący

**Zasady:**
1. Modele w Django są tylko "workami na dane" dla infrastruktury.
2. Klastrowanie obiektów (`parent_object`) nie posiada zabezpieczenia przed cyklem bezpośrednio w bazie. Zawsze zabezpieczaj to w metodzie `clean()` formularza.
3. **Otwarty Słownik Typów:** Pole `type` w modelu `TouristObject` jest celowo zdefiniowane jako czysty `CharField` (bez nałożonego wymogu `choices` na poziomie bazy danych). Gwarantuje to elastyczność przy asymilacji nowych, nieznanych typów z OSM (np. "Wodospad"). Nie próbuj konwertować tego pola na zablokowany `Enum` w modelu. Ułatwienia UX (np. lista podpowiedzi) są realizowane wyłącznie na poziomie widżetów formularza (np. `<datalist>`).

**Zakazane:**
- `DROP COLUMN` lub cofanie migracji PostGIS bez jawnej autoryzacji człowieka.

---

## Instrukcje dla Agenta Architektonicznego i Recenzującego

### AGENT-BLAST-RADIUS — Modyfikacje wspólnych Portów

Zanim zmienisz interfejs w `application/ports/` lub sygnaturę metody domenowej:
1. Przeszukaj całe repozytorium pod kątem wywołań.
2. Zaktualizuj **WSZYSTKIE** Adaptery (w tym `tests/fakes/`), które implementują dany Port w tym samym commicie.

### AGENT-REVIEW — Code Review Pull Requesta

Przed zatwierdzeniem kodu agent musi sprawdzić poniższą checklistę:
```
INVARIANTY
[ ] Czy żadna zmiana nie narusza INVARIANTS.md (np. czy Czysta Domena nie używa GIS)?
[ ] Czy zmiana w regułach biznesowych posiada test mutacyjny weryfikujący krawędzie błędu?
[ ] Czy użyto ClockPort dla pojęcia czasu?

BEZPIECZEŃSTWO
[ ] Czy nowy endpoint zwraca błędy zgodne ze standardem RFC 7807 (ERROR_HANDLING.md)?

ARCHITEKTURA
[ ] Czy zachowano jednokierunkowość importów (w dół do domain/)?
[ ] Czy Task Celery nie zawiera logiki, a jedynie wrapper Use Case'a?
[ ] Czy przestrzegano trybu Read-Only dla poligonów na mapach Admina?
```

---

## Instrukcja obowiązkowa przed każdym zadaniem z kodowaniem

Przed wygenerowaniem pierwszego bloku kodu, agent musi odpowiedzieć na 5 pytań w formie listy punktowanej:

```
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
| 1.1 | 2026-05-29 | AI Architect | Uzupełniono specyfikację pod Fazę C. |
| 1.2 | 2026-05-30 | AI Architect | Dodano sekcję AGENT-DJANGO-ADMIN. |
| 1.3 | 2026-05-31 | AI Architect | Dodano regułę optymalizacyjną dla zapytań GIS (indeksy GiST zamiast dokładnego dystansu) w sekcji AGENT-INFRA-CODE. |