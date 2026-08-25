# ADR-016 — Rozdzielenie tożsamości od autoryzacji (Model Rodzinny)

> **Status:** `accepted`
> **Data:** 2026-06-16
> **Autor:** Dominik / AI Architect
> **Zastępuje:** —
> **Zastąpiony przez:** —

---

## Kontekst

Aplikacja opierała się pierwotnie na klasycznym wzorcu: `1 Użytkownik (User) = 1 Turysta`. Weryfikacja tożsamości odbywała się za pomocą Google OAuth. Podczas testów i analizy User Experience (UX) napotkano krytyczny problem biznesowy: **Aplikacja wykluczała dzieci i osoby starsze**. Dzieci (np. 8-letnie), które są główną grupą docelową wielu odznak (wymuszaną przez `MinAgeRule`/`MaxAgeRule`), nie posiadają własnych kont Google ani skrzynek e-mail. Zmuszanie rodziców do zakładania fałszywych kont e-mail dla swoich dzieci w celu rejestracji w systemie zostało uznane za drastyczny błąd UX (Friction). Z kolei zmuszanie właściciela systemu do utrzymywania bazy haseł dla kont tradycyjnych stanowiło nieakceptowalne ryzyko bezpieczeństwa (RODO).

**Pytanie decyzyjne:**
W jaki sposób umożliwić jednej osobie uwierzytelnionej (np. ojcu z kontem Google) zarządzanie postępami wielu turystów (dzieci), bez jednoczesnego skomplikowania procesu walidacji wieku w Czystej Domenie i bez utraty rygoru bezpieczeństwa bazy danych?

---

## Debata przed decyzją

**Product Owner:** Potrzebujemy modelu "Konta Rodzinnego", znanego z Netflixa ("Kto teraz ogląda?"). Ojciec loguje się na swój e-mail, ale potem w rogu ekranu przełącza się na profil córki i loguje jej szczyty.
**Security Engineer:** To rodzi potężne ryzyko IDOR (Insecure Direct Object Reference). Jeśli API przyjmie log z `profile_id=15`, musimy za każdym razem sprawdzać, czy twórca requestu (`request.user`) jest faktycznym właścicielem (`owner`) tego profilu.
**Domain Expert:** Jeśli Domena przyjmie w obiekcie DTO zły wiek, weryfikacja zostanie sfałszowana. Czysta Domena nie może ufać kontom, musi ufać profilom.

*Wniosek z debaty:* Należy całkowicie odseparować system uwierzytelniania (Authentication / Identity Provider) od tożsamości domenowej (Profile).

---

## Opcje rozważane

### Opcja A: Sub-konta (Logowanie lokalne dla dzieci)
**Opis:** Aplikacja oferuje Google OAuth dla dorosłych, ale umożliwia tworzenie lokalnych kont "zależnych" (login i hasło lub PIN) dla dzieci.
**Plusy:** Zgodność ze standardowym modelem 1 User = 1 Odznaka.
**Minusy:** Ryzyko wycieku haseł. Ogromny narzut na tworzenie interfejsów odzyskiwania haseł (które dzieci i tak by gubiły).

### Opcja B: Parowanie kodami (Konto widmo)
**Opis:** Dziecko używa aplikacji w trybie gościa na osobnym telefonie, a rodzic skanuje kod QR, aby zatwierdzać jego osiągnięcia.
**Plusy:** Pełna autonomia dziecka.
**Minusy:** Architektura przerastająca potrzeby MVP. Wymaga podziału aplikacji na "Aplikację Rodzica" i "Aplikację Dziecka".

### Opcja C: Multi-Profile / Family Model (Wybrane)
**Opis:** Model `User` (Django Auth) trzyma wyłącznie adres e-mail i sesję. Model `TouristProfile` (wraz z wiekiem, pseudonimem i planem Freemium) staje się Głównym Aktorem Domeny. Relacja zmienia się z `OneToOne` na `ForeignKey` (Jeden `User` ma wiele `TouristProfile`). Ojciec przełącza aktywny profil zapisując go w zmiennej sesyjnej (`request.session['active_profile_id']`).

---

## Decyzja

**Wybrano: Opcja C — Multi-Profile / Family Model**

Podejście to wymagało głębokiej refaktoryzacji, wymiany `user_id` na `profile_id` we wszystkich DTO, Portach i Adapterach oraz aktualizacji kilkudziesięciu testów, jednak pozwoliło na zachowanie spójności Czystej Domeny. Domena nigdy nie widzi obiektu `User`. Odbiera ustandaryzowany `VerificationContext` w oparciu o wiek płynący bezpośrednio z wybranego `TouristProfile`.

---

## Konsekwencje

### Pozytywne
- Ogromne ułatwienie UX dla rodzin z dziećmi.
- **Model Biznesowy:** Funkcja ta otworzyła nową ścieżkę monetyzacji systemu. Pakiety Freemium zostały przebudowane tak, by darmowe konto (`FREE`) pozwalało na 1 profil, a płatne konto (`FAMILY / PRO`) pozwalało rodzicowi na dodanie np. 5 profili pod jednym adresem e-mail.
- Ochrona Danych Osobowych: Usunięcie e-maili z widoku publicznego. W systemie istnieje tylko `nickname`.

### Negatywne / Ograniczenia
- Konieczność wdrożenia w widokach rygorystycznego zabezpieczenia przed IDOR.
- Konieczność dbania o "zrzut" aktywnego stanu w przypadku wylogowania lub wygasłej sesji (system stosuje Leniwą Inicjalizację - wybiera domyślnie pierwszy utworzony przez użytkownika profil w przypadku braku aktywnej sesji `profile_id`).

### Działania wymagane (Zrealizowane w lipcu 2026)
- [x] Zmiana twardych relacji w bazie dla modeli `AscentLog` i `UserBadgeProgress` z modelu `User` na `TouristProfile`.
- [x] Zmiana w API wszystkich kluczy wejściowych z `user_id` na `profile_id`.
- [x] Dodanie Endpointu i Widgetu HTMX do przełączania profilu w locie (Dropdown Menu).
- [x] Sygnał Django automatycznie tworzący pierwszy, darmowy profil po pierwszym uwierzytelnieniu przez Google OAuth.

---

## Relacje (Related)
- **C4 Diagram:** `docs/architecture/containers.puml`
- **Kontrakty:** `docs/Manifest/14-domain-purity.md` (Import Linter rule: `domain-purity`)
- **Dług (Debt):** DŁUG-002 — świadome naruszenie czystości architektury w `apps/` z powodu Django ORM
```
