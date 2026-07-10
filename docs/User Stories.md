# User Stories

> **Wersja:** 1.1  
> **Data:** 2026-05-29  
> **Właściciel:** Dominik / AI Architect  
> **Status:** `approved` (Dla Fazy C: Użytkownik i Logistyka)

---

## Format stories

```text
Jako [ROLA], chcę [DZIAŁANIE], aby [CEL / KORZYŚĆ].
```

### Priorytety
| Symbol | Znaczenie |
|--------|-----------|
| 🔴 P0 | Krytyczne — bez tego system nie działa |
| 🟠 P1 | Wysokie — kluczowe dla MVP Fazy C |
| 🟡 P2 | Średnie — ważne, ale można opóźnić |
| 🟢 P3 | Niskie — nice-to-have (np. zaawansowana analityka) |

---

## Epic 1: Konta, Profile Rodzinne i Kontekst

### US-C01 — Rejestracja i Wiek Turysty 🔴 P0
**Story:** Jako Turysta, chcę zdefiniować swoją datę urodzenia w profilu, aby system mógł poprawnie weryfikować odznaki posiadające ograniczenia wiekowe.
**Dotyczy encji:** `TouristProfile` (Nowa), `MinAgeRule`, `MaxAgeRule`
**Powiązane invarianty:** —

**Kryteria akceptacji:**
- [x] Model `TouristProfile` jest powiązany z modelem autoryzacyjnym Django (`User`) za pomocą relacji `OneToOneField`.
- [x] Profil przechowuje bezpiecznie `birth_date`.
- [x] Silnik Domenowy podczas ewaluacji otrzymuje prawdziwą datę z profilu zamiast dotychczasowego mocka w kodzie.

### US-C01b — Katalog i Wybór Odznak (Badge Discovery) 🟠 P1
**Story:** Jako Turysta, chcę przeglądać listę wszystkich dostępnych odznak z możliwością filtrowania (np. według państwa lub głównego pasma), aby móc dodać interesujące mnie pozycje do mojej listy celów.
**Dotyczy encji:** `BadgeModel` (Nowe pola: `country_scope`, `region_scope`), `UserBadgeProgress`

**Kryteria akceptacji:**
- [x] Model `BadgeModel` posiada twarde metadane terytorialne do filtrowania (np. Polska, Sudety), nadawane przez Administratora.
- [x] Turysta klika "Chcę zdobywać", co tworzy intencję (`UserBadgeProgress` ze statusem `NOT_STARTED` i pustym `version_id`).

### US-C01c — Pakiety Freemium i Limity Konta 🟠 P1
**Story:** Jako Właściciel Aplikacji, chcę przypisywać kontom (Głównym Profilom) pakiety subskrypcyjne (np. Free, Family), które limitują zasoby (np. maksymalna liczba podpiętych profili dzieci, liczba zdjęć), aby system mógł się utrzymać.
**Dotyczy encji:** `TouristProfile`, `TouristProfileDTO`
**Kryteria akceptacji:**
- [x] Główne konto posiada limit maksymalnej liczby profili (np. 1 dla FREE, 5 dla FAMILY).
- [x] Ochrona Limitów (Engagement Loop): Limit subskrybowanych odznak dla pakietu FREE (np. max 3) obejmuje **wyłącznie** odznaki w statusie `NOT_STARTED` lub `IN_PROGRESS`. Odznaki ukończone (`COMPLETED` i zarchiwizowane) nie "zżerają" limitu darmowego konta. Gwarantuje to podtrzymanie zaangażowania użytkownika, zachęcając do kupna wersji PRO zablokowanymi mapami topograficznymi, a nie uderzaniem w "twardą ścianę płatności" (Hard Paywall).
- [x] Odrzucenie akcji z powodu wyczerpania limitu rzuca błąd aplikacyjny `400 Bad Request` z jasnym komunikatem zachęcającym do rozszerzenia pakietu.

