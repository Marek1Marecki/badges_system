# Backlog po Audycie — Archiwum Decyzji

> **Dokument archiwalny** gromadzący ostateczne werdykty i decyzje zamknięte na etapie projektowym. Każdy wpis zawiera pełną specyfikację architektoniczną oraz powód zamknięcia (Implementation / Specification / Wont-Fix).
>
> Do głównego życia projektu (do wdrożenia) należy sięgnąć do `docs/backlog.md`.

---

## Zarchiwizowane Decyzje

### [AUDYT-067] Brak polityki wsparcia Wielojęzyczności (i18n)

**Status:** `Wont-Fix / Risk Accepted`

**Obszar:** `Django / Architektura Informacji`

**Priorytet:** `🟢 NISKI`

**Diagnoza Audytora:**
Domena, raporty błędów RFC 7807 oraz szablony HTMX są wbudowane "na sztywno" w języku polskim. Brak zastosowania tagów tłumaczeń Django (`{% trans %}` lub `_("...")`). W przypadku wejścia na rynek czeski lub słowacki, będzie to wymagało przepisania całej warstwy prezentacji.

**Action Items (Do wdrożenia w przypadku internacjonalizacji):**
- [ ] Dodać konfigurację `i18n` do `settings.py` oraz `app_settings.py`.
- [ ] Zmodyfikować DTO wyjściowe i Exception Handlery, aby wywoływały funkcję `ugettext_lazy` przed serializacją JSON-a.

**Decyzja Architektoniczna (Wont-Fix):**

**Zgadzam się w 100% z oceną: rezygnujemy ze wsparcia wielojęzyczności.**

System operuje wokół regulaminów Polskiego Towarzystwa Turystyczno-Krajoznawczego (PTTK), którego jedyną grupą docelowym jest turysta **polskojęzyczny**. Wdrożenie `gettext_lazy`, tagów `{% trans %}` oraz utrzymanie plików `.po` to **przedwczesna optymalizacja** (Premature Internationalization) — szkodliwy "podatek inżynieryjny" bez szans na zwrot z inwestycji (ROI).

**Uzasadnienie biznesowe:**
- Turysta polskojęzyczny zdobywa szczyty w Czechach/Słowacji **w ramach polskiego regulaminu** — nie potrzebuje czeskiej/Słowackiej wersji UI.
- Logika domenowa (reguły biznesowe PTTK) i modele (np. `DomainStatus` w języku polskim) są fundamentalnie zakorzenione w konkretnej kulturze górskiej.
- Wszelkie próby internacjonalizacji w przyszłości będą wymagały świadomej decyzji biznesowej i ponownego rozważenia tego punktu.

**Zaktualizowano:** Językiem wbudowanym na stałe w warstwę prezentacji (Hardcoded) pozostaje język polski.

---

### [x] [AUDYT-066 / 077] Wymóg wsparcia dla wersji Offline (Local-First Architecture)
**Obszar:** `Frontend / UX / Aplikacja Mobilna`  
**Priorytet:** `🟡 ŚREDNI`  
**Status:** `Zamknięte — Graceful Degradation (Read-Only Offline) przyjęte`  

**Context:**
Turysta PTTK wchodzi na szczyty w górach, gdzie zasięg jest niestabilny lub nieistniejący. Oryginalny wymóg (AUDYT-066) wymagał pełnej architektury Offline-First (Local-First) z kolejką asynchroniczną zapisu do IndexedDB, umożliwiając logowanie wejść offline i synchronizację po powrocie do zasięgu.

**Diagnoza Audytora:**
Aplikacja PTTK Badges opiera się na architekturze **Server-Side Rendering (HTMX)** — przeglądka renderuje HTML w Django. Czysta Domena (reguły weryfikacyjne, bitemporalność T-01, limity konta Freemium) jest ewaluowana wyłącznie po stronie serwera.

Wdrożenie pełnego trybu Offline-First wiąże się z niekompatybilnością architektoniczną:

