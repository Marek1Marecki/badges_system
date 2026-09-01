# Edge Cases — przypadki brzegowe

> **Wersja:** 1.2  
> **Data:** 2026-05-30  
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
**Opis:** Przy masowym pobieraniu (Bulk Fetching) oraz pojedynczym odpytywaniu niektórych niemieckich klastrów Overpass API (`overpass-api.de`, `lz4...`), serwery bezwzględnie odrzucają połączenie zwracając błąd `406 Not Acceptable`. Jest to działanie zaporowe (WAF / Load Balancer) chroniące darmową infrastrukturę przed skryptami używającymi metody POST bez odpowiednich nagłówków lub próbującymi wymusić ścisłą negocjację treści (Content Negotiation).  
**Rozwiązanie / workaround:** 
- Zamiast metody `POST`, wszystkie zapytania Overpass QL są przesyłane metodą `GET` bezpośrednio w parametrach adresu URL (`urllib.parse.urlencode({"data": query})`).
- Zabrania się używania nagłówka `Accept: application/json` w zapytaniach do Overpass API. Kod musi w pełni ufać, że to, co odbierze, będzie można sparsować na JSON, nie wymuszając tego nagłówkiem HTTP.
- Problem rozwiązany strukturalnie przez Linear Backoff Retry na maszynie asynchronicznej (maksymalnie 15 prób, zgodnie z definicją w Tasku).
**Test:** `test_successful_fetch_uses_get_method` (zaimplementowane przez `httpx`/`urllib` mocking).

### EC-002 — Nieskończona pętla Nocnego Stróża i martwe węzły (Ghost Nodes)
**Obszar:** `application/use_cases/fetch_osm_data.py` (`RunOsmNightWatchmanUseCase`)  
**Odkryty:** 2026-05-22 przy testowaniu harmonogramów Celery.  
**Status:** `resolved`  
**Opis:** Obiekt w OSM, który nie był edytowany przez społeczność np. od 10 lat, ma wciąż stary `timestamp`. Jeśli system aktualizuje bazę tylko w momencie wykrycia "nowej daty w OSM", obiekty te nigdy nie schodzą z kolejki "do sprawdzenia" i Nocny Stróż utyka w nieskończonej pętli zapytań o te same 100 szczytów każdej nocy.  
**Rozwiązanie / workaround:** Kolumna `last_sync_check` (Data ostatniego sprawdzenia). Niezależnie od tego, czy tagi w OSM uległy zmianie czy nie, po każdym zapytaniu system nadpisuje czas lokalnego rekordu, spychając go na sam koniec kolejki. Dodatkowo, jeśli z paczki 100 węzłów powróci tylko 99, ten jeden zaginiony zostaje autorytatywnie zgłoszony do `OsmSyncConflict` jako obiekt prawdopodobnie zniszczony/usunięty z map świata.  
**Test:** `test_watchman_ghost_node_detection_and_queue_rotation`

### EC-003 — Blokowanie kafelków mapy w panelu Admina (Tile Usage Policy)
**Obszar:** `config/settings.py`, `apps/badges/admin.py`  
**Odkryty:** Podczas konfiguracji widżetu `django-leaflet`.  
**Status:** `resolved`  
**Opis:** Serwery kafelków (Tile Servers) OpenStreetMap rygorystycznie egzekwują zasady użycia i blokują żądania z przeglądarek, które nie wysyłają nagłówka `Referer`. Domyślna polityka bezpieczeństwa Django (`same-origin`) ukrywa ten nagłówek przy odpytywaniu zewnętrznych domen, co skutkuje brakiem podkładu mapowego w panelu Administratora (wyświetla się grafika "Access blocked").  
**Rozwiązanie / workaround:** Do globalnej konfiguracji projektu `config/settings.py` dodano wymuszenie luźniejszej polityki: `SECURE_REFERRER_POLICY = "origin-when-cross-origin"`. Zezwala to przeglądarce na wysłanie pochodzenia do serwerów kafelkowych, odblokowując mapę bez łamania globalnego bezpieczeństwa aplikacji.

---

## 2. Geometria i Przetwarzanie Przestrzenne (PostGIS)

### EC-010 — Rzutowanie przy ST_DWithin (Metry vs Stopnie)
**Obszar:** `infrastructure/adapters/persistence/region_cache_repo.py`  
**Odkryty:** 2026-05-18 podczas analizy wydajności zapytań przestrzennych.  
**Status:** `resolved`  
**Opis:** Funkcja `ST_DWithin` w PostGIS przyjmowana na domyślnej geometrii sferycznej (`EPSG:4326`) operuje w stopniach (degrees), co daje niedokładne wyniki, zamieniając bufor kołowy w elipsę w naszej szerokości geograficznej. Z kolei obliczenia na natywnym typie `geography` są wyjątkowo zasobożerne dla procesora.  
**Rozwiązanie / workaround:** Zjawisko to obsługuje ORM GeoDjango. Obiekty są przechowywane jako WGS84 (`Point/MultiPolygon`, 4326), jednak do filtra przekazywany jest obiekt `D(m=50)`. Wyliczenie odległości na froncie dla panelu admina (do wyświetlenia np. "12 metrów do granicy") wykorzystuje rzutowanie w locie na układ metryczny Web Mercator: `.transform(3857, clone=True)`.  
**Test:** `[brakuje, TODO - weryfikacja rzutowania 3857 w testach integracyjnych PostGIS]`

### EC-011 — Ciche zatajanie błędu geometrii (Silent Fail w GEOS)
**Obszar:** `build_tourist_region_geometry.py` oraz `region_cache_repo.py`  
**Odkryty:** 2026-05-26 podczas weryfikacji jakości kodu (Review ADR-002).  
**Status:** `resolved`  
**Opis:** W procesie łączenia dziesiątek mezoregionów w jeden Region Turystyczny (za pomocą biblioteki GEOS - `unary_union`), początkowo użyto `except Exception: exact_dist = 0.0` lub `return None`, by zapobiec przerwaniu pracy Celery. To powodowało ciche maskowanie faktu, że baza danych może zawierać uszkodzone lub samoprzecinające się (self-intersecting) poligony, których nie da się w żaden sposób wykorzystać w aplikacji klienckiej (np. kafelkach MVT).  
**Rozwiązanie / workaround:** Zero tolerancji dla cichych błędów przy geometrii (Fail-Fast). Usunięto maskujące bloki `except`. Wyjątki infrastrukturalne mają prawo "wybuchnąć" w adapterze i zostają zaprotokołowane jako `ERROR` w głównym pliku `tasks.py`.  
**Test:** `test_geometry_union_fails_fast_on_invalid_polygon`

### EC-058 — Problem N+1 przy weryfikacji Bitemporalności (Bulk Operations)
**Obszar:** `application/use_cases/bulk_log_ascents.py`, `AscentLogRepositoryPort`  
**Status:** `resolved`  
**Opis:** Podczas przetwarzania paczki np. 30 szczytów zdekodowanych z pliku GPX, odpytywanie bazy danych o ramy bitemporalne (`existence_start`, `existence_end`) wewnątrz pętli `for` generowało by 30 osobnych transakcji (zjawisko N+1), co jest śmiertelne dla wydajności operacji masowych.
**Rozwiązanie / workaround:** Zdefiniowano nową sygnaturę portu `get_objects_lifespans(peak_ids: set[int])`, która wykorzystuje `values_list` z klauzulą `IN`. Baza odpowiada jednym błyskawicznym zapytaniem zwracającym słownik. Wewnątrz pętli iterującej po logach wejść, Python odpytuje już tylko ten pre-kalkulowany, lokalny słownik w pamięci RAM.

### EC-059 — Optymalizacja wydajności wyszukiwania wzdłuż Śladu GPX
**Obszar:** `infrastructure/adapters/gpx_parser.py`, `django_map_repo.py`  
**Status:** `resolved`  
**Opis:** Wgranie śladu GPX np. z całodniowego przejścia szlaku generuje geometrię składającą się z kilkudziesięciu tysięcy wierzchołków. Uderzenie z taką figurą bezpośrednio do PostGIS z funkcją odległości (nawet opartą na `ST_DWithin`) mogłoby zawiesić serwer. Dodatkowo Czysta Domena nie może parsować obiektów typu `GEOSGeometry` (zgodnie z ADR-002).
**Rozwiązanie / workaround:** Wprowadzono architekturę wieloetapową. Parser GPX przed przekazaniem linii do warstwy aplikacji dokonuje agresywnego uproszczenia (Line Simplification, `simplify(0.0001)`), redukując liczbę wierzchołków. Zoptymalizowana linia przesyłana jest jako czysty tekst `WKT` (Well-Known Text). Dopiero po stronie adaptera `django_map_repo` WKT jest odtwarzane i przetwarzane szybkim filtrem `distance_lte` z indeksami GiST.

### EC-062 — Relacje M2M zignorowane przez modele `managed = False`
**Obszar:** `apps/badges/models.py`, `migrations/`  
**Status:** `resolved`  
**Opis:** Dodanie relacji `ManyToManyField` (np. pola `neighbors`) do modeli oznaczonych jako `managed = False` (lub dziedziczących z takich modeli) skutkuje tym, że mechanizm `makemigrations` w Django **całkowicie ignoruje** konieczność utworzenia tabel pośrednich w bazie danych. Ręczne usunięcie flagi `managed = False` wymusza na Django próbę utworzenia od nowa całych, głównych tabel, co kończy się błędem `Relation already exists`.
**Rozwiązanie / workaround:** Twardy zakaz manipulowania flagą `managed` w celu wymuszenia migracji. Aby powołać do życia tabele M2M dla niezarządzanych modeli, należy użyć tzw. **Pustej Migracji (Empty Migration)**. Należy wygenerować pusty plik komendą `makemigrations --empty` i użyć instrukcji `migrations.RunSQL`, wpisując tam ręcznie wygenerowany kod `CREATE TABLE IF NOT EXISTS` z poprawnymi nazwami tabel i kolumn uzyskanymi z `Model._meta.get_field(...)`.

---

## 3. Administracja i Integracja UX (Django Admin)

