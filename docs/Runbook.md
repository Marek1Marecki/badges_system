# Runbook — podręcznik operacyjny

> **Wersja:** 1.1  
> **Data:** 2026-05-28  
> **Właściciel:** Dominik / AI Architect  
>
> **Cel:** Nowy developer (lub agent LLM) powinien być w stanie uruchomić projekt lokalnie i rozwiązać najczęstsze problemy infrastrukturalne (szczególnie w środowisku WSL2 / GeoDjango), czytając tylko ten dokument.

---

## Wymagania

| Narzędzie | Minimalna wersja | Instalacja / Uwagi |
|-----------|-----------------|------------|
| **Python** | 3.12+ | Instalowany i zarządzany przez narzędzie `uv`. |
| **uv** | 0.2+ | `curl -LsSf https://astral.sh/uv/install.sh | sh` |
| **Docker** | 24.x | Niezbędny do uruchomienia infrastruktury (PostGIS i Redis). |
| **System** | Ubuntu 22.04+ (WSL2) | **Środowisko natywne Windows nie jest obsługiwane.** Środowisko macOS: Nieprzetestowane, instalacja GDAL przez Homebrew może wymagać dodatkowej konfiguracji ścieżek zmiennych systemowych. |
| **Pakiety OS**| - | Wymagane natywne biblioteki przestrzenne dla GeoDjango: `sudo apt-get update && sudo apt-get install -y binutils libproj-dev gdal-bin` |

---

## Uruchomienie lokalne (Development)

### 1. Klonowanie i setup środowiska

```bash
git clone [REPO_URL]
cd pttk-badges-system

# Instalacja zależności przez uv (tworzy .venv i instaluje pre-commit)
make setup
```

### 2. Zmienne środowiskowe i Sekrety

Zgodnie z *Contract 10*, sekrety nigdy nie trafiają do kodu. Skopiuj szablon środowiska:
```bash
cp .env.example .env
```
W środowisku deweloperskim klasa `AppSettings` pobiera dane domyślne dla lokalnego Dockera (np. hasło bazy danych `postgres`). Zmienna `app_env=development` wyłącza część obostrzeń walidacyjnych (np. wymóg wyłączenia trybu debugowania). Na produkcji plik `.env` nie istnieje — konfiguracja przekazywana jest natywnie przez środowisko kontenera.

### 3. Baza danych i Kolejka (Docker)

```bash
# Uruchomienie bazy PostGIS oraz serwera Redis w tle
docker compose -f docker-compose.dev.yml up -d

# Utworzenie struktur relacyjnych
uv run python manage.py migrate

# Konto administratora (do logowania w panelu)
uv run python manage.py createsuperuser
```

### 4. Uruchomienie Serwisu (3 Terminale w dev)

Architektura mikroserwisowa wymaga 3 niezależnych procesów podczas developmentu:

**Terminal 1: Serwer Web (Django)**
```bash
uv run python manage.py runserver 8005
```

**Terminal 2: Worker Celery (Robotnik)**
```bash
uv run celery -A config worker -l info
```

**Terminal 3: Celery Beat (Nadzorca - Nocny Stróż OSM)**
```bash
uv run celery -A config beat -l info
```
*(Uwaga: w środowisku deweloperskim dla wygody można połączyć Workera i Beata flagą `-B`: `uv run celery -A config worker -B -l info`. Na produkcji **zakazuje się** takiego łączenia — muszą to być dwa osobne kontenery, aby umożliwić niezależne skalowanie poziome (Horizontal Scaling) dla Workerów).*

---

## 4. Zarządzanie Danymi Referencyjnymi (Data Seeding & Snapshots)

Nasz system ściśle oddziela **Dane Użytkowników** (logi, profile) od **Danych Referencyjnych** (odznaki, regiony, szczyty). 
Lokalna baza danych (DEV) traktowana jest jako "Środowisko Robocze" (Sandbox). Prawdziwym, jedynym źródłem prawdy (Single Source of Truth) o regulaminach PTTK i geografii są skompresowane pliki `json.gz` wraz z `manifest.json`, trzymane w katalogu `data/reference/` w repozytorium Git.

