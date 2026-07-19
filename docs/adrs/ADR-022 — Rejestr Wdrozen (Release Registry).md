# ADR-022 — Rejestr Wdrożeń (Release Registry & Version Matrix)

> **Status:** `accepted`  
> **Data:** 2026-07-21  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Zgodnie z `ADR-020 (Architektura Wdrożeń)`, system rozdziela cykle życia aplikacji, schematu bazy danych (migracji) oraz danych referencyjnych (snapshotów). Mimo że wdrożenia te mogą następować niezależnie, podlegają one ścisłym relacjom kompatybilności. Niezgodność wybranej wersji obrazu Dockera ze stanem bazy danych lub starym snapshotem referencyjnym doprowadzi do awarii na środowiskach PRE-PROD i PROD.

W `ADR-020` ustanowiono wymóg: *„System wspiera jedynie kombinacje jawnie przetestowane w potoku CI/CD. Rejestr tych kombinacji dla środowiska PROD stanowi artefakt audytowy...”*. 

**Pytanie decyzyjne:**  
Gdzie i w jakiej formie należy przechowywać autorytatywną Macierz Wersji (Version Matrix) dopuszczonych do wdrożenia, aby proces CI/CD mógł ją odczytywać maszynowo (w celu blokowania błędnych deployów), a zespół zyskał historię audytową ułatwiającą bezpieczny i przewidywalny Rollback?

---

## Opcje rozważane

### Opcja A: Tabela w Bazie Danych (Runtime Registry)
**Opis:** Tabela w PostgreSQL (np. `deployment_registry`), do której CI/CD dopisuje udane kombinacje. Skrypt wdrożeniowy przed wykonaniem operacji odpytuje bazę.
**Plusy:** Łatwe wprowadzanie zmian i audytowanie za pomocą zapytań SQL.
**Minusy:** Problem "Kury i Jajka". Skrypt CI/CD musi połączyć się z bazą danych na PROD *zanim* rozpocznie wdrożenie, co łamie zasadę izolacji i utrudnia weryfikację na etapie planowania potoku (Pipeline). Zmiana danych bazy stwarza ryzyko utraty rejestru po awarii.

### Opcja B: Tagi Obrazów Dockerowych (Tag-based Matrix)
**Opis:** Pakowanie informacji o zależnościach bezpośrednio w nazwę tagu obrazu, np. `app:v1.4.0-schema-0021-snap2026.07`.
**Plusy:** Brak konieczności utrzymywania dodatkowych plików.
**Minusy:** Skrajnie nieczytelne nazwy. Brak możliwości aktualizacji danych referencyjnych bez przebudowywania (lub retagowania) obrazu aplikacji, co łamie ideę niezależnych cykli z ADR-020. Podatność na mutacje tagów.

### Opcja C: Plik Konfiguracyjny GitOps (YAML/JSON w Repozytorium)
**Opis:** Utrzymywanie w repozytorium kodu jawnego pliku (np. `releases.yaml`), który stanowi "Księgę Zatwierdzonych Wdrożeń". Każdy wpis w pliku to definicja Release Candidate (RC) zawierająca hashe i identyfikatory 3 artefaktów.
**Plusy:** Zgodność z filozofią GitOps. Pełna audytowalność przez mechanizmy Pull Request. Potok CI/CD może zweryfikować macierz statycznie (przed dotknięciem jakiegokolwiek środowiska).

---

## Decyzja

Wybieramy **Opcję C: Plik Konfiguracyjny GitOps (`releases.yaml`) jako Release Registry**.

Release Registry stanowi jedyne autorytatywne źródło prawdy określające, które kombinacje artefaktów mogą zostać wdrożone na środowiska PRE-PROD oraz PROD. Środowiska deweloperskie (DEV) i testy lokalne nie korzystają z Release Registry i dopuszczają dowolne kombinacje stanów. Środowisko TEST może generować tymczasowe kombinacje artefaktów na potrzeby automatycznych testów integracyjnych, jednak tylko kombinacje wpisane do Release Registry mogą zostać promowane na PRE-PROD i PROD.

1. **Format, Lokalizacja i Walidacja:**
   Rejestr wdrożeń utrzymywany jest w pliku `deploy/releases.yaml` (lub odpowiedniku JSON) wewnątrz głównego repozytorium projektu. Każda zmiana pliku `releases.yaml` podlega rygorystycznej walidacji schematu (YAML Schema / JSON Schema) w potoku CI (weryfikacja formatu dat, wymaganych pól i typów danych).

2. **Zasada Blokady Pipeline (Deployment Barrier):**
   Deployment Pipeline odmawia wdrożenia kombinacji artefaktów nieobecnej w Release Registry. Każdy skrypt wdrożeniowy na samym początku odczytuje plik `releases.yaml`. Próba zaaplikowania innej kombinacji `app_image`, `migration_identifier` i `snapshot` skutkuje natychmiastowym błędem weryfikacji. Weryfikacja odbywa się przed wykonaniem jakichkolwiek operacji na środowisku docelowym (*pre-flight validation*).

