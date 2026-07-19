# ADR-024 — Strategia Migracji Bazy Danych (Zero-Downtime & Expand-Contract)

> **ADR Status:** `accepted`  
> **Implementation Status:** `planned`  
> **Data:** 2026-07-23  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Aplikacja przeszła w fazę produkcyjną i obsługuje realnych użytkowników. Wdrażanie nowych funkcjonalności (Application Release) regularnie wymaga modyfikacji schematu relacyjnej bazy danych (dodawanie/usuwanie kolumn, zmiana typów). 

Zgodnie z `ADR-020`, architektura wymaga, by każde wdrożenie umożliwiało błyskawiczny Rollback (powrót) do poprzedniego obrazu kontenera bez konieczności oczekiwania na cofnięcie migracji na produkcji (Rolling Back migrations). Dodatkowo, podczas wdrażania nowej wersji (Rolling Deployment), stara i nowa wersja aplikacji może przez chwilę działać równolegle na tym samym, współdzielonym schemacie bazy danych.

Wykonanie standardowej migracji destrukcyjnej (np. `DROP COLUMN` lub `ALTER TABLE TYPE`) w trybie natychmiastowym sprawi, że działający jeszcze, starszy kod aplikacji zgłosi krytyczny błąd bazy danych (Downtime) lub po wdrożeniu Rollbacku aplikacja nie będzie potrafiła operować na bazie, co wymusi ręczną interwencję.

**Pytanie decyzyjne:**  
Jak ustandaryzować proces pisania i wdrażania migracji schematu w Django, aby zminimalizować ryzyko przerw w działaniu (Zero Downtime Deployments) i w 100% wspierać mechanizm błyskawicznego wycofywania wersji (Rollback)?

---

## Opcje rozważane

### Opcja A: Tradycyjne Migracje z Oknem Serwisowym (Maintenance Window)
**Opis:** Każde wdrożenie wymagające migracji bazy danych wiąże się z zamknięciem ruchu do aplikacji (Tryb Maintenance). Migracja zostaje wykonana, kod podmieniony, a ruch przywrócony.
**Plusy:** Najprostsze podejście deweloperskie. Framework Django obsługuje to domyślnie przez `makemigrations`. Brak konieczności utrzymywania kompatybilności wstecznej kodu.
**Minusy:** Odrzucenie wymogu Zero-Downtime. Bardzo kosztowny i stresujący Rollback (wymagający wstrzymania ruchu i wykonania `migrate <app> <stara_migracja>`).

### Opcja B: Wzorzec "Expand and Contract" z izolacją schematu od danych (Wybrane)
**Opis:** Migracje dzielone są na etapy. Operacje destrukcyjne nie są dozwolone w tym samym cyklu wydawniczym, który modyfikuje kod używający danego pola. Wymuszenie pisania kodu aplikacji zdolnego do działania w trybie tolerancji na obecność lub brak starych i nowych struktur. Twarde oddzielenie migracji schematu od skryptów przepisujących dane (Data Migrations).

---

## Decyzja

Wdrażamy rygorystyczną strategię migracji bazującą na wzorcu **Expand and Contract (Rozszerzaj i Kurcz)**. Od tego momentu każda migracja musi spełniać zasady Wstecznej Kompatybilności Schematu (Backward Compatible Schema). Wprowadza się ponadto poniższe żelazne wytyczne inżynieryjne:

### 1. Etapy Cyklu Życia Migracji

**A) Zasada Expand (Faza Rozszerzania):**
- Żadna migracja Expand nie może wprowadzać ograniczenia wymagającego obecności nowych pól po stronie istniejącego (starszego) kodu aplikacji. Nowe kolumny muszą być bezwzględnie dodawane jako opcjonalne (`null=True`). Dodawanie kolumn na dużej tabeli od razu z flagą `default="..."` może powodować kosztowną operację DDL lub blokadę, zależnie od wersji PostgreSQL i typu zmiany. Wypełnianie brakujących danych (Backfill) i ewentualne narzucenie restrykcji `NOT NULL` należy wdrażać etapami.
- Nowa wersja kodu aplikacji w tej fazie potrafi czytać starą strukturę, a nowe wartości bezpiecznie układa w nowej (opcjonalnej) kolumnie.

