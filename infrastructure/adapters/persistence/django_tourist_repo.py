"""Adapter repozytorium dla obszaru Turysty (B2C).

Implementuje porty z application/ports/user_progress_port.py przy użyciu Django ORM.
Zgodnie z 22-ports-adapters-dto-contract.md, izoluje Use Case'y od bazy danych,
zwracając i przyjmując wyłącznie DTO oraz proste typy Pythona.
"""

from collections import defaultdict
from datetime import date
from typing import cast

from django.db.models import Min

from application.dto.ascent_dto import AscentDTO
from application.dto.user_context_dto import BadgeProgressDTO, TouristProfileDTO
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)


class DjangoTouristRepository(
    TouristProfileRepositoryPort,
    AscentLogRepositoryPort,
    UserProgressRepositoryPort,
):
    """Zunifikowany adapter bazy danych dla operacji związanych z Turystą."""

    # =====================================================================
    # TouristProfileRepositoryPort
    # =====================================================================

    def get_profile(self, user_id: int) -> TouristProfileDTO | None:
        from apps.tourists.models import TouristProfile

        try:
            profile = TouristProfile.objects.select_related("user").get(user_id=user_id)
        except TouristProfile.DoesNotExist:
            return None

        # Rzutowanie kluczy na str, a wartości na date z JSONB bazy
        join_dates = {str(k): date.fromisoformat(str(v)) for k, v in profile.club_join_dates.items()}

        return TouristProfileDTO(
            user_id=profile.user.id,
            email=profile.user.email,
            nickname=profile.nickname,
            birth_date=profile.birth_date,
            club_join_dates=join_dates,
            active_plan=profile.active_plan,
            max_photos_per_ascent=profile.max_photos_per_ascent,
            max_active_badges=profile.max_active_badges,
        )

    # =====================================================================
    # AscentLogRepositoryPort
    # =====================================================================

    def get_object_lifespan(self, peak_id: int) -> tuple[date | None, date | None] | None:
        from apps.badges.models import TouristObject

        try:
            obj = TouristObject.objects.get(id=peak_id)
        except TouristObject.DoesNotExist:
            return None

        return (obj.existence_start, obj.existence_end)

    def ascent_exists(self, user_id: int, peak_id: int, ascent_date: date) -> bool:
        from apps.tourists.models import AscentLog

        qs = AscentLog.objects.filter(user_id=user_id, peak_id=peak_id, ascent_date=ascent_date)
        return bool(qs.exists())

    def get_oldest_ascent_date(self, user_id: int, badge_code: str) -> date | None:
        from apps.badges.models import BadgeVersionModel
        from apps.tourists.models import AscentLog

        # Wyciągamy ID szczytów z puli wszystkich historycznych i obecnych wersji tej odznaki
        peak_ids = (
            BadgeVersionModel.objects.filter(badge__code=badge_code).values_list("pool_peaks__id", flat=True).distinct()
        )

        result = AscentLog.objects.filter(user_id=user_id, peak_id__in=peak_ids).aggregate(oldest=Min("ascent_date"))
        return cast(date | None, result["oldest"])

    def save_ascent(self, user_id: int, peak_id: int, ascent_date: date) -> int:
        from apps.tourists.models import AscentLog

        # Idempotentny Upsert (Invariant D-04). Jeśli z powodu laga sieciowego
        # API uderzy tu dwa razy, get_or_create nie wyrzuci błędu bazy z UniqueConstraint.
        log, _ = AscentLog.objects.get_or_create(
            user_id=user_id,
            peak_id=peak_id,
            ascent_date=ascent_date,
            defaults={},
        )
        return cast(int, log.id)

    def get_unconsumed_ascents(self, user_id: int, badge_code: str, cutoff_date: date | None) -> list[AscentDTO]:
        from apps.badges.models import BadgeVersionModel, ObjectRegionCache
        from apps.tourists.models import AscentLog

        # Aby nie ładować do RAM-u tysięcy logów, filtrujemy tylko te obiekty,
        # które fizycznie mogą mieć znaczenie dla tej odznaki.
        peak_ids = (
            BadgeVersionModel.objects.filter(badge__code=badge_code).values_list("pool_peaks__id", flat=True).distinct()
        )

        qs = AscentLog.objects.filter(user_id=user_id, peak_id__in=peak_ids)

        # Odrzucamy logi "zużyte" (Starsze lub równe dacie zamknięcia poprzedniego cyklu)
        if cutoff_date:
            qs = qs.filter(ascent_date__gt=cutoff_date)

        ascents = list(qs)
        if not ascents:
            return []

        # Wstrzykiwanie CQRS (Invariant R-03) — wyciągamy regiony jednym zapytaniem SQL
        fetched_peak_ids = {a.peak_id for a in ascents}
        region_caches = ObjectRegionCache.objects.filter(tourist_object_id__in=fetched_peak_ids).values(
            "tourist_object_id", "region_id"
        )

        region_map = defaultdict(set)
        for rc in region_caches:
            region_map[rc["tourist_object_id"]].add(rc["region_id"])

        return [
            AscentDTO(
                peak_id=a.peak_id,
                ascent_date=a.ascent_date,
                region_ids=frozenset(region_map.get(a.peak_id, set())),
            )
            for a in ascents
        ]

    # =====================================================================
    # UserProgressRepositoryPort
    # =====================================================================

    def _to_progress_dto(self, progress_obj) -> BadgeProgressDTO:
        """Prywatny mapper ORM -> DTO."""
        return BadgeProgressDTO(
            progress_id=progress_obj.id,
            user_id=progress_obj.user_id,
            badge_code=progress_obj.badge.code,
            version_id=progress_obj.version_id,
            cycle_number=progress_obj.cycle_number,
            domain_status=progress_obj.domain_status,
            logistic_status=progress_obj.logistic_status,
            logistic_status_date=progress_obj.logistic_status_date,
        )

    def get_active_progresses(self, user_id: int) -> list[BadgeProgressDTO]:
        from apps.tourists.models import UserBadgeProgress

        qs = UserBadgeProgress.objects.filter(user_id=user_id).select_related("badge", "version")
        return [self._to_progress_dto(p) for p in qs]

    def get_progress(self, user_id: int, badge_code: str, cycle_number: int = 1) -> BadgeProgressDTO | None:
        from apps.tourists.models import UserBadgeProgress

        try:
            prog = UserBadgeProgress.objects.select_related("badge", "version").get(
                user_id=user_id, badge__code=badge_code, cycle_number=cycle_number
            )
            return self._to_progress_dto(prog)
        except UserBadgeProgress.DoesNotExist:
            return None

    def start_progress(self, user_id: int, badge_code: str, version_id: int, cycle_number: int = 1) -> int:
        from apps.badges.models import BadgeModel
        from apps.tourists.models import UserBadgeProgress

        badge = BadgeModel.objects.get(code=badge_code)

        prog, _ = UserBadgeProgress.objects.get_or_create(
            user_id=user_id,
            badge=badge,
            cycle_number=cycle_number,
            defaults={
                "version_id": version_id,
                "domain_status": "NOT_STARTED",
            },
        )
        return cast(int, prog.id)

    def update_domain_status(self, progress_id: int, status: str) -> None:
        from apps.tourists.models import UserBadgeProgress

        UserBadgeProgress.objects.filter(id=progress_id).update(domain_status=status)

    def update_logistic_status(self, progress_id: int, logistic_status: str, status_date: date) -> None:
        from apps.tourists.models import UserBadgeProgress

        UserBadgeProgress.objects.filter(id=progress_id).update(
            logistic_status=logistic_status, logistic_status_date=status_date
        )

    def get_completed_badge_codes(self, user_id: int) -> frozenset[str]:
        from apps.tourists.models import DomainStatus, UserBadgeProgress

        codes = (
            UserBadgeProgress.objects.filter(user_id=user_id, domain_status=DomainStatus.COMPLETED)
            .values_list("badge__code", flat=True)
            .distinct()
        )
        return frozenset(codes)

    def get_progress_by_id(self, user_id: int, progress_id: int) -> BadgeProgressDTO | None:
        from apps.tourists.models import UserBadgeProgress

        try:
            prog = UserBadgeProgress.objects.select_related("badge", "version").get(id=progress_id, user_id=user_id)
            return self._to_progress_dto(prog)
        except UserBadgeProgress.DoesNotExist:
            return None

    def get_all_ascents_for_user(self, user_id: int) -> list[AscentDTO]:
        from apps.badges.models import ObjectRegionCache
        from apps.tourists.models import AscentLog

        ascents = list(AscentLog.objects.filter(user_id=user_id))
        if not ascents:
            return []

        # Doklejanie CQRS zoptymalizowane do jednego zapytania
        peak_ids = {a.peak_id for a in ascents}
        region_caches = ObjectRegionCache.objects.filter(tourist_object_id__in=peak_ids).values(
            "tourist_object_id", "region_id"
        )

        from collections import defaultdict

        region_map = defaultdict(set)
        for rc in region_caches:
            region_map[rc["tourist_object_id"]].add(rc["region_id"])

        return [
            AscentDTO(
                peak_id=a.peak_id,
                ascent_date=a.ascent_date,
                region_ids=frozenset(region_map.get(a.peak_id, set())),
            )
            for a in ascents
        ]
