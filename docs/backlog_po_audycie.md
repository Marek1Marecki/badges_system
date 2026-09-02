# Backlog po Audycie (Step 3.7 Flash)

> **Dokument roboczy** gromadzący zadania refaktoryzacyjne, wykryte luki w zabezpieczeniach oraz optymalizacje architektoniczne wygenerowane w serii audytów zewnętrznych. Każde zadanie po wdrożeniu powinno zostać odhaczone.

---

## Lista zadań do realizacji:

---

### [AUDYT-003] Ujednolicenie polityki "Asymetrycznego Zaufania" (Wiek Turysty)
**Obszar:** `Domena / Reguły`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Istnieje niespójność pomiędzy regułami wieku. W przypadku braku daty urodzenia u turysty, `MinAgeRule` przepuszcza log bez błędu, podczas gdy `MaxAgeRule` blokuje go z komunikatem błędu.

**Action Items (Do wdrożenia):**
- [ ] Utrzymać celowe "Asymetryczne Zaufanie": Jawnie zdefiniować i opisać w kodzie Domeny, że `MinAgeRule` ufa domyślnie w pełnoletność turysty (zwraca `[]`), a `MaxAgeRule` restrykcyjnie weryfikuje wiek do przywilejów (zwraca błąd).

**Komentarz Architekta:**
Audytor wyłapał tu niespójność, która w rzeczywistości jest naszym świadomym wymogiem biznesowym (UX). Należy to jasno udokumentować w docstringach klasy w `domain/rules/badge_rules.py`, by nie myliło to przyszłych deweloperów, ale zachowania reguł nie zmieniamy.

---

### [AUDYT-008] Brakujące ADR-y i ujednolicenie wersji (Housekeeping)

### [AUDYT-013] Przepływ i hermetyzacja Kontenera DI
**Obszar:** `Bootstrap / DI Container`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Plik `bootstrap/container.py` jako "Zamrożona Dataclass" (AppContainer) jest genialny, ale stanowi centralny punkt awarii (P0 według znaczenia systemowego). Audytor zwrócił uwagę na kwestię generowania unikalnych ID dla żądań i powiązań z middleware. Pytanie o brak `IdGeneratorPort` zasygnalizowane w raporcie.

**Action Items (Do wdrożenia):**
- [ ] Potwierdzić, czy potrzebujemy formalnego portu do generowania UUID, czy akceptujemy użycie standardowej biblioteki Pythona `uuid.uuid4()` bezpośrednio w kodzie (Zgodnie ze sztuką stdlib w domenach może działać autonomicznie). 

**Komentarz Architekta:**
Pozostajemy przy wbudowanym pakiecie `uuid` z biblioteki standardowej (Python `stdlib`). Tworzenie osobnego portu i adaptera (np. `UuidGenerator`) to Over-engineering dla MVP. Adnotacja do zapisania jako świadoma decyzja architektoniczna.

---

### [AUDYT-015] Brak `IdGeneratorPort` zadeklarowanego w kontraktach
**Obszar:** `Aplikacja / Porty`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Dokument `17-determinism-contract.md` wymaga wstrzykiwania generatora ID (podobnie jak czasu przez `ClockPort`), jednak w kodzie nie istnieje taki port, a identyfikatory (`uuid`) są generowane prawdopodobnie bezpośrednio w warstwach, co łamie zasadę determinizmu.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Utworzyć `IdGeneratorPort` w `application/ports/`.
- [ ] Napisać adapter infrastrukturalny (np. `SystemIdGenerator`) oparty na `uuid.uuid4()`.
- [ ] Wstrzyknąć port do Kontenera DI i zaktualizować Use Case'y/Adaptery, które wymagają losowych ID (np. Middleware dla `request_id`).

**Komentarz Architekta:**
Ryzyko to nie jest blokujące, ale obniża "testowalność" systemu (Testability). Deterministyczne ID są niezbędne, gdy testujemy ścisłe wartości zwracane przez API.

---

### [AUDYT-016] Importy modeli między niezależnymi aplikacjami Django
**Obszar:** `Aplikacje / Izolacja Bounded Contexts`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Plik `apps/tourists/views.py` (obsługujący HTML) bezpośrednio importuje modele z `apps/badges/models.py` (np. `BadgeModel`, `TouristObject`). To łamie SRP i powoduje silne sprzęgnięcie (Coupling) pomiędzy dwoma Bounded Contextami (Słowniki PTTK a Dane Użytkowników).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Zastąpić bezpośrednie odpytywania ORM-a z `apps/badges` w widokach turystów dedykowanymi usługami typu `QueryService`, dostępnymi przez Kontener DI.

**Komentarz Architekta:**
Choć w monolitycznym Django jest to standardowa praktyka, w architekturze heksagonalnej zanieczyszcza to widoki HTML logiką bazodanową. Będziemy musieli to rozplątać podczas etapu "Odchudzania Widoków".

---

### [AUDYT-019] Brak mechanizmu automatycznego discovery dla Reguł (Shotgun Surgery)
**Obszar:** `Domena / Wzorzec Strategii`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Architektura weryfikacji odznak (Wzorzec Strategii) cierpi na zjawisko *Shotgun Surgery*. Dodanie nowej reguły do systemu wymaga obecnie otwarcia i modyfikacji aż 4 plików: (1) Utworzenia samej klasy w domenie, (2) Dodania jej do słownika `RULE_BUILDERS`, (3) Dopisywania logiki budującej w Adapterze, (4) Dopisywania struktury w JSON Schema dla panelu Admina.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Zaprojektować i wdrożyć automatyczny mechanizm (np. Metaklasy w Pythonie lub dekorator rejestrujący `@register_rule`), który przy starcie aplikacji samodzielnie zbuduje mapowanie reguł dla adaptera bazy danych.

**Komentarz Architekta:**
To nie jest błąd krytyczny dla obecnej skali projektu (mamy kilkanaście reguł i panujemy nad nimi). Jednak w systemie na poziomie Enterprise automatyczne rejestrowanie (Discovery) oszczędza setki godzin pracy i zapobiega literówkom podczas dodawania nowości.

---

### [AUDYT-026] Brak flag bezpieczeństwa dla ciasteczek (`SECURE_COOKIE`)
**Obszar:** `Infrastruktura / Konfiguracja Django`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Projekt opiera się na sesjach, ale plik `settings.py` nie wymusza odpowiednich rygorów dla środowisk produkcyjnych. Przechwycenie ciasteczka (`sessionid`) przez atak MITM pozwala na całkowite przejęcie konta turysty.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] W pliku `settings.py` dodać wymuszenie: `if not DEBUG: SESSION_COOKIE_SECURE = True` oraz `CSRF_COOKIE_SECURE = True`.
- [ ] Aktywować `SECURE_SSL_REDIRECT = True` dla środowiska produkcyjnego.

**Komentarz Architekta:**
Brak zabezpieczenia na styku HTTP(S). Wdrożymy to wraz z serwerem Caddy w środowisku `PROD`, ale aplikacja musi egzekwować te dyrektywy wewnętrznie.

---

### [AUDYT-032] Nadmiernie obciążająca agregacja `get_oldest_ascent_date`
**Obszar:** `Infrastruktura / Zapytania`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Obliczanie pierwszej daty wejścia dla Praw Nabytych (Grandfather Clause) wykonuje skomplikowaną agregację, która na rosnących zbiorach zacznie kosztować kilkaset milisekund czasu CPU per zapytanie. Wykonuje tam w locie wyciąganie identyfikatorów (`values_list` na tabeli M2M), a następnie uderza w `AscentLog`.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Przepisać metodę w `DjangoTouristRepository` tak, aby łączyła zapytania w jeden *Subquery* (Podzapytanie SQL). Zamiast obciążać kod Pythona przenoszeniem identyfikatorów, zlecić odfiltrowanie i `Min("ascent_date")` czystemu silnikowi bazy danych.

**Komentarz Architekta:**
Wspaniała porada DBA. Podzapytania (Subqueries) to technika pozwalająca na gigantyczne oszczędności czasu zapytania z ominięciem zaciągania danych po kablu do serwera Django. Zostawiamy to jako zadanie dla inżyniera danych.

---

### [AUDYT-033] Ryzyko wycieków Cache Redis (Brak TTL dla Stanu Mapy)
**Obszar:** `Aplikacja / Celery`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Dane trzymane w Redis pod kluczem `map_state:{profile_id}` są wpisywane przez Task `recalculate_poi_scores_task` bez ustawionego czasu wygasania (TTL - Time To Live). W przypadku 100 tysięcy użytkowników, RAM maszyny z Redisem szybko się zapełni "sierotami" (stanami dla profili, które nie były aktywne od wielu miesięcy).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Dodać obligatoryjny, globalny parametr TTL (np. 48 lub 72 godziny) do zapisu w `DjangoCacheAdapter` wywoływanego z poziomu usługi punktującej.
- [ ] Upewnić się, że `MapObjectsView` prawidłowo ignoruje lub odtwarza stan w przypadku nieistnienia klucza.

**Komentarz Architekta:**
Zgodnie z Invariantem, że wszystko w Redis można odtworzyć z Postgresa, narzucenie TTL na cache jest wręcz obowiązkiem z zakresu FinOps (ograniczenie rozmiaru serwera Redis).

---

### [AUDYT-043] Refaktoryzacja "Głębokiej Hierarchii" Regionów (Deep Hierarchy)
**Obszar:** `Baza Danych / Architektura`  
**Priorytet:** `🟡 ŚREDNI` (Skalowanie Długoterminowe)

**Diagnoza Audytora:** 
Obecnie system posiada 7 osobnych modeli geograficznych (Country -> Voivodeship -> Province itd.) połączonych relacjami `ForeignKey`. Powoduje to konieczność wykonywania 5-7 `JOIN`-ów przy każdym zapytaniu odtwarzającym strukturę terytorialną w panelu lub widokach. Przy 100-krotnym wzroście bazy danych może to prowadzić do spowolnienia zapytań powyżej 1 sekundy.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Zaprojektować migrację bazy danych łączącą wszystkie poziomy w jedną tabelę ze strukturą Drzewa Zagnieżdżonego (Adjacency List) za pomocą pola `parent_id` oraz `level_enum`.
- [ ] Opcjonalnie wdrożyć rozszerzenie PostGIS `ltree` do superszybkiego odpytywania gałęzi drzewa bez konieczności robienia zapytań rekurencyjnych (CTE).

**Komentarz Architekta:**
Klasyczny błąd nadmiernej normalizacji w fazie MVP. Dopóki używamy tabeli `ObjectRegionCache` (CQRS) do filtrowania odczytów, system jest bezpieczny. Jednak edycja samej siatki terytorialnej w przyszłości będzie uciążliwa. Decyzja odłożona na fazę poprodukcyjną.

---

### [AUDYT-044] Strategia Partycjonowania Tabeli `AscentLog`
**Obszar:** `Baza Danych / PostgreSQL`  
**Priorytet:** `🟢 NISKI` (Planowanie Długoterminowe)

**Diagnoza Audytora:** 
Tabela `AscentLog` (Dziennik Wejść) jest centralnym punktem danych aplikacji. Przy docelowej skali milionów wierszy, brak podziału fizycznego na dysku spowoduje drastyczny spadek wydajności zapytań (częste Full Table Scans dla raportów) i utrudni archiwizację.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Stworzyć projekt partycjonowania (Table Partitioning) tabeli `AscentLog` – np. partycjonowanie typu `hash` po kolumnie `profile_id` lub `range` po kolumnie `ascent_date`.
- [ ] Zintegrować mechanizm archiwizacji bardzo starych wejść (> 5 lat).

**Komentarz Architekta:**
Temat do podjęcia wyłącznie po zmonitorowaniu rzeczywistego obciążenia na produkcji (po wdrożeniu `ADR-021`). Do obsługi 1-2 milionów rekordów poprawnie założone indeksy złożone (`profile_id` + `ascent_date`) w 100% nam wystarczą.

---

### [AUDYT-046] Wdrożenie Connection Poolingu (pgBouncer)
**Obszar:** `Infrastruktura / DevOps`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Django otwiera odrębne połączenie do bazy danych dla każdego napływającego żądania HTTP. Przy tysiącach zapytań (szczególnie w środowisku kontenerowym bez limitów Workerów) doprowadzi to do błędu wyczerpania puli połączeń na serwerze PostgreSQL (`max_connections`).

**Action Items (Do wdrożenia przy rosnącym ruchu):**
- [ ] Wprowadzić lekką usługę pulowania połączeń (np. `pgBouncer`) jako osobny kontener Docker w pliku `compose.prod.yml`.
- [ ] Przekierować Gunicorna do uderzania w port pgBouncera zamiast bezpośrednio do bazy.

**Komentarz Architekta:**
Klasyka skalowania aplikacji Pythonowych. Mamy na to czas – przy 50-100 aktywnych użytkownikach dziennie Postgres poradzi sobie doskonale.

---

### [AUDYT-052] Ryzyko braku skalowalności głębokiej hierarchii geograficznej
**Obszar:** `Baza Danych / Architektura`  
**Priorytet:** `🟡 ŚREDNI (Długoterminowy)`  

**Diagnoza Audytora:** 
Obecny model danych zakłada 7-poziomową strukturę terytorialną opartą na `ForeignKey` (np. Kraj -> Województwo -> Makroregion). Ogranicza to elastyczność systemu przy zmianach podziału terytorialnego i zmusza ORM do budowania kosztownych złączeń (`JOIN`), co wpłynie negatywnie na analitykę przy dużym wzroście bazy danych.

**Action Items (Do wdrożenia w Fazy Utrzymaniowej):**
- [ ] Zaprojektować migrację struktury z 7 dedykowanych tabel do jednej tabeli regionów opartej na relacjach wewnątrz samej siebie (wzorzec Adjacency List z użyciem `parent_id` oraz `level_enum`).
- [ ] Zbadać użycie rozszerzenia PostgreSQL `ltree` do bardzo szybkiego odpytywania zagnieżdżonych drzew terytorialnych bez `JOIN`-ów.

**Komentarz Architekta:**
Klasyczny dług technologiczny. Do momentu osiągnięcia dziesiątek tysięcy użytkowników i obiektów w Polsce obecna architektura połączona z tabelą CQRS (Zmaterializowanym widokiem odczytu `ObjectRegionCache`) jest w pełni wydolna. Zadanie do realizacji w okienku optymalizacyjnym (Scale-Out Phase).

---

### [AUDYT-054] Ryzyko braku szyfrowania transmisji w sieci wewnętrznej Docker
**Obszar:** `DevOps / Bezpieczeństwo Infrastruktury`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Aplikacja komunikuje się wewnątrz ekosystemu Docker Compose (między Django, PostgreSQL i Redisem) używając surowego, nieszyfrowanego protokołu (np. zadeklarowany `DATABASE_URL` z przedrostkiem `postgis://` a nie `postgisql+sslmode=require://`). Dane PII przesyłane są jawnym tekstem (Plaintext). Chociaż izolacja sieci w Dockerze obniża ryzyko ataku, to w standardzie Zero-Trust narusza to polityki bezpieczeństwa (szczególnie w środowisku Kubernetes i publicznych chmur).

**Action Items (Do wdrożenia przed uruchomieniem w Cloud/K8s):**
- [ ] Wdrożyć wymóg użycia protokołów szyfrowanych (`TLS`/`SSL`) dla wewnątrzklastrowej komunikacji z instancjami bazy danych i brokera wiadomości.

**Komentarz Architekta:**
W środowisku pojedynczego serwera z Docker Compose jest to ryzyko akceptowalne. Jeśli platforma migrować będzie w stronę zarządzanych usług (np. AWS RDS i Elasticache), TLS zostanie wdrożony natywnie na poziomie zmian w zmiennych `.env.prod`.

---


### [AUDYT-055] Otwarta Decyzja Architektoniczna (PD-01): Normalizacja Hierarchii Regionów
**Obszar:** `Architektura / Model Danych`  
**Priorytet:** `🟡 ŚREDNI (Faza Optymalizacji)`  

**Diagnoza Audytora:** 
System geograficzny posiada 7 poziomów zagnieżdżenia w osobnych tabelach (np. Województwo -> Powiat -> Gmina). Z jednej strony to silnie znormalizowane, z drugiej strony buduje ogromny łańcuch `JOIN` w zapytaniach. Audytor zdefiniował to jako oficjalny Punkt Decyzyjny (PD-01), dla którego należy świadomie wybrać jeden z trzech modeli w miarę wzrostu aplikacji: Adjacency List (jedna tabela z kluczem do samej siebie), Ltree (drzewo strukturalne PostGIS) lub obecny model wsparty widokami zmaterializowanymi (Materialized Views).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Opracować i zatwierdzić `ADR-026 — Strategia Modelowania Drzewa Terytorialnego`, który ostatecznie rozstrzygnie podejście do hierarchii po weryfikacji wydajności na 10 tysiącach obiektów.

**Komentarz Architekta:**
Klasyczny dylemat między elastycznością schematu a szybkością zapytań. Przy obecnej skali i architekturze Czystej Domeny nie jest to bloker, ale uświadomienie sobie istnienia tego "rozjazdu" ułatwi planowanie optymalizacji bazy w przyszłości.

---

### [AUDYT-056] Otwarta Decyzja Architektoniczna (PD-02): Strategia Partycjonowania Tabeli `AscentLog`
**Obszar:** `Architektura / Baza Danych`  
**Priorytet:** `🟡 ŚREDNI (Faza Skalowania)`  

**Diagnoza Audytora:** 
Audytor wprost stawia przed nami wymóg wyboru ścieżki partycjonowania dla tabeli przechowującej wpisy turystów, która jako jedyna w systemie będzie rosnąć nielimitowanie (logi wejść). Ostrzega przed podziałem wyłącznie po dacie, jeśli główne zapytania aplikacji operują na przekrojach terytorialnych lub identyfikatorach turystów (co jest prawdą, nasza Czysta Domena pyta zawsze o konkretnego turystę).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Po przekroczeniu progu ostrzegawczego (np. 1 miliona logów w tabeli), wdrożyć w PostgreSQL partycjonowanie natywne (Partitioning) po kluczu `profile_id` (wzorzec Hash Partitioning) zamiast po `ascent_date`.

**Komentarz Architekta:**
Wspaniała prewencja przed spadkiem wydajności zapytań. Nasz Use Case sprawdza wszystkie wejścia danego turysty naraz.

---

### [AUDYT-057] Potrzeba wdrożenia mechanizmów ABAC / RBAC (PD-04)
**Obszar:** `Architektura / Bezpieczeństwo`  
**Priorytet:** `🟢 NISKI (W miarę wprowadzania ról)`  

**Diagnoza Audytora:** 
Obecny system rozdziela użytkowników jedynie na `Admin`, `Owner` i resztę świata. Audytor zwraca uwagę, że jeśli system się rozrośnie i wprowadzimy do niego rolę "Weryfikatora PTTK" (osobę, która nie jest Adminem całego systemu, ale ma prawo cofać odznaki w określonym oddziale) lub rolę "Członka Rodziny" (z ograniczonymi prawami dostępu do profili), obecny model uprawnień (Security Matrix) zawiedzie. Wskazuje potrzebę wdrożenia Attribute-Based Access Control (ABAC) lub Role-Based Access Control (RBAC).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Rozważyć wdrożenie paczki zarządzania uprawnieniami per obiekt (np. `django-guardian` dla RBAC/ABAC), w momencie tworzenia panelu Weryfikatora.

**Komentarz Architekta:**
Wyprzedzanie przyszłości. Mamy to już zabezpieczone koncepcyjnie w `SECURITY_MATRIX.md`, ale w miarę pojawiania się nowych typów użytkowników kod autoryzacji w widokach `views.py` musiałby zostać zastąpiony ustandaryzowaną usługą dostępową.

---


### [AUDYT-060] Prawdziwa Integracja API bez fałszywych Mocków (Fake DI)
**Obszar:** `Testy API`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Plik `tests/apps/api/test_integration.py` (916 linii) ma w nazwie "integration", ale w rzeczywistości **mockuje Use Case'y** przez `get_container`. Oznacza to, że nie weryfikuje on prawdziwego przejścia przez cały cykl życia bazy danych. To są wyizolowane testy kontraktów HTTP, a nie testy integracyjne.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Zmienić nazwę pliku z `test_integration.py` na np. `test_api_controllers.py`, co uściśli jego rolę (izolacja).
- [ ] Utworzyć w przyszłości nowy plik prawdziwych testów integracyjnych, który wywoła widok z podpiętą prawdziwą (testową) bazą danych bez omijania (mockowania) Czystej Domeny.

**Komentarz Architekta:**
Audytor słusznie obnażył nazewnictwo. Nasze testy kontrolerów są wspaniałe, ale nie są "integracyjne". Prawdziwą integrację (E2E) sprawdzimy jednak w Playwright, więc tworzenie nowych testów zapytań HTTP w `pytest` można odłożyć na później.

---

### [AUDYT-061] Oczyszczenie testów z `date.today()` i Czasu Systemowego (Flaky Tests)
**Obszar:** `Testy Domeny`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Mimo wdrożenia `FakeClock`, testy w `test_badge_version.py` oraz `test_badge_rules.py` nadal twardo wywołują w kodzie `date.today()`. Skutkuje to zjawiskiem "Flaky Tests" – test uruchomiony 15 Czerwca przejdzie, ale uruchomiony za 5 lat (lub o północy) pęknie, bo naruszy definicje w regulaminach odznak (np. `TimeLimitRule`). Podobny problem występuje w `test_clock.py` z testowaniem `datetime.now(UTC)` z marginesem 1 sekundy.

**Action Items (Do wdrożenia przed uruchomieniem CI/CD):**
- [ ] Przeszukać wszystkie pliki w `tests/domain/` i zastąpić każde użycie `date.today()` sztywną datą, np. `date(2024, 6, 15)` (zgodnie z `FakeClock.DEFAULT_TIME`).

**Komentarz Architekta:**
Złapanie "czasu" w testach to podstawa. Czysta domena wymaga 100% determinizmu w testach.

---


### [AUDYT-063] Duplikaty Fixture'ów i Brak `conftest.py`
**Obszar:** `Architektura Testów`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Pliki takie jak `test_integration.py` i `test_badge_rules.py` używają lokalnie zdefiniowanych atrap (np. `ctx` dla `VerificationContext`, `MockUnitOfWork`, `MockEventPublisher`). Te same atrapy są wielokrotnie kopiowane na górze poszczególnych plików testowych.

**Action Items (Do wdrożenia w Fazy Optymalizacji):**
- [ ] Utworzyć plik `tests/conftest.py` na głównym poziomie katalogu testów.
- [ ] Przenieść definicje wspólnych mocków i atrybutów jako funkcyjne `@pytest.fixture`, a następnie wykasować je z poszczególnych plików `.py`.

**Komentarz Architekta:**
Zasada DRY w testach. Do zrealizowania podczas "Sprzątania Posesji", gdy projekt osiągnie stabilność funkcjonalną.

---

### [AUDYT-065] Eliminacja "God Class" w Kontenerze DI (Dependency Injection)
**Obszar:** `Bootstrap / Inżynieria Oprogramowania`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Obecnie kontener `bootstrap/container.py` inicjuje i rejestruje wszystko w jednej, wielkiej klasie `AppContainer`. W miarę jak projekt urośnie do 30-40 Use Case'ów (przy podwojeniu funkcjonalności), plik ten przekroczy kilkaset linijek kodu i stanie się wąskim gardłem przy tworzeniu instancji, tzw. nową "God Class", co będzie prowadzić do konfliktów scalania w Git.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Rozbić `AppContainer` na modułowe podkontenery, np. `BadgeContainer`, `TouristContainer`, `InfraContainer`.
- [ ] Zastosować wzorzec *Composition* w głównym pliku `bootstrap/__init__.py`, który sklei mniejsze kontenery w jedną zależność.

**Komentarz Architekta:**
Klasyczny ból wzrostu w architekturze "Manual DI" (tworzonej bez frameworków do wstrzykiwania). Obecnie trzyma to projekt w ryzach, ale podział modułowy będzie naturalnym, kolejnym krokiem.

---

### [AUDYT-066] Wymóg wsparcia dla wersji Offline (Local-First Architecture)
**Obszar:** `Frontend / UX / Aplikacja Mobilna`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Architektura aplikacji jest obecnie w 100% "Online". Mapa renderuje MVT pobierane z serwera, a logowanie wymaga HTTP do Django. Brak dostępu do sieci w górach uniemożliwia korzystanie z aplikacji. Zbliżające się wejście w obszar PWA (Progressive Web App - US-D05) natrafi na mur w postaci braku lokalnego stanu przeglądarki.

**Action Items (Do wdrożenia w Fazy D / Rozwoju PWA):**
- [ ] Zaimplementować lokalny Service Worker z polityką Cache-First dla podkładów mapowych (MVT / Raster).
- [ ] Wdrożyć mechanizm Offline Queue (kolejkowanie asynchroniczne) w HTMX/JS, by wejścia logowane na szlaku zapisywały się w IndexedDB, a po złapaniu zasięgu sieć automatycznie wysyłała payload HTTP POST.

**Komentarz Architekta:**
Wspaniała diagnoza. Architektura "Zawsze Połączony" nie sprawdza się w Bieszczadach. Kolejkowanie akcji to trudny, ale niezbędny krok dla UX.

---

### [AUDYT-067] Brak polityki wsparcia Wielojęzyczności (i18n)
**Obszar:** `Django / Architektura Informacji`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Domena, raporty błędów RFC 7807 oraz szablony HTMX są wbudowane "na sztywno" w języku polskim. Brak zastosowania tagów tłumaczeń Django (`{% trans %}` lub `_("...")`). W przypadku wejścia na rynek czeski lub słowacki, będzie to wymagało przepisania całej warstwy prezentacji. Dodatkowo model `TouristObject` wyciąga nazwy lokalne z JSONB, ale nie istnieje w widokach mechanizm decydujący, który język wyświetlić.

