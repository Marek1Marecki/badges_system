# ADR-002 — Typy geometryczne PostGIS jako transport infrastrukturalny, nie value objects domeny

> **Status:** `accepted`
> **Data:** 2025-05-26
> **Autor:** —
> **Zastępuje:** —
> **Zastąpiony przez:** —

---

## Kontekst

System przechowuje pozycje geograficzne obiektów turystycznych (szczyty, schroniska)
jako punkty PostGIS (`Point`, SRID 4326) oraz granice regionów jako wielokąty
(`Polygon`, `MultiPolygon`). Zapytania przestrzenne (`ST_DWithin`, `ST_Intersects`,
`ST_UnaryUnion`) wykonywane są przez Django + GeoDjango na bazie PostgreSQL/PostGIS.

Podczas refaktoryzacji tasków Celery do architektury heksagonalnej (priorytet 3)
pojawiło się pytanie: czy typy geometryczne z biblioteki `django.contrib.gis.geos`
(`Point`, `Polygon`, `MultiPolygon`) powinny wchodzić do warstwy domenowej jako
value objects, czy pozostać wyłącznie w warstwie infrastrukturalnej.

Kontrakty projektu (`14-domain-purity.md`) zabraniają importowania zewnętrznych
bibliotek w `domain/`. Typy GEOS są częścią `django.contrib.gis` — biblioteki
zewnętrznej zależnej od binariów systemowych (GDAL, GEOS, PROJ).

**Pytanie decyzyjne:**
Czy `Point`, `Polygon`, `MultiPolygon` z `django.contrib.gis.geos` powinny
wchodzić do `domain/` jako value objects, czy pozostać w `infrastructure/`
jako szczegół implementacyjny adaptera PostGIS?

---

## Debata przed decyzją

**Security Engineer:** Brak krytycznych luk przy żadnej z opcji — geometria nie
jest danymi wrażliwymi. Ryzyko przy Opcji A: binaria GEOS/GDAL rozszerzają
powierzchnię ataku w obrazie produkcyjnym; są już wymagane przez Django, więc
nie jest to nowe ryzyko.

**DBA:** Opcja A wymusiłaby import `django.contrib.gis.geos` w testach jednostkowych
domeny — testy zaczęłyby zależeć od obecności GDAL w środowisku. Na CI bez
PostGIS testy domenowe przestałyby działać. Opcja B utrzymuje testy domenowe
jako czyste testy Pythona bez wymagań systemowych.

**Jak zaadresowano:**
- Ryzyko Security: nieistotne — GDAL jest już w obrazie.
- Ryzyko DBA: kluczowy argument za Opcją B. Testy domenowe muszą działać
  bez PostGIS (np. w lekkim środowisku CI dla `make test`).

---

## Opcje rozważane

### Opcja A: Geometria jako value object w domenie

**Opis:** Tworzymy własne value objects w `domain/value_objects/` opakowujące
typy GEOS — np. `GeoPoint(lat, lon)`, `GeoPolygon(wkt: str)`. Domena operuje
na tych obiektach. Adaptery konwertują między typami GEOS a domenowymi VO.

**Plusy:**
- Domena ma jawnie nazwaną koncepcję pozycji geograficznej — `GeoPoint` jest
  czytelniejszy niż `Any` w sygnaturach metod.
- Możliwa walidacja w konstruktorze VO (np. szerokość geograficzna w zakresie
  −90..90, długość −180..180).
- Testy domenowe nie wymagają PostGIS jeśli VO trzyma dane jako `float`,
  a nie jako obiekt GEOS.

**Minusy:**
- Każda operacja przestrzenna wymaga podwójnej konwersji: VO → GEOS w adapterze,
  wynik GEOS → VO z powrotem. Przy `ST_UnaryUnion` na setkach geometrii
  koszt konwersji jest niezerowy.
- Logika przestrzenna (przecięcia, odległości, projekcje) i tak musi żyć
  w adapterze — domena nie może jej zawierać. VO bez operacji to tylko
  kontener na dane, mało wartości dodanej.
- Ryzyko nieszczelności: jeśli VO trzyma obiekt GEOS wewnętrznie (dla wydajności),
  narusza Domain Purity. Jeśli trzyma WKT/WKB jako string, konwersja jest
  nieunikniona i kosztowna.
- Przy skomplikowanych geometriach (MultiPolygon z setkami pierścieni) serializacja
  do WKT w VO jest pamięciochierna.

---

### Opcja B: Geometria jako `Any` — transport infrastrukturalny (status quo)

**Opis:** Typy GEOS (`Point`, `Polygon`, `MultiPolygon`) nigdy nie wchodzą
do `domain/` ani `application/`. Adaptery (`RegionCacheRepository`,
`OsmRepository`) przyjmują i zwracają geometrię jako `Any` w DTO
(`TouristObjectData.geom`). Use case'y przekazują geometrię przez
adaptery nie wiedząc czym ona jest.

**Plusy:**
- Pełna zgodność z `14-domain-purity.md` — zero importów zewnętrznych w domenie.
- Testy domenowe i use case'ów działają bez PostGIS, GDAL, GEOS.
  `make test` (szybkie testy) nie wymaga infrastruktury bazodanowej.
- Adaptery mają pełną swobodę w wyborze reprezentacji geometrii —
  można zmienić backend z PostGIS na inny bez dotykania domeny.
