# Edge Cases — przypadki brzegowe

> **Wersja:** 2.0  
> **Data:** 2026-06-20  
> **Właściciel:** Dominik / AI Architect  
>
> **Jak używać:** Zanim zaczniesz implementować funkcję lub "refaktoryzować na czysto" dziwnie wyglądający kod, sprawdź tu, czy ten kod nie rozwiązuje znanej pułapki (np. blokady na zaporach sieciowych WAF, dziwnego zachowania bazy lub OSM).

---

## Globalna zasada: open edge case blokuje PR

Każdy wpis ze statusem `open` musi mieć jedno z poniższych przed mergem PR, który dotyka tego obszaru:
- **Status zmieniony na `resolved`** — z opisem rozwiązania i nazwą testu.
- **Status zmieniony na `wont-fix`** — z uzasadnieniem, dlaczego świadomie nie obsługujemy.

---

## 1. Integracja i Zasilanie Danych (OSM)

### EC-001 — Odrzucanie zapytań przez OSM API (Błąd 406 Not Acceptable)
**Obszar:** `infrastructure/adapters/osm_adapter.py`  
**Odkryty:** 2026-05-21 przez testy integracyjne na środowisku deweloperskim.  
**Status:** `resolved`  
**Opis:** Przy masowym pobieraniu (Bulk Fetching) oraz pojedynczym odpytywaniu niektórych niemieckich klastrów Overpass API (`overpass-api.de`, `lz4...`), serwery bezwzględnie odrzucają połączenie zwracając błąd `406 Not Acceptable`. Jest to działanie zaporowe (WAF / Load Balancer) chroniące darmową infrastrukturę przed skryptami używającymi metody POST bez odpowiednich nagłówków lub próbującymi wymusić ścisłą negocjację treści.  
**Rozwiązanie / workaround:** Zamiast metody `POST`, wszystkie zapytania Overpass QL są przesyłane metodą `GET` bezpośrednio w parametrach adresu URL (`urllib.parse.urlencode({"data": query})`). Zabrania się używania nagłówka `Accept: application/json`. Problem rozwiązany strukturalnie przez Linear Backoff Retry (maksymalnie 15 prób).  
**Test:** `test_successful_fetch_uses_get_method`

### EC-002 — Nieskończona pętla Nocnego Stróża i martwe węzły (Ghost Nodes)
**Obszar:** `application/use_cases/fetch_osm_data.py` (`RunOsmNightWatchmanUseCase`)  
**Odkryty:** 2026-05-22 przy testowaniu harmonogramów Celery.  
**Status:** `resolved`  
**Opis:** Obiekt w OSM, który nie był edytowany przez społeczność np. od 10 lat, ma wciąż stary `timestamp`. Jeśli system aktualizuje bazę tylko w momencie wykrycia "nowej daty w OSM", obiekty te nigdy nie schodzą z kolejki "do sprawdzenia" i Nocny Stróż utyka w nieskończonej pętli zapytań o te same 100 szczytów każdej nocy.  
**Rozwiązanie / workaround:** Kolumna `last_sync_check`. Niezależnie od tego, czy tagi w OSM uległy zmianie czy nie, po każdym zapytaniu system nadpisuje czas lokalnego rekordu, spychając go na sam koniec kolejki. Jeśli z paczki 100 węzłów powróci tylko 99, ten jeden zaginiony zostaje zgłoszony do `OsmSyncConflict` jako obiekt prawdopodobnie usunięty z OSM.  
**Test:** `test_watchman_ghost_node_detection_and_queue_rotation`

### EC-003 — Blokowanie kafelków mapy w panelu Admina (Tile Usage Policy)
**Obszar:** `config/settings.py`, `apps/badges/admin.py`  
**Odkryty:** Podczas konfiguracji widżetu `django-leaflet`.  
**Status:** `resolved`  
**Opis:** Serwery kafelków OpenStreetMap blokują żądania z przeglądarek, które nie wysyłają nagłówka `Referer`. Domyślna polityka bezpieczeństwa Django (`same-origin`) ukrywa ten nagłówek przy odpytywaniu zewnętrznych domen, co skutkuje brakiem podkładu mapowego w panelu Administratora.  
**Rozwiązanie / workaround:** Do `config/settings.py` dodano `SECURE_REFERRER_POLICY = "origin-when-cross-origin"`. Zezwala to przeglądarce na wysłanie pochodzenia do serwerów kafelkowych bez łamania globalnego bezpieczeństwa aplikacji.

---

## 2. Geometria i Przetwarzanie Przestrzenne (PostGIS)

### EC-010 — Rzutowanie przy ST_DWithin (Metry vs Stopnie)
**Obszar:** `infrastructure/adapters/persistence/region_cache_repo.py`  
**Odkryty:** 2026-05-18 podczas analizy wydajności zapytań przestrzennych.  
**Status:** `resolved`  
**Opis:** Funkcja `ST_DWithin` na geometrii sferycznej (`EPSG:4326`) operuje w stopniach, co daje niedokładne wyniki, zamieniając bufor kołowy w elipsę w naszej szerokości geograficznej.  
**Rozwiązanie / workaround:** ORM GeoDjango obsługuje to przez obiekt `D(m=50)`. Obliczenia odległości do wyświetlenia używają rzutowania w locie: `.transform(3857, clone=True)`.  
**Test:** `[brakuje, TODO — weryfikacja rzutowania 3857 w testach integracyjnych PostGIS]`