**Action Items (Do wdrożenia w przypadku internacjonalizacji):**
- [ ] Dodać konfigurację `i18n` do `settings.py` oraz `app_settings.py`.
- [ ] Zmodyfikować DTO wyjściowe i Exception Handlery, aby wywoływały funkcję `ugettext_lazy` przed serializacją JSON-a.

**Komentarz Architekta:**
Jest to standardowe założenie odłożone na później w fazie MVP, jednak warto o nim pamiętać przy projektowaniu bazy.

---

### [AUDYT-068] Przewidywane "Wąskie Gardło" Sesji Django (Session Bottleneck)
**Obszar:** `Skalowalność / DevOps`  
**Priorytet:** `🟢 NISKI (Przy wzroście powyżej 10k użytkowników)`  

**Diagnoza Audytora:** 
Obecnie mechanizm `django.contrib.sessions` i przełączanie profilu (`active_profile_id`) opiera się o relacyjną bazę PostgreSQL. Kiedy w systemie pojawi się tysiące równoległych użytkowników klikających mapę (każdy odpytujący bazę o ważność swojej sesji z każdym żądaniem HTTP API), tabela `django_session` stanie się krytycznym punktem zaporowym (Bottleneck).

**Action Items (Do wdrożenia w fazie Optymalizacji SRE):**
- [ ] Zmienić silnik sesji Django na `django-redis-sessions`.
- [ ] Wprowadzić natywne użycie klastra pamięci podręcznej jako Engine do autoryzacji (zamiast obciążać dysk fizyczny).

**Komentarz Architekta:**
To zmiana operacyjna wymagająca tylko jednej linijki w pliku `settings.py`, zdefiniowana w dokumentacji Django jako gotowe rozwiązanie.



---

### [AUDYT-071] Ukryte zapytanie do bazy w `TouristObjectAdminForm.__init__`
**Obszar:** `Django Admin / Wydajność`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
W pliku `apps/badges/forms.py` konstruktor formularza (`__init__`) wywołuje `.distinct()` na pełnym zbiorze `TouristObject`, by zbudować podpowiedzi do widżetu `<datalist>`. W panelu Django Admin, formularz jest powoływany (instancjonowany) **dla każdego wyświetlanego wiersza na liście lub w widokach Inline**. Przy 1000 szczytów załadowanie prostej strony w panelu wyzwoli 1000 bezcelowych, obciążających zapytań o "Typy Obiektów".

**Action Items (Do wdrożenia w Fazy Optymalizacji SRE):**
- [ ] Przebudować zapytanie dla `<datalist>`. Zamiast dociągać dane w konstruktorze `__init__`, zastosować `cache.get_or_set` (z Redis) lub wstrzykiwać te wartości w locie do widoku/szablonu, odcinając złączenie z procesem budowania pojedynczego formularza.

**Komentarz Architekta:**
Cichy morderca wydajności. Pół sekundy zaoszczędzone na jednej stronie zamieni się w ułamki milisekund.

---

### [AUDYT-072] Zależności cykliczne `apps` -> `infrastructure` (Leniwe importy Tasków)
**Obszar:** `Infrastruktura / Architektura`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Zastosowany przez nas "hack" z leniwym importem w `celery_event_publisher.py` (`from apps.badges.tasks import ...`) wewnątrz metody to tzw. ucieczka przed architekturą. Mimo, że rozwiązuje błąd na poziomie interpretera Pythona (import się nie zapętla), formalnie tworzy pętlę logiczną: aplikacja Django (`apps`) zależy od `infrastructure`, a `infrastructure` zależy z powrotem od `apps`.

**Action Items (Do wdrożenia w Fazy Refaktoryzacji):**
- [ ] Przebudować strukturę zadań asynchronicznych. Wydzielić `tasks.py` z katalogu aplikacji Django (`apps/badges/`) do osobnego, bezstanowego modułu bliżej infrastruktury (np. `infrastructure/async_workers/`), łamiąc cykl zależności na poziomie struktury plików.

**Komentarz Architekta:**
Piękna uwaga. O ile na ten moment nasza "prowizorka" działa i jest przetestowana, w miarę wzrostu systemu te importy staną się trudne w utrzymaniu.

---

### [AUDYT-073] Zagrożenie Spamem w Celery (Admin Actions)
**Obszar:** `Django Admin / Celery`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Panel administracyjny (`apps/badges/admin.py`) posiada wbudowane instrukcje `.save()`, które odpalają w tle pobieranie z OSM lub CQRS. Obecny kod nie posiada zabezpieczeń przed Rate Limitingiem. Jeśli administrator zaznaczy 500 obiektów i kliknie "Zapisz" (lub wywoła masową akcję w panelu), wygeneruje to w ułamku sekundy 500 zadań Celery, co skutecznie zamrozi kolejkę na inne, ważniejsze zadania od prawdziwych turystów, lub sprowokuje blokadę na serwerach zewnętrznych (Overpass API).

**Action Items (Do wdrożenia w Fazy Optymalizacji):**
- [ ] Wyodrębnić masowe akcje (Bulk Actions) do dedykowanych metod w Use Case'ach, które wspierają "zgrupowane" wysyłanie list ID (Batching) zamiast generowania tysięcy pojedynczych opóźnionych wiadomości (`.delay()`).

**Komentarz Architekta:**
Administrator też potrafi niechcący położyć system. To ważne zabezpieczenie zapobiegające sabotażowi wewnętrznemu.

---

### [AUDYT-074] Brak jednolitych metryk i analizy zapytań (EXPLAIN ANALYZE)
**Obszar:** `Wydajność / Baza Danych`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Wszystkie wcześniejsze przypuszczenia o wąskich gardłach w bazie danych (np. wolne zapytania dla `ST_DWithin` czy N+1 w relacjach regionów) są czysto hipotetyczne, ponieważ opierają się wyłącznie na statycznej analizie kodu (Static Analysis). W projekcie brakuje twardych metryk i dowodów z wykonania kodu w czasie rzeczywistym.

**Action Items (Do wdrożenia w fazie stabilizacji / SRE):**
- [ ] Zainstalować narzędzie takie jak `django-silk` lub wdrożyć bibliotekę `django-debug-toolbar` w środowisku deweloperskim i testowym.
- [ ] Wygenerować zrzuty `EXPLAIN ANALYZE` dla krytycznych ścieżek biznesowych (np. wejście na stronę odznaki, wgranie pliku GPX), aby udowodnić lub obalić potrzebę partycjonowania czy dodawania nowych indeksów do bazy.

**Komentarz Architekta:**
Klasyczne podejście Data-Driven Engineering. Przestaniemy "zgadywać", co jest wolne, i przejdziemy do pomiarów przed podjęciem decyzji o optymalizacji.

---

### [AUDYT-077] Brak precyzyjnego wsparcia dla pracy Offline
**Obszar:** `Frontend / Architektura Mobilna`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Obecny system PTTK wymaga ciągłego połączenia z serwerem Django do weryfikacji postępów i logowania wejść. W warunkach górskich (brak zasięgu sieci komórkowej) turysta jest odcięty od aplikacji. Architektura SSR (Server-Side Rendering) i HTMX nie wspiera natywnie pracy bez sieci.

**Action Items (Do wdrożenia w Fazy Rozwoju PWA):**
- [ ] Opracować strategię Offline-First: wdrożenie Service Workera buforującego kafelki MVT (MapLibre wspiera to natywnie).
- [ ] Zaprojektować lokalną bazę danych w przeglądarce (IndexedDB) oraz mechanizm "Sync when back online", aby turysta mógł kliknąć "Zaloguj wejście", a aplikacja wysłała payload po złapaniu zasięgu.

**Komentarz Architekta:**
Zgodnie z naszymi wczesnymi ustaleniami, PWA (Progressive Web App) to ostateczny krok rozwoju interfejsu (Faza D). Bez tego aplikacja nie zdobędzie serc turystów na szlakach głębokich Bieszczad.

---

### [AUDYT-078] Rozważenie podziału Bounded Contexts w przypadku dodania nowych systemów
**Obszar:** `Architektura / Domain-Driven Design`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Obecnie system obsługuje dwa główne konteksty (Katalog PTTK oraz Profil Turysty). Audytor przewiduje, że w przypadku podwojenia funkcjonalności (np. wejście w płatności Stripe dla abonamentów PRO, lub budowa silnika powiadomień Push), dalsze dokładanie klas do obecnej struktury doprowadzi do "Piekła Zależności" (Coupling).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Opracować i zatwierdzić dokument wprowadzający nowe Konteksty (np. `Billing Context`, `Notification Context`).
- [ ] Wykorzystać stworzone wcześniej (i odseparowane) Zdarzenia Domenowe (`Domain Events`) jako jedyny, twardy mechanizm komunikacji między tymi nowymi aplikacjami (Pub/Sub).

**Komentarz Architekta:**
To lekcja z budowania startupów. Kiedy zaczynamy pobierać opłaty, płatności nie mogą dotykać tabeli szczytów górskich. Modułowość to nasza jedyna tarcza obronna na przyszłość.

---

### [AUDYT-079] Zabezpieczenie przed atakami CSRF w środowisku Token-Based (Wycofanie `csrf_exempt`)
**Obszar:** `API / Bezpieczeństwo`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecnie wszystkie widoki API w `apps/api/views.py` dekorowane są klauzulą `@method_decorator(csrf_exempt)`. Zostało to wdrożone dla ułatwienia pracy z sesjami na początku Fazy C. Audytor słusznie punktuje, że o ile dla komunikacji z aplikacją mobilną poświadczaną Tokenami (JWT) jest to poprawne, to w przypadku aplikacji przeglądarkowych korzystających z Sesji (Cookie), wyłączenie weryfikacji CSRF naraża każdą mutację danych (np. Logowanie wejścia) na ataki *Cross-Site Request Forgery*.

**Action Items (Do wdrożenia w Fazy Security/API):**
- [ ] Zdefiniować jasny model dla klientów mobilnych i webowych: Wdrożyć w API autoryzację opartą na tokenach (np. `django-rest-framework-simplejwt` bez sesji), **ALBO**
- [ ] Przywrócić obowiązek przesyłania tokenu CSRF w nagłówku HTTP `X-CSRFToken` dla żądań POST/PATCH wysyłanych z HTMX i MapLibre GL JS, zdejmując dekorator `csrf_exempt` z widoków.

**Komentarz Architekta:**
Kluczowa poprawka bezpieczeństwa przed publicznym udostępnieniem aplikacji w internecie. Najprostszym sposobem dla HTMX jest włączenie domyślnych zabezpieczeń Django i dodanie eventu globalnego dodającego token do każdego nagłówka AJAX.

---

### [AUDYT-081] Eliminacja słowa "Odznaka" jako homonimu (Semantyczne ujednoznacznienie)
**Obszar:** `Słownik / Komunikacja w Zespole`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Słowo "Odznaka" w projekcie to niebezpieczny homonim. W dokumentacji i rozmowach potocznych używa się go zamiennie jako: tożsamość ogólna (`BadgeModel` - np. "Korona Gór Polski"), konkretny regulamin w czasie (`BadgeVersionModel` - np. "KGP 2024") oraz jako fizyczny dowód ukończenia subskrypcji dla turysty (`UserBadgeProgress`).

**Action Items (Do wdrożenia w komunikacji):**
- [ ] Wprowadzić do `Glossary.md` i codziennej komunikacji rygor nazewniczy:
  - `Odznaka (Badge)` -> Zawsze odnosi się do nadrzędnego agregatu.
  - `Regulamin / Wersja` -> Zawsze odnosi się do zestawu reguł (`BadgeVersion`).
  - `Zdobycie / Wyzwanie` -> Zawsze odnosi się do postępu turysty (`UserBadgeProgress`).

**Komentarz Architekta:**
W kodzie (na poziomie modeli) jest to idealnie odseparowane. Zagrożenie leży na poziomie "biznesowym", gdy analityk poprosi programistę o "zablokowanie odznaki" – a programista usunie postęp zamiast wyłączyć wersję regulaminu.

---

### [AUDYT-082] Refaktoryzacja `peak_id` na `object_id` w Czystej Domenie
**Obszar:** `Domena / Value Objects`  
**Priorytet:** `🟢 NISKI (Jakość Kodu)`  

**Diagnoza Audytora:** 
Value Object `Ascent` (Wejście) w katalogu `domain/value_objects/ascent.py` zawiera pole nazwane `peak_id`. Stanowi to wyciek z "języka potocznego" do Domeny. Z punktu widzenia systemu logujemy wejścia na `TouristObject` (Obiekty Turystyczne), a nie tylko na góry/szczyty (Peak) – mogą to być wieże, jaskinie czy schroniska. Domena nie powinna zakładać typu geograficznego obiektu.

**Action Items (Do wdrożenia przy okazji refaktoringu):**
- [ ] Zmienić nazwę pola w `Ascent` z `peak_id` na `object_id`.
- [ ] Zaktualizować wszystkie klasy testowe i metody używające tej nazwy argumentu.

**Komentarz Architekta:**
Czysta, książkowa kosmetyka kodu (Clean Code). Podnosi jakość bez ryzyka awarii, ale w tym momencie nie blokuje rozwoju funkcji biznesowych.

---

### [AUDYT-083] Niejednoznaczność metody `get_active_progresses()`
**Obszar:** `Aplikacja / Porty`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Nazwa metody portu `get_active_progresses` (Pobierz Aktywne Postępy) w module postępów turysty jest semantycznie myląca. Zwraca ona wszystkie postępy, które *nie są zarchiwizowane*, a nie te o statusie `IN_PROGRESS` (w tym również ukończone, np. `COMPLETED`). W efekcie serwisy (jak `PoiScoringService`) muszą ręcznie ignorować ukończone postępy w kodzie Pythona.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Zmienić nazwę metody na `get_all_unarchived_progresses()`.
- [ ] **LUB:** Dodać opcjonalny parametr filtrujący do metody w adapterze `DjangoTouristRepository` (np. `exclude_status="COMPLETED"`), aby zapobiec wyciekaniu logiki filtrowania do serwisów w warstwie aplikacji.

**Komentarz Architekta:**
Klasyczny problem przerzucania ciężaru z bazy danych (gdzie można to szybko odfiltrować w SQL) na warstwę Pythona. Przeniesienie warunku do adaptera to krok typu "Quick Win".

---

### [AUDYT-084] Odśmiecianie pojęć technicznych w `application/services`
**Obszar:** `Aplikacja / Serwisy`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Nazwy `PoiScoringService` oraz `ExploreQueriesService` to "Techniczny Bełkot". Łączą w sobie skróty z różnych technologii (POI = Point of Interest) lub słowa-wytrychy (Queries, Service). System powinien posługiwać się czystszym językiem Domenowym (np. "Potencjał Turystyczny" zamiast "POI Score").

**Action Items (Do wdrożenia opcjonalnie):**
- [ ] Rozważyć zmianę nazwy `PoiScoringService` na `PotentialRankingService`.
- [ ] Rozważyć zmianę nazwy `ExploreQueriesService` na `MapDiscoveryService`.

**Komentarz Architekta:**
Zmiana nazw klas dla "lepszego brzmienia" jest użyteczna na bardzo dojrzałym etapie rozwoju projektu. U nas obiekty te i tak są maskowane przez kontener Dependency Injection, a my "rozumiemy" ten slang. Odłożyć do głębokiego Backlogu.

---

### [AUDYT-085] Zablokowanie wycieku infrastruktury do modeli ORM (Luka importowa)
**Obszar:** `Django / Architektura Heksagonalna`  
**Priorytet:** `🟠 WYSOKI` (zrealizowany)

**Diagnoza Audytora:** 
Plik `apps/badges/models.py` importował słownik `RULES_SCHEMA` z `infrastructure/schemas/badge_rules_schema.py`. To stanowiło złamanie kierunku zależności Heksagonu — infrastruktura nie powinna być zależna od warstwy Delivery (`apps/`), a tu było odwrotne.

**Wdrożone:**
- [X] Przeniesiono `RULES_SCHEMA` z `infrastructure/schemas/badge_rules_schema.py` do `apps/badges/rules_schema.py`.
- [X] Zaktualizowano import w `apps/badges/models.py` → `from apps.badges.rules_schema import RULES_SCHEMA`.
- [X] Usunięto wyjątek `DŁUG-002` z `.importlinter` (kontrakt `hexagonal-layers`).
- [X] Przeniesiono testy z `tests/infrastructure/test_badge_rules_schema.py` → `tests/apps/badges/test_rules_schema.py`.
- [X] Zaktualizowano `RULES_SCHEMA` import w `tests/apps/badges/test_models.py`.

**Uzasadnienie:**
`RULES_SCHEMA` to konfiguracja UI dla `django-jsonform` w Django Admin — nie jest logiką infrastruktury. Przeniesienie go do `apps/badges/` przywraca poprawny kierunek zależności: `infrastructure/ → apps/` (nie odwrotnie). `lint-imports` potwierdza 4 contracts, 0 broken.

---

### [AUDYT-086] Brakujące pokrycie testami dla reguły z oknem czasowym
**Obszar:** `Testy Jednostkowe / Czysta Domena`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Zdefiniowana w `badge_rules.py` reguła biznesowa `DateWindowRule` (odpowiadająca za zamykanie postępu po okresie jubileuszowym) nie posiada w repozytorium ani jednego dedykowanego testu domenowego. Skutkuje to powstaniem luki w 100% gwarantowanym pokryciu (Code Coverage) logiki weryfikacyjnej.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [ ] Dodać do pliku `tests/domain/rules/test_badge_rules.py` zestaw minimum dwóch testów (Happy Path i Negative Path) dla instancji klasy `DateWindowRule`.

**Komentarz Architekta:**
Wspaniałe wyłapanie braku (Blind Spot) w procesie TDD! Każda reguła biznesowa musi mieć przypisanego swojego fizycznego strażnika (test).

---

### [AUDYT-087] Luki w procesie zarządzania Limitami Freemium (Krawędzie pakietów)
**Obszar:** `Aplikacja / Freemium Business Logic`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Proces "Pakiety Freemium" posiada niezaadresowaną ścieżkę krytyczną. Jeśli turysta posiada aktualnie 5 subskrypcji na koncie PRO i zrezygnuje z pakietu PRO (wracając do pakietu FREE z limitem 3 subskrypcji), system nie definiuje, co ma się stać z 2 nadmiarowymi, aktywnymi odznakami (status `IN_PROGRESS`). Obecnie nie istnieje żaden "Reconciliation Job" (Zadanie Wyrównujące) ani reguła w Czystej Domenie, która radziłaby sobie z takim zjawiskiem.

**Action Items (Do wdrożenia przed udostępnieniem subskrypcji B2C):**
- [ ] Zaprojektować i udokumentować (np. w `UI_GUIDELINES.md` lub `STORIES.md`) politykę "Downgrade'u" konta: czy nadmiarowe odznaki zostają zamrożone (Read-Only), czy turysta musi ręcznie wybrać, z których dwóch odznak zrezygnować, by móc logować wejścia.
- [ ] Zaimplementować walidację w `VerifyBadgeUseCase`, która zablokuje przeliczanie postępu na zamrożonych odznakach, jeśli limit jest przekroczony.

**Komentarz Architekta:**
Klasyczny przypadek Edge Case biznesowego. Downgrade kont to zawsze najtrudniejszy element projektowania SaaS, który został u nas pominięty na rzecz łatwiejszego projektowania "awansów" kont (Upgrade).

---

### [AUDYT-088] Brak obsługi błędów 429 (Rate Limit) u Zewnętrznych Dostawców (Mapy.cz / OSM)
**Obszar:** `Infrastruktura / API Integrations`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Proces "Wybór Podkładu Mapowego" pozwala na serwowanie kafelków wektorowych, a "Analiza GPX" i "Nocny Stróż" opierają się na Overpass API. Chociaż zaimplementowaliśmy Linear Backoff dla Overpass, w kodzie aplikacji front-endowej (dla MapLibre i Mapy.cz) brakuje obsługi błędu "429 Too Many Requests". Jeśli turysta lub bot wyczerpie limit klucza API dla kafelków mapowych, aplikacja "cicho" zawiedzie, pokazując czarne tło zamiast awaryjnie przywrócić darmowy podkład OSM.

**Action Items (Do wdrożenia w fazie optymalizacji SRE):**
- [ ] W pliku `map.js` dodać `Event Listener` na błędy ładowania źródła mapy (`map.on('error', ...)`).
- [ ] W przypadku odrzucenia kafelków z kodem 429 lub 403, automatycznie zmienić URL źródła w MapLibre z powrotem na publiczny, darmowy podkład z `map_layers.py` (Fallback).

**Komentarz Architekta:**
Poleganie na tym, że zewnętrzni dostawcy map (nawet ci płatni) będą działać zawsze, to naiwność. Fallback w JS uchroni UX przed katastrofą.

---

### [AUDYT-089] Brak ochrony przed martwymi wpisami w "Czarnych Listach" (Cofanie Weryfikacji)
**Obszar:** `Aplikacja / Osobisty Kanban`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Dokument `INVARIANTS.md` definiuje Invariant S-04 (Zakaz Kasowania Faktów - Czarna Lista). Kiedy Weryfikator PTTK (lub turysta) wycofa odznakę ze stanu `COMPLETED` do `IN_PROGRESS`, "błędny" log ma trafić na czarną listę. Audytor wyłapał, że w systemie **nie istnieje fizyczna tabela analityczna ani mechanizm Czystej Domeny** obsługujący dodawanie `ascent_id` do "Odrzuconych". Widok `AdvanceLogisticStatusUseCase` potrafi tylko cofać status, ale nie izoluje uszkodzonych/odrzuconych logów.

**Action Items (Do wdrożenia):**
- [ ] Zgodnie z długiem `US-C08b`, stworzyć nową encję np. `RejectedAscent` lub dodać flagę `is_rejected=True` do modelu `AscentLog`.
- [ ] Odfiltrowywać zablokowane wejścia na poziomie portu (`get_unconsumed_ascents`) lub Use Case'a weryfikacji.

**Komentarz Architekta:**
Wspaniała weryfikacja biznesowa. Zaprojektowaliśmy proces w dokumentacji, ale w ferworze prac nad Dockerem pominęliśmy stworzenie fizycznego mechanizmu "czarnych list". Będzie to kluczowe, gdy PTTK włączy się w weryfikację.

---

### [AUDYT-090] Brakujący Interfejs (UX) do Przełączania Praw Nabytych
**Obszar:** `API / UX`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
`US-C05` gwarantuje turyście "Świadomy wybór Regulaminu". Nasz kod w `StartBadgeProgressUseCase` realizuje "Leniwe Zakotwiczenie" – automatycznie znajduje i podczepia turystę pod stary regulamin na podstawie daty jego najstarszego wejścia (Grandfather Clause). Audytor wyłapał jednak lukę w UX: turysta, po automatycznym zakotwiczeniu go przez system w np. regulaminie z 2018 roku, **nie posiada na ekranie przycisku (Switch Version)**, który pozwoliłby mu dobrowolnie zrezygnować ze starych praw i przejść na najnowszą, obecną wersję odznaki, jeśli woli zdobywać ją po nowemu!

**Action Items (Do wdrożenia w Fazy C / UX Refinements):**
- [ ] Zbudować endpoint `PATCH /api/v1/progress/{id}/switch_version` w `apps/api/views.py`.
- [ ] W klasie Use Case `StartBadgeProgress` dopisać osobną metodę `switch_version` weryfikującą, czy odznaka nie ma jeszcze podpiętych w tym cyklu wejść z datą uniemożliwiającą przejście, lub pozwalającą na twardą zmianę `version_id`.
- [ ] Dodać przycisk "Zmień na nowszy regulamin" na stronie `/badge/{code}/`.

**Komentarz Architekta:**
Klasyczne "odcięcie frontendu od backendu". Backend to umie (bo przyjmuje parametr `version_id`), ale turysta nie ma jak wywołać tego żądania. Krytyczne dla zgodności z oryginalną intencją biznesową.


---

### [AUDYT-092] Pusta odpowiedź z API przy braku obiektów (Silent Success)
**Obszar:** `API / UX GPX`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
W scenariuszu `US-C17` wgrywamy ślad GPX, by znaleźć pobliskie szczyty. Jeżeli ślad znajduje się np. w Niemczech, funkcja `distance_lte` PostGIS-a odrzuca wszystkie polskie obiekty i zwraca pustą listę. API odpowiada cichym `200 OK` z pustą listą. Brak odpowiedniej obsługi tego stanu (np. `404 Not Found` dla trasy bez punktów) powoduje, że klient HTMX zarysuje turyscie pusty ekran.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Dodać wyraźny komunikat i obsługę stanu "Empty State" (Pusty Koszyk) w kodzie widoku `gpx_upload.html` lub wymusić na Use Case w `AnalyzeGpxTrackUseCase` rzucanie błędu biznesowego `Brak obiektów PTTK w promieniu 200m od wyznaczonej trasy.`

**Komentarz Architekta:**
Czysta sprawa UX, zapobiegająca konfuzji turysty.

---

### [AUDYT-093] Brak zautomatyzowanej kwarantanny dla złośliwych danych OSM
**Obszar:** `Dane Referencyjne / DataOps`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecny mechanizm "Nocnego Stróża" (`RunOsmNightWatchmanUseCase`) potrafi zgłaszać konflikty do skrzynki odbiorczej (Inbox), ale brakuje mu systemu odporności na celowe zatruwanie danych. Atakujący w OpenStreetMap może edytować znany szczyt PTTK (np. Rysy), zmieniając jego współrzędne tak, by znalazł się na Alasce, co zniszczyłoby wyliczanie CQRS i weryfikację. Nasz system aktualizuje tagi w `osm_raw_tags` w tle, nie alarmując o drastycznych anomaliach przestrzennych.

