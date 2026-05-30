# 🏛️ Architektura Systemu Audiobookshelf SRE

Niniejszy dokument stanowi kompletną mapę architektoniczną prywatnego systemu strumieniowania audiobooków (`audiobooksdominika.online`). System został zaprojektowany z wykorzystaniem standardów korporacyjnych (Enterprise SRE, Defense in Depth, GitOps-lite), zoptymalizowany pod kątem bezpieczeństwa (Zero Open Ports), natywnej obsługi aplikacji mobilnych oraz bezobsługowego zarządzania awariami.

---

## 🗺️ Diagram Przepływu (High-Level Topology)

```text
[Użytkownicy / Aplikacje Mobilne ABS]
       │
      (HTTPS / OIDC Auth / HSTS Enforced)
       ▼
 ☁️ CLOUDFLARE EDGE (WAF, SSL, Bypass Cache) ──▶ [Google Cloud Platform OIDC]
       │                                            (Zarządzanie Tożsamością)
      (Zaszyfrowany tunel outbound)
       ▼
 🖥️ HOST LOCAL (Windows 11 / Router z NAT)
       │
 🐧 WIRTUALIZATOR (WSL2 / Linux ext4)
       │
 🐳 DOCKER ENGINE
       │
       ├─▶ 🌐 Sieć wirtualna: abs_net (Bridge)
       │      │
       │      ├── 🚇 cloudflared (Zarządca tunelu)
       │      ├── 📻 audiobookshelf (Główny Serwer ABS)
       │      │      ├── 📚 audioteka-abs (Metadane PL)
       │      │      ├── 📚 lubimyczytac-abs (Metadane PL)
       │      │      └── 📚 abs-storytel (Metadane PL/EN)
       │      │
       │      └── 👁️ uptime-kuma (Monitoring wewn/zewn)
       │
       └─▶ 💾 Warstwa Danych (Storage)
              ├── Wolumeny ext4 (Baza SQLite, Konfiguracja, Cache)
              └── Bind Mount NTFS (Partycja D: - pliki mp3/m4b)
```

---

## 1. 🛡️ Warstwa Brzegowa i Bezpieczeństwa (The Edge & Identity)

System celowo nie posiada otwartych portów na domowym routerze. Cały ruch wejściowy jest filtrowany i proxy'owany przez infrastrukturę Cloudflare. Dostęp administracyjny do panelu kontrolnego Cloudflare (Control Plane) zabezpieczony jest sprzętowo/programowo za pomocą wieloskładnikowego uwierzytelniania (MFA).

### Szyfrowanie i Zgodność Strumieniowania (Cloudflare DNS & Proxy)
*   **Media Streaming Compliance (Bypass Cache):** Aby zachować 100% zgodności z Regulaminem Świadczenia Usług (TOS) darmowego planu Cloudflare, zaimplementowano dedykowaną regułę dla domeny (`audiobooksdominika.online`), która nakazuje sieci CDN omijanie pamięci podręcznej (Bypass Cache). Cloudflare pełni wyłącznie rolę bezpiecznego tunelu, ale nie zapisuje na swoich serwerach przesyłanych plików audio (mp3/m4b), chroniąc domenę przed banem za nadużycia.
*   **Full SSL/TLS Strict & HSTS:** Ruch HTTP jest rygorystycznie przekierowywany na HTTPS na warstwie chmury. Wdrożono politykę **HTTP Strict Transport Security (HSTS)** z 6-miesięcznym czasem wygasania (`Max-Age: 6 months`, włączone subdomeny), wymuszając na przeglądarkach klientów wyłącznie szyfrowane połączenia z serwerem.

