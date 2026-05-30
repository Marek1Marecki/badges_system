# Security Matrix — macierz uprawnień

> **Wersja:** 1.1  
> **Data:** 2026-05-29  
> **Właściciel:** Dominik / AI Architect  
>
> **Zasada naczelna dla agentów LLM:** Każdy nowy endpoint API (Faza C) lub widok HTMX musi mieć przypisaną rolę i warunek dostępu z tej tabeli. Brak jawnej autoryzacji = błąd bezpieczeństwa. Jeśli zasób lub akcja nie istnieje w tej tabeli — zatrzymaj implementację i zgłoś to.

---

## Role użytkowników

| Rola | Opis | Jak przypisana w systemie |
|------|------|---------------------------|
| `admin` | Administrator systemu / Kurator danych. | Wbudowana flaga Django `is_staff=True` lub `is_superuser=True`. |
| `verifier` | Przodownik PTTK / Organizator. Weryfikuje wnioski logistyczne. | Tabela łącząca (M:N) pomiędzy Django `User` a `OrganizerModel` (Jeden przodownik może weryfikować dla wielu oddziałów PTTK jednocześnie). |
| `owner` | Turysta, który wygenerował dany rekord (np. log wejścia). | Identyfikator w rekordzie: `resource.user_id == current_user.id`. |
| `authenticated` | Każdy zalogowany turysta. | Ważna sesja Django / Token JWT. |
| `public` | Niezalogowany gość. | Brak uwierzytelnienia. |

---

## Macierz uprawnień: Faza A i B (Katalog, Infrastruktura)

Zasoby: `TouristObject`, `BadgeModel`, `BadgeVersionModel`, `OsmSyncConflict`, CQRS Cache.

| Akcja | Rola / Warunek | Uwagi |
|-------|---------------|-------|
| Odczyt mapy, szczytów i regulaminów | `public` | API zwraca tylko obiekty ze statusem `READY` (CQRS). |
| Dodawanie/Edycja obiektów turystycznych | `admin` | Poprzez Django Admin. |
| Definiowanie Odznak i Stopni | `admin` | Poprzez Django Admin. |
| Wyzwalanie Tasków Celery (OSM, CQRS) | `admin` | Zabezpieczone na poziomie autoryzacji akcji Admina. |
| Akceptacja konfliktów z OSM | `admin` | Ręczny *Data Override*. |

---

## Macierz uprawnień: Faza C (Dziennik Wejść i Profil)

Zasób: `AscentLog` (Log wejścia), `TouristProfile`

| Akcja | Rola / Warunek | Uwagi |
|-------|---------------|-------|
| Edycja własnego profilu (Data ur., Klub) | `owner` | Wpływa na reguły `MinAgeRule`, `RequiresClubJoinDateRule`. |
| Odczyt publicznego profilu innego turysty | `public` / `authenticated` | **Privacy by Default:** Ujawniane są *tylko* pola zagregowane (Nickname, łączna liczba zdobytych odznak). Zablokowany dostęp do wieku, prawdziwego nazwiska i historii wejść, chyba że flaga `is_public` = True. |
| Rejestracja nowego wejścia na szczyt | `authenticated` | Twórca automatycznie staje się `owner`. |
| Odczyt własnych wejść | `owner` | Filtr `user_id = current_user.id` wymuszony na zapytaniu SQL. |
| Edycja wejścia (Zła data, zmiana zdjęcia) | `owner` | 🔴 **Blokada:** Tylko jeśli wejście **NIE zostało** przypięte do zamkniętego cyklu odznaki (`UserBadgeProgress=COMPLETED`). |
| Usunięcie wejścia | `owner` | 🔴 **Blokada:** Jak wyżej. Próba skasowania "zużytego" wejścia rzuca `PermissionDeniedError`. |
| Wgląd w log wejścia innego turysty | `verifier` | Tylko wtedy, gdy wejście jest częścią przesłanego do niego `VerificationRequest` (ochrona prywatności). |

---

## Macierz uprawnień: Faza C (Postęp i Grywalizacja)

Zasób: `UserBadgeProgress`

| Akcja | Rola / Warunek | Uwagi |
|-------|---------------|-------|
| Odczyt swoich postępów | `owner` | — |
| Rozpoczęcie zdobywania (nowy rocznik/wersja) | `authenticated` | Tworzy nowy rekord `owner`. Gwarantuje Prawa Nabyte. |
| Otwarcie kolejnego cyklu (Pętla prestiżu) | `owner` | Tylko jeśli stary cykl ma status `COMPLETED` / `ALBUM`. |
| Wymuszenie przeliczenia postępu | `owner` | Obliczenia na żywo (Set Math) odczytują tylko własne `AscentLog`. |

---

## Macierz uprawnień: Faza C (Logistyka / Kanban PTTK)

Zasób: `VerificationRequest` (Wniosek Weryfikacyjny)