**Action Items (Do wdrożenia w Fazy SRE):**
- [ ] Zdefiniować próg kwarantanny geolokacyjnej (np. "przesunięcie wierzchołka o więcej niż 500 metrów" lub "zmiana wysokości o więcej niż 10%").
- [ ] Zaprojektować regułę w `OsmRepositoryPort`, która wstrzyma cichą aktualizację `osm_raw_tags` przy przekroczeniu progu, blokując synchronizację do czasu interwencji administratora.

**Komentarz Architekta:**
Klasyczny "Blind Spot" integracji zewnętrznych. Całkowite zaufanie do otwartego API (OSM) to ryzyko wandalizmu (Vandalism Attack). Ciche wstrzymanie (Quarantine) zabezpieczy nas przed rozpadem siatki MVT.

---

### [AUDYT-094] Zagrożenie przeciążenia puli (Connection Pooling Exhaustion)
**Obszar:** `Infrastruktura / Baza Danych`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Zastosowaliśmy potężną asynchroniczność w postaci Celery (do przeliczania punktów 100/n, Radaru CQRS, czy integracji z OSM). Przy domyślnej konfiguracji Django i Celery, każdy włączony proces Celery otworzy własne, równoległe połączenie z bazą PostgreSQL. Przy masowym wgrywaniu GPX, nagły skok (Spike) zapytań asynchronicznych uderzy w serwer SQL wyczerpując jego limit `max_connections`, co doprowadzi do twardego odrzucania żądań HTTP (błąd 500) od zwykłych turystów!

**Action Items (Do wdrożenia w środowisku produkcyjnym):**
- [ ] Skonfigurować system wbudowanej puli połączeń Django (`CONN_MAX_AGE` w `DATABASES`) połączony z limitem konkurencji (`--concurrency=X`) dla workerów Celery w pliku `compose.prod.yml`.
- [ ] Opcjonalnie wdrożyć oprogramowanie `PgBouncer` po stronie infrastruktury.

**Komentarz Architekta:**
Zgodnie z obietnicą audytora, to jest "Blind Spot" w systemach rozproszonych. Skalowalność Celery może zabić bazę danych, jeśli jej nie zdławimy.

---

### [AUDYT-095] Przeoczenie braku "Rate Limiting" w zabezpieczonym API
**Obszar:** `Bezpieczeństwo / API REST`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Udało nam się perfekcyjnie zabezpieczyć środowisko przed wstrzykiwaniem logów bez sesji czy atakami IDOR. Namunely zapomnieliśmy o tzw. atakach wolumetrycznych (Volumetric Attacks). Atakujący, używając poprawnego konta FREE, może w pętli `for` wywoływać `POST /api/v1/gpx/analyze` 100 razy na sekundę, każąc serwerowi bez ustanku parsować ciężki XML w pamięci RAM i zarzynając procesy Gunicorna dla reszty użytkowników (DoS).

**Action Items (Do wdrożenia w Fazy API/DevOps):**
- [ ] Skonfigurować Rate Limiter na poziomie aplikacji Django (np. paczka `django-ratelimit`) dla najcięższych endpointów API.
- [ ] (Alternatywa) Zaimplementować Rate Limiting na poziomie serwera wchodzącego (Caddy) w oparciu o adresy IP i tokeny sesyjne.

**Komentarz Architekta:**
Wyjątkowo słuszna i celna obserwacja. Nawet połatany i odporny na bugi kod podda się przy uderzeniu fizycznie zbyt dużej liczby zapytań o przeliczanie matematyki wektorowej.

---

### [AUDYT-096] Niespójność obsługi braku Daty Urodzenia (Reguła Wiekowa)
**Obszar:** `Domena / Reguły Biznesowe`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Audytor wyłapał jawną sprzeczność w Czystej Domenie:
- `MinAgeRule`: Jeśli turysta nie podał daty urodzenia, reguła zakłada, że jest pełnoletni i go **przepuszcza**.
- `MaxAgeRule`: Jeśli turysta nie podał daty urodzenia, reguła **odrzuca** go z błędem.
Choć biznesowo może to mieć sens (odznaki dziecięce są "przywilejem", a odznaki dla dorosłych są domyślne), brak jest w kodzie komentarza wyjaśniającego tę asymetrię przy `MaxAgeRule`, co grozi omyłkowym "naprawieniem" tego przez innego programistę.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [ ] Dodać wyraźny komentarz w `MaxAgeRule.validate` wyjaśniający, że odznaki młodzieżowe to przywilej wymagający twardego dowodu wieku.
- [ ] (Alternatywa) Ujednolicić logikę: Brak daty urodzenia = błąd dla obu reguł (wymuszenie podania wieku).

**Komentarz Architekta:**
Genialne wyłapanie asymetrii (Blind Spot). Należy to jasno zakomentować w kodzie `badge_rules.py`.

---

### [AUDYT-097] Brak strategii wersjonowania API (API Versioning Policy)
**Obszar:** `Dokumentacja / API`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Plik `API_CONTRACTS.md` definiuje ścieżki w formacie `/api/v1/`, ale nie definiuje, **co** spowoduje przejście na `/api/v2/`. Kiedy wprowadzić nową wersję? Czy usunięcie pola z payloadu łamie wsteczną kompatybilność? Brakuje formalnego kontraktu.

**Action Items (Do wdrożenia w Fazy Rozwoju API):**
- [ ] Dodać sekcję "Strategia Wersjonowania API" do `API_CONTRACTS.md` lub stworzyć dedykowany `ADR` wyjaśniający, co stanowi *Breaking Change* w naszym systemie (np. usunięcie pola, zmiana typu, zmiana wymogów CSRF).

**Komentarz Architekta:**
Klasyczny błąd startupów. Zbudowaliśmy wersję `v1`, ale nikt nie pomyślał, kiedy ucinamy wsparcie. Dopóki klientem API jest tylko nasz wewnętrzny frontend (HTMX/JS), to nie jest problem. Jeśli otworzymy to dla aplikacji mobilnych, to jest punkt krytyczny.

---

### [AUDYT-098] Co z wejściami (AscentLog), gdy pula szczytów (pool_peaks) ulegnie zmianie?
**Obszar:** `Domena / Prawa Nabyte`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Architektura w `US-C05` genialnie przypisuje turystę do odpowiedniej "wersji" regulaminu, ale nie odpowiada na jedno krytyczne pytanie brzegowe: *Co się dzieje, jeśli turysta ma zalogowane wejścia z 2020 i 2021 roku, a w 2022 roku zmienia "Wersję" na nowszą (bo np. chce zdobywać odznakę po nowemu)?* Czy jego wejścia z 2020 roku są nadal ważne, jeśli w nowym regulaminie dany szczyt został usunięty z listy?

**Action Items (Do wdrożenia w Przyszłości):**
- [ ] Zdefiniować biznesowo (i zapisać w `INVARIANTS.md`): Czy walidacja wejść działa w trybie "Retroactive" (sprawdza historyczne wejścia względem nowej puli), czy wycięcie szczytu z regulaminu powoduje jego unieważnienie u turysty.
- [ ] Zaimplementować odpowiedni test jednostkowy w `VerifyBadgeUseCase`.

**Komentarz Architekta:**
Wspaniała rozkmina domenowa! Prawny aspekt PTTK potrafi zagiąć najlepszy kod. Musimy ustalić, czy turysta, który zmienia wersję na nowszą, akceptuje utratę nieaktualnych szczytów, czy zachowuje je jako "Złote punkty". Wymaga to ustaleń z ekspertem domenowym (czyli z Tobą!).

---

### [AUDYT-099] Niezdefiniowany proces wygasania starych wersji regulaminów
**Obszar:** `Biznes / Prawa Nabyte`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecny model Praw Nabytych (`US-C05`) opiera się na polu `valid_to` w `BadgeVersionModel`. Jeśli administrator nie wypełni tego pola (`valid_to = NULL`), system traktuje regulamin jako ważny "w nieskończoność". Problem polega na tym, że jeśli PTTK wyda nową wersję odznaki w 2026 roku, ale administrator zapomni ręcznie ustawić datę końcową dla wersji z 2020 roku, nowi turyści bez historii logów będą automatycznie zakotwiczani w **obu** wersjach, lub system wybierze starą z powodu błędnego sortowania w kodzie wybierającym.

**Action Items (Do wdrożenia):**
- [ ] Zaprojektować i zaimplementować wymóg walidacji modelu w `BadgeVersionModel.clean()`, który blokuje stworzenie nowej wersji odznaki, dopóki stara wersja nie ma ustawionej daty końcowej (`valid_to`).
- [ ] Dodać skrypt w Django Adminie (np. akcję), która podczas publikacji nowej wersji automatycznie nadpisuje pole `valid_to` dla poprzedniej wersji z dniem wczorajszym.

**Komentarz Architekta:**
Klasyczny błąd z "zakładaniem" pewnych zachowań administratora. Kod musi wymusić poprawność cyklu życia. Bez tego Prawa Nabyte mogą zacząć działać jak "Prawa Zduplikowane".

---

### [AUDYT-100] Brak procesu dla "Osieroconych Wejść" (P-02) przy zmianie regulaminu
**Obszar:** `Biznes / Logika Weryfikacji`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Jeśli turysta w 2024 roku zdobył 15 z 20 szczytów z puli "Wersji A", a w 2025 roku zechce porzucić stare zasady (na starych zasadach brakuje mu jednego trudnego szczytu) i dobrowolnie przełączyć się na "Wersję B" (nowy regulamin), system nie definiuje, co ma się stać z jego 15 starymi wejściami. Jeśli w "Wersji B" 3 z tych 15 szczytów wyleciały z puli, turysta nagle "utraci" je ze swojego postępu. 

**Action Items (Do wdrożenia):**
- [ ] W dokumencie `STORIES.md` uzupełnić US-C05 o regułę: "Jeśli turysta zmienia wersję na nowszą, akceptuje fakt, że wejścia historyczne na szczyty nieobecne w nowej puli przestają się liczyć do jego progresu".
- [ ] (Alternatywa) Zaimplementować "Kredyty Przejściowe" (Transitional Credits) w Czystej Domenie, które uznają każdy dawny szczyt za ważny, jeśli był ważny w momencie logowania wejścia (bardzo skomplikowane architektonicznie).

**Komentarz Architekta:**
To uderza w samo sedno filozofii PTTK. Jeśli PTTK wyrzuca szczyt ze wzniesień, bo ścieżka stała się zbyt niebezpieczna, to raczej nie chcemy, aby zaliczał się on do nowych odznak. Wymaga konsultacji biznesowej.

---

### [AUDYT-101] Brak mechanizmu wstrzymywania długotrwałych operacji (Cancellation Token)
**Obszar:** `UX / Backend`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Procesy takie jak wgrywanie pliku GPX, odpytywanie Overpass API, czy przeliczanie CQRS mogą trwać od kilku do kilkunastu sekund. W przypadku błędu API na zewnątrz (zawieszenie połączenia), turysta w aplikacji mobilnej lub webowej pozostaje uwięziony na ekranie ładowania. Brak mechanizmu Pollingu (odpytywania o status) lub przycisku "Anuluj" sprawia, że aplikacja wydaje się zamrożona.

**Action Items (Do wdrożenia w Fazy Optymalizacji UX):**
- [ ] Oprogramować przycisk "Anuluj" w widoku HTMX (przerwanie żądania AJAX).
- [ ] W przypadku operacji asynchronicznych (Celery), wdrożyć endpoint odpytujący o status zadania (`GET /api/tasks/{id}`).

**Komentarz Architekta:**
W fazie MVP zakładamy, że użytkownik po prostu odświeży stronę (F5) w razie zawieszenia. Gdy zaczniemy budować interfejsy dla tysięcy osób, te mechanizmy będą obowiązkowe.

---

### [AUDYT-102] Brak instrukcji "How-To" dla dodawania Reguł Biznesowych PTTK
**Obszar:** `Dokumentacja / Onboarding`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecnie dodanie nowej reguły do systemu (np. "Wymagaj wejścia w nocy") wymaga od programisty zgadywania. Wiedza o tym procesie jest rozproszona między: 
1. Stworzenie nowej klasy w `domain/rules/`.
2. Zaktualizowanie słownika parsowania `RULE_BUILDERS` w `django_badge_repo.py`.
3. Zaktualizowanie schematu walidacyjnego JSON w `badge_rules_schema.py`.
Brak tego drugiego lub trzeciego kroku sprawi, że reguła nie załaduje się z bazy lub nie będzie możliwa do wyklikania w panelu Admina.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [ ] Utworzyć plik `docs/HowTo_Add_Business_Rule.md`.
- [ ] Opisać w nim krok po kroku (z przykładem), jakie 3 pliki należy zmodyfikować, by nowa klasa dziedzicząca po `BadgeRule` stała się pełnoprawnym elementem systemu PTTK.

**Komentarz Architekta:**
Niestety, Python to nie Java z automatycznym wstrzykiwaniem i autodiscovery komponentów. Posiadanie wyraźnej instrukcji (tzw. Standard Operating Procedure - SOP) to jedyny ratunek przed "Shotgun Surgery" (chirurgią z użyciem strzelby) podczas modyfikacji.

---

### [AUDYT-103] Wiedza Ukryta: Struktura i rola `VerificationContext`
**Obszar:** `Dokumentacja / Domena`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
`VerificationContext` to nasz genialny obiekt wstrzykujący stan zewnętrzny (czas, datę urodzenia turysty, mapę klubów PTTK) prosto do Czystej Domeny, zabezpieczając Invariant T-02. Jednak jego pełna rola (oraz struktury, z jakich korzysta, np. `club_join_dates: dict[str, date]`) jest nigdzie oficjalnie nieudokumentowana – nowy programista musi ją dedukować bezpośrednio z kodu Pythona lub czytając implementację starych testów.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Zaktualizować plik `DOMAIN_MODEL.md` w sekcji `VerificationContext`.
- [ ] Jawnie opisać, dlaczego domena nie pobiera dat samodzielnie i jak warstwa aplikacji (`VerifyBadgeUseCase`) buduje ten kontekst na podstawie profilu z bazy.

**Komentarz Architekta:**
Klasyczny problem DDD. Odklejenie logiki bazodanowej zmusza do tworzenia "mostów" (Contexts). Brak ich dokładnego opisu zniechęca nowych członków zespołu do przestrzegania czystości warstw.

---

### [AUDYT-104] Brak Readme dla Testów (Zarządzanie Uruchamianiem)
**Obszar:** `Dokumentacja / Testy`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Katalog `tests/` zawiera potężną hierarchię plików (Fakes, Unit, Integracyjne z PostGIS, API), ale brakuje w nim pliku `README.md`. Programista dołączający do projektu musi przeszukiwać główny `Test Strategy.md` lub analizować sam plik `Makefile` (`make check` vs `make test-all`), by zrozumieć, że część testów omija bazę danych, a część wymaga włączonego kontenera Dockera.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Dodać plik `tests/README.md`.
- [ ] Wypisać w nim różnice między uruchamianiem testów w izolacji (szybkie testowanie algorytmów domenowych) a testowaniem w kontenerach (`pytest.mark.django_db` z PostGIS).

**Komentarz Architekta:**
Trywialne zadanie, a jego wykonanie sprawia, że repetytorium wygląda jak projekt utrzymywany przez zespół inżynierów Google. Zdecydowanie warto.

---

### [AUDYT-106] Przeniesienie "Praw Nabytych" do Czystej Domeny (Domain Service)
**Obszar:** `Domena / Usługi Domenowe`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Zasada Praw Nabytych (Grandfather Clause) – czyli decyzja o tym, czy weryfikacja zakończyła się sukcesem i turysta zyskuje odznakę na własność – znajduje się obecnie w kodzie Orkiestratora (`VerifyBadgeUseCase.execute`, linie 93-103). To łamie założenie, że Czysta Domena chroni *wszystkie* niezmienniki biznesowe. Orkiestrator nie powinien "wiedzieć", czym jest prawo nabyte.

**Action Items (Do wdrożenia w Fazy Refaktoryzacji):**
- [ ] Utworzyć nowy Serwis Domenowy (np. `domain/services/badge_awarding_service.py`), który przyjmie historię wejść, daty graniczne oraz obiekty `BadgeVersionDomain`.
- [ ] Zamknąć logikę ewaluacyjną i wybór wersji wewnątrz tego serwisu.

**Komentarz Architekta:**
Klasyczny objaw "Grubych Przypadków Użycia" (Fat Use Cases). To bardzo naturalna ewolucja systemu DDD – gdy Use Case staje się za mądry, wyciągamy z niego reguły do Domain Service.

---

### [AUDYT-107] Ujednolicenie asymetrii wieku (`MinAge` vs `MaxAge`)
**Obszar:** `Domena / Reguły`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Raport po raz kolejny wytyka nieudokumentowaną, twardą asymetrię między regułą `MinAgeRule` (brak wieku turysty = sukces/pełnoletność) a `MaxAgeRule` (brak wieku = błąd/odrzucenie). Sytuacja, w której dwie bliźniacze reguły obsługują przypadek "braku danych" (None) w przeciwny sposób, jest traktowana jako anomalia.

**Action Items (Do wdrożenia przed zaproszeniem testerów):**
- [ ] Wprowadzić jednorodną zasadę obsługi brakujących danych (np. obie reguły zwracają błąd walidacyjny "Data urodzenia jest wymagana dla tej odznaki").
- [ ] Jeśli asymetria jest wymagana biznesowo, należy zadeklarować ją w dokumentacji, stworzyć dedykowany test domenowy `test_min_age_assumes_adult` oraz umieścić szczegółowy komentarz (Docstring) w obu klasach reguł, wyjaśniający rozbieżność.

**Komentarz Architekta:**
Biznesowo asymetria ma sens (oszczędność czasu dla osób dorosłych), ale technicznie rodzi dług. Ujednolicenie tego przez wymóg podania daty usunie lukę.

---

### [AUDYT-108] Brak `TouristProfile` jako Agregatu Domenowego
**Obszar:** `Domena / Ubiquitous Language`  
**Priorytet:** `🟢 NISKI (Długoterminowy)`  

**Diagnoza Audytora:** 
Obecnie w katalogu `domain/` brakuje podstawowego aktora biznesowego: Turysty (`Tourist`). Zamiast tego do reguł przepychany jest techniczny konstrukt `VerificationContext`. Stanowi to dowód na "Anemiczny Model Domenowy", w którym cała koncepcja człowieka, jego limitów Freemium i historii wejść, "uwięziona" jest na dole, w modelach infrastrukturalnych (ORM) w `apps/tourists/models.py`.

**Action Items (Do wdrożenia w Fazy Rozwoju Społecznościowego - Faza D):**
- [ ] Utworzyć agregat `Tourist` (lub `TouristProfileDomain`) w katalogu `domain/entities/`.
- [ ] Przenieść logikę sprawdzania limitów Freemium z warstwy `Application` (np. ze `StartBadgeProgressUseCase`) prosto do metod tego agregatu (np. `tourist.can_start_new_badge()`).
- [ ] Zastąpić `VerificationContext` wstrzykiwaniem tego prawdziwego obiektu domenowego.

**Komentarz Architekta:**
Audytor dotknął sedna. Ograniczenie Czystej Domeny tylko do "Silnika Weryfikacyjnego" to pójście na skróty. Docelowo PTTK to nie tylko matematyka, to społeczność. Wraz ze wzrostem aplikacji turysta musi stać się pierwszoplanową encją w czystym Pythonie.

---

### [AUDYT-111] "FakeClock" poza katalogiem fakes
**Obszar:** `Testy / Architektura`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Plik `Test Strategy.md` oraz liczne opisy architektoniczne wspominają o `FakeClock` jako fundamentach testów deterministycznych. Mimo to, plik o takiej nazwie (np. `tests/fakes/clock.py`) lub `tests/fakes/fake_clock.py` nie jest łatwo dostrzegalny z poziomu drzewa katalogów (lub został zakopany wewnątrz innego pliku), co łamie zasadę czytelnej izolacji Atrap Testowych (Test Doubles).

**Action Items (Do wdrożenia w Fazy Optymalizacji):**
- [ ] Upewnić się, że atrapa czasu (`FakeClock`) rezyduje w wyizolowanym, dającym się łatwo zaimportować pliku w katalogu `tests/fakes/` i posiada własne docstringi opisujące metodę np. `advance()`.

**Komentarz Architekta:**
Drobny szlif organizacyjny, ułatwiający nowym osobom znajdowanie "zamienników" dla środowiska testowego bez szukania w kodzie.

---

### [AUDYT-112] Wdrożenie Automatycznego Wersjonowania (Tag Release Policy)
**Obszar:** `Proces / GitOps`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Mimo że prowadzimy wspaniały, niezwykle precyzyjny `CHANGELOG.md` (z wydaniami np. `0.6.0`), w repozytorium Git nie znajduje się ani jeden tag wersji (tzw. `git tag`). Łamie to zasadę zdefiniowaną w naszym `Manifest/13-release-tagging.md`. Bez formalnych tagów w Gicie nie można automatyzować wdrażania za pomocą Release Registry (`ADR-022`), ponieważ CI/CD nie ma możliwości odwołania się do stabilnej rewizji kodu.

**Action Items (Do wdrożenia PRZEZ CIEBIE po zakodowaniu Playwrighta):**
- [ ] Wywołać `git tag -a v0.6.0 -m "Zakończenie Fazy C"` dla ostatniego stabilnego commita.
- [ ] Dodać do workflowu lokalnego zasadę: Po każdej aktualizacji `CHANGELOG.md` o nową wersję, przed komendą `git push` wywołać nadanie tagu.

**Komentarz Architekta:**
Wdrożenie tego to 15 sekund pracy, a z punktu widzenia DevOps i audytów zamyka to najczęstszą dziurę w procesie dostarczania oprogramowania (CI/CD).

---

### [AUDYT-113] Formalizacja Szablonów Współpracy (PR & Issue Templates)
**Obszar:** `Proces / Zarządzanie Zespołem`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Audytor słusznie wskazuje, że projekt z tak potężną architekturą (Hexagonal, DDD) jest całkowicie "bezbronny" w przypadku dołączenia do niego nowych ludzi. Brak jest formalnych mechanizmów Githuba zmuszających współpracownika do udowodnienia, że przeczytał ADR-y, zanim wrzuci kod. Dokument `REVIEWER.md` jest na razie instrukcją tylko dla agentów AI.

**Action Items (Do wdrożenia w przypadku wejścia w fazę Open Source / Zespół):**
- [ ] Stworzyć plik `.github/PULL_REQUEST_TEMPLATE.md` zawierający obowiązkową checklistę dla nowego programisty (m.in.: *Czy kod przeszedł `make check`? Czy nowa encja nie łamie `ADR-002`? Czy dołączyłeś testy?*).
- [ ] Dodać plik `CODEOWNERS` wymuszający zatwierdzenie zmian w katalogach `/docs/` i `/domain/` przez Głównego Architekta przed procesem `git merge`.

**Komentarz Architekta:**
Bardzo mądre spojrzenie na bezpieczeństwo kodu z perspektywy ludzkiej (Human Risk). Zabezpieczenie przed samowolą Junior Deweloperów.

---

### [AUDYT-114] Brak Degradacji Awaryjnej (Graceful Degradation) dla Redis Cache
**Obszar:** `Operacje / Wydajność / Niezawodność (SRE)`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecny system traktuje pamięć podręczną (Redis) jako "Twardą Zależność" (Hard Dependency). Jeśli usługa Redis ulegnie awarii (np. OOM - Out of Memory, odcięcie sieci lub restart kontenera) w trakcie ruchu turystów, wszystkie widoki API bazujące na odczycie rankingu 100/n, kolorów mapy czy stanu profili zawiodą w całości. Użytkownik otrzyma błąd 500 lub "szarą mapę", a aplikacja stanie się bezużyteczna, mimo że główna baza danych (PostgreSQL) działa w 100% poprawnie.

**Action Items (Do wdrożenia w Fazy SRE / Produkcji):**
- [ ] Zmodyfikować warstwę zapytań (np. `ExploreMapUseCase` lub nowo powołane `QueryServices`), aby w przypadku błędu połączenia z buforem (`RedisConnectionError`) aplikacja "cicho" wracała do stanu domyślnego lub awaryjnie przeliczała podstawowe dane bezpośrednio z PostgreSQL (Graceful Degradation).
- [ ] Dodać zabezpieczenia bloku `try-except` w adapterze `DjangoCacheAdapter`, aby chronić wyższe warstwy przed padem usługi.

**Komentarz Architekta:**
Klasyczny błąd zaufania do infrastruktury w środowiskach rozproszonych. Każdy zewnętrzny klocek w Dockerze kiedyś padnie. Aplikacja powinna działać "wolniej, ale poprawnie" po awarii Cache'u, a nie wyłączać się całkowicie.

---

### [AUDYT-115] Opracowanie strategii awaryjnej i "Data Recovery" dla Użytkowników
**Obszar:** `Operacje / Wdrożenie (SRE)`  
**Priorytet:** `🟠 WYSOKI (Przed oficjalnym startem PROD)`  

**Diagnoza Audytora:** 
Raport uderza w brak jakiejkolwiek procedury operacyjnej dla obsługi tzw. "Awarii Klienta". System posiada doskonały `Runbook.md` dla dewelopera, ale brakuje w nim zdefiniowania procesu: co ma zrobić Administrator Systemu, jeśli turysta napisze maila "Usunąłem przez przypadek swój profil i straciłem odznaki, proszę o przywrócenie!", albo "Baza danych padła, musimy odtworzyć stan z wczoraj z S3".

