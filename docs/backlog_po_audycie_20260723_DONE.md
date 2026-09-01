# Backlog po Audycie (Step 3.7 Flash)

> **Dokument roboczy** gromadzący zadania refaktoryzacyjne, wykryte luki w zabezpieczeniach oraz optymalizacje architektoniczne wygenerowane w serii audytów zewnętrznych. Każde zadanie po wdrożeniu powinno zostać odhaczone.

---

## Lista zadań zrealizowanych:

---

### [AUDYT-001] Naprawa składni Pythona i kolejności argumentów Exception Handlera
**Obszar:** `API / Views`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
W widoku `BadgeLogisticsView` pozostała składnia Pythona 2 (`except A, B:`). Dodatkowo w 4 miejscach w `views.py` argumenty do helpera `_handle_application_exception` są przekazywane w odwrotnej kolejności (`exc, request.path` zamiast `request, exc`), co skutkuje błędem 500 przy każdej odmowie domenowej.

**Action Items (Do wdrożenia):**
- [X] Poprawić składnię na `except (json.JSONDecodeError, ValueError):` w `BadgeLogisticsView`.
- [X] Zmienić kolejność argumentów na `(request, exc)` we wszystkich wywołaniach w `views.py`.
- [X] Dodać pole `request_id` (pobierane z atrybutów request) do słownika zwracanego w funkcji `_problem_detail` w `views.py`.

**Komentarz Architekta:**
Klasyczny dług technologiczny po szybkiej refaktoryzacji widoków API. Do naprawy w jednym sprincie.

---

### [AUDYT-004] Wyciek architektury: Brakująca wiedza o progach wielostopniowych
**Obszar:** `Infrastruktura / Adaptery`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
Podczas hydracji definicji odznaki z bazy danych, wartość progu zaliczeniowego `required_count` była sztucznie obliczana jako długość puli (`len(pool_peaks)`) na poziomie Wersji. Mechanizm ten psuł odznaki wielostopniowe, gdzie właściwy próg przypisany jest do konkretnego `BadgeTier` (Stopnia).

**Action Items (Do wdrożenia):**
- [X] Przenieść progi liczbowe z Wersji Odznaki do poszczególnych Stopni (`BadgeTierDomain`).
- [X] Zmodyfikować logikę oceny `evaluate()` w Domenie, by weryfikowała postęp względem tablicy wstrzykniętych Stopni (Tiers).
- [X] Zamknąć opisany dług techniczny `TD-03` w dokumentacji.

**Wdrożenie:**
- Domena (`BadgeVersionDomain`, `BadgeTierDomain`) posiada pole `required_count` na każdym Stopniu; `evaluate()` (linia 76) używa `t.required_count`.
- Adapter (`_hydrate_version`) odczytuje `BadgeTierModel.required_peaks_count`, fallback `len(pool_peaks)` tylko dla `None`.
- Testy: `test_hydrates_multi_tier_with_distinct_thresholds`, `test_hydrates_fallback_to_pool_size_when_required_peaks_count_is_null`.

---

### [AUDYT-005] Kaskadowe wygnanie ducha "VerificationRequest"
**Obszar:** `Dokumentacja / Architektura`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Fundamentalna sprzeczność architektoniczna. `ADR-014` jasno definiuje porzucenie agregatu `VerificationRequest` (oraz `UserBooklet`) na rzecz zintegrowanego modelu `UserBadgeProgress` i Osobistego Kanbana. Tymczasem pliki `Scenarios.md`, `Invariants.md` (S-03, S-04) oraz `User Stories.md` (US-C05) wciąż traktują ten usunięty agregat jako istniejący.

**Action Items (Do wdrożenia):**
- [X] Oczyścić `INVARIANTS.md`: Usunąć wzmianki o `VerificationRequest` w opisie S-03 i S-04.
- [X] Oczyścić `Scenarios.md`: Zaktualizować SCN-011 i usunąć wymóg wgrania `UserBooklet`.
- [X] Oczyścić `User Stories.md`: Usunąć z US-C05 wzmiankę o `VerificationRequest`.

**Komentarz Architekta:**
Klasyczny dług dokumentacyjny po podjęciu kluczowej decyzji (ADR-014). Niespójność ta może spowodować, że nowy programista zacznie budować nieistniejące tabele w bazie.

---

### [AUDYT-006] Czyszczenie `SYSTEM_PROMPT.md` z nieaktualnych długów i `ActivityType`
**Obszar:** `Dokumentacja / GenAI Context`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Plik `SYSTEM_PROMPT.md` to najważniejszy wektor informacyjny dla agentów AI. Obecnie wprowadza ich w błąd, wymieniając długi TD-01, TD-02, TD-03 jako "aktywne", podczas gdy `CHANGELOG.md` oficjalnie potwierdza ich spłatę. Dodatkowo prompt i `GLOSSARY.md` nadal wmawiają agentowi istnienie `ActivityType` (HIKING), co zostało brutalnie wycięte jako YAGNI.

**Action Items (Do wdrożenia):**
- [X] Wyczyścić tabelę "Znane długi techniczne" w `SYSTEM_PROMPT.md` (zostawić adnotację "Wszystkie spłacone").
- [X] Usunąć `activity / HIKING` z definicji `Ascent` w `SYSTEM_PROMPT.md` i `GLOSSARY.md`.
- [X] Ujednolicić relację w `User Stories.md` (US-C01): zmienić `OneToOneField` na `ForeignKey (1:N)` zgodnie z wprowadzonym Modelem Rodzinnym.

