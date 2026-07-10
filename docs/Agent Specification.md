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

- **Ochrona struktur danych:** Bezwzględnie zakazuje się pozostawiania przecinków na końcu przypisań zmiennych słownikowych na poziomie modułu (np. `MOJ_SLOWNIK = {...},`), aby zapobiec niejawnej konwersji do `tuple` (Edge Case EC-049).

---

### AGENT-USECASE-CODE — Implementacja Orkiestracji Aplikacji

**Obszar:** `application/use_cases/`, `application/dto/`  
**Typ:** kodujący

**Zasady:**
1. `UseCase` to jedyne miejsce, w którym można orkiestrować przepływ: DTO -> Domena -> Porty -> Wynik.
2. Zależności zewnętrzne (np. repozytoria bazy danych, `ClockPort`) są wstrzykiwane wyłącznie przez konstruktor (`__init__`).
3. Wyłapuj `DomainException` i pozwól im propagować (lub transformuj) do warstwy prezentacji, gdzie zajmie się nimi globalny middleware.
4. **Weryfikacja Bitemporalna (Invariant T-01):** Każdy Use Case odpowiedzialny za zapis logu wejścia (`AscentLog`) lub weryfikację musi przed przekazaniem wejścia do Domeny przeprowadzić twardą walidację czasową obiektu. Algorytm: Jeśli data wejścia jest mniejsza niż `existence_start` (o ile nie NULL) LUB większa niż `existence_end` (o ile nie NULL), Use Case musi rzucić wyjątek typu `BitemporalTimeError` i zablokować zapis/weryfikację.
5. **Separacja DTO (Command vs Query):** Bezwzględnie zakazuje się używania tego samego modelu Pydantic do przyjmowania danych z API oraz do transportowania zhydrowanych danych z bazy.
   - Wejście z API musi używać lekkiego `[Entity]InputDTO` (np. `AscentInputDTO` z samym `peak_id` i `date`).
   - Dane wyciągane z bazy i przekazywane do Czystej Domeny muszą używać bogatego `[Entity]DTO` (np. `AscentDTO` wzbogacone przez adapter bazy o wyliczone z CQRS `region_ids`).
6. **Ochrona Stanu w Pydantic (Mutable Defaults):** Zakazuje się używania mutowalnych wartości domyślnych w klasach Pydantic (np. `club_join_dates: dict = {}`). Zawsze używaj `Field(default_factory=dict)`, aby zapobiec wyciekom stanu pamięci (Memory Leak) pomiędzy różnymi żądaniami w API.
7. **Segregacja DTO (Input vs Zhydrowane):** Bezwzględnie zakazuje się używania tego samego obiektu DTO do odbierania danych z API oraz do transportu danych odczytanych z bazy.
   - `[Entity]InputDTO` (np. `AscentInputDTO`) służy tylko do walidacji surowych danych z zewnątrz (np. formularz HTML/API).
   - `[Entity]DTO` (np. `AscentDTO`) to bogaty, zhydrowany snapshot z bazy danych, często wzbogacony o pre-kalkulowane pola z infrastruktury (np. płaskie `region_ids` z CQRS dla reguł Wildcard), służący do wstrzykiwania stanu do Czystej Domeny.
8. **Ochrona Stanu w Pydantic:** Zakazuje się używania mutowalnych wartości domyślnych w klasach `BaseModel` (np. `club_join_dates: dict = {}`). Zawsze używaj `Field(default_factory=dict)`, aby zapobiec wyciekom stanu pamięci pomiędzy różnymi żądaniami w API.

**Zakazane:**
- Bezpośredni import i wywołanie `apps.badges.models` (ORM) lub zadań z `tasks.py`.
- Zwracanie obiektów bazy danych na zewnątrz Use Case'a. Zwracaj DTO.
- **Dynamiczne walidatory czasu w Pydantic DTO.** Zakazuje się używania `@field_validator` w Pydantic do oceny reguł zależnych od czasu "teraz" (np. walidacja czy data z requestu nie jest z przyszłości). Data w walidatorze modelu Pydantic staje się "zamrożona" podczas uruchomienia procesu lub prowadzi do naruszenia Invariantu T-02. Logika uwarunkowana czasem "dzisiaj" należy wyłącznie do Use Case'a w oparciu o wstrzyknięty `ClockPort`.