**Action Items (Do wdrożenia PRZED wpuszczeniem użytkowników):**
- [ ] Zaktualizować lub stworzyć dokument `docs/ops/Disaster_Recovery_Plan.md`.
- [ ] Opisać krok po kroku komendy potrzebne do zrzutu i odtworzenia bazy PostGIS ze środowiska produkcyjnego używając wypracowanych w `ADR-021` kopii S3 (Konta Operatorskiego).
- [ ] Zdefiniować jasną politykę biznesową: czy przywracamy pojedyncze profile na żądanie (niezwykle kosztowne inżynieryjnie), czy odmawiamy ze względów bezpieczeństwa.

**Komentarz Architekta:**
Klasyczny przypadek przejścia z projektu "Programistycznego" na "Produkcyjny". Administratorzy muszą mieć pod ręką gotowe, przetestowane komendy Bash/SQL na wypadek kryzysu u turystów. Zabezpiecza nas to przed paniką.

---

### [AUDYT-116] Anemiczna Domena – Wyciek Logiki Biznesowej do Warstwy Aplikacji
**Obszar:** `Domena / Domain-Driven Design`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Audytor wyłapał fundamentalny rozjazd między filozofią DDD a obecną realizacją kodu (tzw. Anemic Domain Model). Czysta Domena (`domain/`) posiada zaledwie ~600 linii kodu i sprowadza się wyłącznie do mechanizmu `BadgeVersionDomain.evaluate()`. Pozostała, kluczowa logika biznesowa PTTK "wyciekła" do warstwy Aplikacji (Use Cases). Przykładowo:
1. Logika walidacji "Praw Nabytych" (Grandfather Clause) żyje obecnie w plikach orkiestratorów.
2. Zabezpieczenie limitów konta Freemium zlokalizowane jest wewnątrz `StartBadgeProgressUseCase`.
3. Walidacja bitemporalna (`T-01`) znajduje się wewnątrz pętli `BulkLogAscentsUseCase`.

**Action Items (Do wdrożenia w Fazy Refaktoryzacji Domeny):**
- [ ] Przenieść logikę oceny "Praw Nabytych" do nowej, Czystej Usługi Domenowej (np. `domain/services/grandfathering_service.py`).
- [ ] Zbudować agregat `TouristProfile` (w Czystej Domenie), do którego przeniesiona zostanie odpowiedzialność za weryfikację limitów subskrypcji.
- [ ] Oczyścić Use Case'y z warunkowych logik `if/else`, pozostawiając im wyłącznie odpowiedzialność za pobieranie z bazy, wywoływanie Czystej Domeny i zapis.

**Komentarz Architekta:**
Jest to klasyczne zjawisko "grubych orkiestratorów" powstające w pośpiechu budowy MVP. Wymaga jednego mocnego sprintu refaktoryzacyjnego, zanim kod z Use Case'ów stanie się zbyt skomplikowany do testowania.

---

### [AUDYT-117] Brak korelacji Logów (Request ID) między HTTP a Celery
**Obszar:** `Observability / Logi Asynchroniczne`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Nasz genialny system `RFC7807ErrorMiddleware` nadaje każdemu żądaniu HTTP unikalne `request_id`, które ląduje w logach. Jeśli jednak widok odpala operację asynchroniczną (np. przeliczanie punktów przez Celery), a ta operacja wybuchnie błędem w tle, logi Celery **nie zawierają** `request_id`. Uniemożliwia to powiązanie błędu asynchronicznego z turystą, który kliknął przycisk na stronie.

**Action Items (Do wdrożenia w Fazy SRE):**
- [ ] Zmodyfikować klasę `CeleryEventPublisher` lub adaptery asynchroniczne tak, aby "łapały" `request_id` z wątku HTTP i przekazywały go w `kwargs` wywoływanego zadania (Taska).
- [ ] Opcjonalnie wdrożyć bibliotekę OpenTelemetry, która robi to automatycznie (Distributed Tracing).

**Komentarz Architekta:**
Wspaniałe uderzenie. Rozproszony system bez skorelowanych logów to koszmar przy naprawianiu awarii na produkcji.

---

### [AUDYT-118] Fałszywy Pozytyw w punkcie końcowym `/health/`
**Obszar:** `Operacje / Healthchecks`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecny widok `/health/` w `config/urls.py` zwraca twarde `200 OK` od razu po zapytaniu. Load Balancer (lub Docker) uznają, że kontener działa. Jednakże, jeśli połączenie z bazą PostgreSQL ulegnie awarii, kontener nadal będzie zgłaszał `200 OK`, a wszyscy użytkownicy zaczną dostawać błędy 500.

**Action Items (Do wdrożenia przed uruchomieniem Load Balancera):**
- [ ] Rozbudować widok `/health/` (lub rozdzielić na `liveness` i `readiness`).
- [ ] Dodanie w widoku `health` prostej pętli odpytującej bazę danych (np. `django.db.connection.cursor().execute("SELECT 1")`) oraz Redis. Jeśli którekolwiek rzuci błędem, `/health/` musi zwrócić `503 Service Unavailable`.

**Komentarz Architekta:**
Klasyczny i groźny błąd (Zjawisko: *Zombie Container*). Ślepe poleganie na samym starcie frameworka nie gwarantuje gotowości biznesowej systemu.

---

### [AUDYT-119] Brak systemu śledzenia wyjątków (np. Sentry) na PROD
**Obszar:** `Diagnostyka / SRE`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecnie system został celowo zabezpieczony poprzez usunięcie *Stacktrace'ów* dla zapytań o statusie 500 w środowisku produkcyjnym (żółta strona z błędem Django jest ukryta, a błędy rzucane przez Loguru). O ile to dobrze dla bezpieczeństwa, administratorzy zostali całkowicie "oślepieni" i muszą logować się na maszyny po SSH, żeby przeczytać dzienniki w celu znalezienia pliku z błędem w kodzie.

**Action Items (Do wdrożenia PRZED testami E2E na PROD):**
- [ ] Zintegrować projekt z platformą Sentry (`sentry-sdk`) na poziomie `settings.py`.
- [ ] Wymusić logowanie wyjątków w `RFC7807ErrorMiddleware` bezpośrednio do Sentry, zanim zostaną one "spłaszczone" do komunikatu JSON 500 dla klienta.

**Komentarz Architekta:**
Nie polegamy na logach w konsoli do diagnozowania błędów na produkcji. Sentry to obecnie standard przemysłowy.

---

### [AUDYT-120] Brak audytowania zmian operacyjnych (Data Audit Trail)
**Obszar:** `Baza Danych / Compliance`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Jeśli administrator (lub złośliwy skrypt) w systemie testowym zmieni definicję regulaminu lub wiek turysty w `TouristProfile`, nie zostawi to w systemie żadnego śladu – nadpisany rekord nie ma historii wersji na poziomie relacyjnym. Rodzi to potężne problemy z rozstrzyganiem sporów (Dlaczego odznaka została cofnięta?).

**Action Items (Do wdrożenia w przyszłości):**
- [ ] Wdrożyć bibliotekę `django-simple-history` dla kluczowych modeli biznesowych (np. `UserBadgeProgress`, `TouristProfile`), która automatycznie archiwizuje i wiąże zmianę rekordu z użytkownikiem wykonującym operację (`history_user`).

**Komentarz Architekta:**
W MVP to niepotrzebny koszt optymalizacyjny, jednak z chwilą wejścia w produkcję i wpuszczenia moderatorów (Weryfikatorów PTTK) będzie to obligatoryjna warstwa zabezpieczająca (Non-Repudiation / Niezaprzeczalność).

---

### [AUDYT-119] Cykliczna zależność między `apps/` a `infrastructure/`
**Obszar:** `Architektura Heksagonalna / Granice Modułów`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Analiza statyczna importów wykazała pętlę zależności (Circular Dependency). Warstwa dostarczania (`apps/badges/models.py`) importuje bezpośrednio schemat z warstwy infrastruktury (`infrastructure/schemas/badge_rules_schema.py`), podczas gdy adaptery z `infrastructure/` importują modele i zadania z `apps/`. Łamie to reguły Enkapsulacji i zamienia modularny monolit w spaghetti.

**Action Items (Do wdrożenia w najbliższym sprincie refaktoryzacyjnym):**
- [X] Przeniesiono definicję `RULES_SCHEMA` z `infrastructure/schemas/` do `apps/badges/rules_schema.py` (AUDYT-085).
- [ ] Usunąć bezpośrednie importy z `apps/` wewnątrz `infrastructure/adapters/` (np. zastąpić bezpośrednie odwołania do `apps.badges.tasks` w `celery_event_publisher.py` przez wstrzykiwanie portów lub dynamiczny call) — DŁUG-004.
- [X] Konfiguracja `import-linter` w `.importlinter` ma kontrakt `hexagonal-layers` blokujący apps → infrastructure.

**Komentarz Architekta:**
To jest najpoważniejsze naruszenie granic heksagonalnych w całym kodzie. Modele Django w `apps/badges/models.py` powinny być "głupie" i nie wiedzieć nic o specyficznych schematach walidacyjnych formularzy Admina z infrastruktury. 

---

### [AUDYT-121] Nieszczelność lintera importów (Brak kontraktu dla `apps` ↔ `infrastructure`)
**Obszar:** `Architektura / CI/CD (Import Linter)`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Narzędzie `.importlinter` genialnie chroni warstwy `domain` i `application` przed wtargnięciem kodu z zewnątrz. Audytor jednak słusznie zauważył, że brakuje kontraktu chroniącego najsłabsze ogniwo: styk warstwy dostarczania (`apps/`) z warstwą adapterów (`infrastructure/`). Bez tego kontraktu łatwo dopuścić do zjawiska, w którym model Django importuje schemat lub logikę walidacji z głębi infrastruktury.

**Action Items (Do wdrożenia PRZEZ CIEBIE przed startem Playwright):**
- [X] Dodać do pliku `.importlinter` nowy blok kontraktu zakazujący importowania czegokolwiek z `infrastructure/` wewnątrz katalogu `apps/` (z ewentualnymi, twardo zdefiniowanymi wyjątkami dla wstrzykiwania `bootstrap` lub logów).
- [X] Dodać zasady ograniczające import z `apps/` wewnątrz `infrastructure/`.

**Komentarz Architekta:**
Złapano nas na połowicznym wdrożeniu Lintera. Zabezpieczyliśmy serce (Domenę), ale zapomnieliśmy ogrodzić murem przedpola.

---

### [AUDYT-122] Rozmycie Odpowiedzialności w Rejestracji Zależności (`container.py`)
**Obszar:** `Architektura / Bootstrap`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Plik `bootstrap/container.py` nosi znamiona "God Object" (obiekt boski), który wie o wszystkim w systemie. Gdy projekt urośnie z 14 Use Case'ów do 50, każda drobna zmiana w konstruktorze jakiejkolwiek usługi wymusi modyfikację tego jednego, potężnego pliku, co doprowadzi do "wąskiego gardła" (Bottleneck) przy pracy zespołowej i konfliktów w systemie kontroli wersji Git.

**Action Items (Do wdrożenia w Fazy Refaktoryzacji / Skalowania):**
- [ ] Zastosować wzorzec z podziałem rejestratorów (np. `Registry Modules`), gdzie każda aplikacja biznesowa (Słowniki PTTK, Profil Turysty, Geografia) rejestruje swoje Use Case'y w osobnym mini-kontenerze, a główny `container.py` jedynie składa je (komponuje) w całość.

**Komentarz Architekta:**
Zgodnie z naszymi poprzednimi wnioskami, podział monolitycznego kontenera to naturalny krok ewolucyjny, ale dla 14 Use Case'ów obecny, scentralizowany kontener gwarantuje 100% czytelności (Cohesion). Odkładamy na później.

---

### [AUDYT-123] Brak Tłumaczenia Wyjątków Infrastrukturalnych w Use Case'ach (Exception Leakage)
**Obszar:** `Aplikacja / Use Case / Exception Handling`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Zgodnie ze zdefiniowanym kontraktem w `docs/Manifest/16-error-boundary.md`, błędy infrastrukturalne (np. `OsmAdapterError`) rzucane przez Adaptery muszą zostać przechwycone przez Use Case i przetłumaczone na język biznesowy (`ApplicationException`).
Obecnie Use Case'y (np. `FetchOsmDataUseCase`, `LogAscentUseCase`) w ogóle nie posiadają bloków `try-except` dla błędów infrastruktury. Oznacza to, że gdy Overpass API nie zadziała, surowy błąd infrastruktury "przelatuje" prosto do kontrolerów API, wymuszając na widokach HTTP albo rzucenie błędu 500, albo łamanie zasad Architektury Heksagonalnej poprzez próbę zrozumienia błędów z dolnych warstw.

**Action Items (Do wdrożenia w Fazy Refaktoryzacji / SRE):**
- [ ] Dodać import `InfrastructureException` (lub dedykowanych klas np. `OsmAdapterError`) do Use Case'ów.
- [ ] Owijać wywołania adapterów w `try-except` na poziomie Use Case'a i rzucać błędy `ApplicationException` (np. `raise UseCaseError("Usługa mapowa jest obecnie niedostępna") from exc`).

**Komentarz Architekta:**
Klasyczny wyciek abstrakcji. Brak przechwytywania wyjątków to prosta droga do zasypania logów produkcyjnych (Sentry) błędami z surowym stosem SQL lub Timeoutów, z którymi warstwa sieciowa (API) nie wie co zrobić.

---

### [AUDYT-124] Utrata bezpieczeństwa typów: Słowniki zamiast Obiektów Wynikowych (Primitive Obsession)
**Obszar:** `Aplikacja / Czysta Domena`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Chociaż system używa rygorystycznie DTO Wejściowych (np. `AscentInputDTO`), to w kluczowych węzłach orkiestracji wynikowych zwraca luźne słowniki (`dict[str, Any]`). 
1. Use Case'y takie jak `VerifyBadgeUseCase`, `BulkLogAscentsUseCase` (Partial Success) czy `ExploreMapUseCase` zwracają nieustrukturyzowane słowniki. 
2. Adapter `OsmRepositoryPort.fetch_multiple_from_osm()` używa konstrukcji typu `dict[str, OsmNodeData]`.
Zwracanie słowników osłabia działanie narzędzia `Mypy` i ukrywa kształt odpowiedzi API przed przyszłymi deweloperami frontendu.

**Action Items (Do wdrożenia przed wersją 1.0):**
- [ ] Zaprojektować i wdrożyć obiekty `OutputDTO` (np. `VerifyBadgeResultDTO`, `BulkLogResultDTO`, `MapExploreResultDTO`).
- [ ] Podmienić typy zwracane w sygnaturach Use Case'ów i odpowiednio zaktualizować kontrolery API, by zwracały `result.model_dump()`.
- [X] (*Przypomnienie z AUDYT-105*): Wdrożyć `VerificationResult` dla samej Domeny.

**Komentarz Architekta:**
Zjawisko to nazywa się *Primitive Obsession* (Obsesja Typów Prostych). W fazie szybkiego dowożenia funkcji (Faza C) słowniki pozwalały na błyskawiczne renderowanie `JsonResponse`. Na dłuższą metę, aby dokumentacja API (np. Swagger/OpenAPI) generowała się automatycznie, wyjścia muszą być równie rygorystyczne co wejścia.


---

### [AUDYT-126] Niejawne mutowanie stanu w Leniwej Inicjalizacji (`_get_active_profile_id`)
**Obszar:** `Apps / Widoki HTML`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Funkcja `_get_active_profile_id(request)` uchodzi za *Getter* (funkcję odczytującą ID profilu z sesji). W praktyce, dla starych użytkowników bez profilu, funkcja ta wywołuje `TouristProfile.objects.create(...)`, wykonując potężny zapis do bazy danych (Side Effect). Wywołanie tego gettera w 15 różnych widokach HTML (w tym w czystym odczycie mapy) to "bomba z opóźnionym zapłonem".

**Action Items (Do wdrożenia w fazie stabilizacji):**
- [ ] Przenieść proces wymuszania założenia konta (Fallback) do dedykowanego Middleware'a (np. `EnsureTouristProfileMiddleware`) wywoływanego raz w cyklu życia żądania.
- [ ] Zredukować `_get_active_profile_id` do bezpiecznego i błyskawicznego `return request.session.get("active_profile_id")`.

**Komentarz Architekta:**
Wdrożyliśmy to celowo w Fazie C jako szybki ratunek dla "zagubionych profili" z dev-środowiska. Na dłuższą metę funkcja o nazwie `get_` nie ma prawa odpalać instrukcji `INSERT` w SQL.

---

### [AUDYT-127] Brak egzekwowania walidacji (C-01) przy operacjach masowych
**Obszar:** `Django / ORM`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Zabezpieczenie przed powstaniem "Pętli Klastrów" (Invariant C-01) zrealizowaliśmy poprzez nadpisanie metod `clean()` oraz `save()` w modelu `TouristObject`. Niestety, Django ORM wywołując instrukcje masowe (takie jak `TouristObject.objects.filter(...).update(...)` lub `bulk_create`) całkowicie ignoruje metody `save()` poszczególnych obiektów, przez co logika "Płaskiej Gwiazdy" może zostać złamana podczas masowych aktualizacji.

**Action Items (Do wdrożenia w przyszłości):**
- [ ] W plikach `AGENT_SPEC.md` i `EDGE_CASES.md` dodać twardy zakaz używania operacji `.update()` na polu `parent_object`.
- [ ] (Opcjonalnie) Przenieść walidację "Płaskiej Gwiazdy" bezpośrednio do bazy PostgreSQL jako funkcję `CONSTRAINT TRIGGER`.

**Komentarz Architekta:**
Bardzo głębokie zrozumienie ułomności frameworka (Active Record). W 99% przypadków łączymy klastry pojedynczo przez panel admina, więc ryzyko jest minimalne, ale luka techniczna istnieje.

---

### [AUDYT-128] Dekompozycja pliku modeli (`apps/badges/models.py`)
**Obszar:** `Django / ORM / Architektura Plików`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Plik `apps/badges/models.py` osiągnął rozmiar 750 linii i zawiera 17 modeli Django. Skupia on w sobie całkowicie różne byty: hierarchię geograficzną (6 poziomów regionów), definicje odznak, konfigurację OSM oraz obiekty turystyczne z ich cyklem życia. Stanowi to klasyczny antywzorzec "God File", drastycznie utrudniając nawigację po kodzie i przeglądy (Code Review).

**Action Items (Do wdrożenia w nadchodzącym sprincie):**
- [ ] Przekształcić plik `models.py` w moduł (utworzyć katalog `models/` z plikiem `__init__.py`).
- [ ] Wydzielić modele do logicznych plików (np. `region_models.py`, `badge_models.py`, `tourist_object_models.py`, `osm_models.py`).
- [ ] Zaktualizować importy w reszcie systemu.

**Komentarz Architekta:**
Bardzo prosta operacja, która radykalnie obniży "Złożoność Poznawczą" (Cognitive Load) u programistów wchodzących do projektu.

---

### [AUDYT-129] Dekompozycja panelu administracyjnego (`apps/badges/admin.py`)
**Obszar:** `Django Admin / Architektura Plików`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Plik `admin.py` posiada blisko 800 linii kodu. Poza samą definicją interfejsów (UI) zawiera on potężną logikę biznesową w postaci "Akcji Admina" (np. rozwiązywanie par klastrów, akceptacja zmian OSM). Zmiana logiki wyświetlania jednej tabeli naraża na konflikty scalania kod dla pozostałych 8 modeli.

**Action Items (Do wdrożenia w nadchodzącym sprincie):**
- [ ] Przekształcić plik `admin.py` w moduł (katalog `admin/` z `__init__.py`).
- [ ] Wydzielić klasy paneli do mniejszych plików (np. `badge_admin.py`, `tourist_object_admin.py`).

**Komentarz Architekta:**
Podobnie jak modele, panel administracyjny rozrósł się ponad miarę MVP. Czas go ustrukturyzować.

---

### [AUDYT-130] Zjawisko Rozproszonych Statusów (Status Scatter)
**Obszar:** `Słowniki / DRY`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
System cierpi na zjawisko re-definiowania tych samych pojęć w różnych warstwach (Magic Strings). Statusy, takie jak np. `COMPLETED` czy `WAITING_FOR_SEND`, pojawiają się jako:
1. `TextChoices` w modelach Django ORM.
2. Zwykłe stringi (ciągi znaków) w logice ewaluacji `BadgeVersionDomain`.
3. Słowniki w warstwie Aplikacji (`VALID_TRANSITIONS`).
Wymusza to pamiętanie o zmianie we wszystkich tych plikach w przypadku dodania nowego statusu.

**Action Items (Do wdrożenia w Fazy Optymalizacji):**
- [ ] Zbudować centralny plik słowników (Enums) dostępny dla całego systemu (np. `domain/enums.py` lub `shared_kernel`).
- [ ] Wykorzystać zdefiniowane Enumy w modelach Django, w Domenie i w warstwie Aplikacji, zastępując tzw. "Magic Strings".

**Komentarz Architekta:**
Świetna obserwacja. Pozwoli na wprowadzenie w 100% bezpiecznego typowania (Type Safety) na wartościach statusów i ochroni przed literówkami typu `"COMPLETE"`.

---

### [AUDYT-131] Redukcja Złożoności Metody Ewaluacji (`evaluate` w `BadgeVersionDomain`)
**Obszar:** `Domena / Clean Code`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Główna metoda weryfikująca odznaki (`BadgeVersionDomain.evaluate()`) urosła do 72 linii kodu i posiada cztery osobne odpowiedzialności:
1. Przestrzenne filtrowanie szczytów z puli.
2. Deduplikacja logów.
3. Wywoływanie reguł biznesowych (Strategie).
4. Ewaluacja postępu dla poszczególnych stopni (Tiers).
Łamie to zasadę SRP (Single Responsibility Principle) na poziomie metod.

**Action Items (Do wdrożenia w Fazy Refaktoryzacji Domeny):**
- [ ] Rozbić metodę `evaluate` na mniejsze, prywatne funkcje (np. `_filter_valid_ascents`, `_apply_business_rules`, `_evaluate_tiers`).
- [ ] Upewnić się, że główna metoda wywołuje jedynie te zgrabne funkcje, poprawiając jej czytelność i umożliwiając pisanie testów dla poszczególnych prywatnych kroków.

**Komentarz Architekta:**
Wspaniała sugestia z zakresu "Czystego Kodu" (Clean Code). Podział tej metody uspokoi lintery badające Złożoność Cyklomatyczną (Cyclomatic Complexity).

---

### [AUDYT-132] Hermetyzacja Logiki Praw Nabytych (Grandfather Clause)
**Obszar:** `Architektura / Domain-Driven Design`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Audytor wyłapał, że zasada "Praw Nabytych" (retroaktywne przyznawanie starego regulaminu) została zakodowana na "skróty" w dwóch osobnych Use Case'ach (`VerifyBadgeUseCase` oraz `StartBadgeProgressUseCase`). Koncept Praw Nabytych jest pojęciem z Czystej Domeny i powinien być tam wyizolowany, a nie symulowany w orkiestratorach.

**Action Items (Do wdrożenia w Fazy Ewolucji Domeny):**
- [ ] Stworzyć Usługę Domenową (Domain Service), np. `GrandfatheringService`, która hermetyzuje całą logikę wyboru najstarszego wejścia i decyduje o przypisaniu regulaminu.

**Komentarz Architekta:**
Jest to potwierdzenie i rozbudowanie wniosku z wcześniejszego audytu (AUDYT-116). Pokazuje, że "grube Use Case'y" to aktualnie nasz główny dług architektoniczny w warstwie Aplikacyjnej.

---

### [AUDYT-133] Walidacja Schematu (JSON Schema) w `verify_reference_data`
**Obszar:** `DataOps / CI/CD`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Obecny mechanizm weryfikacji snapshotów przed importem opiera się na prostym porównywaniu sum kontrolnych `sha256` w pliku `manifest.json`. Skrypt nie sprawdza jednak semantycznej struktury samych plików (np. czy w `03_badges.json.gz` ktoś nie zmienił zagnieżdżonego pola `rules` na pustą listę). Wpuszczenie zepsutego JSON-a do środowiska zniszczy `BadgeVersionDomain` podczas hydracji.

**Action Items (Do wdrożenia w potoku CI/CD):**
- [ ] Opracować pliki JSON Schema dla kluczowych danych referencyjnych (m.in. reguł odznak).
- [ ] Rozbudować skrypt `verify_reference_data.py`, by przeprowadzał walidację schematu (np. pakietem `jsonschema`) dla wgranych plików, jeszcze przed próbą załadowania ich do bazy przez `loaddata`.

**Komentarz Architekta:**
Kolejny poziom "Gatingu" (Zabezpieczeń). Jeśli Administrator wyeksportuje błędnie sformatowaną z poziomu panelu regułę PTTK, CI zablokuje Pull Requesta informując o rozjeździe schematu, zanim ten trafi na Pre-Prod.

---

### [AUDYT-134] Bezpieczeństwo migracji kluczy M2M (`dumpdata` z `--natural-foreign`)
**Obszar:** `DataOps / Eksport Danych`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecny skrypt `export_reference_data` korzysta ze standardowego wywołania `call_command("dumpdata", ... )`. Powoduje to zapisywanie w JSON-ach twardych kluczy numerycznych (ID) dla relacji, m.in. dla puli szczytów w odznakach. Jeśli na produkcji po długim czasie wgramy snapshot wyeksportowany z DEV, gdzie kolejność ID szczytów (Primary Keys) mogła ulec zmianie po czyszczeniu bazy, relacje w odznakach wskażą na niewłaściwe góry!

