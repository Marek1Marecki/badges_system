# Invariants — niezmienniki systemu

> **Wersja:** 1.1  
> **Data:** 2026-05-27  
> **Właściciel:** Dominik / AI Architect  
>
> Każdy invariant to reguła biznesowa i architektoniczna, której naruszenie oznacza fatalny błąd systemu. Należy je bezwzględnie egzekwować podczas pisania Use Case'ów i modyfikacji bazy danych.

---

## Poziomy krytyczności

| Symbol | Znaczenie |
|--------|-----------|
| 🔴 KRYTYCZNY | Naruszenie powoduje uszkodzenie danych, utratę historii lub błędy bezpieczeństwa |
| 🟠 WYSOKI | Naruszenie powoduje błędne zachowanie widoczne dla użytkownika |
| 🟡 ŚREDNI | Naruszenie powoduje degradację funkcji, ale system działa |

---

## Grupa T — Czas i Bitemporalność

### T-01 — Cykl życia obiektu (Bitemporality) 🔴 KRYTYCZNY
**Treść:** Wejście na obiekt (`Ascent`) w dniu *X* jest niemożliwe logicznie i fizycznie, jeśli obiekt w tym czasie nie istniał fizycznie.  
Semantyka `NULL` (puste = dowolne):
- `existence_start = NULL` → obiekt istnieje od zawsze
- `existence_end = NULL` → obiekt istnieje bezterminowo  

**Uzasadnienie:** System operuje na historii PTTK. Spalenie schroniska (`existence_end`) w 2015 roku unieważnia wpisy z 2018 r., ale w 100% chroni prawa osób, które zdobyły je w 2010 r.
**Gdzie egzekwować:** 
- Use Case: `VerifyBadgeUseCase` (Faza C) – sprawdzane jako Krok 0 przed regułami.
- Test: `test_T01_ascent_outside_existence_window_is_rejected`

### T-02 — Determinizm Czasu (ClockPort) 🔴 KRYTYCZNY
**Treść:** `domain/` oraz `application/use_cases/` nigdy nie mogą wywoływać `datetime.now()` ani `timezone.now()`.
**Uzasadnienie:** Testowanie reguł zależnych od czasu (np. czy minęły 3 lata limitu) wymaga "zamrożenia" czasu. Każdy Use Case wymagający pojęcia "teraz" musi przyjmować wstrzykniętą instancję `ClockPort`.
**Gdzie egzekwować:** 
- Linter: `audit_contracts.py` oraz `ruff banned-api`.
- Test: `test_T02_domain_logic_uses_injected_clock`

---

## Grupa R — Reguły i Architektura Domeny

### R-01 — Matematyka Zbiorów zamiast GIS (Pool-based Set Verification) 🔴 KRYTYCZNY
**Treść:** Czysta Domena weryfikująca odznaki (`BadgeVersionDomain`) **nie wie** co to współrzędne GPS, PostGIS, czy `ST_DWithin`. Weryfikacja musi polegać na operacjach algebry zbiorów na identyfikatorach.
**Uzasadnienie:** Gwarantuje błyskawiczną weryfikację rzędu `O(1) / O(N)` i całkowicie oddziela proces decyzyjny PTTK od analityki przestrzennej.
**Gdzie egzekwować:** 
- Linter: `import-linter` (zakaz `django.contrib.gis` w domenie).
- Test: `test_R01_evaluate_uses_set_intersection_only`

### R-02 — Fail-Fast dla Fabryk Reguł (Hydracja z JSONB) 🟠 WYSOKI
**Treść:** Jeśli adapter (`django_badge_repo`) znajdzie w JSONie bazy nieznaną regułę lub regułę z brakującym wymaganym parametrem (np. brak wymogu wieku dla `MinAgeRule`), musi twardo rzucić `ValueError`.
**Uzasadnienie:** Ciche pominięcie uszkodzonej reguły skutkowałoby przyznaniem np. odznaki "Tylko dla 18+" ośmioletniemu dziecku. System musi zablokować weryfikację skażonego regulaminu.
**Gdzie egzekwować:** 
- Baza: `infrastructure/adapters/persistence/django_badge_repo.py` (`RULE_BUILDERS`).
- Test: `test_R02_invalid_rule_json_raises_value_error`

---

## Grupa D — Dane i Integralność Administracyjna

