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
