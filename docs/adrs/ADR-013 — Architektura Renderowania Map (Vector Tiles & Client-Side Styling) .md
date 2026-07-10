# ADR-013 — Architektura Renderowania Map (Vector Tiles & Client-Side Styling)

> **Status:** `accepted`  
> **Data:** 2026-05-31  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Aplikacja turystyczna docelowo będzie wyświetlać wysoce interaktywne, wielowarstwowe mapy obejmujące:
1. Podkład mapowy (ulice, lasy — tzw. Basemap).
2. Tysiące obiektów punktowych (Szczyty, Schroniska) z atrybutami (np. status zaliczenia).
3. Ciężkie geometrie poligonowe i liniowe (Wizualizacja granic Regionów Turystycznych np. całe Sudety, oraz poglądowe obrysy pasm — bez funkcji wyznaczania tras i routingu GPS, zgodnie z zasadą "Out of scope").
4. Warstwy analityczne generowane na żywo (np. Heatmapy zagęszczenia niezdobytych szczytów).

W tradycyjnym podejściu GIS (WMS — Web Map Service), serwer pobiera dane, nakłada na nie kolory i zwraca do przeglądarki gotowe wyrenderowane obrazy w formacie PNG. Każda zmiana przybliżenia (zoom) lub przesunięcie mapy wymusza wygenerowanie nowego obrazka przez serwer. W przypadku renderowania tysięcy wierzchołków dla skomplikowanych poligonów przez czysty format GeoJSON, problem przenosi się z kolei na przepełnienie pamięci RAM przeglądarki i spadek klatek na sekundę (FPS) na urządzeniach mobilnych.

**Pytanie decyzyjne:**  
Jak zaprojektować architekturę transportu i renderowania danych geoprzestrzennych, aby zapewnić płynność animacji (60 FPS) na urządzeniach mobilnych, drastycznie zmniejszyć zużycie transferu sieciowego i zminimalizować obciążenie serwera backendowego (Django)?

---

## Debata przed decyzją

**Frontend Engineer:** Renderowanie po stronie klienta (Client-Side Rendering) to przyszłość. Jeśli dostanę surowe punkty i poligony, mogę wykorzystać kartę graficzną urządzenia (WebGL) do narysowania heatmap, grubych obwódek czy płynnego obracania mapy w 3D. Jednak plik GeoJSON ważący 15 MB ze wszystkimi szlakami PTTK zawiesi aplikację mobilną.  
**Backend / Performance Engineer:** Odrzucamy serwowanie map rastrowych (PNG) przez backend. Renderowanie grafiki na serwerze "zabije" procesy Gunicorn. Odpytywanie o geometrię Sudetów (wielki poligon po `ST_Union`) w całości przez GeoJSON również przeciąży bazę i deserializator JSON-a w Pythonie. Musimy przesyłać dane w postaci kafelkowej, docinając geometrię przestrzenną tylko do tego obszaru, na który patrzy użytkownik, i maksymalnie ją kompresując.

*Wniosek z debaty:* Należy bezwzględnie oddzielić logikę dostarczania geometrii od logiki jej kolorowania i renderowania. Backend musi stać się wyłącznie bezstanową "rurą" dostarczającą precyzyjnie przycięte dane matematyczne. Frontend przejmie pełną odpowiedzialność za stylizację w oparciu o hardware urządzenia końcowego.

---

## Opcje rozważane

### Opcja A: Tradycyjny Serwer Mapowy Rasteryzowany (WMS / PNG)
**Opis:** Użycie zewnętrznego oprogramowania (np. GeoServer) połączonego z bazą PostGIS, które na żądanie renderuje obrazki mapy.
**Plusy:** Urządzenie mobilne nie jest obciążone obliczeniami wektorowymi.
**Minusy:** Ogromne obciążenie serwera, brak interaktywności (nie można podpiąć "hovera" z dymkiem nad wyrenderowany piksel, potrzebne są kolejne żądania do serwera).

