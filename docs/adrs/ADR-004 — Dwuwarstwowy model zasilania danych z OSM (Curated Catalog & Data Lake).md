# ADR-004 — Dwuwarstwowy model zasilania danych z OSM (Curated Catalog & Data Lake)

> **Status:** `accepted`  
> **Data:** 2026-05-30  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Aplikacja wymaga zarządzania tysiącami obiektów turystycznych (szczyty, schroniska, przełęcze). Ręczne wprowadzanie współrzędnych i wysokości dla takiej skali jest podatne na błędy i nieefektywne. Naturalnym źródłem danych jest OpenStreetMap (OSM) oraz jego interfejs Overpass API.

OSM charakteryzuje się jednak płynnym schematem (tzw. wolna amerykanka tagów). Pojedynczy węzeł może posiadać kilkadziesiąt tagów, z których większość jest dla systemu odznak bezużyteczna, ale niektóre stają się kluczowe dopiero w określonym kontekście (np. `name:sk` dla szczytów przygranicznych). Ponadto otwarty charakter OSM naraża nasze dane na wandalizm (np. celowe zmiany nazw szczytów).

**Pytanie decyzyjne:**  
Jak zintegrować system z OpenStreetMap, aby zautomatyzować proces wprowadzania obiektów, jednocześnie zabezpieczając bazę danych przed schematycznym chaosem, wandalizmem i utratą użytecznych w przyszłości tagów?

---

## Debata przed decyzją

**Data Engineer:** Jeśli odrzucimy z odpowiedzi OSM wszystko poza `name` i `ele`, a za rok PTTK stworzy odznakę wymagającą nazw historycznych (tag `alt_name:de`), będziemy musieli pisać skrypty uderzające ponownie do API OSM dla wszystkich obiektów w bazie. Z drugiej strony, tworzenie kolumny w PostgreSQL dla każdego możliwego tagu OSM skończy się potężną macierzą rzadką (Sparse Matrix).

**Domain Expert / Administrator:** PTTK opiera się na tradycji, a OSM na dynamicznych zmianach. Jeśli geodeta w OSM zmieni wysokość szczytu o 1 metr, to nie może automatycznie wpływać na weryfikację odznak. System musi pozwalać administratorowi na "twarde" nadpisanie danych z OSM (Data Override), a raz wpisana ręcznie nazwa szczytu nie może być po cichu nadpisana przez automat synchronizujący.

**Security / Reliability Engineer:** OSM Overpass API to zewnętrzny endpoint bez SLA. Co się dzieje, gdy serwery ulegną awarii lub zablokują nasze IP? Czy padnie weryfikacja odznak lub cały panel administracyjny? Musimy rozdzielić proces pobierania danych od reszty systemu.

*Wniosek z debaty:* Potrzebujemy modelu asynchronicznego i hybrydowego, gdzie surowe dane są archiwizowane, a oficjalne dane PTTK są filtrowane i ściśle nadzorowane przez administratora, bez blokowania systemu przy awariach Overpass API.

---

## Opcje rozważane

### Opcja A: Pełne lustrzane odbicie (Mirroring)
**Opis:** Automatyczne pobieranie i regularne, bezwarunkowe nadpisywanie danych w bazie na podstawie zmian w OSM. Baza danych staje się lokalną kopią OSM.
**Plusy:**
- Zawsze aktualne dane.
**Minusy:**
- Podatność na wandalizm (błędy w OSM natychmiast psują system PTTK).
- Brak możliwości wprowadzania obiektów historycznych lub zniszczonych, które usunięto z mapy.
- Narzut na zarządzanie setkami niepotrzebnych atrybutów.

### Opcja B: Selektywny Import typu "Fire and Forget"
**Opis:** Przy tworzeniu obiektu, system pyta Overpass API, wyciąga 3-4 z góry ustalone atrybuty (nazwa, wysokość, współrzędne) do kolumn SQL, a całą resztę odpowiedzi JSON bezpowrotnie odrzuca.
**Plusy:**
- Bardzo czysty i przewidywalny schemat relacyjny.
**Minusy:**
- Brak perspektywiczności (Future-proofing). Utrata danych (np. linków do Wikipedii), które w przyszłości mogłyby się przydać.

