"""Testy dla DjangoBadgeRepo - budowniczych reguł."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model

from domain.rules.badge_rules import MinAgeRule, TimeLimitRule
from infrastructure.adapters.persistence.django_badge_repo import DjangoBadgeRepository

User = get_user_model()


def _create_organizer():
    from apps.badges.models import OrganizerModel

    return OrganizerModel.objects.create(name="PTTK")


@pytest.mark.integration
@pytest.mark.django_db
class TestDjangoBadgeRepositoryHydration:
    """Integracyjne testy hydracji wersji odznaki z JSONB (Invariant R-02)."""

    def setup_method(self):
        self.repo = DjangoBadgeRepository()

    def test_hydrates_valid_version(self):
        """Hydratuje poprawną wersję odznaki z prawidłowym JSONB rules."""
        from apps.badges.models import BadgeModel, BadgeTierModel, BadgeVersionModel, TouristObject

        user = User.objects.create_user(username="validator", email="v@example.com")
        badge = BadgeModel.objects.create(code="KGP", name="Korona Gór Polski", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v2024",
            valid_from=date(2024, 1, 1),
            rules=[
                {"type": "TimeLimitRule", "limit_in_years": 5},
                {"type": "MinAgeRule", "min_age": 18},
            ],
        )
        peak = TouristObject.objects.create(name="P1", type="Szczyt", is_active=True, status="READY")
        version.pool_peaks.add(peak)
        BadgeTierModel.objects.create(version=version, name="Jednostopniowa", order=1, required_peaks_count=1)

        result = self.repo.get_badge_version("KGP", "v2024")

        assert result is not None
        assert result.version_id == version.id
        assert len(result.rules) == 2
        assert isinstance(result.rules[0], TimeLimitRule)
        assert isinstance(result.rules[1], MinAgeRule)
        assert len(result.tiers) == 1
        assert result.tiers[0].required_count == 1

    def test_raises_on_missing_rule_type(self):
        """Rzuca ValueError gdy reguła w JSONB nie ma pola 'type'."""
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="BADGE", name="Badge", organizer=_create_organizer())
        BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v1",
            valid_from=date(2024, 1, 1),
            rules=[{"limit_in_years": 5}],
        )

        with pytest.raises(ValueError, match="Reguła bez pola 'type'"):
            self.repo.get_badge_version("BADGE", "v1")

    def test_raises_on_unknown_rule_type(self):
        """Rzuca ValueError gdy reguła ma nieznany typ."""
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="BADGE", name="Badge", organizer=_create_organizer())
        BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v1",
            valid_from=date(2024, 1, 1),
            rules=[{"type": "NonExistentRule"}],
        )

        with pytest.raises(ValueError, match="Nieznany typ reguły 'NonExistentRule'"):
            self.repo.get_badge_version("BADGE", "v1")

    def test_raises_on_missing_required_parameter(self):
        """Rzuca ValueError gdy reguła ma typ, ale brakuje wymaganego parametru."""
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="BADGE", name="Badge", organizer=_create_organizer())
        BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v1",
            valid_from=date(2024, 1, 1),
            rules=[{"type": "TimeLimitRule"}],
        )

        with pytest.raises(ValueError, match="limit_in_years"):
            self.repo.get_badge_version("BADGE", "v1")

    def test_raises_on_invalid_date_format(self):
        """Rzuca ValueError gdy parametr daty ma zły format."""
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="BADGE", name="Badge", organizer=_create_organizer())
        BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v1",
            valid_from=date(2024, 1, 1),
            rules=[{"type": "StartDateRule", "start_date": "not-a-date"}],
        )

        with pytest.raises(ValueError, match="format daty"):
            self.repo.get_badge_version("BADGE", "v1")

    def test_raises_on_non_list_rules(self):
        """Rzuca błąd gdy pole rules nie jest listą (uszkodzony JSONB)."""
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="BADGE", name="Badge", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v1",
            valid_from=date(2024, 1, 1),
            rules="not-a-list",
        )

        with pytest.raises((ValueError, TypeError)):
            self.repo.get_badge_version("BADGE", "v1")

    def test_raises_on_none_rules(self):
        """Rzuca błąd gdy pole rules to None (uszkodzony JSONB)."""
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="BADGE", name="Badge", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v1",
            valid_from=date(2024, 1, 1),
            rules=None,
        )

        with pytest.raises((ValueError, TypeError)):
            self.repo.get_badge_version("BADGE", "v1")

    def test_hydrates_multi_tier_with_distinct_thresholds(self):
        """AUDYT-004 / TD-03: progi zaliczeniowe pochodzą z poszczególnych Stopni (BadgeTier),
        a nie są sztucznie ustawiane jako len(pool_peaks)."""
        from apps.badges.models import BadgeModel, BadgeTierModel, BadgeVersionModel, TouristObject

        badge = BadgeModel.objects.create(code="MT", name="Multi-Tier", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v2024",
            valid_from=date(2024, 1, 1),
            rules=[],
        )
        peaks = [
            TouristObject.objects.create(name=f"P{i}", type="Szczyt", is_active=True, status="READY") for i in range(5)
        ]
        version.pool_peaks.set(peaks)
        BadgeTierModel.objects.create(version=version, name="brazowa", order=1, required_peaks_count=1)
        BadgeTierModel.objects.create(version=version, name="srebrna", order=2, required_peaks_count=3)

        result = self.repo.get_badge_version("MT", "v2024")

        assert result is not None
        assert len(result.tiers) == 2
        assert result.tiers[0].name == "brazowa"
        assert result.tiers[0].required_count == 1  # nie len(pool_peaks)=5
        assert result.tiers[1].name == "srebrna"
        assert result.tiers[1].required_count == 3  # nie len(pool_peaks)=5

    def test_hydrates_fallback_to_pool_size_when_required_peaks_count_is_null(self):
        """EC-031 / TD-03: gdy Tier nie ma required_peaks_count, fallback = len(pool_peaks).
        To poprawny fallback dla odznak jednostopniowych wymagających 100% puli."""
        from apps.badges.models import BadgeModel, BadgeTierModel, BadgeVersionModel, TouristObject

        badge = BadgeModel.objects.create(code="FB", name="Fallback", organizer=_create_organizer())
        version = BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v2024",
            valid_from=date(2024, 1, 1),
            rules=[],
        )
        peaks = [
            TouristObject.objects.create(name=f"F{i}", type="Szczyt", is_active=True, status="READY") for i in range(4)
        ]
        version.pool_peaks.set(peaks)
        BadgeTierModel.objects.create(version=version, name="jednostopniowa", order=1, required_peaks_count=None)

        result = self.repo.get_badge_version("FB", "v2024")

        assert result is not None
        assert len(result.tiers) == 1
        assert result.tiers[0].required_count == len(peaks)  # fallback = 4
        assert result.tiers[0].required_count == 4


@pytest.mark.integration
@pytest.mark.django_db
class TestDjangoBadgeRepositoryByHydrationFailFast:
    """Weryfikacja Invariant R-02: Fail-Fast dla fabryk reguł (JSONB -> Domena)."""

    def setup_method(self):
        self.repo = DjangoBadgeRepository()

    def test_corrupted_jsonb_does_not_reach_domain(self):
        """Uszkodzony JSONB w regule nie przekracza granicy adapteru -> domena."""
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="BADGE", name="Badge", organizer=_create_organizer())
        BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v1",
            valid_from=date(2024, 1, 1),
            rules=[{"type": "MinAgeRule"}],
        )

        with pytest.raises(ValueError):
            self.repo.get_badge_version("BADGE", "v1")

    def test_unknown_rule_type_does_not_reach_domain(self):
        """Nieznany typ reguły jest odrzucany przed utworzeniem obiektu domenowego."""
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="BADGE", name="Badge", organizer=_create_organizer())
        BadgeVersionModel.objects.create(
            badge=badge,
            version_code="v1",
            valid_from=date(2024, 1, 1),
            rules=[{"type": "GhostRule", "param": "x"}],
        )

        with pytest.raises(ValueError, match="Nieznany typ reguły 'GhostRule'"):
            self.repo.get_badge_version("BADGE", "v1")


@pytest.mark.integration
class TestBadgeVersionDateResolution:
    """Testy AUDYT-012: Sanity check praw nabywczych i Cinderella Bug.

    Model BadgeVersionModel posiada tylko pole ``valid_from``
    (brak ``valid_to``), więc wersja obowiązująca w danym dniu
    to najnowsza wersja z ``valid_from <= target_date``.
    """

    def setup_method(self):
        self.repo = DjangoBadgeRepository()

    @pytest.mark.django_db(transaction=True)
    def test_get_version_id_for_date_returns_latest_valid(self):
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP", name="KGP", organizer=_create_organizer())
        v1 = BadgeVersionModel.objects.create(badge=badge, version_code="v1", valid_from=date(2020, 1, 1))
        v2 = BadgeVersionModel.objects.create(badge=badge, version_code="v2", valid_from=date(2024, 1, 1))

        result = self.repo.get_version_id_for_date("KGP", date(2024, 6, 15))

        assert result == v2.id

    @pytest.mark.django_db(transaction=True)
    def test_get_version_id_for_date_excludes_future_versions(self):
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP", name="KGP", organizer=_create_organizer())
        BadgeVersionModel.objects.create(badge=badge, version_code="v1", valid_from=date(2020, 1, 1))
        future = BadgeVersionModel.objects.create(badge=badge, version_code="v2", valid_from=date(2025, 1, 1))

        result = self.repo.get_version_id_for_date("KGP", date(2024, 1, 1))

        assert result is not None
        assert result != future.id

    @pytest.mark.django_db(transaction=True)
    def test_get_latest_badge_version_excludes_future(self):
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP", name="KGP", organizer=_create_organizer())
        BadgeVersionModel.objects.create(badge=badge, version_code="v1", valid_from=date(2020, 1, 1))
        v_future = BadgeVersionModel.objects.create(badge=badge, version_code="v2", valid_from=date(2099, 1, 1))

        result = self.repo.get_latest_badge_version("KGP")

        assert result is not None
        assert result.version_id != v_future.id

    @pytest.mark.django_db(transaction=True)
    def test_get_version_id_for_date_returns_none_when_no_valid_version(self):
        from apps.badges.models import BadgeModel, BadgeVersionModel

        badge = BadgeModel.objects.create(code="KGP", name="KGP", organizer=_create_organizer())
        BadgeVersionModel.objects.create(badge=badge, version_code="v1", valid_from=date(2025, 1, 1))

        result = self.repo.get_version_id_for_date("KGP", date(2024, 1, 1))

        assert result is None