### EC-011 — Ciche zatajanie błędu geometrii (Silent Fail w GEOS)
**Obszar:** `build_tourist_region_geometry.py` oraz `region_cache_repo.py`  
**Odkryty:** 2026-05-26 podczas weryfikacji jakości kodu (Review ADR-002).  
**Status:** `resolved`  
**Opis:** W procesie łączenia mezoregionów w Region Turystyczny (`unary_union`), użycie `except Exception: return None` maskowało fakt, że baza może zawierać uszkodzone lub samoprzecinające się poligony.  
**Rozwiązanie / workaround:** Zero tolerancji dla cichych błędów przy geometrii (Fail-Fast). Usunięto maskujące bloki `except`. Wyjątki infrastrukturalne logowane są jako `ERROR` w `tasks.py`.  
**Test:** `test_geometry_union_fails_fast_on_invalid_polygon`

### EC-038 — XML Bomb (XXE) w plikach GPX
**Obszar:** `infrastructure/adapters/gpx_parser.py`  
**Status:** `resolved`  
**Opis:** Standardowa biblioteka `xml.etree` jest podatna na ataki Denial of Service (Billion Laughs) przy parsowaniu złośliwych plików wysłanych przez użytkowników. Linter bezpieczeństwa (Bandit S314) zablokował wdrożenie parsera opartego na stdlib.  
**Rozwiązanie / workaround:** Zastosowano bibliotekę `defusedxml`, która bezpiecznie analizuje drzewo XML odrzucając ataki rekursywne.

### EC-039 — Błędy rysowania w OSM (Mikroszczeliny między poligonami)
**Obszar:** `calculate_neighbors.py` (Zależności poziome regionów)  
**Status:** `resolved`  
**Opis:** Funkcja `ST_Touches` do wyznaczania sąsiadujących mezoregionów pomijała wiele powiązań z powodu błędów kartografów w OSM (mikroszczeliny lub nachodzące na siebie poligony).  
**Rozwiązanie / workaround:** Zrezygnowano z `ST_Touches` na rzecz `shape__distance_lte=(..., D(m=50))`. Dodany bufor 50 metrów wchłonął wszystkie błędy kartograficzne, a ciężar obliczeń przeniesiono do jednorazowego skryptu ładującego wyniki do tabeli M2M.

### EC-040 — MVT z PostGIS gubi duże identyfikatory (BigInt)
**Obszar:** `django_mvt_repo.py` i `map.js`  
**Status:** `resolved`  
**Opis:** Protobuf (PBF) w kafelkach MVT generowanych przez PostGIS błędnie rzutuje duże ID (`BigAutoField`), co skutkowało brakiem możliwości kliknięcia regionu na mapie (błąd `undefined`).  
**Rozwiązanie / workaround:** W zapytaniu SQL twardo zrzutowano ID na ciąg znaków (`t.id::text AS db_id_str`). Front-end MapLibre zaktualizowany by ufać wyłącznie tekstowej zmiennej `db_id_str`.

### EC-058 — Problem N+1 przy weryfikacji Bitemporalności (Bulk Operations)
**Obszar:** `application/use_cases/bulk_log_ascents.py`, `AscentLogRepositoryPort`  
**Status:** `resolved`  
**Opis:** Podczas przetwarzania paczki np. 30 szczytów zdekodowanych z pliku GPX, odpytywanie bazy o ramy bitemporalne wewnątrz pętli `for` generowało 30 osobnych transakcji (zjawisko N+1).  
**Rozwiązanie / workaround:** Zdefiniowano nową sygnaturę portu `get_objects_lifespans(peak_ids: set[int])`, która używa `values_list` z klauzulą `IN`. Baza odpowiada jednym zapytaniem zwracającym słownik. Wewnątrz pętli Python odpytuje już tylko lokalny słownik w RAM.

### EC-059 — Optymalizacja wydajności wyszukiwania wzdłuż Śladu GPX
**Obszar:** `infrastructure/adapters/gpx_parser.py`, `django_map_repo.py`  
**Status:** `resolved`  
**Opis:** Wgranie śladu GPX z całodniowego przejścia szlaku generuje geometrię z kilkudziesięciu tysięcy wierzchołków. Uderzenie z taką figurą bezpośrednio do PostGIS mogłoby zawiesić serwer.  
**Rozwiązanie / workaround:** Architektura wieloetapowa: parser GPX dokonuje agresywnego uproszczenia (`simplify(0.0001)`), redukując liczbę wierzchołków. Zoptymalizowana linia przesyłana jest jako tekst WKT. Dopiero adapter `django_map_repo` odtwarza WKT i przetwarza szybkim filtrem `distance_lte` z indeksami GiST.

### EC-062 — Relacje M2M zignorowane przez modele `managed = False`
**Obszar:** `apps/badges/models.py`, `migrations/`  
**Status:** `resolved`  
**Opis:** Dodanie `ManyToManyField` do modeli oznaczonych jako `managed = False` skutkuje tym, że `makemigrations` całkowicie ignoruje konieczność utworzenia tabel pośrednich.  
**Rozwiązanie / workaround:** Twardy zakaz manipulowania flagą `managed` w celu wymuszenia migracji. Zamiast tego używa się **Pustej Migracji** (`makemigrations --empty`) z instrukcją `migrations.RunSQL` zawierającą ręcznie napisany `CREATE TABLE IF NOT EXISTS`.

---

## 3. Administracja i Integracja UX (Django Admin)