1. **Illuzja Paska Postępu:** Pasek Odznaki na smartfonie nie może być aktualizowany natychmiastowo — reguły liczone są w Pythonie, nie w JavaScript. Duplikacja logiki domenowej w JS złamałaby kontrakt czystości Domeny (ADR — Hexagonal Architecture).
2. **Eventual Consistency Hell (T-01):** Wejście zalogowane offline może zostać odrzucone serwerem (np. błąd bitemporalny T-01 "logowanie w przyszłości") dopiero trzy godziny później po powrocie z lasu. Brak możliwości powiadomienia turysty w czasie rzeczywistym = **zaufanie do aplikacji jest naruszane**.
3. **Complexity Bomb:** Service Workery wymagają pełnego modelu cyklu życia cache (aktualizacja HTML po wdrożeniu ADR-022, konflikty wersji, debugowanie w Safari iOS). To nie jest koszt usprawiedliwiający się w budżecie B2C.

**Decision — Wdrożenie kompromisu:**

**Wariant:** `Graceful Degradation (Read-Only Offline)` — tylko odczyt offline, zapis online.

**Wdrożenie:**
1. **Service Worker (PWA)** — agresywne buforowanie:
   - Plików statycznych: CSS, szablony HTMX, ikony.
   - Kafelków wektorowych mapy (MVT) — Cache API + IndexedDB.
   - Efekt: aplikacja otworzy się jako **interaktywna mapa orientacyjna** nawet bez zasięgu.
2. **Mutacje HTMX offline-aware:**
   - JS przechwytuje próbę zapisu (POST/PUT/DELETE) bez połączenia.
   - Wyświetla Toast: `"🔌 Brak zasięgu. Zaloguj wejście po powrocie do schroniska lub wgraj ślad GPX (→ Import GPS)."`.
   - Brak żadnych danych w lokalnej kolejce — **zero desyncu**.
3. **PWA Install Prompt** — możliwość "zainstalowania" jako ikony na ekranie głównym (iOS + Android) bez App Store.

**Architektoniczne Zasady (chronione):**
- Domena NIE jest duplikowana w JS — pozostaje czysta (Hexagonal Architecture).
- Zero kodu offline-first do utrzymania.
- Logika zapisu pozostaje w `LogAscentUseCase` (Python), nie ma ryzyka T-01 offline.

**Konsekwencje:**
- **Pozytywne:** Znaczną poprawa UX na szlaku (mapa działa offline), PWA dostępna na ekranie głównym, energooszczędny cache MVT.
- **Negatywne:** Turysta nie może logować wejść offline. Kompensacja: moduł masowego importu śladów GPS (GPX) udostępnia prosty workflow wieczorem w hotelu.

**Trigger for Review:**
- Jeśli turystów offline-logowanie będzie kluczowym wskaźnikiem sukcesu aplikacji (>70% logowań offline).
- Jeżeli migracja na Mobile-First (React Native natywne) nastąpi — wtedy full offline będzie osiągalny kosztowo.

**Powiązane:**
- **ADR-017:** Frontend — HTMX + SSR zamiast SPA (decyzja odrzuca SPA, które byłoby lepsze dla offline PWA).
- **Invariants:** T-01 (Ochrona przed logowaniem w przyszłości) — nie może być obejedzony offline bez serwera.

---

### [x] [AUDYT-090] Brakujący Interfejs (UX) do Przełączania Praw Nabytych

**Obszar:** `API / UX / Prawa Nabyte`  
**Priorytet:** `🟠 WYSOKI`  
**Status:** `Zamknięte — Implementacja wdrożona` (2026-09-09)

**Context:**
`US-C05` gwarantuje turystowi "Świadomy wybór Regulaminu" — `StartBadgeProgressUseCase` automatycznie zakotwicza go w starszej wersji regulaminu (Grandfather Clause). Audytor wykrył lukę UX: po zakotwiczeniu turysta **nie miał możliwości dobrowolnego przejścia na nowszy regulamin**.

**Decision — Implementacja pełnego cyklu portów i adapterów:**

Implementacja obejmuje wszystkie warstwy (Masterclass w czystej architekturze):

1. **Port:** `update_version_id()` w `UserProgressRepositoryPort` — czysty interfejs.
2. **Adapter:** `DjangoTouristRepo.update_version_id()` — `exclude(domain_status="COMPLETED")` chroni przed mutacją zakończonych odznak.
3. **Use Case:** `StartBadgeProgressUseCase.switch_version()` — pełna walidacja:
   - Własność postępu (`get_progress_by_id(profile_id, progress_id)`)
   - Zamknięcie na `COMPLETED` → HTTP 409
   - Weryfikacja istnienia wersji → HTTP 404