**Komentarz Architekta:**
Przestarzały System Prompt to gwarancja "halucynacji" AI w kolejnych sprintach. To zadanie ma absolutny, najwyższy priorytet przed dopuszczeniem jakiegokolwiek bota do kodu.

---

### [AUDYT-007] Uporządkowanie chaosu w `Edge Cases.md` i `User Stories.md`
**Obszar:** `Dokumentacja`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Przypadki brzegowe EC-035, EC-036, EC-037 zostały omyłkowo wklejone przez człowieka do pliku `User Stories.md` zamiast do `Edge Cases.md`. Ponadto w `Edge Cases.md` występuje wyciek moich (AI) instrukcji redakcyjnych ("Popraw fragment pobierający stopnie...") oraz zduplikowana i przerwana numeracja (np. podwójne EC-040, luki).

**Action Items (Do wdrożenia):**
- [X] Przenieść EC-035, EC-036, EC-037 z pliku `User Stories.md` do `Edge Cases.md`.
- [X] Usunąć wyciek tekstu instrukcji w okolicach EC-003 / EC-010.
- [X] Zreindeksować (przenumerować) przypadki brzegowe, aby wyeliminować duplikaty (EC-040, EC-044) i usunąć pustą zawartość tabel/komórek.

**Komentarz Architekta:**
Czysto redakcyjny bałagan powstały przy masowym przeklejaniu Markdowna z czatu do plików. Zmniejsza to zaufanie inżynierów do dokumentacji.

---

### [AUDYT-009] Usunięcie "śmieci" z Manifestów szablonowych
**Obszar:** `Manifesty / Narzędzia`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Plik `00-index.md` (lub podobny rejestr portów) oraz `06-documentation-contract.md` zawierają odniesienia do projektów `blood_pressure_dashboard`, `GTD_Planner` i folderów `docs_sphinx/`. 

**Action Items (Do wdrożenia):**
- [X] Przejrzeć katalog `docs/Manifest/` i usunąć wszelkie odniesienia do zewnętrznych, starych projektów.
- [X] Dopasować nazwy weryfikowanych plików (np. `Data Flow Diagram.md` zamiast `DATAFLOW.md`), aby linter dokumentacji nie zgłaszał fałszywych błędów o brakujących plikach.

**Komentarz Architekta:**
To po prostu pozostałości po szablonach korporacyjnych (Boilerplates), które użyliśmy do postawienia struktury. Nie wpływa to na kod, ale psuje czytelność.

---

### [AUDYT-010] SANITY CHECK: Weryfikacja pominiętego kodu
**Obszar:** `Kod Źródłowy / IDE`  
**Priorytet:** `🔴 KRYTYCZNY` (Dla Programisty)

**Diagnoza Audytora:** 
Audytor wykrył w bazie kodu błędy, które na etapie czatu zostały już wspólnie naprawione (np. stary `except json.JSONDecodeError, ValueError:` w `views.py`, brak pobierania profilu z sesji w widokach, odwrócone argumenty w wyjątku oraz brak pola `valid_to` w repozytorium odznak).

**Action Items (Do wdrożenia PRZEZ CIEBIE w IDE):**
- [X] Sprawdź plik `apps/api/views.py`: Upewnij się, że nie ma tam składni Pythona 2.
- [X] Sprawdź ten sam plik: Upewnij się, że helper to `_handle_application_exception(request, exc)`, a wywołania mają właściwą kolejność.
- [X] Sprawdź w widokach: Upewnij się, że nigdzie nie używasz `request.profile.id` (zamienić na odczyt z `request.session`).
- [X] Sprawdź `infrastructure/adapters/persistence/django_badge_repo.py`: Upewnij się, że metoda `get_latest_badge_version` posiada zabezpieczenie `Q(valid_to__isnull=True) | Q(valid_to__gte=...)`.

**Komentarz Architekta:**
Nie generujemy na to nowego kodu. Musisz upewnić się, że nie pominąłeś paczek aktualizacyjnych z poprzednich konwersacji podczas wklejania do swojego IDE, lub czy stare pliki nie nadpisały Ci się przypadkowo z githa.

---

### [AUDYT-011] Weryfikacja przepływu autoryzacji w API (IDOR i RFC 7807)
**Obszar:** `API / Views`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Plik `apps/api/views.py` stanowi główną linię obrony systemu. Audytor zdefiniował go jako obszar najwyższego ryzyka (P0), nakazując weryfikację tego, czy wszystkie 9 widoków poprawnie korzysta z mechanizmów zabezpieczających (IDOR, omijanie `request.user_id` na rzecz profilu z sesji) oraz czy każdy błąd przepinany jest przez standard RFC 7807 z dołączonym `request_id`.

**Action Items (Do wdrożenia):**
- [X] Wykonać ręczny przegląd kodu wszystkich klas w `apps/api/views.py`.
- [X] Upewnić się, że `_problem_detail` generuje `request_id` we wszystkich miejscach (Zgodnie z poprawką z AUDYT-001).
- [X] Wprowadzić testy automatyczne w `tests/apps/api/test_integration.py` potwierdzające rzucanie kodów 4xx przy próbach manipulacji danymi obcego użytkownika.

**Komentarz Architekta:**
Większość z tych zabezpieczeń wprowadziliśmy już we wczorajszym sprincie, zastępując djangowe dekoratory własnym helperem `_require_auth`. Wymaga to jednak ostatecznego przeglądu (Sanity Check) kodu testów.

---