### EC-020 — Znikający (Niezapisany) Stopień Odznaki (Django Inlines)
**Obszar:** `apps/badges/admin.py` (`BadgeTierInline`)  
**Odkryty:** 2026-05-23 przy definiowaniu historycznej wersji "Korony Gór Polskich".  
**Status:** `resolved`  
**Opis:** Jeśli wartości domyślne dla wiersza Inline są wpisane w model bazy danych, a administrator nie zmieni ani jednego pola, mechanizm `has_changed()` Django ignoruje cały wiersz i go nie zapisuje. Prowadzi to do tworzenia odznak "bez stopni".  
**Rozwiązanie / workaround:** Zakaz stosowania wartości `default` na poziomie modelu dla słowników Enum używanych w Inline'ach. Model wymusza puste pole bazowe (`---------`), administrator musi świadomie wybrać wartość.  
**Test:** `test_badge_tier_requires_explicit_choice_to_save`

### EC-021 — Konflikt "through" przy MultipleChoice (M2M)
**Obszar:** `apps/badges/admin.py` (`BadgeVersionAdmin`)  
**Odkryty:** 2026-05-21 przy projektowaniu "Wielkiej Korony Sudetów".  
**Status:** `resolved`  
**Opis:** Użycie widżetu `filter_horizontal` wyrzuca błąd aplikacji, jeśli `ManyToManyField` ma zdefiniowaną niestandardową tabelę łączącą przez `through="..."`. Django zgłasza `admin.E013`.  
**Rozwiązanie / workaround:** Zrezygnowano ze śledzenia dodatkowych atrybutów dla puli obiektów odznaki. `BadgeVersionModel.pool_peaks` to prosta, automatyczna relacja M2M. Ewentualna kolejność zdefiniowana jest w Regułach Biznesowych (JSONB).  
**Test:** `test_pool_peaks_uses_implicit_m2m_table`

### EC-022 — Cykliczne relacje w klastrach (A → B → A)
**Obszar:** `apps/badges/models.py` (`TouristObject`), `ProximityCandidateAdmin`  
**Odkryty:** 2026-05-28 podczas analizy zagrożeń spójności danych.  
**Status:** `resolved`  
**Opis:** Relacja `parent_object` pozwala na stworzenie cyklu. Prowadzi to do nieskończonej pętli przy rekurencyjnym odpytywaniu grafu obiektów.  
**Rozwiązanie / workaround:** Wzorzec **"Płaskiej Gwiazdy" (Flat Star Hierarchy)**. Nadpisano `clean()` w `TouristObject` z trzema regułami: obiekt nie może być własnym rodzicem; obiekt mający dzieci nie może otrzymać rodzica; obiekt będący dzieckiem nie może stać się rodzicem (Invariant C-01).

### EC-024 — Keszowanie QuerySetów w formularzach Admina (Puste Dropdowny)
**Obszar:** `apps/badges/admin.py` / `apps/badges/forms.py`  
**Status:** `resolved`  
**Opis:** Definiowanie `ModelChoiceField(queryset=Model.objects.all())` bezpośrednio w ciele klasy formularza powoduje ewaluację zapytania w momencie startu serwera. Nowe rekordy dodane bez restartu nie pojawiają się w liście (Stale Data).  
**Rozwiązanie / workaround:** Dynamiczne QuerySety w formularzach muszą być przypisywane wewnątrz metody `__init__`.

### EC-025 — Surowy kod HTML zamiast widżetu w panelu Admina (Autoescaping)
**Obszar:** `apps/badges/forms.py` (Custom Widgets)  
**Status:** `resolved`  
**Opis:** Nadpisywanie metody `render()` z użyciem konkatenacji stringów zawierających tagi HTML powoduje, że Autoescaping Django zamienia `<` i `>` na encje HTML. Obejście przez `mark_safe()` jest niebezpieczne (XSS) i łamie reguły Bandit.  
**Rozwiązanie / workaround:** Zastosowano `django.utils.html.format_html` oraz `format_html_join`.

### EC-026 — Walidacja obiektów wprowadzanych całkowicie ręcznie (bez OSM i PTTK Code)
**Obszar:** `apps/badges/forms.py` (`TouristObjectAdminForm`)  
**Status:** `resolved`  
**Opis:** Obiekty wprowadzane "z palca" muszą mieć zdefiniowaną nazwę i geometrię. System obsługuje też obiekty z kodem PTTK ale bez OSM.  
**Rozwiązanie / workaround:** Logika miękkiej walidacji: formularz twardo blokuje (`add_error`) brak nazwy i geometrii gdy brak `osm_id`. Jedynie **ostrzega** (`messages.info`), jeśli brak zarówno `osm_id` jak i `code` — by nie blokować dodawania obiektów nieformalnych.

### EC-027 — Brak obsługi widżetów M2M (filter_horizontal) wewnątrz pól JSONB
**Obszar:** `infrastructure/schemas/badge_rules_schema.py`, `django_badge_repo.py`  
**Status:** `resolved`  
**Opis:** Biblioteka `django-jsonform` nie pozwala na osadzanie natywnych widżetów Django (jak `filter_horizontal`) wewnątrz pól JSONB. Administrator musiałby wpisywać ID szczytów ręcznie.  
**Rozwiązanie / workaround:** Zamiast typu `array`, użyto typu `string` w schemacie JSON. Akcja pomocnicza `show_ids_for_json` w `TouristObjectAdmin` generuje gotowy string do skopiowania (np. `"45, 12, 105"`). Adapter `django_badge_repo.py` parsuje string na `frozenset[int]`. *Zabrania się refaktoryzacji tego parsowania — niszczy opisany workflow.*