### US-C01d — Zarządzanie Profilami (Konta Rodzinne) 🔴 P0
**Story:** Jako Turysta, chcę móc utworzyć dodatkowe profile (np. dla moich dzieci) pod jednym kontem logowania Google, aby wygodnie zarządzać ich niezależnymi postępami bez konieczności ciągłego wylogowywania się.
**Dotyczy encji:** `TouristProfile`, `AscentLog`, `UserBadgeProgress`
**Kryteria akceptacji:**
- [x] Użytkownik uwierzytelniony może przełączać "aktywny kontekst profilu" w menu (zapisywane w sesji).
- [x] Logi wejść i postępy są twardo przypinane do ID Profilu (`profile_id`), a nie ID Konta (`user_id`).

### US-C02 — Przynależność Klubowa (Data zapisu) 🟠 P1
**Story:** Jako Turysta, chcę móc odnotować datę dołączenia do konkretnego Klubu (np. KGP), aby system zaliczał mi logi wejść zrobione dopiero po tej dacie.
**Dotyczy encji:** `ClubMembership` (Nowa), `OrganizerModel`, `RequiresClubJoinDateRule`

**Kryteria akceptacji:**
- [ ] Turysta może wybrać Organizatora z bazy i podać datę zapisu.
- [ ] `VerifyBadgeUseCase` ignoruje wejścia starsze niż data członkostwa dla odznak wymagających tej reguły.

### US-C02b — Prawo do bycia zapomnianym (Usuwanie konta) 🟠 P1
**Story:** Jako Turysta, chcę mieć możliwość trwałego i nieodwracalnego skasowania mojego konta wraz z całą historyczną bazą wejść, postępów i wgranych plików, aby zachować pełną kontrolę nad swoimi danymi osobowymi (zgodność z RODO).
**Dotyczy encji:** `TouristProfile`, `AscentLog`, `UserBadgeProgress`, `VerificationRequest` (wszystkie encje powiązane z Userem).

**Kryteria akceptacji:**
- [ ] System wykonuje twarde usunięcie (Hard Delete) głównego konta użytkownika, co za pomocą więzów `CASCADE` w bazie zdejmuje całą jego historię z tabel.
- [ ] Usługa obsługująca usuwanie konta **fizycznie usuwa pliki** (np. `proof_file` ze zdjęciami) z przestrzeni dyskowej/S3, nie pozostawiając sierot.
- [ ] Usunięcie konta emituje zdarzenie (lub bezpośrednie wywołanie) czyszczące klucze przypisane do tego `user_id` w pamięci Redis (Cache Mapy i Rankingu Szczytów).
- [ ] Operacja ta jest chroniona podwójnym potwierdzeniem (np. "Wpisz swoje hasło, aby potwierdzić").

---

## Epic 2: Dziennik Wejść i Złoty Zbiór (The Ascent Log)

### US-C03 — Logowanie Wejścia (Ascent) 🔴 P0
**Story:** Jako Turysta, chcę w najprostszy możliwy sposób zapisać fakt wejścia na konkretny Obiekt Turystyczny podając jedynie datę, aby błyskawicznie budować swoją historię górską.
**Dotyczy encji:** `AscentLog` (Nowa), `TouristObject`
**Powiązane invarianty:** T-01 (Bitemporalność obiektu)

**Kryteria akceptacji:**
- [x] Zapis logu wymaga podania **wyłącznie** `tourist_object_id` oraz `date`.
- [x] Odrzucenie koncepcji deklarowania "aktywności" (np. pieszo/rower) dla maksymalnego uproszczenia UX.
- [x] System twardo odrzuca log (Fail-Fast), jeśli podana data nie mieści się w przedziale `existence_start` i `existence_end` obiektu (T-01).

### US-C04 — Pamiątki z Wejść (Souvenir Photos) 🟢 P3
**Story:** Jako Turysta, chcę opcjonalnie dodać do mojego logu wejścia prywatne zdjęcie (np. selfie z wierzchołka, widok), aby traktować aplikację jako mój osobisty pamiętnik z podróży.
**Dotyczy encji:** `AscentLog`