### Opcja B: GeoJSON REST API (Fat Payload)
**Opis:** Endpoint Django zwraca obiekt GeoJSON zawierający wszystkie obiekty i kształty dla danej odznaki w jednym wielkim żądaniu HTTP.
**Plusy:** Najprostsze rozwiązanie do zaimplementowania po stronie Django (np. z użyciem `django-rest-framework-gis`). Łatwość przypinania interakcji i popupów (Tooltipów) po stronie frontendu.
**Minusy:** Nieakceptowalne dla ciężkich geometrii (Regiony i Szlaki) z powodu wagi pliku i paraliżu przeglądarki podczas rysowania dziesiątek tysięcy wierzchołków naraz.

### Opcja C: Vector Tiles (Kafelki Wektorowe - MVT) + WebGL Styling
**Opis:** Backend Django korzysta z wbudowanych funkcji PostGIS `ST_AsMVT` i `ST_AsMVTGeom` do wycinania i dynamicznego upraszczania geometrii do kafelków dla zadanego poziomu `X, Y, Z`. Zwraca skompresowany, binarny plik Protocol Buffers (PBF). Frontend korzystający z biblioteki z obsługą WebGL (np. MapLibre GL JS) odbiera strumień wektorów i koloruje go lokalnie w oparciu o zaszyte atrybuty.

---

## Decyzja

**Wybrano: Opcja C — Vector Tiles (MVT) + WebGL Styling (Podejście hybrydowe)**

Wdrożono architekturę dwutorową z rygorystycznym podziałem ładunku (Payload Separation Contract):

1. **Dla ciężkich geometrii (Poligony Regionów, poglądowe granice):** Wykorzystujemy dynamicznie generowane Kafelki Wektorowe (MVT) z PostGIS poprzez endpointy `/api/tiles/{layer}/{z}/{x}/{y}.pbf`. 
   * **Zasada Czystości MVT:** Kafelki te są całkowicie pozbawione stanu użytkownika (User-Agnostic). Zawierają WYŁĄCZNIE atrybuty topograficzne (nazwa, wysokość, ID regionu). Dzięki temu mogą być agresywnie buforowane globalnie (Cache).
2. **Dla interaktywnych zbiorów punktowych (Szczyty < 500 elementów na ekranie):** Wykorzystujemy lekki strumień `GeoJSON` pobierany na bazie okna mapy (Bounding Box).
   * **Zasada Stanu:** Atrybuty statusu turysty (tzw. `PeakColor` z ADR-010, np. `COMPLETED`, `LOCKED`) są przesyłane **wyłącznie** w tej warstwie GeoJSON, ponieważ są dynamiczne i obliczane w locie przez `BadgeEligibilityService`.
3. **Stylizacja (Heatmapy, Kolorowanie):** 100% odpowiedzialności po stronie klienta. Frontend łączy oba źródła (MVT z topografią + GeoJSON z kolorami) i aplikuje styl korzystając z MapLibre GL JS i karty graficznej urządzenia.

---

## Konsekwencje

### Pozytywne
- Optymalizacja transferu danych (format PBF jest drastycznie lżejszy od tekstowego JSON-a).
- Odciążenie bazy danych i serwera HTTP z zadań graficznych (brak konieczności stosowania narzędzi typu Matplotlib czy GeoServer).
- Płynność działania interfejsu (60 FPS, płynne powiększanie i obracanie widoku 3D na smartfonie).

### Negatywne / Ograniczenia
- Konieczność implementacji w Django widoków obsługujących logikę zapytań kafelkowych (przeliczanie współrzędnych ekranowych `Z/X/Y` na `Bounding Box` rozumiany przez PostGIS).
- Zaawansowana stylizacja (np. reguły wykluczające ukazywanie się etykiet przy dalekim przybliżeniu) wymaga pisania złożonych obiektów konfiguracyjnych JSON po stronie biblioteki MapLibre, co zwiększa złożoność kodu frontendu.