- **Leniwe Importy (Inline Imports):** Bezwzględny zakaz stosowania lokalnych importów wewnątrz funkcji/metod (np. `import json` wewnątrz bloku `try`), jeśli moduł ten jest wykorzystywany w deklaracji `except` w tej samej funkcji. Prowadzi to do `UnboundLocalError` (Edge Case EC-051). Wszystkie standardowe importy muszą znajdować się na górze pliku.
- **Zasada Bogatego Kontekstu Relacyjnego w Widokach HTML:** 
Jeśli widok Django (`views.py`) pobiera obiekty powiązane (np. odznaki dla danego szczytu) celem wyświetlenia ich w szablonie, 
- **bezwzględnie zakazuje się** spłaszczania ich do list samych stringów (np. samych nazw). Widok musi zawsze konstruować słowniki zawierające klucze identyfikacyjne wymagane do routingu (np. `[{"code": obj.code, "name": obj.name}]`). Umożliwia to szabronom HTML budowanie pełnoprawnej sieci linków (Hyperlinking) bez konieczności kosztownych zapytań o ID w samym szablonie.

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
6. **Ochrona przed IDOR w kontrolerach API:** Widok API nigdy nie może ufać parametrowi `user_id` lub `profile_id` przesłanemu w ciele żądania (JSON Payload). Identyfikacja użytkownika i profilu musi ZAWSZE następować na podstawie `request.user.id` oraz bezpiecznej sesji `request.session.get("active_profile_id")`.
7. **Trailing Slashes:** Każda definicja ścieżki w `urls.py` musi kończyć się ukośnikiem (`/`). Wszystkie wywołania `fetch()` w JavaScript lub testach muszą odpytywać adres zawierający ten ukośnik na końcu (ochrona przed `301 Redirect` gubiącym payload POST).

**Zakazane:**
- Obsługa wyjątków typu `try/except DomainValidationError: return JsonResponse(...)` na poziomie każdego widoku. Polegamy na centralnym `RFC7807ErrorMiddleware`.
- Zwracanie modeli ORM. Zawsze używaj metody `model_dump()` na obiekcie DTO zwróconym z Use Case'a.
- **Zakaz używania djangowych dekoratorów autoryzacji w API:** Nie używaj `@login_required` ani `@method_decorator(require_auth)` nad klasami widoków w `apps/api/views.py`. Walidacja tożsamości musi odbywać się **wewnątrz ciała metody** (np. `def post(self, request):`) poprzez wywołanie lokalnego helpera: `auth_error = _require_auth(request); if auth_error: return auth_error`. 
- **Zakaz list w dekoratorach klas:** Używaj wyłącznie `@method_decorator(csrf_exempt, name="dispatch")`. Przekazywanie list dekoratorów (np. `[csrf_exempt, require_auth]`) w tym projekcie powoduje konflikty z linterem ruff i testami.
- 
- **Wyjątki:** Przy łapaniu wielu wyjątków bezwzględnie używaj krotek `except (ErrorA, ErrorB):`. Składnia z przecinkiem z Pythona 2 wywołuje `SyntaxError`.

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
- **Reguła Integracji Zewnętrznych Paczek:** Jeśli dodajesz zewnętrzną paczkę posiadającą własny panel administracyjny (np. `django-celery-beat`, `django-allauth`), masz bezwzględny obowiązek "unfoldyzacji" tych modeli. Należy je wyrejestrować (`unregister`) z domyślnego Admina i zarejestrować ponownie z dziedziczeniem po klasach Unfold, aby uniknąć ukrycia przycisków akcji przez CSS Reset Tailwinda (Zgodnie z EC-043).

