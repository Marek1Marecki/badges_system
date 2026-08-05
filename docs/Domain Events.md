# Domain Events — zdarzenia domenowe

> **Wersja:** 1.1  
> **Data:** 2026-05-28  
> **Właściciel:** Dominik / AI Architect  
>
> Zdarzenia domenowe opisują **co się stało** w systemie. Ten dokument definiuje przepływ informacji pomiędzy kontekstami bazy danych, Celery i panelu administracyjnego.  
> **Dla agentów LLM:** Jeśli implementujesz logikę asynchroniczną, przestrzegaj rygoru przekazywania danych do kolejek (tylko ID, nigdy obiekty!).

---

## Konwencje i Wzorce

### Aktualny model (Faza A/B): Command-driven Async
Obecnie system komunikuje się asynchronicznie (Event-Driven) głównie na styku Warstwy Aplikacji z Infrastrukturą (Celery), w formie delegacji zadań (Command Pattern w tle). Służy to wyłącznie optymalizacji procesów GIS i odciążeniu interfejsu (UX).

### Planowany model (Faza C): Event-driven Pub/Sub
Prawdziwe Zdarzenia Domenowe (architektura Pub/Sub) będą integralną częścią Fazy C (Kanban Logistyki i Statusy Turystów), gdzie jeden fakt (np. `BadgeVersionCompleted`) będzie publikowany do wspólnej szyny zdarzeń i nasłuchiwany przez wiele niezależnych modułów (powiadomienia, albumy, odblokowywanie kolejnych poziomów).

### Wzorzec: Transactional Outbox / On-Commit
Aby zapobiec sytuacji (Race Condition), w której zadanie wpadnie do kolejki Redis, a główna transakcja w PostGIS z jakiegoś powodu się opóźni lub nie powiedzie (Rolling back), system bezwzględnie egzekwuje wzorzec uruchamiania po udanym commit:

```python
from django.db import transaction

# PRAWIDŁOWO: Celery pobierze obiekt dopiero, gdy ten na 100% znajdzie się w bazie
transaction.on_commit(lambda: my_async_task.delay(obj.id))
```

### Struktura Payloadu (Dla zadań Celery - Command Pattern)
W obecnej fazie (Faza A/B), polecenia wysyłane do kolejki Redis muszą być proste i serializowalne do JSON. 
**ZŁOTA ZASADA:** Do zadania asynchronicznego przekazujemy wyłącznie identyfikatory (`ID`), a nigdy całe obiekty ORM Django (które nie są serializowalne w JSON i stwarzałyby problem "Stale Data" / danych zdezaktualizowanych w momencie wykonania taska).

```python
# Format payloadu wysyłanego do Redis przez Celery:
{
    "task_name": "fetch_osm_data_task",
    "args": [],
    "kwargs": {"object_id": int},  # JEDYNY PAYLOAD — ID encji
    "eta": None,  # null = natychmiastowe
}
```

---

## 1. Zdarzenia Katalogowania (Setup Phase)

### `TouristObjectCreated` (Wysłanie do OSM)
**Kiedy publikowane:** Gdy Administrator utworzy w panelu nowy Obiekt Turystyczny, podając mu `osm_id`.
**Mechanizm:** Hook `save_model` w `TouristObjectAdmin` powiązany z `transaction.on_commit`.
**Konsumenci:** `fetch_osm_data_task`.
**Akcja (Side-effect):** Uruchomienie liniowego systemu `Retry` w celu pobrania z Overpass API pełnego Data Lake i uzupełnienia pustych kolumn "Złotego Standardu".

### `TouristObjectReady` (Wyliczenie CQRS)
**Kiedy publikowane:** Po pomyślnym wykonaniu zadania `fetch_osm_data_task` (status przechodzi na `READY`) LUB gdy Administrator ręcznie wymusi przeliczenie poprzez akcję z menu rozwijanego w Django Admin (`recalculate_regions_async`).
**Mechanizm:** Bezpośrednie wywołanie łańcuchowe (Task Chaining) z poziomu taska OSM, lub wywołanie ręczne.
**Konsumenci:** Silnik PostGIS (CQRS).
**Akcja (Side-effect):** Zniszczenie starych i zbudowanie nowych relacji w tabeli `ObjectRegionCache` na bazie buforów przestrzennych, a następnie wyciągnięcie nazw granicznych z JSONB (`osm_raw_tags`).

