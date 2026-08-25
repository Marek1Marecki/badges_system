# ADR-006 — Klastrowanie bliskości i pojęcie Rodzica (Radar 150m i Skrzynka Odbiorcza)

> **Status:** `accepted`  
> **Data:** 2026-05-26  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Zasilanie bazy danymi z OpenStreetMap (OSM) skutkuje zjawiskiem wysokiego zagęszczenia obiektów (Points of Interest - POI). W jednym miejscu fizycznym (np. na szczycie Skrzycznego) znajdują się wyodrębnione węzły dla: Szczytu, Wieży Widokowej, Schroniska i Tablicy Pamiątkowej. 

Dla systemu odznak i wyświetlania map to ogromny problem z dwóch powodów:
1. **Wizualny Spam (Cluttering):** Frontend próbujący wyrenderować 4 nakładające się na siebie pinezki na dalekim przybliżeniu (zoom) mapy tworzy nieczytelną plamę.
2. **Logika Grywalizacji (Gamification):** Turysta odwiedzający Skrzyczne zalicza jedną, fizyczną "wycieczkę". System powinien umieć wycenić ten obszar (Klaster) zbiorczo (np. "W tym miejscu zdobędziesz 2 punkty do 2 różnych odznak"), a nie traktować ich jako całkowicie odizolowanych wędrówek.

**Pytanie decyzyjne:**  
Jak grupować blisko leżące obiekty w logiczne klastry, zachowując wysoką wydajność dla frontendu, nie tracąc tożsamości poszczególnych obiektów i minimalizując zjawisko *False Positives* (np. łączenia dwóch bliskich, ale oddzielnych i wybitnych szczytów)?

---

## Debata przed decyzją

**Frontend Engineer:** Potrzebuję mechanizmu grupowania już na poziomie bazy danych. Jeśli dostanę 10 000 niesklastrowanych punktów i będę musiał liczyć ich zagęszczenie w przeglądarce klienta za pomocą algorytmów w JavaScript, stracimy klatki na sekundę (FPS) na urządzeniach mobilnych, a aplikacja wyczerpie baterię telefonu. Potrzebuję gotowych, "zakotwiczonych" klastrów z backendu.

**Data Scientist:** Możemy uruchomić algorytm klastrowania gęstościowego (np. DBSCAN w PostGIS) i robić to całkowicie automatycznie w nocy. Zgrupujemy wszystko, co leży w promieniu 150 metrów.
*Kontrargument Eksperta Domenowego (PTTK):* Pełna automatyzacja zniszczy system. Dwa szczyty mogą leżeć blisko siebie na mapie, ale być oddzielone przepaścią i stanowić odrębne cele turystyczne. Z kolei schronisko i szczyt o tej samej nazwie to niemal zawsze ten sam cel. Algorytm tego nie wie – system musi mieć ostateczną autoryzację człowieka (Human-in-the-loop).

**Security / Data Integrity Engineer:** Rekurencyjny klucz obcy (`parent_object`) stwarza ryzyko powstania cykli w grafie bazy danych (np. A jest rodzicem B, a B staje się rodzicem A). Może to spowodować nieskończoną pętlę przy odpytywaniu o strukturę klastra. Django natywnie nie pilnuje tego na poziomie SQL. Jeśli wprowadzamy ten mechanizm, akceptujemy to ryzyko i musimy go pilnować na poziomie walidacji w aplikacji.

---

## Opcje rozważane

### Opcja A: Automatyczne klastrowanie w locie na podstawie geometrii
**Opis:** Przy każdym żądaniu o mapę/obiekty, baza (PostGIS) grupuje obiekty w oparciu o ich aktualne współrzędne i bufor przestrzenny.
**Plusy:**
- Brak potrzeby przechowywania relacji i stanu w bazie danych.
**Minusy:**
- Koszmar wydajnościowy dla bazy danych.
- Całkowity brak kontroli nad wyjątkami (brak uwzględnienia specyfiki terenu).

### Opcja B: Fuzja danych (Data Merging / Destructive)
**Opis:** Kiedy importujemy schronisko leżące 50 metrów od szczytu, nadpisujemy obiekt "Szczyt" dodając mu tag `has_hut=True` i fizycznie usuwamy schronisko z tabeli jako osobny byt.
**Plusy:**
- Idealnie czysta mapa, jeden punkt równa się jednemu obiektowi.
**Minusy:**
- Łamie zasadę zachowania Złotego Standardu. Utrata OSM ID dla zniszczonego obiektu.
- Uniemożliwia zbudowanie odznaki typu "Szlak Schronisk", bo schronisko przestałoby być niezależnym celem z własnymi regułami.

