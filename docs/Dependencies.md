# Dependencies — zależności zewnętrzne

> **Wersja:** 1.2  
> **Data:** 2026-05-30  
> **Właściciel:** Dominik / AI Architect  
> **Aktualizuj** przy każdej zmianie zależności w `pyproject.toml` (oraz przy rygorystycznym zatwierdzaniu `uv.lock`).

---

## Zasady zarządzania zależnościami

1. **Zero cichych instalacji:** Każda zależność ma udokumentowany **powód wyboru** w tym dokumencie.
2. **Izolacja:** Zależności `production` i `dev` są trzymane osobno. Projekty GIS wymagają minimalizacji paczek produkcyjnych.
3. **Zamrożenie:** Wersje w CI/CD oraz środowisku produkcyjnym są **przypięte** w pliku `uv.lock` (użycie `--frozen` przy instalacji).
4. **Minimalizm Czystej Domeny:** Zabrania się dodawania jakichkolwiek zależności zewnętrznych do użytku w katalogu `domain/` (obowiązuje *Domain Purity Contract*).

---

## Narzędzia agentów LLM (nie są zależnościami aplikacji)

> Ta sekcja dokumentuje narzędzia używane przez developerów i agentów podczas pisania kodu. Nie trafiają one do instalatorów środowiska.

| Narzędzie | Wersja / model | Cel | Zasady użycia |
|-----------|---------------|-----|---------------|
| Claude / GPT-4 | Najnowszy model "Reasoning" | Agent kodujący, architektoniczny | Zawsze wczytuje `SYSTEM_PROMPT.md` + odpowiednią sekcję `AGENT_SPEC.md`. Obowiązuje ścisły zakaz wymyślania nazw pakietów do instalacji bez zgody programisty. |
| IDE z AI | — | Edytor z agentem inline | Konfiguracja w `.cursorrules` lub manualne odpytywanie w odizolowanym kontekście okna czatu. |

---

## Zewnętrzne API i usługi (Third-Party Services)

Architektura zakłada minimalizację zewnętrznych zależności sieciowych, w szczególności w trakcie żądań HTTP użytkownika (tzw. hot path). 

| Usługa | Cel | Klucz API? | Fallback jeśli niedostępna |
|--------|-----|------------|---------------------------|
| **Overpass API (OSM)** | Zasilanie `TouristObject` danymi topograficznymi, wysokościami i językami. | Nie | Brak dostępności rozwiązany przez maszynę asynchroniczną. Celery ponawia próbę wg zasady Linear Backoff. Po wyczerpaniu puli (np. 15 prób), wejście w bazie przyjmuje status `ERROR` z opisem awarii i czeka na interwencję administratora. System odznak działa niewzruszenie na starych danych. |

---

## Zależności produkcyjne (Aplikacja i Infrastruktura)

### Biblioteki Core (Szkielet)

| Pakiet | Wersja | Licencja | Powód wyboru | Alternatywy rozważane |
|--------|--------|----------|--------------|----------------------|
| `Django` | `>=6.0.3` | BSD | Dostarcza wbudowany panel Admina, uwierzytelnianie, ORM oraz potężne wsparcie dla GIS. Błyskawiczny Time-to-Market dla narzędzi kuratorskich. | FastAPI (Odrzucone z powodu braku gotowego panelu administracyjnego dla GIS). |
| `psycopg` | `>=3.3.3` | LGPL | Nowoczesny (v3), oficjalny adapter PostgreSQL dla Pythona. Niezbędny do połączenia z bazą. | — |
| `pydantic` | `>=2.8.0` | MIT | Niezrównana weryfikacja i walidacja danych dla DTO (`application/dto/`) oraz adapterów (np. `OsmNodeDTO`). Odrzuca błędne struktury na granicach systemu. | `dataclasses` (Brak wbudowanej, zagnieżdżonej walidacji wejść). |
| `pydantic-settings` | `>=2.4.0` | MIT | Centralne źródło prawdy dla środowiska. Gwarantuje walidację typów dla konfiguracji w warstwie `bootstrap`. | `os.getenv` w kodzie (Zakazane kontraktem). |
| `python-dateutil` | `>=2.9.0` | Apache-2.0 | Zaawansowana obsługa czasu. **UWAGA (Domain Purity):** Używana wyłącznie w warstwie `infrastructure/` (np. przez adaptery kalendarzowe). W procesie refaktoryzacji biblioteka ta została usunięta z `domain/rules`, by zachować czystość 100% `stdlib`. | Wbudowany `datetime.replace` (użyty ostatecznie w Czystej Domenie dla lat przestępnych). |
### Geografia i Panel Administracyjny

| Pakiet | Wersja | Licencja | Powód wyboru | Alternatywy rozważane |
|--------|--------|----------|--------------|----------------------|
| `django-leaflet` | `>=0.30.0`| MPL | Zastępuje domyślne, ciężkie OpenLayers w panelu Django Admin. Gwarantuje piękny, sprzętowo wspomagany i zablokowany tryb "Read-Only" dla poligonów regionów. | Czyste OpenLayers (Toporne API, trudności w formatowaniu). |
| `django-jsonform`| `>=2.22.0`| MIT | Pozwala na dynamiczne renderowanie formularzy w Django Adminie na podstawie JSON Schema. To fundament do wprowadzania naszych Reguł Biznesowych. | Zwykłe pola tekstowe JSON (Fatalny UX dla administratora). |
| `django-tinymce` | `>=4.1.0` | MIT | Bogaty edytor WYSIWYG. Używany wyłącznie dla pola `BadgeVersionModel.rules_text` do bezpiecznego formatowania historycznych treści regulaminów PTTK jako read-only archiwum (bez ingerencji w weryfikację). | — |