**Zakazane:**
- Ręczne tworzenie formularzy HTML dla map. Zawsze korzystaj z integracji biblioteki `django-leaflet`.
- **Używanie domyślnych filtrów w `list_filter` dla dużych tabel relacyjnych:** Bezwzględnie zakazuje się wpisywania nazw pól `ForeignKey` lub `ManyToManyField` do atrybutu `list_filter`, jeśli tabela docelowa może zawierać tysiące rekordów (np. `TouristObject`). Zamiast tego wymagane jest napisanie dedykowanej klasy dziedziczącej po `SimpleListFilter`, która optymalizuje zapytanie (np. pomija nieużywane rekordy/sieroty) i chroni przeglądarkę Administratora przed zamrożeniem pamięci (Edge Case EC-053). Wyszukiwanie tekstowe po takich relacjach realizuj przez `search_fields = ("relacja__pole",)`.

---

### AGENT-FRONTEND-CODE — Implementacja Widoków i Map (HTMX + MapLibre)

**Obszar:** `apps/templates/`, `apps/static/`  
**Typ:** kodujący

**Zasady:**
1. Aplikacja webowa opiera się na Server-Side Rendering (SSR) z użyciem **Django Templates**.
2. Dynamika UI realizowana jest wyłącznie przez **HTMX** (np. `hx-get`, `hx-target`).
3. Wyświetlanie map realizowane jest w **MapLibre GL JS** poprzez czysty JavaScript osadzony w dedykowanych plikach statycznych. Warstwy zasilane są z endpointów GeoJSON lub MVT wystawianych przez Django.
4. **Zasada Map Spamming Defense (Debounce):** Każda akcja przesuwania mapy przez użytkownika (eventy `moveend`, `zoomend`), która odpytuje backend o nowe obiekty, **musi** posiadać opóźnienie (Debounce) na poziomie minimum **300ms**.
5. **Wzorzec wstrzykiwania stanu do JS (Global Window State):** 
Zabrania się wstrzykiwania logiki z użyciem tagów `{{ }}` z Django Templates wprost do plików `.js` (które muszą być statyczne). Jeśli plik `map.js` wymaga kontekstu z widoku (np. identyfikatora odznaki do przefiltrowania mapy lub weryfikacji pakietu PRO), widok HTML nad nim generuje zhermetyzowany blok `<script>window.NAZWA_ZMIENNEJ = "{{ wartosc }}";</script>`. Kod JS odczytuje tę wartość jako opcjonalną (np. `if (window.NAZWA_ZMIENNEJ) { ... }`).

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
8. **Web Scraping z Fail-Silently:** Moduły służące do pobierania danych z nienadzorowanych stron WWW (np. `BeautifulSoupNewsScraper`) podlegają zasadzie cichego niepowodzenia. Wszelkie błędy parsowania struktury HTML (`AttributeError`, `NoneType`) oraz błędy sieciowe muszą być wyłapane, zaraportowane jako `logger.warning` i w żaden sposób nie mogą wyrzucać wyjątków przerywających działanie wątku (Task Celery musi zakończyć się sukcesem i statusem przerwania operacji).
9. **Minimalizm Zależności Scrapowania:** Zakazuje się wprowadzania bibliotek kompilowanych (np. `lxml`) oraz ciężkich klientów HTTP (np. `requests`) do prostych zadań scrapingu. Zawsze używaj `urllib.request` oraz wbudowanego w BeautifulSoup parsera `'html.parser'`.
8. **Prewencja zjawiska N+1 (Eager Loading):** Przy każdym zapytaniu ORM, które pobiera listę obiektów, a następnie w pętli odwołuje się do ich relacji (np. sprawdzanie, do jakich odznak należy dany szczyt), masz **bezwzględny obowiązek** użycia `select_related()` (dla kluczy obcych / relacji 1:1) lub `prefetch_related()` (dla relacji M2M i odwrotnych kluczy obcych). Zabrania się generowania setek zapytań SQL podczas renderowania list i rankingów w Pythonie/HTML.
10. **Wzorzec Łączenia Redis z Django ORM (Ochrona N+1):** W widokach lub serwisach agregujących (np. rankingi), gdzie część stanu żyje w zmaterializowanym cache Redis, a reszta w bazie relacyjnej, bezwzględnie zakazuje się iterowania po kluczach Redis i odpytywania bazy w pętli (np. `Model.objects.get(id=...)`). Należy zawsze wyekstrahować płaską listę identyfikatorów, a następnie użyć klauzuli `filter(id__in=valid_ids)` wspartej odpowiednim `select_related` / `prefetch_related`.
11. **Zapytania Bitemporalne i Wektorowe (Historyczne):** Przy konstruowaniu zapytań ORM filtrujących po dacie dla encji posiadających wektory czasu (np. `BadgeVersionModel.valid_from/valid_to` lub `TouristObject.existence_start/end`), zakazuje się ufania wyłącznie kolumnie początkowej (`lte`). Należy bezwzględnie implementować pełne okno czasowe za pomocą klauzul `Q`, traktując wartość `NULL` jako zbiór otwarty na nieskończoność (np. `Q(existence_end__isnull=True) | Q(existence_end__gte=date)`).

