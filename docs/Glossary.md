# Glossary — słownik pojęć domenowych

> **Wersja:** 1.2  
> **Data:** 2026-05-30  
> **Właściciel:** Dominik / AI Architect  
> **Uwaga dla agentów LLM:** Ten słownik definiuje znaczenie pojęć w kontekście TEGO projektu.  
> Jeśli pojęcie istnieje w ogólnym języku programowania, pierwszeństwo ma definicja poniżej. Zabrania się wymyślania synonimów dla pojęć tu zdefiniowanych.

---

## 1. Architektura Odznak (Badge Hierarchy)

### Organizer (Organizator)

| | |
|---|---|
| **Definicja** | Prawny lub fizyczny byt ustanawiający odznaki. Zarządza regulaminami, wzorami książeczek i przyznaje fizyczne blachy. |
| **Alias** | `OrganizerModel`, Oddział PTTK, Klub |
| **Przykład** | Oddział PTTK Ziemi Wałbrzyskiej |
| **NIE jest** | Nie jest prostym, płaskim polem tekstowym ani słownikiem (choices). To pełnoprawny agregat z własnym cyklem życia. |
| **Używany w** | `OrganizerModel`, Relacja `BadgeModel.organizer` |

### Publication Consent (Zgoda na publikację)
| | |
|---|---|
| **Definicja** | Formalne wyrażenie zgody przez Organizatora (np. Klub) na użycie i wyświetlanie na platformie grafik z ich odznakami, regulaminów oraz wzorów książeczek. |
| **Alias** | `has_publication_consent` |
| **Przykład** | Organizator z odznaczonym polem (False) będzie wymagał ukrycia obrazka `BadgeTierModel.badge_image` w UI aplikacji mobilnej. |
| **NIE jest** | Nie jest zgodą na publikację danych turysty (RODO) – dotyczy wyłącznie praw autorskich PTTK. |
| **Używany w** | `OrganizerModel`, Faza C (Filtry widoczności w UI) |

### Badge (Odznaka)

| | |
|---|---|
| **Definicja** | Główny, trwały byt tożsamościowy ustanowiony przez organizatora. Skupia pod sobą historię zmian regulaminu w czasie. |
| **Alias** | `BadgeModel`, Odznaka-matka |
| **Przykład** | "Korona Gór Polski" (jako idea, niezależnie od roku edycji) |
| **NIE jest** | Nie zawiera żadnych regulaminów, wymagań wiekowych ani puli szczytów (te należą do Wersji Odznaki). Nie jest powiązana bezpośrednio z Użytkownikiem. |
| **Używany w** | `BadgeModel`, `ADR-007` |

### Badge Version (Wersja Odznaki / Regulamin)

| | |
|---|---|
| **Definicja** | Pełen, historyczny snapshot regulaminu odznaki obowiązujący od konkretnej daty. Przechowuje dozwoloną Pulę Szczytów oraz Reguły Biznesowe. |
| **Alias** | `BadgeVersionModel`, `BadgeVersionDomain`, Wersja Regulaminu |
| **Przykład** | "KGP v2024" (obowiązująca od 1 stycznia 2024 r.) |
| **NIE jest** | Pula szczytów w aktywnej wersji nie jest mutowalna (ochrona Praw Nabytych). |
| **Używany w** | `BadgeVersionModel`, Silnik weryfikacji w Czystej Domenie |

### Badge Tier (Stopień Odznaki)

| | |
|---|---|
| **Definicja** | Kamień milowy wewnątrz Wersji Regulaminu. Określa próg liczbowy wejść wymaganych do otrzymania fizycznej blachy. Zaliczenie wszystkich stopni oznacza ukończenie danej Wersji Odznaki. |
| **Alias** | `BadgeTierModel`, Stopień (np. Złoty, Brązowy) |
| **Przykład** | Stopień "Srebrna" wymaga `required_peaks_count = 25`. |
| **NIE jest** | Nie posiada własnej puli szczytów (korzysta z puli zdefiniowanej w Wersji). Nie jest osobnym regulaminem. |
| **Używany w** | `BadgeTierModel`, Silnik Postępu (Faza C) |

### Badge Rule (Reguła Biznesowa)

