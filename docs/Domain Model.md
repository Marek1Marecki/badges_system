# Domain Model — model domenowy

> **Wersja:** 1.1  
> **Data:** 2026-05-27  
> **Właściciel:** Dominik / AI Architect  
> **Uwaga dla agentów LLM:** To jest model *domenowy*, nie schemat bazy danych. Opisuje pojęcia biznesowe i ich relacje. Schemat relacyjny znajduje się w warstwie `infrastructure`.  
> **Ważne:** Wszystkie adnotacje `(→ Invariant X-NN)` odnoszą się do twardych reguł opisanych w pliku `INVARIANTS.md`, z którym ten dokument jest nierozerwalnie związany.

---

## 1. Co NIE jest modelem domenowym (Zakaz importu w `domain/`)
Aby chronić czystość architektury (Domain Purity), następujące byty **nie należą** do domeny i nie mogą być tam importowane ani procesowane:
- **`ObjectRegionCache`**: To zmaterializowany widok (CQRS Read Model) infrastruktury. Domena go nie zna.
- **`ProximityCandidate`**: To operacyjna skrzynka odbiorcza (Inbox) dla administratora. Znika po rozpatrzeniu.
- **`OsmSyncConflict`**: Techniczny mechanizm synchronizacji z zewnętrznym API.
- **Obiekty przestrzenne PostGIS**: `Point`, `MultiPolygon` żyją tylko w infrastrukturze. Domena operuje na płaskich `ID`.

---

## 2. Hierarchia Odznak (Kontekst Definicji / Setup Phase)

### `Organizer` (Organizator)
**Opis:** Prawny lub fizyczny byt ustanawiający odznaki (np. Oddział PTTK).

| Atrybut | Typ domenowy | Typ infrastruktury (Django) | Wymagany |
|---------|--------------|-----------------------------|----------|
| `id` | `int` | `BigAutoField` | Tak |
| `name` | `str` | `CharField` | Tak |
| `club_rules_link` | `str` | `URLField` | Nie |
| `has_publication_consent` | `bool` | `BooleanField` | Tak |

### `Badge` (Odznaka)
**Opis:** Trwała tożsamość odznaki turystycznej (np. "Korona Gór Polski"). Nie zawiera regulaminu.

| Atrybut | Typ domenowy | Typ infrastruktury | Wymagany |
|---------|--------------|--------------------|----------|
| `code` | `str` | `CharField` | Tak |
| `name` | `str` | `CharField` | Tak |
| `organizer_id` | `int` | `ForeignKey` | Tak |
| `is_booklet_required`| `bool` | `BooleanField` | Tak |

### `BadgeVersion` (Wersja Regulaminu)
**Opis:** Zestaw reguł obowiązujący w danym oknie czasowym. To ten obiekt ocenia wejścia turysty.

| Atrybut | Typ domenowy | Typ infrastruktury | Wymagany |
|---------|--------------|--------------------|----------|
| `badge_id` | `int` | `ForeignKey` | Tak |
| `version_code` | `str` | `CharField` | Tak |
| `valid_from` | `date` | `DateField` | Tak |
| `rules` | `list[BadgeRule]`| `JSONField` (Hydracja) | Tak (może być pusta) |
| `pool_peaks` | `frozenset[int]` | `ManyToManyField` | Tak (może być pusta) |

**Reguły biznesowe:**
- Czysta Domena weryfikacji ślepo ufa puli `pool_peaks` wygenerowanej na etapie definiowania. Nie dokonuje w locie operacji przestrzennych GIS *(→ Invariant R-01)*.
- W aktywnej (zdobywanej przez użytkowników) wersji, mutacja puli obiektów jest błędem domenowym łamiącym Prawa Nabyte.

### `BadgeTier` (Stopień Odznaki)
**Opis:** Kamień milowy wewnątrz Wersji Regulaminu (np. Brąz, Srebro). Określa progowe warunki zdobycia.

| Atrybut | Typ domenowy | Typ infrastruktury | Wymagany |
|---------|--------------|--------------------|----------|
| `version_id` | `int` | `ForeignKey` | Tak |
| `name` | `str (Enum)` | `CharField` | Tak |
| `order` | `int` | `PositiveIntegerField` | Tak |
| `required_peaks_count`| `int` | `PositiveIntegerField` | Nie |

**Reguły biznesowe:**
- Kolejność stopni (`order`) musi być bezwzględnie unikalna w ramach jednej Wersji Odznaki *(→ Invariant D-01)*.
- **Semantyka NULL:** Jeśli `required_peaks_count` wynosi `None` (lub jest puste), system przyjmuje regułę biznesową: "Wymagane jest zdobycie 100% (wszystkich) obiektów z puli `pool_peaks` zdefiniowanej w Wersji Odznaki".

