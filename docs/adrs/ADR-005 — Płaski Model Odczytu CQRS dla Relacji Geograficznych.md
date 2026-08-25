# ADR-005 — Płaski Model Odczytu CQRS dla Relacji Geograficznych

> **Status:** `accepted`  
> **Data:** 2026-05-30  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Aplikacja operuje na tysiącach szczytów oraz skomplikowanych poligonach regionów na 7 różnych poziomach hierarchii (Państwo, Województwo, Mezoregion, Region Turystyczny itp.). Administrator PTTK musi mieć możliwość błyskawicznego odfiltrowania bazy obiektów (np. "Pokaż szczyty z Tatr Wysokich"), by przypiąć je do nowo tworzonej odznaki.

Z technicznego punktu widzenia, sprawdzenie przynależności punktu do poligonu (szczególnie z tolerancją na granicy, wymagającą użycia bufora) wymaga wykonania złożonej funkcji przestrzennej w bazie danych (np. `ST_DWithin` na zrzutowanych układach współrzędnych). 

**Pytanie decyzyjne:**  
Czy przynależność terytorialna szczytów powinna być liczona dynamicznie podczas każdego zapytania, czy też relacje te powinny zostać zapisane na stałe w bazie danych w osobnych strukturach (CQRS)?

---

## Debata przed decyzją

**Performance Engineer:** Dynamiczne wywoływanie `ST_DWithin` z rzutowaniem dla 10 000 szczytów na 7 poziomach hierarchii przy każdym wejściu w panel administracyjny "zabije" procesor bazy PostgreSQL. Nawet z indeksami GiST, jest to kosztowana operacja `O(N x M)`. Musimy odseparować zapytania (Odczyt) od logiki wstawiania szczytów (Zapis).

**DBA:** Rozumiem potrzebę cache'owania tych relacji, ale czy mamy dla nich stworzyć 7 osobnych tabel M2M (np. `PeakCountry`, `PeakMesoregion`)? Utrzymanie tak zdenormalizowanego schematu to koszmar migracyjny. Jeśli dodamy 8. poziom ("Parki Narodowe"), musielibyśmy dodać ósmą tabelę M2M.

**Security Engineer:** Nie widzę tu wektorów ataku. Relacje przestrzenne są pochodną fizycznych danych, do których użytkownik końcowy i tak nie ma prawa zapisu.

*Wniosek z debaty:* Konieczne jest zastosowanie wzorca CQRS (Command Query Responsibility Segregation). Relacje muszą być wyliczane z wyprzedzeniem (w tle) i składowane w jednej, zunifikowanej strukturze odczytu (Unified Region Cache), aby uniknąć inflacji tabel (rozwiązanie obaw DBA).

---

## Opcje rozważane

### Opcja A: Dynamiczne obliczenia w locie (On-the-fly GeoQueries)
**Opis:** Przy każdej próbie filtrowania w panelu Django, system dokleja do zapytania klauzule przestrzenne. Tabela szczytów nie przechowuje żadnej informacji o państwach, w których leżą obiekty.
**Plusy:**
- Absolutne "Single Source of Truth". Jeśli granica kraju w bazie drgnie o 5 metrów, szczyt od razu to odczuje. Zero powielania danych.
**Minusy:**
- Katastrofalna wydajność przy dużej skali.
- Niemożliwość podpięcia wbudowanych, standardowych widgetów i filtrów w Django Admin.

### Opcja B: Mocno relacyjne tabele M2M dla każdego poziomu (Strict Relational)
**Opis:** Dla każdego poziomu (Państwo, Prowincja) istnieje dedykowana tabela łącząca szczyt z obiektem nadrzędnym.
**Plusy:**
- Narzuca ścisłą integralność referencyjną i zabezpieczenia kaskadowe w bazie.
**Minusy:**
- Usztywnienie schematu bazy.
- Aby wyświetlić szczyt w panelu z informacją "Polska, Karpaty, Tatry", ORM musi wykonać potężne, sześciostopniowe zapytanie `JOIN`.

