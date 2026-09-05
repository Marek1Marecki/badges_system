"""Concrete `BadgeRule` builders + JSON Schema definitions (AUDYT-019).

Centralized **domain** registry (no infrastructure imports) — eliminuje
Shotgun Surgery: nowa reguła = @register_rule + builder + schema_fn w
jednym miejscu. `infrastructure/factories/badge_rule_factory.py` jest jedynie
cienką fasadą (`build_rule_from_dict`, `RULE_BUILDERS` view) na ten registry.

Każdy builder jest dekorowany `@RuleRegistry.register(name, schema_fn)`,
gdzie `schema_fn` generuje JSON Schema dla panelu django-jsonform.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from domain.rules.badge_rules import (
    DateWindowRule,
    GroupedAlternativesRule,
    MandatoryObjectsRule,
    MaxAgeRule,
    MinAgeRule,
    MultiPoolRequirementRule,
    PrerequisiteBadgeRule,
    RegionCountRule,
    RequiresClubJoinDateRule,
    StartDateRule,
    SubPoolRequirement,
    TimeLimitRule,
)
from domain.rules.registry import RuleRegistry


@RuleRegistry.register(
    "TimeLimitRule",
    lambda: {
        "type": "dict",
        "title": "Limit Czasowy",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "TimeLimitRule"},
            "limit_in_years": {"type": "integer", "title": "Limit (w latach)"},
        },
    },
)
def build_time_limit_rule(data: dict[str, Any]) -> TimeLimitRule:
    """Buduje regułę limitu czasowego."""
    limit = data.get("limit_in_years")
    if limit is None:
        raise ValueError("TimeLimitRule wymaga parametru 'limit_in_years'.")
    return TimeLimitRule(limit_in_years=int(limit))


@RuleRegistry.register(
    "RequiresClubJoinDateRule",
    lambda: {
        "type": "dict",
        "title": "Wymaga zapisu do Klubu",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "RequiresClubJoinDateRule"},
        },
    },
)
def build_club_join_rule(data: dict[str, Any]) -> RequiresClubJoinDateRule:
    """Buduje regułę wymogu zapisu do klubu."""
    return RequiresClubJoinDateRule()


@RuleRegistry.register(
    "MinAgeRule",
    lambda: {
        "type": "dict",
        "title": "Minimalny Wiek",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "MinAgeRule"},
            "min_age": {"type": "integer", "title": "Minimalny wiek (lata)"},
        },
    },
)
def build_min_age_rule(data: dict[str, Any]) -> MinAgeRule:
    """Buduje regułę minimalnego wieku."""
    age = data.get("min_age")
    if age is None:
        raise ValueError("MinAgeRule wymaga parametru 'min_age'.")
    return MinAgeRule(min_age=int(age))


@RuleRegistry.register(
    "MaxAgeRule",
    lambda: {
        "type": "dict",
        "title": "Maksymalny Wiek (dla dzieci/młodzieży)",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "MaxAgeRule"},
            "max_age": {"type": "integer", "title": "Maksymalny wiek (lata)"},
        },
    },
)
def build_max_age_rule(data: dict[str, Any]) -> MaxAgeRule:
    """Buduje regułę maksymalnego wieku."""
    age = data.get("max_age")
    if age is None:
        raise ValueError("MaxAgeRule wymaga parametru 'max_age'.")
    return MaxAgeRule(max_age=int(age))


@RuleRegistry.register(
    "StartDateRule",
    lambda: {
        "type": "dict",
        "title": "Szczyty zaliczane od daty",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "StartDateRule"},
            "start_date": {"type": "string", "format": "date", "title": "Data graniczba (YYYY-MM-DD)"},
        },
    },
)
def build_start_date_rule(data: dict[str, Any]) -> StartDateRule:
    """Buduje regułę daty startowej."""
    date_str = data.get("start_date")
    if not date_str:
        raise ValueError("StartDateRule wymaga parametru 'start_date'.")
    try:
        parsed_date = date.fromisoformat(date_str)
        return StartDateRule(start_date=parsed_date)
    except ValueError as e:
        raise ValueError(f"Nieprawidłowy format daty w StartDateRule: {date_str}") from e


@RuleRegistry.register(
    "DateWindowRule",
    lambda: {
        "type": "dict",
        "title": "Zamknięte Okno Czasowe (np. Jubileusz)",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "DateWindowRule"},
            "start_date": {"type": "string", "format": "date", "title": "Data początkowa (YYYY-MM-DD)"},
            "end_date": {"type": "string", "format": "date", "title": "Data końcowa (YYYY-MM-DD)"},
        },
    },
)
def build_date_window_rule(data: dict[str, Any]) -> DateWindowRule:
    """Buduje regułę zamkniętego okna czasowego."""
    start_str = data.get("start_date")
    end_str = data.get("end_date")
    if not start_str or not end_str:
        raise ValueError("DateWindowRule wymaga 'start_date' i 'end_date'.")
    try:
        return DateWindowRule(start_date=date.fromisoformat(start_str), end_date=date.fromisoformat(end_str))
    except ValueError as e:
        raise ValueError("Nieprawidłowy format daty w DateWindowRule.") from e


@RuleRegistry.register(
    "MandatoryObjectsRule",
    lambda: {
        "type": "dict",
        "title": "Obowiązkowe konkretne obiekty",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "MandatoryObjectsRule"},
            "mandatory_peak_ids": {
                "type": "array",
                "title": "Wpisz numery ID obiektów",
                "items": {"type": "integer"},
            },
        },
    },
)
def build_mandatory_objects_rule(data: dict[str, Any]) -> MandatoryObjectsRule:
    """Buduje regułę obowiązkowych obiektów."""
    raw_ids = data.get("mandatory_peak_ids")
    if not raw_ids:
        raise ValueError("MandatoryObjectsRule wymaga listy 'mandatory_peak_ids'.")
    mandatory_ids = frozenset(int(pid) for pid in raw_ids)
    return MandatoryObjectsRule(mandatory_peak_ids=mandatory_ids)


@RuleRegistry.register(
    "GroupedAlternativesRule",
    lambda: {
        "type": "dict",
        "title": "Wymagane obiekty z RÓŻNYCH grup (Wiaderek)",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "GroupedAlternativesRule"},
            "min_groups_required": {"type": "integer", "title": "Ile różnych grup musi zaliczyć?"},
            "groups": {
                "type": "array",
                "title": "Definicje Grup (Pasm)",
                "items": {
                    "type": "dict",
                    "keys": {
                        "group_name": {"type": "string", "title": "Nazwa grupy", "required": False},
                        "peak_ids": {"type": "array", "title": "ID obiektów", "items": {"type": "integer"}},
                    },
                },
            },
        },
    },
)
def build_grouped_alternatives_rule(data: dict[str, Any]) -> GroupedAlternativesRule:
    """Buduje regułę grup alternatywnych."""
    min_req = data.get("min_groups_required")
    raw_groups_list = data.get("groups")

    if min_req is None or not raw_groups_list:
        raise ValueError("GroupedAlternativesRule wymaga 'min_groups_required' oraz 'groups'.")

    domain_groups: list[frozenset[int]] = []
    for group_dict in raw_groups_list:
        peak_ids = group_dict.get("peak_ids")
        if peak_ids:
            domain_groups.append(frozenset(int(pid) for pid in peak_ids))

    if not domain_groups:
        raise ValueError("GroupedAlternativesRule nie ma żadnych poprawnych grup szczytów.")

    return GroupedAlternativesRule(
        groups=tuple(domain_groups),
        min_groups_required=int(min_req),
    )


@RuleRegistry.register(
    "MultiPoolRequirementRule",
    lambda: {
        "type": "dict",
        "title": "Wymagane ilości z RÓŻNYCH podzbiorów",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "MultiPoolRequirementRule"},
            "pools": {
                "type": "array",
                "title": "Podzbiory (Sub-pule)",
                "items": {
                    "type": "dict",
                    "keys": {
                        "name": {
                            "type": "string",
                            "title": "Nazwa grupy dla wygody (np. Tatry)",
                            "required": False,
                        },
                        "required_count": {"type": "integer", "title": "Wymagana liczba z tej grupy"},
                        "peak_ids": {
                            "type": "string",
                            "title": "ID obiektów (po przecinku, np: 12, 45, 102)",
                        },
                    },
                },
            },
        },
    },
)
def build_multi_pool_rule(data: dict[str, Any]) -> MultiPoolRequirementRule:
    """Buduje regułę wielopuli."""
    raw_pools = data.get("pools")
    if not raw_pools:
        raise ValueError("MultiPoolRequirementRule wymaga listy 'pools'.")

    domain_pools = []
    for pool_data in raw_pools:
        req_count = pool_data.get("required_count")
        raw_ids_str = pool_data.get("peak_ids")
        if req_count is None or not raw_ids_str:
            raise ValueError("Każdy podzbiór musi mieć 'required_count' i 'peak_ids'.")
        try:
            parsed_ids = frozenset(int(pid.strip()) for pid in str(raw_ids_str).split(",") if pid.strip())
        except ValueError as e:
            raise ValueError(f"Błąd parsowania ID obiektów: {raw_ids_str}") from e

        domain_pools.append(
            SubPoolRequirement(required_count=int(req_count), peak_ids=parsed_ids, name=str(pool_data.get("name", "")))
        )

    return MultiPoolRequirementRule(pools=tuple(domain_pools))


@RuleRegistry.register(
    "PrerequisiteBadgeRule",
    lambda: {
        "type": "dict",
        "title": "Wymaga posiadania innej odznaki",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "PrerequisiteBadgeRule"},
            "required_badge_code": {
                "type": "string",
                "title": "Kod wymaganej odznaki (np. KSP)",
                "help_text": "Wpisz kod odznaki, która jest warunkiem wstępnym.",
            },
        },
    },
)
def build_prerequisite_badge_rule(data: dict[str, Any]) -> PrerequisiteBadgeRule:
    """Buduje regułę wymagającą innej odznaki."""
    code = data.get("required_badge_code")
    if not code:
        raise ValueError("PrerequisiteBadgeRule wymaga parametru 'required_badge_code'.")
    return PrerequisiteBadgeRule(required_badge_code=str(code).strip())


@RuleRegistry.register(
    "RegionCountRule",
    lambda: {
        "type": "dict",
        "title": "RegionCountRule",
        "keys": {
            "type": {"type": "string", "widget": "hidden", "default": "RegionCountRule"},
            "region_id": {"type": "integer", "title": "ID regionu"},
            "required_count": {"type": "integer", "title": "Wymagana liczba szczytów"},
        },
    },
)
def build_region_count_rule(data: dict[str, Any]) -> RegionCountRule:
    """Buduje regułę liczby regionów."""
    region_id = data.get("region_id")
    req_count = data.get("required_count")
    if region_id is None or req_count is None:
        raise ValueError("RegionCountRule wymaga 'region_id' oraz 'required_count'.")
    return RegionCountRule(region_id=int(region_id), required_count=int(req_count))
