"""Centralny rejestr reguł odznakowych (Wzorzec Registry / Shotgun Surgery fix, AUDYT-019).

Dzięki `@register_rule` dekorowanemu w `infrastructure/factories/badge_rule_factory.py`,
dodanie nowej reguły wymaga tylko:
  (1) Utworzenia klasy w `domain/rules/badgje_rules.py`,
  (2) Dodania dekorowanego buildera w fabryce + definicji JSON Schema.

Fabryka (`BadgeRuleFactory`) oraz panel admina (`RULES_SCHEMA`) budują się dynamicznie
z tego rejestru — eliminacja etapu ręcznego edytowania dictów i schematów.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
BuilderFn = Callable[[dict[str, Any]], Any]
SchemaFn = Callable[[], dict[str, Any]]


class RuleRegistry:
    """Wątko-beżeczny singleton rejestru reguł."""

    _instance: RuleRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> RuleRegistry:
        """Singleton thread-safe instance accessor."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init_internal()
        return cls._instance

    def _init_internal(self) -> None:
        """Initialize internal registry storage."""
        self._builders: dict[str, BuilderFn] = {}
        self._schema_fns: dict[str, SchemaFn] = {}
        self._order: list[str] = []

    @classmethod
    def register(cls, name: str, schema_fn: SchemaFn) -> Callable[[BuilderFn], BuilderFn]:
        """Decorator rejestrujący buildera + funkcję generującą JSON Schema.

        Kolejność rejestracji jest zachowywana (ważne do identycznej kolejności
        `oneOf` w `RULES_SCHEMA` — testy asercyjne zakładają stałą kolejność).
        """

        def decorator(builder: BuilderFn) -> BuilderFn:
            registry = cls()
            if name not in registry._order:
                registry._order.append(name)
            registry._builders[name] = builder
            registry._schema_fns[name] = schema_fn
            return builder

        return decorator

    @classmethod
    def builder(cls, name: str) -> BuilderFn | None:
        """Return builder callable for rule name or None."""
        return cls()._builders.get(name)

    @classmethod
    def available_types(cls) -> list[str]:
        """Return list of registered rule type names."""
        return list(cls()._order)

    @classmethod
    def builders(cls) -> dict[str, BuilderFn]:
        """Return ordered dict of name → builder (backward-compat view)."""
        reg = cls()
        return {name: reg._builders[name] for name in reg._order if name in reg._builders}

    @classmethod
    def build_schema(cls) -> dict[str, Any]:
        """Dynamicznie generuje `RULES_SCHEMA` z rejestru (AUDYT-019 krok 4)."""
        reg = cls()
        one_of: list[dict[str, Any]] = []
        for name in reg._order:
            schema_fn = reg._schema_fns.get(name)
            if schema_fn is not None:
                one_of.append(schema_fn())
        return {
            "type": "list",
            "title": "Reguły Biznesowe Odznaki",
            "items": {"oneOf": one_of},
        }

    @classmethod
    def clear(cls) -> None:
        """Reset (wyłącznie do testów)."""
        reg = cls()
        reg._builders.clear()
        reg._schema_fns.clear()
        reg._order.clear()

    def __init_subclass__(cls, **kwargs: object) -> None:
        """Prevent subclassing — registry is final."""
        raise TypeError("RuleRegistry nie jest przeznaczony do dziedziczenia.")
