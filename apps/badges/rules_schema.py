"""Schemat JSON dla panelu definiowania reguł odznak (django-jsonform).

Dynamicznie generowany z `domain.rules.registry.RuleRegistry` (AUDYT-019).
Dodanie nowej reguły wymaga jedynie @register_rule w `domain/rules/builders.py`
— schemat odświeży się automatycznie.

BUILDERS side-effect: import `domain.rules.builders` rejestruje wszystkie
@register_rule jako side-effect — dzięki czemu `RuleRegistry.build_schema()`
zawsze zobaczy pełną listę typów reguł, niezależnie od kolejności importów.
"""

from __future__ import annotations

import domain.rules.builders  # noqa: F401 — side-effect: populates RuleRegistry
from domain.rules.registry import RuleRegistry


def get_rules_schema() -> dict[str, object]:
    """Eager build `RULES_SCHEMA` z rejestru w momencie wywołania."""
    return RuleRegistry.build_schema()


RULES_SCHEMA: dict[str, object] = get_rules_schema()
