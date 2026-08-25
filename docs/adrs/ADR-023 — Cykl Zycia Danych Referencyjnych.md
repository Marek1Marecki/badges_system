# ADR-023 — Cykl Życia Danych Referencyjnych (Reference Data Lifecycle)

> **Status:** `accepted`  
> **Data:** 2026-07-22  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Zgodnie z `ADR-020`, środowisko produkcyjne traktuje Dane Referencyjne (szczyty, geometrie regionów, regulaminy odznak, mapowania OSM) jako kod — wgrywany w formie zwalidowanych, niemutowalnych snapshotów (artefaktów). 
Dane Referencyjne są silnie powiązane z Danymi Użytkowników (`User Data`). Przykładowo, rekord `AscentLog` (zalogowane wejście turysty) posiada klucz obcy do `TouristObject` (szczyt), a `UserBadgeProgress` do `BadgeVersionModel`.

**Pytanie decyzyjne:**  
Jak ustandaryzować proces tworzenia, walidacji i modyfikacji Danych Referencyjnych od momentu ich edycji w środowisku autorskim aż do wdrożenia, aby zapobiec korupcji Danych Użytkowników (np. kaskadowemu usunięciu postępów) oraz zapewnić całkowity determinizm środowisk?

---

## Opcje rozważane

### Opcja A: Zarządzanie przez Migracje Danych w Django (Data Migrations)
**Opis:** Każda zmiana w regulaminach lub topografii jest pisana ręcznie jako skrypt Pythona w plikach migracji Django (`migrations.RunPython`).
**Plusy:** Ścisłe powiązanie danych ze schematem bazy.
**Minusy:** Całkowicie niepraktyczne dla tysięcy obiektów GIS. Panel Django Admin staje się bezużyteczny. Pliki migracji spuchłyby do setek megabajtów.

### Opcja B: Edycja na PRE-PROD i synchronizacja w dół
**Opis:** Administrator loguje się na środowisko PRE-PROD, wyklikuje nowe odznaki, a następnie "ściąga" bazę na dół do DEV w celu tworzenia snapshotów.
**Plusy:** Administrator ma środowisko zbliżone do produkcji do "zabawy" danymi.
**Minusy:** Łamie zasadę przepływu jednokierunkowego (ZAKAZ EXPORTU z wyższych środowisk). Ryzyko przemieszania danych testowych z referencyjnymi.

### Opcja C: Autorytatywne Środowisko Autorskie i GitOps (Wybrane)
**Opis:** Wyłącznie dedykowane Środowisko Autorskie jest uprawnione do modyfikacji Danych Referencyjnych. Zmiany są następnie eksportowane do zarchiwizowanych plików (`export_reference_data`), weryfikowane automatycznie w CI i wdrażane jednokierunkowo wzwyż, zgodnie z zasadą Infrastructure as Code.

---

## Decyzja

Wdrażamy rygorystyczny proces **Reference Data Lifecycle**, składający się z sześciu nienaruszalnych zasad:

1. **Monopol Środowiska Autorskiego (Authoring Environment) na Edycję:**
   Wyłącznie wydzielone Środowisko Autorskie może modyfikować Dane Referencyjne. W obecnej architekturze rolę tę pełni środowisko programisty (DEV). Dostęp do zapisu w tabelach referencyjnych (przez Django Admin) na środowiskach TEST, PRE-PROD i PROD musi zostać wyłączony dla wszystkich użytkowników. Ponadto zabrania się bezpośredniej modyfikacji tabel referencyjnych na tych środowiskach przy użyciu zapytań SQL, skryptów administracyjnych lub innych narzędzi bazodanowych. Jedynym dopuszczalnym mechanizmem wdrożenia zmian jest odtworzenie zatwierdzonego snapshotu.

2. **Zakaz Niszczenia Historii (Tombstone Pattern / Soft Delete):**
   Ponieważ Dane Użytkowników polegają referencyjnie na Danych Referencyjnych, **absolutnie zakazuje się fizycznego usuwania (DELETE)** obiektów turystycznych, odznak ani ich wersji ze Środowiska Autorskiego (i docelowo z bazy).
   - Jeśli obiekt (np. wieża widokowa) uległ zniszczeniu, Administrator musi ustawić pole bitemporalne `existence_end` na datę zniszczenia oraz flagę `is_active = False` (Zgodnie z ADR-008).
   - Jeśli odznaka zostaje wycofana, Administrator oznacza ją jako nieaktywną.
   Klucze główne (`id`) obiektów referencyjnych są trwałe i nigdy nie podlegają ponownemu wykorzystaniu. Obiekty usunięte fizycznie z mapy zachowują się w bazie jak "nagrobki" (Tombstones), gwarantując historyczną integralność logów zdobywców.

3. **Tworzenie i Niemutowalność Snapshotu:**
   Zakończenie prac edycyjnych na Środowisku Autorskim wymaga wywołania komendy `export_reference_data`. Komenda ta generuje nowy zestaw plików w archiwum oraz zaktualizowany `manifest.json`. 
   Po pomyślnym wygenerowaniu, snapshot automatycznie otrzymuje od skryptu unikalny identyfikator (`snapshot_id`), który pozostaje niezmienny przez cały cykl życia artefaktu. 
   Utworzony snapshot jest artefaktem niemutowalnym. Próba zmiany choćby jednego znaku w pliku `.json.gz` złamie sumę kontrolną (`digest`) wyliczoną w manifeście i zablokuje proces. `manifest.json` zawiera również pole `schema_version` definiujące strukturę samego pliku JSON manifestu; proces odtwarzania odrzuci snapshot w nieobsługiwanym lub przestarzałym formacie danych.
   Snapshot nie jest wdrażany samodzielnie. Może zostać użyty wyłącznie po uprzednim zaewidencjonowaniu go w rejestrze wydań (Release Registry) zgodnie z ustaleniami z `ADR-022`.

