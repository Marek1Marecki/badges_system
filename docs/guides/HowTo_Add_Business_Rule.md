# How-To: Dodanie Nowej Reguły Biznesowej PTTK

## Cel

Instrukcja krok-po-kroku (SOP) opisująca, **trzy pliki** które należy zmodyfikować,
aby nowa klasa reguły dziedzicząca po `BadgeRule` stała się pełnoprawnym elementem
systemu weryfikacji odznak.

## Kiedy używać?

- Nowa reguła ma logikę inna niż istniejące (np. "Wymagaj wejścia w nocy", "Minimum 3 kluby")
- Reguła musi być konfigurowana w panelu Admina (JSON schema) i ładowana z bazy (factory)

## Krok 1: Utwórz klasę reguły w Domenie

Plik: `domain/rules/badge_rules.py`

Dodaj nową klasę dziedziczącą po `BadgeRule`. Należy zaimplementować trzy metody:

```python
@dataclass(frozen=True)
class NightAscentRule(BadgeRule):
    """Wymaga przynajmniej N wejść dokonanych po zmroku (godz > 18:00)."""

    min_night_ascents: int = 1

    def check(self, ascents: list[Ascent], context: VerificationContext) -> RuleResult:
        night_count = sum(1 for a in ascents if a.ascent_time and a.ascent_time.hour >= 18)
        return RuleResult(
            passed=night_count >= self.min_night_ascents,
            errors=[]
            if night_count >= self.min_night_ascents
            else [f"Brak wejść w nocy (minimum {self.min_night_ascents})"],
        )
```

## Krok 2: Zarejestruj w Fabryce (Registry Pattern)

Plik: `infrastructure/factories/badge_rule_factory.py`

Dodaj (1) funkcję budującą + (2) wpis do słownika `RULE_BUILDERS`:

```python
def _build_night_ascent_rule(data: dict[str, Any]) -> NightAscentRule:
    return NightAscentRule(min_night_ascents=int(data.get("min_night_ascents", 1)))

# W dict RULE_BUILDERS (klucz musi być unikalny!):
"NightAscentRule": _build_night_ascent_rule,
```

> **Uwaga:** Bez tego kroku reguła nie zostanie zamapowana z bazy danych —
> `build_rule_from_dict` rzuci `ValueError: Nieznany typ reguły`.

## Krok 3: Dodaj schemat JSON dla panelu Admina

Plik: `apps/badges/rules_schema.py`

Dodaj nowy wpis `oneOf` w liście `items`, aby reguła była dostępna w UI django-jsonform:

```python
(
    {
        "type": "dict",
        "title": "Wejścia w nocy",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "NightAscentRule"},
            "min_night_ascents": {"type": "integer", "title": "Minimum wejść nocnych", "default": 1},
        },
    },
)
```

> **Uwaga:** Bez tego kroku reguła nie będzie możliwa do skonfigurowania w panelu
> Admina (ale będzie działała jeśli zostanie wstawiona ręcznie do JSONB w bazie).

## Testowanie

```bash
# Test nowej reguły domenowej
ENV_FILE=.env.test uv run pytest tests/domain/rules/test_badge_rules.py -k NightAscentRule

# Test fabryki
ENV_FILE=.env.test uv run pytest tests/infrastructure/factories/test_badge_rule_factory.py -k NightAscentRule
```

## Podsumowanie: 3 pliki = 1 reguła

| # | Plik | Zmiana |
|---|------|--------|
| 1 | `domain/rules/badge_rules.py` | Klasa reguły (logika Czystej Domeny) |
| 2 | `infrastructure/factories/badge_rule_factory.py` | Rejestracja w `RULE_BUILDERS` |
| 3 | `apps/badges/rules_schema.py` | Schemat JSON dla Admina |

Zignorowanie któregokolwiek kroku spowoduje, że reguła albo:
- (brak Kroku 1) Nie istnieje
- (brak Kroku 2) Nie zostanie sparsowana z bazy → `ValueError`
- (brak Kroku 3) Nie da się jej skonfigurować w panelu Admina
