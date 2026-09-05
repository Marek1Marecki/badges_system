"""Thin adapter facade for `BadgeRule` construction (AUDYT-019 registry layer).

Builder logic itself lives in `domain/rules/builders.py` (czysta domena) —
rejestrowane są dekoratorami `@RuleRegistry.register`. Ta warstwa
zapewnia kompatybilność wsteczną dla istniejących importów:
`build_rule_from_dict` oraz `RULE_BUILDERS`.

AUDYT-019: Shotgun Surgery eliminated — adding a new rule requires changes
in exactly ONE place (`domain/rules/builders.py`); schema + factory update
automatycznie.
"""

from collections.abc import Callable
from typing import Any

import domain.rules.builders  # noqa: F401 — side-effect: populates RuleRegistry
from domain.rules.badge_rules import BadgeRule
from domain.rules.registry import RuleRegistry

RULE_BUILDERS: dict[str, Callable[[dict[str, Any]], BadgeRule]] = RuleRegistry.builders()


def build_rule_from_dict(data: dict[str, Any]) -> BadgeRule:
    """Buduje pojedynczą regułę domenową z jednego rekordu JSONB.

    Publiczny interfejs fabryki dla warstwy aplikacji / adapterów.
    Rzuca ValueError gdy typ reguły jest nieznany lub parametry są niepoprawne.

    Args:
        data: dict[str, Any]: Rekord JSONB opisujący regułę (musi zawierać 'type').

    Returns:
        BadgeRule: Hydratowany obiekt reguły domenowej.
    """
    if not isinstance(data, dict):
        raise TypeError(f"Błąd hydracji reguły: oczekiwano dict, otrzymano {type(data).__name__}.")

    data = dict(data)
    rule_type = data.pop("type", None)

    if rule_type is None:
        raise ValueError(f"Reguła bez pola 'type': {data}")

    builder = RuleRegistry.builder(rule_type)
    if builder is None:
        raise ValueError(f"Nieznany typ reguły '{rule_type}'. Dostępne: {sorted(RuleRegistry.available_types())}")

    try:
        result: BadgeRule = builder(data)
        return result
    except ValueError as e:
        raise ValueError(f"Błąd budowy reguły typu '{rule_type}' z danych {data}: {e}") from e
