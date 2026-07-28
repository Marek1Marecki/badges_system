"""Dodatkowe testy dla PoiScoringService pokrywające brakujące ścieżki."""

from datetime import date
from unittest.mock import MagicMock

from application.services.poi_scoring_service import PoiScoringService
from domain.value_objects.verification_result import TierResult, VerificationResult
from tests.fakes.clock import FakeClock


class TestPoiScoringServiceMissingCoverage:
    """Testy dla brakujących ścieżek w PoiScoringService."""

    def test_skips_completed_badges(self) -> None:
        """Odznaki ze statusem COMPLETED są pomijane w obliczeniach."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        cache = MagicMock()
        clock = FakeClock()

        profile = MagicMock()
        profile.birth_date = None
        profile.club_join_dates = {}
        profile_repo.get_profile.return_value = profile

        completed_progress = MagicMock()
        completed_progress.badge_code = "KGP"
        completed_progress.domain_status = "COMPLETED"
        progress_repo.get_active_progresses.return_value = [completed_progress]

        ascent_repo.get_all_ascents_for_user.return_value = []

        uc = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)
        uc.recalculate_and_cache_for_profile(profile_id=1)

        badge_repo.get_badge_version_by_id.assert_not_called()

    def test_uses_latest_version_when_no_version_id(self) -> None:
        """Gdy progress nie ma version_id, używa najnowszej wersji regulaminu."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        cache = MagicMock()
        clock = FakeClock()

        profile = MagicMock()
        profile.birth_date = None
        profile.club_join_dates = {}
        profile_repo.get_profile.return_value = profile

        progress = MagicMock()
        progress.badge_code = "KGP"
        progress.domain_status = "IN_PROGRESS"
        progress.version_id = None
        progress.cycle_number = 1
        progress_repo.get_active_progresses.return_value = [progress]

        badge_version = MagicMock()
        badge_version.pool_peak_ids = [1, 2, 3]
        badge_version.evaluate.return_value = VerificationResult(
            verified=False, status="NOT_STARTED", valid_ascents_count=0, errors=[], tiers=[]
        )
        badge_repo.get_latest_badge_version.return_value = badge_version

        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = []

        uc = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)
        uc.recalculate_and_cache_for_profile(profile_id=1)

        badge_repo.get_latest_badge_version.assert_called_once_with("KGP")

    def test_skips_progress_when_no_badge_version(self) -> None:
        """Pomija progress, gdy nie można znaleźć wersji regulaminu."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        cache = MagicMock()
        clock = FakeClock()

        profile = MagicMock()
        profile.birth_date = None
        profile.club_join_dates = {}
        profile_repo.get_profile.return_value = profile

        progress = MagicMock()
        progress.badge_code = "KGP"
        progress.domain_status = "IN_PROGRESS"
        progress.version_id = 42
        progress.cycle_number = 1
        progress_repo.get_active_progresses.return_value = [progress]

        badge_repo.get_badge_version_by_id.return_value = None

        ascent_repo.get_all_ascents_for_user.return_value = []

        uc = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)
        uc.recalculate_and_cache_for_profile(profile_id=1)

        cache.set.assert_called_once()

    def test_skips_progress_when_no_pool_peak_ids(self) -> None:
        """Pomija progress, gdy badge_version nie ma pool_peak_ids."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        cache = MagicMock()
        clock = FakeClock()

        profile = MagicMock()
        profile.birth_date = None
        profile.club_join_dates = {}
        profile_repo.get_profile.return_value = profile

        progress = MagicMock()
        progress.badge_code = "KGP"
        progress.domain_status = "IN_PROGRESS"
        progress.version_id = 42
        progress.cycle_number = 1
        progress_repo.get_active_progresses.return_value = [progress]

        badge_version = MagicMock()
        badge_version.pool_peak_ids = []
        badge_repo.get_badge_version_by_id.return_value = badge_version

        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = []

        uc = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)
        uc.recalculate_and_cache_for_profile(profile_id=1)

        cache.set.assert_called_once()

    def test_applies_cutoff_date_for_cycle_2(self) -> None:
        """Dla cyklu > 1 stosuje cutoff_date z poprzedniego cyklu."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        cache = MagicMock()
        clock = FakeClock()

        profile = MagicMock()
        profile.birth_date = None
        profile.club_join_dates = {}
        profile_repo.get_profile.return_value = profile

        progress = MagicMock()
        progress.badge_code = "KGP"
        progress.domain_status = "IN_PROGRESS"
        progress.version_id = 42
        progress.cycle_number = 2
        progress_repo.get_active_progresses.return_value = [progress]

        prev_cycle = MagicMock()
        prev_cycle.logistic_status_date = date(2023, 1, 1)

        def get_progress_side_effect(profile_id, badge_code, cycle_number):
            if cycle_number == 1:
                return prev_cycle
            return None

        progress_repo.get_progress.side_effect = get_progress_side_effect

        badge_version = MagicMock()
        badge_version.pool_peak_ids = [1]
        badge_version.evaluate.return_value = VerificationResult(
            verified=False, status="NOT_STARTED", valid_ascents_count=0, errors=[], tiers=[]
        )
        badge_repo.get_badge_version_by_id.return_value = badge_version

        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = []

        uc = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)
        uc.recalculate_and_cache_for_profile(profile_id=1)

        ascent_repo.get_unconsumed_ascents.assert_called_once()
        call_args = ascent_repo.get_unconsumed_ascents.call_args
        # cutoff_date is passed as the 3rd positional argument
        assert call_args.args[2] == date(2023, 1, 1)

    def test_calculates_score_for_red_peaks(self) -> None:
        """Oblicza wynik 100 dla szczytów, które kończą odznakę."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        cache = MagicMock()
        clock = FakeClock()

        profile = MagicMock()
        profile.birth_date = None
        profile.club_join_dates = {}
        profile_repo.get_profile.return_value = profile

        progress = MagicMock()
        progress.badge_code = "KGP"
        progress.domain_status = "IN_PROGRESS"
        progress.version_id = 42
        progress.cycle_number = 1
        progress_repo.get_active_progresses.return_value = [progress]

        badge_version = MagicMock()
        badge_version.pool_peak_ids = [1, 2]
        badge_version.evaluate.side_effect = [
            VerificationResult(
                verified=False,
                status="NOT_STARTED",
                valid_ascents_count=0,
                errors=[],
                tiers=[TierResult(tier_id=1, name="Standard", status="NOT_STARTED", required_count=2)],
            ),  # current
            VerificationResult(
                verified=True,
                status="COMPLETED",
                valid_ascents_count=1,
                errors=[],
                tiers=[TierResult(tier_id=1, name="Standard", status="COMPLETED", required_count=1)],
            ),  # sim for peak 1
            VerificationResult(
                verified=False,
                status="IN_PROGRESS",
                valid_ascents_count=1,
                errors=[],
                tiers=[TierResult(tier_id=1, name="Standard", status="IN_PROGRESS", required_count=2)],
            ),  # sim for peak 2
        ]
        badge_repo.get_badge_version_by_id.return_value = badge_version

        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = []

        uc = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)
        uc.recalculate_and_cache_for_profile(profile_id=1)

        cache_set_call = cache.set.call_args
        scores = cache_set_call[0][1]["scores"]
        assert scores[1] == 100  # Peak 1 completes badge (missing_after_ascent = 0)
        assert scores[2] == 100  # Peak 2: 100 / (2-1) = 100

    def test_marks_orange_when_simulation_does_not_increase_count(self) -> None:
        """Oznacza szczyt jako ORANGE, gdy symulacja nie podbija licznika."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        cache = MagicMock()
        clock = FakeClock()

        profile = MagicMock()
        profile.birth_date = None
        profile.club_join_dates = {}
        profile_repo.get_profile.return_value = profile

        progress = MagicMock()
        progress.badge_code = "KGP"
        progress.domain_status = "IN_PROGRESS"
        progress.version_id = 42
        progress.cycle_number = 1
        progress_repo.get_active_progresses.return_value = [progress]

        badge_version = MagicMock()
        badge_version.pool_peak_ids = [1]
        badge_version.evaluate.return_value = VerificationResult(
            verified=False, status="NOT_STARTED", valid_ascents_count=0, errors=[], tiers=[]
        )
        badge_repo.get_badge_version_by_id.return_value = badge_version

        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = []

        uc = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)
        uc.recalculate_and_cache_for_profile(profile_id=1)

        cache_set_call = cache.set.call_args
        colors = cache_set_call[0][1]["colors"]
        assert colors[1] == "ORANGE"

    def test_accumulates_scores_and_prioritizes_colors(self) -> None:
        """Akumuluje wyniki i priorytetyzuje kolory zgodnie z COLOR_PRIORITY."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        cache = MagicMock()
        clock = FakeClock()

        profile = MagicMock()
        profile.birth_date = None
        profile.club_join_dates = {}
        profile_repo.get_profile.return_value = profile

        progress1 = MagicMock()
        progress1.badge_code = "KGP"
        progress1.domain_status = "IN_PROGRESS"
        progress1.version_id = 42
        progress1.cycle_number = 1

        progress2 = MagicMock()
        progress2.badge_code = "GOT"
        progress2.domain_status = "IN_PROGRESS"
        progress2.version_id = 43
        progress2.cycle_number = 1

        progress_repo.get_active_progresses.return_value = [progress1, progress2]

        badge_version1 = MagicMock()
        badge_version1.pool_peak_ids = [1]
        badge_version1.evaluate.return_value = VerificationResult(
            verified=False, status="NOT_STARTED", valid_ascents_count=0, errors=[], tiers=[]
        )
        badge_repo.get_badge_version_by_id.side_effect = [badge_version1, badge_version1]

        ascent_dto = MagicMock()
        ascent_dto.peak_id = 1
        ascent_dto.to_domain.return_value = MagicMock(peak_id=1)
        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = [ascent_dto]

        uc = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)
        uc.recalculate_and_cache_for_profile(profile_id=1)

        cache_set_call = cache.set.call_args
        colors = cache_set_call[0][1]["colors"]
        # GREEN ma wyższy priorytet niż GRAY
        assert colors[1] == "GREEN"
