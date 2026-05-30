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

### ALBUM (Stan Logistyczny)

| | |
|---|---|
| **Definicja** | Terminalny (ostateczny) status w Maszynie Stanów Wniosku Weryfikacyjnego (VerificationRequest). Oznacza, że turysta fizycznie odebrał pocztą zweryfikowaną odznakę (blachę) z rąk PTTK i "wpiął ją do swojego albumu".
| **Alias** | Zakończone, Dostarczone, Odebrane
| **Przykład** | Zmiana z WAITING_FOR_RECEIVING -> ALBUM.
| **NIE jest** | Nie jest statusem weryfikacji wewnątrz Czystej Domeny (gdzie odpowiednikiem ostatecznym jest COMPLETED w UserBadgeProgress). Jest wyłącznie potwierdzeniem fizycznego łańcucha dostaw.
| **Używany w** | VerificationRequest.status, US-C08 (Maszyna Stanów Logistyki)

### Verification Request (Wniosek Weryfikacyjny)

| | |
|---|---|
| **Definicja** | Pakiet (koszyk), do którego turysta wrzuca zdobyte przez siebie stopnie odznak (mające status `COMPLETED`) i zgłasza je systemowo do Przodownika PTTK celem papierowej weryfikacji i otrzymania fizycznej blachy. Działa w oparciu o Tablicę Kanban i maszynę stanów. |
| **Alias** | Wniosek, Logistyka |
| **Przykład** | Zgłoszenie Srebrnej i Złotej odznaki w jednej paczce. |
| **NIE jest** | - |
| **Używany w** | `VerificationRequest`, Kanban Logistyki (Faza C) |

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-28 | Dominik / AI Architect | Zdefiniowanie fundamentalnych pojęć po zakończeniu Faz A i B. |
| 1.1 | 2026-05-28 | AI Architect | Ujednolicenie nagłówków do formatu bilingwalnego `Eng (Pl)`. Dodanie 5 pojęć krytycznych dla infrastruktury i Praw Nabytych (Existence Window, Ghost Node, Grandfather Clause, Organizer, Verification Cycle). |
| 1.2 | 2026-05-30 | Dominik / AI Architect | Dodanie `Publication Consent` (Zgody na publikację). |
|