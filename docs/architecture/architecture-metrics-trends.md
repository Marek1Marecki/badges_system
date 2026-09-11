# Architecture Metrics Trends

## Cel

Śledzenie trendów złożoności i utrzymywalności kodu w czasie. Aktualizowane co miesiąc.

## Ostatnia aktualizacja

**2026-08-25** — pierwszy wpis, baseline po wdrożeniu metryk.

## Trend ogólny

| Miesiąc | Średnia CC | Średnia MI | Liczba plików > B | Xenon |
|---------|-----------|-----------|-------------------|-------|
| 2026-08 | B (9.80) | — | 0 | PASS |

## Trend per directory

| Miesiąc | domain CC | domain MI | application CC | application MI | infrastructure CC | infrastructure MI | apps CC | apps MI |
|---------|-----------|-----------|----------------|----------------|-------------------|-------------------|---------|---------|
| 2026-08 | 12.55 | 92.99 | 8.62 | 89.89 | 14.20 | 84.42 | 20.38 | 83.37 |

## Alerty

### 2026-08

- ✅ Brak alertów — projekt w dobrym stanie
- ⚠️ Jeden plik z complexity D: `application/services/poi_scoring_service.py:52`
- ⚠️ Jeden plik z MI C: `scripts/audit_contracts.py`

## Jak aktualizować

1. Uruchom `make complexity-trend` na `main`
2. Pobierz `complexity-trend.txt` z CI artifacts
3. Zaktualizuj wartości w tym pliku
4. Dodaj nowy wiersz do tabeli trendów

## Historia zmian

| Data | Zmiana |
|------|--------|
| 2026-08-25 | Pierwszy wpis — baseline |
