# ADR-007 — Hierarchia i Wersjonowanie Odznak (Temporal Modeling i Prawa Nabyte)

> **Status:** `accepted`  
> **Data:** 2026-05-26  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Regulaminy odznak turystycznych zmieniają się w czasie. Zmianie ulega pula wymaganych szczytów (np. Korona Gór Świętokrzyskich w 2006 r. wymagała 36 szczytów, a w 2009 r. 28 szczytów), metody weryfikacji oraz reguły biznesowe. Jednocześnie PTTK silnie honoruje zasadę "Praw Nabytych" (*Grandfather Clause*) – turysta, który rozpoczął zdobywanie odznaki przed zmianą regulaminu, ma prawo ukończyć ją na starych zasadach. Ponadto, większość odznak posiada stopnie (Brązowy, Srebrny, Złoty), które wymuszają zdobycie rosnącej liczby obiektów z tej samej puli.

**Pytanie decyzyjne:**  
Jak zaprojektować strukturę relacyjną odznak, aby bez redundantnej duplikacji danych obsłużyć zmiany regulaminów w czasie, zróżnicowanie na stopnie i sprawiedliwą ewaluację postępów turysty?

---

## Debata przed decyzją

**Domain Expert:** Turysta nie może tracić postępów tylko dlatego, że PTTK zaktualizowało wykaz. Jeśli zlikwidowano szczyt X, a turysta był na nim rok temu, to ten szczyt musi się liczyć do jego "starej" wersji odznaki. Jednocześnie nie chcemy dla turysty tworzyć w UI potworków w stylu "Odznaka X (Wersja 2006) - Brązowa". On ma widzieć po prostu "Odznaka X".
**Data Modeler:** Jeśli dodamy do modelu odznaki pola takie jak `wymagane_szczyty_braz`, `wymagane_szczyty_srebro`, to system nie obsłuży odznak 4- czy 5-stopniowych. Z kolei duplikowanie odznak ("KGP 2000", "KGP 2024") rozbije nam ciągłość statystyk organizatora w bazie.
**Security Engineer:** Brak krytycznych wektorów ataku. Ewentualne ryzyko polega na tym, że wielopoziomowe zapytania (JOIN-y przez Odznakę, Wersję, Stopień i Pule Szczytów) mogą być podatne na ataki DoS przy braku odpowiednich indeksów, jednak zastosowanie klasycznych relacji Foreign Key minimalizuje ten problem. Główne ryzyko jest biznesowe (integralność danych), nie infrastrukturalne.

*Wniosek z debaty:* Należy stworzyć hierarchię, która naturalnie odwzorowuje rzeczywistość organizacyjną (Izomorfizm biznesowy), oddzielając koncepcję "Tożsamości odznaki" od "Zestawu reguł obowiązujących w danym roku".

---

## Opcje rozważane

### Opcja A: Płaski model z duplikacją (Flat Model)
**Opis:** Każda zmiana w regulaminie lub każdy nowy stopień to całkowicie nowy rekord w tabeli `Badge`. 
**Plusy:** Najprostsza struktura bazy (jedna tabela).
**Minusy:** Koszmarne UX dla użytkownika. Fragmentacja historii turysty. Ogromna duplikacja puli szczytów.

### Opcja B: Gigantyczna tabela relacyjna M2M z zakresem dat
**Opis:** Tabela odznak jest jedna, ale relacja do szczytów (`Badge_Peaks`) zawiera kolumny `valid_from` i `valid_to`. Weryfikacja sprawdza w locie, czy szczyt był przypięty do odznaki w roku logowania wejścia.
**Plusy:** Brak duplikacji definicji odznaki na najwyższym poziomie.
**Minusy:** Bardzo skomplikowane i kosztowne obliczeniowo zapytania SQL oraz ewaluacja w Pythonie. Model ten nie rozwiązuje problemu zmian całego regulaminu (np. zmiana wymaganego wieku z biegiem lat, a nie tylko puli szczytów).

