# ADR-010 — Dynamiczne kolorowanie mapy i priorytetyzacja stanów odznak

> **Status:** `accepted`  
> **Data:** 2026-05-30  
> **Autor:** Dominik / AI Architect  
> **Zastępuje:** —  
> **Zastąpiony przez:** —

---

## Kontekst

Aplikacja turystyczna docelowo (Faza C) ma prezentować użytkownikowi mapę obiektów pokolorowaną w zależności od ich przydatności. Stan użyteczności szczytu zmienia się, jeśli użytkownik już go zdobył lub jeśli obiekt objęty jest regułami odznak, które turysta aktywnie zdobywa. 
Jeden obiekt fizyczny (np. Babia Góra) może należeć do wielu odznak jednocześnie. Odznaka A może pozwalać na wejście dzisiaj, a Odznaka B może mieć okno czasowe (np. tylko zimą).

**Pytanie decyzyjne:**  
W jaki sposób ujednolicić reprezentację wizualną obiektu turystycznego podlegającego sprzecznym regułom z wielu odznak, aby mapa była jednoznaczna dla turysty, a logika pozostała optymalna i bezpieczna architektonicznie?

---

## Debata przed decyzją

**Frontend Engineer:** Mapa wymaga jednego parametru statusu dla pinezki (MVT/GeoJSON). Backend musi podać ostateczny werdykt.  
**UX Designer:** Turysta na szlaku potrzebuje odpowiedzi: "Czy opłaca mi się wejść tu dzisiaj?". Zachęta do akcji jest ważniejsza niż blokada. Potrzebujemy stanów: Czerwony (Idź), Niebieski (Idź ponownie dla innej odznaki), Pomarańczowy (Zablokowane na dziś), Zielony (Zdobyty), Szary (Poza kontekstem).  
**Performance / DBA:** Uruchomienie reguł domenowych (w tym arytmetyki czasu `TimeLimitRule`) dla tysięcy szczytów pomnożonych przez kilkanaście aktywnych odznak użytkownika daje złożoność $O(N \times M)$. Wyliczanie tego w locie dla każdego żądania HTTP złamie KPI `< 50ms` określone w `VISION.md`.  
**Software Architect:** Usługa oceniająca "czy wejście dzisiaj się powiedzie" zależy od czasu. Zgodnie z Invariantem `T-02`, czas wymusza wstrzyknięcie `ClockPort`. Dlatego usługa ta (`BadgeEligibilityService`) **nie może** znajdować się w Czystej Domenie (`domain/`), lecz musi być Usługą Aplikacyjną (`application/services/`).

---

## Opcje rozważane

### Opcja A: Zrzucenie konfliktu na Frontend (Fat Client)
**Opis:** API zwraca tablicę statusów dla każdego szczytu, frontend decyduje co z tym zrobić.
**Minusy:** Ciężki payload, powielanie logiki domenowej na iOS, Android i Web.

### Opcja B: Redukcja Priorytetów na Backendzie (Wygrywa najwyższy status)
**Opis:** `BadgeEligibilityService` (w `application/`) symuluje wejścia dla każdej odznaki z datą pobraną z `ClockPort`. Jeśli wyniki są sprzeczne, redukuje je do jednej wartości (`max(priorities)`), gdzie akcja "dziś" (Czerwony/Niebieski) przebija oczekiwanie (Pomarańczowy). Wyniki są wyliczane w locie.
**Plusy:** Jeden punkt prawdy, brak logiki na froncie.
**Minusy:** Zabija wydajność serwera przy każdym ruchu mapą.

### Opcja C: Podejście Hybrydowe z Cache'owaniem (Wybrane)
**Opis:** Logika redukcji z Opcji B zostaje na Backendzie, ale wyniki są trwale buforowane w Redis. Kluczem cache'u jest `(user_id, date_from_clock, map_context)`. 
**Plusy:** Błyskawiczny odczyt mapy zgodny z KPI `< 50ms`. Złożona ewaluacja domenowa wykonywana jest tylko raz dziennie (po północy) lub przy inwalidacji.

---

## Decyzja

**Wybrano: Opcja C — Redukcja Priorytetów na Backendzie z Agresywnym Buforowaniem**

Izolujemy aplikacje klienckie od skomplikowanych zmian w regulaminach. `BadgeEligibilityService` zostanie wdrożony jako Application Service (wymagający `ClockPort` i dostępu do DTO wejść). Aby zneutralizować katastrofalny narzut wydajnościowy, wprowadzamy Redis Cache.

---

## Konsekwencje

### Pozytywne
- Frontend pozostaje "głupi" (renderuje to, co dostanie).
- Jednorodne wykorzystanie reguł `BadgeRule` (Brak duplikacji logiki weryfikacyjnej i mapowej).

### Negatywne / Ograniczenia
- Konieczność rygorystycznego zarządzania Inwalidacją Cache (Cache Invalidation). Każde nowe zalogowanie wejścia przez turystę (`AscentLogCreated`) musi bezwzględnie zniszczyć jego klucz cache w Redis, by mapa natychmiast odzwierciedliła zmianę (Immediate Consistency dla działań własnych).

### Działania wymagane
- [ ] Utworzenie `BadgeEligibilityService` w katalogu `application/services/`.
- [ ] Oprogramowanie inwalidacji cache w Redis przy zapisie logu wejścia.