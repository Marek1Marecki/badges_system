# ADR-028 — Podział Bounded Contexts (Billing i Notyfikacje)

> **Status:** `accepted`  
> **Data:** 2026-09-08  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Aplikacja PTTK Badges dojrzała strukturalnie w obrębie dwóch głównych Domen Biznesowych (Core Domains):
1. **Catalog Context** (`apps.badges`): Zarządzanie "Złotym Standardem" geografii PTTK, regułami odznak i danymi z OSM.
2. **Tourist Context** (`apps.tourists`): Śledzenie historii logów turysty, Osobisty Kanban logistyczny i ewaluacja postępów.

Zgodnie z wchodzeniem w Fazę komercjalizacji (Pakiety Freemium / PRO) oraz potrzebą zwiększenia zaangażowania użytkowników (Retention), zdefiniowano wymagania biznesowe stworzenia dwóch nowych obszarów:
- **Billing:** Obsługa subskrypcji, bramek płatności (np. Stripe/PayU) oraz limitów kont (Quotas).
- **Notifications:** Obsługa komunikacji asynchronicznej (wysyłanie e-maili "Gratulacje, zdobyłeś odznakę!", powiadomień Push, przypomnień o niewysłanych książeczkach po 30 dniach).

**Pytanie decyzyjne:**  
W jaki sposób zintegrować te nowe wymagania w istniejącym kodzie, by uniknąć zjawiska "Wielkiej Kuli Błota" (Big Ball of Mud) i zachować niezależność cykli wydawniczych dla poszczególnych modułów?

---

## Opcje rozważane

### Opcja A: Zmodyfikowanie istniejącego `Tourist Context` (Rozbudowa Monolitu)
**Opis:** Dodanie logiki płatności Stripe i funkcji wysyłania e-maili bezpośrednio do przypadków użycia takich jak `LogAscentUseCase` czy `StartBadgeProgressUseCase`.
**Plusy:** Najszybsze dostarczenie biznesowe (szybkie pisanie kodu).
**Minusy:** Krytyczne złamanie Single Responsibility Principle. Wymóg testowania bramek płatniczych za każdym razem, gdy zmieniana jest logika matematyczna weryfikacji gór. Silne sprzężenie (Coupling) powodujące, że błąd w serwerze SMTP może zablokować zapis wycieczki w bazie danych (!!!).

### Opcja B: Nowe Konteksty Ograniczone i asynchroniczna szyna zdarzeń (Modular Monolith) (Wybrane)
**Opis:** Płatności i Notyfikacje powołuje się do życia jako niezależne moduły Django (`apps.billing` i `apps.notifications`), posiadające własne bazy (lub wyizolowane tabele), własne modele i własne porty. Komunikacja między "Turystą" a "Billingiem" czy "Notyfikacjami" odbywa się w 100% asynchronicznie za pośrednictwem zdefiniowanych Zdarzeń Domenowych (Domain Events) publikowanych do brokera (Celery / RabbitMQ).

---

## Decyzja

Wdrażamy architekturę Modularnego Monolitu (Modular Monolith) ze ścisłymi granicami opartymi na Zdarzeniach Domenowych (Event-Driven Architecture).

1. **Nowe aplikacje Django (Bounded Contexts):**
   Powołuje się do życia wydzielone moduły aplikacyjne: `apps.billing` (odpowiada za pakiety PRO, płatności, faktury) oraz `apps.notifications` (odpowiada za zarządzanie szablonami e-mail/push, dostarczalnością i subskrypcjami użytkowników na powiadomienia).

2. **Event-Driven Choreography (Asynchroniczna Komunikacja):**
   Moduły nie mogą komunikować się poprzez bezpośrednie odwołania do Use Case'ów z innego modułu. Wszelka interakcja opiera się na Reagowaniu na Fakty (Event Sourcing).
   *Przykład:* Gdy `StartBadgeProgressUseCase` zakończy działanie, emituje `BadgeStatusChanged(status='COMPLETED')`. Moduł `notifications` (w osobnym workerze Celery) nasłuchuje tego zdarzenia i podejmuje suwerenną decyzję o wysłaniu e-maila gratulacyjnego do turysty.

3. **Anti-Corruption Layer (ACL):**
   Moduły `billing` i `notifications` posiadają własne mini-adaptery. Nawet jeśli działają w tym samym kodzie Pythona, muszą pobierać identyfikator użytkownika z payloadu zdarzenia i (w razie potrzeby) odpytywać API/Porty z innej aplikacji o szczegóły (np. adres e-mail przypisany do profilu), zamiast importować bezpośrednio klasę modelu `TouristProfile`.

4. **Egzekwowanie przez Linter:**
   Reguły te zostaną zabetonowane w konfiguracji narzędzia `import-linter`, z twardym wymogiem niezależności: np. `apps.tourists` nie ma prawa posiadać importów z `apps.billing`.

---

## Konsekwencje

### Pozytywne
- **Izolacja Awarii (Fault Tolerance):** Awaria serwerów płatności (Stripe) lub poczty e-mail nie blokuje podstawowej funkcjonalności aplikacji – turysta w górach nadal może dodawać wycieczki offline/online.
- **Testowalność:** Płatności i Powiadomienia mogą być testowane i rozwijane przez odrębny zespół deweloperów, bez ingerencji w skomplikowaną domenę weryfikacji terytorialnej PTTK.
- System jest strukturalnie i organizacyjnie przygotowany do łatwego "rozłupania" (Extraction) do mikroserwisów, jeśli obciążenie powiadomieniami przekroczy wydolność jednego serwera (np. 100k e-maili dziennie).

### Negatywne / Działania wymagane
- Konieczność zarządzania spójnością ostateczną (Eventual Consistency). Interfejs użytkownika (UI) musi informować turystę, że np. "Twój plan PRO zostanie aktywowany w ciągu kilku minut", zamiast blokować ekran do natychmiastowego potwierdzenia transakcji.
- Wymaga rozbudowy infrastruktury Zdarzeń Domenowych (np. wdrożenie Outbox Pattern w adapterze bazy, by upewnić się, że żadne zdarzenie nie zgubi się w razie awarii Redis/Celery podczas transakcji).

---

## Warunek rewizji

Strategia zakłada wykorzystywanie struktury Modularnego Monolitu i przesyłanie zdarzeń poprzez wewnętrznego brokera (Celery). Dokument podlega rewizji w przypadku, gdy częstotliwość i ilość emitowanych zdarzeń między kontekstami przekroczy możliwości zarządzania jednym repozytorium kodu, co wymusi przeniesienie powiadomień i płatności do architektury Event-Driven Microservices z wykorzystaniem zewnętrznej szyny zdarzeń (np. Apache Kafka).
