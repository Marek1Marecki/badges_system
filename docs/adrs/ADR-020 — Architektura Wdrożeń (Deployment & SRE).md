# ADR-020 — Architektura Wdrożeń (Deployment & DataOps)

> **Status:** `accepted`  
> **Data:** 2026-07-09  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Aplikacja przeszła z fazy deweloperskiej MVP do fazy utrzymaniowej. System operuje na dwóch krytycznych, lecz niezależnych zbiorach: twardych Danych Referencyjnych (geometria PostGIS, definicje odznak) oraz miękkich Danych Użytkowników (postępy, logi).
Pojawiło się wyzwanie związane ze spójnością i odtwarzalnością środowisk testowych oraz z ryzykiem nadpisania postępów turystów na produkcji w przypadku błędnego zarządzania cyklem życia bazy danych.

**Pytanie decyzyjne:**
Jak ustrukturyzować środowiska (DEV, TEST, PRE-PROD, PROD), proces uwalniania kodu (Release) oraz dystrybucję zmiennych środowiskowych, by wyeliminować ręczne błędy operatora i oddzielić kod aplikacyjny od danych?

---

## Opcje rozważane

### Opcja A: Wiele plików Dockerfile i automatyczny Seed przy każdym restarcie
**Opis:** Tworzymy `Dockerfile.dev`, `Dockerfile.prod`. Komenda `restore_reference_data` zaszyta jest w głównym pliku `entrypoint.sh` wywoływanym przy każdym podniesieniu kontenera.
**Plusy:** Łatwość zrozumienia dla początkujących (izolacja plików budujących).
**Minusy:** Brak gwarancji, że kod przetestowany to ten sam kod co na produkcji. Automatyczny Seed przy restarcie kontenera (np. podczas skalowania poziomego) to wyrok śmierci na wydajność bazy i ogromne ryzyko *Race Condition*.

### Opcja B: Oddzielne zbiory `.env` i wymuszenie ręcznego eksportu (Wybrane)
**Opis:** Używamy jednego wieloetapowego (Multi-Stage) pliku `Dockerfile`. Wyrzucamy wstrzykiwanie zmiennych z plików konfiguracyjnych na rzecz sterowania tym przez Pydantic. Dane referencyjne są wersjonowane jako niezależny artefakt. Skrypty wdrożeniowe to osobny, kontrolowany proces CI/CD.

---

## Decyzja

Wdrażamy rygorystyczny proces **DataOps & Infrastructure as Code**.

**Zasada Deterministycznego Wdrożenia (Guiding Principle):**
Każde środowisko musi być możliwe do odtworzenia wyłącznie z trzech artefaktów: wersji kodu aplikacji, wersji snapshotu danych referencyjnych oraz konfiguracji środowiska. Ręczne modyfikacje środowisk wdrożeniowych są niedopuszczalne. Jedynym sposobem dostarczenia artefaktu do środowisk TEST, PRE-PROD oraz PROD jest zatwierdzony potok CI/CD.

1. **Jedyne Źródła Prawdy i Cykl Życia Danych:**
   Repozytorium kodu oraz repozytorium artefaktów pełnią funkcję źródeł wersji. Kod aplikacji jest wersjonowany w systemie kontroli wersji, natomiast snapshoty danych referencyjnych są przechowywane jako niemutowalne artefakty powiązane z identyfikatorem wersji w manifeście — niezależnie od konkretnej technologii przechowywania (repozytorium kodu, rejestr artefaktów lub magazyn obiektowy).

   **Zasada Niemutowalności Snapshotu:** Snapshot referencyjny po zatwierdzeniu otrzymuje status niemutowalnego artefaktu. Każda zmiana danych referencyjnych wymaga utworzenia nowej wersji snapshotu wraz z nowym identyfikatorem. Niedopuszczalne jest nadpisanie zawartości powiązanej z istniejącym już identyfikatorem wersji. Aby ta gwarancja była techniczne weryfikowalna niezależnie od miejsca przechowywania, każdy snapshot posiada w manifeście sumę kontrolną (`sha256`), liczoną **dla binarnej zawartości pliku snapshotu (np. `snapshot.tar.gz`), nigdy dla samego pliku manifestu** — w przeciwnym razie podmiana zawartości przy zachowaniu tego samego manifestu pozostałaby niewykrywalna. Przykładowa struktura manifestu:

```json
   {
     "snapshot_id": "2026.07.09",
     "sha256": "abc123...",
     "created_at": "2026-07-09",
     "created_by": "reference-data-pipeline",
     "compatible_schema": ">=14,<16"
   }
```

   Pole `compatible_schema` deklaruje zakres wersji schematu bazy danych, z którymi dany snapshot jest zgodny semantycznie — nie jest to wyłącznie techniczne ograniczenie obecności struktur danych, lecz oświadczenie zespołu wdrażającego migrację o zachowaniu znaczenia pól, na których snapshot operuje. Deklaracja ta musi być aktualizowana ręcznie przy każdej migracji zmieniającej semantykę (nie tylko obecność) struktury wykorzystywanej przez dane referencyjne.

   Każdy proces odtwarzający snapshot (Reference Data Release, rollback, odtworzenie środowiska DEV/TEST/PRE-PROD) weryfikuje zgodność sumy kontrolnej pobranego artefaktu z wartością zadeklarowaną w manifeście przed jego zastosowaniem.

   Narzuca się żelazną macierz propagacji:

   | Środowisko | Cel | Dane Referencyjne (Szczyty/Odznaki) | Dane Użytkowników (Logi/Konta) |
   |:---|:---|:---|:---|
   | **DEV** | Rozwój | Odtwarzane z zatwierdzonego snapshotu ➔ lokalna edycja ➔ eksport nowego snapshotu | Fikcyjne |
   | **TEST** | Testy automatyczne | Odtwarzane z zatwierdzonego snapshotu | Generowane syntetycznie |
   | **PRE-PROD** | Walidacja Release Candidate | Odtwarzane z tego samego snapshotu co planowane wdrożenie PROD | Tylko fikcyjne (Testy Manualne i Zautomatyzowane) |
   | **PROD** | Użytkownicy | Aktualizowane wyłącznie poprzez zatwierdzony proces Reference Data Release | **Źródło prawdy. Nigdy nie są kopiowane do środowisk niższych.** |

   *Uwaga dotycząca niezmienności:* PRE-PROD jest środowiskiem wyłącznie do walidacji Release Candidate. Zabrania się wykonywania na nim ręcznych zmian danych referencyjnych oraz konfiguracji. Środowisko PROD jest ostateczne i zakazuje się eksportowania z niego snapshotów referencyjnych.

2. **Izolacja Środowisk:**
   Każde środowisko posiada własną bazę danych, własny cache (Redis), własne wolumeny oraz własną pulę sekretów, i nigdy nie współdzieli stanu, pamięci ani dysku z żadnym innym środowiskiem. Dla środowiska TEST powyższe zasoby są **efemeryczne** — tworzone od zera na potrzeby jednego przebiegu pipeline'u CI i niszczone natychmiast po jego zakończeniu, niezależnie od wyniku. TEST nigdy nie utrzymuje trwałego stanu między uruchomieniami.

   **Zasada Izolacji Sieciowej:** Środowiska nie mogą komunikować się ze sobą bezpośrednio na poziomie sieciowym. Żaden proces uruchomiony w DEV, TEST lub PRE-PROD nie może nawiązać połączenia z bazą danych, cache'em ani żadnym innym zasobem stanowym środowiska PROD, i odwrotnie. Jedynym dopuszczalnym wyjątkiem są kontrolowane kanały administracyjne potoku CI/CD oraz systemu monitoringu, działające z minimalnym wymaganym zakresem uprawnień i podlegające osobnemu audytowi dostępu. Reguła ta chroni przed klasą błędów wynikającą z pomyłki konfiguracyjnej (np. zmiennej środowiskowej wskazującej na niewłaściwy host), która mogłaby ominąć separację zasobów opisaną powyżej mimo formalnego spełnienia zasady "własnej bazy i własnego cache".

