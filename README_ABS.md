# 📚 Audiobookshelf SRE Deployment System (`absctl`)

Ten projekt to kompletny, odporny na awarie (fault-tolerant) system wdrażania i zarządzania infrastrukturą Audiobookshelf działającą na Docker Compose w środowisku WSL2. Został zaprojektowany w oparciu o filozofię **GitOps** oraz standardy **Site Reliability Engineering (SRE)**.

Jego główne filary to:
* **Zero-Downtime-like Deployments:** Orkiestrator `absctl` pilnujący spójności plików (Drift Detection) i wykonujący automatyczne zrzuty bezpieczeństwa (Snapshots).
* **Identity & Edge Security:** Integracja z Google OIDC (Single Sign-On), Cloudflare Tunnels (Zero Open Ports) oraz ścisła zgodność z polityką omijania Cache (Bypass Cache).
* **Deep Observability:** 6-warstwowy, hybrydowy monitoring z wykorzystaniem Uptime Kuma (HTTPS, Docker Socket :ro, Telemetria Tunelu, Monitory PUSH sprzętowe i procesowe).

---

## 🗂️ Struktura Katalogów

Aby system działał poprawnie, wymaga następującej struktury w głównym katalogu projektu:

```text
/home/dominik/Audiobookshelf
├── init.sh                    # Skrypt Bootstrap (Inicjalizacja środowiska od zera)
├── absctl                     # Główny orkiestrator (CLI)
├── docker-compose.yml         # Źródło prawdy o infrastrukturze
├── .env                       # Zmienne środowiskowe (Sekrety)
├── modules/                   # Skrypty wykonawcze (Logika systemu)
├── state/                     # Przechowuje informacje o ostatnim stabilnym stanie (LKG)
├── compose_versions/          # Archiwum plików docker-compose.yml
├── snapshots/pre-deploy/      # Szybkie migawki (tworzone przed każdym wdrożeniem)
├── backup/daily/              # Pełne noce kopie zapasowe
└── logs/                      # Logi operacyjne (rotowane co 14 dni)
```

---

## 🚀 Główne Polecenia (Orkiestrator `absctl`)

Plik `absctl` (AudioBookShelf ConTroL) to jedyny punkt wejścia do systemu. Służy do zarządzania całym cyklem życia aplikacji.

### `./init.sh` (Inicjalizator / Bootstrap)
Polecenie używane wyłącznie w sytuacji **stawiania środowiska całkowicie od zera** (np. po awarii sprzętu i migracji na nowy dysk, przed przywróceniem z backupu).
Skrypt generuje niezbędne drzewo katalogów logistycznych (`logs`, `snapshots`, `state` itp.) oraz powołuje do życia bezpieczne, zewnętrzne wolumeny Dockera (External Volumes), uniezależniając w ten sposób ich cykl życia od kaprysów pliku kompozycji. Dopiero po jednorazowym uruchomieniu tego skryptu, możliwe jest wywołanie poleceń `absctl`.

### `./absctl deploy` (Główny silnik aktualizacji)
Służy do wdrażania zmian w `docker-compose.yml` oraz aktualizacji kontenerów do najnowszych wersji. Wykonuje zautomatyzowany łańcuch zdarzeń:
1. **Walidacja:** Sprawdza poprawność składni YAML oraz środowiska.
2. **Guard:** Wykrywa "Drift" (zapobiega przypadkowemu usunięciu kontenerów).
3. **Snapshot:** Tworzy błyskawiczną migawkę bazy danych i konfiguracji.
4. **Deploy:** Pobiera nowe obrazy i uruchamia kontenery.
5. **Healthcheck:** Czeka (max 120s) na zgłoszenie statusu `healthy`.
6. **Decyzja:**
   * **SUKCES:** Zapisuje nowy stan referencyjny (`latest.yml`).
   * **PORAŻKA:** Wywołuje automatyczny Rollback do stanu sprzed sekundy.

### `./absctl rollback` (Ręczny wehikuł czasu)
Wymusza natychmiastowe zatrzymanie środowiska i przywrócenie bazy danych, konfiguracji oraz wolumenów do stanu z ostatniego udanego Snapshota. Operacja jest **idempotentna** (można ją wywołać wielokrotnie z tym samym skutkiem).