| | |
|---|---|
| **Definicja** | Abstrakcyjna strategia (algorytm) weryfikująca poprawność wejść turysty według specyficznego warunku. W infrastrukturze przechowywana jako JSONB. |
| **Alias** | `BadgeRule`, Reguła JSON, Wzorzec Strategii |
| **Przykład** | `MinAgeRule(8)`, `TimeLimitRule(3)` |
| **NIE jest** | Nie jest regułą sprawdzaną podczas odczytu/wyświetlania map. Zostaje odpalana tylko podczas transakcyjnej weryfikacji logu. |
| **Używany w** | `domain/rules/badge_rules.py`, `RULES_SCHEMA` |

### Object Pool (Pula Obiektów)

| | |
|---|---|
| **Definicja** | Zamknięty zbiór identyfikatorów (`ID`) obiektów turystycznych, z którego turysta może wybierać cele do zdobycia w ramach danej Wersji Odznaki. |
| **Alias** | `pool_peaks`, Lista szczytów odznaki |
| **Przykład** | Zbiór 28 ID szczytów dla odznaki KGP. |
| **NIE jest** | W kontekście weryfikacji domenowej domena operuje na strukturze `frozenset[int]`, nie zna pełnych obiektów modeli Django ani ich geografii. |
| **Używany w** | `BadgeVersionModel.pool_peaks`, `BadgeVersionDomain.pool_peak_ids`, `ADR-009` |

### Grandfather Clause (Prawa Nabyte)

| | |
|---|---|
| **Definicja** | Gwarancja biznesowa, że turysta, który rozpoczął zdobywanie odznaki przed zmianą jej regulaminu, może ukończyć ją na starych zasadach (z użyciem starej Puli Obiektów). |
| **Alias** | Prawa Nabyte |
| **Przykład** | Turysta logujący wejście z 2008 roku ocenia się względem wersji z 2006 r. (36 szczytów), mimo że najnowsza wersja to 2009 r. (28 szczytów). |
| **NIE jest** | Nie jest logiką uwarunkowaną kodem Pythona (brak "IF rocznik = 2006"). Jest realizowana relacyjnie poprzez niezmienne przypisanie turysty do konkretnego ID rekordu w `BadgeVersionModel`. |
| **Używany w** | `UserBadgeProgress` (Faza C), `ADR-007` |

### Archive Pattern (Wzorzec Archiwum)

| | |
|---|---|
| **Definicja** | Rozdzielenie źródeł regulaminu na dwa pola: `official_link` oraz `rules_link` w modelu `BadgeVersion`. Zabezpiecza system przed zjawiskiem tzw. *Link Rot* (wymierania linków na stronach PTTK po latach). |
| **Alias** | Link oficjalny vs Link archiwalny |
| **Przykład** | `official_link` prowadzi do strony oddziału Wałbrzyskiego (która może wygasnąć). `rules_link` prowadzi do nienaruszalnego zbiorczego archiwum regulaminów (np. msw-pttk.org.pl). |
| **NIE jest** | `rules_link` nie jest źródłem prawdy dla odznaki bieżącej, służy wyłącznie dowodzeniu poprawności historycznej przy starych regulaminach. |
| **Używany w** | `BadgeVersionModel.official_link`, `BadgeVersionModel.rules_link` |

---

## 2. Katalog i Geografia (Catalog & Geography)

### Tourist Object (Obiekt Turystyczny)

| | |
|---|---|
| **Definicja** | Złoty Standard dla punktu na mapie. Główna jednostka weryfikowalna przez turystę. |
| **Alias** | `TouristObject`, Szczyt, Schronisko, POI |
| **Przykład** | Szczyt Rysy (ID: 15, Wysokość: 2499) |
| **NIE jest** | Geometria w bazie nie jest wielokątem (obrysem budynku z OSM) – rzutowana jest zawsze na punkt centralny (`centroid`). |
| **Używany w** | `TouristObject`, `FetchOsmDataUseCase` |

### Curated Fields (Twarde Kolumny)

| | |
|---|---|
| **Definicja** | Wyekstrahowane i zatwierdzone oficjalne atrybuty obiektu (Nazwa, Wysokość, Link do Wiki). |
| **Alias** | Złoty Standard, Pola Wyselekcjonowane |
| **Przykład** | `TouristObject.name`, `TouristObject.altitude` |
| **NIE jest** | Nie jest ślepą kopią surowych tagów z OSM. |
| **Używany w** | `TouristObject`, `OsmDataExtractor` |

### Data Lake (Jezioro Danych)