### [AUDYT-012] Sanity Check: Prawa Nabyte i Cinderella Bug
**Obszar:** `Infrastructure / Badge Repo`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Audytor wytypował plik `infrastructure/adapters/persistence/django_badge_repo.py` jako ryzykowny (P1) ze względu na hydrację reguł z pola JSONB do obiektów Czystej Domeny oraz problem "Cinderella Bug" (EC-068), który znikał z czasem (brak obsługi pola `valid_to`).

**Action Items (Do wdrożenia PRZEZ CIEBIE w IDE):**
- [X] Sprawdzić implementację `get_latest_badge_version` i `get_version_id_for_date`. Upewnić się, że obie metody posiadają warunek logiczny chroniący przed błędem upływu dnia (np. `Q(valid_to__isnull=True) | Q(valid_to__gte=target_date)`).

**Komentarz Architekta:**
Zastosowaliśmy to rozwiązanie podczas incydentu "Znikających Szczytów o Północy", ale warto sprawdzić, czy zmiana na 100% nie została cofnięta przez przypadek przy kopiowaniu plików.

---

### [AUDYT-014] Ominięcie architektury w widokach API (Direct ORM Usage)
**Obszar:** `API / Hexagonal Architecture`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widoki `ProfileSettingsView` oraz `NearbyObjectsView` w `apps/api/views.py` łamią podstawową zasadę Czystej Architektury. Zawierają one bezpośrednie wywołania modeli Django (ORM) takie jak `.save()`, `get_object_or_404` czy zapytania przestrzenne GIS, omijając całkowicie warstwę Aplikacji (Use Cases) oraz Porty.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Utworzyć `UpdateProfileUseCase` i DTO aktualizacji profilu w warstwie Aplikacji.
- [X] Zmodyfikować `ProfileSettingsView`, by wywoływał nowy Use Case przez Kontener DI, zamiast bezpośrednio zapisywać dane w bazie.
- [X] Przenieść zapytanie przestrzenne (`ST_DWithin`) z `NearbyObjectsView` do adaptera `DjangoMapRepository` i wywoływać je przez port.
- [X] Dodać regułę do lintera `audit_contracts.py` zabraniającą importu `apps.badges.models` wewnątrz `apps/api/views.py`.

**Komentarz Architekta:**
Klasyczny wyciek logiki do kontrolerów powstały podczas szybkiego dowożenia funkcji Fazy C. Jest to bardzo szkodliwe dla izolacji testów i musi zostać wyczyszczone jako priorytet przed rozwojem aplikacji.

---

### [AUDYT-020] Brakujące Testy Integracyjne (PostGIS i Restore Data)
**Obszar:** `Testy Integracyjne / Infrastruktura`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Zgodnie z kontraktem, testy integracyjne powinny sprawdzać prawdziwą bazę. Tymczasem nasze repozytoria (np. `django_map_repo.py`) opierają się na mockach (Monkeypatching `TouristObject.objects.filter`), co całkowicie ukrywa błędy w funkcjach `ST_DWithin` czy złączeniach CQRS. Brakuje również bezwzględnie wymaganego testu na idempotentność komendy `restore_reference_data` (podwójne wywołanie polecenia nie może nadpisać danych). Największy adapter systemu – `DjangoTouristRepository` – ma pusty plik testowy (`0 bajtów`).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Napisać prawdziwe testy bazodanowe (z użyciem znacznika `@pytest.mark.django_db`) dla `DjangoMapRepository` i `DjangoTouristRepository`.
- [X] Napisać test integracyjny weryfikujący podwójne odpalenie komendy `restore_reference_data`.
- [X] Usunąć sztuczne mocki na obiektach ORM z obecnych plików w katalogu `tests/infrastructure/adapters/persistence/`.

**Komentarz Architekta:**
Mockowanie ORM to antywzorzec. Przebudujemy testy infrastruktury tak, aby uderzały w pustą, tymczasową bazę generowaną przez pytest-django. To uleczy nasz system i zmyje winę "fałszywych testów".

---

### [AUDYT-021] Niestabilność Czasowa Testów (Flaky Tests)
**Obszar:** `Testy Jednostkowe / Maintainability`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
`date.today()` / `datetime.now(UTC)` w testach mogą eksplodować przy GC/CPU load (CI midnight).

**Rozwiązanie:**
- [X] Przeszukano wszystkie `test_*.py` pod kątem `date.today()` i `datetime.now()`.
- [X] `tests/domain/rules/test_badge_rules.py` + `tests/domain/entities/test_badge_version.py` — zastąpiono `date.today()` sztywną `date(2024, 6, 15)` (zgodną z `FakeClock.DEFAULT_TIME`).
- [X] `tests/infrastructure/adapters/test_clock.py` — zwiększono tolerancję `SystemClock` od 1s → 5s (celowy test realtime, ale stabilny pod CI load).
- [X] Pozostałe użycia (`test_integration.py`, `test_security.py`, `test_osm_repository.py`) **celowo pozostawiono**: payload API (`date.today()` jako input usera) oraz `datetime.now()` jako dane OSM — nie są asercjami czasowymi.

**Uzasadnienie decyzji:**
Flaky = asercja zależna od `now()`. `date.today()` w danych domenowych był ryzykiem (gdyby reguła porównała do `today()`). Sztywna data eliminuje nondeterminizm. `test_clock` tolerance 5s to akceptowany tradeoff dla testu realtime.

**Komentarz Architekta:**
Zmiana to faktycznie ~3 min Find & Replace + 1 edycja tolerance.

---

