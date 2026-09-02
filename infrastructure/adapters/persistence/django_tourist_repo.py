"""Adapter repozytorium dla obszaru Turysty (B2C).

AUDYT-002: Zespół `DjangoTouristRepository` (implementujący 3 porty) został
rozbity na trzy dedykowane adaptery, każdy realizujący **jeden port**:

- ``DjangoTouristProfileRepository``  → ``TouristProfileRepositoryPort``
- ``DjangoAscentLogRepository``       → ``AscentLogRepositoryPort``
- ``DjangoUserProgressRepository``    → ``UserProgressRepositoryPort``

Stara klasa ``DjangoTouristRepository`` zachowana jest jako **deprecated**
alias łączący wszystkie trzy, by umożliwić stopnią migrację w `container.py`
oraz testach.
"""

from collections import defaultdict
from datetime import date
from typing import TYPE_CHECKING, cast

from django.db.models import Min

from application.dto.ascent_dto import AscentDTO, AscentInputDTO
from application.dto.user_context_dto import BadgeProgressDTO, TouristProfileDTO
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)

if TYPE_CHECKING:
    from apps.tourists.models import UserBadgeProgress


class DjangoTouristProfileRepository(TouristProfileRepositoryPort):
    """Adapter bazy danych dla portu `TouristProfileRepositoryPort`.

    Odpowiedzialny wyłącznie za odczyt profilu turysty (wiek, limity, kluby).
    """

    def get_profile(self, profile_id: int) -> TouristProfileDTO | None:
        """

        Args:
          profile_id: int:
          profile_id: int:

        Returns:

        """
        from apps.tourists.models import TouristProfile

        try:
            profile = TouristProfile.objects.select_related("user").get(id=profile_id)
        except TouristProfile.DoesNotExist:
            return None

        # Rzutowanie kluczy na str, a wartości na date z JSONB bazy
        join_dates = {str(k): date.fromisoformat(str(v)) for k, v in profile.club_join_dates.items()}

        return TouristProfileDTO(
            profile_id=profile.id,
            is_main_profile=profile.is_main_profile,
            email=profile.user.email,
            nickname=profile.nickname,
            birth_date=profile.birth_date,
            club_join_dates=join_dates,
            active_plan=profile.active_plan,
            max_photos_per_ascent=profile.max_photos_per_ascent,
            max_active_badges=profile.max_active_badges,
        )