**Kryteria akceptacji:**
- [ ] Funkcja w 100% opcjonalna i wyłączona z rygorystycznego procesu weryfikacji odznak (dowodem ostatecznym pozostaje fizyczna książeczka).
- [ ] Z uwagi na koszty magazynowania danych (Storage), funkcja odłożona na późniejsze fazy optymalizacji infrastruktury w chmurze (np. dodanie zewnętrznego S3).

### US-C17 — Import i Analiza Śladu GPX (Smart Logger) 🟠 P1
**Story:** Jako Turysta, chcę wgrać plik z moim śladem GPS (GPX), aby system sam odnalazł na nim obiekty, w których pobliżu przechodziłem, i pozwolił mi je masowo zalogować za pomocą jednego kliknięcia.
**Dotyczy encji:** `AscentLog`, `TouristObject` (Geometry)
**Powiązane invarianty:** D-04 (Idempotentność zapisów), T-01 (Bitemporalność)

**Kryteria akceptacji:**
- [x] System przetwarza plik w locie (in-memory, bez zapisu pliku GPX na dysk serwera w celu ochrony prywatności).
- [x] Ścieżka z pliku jest upraszczana i rzutowana przestrzennie (bufor ok. 100-200m).
- [x] Turysta może zbiorczo edytować przypisaną datę wycieczki przed ostatecznym zatwierdzeniem.
- [x] Zapis do bazy wykorzystuje mechanizm `Bulk Upsert`, a silnik rankingów (Celery) jest wyzwalany **tylko raz** na koniec całej operacji masowej.
- [x] System zwraca raport częściowy (Partial Success), logując poprawne szczyty i pomijając te łamiące warunki bitemporalne dla wybranej daty.

---

## Epic 3: Silnik Postępu (Badge Progress)

### US-C05 — Świadomy wybór Regulaminu i Prawa Nabyte 🔴 P0
**Story:** Jako Turysta z wieloletnią historią górską, chcę aby system domyślnie oceniał mnie według najnowszego regulaminu, ale automatycznie odblokowywał mi możliwość przejścia na starsze wersje regulaminu (Prawa Nabyte) na podstawie daty mojego najstarszego wejścia na szlak.
**Dotyczy encji:** `UserBadgeProgress`, `BadgeVersionModel`, `AscentLog`
**Powiązane invarianty:** P-01 (Prawa Nabyte)

**Kryteria akceptacji:**
- [x] Przy kliknięciu "Rozpocznij", turysta jest przypinany do aktualnie obowiązującej `BadgeVersion`.
- [x] Po dodaniu każdego logu, system ustala wiek najstarszego wejścia turysty. 
- [x] Jeśli najstarsze wejście jest starsze niż obecna wersja odznaki, aplikacja umożliwia turyście ręczne przełączenie się (`switch`) na starsze `BadgeVersion`, do których nabył prawa.
- [x] Przełączanie wersji jest możliwe i płynne tak długo, jak długo odznaka nie została dodana do Wniosku Weryfikacyjnego (`VerificationRequest`). Po utworzeniu wniosku, wersja w `UserBadgeProgress` zostaje zablokowana (Read-Only).

### US-C06 — Silnik Postępu (Set Math w Domenie) 🔴 P0
**Story:** Jako Turysta, chcę zobaczyć na jakim jestem etapie (np. 12/25 szczytów), aby wiedzieć, ile brakuje mi do danego Stopnia odznaki.
**Dotyczy encji:** `UserBadgeProgress`, `BadgeTierModel`, `VerifyBadgeUseCase`

**Kryteria akceptacji:**
- [x] Przeliczanie statusu dla pojedynczej odznaki następuje **synchronicznie w locie (On-Demand)** podczas ładowania jej widoku detali, gwarantując turystom *Immediate Consistency*.
- [x] Przeliczanie masowe (Ranking POI 100/n z US-C16 dla całej mapy) jest delegowane do asynchronicznych zadań **Celery** (Event-Driven), aby nie blokować UI serwera.