### Opcja C: Dwuwarstwowy model hybrydowy (Data Lake + Curated Catalog)
**Opis:**
Zastosowanie architektury dwufazowej w jednym modelu bazy danych:
1. **Data Lake:** Cały surowy JSON pobrany z OSM zapisywany jest nienaruszony w kolumnie `osm_raw_tags` (typu `JSONB`).
2. **Curated Fields:** Konkretne kolumny relacyjne (np. `name`, `altitude`, `geom`).
3. **Smart Extractor:** Adapter (`OsmDataExtractor`), który selektywnie przepompowuje dane z punktu 1 do punktu 2, ale **tylko** jeśli administrator nie wypełnił ich wcześniej ręcznie (Data Override).

---

## Decyzja

**Wybrano: Opcja C — Dwuwarstwowy model hybrydowy (Data Lake + Curated Catalog)**

Decyzja ta idealnie godzi potrzebę elastyczności z rygorem jakości danych. Zapisywanie całego ładunku JSON z OSM nic nie kosztuje (minimalny narzut dyskowy), a tworzy archiwum (`Data Lake`), z którego w każdej chwili można czerpać nowe dane bez odpytywania zewnętrznego API.
Podejście "ręczne zmiany wygrywają z automatem" (Data Overrides) zabezpiecza biznesową integralność katalogu PTTK. Jeśli obiekt zniknie z OSM, jego zdenormalizowane dane pozostaną nienaruszone, chroniąc historię zdobytych odznak.

---

## Konsekwencje

### Pozytywne
- **Future-proofing:** System jest gotowy na nowe wymagania informacyjne bez ponownego importu.
- **Ochrona przed wandalizmem:** Mechanizm aktualizacji OSM odnotowuje zmiany cicho w `JSONB`, ale na poziomie Curated Fields generuje tylko rekomendacje (Skrzynka Konfliktów do akceptacji).

### Negatywne / Ograniczenia
- Lekka duplikacja danych: np. nazwa "Śnieżka" figuruje zarówno w kolumnie `name`, jak i głęboko wewnątrz struktury `osm_raw_tags`.
- **Niedostępność API Overpass blokuje zasilanie nowych obiektów** — ryzyko to obsłużono przez mechanizm retry w Celery (max 15 prób z liniowym backoffem). Co najważniejsze, nie blokuje to bieżącej pracy (panelu admina) ani weryfikacji odznak opartej na danych już zaimportowanych do systemu.

### Działania wymagane (Zrealizowane)
- [x] Stworzenie kolumn `osm_id`, `osm_raw_tags`, `osm_version`, `osm_timestamp` w modelu `TouristObject`.
- [x] Napisanie adaptera `OsmDataExtractor` faworyzującego polskie nazwy.
- [x] Zaimplementowanie mechanizmu zapobiegającego nadpisywaniu pól wypełnionych ręcznie przez Administratora (Data Overrides).
- [x] Asynchroniczne aktualizacje: stworzenie "Nocnego Stróża" weryfikującego stan obiektów w tle.

---

## Warunek rewizji

Dokument poddać rewizji, w przypadku gdy liczba obiektów zasilanych z OSM przekroczy kilkaset tysięcy, co uczyniłoby utrzymywanie pełnych zrzutów `JSONB` dla każdego węzła nieefektywnym. Wtedy należy rozważyć przejście na własny serwer replikacji OSM (np. przez `osm2pgsql`).

---

## Referencje
- Kontrakt konfiguracyjny z infrastrukturą: Wykorzystanie asynchronicznego Skanera OSM (Celery Beat) minimalizuje ryzyko przekroczenia limitów API serwerów Overpass.
