# ADR-021 — Strategia Backupów i Disaster Recovery (DR)

> **Status:** `accepted`  
> **Data:** 2026-07-20  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Zgodnie z wymogami `ADR-020`, przed wpuszczeniem rzeczywistych turystów na serwer produkcyjny (PROD) musimy zdefiniować strategię tworzenia kopii zapasowych. Aplikacja gromadzi dane użytkowników (np. profile, logi wejść, osobiste kanbany), których utrata trwale zniszczyłaby zaufanie do systemu i naraziła organizację na ryzyko roszczeń i naruszeń RODO. 

Dzięki separacji architektonicznej dane referencyjne (geografia, odznaki) są wersjonowane jako niemutowalne artefakty (`snapshot.json.gz` w repozytorium) i odtwarzane deterministycznie. Oznacza to, że **klasyczny backup infrastruktury może skupić się wyłącznie na stanie bazy użytkowników i plikach powiązanych.**

**Pytanie decyzyjne:**  
Jak zaprojektować mechanizm wykonywania, weryfikacji i przetrzymywania kopii zapasowych bazy danych PROD oraz jaki powinien być plan odzyskiwania systemu po katastrofie (Disaster Recovery Plan), aby zminimalizować ryzyko utraty danych RPO (Recovery Point Objective) i czas niedostępności RTO (Recovery Time Objective)?

---

## Opcje rozważane

### Opcja A: Automatyczne backupy maszyn wirtualnych (VM Snapshots) przez dostawcę hostingu
**Opis:** Poleganie na domyślnych usługach snapshotowania całego serwera dostarczanych przez AWS/Hetzner/DigitalOcean.
**Plusy:** Zerowy nakład na konfigurację po stronie aplikacji. Szybkie odtworzenie całego serwera 1:1.
**Minusy:** Bardzo trudne odtworzenie pojedynczych tabel lub rekordów. Backupy są zależne od jednego dostawcy (Vendor Lock-in). W przypadku przejęcia konta hostingowego, znikają zarówno serwery, jak i ich kopie zapasowe (Single Point of Failure).

### Opcja B: Logiczne zrzuty bazy danych (`pg_dump`) wypychane do zewnętrznej pamięci obiektowej S3
**Opis:** Asynchroniczne, cykliczne zadanie, które wykonuje wyizolowany zrzut logiczny (`pg_dump`) bazy danych, kompresuje go, szyfruje i wysyła na zewnętrzny, całkowicie niezależny węzeł S3 (np. AWS S3, Backblaze B2, Cloudflare R2) z polityką niezmienności (Object Lock).

---

## Decyzja

Wybieramy **Opcję B: Logiczne zrzuty do zewnętrznej chmury S3 z polityką retencji**.

1. **Izolacja Magazynu Kopii (Off-site Immutable Backup):**
   Kopie zapasowe muszą fizycznie opuścić infrastrukturę, w której działa serwer PROD. Będą wysyłane do zewnętrznego dostawcy S3.
   Backupy zapisywane są pod niepowtarzalnymi nazwami (zawierającymi timestamp lub UUID), a docelowy *bucket* S3 posiada włączoną politykę niezmienności (Object Lock / WORM - Write-Once-Read-Many), gwarantującą, że zapisany plik nie może zostać nadpisany ani skasowany przed upływem okresu retencji. Dostęp do S3 wymaga restrykcyjnego podziału ról (RBAC):
   - **Konto Aplikacyjne (backup-writer-prod):** Posiada uprawnienia typu **Write-Only (PUT Object)**. Używane przez serwer produkcyjny wyłącznie do zrzucania kopii. 
   - **Konto Operatora DR (backup-recovery):** Posiada uprawnienia odczytu (**GET Object, Restore**). Dostęp logowania chroniony jest przez MFA i wykorzystywany wyłącznie poza serwerem produkcyjnym w procedurze odtwarzania środowiska.

2. **Zasada 3-2-1:**
   Strategia backupów realizuje fundamentalną zasadę "3-2-1": utrzymywane są co najmniej trzy kopie danych, zapisane na dwóch różnych nośnikach, z czego jedna kopia znajduje się poza główną lokalizacją infrastruktury. W praktyce dla środowiska PROD oznacza to lokalną kopię operacyjną oraz kopię przechowywaną w zewnętrznym magazynie S3.