### Ochrona Aplikacji i Bot Mitigation (Cloudflare WAF)
*   **Bot Fight Mode:** Aktywne heurystyczne wykrywanie i blokowanie złośliwego, zautomatyzowanego ruchu przed dotarciem do serwera domowego.
*   **Geo-Blocking:** Blokowanie ruchu spoza zadeklarowanych terytoriów (obecnie spoza Polski).
*   **Rate Limiting:** Zabezpieczenie ścieżek logowania przed atakami słownikowymi i Brute-Force (blokada po 10 błędnych logowaniach w krótkim czasie).
*   **WAF Bypass (Korytarz Życia):** Wyjątek bezpieczeństwa dla ścieżki `/auth/openid/*`, pozwalający na powrót z zewnętrznym tokenem autoryzacyjnym bez interwencji wyzwań JavaScript (JS Challenge).

### Uwierzytelnianie Główne (Google Cloud Platform OIDC)
*   Zrezygnowano z Cloudflare Access przed główną aplikacją ABS, aby zachować 100% natywnej funkcjonalności aplikacji mobilnych (Android Auto, Apple CarPlay, offline sync).
*   **OpenID Connect (OIDC):** Autoryzacja użytkowników została oddelegowana do zewnętrznego dostawcy tożsamości (GCP).
*   **Zero-Registration Policy:** Audiobookshelf ma zablokowaną otwartą rejestrację. Tylko konta o adresach e-mail wprowadzonych ręcznie przez Administratora do lokalnej bazy ABS zostaną wpuszczone przez platformę Google. W systemie zawsze pozostaje jedno, silnie zahasłowane konto lokalne (Emergency Admin) odporne na awarie usług zewnętrznych.

### Cloudflare Zero Trust (Zarządzanie i Monitoring)
*   Używany wyłącznie do ochrony administracyjnej strefy monitoringu (pulpit nawigacyjny Uptime Kuma na `status.audiobooksdominika.online/dashboard`).
*   Wymaga podania jednorazowego kodu OTP (One-Time Password) wysłanego na zadeklarowany adres e-mail Administratora. Publiczna strona statusu dla użytkowników pozostaje widoczna dla wszystkich.

---

## 2. 🖥️ Warstwa Infrastruktury i Wirtualizacji (Host OS)

System działa na maszynie domowej opartej o system operacyjny Microsoft Windows.

*   **Host OS:** Windows 11.
*   **Hypervisor / Środowisko:** WSL2 (Windows Subsystem for Linux). Stanowi pełnoprawne środowisko jądra Linux, pozwalające na natywne uruchamianie kontenerów.
*   **System Plików Wirtualnych (VHDX):** Główny dysk środowiska WSL (`ext4`), na którym przechowywane są bazy danych i konfiguracje Dockera w celu zapewnienia maksymalnej wydajności I/O.
*   **System Plików Gospodarza (NTFS):** Bezpośrednie montowanie partycji systemu Windows (Dysk `D:/Audiobooki`) do środowiska WSL. Służy wyłącznie do przechowywania "zimnych" i ciężkich danych (pliki audio), chroniąc dysk systemowy przed przepełnieniem.
*   **Docker Daemon Logging (Zarządzanie przestrzenią):** Aby zapobiec zjawisku cichego wyczerpywania pamięci wirtualnej hosta przez zapętlone logi aplikacyjne, silnik Docker Desktop został skonfigurowany globalnie (`daemon.json`). Używa sterownika `json-file` z drastycznie ograniczonym limitem rotacji dla wszystkich kontenerów (`max-size: 10m`, `max-file: 3`).

---

## 3. 🐳 Warstwa Orkiestracji (Containerization)

Całość aplikacji uruchamiana jest za pomocą silnika Docker Engine i deklaratywnie definiowana poprzez `docker-compose.yml`.