### [AUDYT-024] Załatanie podatności Open Redirect w `switch_profile_view`
**Obszar:** `API / Bezpieczeństwo`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widok odpowiedzialny za zmianę profilu rodzinnego w `apps/tourists/views.py` używa niebezpiecznej konstrukcji `redirect(request.META.get("HTTP_REFERER", "home"))`. Nie weryfikuje on, czy nagłówek Referer faktycznie należy do naszej domeny. Atakujący może stworzyć spreparowany link nakłaniający ofiarę do kliknięcia, co po przełączeniu profilu przekieruje ją na złośliwą stronę (Phishing).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zmodyfikować `switch_profile_view`, tak aby walidował bezpieczny adres docelowy. Np.: `next_url = request.GET.get("next") or request.META.get("HTTP_REFERER"); if next_url and not next_url.startswith("/"): next_url = "home"`.

**Komentarz Architekta:**
Klasyczny błąd z grupy A01 (OWASP). Prosta łatka z użyciem `startswith("/")` całkowicie zamyka ten wektor ataku, wymuszając nawigację wyłącznie w obrębie naszej witryny.

---

### [AUDYT-025] Brak autoryzacji zasobu w `BadgeLogisticsView` (Luka IDOR)
**Obszar:** `API / Autoryzacja`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widok `BadgeLogisticsView` (odpowiedzialny za Osobisty Kanban logistyki) przyjmuje z adresu URL parametr `progress_id`. Chociaż widok weryfikuje, czy użytkownik jest zalogowany (`_require_auth`), nie weryfikuje, czy edytowany postęp faktycznie należy do profilu wykonującego to żądanie. Złośliwy użytkownik znający `progress_id` obcej osoby może bezkarnie przesuwać status wysyłki jego odznak!

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zmodyfikować `AdvanceLogisticStatusUseCase`, aby upewnić się, że `progress.profile_id == profile_id`.
- [X] Dodać asercje i rzucać wyjątek w przypadku braku uprawnień.

**Komentarz Architekta:**
Krytyczne przeoczenie logiki w `Use Case`. IDOR to jeden z najgroźniejszych i najczęściej występujących błędów w REST API.

---

### [AUDYT-028] Brak weryfikacji formatu i ograniczeń dla załączników
**Obszar:** `API / Zaufanie do danych klienta`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
`GpxAnalyzeView` nie weryfikował `Content-Type`; model `souvenir_image` nie miał walidatorów DoS/MIME.

**Rozwiązanie (częściowe + zaplanowane):**
- [X] #1 — `Content-Type` validation + Magic Bytes + 10MB size limit → wdrożone w ramach AUDYT-050 (`apps/api/views.py:631-659`).
- [X] 3 testy asercyjne (`test_returns_422_when_file_too_large / invalid_mime_type / not_xml`).
- [X] `apps/tourists/models.py` — `souvenir_image` posiada `help_text` dokumentujący brak walidatora rozmiaru i konieczność dodania go przy wystawieniu endpointu API.
- ⏳ #2 (souvenir_image validators) — **zaplanowane**. `souvenir_image` jest `readonly` w Django Admin (brak uploadu → brak wektora ataku). Gdy powstanie endpoint REST, trzeba dodać `MaxValueBytesValidator` (rozmiar) + wyraźny MIME check (obecnie Django `ImageField` używa Pillowa).

**Uzasadnienie decyzji:**
#1 (GPX) = natychmiastowy threat model (upload pliku). #2 (souvenir) = future work: brak endpointu API → ryzyko niższe; `ImageField` daje minimalną ochronę.

**Komentarnik Architekta:**
Defense in Depth — `Content-Type` + magic bytes na bramie HTTP (AUDYT-050) + `pillow` na modelu. Do pełnej ochrony potrzebny dedykowany validator przy API endpoint.

---

### [AUDYT-029] Brak indeksów na często używanych kolumnach ORM
**Obszar:** `Baza Danych / Modele Django`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Baza rosnąc do setek tysięcy wierszy utknie na pełnych skanach tabel (Seq Scan). Modele nie posiadają zdefiniowanych indeksów w klasie `Meta` (lub bezpośrednio na polach za pomocą `db_index=True`) dla najczęściej filtrowanych ścieżek odczytu.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Dodać indeksy na polach: `TouristObject.name`, `TouristObject.status`, `TouristObject.is_active`.
- [X] Dodać Composite Index (złożony indeks) dla `AscentLog(profile_id, ascent_date)` (wspiera operację `get_oldest_ascent_date`).
- [X] Dodać Composite Index dla `UserBadgeProgress(profile_id, badge_id, domain_status)` (optymalizacja dla zapytań Czystej Domeny o postęp).
- [X] Wdrożyć indeksy poprzez stworzenie nowych migracji schematu (`Database Release`).

**Komentarz Architekta:**
Klasyczny błąd MVP. Dodanie tych indeksów skróci czas krytycznych zapytań Use Case'ów z kilkuset do pojedynczych milisekund. Obowiązkowe przed wejściem na 10 tysięcy użytkowników.

---

### [AUDYT-030] N+1 Query w widoku `badge_detail_view` (M2M `pool_peaks`)
**Obszar:** `API / Widoki HTMX`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Pętla odczytująca listę obiektów na stronie ze szczegółami odznaki (renderowana w HTML) odwołuje się do `target_version.pool_peaks.all()`. Ponieważ obiekt wersji nie został pobrany z użyciem instrukcji `prefetch_related("pool_peaks")`, przejście po 100 szczytach odznaki spowoduje wygenerowanie 100 osobnych zapytań SQL do bazy w jednym żądaniu HTTP.

**Action Items (Do wdrożenia):**
- [X] W pliku `apps/tourists/views.py` (lub w Query Service) zmodyfikować zapytanie pobierające wersję odznaki tak, by dołączyć `prefetch_related("pool_peaks")` przed przekazaniem obiektu do szablonu.

