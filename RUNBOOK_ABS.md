# 🛠️ RUNBOOK: Podręcznik Operatora (Admin Guide)

Ten dokument to instrukcja krok po kroku, jak zarządzać środowiskiem Audiobookshelf na co dzień. Zawiera scenariusze operacyjne (co zrobić, gdy...) oraz złote zasady, których nie wolno łamać.

---

## 🛑 Złote Zasady Środowiska

1. **NIGDY nie używaj ręcznie poleceń `docker-compose up` ani `docker-compose down`.** Całym cyklem życia zarządza orkiestrator `./absctl`. Jeśli zrobisz coś z pominięciem orkiestratora, uszkodzisz historię wersji (Plik `latest.yml`) i system rollbacku przestanie działać.
2. **Plik `compose_versions/latest.yml` jest ŚWIĘTY.** Służy on systemowi do porównywania różnic. Nigdy go nie edytuj. Zmiany wprowadzaj tylko w głównym pliku `docker-compose.yml`.
3. **Pamiętaj, że pracujesz na WSL2.** Jeśli zresetujesz komputer z Windowsem, upewnij się, że usługa Docker Desktop / silnik WSL został poprawnie uruchomiony, zanim zaczniesz cokolwiek wdrażać.

---

## 📖 Scenariusze Operacyjne (Dzień z życia Admina)

### Sytuacja 1: Chcę zaktualizować aplikacje do nowszej wersji
*(Np. wyszła nowa wersja Audiobookshelf lub Uptime Kuma).*

**Jak to zrobić:**
1. Otwórz terminal w folderze `/home/dominik/Audiobookshelf`.
2. Wpisz polecenie:
   ```bash
   ./absctl deploy
   ```
**Co się stanie pod spodem?** System sprawdzi składnię, zrobi kopię zapasową starych plików (Snapshot), pobierze nowe obrazy z internetu (`docker compose pull`), zrestartuje kontenery i poczeka 120 sekund. Jeśli nowa wersja ma błędy i nie włączy się poprawnie, system sam cofnie ją do starej wersji.

### Sytuacja 2: Chcę zmienić konfigurację (np. dodać nowy kontener lub port)
*(Np. chcesz dodać nowy serwis lub zmienić zmienną środowiskową).*

**Jak to zrobić:**
1. Otwórz główny plik `docker-compose.yml` lub `.env` i wprowadź pożądane zmiany w edytorze tekstu.
2. Wpisz polecenie:
   ```bash
   ./absctl deploy
   ```

### Sytuacja 3: Chcę ŚWIADOMIE usunąć jakąś usługę
*(Np. zdecydowałeś, że nie chcesz już korzystać z mikroserwisu `audioteka-abs`).*

**Co się stanie jeśli zrobisz to normalnie:** 
Skasujesz linijki z `docker-compose.yml`, wpiszesz `./absctl deploy` i... **system Cię zablokuje**. Zgłosi błąd Guard (Detekcja Driftu) z komunikatem: *"Zmiana destrukcyjna! Usunięto usługę"*.
**Jak to zrobić poprawnie:**
Musisz autoryzować tę operację, przekazując flagę pominięcia blokady:
```bash
ALLOW_REMOVAL=true ./absctl deploy
```

### Sytuacja 4: Awaria Krytyczna! (Czerwony Alert w Uptime Kuma)
*(Wdrażałeś zmiany, system z jakiegoś powodu utknął, nic nie działa, interfejs WWW zgłasza 502).*

**Jak to naprawić (Szybki Rollback):**
Wpisz polecenie:
```bash
./absctl rollback
```
**Co się stanie?** System "zabije" działające kontenery, wyczyści środowisko, zajrzy do pliku `state/last_snapshot`, odszuka ostatnią w 100% sprawną migawkę, nadpisze popsutą konfigurację i bazę danych plikami ze snapshota i uruchomi system w znanej, dobrej konfiguracji.

