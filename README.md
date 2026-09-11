# System Odznak Turystycznych (PTTK Badges)

![Python Version](https://img.shields.io/badge/python-3.14%2B-blue)
![Django Version](https://img.shields.io/badge/django-6.0.x-green)
![Coverage](https://img.shields.io/badge/coverage-80%25%2B-brightgreen)
![Architecture](https://img.shields.io/badge/architecture-Hexagonal%20%7C%20DDD-orange)

Zaawansowany system do autorytatywnego katalogowania górskich obiektów geograficznych (OSM), definiowania skomplikowanych regulaminów PTTK oraz bezstanowej weryfikacji wejść turystów. Zbudowany w Architekturze Heksagonalnej (Ports & Adapters) oraz Domain-Driven Design (DDD). Infrastruktura oparta jest na PostgreSQL + PostGIS z asynchronicznym zasilaniem przez Celery.

---

## 📖 Dokumentacja Architektoniczna

Projekt posiada wyczerpującą dokumentację w katalogu `docs/`. **Zapoznanie się z nią jest obowiązkowe przed programowaniem.**

* [Vision Statement.md](docs/Vision Statement.md) — Cel systemu, problem biznesowy i mierniki.
* [Glossary.md](docs/Glossary.md) — Słownik Języka Wszechobecnego (Ubiquitous Language).
* [Invariants.md](docs/Invariants.md) — Niezmienniki systemu (twarde reguły architektoniczne).
* [Domain Model.md](docs/Domain Model.md) — Opis encji i relacji biznesowych.
* [Architecture.md](docs/architecture/Architecture.md) i [Module Map.md](docs/architecture/Module%20Map.md) — Tech stack i zasady importów.
* [Data Flow Diagram.md](docs/Data Flow Diagram.md) — Przepływ danych w systemie (CQRS, Asynchronia).
* [Dependencies.md](docs/Dependencies.md) — Uzasadnienie użytych bibliotek.
* [Edge Cases.md](docs/Edge Cases.md) — Znane problemy (WAF, OSM) i workaroundy.
* [Runbook.md](docs/guides/Runbook.md) — Podręcznik uruchamiania i Troubleshooting.
* [Test Strategy.md](docs/testing/Test%20Strategy.md) — Strategia testowania (Test Doubles, Fakes).
* **Decyzje Architektoniczne:** Katalog `docs/adrs/` (ADR-001 do ADR-031).

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