### EC-020 — Znikający (Niezapisany) Stopień Odznaki (Django Inlines)
**Obszar:** `apps/badges/admin.py` (`BadgeTierInline`)  
**Odkryty:** 2026-05-23 przy definiowaniu historycznej wersji "Korony Gór Polskich".  
**Status:** `resolved`  
**Opis:** Jeśli w klasie `Inline` formularza Django wartości domyślne dla wiersza (np. `Kolejność = 1`, `Stopień = Jednostopniowa`) są natywnie wpisane w model bazy danych, a administrator nie zmieni ani jednego pola w formularzu dodawania, mechanizm `has_changed()` Django ignoruje cały wiersz i go nie zapisuje. Prowadzi to do tworzenia odznak "bez stopni", jeśli te składają się tylko z wartości domyślnych.  
**Reprodukcja:** 
1. Otwórz edycję Wersji Odznaki w Django Admin.
2. W formularzu Inline (Stopnie Odznak) nie zmieniaj żadnej wartości domyślnej.
3. Kliknij "Zapisz".
4. Wejdź ponownie w edycję — stopień nie został zapisany w bazie.  
**Rozwiązanie / workaround:** Zakaz stosowania wartości `default` na poziomie modelu bazy danych dla słowników typu Enum używanych w Inline'ach. Model wymusza puste pole bazowe, przez co na froncie pojawia się znak `---------`. Administrator musi świadomie zmienić to pole na wymaganą wartość (np. "Jednostopniowa"), co aktywuje flagę `has_changed()` i gwarantuje poprawny zapis.  
**Test:** `test_badge_tier_requires_explicit_choice_to_save`

### EC-021 — Konflikt "through" przy MultipleChoice (M2M)
**Obszar:** `apps/badges/admin.py` (`BadgeVersionAdmin`)  
**Odkryty:** 2026-05-21 przy projektowaniu "Wielkiej Korony Sudetów".  
**Status:** `resolved`  
**Opis:** Użycie wygodnego i szybkiego widżetu `filter_horizontal` w panelu Admina wyrzuca błąd aplikacji, jeśli model Django w polu `ManyToManyField` ma zdefiniowaną niestandardową tabelę łączącą poprzez atrybut `through="..."`.  
**Reprodukcja:** 
1. Zdefiniuj `ManyToManyField` z argumentem `through`.
2. Dodaj to pole do `filter_horizontal` w klasie `ModelAdmin`.
3. Wejdź na stronę edycji modelu. Formularz wyrzuca `admin.E013`.  
**Rozwiązanie / workaround:** Zrezygnowano ze śledzenia dodatkowych atrybutów dla puli obiektów odznaki (np. kolejności ich dodania w tabeli łączącej). `BadgeVersionModel.pool_peaks` to prosta, automatyczna relacja pozwalająca na masowe dodawanie. Ewentualna kolejność (wymuszona regulaminem) nie dotyczy puli, lecz jest definiowana w Regułach Biznesowych (JSONB).  
**Test:** `test_pool_peaks_uses_implicit_m2m_table`

### EC-022 — Cykliczne relacje w klastrach (A → B → A)
**Obszar:** `apps/badges/models.py` (`TouristObject`), `ProximityCandidateAdmin`  
**Odkryty:** 2026-05-28 podczas analizy zagrożeń spójności danych.  
**Status:** `resolved`  
**Opis:** Relacja `parent_object` pozwala na stworzenie cyklu (np. Szczyt jest rodzicem Schroniska, a Schronisko zostaje przypięte jako rodzic Szczytu). Prowadzi to do nieskończonej pętli przy rekurencyjnym odpytywaniu grafu obiektów.  
**Rozwiązanie / workaround:** Odrzucono koncepcję nieskończonych drzew na rzecz wzorca **"Płaskiej Gwiazdy" (Flat Star Hierarchy)**. W modelu `TouristObject` nadpisano metodę `clean()`, która wprowadza 3 twarde reguły: obiekt nie może być własnym rodzicem; obiekt mający dzieci nie może otrzymać rodzica; obiekt będący dzieckiem nie może stać się rodzicem dla kogoś innego. Blokuje to powstawanie grafów o głębokości większej niż 1, trwale uniemożliwiając tworzenie pętli (Invariant C-01 zrealizowany).

### EC-024 — Keszowanie QuerySetów w formularzach Admina (Puste Dropdowny)
**Obszar:** `apps/badges/admin.py` / `apps/badges/forms.py`  
**Odkryty:** Przy implementacji akcji masowego przypisywania szczytów do odznak (Action Form).  
**Status:** `resolved`  
**Opis:** Definiowanie pola `ModelChoiceField(queryset=Model.objects.all())` bezpośrednio w ciele klasy formularza powoduje ewaluację zapytania w momencie ładowania modułu (startu serwera Gunicorn/Runserver). Jeśli administrator doda nowy rekord do bazy bez restartowania serwera, nowy rekord nie pojawi się w rozwijanej liście formularza (zjawisko Stale Data).  
**Rozwiązanie / workaround:** Żelazna zasada Django: dynamiczne QuerySety w formularzach muszą być przypisywane wewnątrz metody `__init__`.

### EC-025 — Surowy kod HTML zamiast widżetu w panelu Admina (Autoescaping)
**Obszar:** `apps/badges/forms.py` (Custom Widgets)  
**Odkryty:** Podczas implementacji dynamicznego pola `<datalist>` dla typów obiektów OSM.  
**Status:** `resolved`  
**Opis:** Przy nadpisywaniu metody `render()` niestandardowego widżetu formularza, zwykła konkatenacja ciągów znaków (stringów) zawierających tagi HTML powoduje, że wbudowany w Django mechanizm *Autoescape* zamienia znaki `<` i `>` na encje HTML (`&lt;`). W efekcie na ekranie wyświetla się surowy kod zamiast kontrolki. Obejście tego za pomocą `mark_safe()` jest niebezpieczne (XSS) i łamie reguły lintera (Bandit).  
**Rozwiązanie / workaround:** Zastosowano `django.utils.html.format_html` oraz `format_html_join`. Funkcje te bezpiecznie budują drzewo HTML, automatycznie escapując jedynie zmienne użytkownika, a tagi HTML traktując jako bezpieczne, co natywnie rozwiązuje problem renderowania bez uciszania linterów.

### EC-026 — Walidacja obiektów wprowadzanych całkowicie ręcznie (bez OSM i PTTK Code)
**Obszar:** `apps/badges/forms.py` (`TouristObjectAdminForm`)  
**Odkryty:** Podczas testowania formularza zapisu.  
**Status:** `resolved`  
**Opis:** Obiekty wprowadzane "z palca" (bez zasilania z `osm_id`) muszą posiadać twardo zdefiniowaną przez administratora nazwę i geometrię (punkt na mapie), aby baza danych była spójna. Z drugiej strony, system obsługuje obiekty, które posiadają kod ewidencyjny (pole `code`, np. PTTK-SCH-01), ale nie ma ich w OSM.  
**Rozwiązanie / workaround:** Zaimplementowano logikę miękkiej walidacji. Formularz twardo blokuje (`add_error`) brak nazwy i geometrii, gdy brak `osm_id`. Jednocześnie formularz jedynie **ostrzega** (`messages.info`), jeśli użytkownik nie podał ani `osm_id`, ani `code`. Zabrania się zamieniania tego ostrzeżenia na twardy błąd, gdyż zablokowałoby to dodawanie obiektów nieformalnych (np. "Skałka pod dębem"), które nie posiadają oficjalnej ewidencji.

### EC-027 — Brak obsługi widżetów M2M (filter_horizontal) wewnątrz pól JSONB
**Obszar:** `infrastructure/schemas/badge_rules_schema.py`, `django_badge_repo.py`  
**Odkryty:** Podczas projektowania reguły `MultiPoolRequirementRule` (Zasada Wiaderek).  
**Status:** `resolved`  
**Opis:** Biblioteka `django-jsonform` nie pozwala na osadzanie potężnych, natywnych widżetów Django (takich jak `filter_horizontal`) wewnątrz generowanych przez nią pół formularza JSONB. Sprawia to, że administrator chcący przypisać 50 szczytów do specyficznego "wiaderka" reguły musiałby szukać i wpisywać ich identyfikatory (ID) w tablicę JSON ręcznie, co jest niedopuszczalne z punktu widzenia UX.  
**Rozwiązanie / workaround:** Zrezygnowano z typu `array` w schemacie JSON dla tej reguły na rzecz typu `string`. W panelu `TouristObjectAdmin` wdrożono niestandardową akcję pomocniczą `show_ids_for_json`, która po odfiltrowaniu i zaznaczeniu szczytów przez Admina zwraca zielony alert z wygenerowanym ciągiem znaków (np. `"45, 12, 105"`). Administrator kopiuje ten ciąg (`Ctrl+C`) i wkleja do pola tekstowego w schemacie JSON (`Ctrl+V`). Adapter bazy danych (`django_badge_repo.py`) posiada dedykowaną logikę parsowania tego stringa w locie na zbiór `frozenset[int]`. *Zabrania się refaktoryzacji tego parsowania w celu wymuszenia czystych typów Array w JSONie, gdyż zniszczy to ten przepływ pracy (Workflow).*

### EC-028 — Błąd "got multiple values for keyword argument 'readonly_fields'"
**Obszar:** `apps/badges/admin.py` (Konfiguracja `fieldsets`)  
**Odkryty:** Podczas reorganizacji panelu `TouristObjectAdmin` po wprowadzeniu statusów asynchronicznych.  
**Status:** `resolved`  
**Opis:** Próba przypisania klucza `"readonly_fields"` wewnątrz definicji sekcji w krotce `fieldsets` (np. obok kluczy `"fields"`, `"classes"`) powoduje natychmiastowy błąd `TypeError` przy renderowaniu widoku przez Django.  
**Rozwiązanie / workaround:** Zmienna `readonly_fields` musi być definiowana wyłącznie jako atrybut na poziomie samej klasy dziedziczącej po `ModelAdmin`. Następnie te same nazwy pól należy normalnie umieścić w liście `"fields"` wewnątrz `fieldsets`. Django samo zorientuje się, że ma je wyrenderować jako zablokowane.

### EC-029 — Konflikt typowania Mypy przy generowaniu HTML w Adminie (SafeString)
**Obszar:** `apps/badges/admin.py` (Dekoratory `@admin.display`)  
**Status:** `resolved`  
**Opis:** Funkcje renderujące własny HTML (za pomocą `format_html`) są oznaczane jako zwracające `-> str`. Jednak `format_html` pod maską zwraca obiekt `SafeString` (zabezpieczony przed XSS), co Mypy interpretuje jako `Any` i zgłasza błąd `[no-any-return]`.  
**Rozwiązanie / workaround:** Zabrania się rzutowania na zwykły string `str(format_html(...))`, gdyż niszczy to flagę bezpieczeństwa. Należy użyć `# type: ignore[no-any-return]`.

---

## 4. Weryfikacja i Postęp Turysty (Faza C)

<!-- Faza C: EC-030 i kolejne wpisy trafią tu przy realizacji User Progress i AscentLogs -->

