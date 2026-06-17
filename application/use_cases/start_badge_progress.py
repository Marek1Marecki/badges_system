"""Przypadek użycia: Rozpoczęcie zdobywania odznaki (Subskrypcja).

Zgodnie z US-C05 (Prawa Nabyte) oraz Invariantem P-01:
System automatycznie wyszukuje najstarszy log wejścia turysty dla danej odznaki.
Jeśli turysta wchodził na szczyty np. w 2018 roku, zostaje "zakotwiczony"
w regulaminie z 2018 roku, niezależnie od tego, że dzisiaj mamy nowszą wersję.
"""

from datetime import date

from application.exceptions import UseCaseError
from application.ports.badge_repository_port import BadgeRepositoryPort
from application.ports.clock_port import ClockPort
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)


class StartBadgeProgressUseCase:
    """Zakotwicza turystę w odpowiedniej wersji regulaminu odznaki."""

    def __init__(
        self,
        progress_repository: UserProgressRepositoryPort,
        ascent_repository: AscentLogRepositoryPort,
        profile_repository: TouristProfileRepositoryPort,
        badge_repository: BadgeRepositoryPort,
        clock: ClockPort,
    ) -> None:
        """Wstrzykuje repozytoria postępu, wejść, regulaminów oraz zegar systemowy."""
        self._progress_repo = progress_repository
        self._ascent_repo = ascent_repository
        self._profile_repo = profile_repository
        self._badge_repo = badge_repository
        self._clock = clock

    def execute(self, profile_id: int, badge_code: str, cycle_number: int = 1) -> int:
        """Rozpoczyna śledzenie postępu odznaki.

        Raises:
            UseCaseError: Jeśli dla wyliczonej daty nie istnieje żaden regulamin.
        """
        # 0. Weryfikacja limitów Freemium (US-C01c)
        profile = self._profile_repo.get_profile(profile_id)
        if profile:
            active_badges_count = len(
                [
                    p
                    for p in self._progress_repo.get_active_progresses(profile_id)
                    if p.domain_status in ("NOT_STARTED", "IN_PROGRESS")
                ]
            )
            if active_badges_count >= profile.max_active_badges:
                raise UseCaseError(
                    f"Osiągnąłeś limit jednocześnie zdobywanych odznak ({profile.max_active_badges}). "
                    f"Ukończ aktywną odznakę lub przejdź na wyższy plan subskrypcji."
                )

        # 1. Krok: Ustalenie daty "zakotwiczenia" (Grandfathering Detection)
        oldest_ascent_date = self._ascent_repo.get_oldest_ascent_date(profile_id, badge_code)

        # Jeśli turysta nie ma jeszcze wejść dla tej odznaki,
        # oceniamy go po aktualnym regulaminie z dzisiaj (T-02).
        anchor_date: date = oldest_ascent_date if oldest_ascent_date else self._clock.now().date()

        # 2. Krok: Odnalezienie właściwej wersji w czasie
        version_id = self._badge_repo.get_version_id_for_date(badge_code, anchor_date)
        if version_id is None:
            raise UseCaseError(
                f"Brak opublikowanej wersji regulaminu dla odznaki '{badge_code}' "
                f"w wyznaczonym dniu zakotwiczenia ({anchor_date})."
            )

        # 3. Krok: Zapis w bazie (Utworzenie subskrypcji)
        progress_id = self._progress_repo.start_progress(
            profile_id=profile_id,
            badge_code=badge_code,
            version_id=version_id,
            cycle_number=cycle_number,
        )

        return progress_id