**Zakazane:**
- Ciche łapanie wyjątków (`except Exception: pass`) w warstwie GIS i hydracji.
- Metody `POST` i twardy `Accept: application/json` w zapytaniach do Overpass API.
- Poleganie na alfabetycznym `Meta.ordering` z modeli w skryptach audytujących, co gubi kontekst chronologiczny błędów.
- **Hardkodowanie harmonogramów Celery Beat:** Zakazuje się modyfikowania pliku `config/celery.py` w celu dodania słownika `app.conf.beat_schedule`. Harmonogramy są zarządzane operacyjnie wyłącznie przez interfejs graficzny bazy danych (`django-celery-beat`), zgodnie z zasadą Operational Excellence.

## Wzorzec: Użycie DSN (Data Source Name) w `settings.py`

Zabrania się definiowania w pliku `settings.py` (oraz wymuszania przekazywania przez `.env`) rozbitych zmiennych środowiskowych dla połączeń z bazami danych lub usługami (np. `DB_HOST`, `DB_USER`, `DB_PASSWORD`). 
Zgodnie ze standardem *12-Factor App*, połączenia muszą być definiowane w postaci zunifikowanych adresów URL (np. `DATABASE_URL=postgis://user:pass@host:5432/dbname`). 
W pliku `config/settings.py` adres ten jest rozbijany na czynniki pierwsze za pomocą biblioteki standardowej `urllib.parse` i mapowany na format wymagany przez docelowy framework (Django).

---

### AGENT-DB-MIGRATIONS — Migracje i Modele Danych

**Obszar:** `apps/[app_name]/models.py`, `migrations/`  
**Typ:** kodujący

**Zasady:**
1. Modele w Django są tylko "workami na dane" dla infrastruktury.
2. Klastrowanie obiektów (`parent_object`) nie posiada zabezpieczenia przed cyklem bezpośrednio w bazie. Zawsze zabezpieczaj to w metodzie `clean()` formularza.
3. **Otwarty Słownik Typów:** Pole `type` w modelu `TouristObject` jest celowo zdefiniowane jako czysty `CharField` (bez nałożonego wymogu `choices` na poziomie bazy danych). Gwarantuje to elastyczność przy asymilacji nowych, nieznanych typów z OSM (np. "Wodospad"). Nie próbuj konwertować tego pola na zablokowany `Enum` w modelu. Ułatwienia UX (np. lista podpowiedzi) są realizowane wyłącznie na poziomie widżetów formularza (np. `<datalist>`).
4. **Zasada DRY dla Relacji M2M w Hierarchii Geograficznej:** Zezwala się (i zaleca) wykorzystywanie domieszek (Mixinów), takich jak `PhysicalRegionMixin`, do definiowania współdzielonych relacji `ManyToManyField("self")`. Django natywnie zinterpretuje `"self"` dla każdego modelu dziedziczącego po Mixinie z osobna. Domieszki te muszą być wprowadzane z ostrożnością w środowiskach typu `managed = False` (zgodnie z obejściem RunSQL opisanym w EC-062).

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