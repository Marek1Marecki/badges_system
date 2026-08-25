   # ADR-003 — Silnik Reguł Biznesowych (Wzorzec Strategii + JSONB)

> **Status:** `accepted`  
> **Data:** 2026-05-26  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

System ma za zadanie weryfikować poprawność zdobywania setek odznak turystycznych PTTK. Analiza regulaminów wykazała ekstremalne zróżnicowanie wymagań (np. limity czasu, minimalny i maksymalny wiek, wymóg posiadania innej odznaki, zamknięte okna jubileuszowe, konieczność opieki dorosłych). 

Nowe regulaminy wprowadzają unikalne, nieprzewidywalne reguły, które nie występują w żadnych innych odznakach (np. "zdobądź obiekty w 30 z 38 pasm" lub "wymaga daty zapisu do klubu").

**Pytanie decyzyjne:**  
W jaki sposób modelować i przechowywać reguły weryfikacyjne dla poszczególnych wersji odznak, aby system był wysoce wydajny, otwarty na rozbudowę i nie wymagał modyfikacji schematu bazy danych przy dodawaniu nowych typów ograniczeń?

---

## Debata przed decyzją

**Backend/Performance Engineer:** Czy ciągła hydracja danych z JSONB do obiektów domenowych (tworzenie klas, parsowanie dat ze stringów) przy każdej weryfikacji nie zrujnuje wydajności aplikacji? Co jeśli system będzie przetwarzał weryfikację 10 000 użytkowników jednocześnie?
*Wniosek:* Skala użycia tego systemu to lokalna turystyka (organizacje PTTK), a nie infrastruktura BigTech. Weryfikacje są wyzwalane punktowo (żądanie turysty w aplikacji) lub w niewielkich partiach. Koszt hydracji kilku reguł to mikrosekundy, co jest całkowicie pomijalnym narzutem w zestawieniu z kosztami utrzymania zdenormalizowanego schematu SQL.

**Security Engineer:** Czy wstrzykiwanie danych z JSONB bezpośrednio do klas Pythona nie rodzi ryzyka Insecure Deserialization (wstrzyknięcia złośliwego kodu)?
*Wniosek:* JSONB jest bezpieczny z dwóch powodów. Po pierwsze, wprowadzają go wyłącznie uwierzytelnieni administratorzy systemu (chronione walidacją JSON Schema). Po drugie, na granicy infrastruktury i domeny zbudowano rygorystyczne fabryki (`RULE_BUILDERS`), które wymuszają sprawdzanie kluczy i rzucają twardy `ValueError`, blokując wszelkie nieznane parametry przed wejściem do Czystej Domeny.

---

## Opcje rozważane

### Opcja A: Twarde modelowanie relacyjne (Szerokie tabele / Kolumny logiczne)

**Opis:** Każda możliwa reguła to osobna kolumna w tabeli `BadgeVersionModel` (np. `min_age_required`, `max_age_required`, `time_limit_months`, `requires_club`).

**Plusy:**
- Ścisłe typowanie na poziomie SQL (np. sprawdzanie typu `INTEGER` przez bazę).
- Łatwe filtrowanie i wyszukiwanie odznak po konkretnej regule wprost przez ORM Django.

**Minusy:**
- Zjawisko *Sparse Matrix* (Macierzy rzadkiej) — tabela `BadgeVersion` zyskałaby docelowo dziesiątki kolumn, z których 95% dla przeciętnej odznaki miałoby wartość `NULL`.
- Łamanie zasady Open/Closed Principle — każda nowa reguła PTTK wymagałaby dodania kolumny, napisania migracji i edycji kodu panelu Admina.

---

### Opcja B: Silnik skryptowy (Ewaluacja w locie)

**Opis:** Zapisywanie logiki biznesowej jako tekstu (np. skryptów Python lub Lua) w polu tekstowym bazy i używanie `eval()`/`exec()` podczas weryfikacji.

**Plusy:**
- Nieskończona elastyczność (administrator może napisać dowolną logikę).