### EC-028 — Błąd "got multiple values for keyword argument 'readonly_fields'"
**Obszar:** `apps/badges/admin.py`  
**Status:** `resolved`  
**Opis:** Przypisanie klucza `"readonly_fields"` wewnątrz definicji sekcji w krotce `fieldsets` powoduje `TypeError` przy renderowaniu widoku.  
**Rozwiązanie / workaround:** Zmienna `readonly_fields` musi być definiowana wyłącznie jako atrybut na poziomie klasy `ModelAdmin`. Te same pola umieszcza się normalnie w liście `"fields"` wewnątrz `fieldsets`.

### EC-029 — Konflikt typowania Mypy przy generowaniu HTML w Adminie (SafeString)
**Obszar:** `apps/badges/admin.py` (Dekoratory `@admin.display`)  
**Status:** `resolved`  
**Opis:** Funkcje renderujące HTML przez `format_html` oznaczone jako `-> str` powodują błąd `mypy` `[no-any-return]` ponieważ `format_html` zwraca `SafeString` (traktowany jako `Any`).  
**Rozwiązanie / workaround:** Zabrania się rzutowania na `str(format_html(...))` — niszczy to flagę bezpieczeństwa XSS. Należy użyć `# type: ignore[no-any-return]`.

### EC-043 — Konflikty renderowania `django-unfold` (Leaflet, JSONForm i obce aplikacje)
**Obszar:** `apps/badges/admin.py`, `apps/badges/forms.py`  
**Status:** `resolved`  
**Opis:** Wdrożenie `django-unfold` (Tailwind CSS) powoduje globalny CSS Reset, który ogołaca ze stylów domyślne widżety Django. Skutkuje to znikaniem map w `django-leaflet`, zepsuciem widżetów `<datalist>`, `django-jsonform` oraz znikaniem przycisków "Dodaj" w zewnętrznych aplikacjach (np. `django-celery-beat`).  
**Rozwiązanie / workaround:** (1) Mapy: `LeafletGeoAdminMixin` dziedziczone przed `ModelAdmin`. (2) JSONForm: nadpisanie `formfield_for_dbfield`. (3) Własne widżety: dziedziczenie z `UnfoldAdminTextInputWidget`. (4) Obce aplikacje: jawne `admin.site.unregister()` + ponowna rejestracja z klasami `unfold.admin`. *Zabrania się agentom LLM usuwania tych obejść podczas refaktoryzacji panelu.*

### EC-044 — Omijanie metody `clean()` przez Akcje Django Admina
**Obszar:** `apps/badges/models.py` (`TouristObject`)  
**Status:** `resolved`  
**Opis:** Wbudowane Akcje Django Admina uderzają bezpośrednio do bazy przez `.save()` lub `.update()`, całkowicie omijając `clean()`. Umożliwiało to stworzenie nielegalnego cyklu A→B→A w relacjach klastrów.  
**Rozwiązanie / workaround:** Wymuszenie walidacji przez nadpisanie metody `save()` w modelu, która zawsze wywołuje `self.clean()`. Błędy rzucają bezpiecznym błędem 500 zamiast cicho korumpować bazę.

### EC-053 — Przepełnienie pamięci przez filtry M2M / FK w Django Adminie
**Obszar:** `apps/badges/admin.py`  
**Status:** `resolved`  
**Opis:** Użycie `list_filter = ("pool_peaks",)` dla relacji do dużej tabeli (ponad 10 000 obiektów) generuje gigantyczną listę w panelu bocznym, zawieszając przeglądarkę Administratora.  
**Rozwiązanie / workaround:** Twardy zakaz domyślnych filtrów dla dużych relacji. Wdrożono `SimpleListFilter` (`PeakInBadgeFilter`) ze zoptymalizowanym zapytaniem `lookups` pobierającym wyłącznie obiekty aktualnie w użyciu.

---

## 4. Weryfikacja i Postęp Turysty (Faza C)

### EC-030 — Wielokrotność zdobywania odznak i Zużycie Wejść (Repeatability & Ascent Consumption)
**Obszar:** `domain/rules/`, `application/use_cases/verify_badge.py`  
**Odkryty:** 2026-05-25 w trakcie analizy regulaminu "Diademu Polskich Gór".  
**Status:** `open` — Decyzja biznesowa i implementacyjna odroczona do Fazy C.  
**Opis:** Odznaka jest często zdobywana wielokrotnie (Pętle Prestiżu). Silnik oceny operuje na zbiorach matematycznych (`set`), które "połykają" duplikaty. Jeśli system bada wszystkie wejścia w życiu turysty, zignoruje fakt, że turysta chce zdobyć odznakę drugi raz na nowych wejściach.  
**Rozwiązanie / workaround:** Zbiór wejść przekazywanych do Use Case'a weryfikacji jest filtrowany przez `UserContext`. Wejścia "zużyte" do zamknięcia Cyklu nr 1 nie mogą zostać przekazane do weryfikacji w Cyklu nr 2. Model progresu rozszerzony o pojęcie Edycji/Cyklu (`cycle_number`, `cutoff_date`).  
**Test:** `[brakuje, TODO — test_EC030_completed_cycle_ascents_are_excluded_from_new_cycle]`

