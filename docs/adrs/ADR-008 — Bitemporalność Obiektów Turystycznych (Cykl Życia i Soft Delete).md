# ADR-008 — Bitemporalność Obiektów Turystycznych (Cykl Życia i Soft Delete)

> **Status:** `accepted`  
> **Data:** 2026-05-26  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Fizyczne obiekty turystyczne, takie jak wieże widokowe czy schroniska, ulegają zniszczeniu, spaleniu lub są demontowane. Jednocześnie nowe obiekty są regularnie budowane. Jeśli schronisko spłonęło w 2023 roku, usunięcie go z bazy danych zniszczyłoby relacyjną integralność logów wejść turystów (`AscentLog`) z lat ubiegłych, uniemożliwiając re-weryfikację zdobytych odznak. Z drugiej strony, pozostawienie zniszczonego obiektu w bazie umożliwiłoby nieuczciwym turystom zalogowanie dzisiejszego wejścia na obiekt, który fizycznie nie istnieje.

**Pytanie decyzyjne:**  
W jaki sposób zarządzać usuniętymi oraz nowo powstałymi obiektami turystycznymi w bazie, by chronić historię wejść (wstecz), zapobiegać oszustwom (wprzód) oraz zachować porządek na mapach w aplikacji mobilnej?

---

## Debata przed decyzją

**DBA:** Twardy `DELETE` (rekordu w SQL) jest absolutnie wykluczony, jeśli tabele logów uderzają do niego po kluczu obcym (chyba że użyjemy `SET NULL`, co i tak zniszczy informację o tym, gdzie turysta był). Potrzebujemy flagi `is_deleted`.
**Domain Expert:** Sama flaga nie wystarczy. PTTK oddało wieżę do użytku w 2020 r. Ktoś wpisuje w książeczkę, że zdobył ją w 2018 r. Flaga `is_deleted=False` mu na to pozwoli, a przecież wieży tam nie było! Potrzebujemy wektorów czasu.
**Security & Operations Engineer:** Co, jeśli administrator ustawi `existence_end` na datę w przyszłości (np. za miesiąc)? Czy zagraża to integralności systemu? Nie, wręcz przeciwnie — staje się to pożądaną funkcją (Future-Scheduling), pozwalającą z wyprzedzeniem zaplanować zamknięcie szlaku, remont schroniska lub rozebranie wieży bez potrzeby pamiętania, by zalogować się do panelu dokładnie w dniu zdarzenia.

*Wniosek z debaty:* Prosta flaga usunięcia nie spełnia wymogów biznesowych PTTK. Konieczne jest wdrożenie pełnego modelu bitemporalnego. Zasadą obsługi dla obiektów geologicznych (istniejących zawsze) staje się paradygmat: "Puste znaczy dowolne".

---

## Opcje rozważane

### Opcja A: Prosty Soft Delete (`is_active` boolean)
**Opis:** Dodanie flagi `is_active=True/False`.
**Plusy:** Proste odfiltrowanie nieistniejących obiektów z wyświetlania na mapie (`filter(is_active=True)`).
**Minusy:** Brak ochrony przed fałszywym logowaniem wejść w przeszłości. System nie wie, KIEDY obiekt przestał istnieć.

### Opcja B: Wersjonowanie całych obiektów (SCD Type 2)
**Opis:** Wzorzec Hurtowni Danych (Slowly Changing Dimensions) – tworzymy nowy rekord szczytu dla każdej zmiany w czasie.
**Plusy:** Ekstremalnie dokładny audyt.
**Minusy:** Gigantyczny *Over-engineering* niszczący wydajność i utrudniający zarządzanie ID obiektów przez administratora PTTK.

