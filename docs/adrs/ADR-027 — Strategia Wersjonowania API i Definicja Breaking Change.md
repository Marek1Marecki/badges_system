# ADR-027 — Strategia Wersjonowania API i Definicja Breaking Change

> **Status:** `accepted`
> **Data:** 2026-09-05
> **Autor:** AI Architect
> **Zastępuje:** Fragment linii 10 w `API Contracts.md` ("Zasada Wersjonowania")
> **Zastąpiony przez:** [Brak]

---

## Kontekst

Plik `API Contracts.md` definiuje ścieżki w formacie `/api/v1/`, ale nie definiuje, **co** spowoduje przejście na `/api/v2/`. Brak formalnego kontraktu definiującego *Breaking Change* zwiększa ryzyko nieświadomego uszkodzenia klientów API, gdy wprowadzamy nowe zmiany do `v1`.

**Pytanie decyzyjne:**
Jaką strategię wersjonowania API przyjąć, aby zapewnić stabilność dla istniejących klientów (HTMX/JS) przy jednoczesnym umożliwieniu ewolucji API bez konieczności natychmiastowego przełączania wszystkich klientów na nową wersję?

---

## Opcje rozważane

### Opcja A: URL Path Versioning (`/api/v1/`, `/api/v2/`)
**Opis:** Standardowy prefix URL określa wersję API. Każda wersja ma własny namespace.
**Plusy:**
- Najprostsza implementacja w Django (`include("v1/urls.py", "v2/urls.py")`)
- Każda wersja może istnieć równolegle (deprecjacja)
- Transparentna dla debugowania i monitorowania (różne logi dla v1/v2)
- HTMX/JS klienci mogą być migracowani stopniowo
**Minusy:**
- Duplikacja kodu pomiędzy wersjami (można łagodzić przez współdzielenie portów/use-case'ów)
- Dłuższe URL-e

### Opcja B: Header-based Versioning (`Accept: application/vnd.appname.v1+json`)
**Opis:** Wersja określana jest w nagłówku `Accept`.
**Plusy:**
- Krótsze URL-e
- Czystszy interfejs REST
**Minusy:**
- Trudniejsze debugowanie (nagłówki nie są widoczne w URL barze)
- Trudniejsze cacheowanie (varnish/CDN trzeba uwzględniać nagłówki)
- Zgodność z OpenAPI/Swagger mniej intuicyjna
- HTMX nie obsługuje nagłówków `Accept` w formularzach

### Opcja C: Query Param Versioning (`/api/ascents/?v=2`)
**Opis:** Wersja jako parametr zapytania.
**Plusy:** Prosty do implementacji
**Minusy:**
- Query params nie są cache-friendly (CDN ignoruje je w cache keys)
- Łamie semantykę REST (`/api/ascents/` ≠ `/api/ascents/?v=2`)
- Trudne do monitorowania i rate-limitingu

---

## Decyzja

Wybieramy **Opcję A: URL Path Versioning (`/api/v1/`, `/api/v2/`)**.

**Zasady wdrożenia:**

1. **Prefix URL** `/api/v1/` jest obowiązkowy dla wszystkich endpointów publicznych i prywatnych. Każda zmiana wersji wymaga nowego prefixu (np. `/api/v2/`).

2. **Definicja Breaking Change** (co wymaga inkrementacji wersji `v1` → `v2`):
   - **Usunięcie pola** z payloadu JSON odpowiedzi (request field)
   - **Usunięcie pola** z request payloadu
   - **Zmiana typu danych** pola (np. `int` → `str`, `date` → `datetime`)
   - **Zmiana wymagania pola** z opcjonalnego na wymagane (lub odwrotnie)
   - **Zmiana kodu błędu** (np. zwracanie innego HTTP status niż dokumentowany)
   - **Zmiana struktury odpowiedzi** (np. przekształcenie listy zwracanej jako array na obiekt `data: []`)
   - **Usunięcie endpointu** (bez zapewnienia migracji do nowego URL)

3. **NIE Breaking Change** (nie wymaga inkrementacji wersji):
   - **Dodanie nowego pola** do odpowiedzi JSON (opcjonalne pole)
   - **Dodanie nowego pola** do request (ze wskazówką `default`)
   - **Dodanie nowego endpointu** (`/api/v1/new-feature`)
   - **Zmiana komunikatu błędu** (tekst ciała, ale nie kodu statusu)
   - **Rozszerzenie istniejącego pola** o nowe wartości enum

4. **Polityka deprecjacji:** Stara wersja `v1` musi być wspierana przez **co najmniej 3 miesiące** po wydaniu `v2`, z dokumentowanym planem usunięcia. Każde `v1` endpointy oznaczone w OpenAPI jako `deprecated: true` wygenerują warning w logach.

5. **OpenAPI jako jedyny autorytatywny kontrakt:** `config/openapi.json` jest źródłem prawdy. Test `test_api_contract_consistency.py` blokuje CI, jeśli `urls.py` ≠ `openapi.json`.

---

## Konsekwencje

### Pozytywne
- Stabilny interfejs dla klientów aplikacji mobilnych (gdy zostaną dodane)
- Transparentny plan migracji (klienci wiedzą, że mają 3 miesiące)
- Łatwe debugowanie i monitoring (różne wersje w logach CD)
- Zgodność z zasadą "version URI = resource identifier"

### Negatywne / Działania wymagane
- **Zadanie do backlogu:** Gdy `v2` będzie potrzebne, utworzyć `apps/api/v2/urls.py` i `config/openapi.v2.json`, zaktualizować router Django.
- **Praca deweloperska:** Duplikacja use-case'ów pomiędzy wersjami — wstępnie rozwiązywane przez współdzielenie `application/` (czysta logika) i jedynie osobną warstwę adapterów w `apps/api/v1/` vs `apps/api/v2/`.

---

## Warunek rewizji (Trigger for Review)

Zrewidować strategię, gdy:
- **Ruch API przekroczy 10,000 żądań dziennie** (rozważyć dodatkowo Header-based jako optymalizację CDN)
- **Pojawi się wymóg Single Sign-On (SSO) dla partnerów B2B**, którzy domagają się `application/vnd.vendor.v2+json`

---

## Relacje (Related)
- **C4 Diagram:** Brak
- **Kontrakty:** `API Contracts.md` (linia 10) — zaktualizowany o odniesienie do tego ADR
- **Dług (Debt):** Brak — dotychczasowe `/api/v1/` automatycznie objęte tą strategią