| Akcja | Rola / Warunek | Stan Przed → Stan Po |
|-------|---------------|----------------------|
| Utworzenie wniosku zbiorczego | `owner` | Tworzy wniosek ze stanem `WAITING_FOR_SEND`. Zabezpieczenie: Odznaki muszą być `COMPLETED`. |
| Zgłoszenie wysłania do PTTK | `owner` | `WAITING_FOR_SEND` → `WAITING_FOR_VERIFICATION`. |
| Wgląd do załączników (Książeczki, Zdjęcia) | `owner` LUB `verifier` | Ochrona RODO. PTTK widzi tylko wnioski do tego Oddziału, dla którego posiada przypisaną rolę weryfikatora. |
| Zatwierdzenie (Weryfikacja PTTK) | `verifier` | `WAITING_FOR_VERIFICATION` → `WAITING_FOR_RECEIVING`. Publikuje Event: *VerificationRequestApproved*. |
| Odrzucenie wniosku (Błąd logów) | `verifier` | `WAITING_FOR_VERIFICATION` → `REJECTED`. Z odblokowaniem `AscentLogs` do edycji dla turysty. |
| Odebranie fizycznej blachy i wpięcie | `owner` | `WAITING_FOR_RECEIVING` → `ALBUM` (Stan terminalny). |

---

## Macierz uprawnień: Faza D [Planowane] (Statystyki i Społeczność)

Zasób: Modele analityczne, Rankingi Szczytów, Tablice Liderów

| Akcja | Rola / Warunek | Uwagi |
|-------|---------------|-------|
| Odczyt rankingów globalnych (np. "Najtrudniejsze szczyty")| `public` | Płaskie widoki CQRS bazujące na anonimizowanych metrykach zbiorczych. |
| Odczyt tablicy Liderów (Top Turyści) | `public` | Tabela ignoruje użytkowników z ustawieniem `is_public = False`. |

---

## Wzorzec implementacji dekoratora uprawnień (API Django)

Ponieważ w Fazie C zbudujemy API, egzekwowanie ról musi być na najwyższym poziomie izolacji, z dala od logiki Domeny.

```python
# Użycie w endpointach API (lub widokach HTMX) z użyciem customowych dekoratorów
from functools import wraps
from application.exceptions import PermissionDeniedError

def require_ownership(model_class):
    """Dekorator sprawdzający, czy zalogowany user jest właścicielem zasobu."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, resource_id, *args, **kwargs):
            if not request.user.is_authenticated:
                raise AuthenticationError("Zaloguj się.")
                
            # Szybki strzał do bazy po ID i Ownera
            is_owner = model_class.objects.filter(id=resource_id, user_id=request.user.id).exists()
            if not is_owner:
                # Nie zdradzaj istnienia (IDOR mitigation):
                # Atakujący nie może skanować bazy po numerach ID sprawdzając które wiersze istnieją.
                raise PermissionDeniedError("Brak uprawnień lub obiekt nie istnieje.")
                
            return view_func(request, resource_id, *args, **kwargs)
        return _wrapped_view
    return decorator


# Przykład widoku modyfikacji logu:
@require_ownership(AscentLog)
def edit_ascent_log_api(request, resource_id):
    # W tym miejscu wiemy już na 100%, że turysta dotyka swojego wpisu.
    # Następnie UseCase sprawdzi, czy wejście nie jest zablokowane cyklem.
    ...
```

### Zasady dla agentów LLM (Defense-in-depth)
1. **Filtruj u źródła:** Zapytania SQL pobierające dane (QuerySets) **MUSZĄ** zawierać klauzulę `.filter(user_id=request.user.id)` tam, gdzie to możliwe, co stanowi drugą linię obrony przed błędem w dekoratorze.
2. **Niemutowalność historii:** Kod aktualizujący/usuwający `AscentLog` zawsze musi przejść przez serwis sprawdzający "Zużycie Wejść" (`UserBadgeProgress`). Log przypięty do wysłanej odznaki traktuj jako `Read-Only` na zawsze.
3. **Nie zdradzaj istnienia:** Próba dostępu do nie swojego rekordu powinna kończyć się komunikatem zrównanym z `404 Not Found` (zamiast `403 Forbidden`), aby zablokować mapowanie identyfikatorów bazy przez atakującego (IDOR mitigation).

---

## Historia zmian

| Wersja | Data | Autor | Opis zmiany |
|--------|------|-------|-------------|
| 1.0 | 2026-05-29 | Dominik / AI Architect | Pierwsza wersja, definiująca dostęp dla Fazy C. |
| 1.1 | 2026-05-29 | AI Architect | Doprecyzowanie relacji M:N dla Weryfikatora. Dodanie polityki "Privacy by Default" do profili użytkowników oraz szkic uprawnień dla planowanej Fazy D (Rankingi). |
