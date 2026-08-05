# Scripts — przewodnik po narzędziach pomocniczych

> **Wersja:** 1.0  
> **Data:** 2026-06-02  
> **Właściciel:** Dominik / AI Architect  
> **Cel:** Opis niezależnych skryptów uruchomieniowych w katalogu `scripts/`, które służą do zarządzania jakością danych, diagnostyki i egzekwowania kontraktów.

---

## 1. Narzędzia Jakości Danych (Data Stewardship)

Skrypty te są używane przez Administratorów i Kuratorów Danych w celu weryfikacji integralności bazy "Złotego Standardu". Wymagają uruchomionej bazy PostGIS.

### `check_badge_pools.py`
* **Uruchomienie:** `uv run python scripts/check_badge_pools.py`
* **Co robi:** Odpytuje bazę danych i generuje w terminalu przejrzyste drzewo tekstowe wszystkich zdefiniowanych odznak, ich wersji, reguł biznesowych z JSONB oraz pełnej listy przypisanych do nich obiektów z Puli Szczytów.
* **Kiedy używać:** Zawsze po zdefiniowaniu nowej, skomplikowanej odznaki (tzw. Sanity Check), aby upewnić się wzrokowo, że nie zapomniano przypisać szczytów, a reguły i stopnie zostały poprawnie odczytane przez adapter bazy danych.

### `check_orphaned_objects.py`
* **Uruchomienie:** `uv run python scripts/check_orphaned_objects.py`
* **Co robi:** Wyszukuje tzw. "Sieroty" — Obiekty Turystyczne, które znajdują się w naszej bazie, ale nie są przypięte do `pool_peaks` żadnej z wersji odznak.
* **Kiedy używać:** Okresowo (np. raz w miesiącu) do audytu bazy. Ułatwia decydowanie, czy "osierocone" obiekty należy podpiąć do nowych odznak, czy usunąć (soft delete), by nie zaśmiecały bazy i Radarów Klastrowania.

### `check_missing_wiki.py`
* **Uruchomienie:** `uv run python scripts/check_missing_wiki.py`
* **Co robi:** Zwraca listę obiektów, dla których system (i ekstraktor OSM) nie potrafił znaleźć linku do Wikipedii. 
* **Uwaga architektoniczna:** Skrypt celowo omija domyślne, alfabetyczne sortowanie modelu i wymusza sortowanie po `id` (chronologicznie), ułatwiając metodyczną pracę naprawczą (zgodnie z `AGENT_SPEC.md`).
* **Kiedy używać:** Głębsze prace redakcyjne nad wzbogacaniem bazy (uzupełnianie danych ręcznych w panelu Django).

---

## 2. Diagnostyka i Development

Skrypty wspierające programistów w testowaniu usług zewnętrznych lub symulowaniu środowiska Fazy C przed zbudowaniem właściwego Frontendu.

### `test_osm.py`
* **Uruchomienie:** `uv run python scripts/test_osm.py`
* **Co robi:** Uruchamia klienta `OverpassClient` dla z góry zdefiniowanego w kodzie identyfikatora (np. `node/477984782` - Kremenaros) i przeprowadza ekstrakcję danych (`OsmDataExtractor`), wypisując do konsoli surowe i przetworzone tagi.
* **Kiedy używać:** Niezastąpione narzędzie przy awariach pobierania danych w Django Admin. Jeśli maszyna asynchroniczna zrzuca obiekt w tryb `ERROR`, używamy tego skryptu do debugowania, "co dokładnie zwracają Niemcy", i testowania skuteczności nagłówków User-Agent.

### `simulate_user.py`
* **Uruchomienie:** `uv run python -m scripts.simulate_user`
* **Uwaga architektoniczna:** Skrypt musi być uruchamiany poprzez flagę modułu `-m` z głównego katalogu projektu, aby Python poprawnie podpiął ścieżki do kontenera DI (`bootstrap`).
* **Co robi:** Integracyjny "Poligon Doświadczalny". Ładuje z bazy prawdziwe szczyty, buduje w pamięci fikcyjne dzienniki wejść turystów i przepuszcza je przez `VerifyBadgeUseCase`.

---

## 3. Strażnicy Architektury (CI / CD)

Te skrypty są integralną częścią potoku CI (Continuous Integration). Uruchamiane automatycznie poprzez komendę `make check`.

### `audit_contracts.py`
* **Uruchomienie:** `uv run python scripts/audit_contracts.py`
* **Co robi:** Analizator Drzewa Składniowego (AST) dla Pythona. Bezwzględny sędzia architektury heksagonalnej. Wyłapuje rzeczy niewykrywalne przez standardowe lintery: użycie `datetime.now()` w Domenie, próby importów ukrytych w blokach `TYPE_CHECKING`, importy ORM-a z Django do Use Case'ów. Dodatkowo generuje mapy powiązań w pliku `.dot` / `.svg`.
* **Kiedy używać:** Uruchamia się automatycznie przy każdym `make check`. W przypadku błędu na czerwono, PR nie ma prawa być wdrożony.

### `check_secrets.py`
* **Uruchomienie:** `uv run python scripts/check_secrets.py` (lub `make secrets-check`)
* **Co robi:** Porównuje aktualne zmienne środowiskowe (lokalnie lub w kontenerze) z kluczami zadeklarowanymi w pliku `.env.example`.
* **Kiedy używać:** Służy jako mechanizm Fail-Fast przy uruchamianiu środowiska i w potokach CI. Jeśli dodasz nowy sekret do systemu, skrypt natychmiast wyrzuci błąd w CI, dopóki administrator nie doda go do Github Secrets.

---

## Zasady dla Agentów LLM (Tworzenie nowych skryptów)

1. **Inicjalizacja Django:** Każdy nowy skrypt w tym katalogu, który musi odpytać bazę danych lub użyć logiki aplikacji, musi bezwzględnie posiadać na początku (przed jakimikolwiek importami z `apps/` lub `domain/`) sekwencję inicjalizującą:
   ```python
   import os, sys

   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
   import django

   django.setup()
   ```
2. **Kapsułkowanie importów (Ruff E402):** Aby nie łamać zasad lintera (importy na poziomie modułu po wywołaniu funkcji), wszystkie importy z naszego systemu (np. `from apps.badges.models import...`) muszą znajdować się **wewnątrz głównej funkcji skryptu** (np. `def generate_report():`).
3. **Sortowanie diagnostyczne:** W skryptach szukających anomalii (np. braki, duplikaty), kategorycznie nakazuje się nadpisywanie domyślnego sortowania modeli poprzez nałożenie `order_by('id')` lub `order_by('created_at')`.