### Opcja C: Model Bitemporalny (Start/End Dates + Status UI)
**Opis:** Dodanie kolumn informacyjnych o czasie fizycznego istnienia: `existence_start` i `existence_end`, oraz pozostawienie flagi interfejsowej `is_active` (sterującej widocznością na froncie). Brak dat (NULL) oznacza nieskończoność:
- `existence_start = NULL` → obiekt istnieje "od zawsze"
- `existence_end = NULL` → obiekt istnieje "do zawsze" (nadal funkcjonuje)

---

## Decyzja

**Wybrano: Opcja C — Model Bitemporalny (Start/End Dates + Status UI)**

Podejście "Puste znaczy dowolne" (Handling Nulls) rozwiązuje problem zjawisk geologicznych (szczyt istnieje "od zawsze"). Dla obiektów stworzonych ludzką ręką pozwala z aptekarską precyzją odrzucać wejścia wykraczające poza okno czasowe istnienia fizycznego obiektu, a także planować zamknięcia w przyszłości. Flaga `is_active` ułatwia frontendowi generowanie warstw mapowych bez skomplikowanych obliczeń dat na zapleczu. Co więcej, podejście to integruje się natywnie z tagiem `start_date` importowanym z Data Lake OSM.

---

## Konsekwencje

### Pozytywne
- **Ochrona Historii (Immutability):** Ani jedno archiwalne wejście w logach systemu nie zostanie utracone z powodu zmian w terenie.
- **Narzędzie Antyfraudowe i Planowanie:** Silnik weryfikacyjny blokuje fałszywe wejścia z datami, w których budynek nie istniał, a Admin może planować zamknięcia obiektów z wyprzedzeniem.

### Negatywne / Ograniczenia
- **Zobowiązanie Architektoniczne w Czystej Domenie:** Wymusza to przekazanie atrybutów `existence_start` i `existence_end` z Infrastruktury do Czystej Domeny (np. przez rozbudowanie agregatu lub wyizolowanie nowej globalnej Reguły Czasu Życia). Silnik weryfikujący musi od teraz zawsze, jako krok "Zero" ewaluacji, krzyżować datę z logu z bitemporalnym wektorem obiektu. Nie jest to prosta aktualizacja panelu Admina, lecz twarde zobowiązanie do zmiany sygnatur weryfikacyjnych.

### Działania wymagane (Zrealizowane)
- [x] Dodanie pól `existence_start`, `existence_end` oraz `is_active` do modelu `TouristObject`.
- [x] Dostosowanie `OsmDataExtractor` do automatycznego parsowania tagu `start_date` z OSM do formatu daty w Pythonie.
- [x] Zgrupowanie nowych pól w logiczny *fieldset* w panelu Django Admin.

---

## Warunek rewizji

Dokument poddać rewizji, jeśli w Fazie C (System Użytkownika) weryfikacja tysięcy logów (`AscentLog`) zacznie cierpieć na problemy wydajnościowe z powodu konieczności każdorazowego odpytywania i krzyżowania bitemporalnych atrybutów obiektów z bazy. W takim scenariuszu należy rozważyć zdenormalizowanie dat istnienia (lub samego wektora ważności) bezpośrednio do tabeli `AscentLog` w momencie zapisu wejścia przez turystę, wymieniając zajętość dysku na prędkość odczytu.

---

## Referencje

- **ADR-003 — Silnik Reguł Biznesowych:** Czysta Domena będzie musiała wchłonąć bitemporalność obiektu jako absolutny priorytet przed ewaluacją jakichkolwiek innych reguł zdefiniowanych w tym ADR.
- **ADR-004 — Dwuwarstwowy model zasilania danych z OSM:** Pobieranie i parsowanie tagu `start_date` z Data Lake odbywa się zgodnie z zasadami izolacji wprowadzonymi w tym dokumencie.
- **ADR-007 — Hierarchia i Wersjonowanie Odznak:** Ustanawia "Prawa Nabytych" dla Odznak, podczas gdy niniejszy ADR (008) zapewnia "Prawa Nabyte" na poziomie pojedynczych, fizycznych Obiektów.
