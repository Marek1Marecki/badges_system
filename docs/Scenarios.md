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
**Powiązane invarianty:** R-01  
**Powiązane edge cases:** EC-030  
**Aktorzy:** Turysta, Przodownik PTTK (Admin)  

**Warunki wstępne:**
- Turysta zdobywa "Koronę Sudetów" (KS) i "Sudeckiego Włóczykija" (SW).
- "SW" w swoich regułach posiada `PrerequisiteBadgeRule(required_badge_code="KS")`.
- Turysta posiada status `COMPLETED` w domenie dla "KS", ale fizyczna blacha nie została jeszcze mu nadana.

**Kroki:**
1. Turysta otwiera postęp dla "SW", a system synchronicznie odpytuje `VerifyBadgeUseCase`.
   → Domena zgłasza, że pula szczytów się zgadza.
   → `VerifyBadgeUseCase` wywołuje port: `UserProgressRepositoryPort.get_badge_logistics_status(user_id, "KS")`.
   → Wynikiem nie jest `ALBUM` (ani odpowiedni status akceptacji weryfikacyjnej).
   → Weryfikacja staje na 100% zablokowana i silnik NIE nadaje statusu `COMPLETED` dla "SW".
2. Turysta wysyła książeczkę dla "KS" do weryfikacji. Przodownik PTTK w tablicy Kanban zmienia stan "KS" na `ALBUM`.
3. Turysta ponownie ładuje widok "SW".
   → `get_badge_logistics_status` zwraca poprawny stan dla "KS".
   → System przyznaje "SW" status `COMPLETED`.

**Stan końcowy:** "Sudecki Włóczykij" gotowy do stworzenia Wniosku Weryfikacyjnego.  

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

### SCN-011 — Wniosek Zbiorczy i Wymóg Książeczki

**Obszar:** `verification_requests`  
**Powiązane invarianty:** S-01 (Kierunek stanów)  
**Powiązane edge cases:** —  
**Aktorzy:** Turysta, Przodownik PTTK  

**Warunki wstępne:**
- Turysta posiada 3 odznaki w statusie postępu `COMPLETED` z tego samego regionu.
- Jedna z odznak posiada flagę na poziomie bazy: `BadgeModel.is_booklet_required = True`.
- Turysta nie wgrał dotąd do systemu pliku PDF z potwierdzeniami (`UserBooklet`).

**Kroki:**
1. Turysta agreguje 3 odznaki w widoku koszyka i klika "Wyślij Wniosek do Weryfikacji".
   → API weryfikacyjne zwraca 422 Unprocessable Entity z komunikatem o braku wymaganej książeczki dla konkretnej odznaki.
2. Turysta wgrywa PDF swojej fizycznej książeczki i ponawia request.
   → System tworzy jeden zbiorczy `VerificationRequest` i nadaje mu status `WAITING_FOR_VERIFICATION`.
3. Przodownik PTTK zatwierdza wniosek w panelu.
   → Zmiana stanu na `WAITING_FOR_RECEIVING` z zapisem timestampu akcji.
4. Próba wykonania żądania API przez złośliwego użytkownika (Hacker) próbującego wymusić zmianę z `WAITING_FOR_RECEIVING` z powrotem na `WAITING_FOR_SEND`.
   → Wyrzucenie błędu `IllegalStateTransitionError` na poziomie weryfikacji tranzycji FSM.

**Stan końcowy:** Bezpieczna, jednokierunkowa wędrówka procesu od wniosku po tablicę logistyczną zakończona zatwierdzeniem.

---

## 3. Zależności Architektoniczne (Faza C) - Nowe Porty

**UWAGA DO AGENTÓW ARCHITEKTONICZNYCH:** Implementacja powyższych scenariuszy będzie wymagała w pierwszej kolejności zdefiniowania i zamockowania (Tests/Fakes) następujących nowych Portów w katalogu `application/ports/`:

- `UserProgressRepositoryPort` — Wymagany przez SCN-001 (Prawa nabyte / Najstarsze wejście), SCN-002 (Weryfikacja logistycznego statusu zależnej odznaki), SCN-010 (Rozpoczynanie kolejnego Cyklu).
- `AscentLogRepositoryPort` — Wymagany przez SCN-001, SCN-010 (Pobieranie odfiltrowanej listy wejść i ich dowodów).
- `VerificationRequestRepositoryPort` — Wymagany przez SCN-011 (Tworzenie paczki, maszyna stanów, załączanie `UserBooklet`).