### Eksport danych (Zrzut Snapshotu)
**Kiedy używać:** Zawsze, gdy za pomocą panelu Django Admin wprowadzisz nową odznakę, zmodyfikujesz regulamin, dodasz nowy szczyt lub zaimportujesz dane z OSM.

**Komenda:**
```bash
uv run python manage.py export_reference_data
```

### Problem 5: Szare pinezki na mapie / Brak widocznej aktualizacji po zalogowaniu wejścia
**Objaw:** Po dodaniu logu wejścia lub subskrybowaniu odznaki szczyty na mapie nie zmieniają koloru, a zysk (100/n) to nadal 0 pkt.
**Przyczyna:** Wyłączony lub zawieszony Worker Celery, błąd rozjazdu kluczy (ID profilu vs ID konta) lub wygaśnięcie Cache.
**Rozwiązanie (Skrypt diagnostyczny):**
Otwórz powłokę systemową `uv run python manage.py shell` i uruchom skrypt analityczny:
```python
from django.contrib.auth import get_user_model
from django.core.cache import cache
from apps.tourists.models import UserBadgeProgress

print("\n--- KTO MA SUBSKRYPCJE? ---")
for prog in UserBadgeProgress.objects.all():
    print(f"Profile ID: {prog.profile_id} subskrybuje: {prog.badge.code}")

print("\n--- CO SIEDZI W CACHE REDIS? ---")
for u_id in get_user_model().objects.values_list("id", flat=True):
    data = cache.get(f"map_state:{u_id}")
    print(f"User/Profile {u_id}: {'TAK (Liczba kluczy: ' + str(len(data.get('colors', {}))) + ')' if data else 'BRAK'}")
```

---

## 6. Testowanie REST API (Tips & Tricks)

API wymaga uwierzytelnienia. Aby ominąć konieczność budowania pełnego flow autoryzacji Google OAuth w narzędziach takich jak Postman czy cURL w środowisku lokalnym, stosuj metodę "Kradzieży Sesji" (Session Hijacking):

1. Otwórz projekt w przeglądarce (np. `http://127.0.0.1:8005/`) i zaloguj się normalnie przez UI.
2. Otwórz Narzędzia Deweloperskie przeglądarki (F12) -> Zakładka *Application* / *Pamięć* -> *Cookies*.
3. Skopiuj wartość ciasteczka `sessionid`.
4. W Postmanie stwórz żądanie (np. `POST /api/v1/ascents/`).
5. W zakładce **Headers** dodaj nagłówek:
   * **Key:** `Cookie`
   * **Value:** `sessionid=TUTAJ_WKLEJ_WARTOŚĆ`
6. Narzędzie testowe uzyska pełny dostęp do API jako Twój zalogowany użytkownik (z wpiętym `profile_id`). Zabezpieczenie przed CSRF nie blokuje zapytań API, ponieważ widoki w `apps/api/views.py` są oznaczone dekoratorem `@csrf_exempt`.

---

## Wdrożenie produkcyjne i Rollback

### Wdrożenie
[Planowane i konfigurowane w **Fazie C** — Przed pierwszym publicznym wdrożeniem sekcja ta zostanie uzupełniona o:
- Procedurę migracji zerowej (Zero-Downtime deployment).
- Konfigurację i *orchestration* kontenerów Celery Worker / Beat jako osobnych procesów z limitami zasobów (Cgroups).
- Instrukcje osadzania biblioteki GDAL w końcowym obrazie `Dockerfile` (Stage 2).]

### Rollback (Wycofywanie zmian)
⚠️ **UWAGA KRYTYCZNA: Cofanie migracji (Rollback) przy operacjach PostGIS (typy geometryczne, indeksy przestrzenne) niesie ogromne ryzyko utraty integralności danych i kształtów wielokątów.**
- Nie wolno wykonywać rollbacku na produkcji bez wykonania pełnego, manualnego zrzutu bazy: `docker compose exec db pg_dump -U postgres badges_db > emergency_dump.sql`.
- Rollback migracji zawierających modyfikacje rozszerzeń PostGIS zawsze wymaga asysty i autoryzacji Lead Developera / DBA.