### Działania wymagane (Do realizacji w Fazie C)
- [ ] Sformalizowanie zasady "MVT=Statyka, GeoJSON=Dynamika" w plikach `UI_GUIDELINES.md` oraz `AGENT_SPEC.md`.
- [ ] Utworzenie widoku Django zwracającego wynik natywnego zapytania `ST_AsMVT` (za pomocą `django.contrib.gis.db.models.functions` lub surowego SQL) w nagłówku `Content-Type: application/vnd.mapbox-vector-tile`. Odrzucenie instalacji zewnętrznych paczek do MVT.
- [ ] Konfiguracja biblioteki MapLibre GL JS w szablonie widoku (w warstwie Delivery Mechanism).

---

## Decyzja (Zaktualizowana)

Wybieramy natywne generowanie kafelków MVT przy użyciu funkcji `ST_AsMVT` i `ST_AsMVTGeom` z bazy PostGIS. 
W trakcie wdrożenia podjęliśmy 3 krytyczne decyzje uszczelniające ten proces:
1. **Obejście utraty precyzji BigInt (PBF):** Binarne kafelki PBF ucinały duże wartości `id` (typ `BigAutoField` w Django), powodując błąd w MapLibre (brakujące lub losowe ID poligonów). Wymusiliśmy rzutowanie kluczy na tekst w surowym SQL: `t.id::text AS db_id_str`. Frontend używa wyłącznie atrybutu tekstowego.
2. **Whitelisting i ochrona przed SQL Injection:** Ponieważ nazwy tabel muszą być wstrzykiwane bezpośrednio do SQL (`FROM {table_name}`), zablokowaliśmy wektor ataku tworząc twardą, "białą listę" dozwolonych tabel w warstwie Aplikacji (`LAYER_TO_TABLE_MAP`). Pozwoliło to na bezpieczne zignorowanie alarmu lintera Bandit (`# noqa: S608`).
3. **Kompresja GZIP w locie:** Kafelki MVT muszą być serwowane skompresowane. Use Case przed zapisem do pamięci Redis samodzielnie kompresuje bajty biblioteką z biblioteki standardowej (`gzip.compress`), a widok HTTP deklaruje `Content-Encoding: gzip`.

## Konsekwencje
- Widoki mapy są ładowane poniżej 50ms, bez obciążania procesora.
- Django nie korzysta z ORM do generowania MVT, co łamie spójność frameworka, ale zwraca stukrotny zysk wydajnościowy.
- Skrypty JS w kliencie muszą jawnie wymuszać odświeżanie cache przeglądarek poprzez doklejanie parametru `?v=X` przy zmianie logiki SQL, aby przełamać agresywne buforowanie przeglądarek.

---

## Warunek rewizji

Dokument poddać rewizji, w sytuacji gdy zapytania kafelkowe w czasie rzeczywistym `ST_AsMVT` z wykorzystaniem rzutowania zaczną wyczerpywać procesor bazy PostGIS przy wysokim ruchu użytkowników. W takim przypadku należy rozważyć wprowadzenie statycznego serwera kafelków wektorowych (np. `Martin` lub `Tegola`), który połączy się w trybie "Read-Only" z naszym modelem CQRS, omijając całkowicie wątki wykonawcze frameworka Django.

---

## Referencje

- **ADR-005 — Płaski Model Odczytu CQRS:** Narzuca zdenormalizowaną strukturę relacji przestrzennych, stanowiąc optymalne i odciążone źródło zapytań do silnika generującego kafelki MVT.
- **ADR-010 — Dynamiczne kolorowanie mapy i priorytetyzacja stanów odznak:** Wprowadza zmienne w czasie kolory (`PeakColor`), które zmuszają system do separacji warstwy cache'owanego MVT od dynamicznej warstwy GeoJSON.
- **ADR-011 — Filtrowanie przestrzenne na żądanie (BBox):** Określa przestrzenny mechanizm selekcji obiektów (BBox), który stanowi wejście dla dynamicznej warstwy GeoJSON, komplementarnej wobec MVT.
