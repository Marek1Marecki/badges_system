"""Testy dla agregatu TouristProfileDomain (AUDYT-037)."""

import pytest

from domain.entities.tourist_profile import TouristProfileDomain
from domain.events import ProfileUpdated


def _make_profile(**overrides) -> TouristProfileDomain:
    """Fabryka testowa profilu turysty."""
    defaults = {
        "profile_id": 1,
        "is_main_profile": True,
        "active_plan": "FREE",
        "max_photos_per_ascent": 1,
        "max_active_badges": 3,
        "club_join_dates": {"KGP": "2020-01-01"},
    }
    defaults.update(overrides)
    return TouristProfileDomain(**defaults)


class TestFreemiumLimits:
    """Logika limitów Freemium."""

    def test_can_log_ascent_within_photo_limit(self):
        profile = _make_profile()
        assert profile.can_log_ascent(photo_count=1) is True

    def test_can_log_ascent_exceeds_photo_limit(self):
        profile = _make_profile(max_photos_per_ascent=1)
        assert profile.can_log_ascent(photo_count=2) is False

    def test_can_track_new_badge_within_limit(self):
        profile = _make_profile(max_active_badges=3)
        assert profile.can_track_new_badge(current_active_count=2) is True

    def test_can_track_new_badge_exceeds_limit(self):
        profile = _make_profile(max_active_badges=3)
        assert profile.can_track_new_badge(current_active_count=3) is False

    def test_non_main_profile_has_no_limits(self):
        profile = _make_profile(is_main_profile=False, max_photos_per_ascent=1, max_active_badges=1)
        assert profile.can_log_ascent(photo_count=100) is True
        assert profile.can_track_new_badge(current_active_count=100) is True


class TestProfileUpdates:
    """Mutacje profilu emitujące ProfileUpdated (AUDYT-051)."""

    def test_change_nickname_emits_event_with_field(self):
        profile = _make_profile()

        updated = profile.with_nickname("nowy-nick", actor_user_id=5)

        assert updated.pending_events  # nie puste
        assert len(updated.events()) == 1
        event = updated.events()[0]
        assert isinstance(event, ProfileUpdated)
        assert event.target_profile_id == 1
        assert event.actor_user_id == 5
        assert "nickname" in event.changed_fields

    def test_change_nickname_empty_raises(self):
        profile = _make_profile()

        with pytest.raises(ValueError, match="Pseudonim profilu nie może być pusty"):
            profile.with_nickname("", actor_user_id=5)

    def test_upgrade_plan_emits_event_only_for_changed_fields(self):
        profile = _make_profile(active_plan="FREE", max_photos_per_ascent=1, max_active_badges=3)

        upgraded = profile.with_upgraded_plan(
            plan="PRO",
            max_photos=5,
            max_badges=99,
            actor_user_id=2,
        )

        event = upgraded.events()[0]
        assert isinstance(event, ProfileUpdated)
        assert set(event.changed_fields) == {"active_plan", "max_photos_per_ascent", "max_active_badges"}
        assert upgraded.active_plan == "PRO"
        assert upgraded.max_photos_per_ascent == 5
        assert upgraded.max_active_badges == 99

    def test_upgrade_plan_same_values_emits_empty_changed_fields(self):
        profile = _make_profile(active_plan="PRO", max_photos_per_ascent=5, max_active_badges=99)

        upgraded = profile.with_upgraded_plan(
            plan="PRO",
            max_photos=5,
            max_badges=99,
            actor_user_id=2,
        )

        event = upgraded.events()[0]
        # Wartości się nie zmieniły — event wciąż emitowany (operacja była próbowana)
        assert event.changed_fields == ()

    def test_immutable_original_after_nickname_change(self):
        """Original agregatu nie ulega zmianie po mutacji (immutable dataclass)."""
        profile = _make_profile()

        profile.with_nickname("nowy", actor_user_id=1)

        # oryginał nie zmienił się
        assert profile.max_photos_per_ascent == 1
        assert profile.max_active_badges == 3
        assert profile.events() == ()