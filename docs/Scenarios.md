# Scenarios — scenariusze testowe systemu

> **Wersja:** 1.1  
> **Data:** 2026-05-29  
> **Właściciel:** Dominik / AI Architect  
>
> Scenariusze to "testy mentalne systemu" — narracyjne opisy, jak system powinien zachować się w złożonych, wielokrokowych sytuacjach. Łączą `STORIES.md`, `INVARIANTS.md` i `EDGE_CASES.md` w jeden przepływ End-to-End.  
> **Dla agentów LLM:** Przed implementacją złożonej funkcji przeczytaj powiązany scenariusz. Są one autorytatywne — jeśli Twój kod produkuje inny wynik niż opisany poniżej, to błąd kodu.

---

## Format scenariusza

```markdown
### SCN-NNN — [Tytuł]
**Obszar:** [moduły]
**Powiązane invarianty:** [ID]
**Powiązane edge cases:** [EC-NNN]
**Aktorzy:** [role użytkowników]

**Warunki wstępne:** [stan systemu przed rozpoczęciem]

**Kroki:**
1. [Akcja aktora]
   → Oczekiwany wynik systemu
2. [Kolejna akcja]
   → Oczekiwany wynik

**Stan końcowy:** [jak powinien wyglądać system po scenariuszu]
**Zdarzenia domenowe:** [jakie Domain Events powinny zostać opublikowane]
**Wynik negatywny (jeśli dotyczy):** [co system powinien odrzucić i dlaczego]
```

---

## 1. Scenariusze Infrastruktury i Administracji (Faza A/B)

### SCN-000 — Katalogowanie Obiektów i Radar (Setup Phase Baseline)

**Obszar:** `infrastructure/adapters`, `tasks`, `django_admin`  
**Powiązane invarianty:** D-02 (Data Override), S-01 (Kierunek stanów)  
**Powiązane edge cases:** EC-001 (WAF bypass), EC-010 (Rzutowanie 3857)  
**Aktorzy:** Administrator  

**Warunki wstępne:**
- System nie posiada w bazie żadnego obiektu.

**Kroki:**
1. Administrator dodaje obiekt w panelu, wypełnia `osm_id = node/477984782`, zostawia puste pola nazwy i wysokości, klika "Zapisz".
   → System zapisuje obiekt ze statusem `FETCHING_OSM` (S-01) i wyzwala `fetch_osm_data_task`.
2. Celery Worker wykonuje bezpieczne zapytanie GET, omijając zaporę (EC-001).
   → Ekstraktor zaciąga "Babią Górę", omijając tagi poboczne, i zapisuje Złoty Standard. Jeśli Admin wypełniłby "Wysokość", Ekstraktor by jej nie nadpisał (D-02).
3. Task pobierania wyzwala `calculate_object_regions_task`.
   → PostGIS wykonuje `ST_DWithin(50m)` (względem zrzutowanego układu metrycznego - EC-010).
   → Baza M2M CQRS otrzymuje wyliczone powiązania z państwami i regionami. Status zmienia się na `READY`.
4. Celery Beat w nocy wyzwala `scan_proximity_candidates_task`.
   → PostGIS szuka sąsiadów w promieniu 150m. Znajduje "Babią Górę" oraz np. pobliski murek "Diablak". 
   → Tworzy w skrzynce `ProximityCandidate` (Radar) wpis do decyzji człowieka.

**Stan końcowy:** Baza zawiera autorytatywny, zwalidowany punkt gotowy do użycia w `pool_peaks` odznaki.  
**Zdarzenia domenowe:** `TouristObjectCreated`, `TouristObjectReady`, `ProximityScanCompleted`

---

## 2. Scenariusze weryfikacji domenowej i Użytkownika (Faza C)

### SCN-001 — Zdobycie odznaki z zamkniętym oknem czasowym na starym regulaminie

**Obszar:** `verify_badge`, `domain/rules`  
**Powiązane invarianty:** T-01, P-01  
**Powiązane edge cases:** —  
**Aktorzy:** Turysta  

