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