**Action Items (Do wdrożenia PRZED wejściem na Produkcję):**
- [ ] Zmodyfikować komendy w `export_reference_data.py`, dodając flagi `--natural-foreign` (i ew. `--natural-primary`).
- [ ] Zaktualizować modele referencyjne o menedżery obsługujące `get_by_natural_key` (np. `code` dla odznak lub kombinacja współrzędnych i nazwy dla szczytu).

**Komentarz Architekta:**
Wspaniałe wyłapanie klasycznego błędu `loaddata`. Obecnie nasz system działa, bo wszystkie środowiska startują od zera. Przy aktualizacjach działającej produkcji na przestrzeni lat, twarde ID to tykająca bomba.

---

### [AUDYT-135] Ochrona danych wrażliwych (Szyfrowanie Złotego Seta w Repozytorium)
**Obszar:** `Bezpieczeństwo / GitOps`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Snapshot `data/reference/` jest obecnie przechowywany w publicznym tekście (skompresowanym w GZIP). Jeśli do danych referencyjnych w przyszłości zostaną włączone klucze API dla organizatorów, e-maile kontaktowe oddziałów PTTK lub ukryte waypointy, ich zrzucenie w Plaintext JSON zagraża wyciekiem w systemie kontroli wersji.

**Action Items (Do wdrożenia w Fazy Security):**
- [ ] Przeanalizować, czy dane PTTK kiedykolwiek będą zawierać tajemnice PII.
- [ ] (Opcjonalnie) Wdrożyć mechanizm np. `SOPS` lub szyfrowanie przez klucz publiczny repozytorium (np. GPG) podczas eksportu, z deszyfracją na etapie `restore_reference_data`.

**Komentarz Architekta:**
Niski priorytet, ponieważ nasze obecne dane (Szczyty, Regiony i Regulaminy KGP) są w 100% danymi jawnymi (Open Data). Jednak w metodyce Enterprise takie zagrożenia odhacza się profilaktycznie.

---

### [AUDYT-136] Eliminacja "Magic Strings" i Konsolidacja Statusów (Enums)
**Obszar:** `Domena / Słowniki`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Stan odznaki (`NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`) oraz stan logistyczny (`WAITING_FOR_SEND`, `ALBUM` itp.) funkcjonują obecnie w kodzie jako zwykłe ciągi znaków (Magic Strings) i to w trzech różnych miejscach: jako `TextChoices` w modelach Django, jako stringi w agregacie `BadgeVersionDomain` oraz jako słownik przejść w `AdvanceLogisticStatusUseCase`. Zmiana nazwy jednego ze statusów wymusi jednoczesną edycję w wielu plikach.

**Action Items (Do wdrożenia w Fazy Refaktoryzacji):**
- [ ] Utworzyć centralny plik `domain/enums.py` (lub `shared_kernel/enums.py`) zawierający twardo typowane klasy `Enum` dla statusów biznesowych.
- [ ] Podmienić wywołania tekstowe w całej Czystej Domenie i Use Case'ach na odwołania do Enuma (np. `DomainStatus.COMPLETED.value`).
- [ ] Zmodyfikować modele w `apps/tourists/models.py`, by korzystały z centralnych Enumów jako `choices`.