### D-01 — Unikalność kolejności stopni (Tiers) 🔴 KRYTYCZNY
**Treść:** W ramach jednej Wersji Regulaminu (`version_id`), wartość pola `order` (Kolejność zdobywania) musi być bezwzględnie unikalna.
**Uzasadnienie:** Dwa stopnie z numerem `order=1` zniszczą algorytm wyliczania postępu (Progress Bar) u Turysty.
**Gdzie egzekwować:** 
- Constraint DB: `UniqueConstraint` w `BadgeTierModel`.
- Walidator: `BadgeTierInlineFormSet`.
- Test: `test_D01_duplicate_tier_order_raises_integrity_error`

### D-02 — Złoty Standard ponad Automatyką (Data Overrides) 🟠 WYSOKI
**Treść:** Ekstraktor OSM zasilający model z Data Lake nigdy nie może nadpisać pól w Złotym Standardzie (np. `name`, `altitude`), jeśli Administrator wpisał tam własną, nienullową wartość.
**Uzasadnienie:** Ręczna edycja oznacza ingerencję autorytatywną. Nadpisanie jej przez nocnego stróża to utrata danych.
**Gdzie egzekwować:** 
- Formularz Admina: `TouristObjectAdminForm.clean()`.
- Adapter: `OsmRepository.update_object_from_osm()`.
- Test: `test_D02_data_override_protects_curated_fields`

---

## Grupa S — Stany i Cykl Życia Obiektu

### S-01 — Kierunkowość przepływu statusu 🟠 WYSOKI
**Treść:** `TouristObject.status` może przechodzić tylko w przód: `DRAFT` → `FETCHING_OSM` → `READY` lub `ERROR`. Cofnięcie do `DRAFT` jest niedozwolone architektonicznie.
**Uzasadnienie:** Zapewnienie jednokierunkowego cyklu życia chroni przed nieskończonymi pętlami asynchronicznego pobierania i zduplikowanymi taskami w Celery.
**Gdzie egzekwować:** 
- Adapter/Model: `OsmRepository.update_object_from_osm()`.
- Test: `test_S01_invalid_status_transition_raises_error`

### S-02 — Ochrona przed Poison Pills (ERROR State) 🟡 ŚREDNI
**Treść:** Obiekt ze statusem `ERROR` (np. uwalony przez trwale zablokowane API dla tego węzła) nie może być automatycznie zresetowany i ponowiony przez nocnego workera.
**Uzasadnienie:** Obiekt w tym statusie wymaga autorytatywnej manualnej interwencji admina (np. korekty błędnego `osm_id`), by nie zapychać kolejki `Celery Beat` martwymi żądaniami.
**Gdzie egzekwować:** 
- Use Case: `FetchOsmDataUseCase` i `RunOsmNightWatchmanUseCase` (ignorowanie obiektów `ERROR`).
- Test: `test_S02_error_status_stops_automatic_retries`

---

## Grupa P — Pule Szczytów i Prawa Nabyte

### P-01 — Niemutowalność aktywnej Puli Szczytów (Immutability) 🔴 KRYTYCZNY
**Treść:** Zbiór `pool_peaks` dla `BadgeVersionModel`, do którego podpięty jest choć jeden aktywny turysta, jest całkowicie niemutowalny.
**Uzasadnienie:** Każda zmiana puli z mocą wsteczną modyfikuje warunki umowy z turystą (łamanie Praw Nabytych). Każda zmiana wykazu szczytów wymusza utworzenie nowej `BadgeVersionModel`.
**Gdzie egzekwować:** 
- Walidator Admina: `BadgeVersionAdmin.save_model()` lub `save_m2m()` (Faza C).
- Test: `test_P01_active_version_pool_is_immutable`

---

## Grupa C — Klastry i Hierarchia Przestrzenna

### C-01 — Brak Cykli w Grafie Klastrów 🔴 KRYTYCZNY
**Treść:** Relacja `parent_object` nie może tworzyć pętli (cykli) w grafie (np. A jest rodzicem B, a B staje się rodzicem A). Żaden obiekt nie może być własnym przodkiem.
**Uzasadnienie:** Naruszenie wygeneruje błędy przy budowaniu widoków frontendowych lub nieskończoną pętlę przy odpytywaniu bazy na okoliczność "Dzieci klastra" przez Use Case.
**Gdzie egzekwować:** 
- Use Case: `ResolveProximityCandidateUseCase` (Logika Auto-Resolve).
- Formularz Admina: Własna metoda `clean()` modelu `TouristObject`.
- Test: `test_C01_cyclic_parent_dependency_raises_validation_error`

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-27 | Dominik / AI Architect | Pierwsza wersja (Grupy T, R, D) |
| 1.1 | 2026-05-27 | AI Architect | Dodano Grupy S (Stany), P (Pule), C (Klastry). Standaryzacja formatu "Gdzie egzekwować" i poziomu krytyczności |