### Opcja C: Asynchroniczne wyliczanie CQRS z jedną Płaską Tabelą (Unified Cache)
**Opis:** Operacje przestrzenne (PostGIS) nie blokują wątku głównego. Są wyzwalane asynchronicznie (Celery) po zapisie szczytu. Zapisują one wyniki do jednej, zdenormalizowanej tabeli `ObjectRegionCache` (Read Model), która używa polimorfizmu (poziom regionu zapisany jako tekst, obok ID). Zapytania (Filtry Admina i Mapy) czytają tylko z tej tabeli.

---

## Decyzja

**Wybrano: Opcja C — Asynchroniczne wyliczanie CQRS z jedną Płaską Tabelą (Unified Cache)**

Wydajność operacji analityczno-filtrujących jest absolutnym priorytetem. Podejście CQRS przenosi kosztowne operacje PostGIS na "spokojniejszy" czas (asynchronicznie po zapisaniu szczytu). Użycie jednej uniwersalnej tabeli odczytowej (`ObjectRegionCache`) drastycznie przyspiesza `JOIN`-y (płaska struktura) i uniezależnia system od wprowadzania nowych typów klasyfikacji terytorialnej w przyszłości.

---

## Konsekwencje

### Pozytywne
- **Wydajność Odczytu:** Filtrowanie dziesiątek tysięcy szczytów przez pryzmat regionów w panelu odbywa się w milisekundach.
- Płaska tabela stanowi jedynie zmaterializowany widok (projekcję) relacji, co gwarantuje zachowanie Single Source of Truth dla samej geometrii i definicji granic w systemie.
- **Logiczne Dziedziczenie (Wydajność Zapisu):** Kiedy definiowany jest nowy nadrzędny "Region Turystyczny" (np. sklejany `ST_Union` z mezoregionów), system **nie wykonuje** nowych operacji `ST_DWithin` dla tysięcy szczytów. Wykorzystuje wirtualne dziedziczenie CQRS – w locie mapuje i kopiuje gotowe wiersze `ObjectRegionCache` z obiektów podległych do nowego obiektu nadrzędnego, co redukuje czas aktualizacji systemu z minut do ułamków sekund. To główna zaleta oddzielenia warstwy Odczytu od Źródła Prawdy geometrycznej.
- **Elastyczność Schematu:** Dodanie do bazy np. "Nadleśnictw" nie wymaga żadnych migracji schematu, a jedynie dodania nowej wartości do słownika i wpięcia w asynchroniczny Skaner.

### Negatywne / Ograniczenia
- **Eventual Consistency:** System cierpi na zjawisko spójności ostatecznej. Bezpośrednio po dodaniu szczytu nie pojawi się on w filtrach do czasu ukończenia zadania przez worker Celery (może to potrwać od ułamka sekundy do kilku minut przy potężnym imporcie).
- Konieczność utrzymywania spójności logiki "przeliczacza" CQRS (jeśli granica państwa zostanie edytowana, należy ręcznie wyzwolić ponowne przeliczenie szczytów).

### Działania wymagane (Zrealizowane)
- [x] Stworzenie polimorficznej tabeli `ObjectRegionCache` łączącej ID obiektu, ID regionu i tekstowy typ poziomu.
- [x] Napisanie taska asynchronicznego (`calculate_object_regions_task`) wykorzystującego PostGIS do zasilania tabeli odczytu.
- [x] Usunięcie obliczeń przestrzennych z widoków oraz głównej metody `save()` modelu w Django.

---

## Warunek rewizji

Zrewidować w przypadku implementacji interaktywnych map wielowarstwowych w aplikacji klienckiej, które wymagałyby natychmiastowej spójności (Immediate Consistency) np. weryfikacji pozycji na żywo względem ruchomego promienia. W takim scenariuszu konieczne będzie zastosowanie dynamicznych kafelków MVT odpytujących bezpośrednio twardą geometrię, omijając tabelę Cache.

---

## Relacje (Related)
- **C4 Diagram:** docs/architecture/components.puml
- **ADR-002 — Typy geometryczne PostGIS jako transport infrastrukturalny, nie value objects domeny:** Tabela odczytu nie przechowuje duplikatów samej geometrii, odwołuje się do niej jedynie relacyjnie, pozostawiając źródło prawdy geometrycznej w infrastrukturze.
