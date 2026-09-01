# Traceability Matrix — Macierz Śledzenia Wymagań

> **Wersja:** 2.0  
> **Data:** 2026-07-10  
> **Cel:** "Living Documentation" dla Analityka i Programisty. Śledzi ścieżkę: User Story ➔ Agregat ➔ Use Case ➔ Test.

---

## 1. Tożsamość i Model Rodzinny (Epic 1)

| Story | Aggregate / Entity | Use Case | Domain Rule / Invariant | Plik Testowy | Status |
|:---|:---|:---|:---|:---|:---:|
| **US-C01** | `TouristProfile` | UC-001 `ProfileSettingsView` | T-02 (Czas w locie), `MinAgeRule` | `tests/domain/rules/test_badge_rules.py` | ✔ |
| **US-C01c**| `TouristProfile` | UC-002 `StartBadgeProgressUseCase` | Limit Konta (IDOR Guard) | `test_start_badge_progress.py` | ✔ |
| **US-C01d**| `TouristProfile` | UC-003 `SwitchProfileView` | Leniwa Inicjalizacja Profilu | `test_integration.py` | ✔ |
| **US-C02** | `TouristProfile` | UC-004 `VerifyBadgeUseCase` | `RequiresClubJoinDateRule` | `test_badge_rules.py` | ✔ |

## 2. Rejestracja Wejść i Smart GPX (Epic 2)

| Story | Aggregate / Entity | Use Case | Domain Rule / Invariant | Plik Testowy | Status |
|:---|:---|:---|:---|:---|:---:|
| **US-C03** | `AscentLog` | UC-005 `LogAscentUseCase` | T-01 (Bitemporalność), T-03 (Brak Przyszłości) | `test_log_ascent.py` | ✔ |
| **US-C03** | `AscentLog` | UC-005 `LogAscentUseCase` | D-04 (Idempotentność / Upsert) | `test_integration.py` | ✔ |
| **US-C17** | `AscentLog` | UC-006 `AnalyzeGpxTrackUseCase` | Ochrona XML Bomb (S314) | *(Bandit / Linter)* | ✔ |
| **US-C17** | `AscentLog` | UC-007 `BulkLogAscentsUseCase` | Partial Success | `test_bulk_log_ascents.py` | ✔ |

## 3. Silnik Reguł i Prawa Nabyte (Epic 3)

| Story | Aggregate / Entity | Use Case | Domain Rule / Invariant | Plik Testowy | Status |
|:---|:---|:---|:---|:---|:---:|
| **US-C05** | `BadgeVersion` | UC-002 `StartBadgeProgressUseCase`| P-01 (Leniwe Zakotwiczenie) | `test_start_badge_progress.py` | ✔ |
| **US-C06** | `BadgeVersion` | UC-004 `VerifyBadgeUseCase` | R-01 (Set Math w RAM) | `test_badge_version.py` | ✔ |
| **US-C09** | `UserBadgeProgress`| UC-004 `VerifyBadgeUseCase` | P-02 (Zużycie Wejść / `cutoff_date`) | `test_verify_badge.py` | ✔ |
| **(Wildcard)**| `Ascent` (VO) | UC-004 `VerifyBadgeUseCase` | R-03 (Wildcard), `RegionCountRule` | `test_badge_rules.py` | ✔ |

## 4. Osobisty Kanban Logistyczny (Epic 4)

| Story | Aggregate / Entity | Use Case | Domain Rule / Invariant | Plik Testowy | Status |
|:---|:---|:---|:---|:---|:---:|
| **US-C07** | `UserBadgeProgress`| UC-008 `AdvanceLogisticStatusUseCase` | S-03 (Separacja Matematyki) | `test_advance_logistic_status.py` | ✔ |
| **US-C08b**| `UserBadgeProgress`| UC-009 `UnsubscribeBadgeUseCase`| Ochrona stanu `COMPLETED` | `test_unsubscribe_badge.py` | ✔ |

## 5. Operacje Danych i Automatyzacja (Epic 6)

| Story | Aggregate / Entity | Use Case | Domain Rule / Invariant | Plik Testowy | Status |
|:---|:---|:---|:---|:---|:---:|
| **US-A01** | `BadgeNewsItem` | UC-010 `FetchBadgeNewsUseCase` | Fail-Silently Web Scraping | `test_news_scraper.py` | ✔ |
| **(Sync)** | `TouristObject` | UC-011 `RunOsmNightWatchmanUseCase` | S-02 (Poison Pill), Ochrona WAF | `test_osm_adapter.py` | ✔ |
| **(Klastry)**| `TouristObject` | UC-012 `TouristObject.clean()` | C-01 (Płaska Gwiazda) | `test_tourist_object_clean.py` | ✔ |

## 6. Operacje i Utrzymanie Danych (Data Stewardship)

| Story | Aggregate / Entity | Use Case | Domain Rule / Invariant | Plik Testowy | Status |
|:---|:---|:---|:---|:---|:---:|
| **Snapshot Referencyjny** | Single Source of Truth w Repozytorium Gita | `export_reference_data.py`, `manifest.json` | Deterministyczne odtwarzanie środowiska za pomocą `restore_reference_data.py`. |
| **Idempotencja DataOps** | Ochrona przed duplikacją na PROD | Zapisano w `TEST_STRATEGY.md` | Test `test_restore_reference_data_is_idempotent` weryfikujący podwójny przebieg. |
| **Architecture Quality & Complexity** | Zapobieganie Erozji Architektury i długowi technologicznemu | `Radon`, `Xenon`, `wily` | Twarda bramka (Gating) w CI/CD odrzucająca funkcje o zbyt wysokiej złożoności cyklomatycznej (Max = B). Comiesięczny raport trendów z artefaktów GitHub Actions. |
| **Zarządzanie Pamięcią (OOM Protection)** | Optymalizacja zapytań o pełną historię turysty | `DjangoTouristRepository` (iterator 2000, `.only()`) | Zabezpiecza serwer przed wyczerpaniem RAM przy masowym eksporcie logów GPX. |
| **Optymalizacja Domeny (Indexes)** | Eliminacja zjawiska Seq Scan dla krytycznych ścieżek | Migracje `AddIndex` (złożone indeksy profili) | Skrócenie czasu zapytań w `VerifyBadgeUseCase` z kilkuset do pojedynczych milisekund. |
| **Ochrona Danych (RODO / Anti-Tombstoning)**| Blokada przypadkowego skasowania historii wejść przy usunięciu konta | `on_delete=models.PROTECT` w relacjach profili | Usunięcie konta wymusza jawną i ostrożną kasację wejść, blokując kaskadę frameworka Django. |

---
**Podsumowanie pokrycia:** Wymagania z Fazy C posiadają 100% powiązanie z fizycznymi plikami testowymi dla warstw logiki.