**Warunki wstępne:**
- System posiada Odznakę X.
- `Wersja A (2015 r.)` (obowiązuje od 2015-01-01) wymaga 10 szczytów, w tym Rysów. Posiada regułę `DateWindowRule(start=2015-01-01, end=2019-12-31)`.
- `Wersja B (2020 r.)` (obowiązuje od 2020-01-01) wymaga 10 szczytów, ale nie ma Rysów w puli. Brak okna czasowego.
- Turysta "Jan" nie rozpoczął jeszcze zdobywania tej odznaki w systemie. Posiada w swoim Dzienniku Wejść (`AscentLog`) wejścia z 2016, 2017 i 2018 roku.

**Kroki:**
1. Turysta klika w UI "Rozpocznij zdobywanie Odznaki X".
   → System analizuje najstarsze logi z jego `AscentLog` dla szczytów należących do sumy pul wszystkich wersji tej odznaki.
   → System identyfikuje, że najstarszy log to rok **2016**.
   → Logika przypisania: `2016` jest $\ge$ `2015-01-01` (Wersja A) i $<$ `2020-01-01` (Wersja B).
   → Na podstawie *Praw Nabytych* automatycznie przypisuje Jana tworząc rekord `UserBadgeProgress` połączony na sztywno z `Wersją A (2015 r.)`. (P-01)
2. Turysta otwiera widok swojego Postępu.
   → System synchronicznie (On-Demand) w locie przelicza wejścia przez matematykę zbiorów.
   → Silnik Domenowy ewaluuje reguły dla Wersji A. Daty logów (2016-2018) mieszczą się w `DateWindowRule`. T-01 (bitemporalność) również przechodzi pomyślnie.
   → System ustawia postęp na `COMPLETED`.

**Stan końcowy:** Rekord `UserBadgeProgress` dla `Wersji A` ma status `COMPLETED`.  
**Wynik negatywny:** Jeśli turysta podałby wejście na Rysy z datą np. 2021 r. (będąc przypisanym do Wersji A), silnik odrzuciłby to wejście ze względu na zamknięte okno jubileuszowe.

---

### SCN-002 — Weryfikacja hierarchii Odznak Zależnych (Drzewko Technologii)

**Obszar:** `verify_badge`, `domain/rules`  
**Powiązane invarianty:** R-01, S-03  
**Powiązane edge cases:** EC-030  
**Aktorzy:** Turysta  

**Warunki wstępne:**
- Turysta zdobywa "Koronę Sudetów" (KS) i "Sudeckiego Włóczykija" (SW).
- "SW" w swoich regułach posiada `PrerequisiteBadgeRule(required_badge_code="KS")`.
- Turysta posiada status `COMPLETED` w domenie dla "KS", ale fizycznie nie ogarnął jeszcze jej wysyłki (nie kupił blachy).

**Kroki:**
1. Turysta otwiera postęp dla "SW", a system synchronicznie odpytuje `VerifyBadgeUseCase`.
   → Domena zgłasza, że pula szczytów dla SW się zgadza.
   → `VerifyBadgeUseCase` sprawdza status domenowy dla odznaki "KS". 
   → Zgodnie z **Inwariantem S-03**, Domena weryfikuje TYLKO status matematyczny (czy "KS" to `COMPLETED`), całkowicie ignorując stan logistyczny (czy "KS" wisi w trackerze turysty jako `WAITING_FOR_SEND` czy `ALBUM`).
   → Warunek `PrerequisiteBadgeRule` jest spełniony. System przyznaje "SW" status `COMPLETED`.

**Stan końcowy:** Osiągnięcia matematyczne nie są blokowane przez papierologię. Turysta ma "SW" gotowego do wysyłki.  

---

### SCN-010 — Wielokrotne Zdobywanie (Pętla Prestiżu i Zużycie Wejść)

**Obszar:** `user_progress`, `verify_badge`  
**Powiązane invarianty:** —  
**Powiązane edge cases:** EC-030  
**Aktorzy:** Turysta  

**Warunki wstępne:**
- Turysta "Anna" ma zweryfikowaną fizycznie odznakę KGP w statusie logistycznym `ALBUM`.
- Rekord postępu Anny ma `cycle_number = 1`. Został domknięty i fizycznie zweryfikowany z datą **2025-05-10**.
- Anna po tej dacie zalogowała 5 nowych wejść na szczyty z KGP.

**Kroki:**
1. Anna klika "Rozpocznij zdobywanie KGP ponownie".
   → System weryfikuje, że Cykl 1 jest zamknięty logistycznie. Tworzy nowy `UserBadgeProgress` z `cycle_number = 2`.