### EC-030 — Wielokrotność zdobywania odznak i Zużycie Wejść (Repeatability & Ascent Consumption)
**Obszar:** `domain/rules/`, `application/use_cases/verify_badge.py`  
**Odkryty:** 2026-05-25 w trakcie analizy regulaminu "Diademu Polskich Gór".  
**Status:** `open` — Decyzja biznesowa i implementacyjna odroczona do Fazy C.  
**Opis:** Odznaka jest często zdobywana przez turystów wielokrotnie (tzw. Pętle Prestiżu, np. druga i trzecia "KGP"). Nasz aktualny silnik oceny w Czystej Domenie operuje na zbiorach matematycznych (`set`), które "połykają" duplikaty. Jeśli system bada wszystkie wejścia w życiu turysty, zignoruje fakt, że turysta chce zdobyć odznakę drugi raz na nowych wejściach. System obecnie odpowiada jedynie na pytanie: *"Czy w całej historii logów Jana Kowalskiego istnieje wystarczająco unikalnych szczytów do tej odznaki?"*.  
**Rozwiązanie / workaround:** Zbiór wszystkich wejść (`AscentLog`) przekazywanych do Use Case'a weryfikacji będzie musiał być uprzednio filtrowany przez `UserContext`. Wejścia "zużyte" do zamknięcia i weryfikacji Cyklu nr 1 dla danej odznaki nie mogą zostać przekazane do weryfikacji w Cyklu nr 2. Odznaka w modelu progresu użytkownika zostanie rozszerzona o pojęcie Edycji/Cyklu.  
**Test:** `[brakuje, TODO - test_EC030_completed_cycle_ascents_are_excluded_from_new_cycle]`

### EC-031 — Próg wejść (required_count) zaszyty w Wersji zamiast w Stopniu
**Obszar:** `infrastructure/adapters/persistence/django_badge_repo.py` (`_hydrate_version`)  
**Status:** `resolved (TD-03 zamknięte)`  
**Opis:** Podczas hydracji `BadgeVersionDomain` adapter przypisuje `required_count=len(pool_peaks)`. Jest to poprawne wyłącznie dla odznak jednostopniowych, w których należy zdobyć 100% szczytów z puli. Dla odznak typu "Zdobądż 20 z 50" lub wielostopniowych, to `BadgeTier` przechowuje rzeczywisty próg.  
**Rozwiązanie / workaround:** Zmiana została wprowadzona w Fazie C (`CHANGELOG.md` 0.3.0): `BadgeTierDomain` posiada własne pole `required_count`, a `evaluate()` ewaluuje progi na poziomie każdego Stopnia — nie na poziomie Wersji. Adapter (`_hydrate_version`) odczytuje `BadgeTierModel.required_peaks_count` i tylko dla `None` (brak tierów) fallbackuje do `len(pool_peaks)`. Oznaczenie fallback jako poprawne zachowanie dla odznak wymagających 100% puli. Testy: `test_hydrates_multi_tier_with_distinct_thresholds` + `test_hydrates_fallback_to_pool_size_when_required_peaks_count_is_null`.

### EC-032 — Testy `RequestFactory` omijają Django Middleware
**Obszar:** `apps/api/views.py`, `tests/apps/api/`  
**Odkryty:** Podczas pisania testów integracyjnych dla REST API.  
**Status:** `resolved`  
**Opis:** Biblioteka `RequestFactory` z Django służy do testowania izolowanych widoków. Oznacza to, że wygenerowane przez nią żądanie trafia *bezpośrednio* do kontrolera, całkowicie omijając stos Middleware (w tym nasz `RFC7807ErrorMiddleware`). Jeśli widok zakłada, że rzucony przez niego `UseCaseError` zostanie elegancko sformatowany w JSON przez warstwę wyżej, w teście z `RequestFactory` wyjątek wyleci na zewnątrz i zepsuje test, a na produkcji bez middleware'u wywołałby błąd 500.  
**Rozwiązanie / workaround:** Zastosowano programowanie defensywne. Widoki API łapią błędy z rodziny `ApplicationException` bezpośrednio w ciele metody (za pomocą lokalnego helpera `_handle_application_exception`). Globalny Middleware pozostaje w systemie jako siatka bezpieczeństwa ostatniej szansy (Catch-All dla błędów 500) oraz wstrzykiwacz `request_id`.

### EC-033 — MagicMock i TypeError przy `JsonResponse`
**Obszar:** `tests/apps/api/`  
**Odkryty:** Podczas asercji widoków zwracających słowniki z danymi.  
**Status:** `resolved`  
**Opis:** Zmockowany przypadek użycia (Use Case) wywołany w teście bez ustawionej jawnie wartości zwracanej (`return_value`), domyślnie zwraca kolejny obiekt `MagicMock`. Przekazanie tego obiektu dalej do widoku, który próbuje osadzić go w słowniku i przepuścić przez `JsonResponse`, kończy się natychmiastowym błędem `TypeError: Object of type MagicMock is not JSON serializable`.  
**Rozwiązanie / workaround:** Obowiązkowe, rygorystyczne definiowanie `.return_value = <typ_prosty>` (np. 42 lub dict) dla każdego zmockowanego serwisu przed wywołaniem żądania testowego.

### EC-034 — Kafelki MVT, Raw SQL i pułapka wstrzyknięcia (Bandit S608)
**Obszar:** `infrastructure/adapters/persistence/django_mvt_repo.py`  
**Odkryty:** Podczas implementacji serwera kafelków (ADR-013).  
**Status:** `resolved`  
**Opis:** GeoDjango nie wspiera natywnie funkcji takich jak `ST_AsMVTGeom` i `ST_TileEnvelope`. Konieczne było użycie surowego SQL (`RawSQL`). Zbudowanie zapytania w formacie stringa f-string (`f"FROM {table_name}"`) wywołuje krytyczny błąd lintera bezpieczeństwa (Possible SQL Injection), ponieważ nie da się parametryzować identyfikatorów tabel w driverze psycopg.  
**Rozwiązanie / workaround:** Zaimplementowano twardą "Białą Listę" (Whitelist) dozwolonych tabel na najwyższym poziomie warstwy Aplikacji (`LAYER_TO_TABLE_MAP` w Use Case). Dzięki temu do adaptera infrastrukturalnego trafia wyłącznie zwalidowany statyczny ciąg znaków, co czyni atak SQL Injection niemożliwym. Linia została jawnie zignorowana komentarzem `# noqa: S608`.

### EC-068 — "Cinderella Bug" (Znikające punkty po północy przy Prawach Nabytych)
**Obszar:** `infrastructure/adapters/persistence/django_badge_repo.py`, `PoiScoringService`  
**Status:** `resolved`  
**Opis:** Algorytm punktacji `100/n` rysujący mapę w czasie rzeczywistym używał mechanizmu symulacji Praw Nabytych, odpytując bazę o wersję regulaminu ważną na "dzisiaj" (`valid_from <= today`). Po minięciu północy (zmiana daty na kolejny dzień), system nagle przestał punktować cele. Wynikało to z błędu zapytania SQL, które ignorowało pole `valid_to`. Stara wersja odznaki zamknięta 3 lata temu również spełniała warunek `valid_from <= today`, więc w locie baza mogła zwrócić błędną (starą i zamkniętą) wersję jako rzekomo "aktywną" na dziś.
**Rozwiązanie / workaround:** Każde historyczne zapytanie o Wersję Odznaki musi obligatoryjnie implementować pełne zamknięcie wektora czasowego z użyciem logiki `Q` w Django ORM: `Q(valid_from__lte=target_date)` ORAZ `(Q(valid_to__isnull=True) | Q(valid_to__gte=target_date))`. Dodatkowo, dla wirtualnego "rysowania mapy" (bez zabetonowanych praw nabytych) wprowadzono osobną metodę `get_latest_badge_version()`, uodparniając mapę na upływ czasu.

---

## 5. Frontend i Interfejs Użytkownika (UI/UX)

### EC-035 — Niezgodność typów w Cache (Szare Pinezki na Mapie)
**Status:** `resolved`  
**Opis:** Klucze ID wyciągnięte z Redis/Pickle były serializowane do `str`, podczas gdy baza operuje na `int`. Skutkowało to brakiem kolorowania szczytów. Rozwiązano przez wdrożenie *Double Lookup* z rzutowaniem w locie.

### EC-036 — Brak wsparcia Data-Driven Styling dla 'line-dasharray'
**Status:** `resolved`  
**Opis:** WebGL w MapLibre "po cichu" nie rysował granic MVT z powodu próby dynamicznej zmiany stylu linii z przerywanej na ciągłą. Rozwiązano rozbijając to na statyczne, oddzielne warstwy.

### EC-037 — Błąd 500 przy relacji ForeignKey (Brakujący Profil)
**Status:** `resolved`  
**Opis:** Użytkownicy zarejestrowani przed wprowadzeniem "Konta Rodzinnego" nie posiadali wygenerowanego `TouristProfile`, co kończyło się błędem `RelatedObjectDoesNotExist`. Rozwiązano wprowadzając *Lazy Initialization* (tworzenie profilu w locie przy odczycie).

### EC-038 — XML Bomb (XXE) w plikach GPX
**Status:** `resolved`  
**Opis:** Zablokowano parsowanie śladów GPX wbudowaną biblioteką Pythona. Zastosowano `defusedxml` by uniknąć ataku Billion Laughs.

### EC-039 — Błędy rysowania w OSM (Mikroszczeliny między poligonami)
**Status:** `resolved`  
**Opis:** Funkcja `ST_Touches` pomijała wiele graniczących regionów przez błędy w rysowaniu OSM. Rozwiązano zmieniając logikę na `shape__distance_lte=(..., D(m=50))` i przenosząc ten ciężar do skryptu pre-kalkulacyjnego M2M (`calculate_neighbors`).

### EC-040 — MVT z PostGIS gubi duże identyfikatory (BigInt)
**Status:** `resolved`  
**Opis:** Format PBF gubił duże ID przy renderowaniu kafelków wektorowych. Rozwiązano przez twarde rzutowanie ID na typ tekstowy w SQL (`t.id::text AS db_id_str`).

### EC-041 — Pułapka domyślnych szablonów .gitignore
**Status:** `resolved`  
**Opis:** (Dawniej EC-040). Brakowało restrykcji na lokalne pliki `.env`, co groziło wyciekiem haseł. Zablokowano zmuszając do stosowania wyłącznie `.env.example`.

### EC-042 — Testy `RequestFactory` omijają Django Middleware
**Status:** `resolved`  
**Opis:** Testowanie widoków przez `RequestFactory` całkowicie omijało `RFC7807ErrorMiddleware`. Zmusiło to nas do wdrożenia obsługi `ApplicationException` bezpośrednio w widokach `views.py`.