| | |
|---|---|
| **Definicja** | Nienaruszony zrzut wszystkich tagów (słownik JSON) z OpenStreetMap dla danego obiektu, zapisany jako archiwum dla przyszłych ekstrakcji. |
| **Alias** | `osm_raw_tags`, Surowe tagi OSM |
| **Przykład** | `{"historic": "ruins", "name:pl": "Zamek"}` |
| **NIE jest** | Nie jest źródłem danych bezpośrednio wyświetlanych turyście (z wyjątkiem zdenormalizowanego pola `local_names`). |
| **Używany w** | `TouristObject.osm_raw_tags`, `ADR-004` |

### Regional Whitelist (Biała Lista Języków)

| | |
|---|---|
| **Definicja** | Odgórnie zdefiniowana lista kodów językowych (np. `pl`, `cs`, `sk`, `de`), z której korzysta ekstraktor przy wyciąganiu nazw lokalnych z Data Lake. |
| **Alias** | `local_names` |
| **Przykład** | Śnieżka otrzyma `{"de": "Schneekoppe", "cs": "Sněžka"}`, nawet jeśli algorytm PostGIS nie stwierdził fizycznej styczności z granicą państwa. |
| **NIE jest** | Ekstrakcja ta nie polega na logicznej walidacji przestrzennej względem granic państw. |
| **Używany w** | `TouristObject.local_names`, `CalculateObjectRegionsUseCase` |

### Existence Window (Okno Czasowe Istnienia)

| | |
|---|---|
| **Definicja** | Bitemporalny przedział czasu (`existence_start` do `existence_end`), w którym dany obiekt fizycznie istniał/istnieje w świecie rzeczywistym. Semantyka `NULL` (puste) oznacza "istnieje zawsze". |
| **Alias** | Bitemporalność, Cykl Życia Obiektu |
| **Przykład** | Wieża widokowa oddana do użytku w 2020 i spalona w 2023 r. |
| **NIE jest** | Nie ma nic wspólnego z datą obowiązywania odznaki (`valid_from`). |
| **Używany w** | `TouristObject.existence_start / existence_end`, Invariant T-01, `ADR-008` |

### Unified Region Cache (Płaska Tabela Odczytu CQRS)

| | |
|---|---|
| **Definicja** | Zmaterializowany widok przestrzenny. Tabela (M2M) wyliczana asynchronicznie przez Celery, zawierająca informację, w jakich regionach fizykogeograficznych (na każdym szczeblu) leży dany Obiekt Turystyczny. |
| **Alias** | `ObjectRegionCache`, Read Model, CQRS Cache |
| **Przykład** | Rysy -> Państwo: Polska (dystans 0.0m) |
| **NIE jest** | Nie jest używana w logice weryfikacji wewnątrz Czystej Domeny. Służy wyłącznie do ultraszybkiego filtrowania w UI Admina. |
| **Używany w** | `ObjectRegionCache`, `CalculateObjectRegionsUseCase`, `ADR-005` |

### Tourist Region (Region Turystyczny)

| | |
|---|---|
| **Definicja** | Sztuczny byt geograficzny na potrzeby PTTK (np. "Sudety", "Beskidy"), składający się ze sklejonych wielokątów mniejszych jednostek (np. mezoregionów). |
| **Alias** | `TouristRegionModel` |
| **Przykład** | Region "Tatry Polskie" |
| **NIE jest** | Z punktu widzenia CQRS staje się po wyliczeniu kolejną równorzędną warstwą w `ObjectRegionCache`. |
| **Używany w** | `TouristRegionModel`, `BuildTouristRegionGeometryUseCase` |

### Cluster / Parent Object (Klaster / Gniazdo)

| | |
|---|---|
| **Definicja** | Grupa bardzo blisko leżących obiektów powiązanych jednoznacznie relacją rodzic-dziecko. |
| **Alias** | `parent_object`, Obiekt Nadrzędny |
| **Przykład** | Szczyt Skrzyczne (Rodzic) skupiający pod sobą Wieżę i Schronisko (Dzieci). |
| **NIE jest** | Tabela nie dopuszcza cykli w grafie powiązań (Invariant C-01). |
| **Używany w** | `TouristObject.parent_object`, Radar Bliskości, UX Mapy (Decluttering) |

---

## 3. Procesy Asynchroniczne i Infrastruktura (Data Ops)