### EC-031 — Próg wejść (required_count) zaszyty w Wersji zamiast w Stopniu
**Obszar:** `infrastructure/adapters/persistence/django_badge_repo.py` (`_hydrate_version`)  
**Status:** `open` (Dług Technologiczny TD-03)  
**Opis:** Adapter przypisuje `required_count=len(pool_peaks)`. Jest to poprawne wyłącznie dla odznak jednostopniowych gdzie należy zdobyć 100% szczytów z puli. Dla odznak "Zdobądź 20 z 50" lub wielostopniowych, to `BadgeTier` przechowuje rzeczywisty próg.  
**Rozwiązanie / workaround:** Do czasu przebudowy weryfikacja poprawnie policzy `valid_ascents_count`, ale pole `verified` fałszywie zwróci `False`. Konieczna refaktoryzacja.

### EC-032 — Testy `RequestFactory` omijają Django Middleware
**Obszar:** `apps/api/views.py`, `tests/apps/api/`  
**Status:** `resolved`  
**Opis:** `RequestFactory` generuje żądanie trafiające bezpośrednio do kontrolera, całkowicie omijając stos Middleware (w tym `RFC7807ErrorMiddleware`). Wyjątek rzucony przez widok wylatuje na zewnątrz zamiast być sformatowany w JSON.  
**Rozwiązanie / workaround:** Widoki API łapią błędy z rodziny `ApplicationException` bezpośrednio przez lokalny helper `_handle_application_exception`. Globalny Middleware pozostaje jako siatka bezpieczeństwa ostatniej szansy dla błędów 500 oraz wstrzykiwacz `request_id`.

### EC-033 — MagicMock i TypeError przy `JsonResponse`
**Obszar:** `tests/apps/api/`  
**Status:** `resolved`  
**Opis:** Zmockowany Use Case bez jawnie ustawionego `return_value` zwraca kolejny `MagicMock`. Przekazanie go do `JsonResponse` kończy się `TypeError: Object of type MagicMock is not JSON serializable`.  
**Rozwiązanie / workaround:** Obowiązkowe, rygorystyczne definiowanie `.return_value = <typ_prosty>` dla każdego zmockowanego serwisu przed wywołaniem żądania testowego.

### EC-034 — Kafelki MVT, Raw SQL i pułapka wstrzyknięcia (Bandit S608)
**Obszar:** `infrastructure/adapters/persistence/django_mvt_repo.py`  
**Status:** `resolved`  
**Opis:** GeoDjango nie wspiera natywnie `ST_AsMVTGeom` i `ST_TileEnvelope`. Konieczne było użycie surowego SQL z f-stringiem (`f"FROM {table_name}"`), co wywołuje błąd Bandit S608 (Possible SQL Injection).  
**Rozwiązanie / workaround:** Twarda biała lista dozwolonych nazw tabel w Use Case (`LAYER_TO_TABLE_MAP` mapowana przez `Model._meta.db_table`). Do adaptera trafia wyłącznie zwalidowany statyczny string. Linia oznaczona `# noqa: S608`.

### EC-045 — Problem N+1 przy weryfikacji PrerequisiteBadgeRule
**Obszar:** `application/use_cases/verify_badge.py`  
**Status:** `resolved`  
**Opis:** Reguła wymagająca posiadania innej ukończonej odznaki wymuszała pobranie wszystkich postępów turysty do RAM i filtrowanie w Pythonie — problem N+1 przy rosnącej historii użytkownika.  
**Rozwiązanie / workaround:** Dodanie zoptymalizowanej metody `get_completed_badge_codes()` w Porcie, wykonującej jedno płaskie zapytanie SQL (`SELECT ... WHERE domain_status='COMPLETED'`).

### EC-068 — "Cinderella Bug" (Znikające punkty po północy przy Prawach Nabytych)
**Obszar:** `infrastructure/adapters/persistence/django_badge_repo.py`, `PoiScoringService`  
**Status:** `resolved`  
**Opis:** Algorytm punktacji `100/n` używał symulacji Praw Nabytych odpytując bazę o wersję regulaminu ważną na "dzisiaj". Po minięciu północy system przestał punktować cele, bo stara wersja odznaki (zamknięta 3 lata temu) spełniała warunek `valid_from <= today` i była błędnie zwracana jako aktywna.  
**Rozwiązanie / workaround:** Każde historyczne zapytanie o Wersję Odznaki implementuje pełne zamknięcie wektora czasowego: `Q(valid_from__lte=target_date)` ORAZ `(Q(valid_to__isnull=True) | Q(valid_to__gte=target_date))`. Dla rysowania mapy wprowadzono osobną metodę `get_latest_badge_version()`.

---

## 5. Frontend i Interfejs Użytkownika (UI/UX)

### EC-035 — Niezgodność typów w Cache (Szare Pinezki na Mapie)
**Obszar:** `application/use_cases/explore_map.py`, `PoiScoringService`  
**Status:** `resolved`  
**Opis:** Klucze ID wyciągnięte z Redis/Pickle były serializowane do `str`, podczas gdy baza operuje na `int`. Skutkowało to brakiem kolorowania szczytów na mapie (wszystkie szare).  
**Rozwiązanie / workaround:** Wdrożenie *Double Lookup* z rzutowaniem w locie: `colors.get(obj.id, colors.get(str(obj.id), "GRAY"))`. Obsługuje oba przypadki: int (natywny cache Django) i str (serializacja JSON przez Redis).