### EC-043 — Konflikty renderowania `django-unfold` (Leaflet, JSONForm i obce aplikacje)
**Obszar:** `apps/badges/admin.py`, `apps/badges/forms.py`  
**Status:** `resolved`  
**Opis:** Wdrożenie `django-unfold` (opartego na Tailwind CSS) powoduje globalny *CSS Reset*, co "ogołaca" ze stylów domyślne widżety i panele Django. Skutkuje to zniknięciem map w `django-leaflet`, zepsuciem widżetów `<datalist>`, nadpisaniem `django-jsonform` oraz **znikaniem przycisków "Dodaj" w zewnętrznych aplikacjach** (np. `django-celery-beat`), które domyślnie używają klasycznego interfejsu.
**Rozwiązanie / workaround:** 
Wdrożono twarde reguły nadpisywania:
1. **Mapy:** Użyto `LeafletGeoAdminMixin` w połączeniu z `ModelAdmin` z Unfold (kolejność dziedziczenia przed `ModelAdmin` jest kluczowa!).
2. **JSONForm:** Nadpisano metodę `formfield_for_dbfield`, aby jawnie wywoływała oryginalną logikę pola.
3. **Własne widżety:** Muszą dziedziczyć z `UnfoldAdminTextInputWidget`.
4. **Obce Aplikacje (Zewnętrzne):** Modele z zewnętrznych bibliotek (np. `PeriodicTask`) muszą zostać jawnie wyrejestrowane (`admin.site.unregister()`) i zarejestrowane ponownie z dziedziczeniem po klasach z `unfold.admin`.
*(Zakazuje się agentom LLM usuwania tych obejść podczas refaktoryzacji panelu).*

### EC-044 — Omijanie metody clean() przez Akcje Django Admina
**Obszar:** `apps/badges/models.py` (`TouristObject`)  
**Status:** `resolved`  
**Opis:** Walidacja zabezpieczająca przed tworzeniem pętli w klastrach (Invariant C-01) została umieszczona w metodzie `clean()`. Niestety, wbudowane "Akcje" (Actions) w Django Adminie uderzają bezpośrednio do bazy przez `.save()` lub `.update()`, całkowicie omijając formularz i metodę `clean()`, co pozwalało na stworzenie nielegalnego cyklu A->B->A.
**Rozwiązanie / workaround:** Wymuszenie twardej walidacji przez nadpisanie metody `save()` w modelu, która zawsze wywołuje `self.clean()`. Błędy wywołane przez Akcje rzucają wtedy bezpiecznym błędem 500 zamiast cicho korumpować bazę.

### EC-045 — Problem N+1 przy weryfikacji PrerequisiteBadgeRule
**Obszar:** `application/use_cases/verify_badge.py`  
**Status:** `resolved`  
**Opis:** Reguła wymagająca posiadania innej ukończonej odznaki wymuszała pobranie przez Use Case wszystkich postępów turysty do pamięci RAM, a następnie filtrowanie ich w Pythonie. Skutkowało to ogromnym obciążeniem pamięci i problemem N+1 przy rosnącej historii użytkownika.
**Rozwiązanie / workaround:** Przeniesienie ciężaru na relacyjną bazę danych poprzez dodanie zoptymalizowanej metody `get_completed_badge_codes()` w Porcie, która wykonuje jedno, płaskie zapytanie SQL (`SELECT ... WHERE domain_status='COMPLETED'`).

### EC-085 — Błędy routingu przez brakujący ukośnik (Trailing Slash)
**Obszar:** `apps/api/urls.py`, `apps/static/js/map.js`  
**Status:** `resolved`  
**Opis:** Django domyślnie wymaga ukośnika na końcu adresu URL (działa `APPEND_SLASH`). Wywołanie w `fetch()` lub Postmanie adresu `/api/v1/map/objects` (bez ukośnika) powoduje zwrócenie przez serwer statusu `301 Redirect` do adresu z ukośnikiem. Jeśli żądanie było typu POST, przekierowanie gubi payload (zmienia się w GET), co prowadzi do niezrozumiałych błędów w API.
**Rozwiązanie / workaround:** Twarda reguła w kodzie – wszystkie ścieżki w `urls.py` muszą kończyć się na `/`, a każdy skrypt JS musi odpytywać adres z ukośnikiem na końcu.

### EC-086 — Błąd składni Pythona 2 przy łapaniu wielu wyjątków
**Obszar:** `apps/api/views.py`  
**Status:** `resolved`  
**Opis:** Podczas refaktoryzacji, agenci LLM potrafią wygenerować przestarzały kod: `except json.JSONDecodeError, ValueError:`. W Pythonie 3 powoduje to natychmiastowy `SyntaxError` przy starcie serwera (Gunicorn/Uvicorn w ogóle nie wstanie).
**Rozwiązanie / workaround:** Prawidłowa składnia wymaga użycia krotki: `except (json.JSONDecodeError, ValueError):`. Egzekwowane przez linter Ruff.

### EC-046 — Konflikt typowania `HttpRequest` i dekoratorów w widokach API
**Obszar:** `apps/api/views.py`  
**Status:** `resolved`  
**Opis:** Podczas definiowania widoków opartych na klasach (CBV), użycie listy dekoratorów `[csrf_exempt, require_auth]` nad klasą, a także jawne typowanie parametru `request: HttpRequest` bez odpowiednich importów na szczycie pliku, wywoływało seryjne błędy lintera Ruff (F821 - undefined name). Co więcej, z uwagi na wdrożenie `_handle_application_exception`, zewnętrzne dekoratory autoryzacji psuły format zwracanych błędów RFC 7807 (zwracając standardowe 403 z HTML).  
**Rozwiązanie / workaround:** Zrezygnowano z dekoratorów autoryzacyjnych i jawnego typowania `HttpRequest` w sygnaturach metod, na rzecz metodycznej asercji wewnątrz ciała widoku: `auth_error = _require_auth(request)`. Nałożono wyłącznie pojedyńczy dekorator `@method_decorator(csrf_exempt, name="dispatch")`.

### EC-047 — Błąd typowania Mypy przy `get_or_create` (Zwracane `Any`)
**Obszar:** `infrastructure/adapters/persistence/` (w tym `django_news_repo.py`)  
**Status:** `resolved`  
**Opis:** Metoda `get_or_create` w ORM Django zwraca krotkę `(obj, created)`. Niestety, wtyczka `django-stubs` dla `mypy` nie zawsze potrafi poprawnie wywnioskować typu flagi `created` i traktuje ją jako `Any`. Jeśli metoda portu deklaruje twardy zwrot typu `bool`, `mypy --strict` wyrzuca błąd `Returning Any from function declared to return bool`.
**Rozwiązanie / workaround:** Zawsze wymuszaj jawne rzutowanie flagi na typ logiczny, np. `return bool(created)`, aby zadowolić lintera i uciąć przepływ `Any` z adaptera do domeny.

### EC-048 — Defensywne typowanie w BeautifulSoup (Atrybuty mogą być listami)
**Obszar:** `infrastructure/adapters/news_scraper.py`  
**Status:** `resolved`  
**Opis:** Przy parsowaniu HTML za pomocą `BeautifulSoup`, wyciąganie atrybutów z tagu, takich jak np. `link_tag.get('href')`, zwraca skomplikowany unijny typ danych. Zgodnie z HTML, atrybuty (szczególnie `class`) mogą być listami. Próba bezpośredniej konkatenacji `str + link_tag.get('href')` powoduje błąd `mypy` ostrzegający przed łączeniem stringa z potencjalną listą lub `None`.
**Rozwiązanie / workaround:** Każdy atrybut wyciągnięty z `BeautifulSoup` przed użyciem musi zostać jawnie "rozpakowany" za pomocą drzewa decyzyjnego: `if isinstance(attr, list): val = str(attr[0]) elif isinstance(attr, str): val = attr else: val = ""`.

### EC-049 — Niezamierzona konwersja `dict` na `tuple` w plikach konfiguracyjnych
**Obszar:** `config/settings.py`  
**Status:** `resolved`  
**Opis:** Podczas definiowania dużych słowników konfiguracyjnych (np. `SOCIALACCOUNT_PROVIDERS`), pozostawienie przecinka na samym końcu po klamrze zamykającej słownik (`},`) powoduje, że Python automatycznie i cicho rzutuje całą strukturę na jednoelementową krotkę (`tuple`). Prowadzi to do błędu `AttributeError: 'tuple' object has no attribute 'get'` w głębokich warstwach zewnętrznych bibliotek (takich jak `allauth`), co jest ekstremalnie trudne do debugowania.
**Rozwiązanie / workaround:** Rygorystyczne przestrzeganie czystości składni na końcu definicji zmiennych globalnych w plikach `.py` (brak przecinków końcowych). Egzekwowane przez linter `ruff`.

### EC-050 — Zdeprecjonowana konfiguracja `django-allauth` (Żółte ostrzeżenia przy starcie)
**Obszar:** `config/settings.py`, logowanie OAuth  
**Status:** `resolved`  
**Opis:** Użycie nowoczesnej wersji `django-allauth` (`>=65.0.0`) w połączeniu ze starymi flagami konfiguracyjnymi (np. `ACCOUNT_EMAIL_REQUIRED = True`, `ACCOUNT_USERNAME_REQUIRED = False`) generuje ostrzeżenia deprecjacji przy uruchamianiu serwera.
**Rozwiązanie / workaround:** Przejście na nowy standard deklaratywny biblioteki. Należy używać zbiorów i list: `ACCOUNT_LOGIN_METHODS = {'email'}` oraz `ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']`.

### EC-051 — `UnboundLocalError` przy leniwych importach w blokach try/except
**Obszar:** `infrastructure/adapters/osm_adapter.py`  
**Status:** `resolved`  
**Opis:** W ramach unikania modyfikacji góry pliku, zastosowano tzw. lokalny (leniwy) import wewnątrz metody (np. `import json` wewnątrz bloku `try`). Jednocześnie w klauzuli `except` sprawdzano wyjątek z tego modułu (`except json.JSONDecodeError:`). Kiedy połączenie sieciowe rzuciło `TimeoutError` przed wykonaniem importu, skrypt przeskoczył do ewaluacji bloku `except`, co zakończyło się twardym błędem aplikacji: `UnboundLocalError: cannot access local variable 'json'`.
**Rozwiązanie / workaround:** Twardy zakaz stosowania lokalnych importów wewnątrz funkcji dla modułów, które biorą udział w logice obsługi wyjątków (`try/except`). Wszystkie tego typu zależności muszą być zadeklarowane na poziomie modułu (na samej górze pliku).