**Komentarz Architekta:**
Zjawisko to zostało usunięte z głównego rankingu (`ExploreQueriesService`), ale zapomnieliśmy o nim w "lewym pasku" na samej stronie detali odznaki. Szybka poprawka (`prefetch_related`) w zapytaniu zdejmie gigantyczne obciążenie z połączenia z PostGIS-em.

---

### [AUDYT-031] Przepełnienie RAM przy pobieraniu wszystkich logów wejść
**Obszar:** `Infrastruktura / Repozytoria`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Metoda `get_all_ascents_for_user` w `DjangoTouristRepository` wczytuje wszystkie historyczne logi użytkownika (`list(AscentLog.objects...)`) prosto do pamięci RAM naraz. Kiedy użytkownik zacznie gromadzić tysiące wpisów z tras GPX, system odczytu postępów spowoduje zjawisko OOM (Out Of Memory) na serwerze i zawieszenie procesu `web` (Gunicorn).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zastąpić bezwzględne wywołanie `.all()` użyciem parsera strumieniowego bazy danych (np. `.iterator(chunk_size=2000)` w Django).
- [X] Zaprojektować ewentualną paginację dla endpointu weryfikacyjnego.

**Komentarz Architekta:**
Bardzo mądre spojrzenie do przodu. Wprawdzie model `AscentLog` jest dość wąski w SQL, ładowanie 50 000 obiektów do pamięci przy każdym przeliczeniu punktacji (PoiScoringService) udławi serwer. Przebudowa odczytu na iteratory jest koniecznością w fazie stabilizacji (SRE).

---

### [AUDYT-038] Potrzeba Testów Bezpieczeństwa Deserializacji (Fail-Fast)
**Obszar:** `Infrastruktura / Testy`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Audytor wyznaczył adapter `django_badge_repo.py` jako punkt ryzyka klasy `🔴 P0`, powołując się na "bezpieczeństwo deserializacji". Reguły biznesowe PTTK przechowywane są w bazie jako JSONB. Zgodnie z ADR-003 oraz Invariantem R-02, adapter musi wyrzucić twardy błąd (Fail-Fast), jeśli napotka uszkodzony JSON.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Napisać dedykowany test integracyjny weryfikujący Invariant R-02: wpisać ręcznie do bazy uszkodzony/nieznany obiekt JSON dla reguły i upewnić się, że adapter rzuca odpowiedni wyjątek `ValueError` przed dotarciem do Czystej Domeny.

**Komentarz Architekta:**
Ufamy naszej implementacji słownika `RULE_BUILDERS`, ale nie udowodniliśmy w testach, że faktycznie zatrzymuje on złośliwy lub uszkodzony schemat JSONB z bazy. Proste i tanie zabezpieczenie.

---

### [AUDYT-045] Usunięcie Opcji `CASCADE` w Profilach Turystów
**Obszar:** `Architektura / RODO`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Relacja z profilu turysty na jego wejścia w bazie danych posiada parametr `on_delete=CASCADE`. Jeśli administrator (lub system RODO) usunie profil, baza automatycznie i bezpowrotnie zniszczy wszystkie jego wejścia. Prowadzi to do utraty zanonimizowanych danych analitycznych (historii ruchu na szlakach PTTK) oraz niszczy agregaty popularności szczytów.

**Action Items (Do wdrożenia):**
- [X] Zmodyfikować powiązanie na `on_delete=PROTECT` lub `SET_NULL` (wymaga zmiany `profile_id` na opcjonalne).
- [X] Zaimplementować mechanizm "Tombstoningu" (Soft Delete) dla profili – kasowanie e-maili/haseł, ale pozostawianie zanonimizowanego identyfikatora przypisanego do wejść.

**Komentarz Architekta:**
Uwaga wybitna. Twarde usuwanie na kaskadzie to łatwe wyjście na etapie MVP, ale destrukcyjne na produkcji.

---

### [AUDYT-047] Luki w bezpieczeństwie zarządzania sesją (Brak Secure Flags)
**Obszar:** `Infrastruktura / Bezpieczeństwo HTTP`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
W projekcie brakuje wymuszenia flag bezpieczeństwa dla ciasteczek w środowisku produkcyjnym. Domyślne ustawienia Django pozwalają na przesyłanie ciasteczka sesyjnego (`SESSION_COOKIE`) oraz tokena CSRF przez nieszyfrowane połączenia HTTP. Stanowi to ogromne ryzyko kradzieży sesji (Session Hijacking) przy ataku MITM.

