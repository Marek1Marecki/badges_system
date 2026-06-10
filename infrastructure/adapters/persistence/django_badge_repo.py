"""Adapter Repo implementujący BadgeRepositoryPort dla Django ORM."""

import logging
from collections.abc import Callable
from datetime import date
from typing import Any

from application.ports.badge_repository_port import BadgeRepositoryPort
from apps.badges.models import BadgeVersionModel
from domain.entities.badge_version import BadgeTierDomain, BadgeVersionDomain
from domain.rules.badge_rules import (
    BadgeRule,
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

logger = logging.getLogger(__name__)


# =====================================================================
# FABRYKI REGUŁ (Hydracja z formatu JSON)
# =====================================================================


def _build_time_limit_rule(data: dict[str, Any]) -> TimeLimitRule:
    limit = data.get("limit_in_years")
    if limit is None:
        raise ValueError("TimeLimitRule wymaga parametru 'limit_in_years'.")
    return TimeLimitRule(limit_in_years=int(limit))


def _build_club_join_rule(data: dict[str, Any]) -> RequiresClubJoinDateRule:
    return RequiresClubJoinDateRule()


def _build_min_age_rule(data: dict[str, Any]) -> MinAgeRule:
    age = data.get("min_age")
    if age is None:
        raise ValueError("MinAgeRule wymaga parametru 'min_age'.")
    return MinAgeRule(min_age=int(age))


def _build_max_age_rule(data: dict[str, Any]) -> MaxAgeRule:
    age = data.get("max_age")
    if age is None:
        raise ValueError("MaxAgeRule wymaga parametru 'max_age'.")
    return MaxAgeRule(max_age=int(age))


def _build_start_date_rule(data: dict[str, Any]) -> StartDateRule:
    date_str = data.get("start_date")
    if not date_str:
        raise ValueError("StartDateRule wymaga parametru 'start_date'.")
    try:
        parsed_date = date.fromisoformat(date_str)
        return StartDateRule(start_date=parsed_date)
    except ValueError as e:
        raise ValueError(f"Nieprawidłowy format daty w StartDateRule: {date_str}") from e


def _build_date_window_rule(data: dict[str, Any]) -> DateWindowRule:
    start_str = data.get("start_date")
    end_str = data.get("end_date")
    if not start_str or not end_str:
        raise ValueError("DateWindowRule wymaga 'start_date' i 'end_date'.")
    try:
        return DateWindowRule(start_date=date.fromisoformat(start_str), end_date=date.fromisoformat(end_str))
    except ValueError as e:
        raise ValueError("Nieprawidłowy format daty w DateWindowRule.") from e


def _build_mandatory_objects_rule(data: dict[str, Any]) -> MandatoryObjectsRule:
    raw_ids = data.get("mandatory_peak_ids")
    if not raw_ids:
        raise ValueError("MandatoryObjectsRule wymaga listy 'mandatory_peak_ids'.")
    mandatory_ids = frozenset(int(pid) for pid in raw_ids)
    return MandatoryObjectsRule(mandatory_peak_ids=mandatory_ids)


def _build_grouped_alternatives_rule(data: dict[str, Any]) -> GroupedAlternativesRule:
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


def _build_multi_pool_rule(data: dict[str, Any]) -> MultiPoolRequirementRule:
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


def _build_prerequisite_badge_rule(data: dict[str, Any]) -> PrerequisiteBadgeRule:
    code = data.get("required_badge_code")
    if not code:
        raise ValueError("PrerequisiteBadgeRule wymaga parametru 'required_badge_code'.")
    return PrerequisiteBadgeRule(required_badge_code=str(code).strip())


def _build_region_count_rule(data: dict[str, Any]) -> RegionCountRule:
    region_id = data.get("region_id")
    req_count = data.get("required_count")
    if region_id is None or req_count is None:
        raise ValueError("RegionCountRule wymaga 'region_id' oraz 'required_count'.")
    return RegionCountRule(region_id=int(region_id), required_count=int(req_count))


RULE_BUILDERS: dict[str, Callable[[dict[str, Any]], BadgeRule]] = {
    "TimeLimitRule": _build_time_limit_rule,
    "RequiresClubJoinDateRule": _build_club_join_rule,
    "MinAgeRule": _build_min_age_rule,
    "MaxAgeRule": _build_max_age_rule,
    "StartDateRule": _build_start_date_rule,
    "DateWindowRule": _build_date_window_rule,
    "MandatoryObjectsRule": _build_mandatory_objects_rule,
    "GroupedAlternativesRule": _build_grouped_alternatives_rule,
    "MultiPoolRequirementRule": _build_multi_pool_rule,
    "PrerequisiteBadgeRule": _build_prerequisite_badge_rule,
    "RegionCountRule": _build_region_count_rule,
}


# =====================================================================
# ADAPTER GŁÓWNY
# =====================================================================


class DjangoBadgeRepository(BadgeRepositoryPort):
    """Implementuje komunikację z bazą relacyjną przy użyciu Django ORM."""

    def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
        try:
            version_model = BadgeVersionModel.objects.prefetch_related("pool_peaks").get(
                badge__code=badge_code, version_code=version_code
            )
        except BadgeVersionModel.DoesNotExist:
            return None
        return self._hydrate_version(version_model, badge_code)

    def get_badge_version_by_id(self, version_id: int) -> BadgeVersionDomain | None:
        try:
            version_model = BadgeVersionModel.objects.prefetch_related("pool_peaks").get(id=version_id)
        except BadgeVersionModel.DoesNotExist:
            return None
        return self._hydrate_version(version_model, version_model.badge.code)

    def get_version_id_for_date(self, badge_code: str, target_date: date) -> int | None:
        from apps.badges.models import BadgeVersionModel

        version = (
            BadgeVersionModel.objects.filter(badge__code=badge_code, valid_from__lte=target_date)
            .order_by("-valid_from")
            .first()
        )
        return version.id if version else None

    def _hydrate_version(self, version_model: BadgeVersionModel, badge_code: str) -> BadgeVersionDomain:
        """Prywatna metoda tłumacząca ORM na obiekt domenowy."""
        pool_peaks = {peak.id for peak in version_model.pool_peaks.all()}
        domain_rules: list[BadgeRule] = []

        for rule_dict in version_model.rules:
            data = dict(rule_dict)
            rule_type = data.pop("type", None)

            if rule_type is None:
                raise ValueError(
                    f"Reguła bez pola 'type' w wersji '{badge_code}/{version_model.version_code}': {rule_dict}"
                )

            builder = RULE_BUILDERS.get(rule_type)
            if builder is None:
                raise ValueError(
                    f"Nieznany typ reguły '{rule_type}' dla wersji '{badge_code}/{version_model.version_code}'."
                )

            try:
                domain_rules.append(builder(data))
            except ValueError as e:
                raise ValueError(
                    f"Błąd hydracji reguły '{rule_type}' dla wersji '{badge_code}/{version_model.version_code}': {e}"
                ) from e

        # ZMIANA (TD-03 Zamknięte): Pobieramy Stopnie z bazy danych!
        from apps.badges.models import BadgeTierModel

        tier_models = BadgeTierModel.objects.filter(version=version_model).order_by("order")

        domain_tiers = []
        for tm in tier_models:
            # Implementacja logiki "Puste znaczy wszystkie z puli"
            req_count = tm.required_peaks_count if tm.required_peaks_count is not None else len(pool_peaks)
            domain_tiers.append(
                BadgeTierDomain(tier_id=tm.id, name=str(tm.name), required_count=req_count, order=tm.order)
            )

        return BadgeVersionDomain(
            version_id=version_model.id,
            rules=domain_rules,
            pool_peak_ids=frozenset(pool_peaks),
            tiers=domain_tiers,  # <--- Zamiast pojedynczego required_count
        )
