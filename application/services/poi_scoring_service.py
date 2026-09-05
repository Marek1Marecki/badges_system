"""Usługa Aplikacyjna: Silnik Punktacji i Kolorowania Mapy.

Zgodnie z ADR-010 i ADR-015: Wylicza punkty 100/n dla szczytów i nadaje im kolory. Wynik jest agresywnie buforowany
Cache z precyzyjnym czasem wygaśnięcia o północy.

AUDYT-033: Stały TTL 300s (5 min) zapewnia świeżość stanu mapy, niezależnie od
czasu dnia. Ogranicza to ryzyko wycieków pamięciowych w Redis przy 100k+ profilach.

AUDYT-035: Logika biznesowa (symulacja wejść, algebra punktowa) została
wydzielona do `domain.services.BadgeEligibilityDomainService`.
Ta warstwa aplikacji odpowiada **wyłącznie** na orkiestrację: pobieranie danych,
wstrzykiwanie czasu, wywołanie serwisu domenowego i zapis do Redisa.
"""

from collections import defaultdict

from application.ports.badge_repository_port import BadgeRepositoryPort
from application.ports.cache_port import CachePort
from application.ports.clock_port import ClockPort
from application.ports.user_progress_port import (
    AscentLogRepositoryPort,
    TouristProfileRepositoryPort,
    UserProgressRepositoryPort,
)

# AUDYT-035: backward-compat re-export — testy importują COLOR_PRIORITY
# z tego modułu. Przekierowujemy do Czystej Dziedziny.
from domain.enums import DomainStatus
from domain.services.badge_eligibility_domain_service import (  # noqa: F401
    COLOR_PRIORITY,
    BadgeEligibilityDomainService,
)
from domain.value_objects.verification_context import VerificationContext

MAP_STATE_TTL_SECONDS: int = 300


class PoiScoringService:
    """Silnik przeliczający i buforujący potencjał celów turystycznych.

    Orkiestruje pobieranie danych i buforowanie; deleguje logikę
    biznesową do ``BadgeEligibilityDomainService``.
    """

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
        self._eligibility = BadgeEligibilityDomainService()

    def recalculate_and_cache_for_profile(self, profile_id: int) -> None:
        """Główna metoda wywoływana przez Celery w tle.

        Args:
          profile_id: ID profilu turysty.

        Returns:
          None.
        """
        now = self._clock.now()
        today_date = now.date()

        # 1. Pobranie danych kontekstowych (warstwa aplikacji)
        profile = self._profile_repo.get_profile(profile_id)
        birth_date = profile.birth_date if profile else None
        club_dates = profile.club_join_dates if profile else {}

        active_progresses = self._progress_repo.get_active_progresses(profile_id)

        completed_badges = frozenset(
            p.badge_code for p in active_progresses if p.domain_status == DomainStatus.COMPLETED
        )

        context = VerificationContext(
            evaluation_time=now,
            tourist_birth_date=birth_date,
            club_join_dates=club_dates,
            completed_badge_codes=completed_badges,
        )

        all_ascents = self._ascent_repo.get_all_ascents_for_user(profile_id)
        all_climbed_peak_ids = frozenset(a.object_id for a in all_ascents)

        final_scores: dict[int, int] = defaultdict(int)
        final_colors: dict[int, str] = {}

        for prog in active_progresses:
            if prog.domain_status == DomainStatus.COMPLETED:
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

            # 2. Ocena stanu — delegujemy do Czystej Dziedziny
            current_eval = badge_version.evaluate(domain_ascents, context)
            curr_valid_count = current_eval.valid_ascents_count

            current_cycle_peak_ids = frozenset(a.object_id for a in domain_ascents)

            # PERF (Performance Warning): O(pool_size * reguły).
            # Ewaluacja całego agregatu dla każdego szczytu "na sucho".
            # Przy 3 aktywnych odznakach (po 200 szczytów) = 600 pełnych iteracji domenowych.
            # Akceptowalne dla workerów w tle (Asynchronia). Jeśli czas wzrośnie > 5s,
            # rozważyć optymalizację algorytmów Set Math wewnątrz samych Reguł.
            for peak_id in badge_version.pool_peak_ids:
                result = self._eligibility.simulate_peak_value(
                    version=badge_version,
                    domain_ascents=domain_ascents,
                    peak_id=peak_id,
                    today_date=today_date,
                    current_cycle_peak_ids=current_cycle_peak_ids,
                    all_climbed_peak_ids=all_climbed_peak_ids,
                    context=context,
                    current_valid_count=curr_valid_count,
                )
                # 4. Akumulacja i priorytetyzacja kolorów (polityka wizualna)
                final_scores[peak_id] += result.score
                current_color = final_colors.get(peak_id, "GRAY")

                if COLOR_PRIORITY[result.color] > COLOR_PRIORITY[current_color]:
                    final_colors[peak_id] = result.color

        # 5. Zapis do bufora Redis z TTL 300s (AUDYT-033)
        cache_payload = {
            "scores": dict(final_scores),
            "colors": final_colors,
        }

        cache_key = f"map_state:{profile_id}"
        self._cache.set(cache_key, cache_payload, timeout_seconds=MAP_STATE_TTL_SECONDS)