3. **Zakres Backupów i Szyfrowanie (RODO):**
   - **Baza PostgreSQL:** Wykonywany jest zrzut logiczny z użyciem narzędzia `pg_dump` w formacie skompresowanym (`-Fc`). Zakresem logicznym backupu są dane użytkowników, jednakże fizyczny zrzut obejmuje całą bazę (w tym dane referencyjne z PostGIS), ponieważ upraszcza to proces odtworzenia i nie zwiększa istotnie kosztu operacji dla MVP.
   - **Bezpieczeństwo Danych:** Ponieważ kopie zapasowe zawierają dane osobowe (RODO), muszą być **bezwarunkowo szyfrowane zarówno podczas transmisji (TLS), jak i w spoczynku (S3 Encryption / SSE-S3)**.
   - **Pliki Użytkowników (Pamiątki):** Pliki statyczne użytkowników są domyślnie przesyłane bezpośrednio do chmury (zgodnie z planowanym `US-D04`), co deleguje obowiązek ich replikacji na dostawcę S3 i zdejmuje ten ciężar z backupu bazy.
   - **Redis Cache:** Wykluczony z backupu operacyjnego. Zgodnie z żelazną regułą architektoniczną: **Wszystkie dane utrzymywane w Redis muszą być w pełni rekonstruowalne na podstawie zawartości bazy PostgreSQL.** Pamięć Redis jest traktowana jako wyłącznie ulotna (Ephemeral).

4. **Cele Odzyskiwania i Retencja (SLA):**
   - **RPO (Recovery Point Objective):** Przyjęto maksymalny czas utraty danych wynoszący **24 godziny**. Jest to świadomy kompromis pomiędzy kosztem infrastruktury a krytycznością danych. System PTTK Badges nie jest obecnie traktowany jako platforma wysokiego ryzyka finansowego. Zrzuty bazy danych wykonywane są automatycznie raz na dobę w nocy. W przypadku wzrostu wymagań biznesowych (np. wdrożenia płatności wewnątrz aplikacji) wartość RPO podlega ponownej analizie.
   - **RTO (Recovery Time Objective):** Deklarowany docelowy czas przywrócenia systemu do pełnej sprawności po awarii wynosi **8 godzin**.
   - **Retencja:**
     - 7 codziennych zrzutów z ostatniego tygodnia.
     - 4 cotygodniowe zrzuty z ostatniego miesiąca.
     - 1 zrzut miesięczny utrzymywany przez rok (na wypadek roszczeń prawnych).

5. **Wyzwalacz Przedwdrożeniowy (Ad-hoc Database Release Backup):**
   Niezależnie od harmonogramu nocnego, zrzut zapasowy `pg_dump` musi zostać uruchomiony **bezwarunkowo przed każdym Wdrożeniem Schematu Bazy Danych (Database Release)**, zgodnie z kontraktem w ADR-020. Backup musi zostać wykonany w sposób gwarantujący transakcyjnie spójny obraz bazy danych. Wdrożenie (Database Release) jest trwale blokowane, jeżeli zrzut zapasowy nie zakończy się sukcesem.

6. **Weryfikacja Odtwarzalności (Disaster Recovery Drill):**
   Raz na kwartał wymagane jest wykonanie próbnego przywracania zniszczonego systemu na odizolowanym serwerze. Wynik testu DR musi być udokumentowany i zawierać: rzeczywisty osiągnięty wskaźnik RTO, identyfikator użytej wersji backupu, listę napotkanych problemów oraz propozycje działań naprawczych.
   Test DR uznaje się za zakończony sukcesem wyłącznie, jeżeli spełnione są wszystkie cztery kryteria:
   1. Baza danych została poprawnie odtworzona z pliku S3.
   2. Odtworzona aplikacja przechodzi standardowy Healthcheck.
   3. Możliwe jest zalogowanie i uwierzytelnienie użytkownika testowego z bazy.
   4. Wykonanie reprezentatywnego zapytania biznesowego zwraca oczekiwane dane.

---

## Konsekwencje

### Pozytywne
- System jest chroniony przed atakami typu Ransomware na infrastrukturę hostingową.
- Rozdzielenie ról S3 całkowicie zamyka wektor ataku z poziomu uszkodzonej lub skompromitowanej produkcji.
- Zdefiniowanie twardych ram czasowych RPO/RTO standaryzuje procedury dla zespołu utrzymaniowego.

### Negatywne / Działania wymagane
- Wymaga przygotowania zwalidowanych skryptów backupowych.
- Stały, lecz niski koszt utrzymania zewnętrznej pamięci obiektowej S3 (wraz z włączonym wersjonowaniem i Object Lock).
- Narzuca obowiązek kwartalnego testowania i dokumentowania procedur DR, co wprost obciąża harmonogram operacyjny zespołu.

---

## Warunek rewizji

Strategia zakłada na tym etapie skalę bazy i ruch sieciowy, dla których jednorazowy zrzut logiczny bazy danych (`pg_dump`) jest rozwiązaniem wystarczającym. Rewizja dokumentu jest bezwzględnie wymagana, jeżeli:
- Parametr RPO (24h) przestanie być akceptowalny biznesowo.
- Zadeklarowany czas odtworzenia (RTO) zostanie przekroczony podczas testu DR Drill.
- Pojawi się wymóg biznesowy odzyskiwania bazy do konkretnego momentu w czasie (PITR - Point-in-Time Recovery).
- Wolumen fizyczny danych i geometrii PostGIS uniemożliwi i/lub zbytnio spowolni wykonywanie codziennych zrzutów `pg_dump`, wymuszając przejście na rozwiązania typu `pgBackRest` i `WAL Archiving` lub migrację na środowisko chmurowe Managed Database.