### Jak działa Algorytm Weryfikacji (Wzorzec Sita i Obserwatora)
> **Zasada implementacyjna (Mental Model dla deweloperów):**  
> 1. **`BadgeVersion` działa jak SITO (Sieve).** 
>    Gdy system weryfikuje turystę, bierze wszystkie jego wejścia z historii i "przesypuje" je przez `BadgeVersion`. Wersja przepuszcza tylko te szczyty, które są w jej `pool_peaks`, a następnie odpala swoje reguły (np. wycina zbiory niespełniające limitu czasu, aktywności czy okna jubileuszowego). Wynikiem pracy Sita jest zbiór **w 100% poprawnych, zwalidowanych wejść**.
> 2. **`BadgeTier` (Stopnie) to bezstanowi OBSERWATORZY (Observers).** 
>    Stopnie nie mają własnych reguł domenowych. One tylko "stoją z boku", patrzą na zbiór, który wyleciał z Sita, i sprawdzają jego długość. 
>    *Przykład:* Sito wypluło 12 ważnych wejść. Stopień Brązowy pyta: *"Czy >= 10?" -> TAK (COMPLETED)*. Stopień Srebrny pyta: *"Czy >= 25?" -> NIE (IN_PROGRESS, 12/25)*. Dzięki temu jeden szczyt zalicza się równocześnie do wszystkich stopni bez konieczności duplikowania wejść.

---

## 3. Katalog Obiektów i Geografia (Infrastructure & CQRS)

### `TouristObject` (Obiekt Turystyczny)
**Opis:** Złoty Standard dla punktu na mapie. Może to być szczyt, schronisko, wieża.

| Atrybut | Typ domenowy | Typ infrastruktury | Wymagany |
|---------|--------------|--------------------|----------|
| `id` | `int` | `BigAutoField` | Tak |
| `name` | `str` | `CharField` | Tak (Override OSM) |
| `type` | `str` | `CharField` | Tak |
| `is_active` | `bool` | `BooleanField` | Tak *(→ Invariant T-01)* |
| `existence_start` | `date` | `DateField` | Nie *(→ Invariant T-01)* |
| `existence_end` | `date` | `DateField` | Nie *(→ Invariant T-01)* |
| `osm_raw_tags` | `dict` | `JSONField` | Nie |
| `status` | `str (Enum)` | `CharField` | Tak |

**Reguły biznesowe:**
- Ręczna edycja pól (np. `name`, `altitude`) przez Administratora (Data Override) ma absolutny priorytet i nie może być nadpisana przez automat OSM *(→ Invariant D-02)*.

---

## 4. Kontekst Weryfikacji (Value Objects Czystej Domeny)

### `AscentContextDTO` (Zhydrowane Wejście)
**Opis:** Abstrakcja logu z wejścia turysty. Przekazywana do Czystej Domeny.
| Atrybut | Typ domenowy | Wymagany | Opis |
|---------|--------------|----------|------|
| `peak_id` | `int` | Tak | Logiczne ID z `TouristObject` |
| `ascent_date` | `date` | Tak | Weryfikowana przez domyślne reguły |
| `region_ids` | `frozenset[int]` | Tak | Zasilone przez CQRS Cache *(→ Invariant R-03)* |
*(Uwaga: Parametr `activity` wycięty jako YAGNI).*

### `VerificationContext` (Kontekst Weryfikacyjny)
**Opis:** Kluczowy obiekt pełniący funkcję "pomostu" pomiędzy bezstanową domeną a stanem konkretnego turysty. Zgodnie z zasadą oddzielenia Wzorca (Blueprint) od Stanu Użytkownika (User State), wstrzykuje on do metody `validate()` reguł biznesowych wszystkie parametry osobiste wymagane do ewaluacji (np. daty z profilu).

| Atrybut (Planowane Faza C)| Typ domenowy | Opis (Uzasadnienie) |
|---------------------------|--------------|---------------------|
| `evaluation_time` | `datetime` | Zastępuje `datetime.now()` gwarantując determinizm w testach (T-02). |
| `tourist_birth_date` | `date` | Zastępuje zaślepkę `TD-02` dla `MinAgeRule` i `MaxAgeRule`. |
| `club_join_dates` | `dict[str, date]` | Zastępuje zaślepkę `TD-02` dla `RequiresClubJoinDateRule`. Mapa kodów klubów na datę zapisu turysty. |

**Reguła biznesowa:** Czysta domena nigdy nie pyta bezpośrednio o te dane (np. nie uderza do bazy `TouristProfile`). Warstwa Aplikacji (Use Case) odpowiada za zbudowanie tego kontekstu przed wywołaniem metody `.evaluate()`.

