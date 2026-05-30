# ADR-001 — Wybór głównego stosu technologicznego (Django, Celery, PostGIS)

> **Status:** `accepted`  
> **Data:** 2026-05-30  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Budowa systemu informatycznego do zarządzania odznakami turystycznymi i obiektami PTTK (Points of Interest) wymaga rozwiązania trzech kluczowych problemów:
1. **Ciężkie operacje przestrzenne:** Przetwarzanie i łączenie poligonów (`ST_Union`), buforowanie granic (`ST_DWithin`) dla tysięcy szczytów.
2. **Data Stewardship (Kuratela Danych):** Wymóg posiadania zaawansowanego, interaktywnego panelu administracyjnego do rozwiązywania konfliktów z OpenStreetMap, klastrowania obiektów i wieloetapowego definiowania regulaminów odznak.
3. **Zasilanie asynchroniczne:** Integracja z zewnętrznymi, często niestabilnymi API (Overpass) wymagająca niezawodnych kolejek z mechanizmami ponawiania (Retry) i harmonogramowania (Cron/Beat).

**Pytanie decyzyjne:**  
Jaki zestaw frameworka webowego, silnika bazy danych oraz brokera zadań asynchronicznych zapewni najszybsze dostarczenie zaawansowanego narzędzia kuratorskiego, będąc jednocześnie w stanie udźwignąć skomplikowane operacje GIS, przy zachowaniu założeń Architektury Heksagonalnej?

---

## Debata przed decyzją

**Frontend / Fullstack Engineer:** Największym kosztem początkowym tego projektu będzie interfejs dla administratorów. Budowa dedykowanego panelu w React/Vue od zera (obsługa map, widżetów M2M, walidacji JSON) zajmie miesiące. Potrzebujemy frameworka z wbudowanym, darmowym panelem generowanym na podstawie modeli.  
**Software Architect:** Użycie Django jest ryzykowne dla Czystej Architektury. ORM Django oparty na wzorcu *Active Record* ma silną tendencję do "rozlewania się" (leaking) na logikę biznesową. FastAPI + SQLAlchemy zapewniłoby czystszy podział warstw i natywną asynchroniczność (async I/O). Niemniej, gotowy panel Admina i GeoDjango to potężne argumenty rynkowe.  
**DevOps / DBA:** PostGIS to absolutny standard branżowy, ale jego integracja niesie koszty. GeoDjango wymaga obecności ciężkich binariów systemowych (GDAL, GEOS, PROJ) w środowisku operacyjnym. Oznacza to, że nasz obraz Docker będzie ciężki, a programiści będą mieli problemy z uruchomieniem projektu lokalnie (poza WSL/Dockerem). Musimy też upewnić się, że testy jednostkowe domeny nie będą uderzać w bazę, bo uruchomienie PostGISa w szybkim CI będzie zbyt wolne.

*Wniosek z debaty:* Szybkość dostarczenia narzędzia dla administratora (Panel Django) i potęga GeoDjango w operacjach GIS przeważają nad architektonicznym ryzykiem monolitu. Ryzyko to zneutralizujemy za pomocą twardych kontraktów (narzucenie Portów i Adapterów w kodzie Pythona). Koszty infrastrukturalne (GDAL) akceptujemy jako nieunikniony podatek od zaawansowanego GIS-u.

---

## Opcje rozważane

### Opcja A: FastAPI + SQLAlchemy / GeoAlchemy2 + ARQ + PostGIS
**Opis:** Lekki, natywnie asynchroniczny framework z czystym ORMem i prostą kolejką zadań opartą na Redis (ARQ).
**Plusy:**
- Świetna wydajność, ścisłe wymuszanie separacji warstw (łatwe wdrożenie DDD).
**Minusy:**
- Brak wbudowanego panelu administracyjnego (gigantyczny koszt zbudowania własnego UI do zarządzania mapami i odznakami).
- Słabsza i bardziej sfragmentaryzowana dokumentacja dla zaawansowanych funkcji GIS w porównaniu do GeoDjango.

### Opcja B: Django + Celery + PostGIS (GeoDjango)
**Opis:** Kompletny framework "Batteries-included", standard branżowy dla kolejek (Celery) oraz potężna nakładka przestrzenna na ORM.
**Plusy:**
- **Django Admin:** Oszczędność setek godzin pracy dzięki automatycznym formularzom, integracji `django-leaflet` i `django-jsonform`.
- **GeoDjango:** Abstrakcje w Pythonie pozwalające na bezpieczne i precyzyjne odpytywanie funkcji PostGIS.
- **Celery:** Battle-tested rozwiązanie do długich zadań, z łatwym zarządzaniem harmonogramami (Celery Beat).
**Minusy:**
- "Ciężki" framework, domyślnie synchroniczny.
- Ryzyko zaciemnienia logiki domenowej kodem powiązanym z frameworkiem.

