# Invariants — niezmienniki systemu

> **Wersja:** 2.0  
> **Data:** 2026-06-01  
> **Właściciel:** Dominik / AI Architect  
>
> Każdy invariant to reguła biznesowa i architektoniczna, której naruszenie oznacza fatalny błąd systemu. Należy je bezwzględnie egzekwować podczas pisania Use Case'ów, modyfikacji bazy danych i projektowania Frontendu.

---

## Poziomy krytyczności

| Symbol | Znaczenie |
|--------|-----------|
| 🔴 KRYTYCZNY | Naruszenie powoduje uszkodzenie danych, utratę historii, wyciek informacji lub pad serwera (np. OOM). |
| 🟠 WYSOKI | Naruszenie powoduje błędne zachowanie widoczne dla użytkownika lub znaczący spadek wydajności. |
| 🟡 ŚREDNI | Naruszenie powoduje degradację funkcji w tle (np. zatkanie kolejki Celery). |

---

## Grupa T — Czas i Bitemporalność

### T-01 — Cykl życia obiektu (Bitemporality) 🔴 KRYTYCZNY
**Treść:** Zalogowanie wejścia na obiekt (`Ascent`) w dniu *X* jest niemożliwe logicznie i fizycznie, jeśli obiekt w tym czasie nie istniał.  
Semantyka `NULL` (puste = dowolne):
- `existence_start = NULL` → obiekt istnieje od zawsze
- `existence_end = NULL` → obiekt istnieje bezterminowo  
**Uzasadnienie:** Chroni historię. Zburzenie schroniska w 2023 unieważnia wejścia z 2024, ale chroni prawa zdobywców z 2010 r.
**Gdzie egzekwować:** 
- Use Case: `application/use_cases/verify_badge.py` (Krok 0 przed ewaluacją domeny).

### T-02 — Determinizm Czasu (ClockPort) 🔴 KRYTYCZNY
**Treść:** Kod w `domain/` oraz `application/` NIGDY nie może wywoływać `datetime.now()` ani `timezone.now()`.
**Uzasadnienie:** Testowanie reguł zależnych od czasu (np. `TimeLimitRule`) wymaga "zamrożenia" czasu. "Teraz" musi być dostarczone z zewnątrz.
**Gdzie egzekwować:** 
- Linter: `audit_contracts.py` oraz `ruff banned-api`.
- Testy: Wstrzykiwanie `FakeClock`.

### T-03 — Zakaz Logowania Przyszłości (Future-Proofing) 🔴 KRYTYCZNY
**Treść:** Turysta nie może zarejestrować wejścia (`AscentLog`) na obiekt z datą późniejszą niż dzisiejsza (czas lokalny turysty lub serwera).
**Uzasadnienie:** Uniemożliwienie oszustw "na zapas" oraz zabezpieczenie przed wpadaniem logów w luki bitemporalne (T-01), których stan na przyszłość mógłby zostać zmieniony przez administratora.
**Gdzie egzekwować:** 
- Use Case: `LogAscentUseCase` z użyciem `ClockPort.now().date()`.

---

## Grupa R — Reguły i Architektura Domeny

### R-01 — Matematyka Zbiorów zamiast GIS (Pool-based Set Verification) 🔴 KRYTYCZNY
**Treść:** Czysta Domena weryfikująca odznaki **nie wie** co to współrzędne, PostGIS, czy `ST_DWithin`. Weryfikacja to operacje algebry zbiorów na `frozenset[int]`.
**Uzasadnienie:** Gwarantuje błyskawiczną weryfikację $O(1) / O(N)$ i całkowicie oddziela proces decyzyjny PTTK od analityki przestrzennej (ADR-009).
**Gdzie egzekwować:** 
- Linter: `import-linter` (zakaz `django.contrib.gis` w domenie).

### R-02 — Fail-Fast dla Fabryk Reguł (Hydracja z JSONB) 🟠 WYSOKI
**Treść:** Jeśli adapter wczytujący reguły z JSONB napotka nieznaną regułę lub brak parametru (np. puste `min_age`), musi twardo rzucić `ValueError`.
**Uzasadnienie:** Ciche pominięcie błędu skutkowałoby np. przyznaniem odznaki "Tylko dla dorosłych" ośmiolatkowi.
**Gdzie egzekwować:** 
- Baza: `infrastructure/adapters/persistence/django_badge_repo.py` (`RULE_BUILDERS`).

### R-03 — Wildcard Rules opierają się na wstrzykniętych ID, nie na bazie 🟠 WYSOKI
**Treść:** Reguły otwarte geograficznie (np. wymagające X szczytów z Beskidu bez precyzowania puli) muszą dokonywać oceny na podstawie wstępnie wyliczonego zbioru `region_ids` wstrzykniętego przez obiekt `AscentContextDTO`. Domena **nigdy nie odpytuje** infrastruktury.
**Uzasadnienie:** Pozwala obsłużyć elastyczne regulaminy (ADR-012) bez łamania czystości domeny (R-01).

---

## Grupa D — Dane i Integralność