**Minusy:**
- Ekstremalne naruszenie bezpieczeństwa (zgodnie z `Security Contract` użycie `eval` w kodzie produkcyjnym jest zakazane).
- Brak sprawdzania typów (Mypy) oraz testowalności automatycznej.

---

### Opcja C: Wzorzec Strategii w Domenie + Konfiguracja JSONB w Infrastrukturze

**Opis:** Logika każdej reguły to osobna, niemutowalna klasa w warstwie domeny, implementująca metodę `validate()`. Repozytorium przechowuje konfigurację w kolumnie `JSONB`. Biblioteka `django-jsonform` (klucz `oneOf`) udostępnia bezpieczny interfejs w panelu Admina.

**Plusy:**
- Pełna zgodność z `14-domain-purity.md` — logika izolowana, deterministyczna, w 100% testowalna jednostkowo.
- Zgodność z OCP — dodanie nowej reguły to nowa klasa i wpis w słowniku `RULE_BUILDERS`, bez dotykania silnika ewaluacji ani schematu bazy.

**Minusy:**
- Ograniczone możliwości natywnego wyszukiwania w bazie (filtrowanie np. "odznak wymagających 8 lat" wymaga operatorów JSONB w ORM).
- Konieczność mapowania i rzucania wyjątków (hydracji) z JSONB na klasy przed każdą weryfikacją.

---

## Decyzja

**Wybrano: Opcja C — Wzorzec Strategii w Domenie + Konfiguracja JSONB w Infrastrukturze**

Przewaga wynikająca z braku konieczności modyfikacji schematu bazy danych przy powstawaniu kolejnych regulaminów PTTK przewyższa koszty hydracji w pamięci podręcznej.
Zastosowanie rygorystycznych Fabryk rzucających wyjątki podczas deserializacji w adapterze niweluje słabości wynikające ze schematów NoSQL. Słownik `oneOf` ułatwia zarządzanie tymi ustawieniami administratorowi.

---

## Konsekwencje

### Pozytywne
- Elastyczny i otwarty na rozbudowę silnik weryfikacyjny.
- Czysty i wąski schemat tabeli odznak w bazie.
- Silna separacja logiki domenowej od magazynowania danych.

### Negatywne / Ograniczenia
- Narzut obliczeniowy przy weryfikacji wynikający z tworzenia obiektów Pythona w locie (akceptowalny przy profilu i skali ruchu aplikacji PTTK).
- Konieczność utrzymywania schematu `RULES_SCHEMA` zsynchronizowanego z rejestrem `RULE_BUILDERS`.

### Działania wymagane (Zrealizowane)
- [x] Opracowanie bazowego interfejsu `BadgeRule` w domenie.
- [x] Instalacja i konfiguracja `django-jsonform` z użyciem klucza `oneOf`.
- [x] Wdrożenie mechanizmu `Fail-Fast` w adapterze (rzucanie `ValueError` przy błędach hydracji zamiast cichego pomijania uszkodzonych reguł).

---

## Warunek rewizji

Zrewidować, jeśli złożoność reguł osiągnie moment, w którym PTTK zechce budować reguły w pełni logiczne oparte o zagnieżdżone drzewa wyrażeń z operatorami AND/OR. Mogłoby to przekroczyć wydolność płaskiej listy wzorca Strategii i wymusić użycie parsera AST.

---

## Relacje (Related)
- **C4 Diagram:** `docs/architecture/components.puml`
- **Kontrakty:** `docs/Manifest/14-domain-purity.md` (Import Linter rule: `domain-purity`)
- **Dług (Debt):** DŁUG-005 — brak walidacji schematu JSONB w runtime na poziomie bazy danych
- **ADR-002 — Geometria jako transport infrastrukturalny:** Decyzja komplementarna: ADR-002 ustala, że "geometria zostaje w infrastrukturze", a ADR-003 gwarantuje, że "czyste reguły biznesowe zostają w domenie".