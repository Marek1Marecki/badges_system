# ADR-011 — Filtrowanie przestrzenne na żądanie (BBox & Hybrydowe Leniwe Wartościowanie)

> **Status:** `accepted`  
> **Data:** 2026-05-30  
> **Autor:** Dominik / AI Architect  

---

## Kontekst

Aplikacja kliencka (moduł odkrywania dla Turysty w Fazie C) będzie przesyłać zapytania o pokolorowane pinezki i obiekty dostępne do zdobycia na ekranie mapy. Na podstawie `ADR-010`, ustalenie koloru konkretnej pinezki wymaga uruchomienia usługi `BadgeEligibilityService`.

Zgodnie z `ARCHITECTURE.md`, aplikacja nie służy do nawigacji (routingu GPS na szlaku), lecz do eksploracji katalogu POI (punktów docelowych). Nawigacja mapowa oznacza w tym kontekście wyłącznie "przesuwanie widoku mapy palcem", co generuje zapytania do bazy danych.

**Pytanie decyzyjne:**  
W którym momencie cyklu życia żądania HTTP należy filtrować zbiór szczytów, aby uniknąć przeciążenia (Over-fetching) i przeciążenia procesora serwera, a jednocześnie maksymalnie wykorzystać zbudowany w ADR-005 zdenormalizowany model odczytu (`ObjectRegionCache`)?

---

## Debata przed decyzją

**Junior Developer:** Kiedy użytkownik ładuje aplikację, możemy pobrać wszystkie 10 000 szczytów z bazy, obliczyć dla nich logikę domenową w `BadgeEligibilityService` i wysłać całość na front.  
**Performance Engineer:** Uruchomienie maszyny ewaluacyjnej dla 10 000 obiektów razy 10 aktywnych odznak to 100 000 iteracji per użytkownik. To klasyczny Over-fetching zabijający CPU serwera w sekundy.  
**DBA:** Mamy już zbudowany `ObjectRegionCache` z ADR-005. Dlaczego nie każemy użytkownikowi po prostu z menu wybrać "Pokaż Tatry", a my zwrócimy mu szybki `JOIN` z tabeli cache, zamiast bawić się we współrzędne?  
**Domain Expert:** Użytkownik chce eksplorować mapę swobodnie (pan & zoom). Ale z drugiej strony, często szuka po regionie. Musimy połączyć te dwa mechanizmy. Nie możemy obciążać PostGISa liczeniem przeciąć geometrycznych (BBox) dla szczytów w Tatrach, jeśli turysta przesuwa mapę po Kaszubach.

*Wniosek z debaty:* Należy zastosować system **Hybrydowy**. Szybki filtr regionalny (CQRS) służy jako "Pre-filter" (odrzucenie 90% bazy bez dotykania funkcji geometrycznych PostGIS). Bounding Box (BBox) służy jako docinarka (ostateczny filtr z użyciem `ST_Within`), przekazująca precyzyjnie przycięty zbiór obiektów (np. 40 sztuk) do usługi domenowej `BadgeEligibilityService`.

---

## Opcje rozważane

### Opcja A: Filtrowanie wyłącznie po regionach tekstowych (CQRS Only)
**Opis:** Klient żąda obiektów podając tekstowe parametry (np. `region=Tatry Wysokie`). Backend odpytuje tylko płaską tabelę `ObjectRegionCache` (zgodnie z ADR-005).
**Plusy:** Ekstremalnie szybki odczyt (czysty SQL JOIN bez żadnej geometrii).
**Minusy:** Całkowicie niekompatybilne ze swobodną nawigacją (pan/zoom) w aplikacji mobilnej. Gdy użytkownik patrzy na styk trzech państw, musiałby jawnie wybrać trzy filtry z listy.