### EC-036 — Brak wsparcia Data-Driven Styling dla `line-dasharray`
**Obszar:** `apps/static/js/map.js` (MapLibre)  
**Status:** `resolved`  
**Opis:** WebGL w MapLibre "po cichu" nie rysował granic MVT z powodu próby dynamicznej zmiany stylu linii z przerywanej na ciągłą za pomocą wyrażeń data-driven. WebGL nie obsługuje tej właściwości dynamicznie.  
**Rozwiązanie / workaround:** Rozwiązano rozbijając na dwie oddzielne, statyczne warstwy: `regions-line-neighbors` (przerywana) i `regions-line-active` (ciągła), przełączane filtrem `['==', ['get', 'id'], activeId]`.

### EC-037 — Błąd 500 przy relacji ForeignKey (Brakujący Profil)
**Obszar:** `apps/tourists/views.py`  
**Status:** `resolved`  
**Opis:** Użytkownicy zarejestrowani przed wprowadzeniem "Konta Rodzinnego" nie posiadali wygenerowanego `TouristProfile`, co kończyło się błędem `RelatedObjectDoesNotExist` przy każdym renderowaniu dashboardu.  
**Rozwiązanie / workaround:** Wprowadzono *Lazy Initialization* — tworzenie `TouristProfile` w locie przy pierwszym odczycie (`get_or_create` w sygnale `post_save` na modelu `User`).

### EC-046 — Konflikt typowania `HttpRequest` i dekoratorów w widokach API
**Obszar:** `apps/api/views.py`  
**Status:** `resolved`  
**Opis:** Użycie listy dekoratorów `[csrf_exempt, require_auth]` nad klasą CBV oraz jawne typowanie `request: HttpRequest` bez odpowiednich importów wywoływało seryjne błędy lintera (F821). Zewnętrzne dekoratory autoryzacji psuły format błędów RFC 7807 (zwracając standardowe 403 z HTML).  
**Rozwiązanie / workaround:** Zrezygnowano z dekoratorów autoryzacyjnych na rzecz asercji wewnątrz ciała widoku: `auth_error = _require_auth(request)`. Nałożono wyłącznie `@method_decorator(csrf_exempt, name="dispatch")`.

### EC-047 — Błąd typowania Mypy przy `get_or_create` (Zwracane `Any`)
**Obszar:** `infrastructure/adapters/persistence/` (w tym `django_news_repo.py`)  
**Status:** `resolved`  
**Opis:** Metoda `get_or_create` zwraca krotkę `(obj, created)`. Wtyczka `django-stubs` dla `mypy` nie zawsze poprawnie wnioskuje typ flagi `created`, traktując ją jako `Any`. Przy twardym zwrocie `bool` mypy `--strict` zgłasza błąd.  
**Rozwiązanie / workaround:** Zawsze wymuszaj jawne rzutowanie: `return bool(created)`.

### EC-048 — Defensywne typowanie w BeautifulSoup (Atrybuty mogą być listami)
**Obszar:** `infrastructure/adapters/news_scraper.py`  
**Status:** `resolved`  
**Opis:** Wyciąganie atrybutów z tagu przez `link_tag.get('href')` zwraca unijny typ. Atrybuty HTML (szczególnie `class`) mogą być listami, co powoduje błąd `mypy` przy bezpośredniej konkatenacji z `str`.  
**Rozwiązanie / workaround:** Każdy atrybut z BS4 musi być "rozpakowany": `if isinstance(attr, list): val = str(attr[0]) elif isinstance(attr, str): val = attr else: val = ""`.

### EC-049 — Niezamierzona konwersja `dict` na `tuple` w plikach konfiguracyjnych
**Obszar:** `config/settings.py`  
**Status:** `resolved`  
**Opis:** Pozostawienie przecinka po klamrze zamykającej słownik (`},`) powoduje, że Python cicho rzutuje strukturę na jednoelementową krotkę. Prowadzi to do `AttributeError: 'tuple' object has no attribute 'get'` w głębokich warstwach zewnętrznych bibliotek (np. `allauth`).  
**Rozwiązanie / workaround:** Rygorystyczne przestrzeganie czystości składni na końcu definicji zmiennych globalnych w `.py`. Egzekwowane przez linter `ruff`.

### EC-050 — Zdeprecjonowana konfiguracja `django-allauth` (Żółte ostrzeżenia przy starcie)
**Obszar:** `config/settings.py`, logowanie OAuth  
**Status:** `resolved`  
**Opis:** Użycie nowoczesnej wersji `django-allauth` (`>=65.0.0`) ze starymi flagami konfiguracyjnymi (np. `ACCOUNT_EMAIL_REQUIRED = True`) generuje ostrzeżenia deprecjacji przy uruchamianiu serwera.  
**Rozwiązanie / workaround:** Przejście na nowy standard deklaratywny: `ACCOUNT_LOGIN_METHODS = {'email'}` oraz `ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']`.

### EC-051 — `UnboundLocalError` przy leniwych importach w blokach try/except
**Obszar:** `infrastructure/adapters/osm_adapter.py`  
**Status:** `resolved`  
**Opis:** Leniwy import (`import json` wewnątrz `try`) w połączeniu z obsługą wyjątku z tego modułu (`except json.JSONDecodeError:`) powoduje `UnboundLocalError` gdy wyjątek sieciowy rzucony zostanie przed wykonaniem importu.  
**Rozwiązanie / workaround:** Twardy zakaz lokalnych importów wewnątrz funkcji dla modułów uczestniczących w logice `try/except`. Wszystkie takie zależności muszą być zadeklarowane na poziomie modułu (góra pliku).