### EC-052 — Niewidzialne zmienne środowiskowe w czystych skryptach Pythona
**Obszar:** `scripts/check_secrets.py` oraz wszelkie narzędzia w katalogu `scripts/`  
**Status:** `resolved`  
**Opis:** Aplikacja główna Django odczytuje plik `.env` bezbłędnie dzięki bibliotece `pydantic-settings` (w `infrastructure/config/app_settings.py`). Jednakże uruchomienie czystego skryptu diagnostycznego poleceniem `python script.py` powoduje, że wywołania `os.getenv("KLUCZ")` zwracają `None`, nawet jeśli plik `.env` istnieje w katalogu. Wynika to z faktu, że czysty Python nie parsuje lokalnego pliku `.env` i nie eksportuje jego zawartości do powłoki systemu operacyjnego bez użycia dodatkowych narzędzi (np. `python-dotenv`).
**Rozwiązanie / workaround:** Zrezygnowano z dodawania zewnętrznych bibliotek dla skryptów testowych. Skrypt `check_secrets.py` został przepisany tak, aby manualnie (za pomocą wbudowanego w Pythona `open()`) parsować plik `.env.example` oraz `.env` i samodzielnie budować logikę weryfikującą obecność sekretów, całkowicie uniezależniając środowisko testowe CI od powłoki systemu operacyjnego (Bash/Zsh).

### EC-053 — Przepełnienie pamięci przez filtry M2M / FK w Django Adminie
**Obszar:** `apps/badges/admin.py`  
**Status:** `resolved`  
**Opis:** Użycie domyślnego mechanizmu filtrowania Django (`list_filter = ("pool_peaks",)`) dla relacji do dużej tabeli (ponad 10 000 obiektów turystycznych) powoduje wygenerowanie przez ORM gigantycznej listy w panelu bocznym. Skutkuje to ogromnym obciążeniem bazy danych, przesyłaniem megabajtów niepotrzebnego HTML-a oraz zawieszaniem się przeglądarki Administratora przy próbie wyrenderowania strony.
**Rozwiązanie / workaround:** Twardy zakaz stosowania domyślnych filtrów dla dużych relacji. Wdrożono niestandardowy filtr oparty na `SimpleListFilter` (`PeakInBadgeFilter`). Klasa ta używa zoptymalizowanego zapytania w metodzie `lookups` (np. `.filter(badgeversionmodel__isnull=False).distinct()`), aby do panelu bocznego zaciągnąć WYŁĄCZNIE te obiekty, które są aktualnie w użyciu, całkowicie pomijając "sieroty". Dodatkowo wykorzystano `search_fields` ze ścieżką relacyjną (`pool_peaks__name`) jako lżejszą alternatywę wyszukiwania.

### EC-054 — Niedziałające przyciski HTMX wewnątrz dynamicznych dymków mapy (Popups)
**Obszar:** `apps/static/js/map.js` (Integracja MapLibre z HTMX)  
**Status:** `resolved`  
**Opis:** Konstruowanie kodu HTML wewnątrz skryptu JavaScript (np. zmienna `popupHtml` dla MapLibre) i osadzanie w nim atrybutów HTMX (np. `hx-post`, `hx-vals`) skutkuje tym, że po kliknięciu przycisku w dymku na mapie, akcja HTMX nie jest wyzwalana. Wynika to z faktu, że biblioteka HTMX buduje nasłuchiwacze zdarzeń tylko podczas ładowania dokumentu. Dynamicznie wstrzyknięty węzeł DOM jest dla niej "niewidzialny".
**Rozwiązanie / workaround:** Po każdym dodaniu dynamicznego elementu do drzewa DOM (np. po wywołaniu `.addTo(map)` dla popupu), należy bezwzględnie wymusić na HTMX przeskanowanie nowego fragmentu za pomocą funkcji bibliotecznej: `htmx.process(popup.getElement());`. Dzięki temu HTMX "zauważy" nowe przyciski i podepnie pod nie obsługę zdarzeń AJAX.

### EC-055 — "Problem Dwóch Mózgów" (Rozjazd pamięci podręcznej Celery i Django)
**Obszar:** `config/settings.py`, `PoiScoringService`, `Redis`  
**Status:** `resolved`  
**Opis:** Pomimo pomyślnego wykonania zadania `recalculate_poi_scores_task` przez Workera Celery w 0.1s, aplikacja webowa Django nie widziała wyników na mapie (szczyty pozostawały szare i dawały 0 punktów). Zjawisko to wystąpiło z powodu braku jawnej deklaracji zmiennej `CACHES` w pliku `settings.py`. Domyślnie Django i Celery używały `LocMemCache` (Lokalnej pamięci RAM procesu). W efekcie Worker Celery zapisywał wynik do swojej pamięci RAM, a Serwer Web (Gunicorn/Runserver) odpytywał swoją, pustą pamięć.  
**Rozwiązanie / workaround:** Wymuszono podpięcie współdzielonego klastra: `CACHES = {"default": {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": ...}}`. Ostrzeżenie operacyjne: po zmianie w kodzie odpowiedzialnym za punktację, ZAWSZE należy restartować proces Workera Celery, by załadował nową logikę do pamięci.

### EC-056 — Dzielenie całkowite w Pythonie a błędna wycena `100/n`
**Obszar:** `application/services/poi_scoring_service.py`  
**Status:** `resolved`  
**Opis:** Pierwsza implementacja wzoru 100/n (`score_value = 100 // missing_n`) zwracała wyniki `0` lub `1` dla większości szczytów. Zastosowanie operatora `//` wymuszało w Pythonie zaokrąglanie w dół przed konwersją do typu zmiennoprzecinkowego (np. `100 // 80` dawało `1`, a `100 // 120` dawało `0`). Dodatkowo waga była wyliczana globalnie przed symulacją wejścia, co fałszowało "zysk" ze szczytu.
**Rozwiązanie / workaround:** Zmieniono na klasyczne dzielenie zmiennoprzecinkowe `100.0 / missing_after_ascent` i zabezpieczono funkcją `round()`. Obliczenia wagi wstawiono **wewnątrz** pętli po przeprowadzeniu symulacji wejścia (Set Math na agregacie), tak aby wynik odzwierciedlał faktyczny zysk dla turysty po odwiedzeniu konkretnej góry.

### EC-060 — Pokusa łamania granic API przez używanie helperów widoków (Coupling)
**Obszar:** `apps/api/views.py` vs `apps/tourists/views.py`  
**Status:** `resolved`  
**Opis:** Podczas refaktoryzacji z `user_id` na `profile_id`, w widokach REST API (`api/views.py`) podjęto próbę zaimportowania i użycia funkcji pomocniczej `_get_active_profile_id` z modułu renderującego szablony HTML (`tourists/views.py`). Spowodowało to błąd lintera (F821), ponieważ takie krzyżowe importy między aplikacjami łamią zasadę niezależności API od warstwy prezentacyjnej.
**Rozwiązanie / workaround:** Zablokowano współdzielenie helperów między API a widokami HTML. Widoki API muszą polegać na natywnym odczycie sesji wewnątrz własnego kontekstu: `request.session.get("active_profile_id") or request.user.profiles.first().id`.

### EC-061 — Przeglądarka ignoruje zmiany logiki MVT (Agresywny Browser Cache)
**Obszar:** `apps/static/js/map.js` (MapLibre), `VectorTileView`  
**Status:** `resolved`  
**Opis:** Modyfikacje logiki backendowej (np. zmiana surowego SQL dodająca nową kolumnę `db_id_str` do zapytania `ST_AsMVTGeom`) są często niewidoczne w aplikacji klienckiej, nawet po twardym odświeżeniu (`Ctrl+F5`) lub usunięciu kluczy z Redis. Przeglądarki internetowe niezwykle agresywnie buforują pliki z rozszerzeniem `.pbf` na dysku lokalnym, ignorując polecenia odświeżenia.  
**Rozwiązanie / workaround:** Zastosowano wzorzec *Cache Busting* na poziomie kodu źródłowego frontendu. W momencie zmiany logiki kafelków MVT na serwerze, programista musi jawnie zmodyfikować adres URL źródła (Source) w MapLibre, dodając unikalny parametr wersji (np. `/api/v1/tiles/...pbf?v=4`). Zmusza to każdą przeglądarkę na świecie do fizycznego porzucenia swoich lokalnych kopii pliku i pobrania nowej struktury z serwera.

### EC-063 — Niewidoczny globalny stan (Window) po optymalizacji renderowania HTML
**Obszar:** `apps/templates/base.html`, `map.js`  
**Status:** `resolved`  
**Opis:** W ramach optymalizacji czasu ładowania strony, tagi `<script>` ładujące główne pliki logiki (np. `map.js`) zostały przeniesione na sam koniec dokumentu HTML (przed zamykający tag `</body>`). Zmiana ta spowodowała, że skrypty mapy próbowały użyć zmiennych wstrzykiwanych z Context Processora (np. limitów Freemium czy aktywnych profili), co kończyło się błędem `ReferenceError` lub wczytywaniem mapy w "Trybie Pustym", gdyż blok ze wstrzykiwaniem stanu wyrenderował się za późno względem inicjalizacji modułów.
**Rozwiązanie / workaround:** Twarda reguła szablonów: podczas gdy ciężkie biblioteki i pliki statyczne `.js` mogą i powinny rezydować na końcu dokumentu, **wstrzykiwanie bezpiecznego kontekstu biznesowego z serwera** (`<script> window.XYZ = {{ ... }}; </script>`) musi bezwzględnie znajdować się w sekcji `<head>`, aby zagwarantować gotowość globalnego stanu przed parsowaniem drzewa DOM i wyzwalaniem modułów klienckich.

---

## 6. Bezpieczeństwo i Integracja OAuth

### EC-064 — "Nagi HTML" przy przekierowaniu dla niezalogowanych
**Obszar:** `apps/templates/account/login.html`  
**Status:** `resolved`  
**Opis:** Kiedy niezalogowany użytkownik wchodzi na podstronę zabezpieczoną `@login_required` (np. `/`), Django domyślnie przekierowuje go na adres `/accounts/login/`. Jeśli system używa biblioteki `django-allauth`, serwuje ona na tym adresie wbudowany, całkowicie pozbawiony stylów CSS (nagi) plik HTML, co dramatycznie psuje User Experience aplikacji opartej na Tailwind CSS.  
**Rozwiązanie / workaround:** Wymagane jest zawsze jawne nadpisywanie wbudowanych szablonów biblioteki. Utworzono plik `apps/templates/account/login.html` dziedziczący po głównym `base.html`, który zawiera stylizowany ekran z przyciskiem logowania.