### Personal Kanban (Osobisty Tracker Logistyki)

| | |
|---|---|
| **Definicja** | Wizualna maszyna stanów w UI Turysty służąca mu wyłącznie jako "przypominajka" o wysłanych książeczkach pocztą (`WAITING_FOR_VERIFICATION`, `ALBUM`). |
| **Alias** | Tracker, Logistyka |
| **NIE jest** | System NIE komunikuje się z organizatorami PTTK. Odznaka oznaczona jako "w weryfikacji" nie jest widoczna dla żadnego urzędnika. |

### Ascent (Wejście / Log wejścia)

| | |
|---|---|
| **Definicja** | Historyczny fakt obycia wycieczki na obiekt przez turystę, zawierający **wyłącznie datę**. Podlega ewaluacji przez Czystą Domenę. Może posiadać wgraną pamiątkową fotografię. |
| **NIE jest** | Z systemu całkowicie usunięto sprawdzanie "Typu aktywności" (Pieszo/Rower) w ramach redukcji długu UX (YAGNI). |

### Night Watchman (Nocny Stróż OSM)

| | |
|---|---|
| **Definicja** | Cykliczne zadanie (Celery Beat), które pobiera małe partie najdawniej sprawdzanych obiektów z OSM, weryfikuje ich wersję, uaktualnia Data Lake i tworzy propozycje ewentualnych zmian. |
| **Alias** | `run_osm_night_watchman_task`, Re-hydrator |
| **Przykład** | - |
| **NIE jest** | Nie nadpisuje Twardych Kolumn (Złotego Standardu) w bazie bez autoryzacji Administratora. |
| **Używany w** | `application/use_cases/fetch_osm_data.py` |

### Ghost Node (Martwy Węzeł / Duch)

| | |
|---|---|
| **Definicja** | Obiekt turystyczny, który zniknął z OpenStreetMap (np. zniszczona wieża, usunięta przez geodetów), co system wyłapuje przy zapytaniach grupowych (Bulk API) jako błąd ilości zwróconych wyników. |
| **Alias** | Duch, Usunięty Węzeł OSM |
| **Przykład** | Zapytanie do OSM o 100 ID-ków zwraca 99 węzłów. Brakujący jest oznaczany jako Duch. |
| **NIE jest** | Nie jest automatycznie usuwany poleceniem `DELETE` z naszej bazy danych (ochrona historii). Otrzymuje propozycję do statusu `is_active=False`. |
| **Używany w** | `RunOsmNightWatchmanUseCase`, `EDGE_CASES.md` (EC-002) |

### Review Queue / Inbox (Skrzynka Konfliktów / Odbiorcza)

| | |
|---|---|
| **Definicja** | Magazyn w panelu Administratora, do którego system zrzuca wykryte rozbieżności z OSM (np. zmiana wysokości szczytu) lub kandydatów do klastrowania z Radaru. |
| **Alias** | `OsmSyncConflict`, `ProximityCandidate`, Inbox |
| **Przykład** | Ostrzeżenie w systemie: "Nowa wysokość z OSM: 1200m (obecnie w bazie 1190m)". |
| **NIE jest** | Pojawienie się konfliktu nie jest błędem (awarią) aplikacji. To pożądany mechanizm zderzenia danych zewnętrznych z ludzką decyzyjnością. |
| **Używany w** | `OsmSyncConflictAdmin`, `ProximityCandidateAdmin` |

### Proximity Scanner (Radar Bliskości)

| | |
|---|---|
| **Definicja** | Asynchroniczny algorytm PostGIS poszukujący niepołączonych obiektów leżących w odległości mniejszej niż 150 metrów, by wygenerować Kandydatów do Klastrów. |
| **Alias** | `scan_proximity_candidates_task`, Skaner Przestrzenny |
| **Przykład** | - |
| **NIE jest** | Nie modyfikuje struktury `parent_object` samodzielnie – wypełnia jedynie `Review Queue`. |
| **Używany w** | `application/use_cases/scan_proximity_candidates.py`, `ADR-006` |

### Data Override (Ręczne Nadpisanie)

| | |
|---|---|
| **Definicja** | Żelazna reguła: jeśli Administrator wypełni pole ręcznie w panelu Django, zautomatyzowane skrypty z OSM nigdy nie nadpisują tego pola (uznając ręczny wpis za priorytetowy). |
| **Alias** | Data Override |
| **Przykład** | Ręczne wpisanie linku do Wikipedii dla skałki, której nie ma w OSM. |
| **NIE jest** | - |
| **Używany w** | Invariant D-02, `TouristObjectAdminForm`, `OsmRepository` |

