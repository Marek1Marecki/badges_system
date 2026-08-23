# Security Gate Policy

## Cel

Polityka ta definiuje, kiedy Trivy powinien blokować build, a kiedy generować
raport informacyjny. Zastępuje ad-hoc podejście "wszystko albo nic" warstwową
klasyfikacją CVE.

## Klasyfikacja CVE

Każde CVE w skanowaniu obrazu jest klasyfikowane po dwóch wymiarach:

- **Availability**: `affected` (istnieje fix) / `fix_deferred` (fix odroczony) / `will_not_fix` (brak planu naprawy)
- **Severity**: `CRITICAL` / `HIGH` / `MEDIUM` / `LOW`

W scanach używamy tylko `--severity HIGH,CRITICAL`. Niższe poziomy są monitorowane,
ale nie blokują żadnej fazy.

## Polityka według fazy

### Development (teraz — do ~4 tyg. przed PROD)

| Kategoria | Działanie | Efekt dla CI |
|-----------|-----------|--------------|
| `CRITICAL + affected` | raport do security backlog | ✅ build przechodzi |
| `HIGH + affected` | raport do security backlog | ✅ build przechodzi |
| `CRITICAL + fix_deferred` | raport do security backlog | ✅ build przechodzi |
| `CRITICAL + will_not_fix` | raport do security backlog | ✅ build przechodzi |
| `HIGH + fix_deferred` | raport do security backlog | ✅ build przechodzi |
| `HIGH + will_not_fix` | raport do security backlog | ✅ build przechodzi |

Mechanizm: Trivy z `--ignore-unfixed` — tylko CVE z dostępnym fixem pojawiają
się w raporcie. CVE `will_not_fix` i `fix_deferred` są zbierane z pełnego
skanu i przechowywane jako artefakt, ale nie blokują build.

Wszystkie CVE trafiają do **security backlog** (`docs/security-backlog.md`).

### Pre-PROD (~4 tyg. przed planowanym release'em)

| Kategoria | Działanie | Efekt dla CI |
|-----------|-----------|--------------|
| `CRITICAL + affected` | naprawa wymagana | ❌ build FAIL |
| `HIGH + affected` | naprawa wymagana | ❌ build FAIL |
| `CRITICAL + fix_deferred` | security exception wymagany | ❌ build FAIL bez exception |
| `CRITICAL + will_not_fix` | security exception wymagany | ❌ build FAIL bez exception |
| `HIGH + fix_deferred` | security exception wymagany | ⚠️ build WARN |
| `HIGH + will_not_fix` | security exception wymagany | ⚠️ build WARN |

Uwaga: w Pre-PROD `HIGH + fix_deferred/will_not_fix` generuje WARN, a nie FAIL.
Jest to świadome złagodzenie — HIGH z brakiem fixa w dystrybucji nie powinien
blokować release'u, ale wymaga udokumentowanego wyjątku. W PROD ten sam kategorii
staje się FAIL, żeby wymusić rozstrzygnięcie przed wdrożeniem.

Mechanizm: Trivy bez `--ignore-unfixed`, z `--exit-code 1`. Wyjątki w
`.trivyignore` z odwołaniem do wpisu w rejestrze exceptionów.

### PROD (release)

| Kategoria | Działanie | Efekt dla CI |
|-----------|-----------|--------------|
| `CRITICAL + affected` | naprawa wymagana | ❌ FAIL |
| `HIGH + affected` | naprawa wymagana | ❌ FAIL |
| `CRITICAL + fix_deferred` | approved exception + review date | ❌ FAIL bez approved exception |
| `CRITICAL + will_not_fix` | approved exception + review date | ❌ FAIL bez approved exception |
| `HIGH + fix_deferred` | approved exception + review date | ❌ FAIL bez approved exception |
| `HIGH + will_not_fix` | approved exception + review date | ❌ FAIL bez approved exception |

## Rejestr wyjątków (Exception Register)

Każdy wpis w `.trivyignore` musi mieć odpowiadający wpis w
`docs/security-exceptions.md`:

```markdown
### EX-001: CVE-2023-45853 (zlib1g)

- **Package**: zlib1g
- **Version**: 1:1.2.13.dfsg-1
- **Severity**: CRITICAL
- **Status**: will_not_fix
- **Why present**: base image dependency (python:3.14-slim-bookworm)
- **Exploitability**: brak exploitable path w aplikacji
- **Compensating controls**: network segmentation, WAF
- **Decision**: accepted
- **Owner**: @username
- **Review date**: 2026-11-30
```

Wyjątki mają termin przeglądu. Po upływie terminu CVE wraca do polityki
domyślnej (FAIL).

## Timeline wdrożenia

```
TERAZ                    -4 tyg.                   PROD release
  │                         │                         │
  ▼                         ▼                         ▼
Development            Pre-PROD hardening        Release Candidate
  │                         │                         │
  ├── Trivy scan           ├── Trivy z --exit-code   ├── Security Gate
  │   + --ignore-unfixed   │   + .trivyignore        │   + SBOM
  │   + classification     │   + exception register  │   + dependency review
  │   + report only        │   + FAIL dla affected   │   + FAIL dla wszystkie
  │   ✅ build passes      │   ❌ build fails        │   ❌ build fails
  │                         │                         │
  └── security backlog     └── zero will_not_fix    └── PROD deploy
       (co 2-4 tyg)            bez approved exception
```

## Zmiany w CI

### Development mode (teraz)

```bash
trivy image \
  --severity HIGH,CRITICAL \
  --ignore-unfixed \
  --format json \
  --output trivy-report.json \
  badges-system:$SHA
```

`--ignore-unfixed` pomija CVE bez fixa w raporcie JSON. Build nie blokuje.

### Pre-PROD / PROD mode

```bash
trivy image \
  --severity HIGH,CRITICAL \
  --exit-code 1 \
  --format json \
  --output trivy-report.json \
  badges-system:$SHA
```

`.trivyignore` wyklucza approved exceptions. Wszystko co nie jest wykluczone
i ma `--exit-code 1` → build FAIL.

## Security backlog

Wszystkie CVE z dev scanów trafiają do `docs/security-backlog.md`:

```markdown
| CVE | Package | Severity | Availability | Action | Owner | Target |
|-----|---------|----------|--------------|--------|-------|--------|
| CVE-2026-49014 | gdal-data | CRITICAL | affected | upgrade GDAL | @username | 2026-09-30 |
| CVE-2023-45853 | zlib1g | CRITICAL | will_not_fix | exception | @username | 2026-11-30 |
```

Backlog jest przeglądany co 2–4 tygodnie. Priorytet: `affected` > `fix_deferred` > `will_not_fix`.

## Obecny stan (2026-08-23)

| Kategoria | Liczba | Rekomendacja |
|-----------|--------|--------------|
| CRITICAL + affected | 4 | backlog remediation |
| CRITICAL + fix_deferred | 2 | security exception |
| CRITICAL + will_not_fix | 1 | security exception |
| HIGH + affected | 57 | backlog remediation |
| HIGH + fix_deferred | 12 | security exception |
| HIGH + will_not_fix | 3 | security exception |

Najważniejsze obszary do analizy:
- GDAL (CVE-2026-49014 HIGH affected) — aplikacja używa GeoDjango, brak fix w Debian 12
- perl-base (CVE-2026-13221 CRITICAL affected, CVE-2026-42496 CRITICAL fix_deferred) — potencjalnie zbędny w production
- libheif1/libaom3 — sterowniki GDAL nieużywane przez aplikację
- libcurl — pośrednia zależność przez HDF5 → GDAL