### D-01 — Unikalność kolejności stopni (Tiers) 🔴 KRYTYCZNY
**Treść:** W ramach jednej Wersji Regulaminu, pole `order` (Kolejność zdobywania) musi być bezwzględnie unikalne.
**Uzasadnienie:** Dwa stopnie z `order=1` zniszczą algorytm wyliczania Progress Baru u Turysty.
**Gdzie egzekwować:** 
- Baza: `UniqueConstraint` w `BadgeTierModel`.
- Formularze: `BadgeTierInlineFormSet`.

### D-02 — Złoty Standard ponad Automatyką (Data Overrides) 🟠 WYSOKI
**Treść:** Ekstraktor OSM zasilający bazę z Data Lake nigdy nie nadpisuje Twardych Kolumn (np. `name`, `altitude`), jeśli Administrator wpisał tam własną wartość.
**Uzasadnienie:** Ręczna edycja oznacza ingerencję autorytatywną (Human-in-the-loop). Nadpisanie to utrata danych.
**Gdzie egzekwować:** 
- Adapter: `OsmRepository.update_object_from_osm()`.

### D-03 — Prawo do publikacji wizerunku (Publication Consent) 🟠 WYSOKI
**Treść:** System nie ma prawa przesyłać na zewnątrz (przez API lub HTML) ścieżek do grafik odznak klubowych (`club_badge_image`) oraz oficjalnych książeczek PTTK, dla których powiązany Organizator posiada ustawioną flagę `has_publication_consent = False`.
**Uzasadnienie:** Ochrona praw autorskich PTTK i zabezpieczenie przed roszczeniami w przypadku braku formalnej zgody oddziału.
**Gdzie egzekwować:** 
- Serializatory DTO API (Faza C).
- Widoki pobierania mediów w Django.

### D-04 — Idempotentność Zapisów Turysty (Upsert) 🟠 WYSOKI
**Treść:** Zapisywanie logów wejść (`AscentLog`) i innych akcji turysty musi być idempotentne. Ponowna próba zapisu wejścia na ten sam `peak_id` przez tego samego `user_id` w tej samej dacie (`ascent_date`) nie może tworzyć zduplikowanego rekordu w bazie.
**Uzasadnienie:** Użytkownicy aplikacji mobilnych (ze względu na złą jakość sieci w górach) mogą generować zduplikowane żądania HTTP (tzw. Double Submit). Baza danych lub Use Case muszą cicho połknąć duplikat (np. ignorując go) lub odrzucić go błędem `409 Conflict`, zapobiegając puchnięciu tabel.
**Gdzie egzekwować:** 
- Baza: `UniqueConstraint` w modelu `AscentLog`.
- Adapter: Flaga `ignore_conflicts=True` w bulk_create / get_or_create.

---

## Grupa S — Stany, Cykle Życia i Logistyka (Faza C)

### S-01 — Kierunkowość zasilania z OSM 🟡 ŚREDNI
**Treść:** Status obiektu przechodzi tylko w przód: `DRAFT` → `FETCHING_OSM` → `READY` lub `ERROR`. Cofnięcie ręczne do `DRAFT` jest niedozwolone.
**Uzasadnienie:** Chroni przed wpadnięciem w nieskończoną pętlę Celery.

### S-02 — Ochrona przed "Zatrutą Pigułką" (Poison Pills w API) 🟡 ŚREDNI
**Treść:** Obiekt ze statusem `ERROR` (np. przez trwale uszkodzone ID z OSM) nie może być automatycznie ponawiany przez Nocnego Stróża.
**Uzasadnienie:** Zapobiega to zapychaniu kolejki martwymi żądaniami. Wymaga kliknięcia przez Admina (Akcja *Retry*).

### S-03 — Czysta separacja Logistyki od Domeny (Kanban vs Math) 🔴 KRYTYCZNY
**Treść:** Silnik Domenowy ewaluuje wyłącznie fakty matematyczne: `NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`. Logistyka pocztowa i weryfikacyjna (`WAITING_FOR_SEND`, `ALBUM`) to oddzielny agregat (`VerificationRequest`), który nie ma wstępu do `domain/` (ADR-014).
**Uzasadnienie:** Turysta może zebrać 5 odznak o statusie `COMPLETED` w ciągu roku i wysłać je jako JEDEN wniosek weryfikacyjny w grudniu. Mieszanie tych stanów niszczy UX.
**Gdzie egzekwować:** 
- Linter: `import-linter` (zakaz importu modeli logistycznych do Czystej Domeny).

### S-04 — Niemutowalność Zużytych Wejść (Ascent Locking) 🔴 KRYTYCZNY 
**Treść:** Turysta traci prawo do edycji, ukrywania lub usunięcia rekordu `AscentLog`, jeśli dany rekord został już wykorzystany do spełnienia warunków Wersji Odznaki w cyklu, który osiągnął stan `COMPLETED`. 
**Furtka Korekcyjna (Escalation):** W przypadku wyłapania oszustwa (lub pomyłki) w logach historycznych przez weryfikatora PTTK przy fizycznym sprawdzaniu, weryfikator (poza Czystą Domeną) może usunąć powiązanie lub rekord `AscentLog`. System musi wtedy synchronicznie cofnąć status `UserBadgeProgress` z `COMPLETED` z powrotem na `IN_PROGRESS`, blokując tym samym proces logistyczny.
**Uzasadnienie:** Zapobiega oszustwom typu "Użyj-Zmień-Użyj", gwarantując twardość zdobytych osiągnięć.
**Gdzie egzekwować:**
- Zapytania do bazy na poziomie API: `DELETE /api/v1/ascents/{id}` (Wyrzuca `403 Forbidden` z informacją o zablokowaniu).

