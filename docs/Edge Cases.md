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
**Status:** `open` — blokuje wdrożenie finalnego widoku Klastrów.  
**Opis:** Relacja `parent_object` pozwala na stworzenie cyklu (np. Szczyt jest rodzicem Schroniska, a Schronisko zostaje przypięte jako rodzic Szczytu). Prowadzi to do nieskończonej pętli przy rekurencyjnym odpytywaniu grafu obiektów w API lub Celery, co skutkuje przepełnieniem stosu (Stack Overflow) na serwerze.  
**Reprodukcja:** 
1. Przypisz Obiekt A jako rodzica dla Obiektu B.
2. Wejdź w edycję Obiektu B i przypisz mu jako rodzica Obiekt A.
3. Zapisz (baza przyjmuje to bez zająknięcia).  
**Rozwiązanie / workaround:** Wymagane jest dodanie walidacji na poziomie formularza oraz ewentualnie metody `clean()` modelu `TouristObject`, zapobiegającej przypisaniu na rodzica obiektu, który już znajduje się w drzewie potomków. System musi twardo odrzucić taką próbę (zgodnie z Invariantem C-01).  
**Test:** `[brakuje, TODO - test_EC022_cyclic_parent_assignment_raises_validation_error]`

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

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-28 | Dominik / AI Architect | Zarchiwizowanie pierwszych rozwiązań operacyjnych z fazy zasilania danymi i panelu administracyjnego. Otwarte EC-030 dla przyszłej weryfikacji użytkowników. |
| 1.1 | 2026-05-28 | AI Architect | Uzupełnienie pól Test i Reprodukcja, rearanżacja do 4 kategorii, dodanie EC-022 (Cykle klastrów). |
| 1.2 | 2026-05-30 | Dominik / AI Architect | Ujednolicono liczbę prób (Retry) na 15 prób zgodnie z wdrożonym logiem w kodzie (maksymalny czas oczekiwania). |
|
