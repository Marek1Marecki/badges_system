"""Adapter Repo implementujący BadgeRepositoryPort dla Django ORM."""

import logging
from datetime import date

from application.ports.badge_repository_port import BadgeRepositoryPort
from apps.badges.models import BadgeVersionModel
from domain.entities.badge_version import BadgeTierDomain, BadgeVersionDomain
from domain.rules.badge_rules import BadgeRule
from infrastructure.factories.badge_rule_factory import build_rule_from_dict

logger = logging.getLogger(__name__)


# =====================================================================
# ADAPTER GŁÓWNY
# =====================================================================


class DjangoBadgeRepository(BadgeRepositoryPort):
    """Implementuje komunikację z bazą relacyjną przy użyciu Django ORM."""

    def get_badge_version(self, badge_code: str, version_code: str) -> BadgeVersionDomain | None:
        """

        Args:
          badge_code: str:
          version_code: str:
          badge_code: str:
          version_code: str:

        Returns:

        """
        try:
            version_model = BadgeVersionModel.objects.prefetch_related("pool_peaks").get(
                badge__code=badge_code, version_code=version_code
            )
        except BadgeVersionModel.DoesNotExist:
            return None
        return self._hydrate_version(version_model, badge_code)

    def get_badge_version_by_id(self, version_id: int) -> BadgeVersionDomain | None:
        """

        Args:
          version_id: int:
          version_id: int:

        Returns:

        """
        try:
            version_model = BadgeVersionModel.objects.prefetch_related("pool_peaks").get(id=version_id)
        except BadgeVersionModel.DoesNotExist:
            return None
        return self._hydrate_version(version_model, version_model.badge.code)

    def get_version_id_for_date(self, badge_code: str, target_date: date) -> int | None:
        """

        Args:
          badge_code: str:
          target_date: date:
          badge_code: str:
          target_date: date:

        Returns:

        """
        version = (
            BadgeVersionModel.objects.filter(
                badge__code=badge_code,
                valid_from__lte=target_date,
            )
            .order_by("-valid_from")
            .first()
        )

        return version.id if version else None

    def _hydrate_version(self, version_model: BadgeVersionModel, badge_code: str) -> BadgeVersionDomain:
        """Prywatna metoda tłumacząca ORM na obiekt domenowy.

        Args:
          version_model: BadgeVersionModel:
          badge_code: str:
          version_model: BadgeVersionModel:
          badge_code: str:

        Returns:

        """
        pool_peaks = {peak.id for peak in version_model.pool_peaks.all()}
        domain_rules: list[BadgeRule] = []

        for rule_dict in version_model.rules:
            try:
                domain_rules.append(build_rule_from_dict(rule_dict))
            except (ValueError, TypeError) as e:
                rule_type = rule_dict.get("type", "<brak>") if isinstance(rule_dict, dict) else type(rule_dict).__name__
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

    def get_latest_badge_version(self, badge_code: str) -> BadgeVersionDomain | None:
        """

        Args:
          badge_code: str:
          badge_code: str:

        Returns:

        """
        from django.utils import timezone

        from apps.badges.models import BadgeVersionModel

        version_model = (
            BadgeVersionModel.objects.filter(badge__code=badge_code, valid_from__lte=timezone.now().date())
            .order_by("-valid_from")
            .first()
        )

        return self._hydrate_version(version_model, badge_code) if version_model else None