**B) Zasada Transition (Faza Przejściowa i Migracje Danych):**
- **Transactional Dual Write:** Jeśli cel wymaga transformacji danych (np. zmiana struktury pola `JSONB`), nowa wersja kodu aplikacji zapisuje w obu miejscach jednocześnie (Dual Write). Podwójny zapis musi być wykonywany w ramach jednej, atomowej transakcji bazodanowej (`transaction.atomic()`). Niedopuszczalne jest asynchroniczne uzupełnianie nowego pola, co rodziłoby ryzyko niespójności przy awarii między zapisami.
- **Rozdzielenie Operacji:** Migracje schematu (`AddField`, `AlterField`) oraz skrypty transformujące dane historyczne (`RunPython`, `RunSQL`) muszą być rozdzielone na osobne pliki migracji, a docelowo na osobne wdrożenia, aby zapobiec konfliktom stanu pomiędzy ORM a rzeczywistą strukturą bazy w locie.
- **Operacje Dużych Danych:** Migracje danych przekraczające ustalony próg (>100 tys. rekordów) muszą być wyizolowane jako asynchroniczne joby batchowe w Celery poza transakcją migracji Django. 
- Zmiana struktury z `NULL` na `NOT NULL` wymusza bezpieczny wzorzec PostgreSQL: dodanie kolumny `NULL` ➔ asynchroniczny *Backfill* ➔ dodanie w PostgreSQL `CONSTRAINT CHECK (col IS NOT NULL) NOT VALID` ➔ walidacja w tle (`VALIDATE CONSTRAINT`) ➔ dopiero ostateczne `SET NOT NULL`.

**C) Zasada Contract (Faza Kurczenia - Operacje Destrukcyjne):**
- **Operacją destrukcyjną** jest każda zmiana schematu, która może uniemożliwić działanie poprzedniej wersji aplikacji lub wymaga pełnej walidacji danych przed wykonaniem (np. usuwanie tabel, usuwanie kolumn, zmiana typu, restrykcje kluczy unikalnych, rename kolumn).
- **Kategoryczny zakaz wdrożeń łączonych:** Operacja destrukcyjna nie może znajdować się w tym samym Wydaniu (Application Release), w którym nowa struktura jest wprowadzana do użycia. Usunięcie starej struktury może odbyć się wyłącznie po wdrożeniu wersji kodu w 100% zignorowanej od usuniętego pola.

*(Przykład procesu podano w sekcji Konsekwencje).*

### 2. Ochrona Wydajności i Dostępności

- **Zakaz automatycznych indeksów Django:** Tworzenie indeksów na dużych tabelach na środowisku produkcyjnym **musi** odbywać się z użyciem mechanizmu `CREATE INDEX CONCURRENTLY` poza standardową transakcją Django migration (`atomic = False`). Automatyczne indeksy generowane przez `makemigrations` (`CREATE INDEX`) wymagają ręcznej rewizji i ewentualnego nadpisania instrukcją `RunSQL`.
- **Migration Timeout Policy:** Każda migracja produkcyjna musi posiadać bezwzględny limit czasu wykonania i blokady (Lock Timeout). W PostgreSQL w warstwie migracyjnej nadpisuje się to klauzulami: `SET lock_timeout='5s'; SET statement_timeout='15min';`. Przekroczenie limitu powoduje przerwanie migracji i wycofanie deploymentu, pozostawiając system w stanie początkowym.

### 3. Zależności i Pipeline Wdrożeniowy

