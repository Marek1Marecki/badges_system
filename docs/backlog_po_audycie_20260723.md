# Backlog po Audycie (Import Linter / Architektura)

> **Dokument roboczy** gromadzący zadania refaktoryzacyjne wynikające z audytu konfiguracji `.importlinter` i oceny zewnętrznej. Każde zadanie po wdrożeniu powinno zostać odhaczone.

---

## Lista zadań do realizacji:

---

### [AUDYT-155] Refaktoryzacja Długu Architektonicznego w `context_processors.py`
**Obszar:** `Architektura / Apps vs Infra`  
**Priorytet:** `🟢 NISKI`  
**Diagnoza:** Wyłom zdefiniowany w `.importlinter` (DŁUG-003). Procesor ładuje konfigurację `map_layers` wprost z warstwy infrastruktury do szablonów Django.
**Action Items:** Zbudować interfejs portu `MapConfigPort` w warstwie Aplikacji i odpytywać go w widokach, zrzucając zależność na Kontener DI.

---

### [AUDYT-156] Refaktoryzacja Długu Architektonicznego w `tasks.py` (OSM)
**Obszar:** `Architektura / Apps vs Infra`  
**Priorytet:** `🟢 NISKI`  
**Diagnoza:** Wyłom zdefiniowany w `.importlinter` (DŁUG-001). Task wciąż powiązany z bezpośrednim odpytywaniem `osm_adapter`.
**Action Items:** Przenieść logikę do przygotowanego już `RunOsmNightWatchmanUseCase` lub podobnej usługi aplikacyjnej.

---

### [AUDYT-157] Refaktoryzacja Długu Architektonicznego w `models.py` (JSON Schema)
**Obszar:** `Architektura / Apps vs Infra`  
**Priorytet:** `🟢 NISKI`  
**Diagnoza:** Wyłom zdefiniowany w `.importlinter` (DŁUG-002). Model Django posiada wiedzę o strukturze walidacji formularzy w infrastrukturze.
**Action Items:** Przenieść powiązanie `django-jsonform` ze schematem z warstwy `models.py` na warstwę wyżej (do definicji `forms.py` lub `admin.py`).

---

### [AUDYT-158] Opracowanie zestawu "Smoke Tests" dla środowiska PRE-PROD/PROD

**Obszar:** `QA / Deployment Validation`  
**Priorytet:** `🟡 ŚREDNI` (Przed automatyzacją wdrożeń)

**Diagnoza Architekta:**
Zgodnie z koncepcją opisaną w docs/architecture/preprod-validation.md, testowanie środowiska po wdrożeniu (Deployment Validation) różni się od testów E2E i Integracyjnych. Obecnie nie posiadamy wydzielonego, minimalistycznego zestawu testów, który można by bezpiecznie odpalić na żywym środowisku (PRE-PROD lub PROD) po wykonaniu release.sh, by potwierdzić, że aplikacja "wstała i oddycha".

**Action Items (Do wdrożenia w Fazy SRE/Deploy):**

- [ ] Stworzyć nowy, mały katalog testów, np. `tests/smoke/`.
- [ ] Napisać w nim 3-5 minimalistycznych testów (np. weryfikacja 200 OK na `/health/`, sprawdzenie ładowania strony głównej, udane logowanie konta testowego, próbny odczyt jednego szczytu z API).
- [ ] Skonfigurować wywołanie tych testów jako ostatni krok potoku po udanym wdrożeniu środowiska (Post-Deployment Sanity Check).

**Komentarz Architekta:**
"Smoke Tests" nie testują logiki biznesowej. Odpowiadają na jedno pytanie: "Czy wtyczka jest w gniazdku, a serwer widzi bazę danych?". Ochroni to nas przed sytuacją, w której CI świeci na zielono, ale na produkcji użyliśmy złego hasła w `.env.prod`.

---

### [AUDYT-159] Eksperyment z Hammett jako runnerem dla Mutmuta

**Obszar:** `QA / Tooling`  
**Priorytet:** `🔵 EKSPERYMENTALNY`

**Diagnoza:**
Mutmut jest obecnie wolny na pełnym zestawie testów. Istnieje pokusa zastąpienia `pytest` przez `hammett` (szybki klon), ale z uwagi na naszą architekturę (wtyczki `pytest-django`, `hypothesis`), `hammett` może nie obsłużyć naszego środowiska testowego.

**Action Items (Do wdrożenia w module EXPERIMENTAL):**
- [ ] Przetestować wywołanie `mutmut run` z flagą `--use-coverage` w połączeniu z ograniczeniem ścieżek (`--paths-to-mutate=domain/`), aby radykalnie skrócić czas wykonywania z użyciem standardowego `pytest`.
- [ ] Przeprowadzić izolowany eksperyment na gałęzi bocznej (Branch): podmienić runner na `hammett` i sprawdzić, czy narzędzie to potrafi poprawnie obsłużyć testy własnościowe (`Hypothesis`). Jeśli tak – zastosować lokalnie. Jeśli nie – odrzucić.
- [ ] Rozważyć przeniesienie pełnego skanu mutacyjnego do zautomatyzowanego potoku Nocnego (Nightly CI Job) w GitHub Actions.