### Zasilanie Asynchroniczne (Data Ops)

| Pakiet | Wersja | Licencja | Powód wyboru |
|--------|--------|----------|--------------|
| `celery` | `>=5.6.3` | BSD | Standard branżowy do offloadowania ciężkich operacji (PostGIS, strzały do API OSM) z głównego wątku HTTP. |
| `redis` | `>=5.0.0` | MIT | Szybki i sprawdzony broker dla Celery oraz backend dla wyników (`result_backend`). |
| `django-celery-beat`| `>=2.6.0` | BSD | Umożliwia dynamiczne definiowanie harmonogramów (Nocny Stróż OSM) z poziomu interfejsu graficznego Django Admina. |

### Obserwowalność (Observability)

| Pakiet | Wersja | Licencja | Powód wyboru |
|--------|--------|----------|--------------|
| `loguru` | `>=0.7.0` | MIT | Zastępuje wbudowany moduł `logging`. Umożliwia prostą definicję `logger.exception()` oraz tryb JSON na produkcji dla całego systemu. |

---

## Planowane zależności (Faza C - Kontekst Użytkownika)

Wchodząc w etap logowania wejść (`AscentLog`) i obsługi klientów mobilnych, architektura będzie musiała poszerzyć stos o następujące pakiety:

| Pakiet | Cel | Status |
|--------|-----|--------|
| `Pillow` | Obsługa weryfikacji i konwersji załączników (dowodów w postaci zdjęć w `AscentLog`). | **Oczekuje na instalację.** |
| `django-ninja` *LUB* `djangorestframework` | Wystawienie endpointów REST dla aplikacji mobilnej z twardym formatowaniem `RFC 7807` dla błędów. | **Do decyzji (Wymagany nowy dokument ADR-010).** |

---

## Zależności deweloperskie (Grupa `dev`)

Nie są instalowane w obrazie produkcyjnym. Służą wyłącznie do utrzymania kontraktów jakości kodu i testów.

| Pakiet | Wersja | Cel |
|--------|--------|-----|
| `ruff` | `>=0.4.0` | Ultrszybki Linter i Formatter. Egzekwuje zakaz `datetime.now()` (TID251) oraz weryfikuje Docstringi. |
| `mypy` | `>=1.10.0`| Rygorystyczny type-checking, używany w trybie `--strict` dla `domain/` i `application/`. |
| `types-python-dateutil` | `>=2.9.0` | Definicje typów dla `dateutil` (Wymagane przez `mypy` do sprawdzania operacji `TimeLimitRule`). |
| `import-linter` | `>=2.0` | Strażnik Czystej Architektury. Zrzuca pipeline CI, jeśli `domain/` spróbuje zaimportować cokolwiek z Django. |
| `pytest` | `>=8.2.0` | Główne środowisko testowe. |
| `pytest-django` | `>=4.8.0` | Pozwala na używanie znaczników `@pytest.mark.django_db` dla testów integracyjnych z PostGISem. |
| `pytest-cov` | `>=5.0.0` | Weryfikacja progu minimalnego (80%) pokrycia kodu w CI. |
| `pre-commit` | `>=3.7.0` | Lokalne egzekwowanie kontraktów (uruchamia `make check` na maszynie dewelopera przed `git push`). |

---

## Pakiety odrzucone / usunięte w toku prac

W trakcie rozwoju projektu dokonano świadomych redukcji zależności, aby zminimalizować powierzchnię ataku i dług technologiczny.

| Pakiet Usunięty | Powód usunięcia | Czym zastąpiono |
|-----------------|-----------------|-----------------|
| `httpx` | Mimo że jest to nowoczesna biblioteka, restrykcyjne zapory WAF (Proxy) serwerów OpenStreetMap rzucały z nią błędy `406 Not Acceptable`. Konieczność surowej kontroli nad nagłówkami HTTP (udawanie przeglądarki Chrome, brak narzuconego `Content-Type`) przesądziła o usunięciu. | Wbudowany w bibliotekę standardową moduł `urllib.request`. System "udaje" przeglądarkę Chrome za pomocą czystych, nieskażonych frameworkiem nagłówków HTTP. |

---

## Security audit

```bash
# Weryfikacja czystości środowiska Pythonowego
uv audit
```
*(Zasada w projekcie: Uruchamiane jako część cyklicznych audytów bezpieczeństwa CI/CD. Wykrycie podatności o statusie CRITICAL lub HIGH w obrazie/zależności blokuje wydanie w pipeline).*

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany                                                                                                                                                                                                                    |
|--------|------|-------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1.0 | 2026-05-29 | Dominik / AI Architect | Pierwsza wersja, definiująca kompletny stos dla Fazy A i B. Udokumentowano usunięcie paczki `httpx`.                                                                                                                           |
| 1.1 | 2026-05-29 | AI Architect | Synchronizacja wersji z plikiem `pyproject.toml`, dodanie sekcji `Planowane zależności (Faza C)`, dodanie sekcji usług zewnętrznych (Overpass API) oraz uwzględnienie stubs dla Mypy (`types-python-dateutil`).                |
| 1.2 | 2026-05-30 | Dominik / AI Architect | Skorygowałem wpadkę architektoniczną. Wyjaśniłem, że `dateutil` jest używane, ale **zostało wyrzucone z Czystej Domeny** podczas naszej refaktoryzacji, i zostaje zachowane tylko jako narzędzie pomocnicze w infrastrukturze! |