### `TouristRegionMerged` (Złączenie Geometrii)
**Kiedy publikowane:** Gdy Administrator zaktualizuje relacje składnikowe w polach `filter_horizontal` dla nowo tworzonego lub edytowanego nadrzędnego Regionu Turystycznego (np. "Sudety").
**Mechanizm:** Nadpisana metoda `save_related` w klasie `TouristRegionAdmin`.
**Konsumenci:** `build_tourist_region_geometry_task`.
**Akcja (Side-effect):** Potężna operacja `ST_Union` na geometrii wszystkich wybranych jednostek podległych, a następnie logiczna (bez odpytywania PostGIS!) migracja wierszy dziedziczących szczytów w tabeli `ObjectRegionCache`.

### `ProximityScanCompleted` (Generowanie Klastrów)
**Kiedy publikowane:** Po zakończeniu asynchronicznego przeczesywania bazy przez skaner (uruchamianego z akcji `run_proximity_scanner` w panelu Admina lub w przyszłości harmonogramem Celery Beat).
**Mechanizm:** Pętla przeszukująca PostGIS z użyciem `ST_DWithin(150m)`.
**Konsumenci:** `ProximityCandidate` (Skrzynka Odbiorcza dla Radaru).
**Akcja (Side-effect):** Zapisanie znalezionych par blisko leżących obiektów (nieposiadających relacji "Rodzic-Dziecko" i nie zignorowanych wcześniej) w tabeli pomocniczej, oczekujących na manualną akceptację Administratora.

---

## 2. Zdarzenia Planowane dla Użytkowników (Faza C - Pub/Sub)

### `BadgeVersionCompleted`
**Kiedy publikowane:** Gdy Czysta Domena potwierdzi, że turysta spełnił 100% matematycznych wymogów dla odznaki.
**Konsumenci (Planowani):** `LogisticsKanbanService`
**Akcja:** Odblokowanie turyście opcji manipulowania polami logistycznymi (`logistic_status`) dla danego rekordu w jego interfejsie.

### `LogisticsStatusAdvanced`
**Kiedy publikowane:** Gdy turysta ręcznie przesunie status odznaki (np. poda datę wysłania przesyłki do PTTK).
**Konsumenci:** —
**Akcja:** Ograniczenie interfejsowe – zablokowanie możliwości modyfikacji/usuwania logów `AscentLog` podpiętych pod ten zamknięty Cykl odznaki.

### `UserProgressStateChanged` (Aktualizacja Rankingu)
**Kiedy publikowane:** Kiedy stan turysty lub otaczających go reguł ulegnie zmianie. Wyzwalane przez: log wejścia, zmianę obserwowanych odznak, osiągnięcie progu wiekowego (urodziny), otwarcie/zamknięcie okna czasowego z regulaminu, lub zmianę struktury obiektu turystycznego przez Admina.
**Konsumenci:** `PoiScoringService` (Cache Manager)
**Akcja:** Usunięcie (Inwalidacja) wpisów z pamięci Redis dla dotkniętych użytkowników, co wymusza asynchroniczne lub leniwe przeliczenie Rankingu Potencjału Obiektów (Score `100/n`) przy następnym żądaniu mapy.

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-28 | Dominik / AI Architect | Pierwsza wersja dokumentu. Usystematyzowanie asynchronicznych haków transakcyjnych. |
| 1.1 | 2026-05-28 | AI Architect | Doprecyzowanie formatu payloadu Celery (wymóg przekazywania wyłącznie ID, nie obiektów Django), kategoryzacja na Fazy (Command vs Pub/Sub), dodanie zdarzenia `ProximityScanCompleted` oraz zdefiniowanie wektorów wyzwolenia dla CQRS. |