---

## 5. Uruchamianie Wdrożeń Produkcyjnych (PRE-PROD / Staging)

Środowisko `PRE-PROD` jest architektonicznym klonem (Twin) serwera `PROD` – posiada ten sam system plików (Read-Only), serwowanie przez Gunicorna, i obostrzenia bezpieczeństwa, z wyłączeniem warstwy Ingress (Caddy). Służy ono lokalnemu testowaniu stabilności nowych wersji przed wgraniem ich do chmury oraz odpalaniu testów wideo (Playwright).

**Zasady:** Nigdy nie edytuj plików bezpośrednio na tym środowisku. Obraz nie przebudowuje się na żywo po zmianach w kodzie.

### Jak podnieść PRE-PROD lokalnie?

1. **Kompilacja i Wersjonowanie (Build Once):**
   Zbuduj lokalnie (lub pobierz) docelowy obraz ze wstrzykniętą aplikacją (tag może być dowolny, polecamy hash z gita lub wersję):
   ```bash
   docker build --target production -t badges-system:latest .
   ```
2. **Definicja Sekretów:**
   Stwórz plik `.env.preprod.secrets` i wstaw tam wszystkie klucze z `.env.example` (baza danych musi nazywać się inaczej niż na DEV, np. `badges_preprod_db`). Upewnij się, że zdefiniowałeś `IMAGE_TAG=latest`.
3. **Wdrożenie Aplikacji i Bazy (Application Release):**
   Wykorzystaj skrypt ujednolicający (który dba o wyizolowanie przestrzeni nazw):
   ```bash
   make preprod-deploy
   ```
4. **Bootstrapping (Pierwsze uruchomienie po starcie bazy):**
   Zasil bazę "Złotym Standardem" ze snapshotów referencyjnych w Gicie.
   ```bash
   # UWAGA: Podstaw właściwą wersję snapshotu w miejsce daty (np. 2026.07.09)
   make preprod ARGS="exec web ./scripts/bootstrap.sh TWOJA_DATA_SNAPSHOTU"
   ```
5. **Diagnostyka Środowiska (SRE):**
   Uruchom sprawdzian odporności i podłączenia wolumenów bazy (ADR-025):
   ```bash
   make preprod-status
   ```
   Jeśli weryfikacja rekordów bazy w konsoli wskazuje na pomyślny wczyt szczytów i odznak, serwer `PRE-PROD` nasłuchuje lokalnie pod adresem: `http://localhost:8008/` (dla wdrożenia Gunicorna) i jest gotowy na przyjęcie testów Playwright.