3. **Cztery Niezależne Cykle Wdrożeniowe (Release Separation):**
   - **Database Release:** Wykonuje migracje schematu bazy danych. Musi zostać wykonany i potwierdzony przed uruchomieniem nowych instancji Application Release wykorzystujących zmieniony schemat — nigdy w odwrotnej kolejności ani równolegle. Dotyczy to w szczególności wdrożeń typu rolling deployment, gdzie stare i nowe instancje aplikacji mogą przez pewien czas działać jednocześnie na tym samym schemacie.
   - **Application Release:** Wdrożenie nowej wersji aplikacji. Wykonuje: `collectstatic` ➔ `showmigrations --plan` ➔ walidację, że wszystkie migracje wymagane przez wdrażany obraz zostały już zastosowane w poprzedzającym go Database Release — brak zgodności blokuje kontynuację wdrożenia, nie jest to wyłącznie krok diagnostyczny ➔ `check --deploy`.
   - **Reference Data Release:** Aktualizacja map/odznak. Wykonuje: walidacja manifestu (w tym sumy kontrolnej oraz zgodności pola `compatible_schema` z aktualnym stanem bazy) ➔ odtwarzanie danych referencyjnych ➔ przeliczenie powiązań przestrzennych. Odtwarzanie danych referencyjnych jest operacją idempotentną — własność ta jest chroniona testem regresyjnym weryfikującym brak zmian stanu bazy przy dwukrotnym uruchomieniu procesu na tym samym snapshocie; test ten jest obowiązkową częścią potoku CI dla tego cyklu.
   - **Infrastructure Release:** Aktualizacja komponentów infrastruktury (np. Docker, Redis, Reverse Proxy). Niezależna od cyklu deweloperskiego.

   **Zasada Kolejności Wdrożeń (Deployment Ordering Rule):**
   Procesy te są technicznie niezależne, jednak podlegają rygorowi kolejności: Database Release musi zostać wdrożony i potwierdzony przed uruchomieniem Application Release, jeśli nowy obraz wymaga migracji nieobecnych w aktualnym schemacie środowiska docelowego — zgodność tę wymusza krok walidacyjny w Application Release opisany powyżej. Analogicznie, Database Release musi zostać wdrożony i potwierdzony przed uruchomieniem Reference Data Release, jeśli snapshot deklaruje w polu `compatible_schema` wymóg wyższy niż obecnie zastosowana wersja schematu; krok walidacji manifestu odczytuje ten wymóg i odmawia kontynuacji, jeśli środowisko docelowe go nie spełnia.

   **Zasada Migracji Destrukcyjnych:** Migracje usuwające strukturę danych (`DROP COLUMN`, `DROP TABLE`, zmiana typu kolumny, usunięcie indeksu wykorzystywanego przez kod) nie mogą zostać wykonane w tym samym Database Release, w którym dana struktura przestaje być używana przez aplikację. Wymagana jest sekwencja co najmniej dwuetapowa: Release N wprowadza nową strukturę i migruje do niej odczyt/zapis aplikacji (Expand), Release N+1 (lub późniejszy) usuwa strukturę już nieużywaną (Contract). Zasada ta jest rozszerzeniem wzorca Expand and Contract i bezpośrednio chroni zdolność do rollbacku aplikacji oraz danych referencyjnych opisaną w punkcie 5.

   **Zasada Akceptacji Release'u:** Każdy z czterech cykli posiada osobną ścieżkę akceptacji oraz audytowalny, niepowtarzalny identyfikator wdrożenia rejestrowany w potoku CI/CD. Żaden Release nie może zostać wykonany ręcznie (np. bezpośrednim wywołaniem komendy administracyjnej na serwerze) poza zatwierdzonym pipeline'em — dotyczy to w szczególności Reference Data Release na środowisku PROD.

   *Zasada Version Matrix:* Każde wdrożenie identyfikowane jest przez zestaw: wersję obrazu aplikacji, wersję migracji schematu oraz wersję snapshotu referencyjnego. System wspiera jedynie kombinacje jawnie przetestowane w potoku CI/CD. Rejestr tych kombinacji dla środowiska PROD stanowi **artefakt audytowy** i musi umożliwiać jednoznaczne odtworzenie dokładnego stanu (obraz + schemat + snapshot), jaki obowiązywał na produkcji w dowolnym momencie w przeszłości — w szczególności w kontekście analizy incydentów. Dokładny format i miejsce przechowywania tego rejestru pozostają poza zakresem niniejszego ADR. Przykładowa forma:

   | Release ID | Obraz Aplikacji | Wersja Schematu | Snapshot Referencyjny |
   |:---|:---|:---|:---|
   | PROD-001 | `app:v1.3.0` | 12 | `2026.06` |
   | PROD-002 | `app:v1.4.0` | 13 | `2026.07` |
   | PROD-003 | `app:v1.5.0` | 14 | `2026.08` |

4. **Hermetyzacja konfiguracji środowisk:**
   Ryzyko przecieku środowisk wyeliminowano, wymuszając jawną definicję pliku docelowego poprzez zmienną systemową (np. `APP_ENV`). Plik współdzielony stosuje się wyłącznie do konfiguracji nie-poufnych oraz flag funkcji (Feature Flags).

5. **Build Once, Deploy Many (Zasada Niemutowalności i Rollbacku):**
   Środowiska TEST, PRE-PROD i PROD są **niemutowalne (Immutable Infrastructure)**. Wszelkie zmiany konfiguracji lub kodu odbywają się wyłącznie poprzez budowę nowego obrazu i ponowne wdrożenie.
   Wszystkie środowiska wdrożeniowe korzystają z tego samego obrazu produkcyjnego, zbudowanego jednokrotnie w potoku CI.

   Każde wdrożenie wspiera **Rollback** do poprzedniej wersji obrazu bez ponownej kompilacji. Z tego powodu bezwzględnie egzekwuje się wzorzec migracji **Expand and Contract**: migracje bazy danych muszą być wstecznie kompatybilne przez co najmniej jedno wydanie, zgodnie z Zasadą Migracji Destrukcyjnych opisaną w punkcie 3.
   Rollback aplikacji obejmuje wyłącznie obraz kontenera i konfigurację (nie obejmuje automatycznego cofania migracji schematu bazy danych).
   Reference Data Release wspiera rollback poprzez ponowne odtworzenie poprzedniej zatwierdzonej wersji snapshotu. **Rollback snapshotu referencyjnego jest możliwy wyłącznie do wersji kompatybilnej z aktualnym schematem bazy danych** — zgodność weryfikowana jest poprzez porównanie pola `compatible_schema` docelowej wersji snapshotu z aktualną wersją schematu; jeśli docelowa wersja snapshotu odwołuje się do struktur danych nieobecnych (lub już usuniętych przez migrację typu *contract*) w aktualnym schemacie, rollback do tej wersji jest zablokowany do czasu przywrócenia zgodności schematu.