### Type Mapping Inbox (Słownik Mapowań OSM)

| | |
|---|---|
| **Definicja** | Mechanizm filtrujący (Whitelist) zapobiegający "śmietnikowi tagów". Wykrywa nowe, nieznane tagi klasyfikujące z OSM (np. `tower:type=observation`) i umieszcza je w kolejce do ręcznego zmapowania przez Administratora na znormalizowany typ obiektu PTTK (np. "Wieża widokowa"). |
| **Alias** | `OsmTypeMapping`, Słownik Typów |
| **Przykład** | Reguła: Jeśli OSM ma `natural=peak`, system z automatu ustawia typ na "Szczyt". |
| **NIE jest** | Nie jest skrzynką konfliktów danych (`OsmSyncConflict`), która rozwiązuje konflikty wartości (np. różnica wysokości). Słownik Mapowań rozwiązuje konflikty *schematu* (klasyfikacji). |
| **Używany w** | `OsmTypeMapping`, `OsmDataExtractor.determine_type()` |

---

## 4. Użytkownik i Weryfikacja (Faza C - User Context)

### Ascent (Wejście / Log wejścia)

| | |
|---|---|
| **Definicja** | Historyczny fakt obycia wycieczki na obiekt przez turystę, zawierający datę i typ aktywności (pieszo, narty). Podlega ewaluacji przez Czystą Domenę. |
| **Alias** | `AscentLog` |
| **Przykład** | Jan Kowalski, Babia Góra, 2024-08-15, HIKING |
| **NIE jest** | Samo logowanie wejścia nie jest równoznaczne ze zdobyciem odznaki, ani nie jest jeszcze weryfikacją fizyczną PTTK. |
| **Używany w** | `Ascent` (Value Object), `AscentLog`, `VerifyBadgeUseCase` |

### User Badge Progress (Postęp)

| | |
|---|---|
| **Definicja** | Zapis stanu turysty przypisanego do konkretnej Wersji Odznaki. Wyliczany na żywo przez Czystą Domenę. Może mieć stan: `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`. |
| **Alias** | Progress Bar, Postęp Turysty |
| **Przykład** | - |
| **NIE jest** | Turysta jest przypisany do wersji (regulaminu), nigdy do głównej "Odznaki-matki". |
| **Używany w** | `UserBadgeProgress` |

### Verification Cycle (Cykl Weryfikacji / Edycja)

| | |
|---|---|
| **Definicja** | Mechanizm pozwalający turyście na wielokrotne zdobywanie tej samej odznaki (tzw. "Pętle Prestiżu"). Wymaga konsumpcji (zużycia) wcześniejszych wejść, tak aby nie wliczały się one do nowej edycji. |
| **Alias** | Cykl, Edycja, Pętla Prestiżu |
| **Przykład** | Zdobycie Złotej Korony Gór Polski po raz drugi (Cykl 2). |
| **NIE jest** | Nie jest to tożsame z nową "Wersją Regulaminu" (turysta powtarza tę samą wersję odznaki na tych samych zasadach). |
| **Używany w** | Faza C, `EDGE_CASES.md` (EC-030) |

### Dynamic POI Score (Potencjał Obiektu)

| | |
|---|---|
| **Definicja** | Całkowitoliczbowa wartość punktowa (`100/n`) określająca opłacalność zdobycia danego obiektu turystycznego dla konkretnego turysty w danym dniu. `100 pkt` jest ekwiwalentem domknięcia jednej odznaki. |
| **Alias** | Ranking, Punkty, Opłacalność |
| **Przykład** | Turysta potrzebuje jeszcze 2 szczytów do KGP i 4 do Korony Tatr. Szczyt należący do obu tych odznak jest warty `50 + 25 = 75` punktów. |
| **NIE jest** | Nie jest wartością stałą. Wartość tego samego szczytu może wynieść 0 punktów w lecie, jeśli jedna z odznak wymaga zdobycia go zimą. Zmienia się wraz z kalendarzem i postępem turysty. |
| **Używany w** | `ADR-015`, US-C16, `BadgeEligibilityService` |

### ALBUM (Stan Logistyczny)