class DjangoAscentLogRepository(AscentLogRepositoryPort):
    """Adapter bazy danych dla portu `AscentLogRepositoryPort`.

    Odpowiedzialny wyłącznie za dziennik wejść (logowanie, odczyt,
    strumieniowanie i masowe zapisy).
    """

    def get_object_lifespan(self, peak_id: int) -> tuple[date | None, date | None] | None:
        """

        Args:
          peak_id: int:
          peak_id: int:

        Returns:

        """
        from apps.badges.models import TouristObject

        try:
            obj = TouristObject.objects.get(id=peak_id)
        except TouristObject.DoesNotExist:
            return None

        return (obj.existence_start, obj.existence_end)

    def ascent_exists(self, profile_id: int, peak_id: int, ascent_date: date) -> bool:
        """

        Args:
          profile_id: int:
          peak_id: int:
          ascent_date: date:
          profile_id: int:
          peak_id: int:
          ascent_date: date:

        Returns:

        """
        from apps.tourists.models import AscentLog

        qs = AscentLog.objects.filter(profile_id=profile_id, peak_id=peak_id, ascent_date=ascent_date)
        return bool(qs.exists())

    def get_oldest_ascent_date(self, profile_id: int, badge_code: str) -> date | None:
        """

        Args:
          profile_id: int:
          badge_code: str:
          profile_id: int:
          badge_code: str:

        Returns:

        """
        from apps.badges.models import BadgeVersionModel
        from apps.tourists.models import AscentLog

        # Wyciągamy ID szczytów z puli wszystkich historycznych i obecnych wersji tej odznaki
        peak_ids = (
            BadgeVersionModel.objects.filter(badge__code=badge_code).values_list("pool_peaks__id", flat=True).distinct()
        )

        result = AscentLog.objects.filter(profile_id=profile_id, peak_id__in=peak_ids).aggregate(
            oldest=Min("ascent_date")
        )
        return cast(date | None, result["oldest"])

    def save_ascent(self, profile_id: int, peak_id: int, ascent_date: date) -> int:
        """

        Args:
          profile_id: int:
          peak_id: int:
          ascent_date: date:
          profile_id: int:
          peak_id: int:
          ascent_date: date:

        Returns:

        """
        from apps.tourists.models import AscentLog

        # Idempotentny Upsert (Invariant D-04). Jeśli z powodu laga sieciowego
        # API uderzy tu dwa razy, get_or_create nie wyrzuci błędu bazy z UniqueConstraint.
        log, _ = AscentLog.objects.get_or_create(
            profile_id=profile_id,
            peak_id=peak_id,
            ascent_date=ascent_date,
            defaults={},
        )
        return cast(int, log.id)

    def get_unconsumed_ascents(self, profile_id: int, badge_code: str, cutoff_date: date | None) -> list[AscentDTO]:
        """

        Args:
          profile_id: int:
          badge_code: str:
          cutoff_date: date | None:
          profile_id: int:
          badge_code: str:
          cutoff_date: date | None:

        Returns:

        """
        from apps.badges.models import BadgeVersionModel, ObjectRegionCache
        from apps.tourists.models import AscentLog

        # AUDYT-053: Aby nie ładować do RAM-u tysięcy logów, filtrujemy tylko te
        # obiekty, które fizycznie mogą mieć znaczenie dla tej odznaki.
        # values_list(...).distinct() jako __in jest kompilowane do SQL — nie
        # materializuje się w RAM.
        peak_ids = (
            BadgeVersionModel.objects.filter(badge__code=badge_code).values_list("pool_peaks__id", flat=True).distinct()
        )

        # AUDYT-053: tylko potrzebne kolumny — peak_id i ascent_date są
        # kolumnami na AscentLog, nie potrzebujemy select_related ani całych OB.
        qs = AscentLog.objects.filter(profile_id=profile_id, peak_id__in=peak_ids)
        if cutoff_date:
            qs = qs.filter(ascent_date__gt=cutoff_date)

        # Przebieg 1: strumień po ascents, by zebrać unikalne peak_ids (chunk_size=2000)
        fetched_peak_ids: set[int] = set()
        for ascent in qs.only("peak_id").iterator(chunk_size=2000):
            fetched_peak_ids.add(ascent.peak_id)
        if not fetched_peak_ids:
            return []

        # Wstrzykiwanie CQRS (Invariant R-03) — regiony w jednym zapytaniu SQL
        region_map: defaultdict[int, set[int]] = defaultdict(set)
        for rc in (
            ObjectRegionCache.objects.filter(tourist_object_id__in=fetched_peak_ids)
            .values("tourist_object_id", "region_id")
            .iterator(chunk_size=2000)
        ):
            region_map[rc["tourist_object_id"]].add(rc["region_id"])

        # Przebieg 2: strumień po ascents, by skonstruować DTO — nie trzyma
        # tysięcy obiektów AscentLog w RAM naraz.
        ascents: list[AscentDTO] = []
        for ascent in qs.only("peak_id", "ascent_date").iterator(chunk_size=2000):
            ascents.append(
                AscentDTO(
                    peak_id=ascent.peak_id,
                    ascent_date=ascent.ascent_date,
                    region_ids=frozenset(region_map.get(ascent.peak_id, set())),
                )
            )
        return ascents

    def get_objects_lifespans(self, peak_ids: set[int]) -> dict[int, tuple[date | None, date | None]]:
        """Pobiera bitemporalne ramy życia dla wielu obiektów naraz (Optymalizacja N+1).

        Args:
          peak_ids: set[int]:
          peak_ids: set[int]:

        Returns:
        """
        from apps.badges.models import TouristObject

        # Pobieramy tylko niezbędne 3 kolumny
        qs = TouristObject.objects.filter(id__in=peak_ids).values_list("id", "existence_start", "existence_end")
        return {row[0]: (row[1], row[2]) for row in qs}

    def bulk_save_ascents(self, profile_id: int, ascents: list[AscentInputDTO]) -> int:
        """Masowo zapisuje wejścia.

        Ignoruje duplikaty (Idempotentność D-04).
        Args:
          profile_id: int:
          ascents: list[AscentInputDTO]:
          profile_id: int:
          ascents: list[AscentInputDTO]:

        Returns:
        """
        from apps.tourists.models import AscentLog

        new_logs = [
            AscentLog(
                profile_id=profile_id,
                peak_id=dto.peak_id,
                ascent_date=dto.ascent_date,
            )
            for dto in ascents
        ]

        if not new_logs:
            return 0

        # ignore_conflicts=True mówi bazie PostgreSQL:
        # "Jeśli naruszę UniqueConstraint (user, peak, date), zignoruj ten wiersz bez wywalania błędu!"
        created = AscentLog.objects.bulk_create(new_logs, ignore_conflicts=True)
        return len(created)

    def get_all_ascents_for_user(self, profile_id: int) -> list[AscentDTO]:
        """

        Args:
          profile_id: int:
          profile_id: int:

        Returns:

        """
        from apps.badges.models import ObjectRegionCache
        from apps.tourists.models import AscentLog

        # AUDYT-053: streaming iterator zamiast materializacji listy w RAM.
        # peak_id (FK id) i ascent_date są kolumnami na AscentLog — nie potrzebujemy select_related.
        ascent_qs = AscentLog.objects.filter(profile_id=profile_id).only("peak_id", "ascent_date")

        # Przebieg 1: zbieramy unikalne peak_ids strumieniowo (niska pamięć).
        peak_ids: set[int] = set()
        for ascent in ascent_qs.iterator(chunk_size=2000):
            peak_ids.add(ascent.peak_id)

        if not peak_ids:
            return []

        # Doklejanie CQRS zoptymalizowane do jednego zapytania SQL
        region_map: defaultdict[int, set[int]] = defaultdict(set)
        for rc in (
            ObjectRegionCache.objects.filter(
                tourist_object_id__in=peak_ids,
            )
            .values("tourist_object_id", "region_id")
            .iterator(chunk_size=2000)
        ):
            region_map[rc["tourist_object_id"]].add(rc["region_id"])

        # Przebieg 2: strumień z powrotem, by nie trzymać 50k obiektów w RAM.
        ascents: list[AscentDTO] = []
        for ascent in ascent_qs.only("peak_id", "ascent_date").iterator(chunk_size=2000):
            ascents.append(
                AscentDTO(
                    peak_id=ascent.peak_id,
                    ascent_date=ascent.ascent_date,
                    region_ids=frozenset(region_map.get(ascent.peak_id, set())),
                )
            )
        return ascents