### Opcja B: Wyłącznie Przestrzenne Bounding Box (BBox Filtering) na Geometrii
**Opis:** Zignorowanie `ObjectRegionCache`. Klient wysyła 4 współrzędne widocznego ekranu. PostGIS wykonuje filtr `geom__within=Polygon.from_bbox(...)` dla wszystkich 10 000 obiektów w bazie. Wynik przekazywany jest do leniwego wartościowania w domenie.
**Plusy:** Pełna swoboda nawigacji.
**Minusy:** Odrzuca potężną optymalizację zbudowaną w ADR-005. Zmusza PostGIS do niepotrzebnej analizy indeksu przestrzennego (GiST) dla obiektów leżących setki kilometrów od mapy.

### Opcja C: Filtrowanie Hybrydowe (CQRS Pre-filter + BBox Docięcie)
**Opis:** Aplikacja kliencka oprócz współrzędnych BBox przesyła (jeśli to możliwe) kontekst regionalny lub aplikacja serwerowa w locie mapuje "środek ekranu" na region CQRS. PostGIS wykonuje szybki filt `ObjectRegionCache`, zawężając pulę obiektów z 10 000 do np. 500, a dopiero dla tych 500 odpala funkcję geometryczną `ST_Within` na BBox, redukując wynik do ostatecznych 40 pinezek przekazywanych do `BadgeEligibilityService`.

---

## Decyzja

**Wybrano: Opcja C — Filtrowanie Hybrydowe (CQRS Pre-filter + BBox Docięcie)**

Rozwiązanie to jest optymalnym kompromisem, który w pełni integruje ustalenia z `ADR-005` (szybkie CQRS dla Admina i odfiltrowywania masy danych) z wymogami elastycznego UX opisanymi w `ADR-010` i `ADR-013` (dynamiczna eksploracja wizualna mapy na kafelkach wektorowych/GeoJSON). Chroni ono procesor serwera (zmniejszając rozmiar puli wejściowej dla PostGIS) i zachowuje niską latencję przy ewaluacji domenowej.

---

## Konsekwencje

### Pozytywne
- Optymalizacja użycia indeksów przestrzennych GiST (PostGIS pracuje na ułamku bazy).
- Zapewnienie stałego obciążenia w Czystej Domenie (niezależnie od skali bazy, domena ocenia statystycznie < 50 szczytów na żądanie).

### Negatywne / Ograniczenia
- **Brak zintegrowanego paska postępu z poziomu mapy:** Wyliczanie postępu globalnego (np. "Złota Odznaka: 45/100") będzie wymagało osobnego endpointu REST API omijającego całkowicie BBox i `ObjectRegionCache`, operującego wyłącznie na algebrze zbiorów w `domain/`.
- Ryzyko tzw. "Map Spammingu" przez klienta. Konieczne jest wdrożenie sztywnych mechanizmów dławienia (Throttling) na poziomie warstwy interfejsu (UX).

### Działania wymagane (Do realizacji w Fazie C)
- [ ] Zaprojektowanie endpointu API mapy implementującego potok: `CQRS Prefilter -> BBox Filter -> BadgeEligibilityService -> JSON Response`.
- [ ] Wymuszenie sprzętowego Debounce/Throttling w regułach Frontendowych (zapisane w `AGENT_SPEC.md`).

---

## Warunek rewizji

Gdy natężenie ruchu (setki żądań na sekundę od turystów ruszających palcem po mapie) spowoduje wyczerpanie puli połączeń bazy PostgreSQL (DB Connection Pooling), pomimo filtrowania BBox. Należy wtedy wdrożyć rozwiązania buforujące w oparciu o Kafelki Wektorowe (Vector Tiles, `ST_AsMVT`), w których pre-kompilowane kafelki z przypisanymi identyfikatorami są pobierane w partiach, a ewaluacja koloru odbywa się po stronie urządzenia mobilnego na bazie słownika postępu turysty pobranego jednorazowo przy starcie aplikacji.

---

## Relacje (Related)
- **ADR-005 — Płaski Model Odczytu CQRS:** Kluczowy pre-filtr zdejmujący obciążenie z zapytań przestrzennych BBox.
- **ADR-010 — Dynamiczne kolorowanie mapy i priorytetyzacja stanów odznak:** Wprowadza zależność usługi `BadgeEligibilityService` jako ostatecznego decydenta na dociętym przez BBox zbiorze.