### EC-052 — Niewidzialne zmienne środowiskowe w czystych skryptach Pythona
**Obszar:** `scripts/check_secrets.py`  
**Status:** `resolved`  
**Opis:** Skrypt diagnostyczny uruchamiany przez `python script.py` nie parsuje pliku `.env`, więc wywołania `os.getenv("KLUCZ")` zwracają `None`. Plik `.env` nie jest automatycznie eksportowany do powłoki bez narzędzi takich jak `python-dotenv`.  
**Rozwiązanie / workaround:** Skrypt `check_secrets.py` przepisany by ręcznie parsować `.env.example` oraz `.env` przez wbudowane `open()`, uniezależniając środowisko testowe CI od powłoki systemu operacyjnego.

### EC-054 — Niedziałające przyciski HTMX wewnątrz dynamicznych dymków mapy (Popups)
**Obszar:** `apps/static/js/map.js` (Integracja MapLibre z HTMX)  
**Status:** `resolved`  
**Opis:** HTMX buduje nasłuchiwacze zdarzeń tylko podczas ładowania dokumentu. Dynamicznie wstrzyknięty węzeł DOM (np. popup MapLibre) jest dla niej "niewidzialny" — atrybuty `hx-post`, `hx-vals` nie działają.  
**Rozwiązanie / workaround:** Po każdym dodaniu dynamicznego elementu do DOM należy wymusić skanowanie: `htmx.process(popup.getElement())`. Dopiero wtedy HTMX podpina obsługę zdarzeń pod nowe przyciski.

### EC-055 — "Problem Dwóch Mózgów" (Rozjazd pamięci podręcznej Celery i Django)
**Obszar:** `config/settings.py`, `PoiScoringService`, Redis  
**Status:** `resolved`  
**Opis:** Brak jawnej deklaracji `CACHES` w `settings.py` powoduje, że Django i Celery używają `LocMemCache` (lokalnej RAM procesu). Worker Celery zapisywał wynik do swojej pamięci RAM, a serwer Web odpytywał swoją pustą pamięć — szczyty pozostawały szare.  
**Rozwiązanie / workaround:** Wymuszono podpięcie współdzielonego Redis: `CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", ...}}`. Ostrzeżenie: po zmianie logiki punktacji zawsze restartuj Worker Celery.

### EC-056 — Dzielenie całkowite w Pythonie a błędna wycena `100/n`
**Obszar:** `application/services/poi_scoring_service.py`  
**Status:** `resolved`  
**Opis:** Operator `//` wymuszał zaokrąglanie w dół przed konwersją do float (np. `100 // 80 = 1`, `100 // 120 = 0`). Waga była też wyliczana globalnie przed symulacją wejścia, fałszując "zysk" ze szczytu.  
**Rozwiązanie / workaround:** Zmieniono na klasyczne dzielenie zmiennoprzecinkowe `round(100.0 / missing_after_ascent)`. Obliczenia wagi wstawiono wewnątrz pętli po przeprowadzeniu symulacji wejścia.

### EC-060 — Pokusa łamania granic API przez używanie helperów widoków (Coupling)
**Obszar:** `apps/api/views.py` vs `apps/tourists/views.py`  
**Status:** `resolved`  
**Opis:** Podczas refaktoryzacji próbowano zaimportować funkcję pomocniczą `_get_active_profile_id` z modułu renderującego szablony HTML (`tourists/views.py`) do widoków REST API. Spowodowało to błąd lintera (F821) — krzyżowe importy między aplikacjami łamią zasadę niezależności API od warstwy prezentacyjnej.  
**Rozwiązanie / workaround:** Zablokowano współdzielenie helperów między API a widokami HTML. Widoki API odczytują sesję natywnie: `request.session.get("active_profile_id") or request.user.profiles.first().id`.

### EC-061 — Przeglądarka ignoruje zmiany logiki MVT (Agresywny Browser Cache)
**Obszar:** `apps/static/js/map.js` (MapLibre), `VectorTileView`  
**Status:** `resolved`  
**Opis:** Modyfikacje backendowej logiki SQL (np. dodanie kolumny `db_id_str`) są niewidoczne w aplikacji klienckiej nawet po twardym odświeżeniu. Przeglądarki agresywnie buforują pliki `.pbf` na dysku lokalnym.  
**Rozwiązanie / workaround:** Wzorzec *Cache Busting*: przy zmianie logiki kafelków MVT programista dodaje unikalny parametr wersji w `map.js` (np. `/api/v1/tiles/...pbf?v=4`). Zmusza to każdą przeglądarkę do porzucenia lokalnych kopii.

### EC-063 — Niewidoczny globalny stan (Window) po optymalizacji renderowania HTML
**Obszar:** `apps/templates/base.html`, `map.js`  
**Status:** `resolved`  
**Opis:** Przeniesienie tagów `<script>` na koniec `</body>` spowodowało błąd `ReferenceError` — skrypty mapy próbowały użyć zmiennych wstrzykiwanych z Context Processora, które wyrenderowały się za późno.  
**Rozwiązanie / workaround:** Twarda reguła szablonów: ciężkie biblioteki `.js` mogą rezydować na końcu dokumentu, ale **wstrzykiwanie bezpiecznego kontekstu biznesowego z serwera** (`<script> window.XYZ = {{ ... }}; </script>`) musi bezwzględnie znajdować się w sekcji `<head>`.

