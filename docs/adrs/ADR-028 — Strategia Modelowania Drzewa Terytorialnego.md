# ADR-028 — Strategia Modelowania Drzewa Terytorialnego (Hierarchia Regionów)

> **Status:** `accepted`  
> **Data:** 2026-09-03  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** Architektura z 7 oddzielnymi modelami geograficznymi (Faza MVP).  
> **Zastąpiony przez:** —  
> **Powiązane:** AUDYT-055 (PD-01), ADR-024 (Strategia Migracji), ADR-026 (PostgreSQL Volume Layout), ADR-028 (nadrzędny rejestr)

---

## Kontekst

W Fazie MVP system bazował na wysoce znormalizowanej, 7-poziomowej strukturze tabel geograficznych (`CountryModel` -> `VoivodeshipModel` -> `ProvinceModel` -> ... -> `MesoregionModel`). Stanowiło to doskonałe odwzorowanie logiczne, jednak wygenerowało ogromny dług wydajnościowy dla silnika relacyjnego PostgreSQL. Każde odtworzenie pełnej ścieżki regionu lub wyliczenie szczytów w obrębie danego województwa i jego jednostek podległych wymagało 6 połączonych klauzul `JOIN`. W benchmarkach dla 10 000 obiektów czas odpowiedzi sięgał 45-50ms, co naruszało założenia Opcji Skalowalności z `AUDYT-055`.

Ze względu na specyfikę biznesową (granice fizyczno-geograficzne i administracyjne państw zmieniają się niezwykle rzadko), priorytetem jest optymalizacja odczytów podziału terytorialnego, przy akceptacji wyższych kosztów zapisu (modyfikacji węzłów).

**Pytanie decyzyjne:**  
Jak zrekonstruować schemat relacyjny drzewa terytorialnego, by zminimalizować złożoność zapytań SQL (`JOIN`), umożliwiając błyskawiczne filtrowanie obiektów PTTK dla zapytań przestrzennych i analitycznych na dużą skalę?

---

### Opcje rozważane

### Opcja A: Adjacency List (Wzorzec `parent_id`)
**Opis:** Konsolidacja 7 tabel do jednej (`RegionModel`), wykorzystującej rekurencyjny klucz obcy do samej siebie (`parent_id`).  
**Plusy:** Natywne wsparcie Django (szybka implementacja bez specjalnych typów danych). Prosta edycja w panelu Admina.  
**Minusy:** Brak natywnego indeksowania "poddrzew" (descendants). Pobieranie ścieżki wymaga skomplikowanych zapytań `CTE WITH RECURSIVE`, co na poziomie >5 warstw zagnieżdżenia nadal generuje wysokie obciążenie (powyżej 35ms w skrajnych przypadkach).  

### Opcja B: Materialized Views (Status Quo z warstwą pre-kalkulacyjną)
**Opis:** Pozostawienie 7 tabel, lecz dobudowanie zapytania MView generującego płaską strukturę w tle.  
**Plusy:** Brak konieczności migracji danych oraz zmiany logiki importu OSM.  
**Minusy:** Uciążliwe i długotrwałe odświeżanie widoków (Refresh). Narzut na logikę aplikacyjną przy każdym dodanym regionie.  

### Opcja C: Implementacja `Ltree` w modelu hybrydowym (Wybrane)
**Opis:** Skonsolidowanie 7 tabel w jeden model `RegionBaseModel` wykorzystujący pole `level_enum`. Implementacja rozszerzenia PostgreSQL `ltree`, gdzie każde drzewo reprezentowane jest ścieżką wektorową (np. `pl.slaskie.przykatury.kamien_zamkowy`).  
**Plusy:**  
- Absolutna dominacja w odczytach (O(1)). Indeksy GiST na ścieżce `ltree` pozwalają na wyciągnięcie pełnego poddrzewa w czasie <2ms przy 10k rekordach.  
- Zdolność błyskawicznego wyciągania "chlebowych okruszków" (Breadcrumbs) dla SEO w widokach aplikacji.  
**Minusy:**  
- Zmiana korzenia w drzewie (np. przeniesienie gminy do innego powiatu) zmusza do wykonania operacji `UPDATE path` dla wszystkich dzieci (wysoki koszt).  