2. Anna otwiera widok Cyklu 2. System synchronicznie przelicza postęp w locie (On-Demand).
   → `VerifyBadgeUseCase` ładuje historię Anny, jednak ZANIM przekaże logi do Czystej Domeny, filtruje je (Zasada Zużycia): Odrzuca z listy wszystkie `AscentLog` z datą $\le$ `2025-05-10`.
   → Do Domeny (Set Math) trafia tylko 5 najnowszych szczytów.
   → Wynik weryfikacji to `IN_PROGRESS` z wynikiem `5/28`.

**Stan końcowy:** Anna ma dwa osobne byty postępu dla KGP. Pierwszy to zablokowana historia, drugi to aktywny pasek startujący od zera.  
**Zdarzenia domenowe:** (Publikacja zdarzenia rozpoczęcia Cyklu 2 do szyny eventowej).

---

### SCN-011 — Osobisty Tracker i Logistyka (Personal Kanban)

**Obszar:** `advance_logistic_status`, `logistics_view`  
**Powiązane invarianty:** S-01 (Kierunek stanów), S-03  
**Powiązane edge cases:** —  
**Aktorzy:** Turysta  

**Warunki wstępne:**
- Turysta posiada odznakę w statusie domenowym `COMPLETED`.
- Odznaka posiada status logistyczny `None` (lub `WAITING_FOR_SEND`).

**Kroki:**
1. Turysta klika przycisk "Wysłano pocztą" w swoim panelu Kanban (Moja Logistyka).
   → UseCase uderza do API (`PATCH`).
   → Maszyna Stanów weryfikuje przejście. Status zmienia się na `WAITING_FOR_VERIFICATION` z dzisiejszą datą. Odznaka przeskakuje do następnej kolumny.
2. Turysta orientuje się, że kliknął złą odznakę.
   → Turysta klika "Cofnij". API przyjmuje z powrotem status `WAITING_FOR_SEND` (Elastyczna maszyna FSM).
3. Turysta po miesiącu otrzymuje blachę pocztą i klika "Wepnij do Albumu".
   → Zmiana stanu na `ALBUM` (stan terminalny).
4. Próba wykonania żądania API przez złośliwego użytkownika (Hacker) próbującego wymusić zmianę logistyki dla odznaki, która ma matematyczny status `IN_PROGRESS`.
   → Wyrzucenie błędu `ConflictError` z komunikatem, że weryfikacja logistyki możliwa jest wyłącznie dla skompletowanych wyzwań.

**Stan końcowy:** Turysta zarządza statusem swoich przesyłek bez wymogu wgrywania dowodów (fizyczna weryfikacja odbywa się poza systemem, np. w oddziale PTTK).

---

### SCN-012 — Onboarding nowego turysty i pakiety Freemium (Google OAuth)

**Obszar:** `OAuth`, `TouristProfile`, `Badge Progress`
**Powiązane User Stories:** US-C01, US-C01b, US-C01c
**Aktorzy:** Nowy Turysta (Niezalogowany)

**Warunki wstępne:**
- System posiada co najmniej 1 aktywną odznakę (np. "Sudecki Włóczykij").
- Użytkownik nie istnieje w bazie danych.

**Kroki (Test E2E dla Playwright):**
1. Turysta klika "Zaloguj przez Google".
   → System uwierzytelnia użytkownika przez OAuth.
   → Sygnał `post_save` automatycznie generuje rekord `TouristProfile`.
   → Turysta otrzymuje pakiet subskrypcyjny `FREE` z limitem np. 3 aktywnych odznak.
2. Turysta zostaje przekierowany na Pulpit (Dashboard).
   → Ekran "Moje Odznaki" jest pusty (Empty State). System zaprasza do "Katalogu Odznak".
3. Turysta przechodzi do Katalogu i klika "Zacznij zdobywać" przy odznace "Sudecki Włóczykij".
   → Use Case weryfikuje limit pakietu `FREE` (0 < 3).
   → Subskrypcja zostaje utworzona.
4. Turysta wraca na Pulpit Mapowy.
   → Silnik 100/n przelicza potencjał WYŁĄCZNIE dla szczytów z "Sudeckiego Włóczykija". Inne szczyty pozostają wyszarzone.