4. **Pre-Flight Validation (Weryfikacja Integralności Danych):**
   Potok CI/CD nie może ślepo ufać plikom snapshotu. Wprowadza się wymóg uruchomienia zautomatyzowanej weryfikacji przed akceptacją Pull Requesta. Walidator działa w izolacji i sprawdza:
   - Zgodność struktury danych z obowiązującym schematem deklarowanym w `manifest.json`.
   - Poprawność sum kontrolnych (`digest`) dla wygenerowanych plików `.json.gz`.
   - Unikalność biznesowych identyfikatorów (np. kodów odznak).
   - Poprawność wskaźników referencyjnych (klucze obce `ForeignKey` wskazujące wyłącznie obiekty istniejące wewnątrz tej samej lub wcześniej zatwierdzonej paczki).
   - Integralność geometrii GIS (np. weryfikacja poprawności `SRID` oraz walidacja strukturalna przez funkcję `ST_IsValid`).
   Odrzucenie weryfikacji wymusza poprawę danych na Środowisku Autorskim i wygenerowanie nowego snapshotu.

5. **Atomowość i Idempotentność Odtwarzania (Restore Pattern):**
   Wdrażanie Danych Referencyjnych (`restore_reference_data`) na środowiskach docelowych (TEST, PRE-PROD, PROD) opiera się na mechanizmach `Upsert` (Aktualizuj lub Wstaw). Operacja ta musi być w 100% idempotentna — wielokrotne uruchomienie przywracania z tego samego snapshotu nie modyfikuje niepotrzebnie danych, ani nie powiela rekordów. Proces odtwarzania wykonywany jest w pojedynczej transakcji bazy danych (`transaction.atomic()`). W przypadku błędu system wycofuje wszystkie zmiany powiązane ze snapshotem i żadna jego część nie pozostaje częściowo zaimportowana.
   **Proces `restore_reference_data` nie wykonuje operacji fizycznego usuwania rekordów z bazy. Brak obiektu w przesyłanym snapshocie nie jest w żadnym wypadku interpretowany przez aplikację jako polecenie wyczyszczenia (usunięcia) tego rekordu z bazy docelowej.** Gwarantuje to bezpieczeństwo logów wejść w przypadku wadliwego lub częściowego eksportu ze Środowiska Autorskiego.

---

## Konsekwencje

### Pozytywne
- **Ochrona Spójności (Referential Integrity):** Zasada *Soft Delete / Tombstone* całkowicie chroni historię wędrówek turystów. Usunięcie szczytu z mapy OSM nie niszczy dorobku zdobywców z ubiegłych lat.
- **Bezpieczeństwo Produkcji:** Zablokowanie edycji w panelu Admina na produkcji eliminuje ryzyko wprowadzania "szybkich poprawek" na żywym organizmie (Hotfixing), które skutkowałyby rozjazdem bazy PROD ze snapshotem w repozytorium (Data Drift). Zabezpieczony jest również scenariusz utraty postępów z powodu nieobecności rekordu w świeżo zaimportowanym zrzucie.
- Odtwarzalność środowisk dla testerów QA opiera się na absolutnie przewidywalnym, powtarzalnym i zwalidowanym zbiorze danych.

### Negatywne / Działania wymagane
- Narzuca duży rygor na pracę Administratora. Nawet poprawa literówki w nazwie góry w systemie produkcyjnym wymaga pełnego cyklu: zmiana na DEV ➔ eksport ➔ zatwierdzenie Pull Requesta w Git ➔ Reference Data Release. Zwiększa to czas wprowadzania drobnych poprawek (Lead Time).
- Wymaga fizycznego zaprogramowania nakładek bezpieczeństwa w klasach Django Admin (np. `has_add_permission`, `has_change_permission` zwracających `False` dla środowiska `PROD`).
- Wymaga zaimplementowania skryptu weryfikującego (Lintera Danych) do sprawdzania spójności paczek JSON w potoku CI/CD.

---

## Warunek rewizji

Dokument podlega rewizji w momencie, gdy:
- Zbiór danych referencyjnych osiągnie rozmiary powodujące zauważalne opóźnienia w operacjach CI/CD lub przekraczanie limitów wielkości repozytorium (mimo kompresji GZIP).
- Pojawi się potrzeba współbieżnej edycji danych referencyjnych przez wielu administratorów pracujących równolegle nad tym samym wycinkiem (co przekracza możliwości izolowanego środowiska DEV bez ryzyk konfliktów scalania podczas eksportu).

W takich sytuacjach należy rozważyć przejście z systemu opartego na plikach na dedykowany system klasy MDM (Master Data Management) lub zewnętrzny rejestr referencyjny z natywnym wsparciem dla rozproszonej współpracy i wersjonowania danych.

## Relacje (Related)
- **ADR-008 — Bitemporalność Obiektów Turystycznych (Cykl Życia i Soft Delete):** Zasada Soft Delete / Tombstone Pattern gwarantująca historyczną integralność logów zdobywców.
- **ADR-020 — Architektura Wdrożeń (Deployment & SRE):** Cykl życia danych referencyjnych implementuje zasady niemutowalności snapshotów i izolacji środowisk zdefiniowane w ADR-020.
- **ADR-022 — Rejestr Wdrożeń (Release Registry):** Snapshot referencyjny może zostać użyty wyłącznie po uprzednim zaewidencjonowaniu go w rejestrze wydań zgodnie z ustaleniami z ADR-022.