### US-C09 — Kolejny Cykl Odznaki (Pętla Prestiżu) 🟠 P1
**Story:** Jako Turysta, chcę rozpocząć ponowne zdobywanie tej samej odznaki (nowy cykl), aby móc zweryfikować ją po raz kolejny, używając wyłącznie nowych wejść.
**Dotyczy encji:** `UserBadgeProgress` (Rozbudowa o `cycle_number`)
**Powiązane edge cases:** EC-030

**Kryteria akceptacji:**
- [x] Dodanie pola `cycle_number` (domyślnie 1) do `UserBadgeProgress`.
- [x] Turysta może utworzyć nowy cykl TYLKO wtedy, gdy poprzedni cykl jest w statusie `COMPLETED`.
- [x] Wejścia wykorzystane do zamknięcia Cyklu 1 są odfiltrowywane i nie wchodzą do puli ewaluacyjnej Cyklu 2.

---

## Epic 4: Logistyka i Osobisty Kanban (Personal Fulfillment Tracker)

### US-C07 — Wejście do Logistyki (Automatyczny Inbox) 🟠 P1
**Story:** Jako Turysta, chcę aby każda moja zdobyta odznaka (lub jej stopień) automatycznie trafiała na moją listę logistyczną, abym wiedział, które książeczki są gotowe do fizycznej wysyłki.
**Dotyczy encji:** `UserBadgeProgress`, `BadgeTierModel`
**Powiązane invarianty:** S-03 (Domena nie zna logistyki)

**Kryteria akceptacji:**
- [x] Gdy Czysta Domena oceni dany stopień/wersję na `COMPLETED`, pozycja ta automatycznie pojawia się w widoku Logistyki (Kanban) ze statusem `WAITING_FOR_SEND`.
- [x] To Turysta (a nie system) grupuje je fizycznie w koperty w świecie rzeczywistym.

### US-C08 — Osobista Maszyna Stanów i Alerty (Tracking) 🟠 P1
**Story:** Jako Turysta, chcę ręcznie aktualizować statusy moich wysłanych odznak i otrzymywać ostrzeżenia o opóźnieniach, aby nie zgubić śladu po moich książeczkach weryfikacyjnych.
**Dotyczy encji:** `UserBadgeProgress` (pola logistyczne: `logistic_status`, `sent_date`, `verified_date`, `received_date`)

**Kryteria akceptacji:**
- [x] Turysta samodzielnie przesuwa status na `WAITING_FOR_VERIFICATION` (podając datę wysyłki na poczcie).
- [x] System wyświetla alert ⚠️ (bez zadań w tle, wyliczany w locie w widoku), jeśli od daty wysyłki minęło > 30 dni.
- [x] Turysta zmienia status na `WAITING_FOR_RECEIVING` (gdy opłaci blachę / dostanie info z PTTK, podając datę).
- [x] System wyświetla alert ⚠️, jeśli od daty weryfikacji minęło > 30 dni, a listonosz nie przyniósł blachy.
- [x] Turysta klika `ALBUM` (stan terminalny) po fizycznym otrzymaniu odznaki.

### US-C08b — Autoryzowana Korekta Błędów Logistycznych 🟠 P1
**Story:** Jako Turysta, jeśli weryfikator PTTK zgłosił błąd w moim wpisie przypiętym do skompletowanej odznaki, chcę móc poprosić system o usunięcie "fałszywego" wejścia bez konieczności resetowania całego mojego konta.
**Dotyczy encji:** `AscentLog`, `UserBadgeProgress`
**Powiązane invarianty:** S-04

**Kryteria akceptacji:**
- [ ] Turysta nie może użyć standardowego przycisku "Usuń" dla zablokowanego logu.
- [ ] Turysta posiada przycisk "Zgłoś pomyłkę / Cofy weryfikację" przy zamkniętym Cyklu odznaki.
- [ ] Akcja ta degradowuje stan odznaki z `COMPLETED` do `IN_PROGRESS`, po czym "odpina" kłódkę ze wszystkich logów `AscentLog`, pozwalając turyście na usunięcie błędnego wejścia i uzupełnienie braków prawdziwą wycieczką.

---

## Epic 5: Odkrywanie i Mapa (Map & Discovery)