4. **API:** `PATCH /api/v1/progress/{progress_id}/switch_version/` (`BadgeVersionSwitchView`).
5. **DTO:** `VersionSwitchRequestDTO` — wymuszone przez test architektoniczny `test_api_views_use_dto_for_mutation` (gating).
6. **OpenAPI:** `/progress/{progress_id}/switch_version/` — wymuszone przez test `test_django_api_paths_are_subset_of_openapi`.
7. **Fake:** `FakeUserProgressRepository.update_version_id()` — do testów Use Case.
8. **Event:** `UserProgressStateChanged` publikowane po przełączeniu (AUDYT-117 — bez `request_id` w Domenie).

**Globalny `autouse fixture` w `tests/conftest.py` (AUDYT-117):** Reset ContextVar (`request_id`) między testami — uniemożliwia "przepływ" `request_id` z jednego testu do drugiego (Flaky Tests under pytest-randomly).

**Konsekwencje:**
- Turysta może przejść na nowszy regulamin w dowolnym momencie, dopóki odznaka nie jest zakończona.
- `version_id` w `UserBadgeProgress` aktualizowany dokładnie raz (atomic update via ORM filter).
- Pełna kompatybilność z istniejącym `verify_badge.py` — po przełączeniu nowa wersja regulaminu jest używana dla dalszych wejść.

**Powiązane:**
- **US-C05:** Prawa Nabyte (Specyfikacja).
- **ADR-007:** Hierarchia i Wersjonowanie Odznak (Temporal Modeling).
- **ADR-030:** Distributed Tracing (ContextVar reset w conftest.py).

---

### [x] [AUDYT-115] Opracowanie strategii awaryjnej i "Data Recovery" dla Użytkowników
**Obszar:** `Operacje / Wdrożenie (SRE)`
**Priorytet:** `🟠 WYSOKI (Przed oficjalnym startem PROD)`
**Status:** `Zamknięte — Dokumentacja wdrożona` (2026-09-09)

**Decision:**
Wdrożono operacyjny **Disaster Recovery Plan** (`docs/ops/Disaster_Recovery_Plan.md`) jako oficjalną "Biblię SRE". Plan obejmuje:

1. **Pełna odbudowa bazy PROD** — krok-po-kroku: `pg_dump` → S3 (bucket `pttk-badges-prod-backups`, Object Lock WORM), pobranie na izolowany serwer DR, `pg_restore` przez `docker compose exec db` (unikanie rozjazdu wersji klienta PostgreSQL). Healthcheck + reprezentatywne zapytanie.
2. **Odtworzenie pojedynczego profilu** — polityka biznesowa: **możliwe na żądanie**, ale wymaga ręcznego SQL-a i potwierdzenia Lead Developera (~30–60 min), nie gwarantowane <4h. Uzasadnienie: Prawa Nabyte są rekonstruowalne z logów wejść; profil można odtworzyć, ale koszt operacyjny nie zwaloryzowany jest jako natychmiastowy.
3. **Procedura przed migracją** — backup ad-hoc `prod-backup.sh` zwykły przed `Database Release` (ADR-021, punkt 5).
4. **Checklista 30-minutowa** — tabelaryczny plan akcji dla pierwszych 30 minut incydentu (zablokuj PROD, znajdź backup, potwierdź ticket, odtwórz, healthcheck, powiadom).

**Krytyczne zasady operacyjne:**
- **RPO:** 24h (max utrata danych).
- **RTO:** 8h (max downtime).
- **3-2-1 Rule:** 3 kopie, 2 media, 1 off-site (S3 Object Lock).
- **pg_dump/pg_restore ALASWY** przez `docker compose.exec db` (por. `scripts/dev-backup.sh`).

**Otwarty dług:**
- Skrypty `prod-backup.sh` i `prod-restore.sh` istnieją tylko w wersji `dev-`. Tworzenie wersji PROD to otwarte zadanie.

**Powiązane:**
- **ADR-021:** Strategia Backupów i Disaster Recovery.
- **ADR-020:** Architektura Wdrożeń (SRE).
- **ADR-026:** PostgreSQL Volume Layout.
- **docs/Runbook.md:** Operacje codzienne, migracje schematu.
- **scripts/dev-backup.sh** | **scripts/dev-restore.sh:** Referencja dla wersji PROD.