### `./absctl backup` (Kombajn danych)
Generuje ciężką, audytowalną kopię zapasową. Przeznaczony do uruchamiania z harmonogramu (Cron).

### `./absctl validate` (Dry-run)
Uruchamia wyłącznie skrypty sprawdzające (Validate + Guard) bez dokonywania żadnych zmian w działającym systemie.

---

## 🧩 Logika Modułów (Katalog `modules/`)

Każdy skrypt w folderze `modules/` odpowiada za jedną, odizolowaną funkcję.

### 1. `validate.sh` (Strażnik Środowiska)
* Sprawdza, czy Docker Daemon odpowiada.
* Weryfikuje istnienie pliku `.env` oraz kluczowych zmiennych (np. token Cloudflare).
* Wykonuje walidację składni YAML (`docker compose config`).
* Weryfikuje istnienie kluczowych, zewnętrznych wolumenów (chroniąc przed wyczyszczeniem stanu `external: true`).

### 2. `guard.sh` (Ochrona przed Driftem)
* Analizuje semantyczną strukturę poprzedniej wersji infrastruktury (`latest.yml`) w odniesieniu do bieżącej konfiguracji.
* Zatrzymuje wdrożenie ze statusem ERROR, jeśli wykryje usunięcie jakiejkolwiek usługi (np. `cloudflared`) lub wolumenu.
* **⚠️ JAK ŚWIADOMIE USUNĄĆ KONTENER:** Jeśli refaktoryzacja jest celowa, należy ominąć Guarda uruchamiając komendę z flagą:
  `ALLOW_REMOVAL=true ./absctl deploy`

### 3. `snapshot.sh` (Szybka Migawka przed aktualizacją)
* Aktywnie zamraża główny kontener aplikacyjny (`audiobookshelf`) na kilka sekund na czas trwania zapisu, aby zapobiec korupcji bazy danych SQLite i zjawiskom typu *torn-write*.
* Wykorzystuje **zapis atomiczny** (`mv -Tf` z folderu `.tmp`), gwarantując, że snapshot zostanie zapisany w 100% albo wcale.
* Utrzymuje porządek na dysku (automatyczna rotacja: zachowuje tylko 5 ostatnich, czystych wdrożeń).

### 4. `deploy.sh` & `health.sh` (Silnik Wykonawczy)
* `deploy.sh` zawsze używa flagi `--remove-orphans`, by nie zostawiać sierot (nieużywanych kontenerów w sieci).
* `health.sh` używa szablonów języka Go w `docker inspect`, by bezpiecznie weryfikować przejście kontenerów ze stanu `starting` w `healthy`, poddając się po 120 sekundach.

```text
🔄 FLOW WDROŻENIOWY (absctl deploy)
 ├─ validate (sprawdzenie składni i portów)
 ├─ guard (porównanie z latest.yml)
 ├─ snapshot (zamrożenie bazy i zrzut do tar.gz)
 ├─ compose pull (pobranie nowości)
 ├─ compose up (uruchomienie)
 └─ healthcheck (oczekiwanie na status 'healthy')
     ├─ SUKCES ──> nadpisanie latest.yml
     └─ PORAŻKA ─> rollback.sh (przywrócenie snapshota)
```

### 5. `rollback.sh` (Ratownik Systemowy)
* Identyfikuje ostatni działający stan na podstawie `state/last_snapshot`.
* Weryfikuje poprawność archiwum `.tar.gz` przed próbą jego wgrania na dysk produkcyjny.
* Używa flag `--force-recreate` oraz wymuszonego czyszczenia anonimowych wolumenów (`down -v`), aby zapewnić deterministyczny i czysty start ze starymi danymi.

### 6. `backup.sh` (Zarządzanie Czasoprzestrzenią)
* Skrypt przeznaczony na cotygodniowe archiwizowanie całej struktury produkcyjnej.
* Posiada twardy, systemowy **Lockfile (`flock`)**, który blokuje powielenie procesów w przypadku restartów maszyny, zapobiegając nadpisywaniu uciętych archiwów.
* Wymusza pauzę aplikacji (stop kontenera) na czas pakowania wolumenów, by wyeliminować modyfikację plików bazodanowych w locie.
* **Bezpieczeństwo Sekretów:** Ogranicza uprawnienia plików backupu (zawierających `.env`) wyłącznie dla administratora (`chmod 600`), przeciwdziałając eskalacji przywilejów w WSL.
* **Test Integralności:** Po spakowaniu, wykonuje test odczytu kontrolnego tar-a (`tar tzf`) oraz generuje sumy kontrolne SHA-256. 
* Informuje system monitoringu (Uptime Kuma) o sukcesie operacji. 