### US-C10 — Globalna Mapa Celów (Global Map) 🟠 P1
**Story:** Jako Turysta, chcę widzieć na jednej mapie wszystkie szczyty w Polsce pokolorowane na podstawie moich postępów we wszystkich aktywnych odznakach, abym wiedział, gdzie najbardziej opłaca mi się dziś pojechać.
**Dotyczy encji:** `MapContext` (DTO), `BadgeEligibilityService` (Application Service)
**Powiązane ADR:** ADR-010, ADR-011

**Kryteria akceptacji:**
- [x] Obiekty mają nadany jeden z 5 ujednoliconych stanów (Szary, Zielony, Czerwony, Niebieski, Pomarańczowy).
- [x] Obliczenia są buforowane w Redis (klucz per `user_id` + dzisiejsza data), aby zapytania działały poniżej 50ms.
- [x] API akceptuje Bounding Box (BBox) z mapy i zwraca tylko obiekty w widocznym oknie (Lazy Evaluation).

### US-C11 — Mapa Konkretnej Odznaki (Badge Map) 🟠 P1
**Story:** Jako Turysta, chcę otworzyć szczegóły "Korony Sudetów" i widzieć mapę odfiltrowaną i pokolorowaną WYŁĄCZNIE przez pryzmat tej jednej odznaki.
**Dotyczy encji:** `MapContext` (DTO)

**Kryteria akceptacji:**
- [x] Obiekty spoza puli tej odznaki nie są przesyłane do przeglądarki.
- [x] Kolorowanie ignoruje postęp w innych odznakach (np. szczyt może być Czerwony dla tej mapy, mimo że globalnie jest Niebieski).

### US-C12 — Nawigacja Regionalna (Mapy Pośrednie) 🟠 P1
**Story:** Jako Turysta, chcę móc wygenerować mapę zawężoną do konkretnego poziomu geograficznego (np. tylko Państwo, tylko Makroregion, tylko Mezoregion), aby skupić się na celach w moim fizycznym zasięgu.
**Kryteria akceptacji:**
- [x] Utworzenie dedykowanych widoków dla jednostek geograficznych.
- [x] Warstwa wektorowa (MVT) wyświetla klikalne poligony regionów sąsiadujących.
- [x] Kliknięcie w sąsiedni poligon na mapie dynamicznie przeładowuje kontekst aplikacji na nowy region (np. przejście z Beskidu Śląskiego do Małego).

### US-C13 — Płynny UX Mapy (Heatmapa i Klastrowanie) 🟠 P1
**Story:** Jako Turysta, chcę aby przy dużym oddaleniu mapy obiekty scalały się w "mapę ciepła" (Heatmap), a przy przybliżeniu zamieniały w klikalne pinezki, aby uniknąć zasłonięcia ekranu tysiącami ikon.
**Dotyczy:** Frontend (MapLibre GL JS), `UI_GUIDELINES.md`
**Kryteria akceptacji:**
- [x] Wdrożenie warstwy `heatmap` w MapLibre widocznej dla `zoom < X`.
- [x] Wdrożenie warstwy `symbol` widocznej dla `zoom >= X`.
- [x] Kliknięcie pinezki otwiera natywny popup (Tooltip) ze skróconym opisem i linkiem do szczegółów. Obliczenia wizualne obciążają wyłącznie urządzenie klienckie.

### US-C14 — Detale Obiektu i Radar 2 km 🟡 P2
**Story:** Jako Turysta, wchodząc na stronę konkretnego obiektu, chcę widzieć mapę celów znajdujących się w promieniu 2 km od niego, aby optymalnie zaplanować moją wycieczkę.
**Kryteria akceptacji:**
- [x] Strona ze szczegółami obiektu (`TouristObject`).
- [x] Na stronie osadzona jest mini-mapa wyrenderowana na podstawie szybkiego zapytania `ST_DWithin` (2000m) z bazy PostGIS.
- [x] Na liście uwzględniona jest dynamiczna kolorystyka obiektów (czy już je zdobyłem).

