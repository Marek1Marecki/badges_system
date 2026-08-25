# ADR-025 — Infrastruktura Testowa (CI) i Zarządzanie Wolumenami PostgreSQL 18+

> **Status:** `accepted`  
> **Data:** 2026-07-19  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

W miarę dojrzewania aplikacji w fazie C, system infrastruktury zderzył się z dwoma równoległymi problemami związanymi z izolacją środowisk i zarządzaniem stanem (State Management).

**Problem 1: Środowisko TEST i powtarzalność CI**  
Zgodnie z wdrożeniem zautomatyzowanych procesów (GitHub Actions) i przygotowaniami do Playwright (E2E), aplikacja wymaga dedykowanego środowiska `TEST`. Środowisko to nie służy do programowania (nie jest DEV) ani utrzymania danych (nie jest PROD). Wymaga ono gwarancji uruchomienia w warunkach "Czystej Karty" (Clean State) dla każdego przebiegu. Pytaniem decyzyjnym jest: w jaki sposób odizolować środowisko testowe w architekturze `docker-compose`, unikając konfliktów portów, wycieków stanu pomiędzy testami oraz nie naruszając środowiska deweloperskiego na tej samej maszynie?

**Problem 2: Utrata danych w PostgreSQL 18+ (Volume Layout)**  
Projekt opiera się na oficjalnym obrazie `postgis/postgis` (PostgreSQL). Od wersji 18, maintainerzy obrazu zmienili domyślną lokalizację katalogu danych (`PGDATA`) z płaskiej ścieżki `/var/lib/postgresql/data` na strukturę wersjonowaną (np. `/var/lib/postgresql/18/docker`), aby ułatwić migrację `pg_upgrade --link` między wersjami major.  
Podczas aktualizacji obrazu, podpięcie starego wolumenu do tradycyjnej ścieżki `/var/lib/postgresql/data` sprawiło, że silnik Postgres nie znalazł oczekiwanego katalogu `18/docker` i utworzył nowy, pusty klaster bazy danych, w pełni zdając Healthcheck, podczas gdy prawdziwe dane stały się "niewidzialne" i nieosiągalne dla aplikacji (Fałszywy Pozytyw w Healthchecku).

---

## Decyzja 1: Izolacja Środowiska TEST (Efemeryczne CI)

Zostaje wprowadzone dedykowane środowisko TEST opierające się na plikach `.env.test` i `compose.test.yml`, podlegające następującym rygorom:

1. **Unikalna Przestrzeń Nazw (Namespace Isolation):**
   Każde uruchomienie testów musi odbywać się w izolacji od pozostałych środowisk działających na tym samym demonie Dockera. Osiągane jest to przez nadanie unikalnej nazwy projektu, np. `docker compose -p ci-${CI_RUN_ID} ...`. Rozwiązuje to problem konfliktów na portach i umożliwia współbieżne wykonywanie potoków CI.
   
2. **Efemeryczność (Brak trwałego stanu):**
   Środowisko TEST **nie posiada nazwanych wolumenów (named volumes)**, nie przechowuje danych pomiędzy wykonaniami i jest każdorazowo całkowicie niszczone poleceniem `docker compose down -v --remove-orphans`. Zrezygnowano z rozwiązania `tmpfs` na korzyść standardowych mechanizmów ulotności ze względu na większą przenośność pomiędzy systemami Mac, Windows i Linux.
   
3. **Synchronizacja Zadań:**
   Zmienna `CELERY_TASK_ALWAYS_EAGER=True` wymusza na zadaniach Celery tryb synchroniczny. W środowisku TEST unika się w ten sposób konieczności uruchamiania dodatkowych kontenerów dla Workera i Beata, co przyspiesza testy i ułatwia weryfikację.
   
4. **Obraz "Testing" (Kopiowanie vs Volume Mount):**
   W pliku `compose.test.yml` aplikacja zasilana jest z targetu budowania `testing`. Kategorycznie zabrania się używania podmontowanych wolumenów (`volumes: - .:/app`) charakterystycznych dla trybu DEV. Kod jest na sztywno wkopiowany do obrazu w procesie `docker build`, dając gwarancję testowania docelowego artefaktu wdrożeniowego.

---

## Decyzja 2: Pancerne Zarządzanie Wolumenami PostgreSQL 18+

Aby zapewnić stabilność danych na środowiskach zachowujących stan (DEV, PRE-PROD, PROD) wobec zmian w architekturze wewnętrznej obrazów bazy danych:

1. **Podnoszenie Punktu Montowania (Mount Point):**
   Wolumen danych PostgreSQL we wszystkich środowiskach jest montowany wyżej w hierarchii folderów:
   ```yaml
   volumes:
      - postgis_data:/var/lib/postgresql

## Relacje (Related)
- **C4 Diagram:** docs/architecture/containers.puml
- **ADR-020 — Architektura Wdrożeń (Deployment & SRE):** Środowisko TEST implementuje zasadę izolacji środowisk i efemeryczności zdefiniowaną w ADR-020.