```text
💾 FLOW ARCHIWIZACYJNY (absctl backup / cron 3:00)
 ├─ lock (flock - blokada równoległa)
 ├─ stop kontenera (konsystencja bazy sqlite)
 ├─ snapshot wolumenów (tar.gz)
 ├─ start kontenera
 ├─ checksum (SHA256) + test integralności odczytu
 ├─ retention (usunięcie > 30 dni)
 └─ kuma push (wysłanie zielonego statusu do monitoringu)
```

### 7. `disk.sh` (Strażnik Przestrzeni WSL2)
* Autonomiczny skrypt monitorujący zajętość wirtualnego dysku (partycji root `/` w środowisku WSL).
* Działa w oparciu o mechanizm PUSH (Dead Man's Switch). 
* Jeśli zajętość dysku przekroczy zdefiniowany próg (domyślnie 90%), natychmiast wysyła sygnał błędu do Uptime Kuma, chroniąc silnik Docker oraz bazę SQLite przed korupcją spowodowaną brakiem miejsca.

---

## ⚙️ Automatyzacja (Harmonogram zadań)

W celu zautomatyzowania polityki bezpieczeństwa Danych (Disaster Recovery) oraz monitoringu sprzętowego, do harmonogramu Linuxa (Cron) wpięto niezbędne skrypty.

Aby edytować harmonogram, wpisz w terminalu: `crontab -e`
Wymagane wpisy dla tego projektu:

```bash
# Pełny cotygodniowy backup (w niedzielę o 11:00) z wysłaniem raportu PUSH do Uptime Kuma
0 11 * * 0 cd /home/dominik/Audiobookshelf && ./absctl backup

# Strażnik miejsca na wirtualnym dysku WSL2 (uruchamiany co 6 godzin)
0 */6 * * * bash /home/dominik/Audiobookshelf/modules/disk.sh
```

## 🗓️ Okna Serwisowe i Konserwacja (Maintenance)

System został zoptymalizowany tak, aby zapobiegać fałszywym alarmom (Alert Fatigue) podczas rutynowych zadań. 

**Tygodniowy Backup (Niedziela 11:00):**
Operacja backupu (`backup.sh`) celowo zatrzymuje główny kontener `audiobookshelf`, aby zapewnić spójność bazy danych. 
Aby zapobiec wysyłaniu fałszywych powiadomień o awarii, w panelu Uptime Kuma skonfigurowano **Okno Konserwacyjne (Maintenance Window)** na niedzielę w godzinach 11:00 - 11:05. W tym czasie powiadomienia są wstrzymane, a statystyki SLA (100% Uptime) pozostają nienaruszone.

**⚠️ ZŁOTA ZASADA ZMIANY HARMONOGRAMU:** 
Jeśli kiedykolwiek zdecydujesz się zmienić godzinę lub dzień wykonywania kopii zapasowej w harmonogramie Linuxa (`crontab -e`), **MUSISZ** również zaktualizować czas trwania "Konserwacji" w ustawieniach Uptime Kuma oraz zaktualizować komunikaty informacyjne dla użytkowników na stronie statusu i w panelu logowania ABS.

---

## 🚨 Sytuacje Awaryjne

**Co zrobić, gdy aplikacja nie działa (Error 502 / Offline)?**
1. System posiada auto-rollback. Prawdopodobnie sam już przywrócił stabilną wersję. Sprawdź logi w `logs/deploy.log`.
2. Jeśli problem wynika z awarii sprzętowej lub ręcznego zatrzymania, wywołaj:
   `./absctl rollback`
3. Sprawdź stan środowiska i logi Dockera, jeśli usługa nadal nie odpowiada. Pamiętaj, że zawsze możesz awaryjnie uruchomić Dockera pomijając skrypty: `docker-compose up -d`.