# ADR-018 — Uwierzytelnienie i Zarządzanie Tożsamością (Google OAuth + Model Rodzinny)

> **Status:** `accepted`
> **Data:** 2026-08-20
> **Autor:** AI Architecture / System Owner
> **Zastępuje:** Brak
> **Zastąpiony przez:** Brak
> **Związane:** ADR-016 — Rozdzielenie tożsamości od autoryzacji (Model Rodzinny)

---

## Kontekst

Aplikacja PTTK Badges wymaga prostego, bezpiecznego i szybkiego logowania dla turystów, którzy w górach nie chcą pamiętać haseł ani registracji formularzami. Jednocześnie potrzebujemy modelu "Konta Rodzinnego" (Familly Account), gdzie jeden login Google może obsługiwać wielu członków rodziny (dzieci, rodziców) z odrębnymi profilami. Wymagania to: zerowy próg rejestracji, brak ryzyka wycieku haseł oraz silna separacja tożsamości (Google) od profilu turysty.

**Pytanie decyzyjne:**
Jak zaimplementujemy uwierzytelnianie, aby zapewnić zero-jednoznaczną rejestrację przez Google, model rodzinny profili i separację tożsamości od logiki domenowej PTTK, nie zarządzając hasłami?

---

## Opcje rozważane

### Opcja A: Django `auth.User` + hasła lokalne z rejestracją formularzem
**Opis:** Standardowy system Django z `UserCreationForm`, hasłami w bazie i `django.contrib.auth`.
**Plusy:**
- Zero dodatkowych zależności poza Django.
- Pełna kontrola nad walidacją haseł i resetami.

**Minusy:**
- Wymaga rejestracji i pamiętania hasła — znacząco podnosi próg dla turystów w terenie.
- Ryzyko wycieku haseł (choć haszowane, to dodatkowy attack surface).
- `auth.User` mocno splata się z profilem turysty — trudna separacja tożsamości od danych PTTK.

### Opcja B: django-allauth + Google OAuth2 + `TouristProfile` jako oddzielna encja
**Opis:** Uwierzytelnianie wyłącznie przez Google OAuth2 (`django-allauth`), `auth.User` = jedynie tożsamość. `TouristProfile` to osobny model z `ForeignKey` do `User` (relacja 1:N), obsługujący "Konto Rodzinne".

**Plusy:**
- Zero hasła — turysta loguje się Google’em (single tap na telefonie).
- `auth.User` przechowuje **tylko** tożsamość (email, Google ID); dane PTTK (`peak_ids`, `active_profile`, logowanie) żyją w `TouristProfile` — czysta separacja.
- Model rodzinny: każdy `User` może mieć wielu `TouristProfile` (dzieci, rodzice); aktywny profil wybierany w UI.
- Brak ryzyka wycieku haseł — nie ma hasła do wycieku.

**Minusy:**
- Zależność od `django-allauth` (ciężka, ale utrzymywana).
- `auth.User` musi pozostać "anemicznym" — logika domenowa nie może importować ani zależeć od `allauth`.

---

## Decyzja

Wybieramy **Opcję B: django-allauth + Google OAuth2 + `TouristProfile`**.

**Zasady wynikające z decyzji (chroniące architekturę):**
1. `auth.User` = **ewoluowanie tożsamości** — nie może zawierać logiki PTTK.
2. `TouristProfile` = **agregat turysty** — jedyny model z danymi PTTK, `ForeignKey` → `auth.User`.
3. `apps.api.views` pobiera profil **wyłącznie** przez `request.session.get("active_profile_id")` (lub fallback) — nigdy nie importuje `allauth` ani `auth.User` bezpośrednio w logice domenowej.
4. Weryfikacja e-maila odbywa się przez Google (verified email w OAuth), nie przez `django-allauth` confirmation logic — to **tożsamość**, nie **profil**.

---

## Konsekwencje

### Pozytywne
- 0 wycieków haseł — brak haseł w systemie.
- Zero barier rejestracyjnych dla turystów w terenie.
- Czysta separacja tożsamości (User) od profilu (TouristProfile) umożliwia późniejszą zmianę dostawcy OAuth bez migracji danych PTTK.

### Negatywne / Działania wymagane
- [ ] `TouristProfile` musi być tworzony lazily (`get_or_create`) w middleware/views — patrz AUDYT-069 (race condition).
- [ ] Upewnić się, że `User.email` jest wystarczający dla logiki domenowej (inaczej wstrzyknąć `IdentityPort`).
- [ ] Zadbać o fallback, gdy użytkownik usuwa Google Connection — profil PTTK zachowuje się jako "osiercony".

---

## Warunek rewizji (Trigger for Review)

Zrewidować, gdy:
- Potrzebujemy lokalnych kont administratorów (np. Weryfikatorom PTTK) — można dodać `admin/` auth osobno.
- Google OAuth straci trust lub zmieni API — `django-allauth` ma wymianę na innego dostawcę OAuth w konfiguracji.
- Model rodzinny stanie się skomplikowany (np. grupy współdzielenia odznak) — rozważyć `django-guardian` (zob. AUDYT-057).

## Relacje (Related)
- **Z:** ADR-016 — Rozdzielenie tożsamości od autoryzacji (Model Rodzinny).
- **Z:** AUDYT-069 — race condition w leniwym tworzeniu `TouristProfile` (`get_or_create`).
- **Z:** AUDYT-070 — niespójne pobieranie `profile_id` w API.
- **Kontrakty:** `apps.tourists` i `apps.badges` mogą importować `auth.User`, ale `domain/` i `application/` nie mogą (import-linter zabrania).