3. **Zakaz Modyfikacji z CI/CD (Immutable Registry Workflow):**
   Rejestr jest modyfikowany **wyłącznie** poprzez Pull Request zatwierdzony zgodnie z procesem Release Management. Potok CI/CD jedynie weryfikuje jego poprawność; system nie posiada uprawnień do automatycznej modyfikacji tego pliku.

4. **Struktura Wpisu Wdrożeniowego (Release Record):**
   Wpis w pliku `releases.yaml` wymusza stosowanie stałych wartości weryfikacyjnych (Digests/Hashes), uodparniając system na podmianę obrazów (Image Spoofing). Identyfikator bazy to jednoznaczna nazwa migracji w standardzie Django. Oznaczenie `digest` stosowane jest jednorodnie dla obrazów i plików.
   *Przykład struktury obiektowej:*
   ```yaml
   releases:
     - id: PROD-042
   
       application:
         tag: v1.4.0
         digest: sha256:8af3...
   
       database:
         migration_identifier: 0021_create_physical_neighbors
   
       reference_data:
         snapshot: 2026.07.09
         digest: sha256:abc123def456...
   
       lifecycle:
         test: 2026-07-20T08:15:00Z
         preprod: 2026-07-20T12:11:00Z
         prod: 2026-07-21T09:00:00Z
   
       status: ACTIVE
   ```

5. **Cykl Życia Wydania i Niemutowalność Złych Wydań (Revocation):**
   Pole `status` definiuje stan przydatności rekordu i może przyjmować wartości takie jak `ACTIVE`, `REVOKED`, `DEPRECATED`, `SUPERSEDED` lub inne zdefiniowane operacyjnie. W danym momencie tylko jeden rekord może posiadać status `ACTIVE` dla środowiska PROD. Jeśli określony `id` wdrożony na środowiska docelowe wykaże krytyczne błędy, zabrania się fizycznego "kasowania" tego wpisu w pliku `releases.yaml`. Jego status musi zostać zaktualizowany na `REVOKED`. Gwarantuje to nienaruszalność historii audytowej.

6. **Zasada Bezpiecznego Wycofywania (Rollback Strategy):**
   Rollback polega na wskazaniu wcześniejszego wpisu Release Registry i ponownym wdrożeniu kompletnego zestawu artefaktów wskazanych przez ten rekord. Pipeline kategorycznie nie dopuszcza częściowego rollbacku (np. wycofania samego obrazu aplikacji przy jednoczesnym pozostawieniu obecnego, nowszego snapshotu referencyjnego), chyba że owa pożądana, "hybrydowa" kombinacja widnieje jako legalny i zatwierdzony wpis w rejestrze. Chroni to system przed powstawaniem struktur nieprzetestowanych integracyjnie.

7. **Niemutowalność Artefaktów:**
   Wszystkie artefakty wskazywane przez Release Registry (obrazy Docker, snapshoty danych referencyjnych) muszą być niezmienne. Publikacja nowej wersji powoduje utworzenie nowego artefaktu, nigdy nadpisanie istniejącego. Release Registry może wskazywać wyłącznie artefakty identyfikowane przez ich niezmienne identyfikatory (digesty).

---

## Konsekwencje

### Pozytywne
- **Bezpieczeństwo Odtwarzania:** Rollback na środowisku produkcyjnym sprowadza się do jednej komendy wskazującej znane `release_id`. System CI sam "wie", z jakiego obrazu i snapshotu musi to złożyć, a blokada "częściowych rollbacków" zapobiega uszkodzeniom bazy danych.
- **GitOps:** Pełna przejrzystość wdrożeń. Zmiana statusu wdrożenia wymaga Pull Requesta i rewizji, pozostawiając ślad w historii Git ze znacznikiem czasu.
- Ochrona przed tzw. *Frankenstein Deployments* (mieszaniem starych snapshotów z nowym kodem lub odwrotnie).

### Negatywne / Działania wymagane
- Konieczność oprogramowania logiki walidacji pliku `.yaml` wewnątrz skryptów CI/CD (np. poprzez parser Python sprawdzający schemat YAML, sumy `sha256` oraz weryfikujący poprawność węzłów w `lifecycle` względem blokad).
- Dodatkowy krok administracyjny (aktualizacja pliku `releases.yaml`) przy tworzeniu nowych wydań Danych Referencyjnych, nawet jeśli kod aplikacji się nie zmienia.

---

## Warunek rewizji

Dokument podlega rewizji w przypadku migracji infrastruktury na systemy orkiestracji takie jak Kubernetes (gdzie funkcję Release Registry mogą wprost przejąć mechanizmy Helm, ArgoCD, lub Custom Resource Definitions) albo wdrożenia zaawansowanych rejestrów artefaktów (np. wbudowanych w GitLab CI/CD). Rewizja jest również wymagana w przypadku wprowadzenia podpisywania artefaktów w łańcuchu dostaw oprogramowania (Software Supply Chain Security, np. Sigstore/Cosign lub GPG), umożliwiającego kryptograficzną weryfikację autentyczności zatwierdzonych kombinacji przed ich wdrożeniem, co będzie wymagało rozszerzenia modelu Release Registry.
