# ADR-026 — PostgreSQL Volume Layout (PostgreSQL 18+)

> **Status:** `proposed`
> **Data:** 2026-07-19
> **Autor:** Dominik / AI Architect
> **Zastępuje:** —
> **Zastąpiony przez:** —

---

## Kontekst

Projekt korzysta z obrazu `postgis/postgis`, opartego na oficjalnym obrazie
`postgres`. Od wersji PostgreSQL 18 oficjalny obraz zmienił domyślną
lokalizację katalogu danych (`PGDATA`) z płaskiej ścieżki
`/var/lib/postgresql/data` na strukturę wersjonowaną per major:
`/var/lib/postgresql/<major>/docker` (np. `/var/lib/postgresql/18/docker`).
Celem tej zmiany po stronie maintainerów obrazu jest wsparcie dla
`pg_upgrade --link` między głównymi wersjami bez konieczności migracji
wolumenu — nowa i stara wersja danych mogą współistnieć jako podkatalogi
tego samego, nadrzędnego wolumenu.

W tym projekcie doszło do incydentu utraty danych (1163 obiekty turystyczne,
konfiguracja użytkowników) w środowisku DEV: plik `compose.yml` montował
wolumen bezpośrednio pod starą, płaską ścieżką
(`postgis_data:/var/lib/postgresql/data`), podczas gdy obraz w użyciu był
już w wersji PostgreSQL 18. Efekt: kontener przy starcie nie znalazł swojego
oczekiwanego katalogu danych pod `/var/lib/postgresql/18/docker` (bo wolumen
był podpięty gdzie indziej), więc **utworzył nowy, pusty klaster bazy
danych** zamiast zgłosić błąd. `db healthy` w healthchecku nie wykrywa tego
przypadku — proces Postgres faktycznie odpowiada, tylko na pustej bazie.
Dane nie zostały fizycznie skasowane, ale stały się nieosiągalne dla
aplikacji bez ręcznej interwencji.

**Pytanie decyzyjne:**
Jak zamontować wolumen danych PostgreSQL, żeby był poprawny dla PostgreSQL
18+, przetrwał przyszłe migracje na kolejne wersje major (`pg_upgrade
--link`), i żeby niedopasowanie ścieżki nie prowadziło po cichu do utraty
dostępu do danych?

---

## Opcje rozważane

### Opcja A: Montowanie wprost pod wersjonowaną ścieżką (`.../18/docker`)

**Opis:** `postgis_data:/var/lib/postgresql/18/docker`.

**Plusy:** Działa dla obecnej wersji (18) bez dodatkowej wiedzy o warstwie
niżej.

**Minusy:** Przy przyszłym upgrade do PostgreSQL 19 ścieżka zmieni się na
`.../19/docker` — wymagałoby to zmiany definicji wolumenu w compose i
ręcznego przeniesienia danych między "wersjonowanymi" podkatalogami tego
samego wolumenu. Dokładnie odwrotność tego, co ta zmiana w oficjalnym
obrazie miała ułatwić.

### Opcja B: Montowanie rodzica (`/var/lib/postgresql`) — Wybrane

**Opis:** `postgis_data:/var/lib/postgresql`. Obraz sam zarządza
podkatalogiem `<major>/docker` wewnątrz tego wolumenu.

**Plusy:** Zgodne z zamierzonym przez maintainerów obrazu wzorcem — ten sam
wolumen przetrwa upgrade do PostgreSQL 19+ bez zmiany definicji w compose.
`pg_upgrade --link` może operować na obu podkatalogach (`18/docker`,
`19/docker`) w obrębie tego samego wolumenu.