---

## Grupa P — Pule, Prawa Nabyte i Prestiż

### P-01 — Niemutowalność Aktywnej Wersji Odznaki 🔴 KRYTYCZNY
**Treść:** Pula szczytów (`pool_peaks`) i zbiór reguł dla danej Wersji Odznaki stają się niemutowalne (Read-Only) w momencie przypisania do nich pierwszego Turysty.
**Uzasadnienie:** Żelazna ochrona Praw Nabytych turysty. Organizator może stworzyć nową wersję z nową datą obowiązywania, ale nigdy nie może zmienić reguł w trakcie gry.
**Gdzie egzekwować:** 
- Walidatory: Django Admin blokujący modyfikację wierszy posiadających podpiętych użytkowników.

### P-02 — Konsumpcja Wejść i Pętle Prestiżu (Ascent Consumption) 🔴 KRYTYCZNY
**Treść:** Gdy Turysta zdobywa odznakę wielokrotnie (Rozpoczyna Cykl 2), żadne z jego wejść użytych do osiągnięcia statusu `COMPLETED` w Cyklu 1 nie może wziąć udziału w ewaluacji Cyklu 2 (ADR-007 / Edge Case 030).
**Uzasadnienie:** Ochrona przed nadużyciami. 100 wejść może zamknąć np. 3 cykle, ale wejście to zasób "zużywalny".
**Gdzie egzekwować:** 
- Use Case: `application/use_cases/verify_badge.py` (Filtrowanie przekazywanych wejść do Domeny względem timestampu zamknięcia poprzedniego cyklu).

---

## Grupa C — Geometria, Klastry i Infrastruktura Mapowa (Faza C/D)

### C-01 — Brak Cykli w Grafie Relacji Rodzic-Dziecko 🔴 KRYTYCZNY
**Treść:** Relacja `parent_object` nie może stworzyć pętli (np. A jest rodzicem B, a B rodzicem A).
**Uzasadnienie:** Naruszenie wywoła rekurencję bez wyjścia i przepełni pamięć (Stack Overflow) w API i Celery.
**Gdzie egzekwować:** 
- Use Case: Logika Auto-Resolve w `Proximity Scanner` oraz walidatory w Django Adminie dla `TouristObject`.

### M-01 — Zasada Hermetyzacji Warstw Mapy (MVT vs GeoJSON) 🔴 KRYTYCZNY
**Treść:** Kafelki Wektorowe (MVT) używane do map muszą być **w 100% zanonimizowane (User-Agnostic)** i statyczne (np. same granice regionów), aby mogły być zakechowane globalnie na CDN. Wszelkie statusy zależne od turysty (np. szczyt zaliczony, zablokowany - `PeakColor`) muszą być przesyłane **osobno** przez lekką, dynamiczną warstwę GeoJSON punktów (ADR-013).
**Uzasadnienie:** Połączenie stanu turysty z ciężką geometrią poligonów spowoduje eksplozję rozmiaru pamięci Cache i zarżnie bazę PostGIS przy próbie dynamicznego docinania wektorów dla każdego usera z osobna.

### M-02 — Zabezpieczenie przed Map Spammingiem (Debounce) 🟠 WYSOKI
**Treść:** Każde zapytanie przestrzenne wywoływane ruchem mapy w aplikacji turysty (np. pobieranie punktów przez BBox) musi być obłożone opóźnieniem rzędu min. `300ms` (Debounce) po zakończeniu ruchu (`moveend`).
**Uzasadnienie:** Ochrona puli połączeń bazy danych. Bez tego frontend "zbombardowałby" backend setkami zapytań SQL podczas jednego, ciągłego machnięcia palcem po ekranie smartfona.
**Gdzie egzekwować:** 
- Frontend: `UI_GUIDELINES.md` i kod JavaScript.

### M-03 — Zakaz edycji ciężkich geometrii w przeglądarce 🔴 KRYTYCZNY
**Treść:** Poligony i MultiPoligony terytoriów (Kraje, Makroregiony, Regiony Turystyczne po `ST_Union`) renderowane w Django Adminie muszą mieć kategorycznie nałożony parametr `modifiable = False` w Leaflecie.
**Uzasadnienie:** Próba renderowania edytora wektorowego dla poligonu posiadającego 25 000 wierzchołków na 100% zablokuje, a następnie wysadzi (Out of Memory) przeglądarkę Administratora. Dopuszczalna jest jedynie edycja prostych punktów (`PointField`).
**Gdzie egzekwować:** 
- Kod: Klasy dziedziczące po `LeafletGeoAdmin`.
