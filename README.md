# System Odznak Turystycznych (PTTK Badges)

![Python Version](https://img.shields.io/badge/python-3.14%2B-blue)
![Django Version](https://img.shields.io/badge/django-6.0.x-green)
![Coverage](https://img.shields.io/badge/coverage-80%25%2B-brightgreen)
![Architecture](https://img.shields.io/badge/architecture-Hexagonal%20%7C%20DDD-orange)

Zaawansowany system do autorytatywnego katalogowania górskich obiektów geograficznych (OSM), definiowania skomplikowanych regulaminów PTTK oraz bezstanowej weryfikacji wejść turystów. Zbudowany w Architekturze Heksagonalnej (Ports & Adapters) oraz Domain-Driven Design (DDD). Infrastruktura oparta jest na PostgreSQL + PostGIS z asynchronicznym zasilaniem przez Celery.

---

## 📖 Dokumentacja Architektoniczna

Projekt posiada wyczerpującą dokumentację w katalogu `docs/`. **Zapoznanie się z nią jest obowiązkowe przed programowaniem.**

* [VISION.md](docs/VISION.md) — Cel systemu, problem biznesowy i mierniki.
* [GLOSSARY.md](docs/GLOSSARY.md) — Słownik Języka Wszechobecnego (Ubiquitous Language).
* [INVARIANTS.md](docs/INVARIANTS.md) — Niezmienniki systemu (twarde reguły architektoniczne).
* [DOMAIN_MODEL.md](docs/DOMAIN_MODEL.md) — Opis encji i relacji biznesowych.
* [ARCHITECTURE.md](docs/ARCHITECTURE.md) i [MODULES.md](docs/MODULES.md) — Tech stack i zasady importów.
* [DATAFLOW.md](docs/DATAFLOW.md) — Przepływ danych w systemie (CQRS, Asynchronia).
* [DEPENDENCIES.md](docs/DEPENDENCIES.md) — Uzasadnienie użytych bibliotek.
* [EDGE_CASES.md](docs/EDGE_CASES.md) — Znane problemy (WAF, OSM) i workaroundy.
* [RUNBOOK.md](docs/RUNBOOK.md) — Podręcznik uruchamiania i Troubleshooting.
* [TEST_STRATEGY.md](docs/TEST_STRATEGY.md) — Strategia testowania (Test Doubles, Fakes).
* **Decyzje Architektoniczne:** Katalog `docs/adr/` (ADR-001 do ADR-015).

> **Dla Agentów AI:** Przed rozpoczęciem pracy, agent musi przeczytać plik `SYSTEM_PROMPT.md` oraz zasady zawarte w `.cursorrules`.

---

## 🚀 Quick Start (Uruchomienie lokalne)

```bash
# 1. Klonowanie i setup środowiska
git clone [REPO_URL]
cd badges_system
cp .env.example .env
make setup

# 2. Uruchomienie infrastruktury
docker compose -f docker-compose.dev.yml up -d
uv run python manage.py migrate
uv run python manage.py createsuperuser

# 3. Uruchomienie serwisów (3 osobne terminale)
uv run python manage.py runserver 8005
uv run celery -A config worker -l info
uv run celery -A config beat -l info