### US-C15 — Wybór Podkładu Mapowego (Basemap Switcher) 🟢 P3
**Story:** Jako Turysta, chcę mieć możliwość przełączania podkładu mapy (np. na Mapy.cz, OpenStreetMap, mapę turystyczną), aby móc lepiej orientować się w terenie szlaków górskich.
**Kryteria akceptacji:**
- [x] Implementacja standardowego widżetu wyboru warstw rastrowych w UI MapLibre.
- [x] (Zależność operacyjna) Uzyskanie i bezpieczne zmagazynowanie darmowych kluczy API dostawców w `AppSettings`.

### US-C16 — Ranking Potencjału Obiektów (Min-Maxing) 🟠 P1
**Story:** Jako Turysta, chcę widzieć punktację "opłacalności" niezdobytych przeze mnie szczytów (oraz sumę punktów dla całych regionów), aby optymalnie zaplanować wycieczkę, która najbardziej przybliży mnie do zdobycia blach.
**Dotyczy encji:** `BadgeEligibilityService` (App Layer), Redis Cache
**Powiązane ADR:** ADR-015

**Kryteria akceptacji:**
- [x] Szczyt punktuje według wzoru `Σ (100 / n_pozostałych)`. Wynik to liczba całkowita.
- [x] Wynik ignoruje odznaki, które na dzisiejszą datę są odrzucane przez domeny (np. złe okno czasowe).
- [x] Turysta może wyświetlić ranking topowych szczytów dla wybranego przez CQRS regionu (np. "Najbardziej opłacalne w Sudetach").
- [x] Turysta może wyświetlić zagregowany ranking całych regionów (Suma potencjału wszystkich szczytów z danego pasma górskiego).

### EC-035 — Niezgodność typów w Cache (Szare Pinezki na Mapie)
**Obszar:** `application/use_cases/explore_map.py`, Redis Cache  
**Odkryty:** Podczas implementacji endpointu GeoJSON i nakładania kolorów z Cache.  
**Status:** `resolved`  
**Opis:** Klucze ID obiektów wyciągnięte z bazy danych są w Pythonie typu `int`. Natomiast po odczytaniu słownika z bufora opartego na Redis i JSON/Pickle, często klucze zostają zserializowane do typu `str` (np. `"15"` zamiast `15`). Próba bezpośredniego wyszukania po `dict.get(obj.id)` zwracała `None`, co skutkowało przypisywaniem domyślnego koloru `GRAY` i `0` punktów dla prawidłowych szczytów.  
**Rozwiązanie / workaround:** Wprowadzono wariant *Double Lookup* z rzutowaniem w locie. Odczyt zawsze najpierw pyta o int, a jako fallback o string: `scores.get(obj.id, scores.get(str(obj.id), 0))`.

### EC-036 — Brak wsparcia Data-Driven Styling dla 'line-dasharray'
**Obszar:** `apps/static/js/map.js` (MapLibre GL JS)  
**Odkryty:** Podczas próby dynamicznego rysowania przerywanych i ciągłych granic MVT na jednej warstwie.  
**Status:** `resolved`  
**Opis:** Zastosowanie wyrażenia warunkowego `['case', ['==', ['get', 'id'], 1], [1], [2,2]]` dla właściwości `line-dasharray` w MapLibre GL JS jest technicznie niewspierane przez silnik WebGL tej biblioteki. Skutkuje to "cichą awarią" – warstwa po prostu nie jest renderowana na mapie, bez żadnych błędów w konsoli.  
**Rozwiązanie / workaround:** Zamiast jednej, dynamicznej warstwy, kod JS musi rozdzielić warstwy na osobne (np. `regions-line-active` oraz `regions-line-neighbors`), używając filtru `['==', ...]` na poziomie całej warstwy, i definiując atrybut `line-dasharray` sztywno (statycznie) dla każdej z nich osobno.