---

## 5. Kontekst Użytkownika i Logistyka (Faza C - B2C)

### `TouristProfile` (Profil Turysty)
**Opis:** Rozszerzenie konta autoryzacyjnego Django (`User`) o dane domenowe i biznesowe limity (Freemium).

| Atrybut | Typ domenowy | Wymagany | Opis |
|---------|--------------|----------|------|
| `user_id` | `int` | Tak | Relacja ForeignKey (1:N) do konta w systemie Auth. |
| `is_main_profile` | `bool` | Tak | Oznacza główny profil zarządzający subskrypcją. || `nickname`| `str` | Tak | Pseudonim publiczny (Privacy by Default). |
| `preferred_base_map`| `str` | Tak | Ostatnio użyty podkład mapowy na urządzeniu. |
| `birth_date`| `date` | Nie | Używana przez Domenę do ewaluacji `MinAgeRule`. |
| `active_plan`| `str` | Tak | Pakiet subskrypcyjny (np. FREE, PRO). |
| `max_active_badges`| `int` | Tak | Limit weryfikowany przed dołączeniem do odznaki. |
| `club_join_dates` | `dict` | Nie | Daty zapisu do klubów (zasilają `RequiresClubJoinDateRule`). |

### `AscentLog` (Dziennik Wejść)
**Opis:** Niezmienna historia wycieczek. Fakt wejścia powiązany z bitemporalnością obiektu.

| Atrybut | Typ domenowy | Wymagany | Opis |
|---------|--------------|----------|------|
| `profile_id` | `int` | Tak | Turysta (Profil), którego dotyczy ten log wejścia. |
| `peak_id` | `int` | Tak | Fizyczny obiekt turystyczny. |
| `ascent_date` | `date` | Tak | Data faktycznego wejścia. Weryfikowana bitemporalnie *(→ Invariant T-01 i T-03)*. |
| `souvenir_image`| `str` | Nie | Opcjonalna pamiątka, pomijana w Czystej Domenie (YAGNI). |

*(Zabezpieczone unikalnym kluczem (user, peak, date) chroniącym przed podwójnym zapisem → Invariant D-04).*

### `UserBadgeProgress` (Zmaterializowany Postęp i Osobisty Kanban)
**Opis:** Płaska tabela przechowująca snapshot ewaluacji matematycznej oraz stan śledzenia fizycznej książeczki przez turystę.

| Atrybut | Typ domenowy | Wymagany | Opis |
|---------|--------------|----------|------|
| `profile_id` | `int` | Tak | Turysta (Profil), którego dotyczy ta odznaka. |
| `badge_id` | `int` | Tak | Wskazuje odznakę główną (Intencja). |
| `version_id` | `int` | Nie | PUSTE aż do pierwszego logu wejścia. Leniwe zakotwiczenie gwarantujące Prawa Nabyte. |
| `cycle_number` | `int` | Tak | Obsługa Odznak Wielokrotnych (Pętla Prestiżu). |
| `domain_status` | `str (Enum)` | Tak | Stan matematyczny wyliczany w locie (`NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`). |
| `logistic_status`| `str (Enum)` | Nie | Stan w Osobistym Trackerze turysty (np. `WAITING_FOR_SEND`). Manipulowany poza Domeną *(→ Invariant S-03)*. |

---

## 6. Relacje między encjami (Setup Phase)

```
Organizer ──1──────────────N── Badge
Badge ──1──────────────────N── BadgeVersion
BadgeVersion ──1───────────N── BadgeTier
BadgeVersion ──N───────────M── TouristObject (Relacja przez ID: pool_peaks)
TouristObject ──1──────────N── ObjectRegionCache (Zewnętrzny Read Model CQRS)
TouristObject ──1──────────N── TouristObject (Relacja: parent_object / Klastry)

[Kontekst Weryfikacji]
Ascent ───(wskazuje przez peak_id)───► TouristObject
```

## 7. Stany obiektów (TouristObject)
```
          ┌─────────┐
          │  DRAFT  │ (Dodany z OSM ID)
          └────┬────┘
               │ fetch_osm_data_task.delay()
          ┌────▼────────┐
          │ FETCHING_OSM│ (Ponawianie: Linear Backoff)
          └────┬────────┘
               ├────────────────────┐ (Wyczerpanie prób)
               ▼                    ▼
          ┌─────────┐         ┌─────────┐
          │  READY  │         │  ERROR  │ ◄── Wymaga interwencji Admina
          └─────────┘         └─────────┘
               ▲
               │ (Przelicz geografię - CQRS)
```