### Rollback (Wycofywanie zmian)
Zgodnie ze strategią określoną w `ADR-024` (Expand and Contract), procedura wycofywania wersji zepsutego kodu ogranicza się wyłącznie do "revertowania" wskaźnika obrazu w pliku środowiskowym i powtórnego przepięcia ruchu na starszą aplikację:
1. Zmień `IMAGE_TAG` w pliku `.env.preprod.secrets` na wcześniejszą, działającą wersję.
2. Zastosuj komendę wdrożeniową: `make preprod-deploy`. 
Aplikacja, dzięki kompatybilności wstecznej bazy, ożyje w poprzedniej wersji.
```

---

---

## Logi i monitoring

| Komponent | Gdzie szukać lokalnie | Środowisko docelowe (Produkcja) |
|-----------|-----------------------|---------------------------------|
| **Django (Web)** | `stdout` w Terminalu 1. Dzięki Loguru, format to czytelny, kolorowy tekst. | Strumień JSON przechwytywany przez demona Dockera (Logstash / ELK). |
| **Celery Tasks** | `stdout` w Terminalu 2. Raporty o wynikach pobierania z OSM i przeliczania klastrów CQRS. | Osobny indeks strumienia JSON w ELK. Błędy 500 kierowane do Sentry. |
| **PostgreSQL** | `docker compose logs -f db` | Narzędzia analityczne bazy w chmurze (np. AWS RDS Logs). |

---

## Typowe problemy i rozwiązania

### Problem 1: `Temporary failure in name resolution` w WSL2
**Objaw:** Celery lub skrypty rzucają timeoutem HTTP, nie mogąc połączyć się z zewnętrznym API (Overpass), podczas gdy przeglądarka w Windowsie ma internet.  
**Przyczyna:** Środowisko WSL2 traci poprawną konfigurację DNS po wybudzeniu komputera z uśpienia, przez co Python nie potrafi zamienić domen na adresy IP.  
**Rozwiązanie:** 
Zresetuj i wymuś publiczne DNSy wewnątrz środowiska wirtualnego Linuxa:
```bash
sudo rm /etc/resolv.conf
sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'
sudo bash -c 'echo "nameserver 1.1.1.1" >> /etc/resolv.conf'
```

### Problem 2: Błąd 406 Not Acceptable od Overpass API
**Objaw:** Pobieranie danych OSM ulega natychmiastowej awarii (HTTP 406) np. z serwerów `overpass-api.de`.  
**Przyczyna:** WAF i Load Balancery serwerów OSM chronią infrastrukturę przed skryptami używającymi metody `POST` lub twardego nagłówka `Accept: application/json` w poszukiwaniu botów.  
**Rozwiązanie:** Adapter OSM (`infrastructure/adapters/osm_adapter.py`) został z premedytacją zaprojektowany tak, aby z pełnym sukcesem ominąć zaporę WAF używając metody `GET`, fałszywych nagłówków przeglądarki Chrome oraz tolerancyjnego negocjowania treści (`*/*`). *Nie próbuj "naprawiać" lub optymalizować nagłówków adaptera HTTPx/Urllib!*

### Problem 3: `admin.E013` przy użyciu `filter_horizontal`
**Objaw:** Błąd uruchomienia serwera przy wprowadzaniu Odznaki.  
**Przyczyna:** Próba wdrożenia widżetu `filter_horizontal` na polu `ManyToManyField` posiadającym narzuconą, własną tabelę za pomocą klauzuli `through`.  
**Rozwiązanie:** Zrezygnowaliśmy z twardych kolumn kolejności na poziomie relacyjnym Puli Szczytów. `BadgeVersionModel.pool_peaks` to prosta relacja M2M z pełnym wsparciem w UX Admina. Kolejność jest rygorem wynikającym z `BadgeTierModel`, a nie struktury tabel.

### Problem 4: `ImportError: libgdal.so` przy starcie lub imporcie Django
**Objaw:** `uv run python manage.py` wyrzuca ścianę błędu o braku plików obiektów współdzielonych (*shared objects*) po zainstalowaniu zależności.  
**Przyczyna:** Środowisko nie posiada systemowych bibliotek graficznych i geodezyjnych C++, których jako bazy wymaga pakiet GeoDjango. Menedżer `uv` i `pip` nie potrafią instalować zależności systemowych.  
**Rozwiązanie:** Upewnij się, że spełniłeś wymagania opisane w sekcji Pakiety OS:
`sudo apt-get install binutils libproj-dev gdal-bin`

### Problem 6: Worker Celery wykonuje stary, "nieistniejący" kod (Błędy sygnatur i AttributeError)
**Objaw:** Po zmianie nazwy metody w serwisie domenowym (np. z `recalculate_for_user` na `recalculate_for_profile`) i zaktualizowaniu zadania w `tasks.py`, zadania w kolejce nadal wybuchają z błędem typu "Obiekt nie posiada takiej metody". Lintery (`make check`) nie zgłaszają żadnych problemów.
**Przyczyna:** Celery Workers to długożyjące procesy operacyjne. Wczytują one wszystkie moduły Pythona do pamięci RAM przy starcie i **nigdy** same z siebie ich nie odświeżają, ignorując zapisy w plikach `.py` dokonywane w trakcie developmentu.
**Rozwiązanie:** Po **KAŻDEJ** zmianie w kodzie logicznym zlokalizowanym w `domain/`, `application/` lub `tasks.py`, należy bezwzględnie "zabić" proces Workera w terminalu (`Ctrl+C`) i uruchomić go ponownie (`uv run celery -A config worker -l info`).