### Opcja C: Hierarchia "Rodzic-Dziecko" z asynchronicznym radarem (Inbox Pattern)
**Opis:** Do `TouristObject` dodajemy pole `parent_object` (rekurencyjny klucz obcy). Tworzymy osobną tabelę `ProximityCandidate` (Skrzynka Odbiorcza). Asynchroniczny skaner (Celery) w nocy przeszukuje bazę dla nowych obiektów bez rodzica używając `ST_DWithin(150m)`. Wyniki lądują w Skrzynce. Administrator przegląda listę par i jednym kliknięciem przypina relację: "Szczyt X jest Rodzicem dla Schroniska Y" (lub odrzuca relację).

---

## Decyzja

**Wybrano: Opcja C — Hierarchia "Rodzic-Dziecko" z asynchronicznym radarem (Inbox Pattern)**

Zastosowanie wzorca *Human-in-the-loop* (Człowiek w pętli) rozwiązuje problem zaufania do algorytmów przestrzennych w trudnym terenie górskim. Pole `parent_object` staje się "Kotwicą Klastra" (Cluster Anchor), co pozwala frontendowi na błyskawiczne pobieranie z bazy zgrupowanych obiektów bez wykonywania drogiej matematyki.
Rozdzielenie skanowania przestrzennego (PostGIS w Celery) od zatwierdzania (Django Admin) likwiduje opóźnienia w interfejsie i zjawisko *Alert Fatigue* (zmęczenia ostrzeżeniami — sytuacja, w której administrator widząc setki irytujących powiadomień podczas zwykłej pracy zaczyna je ignorować lub akceptować bez czytania).

---

## Konsekwencje

### Pozytywne
- **Wydajność UX (Gamifikacja):** Backend może wprost połączyć odznaki turysty z relacjami `parent_object` w milisekundy, obliczając "wartość wycieczki" dla konkretnego klastra punktów, nie obciążając bazy GIS.
- Nienaruszone dziedzictwo danych OSM — każdy obiekt zachowuje swoją tożsamość, geometrię i metadane w tabeli `TouristObject`.

### Negatywne / Ograniczenia
- **Ryzyko pętli (Data Integrity):** Brak zabezpieczenia na poziomie bazy danych (constraintów) przed zapętleniem się rodziców (Cykliczny Graf). Administrator może omyłkowo stworzyć cykl przy ręcznej edycji, co należy udokumentować jako dług techniczny do zabezpieczenia w warstwie formularzy Django.
- **Dług Operacyjny:** Administrator musi regularnie (np. raz w tygodniu po masowym imporcie z OSM) przeglądać i "przeklikiwać" Skrzynkę Odbiorczą. W przypadku potężnych importów lista może wynosić setki pozycji.

### Działania wymagane (Zrealizowane)
- [x] Dodanie pola `parent_object` do modelu `TouristObject` (relacja `self`).
- [x] Utworzenie modelu technicznego `ProximityCandidate` do magazynowania znalezionych par.
- [x] Opracowanie zadania `scan_proximity_candidates_task` z użyciem `ST_DWithin(150m)`.
- [x] Wdrożenie masowych akcji w Django Adminie (`make_a_parent`, `ignore_pair`), pozwalających rozwiązywać propozycje klastrowania bezpośrednio z listy.
- [x] Implementacja logiki Auto-Resolve dla "rodzeństwa" (skrypt w panelu admina automatycznie zamyka i ignoruje pary w skrzynce odbiorczej, jeśli dla obu obiektów przypisano już wspólnego rodzica).

---

## Warunek rewizji

Gdy baza obiektów urośnie do dziesiątek tysięcy punktów per region, a czas pracy administratora na "przeklikiwanie" Skrzynki Odbiorczej przekroczy kilka godzin tygodniowo. Wtedy należy rozważyć wdrożenie prostej heurystyki lub modelu ML (Machine Learning), który dokonywałby automatycznego klastrowania w trybie Auto-Accept w oparciu o słownik typów (np. systemowa reguła: *Jeżeli obok siebie leżą `PEAK` i `HUT`, `PEAK` zawsze staje się rodzicem, omijaj Inbox*).

---

## Relacje (Related)
- **Dług (Debt):** Ryzyko cyklicznego grafu w relacji `parent_object` — brak zabezpieczenia na poziomie bazy danych (constraintów) przed zapętleniem się rodziców; wymaga walidacji w warstwie aplikacji. Dług operacyjny: Administrator musi regularnie przeglądać Skrzynkę Odbiorczą.
- **ADR-005 — Płaski Model Odczytu CQRS:** Decyzja komplementarna, zdejmująca z głównej pętli żądań HTTP kosztowne obliczenia przestrzenne.