### Sytuacja 5: Przywracanie serwera po awarii sprzętu (Disaster Recovery)
*(Padł dysk SSD, zainstalowałeś Windowsa i WSL2 na nowo od zera).*

**Jak to naprawić:**
Raz w tygodniu (niedziela o 11 rano) system pakuje się do folderu `backup/daily/`.
1. Skopiuj najnowszy folder z backupem na nowy serwer.
2. W nowym serwerze utwórz ręcznie brakujące wolumeny za pomocą np. skryptu `init.sh`.
3. Rozpakuj pliki `.tar.gz` z backupu bezpośrednio do odpowiednich wolumenów.
4. Skopiuj plik `compose.yml` z folderu z backupem jako główny `docker-compose.yml`.
5. Uruchom `./absctl deploy`.

---

## 👥 Zarządzanie Użytkownikami i SSO

Audiobookshelf jest spięty z Google OAuth2. Procedura dodawania nowego znajomego do systemu wygląda następująco:

1. **Autoryzacja w Google:**
   Zaloguj się do Google Cloud Console (`console.cloud.google.com`) -> Przejdź do Ekranu Zgody OAuth (OAuth Consent Screen) -> w sekcji "Test users" kliknij Dodaj i wpisz adres Gmail znajomego.
2. **Stworzenie profilu w ABS:**
   Zaloguj się do panelu administratora w Audiobookshelf -> zakładka Użytkownicy -> Dodaj.
   Przypisz uprawnienia oraz wpisz **ten sam** adres Gmail w profilu użytkownika.
3. Znajomy może teraz wejść na `https://audiobooksdominika.online` i kliknąć "Zaloguj przez Google".

**⚠️ UWAGA RATUNKOWA:** Zawsze weryfikuj, czy znasz hasło (i login lokalny) do swojego głównego konta awaryjnego (Konto Root, któremu nie przypisano logowania Google). W razie awarii usług Google to jedyny sposób na dostanie się do systemu!

---

## 🗓️ Okna Serwisowe i Konserwacja (Maintenance)

System został zoptymalizowany tak, aby zapobiegać fałszywym alarmom (Alert Fatigue) podczas rutynowych zadań. 

**Tygodniowy Backup (Niedziela 11:00):**
Operacja backupu (`backup.sh`) celowo zatrzymuje główny kontener `audiobookshelf`, aby zapewnić spójność bazy danych. 
Aby zapobiec wysyłaniu fałszywych powiadomień o awarii, w panelu Uptime Kuma skonfigurowano **Okno Konserwacyjne (Maintenance Window)** na niedzielę w godzinach 11:00 - 11:05. W tym czasie powiadomienia są wstrzymane, a statystyki SLA (100% Uptime) pozostają nienaruszone.

**⚠️ ZŁOTA ZASADA ZMIANY HARMONOGRAMU:** 
Jeśli kiedykolwiek zdecydujesz się zmienić godzinę lub dzień wykonywania kopii zapasowej w harmonogramie Linuxa (`crontab -e`), **MUSISZ** również zaktualizować czas trwania "Konserwacji" w ustawieniach Uptime Kuma oraz zaktualizować komunikaty informacyjne dla użytkowników na stronie statusu i w panelu logowania ABS.

---

## 🔍 Gdzie szukać przyczyn błędów?

Jeśli orkiestrator zgłasza problemy, oto miejsca, w których znajdziesz odpowiedzi:

*   **Logi wdrażania:** `cat logs/deploy.log` (tu znajdziesz dokładny moment, w którym `absctl` się wywrócił).
*   **Logi cotygodniowego backupu:** `cat logs/backup.log` (jeśli rano Uptime Kuma świeci na czerwono, sprawdź ten plik).
*   **Aktualny stan aplikacji:** Użyj publicznej strony statusu wygenerowanej przez Uptime Kuma (`status.audiobooksdominika.online`).
*   **Logi Dockera:** Jeśli healthcheck nie przechodzi, wpisz:
    `docker logs audiobookshelf --tail 50` 
    aby zobaczyć, co serwer audiobooków wyrzuca do konsoli.