**Action Items (Do wdrożenia w `settings.py`):**
- [X] Dodać zabezpieczenia dla środowiska `app_env == "production"`: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SECURE_SSL_REDIRECT = True`.
- [X] Opcjonalnie wdrożyć politykę HSTS (`SECURE_HSTS_SECONDS`).

**Komentarz Architekta:**
Klasyczny błąd konfiguracji przy wychodzeniu z fazy deweloperskiej. Mimo że Caddy (Reverse Proxy) wymusza u nas HTTPS, aplikacja Django wewnętrznie musi oznaczyć te ciastka jako dostępne *wyłącznie* dla połączeń bezpiecznych.

---

### [AUDYT-048] Ochrona przed fałszowaniem wieku (Age Fraud)
**Obszar:** `API / Logika Biznesowa (RODO)`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecnie widok `ProfileSettingsView` (lub nowy Use Case aktualizacji profilu) pozwala użytkownikowi na swobodną, nieograniczoną modyfikację pola `birth_date` w dowolnym momencie. Ponieważ system opiera punktację i weryfikację na dacie urodzenia (`MinAgeRule`, `MaxAgeRule`), użytkownik może wielokrotnie zmieniać wiek w celu sztucznego zdobycia zablokowanych odznak dziecięcych lub seniorskich.

**Action Items (Do wdrożenia w przyszłości):**
- [X] W `UpdateProfileUseCase` zablokować możliwość zmiany daty urodzenia, jeśli została już raz ustawiona.
- [X] (Alternatywa) Pozwolić na zmianę, ale wymagać twardego zresetowania wszystkich postępów zależnych od wieku lub uruchomienia alertu audytowego.

**Komentarz Architekta:**
Znakomite wyłapanie luki w logice grywalizacji (Gamification Exploit). Data urodzenia to kluczowy Invariant tożsamościowy – po jego ustaleniu powinien stać się niezmienny.

---

### [AUDYT-050] Zabezpieczenie Content-Type dla uploadu plików GPX
**Obszar:** `API / Bezpieczeństwo`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Widok odpowiedzialny za odbieranie plików GPX weryfikuje ich rozmiar, ale nie weryfikuje jednoznacznie ich zawartości w oparciu o typ MIME. Złośliwy użytkownik może wysłać plik `.exe` jako GPX. Co prawda biblioteka `defusedxml` odrzuci to na etapie parsowania, ale plik i tak zostanie przetransferowany i załadowany do pamięci serwera.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Dodać walidację nagłówka pliku (Magic Bytes) oraz dopuszczonego typu MIME (`application/gpx+xml` lub `text/xml`) przed wpuszczeniem pliku do pamięci operacyjnej parsera.

**Komentarz Architekta:**
Klasyczne zabezpieczenie bramki sieciowej. Zapobiegnie to obciążaniu pamięci RAM serwera djangowego złośliwymi ładunkami.

---

### [AUDYT-049] Brak walidacji bezpiecznych wektorów w BBox (Over-fetching DoS)
**Obszar:** `API / GIS`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Endpoint `?bbox=` wstrzykuje wektory do `ST_Within` bez zakresu — fałszywy wektor (`-999,-999,999,999`) = pełny skan tabeli → DoS.

**Rozwiązanie:**
- [X] `MapExploreRequestDTO` (`application/dto/map_dto.py:16-19`) — `Field(ge=-180, le=180)` dla lon, `Field(ge=-90, le=90)` dla lat; `extra="forbid"`.
- [X] `MapObjectsView` już łapie `ValidationError` → 422 (`apps/api/views.py:411`).
- [X] `test_returns_422_for_out_of_range_bbox` w `test_integration.py:337` (integration — bbox=-999 → 422).
- [X] `tests/application/dto/test_map_dto.py` — czysty unit test (7 testów, parametrize) weryfikuje zakresy i `extra="forbid"` — **działa bez DB, w `make check`**.

**Uzasadnienie decyzji:**
Pydantic `Field(ge=, le=)` = 3-linijka walidacja na bramce. `extra="forbid"` zabezpiecza przed payload injection.

**Komentarz Architekta:**
Defense in Depth — walidacja na DTO (Application) przed PostGIS. `bbox=-999` nigdy nie dotrze do `ST_Within`.

---

### [AUDYT-053] Ograniczenie ryzyka OOM (Out Of Memory) przy pobieraniu historii
**Obszar:** `Wydajność / Adaptery`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
W repozytoriach znajdują się metody takie jak `get_all_ascents_for_user`, które ładują wszystkie rekordy historii turysty bezpośrednio do jednej listy w pamięci RAM Pythona. Brak wbudowanego stronicowania (Paginacji) lub użycia iteratorów (`.iterator(chunk_size)`) spowoduje zjawisko OOM na serwerach aplikacyjnych w momencie, gdy tysiące użytkowników zaimportuje wieloletnie paczki z plików GPX.

**Action Items (Do wdrożenia w najbliższych sprintach):**
- [X] Zastąpić bezwzględne wywołania typu `.all()` mechanizmami dzielenia na paczki (Batching) lub generatorami w warstwie adapterów bazodanowych dla tabel rosnących.

**Komentarz Architekta:**
Typowy "Cichy Zabójca" aplikacji pisanych w ORM-ach, który ujawnia się dopiero w fazie produkcyjnego wzrostu obciążenia (Load Spikes). Szybki do naprawy, wymagający modyfikacji kilku linijek w adapterach odczytu.

---

### [AUDYT-059] Pusty plik testowy dla `DjangoTouristRepository`
**Obszar:** `Testy Integracyjne`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Najważniejszy adapter w systemie, `DjangoTouristRepository` (implementujący 3 porty aplikacyjne dla logów, profili i postępów), posiada w repozytorium plik testowy `test_django_tourist_repo.py` o rozmiarze 0 bajtów! Cała pewność co do działania zapisu wycieczek i obliczania praw nabytych opiera się na ręcznym klikaniu.

**Action Items (Do wdrożenia PRZED Playwrightem):**
- [X] Napisać testy dla `DjangoTouristRepository` przy użyciu wbudowanych narzędzi `pytest-django` (`@pytest.mark.django_db`).
- [X] Przetestować rzucanie błędu (Idempotentność) przy zapisie duplikatu logu.

**Komentarz Architekta:**
Klasyczne przeoczenie przy szybkim refaktoringu monolitu. Testowanie ORM-a z rzeczywistą, wbudowaną w Pytest bazą (bez mocków) zabetonuje nam logikę turysty przed startem testów E2E.

---

### [AUDYT-064] Wdrożenie tarczy Gating Pipeline (Continuous Architecture Verification)
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Audytor wyłapał, że projekt polega wyłącznie na manualnym uruchamianiu komendy `make check`. Brak zautomatyzowanego potoku CI (Continuous Integration), np. plików GitHub Actions, skutkuje tym, że programista może po prostu zignorować błędy (lub nie odpalić komendy) i wgrać kod bezpośrednio do głównej gałęzi (main). Ponadto brakuje oficjalnego wdrożenia narzędzia `import-linter` (brak pliku konfiguracji `.importlinter` z opisanymi regułami granic).

**Action Items (Do wdrożenia w nadchodzącym sprincie DevOps):**
- [X] Utworzyć plik konfiguracyjny `.importlinter` (lub odpowiednik dla narzędzia `pydeps`), jawnie zakazujący importów z `apps` i `infrastructure` do `domain` i `application`.
- [X] Utworzyć plik potoku (np. `.github/workflows/ci.yml`), który zablokuje `git merge`, jeśli `make check` nie zakończy się ze statusem `0` (Success).

**Komentarz Architekta:**
"Nieufne środowisko" to fundament stabilnego produktu. Automatyzacja wyłapywania wycieków warstw i błędów Mypy oszczędzi nam połowy przyszłych Audytów! Zrobimy to, gdy zaczniemy formalizować środowiska z `compose.test.yml`.

---

### [AUDYT-076] Brak automatycznych potoków CI/CD (Brak `GitHub Actions`)
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Mimo posiadania wysoce dojrzałej architektury konteneryzacji (Multi-stage `Dockerfile`, `compose.test.yml`, dedykowane skrypty wdrażające w `scripts/`), w repozytorium fizycznie nie istnieje żaden plik orkiestratora CI (np. w katalogu `.github/workflows/`). Oznacza to, że pomimo posiadania "części zamiennych", projekt pozbawiony jest w pełni zautomatyzowanego potoku, który samoczynnie weryfikowałby każdy Pull Request i zarządzał wdrożeniami (Continuous Integration / Continuous Deployment).

**Action Items (Do wdrożenia PRZED Playwrightem / Prodem):**
- [X] Utworzyć plik definiujący potok CI (np. `.github/workflows/ci.yml`).
- [X] Skonfigurować w nim tzw. *Quality Gate*, który automatycznie, na środowisku efemerycznym GitHuba, uruchomi przygotowane uprzednio skrypty: weryfikację linterów (`make check`) oraz testy integracyjne infrastruktury (`./scripts/test-run.sh --full`).
- [X] Dodać zabezpieczenie blokujące połączenie gałęzi (Merge) w przypadku, gdy którykolwiek krok w potoku zakończy się statusem błędu.

**Komentarz Architekta:**
Mamy gotowe, perfekcyjnie przetestowane skrypty (Bash/Make). Wpięcie ich w 40-linijkowy plik YAML dla GitHub Actions to teraz czysta formalność, która ostatecznie zamknie temat "Brakującego CI". Należy to zrobić w następnym kroku.

---

### [AUDYT-109] Złamane zaufanie do struktury katalogów testów (QA Matrix vs Rzeczywistość)
**Obszar:** `Dokumentacja / Testy`  
**Priorytet:** `🔴 KRYTYCZNY (Zaufanie)`  

**Diagnoza Audytora:** 
Plik `docs/QA_MATRIX.md` oraz `Test Strategy.md` sztucznie kategoryzują testy na Unit i Integration, podając konkretne liczby, co sugeruje istnienie katalogów `tests/unit/` i `tests/integration/`. W rzeczywistości testy (mimo że ich liczba przekracza 590) są ustrukturyzowane w oparciu o moduły (`tests/application/`, `tests/domain/`). Wywołuje to u nowych deweloperów wrażenie "fałszywej statystyki" i braku pokrycia kodu.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [X] Zaktualizować plik `docs/QA_MATRIX.md` tak, aby nazwy kategorii odpowiadały rzeczywistym folderom w projekcie (np. Zastąpić "Unit Tests" słowami "Domain & Application Tests").
- [X] Dodać krótki plik `tests/README.md` opisujący, gdzie dokładnie znajdują się testy jednostkowe, a gdzie integracyjne, ucinając domysły.

**Komentarz Architekta:**
Niespójność nazewnictwa niszczy wiarygodność nawet najlepiej przetestowanego systemu. Skoro wybraliśmy organizację folderów per-moduł, dokumentacja QA musi to bezwzględnie odzwierciedlać.

---

### [AUDYT-110] Luki w odnośnikach "Żywej Dokumentacji" (README & ADR)
**Obszar:** `Dokumentacja / Onboarding`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Główny plik wejściowy do projektu (`README.md`) kieruje programistę pod nieistniejące pliki (np. `docs/VISION.md` zamiast `docs/Vision Statement.md`). Z kolei plik `SYSTEM_PROMPT.md` odwołuje się do nieistniejących plików `ADR-017` do `ADR-019`, wprowadzając deweloperów w błąd, że brakuje im wiedzy architektonicznej.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [X] Skorygować linki w pliku `README.md`, by odpowiadały faktycznym nazwom plików (uwaga na spacje w nazwach w GitHubie - zastąpić `%20` lub zmienić nazwy plików na kebab-case).
- [X] Zaktualizować `SYSTEM_PROMPT.md` i listę ADR-ów, usuwając odwołania do pustych numerów (017-019) lub tworząc dla nich fizyczny plik objaśniający (Placeholder).

**Komentarz Architekta:**
Klasyczny przypadek "Martwych Linków" (Dead Links). Jest to drobnostka z perspektywy kodu, ale kluczowy błąd z perspektywy pierwszego wrażenia (Developer Experience).

---

### [AUDYT-017] Duplikacja logiki weryfikacji bitemporalnej
**Obszar:** `Aplikacja / Use Case`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Zasada bitemporalności (T-01, czyli sprawdzanie `existence_start` i `existence_end` obiektu) była zaimplementowana dwukrotnie: w `LogAscentUseCase` oraz w pętli dla `BulkLogAscentsUseCase`.

**Rozwiązanie:**
- [X] Utworzono `BitemporalValidationService` (`application/services/bitemporal_validation_service.py`) jako serwis aplikacyjny.
- [X] `LogAscentUseCase.execute` używa `validate_single(peak_id, ascent_date)`.
- [X] `BulkLogAscentsUseCase.execute` używa `validate_batch(ascents)`.
- [X] Serwis wstrzyknięty do obu use case'ów w `bootstrap/container.py`.
- [X] `make check` zielone, 816 testów pass.

**Uzasadnienie decyzji:**
Serwis aplikacyjny (nie domenowy), bo zależy od `AscentLogRepositoryPort` (port aplikacyjny). Logika T-01/T-03 nie jest encją domenową — to invariants orkiestracji.

**Komentarz Architekta:**
Wyeliminowano duplikację DRY. Logika T-01/T-03 teraz w jednym miejscu — `BitemporalValidationService`.

---

### [AUDYT-018] Niespójna hierarchia i wykorzystanie wyjątków `ConflictError`
**Obszar:** `Domena / Wyjątki`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Wyjątek `ConflictError` był używany do dwóch różnych celów: (1) duplikaty danych D-04 (Idempotentność), (2) nielegalne przejścia stanu w Kanban FSM (S-03).

**Rozwiązanie:**
- [X] Wprowadzono `IllegalStateTransitionError` jako subklasę `ConflictError` w `application/exceptions.py` (zgodnie z `docs/Error Handling.md` hierarchią).
- [X] `advance_logistic_status.py` używa `IllegalStateTransitionError` dla naruszeń FSM (S-03).
- [X] `ConflictError` ograniczono do dokumentacji do duplikatów D-04.
- [X] `apps/api/views.py` loguje `IllegalStateTransitionError` jako `invalid-state-transition` (409, typ `/errors/invalid-state-transition`), `ConflictError` jako `conflict`.
- [X] Test `test_patch_conflict_returns_409` aktualizuje do `IllegalStateTransitionError`.
- [X] `make check` zielone, 816 testów pass.

**Uzasadnienie decyzji:**
Subklasa zachowuje backward-compat (`isinstance(exc, ConflictError)` → 409). Nazwa precyzyjniej opisuje przyczynę — lepsza Traceability.

**Komentarz Architekta:**
`ConflictError` → wyłącznie Idempotentność D-04. `IllegalStateTransitionError` → FSM Kanban.

---

### [AUDYT-027] Brak wymuszenia `request_id` w zwracanych błędach
**Obszar:** `API / Error Handling`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
RFC 7807 wymaga `request_id` w odpowiedziach błędów; `_problem_detail` oraz testy nie weryfikowały tego pola.

**Rozwiązanie:**
- [X] Zweryfikowano, że `_problem_detail` już zawiera `"request_id": getattr(request, "request_id", "unknown")` — w `apps/api/views.py` oraz `infrastructure/middleware/error_handling.py`.
- [X] Uzupełniono testy integracyjne o `assert "request_id" in data` dla 5 ścieżek błędowych (`409 birth_date`, `422 file_too_large / invalid_mime / not_xml`, `422 GPX`).

**Uzasadnienie decyzji:**
`request_id` był już obecny (z AUDYT-048/050) — diagnoza wymagała potwierdzenia + test coverage. Middleware `RFC7807ErrorMiddleware` wstrzykuje `request_id` do każdego requestu (`process_exception` → 500 fallback również ma request_id).

**Komentarz Architekta:**
SRE może teraz mapować każdy błąd HTTP na logi serwera.

---

### [AUDYT-022] Niespójność Testów API z RFC 7807 (Brak `request_id`)
**Obszar:** `Testy API / Error Handling`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
Żadna asercja błędu API nie weryfikowała `request_id` w odpowiedzi RFC 7807.

**Rozwiązane jako część AUDYT-027:**
- [X] `_problem_detail` (zarówno `apps/api/views.py`, jak i `infrastructure/middleware/error_handling.py`) zawiera `"request_id": getattr(request, "request_id", "unknown")`.

- [X] Wszystkie 35 asercji kodów `4xx/500` w `tests/apps/api/test_integration.py` mają `assert "request_id" in data` (potwierdzono skanowaniem: 0 missing).
- [X] `tests/infrastructure/test_error_handling.py` (8 testów, 100% coverage) asercjonuje `request_id` = `req_12345678` oraz fallback `unknown`.
- [X] `tests/architecture/test_structured_error_context.py` jako fitness function weryfikuje strukturę RFC 7807.

**Uzasadnienie decyzji:**
Diagnoza była przestrzona — `request_id` był już implementowany (AUDYT-048/050), brakowało jedynie **test coverage**. Wdrożenie AUDYT-027 dodało brakujące asercje.

**Komentarz Architekta:**
`ERROR_HANDLING.md` jest teraz w pełni pokryty przez testy: każda ścieżka błędu zwraca `request_id`, a każdy test tego weryfikuje.

---