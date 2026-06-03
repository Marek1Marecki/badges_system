# ADR-012 — Weryfikacja celów otwartych geograficznie (Wildcard JSON Rules)

> **Status:** `accepted`  
> **Data:** 2026-05-30  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Zgodnie z `ADR-009` (Pool-based Set Verification), domyślnym i preferowanym mechanizmem weryfikacji odznak jest przecinanie zbioru wejść turysty z zamkniętą pulą identyfikatorów szczytów (`pool_peaks` przypinane do Wersji Odznaki).
Jednakże, analiza regulaminów PTTK wykazuje istnienie odznak o charakterze terytorialnie otwartym, np.: *"Zdobądź dowolne 20 szczytów leżących w granicach Beskidu Żywieckiego"*. Regulaminy te nie posiadają oficjalnego, zamkniętego wykazu obiektów (załącznika).

**Pytanie decyzyjne:**  
W jaki sposób technicznie obsłużyć weryfikację odznak bez sztywnego wykazu obiektów, unikając jednocześnie ręcznego przypinania setek potencjalnych szczytów do puli `pool_peaks` przez Administratora i nie łamiąc Czystości Domeny (Invariant R-01)?

---

## Debata przed decyzją

**Software Architect:** Utrzymajmy dogmat z `ADR-009`. Wymuśmy na administratorze, aby przy tworzeniu odznaki wyfiltrował w panelu obiekty z Beskidu i kliknął "Wybierz wszystkie". Jeśli Domena musi weryfikować geografię z pominięciem puli M2M, złamiemy zasadę bezstanowości.  
**Domain Expert / Administrator:** Zmuszenie mnie do przypinania wszystkich gór Beskidu na sztywno rodzi gigantyczne ryzyko operacyjne. Za pół roku "Nocny Stróż" (Celery) zaciągnie z OSM nową wieżę w Beskidzie. Jeśli nie dodam jej ręcznie do zamkniętej puli odznaki, turysta wejdzie na nią i zostanie odrzucony przez system. System sam musi akceptować wszystko, co wpadnie w granice danego terytorium.  
**Data Integrity Engineer:** Możemy oddelegować ten licznik do reguły JSON (np. `RegionCountRule`), omijając pulę M2M. Jednak musimy uważać, by nie wpuścić do domeny obiektów `ObjectRegionCache`! Domena nie może wywoływać ORM-a.  

*Wniosek z debaty:* Elastyczność i bezobsługowość na przyszłe dane OSM wymusza wyłom od `ADR-009` dla tego specyficznego typu odznak. Logika zliczania zostaje przeniesiona do Wzorca Strategii (JSON). Naruszenie czystości domeny (R-01) jest pozorne i zostanie zabezpieczone przez wstrzyknięcie wymaganej wiedzy terytorialnej z zewnątrz, na poziomie budowania DTO w warstwie Aplikacji.

---

## Opcje rozważane

### Opcja A: Wymuszone zamknięcie zbioru (Forced Pool Initialization)
**Opis:** Administrator musi ręcznie podpiąć wyfiltrowane obiekty z regionu do relacji M2M w panelu.
**Plusy:** Pełna zgodność z `ADR-009`.
**Minusy:** Brak elastyczności, odznaka staje się "przestarzała" w dniu pojawienia się nowego węzła z OSM na tym terytorium.

### Opcja B: Wzorzec Strategii z wstrzyknięciem kontekstu (Wildcard JSON Rules)
**Opis:** Dla odznak terytorialnych pole `pool_peaks` pozostaje puste. Dodajemy do bazy nową regułę biznesową `RegionCountRule(region_id=15, required_count=20)`. Warstwa Aplikacji (Use Case), budując obiekt weryfikacji, odpytuje CQRS i dokleja do każdego wejścia (`Ascent`) płaską listę identyfikatorów jego regionów (`region_ids: frozenset[int]`). 
Domena (Sito) liczy wejścia, dla których przekazany zbiór `region_ids` przecina się z `region_id` zdefiniowanym w regule.

---

## Decyzja

**Wybrano: Opcja B — Wzorzec Strategii z wstrzyknięciem kontekstu (Wildcard JSON Rules)**

Decyzja ta gwarantuje bezobsługowość systemu przy napływie nowych danych z OSM, zachowując bezwzględnie zasady *Domain Purity*. Reguła `RegionCountRule` żyjąca w domenie nie wywołuje postGIS, nie wie nic o geografii ani geometriach — dokonuje jedynie szybkiego przecięcia matematycznego między własnym ID a zbiorem dostarczonym przez DTO, całkowicie zachowując Invariant R-01.

---

## Konsekwencje

### Pozytywne
- System natywnie "uczy się" zdobywania otwartych odznak – każdy nowo powstały szczyt przypisany asynchronicznie przez Celery do Beskidu Żywieckiego od razu punktuje turystom.
- Zachowano wydajność `O(1)` przy ewaluacji (czyste zbiory w RAM).

### Negatywne / Ograniczenia
- Rozmycie Odpowiedzialności (Responsibility Blur). Zliczanie zdobytych szczytów realizowane jest dwutorowo (zwykle na poziomie bazy i agregatu `BadgeVersionDomain.required_count`, a tu na poziomie strategii `BadgeRule`).
- Wymuszone "spuchnięcie" wchodzącego DTO (`AscentContextDTO`), które musi taszczyć za sobą identyfikatory regionów na okoliczność, gdyby któraś reguła ich potrzebowała.

### Działania wymagane (Do realizacji w Fazie C)
- [ ] Zaktualizowanie `INVARIANTS.md` o nowy kontrakt `R-03`.
- [ ] Zaprojektowanie wzbogaconego DTO (`AscentContextDTO` / `VerificationContext`) posiadającego zbiór `region_ids: frozenset[int]` w warstwie `application/`.
- [ ] Oprogramowanie klasy `RegionCountRule` w warstwie `domain/rules/`.

---

## Warunek rewizji

Gdy więcej niż 30% odznak w systemie zacznie korzystać z weryfikacji opartej o `RegionCountRule` (zamiast standardowego `pool_peaks`). Wtedy należy rozważyć generalną refaktoryzację silnika ewaluacyjnego i ujednolicenie mechanizmów zliczania, tak aby pozbyć się dwutorowości systemu.

---

## Referencje
- **ADR-009 — Weryfikacja wejść jako operacje na zbiorach.** Niniejszy dokument sankcjonuje celowe i strukturalnie odizolowane odstępstwo od bazowego założenia ADR-009 w zakresie pominięcia zamkniętej listy M2M `pool_peaks`.
- `INVARIANTS.md` — Reguła R-01 (zachowana) oraz nowa reguła R-03.