- **Rozdzielenie Rollbacku Aplikacji od Danych:** Rollback obrazu kontenera (`app_only`) nie jest równoznaczny z rollbackiem stanu danych. Opcje rollbacku ze zmianą struktury bazy (lub powrotu do starszych danych logicznych) wymagają osobnej procedury (np. Restore Backupu lub kompensacyjnej migracji odwrotnej).
- **Test Kompatybilności Wstecznej w CI/CD (Dual-Version Testing):** Pipeline CI/CD na środowisku `TEST` lub `PRE-PROD` musi weryfikować wzorzec Expand-Contract poprzez uruchomienie *poprzedniej wersji* obrazu aplikacji na najnowszym *zmodyfikowanym schemacie bazy*. Gwarantuje to, że rollback aplikacji będzie fizycznie możliwy bez wycofania bazy.
- **Feature Flags (Flagi Funkcji):** Aktywacja nowej ścieżki biznesowej podczas fazy Transition powinna odbywać się w kodzie przez Feature Flag (`.env.shared`), a nie poprzez sam fakt wdrożenia obrazu z nowym modelem bazy.
- **Migration Ownership:** Każda złożona migracja destrukcyjna na produkcji posiada przypisanego Właściciela Biznesowo-Technicznego (Migration Owner), odpowiedzialnego za ocenę ryzyka, plan Expand/Contract, test wydajności i plan Rollbacku.

---

## Konsekwencje

### Wzorcowy Przykład Wdrożenia (Zmiana nazwy kolumny)

| Wdrożenie (Release) | Działanie na Bazie (Schemat) | Wersja Kodu Aplikacji |
| :--- | :--- | :--- |
| **R1 (Expand)** | `+ elevation (null=True)`<br>*(Stare `altitude` nienaruszone)* | Kod aplikacji bez zmian. Oczekuje tylko na starą kolumnę `altitude`. |
| **R2 (Transition)**| (Brak zmian schematu). Asynchroniczny skrypt przepisujący dane (Backfill) w tle. | Kod wspiera **Transactional Dual-Write** na obu kolumnach, ale odczytuje preferencyjnie z nowej `elevation`. |
| **R3 (Deprecate)** | Opcjonalnie: Zmiana na `NOT NULL` za pomocą `NOT VALID`. | Kod ulega uproszczeniu, całkowicie porzuca odwołania do `altitude`. Odczyt i zapis tylko na `elevation`. |
| **R4 (Contract)** | `DROP COLUMN altitude` | W 100% stabilny kod na zredukowanej bazie. Brak wycieku stanu. |

### Pozytywne
- **Zero-Downtime Deployments:** Aktualizacje aplikacji na produkcji odbywają się bez zamykania systemu. Stare i nowe kontenery mogą koegzystować.
- **Bezpieczny Rollback Aplikacji:** Natychmiastowe przywrócenie awaryjnego systemu po wadliwym wdrożeniu polega wyłącznie na zmianie wskazywanej wersji obrazu na starszą, co działa bezproblemowo, gdyż "stara" aplikacja zawsze znajduje starszy układ bazy, do którego została zaprogramowana.

### Negatywne / Działania wymagane
- Znacznie zwiększone "obciążenie poznawcze" (Cognitive Load) programistów. Narzędzie `makemigrations` musi być traktowane z rezerwą.
- Wymuszone zarządzanie cyklem życia starych ścieżek wejściowych w modelach DTO (Pydantic API). Rozszerzenie kontraktów komunikacyjnych podlega takim samym rygorom (dodanie pola do API JSON, usunięcie po okresie karencji).
- Utrzymanie tzw. długu przejściowego w kodzie Pythona przez kilka tygodni/miesięcy pomiędzy fazą Expand a Contract.

---

## Warunek rewizji

Strategia ta zakłada środowisko wysokiej dostępności (HA - High Availability). Podlega rewizji w przypadku, gdy zespół utrzymaniowy uzyska zgodę biznesową na regularne, awaryjne okna serwisowe (Maintenance Windows), podczas których ruch z zewnątrz (B2C) jest całkowicie odcinany. Zamknięty ruch eliminuje potrzebę utrzymywania zgodności dwóch wersji kodu równolegle na tym samym schemacie, dopuszczając klasyczny proces jednoczesnych, destrukcyjnych migracji bazy i wdrożenia nowej wersji.
