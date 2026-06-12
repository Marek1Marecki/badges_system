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
**Status:** `open` (Dług Technologiczny TD-03)  
**Opis:** Podczas hydracji `BadgeVersionDomain` adapter przypisuje `required_count=len(pool_peaks)`. Jest to poprawne wyłącznie dla odznak jednostopniowych, w których należy zdobyć 100% szczytów z puli. Dla odznak typu "Zdobądź 20 z 50" lub wielostopniowych, to `BadgeTier` przechowuje rzeczywisty próg.  
**Rozwiązanie / workaround:** Do czasu przebudowy Use Case'a tak, by wstrzykiwał progi ze Stopni (Tiers) do Czystej Domeny, weryfikacja takich odznak poprawnie policzy `valid_ascents_count`, ale pole `verified` fałszywie zwróci `False`. Konieczna refaktoryzacja w Fazie C.

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

---

## 5. Repozytorium i CI/CD (Operacje)

### EC-040 — Pułapka domyślnych szablonów `.gitignore` (Utrata plików kontraktowych)
**Obszar:** `.gitignore`, CI/CD Pipeline  
**Odkryty:** Podczas pierwszego commitu inicjalizującego repozytorium.  
**Status:** `resolved`  
**Opis:** Popularne w internecie szablony pliku `.gitignore` dla Pythona często domyślnie wykluczają pliki takie jak `.python-version`, `.dockerignore`, a generatory mogą zignorować pliki blokujące (lockfiles) takie jak `uv.lock`. Dodanie takiego szablonu do projektu powoduje niewypchnięcie tych plików na serwer, co natychmiast łamie pipeline CI/CD (brak spójności wersji Pythona, brak zamrożonych zależności) lub powoduje wgranie 2-gigabajtowego folderu `.venv` do obrazu Dockera produkcyjnego.  
**Rozwiązanie / workaround:** Zdefiniowano twardy nakaz commitowania plików kontrolnych. Pliki `.dockerignore`, `.python-version`, `uv.lock` oraz katalog `.github/` **zawsze** muszą być śledzone przez system Git. Ewentualne próby ich zignorowania zostaną wyłapane przez awarię kontraktu CI.

### EC-041 — "Leniwe" omijanie linterów przez agentów LLM (C408, E501)
**Obszar:** Agenci LLM, Linter `ruff` (Pipeline CI)  
**Odkryty:** Podczas implementacji reguł `GroupedAlternativesRule` z użyciem pustych list.  
**Status:** `resolved`  
**Opis:** Modele generujące kod (LLM) mogą czasami napotkać trudności z wygenerowaniem optymalnej składni Pythona (np. dławienie się na znakach `[]` i zastępowanie ich przez wywołania `list()`). Gdy linter `ruff` (C408) słusznie zgłosi błąd nieoptymalnego kodu, agenci mają silną tendencję do "uciszania" ostrzeżenia poprzez wstawianie komentarzy typu `# noqa: C408` zamiast naprawy samej logiki. Zjawisko to maskuje dług techniczny w projekcie.  
**Rozwiązanie / workaround:** Ustanowiono twardą zasadę w Protokołach Agenta (`.cursorrules` i `AGENT_SPEC.md`): Agenci mają bezwzględny zakaz uciszania linterów strukturalnych (jak `C`, `E`, `F`) za pomocą komentarzy `noqa` (z wyjątkiem jawnie uwarunkowanych wyjątków z grupy `S` - Security, jak w przypadku celowego użycia `mark_safe`). Jakikolwiek kod ignorujący linter z powodu wygody modelu musi zostać odrzucony podczas Code Review.

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-28 | Dominik / AI Architect | Zarchiwizowanie pierwszych rozwiązań operacyjnych z fazy zasilania danymi i panelu administracyjnego. Otwarte EC-030 dla przyszłej weryfikacji użytkowników. |
| 1.1 | 2026-05-28 | AI Architect | Uzupełnienie pól Test i Reprodukcja, rearanżacja do 4 kategorii, dodanie EC-022 (Cykle klastrów). |
| 1.2 | 2026-05-30 | Dominik / AI Architect | Ujednolicono liczbę prób (Retry) na 15 prób zgodnie z wdrożonym logiem w kodzie (maksymalny czas oczekiwania). |
|
