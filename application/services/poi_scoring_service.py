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
        """Inicjalizuje serwis z wymaganymi repozytoriami i zależnościami."""
        self._progress_repo = progress_repository
        self._ascent_repo = ascent_repository
        self._profile_repo = profile_repository
        self._badge_repo = badge_repository
        self._clock = clock
        self._cache = cache

    def recalculate_and_cache_for_profile(self, profile_id: int) -> None:
        """Główna metoda wywoływana przez Celery w tle."""
        now = self._clock.now()
        today_date = now.date()

        profile = self._profile_repo.get_profile(profile_id)
        birth_date = profile.birth_date if profile else None
        club_dates = profile.club_join_dates if profile else {}

        active_progresses = self._progress_repo.get_active_progresses(profile_id)

        completed_badges = frozenset([p.badge_code for p in active_progresses if p.domain_status == "COMPLETED"])

        context = VerificationContext(
            evaluation_time=now,
            tourist_birth_date=birth_date,
            club_join_dates=club_dates,
            completed_badge_codes=completed_badges,
        )

        final_scores: dict[int, int] = defaultdict(int)
        final_colors: dict[int, str] = {}

        all_ascents = self._ascent_repo.get_all_ascents_for_user(profile_id)
        all_climbed_peak_ids = {a.peak_id for a in all_ascents}

        for prog in active_progresses:
            if prog.domain_status == "COMPLETED":
                continue

            # MAGIA WIZUALIZACJI: Rozwiązanie Leniwego Zakotwiczenia
            if prog.version_id:
                # Turysta ma przypięte Prawa Nabyte (Zalogował już wejście)
                badge_version = self._badge_repo.get_badge_version_by_id(prog.version_id)
            else:
                # Turysta tylko subskrybuje. Dla celów mapy pokazujemy mu po prostu
                # aktualnie obowiązujące zasady z dzisiaj (najnowszą wersję).
                badge_version = self._badge_repo.get_latest_badge_version(prog.badge_code)

            if not badge_version:
                continue

            cutoff_date = None
            if prog.cycle_number > 1:
                prev_cycle = self._progress_repo.get_progress(profile_id, prog.badge_code, prog.cycle_number - 1)
                if prev_cycle and prev_cycle.logistic_status_date:
                    cutoff_date = prev_cycle.logistic_status_date

            unconsumed_ascents_dto = self._ascent_repo.get_unconsumed_ascents(profile_id, prog.badge_code, cutoff_date)
            domain_ascents = [dto.to_domain() for dto in unconsumed_ascents_dto]

            # 1. Oceń aktualny stan, aby znaleźć aktualną liczbę ważnych wejść
            current_eval = badge_version.evaluate(domain_ascents, context)
            curr_valid_count = current_eval.valid_ascents_count

            unconsumed_peak_ids = {a.peak_id for a in domain_ascents}

            if not badge_version.pool_peak_ids:
                continue

            # PERF (Performance Warning): O(pool_size * reguły).
            # Ewaluacja całego agregatu dla każdego szczytu "na sucho".
            # Przy 3 aktywnych odznakach (po 200 szczytów) = 600 pełnych iteracji domenowych.
            # Akceptowalne dla workerów w tle (Asynchronia). Jeśli czas wzrośnie > 5s,
            # rozważyć optymalizację algorytmów Set Math wewnątrz samych Reguł.
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
                    # Zwraca obiekt VerificationResult, a nie słownik
                    sim_eval = badge_version.evaluate(domain_ascents + [sim_ascent], context)
                    sim_valid_count = sim_eval.valid_ascents_count  # <--- ZMIANA (odczyt z obiektu)

                    # Jeśli to wirtualne wejście podbiło licznik, znaczy że szczyt jest ważny!
                    if sim_valid_count > curr_valid_count:
                        color = "RED"

                        # Pobieramy docelowy próg z najwyższego niedokończonego stopnia
                        # (Ponieważ Domena wspiera teraz wiele stopni, szukamy pierwszego, który nie jest COMPLETED)
                        pending_tier = next((t for t in sim_eval.tiers if t.status != "COMPLETED"), None)
                        target = pending_tier.required_count if pending_tier else len(badge_version.pool_peak_ids)

                        missing_after_ascent = max(target - sim_valid_count, 0)

                        if missing_after_ascent == 0:
                            score = 100
                        else:
                            score = round(100.0 / missing_after_ascent)
                    else:
                        color = "ORANGE"  # Zablokowany na dziś

                # 3. Akumulacja i priorytetyzacja kolorów
                final_scores[peak_id] += score
                current_color = final_colors.get(peak_id, "GRAY")

                if COLOR_PRIORITY[color] > COLOR_PRIORITY[current_color]:
                    final_colors[peak_id] = color

        # Zapisz w Cache z TTL dokładnie do północy
        tomorrow = today_date + timedelta(days=1)
        midnight = datetime.combine(tomorrow, dt_time.min, tzinfo=now.tzinfo)
        seconds_to_midnight = int((midnight - now).total_seconds())

        cache_payload = {
            "scores": dict(final_scores),
            "colors": final_colors,
        }

        cache_key = f"map_state:{profile_id}"
        self._cache.set(cache_key, cache_payload, timeout_seconds=seconds_to_midnight)