*   **Isolacja Sieciowa (`abs_net`):** Prywatna sieć typu *bridge*. Żaden kontener (poza Uptime Kuma udostępnianym lokalnie na porcie 3001) nie wystawia portów bezpośrednio na maszynę WSL. Cała komunikacja ze światem odbywa się za pomocą wewnętrznego przekierowania ruchu z tunelu.
*   **Docker Volumes (Stateful Data):** Zewnętrznie zarządzane wolumeny (`external: true`). Kompozycja Dockera nie ma prawa ich usunąć. Separacja *Runtime* od *State*.
*   **Zarządzanie Sekretami (Secrets Management):** Wrażliwe dane (Tokeny Cloudflare, klucze API) nie są zapisywane jawnym tekstem w kodzie kompozycji. Przekazywane są w izolowanym pliku `.env`, który chroniony jest restrykcyjnymi uprawnieniami systemu plików Linux (`chmod 600`), zapobiegając nieautoryzowanemu odczytowi.

---

## 4. 📦 Warstwa Aplikacyjna (The Stack)

Wykaz usług działających w klastrze (Kontenery):

### 1. `audiobookshelf` (Core Service)
*   Główne serce systemu. Serwuje interfejs webowy, zarządza bazą danych (SQLite), sesjami użytkowników oraz strumieniowaniem mediów.
*   **Optymalizacje:** Parametry `ulimits` podniesione do 65536, aby obsłużyć masowe skanowanie tysięcy plików.
*   **Healthcheck:** Wbudowany test nasłuchiwania portu 80 (`nc`), warunkujący uruchomienie innych usług.

### 2. `cloudflared` (Inbound Router)
*   Kontener nawiązujący szyfrowane połączenie wychodzące do sieci Cloudflare. 
*   **Polityka zaufania:** Uruchamia się tylko, jeśli usługa `audiobookshelf` zgłosi status `healthy`.
*   **Read-Only RootFS:** Działa w trybie "Tylko do odczytu", co drastycznie ogranicza wektory ataków typu RCE.

### 3. Dostawcy Metadanych (`lubimyczytac`, `audioteka`, `storytel`)
*   Zestaw mikroserwisów dostarczających polskojęzyczne okładki i opisy.
*   Podobnie jak router krawędziowy, pracują na warstwie **Read-Only Root Filesystem**, zwiększając postawę bezpieczeństwa systemu (Security Posture).