---

## Konsekwencje

### Pozytywne
- **Ochrona Produkcji:** Brak automatycznego importu przy starcie kontenera eliminuje ryzyko zniszczenia danych na środowisku PROD w trakcie normalnych wdrożeń kodu.
- Architektura zapobiega tzw. Dryfowi Konfiguracji (Configuration Drift) – wszystkie środowiska wdrożeniowe używają tego samego bazowego obrazu systemowego.
- Pełna gotowość do wykonywania automatycznych testów end-to-end na odizolowanym, stabilnym środowisku `PRE-PROD` posiadającym spójne dane wejściowe.
- Niemutowalność snapshotów (wzmocniona sumą kontrolną liczoną z zawartości artefaktu), izolacja sieciowa, jawna ścieżka akceptacji Release'u oraz rozdzielenie migracji ekspansywnych od destrukcyjnych eliminują cztery osobne klasy błędów integralności danych, konfiguracji i procedury, które nie były pokryte przez samą separację zasobów.

### Negatywne / Działania wymagane
- Skomplikowany proces wdrażania nowości w regulaminach PTTK (wymaga zatwierdzenia snapshotu referencyjnego za pomocą odpowiednich skryptów osobno od wdrożenia samej aplikacji).
- W przypadku rzadkich migracji schematu niezgodnych wstecz wymagane jest zaplanowanie okna serwisowego.
- Wymaga natychmiastowego zdefiniowania strategii tworzenia kopii zapasowych (Backup), zanim na PROD wejdą prawdziwi turyści.
- Wymaga utrzymania testu regresyjnego potwierdzającego idempotentność procesu odtwarzania danych referencyjnych jako stałego elementu potoku CI.
- Wymaga konfiguracji sieciowej (np. reguł firewalla, osobnych sieci Docker/VPC per środowisko) egzekwującej Zasadę Izolacji Sieciowej — nie tylko deklaratywnej separacji zasobów.
- Wymaga wdrożenia mechanizmu obliczania i weryfikacji sumy kontrolnej snapshotu w potoku CI/CD oraz utrzymania rejestru Version Matrix jako artefaktu audytowego dla środowiska PROD.
- Wymaga dyscypliny zespołu przy planowaniu migracji destrukcyjnych — każda migracja typu Contract musi być poprzedzona co najmniej jednym wydaniem, w którym dana struktura jest już nieużywana, ale jeszcze obecna.

---

## Warunek rewizji

Dokument wymaga uzupełnienia o **ADR-021 (Strategia Backupów i Disaster Recovery)** na 14 dni przed oficjalnym otwarciem ruchu dla turystów na serwerze produkcyjnym. Backup operacyjny obejmuje wyłącznie dane użytkowników. Dane referencyjne nie wymagają backupu operacyjnego bazy danych, ponieważ ich źródłem prawdy są niemutowalne snapshoty — wymagają natomiast ochrony integralności i dostępności repozytorium artefaktów oraz zachowania pełnej historii wersji, co jest przedmiotem odrębnego ustalenia poza niniejszym ADR. Przed wykonaniem migracji na PROD zawsze wykonywany jest backup bazy danych użytkowników.

Rewizja niniejszego dokumentu jest również wymagana w przypadku: wprowadzenia piątego środowiska wdrożeniowego, zmiany dostawcy sekretów/konfiguracji, odkrycia przypadku, w którym proces odtwarzania danych referencyjnych przestaje być idempotentny, lub zmiany technologii przechowywania artefaktów referencyjnych.

## Relacje (Related)
- **ADR-021 — Strategia Backupów i Disaster Recovery:** Dokument wymagany do uzupełnienia przed otwarciem ruchu na PROD; definiuje RPO/RTO dla danych użytkowników, które są kluczowe dla bezpieczeństwa wdrożeń opisanych w niniejszym ADR.
- **ADR-024 — Strategia Migracji (Expand and Contract):** Zasada Migracji Destrukcyjnych opisana w punkcie 3 jest rozszerzeniem wzorca Expand and Contract zdefiniowanego w ADR-024.
