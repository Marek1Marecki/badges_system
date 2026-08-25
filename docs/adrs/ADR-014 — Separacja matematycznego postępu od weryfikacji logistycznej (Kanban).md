# ADR-014 — Separacja matematycznego postępu od osobistej logistyki (Tracker)

> **Status:** `accepted`  
> **Data:** 2026-06-02  
> **Autor:** Dominik / AI Architect  

---

## Kontekst

Zdobycie odznaki turystycznej dzieli się na dwa etapy: matematyczne spełnienie warunków z regulaminu (zdobycie) oraz papierowa biurokracja (wysłanie fizycznej książeczki pocztą do PTTK, oczekiwanie na weryfikację i odesłanie blachy). Aplikacja nie integruje się z systemami oddziałów PTTK (B2B), lecz służy wyłącznie Turyście jako narzędzie B2C (Osobisty Tracker).

**Pytanie decyzyjne:**  
W jaki sposób zamodelować stany zdobywania odznak, aby oddzielić czystą walidację od śledzenia wysyłek pocztowych przez turystę?

---

## Debata przed decyzją

**Backend Engineer:** Dodajmy pole `status` do `UserBadgeProgress` z enumem od `IN_PROGRESS` aż po `ALBUM`. To jedna tabela i jedno źródło prawdy.  
**Domain Expert:** Fakt wejścia na górę to czysta matematyka. Logistyka to osobny kontekst. Domena weryfikacji nie może znać pojęć "Poczta" czy "Album".  
**UX Designer:** Nie możemy zmuszać systemu do integracji z urzędnikami PTTK. Kanban logistyczny ma służyć tylko jako przypominajka ("alert po 30 dniach") dla turysty. To on jest właścicielem tego procesu i sam "przeklikuje" etapy.

*Wniosek z debaty:* Należy odseparować matematyczny postęp (Sito) od logistyki, zachowując jednak oba te stany bezpośrednio w kontroli Użytkownika.

---

## Opcje rozważane

### Opcja A: Jedna, liniowa Maszyna Stanów
**Opis:** Silnik Domenowy zna wszystkie statusy (w tym logistyczne).

### Opcja B: Rozdzielenie na Snapshot Domenowy i Osobisty Tracker
**Opis:** Obliczanie postępu odbywa się w locie, a wynik (`NOT_STARTED`, `IN_PROGRESS`, `COMPLETED`) jest zapisywany jako *State Snapshot* w `UserBadgeProgress`. Ten zmaterializowany status odblokowuje dostęp do drugiej, niezależnej maszyny stanów logistycznych (np. nowe pola w tej samej encji: `logistic_status`, `sent_date`), którymi turysta zarządza całkowicie ręcznie.

---

## Decyzja

**Wybrano: Opcja B — Rozdzielenie na Snapshot Domenowy i Osobisty Tracker**

Czysta Domena stwierdza fakt `COMPLETED` i zapisuje go w tabeli progresu. To odblokowuje dla turysty moduł Logistyki w UX. Odrzucono koncepcję budowy systemu B2B dla Weryfikatorów, ograniczając system do wsparcia pamięci turysty (alerty 30-dniowe liczone w locie w widokach).

---

## Konsekwencje

### Pozytywne
- Czysta Domena (`BadgeVersionDomain`) nie wie nic o poczcie i blachach (Invariant S-03).
- Brak skomplikowanych agregatów "Wniosków Zbiorczych" — system jest ekstremalnie lekki.

### Działania wymagane (Zrealizowane)
- [x] Odrzucenie agregatu `VerificationRequest`. Pola logistyczne trafiają do `UserBadgeProgress`.
- [x] Dopisanie zakazu mieszania statusów (S-03) do `INVARIANTS.md`.

## Relacje (Related)