### 4. `uptime-kuma` (Obserwowalność i Monitoring)
*   Serwer centralnego monitoringu z wbudowanym interfejsem graficznym.
*   Utrzymuje własny wbudowany `healthcheck` (odpytujący API w interwale 30s).
*   Zaimplementowano hybrydowy model monitorowania produkcyjnego (Observability Layer):
    1.  **Warstwa Edge (Zewnętrzna):** Sprawdzanie publicznego URL z weryfikacją słowa kluczowego.
    2.  **Warstwa Sieciowa (Tunel):** Odpytywanie metryk kontenera `cloudflared` (port `2000`).
    3.  **Warstwa Aplikacji (HTTP Wewnętrzne):** Monitoring kontenera `audiobookshelf:80` w sieci izolowanej.
    4.  **Natywna Warstwa Jądra (Docker Socket):** Integracja z Docker Engine poprzez zmapowane gniazdo systemowe (`/var/run/docker.sock`). Gniazdo zamontowane jest w trybie **Tylko do odczytu (`:ro`)**, eliminując ryzyko eskalacji uprawnień (Privilege Escalation), dając wgląd w Restart Loops czy OOM Kills.
    5.  **Warstwa Sprzętowa i Danych (Push):** Monitory pasywne (Dead Man's Switch) audytujące nocny backup (`backup.sh`) oraz zajętość wirtualnego dysku WSL2 (`disk.sh`).
    6.  **Warstwa Certyfikatów:** Automatyczna weryfikacja ważności certyfikatów SSL/TLS.
    7.  **Zarządzanie Oknami Serwisowymi (SLA Protection):** Wdrożono natywne harmonogramy konserwacji (Maintenance Windows) skorelowane z zadaniami `cron` (cotygodniowy backup o 11:00 w niedzielę). Zapobiega to zjawisku szumu informacyjnego (Alert Fatigue).
    8.  **Zewnętrzny Punkt Obserwacyjny (External Watchdog):** W celu wyeliminowania problemu "Kto pilnuje strażnika?" (tzw. Single Point of Failure na warstwie zasilania/łącza fizycznego), system lokalny wspierany jest przez zewnętrzną usługę chmurową UptimeRobot. Odpytuje ona publiczny adres domeny z zewnątrz klastra, gwarantując dostarczenie alertu Push na urządzenie mobilne administratora w sytuacji całkowitej utraty zasilania serwera domowego (Blackout) lub krytycznej awarii domowego łącza internetowego.
---

## 5. ⚙️ Warstwa SRE i Automatyzacji (absctl)

Autorski system CI/CD działający lokalnie. Oparty o powłokę Bash zestaw modułów `absctl` eliminuje ryzyko błędu ludzkiego podczas operacji administracyjnych.

### Komponenty Logiczne Systemu:
*   **Policy & Syntax Engine (`validate.sh`):** Waliduje składnię YAML, bada dostępność Daemona Docker oraz weryfikuje istnienie krytycznych zmiennych środowiskowych i wolumenów typu `external`.
*   **Drift Detector (`guard.sh`):** Analizuje drzewo logiczne YAML-a. Porównuje aktualny plik z ostatnio zatwierdzonym stanem referencyjnym (`latest.yml`), chroniąc przed przypadkowym usunięciem linijek w konfiguracji.
*   **Atomic State Manager (`deploy.sh`, `health.sh`):** Silnik aktualizacji. Posiada aktywny wyłącznik czasowy (Timeout 120s) sprawdzający status `healthy`.
*   **Wehikuł Czasu (`rollback.sh`):** Moduł zdolny do całkowitego odtworzenia zatrzymanej infrastruktury, nadpisania plików konfiguracyjnych i odtworzenia bazy SQLite z bezstratnego zrzutu. Operacja jest idempotentna.

---

## 6. 💾 Warstwa Zarządzania Danymi (Disaster Recovery)

Dane w systemie zostały ściśle podzielone na dwie kategorie:

1.  **Audiobooki (Media):** Przechowywane bezpiecznie na partycji Windows (NTFS). Nie podlegają backupowi ze strony środowiska Docker z uwagi na statyczny charakter (łatwe do odtworzenia z fizycznych dysków-matek).
2.  **Konfiguracja i Metadane (State):** Dane krytyczne, zapisane na wysoce wydajnym dysku WSL2 (ext4). Podlegają reżimowi podwójnej ochrony:

*   **Pre-Deploy Snapshots (`snapshot.sh`):**
    *   Częstotliwość: Tworzone każdorazowo przed poleceniem `deploy`.
    *   Charakterystyka: Błyskawiczne zrzuty, zapisywane atomowo. Kontener ulega chwilowemu zamrożeniu, aby uniknąć uszkodzeń bazy (Torn Writes). Rotowane do 5 ostatnich instancji.
*   **Weekly Scheduled Backups (`backup.sh`):**
    *   Częstotliwość: Uruchamiane z mechanizmu Linux `cron` raz w tygodniu (Niedziela 11:00).
    *   Charakterystyka: Zgodnie z zasadą logicznej separacji danych, fizyczne archiwum docelowe wyprowadzono poza system plików wirtualizatora WSL2, kierując zrzuty bezpośrednio na dysk przestrzeni gospodarza (np. `/mnt/d/Audiobookshelf_Backup`). Zapewnia to przetrwanie danych krytycznych w przypadku korupcji pliku `.vhdx` lub awarii dysku systemowego `C:`. Skrypt tworzy kompleksowy obraz systemu, generuje sumy kontrolne (`SHA256`) oraz utrzymuje 30-dniową rotację po stronie dysku `D:`.
--- 