### EC-037 — Błąd 500 przy relacji OneToOneField (Brakujący Profil)
**Obszar:** `apps/tourists/views.py`  
**Odkryty:** Przy wejściu na podstronę `/profile/` kontem administratora.  
**Status:** `resolved`  
**Opis:** Kod aplikacji często odwołuje się wprost do `request.user.tourist_profile`. Dla nowych użytkowników rejestrujących się przez Google OAuth profil ten powstaje dzięki sygnałom Django (`post_save`). Jednak konta utworzone historycznie (np. przez `createsuperuser`) nie posiadają tego profilu, co kończy się natychmiastowym błędem `RelatedObjectDoesNotExist`.  
**Rozwiązanie / workaround:** Zakaz odwoływania się do profilu "w ciemno". W widokach opierających się na profilu wdrożono wzorzec *Lazy Initialization* poprzez użycie `TouristProfile.objects.get_or_create(user=request.user, defaults={...})`.

---

## Epic 6: Automatyzacja Administracyjna (Data Stewardship)

### US-A01 — Radar Aktualności Odznak (News Scraper) 🔴 P1
**Story:** Jako Administrator, chcę, aby system automatycznie i cyklicznie monitorował zewnętrzne portale turystyczne (np. odznaki.org) w poszukiwaniu nowych odznak i zmian w regulaminach, aby oszczędzić czas na ręcznym śledzeniu nowości.
**Dotyczy encji:** `BadgeNewsItem` (Nowa encja techniczna, Skrzynka Odbiorcza)
**Powiązane zasady:** Wymóg Fail-Silently (Ciche niepowodzenie w przypadku zmiany struktury HTML zewnętrznej strony).

**Kryteria akceptacji:**
- [x] Celery Beat codziennie uruchamia zadanie skanujące (Web Scraping).
- [x] Mechanizm twardej deduplikacji (np. `unique=True` dla URL artykułu lub jego hasha) gwarantuje, że do bazy trafiają wyłącznie nowe informacje.
- [x] W panelu Django Admin powstaje dedykowany Inbox z aktualnościami, posiadający statusy: "Nieprzeczytane" / "Przeczytane".
- [x] Administrator posiada akcję masową "Oznacz jako przeczytane", po której użyciu powiadomienia znikają z domyślnego widoku, zostając zarchiwizowane w bazie.

---

## Epic 7: Społeczność i Rywalizacja (Faza D - Social & Leaderboards)

### US-D01 — Globalny Ranking Turystów (Leaderboard) 🟠 P1
**Story:** Jako Turysta, chcę widzieć tabelę wyników innych użytkowników (np. TOP 50 w tym miesiącu), aby móc zdrowo rywalizować i zwiększać swoje zaangażowanie.
**Dotyczy encji:** `TouristProfile` (Agregacje)
**Kryteria akceptacji:**
- [ ] Widok "Tablica Liderów" grupujący użytkowników według liczby zdobytych szczytów lub ukończonych odznak.
- [ ] Zgodnie z Privacy by Default, system używa wyłącznie pola `nickname`.
- [ ] Ranking jest przeliczany i buforowany asynchronicznie (Celery), aby nie obciążać bazy.

### US-D02 — Odznaki Okolicznościowe i Eventy 🟡 P2
**Story:** Jako Właściciel, chcę móc zdefiniować odznakę limitowaną czasowo (np. działającą tylko jeden weekend), aby napędzać ruch w aplikacji z okazji świąt lub wydarzeń.
**Dotyczy encji:** `BadgeModel`, `DateWindowRule`
**Kryteria akceptacji:**
- [ ] Możliwość zdefiniowania globalnego okna czasowego dla całego wyzwania.
- [ ] Turyści widzą na pulpicie odliczanie "Pozostało: 2 dni 14 godzin".

### US-D03 — Profil Publiczny (Gablota Chwały) 🟢 P3
**Story:** Jako Turysta, chcę móc wygenerować publiczny, bezpieczny link do mojego profilu, aby pochwalić się znajomym zdobytymi blachami.
**Kryteria akceptacji:**
- [ ] Nowy widok HTTP w trybie READ-ONLY.
- [ ] Turysta widzi w ustawieniach opcję "Udostępnij mój profil".

---

