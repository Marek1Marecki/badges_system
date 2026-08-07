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
- [ ] Przejrzeć katalog `docs/Manifest/` i usunąć wszelkie odniesienia do zewnętrznych, starych projektów.
- [ ] Dopasować nazwy weryfikowanych plików (np. `Data Flow Diagram.md` zamiast `DATAFLOW.md`), aby linter dokumentacji nie zgłaszał fałszywych błędów o brakujących plikach.

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