### Opcja C: Rozwiązania bezserwerowe (Serverless) + SQLite/SpatiaLite
**Opis:** Lekka architektura pozbawiona dedykowanej bazy relacyjnej.
**Plusy:**
- Trywialne wdrożenie, brak problemów z ciężkimi obrazami Docker (brak GDAL/PostGIS).
**Minusy:**
- SpatiaLite nie udźwignie równoległych operacji `ST_Union` przy setkach zapytań z Celery (problemy z ryglem bazy - DB Locking).

---

## Decyzja

**Wybrano: Opcja B — Django + Celery + PostGIS (GeoDjango)**

Krytycznym czynnikiem sukcesu w fazie zasilania systemu (Data Stewardship) jest dostarczenie wygodnego, mapowego interfejsu dla organizatora PTTK, który pozwala na rozwiązywanie konfliktów z OSM i definiowanie reguł. Ekosystem Django rozwiązuje ten problem całkowicie bez budowania własnego frontendu. Skomplikowane przetwarzanie geograficzne zostanie bez wahania oddelegowane do silnika PostGIS. Monolityczna i wiążąca natura frameworka Django zostanie odizolowana od logiki biznesowej za pomocą rygorystycznego lintera importów, który obroni warstwę `domain/` przed zależnościami od Django.

---

## Konsekwencje

### Pozytywne
- **Time-to-Market:** Gotowy, bezpieczny i rozszerzalny panel zarządzania (CRUD, mapy Leaflet, formularze JSON) od pierwszego dnia projektu.
- **Odporność na awarie zewnętrzne:** Integracja Celery z Redis pozwala na zaawansowaną logikę ponawiania (Backoff/Retry) dla tysięcy zapytań do niestabilnego API OpenStreetMap.

### Negatywne / Ograniczenia
- **Wymóg binariów systemowych (Infrastructure Tax):** Użycie GeoDjango wymusza posiadanie zainstalowanych paczek systemowych na maszynie dewelopera. Środowisko deweloperskie opiera się na dystrybucji Linuxa (Ubuntu/WSL2) oraz wymusza stosowanie cięższych obrazów kontenerowych.
- **Architektura Testów:** Silne powiązanie modeli Django z bazą narzuca konieczność stworzenia całkowicie niezależnych struktur *Test Doubles* (np. `FakeBadgeRepository`) oraz testowania logiki biznesowej bez użycia bazy danych, aby spełnić wymóg czasowy `< 10s` dla testów lokalnych.
- **Ryzyko szczelności Domeny:** Konieczność stałego monitorowania i odpierania pokus rozwiązywania problemów biznesowych za pomocą Django ORM wewnątrz czystej Domeny (np. pokusa, by `BadgeVersionDomain.evaluate()` wywołało wprost `TouristObject.objects.filter()`, żeby sprawdzić, czy szczyt istniał w danym dniu — zamiast otrzymać tę informację wstrzykniętą czysto przez port).

### Działania wymagane (Zrealizowane)
- [x] Opracowanie pliku `14-domain-purity.md` zakazującego importowania modułów Django do logiki biznesowej.
- [x] Konfiguracja środowiska wirtualnego kompatybilnego z `gdal-bin`.
- [x] Podzielenie systemu na odseparowane komponenty: Modele (Zapis w Django), Use Case'y (Aplikacja), Taski (Owijka dla Celery) i Domenę (Czysty Python).

---

## Warunek rewizji

Gdy system wyjdzie poza obszar zarządzania i kurateli danych (Panel Admina), a obciążenie zacznie generować ruch ze strony tysięcy użytkowników mobilnych odpytujących wyłącznie końcówki API. Wtedy należy rozważyć pozostawienie bazy PostGIS oraz aplikacji Django (tylko jako Headless CMS / Panel Admina), a przepisanie samych endpointów klienckich na lżejszy framework asynchroniczny (np. Go / FastAPI), podpięty bezpośrednio pod płaskie modele odczytu zrealizowane przez CQRS.

---

## Referencje

- **ADR-002 — Typy geometryczne PostGIS jako transport infrastrukturalny.** Jest to bezpośrednia tarcza obronna, która mitiguje negatywne skutki niniejszej decyzji (ADR-001) powstrzymując typy obiektów systemowych GDAL/GEOS przed wciekaniem do czystej logiki systemu.
- Architektura Heksagonalna (Ports and Adapters).
