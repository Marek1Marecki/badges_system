# Glosariusz (Ubiquitous Language)

Unormowany słownik projektowy dla zespołu badges_system.

## Odznaki – rygor nazewniczy (AUDYT-081)

Słowo **"Odznaka"** w projekcie jest homonimem. Aby uniknąć nieporozumień w
komunikacji, używaj następujących terminów:

| Termin          | Znaczenie                                           | Model danych (techniczny)   |
|-----------------|-----------------------------------------------------|------------------------------|
| **Odznaka** (Badge) | Nadrzędny agregat — ogólna koncepcja odznaki (np. "Korona Gór Polski"). | `BadgeModel` |
| **Regulamin** / **Wersja** | Zestaw reguł obowiązujący w określonym czasie (np. "KGP 2024"). | `BadgeVersionModel` |
| **Zdobycie** / **Wyzwanie** | Postęp turysty wobec konkretnej wersji regulaminu. | `UserBadgeProgress` |

### Przykłady poprawnej komunikacji

- ✅ "Wyłączmy **regulamin** odznaki X na sezon 2025." → dezaktywacja `BadgeVersionModel`.
- ❌ "Zablokujmy odznakę X." → niejasne — wyłączamy regulamin (wersję), czy postęp użytkownika?

### Dlaczego to ważne

W kodzie (modelach) poziomy te są idealnie odseparowane. Zagrożenie leży na
poziomie biznesowym: analityk prosząc o "zablokowanie odznaki" może przez całą
rozmowę oznaczać różne rzeczy, co grozi mylącym zadaniem dla programistów.
