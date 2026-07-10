# Security Matrix — macierz uprawnień

> **Wersja:** 1.2  
> **Data:** 2026-06-02  
> **Właściciel:** Dominik / AI Architect  
>
> **Zasada naczelna dla agentów LLM:** Każdy nowy endpoint API (Faza C) lub widok HTMX musi mieć przypisaną rolę z tej tabeli. Brak jawnej autoryzacji = błąd bezpieczeństwa.

---

## Role użytkowników

| Rola | Opis | Jak przypisana w systemie |
|------|------|---------------------------|
| `admin` | Administrator systemu / Kurator danych. | Wbudowana flaga Django `is_staff=True` lub `is_superuser=True`. |
| `owner` | Turysta, który wygenerował dany rekord (np. log wejścia, postęp). | Identyfikator w rekordzie: `resource.user_id == current_user.id`. |
| `authenticated` | Każdy zalogowany turysta. | Ważna sesja Django / Token JWT. |
| `public` | Niezalogowany gość. | Brak uwierzytelnienia. |
| `owner` | Turysta (właściciel konta Google), który ma podpięty dany Profil Turysty. | Identyfikator w rekordzie odnosi się do Profilu (`profile_id`), a Profil posiada `user_id == current_user.id`. Posiadacz konta ma pełny dostęp do wszystkich profili, które sam utworzył (Konta Rodzinne). |
| `anonymous` | `request.user.is_authenticated == False` | Odwiedzający. Posiada dostęp WYŁĄCZNIE do publicznego frontendu i zablokowanych endpointów mapy. |
| `owner` | Profil przypisany do aktualnego konta (`request.session['active_profile_id']` ma właściciela `request.user.id`) | Turysta na swoim koncie. Ma pełne prawa do logowania wejść, zmian w Osobistym Kanbanie oraz aktualizacji wieku/mapy. |
| `admin` | `request.user.is_staff == True` | Właściciel Aplikacji. Ma pełen dostęp do Django Admina, edycji regulaminów, zatwierdzania M2M i Radaru. |

---

## Macierz uprawnień: Faza A i B (Katalog, Infrastruktura)

| Akcja | Rola / Warunek | Uwagi |
|-------|---------------|-------|
| Odczyt mapy, szczytów i regulaminów | `public` | API zwraca tylko obiekty ze statusem `READY` (CQRS). |
| Dodawanie/Edycja obiektów i odznak | `admin` | Poprzez Django Admin. |
| Wyzwalanie Tasków Celery / Konflikty | `admin` | Ręczny *Data Override*. |

---

## Macierz uprawnień: Faza C (Dziennik Wejść i Profil)

Zasób: `AscentLog` (Log wejścia), `TouristProfile`

| Akcja | Rola / Warunek | Uwagi |
|-------|---------|-------|
| Edycja własnego profilu (Data ur., Klub) | `owner` | Wpływa na reguły wiekowe i klubowe w Domenie. |
| Odczyt profilu innego turysty | `public` / `authenticated` | **Privacy by Default:** Ujawniane są *tylko* pola zagregowane (Nickname, liczba odznak). Reszta ukryta, chyba że flaga `is_public = True`. |
| Rejestracja nowego wejścia | `authenticated` | Twórca automatycznie staje się `owner`. |
| Edycja/Usunięcie "niezużytego" wejścia | `owner` | Turysta może swobodnie modyfikować logi, które nie zbudowały jeszcze żadnej zdobytej odznaki. |
| Edycja/Usunięcie "zużytego" wejścia (`COMPLETED`) | `admin` | 🔴 **Blokada dla Turysty:** Jeśli wejście zbudowało "ukończony" Cykl odznaki, `owner` zostaje zablokowany. Wymagana jest asysta Weryfikatora (Autoryzowana Korekta) poprzez osobne zgłoszenie w systemie. |

---

## Macierz uprawnień: Faza C (Postęp i Osobisty Kanban Logistyczny)

Zasób: `UserBadgeProgress`

| Akcja | Rola / Warunek | Uwagi |
|-------|---------------|-------|
| Rozpoczęcie zdobywania | `authenticated` | Tworzy nowy rekord `owner`. Gwarantuje Prawa Nabyte. |
| Otwarcie kolejnego cyklu | `owner` | Tylko jeśli stary cykl ma status `COMPLETED` / `ALBUM`. |
| Wymuszenie przeliczenia postępu | `owner` | Obliczenia na żywo odczytują tylko własne `AscentLog`. |
| Przesunięcie statusu Kanbanu | `owner` | Turysta sam zarządza swoim statusem wysyłki: `WAITING_FOR_SEND` → `VERIFICATION` → `RECEIVING` → `ALBUM`. Nikt inny nie ma dostępu. |