### EC-065 — Metoda GET dla linków logowania OAuth zablokowana ze względów bezpieczeństwa (CSRF)
**Obszar:** `apps/templates/base.html`, Przyciski Logowania  
**Status:** `resolved`  
**Opis:** Nowoczesne wersje `django-allauth` (ze względów ochrony przed atakami na sesję) zabraniają inicjowania procesu OAuth (np. przekierowania do Google) za pomocą zwykłego linku `<a>` z parametrem `href`. Próba użycia linku skutkuje ekranem z ostrzeżeniem lub błędem metody HTTP.  
**Rozwiązanie / workaround:** Każdy przycisk "Zaloguj" wywołujący zewnętrznego dostawcę tożsamości musi być bezwzględnie zaimplementowany jako element `<button type="submit">` wewnątrz formularza `<form method="post">` z dołączonym tagiem `{% csrf_token %}`.

### EC-066 — Odrzucenie połączenia (Error 401 invalid_client) przy logowaniu Google
**Obszar:** `config/settings.py` (Zmienne środowiskowe z `.env`)  
**Status:** `resolved`  
**Opis:** Po kliknięciu w przycisk logowania przeglądarka zostaje odrzucona przez serwery Google z błędem 401 (OAuth client was not found).  
**Rozwiązanie / workaround:** Zjawisko to występuje z powodu błędu autoryzacji w chmurze (Google Cloud Console). Należy upewnić się, że zmienna `GOOGLE_OAUTH_CLIENT_ID` wczytywana z pliku `.env` jest dokładną kopią klucza z konsoli, a podany tam "Authorized redirect URI" w 100% odpowiada adresowi, z którego odpytuje nasza aplikacja deweloperska lub produkcyjna (np. `http://127.0.0.1:8005/accounts/google/login/callback/`).

---

## 7. Architektura Rodzinna i Błędy Stanu (Family Model & State)

### EC-087 — Zjawisko "Zaginionego Profilu" na starych kontach (Lazy Initialization Bypass)
**Obszar:** `apps/tourists/views.py`  
**Status:** `resolved`  
**Opis:** Konta utworzone na początku fazy deweloperskiej (np. za pomocą komendy `createsuperuser` w terminalu) nie posiadają podpiętego rekordu w tabeli `TouristProfile`, ponieważ zostały utworzone przed wpięciem sygnału `post_save`. Wejście takiego użytkownika na główną stronę powodowało błąd 500 w helperze odczytującym ID z bazy.  
**Rozwiązanie / workaround:** Odbudowano mechanizm "Leniwego Ładowania" w helperze `_get_active_profile_id`. Jeśli system nie znajdzie profilu, w ułamku sekundy automatycznie i "po cichu" zakłada domyślny, darmowy profil (`is_main_profile=True`, pakiet `FREE`) powiązany z zalogowanym użytkownikiem.

### EC-067 — Omyłkowe wywoływanie `request.profile` zamiast z sesji (Model Rodzinny)
**Obszar:** `apps/api/views.py` (i inne widoki żądań)  
**Status:** `resolved`  
**Opis:** Po wdrożeniu Modelu Rodzinnego (gdzie jeden `request.user` z Django posiada wiele `TouristProfile`), próby ułatwienia sobie pobierania profilu w kodzie poprzez odwoływanie się do nieistniejącego atrybutu (np. `profile_id = request.profile.id`) kończą się błędem `AttributeError: 'WSGIRequest' object has no attribute 'profile'`.  
**Rozwiązanie / workaround:** Twardy nakaz korzystania z wyciągania identyfikatora z sesji HTTP. Każdy widok API musi bezwzględnie weryfikować aktywny kontekst używając: `profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id`.

---

## 8. Pułapki Infrastruktury Docker i MVT (DevOps Gotchas)

### EC-069 — Utrata danych w PostgreSQL po zmianie nazwy wolumenu Dockera
**Obszar:** `compose.yml`, Wolumeny Dockera  
**Status:** `resolved`  
**Opis:** Zmiana struktury plików Compose lub zmiana nazwy przypisanego wolumenu (np. z `db_data` na `postgis_data`) powoduje, że przy kolejnym `docker compose up` system tworzy nową, całkowicie pustą bazę danych. Stare dane nie są kasowane fizycznie, ale zostają "odcięte" (Orphaned Volume), symulując utratę dorobku.
**Rozwiązanie / workaround:** Świadomość administracyjna. Przed modyfikacją nazw usług w Dockerze zawsze weryfikuje się punkt montowania poleceniem `docker volume ls | grep postgres`. Zabrania się usuwania bazy komendą `down -v` poza celowym resetem w skryptach lokalnych.

### EC-070 — Rozjazd uwierzytelnienia PostGIS po zmianie pliku `.env`
**Obszar:** `compose.yml`, `PostgreSQL`, pliki `.env`  
**Status:** `resolved`  
**Opis:** Baza PostgreSQL zapamiętuje dane uwierzytelniające (`POSTGRES_PASSWORD`) podane przy pierwszej inicjalizacji na pustym wolumenie dyskowym. Zmiana hasła w pliku środowiskowym `.env` po zainicjowaniu dysku nie zmienia hasła w samej bazie danych. W efekcie kontenery z Django i Celery próbują zalogować się z użyciem "nowego" hasła i wybuchają błędem `Connection Refused` (Brak autoryzacji).
**Rozwiązanie / workaround:** Utrzymanie identycznych danych logowania dla bazy DEV lub jawna zmiana hasła poprzez zapytanie `ALTER USER` bezpośrednio w powłoce SQL. Zmiana hasła w `.env` skutkuje wyłącznie na w pełni świeżych środowiskach (TEST, PRE-PROD).

### EC-071 — Utrata zadań asynchronicznych (In-Flight Tasks) przy restarcie Redis
**Obszar:** `compose.yml`, `Celery`, `Redis`  
**Status:** `resolved`  
**Opis:** W przypadku użycia domyślnego obrazu `redis:7-alpine` jako brokera wiadomości, dane trzymane są wyłącznie w ulotnej pamięci RAM. Jeśli kontener zostanie zrestartowany w trakcie wykonywania długiego zadania przez Workera (np. `PoiScoringService`), zlecenie z kolejki bezpowrotnie przepada (Zjawisko Task Drop).
**Rozwiązanie / workaround:** Zdefiniowanie dyrektyw w `compose.yml`: Wymuszenie twardego limitu pamięci (`--maxmemory-policy noeviction`) oraz aktywacja trybu AOF (`--appendonly yes`) zapobiegają cichemu usuwaniu zadań kosztem ewentualnego zawieszenia przy przepełnieniu (co jest obsługiwane logiką `retry` w Celery).

### EC-072 — Brak interpolacji zmiennych `env_file` w Docker Compose
**Obszar:** `compose.yml`, `.env`, konfiguracja DSN  
**Status:** `resolved`  
**Opis:** Użycie konstrukcji interpolacyjnej typu `DATABASE_URL=postgis://${USER}:${PASS}@db/` wewnątrz pliku ładowanego przez klauzulę `env_file` (np. `.env.dev`) w Docker Compose skutkuje brakiem rozwiązania zmiennych. Docker wstrzykuje do kontenera surowy, nieprzetworzony ciąg znaków z symbolami dolara, co powoduje natychmiastowe błędy połączenia biblioteki `dj-database-url`.
**Rozwiązanie / workaround:** Całkowite porzucenie interpolacji na poziomie plików konfiguracyjnych Dockera. DSN (Data Source Name) kompilowany jest programowo i dynamicznie w czystym Pythonie wewnątrz `app_settings.py` (przy użyciu `@computed_field` z modułu Pydantic) w oparciu o czyste, rozbite zmienne składowe (User, Pass, DB, Port).

### EC-073 — Błąd HTTP 400 zablokowany przez Healthcheck i `ALLOWED_HOSTS`
**Obszar:** `Dockerfile`, `config/settings.py`  
**Status:** `resolved`  
**Opis:** Aplikacja działa poprawnie, lecz kontener w Dockerze wchodzi w cykl powtarzających się restartów ze statusem "Unhealthy". Wdrożony sprzętowy Healthcheck (wykonujący natywne zapytanie HTTP GET na `localhost:8000/health/` wewnątrz kontenera) uderza w zaporę Django `ALLOWED_HOSTS`. Ponieważ w środowisku docelowym akceptujemy tylko nazwy domen, ruch z wewnętrznego `localhost` zostaje odrzucony błędem HTTP 400 (DisallowedHost).
**Rozwiązanie / workaround:** Dodano na twardo wpisy `"localhost"`, `"127.0.0.1"`, `"[::1]"` do stałej części tablicy `ALLOWED_HOSTS` w pliku `settings.py`, co "udrożniło" weryfikację zdrowia usługi z jednoczesnym dynamicznym rozszerzaniem reszty listy za pomocą danych wstrzykniętych z Pydantica.

### EC-074 — Błąd połączenia `could not translate host name "db"` podczas testów hosta
**Obszar:** `Makefile`, Środowisko `TEST`  
**Status:** `resolved`  
**Opis:** Wykonanie komendy `make test-all` na komputerze programisty (poza kontenerem) kończy się natychmiastowym błędem połączenia PostgreSQL. Mechanizm izolacji środowisk narzuca dla testów plik `.env.test`, w którym zmienna hosta zdefiniowana jest na sztywno jako `POSTGRES_HOST=db`. Host nie posiada wiedzy o strukturze sieciowej (DNS) wewnątrz wirtualnego środowiska Dockera, więc nie potrafi namierzyć węzła "db".
**Rozwiązanie / workaround:** Tryb wywołania wymusza rozdzielenie: Testy mogą być odpalane wprost przez hermetyczny kontener `docker compose run --rm web` ORAZ, w przypadku testowania bezpośrenio z maszyny hosta, można obejść problem manualnie wywołując nadpisanie portów wystawionych przez docker-compose: `POSTGRES_HOST=localhost make test-all`.

### EC-075 — Ślepe założenia dotyczące środowiska w testach `pytest`
**Obszar:** `tests/config/test_app_settings.py`  
**Status:** `resolved`  
**Opis:** Testy jednostkowe zakładające wartości z pliku `.env.dev` (np. `APP_ENV=development` lub `POSTGRES_USER`) wybuchają błędem `AssertionError` przy uruchomieniu w wyizolowanym kontenerze testowym (środowisko `TEST`), gdzie plik `.env.test` nadpisuje środowisko celowo na `APP_ENV=test`.
**Rozwiązanie / workaround:** Zastosowano wzorzec izolacji testów za pomocą obiektu `monkeypatch` w Pyteście. Przed zainstancjonowaniem klasy `AppSettings` w teście, kod wymusza twardy reset zmiennych systemowych (`monkeypatch.delenv("APP_ENV", raising=False)` oraz `monkeypatch.setenv("ENV_FILE", ".env.dummy")`), aby test weryfikował absolutnie "gołą" (bez domyślnego wstrzykiwania ze środowiska) klasę konfiguracyjną.

