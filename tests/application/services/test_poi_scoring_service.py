"""Testy dla PoiScoringService."""

from datetime import date
from unittest.mock import MagicMock

from application.dto.ascent_dto import AscentDTO
from application.dto.user_context_dto import BadgeProgressDTO, TouristProfileDTO
from application.services.poi_scoring_service import COLOR_PRIORITY, PoiScoringService
from domain.entities.badge_version import BadgeTierDomain, BadgeVersionDomain
from domain.value_objects.ascent import Ascent
from tests.fakes.clock import FakeClock


class TestPoiScoringService:
    """Testy klasy PoiScoringService."""

    def test_init(self):
        """Test inicjalizacji serwisu."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        badge_repo = MagicMock()
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        assert service._progress_repo == progress_repo
        assert service._ascent_repo == ascent_repo
        assert service._profile_repo == profile_repo
        assert service._badge_repo == badge_repo
        assert service._clock == clock
        assert service._cache == cache

    def test_recalculate_and_cache_for_profile_with_no_profile(self):
        """Test przeliczania gdy użytkownik nie ma profilu."""
        progress_repo = MagicMock()
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = None
        badge_repo = MagicMock()
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        profile_repo.get_profile.assert_called_once_with(1)

    def test_recalculate_and_cache_for_profile_with_no_active_progresses(self):
        """Test przeliczania gdy użytkownik nie ma aktywnych postępów."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = []
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        cache.set.assert_called_once()

    def test_recalculate_and_cache_for_profile_with_completed_badge(self):
        """Test przeliczania gdy odznaka jest już ukończona."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = [
            BadgeProgressDTO(
                progress_id=1,
                profile_id=1,
                badge_code="KGP",
                version_id=1,
                cycle_number=1,
                domain_status="COMPLETED",
                logistic_status=None,
                logistic_status_date=None,
            )
        ]
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        cache.set.assert_called_once()

    def test_recalculate_and_cache_for_profile_with_no_version_id(self):
        """Test przeliczania gdy postęp nie ma version_id."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = [
            BadgeProgressDTO(
                progress_id=1,
                profile_id=1,
                badge_code="KGP",
                version_id=None,
                cycle_number=1,
                domain_status="IN_PROGRESS",
                logistic_status=None,
                logistic_status_date=None,
            )
        ]
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        badge_repo.get_version_id_for_date.return_value = 1
        badge_repo.get_badge_version_by_id.return_value = BadgeVersionDomain(
            version_id=1,
            rules=[],
            pool_peak_ids=frozenset([1, 2, 3]),
            tiers=[BadgeTierDomain(tier_id=1, name="Tier 1", required_count=2, order=1)],
        )
        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = []
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        # When version_id is None, the loop continues without calling get_version_id_for_date
        # This is the actual behavior of the service
        cache.set.assert_called_once()

    def test_recalculate_and_cache_for_profile_with_green_color(self):
        """Test przeliczania gdy szczyt jest już zdobyty w obecnym cyklu."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = [
            BadgeProgressDTO(
                progress_id=1,
                profile_id=1,
                badge_code="KGP",
                version_id=1,
                cycle_number=1,
                domain_status="IN_PROGRESS",
                logistic_status=None,
                logistic_status_date=None,
            )
        ]
        ascent_repo = MagicMock()
        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = [
            AscentDTO(peak_id=1, ascent_date=date(2026, 1, 1), region_ids=frozenset())
        ]
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        badge_repo.get_badge_version_by_id.return_value = BadgeVersionDomain(
            version_id=1,
            rules=[],
            pool_peak_ids=frozenset([1, 2, 3]),
            tiers=[BadgeTierDomain(tier_id=1, name="Tier 1", required_count=2, order=1)],
        )
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        cache.set.assert_called_once()
        call_args = cache.set.call_args
        cache_key = call_args[0][0]
        cache_payload = call_args[0][1]
        assert cache_key == "map_state:1"
        assert "colors" in cache_payload
        assert cache_payload["colors"][1] == "GREEN"

    def test_recalculate_and_cache_for_profile_with_blue_color(self):
        """Test przeliczania gdy szczyt był zdobyty w starym cyklu."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = [
            BadgeProgressDTO(
                progress_id=1,
                profile_id=1,
                badge_code="KGP",
                version_id=1,
                cycle_number=1,
                domain_status="IN_PROGRESS",
                logistic_status=None,
                logistic_status_date=None,
            )
        ]
        ascent_repo = MagicMock()
        ascent_repo.get_all_ascents_for_user.return_value = [Ascent(peak_id=1, ascent_date=date(2025, 1, 1))]
        ascent_repo.get_unconsumed_ascents.return_value = []
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        badge_repo.get_badge_version_by_id.return_value = BadgeVersionDomain(
            version_id=1,
            rules=[],
            pool_peak_ids=frozenset([1, 2, 3]),
            tiers=[BadgeTierDomain(tier_id=1, name="Tier 1", required_count=2, order=1)],
        )
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        cache.set.assert_called_once()
        call_args = cache.set.call_args
        cache_payload = call_args[0][1]
        assert cache_payload["colors"][1] == "BLUE"

    def test_recalculate_and_cache_for_profile_with_red_color(self):
        """Test przeliczania gdy szczyt jest nowym celem (RED)."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = [
            BadgeProgressDTO(
                progress_id=1,
                profile_id=1,
                badge_code="KGP",
                version_id=1,
                cycle_number=1,
                domain_status="IN_PROGRESS",
                logistic_status=None,
                logistic_status_date=None,
            )
        ]
        ascent_repo = MagicMock()
        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = []
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        badge_repo.get_badge_version_by_id.return_value = BadgeVersionDomain(
            version_id=1,
            rules=[],
            pool_peak_ids=frozenset([1, 2, 3]),
            tiers=[BadgeTierDomain(tier_id=1, name="Tier 1", required_count=3, order=1)],
        )
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        cache.set.assert_called_once()
        call_args = cache.set.call_args
        cache_payload = call_args[0][1]
        assert cache_payload["colors"][1] == "RED"
        assert cache_payload["scores"][1] > 0

    def test_recalculate_and_cache_for_profile_with_red_color_score_100(self):
        """Test przeliczania gdy brakuje 0 szczytów (score=100)."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = [
            BadgeProgressDTO(
                progress_id=1,
                profile_id=1,
                badge_code="KGP",
                version_id=1,
                cycle_number=1,
                domain_status="IN_PROGRESS",
                logistic_status=None,
                logistic_status_date=None,
            )
        ]
        ascent_repo = MagicMock()
        ascent_repo.get_all_ascents_for_user.return_value = []
        ascent_repo.get_unconsumed_ascents.return_value = []
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        badge_repo.get_badge_version_by_id.return_value = BadgeVersionDomain(
            version_id=1,
            rules=[],
            pool_peak_ids=frozenset([1]),
            tiers=[BadgeTierDomain(tier_id=1, name="Tier 1", required_count=1, order=1)],
        )
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        cache.set.assert_called_once()
        call_args = cache.set.call_args
        cache_payload = call_args[0][1]
        assert cache_payload["colors"][1] == "RED"
        assert cache_payload["scores"][1] == 100

    def test_color_priority_hierarchy(self):
        """Test hierarchii priorytetów kolorów."""
        assert COLOR_PRIORITY["RED"] == 5
        assert COLOR_PRIORITY["ORANGE"] == 4
        assert COLOR_PRIORITY["GREEN"] == 3
        assert COLOR_PRIORITY["BLUE"] == 2
        assert COLOR_PRIORITY["GRAY"] == 1

    def test_blue_color_value_is_literal(self):
        """Test że wartość koloru BLUE jest literałem stringa używanym w cache payload."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = [
            BadgeProgressDTO(
                progress_id=1,
                profile_id=1,
                badge_code="KGP",
                version_id=1,
                cycle_number=1,
                domain_status="IN_PROGRESS",
                logistic_status=None,
                logistic_status_date=None,
            )
        ]
        ascent_repo = MagicMock()
        ascent_repo.get_all_ascents_for_user.return_value = [Ascent(peak_id=1, ascent_date=date(2025, 1, 8))]
        ascent_repo.get_unconsumed_ascents.return_value = []
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        badge_repo.get_badge_version_by_id.return_value = BadgeVersionDomain(
            version_id=1,
            rules=[],
            pool_peak_ids=frozenset([1, 2, 3]),
            tiers=[BadgeTierDomain(tier_id=1, name="Tier 1", required_count=2, order=1)],
        )
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        cache_set_call = cache.set.call_args
        colors = cache_set_call[0][1]["colors"]
        assert colors[1] == "BLUE"
        assert colors[1] != "XXBLUEXX"

    def test_cache_timeout_until_midnight(self):
        """Test że cache timeout jest ustawiony do północy."""
        progress_repo = MagicMock()
        progress_repo.get_active_progresses.return_value = []
        ascent_repo = MagicMock()
        profile_repo = MagicMock()
        profile_repo.get_profile.return_value = TouristProfileDTO(
            profile_id=1,
            is_main_profile=True,
            email="test@example.com",
            nickname="test",
            active_plan="Free",
            max_photos_per_ascent=0,
            max_active_badges=3,
        )
        badge_repo = MagicMock()
        clock = FakeClock()
        cache = MagicMock()

        service = PoiScoringService(progress_repo, ascent_repo, profile_repo, badge_repo, clock, cache)

        service.recalculate_and_cache_for_profile(1)

        call_args = cache.set.call_args
        timeout_seconds = call_args[1]["timeout_seconds"]
        assert timeout_seconds > 0
        assert timeout_seconds <= 86400  # Maksymalnie 24 godziny