**Wynik negatywny (Limit Freemium):** 
Jeśli turysta spróbuje zasubskrybować 4. odznakę na pakiecie `FREE`, interfejs HTMX przechwyci błąd `400 Bad Request` i wyświetli na ekranie Toast z komunikatem z Middleware RFC7807: *"Przekroczono limit pakietu FREE"*.

---

### SCN-013 — Logowanie wejścia a limity Freemium i Bitemporalność

**Obszar:** `log_ascent`, `TouristProfile`  
**Powiązane invarianty:** T-01, T-03, D-04  
**Powiązane User Stories:** US-C01c, US-C03  
**Aktorzy:** Turysta (Darmowe Konto)  

**Warunki wstępne:**
- Obiekt X ma `existence_start = 2020-01-01`.
- Turysta posiada pakiet `FREE` (limit 1 zdjęcia per wejście).

**Kroki i Test Scenarios (E2E / Integration):**
1. Turysta próbuje zalogować wejście na Obiekt X z datą `2019-12-31`.
   → *Negative Case:* System odrzuca żądanie (`422 Unprocessable Entity`) z powodu złamania bitemporalności (T-01).
2. Turysta próbuje zalogować wejście na Obiekt X z datą jutrzejszą.
   → *Negative Case:* System odrzuca żądanie (`422 Unprocessable Entity`) z powodu wejścia w przyszłości (T-03).
3. Turysta loguje wejście z datą dzisiejszą, załączając 2 zdjęcia.
   → *Edge Case:* System odrzuca żądanie (`400 Bad Request`), informując o przekroczeniu limitu `max_photos_per_ascent` dla pakietu FREE.
4. Turysta poprawia formularz (dzisiejsza data, 0 zdjęć) i wysyła.
   → *Happy Path:* System zwraca `201 Created` z `ascent_id`.
5. Turysta ponownie klika "Wyślij" z tymi samymi danymi (podwójne kliknięcie myszką).
   → *Idempotency Case:* System przechwytuje konflikt (D-04) i zwraca `409 Conflict`, nie duplikując wpisu w bazie.

---

### SCN-014 — Automatyczna Weryfikacja Postępu (On-Demand)

**Obszar:** `verify_badge`  
**Powiązane invarianty:** R-01, P-02  
**Aktorzy:** Turysta  

**Warunki wstępne:**
- Turysta zasubskrybował odznakę z wymogiem zdobycia 3 obiektów z puli. Wersja odznaki jest zakotwiczona.
- Turysta zalogował już 2 poprawne wejścia na szczyty z tej puli.
- Status domenowy odznaki to `IN_PROGRESS`.

**Kroki i Test Scenarios (E2E / Integration):**
1. Turysta na mapie klika 3. obiekt z puli i dodaje log wejścia (Dziś).
   → Żądanie logowania zwraca sukces.
   → UI Turysty (HTMX) odświeża komponent postępu, wykonując `GET /progress/`.
2. Odbiór żądania `GET /progress/` przez system.
   → `VerifyBadgeUseCase` pobiera z bazy profil, zakotwiczoną wersję i **niezużyte** logi wejść.
   → Konstruowany jest `VerificationContext` ze wstrzykniętym `ClockPort.now()`.
   → Czysta Domena krzyżuje 3 wejścia turysty z pulą odznaki (Set Math). Próg (3/3) zostaje osiągnięty.
3. System aktualizuje stan bazy.
   → Status w `UserBadgeProgress` zmienia się z `IN_PROGRESS` na `COMPLETED`.
4. Odpowiedź dociera do UI.
   → Turysta widzi na ekranie 100% na pasku postępu oraz odblokowany Osobisty Kanban (Logistykę).

---

### SCN-015 — Grupowanie Celów w Klastry (Wizualizacja Rankingu)

**Obszar:** `poi_ranking_view`, `Ranking`  
**Powiązane invarianty:** C-01 (Płaska Gwiazda)  
**Powiązane ADR:** ADR-006, ADR-015  
**Aktorzy:** Turysta  

**Warunki wstępne:**
- System posiada Klaster: "Skrzyczne" (Rodzic) oraz "Schronisko Skrzyczne" (Dziecko).
- Silnik 100/n zbuforował w Redis, że Szczyt jest wart 10 pkt, a Schronisko 5 pkt.

