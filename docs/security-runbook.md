# Security Runbook

 instrukcje uruchamiania skanów bezpieczeństwa i aktualizacji security backlog.

## Skanowanie obrazu (Trivy)

```bash
# Pełny skan (wszystkie CVE)
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd)":/work -w /work \
  aquasec/trivy:0.58.0 \
  image \
  --db-repository public.ecr.aws/aquasecurity/trivy-db \
  --severity HIGH,CRITICAL \
  --scanners vuln \
  --format json \
  --output /work/trivy-report-full.json \
  badges-system:<tag>

# Development mode (tylko affected)
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v "$(pwd)":/work -w /work \
  aquasec/trivy:0.58.0 \
  image \
  --db-repository public.ecr.aws/aquasecurity/trivy-db \
  --severity HIGH,CRITICAL \
  --scanners vuln \
  --ignore-unfixed \
  --format json \
  --output /work/trivy-report.json \
  badges-system:<tag>
```

## Aktualizacja security backlog

```bash
# Z pełnego raportu
python scripts/update_security_backlog.py trivy-report-full.json

# Z raportu development
python scripts/update_security_backlog.py trivy-report.json

# Dry-run
python scripts/update_security_backlog.py trivy-report.json --dry-run

# Custom output
python scripts/update_security_backlog.py trivy-report.json --output docs/security-backlog.md
```

## Harmonogram

| Akcja | Częstotliwość | Kto |
|-------|---------------|-----|
| Skan Trivy (development) | co commit | CI |
| Aktualizacja security-backlog.md | co 2–4 tygodnie | zespół |
| Przegląd exceptions | co 2–4 tygodnie | zespół |
| Security gate (Pre-PROD) | -4 tyg. przed PROD | zespół + release manager |

## W fazie development

- CI generuje `trivy-report.json` z `--ignore-unfixed`
- Skrypt aktualizuje `docs/security-backlog.md`
- Build nie blokuje się na CVE
- Wszystkie CVE trafiają do artefaktów

## Przejście do Pre-PROD

1. Zaktualizuj `.github/workflows/ci.yml`:
   - Zamień `--ignore-unfixed` na `--exit-code 1`
   - Dodaj `.trivyignore` z approved exceptions

2. Zatwierdź wyjątki w `docs/security-exceptions.md`

3. Uruchom pełny skan bez `--ignore-unfixed`

4. Sprawdź, czy build przechodzi z `.trivyignore`

## Pliki

- `docs/security-gate-policy.md` — polityka security gate
- `docs/security-backlog.md` — rejestr CVE
- `docs/security-exceptions.md` — zaakceptowane wyjątki
- `scripts/update_security_backlog.py` — skrypt aktualizacji backlogu

## Troubleshooting

### Skrypt nie generuje outputu

Sprawdź czy `trivy-report.json` istnieje i ma poprawny format JSON.

### Brak CVE w raporcie

Sprawdź czy Trivy ma aktualną bazę danych:
```bash
docker run --rm aquasec/trivy:0.58.0 image --download-db-only
```

### Build blokuje się w CI

Sprawdź czy `.trivyignore` istnieje i zawiera wszystkie approved exceptions.