### EC-076 — Testy poboczne skryptów łączące się z Internetem
**Obszar:** `scripts/test_osm.py`  
**Status:** `resolved`  
**Opis:** Pytest przy standardowej komendzie zbiera wszystkie pliki pasujące do wzorca `test_*.py` z głównego katalogu. Spowodowało to omyłkowe zebranie przez skaner pliku `scripts/test_osm.py`, który nie był testem jednostkowym, lecz manualnym poligonem doświadczalnym wykonującym prawdziwe (żywe) żądania do zewnętrznego Overpass API. Spowolniało to potok CI/CD i narażało środowisko `TEST` na błędy 404 (timeout sieciowy we Francji).
**Rozwiązanie / workaround:** W pliku `pyproject.toml` na stałe przypisano flagę konfiguracyjną `testpaths = ["tests"]`, twardo zawężając poszukiwania modułu testowego wyłącznie do katalogu wirtualnego, chroniąc `scripts/` przed automatycznym wykonaniem w pipeline.

### EC-077 — Zderzenie tożsamości środowisk przez domyślne nazewnictwo wolumenów i projektów
**Obszar:** `compose.preprod.yml`, `compose.test.yml`, Docker Volume  
**Status:** `resolved`  
**Opis:** Pomimo definicji odrębnych zmiennych środowiskowych i portów dla DEV i PRE-PROD, uruchomienie środowiska z tego samego katalogu źródłowego (bez jawnie podanej nazwy projektu przez `-p` lub `COMPOSE_PROJECT_NAME`) powodowało współdzielenie **fizycznych wolumenów bazy danych** (`badges_system_postgis_data`). W najgorszym scenariuszu, uruchomienie PRE-PROD wykonywało migracje bezpośrednio na bazie z danymi DEV, prowadząc do zniszczenia danych testowych i rozspójnienia klastra PostgreSQL.
**Rozwiązanie / workaround:** Zastosowano dwa twarde zabezpieczenia ("Defense in Depth"). Po pierwsze, każdy z plików `.yml` w sekcji `volumes` deklaruje **twardą, unikalną nazwę** (np. `badges_system_preprod_postgis_data`), nadpisując globalne definicje z `compose.yml`. Po drugie, zabrania się ręcznego używania `docker compose` dla środowisk wyższych na tej samej maszynie — wprowadzono rygorystyczne skrypty opakowujące (`preprod-run.sh` i `test-run.sh`), które zawsze i bezwarunkowo wymuszają argument `-p` separujący konteksty.

### EC-078 — Nadpisywanie tagów obrazów przy współdzielonych środowiskach (Tag Collisions)
**Obszar:** `compose.test.yml`, `compose.override.yml`, Docker Image  
**Status:** `resolved`  
**Opis:** W pliku `compose.test.yml` brakowało jawnej definicji `image:`. Docker przy budowaniu obrazów domyślnie używa nazwy usługi (np. `web`) z nazwą projektu. Gdy środowisko TEST dzieliło domyślną nazwę projektu z DEV, kompilacja etapu `testing` po cichu **nadpisywała obraz ze środowiska DEV** nowym obrazem testowym. Skutkowało to zmianą wbudowanego punktu wejścia (`entrypoint` zmieniał się na `pytest` zamiast powłoki Django), całkowicie psując komendy w środowisku deweloperskim.
**Rozwiązanie / workaround:** W pliku `compose.test.yml` zadeklarowano twardą, stałą nazwę `image: badges_system-web-testing`, która nigdy nie skoliduje z tagami DEV i PROD niezależnie od tego, czy programista pominie argument `-p` przy uruchamianiu.

### EC-079 — Błąd 127 (Command Not Found) po przebudowie entrypointu
**Obszar:** `Dockerfile`, `scripts/entrypoint.sh`  
**Status:** `resolved`  
**Opis:** Kontenery oparte o obraz produkcyjny uległy awarii (CrashLoopBackOff) przy próbie uruchomienia, rzucając błąd `Restarting (127)`. Jest to sygnał od wbudowanego w Linuksa środowiska powłoki, że skrypt zdefiniowany w `ENTRYPOINT` stracił (lub nigdy nie otrzymał) flagi wykonywalności (`+x`) na poziomie systemu hosta przed wbudowaniem w obraz Dockera. 
**Rozwiązanie / workaround:** Zapewniono komendę `RUN chmod +x` dla katalogu ze skryptami bezpośrednio w etapie `production` w pliku `Dockerfile`. W skrajnych przypadkach zablokowania powłoki należy zresetować system plików: `chmod +x scripts/*.sh` lokalnie przed wywołaniem `docker build`.

### EC-080 — Kolizja poleceń `uv run` z polityką `read_only: true` (OS Error 30)
**Obszar:** `compose.preprod.yml`, `uv` package manager  
**Status:** `resolved`  
**Opis:** Uruchomienie narzędzi lub skryptów w środowisku `PRE-PROD` korzystających z polecenia `uv run python ...` spowodowało krytyczny błąd `Read-only file system (os error 30)`. Narzędzie `uv` przy każdym wywołaniu próbuje zaktualizować pamięć podręczną kompilacji (`.cache`) lub pobrać pliki. Parametr `read_only: true` wymuszony z powodów bezpieczeństwa SRE całkowicie blokuje takie zapisy.
**Rozwiązanie / workaround:** Całkowite wyeliminowanie `uv run` z komend produkcyjnych i skryptów wdrożeniowych (np. `bootstrap.sh`, `celery_worker command`). Obraz produkcyjny musi wywoływać czysty proces interpretera wprost z zainstalowanego środowiska (np. `python manage.py ...` lub `celery -A ...`), które nie próbuje manipulować strukturą dyskową.

### EC-081 — Gunicorn wyparty z zależności środowiskowych przez `uv sync --no-dev`
**Obszar:** `pyproject.toml`, `Dockerfile`  
**Status:** `resolved`  
**Opis:** Wdrożenie zasady kompilacji zaleceń produkcyjnych (`--no-dev`) pozbawiło obraz kluczowych serwerów i usług, skutkując błędem `exec: gunicorn: not found`. Wynika to z pozostawienia narzędzi takich jak `gunicorn` czy `whitenoise` w grupie nieoficjalnej lub pominięcia ich w twardej deklaracji w pliku konfiguracyjnym projektu.
**Rozwiązanie / workaround:** Serwery ASGI/WSGI (np. `gunicorn`) oraz middleware obsługi plików statycznych na produkcji (np. `whitenoise`) muszą być zdefiniowane w bloku głównych zależności `[project.dependencies]` w `pyproject.toml`, a nie tylko doinstalowywane ręcznie w lokalnym środowisku.

### EC-082 — Przeciek starych implementacji Mypy (`AppContainer is not subscriptable`) do skryptów pobocznych
**Obszar:** `manage.py`, Skrypty Customowe  
**Status:** `resolved`  
**Opis:** Nawet po pozytywnym wdrożeniu `make check` dla wszystkich głównych katalogów, skrypt zarządzający `restore_reference_data` wyrzucił błąd w fazie produkcyjnej: `AppContainer object is not subscriptable`. Była to resztka z poprzedniego etapu (dostęp po kluczu słownikowym), której linter nie wychwycił, ponieważ domyślnie omija skanowanie folderów z narzędziami `management/commands` we frameworku Django.
**Rozwiązanie / workaround:** Każda refaktoryzacja warstw fundamentalnych (Kontener DI) wymaga jawnej weryfikacji wszystkich skryptów w katalogach poleceń (`commands/`) pod kątem zgodności z nowymi typami obiektów (np. zmiana z `get_container()["..."]` na `get_container()....`). Zalecono rozszerzenie konfiguracji lintera o te katalogi w `pyproject.toml`.

### EC-083 — Blokada `SynchronousOnlyOperation` przy wywoływaniu ORM z fiktur Playwrighta
**Obszar:** `tests/e2e/conftest.py`, `Playwright`, `Django ORM`  
**Status:** `resolved`  
**Opis:** Wstrzykiwanie sesji do przeglądarki wymagało wygenerowania ciasteczka przez komendę zarządzającą Django. Bezpośrednie wywołanie `call_command` z wnętrza fiktury Playwrighta (`logged_in_context`) skutkowało rzuceniem błędu `SynchronousOnlyOperation` przez Django. Wynika to z faktu, że silnik Playwright działa natywnie w pętli asynchronicznej (Async Event Loop), a Django ORM kategorycznie blokuje dostęp do bazy danych z wątków asynchronicznych bez użycia specjalnych adapterów (np. `sync_to_async`).
**Rozwiązanie / workaround:** Zamiast walczyć z pętlą asynchroniczną i blokadami wątków `pytest-django`, wywołanie komendy zepchnięto na poziom systemu operacyjnego. Skrypt używa `subprocess.run(["python", "manage.py", "create_test_session", ...])` wewnątrz kontenera testowego. Tworzy to całkowicie nowy, synchroniczny podproces Pythona, omijając blokady pamięci asynchronicznej.

### EC-084 — Globalny wymóg `Coverage` blokujący testy E2E
**Obszar:** `pyproject.toml`, `GitHub Actions (ci.yml)`  
**Status:** `resolved`  
**Opis:** Plik konfiguracyjny projektu narzuca twardy wymóg: `fail-under=80` (minimum 80% pokrycia kodu testami). Uruchomienie potoku testów E2E, który z założenia "klika" tylko po wierzchu aplikacji (Smoke Tests), siłą rzeczy pokrywa jedynie mały procent linii kodu. Pytest kończył się z sukcesem dla testów, ale narzędzie `pytest-cov` rzucało kodem błędu 1, blokując cały pipeline CI na GitHubie.
**Rozwiązanie / workaround:** W zadaniu GitHub Actions odpowiadającym za testy E2E nadpisano opcje konfiguracyjne w locie, stosując flagę `--override-ini="addopts="`. Neutralizuje to globalne ustawienia coverage, pozwalając testom E2E skupić się wyłącznie na poprawności funkcjonalnej, bez generowania bezużytecznych statystyk pokrycia.