**Kroki (Test Scenarios E2E):**
1. Turysta wchodzi na podstronę `/ranking/` (Ranking Celów).
   → *Happy Path:* System identyfikuje, że Szczyt i Schronisko mają wspólny `anchor_id`.
   → Tabela renderuje główny wiersz "📦 Klaster: Skrzyczne (Okolice)" z widocznym zyskiem całkowitym `+15 pkt`.
   → Bezpośrednio pod nagłówkiem renderowane są dwa wiersze: Szczyt (+10 pkt) oraz Schronisko (+5 pkt) opatrzone wcięciem i znakiem podrzędności (↳).
2. Sytuacja brzegowa: Szczyt wypadł z punktacji (0 pkt, np. został zdobyty), ale Schronisko nadal daje 5 pkt.
   → *Edge Case:* Tabela nadal renderuje nagłówek Klastra (z sumą +5 pkt). Rodzic (Szczyt) pojawia się w zestawieniu dla kontekstu (z wartością 0 pkt i szarym tłem), by turysta widział, dlaczego w ogóle tam idzie.

---

### SCN-016 — Smart Logger GPX (Masowa Rejestracja i Partial Success)

**Obszar:** `analyze_gpx_track`, `bulk_log_ascents`  
**Powiązane invarianty:** T-01, T-03, D-04, M-02  
**Powiązane User Stories:** US-C17  
**Aktorzy:** Turysta  

**Warunki wstępne:**
- System posiada 3 obiekty: Obiekt A, Obiekt B i Obiekt C (Spalony/Zamknięty z `existence_end = 2022-01-01`).
- Turysta dysponuje plikiem GPX. Ślad przebiega w odległości < 100 metrów od wszystkich 3 obiektów.
- Plik GPX zawiera tag `<time>` z datą `2024-05-10`.

**Kroki i Test Scenarios (E2E / Integration):**
1. Turysta uderza w endpoint `POST /api/v1/gpx/analyze/` wysyłając plik GPX.
   → *Geospatial Case:* Adapter parsuje XML (w RAM), upraszcza linię, wyciąga datę z tagu i rzuca ją do PostGIS na `ST_DWithin(200m)`.
   → *Oczekiwany efekt:* API zwraca `200 OK` z DTO zawierającym sugerowaną datę `2024-05-10` oraz listę 3 obiektów (A, B, C).
2. Turysta akceptuje sugerowaną datę i odsyła listę ID 3 obiektów do `POST /api/v1/ascents/bulk/`.
   → *Batching Case:* Use Case pobiera z bazy cykle życia obiektów JEDNYM zapytaniem (unikając problemu N+1).
   → *Bitemporal Case:* Obiekt A i B przechodzą walidację. Obiekt C zostaje odrzucony, bo `2024-05-10` > `existence_end` (2022-01-01).
   → *Idempotency Case:* Turysta miał już w bazie log z wejścia na Obiekt A w tym samym dniu. Baza "cicho połyka" ten fakt (`ignore_conflicts=True`).
   → *Partial Success:* API zwraca `200 OK` z komunikatem `{"saved_count": 1, "errors": [{"peak_id": C...}]}`.
3. API wyzwala proces przeliczania rankingu (Celery).
   → *Throttling Case:* Task `recalculate_poi_scores_task.delay()` zostaje wywołany dokładnie JEDEN raz dla tego `profile_id`, a nie 3 razy (zapobiega to Task Spammingowi).

---

## 3. Zależności Architektoniczne (Faza C) - Nowe Porty

**UWAGA DO AGENTÓW ARCHITEKTONICZNYCH:** Implementacja powyższych scenariuszy będzie wymagała w pierwszej kolejności zdefiniowania i zamockowania (Tests/Fakes) następujących nowych Portów w katalogu `application/ports/`:

- `UserProgressRepositoryPort` — Wymagany przez SCN-001 (Prawa nabyte / Najstarsze wejście), SCN-002 (Weryfikacja logistycznego statusu zależnej odznaki), SCN-010 (Rozpoczynanie kolejnego Cyklu).
- `AscentLogRepositoryPort` — Wymagany przez SCN-001, SCN-010 (Pobieranie odfiltrowanej listy wejść i ich dowodów).