- Implementacja już istnieje i jest przetestowana (priorytet 3).

**Minusy:**
- `Any` w sygnaturach to utrata informacji typowej — mypy nie weryfikuje
  co przepływa przez `geom`.
- Brak walidacji geometrii na granicy warstw — błędna geometria może
  przejść niezauważona aż do zapytania PostGIS.
- Trudniejsze onboardowanie: nowy developer widzi `geom: Any` i musi
  zajrzeć do adaptera żeby wiedzieć jaki typ tam faktycznie jest.

---

### Opcja C: Własne VO z WKT jako reprezentacją wewnętrzną

**Opis:** `domain/value_objects/geometry.py` zawiera `GeoPoint(lat: float, lon: float)`
i `GeoRegion(wkt: str)`. Adaptery konwertują `Point(lon, lat, srid=4326)` ↔
`GeoPoint`. `wkt` jako string jest przenośny — nie zależy od GEOS.

**Plusy:**
- Walidacja zakresu współrzędnych w konstruktorze VO — domenowa reguła biznesowa.
- Brak zależności od GEOS w domenie — testy domenowe czyste.
- Czytelniejsze sygnatury niż `Any`.

**Minusy:**
- WKT dla złożonych geometrii (granice województw — tysiące punktów)
  to napisy długości megabajtów. Parsowanie WKT przy każdej operacji
  to istotny narzut wydajnościowy.
- Nadal wymaga konwersji w adapterze przy każdym zapytaniu PostGIS.
- `GeoRegion(wkt: str)` nie daje żadnej gwarancji poprawności geometrii
  — WKT może być syntaktycznie poprawny ale geometrycznie nieprawidłowy
  (self-intersecting polygon). Realna walidacja i tak musi przejść przez GEOS.
- Wprowadza złożoność bez proporcjonalnej wartości — problem `Any`
  rozwiązuje się przez dodanie TypeAlias, nie przez nowy VO.

---

## Decyzja

**Wybrano: Opcja B — Geometria jako transport infrastrukturalny**

Domena systemu odznak turystycznych nie operuje na geometriach — nie ma
reguł biznesowych które porównują kształty, obliczają przecięcia lub
mierzą odległości. Całą logikę przestrzenną wykonuje baza danych przez
PostGIS. Domena operuje na `object_id` i `region_id` — identyfikatorach,
nie na kształtach.

W tej sytuacji tworzenie value objects dla geometrii byłoby rozwiązaniem
szukającym problemu. Jedyna konkretna korzyść z Opcji A i C to czytelniejsze
sygnatury — tę korzyść osiągamy taniej przez `TypeAlias` w warstwie
infrastrukturalnej bez naruszania Domain Purity.

Kluczowy argument DBA: testy jednostkowe domeny muszą działać bez PostGIS.
Opcja B to gwarantuje — `make test` nie wymaga GDAL ani połączenia z bazą.

---

## Konsekwencje

### Pozytywne
- Testy domenowe i use case'ów działają bez PostGIS w każdym środowisku.
- Pełna zgodność z `14-domain-purity.md` — domena zależy tylko od stdlib.
- Swoboda zmiany backendu geometrycznego bez dotykania domeny.
- Niższy koszt onboardingu dla developerów bez doświadczenia z GIS.

### Negatywne / Ograniczenia
- `geom: Any` w `TouristObjectData` — mypy nie weryfikuje typu geometrii.
- Brak walidacji geometrii na granicy use case ↔ adapter — błędna geometria
  ujawni się dopiero przy zapytaniu PostGIS z komunikatem błędu z bazy.
- Developer musi zajrzeć do adaptera żeby wiedzieć jaki typ faktycznie
  przepływa przez pole `geom`.

### Działania wymagane
- [x] `TouristObjectData.geom` typowane jako `Any` — zrealizowane w `region_cache_repo.py`
- [x] Use case'y nie importują `django.contrib.gis` — zrealizowane w priorytecie 3
- [ ] Dodać `TypeAlias` w `infrastructure/adapters/persistence/region_cache_repo.py`:
      `GeoPoint = Any  # django.contrib.gis.geos.Point, SRID 4326`
      — poprawia czytelność bez naruszania kontraktów
- [ ] Dodać ten ADR do rejestru w `SYSTEM_PROMPT.md` (sekcja Aktywne ADR-y)

---

## Warunek rewizji

Jeśli w domenie pojawią się reguły biznesowe operujące na geometrii —
np. "szczyt musi leżeć w granicach regionu turystycznego" jako reguła
walidacji odznaki, a nie jako zapytanie do bazy — wtedy rozważyć Opcję C
z `GeoPoint(lat, lon)` jako prostym value object bez zależności od GEOS.

Rewizja wymagana również jeśli backend geometryczny zostanie zmieniony
(np. z PostGIS na SQLite/SpatiaLite na środowisko deweloperskie) —
`Any` jako typ utrudni wtedy odnalezienie wszystkich miejsc konwersji.

---

## Relacje (Related)
- **C4 Diagram:** docs/architecture/components.puml
- **Kontrakty:** `docs/Manifest/14-domain-purity.md` (Import Linter rule: `domain-purity`)
- **Implementacja:** `infrastructure/adapters/persistence/region_cache_repo.py` (Opcja B), `application/use_cases/calculate_object_regions.py` (use case bez importów GIS)