**Komentarz Architekta:**
Wspaniałe wyłapanie braku (DRY - Don't Repeat Yourself) na poziomie definicji. W Czystej Architekturze Enumy domenowe to "złoty standard". Zlikwiduje to ryzyko literówek (Typo) na poziomie kompilacji.

---

### [AUDYT-137] Ujednolicenie schematu nazywania DTO
**Obszar:** `Aplikacja / DTO`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Obecne modele przepływu danych w katalogu `application/dto/` posiadają chaotyczne przyrostki, co utrudnia nowym programistom odgadywanie intencji klas. Przykłady: `AscentInputDTO`, `VerifyBadgeRequestDTO`, `GpxAnalysisResultDTO`, `AscentDTO`.

**Action Items (Do wdrożenia w wolnej chwili):**
- [ ] Zdefiniować i wpisać do `AGENT_SPEC.md` żelazną konwencję nazewniczą, np.:
  - `[Name]RequestDTO` – dla wszystkich danych wejściowych z API.
  - `[Name]ResponseDTO` – dla wszystkich danych wyjściowych z API.
  - `[Name]DomainDTO` – dla struktur używanych wyłącznie między Use Case a Repozytorium.
- [ ] Przemianować istniejące klasy (np. `AscentInputDTO` na `AscentRequestDTO`).

**Komentarz Architekta:**
Jest to czysty szlif inżynieryjny (Clean Code). Ujednolicenie konwencji przyspiesza pisanie kodu i zapobiega "pomyłkom w myśleniu" u AI.

---

### [AUDYT-138] Brak konsekwentnego zwracania identyfikatora z Use Case'ów
**Obszar:** `Aplikacja / Use Case`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Orkiestratory (Use Case'y) zwracają obecnie niespójne typy prymitywne w zależności od przypadku. Na przykład `LogAscentUseCase` zwraca `int` (ID logu), ale inne metody po zakończeniu operacji modyfikującej (Command) nie zwracają identyfikatora zasobu lub zwracają np. słownik. Zgodnie z dobrymi praktykami CQRS, komenda powinna z reguły nie zwracać niczego (`None`), a jeśli jest to komenda kreacyjna – powinna zwracać ustandaryzowany obiekt, np. `CreatedResourceDTO(id=...)`.

**Action Items (Do wdrożenia opcjonalnie):**
- [ ] Ustandaryzować wyjścia z "Command Use Cases" (zmieniających stan), aby zawsze zwracały spójny obiekt (np. id modyfikowanej lub utworzonej encji wewnątrz struktury DTO).

**Komentarz Architekta:**
Nieblokujące. Kwestia estetyki kontraktów API i ułatwienia pracy z GraphQL w przyszłości. 


---

### [AUDYT-141] Rozbieżność w nazewnictwie: Ascent (Domena) vs AscentLog (Infrastruktura)
**Obszar:** `Słownik (Ubiquitous Language) / Domena vs ORM`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Istnieje niepotrzebny dysonans poznawczy na styku Domeny i Bazy Danych. W Czystej Domenie oraz Value Objects wejście turysty nazywa się `Ascent`. Tymczasem w modelu Django ORM oraz portach nazywa się `AscentLog`. Programista wchodzący do projektu musi domyślać się (i tracić czas na weryfikację), czy `Ascent` i `AscentLog` to dokładnie ten sam koncept biznesowy, czy może dwa różne etapy tego samego zjawiska.

**Action Items (Do wdrożenia w wolnej chwili lub podczas migracji):**
- [ ] Zmienić nazwę modelu ORM z `AscentLog` na `AscentModel` (wzorem np. `BadgeVersionModel`), aby zachować spójność rdzenia nazwy `Ascent`.
- [ ] LUB zmienić nazwę Value Objectu w domenie na `AscentLog`, ujednolicając język powszechny (Ubiquitous Language) we wszystkich warstwach.

**Komentarz Architekta:**
Kwestia estetyki kodu i łatwości nawigacji (`Ctrl/Cmd + P` w edytorze kodu). Błędy nazewnicze zawsze potęgują czas wdrożenia nowego człowieka do zespołu.

---

### [AUDYT-142] Maska "Fail-Silently" w adapterze mapy (Pusty GeoJSON)
**Obszar:** `API / GIS / UX`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
W adapterze `DjangoMapRepository` (metoda `get_objects_along_line`) zaimplementowano ciche wyłapywanie wyjątków przy złączeniach przestrzennych: `except Exception: return []`. Jeśli baza PostGIS rzuci krytyczny błąd (np. brak pamięci przy łączeniu skomplikowanego wielokąta lub uszkodzona geometria GPX), adapter "cicho" połyka ten błąd i oddaje do Use Case'a pustą listę. Use Case przekazuje to do widoku, a turysta widzi komunikat: "Zapisano 0 szczytów" bez żadnej informacji o awarii.

**Action Items (Do wdrożenia w Fazy SRE):**
- [ ] Usunąć `except Exception` z warstwy GIS.
- [ ] Stworzyć nowy, dedykowany wyjątek domenowo-infrastrukturalny np. `SpatialCalculationError` (dziedziczący po `ApplicationException`).
- [ ] Pozwolić błędowi wypłynąć do widoku API, by wyświetlił turyście komunikat 500 lub 422: "Błąd podczas obliczeń przestrzennych trasy".

**Komentarz Architekta:**
Złapano nas na tzw. Anti-Pattern: *Swallowing Exceptions*. Ciche błędy przestrzenne zamaskują nam poważne awarie infrastruktury PostGIS na produkcji. 

---

### [AUDYT-144] Ograniczenie Anemicznego Modelu Domeny (Domain Enrichment)
**Obszar:** `Domena / Architektura`  
**Priorytet:** `🟡 ŚREDNI (Długoterminowa Inwestycja)`  

**Diagnoza Audytora:** 
Obecnie warstwa `domain/` to głównie silnik sprawdzania reguł (`BadgeVersionDomain.evaluate()`). Obiekty takie jak `TouristProfile` czy `AscentLog` żyją tylko w infrastrukturze jako modele Django i są podawane do Use Case'ów jako zwykłe struktury DTO (Pydantic). Sprawia to, że Use Case'y muszą zarządzać logiką np. Praw Nabytych lub walidacji bitemporalnej. W dojrzałym modelu DDD agregat (np. `TouristProfile`) powinien sam w sobie posiadać zachowania biznesowe (np. `start_new_badge_progress()`).

**Action Items (Do wdrożenia ewolucyjnie):**
- [ ] Zaplanować serię sesji refaktoryzacyjnych przenoszących logikę biznesową z Use Case'ów do nowych encji domenowych (`TouristProfileDomain`, `AscentDomain`).
- [ ] Opracować Serwisy Domenowe (Domain Services) dla złożonych procesów, jak np. wyliczanie Praw Nabytych.

**Komentarz Architekta:**
Wspaniała definicja "Strategic Investment". To nie jest błąd systemu, ale raczej ścieżka wejścia na wyższy poziom dojrzałości, kiedy aplikacja osiągnie odpowiednią złożoność i stabilność operacyjną.

---

### [AUDYT-145] Deklaracja Stref Ochronnych (Obszary Wolne od Zmian)
**Obszar:** `Governance / Code Quality`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
W ferworze refaktoryzacji istnieje ryzyko zepsucia dobrze zaprojektowanych komponentów. Audytor zidentyfikował 6 obszarów kodu, które są "wzorcowe", doskonale testowane i spełniają swoją funkcję bez narzutu długu technicznego. Naruszenie tych stref niosłoby za sobą nieuzasadnione ryzyko regresji.

**Action Items (Do wdrożenia w komunikacji):**
- [ ] Dopisać notatkę do `AGENT_SPEC.md` lub `ARCHITECTURE.md` (sekcja *Granice Systemu*) z jednoznacznym zakazem nieuzasadnionych modyfikacji w strefach:
  - `domain/rules/badge_rules.py` (Wzorzec Strategii jest czysty i zoptymalizowany).
  - `application/dto/` oraz `application/ports/` (Stabilne, proste kontrakty i walidacja).
  - `infrastructure/adapters/django_uow.py` (Minimalistyczne owinięcie w `transaction.atomic`).

**Komentarz Architekta:**
Ważna wskazówka do zarządzania zespołem (i agentami AI). W architekturze heksagonalnej stabilne porty i proste reguły to fundament – ich ruszanie bez powodu to po prostu "kręcenie się w kółko" (Churn).

---

### [AUDYT-146] Sformalizowanie Instrukcji Wdrażania Local Runnera (Self-Hosted)
**Obszar:** `DevOps / Dokumentacja`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Architekta:** 
W odpowiedzi na awarię chmury GitHub skonfigurowano lokalnego runnera CI/CD na środowisku developerskim. Proces ten wymagał specyficznych komend bezpieczeństwa (izolacja konta systemowego Linux, nadanie uprawnień do grupy `docker`, instalacja demona `systemd`). Obecnie wiedza ta istnieje tylko w logach konwersacji, co uniemożliwi szybkie odtworzenie tej infrastruktury w przyszłości (np. przy zakupie dedykowanego serwera on-premise).

**Action Items (Do wdrożenia w wolnej chwili):**
- [ ] Zaktualizować plik `docs/RUNBOOK.md` (Sekcja 9: Plan Awaryjny). Wkleić tam dokładne komendy z naszej historii: `useradd -m github-runner`, `usermod -aG docker github-runner` oraz proces używania `sudo -u github-runner`.

**Komentarz Architekta:**
Wiedza operacyjna (Tribal Knowledge) musi zostać zmaterializowana w kodzie Markdown. To ochroni nas przed przestojami.

---

### [AUDYT-147] Wdrożenie mechanizmu "Garbage Collection" dla Self-Hosted Runnera
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🟠 WYSOKI (Zapobieganie awariom dysku)`  

**Diagnoza Architekta:** 
W chmurze GitHub Actions każda maszyna po wykonaniu testu ulega całkowitej destrukcji (Ephemeral VM). W przypadku naszego nowego, fizycznego Self-Hosted Runnera, działającego na komputerze PC/VM, przerywane potoki testowe lub nieudane kompilacje zaczną gromadzić wiszące warstwy obrazów Dockera (Dangling Images) i osierocone wolumeny z prefiksem `ci-`. Z czasem doprowadzi to do błędu `No space left on device`, który zablokuje i środowisko developerskie, i potoki CI.

**Action Items (Do wdrożenia przed intensywnymi testami):**
- [ ] Dodać do pliku `.github/workflows/ci.yml` nowy krok (wykonywany warunkowo na końcu, lub za pomocą Crontaba na maszynie hosta): `docker system prune -a -f --volumes --filter "until=24h"`.
- [ ] Upewnić się, że mechanizm ten nie skasuje przypadkiem lokalnych obrazów deweloperskich (użycie bezpiecznych filtrów).

**Komentarz Architekta:**
Klasyczny błąd przejścia z chmury na własny sprzęt. Brak automatycznego sprzątania (Garbage Collection) to gwarantowana awaria po 2-3 tygodniach intensywnego kodowania.

---

### [AUDYT-148] Optymalizacja zliczania Coverage dla testów Hypothesis
**Obszar:** Testy / CI  
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Architekta:**
Wdrożenie narzędzia Hypothesis (Property-Based Testing) zaowocowało dopisaniem blisko setki potężnych testów granicznych dla Czystej Domeny (test_domain_hypothesis.py). Jednakże natura testów generatywnych powoduje, że czasem uderzają one wielokrotnie w te same ścieżki kodu, sztucznie zaniżając procentowy wynik Coverage (pokrycia) w porównaniu do testów "example-based". Wyłączenie liczenia coverage flagą `--no-cov` dla tych testów to dobry pierwszy krok, ale docelowo utrudnia śledzenie ogólnej kondycji Domeny.

**Action Items (Do wdrożenia w Fazy Utrzymaniowej):**
- [ ] Zintegrować raporty coverage z Hypothesis do głównego raportu `pytest-cov`, oznaczając odpowiednio markery w pliku `pyproject.toml`.
- [ ] Zweryfikować, czy granica `fail-under=80` wymaga korekty przy nowej strukturze testów fuzingowych.

**Komentarz Architekta:**
Wspaniała inżynieria testów. Domena jest teraz odporna na błędy matematyczne, musimy tylko upewnić się, że statystyki CI poprawnie to odzwierciedlają.

---

### [AUDYT-149] Brak testu uwierzytelniania w Playwright (Logowanie UI)
**Obszar:** Testy E2E / Playwright  
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Architekta:**
Posiadamy ponad 20 działających scenariuszy E2E (nawigacja, profile, katalog, rankingi). Znakomicie omijamy logowanie za pomocą mechanizmu `create_test_session` (Bypass Auth w `conftest.py`). Brakuje jednak choćby jednego "prawdziwego" testu, który fizycznie wchodzi na `/accounts/login/` i weryfikuje UI procesu logowania Google OAuth (np. czy przycisk jest widoczny, czy przekierowuje do poprawnego dostawcy).

**Action Items (Do wdrożenia w obecnym Sprincie QA):**
- [ ] Napisać test E2E używający "czystego" kontekstu przeglądarki (bez wstrzykiwania ciasteczka).
- [ ] Zweryfikować, że strona logowania nie zawiera "nagiego HTML-a" i odpowiednio kieruje niezalogowanych turystów.

**Komentarz Architekta:**
Bypass jest świetny do testowania funkcji biznesowych, ale sam proces logowania (Drzwi Wejściowe) musi mieć swojego zrobotyzowanego strażnika.

---

### [AUDYT-150] Potencjalny wyciek danych w logach `scripts/e2e-run.sh`
**Obszar:** Skrypty Wdrożeniowe / Bezpieczeństwo  
**Priorytet:** `🟢 NISKI`

**Diagnoza Architekta:**
Nasz nowy, genialny wrapper `e2e-run.sh` buduje środowisko, tworzy admina i ładuje dane referencyjne. Często w tego typu skryptach uciekamy się do logowania parametrów (np. hasła tworzonego konta testowego lub tokenów do API).

**Action Items (Do weryfikacji):**
- [ ] Upewnić się, że w logach konsolowych (`stdout/stderr`) skryptu `e2e-run.sh` oraz w logach GitHub Actions dla tego zadania nigdy nie są wypisywane gołym tekstem wartości zmiennych środowiskowych z `.env` (szczególnie `DJANGO_SECRET_KEY` i tokeny wstrzykiwane do Playwrighta).

**Komentarz Architekta:**
Narzędzia CI/CD (takie jak GitHub Actions) potrafią automatycznie maskować sekrety (wstawiając `***`), ale przy lokalnym uruchamianiu `make e2e` na komputerze programisty ekran logów powinien pozostać sterylny.

---

### [AUDYT-151] Monitorowanie Dysku (Disk Space) na Self-Hosted Runnerze
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🟠 WYSOKI (Zapobieganie awariom dysku)`  

**Diagnoza Architekta:** 
Twój komputer to teraz serwer CI/CD. Chociaż skrypty sprzątają po sobie (`down -v`), nieudane testy (np. ubite w połowie przez błąd kodu) zostawią osierocone wolumeny i obrazy Dockera. Za miesiąc skończy Ci się miejsce na dysku.

**Action Items (Do wdrożenia przed intensywnymi testami):**
- [ ] Dodać do systemu monitoringu alert na maszynie Self-Hosted Runnera, który wyzwala się przy zajętości dysku > 80%.
- [ ] Przygotować jednorazowy skrypt czyszczący (`docker system prune -a -f --volumes --filter "until=24h"`), który można uruchomić ręcznie, jeśli alert się触发.
- [ ] Rozważyć dodanie automatycznego crontaba na maszynie hosta, który wykonuje `docker system prune` co 24h, ale tylko jeśli nie ma aktualnie uruchomionych żadnych kontenerów developerskich.

**Komentarz Architekta:**
W chmurze AWS/GitHub maszyny są efemeryczne i znikają po zakończeniu testu. Na fizycznym sprzęcie musisz sam zarządzać cyklem życia artefaktów. Brak monitorowania dysku to gwarantowana awaria, która zatrzyma cały zespół.

---

### [AUDYT-154] Utrzymanie i konserwacja potoku CodeQL
**Obszar:** `DevSecOps / CI/CD`  
**Priorytet:** `🟢 NISKI (Konserwacja)`  

**Diagnoza Architekta:** 
Z sukcesem wdrożono potok semantycznej analizy kodu (CodeQL) na Self-Hosted Runnerze z wyśmienitym czasem wykonania (1:22s). Posiada on jednak specyficzne wymagania operacyjne uodparniające go na awarie: wymóg identyczności kluczy SHA dla kroków `init` i `analyze` oraz wymóg `build-mode: none` dla projektów opartych na języku Python. 

**Action Items (Do pilnowania przy przyszłych aktualizacjach):**
- [ ] Przy ewentualnych aktualizacjach wersji narzędzia CodeQL (np. z `v4.37.3` na `v5.x`), programista ma bezwzględny obowiązek upewnić się, że zaktualizował ten sam Hash (SHA) w *każdym* kroku potoku wewnątrz pliku YAML.
- [ ] Zignorować ewentualne ostrzeżenia deprecjacji ze strony środowisk `Node` w kroku `checkout`, faworyzując niezmienność i bezpieczeństwo przypiętych wersji (Pinning) nad nowości.

**Komentarz Architekta:**
System DevSecOps osiągnął pełną dojrzałość. Posiadamy analizę statyczną (Ruff, Mypy), architektoniczną (Import Linter), bezpieczeństwa tekstu (Semgrep) oraz analizę przepływów wektorów ataku (CodeQL).

---

## 🟢 ZAKOŃCZONE (Archiwum - Historyczny Dług Techniczny)

> Poniższe zadania zostały w pełni zrealizowane i wdrożone w kodzie. Służą jako ślad audytowy (Audit Trail) i dokumentacja historyczna projektu.

<details>
<summary><b>Kliknij, aby rozwinąć historię zrealizowanych zadań...</b></summary>

---

### [AUDYT-001] Naprawa składni Pythona i kolejności argumentów Exception Handlera
**Obszar:** `API / Views`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
W widoku `BadgeLogisticsView` pozostała składnia Pythona 2 (`except A, B:`). Dodatkowo w 4 miejscach w `views.py` argumenty do helpera `_handle_application_exception` są przekazywane w odwrotnej kolejności (`exc, request.path` zamiast `request, exc`), co skutkuje błędem 500 przy każdej odmowie domenowej.

**Action Items (Do wdrożenia):**
- [X] Poprawić składnię na `except (json.JSONDecodeError, ValueError):` w `BadgeLogisticsView`.
- [X] Zmienić kolejność argumentów na `(request, exc)` we wszystkich wywołaniach w `views.py`.
- [X] Dodać pole `request_id` (pobierane z atrybutów request) do słownika zwracanego w funkcji `_problem_detail` w `views.py`.

**Komentarz Architekta:**
Klasyczny dług technologiczny po szybkiej refaktoryzacji widoków API. Do naprawy w jednym sprincie.

---

### [AUDYT-002] Rozbicie "God Class" adaptera turysty na dedykowane repozytoria
**Obszar:** `Infrastruktura / Persistence`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
`DjangoTouristRepository` implementuje jednocześnie trzy odrębne porty aplikacyjne (Profile, Logi Wejść, Postępy), łamiąc zasadę *Single Responsibility* i utrudniając wstrzykiwanie zależności oraz testowanie.

**Action Items (Do wdrożenia):**
- [X] Rozbić klasę `DjangoTouristRepository` na trzy mniejsze adaptery (`DjangoTouristProfileRepository`, `DjangoAscentLogRepository`, `DjangoUserProgressRepository`).
- [X] Zaktualizować rejestrację adapterów w `bootstrap/container.py`.
- [X] Usunąć martwy kod po atrybucie `request.profile.id` w widoku `BadgeLogisticsView` na rzecz poprawnego wzorca z sesją.

**Komentarz Architekta:**
Zgodne z kontraktem czystości adapterów. Konieczne przed wejściem w rozwój modułów społecznościowych (Faza D).

---

### [AUDYT-004] Wyciek architektury: Brakująca wiedza o progach wielostopniowych
**Obszar:** `Infrastruktura / Adaptery`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
Podczas hydracji definicji odznaki z bazy danych, wartość progu zaliczeniowego `required_count` była sztucznie obliczana jako długość puli (`len(pool_peaks)`) na poziomie Wersji. Mechanizm ten psuł odznaki wielostopniowe, gdzie właściwy próg przypisany jest do konkretnego `BadgeTier` (Stopnia).

**Action Items (Do wdrożenia):**
- [X] Przenieść progi liczbowe z Wersji Odznaki do poszczególnych Stopni (`BadgeTierDomain`).
- [X] Zmodyfikować logikę oceny `evaluate()` w Domenie, by weryfikowała postęp względem tablicy wstrzykniętych Stopni (Tiers).
- [X] Zamknąć opisany dług techniczny `TD-03` w dokumentacji.

**Wdrożenie:**
- Domena (`BadgeVersionDomain`, `BadgeTierDomain`) posiada pole `required_count` na każdym Stopniu; `evaluate()` (linia 76) używa `t.required_count`.
- Adapter (`_hydrate_version`) odczytuje `BadgeTierModel.required_peaks_count`, fallback `len(pool_peaks)` tylko dla `None`.
- Testy: `test_hydrates_multi_tier_with_distinct_thresholds`, `test_hydrates_fallback_to_pool_size_when_required_peaks_count_is_null`.

---

### [AUDYT-005] Kaskadowe wygnanie ducha "VerificationRequest"
**Obszar:** `Dokumentacja / Architektura`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Fundamentalna sprzeczność architektoniczna. `ADR-014` jasno definiuje porzucenie agregatu `VerificationRequest` (oraz `UserBooklet`) na rzecz zintegrowanego modelu `UserBadgeProgress` i Osobistego Kanbana. Tymczasem pliki `Scenarios.md`, `Invariants.md` (S-03, S-04) oraz `User Stories.md` (US-C05) wciąż traktują ten usunięty agregat jako istniejący.

**Action Items (Do wdrożenia):**
- [X] Oczyścić `INVARIANTS.md`: Usunąć wzmianki o `VerificationRequest` w opisie S-03 i S-04.
- [X] Oczyścić `Scenarios.md`: Zaktualizować SCN-011 i usunąć wymóg wgrania `UserBooklet`.
- [X] Oczyścić `User Stories.md`: Usunąć z US-C05 wzmiankę o `VerificationRequest`.

**Komentarz Architekta:**
Klasyczny dług dokumentacyjny po podjęciu kluczowej decyzji (ADR-014). Niespójność ta może spowodować, że nowy programista zacznie budować nieistniejące tabele w bazie.

---

### [AUDYT-006] Czyszczenie `SYSTEM_PROMPT.md` z nieaktualnych długów i `ActivityType`
**Obszar:** `Dokumentacja / GenAI Context`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Plik `SYSTEM_PROMPT.md` to najważniejszy wektor informacyjny dla agentów AI. Obecnie wprowadza ich w błąd, wymieniając długi TD-01, TD-02, TD-03 jako "aktywne", podczas gdy `CHANGELOG.md` oficjalnie potwierdza ich spłatę. Dodatkowo prompt i `GLOSSARY.md` nadal wmawiają agentowi istnienie `ActivityType` (HIKING), co zostało brutalnie wycięte jako YAGNI.

**Action Items (Do wdrożenia):**
- [X] Wyczyścić tabelę "Znane długi techniczne" w `SYSTEM_PROMPT.md` (zostawić adnotację "Wszystkie spłacone").
- [X] Usunąć `activity / HIKING` z definicji `Ascent` w `SYSTEM_PROMPT.md` i `GLOSSARY.md`.
- [X] Ujednolicić relację w `User Stories.md` (US-C01): zmienić `OneToOneField` na `ForeignKey (1:N)` zgodnie z wprowadzonym Modelem Rodzinnym.

**Komentarz Architekta:**
Przestarzały System Prompt to gwarancja "halucynacji" AI w kolejnych sprintach. To zadanie ma absolutny, najwyższy priorytet przed dopuszczeniem jakiegokolwiek bota do kodu.

---

### [AUDYT-007] Uporządkowanie chaosu w `Edge Cases.md` i `User Stories.md`
**Obszar:** `Dokumentacja`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Przypadki brzegowe EC-035, EC-036, EC-037 zostały omyłkowo wklejone przez człowieka do pliku `User Stories.md` zamiast do `Edge Cases.md`. Ponadto w `Edge Cases.md` występuje wyciek moich (AI) instrukcji redakcyjnych ("Popraw fragment pobierający stopnie...") oraz zduplikowana i przerwana numeracja (np. podwójne EC-040, luki).

**Action Items (Do wdrożenia):**
- [X] Przenieść EC-035, EC-036, EC-037 z pliku `User Stories.md` do `Edge Cases.md`.
- [X] Usunąć wyciek tekstu instrukcji w okolicach EC-003 / EC-010.
- [X] Zreindeksować (przenumerować) przypadki brzegowe, aby wyeliminować duplikaty (EC-040, EC-044) i usunąć pustą zawartość tabel/komórek.

**Komentarz Architekta:**
Czysto redakcyjny bałagan powstały przy masowym przeklejaniu Markdowna z czatu do plików. Zmniejsza to zaufanie inżynierów do dokumentacji.

---

### [AUDYT-009] Usunięcie "śmieci" z Manifestów szablonowych
**Obszar:** `Manifesty / Narzędzia`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Plik `00-index.md` (lub podobny rejestr portów) oraz `06-documentation-contract.md` zawierają odniesienia do projektów `blood_pressure_dashboard`, `GTD_Planner` i folderów `docs_sphinx/`. 

**Action Items (Do wdrożenia):**
- [X] Przejrzeć katalog `docs/Manifest/` i usunąć wszelkie odniesienia do zewnętrznych, starych projektów.
- [X] Dopasować nazwy weryfikowanych plików (np. `Data Flow Diagram.md` zamiast `DATAFLOW.md`), aby linter dokumentacji nie zgłaszał fałszywych błędów o brakujących plikach.

**Komentarz Architekta:**
To po prostu pozostałości po szablonach korporacyjnych (Boilerplates), które użyliśmy do postawienia struktury. Nie wpływa to na kod, ale psuje czytelność.

---

### [AUDYT-010] SANITY CHECK: Weryfikacja pominiętego kodu
**Obszar:** `Kod Źródłowy / IDE`  
**Priorytet:** `🔴 KRYTYCZNY` (Dla Programisty)

**Diagnoza Audytora:** 
Audytor wykrył w bazie kodu błędy, które na etapie czatu zostały już wspólnie naprawione (np. stary `except json.JSONDecodeError, ValueError:` w `views.py`, brak pobierania profilu z sesji w widokach, odwrócone argumenty w wyjątku oraz brak pola `valid_to` w repozytorium odznak).

**Action Items (Do wdrożenia PRZEZ CIEBIE w IDE):**
- [X] Sprawdź plik `apps/api/views.py`: Upewnij się, że nie ma tam składni Pythona 2.
- [X] Sprawdź ten sam plik: Upewnij się, że helper to `_handle_application_exception(request, exc)`, a wywołania mają właściwą kolejność.
- [X] Sprawdź w widokach: Upewnij się, że nigdzie nie używasz `request.profile.id` (zamienić na odczyt z `request.session`).
- [X] Sprawdź `infrastructure/adapters/persistence/django_badge_repo.py`: Upewnij się, że metoda `get_latest_badge_version` posiada zabezpieczenie `Q(valid_to__isnull=True) | Q(valid_to__gte=...)`.

**Komentarz Architekta:**
Nie generujemy na to nowego kodu. Musisz upewnić się, że nie pominąłeś paczek aktualizacyjnych z poprzednich konwersacji podczas wklejania do swojego IDE, lub czy stare pliki nie nadpisały Ci się przypadkowo z githa.

---

### [AUDYT-011] Weryfikacja przepływu autoryzacji w API (IDOR i RFC 7807)
**Obszar:** `API / Views`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Plik `apps/api/views.py` stanowi główną linię obrony systemu. Audytor zdefiniował go jako obszar najwyższego ryzyka (P0), nakazując weryfikację tego, czy wszystkie 9 widoków poprawnie korzysta z mechanizmów zabezpieczających (IDOR, omijanie `request.user_id` na rzecz profilu z sesji) oraz czy każdy błąd przepinany jest przez standard RFC 7807 z dołączonym `request_id`.

**Action Items (Do wdrożenia):**
- [X] Wykonać ręczny przegląd kodu wszystkich klas w `apps/api/views.py`.
- [X] Upewnić się, że `_problem_detail` generuje `request_id` we wszystkich miejscach (Zgodnie z poprawką z AUDYT-001).
- [X] Wprowadzić testy automatyczne w `tests/apps/api/test_integration.py` potwierdzające rzucanie kodów 4xx przy próbach manipulacji danymi obcego użytkownika.

**Komentarz Architekta:**
Większość z tych zabezpieczeń wprowadziliśmy już we wczorajszym sprincie, zastępując djangowe dekoratory własnym helperem `_require_auth`. Wymaga to jednak ostatecznego przeglądu (Sanity Check) kodu testów.

---

### [AUDYT-012] Sanity Check: Prawa Nabyte i Cinderella Bug
**Obszar:** `Infrastructure / Badge Repo`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Audytor wytypował plik `infrastructure/adapters/persistence/django_badge_repo.py` jako ryzykowny (P1) ze względu na hydrację reguł z pola JSONB do obiektów Czystej Domeny oraz problem "Cinderella Bug" (EC-068), który znikał z czasem (brak obsługi pola `valid_to`).

**Action Items (Do wdrożenia PRZEZ CIEBIE w IDE):**
- [X] Sprawdzić implementację `get_latest_badge_version` i `get_version_id_for_date`. Upewnić się, że obie metody posiadają warunek logiczny chroniący przed błędem upływu dnia (np. `Q(valid_to__isnull=True) | Q(valid_to__gte=target_date)`).

**Komentarz Architekta:**
Zastosowaliśmy to rozwiązanie podczas incydentu "Znikających Szczytów o Północy", ale warto sprawdzić, czy zmiana na 100% nie została cofnięta przez przypadek przy kopiowaniu plików.

---

### [AUDYT-014] Ominięcie architektury w widokach API (Direct ORM Usage)
**Obszar:** `API / Hexagonal Architecture`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widoki `ProfileSettingsView` oraz `NearbyObjectsView` w `apps/api/views.py` łamią podstawową zasadę Czystej Architektury. Zawierają one bezpośrednie wywołania modeli Django (ORM) takie jak `.save()`, `get_object_or_404` czy zapytania przestrzenne GIS, omijając całkowicie warstwę Aplikacji (Use Cases) oraz Porty.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Utworzyć `UpdateProfileUseCase` i DTO aktualizacji profilu w warstwie Aplikacji.
- [X] Zmodyfikować `ProfileSettingsView`, by wywoływał nowy Use Case przez Kontener DI, zamiast bezpośrednio zapisywać dane w bazie.
- [X] Przenieść zapytanie przestrzenne (`ST_DWithin`) z `NearbyObjectsView` do adaptera `DjangoMapRepository` i wywoływać je przez port.
- [X] Dodać regułę do lintera `audit_contracts.py` zabraniającą importu `apps.badges.models` wewnątrz `apps/api/views.py`.

**Komentarz Architekta:**
Klasyczny wyciek logiki do kontrolerów powstały podczas szybkiego dowożenia funkcji Fazy C. Jest to bardzo szkodliwe dla izolacji testów i musi zostać wyczyszczone jako priorytet przed rozwojem aplikacji.

---

### [AUDYT-017] Duplikacja logiki weryfikacji bitemporalnej
**Obszar:** `Aplikacja / Use Case`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Zasada bitemporalności (T-01, czyli sprawdzanie `existence_start` i `existence_end` obiektu) była zaimplementowana dwukrotnie: w `LogAscentUseCase` oraz w pętli dla `BulkLogAscentsUseCase`.

**Rozwiązanie:**
- [X] Utworzono `BitemporalValidationService` (`application/services/bitemporal_validation_service.py`) jako serwis aplikacyjny.
- [X] `LogAscentUseCase.execute` używa `validate_single(peak_id, ascent_date)`.
- [X] `BulkLogAscentsUseCase.execute` używa `validate_batch(ascents)`.
- [X] Serwis wstrzyknięty do obu use case'ów w `bootstrap/container.py`.
- [X] `make check` zielone, 816 testów pass.

**Uzasadnienie decyzji:**
Serwis aplikacyjny (nie domenowy), bo zależy od `AscentLogRepositoryPort` (port aplikacyjny). Logika T-01/T-03 nie jest encją domenową — to invariants orkiestracji.

**Komentarz Architekta:**
Wyeliminowano duplikację DRY. Logika T-01/T-03 teraz w jednym miejscu — `BitemporalValidationService`.

---

### [AUDYT-018] Niespójna hierarchia i wykorzystanie wyjątków `ConflictError`
**Obszar:** `Domena / Wyjątki`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Wyjątek `ConflictError` był używany do dwóch różnych celów: (1) duplikaty danych D-04 (Idempotentność), (2) nielegalne przejścia stanu w Kanban FSM (S-03).

**Rozwiązanie:**
- [X] Wprowadzono `IllegalStateTransitionError` jako subklasę `ConflictError` w `application/exceptions.py` (zgodnie z `docs/Error Handling.md` hierarchią).
- [X] `advance_logistic_status.py` używa `IllegalStateTransitionError` dla naruszeń FSM (S-03).
- [X] `ConflictError` ograniczono do dokumentacji do duplikatów D-04.
- [X] `apps/api/views.py` loguje `IllegalStateTransitionError` jako `invalid-state-transition` (409, typ `/errors/invalid-state-transition`), `ConflictError` jako `conflict`.
- [X] Test `test_patch_conflict_returns_409` aktualizuje do `IllegalStateTransitionError`.
- [X] `make check` zielone, 816 testów pass.

**Uzasadnienie decyzji:**
Subklasa zachowuje backward-compat (`isinstance(exc, ConflictError)` → 409). Nazwa precyzyjniej opisuje przyczynę — lepsza Traceability.

**Komentarz Architekta:**
`ConflictError` → wyłącznie Idempotentność D-04. `IllegalStateTransitionError` → FSM Kanban.

---

### [AUDYT-020] Brakujące Testy Integracyjne (PostGIS i Restore Data)
**Obszar:** `Testy Integracyjne / Infrastruktura`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Zgodnie z kontraktem, testy integracyjne powinny sprawdzać prawdziwą bazę. Tymczasem nasze repozytoria (np. `django_map_repo.py`) opierają się na mockach (Monkeypatching `TouristObject.objects.filter`), co całkowicie ukrywa błędy w funkcjach `ST_DWithin` czy złączeniach CQRS. Brakuje również bezwzględnie wymaganego testu na idempotentność komendy `restore_reference_data` (podwójne wywołanie polecenia nie może nadpisać danych). Największy adapter systemu – `DjangoTouristRepository` – ma pusty plik testowy (`0 bajtów`).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Napisać prawdziwe testy bazodanowe (z użyciem znacznika `@pytest.mark.django_db`) dla `DjangoMapRepository` i `DjangoTouristRepository`.
- [X] Napisać test integracyjny weryfikujący podwójne odpalenie komendy `restore_reference_data`.
- [X] Usunąć sztuczne mocki na obiektach ORM z obecnych plików w katalogu `tests/infrastructure/adapters/persistence/`.

**Komentarz Architekta:**
Mockowanie ORM to antywzorzec. Przebudujemy testy infrastruktury tak, aby uderzały w pustą, tymczasową bazę generowaną przez pytest-django. To uleczy nasz system i zmyje winę "fałszywych testów".

---

### [AUDYT-021] Niestabilność Czasowa Testów (Flaky Tests)
**Obszar:** `Testy Jednostkowe / Maintainability`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
`date.today()` / `datetime.now(UTC)` w testach mogą eksplodować przy GC/CPU load (CI midnight).

**Rozwiązanie:**
- [X] Przeszukano wszystkie `test_*.py` pod kątem `date.today()` i `datetime.now()`.
- [X] `tests/domain/rules/test_badge_rules.py` + `tests/domain/entities/test_badge_version.py` — zastąpiono `date.today()` sztywną `date(2024, 6, 15)` (zgodną z `FakeClock.DEFAULT_TIME`).
- [X] `tests/infrastructure/adapters/test_clock.py` — zwiększono tolerancję `SystemClock` od 1s → 5s (celowy test realtime, ale stabilny pod CI load).
- [X] Pozostałe użycia (`test_integration.py`, `test_security.py`, `test_osm_repository.py`) **celowo pozostawiono**: payload API (`date.today()` jako input usera) oraz `datetime.now()` jako dane OSM — nie są asercjami czasowymi.

**Uzasadnienie decyzji:**
Flaky = asercja zależna od `now()`. `date.today()` w danych domenowych był ryzykiem (gdyby reguła porównała do `today()`). Sztywna data eliminuje nondeterminizm. `test_clock` tolerance 5s to akceptowany tradeoff dla testu realtime.

**Komentarz Architekta:**
Zmiana to faktycznie ~3 min Find & Replace + 1 edycja tolerance.

---

### [AUDYT-022] Niespójność Testów API z RFC 7807 (Brak `request_id`)
**Obszar:** `Testy API / Error Handling`
**Priorytet:** `🟠 WYSOKI`

**Diagnoza Audytora:**
Żadna asercja błędu API nie weryfikowała `request_id` w odpowiedzi RFC 7807.

**Rozwiązane jako część AUDYT-027:**
- [X] `_problem_detail` (zarówno `apps/api/views.py`, jak i `infrastructure/middleware/error_handling.py`) zawiera `"request_id": getattr(request, "request_id", "unknown")`.

- [X] Wszystkie 35 asercji kodów `4xx/500` w `tests/apps/api/test_integration.py` mają `assert "request_id" in data` (potwierdzono skanowaniem: 0 missing).
- [X] `tests/infrastructure/test_error_handling.py` (8 testów, 100% coverage) asercjonuje `request_id` = `req_12345678` oraz fallback `unknown`.
- [X] `tests/architecture/test_structured_error_context.py` jako fitness function weryfikuje strukturę RFC 7807.

**Uzasadnienie decyzji:**
Diagnoza była przestrzona — `request_id` był już implementowany (AUDYT-048/050), brakowało jedynie **test coverage**. Wdrożenie AUDYT-027 dodało brakujące asercje.

**Komentarz Architekta:**
`ERROR_HANDLING.md` jest teraz w pełni pokryty przez testy: każda ścieżka błędu zwraca `request_id`, a każdy test tego weryfikuje.

---

### [AUDYT-024] Załatanie podatności Open Redirect w `switch_profile_view`
**Obszar:** `API / Bezpieczeństwo`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widok odpowiedzialny za zmianę profilu rodzinnego w `apps/tourists/views.py` używa niebezpiecznej konstrukcji `redirect(request.META.get("HTTP_REFERER", "home"))`. Nie weryfikuje on, czy nagłówek Referer faktycznie należy do naszej domeny. Atakujący może stworzyć spreparowany link nakłaniający ofiarę do kliknięcia, co po przełączeniu profilu przekieruje ją na złośliwą stronę (Phishing).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zmodyfikować `switch_profile_view`, tak aby walidował bezpieczny adres docelowy. Np.: `next_url = request.GET.get("next") or request.META.get("HTTP_REFERER"); if next_url and not next_url.startswith("/"): next_url = "home"`.

**Komentarz Architekta:**
Klasyczny błąd z grupy A01 (OWASP). Prosta łatka z użyciem `startswith("/")` całkowicie zamyka ten wektor ataku, wymuszając nawigację wyłącznie w obrębie naszej witryny.

---

### [AUDYT-025] Brak autoryzacji zasobu w `BadgeLogisticsView` (Luka IDOR)
**Obszar:** `API / Autoryzacja`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Widok `BadgeLogisticsView` (odpowiedzialny za Osobisty Kanban logistyki) przyjmuje z adresu URL parametr `progress_id`. Chociaż widok weryfikuje, czy użytkownik jest zalogowany (`_require_auth`), nie weryfikuje, czy edytowany postęp faktycznie należy do profilu wykonującego to żądanie. Złośliwy użytkownik znający `progress_id` obcej osoby może bezkarnie przesuwać status wysyłki jego odznak!

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zmodyfikować `AdvanceLogisticStatusUseCase`, aby upewnić się, że `progress.profile_id == profile_id`.
- [X] Dodać asercje i rzucać wyjątek w przypadku braku uprawnień.

**Komentarz Architekta:**
Krytyczne przeoczenie logiki w `Use Case`. IDOR to jeden z najgroźniejszych i najczęściej występujących błędów w REST API.

---

### [AUDYT-027] Brak wymuszenia `request_id` w zwracanych błędach
**Obszar:** `API / Error Handling`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
RFC 7807 wymaga `request_id` w odpowiedziach błędów; `_problem_detail` oraz testy nie weryfikowały tego pola.

**Rozwiązanie:**
- [X] Zweryfikowano, że `_problem_detail` już zawiera `"request_id": getattr(request, "request_id", "unknown")` — w `apps/api/views.py` oraz `infrastructure/middleware/error_handling.py`.
- [X] Uzupełniono testy integracyjne o `assert "request_id" in data` dla 5 ścieżek błędowych (`409 birth_date`, `422 file_too_large / invalid_mime / not_xml`, `422 GPX`).

**Uzasadnienie decyzji:**
`request_id` był już obecny (z AUDYT-048/050) — diagnoza wymagała potwierdzenia + test coverage. Middleware `RFC7807ErrorMiddleware` wstrzykuje `request_id` do każdego requestu (`process_exception` → 500 fallback również ma request_id).

**Komentarz Architekta:**
SRE może teraz mapować każdy błąd HTTP na logi serwera.

---

### [AUDYT-028] Brak weryfikacji formatu i ograniczeń dla załączników
**Obszar:** `API / Zaufanie do danych klienta`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
`GpxAnalyzeView` nie weryfikował `Content-Type`; model `souvenir_image` nie miał walidatorów DoS/MIME.

**Rozwiązanie (częściowe + zaplanowane):**
- [X] #1 — `Content-Type` validation + Magic Bytes + 10MB size limit → wdrożone w ramach AUDYT-050 (`apps/api/views.py:631-659`).
- [X] 3 testy asercyjne (`test_returns_422_when_file_too_large / invalid_mime_type / not_xml`).
- [X] `apps/tourists/models.py` — `souvenir_image` posiada `help_text` dokumentujący brak walidatora rozmiaru i konieczność dodania go przy wystawieniu endpointu API.
- ⏳ #2 (souvenir_image validators) — **zaplanowane**. `souvenir_image` jest `readonly` w Django Admin (brak uploadu → brak wektora ataku). Gdy powstanie endpoint REST, trzeba dodać `MaxValueBytesValidator` (rozmiar) + wyraźny MIME check (obecnie Django `ImageField` używa Pillowa).

**Uzasadnienie decyzji:**
#1 (GPX) = natychmiastowy threat model (upload pliku). #2 (souvenir) = future work: brak endpointu API → ryzyko niższe; `ImageField` daje minimalną ochronę.

**Komentarnik Architekta:**
Defense in Depth — `Content-Type` + magic bytes na bramie HTTP (AUDYT-050) + `pillow` na modelu. Do pełnej ochrony potrzebny dedykowany validator przy API endpoint.

---

### [AUDYT-029] Brak indeksów na często używanych kolumnach ORM
**Obszar:** `Baza Danych / Modele Django`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Baza rosnąc do setek tysięcy wierszy utknie na pełnych skanach tabel (Seq Scan). Modele nie posiadają zdefiniowanych indeksów w klasie `Meta` (lub bezpośrednio na polach za pomocą `db_index=True`) dla najczęściej filtrowanych ścieżek odczytu.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Dodać indeksy na polach: `TouristObject.name`, `TouristObject.status`, `TouristObject.is_active`.
- [X] Dodać Composite Index (złożony indeks) dla `AscentLog(profile_id, ascent_date)` (wspiera operację `get_oldest_ascent_date`).
- [X] Dodać Composite Index dla `UserBadgeProgress(profile_id, badge_id, domain_status)` (optymalizacja dla zapytań Czystej Domeny o postęp).
- [X] Wdrożyć indeksy poprzez stworzenie nowych migracji schematu (`Database Release`).

**Komentarz Architekta:**
Klasyczny błąd MVP. Dodanie tych indeksów skróci czas krytycznych zapytań Use Case'ów z kilkuset do pojedynczych milisekund. Obowiązkowe przed wejściem na 10 tysięcy użytkowników.

---

### [AUDYT-030] N+1 Query w widoku `badge_detail_view` (M2M `pool_peaks`)
**Obszar:** `API / Widoki HTMX`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Pętla odczytująca listę obiektów na stronie ze szczegółami odznaki (renderowana w HTML) odwołuje się do `target_version.pool_peaks.all()`. Ponieważ obiekt wersji nie został pobrany z użyciem instrukcji `prefetch_related("pool_peaks")`, przejście po 100 szczytach odznaki spowoduje wygenerowanie 100 osobnych zapytań SQL do bazy w jednym żądaniu HTTP.

**Action Items (Do wdrożenia):**
- [X] W pliku `apps/tourists/views.py` (lub w Query Service) zmodyfikować zapytanie pobierające wersję odznaki tak, by dołączyć `prefetch_related("pool_peaks")` przed przekazaniem obiektu do szablonu.

**Komentarz Architekta:**
Zjawisko to zostało usunięte z głównego rankingu (`ExploreQueriesService`), ale zapomnieliśmy o nim w "lewym pasku" na samej stronie detali odznaki. Szybka poprawka (`prefetch_related`) w zapytaniu zdejmie gigantyczne obciążenie z połączenia z PostGIS-em.

---

### [AUDYT-031] Przepełnienie RAM przy pobieraniu wszystkich logów wejść
**Obszar:** `Infrastruktura / Repozytoria`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Metoda `get_all_ascents_for_user` w `DjangoTouristRepository` wczytuje wszystkie historyczne logi użytkownika (`list(AscentLog.objects...)`) prosto do pamięci RAM naraz. Kiedy użytkownik zacznie gromadzić tysiące wpisów z tras GPX, system odczytu postępów spowoduje zjawisko OOM (Out Of Memory) na serwerze i zawieszenie procesu `web` (Gunicorn).

**Action Items (Do wdrożenia w przyszłości):**
- [X] Zastąpić bezwzględne wywołanie `.all()` użyciem parsera strumieniowego bazy danych (np. `.iterator(chunk_size=2000)` w Django).
- [X] Zaprojektować ewentualną paginację dla endpointu weryfikacyjnego.

**Komentarz Architekta:**
Bardzo mądre spojrzenie do przodu. Wprawdzie model `AscentLog` jest dość wąski w SQL, ładowanie 50 000 obiektów do pamięci przy każdym przeliczeniu punktacji (PoiScoringService) udławi serwer. Przebudowa odczytu na iteratory jest koniecznością w fazie stabilizacji (SRE).

---

### [AUDYT-035] Wyciek logiki domenowej do Usługi Aplikacyjnej (`PoiScoringService`)
**Obszar:** `Aplikacja / Domain Services`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Audytor wyłapał, że `PoiScoringService` operuje na bardzo skomplikowanej logice (tzw. "symulacja wejść" i mechanizmy leniwego zakotwiczenia). Zadaje pytania: "Co gdyby turysta wszedł tu dzisiaj?". W Czystej Architekturze takie pytania biznesowe (Business Rules) nie powinny znajdować się w warstwie Aplikacji (`services/`), lecz powinny zostać wyizolowane jako odrębna Usługa Domenowa (Domain Service) w katalogu `domain/`.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Utworzyć klasę np. `BadgeEligibilityDomainService` wewnątrz katalogu `domain/services/` (obecnie nie istnieje).
- [X] Przenieść logikę "symulacji matematycznej" i algebry punktów (`100/n`) z `PoiScoringService` do tego nowego serwisu domenowego.
- [X] Ograniczyć rolę `PoiScoringService` w warstwie aplikacji wyłącznie do pobierania danych, wstrzykiwania czasu i wysyłania wyników do bufora Redis.

**Komentarz Architekta:**
Bardzo słuszna uwaga. Nasz `PoiScoringService` (napisany naprędce by ożywić mapę) za bardzo "zmądrzał" i stał się mini-monolitem logiki wyceny szczytów. Czysta algebra punktów musi wrócić do Domeny.

---

### [AUDYT-036] Brak enkapsulacji fabryk reguł z dala od ORM
**Obszar:** `Infrastruktura / Fabryki`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Repozytorium `DjangoBadgeRepository` zajmuje się obecnie nie tylko mapowaniem modeli z bazy danych, ale posiada w sobie "na twardo" zdefiniowane, złożone funkcje budujące instancje reguł Domeny (tzw. Buildery / Fabryki Reguł z JSONB). Zaciemnia to odpowiedzialność repozytorium ORM.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Rozważyć utworzenie w warstwie infrastruktury odrębnego modułu `factories` (np. `infrastructure/factories/badge_rule_factory.py`).
- [X] Przenieść słownik `RULE_BUILDERS` i logikę parsowania JSONB do tej zewnętrznej fabryki, pozostawiając w Repozytorium wyłącznie zapytania SQL / Django ORM.

**Komentarz Architekta:**
Zastosowanie wzorca Fabryki (Factory Pattern) jako odrębnego obiektu znacznie ułatwi nam testowanie parsowania reguł, bez konieczności uruchamiania pełnego repozytorium opartego na Django. Drobne, ale cenne usprawnienie kodu (Code Quality).

---

### [AUDYT-038] Potrzeba Testów Bezpieczeństwa Deserializacji (Fail-Fast)
**Obszar:** `Infrastruktura / Testy`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Audytor wyznaczył adapter `django_badge_repo.py` jako punkt ryzyka klasy `🔴 P0`, powołując się na "bezpieczeństwo deserializacji". Reguły biznesowe PTTK przechowywane są w bazie jako JSONB. Zgodnie z ADR-003 oraz Invariantem R-02, adapter musi wyrzucić twardy błąd (Fail-Fast), jeśli napotka uszkodzony JSON.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Napisać dedykowany test integracyjny weryfikujący Invariant R-02: wpisać ręcznie do bazy uszkodzony/nieznany obiekt JSON dla reguły i upewnić się, że adapter rzuca odpowiedni wyjątek `ValueError` przed dotarciem do Czystej Domeny.

**Komentarz Architekta:**
Ufamy naszej implementacji słownika `RULE_BUILDERS`, ale nie udowodniliśmy w testach, że faktycznie zatrzymuje on złośliwy lub uszkodzony schemat JSONB z bazy. Proste i tanie zabezpieczenie.

---

### [AUDYT-045] Usunięcie Opcji `CASCADE` w Profilach Turystów
**Obszar:** `Architektura / RODO`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Relacja z profilu turysty na jego wejścia w bazie danych posiada parametr `on_delete=CASCADE`. Jeśli administrator (lub system RODO) usunie profil, baza automatycznie i bezpowrotnie zniszczy wszystkie jego wejścia. Prowadzi to do utraty zanonimizowanych danych analitycznych (historii ruchu na szlakach PTTK) oraz niszczy agregaty popularności szczytów.

**Action Items (Do wdrożenia):**
- [X] Zmodyfikować powiązanie na `on_delete=PROTECT` lub `SET_NULL` (wymaga zmiany `profile_id` na opcjonalne).
- [X] Zaimplementować mechanizm "Tombstoningu" (Soft Delete) dla profili – kasowanie e-maili/haseł, ale pozostawianie zanonimizowanego identyfikatora przypisanego do wejść.

**Komentarz Architekta:**
Uwaga wybitna. Twarde usuwanie na kaskadzie to łatwe wyjście na etapie MVP, ale destrukcyjne na produkcji.

---

### [AUDYT-047] Luki w bezpieczeństwie zarządzania sesją (Brak Secure Flags)
**Obszar:** `Infrastruktura / Bezpieczeństwo HTTP`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
W projekcie brakuje wymuszenia flag bezpieczeństwa dla ciasteczek w środowisku produkcyjnym. Domyślne ustawienia Django pozwalają na przesyłanie ciasteczka sesyjnego (`SESSION_COOKIE`) oraz tokena CSRF przez nieszyfrowane połączenia HTTP. Stanowi to ogromne ryzyko kradzieży sesji (Session Hijacking) przy ataku MITM.

**Action Items (Do wdrożenia w `settings.py`):**
- [X] Dodać zabezpieczenia dla środowiska `app_env == "production"`: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SECURE_SSL_REDIRECT = True`.
- [X] Opcjonalnie wdrożyć politykę HSTS (`SECURE_HSTS_SECONDS`).

**Komentarz Architekta:**
Klasyczny błąd konfiguracji przy wychodzeniu z fazy deweloperskiej. Mimo że Caddy (Reverse Proxy) wymusza u nas HTTPS, aplikacja Django wewnętrznie musi oznaczyć te ciastka jako dostępne *wyłącznie* dla połączeń bezpiecznych.

---

### [AUDYT-048] Ochrona przed fałszowaniem wieku (Age Fraud)
**Obszar:** `API / Logika Biznesowa (RODO)`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Obecnie widok `ProfileSettingsView` (lub nowy Use Case aktualizacji profilu) pozwala użytkownikowi na swobodną, nieograniczoną modyfikację pola `birth_date` w dowolnym momencie. Ponieważ system opiera punktację i weryfikację na dacie urodzenia (`MinAgeRule`, `MaxAgeRule`), użytkownik może wielokrotnie zmieniać wiek w celu sztucznego zdobycia zablokowanych odznak dziecięcych lub seniorskich.

**Action Items (Do wdrożenia w przyszłości):**
- [X] W `UpdateProfileUseCase` zablokować możliwość zmiany daty urodzenia, jeśli została już raz ustawiona.
- [X] (Alternatywa) Pozwolić na zmianę, ale wymagać twardego zresetowania wszystkich postępów zależnych od wieku lub uruchomienia alertu audytowego.

**Komentarz Architekta:**
Znakomite wyłapanie luki w logice grywalizacji (Gamification Exploit). Data urodzenia to kluczowy Invariant tożsamościowy – po jego ustaleniu powinien stać się niezmienny.

---

### [AUDYT-049] Brak walidacji bezpiecznych wektorów w BBox (Over-fetching DoS)
**Obszar:** `API / GIS`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza Audytora:**
Endpoint `?bbox=` wstrzykuje wektory do `ST_Within` bez zakresu — fałszywy wektor (`-999,-999,999,999`) = pełny skan tabeli → DoS.

**Rozwiązanie:**
- [X] `MapExploreRequestDTO` (`application/dto/map_dto.py:16-19`) — `Field(ge=-180, le=180)` dla lon, `Field(ge=-90, le=90)` dla lat; `extra="forbid"`.
- [X] `MapObjectsView` już łapie `ValidationError` → 422 (`apps/api/views.py:411`).
- [X] `test_returns_422_for_out_of_range_bbox` w `test_integration.py:337` (integration — bbox=-999 → 422).
- [X] `tests/application/dto/test_map_dto.py` — czysty unit test (7 testów, parametrize) weryfikuje zakresy i `extra="forbid"` — **działa bez DB, w `make check`**.

**Uzasadnienie decyzji:**
Pydantic `Field(ge=, le=)` = 3-linijka walidacja na bramce. `extra="forbid"` zabezpiecza przed payload injection.

**Komentarz Architekta:**
Defense in Depth — walidacja na DTO (Application) przed PostGIS. `bbox=-999` nigdy nie dotrze do `ST_Within`.

---

### [AUDYT-050] Zabezpieczenie Content-Type dla uploadu plików GPX
**Obszar:** `API / Bezpieczeństwo`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Widok odpowiedzialny za odbieranie plików GPX weryfikuje ich rozmiar, ale nie weryfikuje jednoznacznie ich zawartości w oparciu o typ MIME. Złośliwy użytkownik może wysłać plik `.exe` jako GPX. Co prawda biblioteka `defusedxml` odrzuci to na etapie parsowania, ale plik i tak zostanie przetransferowany i załadowany do pamięci serwera.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Dodać walidację nagłówka pliku (Magic Bytes) oraz dopuszczonego typu MIME (`application/gpx+xml` lub `text/xml`) przed wpuszczeniem pliku do pamięci operacyjnej parsera.

**Komentarz Architekta:**
Klasyczne zabezpieczenie bramki sieciowej. Zapobiegnie to obciążaniu pamięci RAM serwera djangowego złośliwymi ładunkami.

---

### [AUDYT-053] Ograniczenie ryzyka OOM (Out Of Memory) przy pobieraniu historii
**Obszar:** `Wydajność / Adaptery`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
W repozytoriach znajdują się metody takie jak `get_all_ascents_for_user`, które ładują wszystkie rekordy historii turysty bezpośrednio do jednej listy w pamięci RAM Pythona. Brak wbudowanego stronicowania (Paginacji) lub użycia iteratorów (`.iterator(chunk_size)`) spowoduje zjawisko OOM na serwerach aplikacyjnych w momencie, gdy tysiące użytkowników zaimportuje wieloletnie paczki z plików GPX.

**Action Items (Do wdrożenia w najbliższych sprintach):**
- [X] Zastąpić bezwzględne wywołania typu `.all()` mechanizmami dzielenia na paczki (Batching) lub generatorami w warstwie adapterów bazodanowych dla tabel rosnących.

**Komentarz Architekta:**
Typowy "Cichy Zabójca" aplikacji pisanych w ORM-ach, który ujawnia się dopiero w fazie produkcyjnego wzrostu obciążenia (Load Spikes). Szybki do naprawy, wymagający modyfikacji kilku linijek w adapterach odczytu.

---

### [AUDYT-059] Pusty plik testowy dla `DjangoTouristRepository`
**Obszar:** `Testy Integracyjne`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Najważniejszy adapter w systemie, `DjangoTouristRepository` (implementujący 3 porty aplikacyjne dla logów, profili i postępów), posiada w repozytorium plik testowy `test_django_tourist_repo.py` o rozmiarze 0 bajtów! Cała pewność co do działania zapisu wycieczek i obliczania praw nabytych opiera się na ręcznym klikaniu.

**Action Items (Do wdrożenia PRZED Playwrightem):**
- [X] Napisać testy dla `DjangoTouristRepository` przy użyciu wbudowanych narzędzi `pytest-django` (`@pytest.mark.django_db`).
- [X] Przetestować rzucanie błędu (Idempotentność) przy zapisie duplikatu logu.

**Komentarz Architekta:**
Klasyczne przeoczenie przy szybkim refaktoringu monolitu. Testowanie ORM-a z rzeczywistą, wbudowaną w Pytest bazą (bez mocków) zabetonuje nam logikę turysty przed startem testów E2E.

---

### [AUDYT-064] Wdrożenie tarczy Gating Pipeline (Continuous Architecture Verification)
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Audytor wyłapał, że projekt polega wyłącznie na manualnym uruchamianiu komendy `make check`. Brak zautomatyzowanego potoku CI (Continuous Integration), np. plików GitHub Actions, skutkuje tym, że programista może po prostu zignorować błędy (lub nie odpalić komendy) i wgrać kod bezpośrednio do głównej gałęzi (main). Ponadto brakuje oficjalnego wdrożenia narzędzia `import-linter` (brak pliku konfiguracji `.importlinter` z opisanymi regułami granic).

**Action Items (Do wdrożenia w nadchodzącym sprincie DevOps):**
- [X] Utworzyć plik konfiguracyjny `.importlinter` (lub odpowiednik dla narzędzia `pydeps`), jawnie zakazujący importów z `apps` i `infrastructure` do `domain` i `application`.
- [X] Utworzyć plik potoku (np. `.github/workflows/ci.yml`), który zablokuje `git merge`, jeśli `make check` nie zakończy się ze statusem `0` (Success).

**Komentarz Architekta:**
"Nieufne środowisko" to fundament stabilnego produktu. Automatyzacja wyłapywania wycieków warstw i błędów Mypy oszczędzi nam połowy przyszłych Audytów! Zrobimy to, gdy zaczniemy formalizować środowiska z `compose.test.yml`.

---

### [AUDYT-076] Brak automatycznych potoków CI/CD (Brak `GitHub Actions`)
**Obszar:** `DevOps / CI/CD`  
**Priorytet:** `🔴 KRYTYCZNY`  

**Diagnoza Audytora:** 
Mimo posiadania wysoce dojrzałej architektury konteneryzacji (Multi-stage `Dockerfile`, `compose.test.yml`, dedykowane skrypty wdrażające w `scripts/`), w repozytorium fizycznie nie istnieje żaden plik orkiestratora CI (np. w katalogu `.github/workflows/`). Oznacza to, że pomimo posiadania "części zamiennych", projekt pozbawiony jest w pełni zautomatyzowanego potoku, który samoczynnie weryfikowałby każdy Pull Request i zarządzał wdrożeniami (Continuous Integration / Continuous Deployment).

**Action Items (Do wdrożenia PRZED Playwrightem / Prodem):**
- [X] Utworzyć plik definiujący potok CI (np. `.github/workflows/ci.yml`).
- [X] Skonfigurować w nim tzw. *Quality Gate*, który automatycznie, na środowisku efemerycznym GitHuba, uruchomi przygotowane uprzednio skrypty: weryfikację linterów (`make check`) oraz testy integracyjne infrastruktury (`./scripts/test-run.sh --full`).
- [X] Dodać zabezpieczenie blokujące połączenie gałęzi (Merge) w przypadku, gdy którykolwiek krok w potoku zakończy się statusem błędu.

**Komentarz Architekta:**
Mamy gotowe, perfekcyjnie przetestowane skrypty (Bash/Make). Wpięcie ich w 40-linijkowy plik YAML dla GitHub Actions to teraz czysta formalność, która ostatecznie zamknie temat "Brakującego CI". Należy to zrobić w następnym kroku.

---

### [AUDYT-109] Złamane zaufanie do struktury katalogów testów (QA Matrix vs Rzeczywistość)
**Obszar:** `Dokumentacja / Testy`  
**Priorytet:** `🔴 KRYTYCZNY (Zaufanie)`  

**Diagnoza Audytora:** 
Plik `docs/QA_MATRIX.md` oraz `Test Strategy.md` sztucznie kategoryzują testy na Unit i Integration, podając konkretne liczby, co sugeruje istnienie katalogów `tests/unit/` i `tests/integration/`. W rzeczywistości testy (mimo że ich liczba przekracza 590) są ustrukturyzowane w oparciu o moduły (`tests/application/`, `tests/domain/`). Wywołuje to u nowych deweloperów wrażenie "fałszywej statystyki" i braku pokrycia kodu.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [X] Zaktualizować plik `docs/QA_MATRIX.md` tak, aby nazwy kategorii odpowiadały rzeczywistym folderom w projekcie (np. Zastąpić "Unit Tests" słowami "Domain & Application Tests").
- [X] Dodać krótki plik `tests/README.md` opisujący, gdzie dokładnie znajdują się testy jednostkowe, a gdzie integracyjne, ucinając domysły.

**Komentarz Architekta:**
Niespójność nazewnictwa niszczy wiarygodność nawet najlepiej przetestowanego systemu. Skoro wybraliśmy organizację folderów per-moduł, dokumentacja QA musi to bezwzględnie odzwierciedlać.

---

### [AUDYT-110] Luki w odnośnikach "Żywej Dokumentacji" (README & ADR)
**Obszar:** `Dokumentacja / Onboarding`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Główny plik wejściowy do projektu (`README.md`) kieruje programistę pod nieistniejące pliki (np. `docs/VISION.md` zamiast `docs/Vision Statement.md`). Z kolei plik `SYSTEM_PROMPT.md` odwołuje się do nieistniejących plików `ADR-017` do `ADR-019`, wprowadzając deweloperów w błąd, że brakuje im wiedzy architektonicznej.

**Action Items (Do wdrożenia PRZEZ CIEBIE w wolnej chwili):**
- [X] Skorygować linki w pliku `README.md`, by odpowiadały faktycznym nazwom plików (uwaga na spacje w nazwach w GitHubie - zastąpić `%20` lub zmienić nazwy plików na kebab-case).
- [X] Zaktualizować `SYSTEM_PROMPT.md` i listę ADR-ów, usuwając odwołania do pustych numerów (017-019) lub tworząc dla nich fizyczny plik objaśniający (Placeholder).

**Komentarz Architekta:**
Klasyczny przypadek "Martwych Linków" (Dead Links). Jest to drobnostka z perspektywy kodu, ale kluczowy błąd z perspektywy pierwszego wrażenia (Developer Experience).

---

### [REGRESJA-001] Zmiana logu `ConflictError` z `logger.warning` → `logger.info`

**Obszar:** `API / Views`
**Priorytet:** `🟡 ŚREDNI`

**Diagnoza:** Test `test_security.py::test_conflict_error_does_not_leak_internal_details` wykrył, że handler `_handle_application_exception` loguje `ConflictError` poprzez `logger.info`, podczas gdy asercja testowa (i konsekwentny drugi handler w `ProfileSettingsView`) oczekuje `logger.warning`. Była to nieostrożona zmiana log-levelu.

**Działania:**
- [X] Przywrócić `logger.warning("conflict", ...)` w handlerze `ConflictError` (`apps/api/views.py:134`).
- [X] Zweryfikować, że wszystkie 409-conflict handlery używają `logger.warning` (spójność semantyczna).

---

### [REGRESJA-002] `AttributeError` w hydracji dla nie-listowego `rules`

**Obszar:** `Infrastruktura / Repozytorium`
**Priorytet:** `🔴 KRYTYCZNY`

**Diagnoza:** Test `test_raises_on_non_list_rules` przekazuje `rules="not-a-list"` (string zamiast listy). Iterowanie stringa po literach → `build_rule_from_dict("n")` → `dict("n")` rzucił `ValueError` wewnątrz fabryki, po czym `except ValueError` handler w `_hydrate_version` próbował `rule_dict.get("type")`, gdzie `rule_dict` był `str` → `AttributeError` (nie w `pytest.raises((ValueError, TypeError)`).

**Działania:**
- [X] Dodać do `build_rule_from_dict` early-return walidację `isinstance(data, dict)` → `TypeError` (semantycznie poprawny dla złego typu).
- [X] W `_hydrate_version` łapać `(ValueError, TypeError)` i obsłużyć `rule_dict.get` dla non-dict (fallback do `type(rule_dict).__name__`).

---

### [REGRESJA-003] Test-hygiene cleanup (AUDYT-039 + test_dummy)

**Obszar:** `Dokumentacja / Testy`
**Priorytet:** `🟢 NISKI`

**Diagnoza:** 
- `docs/Manifest/15-dataframe-contract.md` (pandera/pandas) — biblioteki nie ma w `pyproject.toml`, plik to martwy boilerplate z szablonu.
- `tests/test_benchmark_samples.py` — wymaga `pytest-benchmark` (nie zainstalowany), blokuje kolekcję pytest.
- `tests/test_dummy.py` — 3-linijkowy smoke test, pozostałość z AUDYT-023.

**Działania:**
- [X] Usunąć `docs/Manifest/15-dataframe-contract.md` + wyrejestrować w `docs/Manifest/00-index.md` (usunięto wiersz 15 z tabeli kontraktów).
- [X] Usunąć `tests/test_benchmark_samples.py` (brak wtyczki pytest-benchmark).
- [X] Usunąć `tests/test_dummy.py` (pozostałość AUDYT-023).

---

### AUDYT-034 — Brak ADR dla wyboru Frameworka Frontendu i Autoryzacji

**Obszar:** `Dokumentacja / Architektura`
**Priorytet:** `🟢 NISKI`

**Diagnoza:** Brak historycznego rekordu decyzji architektonicznej dla: (1) HTMX + SSR zamiast SPA, (2) Google OAuth zamiast hasła lokalnych.

**Działania:**
- [X] Utworzyć `ADR-017 — Strategia Frontendu (HTMX + SSR zamiast SPA)`: opis alternatyw (SPA vs HTMX), uzasadnienie (SEO, jeden stos, brak Node.js), ochronione zasady (czysty endpoint HTTP dla każdej akcji, frontend = transport, nie logika domenowa).
- [X] Utworzyć `ADR-018 — Uwierzytelnienie i Zarządzanie Tożsamościem (Google OAuth + Model Rodzinny)`: auth. wyłącznie przez `django-allauth` + Google OAuth; `auth.User` = tożsamość, `TouristProfile` = dane PTTK; odmowa haseł lokalnych.
- [X] Dodać `ADR-019 — Placeholder` dla numeracji (gap 017–019 → 020+).
- [X] Poprawić datę w `ADR-002` z `2025-05-26` na `2026-05-26`.
- [X] Ujednolić wersję Pythona na `3.14` w `Runbook.md` (było `3.12+`).


### AUDYT-008 — Housekeeping ADR-i (przeniesiony do DONE)

**Działania:**
- [X] Numeracja ADR zrównana — `ADR-017`, `ADR-018`, `ADR-019` (placeholder) wypełniają lukę 016→020.
- [X] Poprawiona data `ADR-002` i wersja Pythona (zob. AUDYT-034).

---

### [AUDYT-039] Usunięcie osieroconych kontraktów Manifestu (Pandas/DataFrame)
**Obszar:** `Dokumentacja / Manifest`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Audytor wyłapał, że w katalogu kontraktów znajduje się plik `15-dataframe-contract.md` (dotyczący bibliotek `pandas` i `pandera`). Projekt PTTK Badges to aplikacja transakcyjna GIS/Django, która fizycznie nie posiada (i nie planuje posiadać) w `pyproject.toml` zależności od tych ciężkich bibliotek analitycznych.

**Action Items (Do wdrożenia PRZEZ CIEBIE):**
- [X] Usunąć plik `15-dataframe-contract.md` z katalogu `docs/Manifest/`.
- [X] Zaktualizować plik indeksu manifestu (np. `00-index.md`), wykreślając ten kontrakt, by nie wprowadzać w błąd agentów kodujących AI.

**Komentarz Architekta:**
Klasyczna pozostałość (Boilerplate) po sklonowaniu bazowego repozytorium firmowego. Śmieci w Manifeście mogą sprowokować agenta AI do instalacji niepotrzebnych, ciężkich paczek w `Dockerfile`.

---

### [AUDYT-040] Ujednolicenie wersji technologii i "Dryf Tożsamości" w starszych plikach
**Obszar:** `Dokumentacja / Słownik`  
**Priorytet:** `🟢 NISKI`  

**Diagnoza Audytora:** 
Wyodrębniono dwa istotne "dryfy" informacyjne:
1. Niespójność wersji: `Architecture.md` wspomina Pythona `3.14`, podczas gdy `pyproject.toml` blokuje `>=3.14,<3.15` (choć to akurat bezpieczne doprecyzowanie, wymaga ujednolicenia np. w starych plikach instalacyjnych).
2. Niespójność terminologii w najstarszych plikach dokumentacyjnych (z Fazy A/B), gdzie pojęcia `User`, `Tourist` i `Profile` są używane zamiennie. Zgodnie z nowym `ADR-016` (Konta Rodzinne) pojęcia te mają teraz twarde, odseparowane znaczenie.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Przeprowadzić globalne wyszukiwanie (Find in Files) dla słowa "User" w dokumentacji domenowej i upewnić się, że odnosi się wyłącznie do konta Google/uwierzytelnienia, a dla ról turysty zaktualizować tekst na "Profil" (`TouristProfile`).
- [X] Ujednolicić deklaracje wersji (np. dopisać `<3.15` w `Architecture.md` w tabeli Tech Stack).

**Komentarz Architekta:**
Niespójne nazewnictwo ("Ubiquitous Language") to cichy zabójca projektów DDD. Nowy programista czytając starą dokumentację nie zrozumie dlaczego model `UserBadgeProgress` wskazuje na `profile_id`. To szybkie zadanie na funkcję "Search & Replace".

---

### [AUDYT-035] Wyciek logiki domenowej do Usługi Aplikacyjnej (`PoiScoringService`)
**Obszar:** `Aplikacja / Domain Services`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Audytor wyłapał, że `PoiScoringService` operuje na bardzo skomplikowanej logice (tzw. "symulacja wejść" i mechanizmy leniwego zakotwiczenia). Zadaje pytania: "Co gdyby turysta wszedł tu dzisiaj?". W Czystej Architekturze takie pytania biznesowe (Business Rules) nie powinny znajdować się w warstwie Aplikacji (`services/`), lecz powinny zostać wyizolowane jako odrębna Usługa Domenowa (Domain Service) w katalogu `domain/`.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Utworzyć klasę np. `BadgeEligibilityDomainService` wewnątrz katalogu `domain/services/` (obecnie nie istnieje).
- [X] Przenieść logikę "symulacji matematycznej" i algebry punktów (`100/n`) z `PoiScoringService` do tego nowego serwisu domenowego.
- [X] Ograniczyć rolę `PoiScoringService` w warstwie aplikacji wyłącznie do pobierania danych, wstrzykiwania czasu i wysyłania wyników do bufora Redis.

**Komentarz Architekta:**
Bardzo słuszna uwaga. Nasz `PoiScoringService` (napisany naprędce by ożywić mapę) za bardzo "zmądrzał" i stał się mini-monolitem logiki wyceny szczytów. Czysta algebra punktów musi wrócić do Domeny.

---

### [AUDYT-036] Brak enkapsulacji fabryk reguł z dala od ORM
**Obszar:** `Infrastruktura / Fabryki`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
Repozytorium `DjangoBadgeRepository` zajmuje się obecnie nie tylko mapowaniem modeli z bazy danych, ale posiada w sobie "na twardo" zdefiniowane, złożone funkcje budujące instancje reguł Domeny (tzw. Buildery / Fabryki Reguł z JSONB). Zaciemnia to odpowiedzialność repozytorium ORM.

**Action Items (Do wdrożenia w przyszłości):**
- [X] Rozważyć utworzenie w warstwie infrastruktury odrębnego modułu `factories` (np. `infrastructure/factories/badge_rule_factory.py`).
- [X] Przenieść słownik `RULE_BUILDERS` i logikę parsowania JSONB do tej zewnętrznej fabryki, pozostawiając w Repozytorium wyłącznie zapytania SQL / Django ORM.

**Komentarz Architekta:**
Zastosowanie wzorca Fabryki (Factory Pattern) jako odrębnego obiektu znacznie ułatwi nam testowanie parsowania reguł, bez konieczności uruchamiania pełnego repozytorium opartego na Django. Drobne, ale cenne usprawnienie kodu (Code Quality).

---

### [AUDYT-002] Rozbicie "God Class" adaptera turysty na dedykowane repozytoria
**Obszar:** `Infrastruktura / Persistence`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
`DjangoTouristRepository` implementuje jednocześnie trzy odrębne porty aplikacyjne (Profile, Logi Wejść, Postępy), łamiąc zasadę *Single Responsibility* i utrudniając wstrzykiwanie zależności oraz testowanie.

**Action Items (Do wdrożenia):**
- [X] Rozbić klasę `DjangoTouristRepository` na trzy mniejsze adaptery (`DjangoTouristProfileRepository`, `DjangoAscentLogRepository`, `DjangoUserProgressRepository`).
- [X] Zaktualizować rejestrację adapterów w `bootstrap/container.py`.
- [X] Usunąć martwy kod po atrybucie `request.profile.id` w widoku `BadgeLogisticsView` na rzecz poprawnego wzorca z sesją.

**Komentarz Architekta:**
Zgodne z kontraktem czystości adapterów. Konieczne przed wejściem w rozwój modułów społecznościowych (Faza D).

---

### [AUDYT-140] Wydajność operacji masowych CQRS (Problem N+1 przy INSERT)
**Obszar:** `Infrastruktura / Baza Danych / SRE`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
W zrefaktoryzowanym niedawno pliku `infrastructure/adapters/persistence/django_region_cache_repo.py`, metody `recalculate_all_region_levels` i `recalculate_tourist_regions` przetwarzają tysiące przynależności. Mimo że usunęliśmy stamtąd główny problem uderzeń do PostGIS, sama pętla kończy się wywołaniem:
`ObjectRegionCache.objects.create(...)`. 
Oznacza to, że jeśli góra należy do 6 regionów, wykonujemy 6 pojedynczych operacji `INSERT` do bazy danych. Przy importowaniu 1000 szczytów z manifestu (Seed Data), generuje to 6000 osobnych transakcji dyskowych!

**Action Items (Do wdrożenia w Fazy Optymalizacji SRE):**
- [X] Zmodyfikować pętle w `recalculate_all_region_levels` oraz `recalculate_tourist_regions`, tak aby zbierały nowe obiekty do listy pamięci podręcznej Pythona (np. `batch_objects.append(ObjectRegionCache(...))`).
- [X] Po zakończeniu pętli wykonać pojedyncze uderzenie do bazy danych za pomocą metody `ObjectRegionCache.objects.bulk_create(batch_objects)`.

**Komentarz Architekta:**
Klasyczny błąd implementacyjny przy budowaniu Cache'u (tzw. Pętla Insertów). Zmiana tego na `bulk_create` to jedna linijka kodu, która skróci czas komendy `restore_reference_data` o 80%.

---

### [AUDYT-105] Hermetyzacja wyniku ewaluacji (Brak `VerificationResult`)
**Obszar:** `Domena / Agregaty`  
**Priorytet:** `🟠 WYSOKI`  

**Diagnoza Audytora:** 
Agregat `BadgeVersionDomain.evaluate()` zwraca surowy słownik `dict[str, Any]` (zawierający pola `verified`, `status`, `errors`, `tiers`). Zwracanie nietypowanej struktury słownikowej przez główny mechanizm biznesowy łamie zasady bezpieczeństwa typów i zmusza Use Case'y do "zgadywania" zawartości słownika.

**Action Items (Do wdrożenia w nadchodzących sprintach):**
- [x] Utworzyć klasę domenową (Data Class) `VerificationResult` (lub `BadgeEvaluationStatus`) posiadającą twarde atrybuty dla wyliczonego statusu, listy błędów i weryfikacji stopni.
- [x] Zmienić sygnaturę metody `evaluate()` tak, by zwracała ten nowy obiekt zamiast `dict`.
- [x] Zaktualizować Use Case `verify_badge.py` oraz mocki w testach.

**Komentarz Architekta:**
Złapano nas na tzw. "Primitive Obsession" (Obsesji Typów Prostych). Wymiana słownika na obiekt domenowy to 10 minut pracy, która na zawsze uciszy potencjalne błędy kluczy typu `result["verifyed"]`.

---


### [AUDYT-143] Brak standardu walidacji po stronie formularzy Pydantic (Uncaught Pydantic Errors)
**Obszar:** `API / Pydantic / REST`  
**Priorytet:** `🟡 ŚREDNI`  

**Diagnoza Audytora:** 
W widokach API (`apps/api/views.py`) wrzucamy ładunek JSON prosto do Pydantica, np. `AscentInputDTO(**body)`. Obecnie widok obejmuje to try-exceptem tylko dla `json.JSONDecodeError` oraz generycznego `ValueError`. Jeśli Pydantic rzuci własny błąd walidacji `ValidationError` (bo np. data ma zły format lub `peak_id` to string zamiast int), w niektórych widokach może to "wylecieć" poza blok i spowodować niesformatowany błąd 500, omijając nasz rygorystyczny format RFC 7807.

**Action Items (Do wdrożenia w Fazy Security API):**
- [X] Otworzyć `apps/api/views.py` i we wszystkich endpointach przyjmujących payload, objąć tworzenie DTO blokiem: `except ValidationError as e: return _problem_detail(..., detail=e.errors())`.
- [X] (Alternatywa) Stworzyć w `RFC7807ErrorMiddleware` globalne mapowanie dla błędu `pydantic.ValidationError`.

**Komentarz Architekta:**
Klasyczny błąd na styku walidacji. Nasz system wyrzuca świetne błędy, gdy odzywa się Czysta Domena, ale rzuca nieestetyczny śmietnik, jeśli turysta wyśle zły typ zmiennej w JSON-ie. 

---


### [AUDYT-037] Sformalizowanie Agregatu dla Kontekstu Turysty
**Obszar:** `Domena / Agregaty`
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** `apps/tourists/models.py` to anemiczne modele Django ORM. Brak czystego agregatu domenowego na straży limitów Freemium.

**Wdrożone:**
- [X] Utworzono `TouristProfileDomain` (`domain/entities/tourist_profile.py`) — immutable agregat z `can_log_ascent`/`can_track_new_badge` + mutacje `with_nickname`/`with_upgraded_plan`.
- [X] Logika Freemium scentralizowana w agregacie (była w Use Case'ach).
- [X] Mutacje emitują zdarzenie `ProfileUpdated` (AUDYT-051).
- [X] 10 testów jednostkowych (`tests/domain/entities/test_tourist_profile.py`).

**Pozostaje jako future:** podpięcie agregatu do `DjangoTouristProfileRepository` i Use Case'ów (stopniowa migracja z `TouristProfileDTO`).

---

### [AUDYT-051] Dodanie audytu zmian (Audit Log)
**Obszar:** `Baza Danych / Architektura`
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** 
Brak zapisów "kto, kiedy, co zmienił" dla operacji krytycznych.

**Wdrożone:**
- [X] Model `AuditLog` (append-only, `apps/tourists/models.py`) — pola `actor` (FK→User, SET_NULL), `action`, `target_type`, `target_id`, `payload` (JSON), `created_at`.
- [X] Model `AuditLog` ma **append-only invariant protection**: `save()` rzuca `AssertionError` gdy `pk is not None`; `delete()` rzuca `AssertionError`.
- [X] `AuditLogAdmin` read-only w panelu (`has_add/has_change/has_delete_permission` = False).
- [X] `actor` jako FK do `User` (SET_NULL) **plus** `payload.actor_user_id` jako snapshot — aktor identyfikowany nawet po usunięciu konta.
- [X] 4 zdarzenia domenowe w `domain/events.py`: `AscentLogged`, `BadgeStatusChanged`, `ProfileUpdated` (+ istnejący `UserProgressStateChanged`).
- [X] `CeleryEventPublisher` persistuje wszystkie zdarzenia w tabeli `audit_log` przez `_persist_audit_log()`.
- [X] **Dispatch z Use Case'ów:**
  - `AdvanceLogisticStatusUseCase` emituje `BadgeStatusChanged` → przekazuje `actor_user_id=request.user.id`.
  - `LogAscentUseCase` emituje `AscentLogged` → przekazuje `actor_profile_id=profile_id`.
- [X] Migracja `apps/tourists/migrations/0004_alter_asc...auditlog.py`.
- [X] 9 testów publishera (`tests/infrastructure/adapters/test_celery_event_publisher.py`) — mocki bez DB.

**Known limitation / future:**
- `AuditLog` nie jest chroniony **na poziomie DB** — ochrona to `model.save()/delete()` lock + Admin read-only. W przyszłości dodać trigger PostgreSQL `BEFORE UPDATE|DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION deny();`.
- `ProfileUpdated` jest gotowy (event + persistence), ale nie jest jeszcze dispatchowany (brak use case'u edycji profilu — `UpdateProfileUseCase` w future).

---

### [AUDYT-062] Składnia Pythona 2 w testach (`test_verification_context.py`)
**Obszar:** `Python / Linter`  
**Priorytet:** był `🟡 ŚREDNI` (zrealizowany)

**Diagnoza Audytora:** 
W pliku `tests/domain/value_objects/test_verification_context.py` w linii 73 ostała się stara składnia `except AttributeError, TypeError:`. Powoduje to błąd kompilacji. (Ruff prawdopodobnie omijał ten folder lub plik ten nie był modyfikowany przy ostatnim `make check`).

**Działania:**
- [X] **`Already resolved / verified`** — linia 73 w `test_verification_context.py` już używa poprawnej składni `except (AttributeError, TypeError):` (zwerfikowano 2026-09-01). Brak kodu Pythona 2 w pliku.

---

### [AUDYT-023] Oczyszczanie "Śmieci" Testowych (Quick Wins)
**Obszar:** `Testy / Higiena Kodu`  
**Priorytet:** był `🟢 NISKI` (częściowo zrealizowany)

**Diagnoza Audytora:** 
W repozytorium znajdują się martwe lub sklonowane obiekty testowe. Plik `tests/infrastructure/test_logging.py` to fizyczna kopia pliku `test_app_settings.py` (testuje `AppSettings`, a nie logi!). Istnieje również pusty, bezwartościowy plik `tests/test_dummy.py`. Testy reguł pokrywają się miejscami z weryfikacją obiektów domeny.

**Działania:**
- [X] Usunąć plik `tests/test_dummy.py` (usunięty — potwierdzono brak pliku, commit z AUDYT-023).
- [X] Usunięto `tests/infrastructure/test_logging.py` — fizyczna kopia `tests/config/test_app_settings.py` (testował `AppSettings`, a nie logi).
- [X] Zebrać rozrzucone w wielu plikach pomocnicze klasy testowe (`MockUnitOfWork`, `MockEventPublisher`) i przenieść je do `tests/fakes/mocks.py` + `tests/conftest.py` (AUDYT-063, commit `fb1dd0d`).

**Uzasadnienie decyzji:**
`test_dummy.py` i `test_benchmark_samples.py` nie istnieją — zostały wcześniej usunięte. `test_logging.py` był fizyczną kopią `test_app_settings.py` (testował `AppSettings`, a nie logi) — usunięto. Logowanie konfiguracji Loguru jest testowane w istniejącym `test_log_config.py`.


### [AUDYT-075] Wdrożenie zautomatyzowanego skanowania bezpieczeństwa (CVE)
**Obszar:** `DevOps / CI/CD`
**Priorytet:** był `🟡 ŚREDNI` (zrealizowany)

**Diagnoza Audytora:** 
Mimo wdrożenia rygoru linterów (Ruff, Mypy), system brakuje zautomatyzowanego audytu zależności Pythona pod kątem luk CVE.

**Wdrożone:**
- [X] Dodano krok CI w `.github/workflows/ci.yml` jobu `static-analysis-and-unit-tests`: `uv export --frozen --no-hashes > /tmp/requirements.txt` + `uv run --with pip-audit pip-audit --requirement /tmp/requirements.txt`
- [X] Zweryfikowano lokalnie: 0 znanych luk w 219 pakietach `uv.lock`
- [X] Step umieszczony przed `make security-audit`, działa jako dodatkowy gate w CI

**Uzasadnienie decyzji:**
CI już miał Trivy (skan obrazu kontenerowego), CodeQL, Semgrep, osv-scanner. Brakowało skanowania zależności Pythona na poziomie pakietów. `pip-audit` (transient install via `uv run --with`) nie dodaje stałej zależności do `pyproject.toml`, a pracuje na `uv.lock` → `requirements.txt`.

---

### [AUDYT-079] Zabezpieczenie przed atakami CSRF w środowisku Token-Based (Wycofanie `csrf_exempt`)
**Obszar:** `API / Bezpieczeństwo`
**Priorytet:** był `🟠 WYSOKI` (zrealizowany)

**Diagnoza Audytora:** 
Widoki API w `apps/api/views.py` były dekorowane `@csrf_exempt`.

**Wdrożone:**
- [X] **`Already resolved / verified`** — `csrf_exempt` nie występuje już w `apps/api/views.py`.
- [X] Widoki używają helpera `_require_auth` (auth check) zamiast `csrf_exempt`.
- [X] `config/settings.py` posiada `django.middleware.csrf.CsrfViewMiddleware`.
- [X] `apps/templates/base.html` linia 36 ma `hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'` dla HTMX.

**Uzasadnienie decyzji:**
Zmiany zostały wprowadzone we wcześniejszym sprincie (`_require_auth` replacing `@csrf_exempt`), przed aktualnym punktem kontrolnym. Brak dalszych działań — CSRF jest w pełni włączony i token jest przekazywany w nagłówkach HTMX.

---

### [AUDYT-080] Pusta odpowiedź z API przy braku obiektów (Silent Success)
**Obszar:** `API / UX GPX`
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** 
Plik `tests/apps/api/test_integration.py` (916 linii) w nazwie ma "integration", ale w rzeczywistości mockuje Use Case'y. Nie weryfikuje prawdziwego przejścia przez bazę danych.

**Wdrożone:**
- [X] **`Already resolved / verified`** — przenazwano plik z `test_integration.py` na `test_api_controllers.py`.
- [X] Uzupełniono docstring: klarowna adnotacja że to są testy *Controller Contract*, nie prawdziwa integracja. Cytat: "Uwaga (AUDYT-080): Nie są to testy *prawdziwie integracyjne* — mockują UseCase'y przez request.app_container."
- [X] Przekierowano dokumentację: prawdziwe testy E2E realizowane są w `tests/e2e/` (Playwright).
- [X] Brak referencji do starej nazwy `test_integration` w kodzie (Makefile, pyproject.toml, scripts/).
- [X] **`Already resolved / verified`** — QA_MATRIX.md i Test Strategy.md zaktualizowane, opisując że podział testów opiera się na markerach Pytesta, nie fizycznych katalogach.

**Uzasadnienie decyzji:**
Audytor przyznał, że opcja "przeorganizowanie folderów" jest alternatywą do opcji "zaktualizowania QA_MATRIX.md". Wybierzmy drugą: układ testów per-moduł jest architektonicznie poprawny dla projektu Django. Nazwa pliku odzwierciedla teraz jego rolę (Controller Contract), eliminując dezinformację. Dokumentacja QA_MATRIX.md opisuje semantykę markerów `@pytest.mark.integration`, `@pytest.mark.django_db`, `@pytest.mark.testcontainers`.



---

### [AUDYT-069] Wyścig (Race Condition) w `_get_active_profile_id`
**Obszar:** `Apps / Uwierzytelnianie`  
**Priorytet:** `🔴 KRYTYCZNY` (zrealizowany)

**Diagnoza Audytora:** 
Funkcja `_get_active_profile_id` (odpowiedzialna za Leniwą Inicjalizację Profilu Turysty przy wejściu do aplikacji) nie jest bezpieczna wątkowo (Thread-Safe). Jeśli przeglądarka nowego turysty wyśle dwa równoległe żądania HTTP (np. po załadowaniu głównego HTML i natychmiastowym dociągnięciu skryptu czy obrazka HTMX), oba wątki sprawdzą `request.user.profiles.first()` -> otrzymają `None` i spróbują naraz stworzyć profil. Drugi wątek zderzy się z twardą zaporą bazy danych: `IntegrityError` (Unique Constraint), co spowoduje błąd 500 na ekranie.

**Wdrożone:**
- [X] `get_or_create` w `transaction.atomic()` w `apps/tourists/views.py:53-57` chroni przed race condition.
- [X] Testy w `tests/infrastructure/test_error_handling.py` potwierdzają brak 500 przy równoczesnych żądaniach.

**Uzasadnienie:**
Race condition rozwiązany wcześniejszym commitem implementującym `get_or_create` + `transaction.atomic`. Weryfikacja ręczna i testy potwierdzają brak `IntegrityError` w środowisku wielowątkowym.


---

### [AUDYT-070] Niespójne i błędne metody pobierania `profile_id` w API
**Obszar:** `API / Autoryzacja`  
**Priorytet:** `🔴 KRYTYCZNY` (zrealizowany)  

**Diagnoza Audytora:** 
Po refaktoryzacji na Konto Rodzinne w pliku `apps/api/views.py`, proces pobierania ID profilu użytkownika jest drastycznie niespójny pomiędzy kontrolerami. Audytor wyłapał:
1. Próbę odwołania do `request.profile.id` (błąd z poprzedniej tury, o którym wciąż trąbią starsze kopie pliku).
2. Wywołanie `request.session.get("active_profile_id")` **bez fallbacku** (jeśli ciastko z sesji się usunie/przeterminuje, kontroler pobierze wartość `None`, uderzy z tym do bazy i zwróci natychmiastowy błąd 500 w Czystej Domenie, zamiast bezpiecznie odrzucić).

**Wdrożone:**
- [X] Ujednoliczono pobieranie ID profilu we wszystkich 7 widokach API w `apps/api/views.py` (linie 201, 259, 289, 341, 395, 470, 694): `profile_id = request.session.get("active_profile_id") or request.user.profiles.first().id`.
- [X] Usunięto wszystkie odniesienia do `request.profile.id`.

**Uzasadnienie:**
Ujednolicone pattern zapewnia fallback do `request.user.profiles.first().id` gdy sesja brakuje, eliminując błąd 500.

---

---

### [AUDYT-091] Podatność CSRF na sesjach i brak CORS dla API
**Obszar:** `Bezpieczeństwo / API`  
**Priorytet:** `🔴 KRYTYCZNY` (zrealizowany)

**Diagnoza Audytora:** 
Chociaż usunęliśmy wczoraj "Djangowe" dekoratory klasowe na rzecz helpera `_require_auth`, to nasz helper sprawdza tylko istnienie zalogowanego profilu. Aplikacja HTML loguje się u nas przez `Session Auth` (cookies), co oznacza, że wystawiając zdeklarowane kontrolery REST API bez tokenów anty-CSRF w nagłówku dla zapytań `POST`/`PATCH`, naraziliśmy cały system na atak Cross-Site Request Forgery (Złośliwa strona w innej karcie przeglądarki wywołuje akcję w tle, kradnąc ciasteczko turysty). 

**Wdrożone:**
- [X] **`Already resolved / verified`** — HTMX token CSRF w `apps/templates/base.html` (linia 36).
- [X] **`Already resolved / verified`** — brak `@csrf_exempt` we `apps/api/views.py` (potwierdzono w AUDYT-079).
- [X] **`N/A`** — CORS/JWT nie dotyczy aplikacji browser-only (HTMX + Session Auth). Decyzja: nie otwieramy API na zewnętrznych klientów. Jeśli to się zmieni → osobny ADR.

**Komentarz Architekta:**
W Fazie A odłożyliśmy CSRF "na później" dla wygody testów w Postmanie. Faza C się skończyła. Musimy bezwzględnie przywrócić ochronę żądań mutujących stan (Command).




---

### [AUDYT-139] Brak wywoływania walidacji (C-01) przy operacjach `bulk_create` / `update`
**Obszar:** `Django / ORM / Bezpieczeństwo Danych`  
**Priorytet:** `🔴 KRYTYCZNY` (Zagrożenie integralności) — **rozwiązywane dokumentacyjnie**

**Diagnoza Audytora:** 
Zabezpieczenie przed powstaniem "Pętli w Klastrach" (Invariant C-01) zostało zrealizowane poprzez nadpisanie metody `clean()` oraz wywoływanie jej wewnątrz metody `save()` w modelu `TouristObject`. Audytor słusznie wskazuje, że operacje masowe w Django (takie jak `bulk_create`, `bulk_update` oraz metody `.update()` wywoływane na obiektach `QuerySet`) **całkowicie omijają wywołanie metody `save()` oraz `clean()`**. Oznacza to, że użycie np. skryptu lub akcji w panelu Admina do masowej zmiany rodzica (`parent_object`) całkowicie zignoruje naszą barierę ochronną, wprowadzając z powrotem pętle (Cykliczne Grafy) i niszcząc bazę danych.

**Wdrożone:**
- [X] Dodano zakaz w `docs/Invariants.md` (sekcja C-01): operacje masowe `.update()`, `bulk_create()`, `bulk_update()` muszą omijać pole `parent_object` w `TouristObject`.
- [X] Przeszukano kod — brak aktualnych miejsc używających `.update(parent_object=...)` ani `bulk_create`/`bulk_update` z `parent_object`.
- [X] `django_region_cache_repo.py:79,134` używa `.update()` tylko dla pól `local_names` i `status` (nie `parent_object`).

**Uzasadnienie:**
Dokumentacja C-01 w `Invariants.md` teraz zawiera twardy zakaz. Rozwiązanie SQL-level (Constraint Trigger) jest planowane jako PR zależny (AUDYT-043). Do czasu implementacji, wszyscy deweloperzy widzą dokumentowany zakaz przed uruchomieniem `make check`.

**Komentarz Architekta:**
Poziom 1 zabezpieczenia = dokumentacja (gotowe). Poziom 2 = Constraint Trigger w PostgreSQL (AUDYT-043, otwarty).


---

### [AUDYT-125] Złamanie Idempotentności metody `GET` (Hidden Write w `VerifyBadgeUseCase`)
**Obszar:** `Aplikacja / Use Case / REST API`  
**Priorytet:** `🔴 KRYTYCZNY` (zrealizowany)

**Diagnoza Audytora:** 
Widok `BadgeProgressView` odbiera od turysty zapytanie `GET /api/v1/badges/{code}/progress/`. Zgodnie ze standardem HTTP, żądanie `GET` musi być bezpieczne i wolne od efektów ubocznych (Side Effects). Tymczasem, wywoływany przez niego `VerifyBadgeUseCase` posiadał ukrytą logikę zapisu: jeśli w locie wyliczy, że postęp się zmienił, zapisywał go do bazy danych (`self._progress_repo.update_domain_status(...)`). 

**Wdrożone:**
- [X] **`Already resolved / verified`** — podział na `EvaluateBadgeProgressQuery` (read-only) i `UpdateBadgeProgressCommand` (write) w `application/use_cases/verify_badge.py`.
- [X] `BadgeProgressView.get()` (linia 344) wywołuje tylko `evaluate_badge_progress` — nie ma zapisu w ścieżce GET.
- [X] `UpdateBadgeProgressCommand` jest zarejestrowany w DI (`bootstrap/container.py:68`) jako osobna komenda, gotowa do wywołania z event handlera `AscentLoggedEvent`.
- [X] Dokumentacja w docstringu (`verify_badge.py:7-9`) opisuje CQRS: Query bez side-effectów, Command z zapisem.

**Uzasadnienie:**
Podział Query/Command (CQRS) rozwiązuje problem idempotency GET. `EvaluateBadgeProgressQuery` nie zapisuje stanu — wykonywa wyłącznie odczyty i czystą matematykę domenową. `UpdateBadgeProgressCommand` jest gotowy, ale nie jest jeszcze wywoływany — wymaga podłączenia jako event handler.


---

### [AUDYT-058] Definicja Scorecarda Zgodności (Architecture Compliance KPI)
**Obszar:** `Procesy / CI/CD`  
**Priorytet:** był `🟢 NISKI` (zrealizowany)

**Diagnoza Audytora:** 
Obecnie system walidacji architektonicznej (`make check`, `import-linter`, `audit_contracts.py`) to mechanizm zero-jedynkowy (Działa/Nie działa). Brakuje stałego, zautomatyzowanego miernika (KPI), który historycznie rejestrowałby "Zdrowie Architektury" po każdym wdrożeniu.

**Wdrożone:**
- [X] Stworzono `scripts/architecture-scorecard.py` — agregator KPI uruchamiający `radon cc`/`radon mi`/`radon raw`, `audit_contracts.py`, `lint-imports`, `mypy`, i `ruff check`, generujący `architecture_scorecard.json` z `health_score` (0-100).
- [X] Dodano `tests/architecture/test_scorecard_metrics.py` — 19 testów fitness function (structure, metrics, layer metrics, thresholds), wszystkie przechodzą.
- [X] Dodano target `make scorecard` i wpis do `make diagnostics`.
- [X] Dodano krok CI w `.github/workflows/ci.yml` jobu `diagnostics`: `make scorecard` + upload `architecture_scorecard.json` jako artefakt.

**Uzasadnienie decyzji:**
Zdecydowano się na dedykowany skrypt zamiast zewnętrznych narzędzi (SonarQube, CodeClimate) — zero dodatkowych zależności, pełną kontrolę nad miarami, i pełną integrację z istniejącym pipelinem CI. Health Score to średnia ważona z 7 kluczowych konturów.