## Epic 8: Infrastruktura i Wdrożenie Produkcyjne (DevOps)

### US-D04 — Chmurowy Magazyn Pamiątek (Cloud Storage) 🟠 P1
**Story:** Jako Właściciel, chcę zintegrować zewnętrzny magazyn obiektowy (np. AWS S3 / R2), aby w końcu odblokować turyście możliwość wgrywania zdjęć z wycieczek (US-C04) bez zapychania mojego serwera.
**Dotyczy encji:** `django-storages`
**Kryteria akceptacji:**
- [ ] Wdrożenie paczki `django-storages` i konfiguracja S3 Boto3 w `app_settings.py`.
- [ ] Zablokowanie wysyłania plików > 5MB z użyciem HTMX/JS na frontendzie.

### US-D05 — Aplikacja Instalowana na Telefonie (PWA) 🟡 P2
**Story:** Jako Turysta, chcę móc "zainstalować" tę stronę internetową na moim smartfonie, aby działała na pełnym ekranie i posiadała ikonkę w moim menu.
**Kryteria akceptacji:**
- [ ] Wygenerowanie pliku `manifest.json`.
- [ ] Wdrożenie `Service Worker` w JS do obsługi zapytań offline i cache'owania podkładu PTTK.

### US-D06 — Serwer Produkcyjny (Docker Prod) 🔴 P0
**Story:** Jako Architekt, chcę stworzyć niezależną, wysoce bezpieczną konfigurację Docker Compose, aby móc opublikować projekt w Internecie.
**Kryteria akceptacji:**
- [ ] Utworzenie `docker-compose.prod.yml`.
- [ ] Konfiguracja serwera Gunicorn jako bramki WSGI.
- [ ] Zablokowanie `DEBUG=False` i serwowanie `STATIC_FILES` poprzez Nginx / Caddy.

---

## Mapa zależności

| Story | Opis skrócony | Blokuje | Zablokowana przez |
|-------|---------------|---------|-------------------|
| **US-C01** | Profil i Wiek | US-C02, US-C01c, US-C06 | — |
| **US-C01b**| Katalog i Wybór Odznak| US-C05 | — |
| **US-C01c**| Pakiety Freemium | US-C03, US-C04 | US-C01 |
| **US-C02** | Przynależność Klubowa | — | US-C01 |
| **US-C02b**| Prawo do bycia zapomnianym| — | US-C01 |
| **US-C03** | Logowanie Wejścia | US-C06, US-C04 | US-C01, US-C01c |
| **US-C04** | Załączniki do Wejść | — | US-C03, US-C01c |
| **US-C05** | Zapis na Odznakę | US-C06, US-C07 | US-C01, US-C01b |
| **US-C06** | Silnik Postępu | US-C07, US-C09, US-C10 | US-C01, US-C03, US-C05 |
| **US-C09** | Pętla Prestiżu (Cykle)| — | US-C06 |
| **US-C07** | Osobisty Kanban (Inbox)| US-C08 | US-C06, US-C05 |
| **US-C08** | Maszyna Stanów Logistyki| — | US-C07 |
| **US-C10** | Globalna Mapa | US-C11, US-C12, US-C13, US-C15 | US-C06 |
| **US-C11** | Mapa Odznaki | — | US-C10 |
| **US-C12** | Nawigacja Regionalna | — | US-C10 |
| **US-C13** | Płynny UX (Heatmap) | — | US-C10 |
| **US-C14** | Detale i Radar 2 km | — | — |
| **US-C15** | Wybór Podkładów | — | US-C10 |
| **US-C16** | Ranking Potencjału (100/n) | — | US-C06 |
| **US-A01** | Radar Aktualności (Scraper)| — | — |

---

## Historia zmian
| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-29 | Dominik / AI Architect | Pierwsza wersja (Faza C). |
| 1.1 | 2026-05-29 | AI Architect | Uzupełnienie Mapy Zależności. Doprecyzowanie synchronicznego triggera US-C06 (Immediate Consistency), dodanie US-C09 (Pętla Prestiżu / EC-030). |
