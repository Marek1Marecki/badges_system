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
