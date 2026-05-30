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

### `Ascent` (Wejście)
**Opis:** Abstrakcja reprezentująca log z wejścia turysty. Przekazywana do Czystej Domeny.

| Atrybut | Typ domenowy | Wymagany | Opis |
|---------|--------------|----------|------|
| `peak_id` | `int` | Tak | Musi logicznie odpowiadać `TouristObject.id` |
| `ascent_date` | `date` | Tak | Weryfikowana przez domyślne reguły czasowe |
| `activity` | `enum (ActivityType)`| Tak | Sposób zdobycia (HIKING, CYCLING) |

---

## 5. Encje planowane (Faza C - Kontekst Użytkownika)
*Te encje powstaną w kolejnym etapie, by zamknąć pętlę systemu:*
- **`AscentLog`**: Trwały zapis w bazie faktu wejścia turysty na obiekt, poddany przed zapisanem weryfikacji bitemporalnej (T-01).
- **`UserBadgeProgress`**: Tabela mapująca Turystę do konkretnej `BadgeVersion`. Zapisuje datę rozpoczęcia zdobywania i aktualizuje stan (`IN_PROGRESS`, `COMPLETED`) po wyliczeniu go przez `VerifyBadgeUseCase`.

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
