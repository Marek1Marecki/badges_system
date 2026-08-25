# ADR-009 — Weryfikacja wejść jako operacje na zbiorach (Pool-based Set Verification)

> **Status:** `accepted`  
> **Data:** 2026-05-26  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Regulaminy określają warunki takie jak: "Zdobądź 10 dowolnych szczytów w Tatrach" lub "Zdobądź szczyty z załącznika". Na poziomie implementacji silnika weryfikacyjnego (Czystej Domeny) powstaje dylemat: w jaki sposób kod domenowy ma upewnić się, że wejście zalogowane przez turystę faktycznie leży w Tatrach i spełnia kryteria przestrzenne regulaminu?

**Pytanie decyzyjne:**  
Czy warstwa Domeny (weryfikacja) powinna używać mechanizmów GIS i odpytywać bazę danych o atrybuty i położenie przestrzenne szczytów podczas sprawdzania wejść turysty?

---

## Debata przed decyzją

**Domain Expert:** System ma egzekwować autorytatywną listę PTTK. Jeśli PTTK uznało, że dane 10 szczytów tworzy "Odznakę Tatrzańską", to weryfikator nie sprawdza na mapie, czy jeden ze szczytów przypadkiem nie leży za miedzą. Interesuje nas zamknięty zbiór obiektów zatwierdzonych przez oddział.  
**Software Architect:** Użycie narzędzi przestrzennych (`ST_Contains`, `ST_DWithin`) bezpośrednio w Use Case lub Czystej Domenie weryfikacji złamałoby założenie o bezstanowości (statelessness) i izolacji domeny od technologii (PostGIS). Weryfikacja musi być operacją pamięciową rzędu milisekund, a nie ciężką analityką.  
**Security / Data Integrity Engineer:** Z perspektywy integralności danych, ślepe zaufanie domeny do zbioru ID rodzi ryzyko ewaluacji wejść na "duchach". Administrator mógłby omyłkowo przypiąć ID obiektu, który nie istnieje. Baza danych musi gwarantować twardą referencyjność (Foreign Keys) na etapie zapisu `pool_peaks`, aby wstrzyknięty do domeny `frozenset[int]` zawierał wyłącznie poprawne i istniejące identyfikatory.

*Wniosek z debaty:* Ochrona bezstanowości, determinizmu i wydajności domeny jest nadrzędna. Wszelkie weryfikacje przestrzenne i referencyjne muszą zostać przesunięte do infrastruktury (na etap definiowania odznaki w panelu), zasilając domenę wyłącznie bezpiecznym, ustrukturyzowanym zbiorem identyfikatorów matematycznych.

---

## Opcje rozważane

### Opcja A: Weryfikacja przestrzenna w locie (Domain uses GIS)
**Opis:** Domena przyjmuje listę współrzędnych GPS z wejść turysty i wywołuje usługi infrastrukturalne odpytujące poligon np. Tatr w PostGIS.
**Plusy:** Autonomiczność – brak konieczności wstępnego definiowania "sztywnych list" przez admina.
**Minusy:** Krytyczne naruszenie *Domain Purity Contract*. Bardzo wolna ewaluacja. Całkowite odseparowanie PTTK od decyzyjności (system próbuje być "mądrzejszy" od organizatora).

### Opcja B: Weryfikacja oparta o Predefiniowane Pule i Matematykę Zbiorów (Pool-based Set Verification)
**Opis:** Przeniesienie całego ciężaru weryfikacji geograficznej na Fazę Administracyjną (Setup Phase). Administrator wykorzystując filtry przestrzenne, przygotowuje listę obiektów i przypina je jako relację M2M do Wersji Odznaki. Domena otrzymuje wstrzyknięty zbiór (np. `frozenset[int] = {15, 23, 42}`) i wykorzystuje wbudowane mechanizmy algebry zbiorów (np. `intersection()`) ze zbiorem zgłoszonych przez turystę wejść.

---

## Decyzja

**Wybrano: Opcja B — Pool-based Set Verification**

Rozwiązanie to odcina *Katalogowanie i Geografię* od *Decyzyjności Biznesowej*. Odrzucając parametry topograficzne z agregatów przekazywanych do domeny (jak wysokość czy położenie postGIS), sprowadzamy obiekt do płaskiego identyfikatora. Logika weryfikacji zamienia się w czystą, w 100% testowalną operację algebry zbiorów w pamięci RAM. To samo podejście pozwala na natywne eliminowanie wielokrotnych zgłoszeń tego samego szczytu w jednej ewaluacji (redukcja do unikalnych kluczy w strukturze `set`).

---

## Konsekwencje

### Pozytywne
- **Wydajność algorytmiczna:** Złożoność ewaluacji w silniku reguł jest sprowadzona do O(1) lub O(N) przy szukaniu przecięć (`set.intersection`).
- **Niezależność:** Use Case weryfikujący postęp turysty działa bez jakichkolwiek zapytań przestrzennych do bazy danych w trakcie egzekucji.

### Negatywne / Ograniczenia
- **Ślepe zaufanie do puli:** Konieczność rygorystycznego przygotowania bazy przed udostępnieniem odznaki. Administrator PTTK ponosi pełną odpowiedzialność za to, jakie szczyty włączy w listę `pool_peaks`. Algorytm Domeny ślepo ufa, że pula została skomponowana prawidłowo pod kątem geograficznym.

### Działania wymagane (Zrealizowane)
- [x] Oparcie modelu ewaluacji w `BadgeVersionDomain` na strukturze `frozenset[int]`.
- [x] Zaprogramowanie reguł biznesowych (np. `GroupedAlternativesRule`, `MandatoryObjectsRule`) z wykorzystaniem wbudowanych w Pythona matematycznych właściwości zbiorów, z pominięciem list (`list`).

---

## Warunek rewizji

Zrewidować, jeśli PTTK wprowadzi odznaki, w których reguły zaliczania są *dynamiczne geograficznie*, a lista nie da się autorytatywnie predefiniować przez administratora (np. "Zdobądź dowolne 10 szczytów powyżej 1500 m n.p.m. w danym sezonie zimowym"). Wtedy Model Oparty o Pule (Option B) przestanie wystarczać i konieczne będzie wdrożenie modelu hybrydowego, w którym infrastruktura w locie pre-filtruje dynamiczny zbiór dopuszczalnych identyfikatorów i wstrzykuje go do domeny przed wywołaniem metody `execute()`.

---

## Relacje (Related)
- **ADR-003 — Silnik Reguł Biznesowych:** Implementacja reguł takich jak `MandatoryObjectsRule` czy `GroupedAlternativesRule` jest bezpośrednim wynikiem przyjęcia matematyki zbiorów (Set Math) zdefiniowanej w niniejszym ADR.
- **ADR-005 — Płaski Model Odczytu CQRS:** To właśnie zdenormalizowane tabele zdefiniowane w ADR-005 pozwalają administratorowi na szybkie odfiltrowanie tysięcy szczytów geograficznych na etapie *Setup Phase*, co zdejmuje z domeny konieczność posiadania wiedzy o przestrzeni i umożliwia działanie *Pool-based Set Verification*.
- **ADR-012 — Weryfikacja celów otwartych geograficznie:** Oficjalnie zdefiniowany i hermetycznie odizolowany wyjątek od reguły "sztywnego załącznika M2M", pozwalający Domenie ewaluować szerokie regiony geograficzne bez bezpośredniego łamania dogmatu operacji na zbiorach.