### EC-085 — Awarie chmury i wąskie gardła w GitHub Actions (Capacity Limits)
**Obszar:** `CI/CD`, `.github/workflows/ci.yml`  
**Status:** `resolved (Workaround defined)`  
**Opis:** Ze względu na korzystanie ze współdzielonych zasobów (Shared Runners) w GitHub Actions, projekt jest narażony na globalne awarie infrastruktury Microsoftu. Objawia się to opóźnionymi uruchomieniami potoków (Queued), twardymi błędy uruchomienia runnera, lub odrzuceniami obrazów Docker w fazie budowania.
**Rozwiązanie / workaround:** Zgodnie z filozofią "Infrastructure as Code", cały pipeline został scentralizowany i zabezpieczony w skryptach systemowych (np. `make check`, `scripts/test-run.sh`, `scripts/e2e-run.sh`). Zależność od GitHub Actions ograniczono wyłącznie do warstwy orkiestracji (wyzwalania skryptu). W przypadku długotrwałej awarii GitHuba, Release Manager może z powodzeniem uruchomić kompletną pętlę walidacyjną lokalnie, wywołując polecenie `make verify`, które uderza w izolowane środowiska Dockera, gwarantując 100% pewności wdrażanego kodu nawet bez połączenia z chmurą.

### EC-086 — Fałszywe poczucie bezpieczeństwa z nieobsługiwanymi flagami (np. `--snapshot`)
**Obszar:** `management/commands/restore_reference_data.py`, skrypty wdrożeniowe  
**Status:** `resolved`  
**Opis:** Podczas pracy nad mechanizmem Rollbacku, w skryptach bashowych (np. `bootstrap.sh`) przekazywano do komend Django argument `--snapshot="${SNAPSHOT_ID}"`. Sama implementacja pythonowej komendy `restore_reference_data` nie obsługiwała jednak tego argumentu w bibliotece `argparse`. Zamiast przywracać wybraną, starszą wersję (Rollback), komenda cicho ignorowała parametr i po prostu wczytywała najnowsze dane znajdujące się w katalogu `data/reference/`. Stwarzało to iluzję działającego procesu Rollbacku.
**Rozwiązanie / workaround:** Zastosowano zasadę "No False Promises" (Żadnych Fałszywych Obietnic). Flaga `--snapshot` została usunięta z wywołań w skryptach powłoki. Rollback (aż do pełnej implementacji wersjonowanych katalogów w Pythonie) musi być wywoływany ręcznie poprzez cofnięcie commita w Gicie (`git checkout`) przed użyciem standardowej komendy `restore_reference_data`.

### EC-087 — CodeQL: `Config file could not be found` (Rozjazd wersji SHA)
**Obszar:** `.github/workflows/codeql.yml`  
**Status:** `resolved`  
**Opis:** Podczas uruchamiania potoku analitycznego CodeQL, zadanie `analyze` kończy się natychmiastowym błędem braku pliku konfiguracycyjnego bazy danych. Zjawisko to występuje, gdy krok inicjujący (`github/codeql-action/init@...`) korzysta z innej wersji narzędzia (inny hash Git/SHA) niż krok analizujący (`github/codeql-action/analyze@...`). Różne wersje nie potrafią odczytać swoich wewnętrznych artefaktów.
**Rozwiązanie / workaround:** Zgodnie ze standardem *Supply-Chain Security*, wszystkie etapy wchodzące w skład tego samego narzędzia w jednym pliku CI muszą być "przypięte" (Pinned) do **dokładnie tego samego, 40-znakowego klucza SHA** (np. `e4fba868fa4b1b91e1fdab776edc8cfbe6e9fb81`).

### EC-088 — Spadek wydajności CodeQL i niepotrzebne budowanie dla Pythona
**Obszar:** `CodeQL`, środowisko Python  
**Status:** `resolved`  
**Opis:** Narzędzie CodeQL próbuje domyślnie używać kroku `autobuild`, który sprawdza pliki Makefile lub skrypty budujące w poszukiwaniu języków kompilowanych (C/C++/Java). Dla projektów opartych na Pythonie (jak Django) jest to potężna strata zasobów i czasu (szczególnie na Self-Hosted Runnerach), co dodatkowo "zaśmieca" środowisko wirtualne niepotrzebnymi procesami.
**Rozwiązanie / workaround:** W konfiguracji kroku `init` dla narzędzia CodeQL wprowadzono twardą flagę `build-mode: none`. Powoduje to natychmiastowe przejście do czystej analizy statycznej kodu (AST), skracając czas działania skanera do kilkudziesięciu sekund.

### EC-089 — Zatrzymanie potoku CI/CD przez pakiety deweloperskie w obrazie
**Obszar:** `Dockerfile`, `Trivy`, `pyproject.toml`  
**Status:** `resolved`  
**Opis:** Na etapie budowy obrazów dla środowiska testowego (CI/CD) ładowano całą grupę pakietów `--group dev` (zawierającą m.in. narzędzie `semgrep` opierające się na pakiecie `mcp`). Kiedy bramka bezpieczeństwa (Skaner Trivy) analizowała obraz przed testami E2E, blokowała cały pipeline zgłaszając podatności (CRITICAL) w tym pakiecie.
**Rozwiązanie / workaround:** Wprowadzono twardą segregację w `pyproject.toml`. Utworzono nową grupę `[dependency-groups.test]` zawierającą wyłącznie pakiety niezbędne do uruchomienia testów w kontenerze (np. `pytest`, `pytest-django`, `hypothesis`). W etapie `testing` w Dockerfile wymuszono użycie polecenia `uv sync --frozen --group test --no-dev`. Grupa `dev` służy od tej pory wyłącznie do testów uruchamianych manualnie na hoście (Lintery).

### EC-090 — Niepoprawne nadpisywanie pliku środowiskowego w testach (Test Isolation)
**Obszar:** `tests/config/test_app_settings.py`, `pydantic-settings`  
**Status:** `resolved`  
**Opis:** Testy próbujące udowodnić, że aplikacja domyślnie wstaje w trybie `development` po wyłączeniu wszystkich flag, kończyły się błędem (`AssertionError: assert 'test' == 'development'`). Wynikało to z faktu, że środowisko CI/CD (lub `Makefile`) miało sztywno zapisaną zmienną `APP_ENV=test` lub ładujące `.env.test`. Próba obejścia tego za pomocą `monkeypatch.setenv("ENV_FILE", ".dummy")` w Pyteście nie działała, ponieważ klasa `AppSettings` i sam Pydantic "zatrzaskują" w pamięci (Cache) raz odczytany stan ze zmiennych środowiskowych przy pierwszym załadowaniu modułu.
**Rozwiązanie / workaround:** Zamiast operować na powłoce systemowej Pytestu, wprowadzono ręczne, bezpośrednie wstrzykiwanie braku pliku podczas instancjowania klasy do celów testowych: `AppSettings(_env_file=None)`. Weryfikuje to bezpośrednio kod klasy, całkowicie izolując testy od `os.environ` w środowisku testowym. Dodatkowo wprowadzono customowy walidator w `AppSettings`, zamieniający słowo tekstowe `"release"` na fałsz logiczny `False` w celu uodpornienia na specyficzne wartości podawane przez starsze skrypty w `DEBUG`.

### EC-091 — Błędy walidacji 403 vs 405 w środowisku Fuzzingu (Schemathesis)
**Obszar:** `API`, `Schemathesis`, `Django Middleware`  
**Status:** `resolved (Risk Accepted)`  
**Opis:** Podczas eksperymentalnego testowania API fuzzerem `Schemathesis`, narzędzie zgłaszało błędy naruszenia kontraktu OpenAPI dla metod z grupy `QUERY` (oraz innych nieobsługiwanych metod), ponieważ oczekiwało od serwera poprawnego błędu `405 Method Not Allowed`. Tymczasem stos Middleware'ów bezpieczeństwa w Django odrzucał te niecodzienne metody wcześniej na poziomie walidacji CSRF lub autoryzacji, zwracając `403 Forbidden`.
**Rozwiązanie / workaround:** Zjawisko to zostało zdefiniowane jako **Oczekiwane (Expected Limitation)**. Próba przepisywania silnika bezpieczeństwa Django po to, by usatysfakcjonować skaner API, stanowiłaby naruszenie bezpieczeństwa. 16 takich naruszeń stanowi historyczny, zaakceptowany poziom odniesienia (Baseline). Głównym zadaniem fuzzera jest wykrywanie nieprzewidzianych załamań serwera (`HTTP 5xx`), a nie estetyki odrzuceń na bramce HTTP.

### EC-092 — Destrukcja lokalnego środowiska DEV przez skanery DAST i Load Testy
**Obszar:** `Makefile`, `k6`, `OWASP ZAP`  
**Status:** `resolved`  
**Opis:** Eksperymentalne narzędzia weryfikujące bezpieczeństwo dynamiczne (DAST - np. OWASP ZAP) oraz narzędzia do testów obciążeniowych (np. k6) domyślnie uderzały w adres `localhost:8000/8005` (środowisko deweloperskie). Zmasowany ruch i generowanie zmutowanych payloadów (np. próby wstrzyknięcia XSS lub masowe tworzenie sesji) prowadziły do zanieczyszczenia lokalnej bazy danych programisty (Data Pollution), wyczerpania puli połączeń do PostGIS i degradacji lokalnego środowiska pracy.
**Rozwiązanie / workaround:** Wprowadzono bezwzględną politykę "Sterylnego Poligonu". Narzędzia inwazyjne/destrukcyjne otrzymały dedykowane skrypty ładujące (`scripts/k6-run.sh`, `scripts/zap-run.sh`). Zmuszają one narzędzia do każdorazowego, automatycznego podnoszenia ulotnego środowiska `E2E` (na wyizolowanym porcie `8009` z efemeryczną bazą danych), przeprowadzenia testu i wykonania procedury "Sprzątania" (`docker compose down -v --remove-orphans`). Środowisko `DEV` programisty pozostaje w 100% bezpieczne.

### EC-093 — Błąd długości nazwy indeksu (Composite Index Naming Constraint)
**Obszar:** `apps/tourists/models.py`, `migrations`  
**Status:** `resolved`  
**Opis:** Podczas dodawania złożonego indeksu bazodanowego (Composite Index) dla optymalizacji odczytów Czystej Domeny, zdefiniowano nazwę `progress_profile_badge_status_idx` (33 znaki). Bazy danych (np. domyślne reguły PostgreSQL / silnik migracji Django) posiadają twarde restrykcje dotyczące długości identyfikatorów, co może skutkować błędem podczas aplikowania migracji (Database Release).
**Rozwiązanie / workaround:** Zastosowano agresywną kompresję nazw (akronimizację) dla indeksów łączonych. Ostateczna nazwa to `progress_p_b_s_idx` (18 znaków), co mieści się w bezpiecznym limicie i pozwala migracji przejść płynnie. Należy stosować krótkie akronimy dla wszystkich nowych indeksów `Meta.indexes`.