**Minusy:** Wymaga jednorazowej migracji dla istniejących środowisk, które
już mają dane pod starą, płaską ścieżką (patrz sekcja "Migracja istniejącego
wolumenu" niżej) — nie jest to zmiana neutralna dla środowisk z danymi.

---

## Decyzja

Montujemy wolumen danych PostgreSQL pod ścieżką **rodzica**,
`/var/lib/postgresql`, nie pod konkretną, wersjonowaną podścieżką:

```yaml
volumes:
  - postgis_data:/var/lib/postgresql
```

**Świadomie NIE ustawiamy zmiennej `PGDATA` jawnie** (np. na
`/var/lib/postgresql/18/docker`). Entrypoint oficjalnego obrazu sam oblicza
właściwą podścieżkę na podstawie zainstalowanej wersji majorowej — jawne
wpisanie konkretnego numeru wersji w `PGDATA` odtworzyłoby dokładnie
Opcję A (odrzuconą wyżej) w innym miejscu: przy przyszłym upgrade do
PostgreSQL 19 zahardkodowana wartość `18/docker` przestałaby być poprawna,
a nic by o tym głośno nie ostrzegło.

Dotyczy to `compose.yml` (wspólnego dla wszystkich środowisk) oraz każdego
środowiska, które w przyszłości mogłoby definiować własny, niezależny
wolumen Postgresa.

### Jawne nazywanie wolumenów (`name:`)

Ta sama klasa ryzyka co niedopasowanie PGDATA — tylko na poziomie
**tożsamości wolumenu**, nie ścieżki wewnątrz niego — dotyczy domyślnego
nazewnictwa wolumenów przez Docker Compose (`<nazwa_projektu>_<klucz>`).
Jeśli nazwa projektu Compose kiedykolwiek się zmieni (inny katalog,
`COMPOSE_PROJECT_NAME`, flaga `-p`), Compose utworzy **nowy, pusty wolumen
o innej wygenerowanej nazwie**, zamiast podpiąć się pod istniejące dane —
identyczny mechanizm cichej utraty dostępu jak przy niedopasowaniu ścieżki
PGDATA, tylko jeden poziom wyżej.

Dlatego wolumeny `postgis_data`/`redis_data` w `compose.yml` mają jawnie
przypisaną nazwę (`name:`), niezależną od kontekstu, w jakim wywoływany
jest `docker compose`. Zmiana nazwy istniejącego, już zawierającego dane
wolumenu na nazwę INNĄ niż ta, pod którą Docker go faktycznie zarejestrował
(weryfikowalne przez `docker volume ls`), podlega tej samej procedurze co
zmiana ścieżki PGDATA: obowiązkowy `dev-backup` przed zmianą, nigdy "w
locie" bez sprawdzenia.

### Kontrola operacyjna (nie tylko konfiguracja)

Sam poprawny zapis w `compose.yml` nie jest wystarczający — incydent, który
doprowadził do tej decyzji, nastąpił mimo że w momencie jego wystąpienia
konfiguracja "wyglądała" na rozsądną. Dlatego:

1. `scripts/dev-status.sh` weryfikuje rzeczywisty punkt montowania przez
   `docker inspect` ORAZ, niezależnie, przez zapytanie do samego procesu
   PostgreSQL (`SHOW data_directory;`) — dwie różne perspektywy tej samej
   kontroli, celowo bez zakładania z góry konkretnego numeru wersji
   w oczekiwanej ścieżce.
2. `scripts/dev-backup.sh` musi zostać wykonany **przed** jakąkolwiek zmianą
   wersji obrazu PostgreSQL — nie jest to zalecenie, tylko wymagany krok w
   procedurze aktualizacji (patrz Warunek rewizji).
3. `scripts/dev-reset.sh` domyślnie proponuje backup przed jakąkolwiek
   operacją usuwającą wolumeny.

### Migracja istniejącego wolumenu

Środowisko, które ma już dane pod starą ścieżką
(`postgis_data:/var/lib/postgresql/data`, PostgreSQL ≤17), **nie może**
bezpiecznie przejść na nowy mount przez samą zmianę pliku `compose.yml`.
Wymagany jest jawny `pg_dump`/`pg_restore` (patrz `scripts/dev-backup.sh` /
`scripts/dev-restore.sh`) — analogicznie do dowolnej migracji między
niezgodnymi wersjami major PostgreSQL, zgodnie z ADR-024 (Expand and
Contract) w odniesieniu do zmian niezgodnych wstecz.

---

## Konsekwencje

### Pozytywne
- Wolumen przetrwa przyszłe aktualizacje PostgreSQL (19+) bez zmiany
  definicji compose ani ręcznego przenoszenia danych.
- Zgodność z zamierzonym przez maintainerów obrazu wzorcem — mniejsze ryzyko
  niespodzianek przy kolejnych aktualizacjach obrazu bazowego.
- `dev-status.sh` wykrywa niedopasowanie mountu automatycznie, zamiast
  polegać wyłącznie na tym, że ktoś to zauważy ręcznie.

### Negatywne / Działania wymagane
- Każde środowisko z danymi pod starą ścieżką wymaga jednorazowej,
  kontrolowanej migracji (backup + zmiana konfiguracji + restore) — nie
  wolno tego robić "w locie" bez backupu.
- Każda przyszła zmiana wersji major obrazu PostgreSQL wymaga wykonania
  `dev-backup` (lub odpowiednika dla PRE-PROD/PROD) jako obowiązkowego,
  nie opcjonalnego kroku poprzedzającego.

---

## Warunek rewizji

Rewizja wymagana przy: (a) zmianie strategii wolumenów przez maintainerów
oficjalnego obrazu `postgres`/`postgis`, (b) przejściu na zarządzaną usługę
bazodanową (RDS/Cloud SQL i podobne), gdzie ta decyzja przestaje mieć
zastosowanie, (c) wprowadzeniu analogicznego mechanizmu dla PRE-PROD/PROD
(ten ADR w obecnej formie koncentruje się na incydencie w DEV — rozszerzenie
procedury `dev-backup`-przed-upgrade na `release-database.sh` dla
środowisk wdrożeniowych wymaga osobnej decyzji, potencjalnie uzupełnienia
tego dokumentu).

## Relacje (Related)
- **ADR-024 — Strategia Migracji (Expand and Contract):** Zmiana punktu montażowania wolumenu PostgreSQL wymaga jednorazowej, kontrolowanej migracji (backup + zmiana konfiguracji + restore), zgodnie z zasadami niezgodnych wstecz zmian z ADR-024.