### Opcja C: Hierarchia Trójpoziomowa (Badge -> Version -> Tier)
**Opis:** Podział na trzy autonomiczne byty:
1. `BadgeModel`: Trwała tożsamość odznaki (Nazwa, Organizator).
2. `BadgeVersionModel`: Regulamin osadzony w czasie (Pula obiektów, Reguły JSON, Daty obowiązywania).
3. `BadgeTierModel`: Stopień (Wymagana ilość obiektów z Puli, Kolejność, Grafika blachy).

---

## Decyzja

**Wybrano: Opcja C — Hierarchia Trójpoziomowa**

Dekompozycja na tożsamość, przepisy w czasie i stopnie zaawansowania to idealne odwzorowanie (Izomorfizm) modelu biznesowego PTTK. 
Rozwiązuje to problem "Praw Nabytych" strukturalnie: system po prostu na trwałe przypisze turystę (w tabeli `UserBadgeProgress` w Fazie C) do konkretnego rekordu `BadgeVersionModel`, na podstawie daty jego pierwszego zgłoszonego wejścia. Niezależnie od tego, ile nowych wersji PTTK stworzy w przyszłości, silnik weryfikacyjny będzie odpytywał tę i tylko tę historycznie zakotwiczoną wersję.

---

## Konsekwencje

### Pozytywne
- **Ochrona Praw Nabytych:** Architektura gwarantuje całkowitą spójność weryfikacji wstecznej.
- **Skalowalność stopni:** Wiele poziomów (Brąz, Srebro, Złoto) korzysta z jednej, wspólnie zdefiniowanej dla wersji Puli Szczytów, co drastycznie zmniejsza czas pracy administratora i eliminuje niespójności.

### Negatywne / Ograniczenia
- **Wymóg Niemutowalności (Immutability):** `BadgeVersionModel` nie posiada twardych blokad bazodanowych zapobiegających edycji. Jednak architektonicznie, po tym jak pierwszy użytkownik rozpocznie zdobywanie odznaki, wersja (w szczególności jej `pool_peaks`) musi być traktowana jako *niemutowalna*. Zmiana puli w aktywnej wersji złamie Prawa Nabyte tysięcy turystów. Każda zmiana wymaga utworzenia nowej Wersji. Obostrzenie to stanowi dług operacyjny, który należy egzekwować procedurami lub blokadami na poziomie interfejsu (Formularze Django).
- Zwiększona złożoność walidacji w Django Adminie (konieczność pisania dedykowanych formsetów walidacyjnych, zapobiegających np. zdublowaniu kolejności stopni w ramach jednej wersji).

### Działania wymagane (Zrealizowane)
- [x] Utworzenie modeli `BadgeModel`, `BadgeVersionModel`, `BadgeTierModel`.
- [x] Opracowanie logiki walidacji formularzy w Django Adminie zapobiegającej dublowaniu kolejności zdobywania (UniqueConstraint na `version` i `order`).
- [x] Implementacja Czystej Domeny (`BadgeVersionDomain`), w której ewaluacja opiera się na wspólnym zbiorze szczytów Wersji, a próg do pokonania pobierany jest ze Stopnia.

---

## Warunek rewizji

Zrewidować, jeśli PTTK wprowadzi regulaminy, w których **poszczególne stopnie tej samej odznaki (w tym samym czasie) mają całkowicie odrębne pule obiektów do wyboru**, nie pokrywające się ze sobą w żaden logiczny sposób. Złamałoby to nasze fundamentalne założenie, że `pool_peaks` należy do poziomu Wersji, i mogłoby wymusić przesunięcie relacji M2M w dół hierarchii (bezpośrednio do `BadgeTierModel`).

---

## Referencje
- **ADR-003 — Silnik Reguł Biznesowych:** Zgodnie z tym dokumentem, elastyczne reguły weryfikacyjne w formacie JSONB (np. limity czasu, minimalny wiek) przypinane są bezpośrednio do historycznej "Wersji", a nie do samej "Odznaki", uzupełniając czasową izolację wymogów.
- **ADR-004 — Dwuwarstwowy model zasilania danych z OSM:** Obiekty turystyczne wpinane w relację M2M do Puli Szczytów pochodzą z ustrukturyzowanego "Złotego Katalogu", gwarantując, że wersje historyczne odznak korzystają ze stabilnych i zwalidowanych węzłów przestrzennych.