# Vision Statement

> **Wersja:** 1.1  
> **Data:** 2026-05-29  
> **Właściciel:** Dominik / AI Architect  
> **Status:** `approved`

---

## 1. Problem do rozwiązania

Współczesna turystyka górska i system odznak PTTK (oraz innych klubów i organizacji) opiera się na rozproszonych, często wygasających stronach internetowych, zdezaktualizowanych wykazach szczytów i żmudnej, ręcznej weryfikacji papierowych książeczek. 

Dla **turystów**, śledzenie skomplikowanych, wciąż zmieniających się regulaminów (np. limity czasu, okna jubileuszowe, konieczność opieki, specyficzne wymogi pasm górskich) prowadzi do frustracji i błędów skutkujących odrzuceniem wniosków. 
Z kolei **organizatorzy (administratorzy)** tracą setki godzin na ręczne aktualizowanie danych topograficznych z OpenStreetMap, weryfikowanie Praw Nabytych ze starych roczników oraz sprawdzanie, czy dany szczyt na pewno łapie się do wymogów konkretnej odznaki. System ten nie "myśli" i nie wspiera użytkownika, a jedynie wymaga papierowej biurokracji.

---

## 2. Dla kogo

| Segment | Opis | Główna potrzeba |
|---------|------|-----------------|
| **Turysta (Użytkownik)** | Aktywny piechur, który kolekcjonuje odznaki, zdobywa szczyty i loguje wejścia. | Chce widzieć jasny, grywalizacyjny postęp (Progress Bar), wiedzieć, "gdzie opłaca się pojechać w ten weekend" (Rekomendacje Klastrów), oraz mieć 100% pewność, że jego wejścia spełniają regulamin, *zanim* wyśle książeczkę do PTTK. |
| **Administrator (Kurator Danych)** | Osoba definiująca regulaminy odznak i zarządzająca Złotym Standardem obiektów. | Chce narzędzia, które asynchronicznie załatwi "brudną robotę" z danymi przestrzennymi (OSM/PostGIS), dając szybki, wyklikiwany interfejs do budowania z klocków (reguł JSON) dowolnie skomplikowanych regulaminów. |
| **Weryfikator PTTK** | Działacz odbierający fizyczne książeczki do weryfikacji i przyznania blachy. | Chce ustrukturyzowanej Tablicy Kanban, w której system z góry matematycznie poświadczył poprawność wejść (Set Math, Time Limits), pozostawiając mu jedynie fizyczną kontrolę zdjęć i stempli. |

---

## 3. Wizja systemu

**Wizja:** System Odznak Turystycznych pozwala turystom na bezstresową grywalizację górskich osiągnięć poprzez matematyczną weryfikację logów wejść, a organizatorom na "klockowe", niewymagające pisania kodu definiowanie skomplikowanych regulaminów, dzięki czemu proces zdobywania odznak staje się w pełni cyfrowy, zautomatyzowany i odporny na zmiany w czasie (Bitemporalność i Prawa Nabyte).

---

## 4. Co system NIE jest

- **Nie jest nawigacją turystyczną (Routing GPS).** Nie wyznacza tras, nie mierzy kroków ani przebytych kilometrów na szlaku. Opiera się na weryfikacji punktów docelowych (Point of Interest).
- **Nie jest klonem OpenStreetMap (Data Hoarding).** Zewnętrzne dane są wykorzystywane selektywnie. System utrzymuje autorytatywny, niezależny "Złoty Standard" kuratorowany przez Administratora. Ręczne wpisy mają zawsze priorytet nad automatem (Data Overrides).
- **Nie jest 100% automatem weryfikacyjnym.** Zaufanie do fizycznej obecności turysty na szczycie weryfikuje ostatecznie człowiek (Weryfikator PTTK na podstawie zdjęć/pieczątek w systemie). System potwierdza jedynie legalność regulaminową (daty, wiek, reguły pasm).

---

## 5. Mierniki sukcesu

| Metryka | Cel | Jak mierzyć |
|---------|-----|-------------|
| **Płynność UX Administratora** | < 2 sekundy | Czas odpowiedzi panelu Admina przy renderowaniu i filtrowaniu bazy >10 000 szczytów z użyciem widżetów przypisywania odznak. |
| **Wydajność Filtrowania (CQRS)** | < 150 ms | Czas zapytania bazodanowego zwracającego szczyty do wyboru dla Odznaki na podstawie wyliczonych relacji przestrzennych. |
| **Wydajność Domeny (Ewaluacja)**| < 50 ms | Czas odpowiedzi `VerifyBadgeUseCase` dla turysty posiadającego w historii > 500 wejść na obiekty. |
| **Auto-Resolve (OSM)** | > 90% | Odsetek obiektów importowanych z OSM, które nie wymagają generowania Konfliktów w Skrzynce Odbiorczej (dzięki działaniu Smart Extractora). |

---

## 6. Założenia i ograniczenia

**Założenia:**
- Zdecydowana większość obiektów turystycznych (szczyty, schroniska, zamki) posiada swoje precyzyjne odzwierciedlenie w OpenStreetMap (Overpass API).
- Regulaminy PTTK, bez względu na to, jak skomplikowanie zostały sformułowane w języku naturalnym, dają się ostatecznie sprowadzić do operacji na zbiorach (Set Math) w połączeniu z wektorami czasu.

**Ograniczenia:**
- **Infrastrukturalne:** Zaawansowana analiza przestrzenna i klastrowanie (Radar Bliskości) wymusza oparcie architektury bazy o PostGIS. Nakłada to tzw. *Infrastructure Tax* na projekt – wymaga serwerów i obrazów Docker zdolnych obsłużyć natywne binaria `GDAL/GEOS`.
- **Ewaluacyjne:** Eventual Consistency (Spójność Ostateczna) w warstwie geograficznej. System potrzebuje asynchronicznych cykli (od sekund do minut w Celery), by nowo dodany obiekt stał się pełnoprawnie "widoczny" w filtrach dla Administratora przy zakładaniu odznaki.

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-29 | Dominik / AI Architect | Pierwsza oficjalna, zatwierdzona wersja po zakończeniu architektonicznych Faz A i B, otwierająca drogę do Fazy C. |
| 1.1 | 2026-05-29 | AI Architect | Usunięcie niemierzalnych metryk ludzkich na rzecz weryfikowalnej z poziomu logów wydajności UI (P99 response time dla filtrowania 10 000 szczytów). Korekty edytorskie. |