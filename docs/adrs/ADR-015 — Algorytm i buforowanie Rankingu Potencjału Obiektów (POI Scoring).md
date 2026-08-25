# ADR-015 — Algorytm i buforowanie Rankingu Potencjału Obiektów (POI Scoring)

> **Status:** `accepted`  
> **Data:** 2026-06-02  
> **Autor:** Dominik / AI Architect  

---

## Kontekst
W ramach rozbudowy grywalizacji (Gamification), aplikacja ma podpowiadać turyście, które obiekty turystyczne (POI) są dla niego najbardziej "opłacalne" do zdobycia w danym momencie. Opłacalność rośnie wraz ze zbliżaniem się do ukończenia odznaki. Ze względu na zawiłości regulaminowe (okna czasowe, pory roku), wartość ta zależy od Czystej Domeny, a ze względu na wydajność - nie może być liczona synchronicznie na żądanie przy renderowaniu widoków list i map.

**Pytanie decyzyjne:**  
Jaki model matematyczny przyjąć dla oceny potencjału szczytów i jak zaprojektować jego przeliczanie, aby nie zablokować bazy danych przy tysiącach zapytań o ranking regionalny?

---

## Decyzja

**Wybrano: Algorytm "100/n" z asynchroniczną pre-kalkulacją (Redis Cache)**

1. **Model Matematyczny:**
   Każdy szczyt otrzymuje punkty za każdą subskrybowaną przez użytkownika (i nieukończoną w danym Cyklu) Wersję Odznaki. Wzór to: `Score = Suma( 100 / n )`, gdzie `n` to liczba szczytów pozostałych do zdobycia w danej odznace/stopniu.
   Wynik jest zaokrąglany do liczby całkowitej (Integer). Zdobycz na poziomie 100 punktów oznacza matematycznie ekwiwalent ukończenia dokładnie jednej całej odznaki.

2. **Warunkowanie Domenowe (Sito):**
   Jeśli Czysta Domena (`BadgeRule.validate()`) odrzuci potencjalne wejście na dziś (np. z powodu `DateWindowRule` lub odznaki zimowej latem), odznaka ta generuje `0` punktów do rankingu dla tego obiektu na dany dzień.

3. **Infrastruktura (Event-Driven Cache Invalidation):**
   Ranking nie jest liczony w locie (On-Demand) przy każdym ruchu mapą. Wyniki są buforowane w Redis. Zamiast zasobożernego, codziennego przeliczania wszystkich turystów, wdrożono unieważnianie cache'u oparte na zdarzeniach (Event-Driven). Klucz Redis dla danego turysty jest niszczony (co wymusza przeliczenie przy najbliższym odczycie) WYŁĄCZNIE gdy wystąpi jedno ze zdarzeń psujących stan:
   - Zdarzenia Użytkownika: Dodanie wejścia na szczyt, zmiana subskrypcji odznak.
   - Zdarzenia Czasowe: Dzień urodzin turysty (wpływ na `MinAge/MaxAgeRule`), otwarcie/zamknięcie predefiniowanych okien sezonowych lub jubileuszowych.
    - Zdarzenia Administracyjne: Zmiana flagi `is_active` obiektu w bazie, modyfikacja puli odznaki.

## Relacje (Related)


---

## Konsekwencje

### Pozytywne
- Ogromny spadek obciążenia procesora serwera w nocy. Architektura Event-Driven ogranicza przeliczenia wyłącznie do tych użytkowników, u których fizycznie zaszła zmiana stanu biznesowego.

### Negatywne / Ograniczenia
- Złożoność architektury zdarzeniowej: Każdy nowy proces biznesowy (np. dodanie nowego typu reguły czasowej) wymusza na programiście pamiętanie o dodaniu odpowiedniego "włącznika" inwalidującego cache użytkowników.