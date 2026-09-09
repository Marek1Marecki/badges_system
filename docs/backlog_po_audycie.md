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