### EC-067 — Omyłkowe wywoływanie `request.profile` zamiast z sesji (Model Rodzinny)
**Obszar:** `apps/api/views.py` (i inne widoki żądań)  
**Status:** `resolved`  
**Opis:** Po wdrożeniu Modelu Rodzinnego (jeden `request.user` z wieloma `TouristProfile`), odwołanie do nieistniejącego `request.profile.id` kończy się `AttributeError: 'WSGIRequest' object has no attribute 'profile'`.  
**Rozwiązanie / workaround:** Twardy nakaz korzystania z sesji HTTP: `profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id`.

### EC-069 — Fałszywa Pustka Mapy (False Emptiness) u nowych użytkowników
**Obszar:** `apps/static/js/map.js`, `PoiScoringService`  
**Status:** `resolved`  
**Opis:** Nowy turysta bez zasubskrybowanych odznak widział całkowicie pustą mapę bez obiektów. Warstwa pinezek była schowana na domyślnym poziomie przybliżenia (Zoom 5), a warstwa Heatmapy wyświetlała obiekty wyłącznie o wartości potencjału `> 0`.  
**Rozwiązanie / workaround:** Utrzymanie stałej, delikatnej warstwy "Drogi Mlecznej" (małe kropki z przezroczystością `0.4` dla zoomu 5-9) bez względu na potencjał punktowy. Zapewnia turyście orientację topograficzną przed wyborem odznaki.

---

## 6. Bezpieczeństwo i Integracja OAuth

### EC-064 — "Nagi HTML" przy przekierowaniu dla niezalogowanych
**Obszar:** `apps/templates/account/login.html`  
**Status:** `resolved`  
**Opis:** Niezalogowany użytkownik przekierowany przez `@login_required` widzi wbudowany szablon `django-allauth` — całkowicie pozbawiony stylów CSS, co dramatycznie psuje UX aplikacji opartej na Tailwind CSS.  
**Rozwiązanie / workaround:** Jawne nadpisywanie wbudowanych szablonów biblioteki. Utworzono `apps/templates/account/login.html` dziedziczący po `base.html` z stylizowanym ekranem logowania.

### EC-065 — Metoda GET dla linków logowania OAuth zablokowana (CSRF)
**Obszar:** `apps/templates/base.html`, Przyciski Logowania  
**Status:** `resolved`  
**Opis:** Nowoczesne wersje `django-allauth` zabraniają inicjowania OAuth przez zwykły link `<a>`. Próba użycia linku skutkuje ekranem z ostrzeżeniem lub błędem metody HTTP.  
**Rozwiązanie / workaround:** Każdy przycisk "Zaloguj" wywołujący zewnętrznego dostawcę tożsamości musi być `<button type="submit">` wewnątrz `<form method="post">` z `{% csrf_token %}`.

### EC-066 — Odrzucenie połączenia (Error 401 invalid_client) przy logowaniu Google
**Obszar:** `config/settings.py` (Zmienne środowiskowe z `.env`)  
**Status:** `resolved`  
**Opis:** Po kliknięciu przycisku logowania przeglądarka jest odrzucana przez Google z błędem 401 (OAuth client was not found).  
**Rozwiązanie / workaround:** Należy upewnić się, że `GOOGLE_OAUTH_CLIENT_ID` z `.env` jest dokładną kopią klucza z Google Cloud Console, a "Authorized redirect URI" w 100% odpowiada adresowi aplikacji (np. `http://127.0.0.1:8005/accounts/google/login/callback/`).

---

## 7. Repozytorium i CI/CD (Operacje)

### EC-041 — Pułapka domyślnych szablonów `.gitignore` (Utrata plików kontraktowych)
**Obszar:** `.gitignore`, CI/CD Pipeline  
**Odkryty:** Podczas pierwszego commitu inicjalizującego repozytorium.  
**Status:** `resolved`  
**Opis:** Popularne szablony `.gitignore` dla Pythona domyślnie wykluczają pliki takie jak `.python-version`, `.dockerignore`, a generatory mogą zignorować lockfile'y (`uv.lock`). Dodanie takiego szablonu powoduje niewypchnięcie tych plików na serwer, co natychmiast łamie pipeline CI/CD.  
**Rozwiązanie / workaround:** Twardy nakaz commitowania plików kontrolnych: `.dockerignore`, `.python-version`, `uv.lock` oraz katalog `.github/` **zawsze** muszą być śledzone przez Git.

### EC-042 — "Leniwe" omijanie linterów przez agentów LLM (C408, E501)
**Obszar:** Agenci LLM, Linter `ruff` (Pipeline CI)  
**Status:** `resolved`  
**Opis:** Modele generujące kod mają tendencję do "uciszania" ostrzeżeń lintera przez komentarze `# noqa: C408` zamiast naprawy samej logiki. Maskuje to dług techniczny w projekcie.  
**Rozwiązanie / workaround:** Twardy zakaz dla agentów: komentarze `noqa` są dopuszczalne wyłącznie dla grupy `S` (Security, jak celowe `mark_safe`) z udokumentowanym uzasadnieniem. Jakikolwiek kod uciszający linter strukturalny z powodu wygody modelu musi zostać odrzucony podczas Code Review.

### EC-070 — Błąd składni Pythona 2 przy łapaniu wielu wyjątków
**Obszar:** `apps/api/views.py`  
**Status:** `resolved`  
**Opis:** Podczas refaktoryzacji agenci LLM generują przestarzały kod: `except json.JSONDecodeError, ValueError:`. W Pythonie 3 powoduje to natychmiastowy `SyntaxError` — serwer w ogóle nie wystartuje.  
**Rozwiązanie / workaround:** Prawidłowa składnia: `except (json.JSONDecodeError, ValueError):`. Egzekwowane przez linter Ruff.