class DjangoUserProgressRepository(UserProgressRepositoryPort):
    """Adapter bazy danych dla portu `UserProgressRepositoryPort`.

    Odpowiedzialny wyłącznie za subskrypcje, Prawa Nabyte i Osobisty Kanban
    (tworzenie, aktualizacja i odczyt postępów użytkownika).
    """

    def _to_progress_dto(self, progress_obj: UserBadgeProgress) -> BadgeProgressDTO:
        """Prywatny mapper ORM -> DTO.

        Args:
          progress_obj:

        Returns:
        """
        return BadgeProgressDTO(
            progress_id=progress_obj.id,
            profile_id=progress_obj.profile_id,
            badge_code=progress_obj.badge.code,
            version_id=progress_obj.version_id,
            cycle_number=progress_obj.cycle_number,
            domain_status=progress_obj.domain_status,
            logistic_status=progress_obj.logistic_status,
            logistic_status_date=progress_obj.logistic_status_date,
        )

    def get_active_progresses(self, profile_id: int) -> list[BadgeProgressDTO]:
        """

        Args:
          profile_id: int:
          profile_id: int:

        Returns:

        """
        from apps.tourists.models import UserBadgeProgress

        qs = UserBadgeProgress.objects.filter(profile_id=profile_id).select_related("badge", "version")
        return [self._to_progress_dto(p) for p in qs]

    def get_progress(self, profile_id: int, badge_code: str, cycle_number: int = 1) -> BadgeProgressDTO | None:
        """

        Args:
          profile_id: int:
          badge_code: str:
          cycle_number: int:

        Returns:

        """
        from apps.tourists.models import UserBadgeProgress

        try:
            progress = UserBadgeProgress.objects.select_related("badge", "version").get(
                profile_id=profile_id, badge__code=badge_code, cycle_number=cycle_number
            )
        except UserBadgeProgress.DoesNotExist:
            return None

        return self._to_progress_dto(progress)

    def start_progress(self, profile_id: int, badge_code: str, version_id: int, cycle_number: int = 1) -> int:
        """

        Args:
          profile_id: int:
          badge_code: str:
          version_id: int:
          cycle_number: int:

        Returns:

        """
        from apps.badges.models import BadgeModel
        from apps.tourists.models import UserBadgeProgress

        badge = BadgeModel.objects.get(code=badge_code)

        prog, _ = UserBadgeProgress.objects.get_or_create(
            profile_id=profile_id,
            badge=badge,
            cycle_number=cycle_number,
            defaults={
                "version_id": version_id,
                "domain_status": "NOT_STARTED",
            },
        )
        return cast(int, prog.id)

    def update_domain_status(self, progress_id: int, status: str) -> None:
        """

        Args:
          progress_id: int:
          status: str:
          progress_id: int:
          status: str:

        Returns:

        """
        from apps.tourists.models import UserBadgeProgress

        UserBadgeProgress.objects.filter(id=progress_id).update(domain_status=status)

    def update_logistic_status(self, progress_id: int, logistic_status: str, status_date: date) -> None:
        """

        Args:
          progress_id: int:
          logistic_status: str:
          status_date: date:
          progress_id: int:
          logistic_status: str:
          status_date: date:

        Returns:

        """
        from apps.tourists.models import UserBadgeProgress

        UserBadgeProgress.objects.filter(id=progress_id).update(
            logistic_status=logistic_status, logistic_status_date=status_date
        )

    def get_completed_badge_codes(self, profile_id: int) -> frozenset[str]:
        """

        Args:
          profile_id: int:
          profile_id: int:

        Returns:

        """
        from apps.tourists.models import DomainStatus, UserBadgeProgress

        codes = (
            UserBadgeProgress.objects.filter(profile_id=profile_id, domain_status=DomainStatus.COMPLETED)
            .values_list("badge__code", flat=True)
            .distinct()
        )
        return frozenset(codes)

    def get_progress_by_id(self, profile_id: int, progress_id: int) -> BadgeProgressDTO | None:
        """

        Args:
          profile_id: int:
          progress_id: int:

        Returns:

        """
        from apps.tourists.models import UserBadgeProgress

        try:
            progress = UserBadgeProgress.objects.select_related("badge", "version").get(
                id=progress_id, profile_id=profile_id
            )
        except UserBadgeProgress.DoesNotExist:
            return None

        return self._to_progress_dto(progress)

    def delete_progress(self, profile_id: int, badge_code: str) -> None:
        """

        Args:
          profile_id: int:
          badge_code: str:
          profile_id: int:
          badge_code: str:

        Returns:

        """
        from apps.tourists.models import UserBadgeProgress

        UserBadgeProgress.objects.filter(profile_id=profile_id, badge__code=badge_code).delete()


class DjangoTouristRepository(DjangoTouristProfileRepository, DjangoAscentLogRepository, DjangoUserProgressRepository):
    """**DEPRECATED** — Zunifikowany adapter łączący trzy porty.

    AUDYT-002: Ta klasa została rozbita na trzy dedykowane adaptery. Zachowana
    jedynie dla kompatybilności wstecznej. Użyj odpowiednich podklas bezpośrednio.
    """
