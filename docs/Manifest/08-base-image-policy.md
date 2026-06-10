# Base Image Policy

**Status:** Egzekwowalny  
**Zakres:** Wszystkie projekty używające Docker

---

## Zasada tagowania

### W Dockerfile

Pinujemy **minor** wersję Pythona **i wersję dystrybucji OS**:

```dockerfile
FROM python:3.12-slim-bookworm
```

**Dlaczego minor, nie patch?** Pinowanie patcha (`3.12.12`) daje złudne poczucie kontroli — i tak wymaga ręcznej aktualizacji. Pinowanie minor zachowuje prostotę, a SHA w CI zapewnia świadomość dokładnej wersji przy każdym buildzie.

**Dlaczego `-bookworm`, nie samo `-slim`?** Tag `-slim` bez wersji OS jest ruchomym celem — może przeskoczyć z Debian 12 (bookworm) na Debian 13 (trixie) bez ostrzeżenia. Zmiana dystrybucji może podmienić wersje bibliotek systemowych (libc, OpenSSL) i złamać buildy projektów GIS (GDAL, PROJ, GEOS). Jawne wskazanie `-bookworm` gwarantuje stabilność środowiska systemowego niezależnie od aktualizacji Pythona.

### Aktualne mapowanie

| Tag Pythona | Debian |
|-------------|--------|
| `python:3.10-slim-bookworm` | Debian 12 |
| `python:3.12-slim-bookworm` | Debian 12 |
| `python:3.14-slim-bookworm` | Debian 12 |

### W CI Pipeline

Każdy build rejestruje dokładny SHA obrazu bazowego:

```yaml
- name: Log base image SHA
  run: docker inspect python:3.12-slim-bookworm --format='{{index .RepoDigests 0}}'
```

SHA jest używany do audytu i weryfikacji reproducibility. Nie pinujemy SHA w Dockerfile (zbyt częste zmiany) — logujemy go w CI jako ślad audytowy.

---

## Kiedy aktualizujemy

1. **Regularnie** — co 3 miesiące
2. **Ad-hoc** — przy ogłoszeniu krytycznej luki bezpieczeństwa
3. **Przed release** — weryfikacja że build przechodzi z aktualnym obrazem

---

## Procedura aktualizacji

```bash
docker build --no-cache -t app:test .
uv lock --check
make check
```

Build musi przejść bez błędów, wszystkie testy muszą przejść. Wpis w `CHANGELOG.md` z uzasadnieniem.

**Zasada aktualizacji Trivy:** każda aktualizacja obrazu bazowego wymusza sprawdzenie i aktualizację Trivy do najnowszej kompatybilnej wersji — bazy CVE muszą być aktualne względem nowego obrazu.

---

## Zakazane praktyki

- Używanie tagu `latest`
- Używanie `-slim` bez wersji OS (`python:3.12-slim` zamiast `python:3.12-slim-bookworm`)
- Brak wpisu w CHANGELOG przy zmianie obrazu bazowego
- Automatyczna aktualizacja bez weryfikacji CI
- Różne tagi obrazu bazowego w Stage 1 i Stage 2 tego samego Dockerfile