| | |
|---|---|
| **Definicja** | Terminalny (ostateczny) status w osobistej maszynie stanów śledzenia przesyłki. Oznacza, że turysta fizycznie otrzymał blachę i umieścił ją w swoich prywatnych zbiorach. |
| **Alias** | Zakończone, Dostarczone, Odebrane |
| **NIE jest** | System NIE komunikuje się z PTTK. Osiągnięcie statusu ALBUM to wyłącznie potwierdzenie, że listonosz dostarczył turyście przesyłkę. |

---

## 5. Wzorce Architektoniczne (Architecture Patterns)

Ta sekcja mapuje uniwersalne wzorce inżynierii oprogramowania na ich **konkretną implementację** w tym projekcie. Chroni to system przed wprowadzaniem obcych frameworków przez agentów LLM.

### Strategy Pattern (Wzorzec Strategii)

| | |
|---|---|
| **Definicja** | Wzorzec behawioralny pozwalający na definiowanie rodziny algorytmów (reguł) i ich wymienną ewaluację w locie. W naszym systemie polega to na odtwarzaniu klas dziedziczących po `BadgeRule` z konfiguracji JSONB w bazie danych. |
| **Używany w** | `domain/rules/`, `ADR-003` |

### Factory Registry (Słownik Fabryk / Rejestr)

| | |
|---|---|
| **Definicja** | Sztywny, wbudowany w kod słownik mapujący nazwę tekstową reguły z JSON-a (np. `"MinAgeRule"`) na bezpieczną, sprawdzającą typy funkcję budującą dany obiekt domenowy. |
| **Alias** | `RULE_BUILDERS` |
| **Cel** | Pełni funkcję bariery `Fail-Fast` (Invariant R-02). Chroni Czystą Domenę przed złośliwym lub uszkodzonym JSON-em z bazy danych (Insecure Deserialization). |
| **Używany w** | `infrastructure/adapters/persistence/django_badge_repo.py` |

### Application Service vs Domain Service (Usługa Aplikacyjna)

| | |
|---|---|
| **Definicja** | W tym projekcie, jeśli usługa musi weryfikować "aktualny czas" (wymaga wstrzyknięcia `ClockPort`) lub pobierać dane z bazy, jest **Usługą Aplikacyjną** (żyje w `application/`). Domena (Czysty Python) pozostaje bezstanowa i operuje tylko na tym, co dostanie w parametrach. |
| **Przykład** | `BadgeEligibilityService` to usługa aplikacyjna (bo sprawdza dzisiejszą datę dla mapy), a `VerifyBadgeUseCase` to orkiestrator. |
| **Używany w** | `application/services/`, `ADR-010`, Invariant T-02 |

### Archive Pattern (Wzorzec Archiwum)

| | |
|---|---|
| **Definicja** | Rozdzielenie źródeł regulaminu w modelu na dwa niezależne adresy URL w celu ochrony przed tzw. *Link Rot* (wymieraniem linków). |
| **Implementacja** | `official_link` prowadzi do strony oddziału PTTK (która może wygasnąć). `rules_link` prowadzi do nienaruszalnego archiwum chroniącego prawowitość starych Wersji Odznak. |
| **Używany w** | `BadgeVersionModel` |

### Temporal Modeling (Modelowanie Czasowe)

| | |
|---|---|
| **Definicja** | Zbiorcze określenie na nasze podejście do obsługi upływającego czasu. W tym projekcie dzieli się na dwa konkretne wzorce: **Bitemporalność** (fizyczny czas istnienia obiektów w terenie - `existence_start`/`end`) oraz **Prawa Nabyte** (izolacja wymagań odznak za pomocą relacji do zamrożonej w czasie `BadgeVersionModel`). |
| **Używany w** | `ADR-007`, `ADR-008`, `AscentLog` |

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-28 | Dominik / AI Architect | Zdefiniowanie fundamentalnych pojęć po zakończeniu Faz A i B. |
| 1.1 | 2026-05-28 | AI Architect | Ujednolicenie nagłówków do formatu bilingwalnego `Eng (Pl)`. Dodanie 5 pojęć krytycznych dla infrastruktury i Praw Nabytych (Existence Window, Ghost Node, Grandfather Clause, Organizer, Verification Cycle). |
| 1.2 | 2026-05-30 | Dominik / AI Architect | Dodanie `Publication Consent` (Zgody na publikację). |
