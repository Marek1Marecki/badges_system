# Security Exceptions

Rejestr zaakceptowanych wyjątków bezpieczeństwa. Każdy wpis odpowiada pozycji
w `.trivyignore` i ma termin przeglądu.

Każdy wpis w `docs/security-exceptions.md` odpowiada wpisowi w `.trivyignore`.
Format `.trivyignore`:

```yaml
ignore:
  "CVE-2023-45853":
    Package: zlib1g
    Reason: EX-001 - accepted until 2026-11-30
```

Nie twórz wpisów w `.trivyignore` w fazie development. Plik powinien pojawić
się dopiero w Pre-PROD, po zatwierdzeniu wyjątków przez zespół.

Po upływie terminu wyjątek traci ważność i CVE wraca do domyślnej polityki
security gate. W `.trivyignore` usuwa się wtedy odpowiedni wpis.

## Format wpisu

```markdown
### EX-XXX: CVE-YYYY-XXXXX (package)

- **Package**: nazwa pakietu
- **Version**: zainstalowana wersja
- **Severity**: CRITICAL / HIGH
- **Status**: will_not_fix / fix_deferred / accepted
- **Why present**: dlaczego pakiet jest w obrazie
- **Exploitability**: czy aplikacja jest narażona
- **Compensating controls**: kontrolki kompensujące
- **Decision**: accepted / rejected
- **Owner**: @username
- **Review date**: YYYY-MM-DD
```

## Aktywne wyjątki

### EX-001: CVE-2023-45853 (zlib1g)

- **Package**: zlib1g
- **Version**: 1:1.2.13.dfsg-1
- **Severity**: CRITICAL
- **Status**: will_not_fix
- **Why present**: base image dependency (python:3.14-slim-bookworm)
- **Exploitability**: brak exploitable path w aplikacji — zlib używany przez
  Pillow do kompresji obrazów, ale dane wejściowe są generowane przez aplikację,
  nie przez użytkownika
- **Compensating controls**: network segmentation, WAF, input validation
- **Decision**: accepted
- **Owner**: —
- **Review date**: 2026-11-30

### EX-002: CVE-2026-49014 (gdal-data / libgdal32 / gdal-plugins)

- **Package**: gdal-data, libgdal32, gdal-plugins
- **Version**: 3.6.2+dfsg-1
- **Severity**: HIGH
- **Status**: will_not_fix
- **Why present**: wymagane przez Django GIS (GeoDjango) do operacji
  geoprzestrzennych
- **Exploitability**: aplikacja używa GeoDjango do wczytania danych z
  zaufanych źródeł (dump PostgreSQL), nie przyjmuje danych od użytkowników
- **Compensating controls**: dane wejściowe są walidowane przez Django ORM,
  brak bezpośredniego odczytu plików użytkownika przez GDAL
- **Decision**: accepted do czasu upgrade GDAL
- **Owner**: —
- **Review date**: 2026-09-30

### EX-003: CVE-2026-13221 + CVE-2026-42496 (perl-base)

- **Package**: perl-base
- **Version**: 5.36.0-7+deb12u3
- **Severity**: CRITICAL
- **Status**: affected + fix_deferred
- **Why present**: essential package w base image python:3.14-slim-bookworm
- **Exploitability**: aplikacja nie używa Perla, brak skryptów Perl w /app,
  perl nie jest w PATH w runtime
- **Compensating controls**: brak exec Perla w kontenerze, aplikacja nie wywołuje Perla
- **Decision**: accepted jako ryzyko base image
- **Owner**: —
- **Review date**: 2026-11-30

### EX-004: CVE-2023-6879 (libaom3)

- **Package**: libaom3
- **Version**: 3.6.0-1+deb12u2
- **Severity**: CRITICAL
- **Status**: affected
- **Why present**: transitivity przez libheif1 → libgdal32
- **Exploitability**: aplikacja nie używa HEIF/AVIF, Pillow nie ma włączonego
  wsparcia heif (`features.check("heif")` zwraca False)
- **Compensating controls**: brak użycia formatów HEIF/AVIF w aplikacji
- **Decision**: accepted do czasu usunięcia libheif/libaom z obrazu
- **Owner**: —
- **Review date**: 2026-09-30

### EX-005: CVE-2025-7458 (libsqlite3-0)

- **Package**: libsqlite3-0
- **Version**: 3.6.0-1+deb12u2
- **Severity**: CRITICAL
- **Status**: affected
- **Why present**: wspólna zależność systemowa (PROJ, GDAL, Python)
- **Exploitability**: aplikacja używa SQLite przez Django ORM,
  dane są walidowane i pochodzą z zaufanych źródeł
- **Compensating controls**: Django ORM sanitizes queries, brak bezpośredniego SQL
- **Decision**: accepted do czasu upgrade base image
- **Owner**: —
- **Review date**: 2026-11-30

### EX-006: CVE-2025-59375 (libexpat1)

- **Package**: libexpat1
- **Version**: 2.5.0-1+deb12u2
- **Severity**: HIGH
- **Status**: will_not_fix
- **Why present**: wspólna zależność systemowa (libxml2, Python)
- **Exploitability**: aplikacja używa defusedxml zamiast xml.etree,
  dane XML są walidowane
- **Compensating controls**: defusedxml, brak parsowania XML od użytkowników
- **Decision**: accepted do czasu upgrade base image
- **Owner**: —
- **Review date**: 2026-11-30

### EX-007: CVE-2023-52355 (libtiff6)

- **Package**: libtiff6
- **Version**: 4.5.0-6+deb12u4
- **Severity**: HIGH
- **Status**: will_not_fix
- **Why present**: transitivity przez libgdal32
- **Exploitability**: aplikacja nie przetwarza plików TIFF od użytkowników,
  używa tylko wektorowych geometrii GeoDjango
- **Compensating controls**: brak obsługi TIFF w aplikacji
- **Decision**: accepted do czasu upgrade GDAL
- **Owner**: —
- **Review date**: 2026-09-30

### EX-008: CVE-2026-6653 (libxml2)

- **Package**: libxml2
- **Version**: 2.9.14+dfsg-1.3~deb12u6
- **Severity**: CRITICAL
- **Status**: fix_deferred
- **Why present**: wspólna zależność systemowa (Python, libxml2)
- **Exploitability**: aplikacja używa defusedxml zamiast xml.etree,
  dane XML są walidowane
- **Compensating controls**: defusedxml, brak parsowania XML od użytkowników
- **Decision**: accepted do czasu upgrade base image
- **Owner**: —
- **Review date**: 2026-11-30

## Proces przeglądu

1. Co 2–4 tygodnie zespół przegląda rejestr
2. Dla każdego wyjątku z terminem przeglądu:
   - sprawdź czy pojawił się fix
   - sprawdź czy aplikacja nadal nie używa dotkniętej funkcji
   - zaktualizuj status
3. Wyjątki z przekroczonym terminem przeglądu:
   - jeśli brak fix → odnow wyjątek z nowym terminem
   - jeśli jest fix → usuń wyjątek, zaktualizuj obraz
4. Wszystkie zmiany są rejestrowane w tym pliku

## Zmiana statusu

```markdown
### EX-002: CVE-2026-49014 (gdal-data)

- **Status**: accepted → resolved
- **Resolved by**: upgrade to Debian 13 (GDAL 3.8.0)
- **Date**: 2026-10-15
```
