# QA Matrix — Macierz Śledzenia Jakości

> **Wersja:** 1.0  
> **Cel:** Centrum dowodzenia dla inżynierów Testów Automatycznych (QA) i Playwright.  
> **Uwaga:** Kategorie testów odpowiadają folderom w `tests/` według warstw architektury heksagonalnej (nie według sztucznego podziału Unit/Integration).

---

## 1. Statystyki Pokrycia Systemu (Current State)

| Typ Wymagania / Testu | Lokalizacja w Repo | Liczba Zdefiniowana | Liczba Zrealizowana | Pokrycie |
|:---|:---|:---:|:---:|:---:|
| User Stories (Faza A-C) | `tests/application/`, `tests/apps/api/` | 16 | 16 | 100% |
| Reguły Domenowe (Sito) | `tests/domain/` | 12 | 12 | 100% |
| Domain & Application Tests | `tests/domain/`, `tests/application/` | ~500 | ~500 | ~100% |
| Infrastructure & Integration Tests | `tests/infrastructure/`, `tests/apps/` | ~120 | ~120 | ~75% |
| **Testy E2E (Playwright)** | `tests/e2e/` | **5** (Draft) | **0** | **0%** |

*(Ogólne pokrycie kodu: >82% w czasie <15s)*

---

## 2. Plany Testów E2E (Playwright) — Ścieżki Krytyczne

Te testy mają najwyższy priorytet do zautomatyzowania przed uruchomieniem serwera produkcyjnego.

| ID | Scenariusz BDD | Ryzyko | Status | Powiązany SCN |
|:---|:---|:---:|:---:|:---|
| **E2E-001** | Użytkownik loguje się przez Google, widzi `dashboard`, klika "Pokaż Katalog", wybiera odznakę i zaczyna zdobywanie (weryfikacja `SUBSCRIBED`). | **High** | ⏳ | SCN-012 |
| **E2E-002** | Użytkownik otwiera mapę (MVT render), klika pinezkę, dodaje log wejścia (Dziś). Mapa odświeża się (Debounce), a kolor szczytu zmienia się na `GREEN`. | **High** | ⏳ | SCN-014 |
| **E2E-003** | Użytkownik przesyła złośliwy plik XML udający GPX. System łagodnie go odrzuca błędem walidacji na Modalu. | **Medium**| ⏳ | SCN-016 |
| **E2E-004** | Użytkownik w Kanbanie ("Moja Logistyka") przesuwa gotową odznakę do "Weryfikacji", po czym cofa błąd do "Wysłano" bez błędu 409. | **High** | ⏳ | SCN-011 |
| **E2E-005** | Administrator dodaje odznakę, klika `export_reference_data`, niszczy bazę, a następnie odtwarza środowisko i widzi wszystkie relacje M2M. | **Low** | ⏳ | (Data Stewardship) |
