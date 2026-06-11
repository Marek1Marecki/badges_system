"""Usługa Aplikacyjna: Silnik Punktacji i Kolorowania Mapy.

Zgodnie z ADR-010 i ADR-015: Wylicza punkty 100/n dla szczytów i nadaje im kolory.
Wynik jest agresywnie buforowany w Cache z precyzyjnym czasem wygaśnięcia o północy.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from datetime import time as dt_time

from application.ports.badge_repository_port import BadgeRepositoryPort
from application.ports.cache_port import CachePort
from application.ports.clock_port import ClockPort
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)
from domain.value_objects.ascent import Ascent
from domain.value_objects.verification_context import VerificationContext

# Hierarchia kolorów zgodnie z ADR-010 i UI_GUIDELINES.md
COLOR_PRIORITY = {
    "RED": 5,  # Nowy cel (Idź!)
    "ORANGE": 4,  # Zablokowane dziś (np. zła zima)
    "GREEN": 3,  # Zaliczone w obecnym cyklu
    "BLUE": 2,  # Zaliczone w starym cyklu (Wymaga powtórki)
    "GRAY": 1,  # Poza kontekstem
}


class PoiScoringService:
    """Silnik przeliczający i buforujący potencjał celów turystycznych."""

    def __init__(
        self,
        progress_repository: UserProgressRepositoryPort,
        ascent_repository: AscentLogRepositoryPort,
        profile_repository: TouristProfileRepositoryPort,
        badge_repository: BadgeRepositoryPort,
        clock: ClockPort,
        cache: CachePort,
    ) -> None:
        """Inicjalizuje serwis z repozytoriami i zależnościami."""
        self._progress_repo = progress_repository
        self._ascent_repo = ascent_repository
        self._profile_repo = profile_repository
        self._badge_repo = badge_repository
        self._clock = clock
        self._cache = cache

    def recalculate_and_cache_for_user(self, user_id: int) -> None:
        """Główna metoda wywoływana przez Celery w tle."""
        now = self._clock.now()
        today_date = now.date()

        profile = self._profile_repo.get_profile(user_id)
        birth_date = profile.birth_date if profile else None
        club_dates = profile.club_join_dates if profile else {}

        active_progresses = self._progress_repo.get_active_progresses(user_id)

        completed_badges = frozenset([p.badge_code for p in active_progresses if p.domain_status == "COMPLETED"])

        context = VerificationContext(
            evaluation_time=now,
            tourist_birth_date=birth_date,
            club_join_dates=club_dates,
            completed_badge_codes=completed_badges,
        )

        final_scores: dict[int, int] = defaultdict(int)
        final_colors: dict[int, str] = {}

        all_ascents = self._ascent_repo.get_all_ascents_for_user(user_id)
        all_climbed_peak_ids = {a.peak_id for a in all_ascents}

        for prog in active_progresses:
            if prog.domain_status == "COMPLETED" or not prog.version_id:
                continue

            badge_version = self._badge_repo.get_badge_version_by_id(prog.version_id)
            if not badge_version:
                continue

            cutoff_date = None
            if prog.cycle_number > 1:
                prev_cycle = self._progress_repo.get_progress(user_id, prog.badge_code, prog.cycle_number - 1)
                if prev_cycle and prev_cycle.logistic_status_date:
                    cutoff_date = prev_cycle.logistic_status_date

            unconsumed_ascents_dto = self._ascent_repo.get_unconsumed_ascents(user_id, prog.badge_code, cutoff_date)
            domain_ascents = [dto.to_domain() for dto in unconsumed_ascents_dto]

            # 1. Oceń aktualny stan, aby znaleźć "n"
            current_eval = badge_version.evaluate(domain_ascents, context)
            curr_valid_count = current_eval.get("valid_ascents_count", 0)
            required_count = current_eval.get("required_count", len(badge_version.pool_peak_ids))

            missing_n = required_count - curr_valid_count
            score_value = 100 // missing_n if missing_n > 0 else 0

            unconsumed_peak_ids = {a.peak_id for a in domain_ascents}

            # Wildcard Rules (otwarte regiony) pomijamy w pre-kalkulacji wizualnej
            if not badge_version.pool_peak_ids:
                continue

            # 2. Symulacja dla każdego szczytu z Puli
            for peak_id in badge_version.pool_peak_ids:
                color = "GRAY"
                score = 0

                if peak_id in unconsumed_peak_ids:
                    color = "GREEN"
                elif peak_id in all_climbed_peak_ids:
                    color = "BLUE"
                else:
                    # Symulacja: "A co gdyby turysta wszedł tu dzisiaj?"
                    sim_ascent = Ascent(peak_id=peak_id, ascent_date=today_date, region_ids=frozenset())
                    sim_eval = badge_version.evaluate(domain_ascents + [sim_ascent], context)

                    if sim_eval.get("valid_ascents_count", 0) > curr_valid_count:
                        color = "RED"
                        score = score_value
                    else:
                        color = "ORANGE"  # Np. w zimie szczyt zamknięty przez reguły

                # 3. Akumulacja i priorytetyzacja kolorów
                final_scores[peak_id] += score
                current_color = final_colors.get(peak_id, "GRAY")

                if COLOR_PRIORITY[color] > COLOR_PRIORITY[current_color]:
                    final_colors[peak_id] = color

        # Zapisz w Cache z TTL dokładnie do północy (Czas na odświeżenie okien czasowych!)
        tomorrow = today_date + timedelta(days=1)
        midnight = datetime.combine(tomorrow, dt_time.min, tzinfo=now.tzinfo)
        seconds_to_midnight = int((midnight - now).total_seconds())

        cache_payload = {
            "scores": dict(final_scores),
            "colors": final_colors,
        }

        cache_key = f"map_state:{user_id}"
        self._cache.set(cache_key, cache_payload, timeout_seconds=seconds_to_midnight)