---

## Decyzja

Wybieramy **Opcję C: Wdrożenie `ltree` z podejściem Hybrydowym (CQR- na poziomie modelu)**.

1. **Konsolidacja Modeli:** System zostanie zmigrowany do jednej płaskiej tabeli bazowej `regions_flat`. Obecne 7 poziomów zostanie zredukowane do kolumny `level` (wyliczenie Enum).  
2. **Hybrydowe Zarządzanie Drzewem:** Ponieważ panel administracyjny Django nie radzi sobie natywnie i intuicyjnie z edycją wpisów tekstowych `ltree` przez operatora PTTK:  
   - Tabela nadal zachowa kolumnę `parent_id` (ForeignKey) wyłącznie dla celów edycji i weryfikacji relacyjnej przez formularze (Command / Wpis).  
   - Tabela otrzyma nową kolumnę `path` typu `ltree` wykorzystywaną wyłącznie do odczytów przestrzennych (Query / Odczyt).  
   - Przebudowa pola `path` (generowanie ścieżki z `parent_id`) następuje asynchronicznie za pomocą sygnału Django `post_save` po udanym operowaniu na modelu w Adminie, ukrywając logikę `ltree` przed użytkownikiem.  
3. **Zgodność z Czystą Domeną:** W modelu domenowym `RegionHierarchyDomain` ścieżka funkcjonuje wyłącznie jako standardowy Value Object typu "String-List", co całkowicie odcina Czystego Pythona od wiedzy na temat wdrożenia `ltree` na poziomie silnika bazy.  

---

## Konstrukcja ścieżki `ltree`

Ścieżka budowana jest z **lowercase, url-safe segmentów** oddzielonych kropką:

```
pl                                         # Country
  .slaskie                                 # Voivodeship (code: SL)
    .pruska                               # Province
      .karpacz                            # Subprovince
        .beskidy                          # Macroregion
          .jasien                         # Mesoregion
            .kasprowy                     # Tourist Region (najniższy)
```

- Segmenty: `code` (max 100 znaków) → `lower()` + URL-slug.  
- Brak `parent_id` (root) → `path = 'pl'`.  
- `level` jako ENUM (`CountryEnum`).

---

## Konsekwencje

### Pozytywne
- Błyskawiczne filtrowanie regionów i podregionów na mapach wektorowych HTMX.  
- Likwidacja 6 zbędnych modeli ORM i znaczne uproszczenie zapytań.  
- Wyeliminowanie cykli `JOIN`, redukując obciążenie puli połączeń przy `pgBouncer`.  

### Negatywne / Działania wymagane
- Konieczność włączenia instrukcji `CREATE EXTENSION IF NOT EXISTS ltree;` w specjalnej, wstępnej migracji Django (wymaga uprawnień SuperUsera dla roli zasilającej bazę w środowiskach TEST i PRE-PROD, zgodnie z ADR-026).  
- Kosztowna i ryzykowna pierwsza migracja danych: wymaga napisania zaawansowanego skryptu (`RunPython`), który podczas wdrożenia zmapuje dotychczasowe rekordy z 7 osobnych tabel do jednej tabeli `regions_flat`, przepisze ich klucze główne, a na końcu wymusi aktualizację ID w tabeli logów i odznak (Potężna migracja destrukcyjna objęta prawami z ADR-024).  

---

## Warunek rewizji

Strategia zakłada statyczność podziału. Dokument podlega rewizji w przypadku radykalnej zmiany logiki biznesowej, np. w której regiony PTTK definiowane są całkowicie dynamicznie na podstawie siatki kartograficznej niezależnej od państwowego podziału terytorialnego i krzyżują się ze sobą swobodnie z dnia na dzień (wymagając modelu wielokrotnego dziedziczenia).
